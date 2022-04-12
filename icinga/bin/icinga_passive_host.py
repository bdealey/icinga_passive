#! /usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020, Julen Larrucea <code@larrucea.eu>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GPLv2, the GNU General Public License version 2, as
# published by the Free Software Foundation. http://gnu.org/licenses/gpl.html

"""
This tool executes a command from the shell and send the output as a
"passive" check for the given host and service into the Icinga2 API.
It is written as a poligloth, so it should work in both Python2 and Python3.
It is written in a slightly trickier way to use only modules in the standard
python library.
"""

from ipaddress import ip_address
import os
import re   
import ssl
import sys
import json
import socket
import base64
import platform
import subprocess
import argparse
import socket
import distro
import json

verbose = False

# Import the functions with the same name to be able to use them
# regardles of the python version
python_version = platform.python_version().split('.')[0]
if python_version == '3':
    from urllib.request import Request, urlopen
elif python_version == '2':
    from urllib2 import Request, urlopen
else:
    print('ERROR: The current Python version is not supported.')
    print('It is neither 2 nor 3!')
    sys.exit(1)


# Do not verify SSL context (probably Icinga2 has a self-signed certificate)
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and 
  getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context

try:
    from icinga_passive_presets import get_presets
    presets_loaded = True
except Exception as e:
    print("WARNING: Unable to load presets")
    presets_loaded = False


# Create an ssl context to ignore SSL validation
def ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

# Try to read API credentials from .icinga_api_creds or prompt the user
def load_creds():
    filename = os.path.expanduser('~') + '/.icinga_api_creds'
    if os.path.isfile(filename):
        try:
            with open(filename) as fh:
                creds = json.load(fh)
                if creds:
                    return creds
        except ValueError as e:
            print('ERROR: the "' + filename + '" seems to be empty or have ' +
                  'wrong format')
            sys.exit(1)

    # print('Enter the API endpoint for Icinga2, for example:')
    # print('  "https://icinga2.example.com:5665"')
    # endpoint = input('Icinga2 endpoint: ')
    # user = input('Enter the username for the Icinga2 API: ')
    # password = input('Enter the password for the Icinga2 API: ')
    # if user and password:
    #     creds = {'username': user,
    #              'password': password,
    #              'endpoint': endpoint}
    #     with open(filename, 'w') as fh:
    #         json.dump(creds, fh)
    #     return creds


# Run a (shell) command and return stdout (list of lines) and RC as a dict
# cmd is a string or a list of elements
def run_cmd(cmd, verbose=False):
    result = {}
    # if isinstance(cmd, str):
    #    cmd = cmd.split()

    if verbose:
        print("Running the following command: " + cmd)
    try:
        out = subprocess.check_output(cmd,
                                      stderr=subprocess.STDOUT,
                                      shell=True
                                      ).decode('utf-8')

        result['rc'] = 0
        result['stdout'] = out.strip()
    except subprocess.CalledProcessError as e:
        result['rc'] = e.returncode
        output = e.output.decode('utf-8')
        result['stdout'] = out.strip()
        #WPD result['stdout'] = output.strip()
        #WPD print('ERROR: The command exited with status ' + str(result['rc']) + 'and erro message:')
        #WPD print(output)
        #WPD sys.exit(1)

    return result


# Make an API request to the given path
# If data (dict) is provided, it will be a POST request
def api_req(method, endpoint, api_path, auth, data=None, verbose=False):

    # Escape posible spaces or '!' characters in the api_path and GET variables
    if ' ' in api_path:
        api_path = api_path.replace(' ', '%20')
    if '!' in api_path:
        api_path = api_path.replace('!', '%21')
    req_url = f"{endpoint}/{api_path}"

    if data:
        data = json.dumps(data)
        # In Python3 the data has to be of type "bytes"
        if python_version == '3':
            data = data.encode('utf-8')

    r = Request(url = req_url, data=data, method=method)

    r.add_header("Authorization", "Basic %s" % auth)  
    if data:
        r.add_header("Content-Type", "application/json")  
        r.add_header("Accept", "application/json")  

    if verbose:
        print('Sending the following request:')
        print('URL: ' + req_url)
        print('HTTP-Headers: ' + json.dumps(r.headers, indent=4))
        if data:
            print('Data: ', r.data)

    try:
        result = urlopen(r)
        res = result.read()
        if type(res) == bytes:
            res = res.decode('utf-8')
    except BaseException as e:
        print('ERROR: Received error from icinga2 server. Has check been defined?\n')
        print(f"{e}")
        sys.exit(2)

    if verbose:
        print('Result received')

    # If something went wrong or unexpected, tell me more
    try:
        rdict = json.loads(res)
    except ValueError as e:
        data = parse_perms(res)
        if data:
            return data

    if 'results' in rdict and rdict['results']:
        return rdict['results']
    elif 'status' in rdict and rdict['status'] == 'No objects found.':
        print('\nERROR: no objects found on path:')
        print(api_path)
        return []
    else:
        print('\nERROR: something went wrong at API path:')
        print(api_path)
        print('Error message:', rdict)
        sys.exit(1)    


def generate_icigna_identifier():
    data = ""
    prefix = "HZA"
    try:
        hzconfig = open("/opt/hopzero/config/hopzero.ini", "r") 
        data = hzconfig.read()
        hzconfig.close()   
    except BaseException as e:
        print("Error, could not read HZ config file")
        sys.exit(2)

    ## Extract the values out of the fiel
    serial_number_re = re.findall("serial_number: (.+)", data)
    customer_id_re   = re.findall("customer_id:\s*(.+)", data)  

    serial_number = ""
    if serial_number_re:
        serial_number = serial_number_re[0]
    
    customer_id = ""
    if customer_id_re:
        customer_id = customer_id_re[0]

    icinga_identifer = f"{prefix}_{customer_id}_{serial_number}"
    return icinga_identifer

def get_os_attr_dict():
    attrs = {}
    vars = {}
    platform_system = platform.system() 
    ## Not currently supported on windows
    platform_version = ''
    platform_name = ''
    if platform_system in ['Linux', 'Darwin']:
        platform_name = distro.name(pretty=True)
        platform_version = distro.version()

    python_version = sys.version.split('\n')[0].split()
    vars['python_version'] = python_version[0]
    vars['machine'] = platform.machine()
    vars['os'] = platform_system
    vars['os_name'] = platform_name
    vars['os_version'] = platform_version

    ## Hostname/ip via socket
    local_host = socket.gethostname()
    local_ip = socket.gethostbyname(local_host)
    vars['host_name'] = local_host
    vars['local_ip'] = local_ip

    ## Read hzagent config
    hzagent_version = ''
    hzagent_installed = ''
    try:
        with open("/opt/hopzero/config/hzagent.json", "r") as jsonfile:
            data = json.load(jsonfile)
        hzagent_version = data['hzagent_version']
        hzagent_installed = data['installed_date']
    except BaseException as e:
        print(f"Error could not find hzagent config file")
        
    vars['hzagent_ver'] = hzagent_version
    vars['hzagent_installed'] = hzagent_installed
    attrs['address'] = local_ip
    attrs['vars'] = vars
    return attrs

def create_host( endpoint, auth ):
    print('Creating host ....', auth)
    api_path_base = 'v1/objects/hosts/'

    icigna_identifer = generate_icigna_identifier()

    api_path = f"{api_path_base}{icigna_identifer}"

    data = {}
    data['templates'] = ["hzagent-host"]

    attrs = get_os_attr_dict()
    data['attrs'] = attrs

    print(attrs)
    api_req('PUT', endpoint, api_path, auth, data, verbose)

def delete_host( endpoint, auth ):
    print('Deleting host ....')
    api_path = 'v1/objects/hosts'

    icigna_identifer = generate_icigna_identifier()
    data = {}
    data['filter'] = f'match("{icigna_identifer}", host.name)'
    data['cascade'] = True

    api_req('DELETE', endpoint, api_path, auth, data, verbose)


def main():
    global verbose

    creds = load_creds()
    username = creds['username']
    password = creds['password']
    endpoint = creds['endpoint']

    # Python3 requires the auth pair to be in bytes and python2 as string
    auth_pair = username + ':' + password
    if python_version == '3':
        auth_pair = str.encode(auth_pair)
    auth = base64.b64encode(auth_pair)
    if python_version == '3':
        auth = auth.decode('utf-8')

    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mode',    choices=['create','delete'], help='Create or delete this host from icinga2')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print verbose output')

    args = parser.parse_args()

    verbose = args.verbose

    ## Create hosts should be called from the hzagent installer, and needs to be run only once
    if args.mode == "create":
        create_host(endpoint, auth)
    elif args.mode == "delete":
        delete_host(endpoint, auth)
    else:
        print("ERROR: Mode not recoginized:", args.mode)
        sys.exit(1)


if __name__ == '__main__':
    main()
