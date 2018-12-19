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
import datetime
import pprint
import pexpect
import argparse
import itertools

# Change the default values for the below parameters
# ==================================================
version = '1.0'
default_timeout_secs = 60
default_options = '-o CheckHostIP=no -o LogLevel=quiet -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
# ==================================================

_DEBUG_ = False
var_regex = re.compile('({[ \t]*(\w+)[ \t]*})')
NO_RECURSIONS = 10

action_mandatory_params = {
    "ssh" : ['hostname', 'username', 'password', 'password_prompt',
             'shell_prompt', 'sudo_password_prompt:{password_prompt}'],
    "scp" : ['hostname', 'username', 'password', 'password_prompt',
             'progress_prompt', 'source_dir', 'source_files', 'target_dir'],
    "local" : []
}

class tcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    LCYAN = '\033[96m'
    WHITE = '\033[97m'
    LGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    NORMAL = '\033[0m'
    BOLD = '\033[1m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

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
            double_colored_print('\nReading config from: ', config_json_file, tcolors.BOLD, tcolors.HEADER)
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
                for index, val in enumerate(new_variables[groupname]):
                    val.update(dict_list_value[index])
            variable_names.append(key)
        else:
            new_variables[variable] = variables[variable]
            variable_names.append(variable)
    return variable_names, new_variables

def get_timeout_secs(variables_dict):
    timeout_secs = default_timeout_secs
    if 'timeout_secs' in variables_dict:
        try:
            timeout_secs =  int(variables_dict['timeout_secs'])
        except:
            colored_print("WARNING: 'timeout_secs' should be a number: Using default value of {0} secs...".format(default_timeout_secs), tcolors.WARNING)
    return timeout_secs

def load_variables(config):
    config_constants = config['constants'] if 'constants' in config else {}
    config_variables = config['variables'] if 'variables' in config else {}
    variables = {}
    variables.update(config_constants)
    variables.update(config_variables)

    if 'run_id' in variables:
        run_id = variables['run_id']
    else:
        utc_datetime = datetime.datetime.utcnow()
        run_id = utc_datetime.strftime('RID_%Y%m%d_%H%M%S_UTC')
        variables['run_id'] = run_id
    variables['timeout_secs'] = get_timeout_secs(variables)

    variable_names, dict_variables = convert_group_list_to_dict(variables)
    variable_values = cartition_product(dict_variables)
    if _DEBUG_:
        print '-------- load_variables : Before ({0})-------'.format(len(variable_values))
        for i in variable_values:
            print i
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
    if _DEBUG_:
        print '-------- load_variables : After ({0})--------'.format(len(variable_values))
        for i in variable_values:
            print i
        print '--------- load_variables : End --------'
        print variable_names
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
    return input_str.replace('\r\n', '\n').replace(' \r', '').replace('\r','') 

def remote_scp(hostname, username, password, password_prompt, progress_prompt, source, target_dir, direction, timeout):
    if direction.lower() == 'get':
        format_str = 'scp -r {0} {1}:{2} {3}'
    elif direction.lower() == 'send':
        if '*' in source:
            format_str = "bash -c 'scp -r {0} {2} {1}:{3}'"
        else:
            format_str = 'scp -r {0} {2} {1}:{3}'
    else:
        colored_print("Direction '{0}' not supported. Exiting...", tcolors.FAIL)
        sys.exit(1)
    username_at_host = '{0}@{1}'.format(username, hostname)
    command = format_str.format(default_options, username_at_host, source, target_dir)
    double_colored_print('Transferring... ', command, tcolors.BOLD, tcolors.WARNING)
    try:
        connection = pexpect.spawn(command, timeout=timeout)
        connection.expect(password_prompt)
        connection.sendline(password)
        while True:
            ret = connection.expect([progress_prompt, pexpect.EOF, pexpect.TIMEOUT], timeout=timeout)
            if ret == 0:
                colored_print_without_newline('\r{0}{1}'.format(connection.before, connection.after), tcolors.LCYAN)
                continue
            elif ret == 1:
                colored_print(connection.before, tcolors.LCYAN)
                double_colored_print('Transfer {0}: '.format(source), 'Done\n', tcolors.BOLD, tcolors.LGREEN)
                return True
            elif ret == 2:
                colored_print('Timed out. Potentially very big file', tcolors.FAIL)
                return False
    except Exception as e:
        colored_print('Unable to scp: {0}'.format(str(e)), tcolors.FAIL)
        return False

def expect_spawn(command, shell_prompt, timeout, password_prompt = None, password = None):
    double_colored_print('Connecting... ', command, tcolors.BOLD, tcolors.WARNING)
    try:
        connection = pexpect.spawn(command, timeout=timeout)
        if password_prompt:
            connection.expect(password_prompt)
            connection.sendline(password)
        connection.expect(shell_prompt)
        colored_print('Connection established...\n', tcolors.WHITE)
        return connection
    except Exception as e:
        colored_print('\nUnable to ssh : {0}'.format(str(e)), tcolors.FAIL)
        return None

def run_ssh_command(connection, command, shell_prompt, password_prompt = None, password = None):
    double_colored_print('Running command: ', command, tcolors.BOLD, tcolors.WARNING)

    connection.sendline(command)
    if password_prompt:
        ret = connection.expect([password_prompt, shell_prompt, pexpect.EOF])
        if ret == 0: # matched password_prompt
            connection.sendline(password)
            connection.expect([shell_prompt, pexpect.EOF])
    else:
        if shell_prompt:
            connection.expect([shell_prompt, pexpect.EOF])
    before = trim_cr(connection.before)
    after = trim_cr(connection.after)
    colored_print('{0}{1}'.format(before, after), tcolors.LCYAN)

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
    if step['action'] == 'scp' or step['action'] == 'ssh':
        action_params.update([ 'timeout_secs' ])
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
    return action_params, commands_params, combined_params


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
    for item in mandatory_params:
        if ':' in item:
            item, substitute = item.split(':', 1)
        else:
            substitute = None
        if item not in step:
            if item in variable_names:
                step[item] = '{' + item + '}'
            elif substitute in variable_names:
                step[item] = '{' + substitute + '}'
            else:
                double_colored_print('Skipping this action...\nReason: Missing configuration: ',
                                                        item, tcolors.FAIL, tcolors.WARNING)
                return False
    return True

def validate_all_variables(params, variable_names):
    for param in params:
        if param not in variable_names:
            double_colored_print('Skipping this action...\nReason: Missing configuration: ',
                                                        param, tcolors.FAIL, tcolors.WARNING)
            return False
    return True

def execute_action(action, step, variable_names, variable_values):
    if not validate_action_parameters(step, action_mandatory_params[action], variable_names):
        return
    action_params, commands_params, combined_params = clean_and_split_params(step)
    if not validate_all_variables(combined_params, variable_names):
        return

    if _DEBUG_:
        print '------- Params'
        print 'Action Params : ', action_params
        print 'Command Params : ', commands_params
        print 'Combined Params : ', combined_params
        print '------- variable_names'
        print variable_names

    if step['action'] == 'local':
        dist_commands_variables = get_distinct_subset(commands_params, variable_values)
        for variable in dist_commands_variables:
            if _DEBUG_:
                print '>>>>>>>>>>> command_variable : ', variable
            for command in step['commands']:
                command = format(command, variable)
                double_colored_print('Running command: ', command, tcolors.BOLD, tcolors.WARNING)
                (command_output, exitstatus) = pexpect.run(command, withexitstatus=1)
                colored_print('{0}'.format(command_output), tcolors.LCYAN)
                if exitstatus == 0:
                    colored_print('Completed with exit status: {0}'.format(exitstatus), tcolors.BOLD)
                else:
                    colored_print('Completed with exit status: {0}'.format(exitstatus), tcolors.FAIL)
    elif step['action'] == 'scp':
        dist_combined_variables = get_distinct_subset(combined_params, variable_values)
        for variable in dist_combined_variables:
            if _DEBUG_:
                print '>>>>>>>>>>> combined_variable : ', variable
            direction = 'get'
            if 'direction' in step:
                direction = format(step['direction'], variable)
                if not (direction == 'get' or direction == 'send'):
                    colored_print('Skipping this action...\nReason: Unsupported direction for scp: {0}'.format(direction), tcolors.FAIL)
                    colored_print("Should be 'get' or 'send'", tcolors.FAIL)
                    return
            hostname = format(step['hostname'], variable)
            username = format(step['username'], variable)
            password = format(step['password'], variable)
            if 'timeout_secs' in step:
                timeout = get_timeout_secs(step)
            else:
                timeout = variable['timeout_secs']
            password_prompt = format(step['password_prompt'], variable)
            progress_prompt = format(step['progress_prompt'], variable)
            source_dir = format(step['source_dir'], variable)
            target_dir = format(step['target_dir'], variable)
            if not isinstance(step['source_files'], list):
                step['source_files'] = [ step['source_files'] ]
            for source_file in step['source_files']:
                source_file = format(source_file, variable)
                source = os.path.join(source_dir, source_file)
                remote_scp(hostname, username, password, password_prompt, progress_prompt, source, target_dir, direction, timeout)
    elif step['action'] == 'ssh':  #TODO_LATER: Implement local bash connection
        dist_action_variables = get_distinct_subset(action_params, variable_values)
        dist_combined_variables = get_distinct_subset(combined_params, variable_values)
        for act_variable in dist_action_variables:
            if _DEBUG_:
                print '>>>>>>>>>>> act_variable : ', act_variable
            hostname = format(step['hostname'], act_variable)
            username = format(step['username'], act_variable)
            password = format(step['password'], act_variable)
            if 'timeout_secs' in step:
                timeout = get_timeout_secs(step)
            else:
                timeout = act_variable['timeout_secs']
            password_prompt = format(step['password_prompt'], act_variable)
            sudo_password_prompt = format(step['sudo_password_prompt'], act_variable)
            shell_prompt = format(step['shell_prompt'], act_variable)
            command = 'ssh {0} {1}@{2}'.format(default_options, username, hostname)
            connection = expect_spawn(command, shell_prompt, timeout, password_prompt, password)
            if not connection:
                continue
            dist_commands_variables = get_filtered_variables(act_variable, dist_combined_variables)
            for cmd_variable in dist_commands_variables:
                if _DEBUG_:
                    print '>>>>>>>>>>> cmd_variable : ', cmd_variable
                for command in step['commands']:
                    combined_variables = {}
                    combined_variables.update(act_variable)
                    combined_variables.update(cmd_variable)
                    command = format(command, combined_variables)
                    if 'sudo' in command: # Doesn't harm to pass sudo password; as its only used if prompted
                        run_ssh_command(connection, command, shell_prompt, sudo_password_prompt, password)
                    else:
                        run_ssh_command(connection, command, shell_prompt)
            run_ssh_command(connection, 'exit', '.*')
    else:
        colored_print('Skipping this action...\nReason: Unsupported action: {0}'.format(step['action']), tcolors.FAIL)

def execute(config):
    if not config or 'main' not in config:
        colored_print('Nothing configured to execute. Could not find "main" in the config.', tcolors.FAIL)
        sys.exit(1)

    run_id, variable_names, variable_values = load_variables(config)

    for index, step_name in enumerate(config['main']):
        if step_name.startswith(('#', '-')):
            colored_print("\n{0}. Skipping action... {1} (starting with '-' or '#')".format(index + 1, step_name), tcolors.HEADER)
            continue
        message = '\n{0}. Running action... {1}'.format(index + 1, step_name)
        colored_print(message, tcolors.HEADER)
        colored_print('{0}\n'.format('-'*(len(message)-1)), tcolors.HEADER)
        if step_name not in config:
            colored_print('Step "{0}" is not defined in the config file. Skipping the action...'.format(step_name), tcolors.FAIL)
            continue
        step = config[step_name]
        if 'action' not in step:
            colored_print('Step "{0}" does not have an action type. Skipping the action...'.format(step_name), tcolors.FAIL)
            continue
        action = step['action']
        if action not in action_mandatory_params.keys():
            colored_print('Step "{0}": Unsupported action type: {1}. Skipping the action...'.format(step_name, action), tcolors.FAIL)
            continue
        execute_action(action, step, variable_names, variable_values)
    colored_print('\nSuccessfully completed with RUN ID : {0}'.format(run_id), tcolors.BOLD)
    colored_print('', tcolors.BOLD)

def main():
    description = 'Version %s. \nScript to execute configured commands in local and remote hosts.' % version
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-f', '--conf-file', dest='conf_file', help='Name of the config file in JSON format', required=True)
    parser.add_argument('--debug', help='*NOT IMPLEMENTED YET* With debug flag, the program will ONLY echo/output all the resolved commands after connecting to the remote/local host; but will NOT attempt to run these commands. This is useful while configuring a new requirement to avoid unwanted impact of running certain non-recoverable commands like "rm -fr"', action='store_true')
    args = parser.parse_args()

    '''
    if args.debug:
        _DEBUG_ = True
    else:
        __import__(pexpect)
    '''

    config = load_config(args.conf_file)
    execute(config)

if __name__ == "__main__":
	main()


