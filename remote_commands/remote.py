#!/usr/bin/env python

########################################################################################
#
# This is a python script to perform ssh and scp on a remote host
#
# This tool can be run from Windows, Mac or Linux machines installed with python 2.x
# The machine should have access to the remote machines
#
# Type 'python remote.py' and press enter for running instructions
#
# For any questions or suggestions please contact : Ajmal Yusuf <ayusuf@hortonworks.com>
########################################################################################

import sys
import os
import re
import json
import platform
import logging
import datetime
import pprint
import pexpect
import argparse
import itertools

logger = logging.getLogger(__name__)

# Change the default values for the below parameters
# ==================================================
version = '1.1'
default_live_run = False
default_variables = {
    'shell' : 'bash',
    'timeout_secs' : '60',
    'shell_prompt' : '\\$ $',
    'password_prompt' : 'password: ',
    'sudo_password_prompt' : 'password for {username}:',
    'progress_prompt' : 'ETA'
}
default_options = '-o CheckHostIP=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet'
scp_format = {
    'get' : "{shell} -c 'scp -r {options} {username}@{hostname}:{source} {target_dir}'",
    'send' : "{shell} -c 'scp -r {options} {source} {username}@{hostname}:{target_dir}'"
}
ssh_format = 'ssh {options} {username}@{hostname}'
# ==================================================

var_regex = re.compile('({[ \t]*(\w+)[ \t]*})')
NO_RECURSIONS = 10

action_mandatory_params = {
    "ssh" : ['timeout_secs', 'hostname', 'username', 'password', 'password_prompt',
             'shell_prompt', 'sudo_password_prompt'],
    "scp" : ['shell', 'timeout_secs', 'hostname', 'username', 'password', 'password_prompt',
             'progress_prompt', 'direction', 'source_dir', 'source_file', 'target_dir'],
    "ssh-int" : ['timeout_secs', 'hostname', 'username', 'password', 'password_prompt',
             'shell_prompt', 'sudo_password_prompt'],
    "local" : ['shell']
}

class tcolors:
    HEADER = '\033[95m'
    BOLDHEADER = '\033[1m\033[95m'
    OKBLUE = '\033[94m'
    LCYAN = '\033[96m'
    WHITE = '\033[97m'
    LGREEN = '\033[92m'
    BOLDLGREEN = '\033[1m\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[1m\033[91m'
    ENDC = '\033[0m'
    NORMAL = '\033[0m'
    BOLD = '\033[1m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

def print_json(output, heading = None):
    if heading:
        print heading
        print '=' * len(heading)
    print json.dumps(output, indent=4)

def dump_json(output, filename):
    try:
        with open(filename, 'w') as outfile:
            double_colored_print('Writing config file: ', filename + '\n', tcolors.BOLD, tcolors.BOLDLGREEN)
            json.dump(output, outfile, indent=4)
    except Exception as e:
        colored_print('Unable to write JSON config file: ', filename, tcolors.FAIL, tcolors.WARNING)
        colored_print('Reason: {0}'.format(str(e)), tcolors.FAIL)

def colored_print_without_newline(message, color):
    if platform.system() == 'Windows':
        color = ''
    sys.stdout.write(color + message + tcolors.ENDC)
    sys.stdout.flush()

def colored_print(message, color):
    if platform.system() == 'Windows':
        color = ''
    sys.stdout.write(color + message + tcolors.ENDC + '\n')

def double_colored_print(f_msg, s_msg, f_color, s_color):
    if platform.system() == 'Windows':
        f_color, s_color  = '', ''
    sys.stdout.write( f_color + f_msg + tcolors.ENDC + s_color + s_msg + tcolors.ENDC + '\n' )

def load_config(config_json_file):
    try:
        with open(config_json_file) as json_data_file:
            double_colored_print('\nReading config from: ', config_json_file, tcolors.BOLD, tcolors.BOLDLGREEN)
            colored_print('', tcolors.NORMAL)
            return json.load(json_data_file)
    except Exception as e:
        colored_print('Unable to load JSON config file: {0}'.format(config_json_file), tcolors.FAIL)
        colored_print('Reason: {0}'.format(str(e)), tcolors.FAIL)
        colored_print('Exiting...', tcolors.WHITE)

def convert_group_list_to_dict(variables):
    def get_as_dict_list(key, value):
        new_list = []
        if isinstance(value, list):
            for v in value:
                new_list.append({ key : v })
        else:
            new_list.append([{ key : value }])
        return new_list

    variable_names = []
    new_variables = {}
    for variable in variables:
        if variable.startswith(('#', '-')):
            continue
        if not isinstance(variables[variable], list):
            variables[variable] = [ variables[variable] ]
        if '.' in variable:
            groupname, key = variable.rsplit('.', 1)
            value = variables[variable]
            dict_list_value = get_as_dict_list(key, value)
            if groupname not in new_variables:
                new_variables[groupname] = dict_list_value
            else:
                if len(dict_list_value) != len(new_variables[groupname]):
                    double_colored_print('Unable to resolve the group.parameter: ', '{0}.{1}'.format(groupname,key), tcolors.FAIL, tcolors.WARNING)
                    colored_print('Reason: All parameters within a group should have the same number of items. Exiting...', tcolors.FAIL)
                    sys.exit(1)
                for index, val in enumerate(new_variables[groupname]):
                    val.update(dict_list_value[index])
            variable_names.append(key)
        else:
            new_variables[variable] = variables[variable]
            variable_names.append(variable)
    return variable_names, new_variables

def get_timeout_secs(timeout_value):
    try:
        return int(timeout_value)
    except:
        colored_print("WARNING: 'timeout_secs' should be a number: " \
                      "Using default value of {0} secs...".format(default_variables['timeout_secs']), tcolors.WARNING)
        return default_variables['timeout_secs']

def populate_defaults(variables):
    if 'run_id' in variables:
        run_id = variables['run_id']
    else:
        utc_datetime = datetime.datetime.utcnow()
        run_id = utc_datetime.strftime('RID_%Y%m%d_%H%M%S_UTC')
        variables['run_id'] = run_id
    for defaut_variable in default_variables:
        if defaut_variable not in variables:
            variables[defaut_variable] = default_variables[defaut_variable]
    return run_id, variables

def load_variables(config):
    config_constants = config['constants'] if 'constants' in config else {}
    config_variables = config['variables'] if 'variables' in config else {}
    variables = {}
    variables.update(config_constants)
    variables.update(config_variables)
    run_id, variables = populate_defaults(variables)

    variable_names, dict_variables = convert_group_list_to_dict(variables)
    variable_values = cartition_product(dict_variables)
        
    for variable in variable_values:
        for value in variable:
            if isinstance(variable[value], (str, unicode)):
                depth = 0
                while var_regex.search(variable[value]):
                    if depth == NO_RECURSIONS:
                        double_colored_print('Unable to resolve the parameter: ', variable[value], tcolors.FAIL, tcolors.WARNING)
                        colored_print('Reason: Potential cyclic dependency.  Exiting...', tcolors.FAIL)
                        sys.exit(1)
                    try:
                        variable[value] = format(variable[value], variable)
                    except KeyError as ke:
                        parameter_name = '{' + str(ke.args[0]) + '}'
                        double_colored_print('Unable to resolve the parameter: ', parameter_name, tcolors.FAIL, tcolors.WARNING)
                        colored_print('Exiting...', tcolors.FAIL)
                        sys.exit(1)
                    depth += 1
    return run_id, variable_names, variable_values

def cartition_product(variables):
    keylist = []
    valuelist = []
    for i in variables:
        keylist.append(i)
        if isinstance(variables[i], list):
            valuelist.append(variables[i])
        else:
            valuelist.append([ variables[i] ])
    var_list = []
    for elements in itertools.product(*valuelist):
        item = {}
        for index, element in enumerate(elements):
            if isinstance(element, dict):
                for key in element:
                    item[key] = element[key]
            else:
                if keylist[index] not in item: # Give preference to item in dict
                    item[keylist[index]] = element
        var_list.append(item)
    return var_list

def pretty_print(d):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(d)

# If you need to change the str formatting later
def format(format_str, variables):
    return format_str.format(**variables)

def trim_cr(input_str):
    if isinstance(input_str, str):
        return input_str.replace('\r\n', '\n').replace(' \r', '').replace('\r','') 
    else:
        return ''

def remote_scp(var, timeout):
    var['options'] = default_options
    var['source'] = os.path.join(var['source_dir'], var['source_file'])
    command = format(scp_format[var['direction'].lower()], var)

    if not default_live_run:
        double_colored_print('Command for live-run:\n', command, tcolors.BOLD, tcolors.WARNING)
        return
    double_colored_print('Transferring... ', command, tcolors.BOLD, tcolors.WARNING)
    try:
        connection = pexpect.spawn(command, timeout=timeout)
        connection.expect(var['password_prompt'])
        connection.sendline(var['password'])
        while True:
            ret = connection.expect([var['progress_prompt'], pexpect.EOF, pexpect.TIMEOUT], timeout=timeout)
            if ret == 0:
                colored_print_without_newline('\r{0}{1}'.format(connection.before, connection.after), tcolors.LCYAN)
                continue
            elif ret == 1:
                colored_print(connection.before, tcolors.LCYAN)
                double_colored_print('Transfer {0}: '.format(var['source']), 'Done\n', tcolors.BOLD, tcolors.LGREEN)
                return True
            elif ret == 2:
                colored_print('Timed out. Potentially very big file', tcolors.FAIL)
                return False
    except Exception as e:
        colored_print('Unable to scp: {0}'.format(str(e)), tcolors.FAIL)
        return False

def expect_spawn(var, timeout):
    var['options'] = default_options
    command = format(ssh_format, var)
    double_colored_print('Connecting... ', command, tcolors.BOLD, tcolors.WARNING)
    try:
        connection = pexpect.spawn(command, timeout=timeout)
        ret = connection.expect([var['password_prompt'], var['shell_prompt']])
        if ret == 0:
            connection.sendline(var['password'])
            connection.expect(var['shell_prompt'])
        colored_print('Connection established...\n', tcolors.WHITE)
        return connection
    except Exception as e:
        msg = "Timed out waiting for the prompt: '{0}'\n".format(var['shell_prompt'])
        double_colored_print('\nUnable to ssh : ', msg, tcolors.BOLD, tcolors.FAIL)
        double_colored_print('Exception : ', str(e) + '\n', tcolors.BOLD, tcolors.FAIL)
        return None

def run_ssh_command(connection, command, var):
    if not default_live_run:
        double_colored_print('Command for live-run: ', command, tcolors.BOLD, tcolors.WARNING)
        return True
    if not connection:
        double_colored_print('No connection. Unable to run the command: ', command, tcolors.FAIL, tcolors.WARNING)
        return True
    double_colored_print('Running command: ', command, tcolors.BOLD, tcolors.WARNING)
    connection.sendline(command)

    if 'sudo' in command:  #Doesn't harm to pass sudo password; as its only used if prompted
        ret = connection.expect([var['sudo_password_prompt'], pexpect.EOF, var['shell_prompt']])
        if ret == 0: # matched sudo_password_prompt
            connection.sendline(var['password'])
            ret = connection.expect([var['shell_prompt'], pexpect.EOF])
    else:
        ret = connection.expect([var['shell_prompt'], pexpect.EOF])
    response = trim_cr(connection.before) + trim_cr(connection.after)
    if response.startswith(command):
        response = response[len(command):].lstrip()
    colored_print(response, tcolors.NORMAL)
    if ret == 1: # pexpect.EOF
        return False
    return True

def clean_and_split_params(step):
    action_params = set()
    step_keys = list(step.keys()) # Creating a copy of keys as we need to delete commented keys
    for param in step_keys:
        if param.startswith(('#', '-')):
            del(step[param])
            continue
        if not (param == 'action' or param == 'commands'):
            if isinstance(step[param], (str,unicode)):
                matches = var_regex.finditer(step[param])
                for match in matches:
                    action_params.add(match.group(2))
            elif isinstance(step[param], list):
                for item in step[param]:
                    matches = var_regex.finditer(item)
                    for match in matches:
                        action_params.add(match.group(2))
    commands_params = set()
    if 'commands' in step:
        step['commands'] = [x for x in step['commands'] if not x.startswith(('#','-'))]
        for command in step['commands']:
            matches = var_regex.finditer(command)
            for match in matches:
                if match.group(2) not in action_params:
                    commands_params.add(match.group(2))
    combined_params = set()
    combined_params.update(action_params)
    combined_params.update(commands_params)
    return list(action_params), list(commands_params), list(combined_params)


def get_distinct_subset(params, variables):
    distinct_variables = []
    for variable in variables:
        selection = {}
        for param in params:
            selection[param] = variable[param]
        if selection not in distinct_variables:
            distinct_variables.append(selection)
    return distinct_variables

def get_filtered_variables(filter_dict, variables):
    filtered_variables = []
    for variable in variables:
        filtered = True
        for filt in filter_dict:
            if filt in variable and variable[filt] != filter_dict[filt]:
                filtered = False
                break
        if filtered:
            filtered_variables.append(variable)
    return filtered_variables

def validate_action_parameters(step, mandatory_params, variable_names):
    step_keys = list(step.keys())
    mandatory_keys = mandatory_params + ['action', 'commands']
    for key in step_keys:
        if key not in mandatory_keys:
            del step[key]
    for item in mandatory_params:
        if item not in step:
            if item in variable_names:
                step[item] = '{' + item + '}'
            else:
                double_colored_print('Skipping this action...\nReason: Missing configuration: ',
                                                        item, tcolors.FAIL, tcolors.WARNING)
                return False
        elif item == 'timeout_secs':
            step[item] = str(step[item])
    return True

def validate_all_variables(params, variable_names):
    for param in params:
        if param not in variable_names:
            double_colored_print('Skipping this action...\nReason: Unable to resolve: ',
                                                        param, tcolors.FAIL, tcolors.WARNING)
            return False
    return True

def execute_action(action, step, variable_names, variable_values):
    if not validate_action_parameters(step, action_mandatory_params[action], variable_names):
        return
    action_params, commands_params, combined_params = clean_and_split_params(step)
    if not validate_all_variables(combined_params, variable_names):
        return
    dist_combined_variables = get_distinct_subset(combined_params, variable_values)

    if step['action'] == 'local':
        for variable in dist_combined_variables:
            shell = format(step['shell'], variable)
            for command in step['commands']:
                command = format('{0} -c "{1}"'.format(shell, command), variable)

                if not default_live_run:
                    double_colored_print('Command for live-run: ', command, tcolors.BOLD, tcolors.WARNING)
                    continue

                double_colored_print('Running command: ', command, tcolors.BOLD, tcolors.WARNING)
                (command_output, exitstatus) = pexpect.run(command, withexitstatus=1)
                colored_print('{0}'.format(command_output), tcolors.NORMAL)
                if exitstatus == 0:
                    colored_print('Completed with exit status: {0}'.format(exitstatus), tcolors.BOLD)
                else:
                    colored_print('Completed with exit status: {0}'.format(exitstatus), tcolors.FAIL)
    elif step['action'] == 'scp':
        for variable in dist_combined_variables:
            direction = format(step['direction'], variable)
            var = {}
            for p in action_mandatory_params[step['action']]:
                if isinstance(step[p], list):
                    double_colored_print('Skipping this action...\nReason: Action parameter should be a string: ', p, tcolors.FAIL, tcolors.WARNING)
                    return
                var[p] = format(step[p], variable)
            if var['direction'].lower() not in scp_format.keys():
                colored_print('Skipping this action...\nReason: Unsupported direction for scp: {0}'.format(var['direction']), tcolors.FAIL)
                colored_print("Should be one of {0}".format(scp_format.keys()), tcolors.FAIL)
                return
            remote_scp(var, get_timeout_secs(var['timeout_secs']))
    elif step['action'] == 'ssh' or step['action'] == 'ssh-int':
        dist_action_variables = get_distinct_subset(action_params, variable_values)
        for index, act_variable in enumerate(dist_action_variables):
            var = {}
            for p in action_mandatory_params[step['action']]:
                if isinstance(step[p], list):
                    double_colored_print('Skipping this action...\nReason: Action parameter should be a string: ', p, tcolors.FAIL, tcolors.WARNING)
                    return
                var[p] = format(step[p], act_variable)

            connection = expect_spawn(var, get_timeout_secs(var['timeout_secs']))
            if connection:
                if step['action'] == 'ssh':
                    # Below filtering is needed to filter in only variables matching the loop action variable
                    dist_commands_variables = get_filtered_variables(act_variable, dist_combined_variables)
                    for cmd_variable in dist_commands_variables:
                        for command in step['commands']:
                            command = format(command, cmd_variable)
                            ret = run_ssh_command(connection, command, var)
                            if not ret:
                                connection.close()
                                connection = None
                        colored_print('', tcolors.NORMAL)
                else: # step['action'] == 'ssh-int'
                    break_after_output = False
                    commands = []
                    command = ''
                    while True:
                        response = trim_cr(connection.before) + trim_cr(connection.after)
                        if response.startswith(command):
                            response = response[len(command):].lstrip()
                        colored_print_without_newline(response, tcolors.NORMAL)
                        if break_after_output:
                            colored_print('\nExiting interative ssh ...\n', tcolors.BOLD)
                            break

                        prompt = "(Type 'exit' to exit interactive ssh) > "
                        colored_print_without_newline(prompt, tcolors.NORMAL)
                        command = raw_input()
                        if '\x1b' in command:
                            colored_print('Ignoring command ...', tcolors.BOLD)
                            command = ''
                        try:
                            command = command.strip()
                            commands.append(command)
                            connection.sendline(command)
                            if 'sudo' in command:  #Doesn't harm to pass sudo password; as its only used if prompted
                                ret = connection.expect([var['sudo_password_prompt'], pexpect.EOF, var['shell_prompt']])
                                if ret == 0: # matched sudo_password_prompt
                                    connection.sendline(var['password'])
                                    ret = connection.expect([var['shell_prompt'], pexpect.EOF])
                            else:
                                ret = connection.expect([var['shell_prompt'], pexpect.EOF])
                            if ret == 1: # pexpect.EOF
                                break_after_output = True
                        except Exception as e:
                            print 'Something happened. Exception : {0}'.format(str(e))
                            return
                    if index == 0 and len(dist_action_variables) > 1 and commands:
                        res = raw_input('Run all these commands on rest of the hosts? [y]/n : ')
                        colored_print('', tcolors.NORMAL)
                        if not res or not (res.upper() == 'N' or res.upper() == 'NO'):
                            step['action'] = 'ssh'
                            step['commands'] = commands
                            config_out = { "main" : [ "interative_ssh" ], "interative_ssh" : step }
                            dump_json(config_out, 'interactive.json')
                if connection:
                    connection.close()

def execute(config, live_run):
    if not config or 'main' not in config:
        colored_print('Nothing configured to execute. Could not find "main" in the config.', tcolors.FAIL)
        sys.exit(1)

    global default_live_run
    if not default_live_run:
        default_live_run = live_run

    run_id, variable_names, variable_values = load_variables(config)

    for index, step_name in enumerate(config['main']):
        if not step_name.strip():
            colored_print("\n{0}. Skipping action... '{1}' : Blank action name not supported".format(index+1, step_name), tcolors.HEADER)
            continue
        if step_name.startswith(('#', '-')):
            #colored_print("\n{0}. Skipping action... '{1}' : Commented by prefixing with '-' or '#'".format(index+1, step_name), tcolors.HEADER)
            continue
        if step_name not in config:
            colored_print("\n{0}. Skipping action... '{1}' : Not defined in the config file".format(index+1, step_name), tcolors.HEADER)
            continue
        step = config[step_name]
        if 'action' not in step:
            colored_print("\n{0}. Skipping action... '{1}' : Missing action type".format(index+1, step_name), tcolors.HEADER)
            continue
        action = step['action']
        if action not in action_mandatory_params.keys():
            colored_print("\n{0}. Skipping action... '{1}' : Unsupported action type '{2}'".format(index+1, step_name, action), tcolors.HEADER)
            continue

        message1 = '\n{0}. Running action... '.format(index + 1)
        message2 = '{0} ({1})'.format(step_name, action)
        double_colored_print(message1, message2, tcolors.HEADER, tcolors.BOLDHEADER)
        colored_print('{0}\n'.format('-'*(len(message1 + message2)-1)), tcolors.HEADER)

        execute_action(action, step, variable_names, variable_values)
    double_colored_print('\nSuccessfully completed with RUN ID : ', run_id, tcolors.BOLD, tcolors.BOLDLGREEN)
    colored_print('', tcolors.BOLD)

def main():
    live_run_desc = 'The program is capable of running any UNIX command on any host with credentials. ' \
                    'To AVOID any unwanted consequences of running certain non-recoverable commands like "rm -fr", ' \
                    'the program will EXECUTE the commands only if this flag is enabled. If False, the program ' \
                    'will ONLY output all the resolved commands.'
    description = 'Version %s. \nScript to execute configured commands in local and remote hosts. ' \
                  'The program is capable of running any UNIX command on any host with credentials.' % version
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-f', '--conf-file', dest='conf_file', help='Name of the config file in JSON format', required=True)
    parser.add_argument('--live-run', dest='live_run', help=live_run_desc, action='store_true')
    args = parser.parse_args()

    '''
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger.info("This is info")
    logger.warning("This is warning")
    logger.error("This is error")
    logger.debug("This is debug")
    logger.critical("This is critical")
    '''

    config = load_config(args.conf_file)
    execute(config, args.live_run)

if __name__ == "__main__":
	main()


