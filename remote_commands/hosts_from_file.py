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
import re
import json
import getpass
import argparse

import remote

version = '1.0'

username_regex_patt = '^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$'
ip_regex_patt = '^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}'
host_regex_patt = '^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'

#ValidIpAddressRegex = '^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$'

def print_json(output):
    print json.dumps(output, indent=4)

def get_host_credentials(cred_file, sshuser, sshpass):
    with open(cred_file) as hf:
        lines = hf.readlines()

    ip_regex = re.compile(ip_regex_patt)
    host_regex = re.compile(host_regex_patt)

    prompt_cleared = False
    credentials = {}
    for line in lines:
        line = line.rstrip('\n')
        if not line or line.startswith('#'):
            continue
        if len(line.split(',')) < 3:
            print 'Skipping. Bad record : {0}'.format(line)
            continue
        hostname, username, password = line.split(',',2)
        hostname = hostname.strip()
        username = username.strip()
        if host_regex.search(hostname) or ip_regex.search(hostname):
            if 'credentials.hostname' not in credentials:
                credentials = { 'credentials.hostname' : [], 'credentials.username' : [], 'credentials.password' : [] }
            credentials['credentials.hostname'].append(hostname)

            if username:
                credentials['credentials.username'].append(username)
            elif sshuser:
                credentials['credentials.username'].append(sshuser)
            else:
                print 'Skipping. No username provided : {0}'.format(line)
                continue

            if password:
                credentials['credentials.password'].append(password)
            elif sshpass:
                credentials['credentials.password'].append(sshpass)
            else:
                print 'Skipping. No password provided : {0}'.format(line)
                continue
    return credentials

def main(config_filename = None):
    description = 'Version %s. \nScript to read remote host credentials from a file and run the remote program' % version
    live_run_desc = 'The program is capable of running any UNIX command on any host with credentials. ' \
                    'To AVOID any unwanted consequences of running certain non-recoverable commands like "rm -fr", ' \
                    'the program will EXECUTE the commands only if this flag is enabled. If False, the program ' \
                    'will ONLY output all the resolved commands.'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-u', '--username', help='SSH username for the host', required=False)
    parser.add_argument('-p', '--password', help='Password for the SSH user', required=False)
    parser.add_argument('-f', '--conf-file', dest='conf_file', help='Config file to pass to remote program', required=False)
    parser.add_argument('-c', '--cred-file', dest='cred_file', help='CSV file with hostname,ssh-username,ssh-password', required=True)
    parser.add_argument('--live-run', dest='live_run', help=live_run_desc, action='store_true')
    args = parser.parse_args()

    username = args.username
    password = args.password
    conf_file = args.conf_file
    cred_file = args.cred_file
    #password = getpass.getpass('Ambari password for username [{0}]: '.format(username))
    #if not password:
    #    password = blabla

    credentials = get_host_credentials(cred_file, username, password)

    if conf_file:
        config = remote.load_config(conf_file)
        if 'variables' not in config:
            config['variables'] = credentials
        config['variables']['credentials.hostname'] = credentials['credentials.hostname']
        config['variables']['credentials.username'] = credentials['credentials.username']
        config['variables']['credentials.password'] = credentials['credentials.password']
        remote.execute(config, args.live_run)
    else:
        print 'Variable json'
        print_json( { 'variables' : credentials } )

if __name__ == "__main__":
    main()
