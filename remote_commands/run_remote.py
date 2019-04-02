#!/usr/bin/env python

########################################################################################
# For any questions or suggestions please contact : Ajmal Yusuf <ayusuf@hortonworks.com>
########################################################################################

import sys
import os
import re
import json
import getpass
import argparse

import remote
import conf
import cred
import hosts
import ambari

version = '2.0'

def main():
    def add_common_arguments(subparser, only_conf = False):
        description = 'The program is capable of running any UNIX command on any host with credentials. ' \
                      'To AVOID any unwanted consequences of running certain non-recoverable commands ' \
                      'like "rm -fr", the program will EXECUTE the commands only if this flag is enabled. ' \
                      'If False, the program will ONLY output all the resolved commands.'

        subparser.add_argument('-u', '--username', dest='username', help='SSH username to connect to hosts', required=False)
        subparser.add_argument('-p', '--password', dest='password', help='SSH password to connect to hosts', required=False)
        subparser.add_argument('--run-id', dest='run_id', help='Unique RUN ID. Default: Will be automatically generated.', required=False)
        subparser.add_argument('--live-run', dest='live_run', help=description, action='store_true')
        if only_conf:
            subparser.add_argument('-n', '--hostnames', dest='hostnames',
                                    help='Hostname(s). Comma separated for multiple values', required=False)
        or_group = subparser.add_argument_group(title='only one or the other')
        group = or_group.add_mutually_exclusive_group(required=False)
        group.add_argument('-f', '--conf-file', dest='conf_file', help='Name of the config file in JSON format')
        group.add_argument('--interact', help='Flag to enable SSH in an interactive mode', action='store_true')

    prog = 'run_remote.py'
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

    description = 'Uses hostnames from the a credential csv file having hostname,username,password as columns'
    cred_parser = subparsers.add_parser('cred', help=description)
    cred_parser.add_argument('-c', '--cred-file', dest='cred_file', help='CSV file with ' \
                             'hostname,username,password as columns. The password (last) ' \
                             'column will NOT be trimmed and can have white spaces.', required=True)
    add_common_arguments(cred_parser)

    description = 'Uses hostnames, log directories for a specific service/component from Ambari API'
    ambari_parser = subparsers.add_parser('ambari', help=description)
    ambari_parser.add_argument('-a', '--ambari-server', dest='ambari_server', help='IP/Hostname of the Ambari Server', required=False)
    ambari_parser.add_argument('-r', '--port', help='Port number for Ambari Server. Default: 8080', required=False)
    ambari_parser.add_argument('-x', '--ambari-user', dest='ambari_user', help='Username for Ambari UI. Default: admin.', required=False)
    ambari_parser.add_argument('-y', '--ambari-pass', dest='ambari_pass', help='Password for Ambari UI. Default: admin', required=False)
    ambari_parser.add_argument('-n', '--clustername', help='Name of the cluster. Default: First available cluster name in Ambari', required=False)
    ambari_parser.add_argument('-s', '--service', help='Service Name', required=False)
    ambari_parser.add_argument('-c', '--component', help='Component Name', required=False)
    add_common_arguments(ambari_parser)

    args = parser.parse_args()

    if args.username == ':p':
        args.username = raw_input('Enter ssh username [exit]: ')
        if not args.username:
            sys.exit(0)

    if args.password == ':p':
        if args.username:
            args.password = getpass.getpass('Password for the user({0}) [exit]: '.format(args.username))
        else:
            args.password = getpass.getpass('Enter ssh password [exit]: ')
        if not args.password:
            sys.exit(0)

    variables = {}
    if args.command == 'hosts':
        variables = hosts.get_cluster_hosts(args.username, args.password, args.include_prefix, args.exclude_prefix)
    elif args.command == 'cred':
        variables = cred.get_host_credentials(args.cred_file, args.username, args.password)
    elif args.command == 'ambari':
        variables = ambari.get_ambari_hosts(args.ambari_server, args.port, args.ambari_user, args.ambari_pass, \
                                args.clustername, args.service, args.component, args.username, args.password)
    elif args.command == 'conf':
        variables = conf.get_variables(args.hostnames, args.username, args.password)

    if args.run_id:
        variables['run_id'] = args.run_id

    if args.conf_file:
        config = remote.load_config(args.conf_file)
    elif args.interact:
        config = { "main" : [ "interative_ssh" ], "interative_ssh" : { "action" : "ssh-int" } }
    else:
        remote.print_json( { 'variables' : variables }, 'variables (json)' )
        sys.exit(0)

    remote.execute(config, args.live_run, variables)

#### Program Start ####

if __name__ == "__main__":
    main()
