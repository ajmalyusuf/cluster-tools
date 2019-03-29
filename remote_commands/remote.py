#!/usr/bin/env python

########################################################################################
# For any questions or suggestions please contact : Ajmal Yusuf <ayusuf@hortonworks.com>
########################################################################################

import sys
import os
import re
import json
import platform
import logging
import datetime
import pexpect
import getpass
import argparse
import itertools

'''
sshuser@hn0-lazhuh:~$
[ajmal@dfs4-dev ~]$
[root@dfs1-dev ~]#
new_patt =  '\[?(.+)@([^\]\:\$\#\~\s]+)[\]\:\$\#\~\s]+\s+'
'''
# Change the default values for the below parameters
# ==================================================
version = '1.1'
default_live_run = False
default_variables = {
    'shell' : 'bash',
    'timeout_secs' : 60,
    'shell_prompt' : '[\$\#]? $',
    'password_prompt' : 'password: ',
    'sudo_password_prompt' : 'password for {username}:',
    'progress_prompt' : 'ETA',
    'options' : '-o CheckHostIP=no -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' # -o LogLevel=quiet'
}

scp_format = {
    'get' : "{shell} -c 'scp -r {options} {username}@{hostname}:{source} {target_dir}'",
    'send' : "{shell} -c 'scp -r {options} {source} {username}@{hostname}:{target_dir}'"
}
ssh_format = 'ssh {options} {username}@{hostname}'
# ==================================================

space_regex = re.compile('\s')
var_regex = re.compile('({[ \t]*(\w+)[ \t]*})')
NO_RECURSIONS = 10

action_mandatory_params = {
    "ssh" : ['timeout_secs', 'hostname', 'username', 'password', 'password_prompt',
             'shell_prompt', 'sudo_password_prompt', 'options'],
    "scp" : ['shell', 'timeout_secs', 'hostname', 'username', 'password', 'password_prompt',
             'progress_prompt', 'direction', 'source_dir', 'source_file', 'target_dir', 'options'],
    "ssh-int" : ['timeout_secs', 'hostname', 'username', 'password', 'password_prompt',
             'shell_prompt', 'sudo_password_prompt', 'options'],
    "local" : ['shell']
}

params_error_messages = {
    "{username}" : "'username' not provided. You may pass it as -u/--username parameter OR " \
                   "\nconfigure 'username' in the 'default_properties.json' file.",
    "{password}" : "'password' not provided. You may pass it as -p/--password parameter OR " \
                   "\nconfigure 'password' in the 'default_properties.json' file."
}

parameter_groups = {
    'hostname' : 'remote_credentials',
    'username' : 'remote_credentials',
    'password' : 'remote_credentials'
}

class tcolors:
    HEADER = '\033[95m'
    BOLDHEADER = '\033[1m\033[95m'
    OKBLUE = '\033[94m'
    LCYAN = '\033[96m'
    WHITE = '\033[97m'
    LGREEN = '\033[92m'
    BOLDLGREEN = '\033[1m\033[92m'
    WARNING = '\033[1m\033[93m'
    FAIL = '\033[1m\033[91m'
    ENDC = '\033[0m'
    NORMAL = '\033[0m'
    BOLD = '\033[1m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

def print_json(output, heading = None):
    if heading:
        print heading
        print '-' * len(heading)
    print json.dumps(output, indent=4)

def dump_json(output, filename):
    try:
        with open(filename, 'w') as outfile:
            double_colored_print('Writing config file: ', filename, tcolors.BOLD, tcolors.BOLDLGREEN)
            json.dump(output, outfile, indent=4)
    except Exception as e:
        double_colored_print('Unable to write JSON config file: ', filename, tcolors.FAIL, tcolors.WARNING)
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
            double_colored_print('\nReading config from: ', config_json_file + '\n', tcolors.BOLD, tcolors.BOLDLGREEN)
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
        double_colored_print("WARNING: 'timeout_secs' should be a number. Using default ", 
                             '{0} secs...'.format(default_variables['timeout_secs']), tcolors.FAIL, tcolors.LGREEN)
        return default_variables['timeout_secs']

def populate_defaults(config):
    def present(variable):
        for key in clean_variables:
            if key == variable or key.endswith('.' + variable):
                return True
        return False
    def get_value(key, value):
        if isinstance(value, (str, unicode)):
            if value.startswith(':p?') or value.startswith(':pp?'):
                if(key == 'username' or key.endswith('.username')) and 'username' in default_variables:
                    value = default_variables['username']
                elif (key == 'password' or key.endswith('.password')) and 'password' in default_variables:
                    value = default_variables['password']

            if value.startswith(':p?'):
                value = raw_input('Enter the value for {0}{1}{2} [exit]: '.format(tcolors.BOLD, key, tcolors.NORMAL))
                if not value:
                    sys.exit(0)
            elif value.startswith(':pp?'):
                value = getpass.getpass('Enter the value for {0}{1}{2} [exit]: '.format(tcolors.WARNING, key, tcolors.NORMAL))
                if not value:
                    sys.exit(0)
        return value 
    def insert_into_variables_if_not_present(key, value):
        org_key = key
        value = get_value(key, value)
        if '.' in key:
            groupname, key = key.rsplit('.', 1)
        if not present(key):
            if isinstance(value, list) and len(value) > 1:
                key = parameter_groups[key] + '.' + key if key in parameter_groups else org_key
            clean_variables[key] = value
        else:
            double_colored_print('Ignoring duplicate variable: ',
                    '"{0}" : "{1}"'.format(org_key, value), tcolors.FAIL, tcolors.BOLD)

    clean_variables = {}
    if 'variables' in config:
        ordered_prompt_variables = {}
        non_ordered_prompt_variables = []
        for key in config['variables']:
            value = config['variables'][key]
            if key.startswith(('#', '-')) or not value:
                continue
            if space_regex.search(key):
                double_colored_print('Ignoring invalid variable: ', '"{0}"'.format(key), tcolors.FAIL, tcolors.BOLD)
                continue
            if '.' in key:
                order, new_key = key.split('.',1)
                if order.isdigit():
                    ordered_prompt_variables[order] = (new_key, value)
                    continue
            non_ordered_prompt_variables.append((key, value))
        for slno in sorted(ordered_prompt_variables, key=int):
            (key, value) = ordered_prompt_variables[slno]
            insert_into_variables_if_not_present(key, value)
        for key, value in non_ordered_prompt_variables:
            insert_into_variables_if_not_present(key, value)

    for key in default_variables:
        if not present(key):
            clean_variables[key] = default_variables[key]

    if 'run_id' not in clean_variables:
        clean_variables['run_id'] = generate_run_id()
    return clean_variables['run_id'], clean_variables

def generate_run_id():
    utc_datetime = datetime.datetime.utcnow()
    return utc_datetime.strftime('RID_%Y%m%d_%H%M%S_UTC')

def load_variables(config):
    run_id, variables = populate_defaults(config)
    variable_names, dict_variables = convert_group_list_to_dict(variables)
    variable_values = cartesian_product(dict_variables)

    for variable in variable_values:
        for value in variable:
            if isinstance(variable[value], (str, unicode)):
                depth = 0
                while var_regex.search(variable[value]):
                    if depth == NO_RECURSIONS:
                        double_colored_print('Unable to resolve the parameter: ', variable[value], tcolors.FAIL, tcolors.WARNING)
                        colored_print('Reason: Potential cyclic dependency.  Exiting...\n', tcolors.FAIL)
                        sys.exit(1)
                    try:
                        variable[value] = format(variable[value], variable)
                    except KeyError as ke:
                        parameter_name = '{' + str(ke.args[0]) + '}'
                        double_colored_print('Unable to resolve the variable: ', value + ' = "' + variable[value] + '"', tcolors.FAIL, tcolors.WARNING)
                        double_colored_print('Undefined variable: ', parameter_name, tcolors.FAIL, tcolors.WARNING)
                        if parameter_name in params_error_messages:
                            colored_print(params_error_messages[parameter_name], tcolors.NORMAL)
                        colored_print('Exiting...\n', tcolors.FAIL)
                        sys.exit(1)
                    depth += 1
    return run_id, variable_names, variable_values

def cartesian_product(variables):
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

# If you need to change the str formatting later
def format(format_str, variables):
    return format_str.format(**variables)

def trim_cr(input_str):
    if isinstance(input_str, str):
        return input_str.replace('\r\n', '\n').replace(' \r', '').replace('\r','') 
    else:
        return ''

def remote_scp(var, timeout):
    var['source'] = os.path.join(var['source_dir'], var['source_file'])
    command = format(scp_format[var['direction'].lower()], var)
    if not default_live_run:
        double_colored_print('Command: ', command, tcolors.BOLD, tcolors.WARNING)
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
                double_colored_print('Transfer {0}: '.format(var['source']), 'Done', tcolors.BOLD, tcolors.LGREEN)
                return True
            elif ret == 2:
                colored_print('Timed out. Potentially very big file', tcolors.FAIL)
                return False
    except Exception as e:
        colored_print('Unable to scp: {0}'.format(str(e)), tcolors.FAIL)
        return False

def expect_spawn(var, timeout):
    command = format(ssh_format, var)
    double_colored_print('Connecting... ', command, tcolors.BOLD, tcolors.WARNING)
    try:
        connection = pexpect.spawn(command, timeout=timeout)
        connection.setecho(False)
        ret = connection.expect([var['password_prompt'], var['shell_prompt']])
        if ret == 0:
            colored_print_without_newline('Sending password ... ', tcolors.BOLD)
            connection.sendline(var['password'])
            connection.expect(var['shell_prompt'])
        colored_print('Connection established', tcolors.LGREEN)
        response = trim_cr(connection.before) + trim_cr(connection.after)
        #if default_live_run:
        #    colored_print_without_newline(response, tcolors.NORMAL)
        return connection, response
    except Exception as e:
        msg = "Timed out waiting for the prompt: '{0}'\n".format(var['shell_prompt'])
        double_colored_print('\nUnable to ssh : ', msg, tcolors.BOLD, tcolors.FAIL)
        double_colored_print('Exception : ', str(e) + '\n', tcolors.BOLD, tcolors.FAIL)
        return None, None

def run_ssh_command(connection, command, var):
    if not default_live_run:
        double_colored_print('Command: ', command, tcolors.BOLD, tcolors.WARNING)
        return True
    if not connection:
        double_colored_print('No connection. Unable to run the command: ', command, tcolors.FAIL, tcolors.WARNING)
        return True

    if isinstance(command, list):
        command, wait = command
        extra_info = ' (may take upto {0} seconds)'.format(var['timeout_secs'])
    else:
        extra_info = ''
    double_colored_print(command, extra_info, tcolors.WARNING, tcolors.BOLD)
    connection.sendline(command)

    ret = connection.expect([var['shell_prompt'], pexpect.EOF, pexpect.TIMEOUT, var['sudo_password_prompt']])
    if ret == 3:
        colored_print_without_newline('Sending password ... ', tcolors.BOLD)
        connection.sendline(var['password'])
        colored_print('Done', tcolors.LGREEN)
        ret = connection.expect([var['shell_prompt'], pexpect.EOF, pexpect.TIMEOUT])

    response = trim_cr(connection.before) + trim_cr(connection.after)
    #if response.startswith(command):
    #    response = response[len(command):].lstrip()
    colored_print_without_newline(response, tcolors.NORMAL)
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
            parameter_name = '{' + item + '}'
            if item in variable_names:
                step[item] = parameter_name
            else:
                double_colored_print('Skipping this action...\nReason: Missing parameter: ',
                                                        item, tcolors.FAIL, tcolors.WARNING)
                if parameter_name in params_error_messages:
                    colored_print(params_error_messages[parameter_name], tcolors.NORMAL)
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

def resolve_all_variables(step, variable):
    new_step = {}
    for p in action_mandatory_params[step['action']]:
        if isinstance(step[p], list):
            double_colored_print('Skipping this action...\nReason: Action parameter should be a string: ',
                                    p, tcolors.FAIL, tcolors.WARNING)
            return None
        new_step[p] = format(step[p], variable)
    return new_step

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
                    double_colored_print('Command: ', command, tcolors.BOLD, tcolors.WARNING)
                    continue

                double_colored_print('Running command: ', command, tcolors.BOLD, tcolors.WARNING)
                (command_output, exitstatus) = pexpect.run(command, withexitstatus=1)
                if command_output:
                    colored_print('{0}'.format(command_output.rstrip()), tcolors.NORMAL)
                if exitstatus == 0:
                    colored_print('Exit status: {0}'.format(exitstatus), tcolors.LGREEN)
                else:
                    colored_print('Exit status: {0}'.format(exitstatus), tcolors.FAIL)
    elif step['action'] == 'scp':
        for variable in dist_combined_variables:
            var = resolve_all_variables(step, variable)
            if not var:
                continue
            if var['direction'].lower() not in scp_format.keys():
                double_colored_print('Skipping this action...\nReason: Unsupported direction for scp: ',
                                        var['direction'], tcolors.FAIL, tcolors.WARNING)
                double_colored_print('Should be one of ', str(scp_format.keys()), tcolors.FAIL, tcolors.WARNING)
                return
            remote_scp(var, get_timeout_secs(var['timeout_secs']))
    elif step['action'] == 'ssh' or step['action'] == 'ssh-int':
        dist_action_variables = get_distinct_subset(action_params, variable_values)
        for index, act_variable in enumerate(dist_action_variables):
            var = resolve_all_variables(step, act_variable)
            if not var:
                continue
            connection, response = expect_spawn(var, get_timeout_secs(var['timeout_secs']))
            if connection:
                if step['action'] == 'ssh':
                    if default_live_run:
                        if '\n' in response:
                            split_res = response.rsplit('\n', 1)[0]
                            if split_res:
                                response = '\n' + response.rsplit('\n', 1)[-1]
                        colored_print_without_newline(response, tcolors.NORMAL)
                    else:
                        colored_print('', tcolors.NORMAL)
                    # Below filtering is needed to filter in only variables matching the loop action variable
                    dist_commands_variables = get_filtered_variables(act_variable, dist_combined_variables)
                    for cmd_variable in dist_commands_variables:
                        for command in step['commands']:
                            if not isinstance(command, list):
                                command = format(command, cmd_variable)
                            ret = run_ssh_command(connection, command, var)
                            if not ret:
                                connection.close()
                                connection = None
                        colored_print('', tcolors.NORMAL)
                    if default_live_run:
                        colored_print('', tcolors.NORMAL)
                else: # step['action'] == 'ssh-int'
                    commands = []
                    timeout = 10
                    colored_print_without_newline(response, tcolors.NORMAL)
                    extra_prompt = "('exit' to end interactive ssh) > "
                    colored_print_without_newline(extra_prompt, tcolors.BOLD)
                    while True:
                        command = raw_input()
                        if '\x1b' in command:
                            colored_print('Ignoring command ...', tcolors.BOLD)
                            command = ''
                        command = command.strip()
                        connection.sendline(command)

                        ret = connection.expect([var['shell_prompt'], pexpect.EOF, pexpect.TIMEOUT, var['sudo_password_prompt']], timeout=timeout)
                        if ret == 3:
                            colored_print_without_newline('Sending password ... ', tcolors.BOLD)
                            connection.sendline(var['password'])
                            colored_print('Done', tcolors.LGREEN)
                            ret = connection.expect([var['shell_prompt'], pexpect.EOF, pexpect.TIMEOUT], timeout=timeout)

                        response = trim_cr(connection.before) + trim_cr(connection.after)
                        #if response.startswith(command):
                        #    response = response[len(command):].lstrip()
                        colored_print_without_newline(response, tcolors.NORMAL)
                        if ret == 1:
                            commands.append(command)
                            colored_print('Exiting interative ssh ...\n', tcolors.BOLD)
                            break
                        elif ret == 2:
                            command = [command, 'wait']
                        else:
                            res = response.rsplit('\n',1)
                            if res:
                                prompt = res[-1]
                                if '{0}@'.format(var['username']) in prompt:
                                    colored_print_without_newline(extra_prompt, tcolors.BOLD)
                        commands.append(command)
                    if len(dist_action_variables) > 1 and commands:
                        res = raw_input('Run all these commands on rest of the hosts? [y]/n : ')
                        colored_print('', tcolors.NORMAL)
                        if not res or not (res.upper() == 'N' or res.upper() == 'NO'):
                            step['action'] = 'ssh'
                            step['commands'] = commands
                            config_out = { "main" : [ "interative_ssh" ], "interative_ssh" : step }
                            dump_json(config_out, 'interactive.json')
                if connection:
                    connection.close()

def override_defaults_from_defaults_ini_file(live_run):
    global default_live_run
    global default_variables
    try:
        default_prop_file = 'default_properties.json'
        with open(default_prop_file) as dpf:
            def_prop = json.load(dpf)
            for item in default_variables:
                if item in def_prop:
                    default_variables[item] = def_prop[item]
            if 'username' in def_prop:
                default_variables['username'] = def_prop['username']
            if 'password' in def_prop:
                default_variables['password'] = def_prop['password']
            if live_run:
                default_live_run = True
            elif 'default_live_run' in def_prop:
                dlr = def_prop['default_live_run']
                if (isinstance(dlr, bool) and dlr == True) or (isinstance(dlr, (str, unicode)) and dlr.upper() == 'TRUE'):
                    default_live_run = True
    except Exception as e:
        double_colored_print('Unable to read properties file: ', default_prop_file, tcolors.FAIL, tcolors.WARNING)
        colored_print('Reason: {0}'.format(str(e)), tcolors.FAIL)
        colored_print('Proceeding with hard coded defaults.', tcolors.NORMAL)

def replace_config_variables(config, new_variables):
    if not isinstance(new_variables, dict):
        return
    variables = {}
    if 'variables' in config:
        variables = config['variables']

    for key in new_variables:
        value = new_variables[key]
        if not key.startswith(('#', '-')) and new_variables[key]:
            org_key = key
            if '.' in key:
                groupname, key = key.rsplit('.', 1)
            variables = {k: v for k, v in variables.iteritems() if not (k == key or k.endswith('.' + key))}
            variables[org_key] = new_variables[org_key]
    config['variables'] = variables

def execute(config, live_run, override_variables = None):
    if not config or 'main' not in config:
        colored_print('Nothing configured to execute. Could not find "main" in the config.', tcolors.FAIL)
        sys.exit(1)
    override_defaults_from_defaults_ini_file(live_run)
    replace_config_variables(config, override_variables)

    run_id, variable_names, variable_values = load_variables(config)
    for index, step_name in enumerate(config['main']):
        if not step_name.strip():
            colored_print("\n{0}. Skipping action... '{1}' : Blank action name not supported".format(index+1, step_name), tcolors.HEADER)
            continue
        if step_name.startswith(('#', '-')):
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
    double_colored_print('\nCompleted with RUN ID : ', run_id, tcolors.BOLD, tcolors.BOLDLGREEN)
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

    '''  TO BE IMPLEMENTED
    logger = logging.getLogger(__name__)

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
    if config:
        execute(config, args.live_run)

if __name__ == "__main__":
	main()


