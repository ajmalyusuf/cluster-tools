#!/usr/bin/env python

########################################################################################
# For any questions or suggestions please contact : Ajmal Yusuf <ayusuf@hortonworks.com>
########################################################################################

import sys
import os
import re
import json

def get_variables(hostnames, username, password):
    variables = {}
    if hostnames:
        hostname = hostnames.split(',')
        variables['hostname'] = hostname
    if username:
        variables['username'] = username
    if password:
        variables['password'] = password
    return variables
