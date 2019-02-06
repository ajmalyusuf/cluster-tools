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
import etchosts
import ambari

version = '1.0'
username_regex_patt = '^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$'
ip_regex_patt = '^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}'
host_regex_patt = '^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
#ValidIpAddressRegex = '^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$'

def main():
    def add_common_arguments(subparser, only_conf = False):
        description = 'The program is capable of running any UNIX command on any host with credentials. ' \
                      'To AVOID any unwanted consequences of running certain non-recoverable commands ' \
                      'like "rm -fr", the program will EXECUTE the commands only if this flag is enabled. ' \
                      'If False, the program will ONLY output all the resolved commands.'

        subparser.add_argument('--ssh-user', dest='ssh_user', help='SSH username to connect to hosts', required=False)
        subparser.add_argument('--ssh-pass', dest='ssh_pass', help='SSH password to connect to hosts', required=False)
        subparser.add_argument('--run-id', dest='run_id', help='Unique RUN ID. Default: Will be automatically generated.', required=False)
        subparser.add_argument('--live-run', dest='live_run', help=description, action='store_true')
        if only_conf:
            subparser.add_argument('-f', '--conf-file', dest='conf_file', help='Name of the config file in JSON format', required=True)
        else:
            or_group = subparser.add_argument_group(title='only one or the other')
            group = or_group.add_mutually_exclusive_group(required=False)
            group.add_argument('-f', '--conf-file', dest='conf_file', help='Name of the config file in JSON format')
            group.add_argument('--interactive', help='Flag to enable SSH in an interactive mode', action='store_true')

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
    etc_parser = subparsers.add_parser('etc', help=description)
    etc_parser.add_argument('-i', '--include-prefix', dest='include_prefix', help='Hostname prefixes to be included', required=False)
    etc_parser.add_argument('-e', '--exclude-prefix', dest='exclude_prefix', help='Hostname prefixes to be excluded. If include_prefix is provided, that takes preference', required=False)
    add_common_arguments(etc_parser)

    description = 'Uses hostnames from the a credential csv file having hostname,sshuser,password'
    cred_parser = subparsers.add_parser('cred', help=description)
    cred_parser.add_argument('-c', '--cred-file', dest='cred_file', help='CSV file with hostname,ssh-username,ssh-password', required=True)
    add_common_arguments(cred_parser)

    description = 'Uses hostnames, log directories for a specific service/component from Ambari API'
    ambari_parser = subparsers.add_parser('ambari', help=description)
    ambari_parser.add_argument('-a', '--ambari-server', dest='ambari_server', help='IP/Hostname of the Ambari Server', required=True)
    ambari_parser.add_argument('-r', '--port', help='Port number for Ambari Server. Default: 8080', required=False)
    ambari_parser.add_argument('-u', '--ambari-user', dest='ambari_user', help='Username for Ambari UI. Default: admin.', required=False)
    ambari_parser.add_argument('-p', '--ambari-pass', dest='ambari_pass', help='Password for Ambari UI. Default: admin', required=False)
    ambari_parser.add_argument('-n', '--clustername', help='Name of the cluster. Default: First available cluster name in Ambari', required=False)
    ambari_parser.add_argument('-s', '--service', help='Service Name', required=False)
    ambari_parser.add_argument('-c', '--component', help='Component Name', required=False)
    add_common_arguments(ambari_parser)

    args = parser.parse_args()

    if args.ssh_user and (args.ssh_pass == ':p' or not args.ssh_pass):
        args.ssh_pass = getpass.getpass('SSH password for the user({0}): '.format(args.ssh_user))

    variables = {}
    if args.command == 'etc':
        variables = etchosts.get_cluster_hosts(args.ssh_user, args.ssh_pass, args.include_prefix, args.exclude_prefix)
    elif args.command == 'cred':
        variables = cred.get_host_credentials(args.cred_file, args.ssh_user, args.ssh_pass)
    elif args.command == 'ambari':
        variables = ambari.get_ambari_hosts(args.ambari_server, args.port, args.ambari_user, args.ambari_pass, \
                                            args.clustername, args.service, args.component, args.ssh_user, args.ssh_pass)
    else: # args.command == 'conf'
        pass

    config = {}
    if args.conf_file:
        config = remote.load_config(args.conf_file)
    elif args.interactive:
        config = { "main" : [ "interative_ssh" ], "interative_ssh" : { "action" : "ssh-int" } }
    else:
        remote.print_json( { 'variables' : variables }, 'Variable json' )
        sys.exit(0)

    if config:
        if variables:
            config['variables'] = variables
        if args.run_id and 'variables' in config:
            config['variables']['run_id'] = args.run_id
        remote.execute(config, args.live_run)

#### Program Start ####

if __name__ == "__main__":
    main()
