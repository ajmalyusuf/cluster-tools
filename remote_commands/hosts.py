#!/usr/bin/env python

########################################################################################
# For any questions or suggestions please contact : Ajmal Yusuf <ayusuf@hortonworks.com>
########################################################################################

import os
import re
import sys
import json

etc_host_file = '/etc/hosts'
ip_regex_patt = '^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}'

def get_cluster_hosts(sshuser, sshpass, include_prefix = None, exclude_prefix = None):
    inc_tup, exc_tup = None, None
    if include_prefix:
        inc_tup = tuple(include_prefix.replace(' ', '').split(','))
    if exclude_prefix:
        exc_tup = tuple(exclude_prefix.replace(' ', '').split(','))

    regex = re.compile(ip_regex_patt)
    with open(etc_host_file) as hf:
        lines = hf.readlines()

    hostnames = []
    for line in lines:
        line = re.sub('\s+', ' ', line).strip()
        match = regex.search(line)
        if match:
            names = line.split(' ')
            if len(names) > 2:
                hostname = names[1]
                if inc_tup:
                    if hostname.startswith(inc_tup):
                        hostnames.append(hostname)
                    continue
                if exc_tup:
                    if hostname.startswith(exc_tup):
                        continue
                hostnames.append(hostname)

    credentials = {}
    credentials['hostname'] = hostnames
    if sshuser:
        credentials['username'] = sshuser
    if sshpass:
        credentials['password'] = sshpass
    return credentials

