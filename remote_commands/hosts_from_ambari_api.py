#!/usr/bin/env python

########################################################################################
#
# This is a python script to read Ambari configurations and copy the logs
# from appropriate service log_dir
#
# This tool can be run from Windows, Mac or Linux machines installed with python 2.x
# The machine should have access to both Ambari Server nodes on each clusters
#
# Type 'python get_cluster_logs.py' and press enter for running instruction
#
# For any questions or suggestions please contact : Ajmal Yusuf <ayusuf@hortonworks.com>
########################################################################################

import sys
import os
import json
import datetime
import getpass
import urllib2
import base64
import pprint
import argparse

import remote

version = '1.0'

# Change the default values for the below parameters
# ========================================================================================
default_ssh_user = 'sshuser'
default_ambari_user = 'admin'
default_ambari_password = 'admin'
default_ambari_port = '8080'
default_logfile_masks = [ '*.log', '*.err', '*.out', '*.audit', 'gc.log*' ]
default_service_log_subdir = { 'HDFS' : 'hdfs', 'MAPREDUCE2' : 'mapred', 'YARN' : 'yarn' }
default_log_dir_properties = [
    "hdfs_log_dir_prefix",
    "hcat_log_dir",
    "hive_log_dir",
    "mapred_log_dir_prefix",
    "oozie_log_dir",
    "ranger_admin_log_dir",
    "ranger_usersync_log_dir",
    "livy_log_dir",
    "spark_log_dir",
    "livy2_log_dir",
    "spark_log_dir",
    "yarn_log_dir_prefix",
    "zk_log_dir",
    "infra_solr_client_log_dir",
    "infra_solr_log_dir",
    "metrics_monitor_log_dir",
    "metrics_collector_log_dir",
    "metrics_grafana_log_dir",
    "hbase_log_dir",
    "metadata_log_dir",
    "beacon_log_dir",
    "druid_log_dir",
    "hbase_log_dir",
    "kafka_log_dir",
    "hst_log_dir",
    "activity_log_dir",
    "storm_log_dir",
    "superset_log_dir",
    "zeppelin_log_dir"
]
# ========================================================================================

def print_json(output):
    print json.dumps(output, indent=4)

# If you need to change the str formatting later
def format(format_str, variables):
    return format_str.format(**variables)

def create_global_api_accessor(login, password):
    global perform_request
    def perform_request(api_url, request_type='GET', request_body=''):
        try:
            admin_auth = base64.encodestring('%s:%s' % (login, password)).replace('\n', '')
            request = urllib2.Request(api_url)
            request.add_header('Authorization', 'Basic %s' % admin_auth)
            request.add_header('X-Requested-By', 'ambari')
            request.add_data(request_body)
            request.get_method = lambda: request_type
            response = urllib2.urlopen(request)
            response_body = response.read()
        except Exception as exc:
            raise Exception('Problem with accessing api. Reason: {0}'.format(exc))
        return response_body

def get_url_data(url):
    #print '>>> ' + url   # Ajmal
    return perform_request(url)

def get_default_cluster_name(base_url):
    url = '{0}/clusters/'.format(base_url)
    return json.loads(get_url_data(url))['items'][0]['Clusters']['cluster_name']

def get_all_current_properties(cluster_url):
    curr_configs_url = cluster_url + '/configurations/service_config_versions?is_current=true'
    items = json.loads(get_url_data(curr_configs_url))['items']

    service_group_type_properties = {}
    for item in items:
        service = str(item['service_name'])
        if service not in service_group_type_properties.keys():
            service_group_type_properties[service] = {}
        if item['group_id'] == -1:
            group_name = 'Default'
        else:
            group_name = str(item['group_name'])
        listTypes = {}
        for conf in item['configurations']:
            listTypes[str(conf['type'])] = conf['properties']
        service_group_type_properties[service][group_name] = listTypes
    return service_group_type_properties

def get_service_log_dir(cluster_url, selected_service):
    curr_configs_url = cluster_url + '/configurations/service_config_versions?is_current=true'
    items = json.loads(get_url_data(curr_configs_url))['items']

    service_log_dirs = {}
    for item in items:
        service = str(item['service_name'])
        if service != selected_service:
            continue
        if service not in service_log_dirs.keys():
            service_log_dirs[service] = []
        for conf in item['configurations']:
            for prop in conf['properties']:
                if prop in default_log_dir_properties:
                    if service in default_service_log_subdir:
                        log_dir = os.path.join(str(conf['properties'][prop]), default_service_log_subdir[service])
                    else:
                        log_dir = str(conf['properties'][prop])
                    service_log_dirs[service].append(log_dir)
                elif 'log_dir' in prop:
                    print 'Potential log dir -> {0}.{1} : {2}'.format(service, str(prop), str(conf['properties'][prop]))
    return service_log_dirs

def get_service_components_hostname(cluster_url, service, component):
    service_components_url = '{0}/services/{1}/components'.format(cluster_url, service)
    c_items = json.loads(get_url_data(service_components_url))['items']
    components = []
    for c_item in c_items:
        components.append(str(c_item['ServiceComponentInfo']['component_name']))
        
    if not component == 'ALL':
        if not component or not component in components:
            components = get_selection(components, '{0} component'.format(service), include_all=True)
        else:
            components = [ component ]

    hostnames_components = {}
    for component in components:
        service_components_host_url = '{0}/{1}?fields=host_components/HostRoles/host_name'.format(service_components_url, component)
        h_items = json.loads(get_url_data(service_components_host_url))['host_components']
        for h_item in h_items:
            hostname = str(h_item['HostRoles']['host_name'])
            if hostname not in hostnames_components:
                hostnames_components[hostname] = [ component ]
            else:
                hostnames_components[hostname].append(component)
    return hostnames_components

def get_selection(items, name, include_all = False):
    items = sorted(items)
    print ''
    index = 1
    for item in items:
        print '{0}. {1}'.format(index, item)
        index += 1
    if include_all:
        print '{0}. {1}'.format(index, 'All of the above')
    remote.colored_print_without_newline('Select {0} [Exit]: '.format(name), remote.tcolors.WHITE)
    selection = raw_input()
    if selection:
        try:
            index = int(selection)-1
            if index >= 0 and index < len(items):
                if include_all:
                    return [ items[index] ]
                else:
                    return items[index]
            elif include_all and index == len(items):
                return items
            else:
                raise IndexError('list index out of range')
        except Exception as e:
            remote.colored_print('Exception: ' + str(e), remote.tcolors.ITALIC)
            remote.colored_print('Invalid selection. Please re-run and try again.', remote.tcolors.BOLD)
            sys.exit(1)
    else:
        remote.colored_print('Nothing selected. Exiting...', remote.tcolors.BOLD)
        sys.exit(1)

def execute(username, password, clustername, base_url, selected_service, selected_component, conf_file, ssh_user, ssh_pass, run_id):
    if not clustername:
        clustername = get_default_cluster_name(base_url)
    cluster_url = '{0}/clusters/{1}'.format(base_url, clustername)

    service_group_type_dict = get_all_current_properties(cluster_url)
    services = list(service_group_type_dict)
    if not selected_service:
        selected_service = get_selection(services, 'a service')

    service_log_dirs = get_service_log_dir(cluster_url, selected_service)
    hostnames_components = get_service_components_hostname(cluster_url, selected_service, selected_component)

    print '\nBelow are the hosts/nodes for {0}:'.format(selected_service)
    for index, host in enumerate(sorted(hostnames_components)):
        print '{0}. {1}'.format(index+1, host)
        for component in hostnames_components[host]:
            print '    - {0}'.format(component)
    print ''

    if not conf_file:
        selection = raw_input('Do you want to get the config variables to run the script manually? [n]: ')
        if not (selection.upper() == 'Y' or selection.upper() == 'YES'):
            sys.exit(0)

    variables = {}
    variables['group1.service'] = []
    variables['group1.log_dir'] = []
    for log_dir in service_log_dirs[selected_service]:
        variables['group1.service'].append(selected_service)
        variables['group1.log_dir'].append(log_dir)

    variables['credential.hostname'] = []
    variables['credential.username'] = []
    variables['credential.password'] = []
        
    prompt_cleared = False
    for host in sorted(hostnames_components):
        variables['credential.hostname'].append(host)
        if ssh_user:
            variables['credential.username'].append(ssh_user)
        else:
            username = raw_input("\nEnter SSH username for '{0}' [{1}]: ".format(host, default_ssh_user))
            if not username:
                username = default_ssh_user
            variables['credential.username'].append(username)
        if ssh_pass:
            variables['credential.password'].append(ssh_pass)
        else:
            if ssh_user:
                username = ssh_user
            password = getpass.getpass('Password for {0} [Exit]: '.format(username))
            if not password:
                print 'Exiting...'
                sys.exit(0)
            variables['credential.password'].append(password)
        if not prompt_cleared and (not ssh_user or not ssh_pass) and len(hostnames_components) > 1:
            prompt_cleared = True
            selection = raw_input('Use the same credentials for all the host{s}? [y]: ')
            if not selection or selection.upper() == 'Y' or selection.upper() == 'YES':
                ssh_user = username
                ssh_pass = password

    if run_id:
        variables['run_id'] = run_id
    if conf_file:
        config = remote.load_config(conf_file)
        config['variables'] = variables
        remote.execute(config)
    else:
        output = { 'variables' : variables }
        print_json(output)

def main(config_filename = None):
    description = 'Version %s. \nScript to pull service configs and logs from cluster' % version
    live_run_desc = 'The program is capable of running any UNIX command on any host with credentials. ' \
                    'To AVOID any unwanted consequences of running certain non-recoverable commands like "rm -fr", ' \
                    'the program will EXECUTE the commands only if this flag is enabled. If False, the program ' \
                    'will ONLY output all the resolved commands.'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-a', '--ambari_host', help='IP/Hostname of the Ambari Server', required=True)
    parser.add_argument('-r', '--port', help='Port number for Ambari Server. Default: 8080', required=False)
    parser.add_argument('-u', '--username', help='Username for Ambari UI. Default: admin.', required=False)
    parser.add_argument('-p', '--password', help='Password for Ambari UI. Default: admin', required=False)
    parser.add_argument('-n', '--clustername', help='Name of the cluster. Default: First available cluster name in Ambari', required=False)
    parser.add_argument('-s', '--service', help='Service Name', required=False)
    parser.add_argument('-c', '--component', help='Component Name', required=False)
    parser.add_argument('-f', '--conf-file', dest='conf_file', help='Name of the config file in JSON format', required=False)
    parser.add_argument('--ssh-user', dest='ssh_user', help='SSH username to connect to hosts', required=False)
    parser.add_argument('--ssh-pass', dest='ssh_pass', help='SSH password to connect to hosts', required=False)
    parser.add_argument('--run-id', dest='run_id', help='Unique RUN ID. Default: Will be automatically generated.', required=False)
    parser.add_argument('--live-run', dest='live_run', help=live_run_desc, action='store_true')
    args = parser.parse_args()

    ambari_server = args.ambari_host
    conf_file = args.conf_file
    port = args.port if args.port else default_ambari_port
    username = args.username if args.username else default_ambari_user
    clustername = args.clustername if args.clustername else None
    service = args.service.upper() if args.service else None
    component = args.component.upper() if args.component else None
    ssh_user = args.ssh_user if args.ssh_user else None
    ssh_pass = args.ssh_pass if args.ssh_pass else None
    run_id = args.run_id if args.run_id else None
    protocol = 'http'

    if args.password:
        password = args.password
    else:
        if username == default_ambari_user:
            password = getpass.getpass("Ambari password for '{0}' [{1}]: ".format(username, default_ambari_password))
            if not password:
                password = default_ambari_password
        else:
            password = getpass.getpass("Ambari password for '{0}': ".format(username))
    create_global_api_accessor(username, password)
    base_url = '{0}://{1}:{2}/api/v1'.format(protocol, ambari_server, port)
                            
    execute(username, password, clustername, base_url, service, component, conf_file, ssh_user, ssh_pass, run_id)

if __name__ == "__main__":
    main()
