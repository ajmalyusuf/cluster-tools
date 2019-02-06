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

username_regex_patt = '^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$'
ip_regex_patt = '^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}'
host_regex_patt = '^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
#ValidIpAddressRegex = '^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$'

def get_first_valid(values, error_str=None):
    for value in values:
        if value:
            return value
    print error_str
    return None

def get_host_credentials(cred_file, sshuser, sshpass):
    with open(cred_file) as hf:
        lines = hf.readlines()

    ip_regex = re.compile(ip_regex_patt)
    host_regex = re.compile(host_regex_patt)

    credentials = { 'credentials.hostname' : [], 'credentials.username' : [], 'credentials.password' : [] }
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
            username = get_first_valid([username, sshuser], 'Skipping. No username provided : {0}'.format(line))
            if not username:
                continue
            password = get_first_valid([password, sshpass], 'Skipping. No password provided : {0}'.format(line))
            if not password:
                continue
            credentials['credentials.hostname'].append(hostname)
            credentials['credentials.username'].append(username)
            credentials['credentials.password'].append(password)
    return credentials
