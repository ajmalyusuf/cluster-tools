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
import datetime
import getpass
import pprint
import argparse

import remote

version = '1.0'

etc_host_file = '/etc/hosts'
ip_regex_patt = '^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}'

def pretty_print(d):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(d)

def get_cluster_hosts(host_file, include_prefix = None, exclude_prefix = None):
    inc_tup, exc_tup = None, None
    if include_prefix:
        inc_tup = tuple(include_prefix.replace(' ', '').split(','))
    if exclude_prefix:
        exc_tup = tuple(exclude_prefix.replace(' ', '').split(','))

    regex = re.compile(ip_regex_patt)
    with open(host_file) as hf:
        lines = hf.readlines()
    hosts = []
    for line in lines:
        line = re.sub('\s+', ' ', line).strip()
        match = regex.search(line)
        if match:
            names = line.split(' ')
            if len(names) > 2:
                hostname = names[1]
                if inc_tup:
                    if hostname.startswith(inc_tup):
                        hosts.append(hostname)
                    continue
                if exc_tup:
                    if hostname.startswith(exc_tup):
                        continue
                hosts.append(hostname)
    return hosts

def main(config_filename = None):
    description = 'Version %s. \nScript to read cluster hostnames from /etc/hosts and pass it to the remote program' % version
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-u', '--username', help='SSH username for the host', required=True)
    parser.add_argument('-p', '--password', help='Password for the SSH user', required=True)
    parser.add_argument('-f', '--conf-file', dest='conf_file', help='Config file to pass to remote program', required=False)
    parser.add_argument('-i', '--include-prefix', dest='include_prefix', help='Hostname prefixes to be included', required=False)
    parser.add_argument('-e', '--exclude-prefix', dest='exclude_prefix', help='Hostname prefixes to be excluded. If include_prefix is provided, that takes preference', required=False)
    args = parser.parse_args()

    username = args.username
    password = args.password
    conf_file = args.conf_file
    #password = getpass.getpass('Ambari password for username [{0}]: '.format(username))
    #if not password:
    #    password = default_ambari_password

    usernames = []
    passwords = []
    hosts = get_cluster_hosts(etc_host_file, args.include_prefix, args.exclude_prefix)
    for host in hosts:
        usernames.append(username)
        passwords.append(password)

    if conf_file:
        config = remote.load_config(conf_file)
        if 'variables' not in config:
            config['variables'] = {}
        config['variables']['credentials.hostname'] = hosts
        config['variables']['credentials.username'] = usernames
        config['variables']['credentials.password'] = passwords
        remote.execute(config)
    else:
        pretty_print( hosts )

if __name__ == "__main__":
    main()
