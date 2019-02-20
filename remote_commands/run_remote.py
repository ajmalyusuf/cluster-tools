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
import cred
import hosts
import ambari

version = '1.0'

def main():
    def add_common_arguments(subparser, only_conf = False):
        description = 'The program is capable of running any UNIX command on any host with credentials. ' \
                      'To AVOID any unwanted consequences of running certain non-recoverable commands ' \
                      'like "rm -fr", the program will EXECUTE the commands only if this flag is enabled. ' \
                      'If False, the program will ONLY output all the resolved commands.'

        subparser.add_argument('-u', '--sshuser', dest='ssh_user', help='SSH username to connect to hosts', required=False)
        subparser.add_argument('-p', '--sshpass', dest='ssh_pass', help='SSH password to connect to hosts', required=False)
        subparser.add_argument('--run-id', dest='run_id', help='Unique RUN ID. Default: Will be automatically generated.', required=False)
        subparser.add_argument('--live-run', dest='live_run', help=description, action='store_true')
        if only_conf:
            subparser.add_argument('-f', '--conf-file', dest='conf_file', help='Name of the config file in JSON format', required=True)
        else:
            or_group = subparser.add_argument_group(title='only one or the other')
            group = or_group.add_mutually_exclusive_group(required=False)
            group.add_argument('-f', '--conf-file', dest='conf_file', help='Name of the config file in JSON format')
            group.add_argument('--interact', help='Flag to enable SSH in an interactive mode', action='store_true')

    prog = 'remote'
    usage = 'usage: host [-h] [COMMAND]'
    description = 'Script to execute configured commands in local and remote hosts. ' \
                'The program is capable of running any UNIX command on any host with credentials'
    parser = argparse.ArgumentParser(version='{0} {1}'.format(prog, version), description=description, prog=prog)
    subparsers = parser.add_subparsers(title='subcommands', description='Following subcommands are supported:', dest='command')

    description = 'Uses hostnames from the config file itself'
    conf_parser = subparsers.add_parser('conf', help=description)
    add_common_arguments(conf_parser, True)

    description = 'Uses hostnames from /etc/hosts file'
    etc_parser = subparsers.add_parser('hosts', help=description)
    etc_parser.add_argument('-i', '--include-prefix', dest='include_prefix', help='Hostname prefixes to be included', required=False)
    etc_parser.add_argument('-e', '--exclude-prefix', dest='exclude_prefix', help='Hostname prefixes to be excluded. ' \
                            'If include_prefix is provided, that takes preference', required=False)
    add_common_arguments(etc_parser)

    description = 'Uses hostnames from the a credential csv file having hostname,sshuser,password as columns'
    cred_parser = subparsers.add_parser('cred', help=description)
    cred_parser.add_argument('-c', '--cred-file', dest='cred_file', help='CSV file with ' \
                             'hostname,ssh-username,ssh-password as columns. The password (last) ' \
                             'column will NOT be trimmed and can have white spaces.', required=True)
    add_common_arguments(cred_parser)

    description = 'Uses hostnames, log directories for a specific service/component from Ambari API'
    ambari_parser = subparsers.add_parser('ambari', help=description)
    ambari_parser.add_argument('-a', '--ambari-server', dest='ambari_server', help='IP/Hostname of the Ambari Server', required=True)
    ambari_parser.add_argument('-r', '--port', help='Port number for Ambari Server. Default: 8080', required=False)
    ambari_parser.add_argument('-x', '--ambari-user', dest='ambari_user', help='Username for Ambari UI. Default: admin.', required=False)
    ambari_parser.add_argument('-y', '--ambari-pass', dest='ambari_pass', help='Password for Ambari UI. Default: admin', required=False)
    ambari_parser.add_argument('-n', '--clustername', help='Name of the cluster. Default: First available cluster name in Ambari', required=False)
    ambari_parser.add_argument('-s', '--service', help='Service Name', required=False)
    ambari_parser.add_argument('-c', '--component', help='Component Name', required=False)
    add_common_arguments(ambari_parser)

    args = parser.parse_args()

    if args.ssh_user == ':p':
        args.ssh_user = raw_input('Enter ssh username [exit]: ')
        if not args.ssh_user:
            sys.exit(0)

    if args.ssh_pass == ':p':
        if args.ssh_user:
            args.ssh_pass = getpass.getpass('Password for the user({0}) [exit]: '.format(args.ssh_user))
        else:
            args.ssh_pass = getpass.getpass('Enter ssh password [exit]: ')
        if not args.ssh_pass:
            sys.exit(0)

    variables = {}
    if args.command == 'hosts':
        variables = hosts.get_cluster_hosts(args.ssh_user, args.ssh_pass, args.include_prefix, args.exclude_prefix)
    elif args.command == 'cred':
        variables = cred.get_host_credentials(args.cred_file, args.ssh_user, args.ssh_pass)
    elif args.command == 'ambari':
        variables = ambari.get_ambari_hosts(args.ambari_server, args.port, args.ambari_user, args.ambari_pass, \
                                args.clustername, args.service, args.component, args.ssh_user, args.ssh_pass)
    if args.run_id:
        variables['run_id'] = args.run_id

    config = {}
    if args.conf_file:
        config = remote.load_config(args.conf_file)
    elif args.interact:
        config = { "main" : [ "interative_ssh" ], "interative_ssh" : { "action" : "ssh-int" } }
    else:
        remote.print_json( { 'variables' : variables }, 'Variable (json)' )
        sys.exit(0)

    if config:
        if variables:
            config['variables'] = variables
        remote.execute(config, args.live_run)

#### Program Start ####

if __name__ == "__main__":
    main()
