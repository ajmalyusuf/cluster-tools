#!/usr/bin/env python

########################################################################################
# For any questions or suggestions please contact : Ajmal Yusuf <ayusuf@hortonworks.com>
########################################################################################

import sys
import os
import json
import datetime
import getpass
import urllib2
import base64

import remote

# Change the default values for the below parameters
# ========================================================================================
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
            #raise Exception('Problem with accessing api. Reason: {0}'.format(exc))
            print 'Unable to connect to Ambari API URL: {0}'.format(api_url)
            print 'Reason: {0}'.format(str(exc))
            sys.exit(1)
        else:
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

def execute(username, password, clustername, base_url, selected_service, selected_component, ssh_user, ssh_pass):
    if not clustername:
        clustername = get_default_cluster_name(base_url)
    cluster_url = '{0}/clusters/{1}'.format(base_url, clustername)

    service_group_type_dict = get_all_current_properties(cluster_url)
    services = list(service_group_type_dict)
    if not selected_service:
        selected_service = get_selection(services, 'a service')

    service_log_dirs = get_service_log_dir(cluster_url, selected_service)
    hostnames_components = get_service_components_hostname(cluster_url, selected_service, selected_component)

    variables = {}
    variables['group1.service'] = []
    variables['group1.log_dir'] = []
    for log_dir in service_log_dirs[selected_service]:
        variables['group1.service'].append(selected_service)
        variables['group1.log_dir'].append(log_dir)

    variables['hostname'] = []
    print '\nBelow are the hosts/nodes for {0}:'.format(selected_service)
    for index, host in enumerate(sorted(hostnames_components)):
        print '{0}. {1}'.format(index+1, host)
        for component in hostnames_components[host]:
            print '    - {0}'.format(component)
        variables['hostname'].append(host)
    print ''
    if ssh_user:
        variables['username'] = ssh_user
    if ssh_pass:
        variables['password'] = ssh_pass
    return variables

def get_ambari_hosts(ambari_server, ambari_port, ambari_username, ambari_password, clustername, service, component, ssh_user, ssh_pass):
    if not (ambari_server or ambari_port or ambari_username or ambari_password):
        try:
            default_prop_file = 'default_properties.json'
            with open(default_prop_file) as dpf:
                def_prop = json.load(dpf)
                if not ambari_server and 'ambari_server' in def_prop:
                    ambari_server = def_prop['ambari_server']
                if not ambari_port and 'ambari_port' in def_prop:
                    ambari_port = def_prop['ambari_port']
                if not ambari_username and 'ambari_username' in def_prop:
                    ambari_username = def_prop['ambari_username']
                if not ambari_password and 'ambari_password' in def_prop:
                    ambari_password = def_prop['ambari_password']
        except Exception as e:
            double_colored_print('Unable to read properties file: ', default_prop_file, tcolors.FAIL, tcolors.WARNING)
            colored_print('Reason: {0}'.format(str(e)), tcolors.FAIL)
                
    ambari_port = ambari_port if ambari_port else default_ambari_port
    ambari_username = ambari_username if ambari_username else default_ambari_user
    protocol = 'http'

    if not ambari_password:
        if ambari_username == default_ambari_user:
            ambari_password = getpass.getpass("Ambari password for '{0}' [{1}]: ".format(ambari_username, default_ambari_password))
            if not ambari_password:
                ambari_password = default_ambari_password
        else:
            ambari_password = getpass.getpass("Ambari password for '{0}': ".format(ambari_username))
    create_global_api_accessor(ambari_username, ambari_password)
    base_url = '{0}://{1}:{2}/api/v1'.format(protocol, ambari_server, ambari_port)
    print '\nConnecting to Ambari REST API: {0}'.format(base_url)
                            
    return execute(ambari_username, ambari_password, clustername, base_url, service, component, ssh_user, ssh_pass)

