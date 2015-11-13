__FILENAME__ = apache_log_age
#!/usr/bin/env python
#
# License: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from log_freshness import check_logs

# Apache log age: alert if the apache access log hasn't been modified in over 
# 2 hours. This script is really more of an example of how to use 
# log_freshness.py

# Alert if log hasn't been modified in over 2 hours
check_logs((60*60*2, '/var/log/apache/access.log'))

########NEW FILE########
__FILENAME__ = check_drbd
#!/usr/bin/env python

# Cloudkick plugin that monitors various DRBD parameters.
#
# Plugin arguments:
# 1. Minor device number of the DRBD device to monitor
#
# Author: Andrew Miklas / PagerDuty
# Copyright (c) 2011 PagerDuty, Inc. <andrew@pagerduty.com>
#
# MIT License:
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import re

def parse_line(line):
    d = {}

    # Extract everything that looks line a k/v pair
    for kv_pair in line.split():
        l = kv_pair.split(':', 1)
        if len(l) < 2:
            continue
        d[l[0]] = l[1]

    return d


def read_proc_drbd(filename, device_num):
    try:
        info_fd = open(filename, "r")
    except IOError:
        print 'status err drbd device (%s) not found' % (filename)
        sys.exit(1)

    device_num = str(device_num)
    dev_stats = {}

    while True:
        line = info_fd.readline()
        if not line: break

        match = re.search(r'^\s*(\d+):\s+(.*)$', line)
        if not match:
            continue
        if match.groups()[0] == device_num:
            # Device stat lines come in pairs.  We've already got the
            # first one, so read in the second.
            for l in [match.groups()[1], info_fd.readline()]:
                dev_stats.update(parse_line(l))
            return dev_stats

    # Device not found
    return None


fmt_string = str
fmt_count = str

def fmt_size(val):
    # DRBD sizes are in KiBytes
    return str(int(val) * 1024)


METRICS = (
    ("connection_state", "cs", "string", fmt_string),
    ("disk_state", "ds", "string", fmt_string),
    ("roles", "ro", "string", fmt_string),

    ("network_send", "ns", "int", fmt_size),
    ("network_send_rate", "ns", "gauge", fmt_size),
    ("network_receive", "nr", "int", fmt_size),
    ("network_receive_rate", "nr", "gauge", fmt_size),
    ("disk_write", "dw", "int", fmt_size),
    ("disk_write_rate", "dw", "gauge", fmt_size),
    ("disk_read", "dr", "int", fmt_size),
    ("disk_read_rate", "dr", "gauge", fmt_size),
    ("out_of_sync", "oos", "int", fmt_size),
    ("out_of_sync_rate", "oos", "gauge", fmt_size),

    ("activity_log", "al", "int", fmt_count),
    ("activity_log_rate", "al", "gauge", fmt_count),
    ("bit_map", "bm", "int", fmt_count),
    ("bit_map_rate", "bm", "gauge", fmt_count),

    ("local_count", "lo", "int", fmt_count),
    ("pending", "pe", "int", fmt_count),
    ("unacknowledged", "ua", "int", fmt_count),
    ("application_pending", "ap", "int", fmt_count),
    ("epochs", "ep", "int", fmt_count)
)

OK_CONN_STATES = ("Connected", "VerifyS", "VerifyT")
WARN_CONN_STATES = ("StandAlone", "Disconnecting", "StartingSyncS", "StartingSyncT", "WFBitMapS", "WFBitMapT", "WFSyncUUID", "SyncSource", "SyncTarget", "PausedSyncS", "PausedSyncT")


if len(sys.argv) < 2:
    print >>sys.stderr, "Usage: check_drbd.py drbd_dev_num"
    exit(2)

device_num = sys.argv[1]
dev_stats = read_proc_drbd("/proc/drbd", device_num)

if dev_stats is None:
    print >>sys.stderr, "Couldn't find DRBD device number %s" % device_num
    sys.exit(1)

conn_state = dev_stats.get("cs")
if conn_state is None:
    print >>sys.stderr, "Connection state can't be found!"
    sys.exit(1)

if conn_state in OK_CONN_STATES:
    print 'status ok Connection is in an OK state'
elif conn_state in WARN_CONN_STATES:
    print 'status warn Connection is in a WARN state'
else:
    print 'status err Connection is in a ERR state'

for m in METRICS:
    if m[1] in dev_stats:
        print "metric %s %s %s" % (m[0], m[2], m[3](dev_stats.get(m[1])))

sys.exit(0)

########NEW FILE########
__FILENAME__ = check_ldap
#!/usr/bin/env python
#
# License: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# This Cloudkick Agent plugin attempts to bind to the specified LDAP server
# and will report an error if it is unable to do so.
#
# It depends on the 'python-ldap' library from http://www.python-ldap.org/
#
# In most cases you will only need to specify the server name
#

import ldap


SERVER = 'localhost'
USER = ''
PASS = ''
NETWORK_TIMEOUT = 5

try:
  l = ldap.open(SERVER)
  l.set_option(ldap.OPT_NETWORK_TIMEOUT, NETWORK_TIMEOUT)
  l.simple_bind(USER, PASS)
  print "status ok LDAP Bind Successful"
except ldap.LDAPError, e:
  # Error messages must be truncated to 48 characters
  print "status err %s" % str(e)[:48]
except Exception, e:
  print "status err Unknown Bind Error"

########NEW FILE########
__FILENAME__ = check_loopback
#!/usr/bin/env python
#
# License: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Cloudkick plugin that checks if the loopback interface is available, has at least one ip address
# assigned and is up
#

import re
import sys
import random
import socket
import subprocess

DEFAULT_INTERFACE = 'lo0'
DEFAULT_TIMEOUT = 2

def main():
  arg_len = len(sys.argv)

  if arg_len >= 2:
    loopback_interface = sys.argv[1]
  else:
    loopback_interface = DEFAULT_INTERFACE

  if arg_len == 3:
    connect_timeout = int(sys.argv[2])
  else:
    connect_timeout = DEFAULT_TIMEOUT

  (stdout, stderr) = subprocess.Popen(['ifconfig', '-v', loopback_interface], stdout = subprocess.PIPE, stderr = subprocess.PIPE, close_fds = True).communicate()

  if stderr.find('Device not found') != -1 or stderr.find('does not exist') != -1:
    print 'status err %s interface not found' % (loopback_interface)
    sys.exit(1)

  lines = stdout.split('\n')
  has_ip_address = False
  for line in lines:
    line = line.strip()

    match = re.search(r'inet (addr)?:?(.*?) ', line)
    if match:
      has_ip_address = True
      inet_addr = match.groups()[1]
      break

  if not has_ip_address:
     print 'status err %s interface has no ip address' % (loopback_interface)
     sys.exit(1)

  port = random.randint(20000, 40000)
  try:
    if int(sys.version[0]) == 2 and int(sys.version[2]) <= 5:
        connection_socket = socket.socket(socket.AF_INET)
        connection_socket.settimeout(connect_timeout)
        connection = connection_socket.connect((inet_addr, port))
    else:
        connection = socket.create_connection((inet_addr, port), connect_timeout)
  except socket.timeout, e:
    print 'status err can\'t establish connection to %s:%s' % (inet_addr, port)
    sys.exit(1)
  except socket.error:
    pass

  print 'status ok %s interface is up and working' % (loopback_interface)
  sys.exit(0)

main()

########NEW FILE########
__FILENAME__ = check_nvidia_gpu
#!/usr/bin/env python
#
# License: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Cloudkick plugin for monitoring Nvidia GPU metrics

import re
import sys
import subprocess

COMMAND = 'nvidia-smi'
COMMAND_ARGS = [ '-q', '-a' ]

METRIC_MAPPINGS = {
                  'gpu': {'type': 'int', 'display_name': 'gpu_usage'},
                  'memory': {'type': 'int', 'display_name': 'memory_usage'},
                  'product name': {'type': 'string', 'display_name': 'product_name'}
}

GPU_NUMBER_RE = re.compile(r'GPU\s+(\d+)', re.IGNORECASE)

def close_file(file_handle):
  try:
    file_handle.close()
  except Exception:
    pass

def main():
  file_handle = open('/tmp/cloudkick-plugin-tmp', 'w')

  command = [ COMMAND ] + COMMAND_ARGS
  (stdout, stderr) = subprocess.Popen(command, stdout = subprocess.PIPE, \
                       stderr = subprocess.PIPE, close_fds = True).communicate()

  try:
    metric_values = parse_output(stdout)
  except Exception, e:
    if stderr:
      error = stderr
    else:
      error = str(e)
    print 'status err Failed to parse metrics: %s' % (error)
    close_file(file_handle)
    sys.exit(1)

  if not metric_values:
    print 'status err Failed to retrieve metrics %s' % (', ' .join(METRIC_MAPPINGS.keys()))
    close_file(file_handle)
    sys.exit(1)

  close_file(file_handle)
  print_metrics(metric_values)

def parse_output(output):
  lines = output.split('\n')

  metric_keys = METRIC_MAPPINGS.keys()
  metric_values = {}
  gpu_number = None
  for line in lines:
    line_original = line.strip()
    line_lower = line_original.lower()

    match = re.match(GPU_NUMBER_RE, line_lower)
    if match:
      gpu_number = match.group(1)
      continue

    split_lower = line_lower.split(':')
    split_original = line_original.split(':')
    if len(split_lower) != 2:
      continue

    name = split_lower[0].strip()
    value = split_original[1].strip()
    metric = METRIC_MAPPINGS.get(name, None)

    if metric and gpu_number is not None:
      name = 'gpu_%s_%s' % (gpu_number, name)
      display_name = 'gpu_%s_%s' % (gpu_number, metric['display_name'])
      metric_values[name] = { 'display_name': display_name, 'value': value}

  return metric_values

def print_metrics(metric_values):
  metrics = []
  output = []
  for key, value in metric_values.items():
    key = re.sub('gpu_\d+_', '', key)
    metric_type = METRIC_MAPPINGS.get(key).get('type')
    display_name = value['display_name']
    metric_value = value['value']

    metrics.append('%s: %s' % (display_name, metric_value))
    output.append('metric %s %s %s' % (display_name, metric_type, metric_value))

  print 'status ok %s' % (', ' . join(metrics))
  print '\n' . join(output)

main()

########NEW FILE########
__FILENAME__ = cyberpower_status
#!/usr/bin/python -tt
# cyberpower_status.py
#
# Builds metrics provided to us by the PowerPanel package (pwrstat)
# for CyberPower UPS units.
#
# Written for the CP850PFCLCD using version 1.2 of PowerPanel for Linux, 
# it should function the same for any CyberPower UPS unit that supports
# communications over USB. If you run into any bugs, let me know.
#
# Copyright (C) 2011  James Bair <james.d.bair@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import commands
import os
import sys

def getInfo():
   """
   Get all pertinent information from our CyberPower UPS
   """
   
   # Ensure pwrstat is present. If not, abort.
   status, out = commands.getstatusoutput('pwrstat -status')
   if status:
       msg = "status err Unable to find PowerPanel software.\n"
       msg += "Please install the required software and try again.\n"
       sys.stderr.write(msg)
       sys.exit(status)

   # Build our results into key: value pairs.
   results = {}
   # All values are separated by a line of periods.
   # Get the items on either side.
   for line in out.split('\n'):
       if '.' in line:
           option = line.split('.')[0].strip()
           value = line.split('.')[-1].strip()
           # Rename a few options to make them more clear.
           # Also, in making numbers ints, we lose the Volt/Watt label.
           if option == 'Load':
               option = 'Load Wattage'
                # Might as well pull out the percentage while we are here.
               results['Watt Percentage'] = int(line.split()[-2].split('(')[1])
           elif option == 'Rating Power':
               option = 'Rating Wattage'
           elif option == 'Battery Capacity':
               option = 'Battery Percentage'
           elif option == 'Remaining Runtime':
               option = 'Minutes Remaining'
               # A period after "Min" requires a different split
               value = int(line.split('.')[-2].strip().split()[0])

           # Pull the options we want as integers.
           if option in ( 'Rating Wattage', 'Battery Percentage',
                          'Utility Voltage', 'Output Voltage', 
                          'Rating Voltage', 'Load Wattage' ):
               value = int(value.split()[0])

           # Add our new key
           results[option] = value

   # Send the results
   return results

def makeMetric(ourName, ourValue, gauge=False):
    """
    Build a metric string per the documentation here:
    https://support.cloudkick.com/Creating_a_plugin
    """

    # Find our type
    ourType = type(ourValue)

    # Check if it's a string, int or float.
    if ourType not in ( str, int, float ):
        msg = 'status err Invalid value passed to makeMetric. Exiting.\n'
        sys.stderr.write(msg)
        sys.exit(1)

    # Set to gauge if needed, otherwise change our object to it's name.
    if gauge and ourType is int:
        ourType = 'gauge'
    # CloudKick wants string instead of str
    elif ourType is str:
        ourType = 'string'
    else:
        ourType = ourType.__name__

    # Cannot have spaces in our name, so replace_with_underscores.
    ourName = ourName.replace(' ', '_')

    # Send our metric.
    return 'metric %s %s %s\n' % (ourName, ourType, ourValue)

# MAIN
if __name__ == '__main__':
    # pwrstat requires root to poll UPS
    if os.getuid():
        msg = 'status err This script must be run as root.\n'
        sys.stderr.write(msg)
        sys.exit(1)

    # Get our info from the UPS
    info = getInfo()
    # If we have the info, check it's state
    if info:
        if info['State'] == 'Normal':
            status = 'ok'
        else:
            status = 'warn'

        # First, build our status message based on state.
        msg = "status %s Our %s UPS is in a '%s' state.\n" % (status, 
                                                              info['Model Name'],
                                                              info['State'])
        
        # Then, iterate through our keys
        for k, v in info.items():
            msg += makeMetric(k, v)

        # Send it all to stdout and we are done.
        sys.stdout.write(msg)
        sys.exit(0)

    # If we got here, something went wrong.
    else:
        sys.stdout.write('status err Unable to get our UPS information.\n')
        sys.exit(1)

########NEW FILE########
__FILENAME__ = fail2ban
#!/usr/bin/env python
"""
Count the number of IPs that were banned in the last minute.

Usage:
  fail2ban.py [warn_count] [alert_count]

LICENSE: http://www.opensource.org/licenses/mit-license.php
AUTHOR:  Caleb Groom <http://github.com/calebgroom>
"""

import sys
import glob
import os.path
import ConfigParser
import socket
from datetime import datetime, timedelta

WARN_COUNT = 2
ALERT_COUNT = 5
now = datetime.now() - timedelta(minutes=1)

# The alerting thresholds can be overridden via command line arguments
limits = [WARN_COUNT, ALERT_COUNT]
for i in [2,3]:
    if len(sys.argv) >= i:
      try:
          limits[i-2] = int(sys.argv[i-1])
      except ValueError:
          print 'status err argument "%s" is not a valid integer' % sys.argv[i-1]
          sys.exit(1)

# Discover 'logtarget' setting in configuration file
paths = ['/etc/fail2ban.conf', '/etc/fail2ban/*.conf']
config_files = []
for p in paths:
    files = glob.glob(p)
    for f in files:
        if os.path.isfile(f):
            config_files.append(f)

config = ConfigParser.ConfigParser()
config.read(config_files)
try:
    logfile = config.get("Definition", "logtarget")
except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
    print 'status err "logtarget" is not defined in', ', ' .join(config_files)
    sys.exit(1)

if not os.path.isfile(logfile):
    print 'status err log file', logfile, 'is not a file'
    sys.exit(1)

# Drop the seconds from the timestam and look for ban entries.
# Sample ban message:
#     2010-10-21 18:01:08,099 fail2ban.actions: WARNING [ssh-iptables] Ban 1.2.3.4
timestamp = now.isoformat(' ')[:17]
count = 0
ips = []

try:
    f = open(logfile, 'r')
except IOError:
    print 'status err Unable to open log file', logfile
    sys.exit(1)

needle = ' Ban '
for line in f:
    if line.startswith(timestamp):
        i = line.rfind(needle)
        if i == -1:
            continue
        ip = line[i+len(needle):len(line)-1]
        try:
            socket.inet_aton(ip)
            # Matching timestamp, 'Ban' and valid IP
            count += 1
            ips.append(ip)
        except socket.error:
            pass

try:
    f.close()
except Exception:
  pass

print 'metric bans int', count

if count == 0:
    ips = ""

if count >= limits[1]:
    print 'status err', count, 'IPs banned', ips
elif count >= limits[0]:
    print 'status warn', count, 'IPs banned', ips
else:
    print 'status ok', count, 'IPs banned', ips

########NEW FILE########
__FILENAME__ = latency_check
#!/usr/bin/env python
#
# License: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Cloudkick plugin for monitoring latency between local and remote host.
#
# Plugin takes the following arguments:
#
# 1. IPv4 or IPv6 address of the target machine
# 2. number of packets to send
# 3. timeout (how long to wait for a response before quitting)
#
# Note 1: timeout must be lower or equal to 19, because plugins running longer then 20 seconds are 
#         automatically killed by the agent
# Note 2: If using IPv6 address, the address must be in the full uncompressed form 
#         (http://grox.net/utils/ipv6.php)
#

import re
import os
import sys
import subprocess

DEFAULT_PACKET_COUNT = 3
DEFAULT_TIMEOUT = DEFAULT_PACKET_COUNT * 4

IPV4_RE = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
IPV6_RE = re.compile(r'^(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}$', re.IGNORECASE)

LINUX_PACKETS_RE = re.compile(r'(\d+) packets transmitted, (\d+) received, (.*?)% packet loss, time (\d+)ms')
LINUX_STATS_RE = re.compile(r'rtt min/avg/max/mdev = (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+) ms')
FREEBSD_PACKETS_RE = re.compile(r'(\d+) packets transmitted, (\d+) packets received, (.*?)% packet loss')
FREEBSD_STATS_RE = re.compile(r'round-trip min/avg/max/(stddev|std-dev) = (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+) ms')

METRIC_TYPES = {
  'trans_packets': 'int',
  'recv_packets': 'int',
  'lost_packets': 'int',
  
  'response_min': 'float',
  'response_max': 'float',
  'response_avg': 'float'
}

def main(ip_address, packet_count, timeout):
  platform = get_platform()
  
  if platform == 'unknown':
    print 'status err Unsupported platform: %s' % (sys.platform)
    sys.exit(1)
  
  command_arguments = ['-c', packet_count]
  if re.match(IPV4_RE, ip_address):
    command = 'ping'
    
    if platform == 'freebsd':
      command_arguments.extend(['-t', timeout])
    else:
      command_arguments.extend(['-w', timeout])
  elif re.match(IPV6_RE, ip_address):
    command = 'ping6'
  
  command_arguments.insert(0, command)
  command_arguments.append(ip_address)
  
  (stdout, stderr) = subprocess.Popen(command_arguments, stdout = subprocess.PIPE, \
                                      stderr = subprocess.PIPE, close_fds = True).communicate()
  
  if stderr:
    print 'status err Failed executing %s command: %s' % (command, stderr[:17])
    sys.exit(1)
  
  metric_values = parse_response(stdout)
  print_metrics(metric_values)
    
def parse_response(response):
  platform = get_platform()
  
  if platform == 'linux':
    packets_re = LINUX_PACKETS_RE
    stats_re = LINUX_STATS_RE
  elif platform == 'freebsd':
    packets_re = FREEBSD_PACKETS_RE
    stats_re = FREEBSD_STATS_RE
    
  packet_stats = re.search(packets_re, response)
  response_stats = re.search(stats_re, response)
  
  if not packet_stats:
    print 'status err Failed to parse response: %s' % (response[:21])
    sys.exit(1)
  
  metric_values = {}
  metric_values['trans_packets'] = packet_stats.group(1)
  metric_values['recv_packets'] = packet_stats.group(2)
  metric_values['lost_packets'] = int(metric_values['trans_packets']) - int(metric_values['recv_packets'])
  
  
  if response_stats:  
    metric_values['response_min'] = response_stats.group(1)
    metric_values['response_max'] = response_stats.group(2)
    metric_values['response_avg'] = response_stats.group(3)

  return metric_values

def print_metrics(metric_values):
  for key, value in metric_values.items():
      print 'metric %s %s %s' % (key, METRIC_TYPES[key], value)

def get_platform():
  if sys.platform.find('linux') != -1:
    platform = 'linux'
  elif sys.platform.find('freebsd') != -1:
    platform = 'freebsd'
  else:
    platform = 'unknown'
    
  return platform

if __name__ == '__main__':
  arg_len = len(sys.argv)
  
  if arg_len not in [2, 3, 4]:
    print 'status err Invalid number of arguments (%s)' % (arg_len - 1)
    sys.exit(1)
  
  packet_count = None
  timeout = None  
  if arg_len >= 2:
    ip_address = sys.argv[1]
  if arg_len >= 3:
    packet_count = sys.argv[2]
  if arg_len >= 4:
    timeout = sys.argv[3]
  
  packet_count = int(packet_count or DEFAULT_PACKET_COUNT)
  timeout = int(timeout or DEFAULT_TIMEOUT)
  
  if timeout > 19:
    print 'status err timeout argument (%s) must be <= 19' % (timeout)
    sys.exit(1)
  
  if not re.match(IPV4_RE, ip_address) and not re.match(IPV6_RE, ip_address):
    print 'status err Invalid address: %s' % (ip_address)
    sys.exit(1)
  
  main(ip_address, str(packet_count), str(timeout))

########NEW FILE########
__FILENAME__ = log_freshness
#!/usr/bin/env python
#
# License: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
import sys, os, time

DEFAULT_AGE=600

def check_logs(*logs):
  out = []
  total = 0
  status = 'ok'
  msg = 'everything looks good'
  n = time.time()
  for l in logs:
    if isinstance(l, (list, tuple)):
      limit, l = l
    else:
      limit = DEFAULT_AGE
    try:
      s = os.stat(l)
    except Exception:
      status = 'err'
      msg = "file not found '%s'" % l
    else:
      diff = n - (s.st_mtime)
      msg = 'everything looks good, modified %d seconds ago' % diff
      if diff > limit:
        status = 'err'
        msg = '%s not modified in %d seconds' % (l, diff)

  out.insert(0, "status %s %s" % (status, msg))
  print '\n'.join(out)

if len(sys.argv) < 2:
  sys.exit('Usage: %s <log file to check>' % sys.argv[0])

if not os.path.exists(sys.argv[1]):
  sys.exit('status err file %s not found' % (sys.argv[1]))
else:
  check_logs(sys.argv[1])

########NEW FILE########
__FILENAME__ = mdadm_check
#!/usr/bin/python
# CloudKick Plugin to check the status of any
# mdadm devices on a server.
#
# Copyright (C) 2011 James Bair <james.d.bair@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import commands
import os
import re
import stat
import sys

def systemCommand(command):
    """
    Wrapper for executing a system command. Reports error to CloudKick
    as well as to standard error.
    """

    commStatus, commOut = commands.getstatusoutput(command)
    # If our command fails, abort entirely and notify CloudKick
    if commStatus != 0:
        sys.stderr.write('Error: Failure when executing the following ')
        sys.stderr.write("command: '%s'\n" % (command,))
        sys.stderr.write("Exit status: %d\n" % (commStatus,))
        sys.stderr.write("Output: %s\n\n" % (commOut,))
        sys.stderr.write('status err System command failure: ')
        sys.stderr.write('%s\n' % (command,))
        sys.exit(1)
    # If we get a 0 exit code, all is well. Return the data.
    else:
        return commOut

def which(program):
    """
    Used to find a program in the system's PATH
    Shamelessly borrowed from stackoverflow here:
    http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
    """

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def findMdDevices():
    """
    Finds all /dev/md* devices on the system.
    """

    results = []
    devPath = '/dev/'
    validation = devPath + 'md'
    for device in os.listdir(devPath):
        fullPath = devPath + device
        if validation not in fullPath:
            continue
        mode = os.stat(fullPath).st_mode
        if stat.S_ISBLK(mode):
            results.append(fullPath)

    # In case we have no /dev/md* devices
    if results == []:
        results = None

    return results

def makeMetric(ourName, ourValue, gauge=False):
    """
    Build a metric string per the documentation here:
    https://support.cloudkick.com/Creating_a_plugin
    """

    # Find our type
    ourType = type(ourValue)

    # Check if it's a string, int or float.
    if ourType not in ( str, int, float ):
        msg = 'status err Invalid value passed to makeMetric. Exiting.\n'
        sys.stderr.write(msg)
        sys.exit(1)

    # Set to gauge if needed, otherwise change our object to it's name.
    if gauge and ourType is int:
        ourType = 'gauge'
    # CloudKick wants string instead of str
    elif ourType is str:
        ourType = 'string'
    else:
        ourType = ourType.__name__

    # Cannot have spaces in our name, so replace_with_underscores.
    ourName = ourName.replace(' ', '_')

    # Send our metric.
    return 'metric %s %s %s\n' % (ourName, ourType, ourValue)


def main():
    """
    Main function for mdadm_check.py
    """

    # Make sure mdadm is installed
    prog = 'mdadm'
    if not which(prog):
        msg = 'status warn %s is not installed on this system.\n' % (prog,)
        sys.stdout.write(msg)
        sys.exit(0)

    # Find our devices; exit if none found.
    devices = findMdDevices()
    if not devices:
        msg = 'status warn No mdadm devices found on this system.\n'
        sys.stdout.write(msg)
        sys.exit(0)

    # Used in reporting
    devNum = len(devices)

    # Create a dict for each device
    comp = re.compile('^\s+(\w+\s*\w*)\s+\:\s+(.*)\s*$', re.MULTILINE)
    devStats = {}
    safeStates = ( 'clean', 'active' )
    for device in devices:
        raidInfo = systemCommand('mdadm --detail %s' % (device,))
        results = dict(comp.findall(raidInfo))

        # I have no idea why, but state holds a trailing space.
        # I just strip them all. Equality for all states!
        # Also, while we are here, we try to change them from
        # a string over to a int or a float.
        for result in results:
            results[result] = results[result].strip()
            # Try an integer first
            try:
                results[result] = int(results[result])
            except:
                # Then try floating point
                try:
                    results[result] = float(results[result])
                except:
                    pass
        # Check for failed arrays
        state = results['State']
        if state not in safeStates:
            msg = "status warn Array %s is in a '%s' state.\n" % (device, state) 
            sys.stdout.write(msg)
            sys.exit(1)
        devStats[device] = results

    # It's the little things.
    if devNum == 1:
        devStr = 'device'
    else:
        devStr = 'devices'

    # Build our metrics
    msg = ''
    for device in devStats:    
        devName = device.split('/')[-1] + '_'
        for stat in devStats[device]: 
            ourName = devName + stat
            ourValue = devStats[device][stat]
            msg += makeMetric(ourName, ourValue)

    # Send the all clear
    msg += "status ok Verified the following %d %s in a clean state: %s\n" % (devNum, devStr, ' '.join(devices))
    sys.stdout.write(msg)
    sys.exit(0)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = mysql_stats
#!/usr/bin/env python
#
# License: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# By default, MySQL does not allow root to run mysqladmin with no password.
# To get this script working, create /root/.my.cnf and put the following lines 
# in it (sans # signs)...
#
#[client]
#user = a_valid_mysql_user
#password = a_secret_password_1234
#host = localhost
#
# ...filling in your values for the user and password. Be sure to chmod .my.cnf
# to 600. You don't want other users to be able to read the username and 
# password.

import commands
import sys

metric_types = {
                "threads": "int",
                "questions": "gauge",
                "slow_queries": "gauge",
                "opens": "gauge",
                "flush_tables": "gauge",
                "open_tables": "int",
                "queries_per_second_avg": "float",
                }

(status, output) = commands.getstatusoutput("su -c \"mysqladmin status\"")

if status != 0:
  print "status err Error running mysqladmin status: %s" % output
  sys.exit(status)

print "status ok mysqladmin success"

pairs = output.split("  ")

for pair in pairs:
  (key, value) = pair.split(": ")
  key = key.lower().replace(" ", "_")

  if metric_types.get(key):
    print "metric %s %s %s" % (key, metric_types[key], value)

########NEW FILE########
__FILENAME__ = node_statuses
#!/usr/bin/env python

'''
Node statuses: grabs node statuses from the Cloudkick API, then returns metrics on how many have checks in good/warning/error state.
'''

from oauth import oauth
import urllib
try:
    import simplejson as json
except ImportError:
    import json

# TODO: automatically read these from /etc/cloudkick.conf
OAUTH_KEY    = 'xxxxxxxxxxxxxxxx'
OAUTH_SECRET = 'xxxxxxxxxxxxxxxx'

FAILURE_THRESHOLD = 0.5 # fraction of nodes that must be in bad state for this check to fail
NODE_QUERY = 'tag:cassandra tag:prod'

# You probably never need to change these
API_SERVER = 'api.cloudkick.com'
API_VERSION = '2.0'
BASE_URL = 'https://%s/%s/' % (API_SERVER, API_VERSION)

# Enabling debug will break this script's functionality as a plugin
DEBUG = False

def oauth_request(url, method, parameters):
    signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
    consumer = oauth.OAuthConsumer(OAUTH_KEY, OAUTH_SECRET)

    oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer,
                                                               http_url=url,
                                                               http_method=method,
                                                               parameters=parameters)
    oauth_request.sign_request(signature_method, consumer, None)
    url = oauth_request.to_url()
    if DEBUG: print 'url:', url

    request = urllib.urlopen(url)
    response = request.read()
    if DEBUG: print 'response:', response
    return response

def get_node_ids(query):
    node_ids = []

    response = oauth_request(BASE_URL + 'nodes', 'GET', {'query': query})

    node_json = json.loads(response)
    if not node_json:
        raise Exception('Query \"%s\" matches no nodes' % query)
    for node in node_json.values()[0]:
        node_ids.append(str(node['id']))
    return node_ids

def get_statuses(node_ids):
    statuses = []
    for node_id in node_ids:
        response = oauth_request(BASE_URL + 'status/nodes', 'GET', {'node_ids': node_id})
        status_json = json.loads(response)
        statuses.append((node_id, status_json.items()[0][1]['overall_check_statuses']))
    return statuses


node_ids = get_node_ids(NODE_QUERY)
if DEBUG: print 'node ids:', node_ids

statuses = get_statuses(node_ids)

totals = {}
for node_id, status in statuses:
    if totals.get(status) == None:
        totals[status] = 1
    else:
        totals[status] += 1

for status, total in totals.items():
    print 'metric %s_total int %s' % (status, total)

total_bad = totals.get('Error', 0) + totals.get('Warning', 0)
total_ok = totals.get('Ok', 0)
total_nodes = total_bad + total_ok
failure_ratio = total_bad / float(total_nodes)
print 'metric failure_ratio float %s' % failure_ratio

overall_status = 'err'
if failure_ratio < FAILURE_THRESHOLD:
    overall_status = 'ok'

print 'status %s %s bad, %s ok out of %s nodes' % (overall_status, total_bad, total_ok, total_nodes)

########NEW FILE########
__FILENAME__ = open_files
#!/usr/bin/env python
"""
Cloudkick open files plugin
Developed by Daniel Benamy at WNYC
Based on the Varnish plugin developed by Christopher Groskopf for The Chicago
Tribune News Applications Team

Source released under the MIT license.

Description:

Determines how many files a user has open using lsof.

Error reporting:

Outputs an error if a user wasn't specified as an argument or if lsof didn't
execute properly.

Warn reporting:

Never outputs a warning.
"""

from subprocess import Popen, PIPE
import sys
import time

if len(sys.argv) == 1:
    print 'status err User must be specified as a command line argument.'
    sys.exit()
user = sys.argv[1]

# If I take out this line, result winds up as None when run by cloudkick-agent
# but not when run manually. What the hell???!!!
f = open('/tmp/some-junk-so-the-open-files-check-works', 'w')

proc = Popen(['lsof', '-u', user, '-F', 'f'], stdout=PIPE)
result = proc.communicate()[0]
if not result:
    print 'status err lsof failed to run.'
    sys.exit()

lines = result.split('\n')
fds = filter(lambda line: line.startswith('f'), lines)

print 'status ok Got open file count.'
print 'metric open_files int %d' % len(fds)

########NEW FILE########
__FILENAME__ = postresql_stats
#!/usr/bin/env python
#
# Cloudkick plugin for monitoring PostgreSQL server status.
#
# Author: Steve Hoffmann
#
# Requirements:
# - Python PostgreSQL adapter (http://initd.org/psycopg/)
#
# Plugin arguments:
# 1. database name (default = postgres)
# 2. user (default = postgres)
# 3. hostname (default = localhost)
# 4. password (default = None)
#

DEFAULT_DATABASE = 'postgres'
DEFAULT_USER = 'postgres'
DEFAULT_HOST = 'localhost'
DEFAULT_PASSWORD = None

import sys
import commands
import warnings
import psycopg2

warnings.filterwarnings('ignore', category = DeprecationWarning)

def open_db(database, user, host = None, password = None):
  dsn = "dbname=%s user=%s" % (database, user)

  if host:
    dsn += ' host=%s' % (host)

  if password:
    dsn += ' password=%s' % (password)

  try:
    return psycopg2.connect(dsn)
  except psycopg2.OperationalError, e:
    print 'status err %s' % (e.message[:48].strip())
    sys.exit(1)

def retrieve_metrics(database, user, host, password):
  conn = open_db(database, user, host, password)
  cur = conn.cursor()

  stats = dict()

  cur.execute("SELECT datname, count(1) FROM pg_stat_activity GROUP BY datname");
  for row in cur:
     stats['conns_' + row[0]] = ('int', row[1])

  cur.execute("SELECT datname, count(1) FROM pg_stat_activity WHERE current_query != '<IDLE>'"
              " GROUP BY datname")
  for row in cur:
     stats['active_queries_' + row[0]] = ('int', row[1])

  cur.execute("SELECT datname, count(1) FROM pg_stat_activity WHERE waiting=true GROUP BY datname")
  for row in cur:
     stats['waiting_queries_' + row[0]] = ('int', row[1])

  cur.execute("SELECT checkpoints_timed, checkpoints_req, buffers_alloc FROM pg_stat_bgwriter")
  row = cur.fetchone()
  stats['expected_checkpoints'] = ('gauge', row[0])
  stats['actual_checkpoints'] = ('gauge', row[1])
  stats['buffers_alloc'] = ('gauge', row[2])

  int_cols = "xact_commit", "xact_rollback", "blks_read", "tup_fetched","tup_inserted", "tup_updated", \
             "tup_deleted"
  cur.execute("SELECT datname, " + ', ' . join(int_cols) + ", (blks_read - blks_hit) / (blks_read+0.000001)"
              " AS blk_miss_pct FROM pg_stat_database")

  for row in cur:
     datname = row[0]
     colno = 1
     for key in int_cols:
       stats[datname + '_' + key] = ('gauge', row[colno])
       colno += 1
     if 0 <= row[colno] <= 1:
       stats[datname + '_blk_miss_pct'] = ('float', row[colno])

  cur.close()
  conn.close()

  return stats

def print_metrics(metrics):
  print "status ok postgresql_stats success"
  for (key, stat) in metrics.iteritems():
     print "metric %s %s %s" % (key, stat[0], stat[1])

def main():
  arg_len = len(sys.argv)

  if arg_len >= 2:
    database = sys.argv[1]
  else:
    database = DEFAULT_DATABASE

  if arg_len >= 3:
    user = sys.argv[2]
  else:
    user = DEFAULT_USER

  if arg_len >= 4:
    host = sys.argv[3]
  else:
    host = DEFAULT_HOST

  if arg_len >= 5:
    password = sys.argv[4]
  else:
    password = DEFAULT_PASSWORD

  metrics = retrieve_metrics(database, user, host, password)
  print_metrics(metrics)

main()

########NEW FILE########
__FILENAME__ = rabbitmq
#!/usr/bin/env python
#
# License: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Cloudkick plugin for monitoring a RabbitMQ stats.
#
# Example usage (arguments which you pass in to the plugin the Cloudkick
#                dashboard):
#
# Monitor queue "bg_jobs" memory usage, number of consumers and number of
# messages:
#
# --action list_queues --queue bg_jobs --parameters memory,consumers,messages
#
# Monitor exchange "amqp.direct" type, durability and auto_delete value
#
# --action list_exchanges --exchange amqp.direct --parameters type,durable,auto_delete

import re
import sys
import subprocess
import optparse

METRIC_TYPES = {
  'list_queues': {
    'name': 'string',
    'durable': 'string',
    'auto_delete': 'string',
    'arguments': 'string',
    'pid': 'int',
    'owner_pid': 'int',
    'messages_ready': 'int',
    'messages_unacknowledged': 'int',
    'messages': 'int',
    'consumers': 'int',
    'memory': 'int'
  },

  'list_exchanges': {
    'name': 'string',
    'type': 'string',
    'durable': 'string',
    'auto_delete': 'string',
    'internal': 'string',
    'argument': 'string'
  }
}

def retrieve_stats(vhost, action, queue, exchange, parameters,
                   rabbitmqctl_path):
  value = queue or exchange
  command = [ rabbitmqctl_path, action, '-p', vhost ]
  parameters = parameters.split(',')

  parameters = [ p.lower() for p in parameters \
                 if p.lower() in METRIC_TYPES[action].keys() ]

  command.extend( [ 'name' ] + parameters)
  process1 = subprocess.Popen(command, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
  process2 = subprocess.Popen([ 'grep', value ], stdin=process1.stdout,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
  process1.stdout.close()
  stdout, stderr = process2.communicate()

  if stderr:
    return None, stderr

  stdout = stdout.split('\n')
  stdout = stdout[0]

  if not stdout:
    return None, 'Empty output'

  return parse_stats( [ 'name' ] + parameters, stdout), None

def parse_stats(parameters, data):
  values = re.split('\s+', data)

  stats = {}
  for index, parameter in enumerate(parameters):
    stats[parameter] = values[index]

  return stats

def print_metrics(action, metrics):
  for key, value in metrics.iteritems():
    metric_type = METRIC_TYPES[action].get(key, None)

    if not metric_type:
      continue

    print 'metric %s %s %s' % (key, metric_type, value)

if __name__ == '__main__':
  parser = optparse.OptionParser()
  parser.add_option('--path', action='store', dest='rabbitmqctl_path',
                    default='rabbitmqctl',
                    help='Path to the rabbitmqctl binary (optional)')
  parser.add_option('--action', action='store', dest='action',
                    help='Action (list_queues or list_exchanges)')
  parser.add_option('--vhost', action='store', dest='vhost', default='/',
                    help='Vhost (optional)')
  parser.add_option('--queue', action='store', dest='queue',
                    help='Queue name')
  parser.add_option('--exchange', action='store', dest='exchange',
                    help='Exchange name')
  parser.add_option('--parameters', action='store', dest='parameters',
                    default='messages',
                    help='Comma separated list of parameters to retrieve (default = messages)')
  parser.add_option('--queue-length', type='int', action='store', dest='length',
                    help='Max messages in the queue before alert')

  (options, args) = parser.parse_args(sys.argv)

  rabbitmqctl_path = options.rabbitmqctl_path
  action = getattr(options, 'action', None)
  vhost = options.vhost
  queue = getattr(options, 'queue', None)
  exchange = getattr(options, 'exchange', None)
  parameters = options.parameters
  length = getattr(options, 'length', None)

  if not action:
    print 'status err Missing required argument: action'
    sys.exit(1)

  if action == 'list_queues' and not queue:
    print 'status err Missing required argument: queue'
    sys.exit(1)
  elif action == 'list_exchanges' and not exchange:
    print 'status err Missing required argument: exchange'
    sys.exit(1)

  if action not in METRIC_TYPES.keys():
    print 'status err Invalid action: %s' % (action)
    sys.exit(1)

  if not parameters:
    print 'status err Missing required argument: parameters'
    sys.exit(1)

  metrics, error = retrieve_stats(vhost, action, queue, exchange,
                                  parameters, rabbitmqctl_path)

  if error:
    print 'status err %s' % (error)
    sys.exit(1)
  if length:
    if int(metrics['messages']) > length:
      print 'status err Message queue %s at %d and above threshold of %d' % (
            queue, int(metrics['messages']), length)
      sys.exit(1)
  print 'status ok metrics successfully retrieved'
  print_metrics(action, metrics)

########NEW FILE########
__FILENAME__ = raid_check
#!/usr/bin/python
# CloudKick Plugin to check the status of any
# and all RAID devices on a server. Looks for
# degraded/broken arrays.
#
# Supported/Tested Devices:
# 3ware 7506
#
# Contribs welcome! If you have a RAID device you want supported,
# feel free to add support or email me and I'll be glad to add support.
# I wrote this plugin a bit "overkill" specifically to be able to
# add support for other cards/vendors easily.
#
# Copyright (C) 2011 James Bair <james.d.bair@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import commands
import re
import sys

def systemCommand(command):
    """
    Wrapper for executing a system command. Reports error to CloudKick
    as well as to standard error.
    """

    commStatus, commOut = commands.getstatusoutput(command)
    # If our command fails, abort entirely and notify CloudKick
    if commStatus != 0:
        sys.stderr.write('Error: Failure when executing the following ')
        sys.stderr.write("command: '%s'\n" % (command,))
        sys.stderr.write("Exit status: %d\n" % (commStatus,))
        sys.stderr.write("Output: %s\n\n" % (commOut,))
        sys.stderr.write('status err System command failure: ')
        sys.stderr.write('%s\n' % (command,))
        sys.exit(1)
    # If we get a 0 exit code, all is well. Return the data.
    else:
        return commOut

def ourRaidVendors():
    """
    Find if the server has RAID at all.
    If it does, return our types (lsi or 3ware).
    """

    adapters = []
    results = []
    # Put spaces around vendors to avoid accidental detection.
    vendors = (' 3ware ',)

    # Pull our info from lspci
    lspciData = systemCommand('lspci')
    for line in lspciData.split('\n'):
        if 'RAID' in line:
            adapters.append(line)

    # If we find no RAID, we are done.
    if adapters == []:
        return None

    # Find out which vendors we have
    # RAID with
    for adapter in adapters:
        for vendor in vendors:
            # Don't want double vendor entries
            if vendor in results:
                continue
            # Add our vendor in, without the spaces
            if vendor in adapter:
                results.append(vendor.strip())

    # In case we find no vendors
    if results == []:
        return None

    # Check if we have the ability to audit 3ware controllers
    # This should exit cleanly if all is well. Run outside of systemCommand()
    # so we can return a specific error message.
    if '3ware' in results:
        commStatus, commOut = commands.getstatusoutput('tw_cli show')
        if commStatus != 0:
            sys.stderr.write('status err Missing required ')
            sys.stderr.write('3ware RAID utility "tw_cli".\n')
            sys.exit(1)

    return results

def get3wareControllers():
    """
    Find all 3ware controllers on the system.
    """

    # All 3ware controllers should be c0, c1, c2 etc.
    #Ctl   Model        (V)Ports  Drives   Units   NotOpt  RRate   VRate  BBU
    #------------------------------------------------------------------------
    #c2    7506-4LP     4         4        1       0       2       -      -
    raidData = systemCommand('tw_cli show')
    results = re.findall('(c[0-9*]) ', raidData)
    return results

def get3wareStatus(controller):
    """
    Check the status of all RAID arrays on the given controller.
    """

    # Looking for the OK portion of this line:
    #Unit  UnitType  Status         %RCmpl  %V/I/M  Stripe  Size(GB)  Cache  AVrfy
    #------------------------------------------------------------------------------
    #u0    RAID-5    OK             -       -       64K     569.766   W      -
    raidData = systemCommand('tw_cli /%s show' % (controller,))
    results = re.findall('u[0-9]\s*RAID-[0-9]*\s*(\w*)', raidData)
    return results

def main():
    """
    Main function for raid_check.py
    """

    # Supported vendors - would love to extend this!
    supportedVendors = ('3ware',)

    # See if we have any RAID at all
    vendors = ourRaidVendors()

    # Make sure we have what we need
    if vendors is None:
        sys.stdout.write('status warn No RAID devices found on this system.\n')
        sys.exit(0)
    # If we have RAID, let's see if everything is okay
    else:
        # Validate it's supported
        for vendor in vendors:
            if vendor not in supportedVendors:
                sys.stdout.write("status warn Unsupported RAID vendor ")
                sys.stdout.write("'%s' found.\n" % (vendor,))
                sys.exit(0)

            # 3Ware support. Works with lists of controllers.
            if vendor == '3ware':
                controllers = get3wareControllers()
                for controller in controllers:
                    # Find the statuses
                    statuses = get3wareStatus(controller)
                    for status in statuses:
                        if status == 'OK':
                            # We print an all good if no exceptions are caught
                            # on any arrays on any controllers.
                            continue
                        else:
                            sys.stdout.write('status warn ')
                            sys.stdout.write("Failed status ")
                            sys.stdout.write("%s found on " % (status,))
                            sys.stdout.write("controller %s\n" % (controller,))
                            sys.exit(0)

            # If we are here, it's listed as supported in main(),
            # but no logic is in place.
            else:
                sys.stderr.write("status err Supported vendor ")
                sys.stderr.write("'%s' missing support.\n" % (vendor,))
                sys.exit(1)

            # If all of our controllers and RAID arrays pass without fail
            # we are good to go!
            contNum = len(controllers)
            if contNum == 1:
                contStr = 'controller'
            else:
                contStr = 'controllers'

            sys.stdout.write('status ok ')
            sys.stdout.write('Checked %d %s: ' % (contNum, contStr))
            sys.stdout.write(', '.join(controllers))
            sys.stdout.write('\n')
            sys.exit(0)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rds_stats
#!/usr/bin/env python

# Cloudkick plugin that monitors CloudWatch stats for RDS instances.
#
# Requirements:
# - Boto (http://boto.s3.amazonaws.com/index.html)
#
# Plugin arguments:
# 1. DBInstanceIdentifier
# 2. AWS Access Key
# 3. AWS Secret Access Key
#
# Author: Phil Kates
# Copyright (c) 2010 Phil Kates <me@philkates.com>
#
# MIT License:
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import datetime
import sys
from optparse import OptionParser
from boto.ec2.cloudwatch import CloudWatchConnection

### Arguments
parser = OptionParser()
parser.add_option("-i", "--instance-id", dest="instance_id",
                help="DBInstanceIdentifier")
parser.add_option("-a", "--access-key", dest="access_key",
                help="AWS Access Key")
parser.add_option("-k", "--secret-key", dest="secret_key",
                help="AWS Secret Access Key")

(options, args) = parser.parse_args()

if (options.instance_id == None):
    parser.error("-i DBInstanceIdentifier is required")
if (options.access_key == None):
    parser.error("-a AWS Access Key is required")
if (options.secret_key == None):
    parser.error("-k AWS Secret Key is required")
###

### Real code
metrics = {"CPUUtilization":{"type":"float", "value":None},
    "ReadLatency":{"type":"float", "value":None},
    "DatabaseConnections":{"type":"int", "value":None},
    "FreeableMemory":{"type":"float", "value":None},
    "ReadIOPS":{"type":"int", "value":None},
    "WriteLatency":{"type":"float", "value":None},
    "WriteThroughput":{"type":"float", "value":None},
    "WriteIOPS":{"type":"int", "value":None},
    "SwapUsage":{"type":"float", "value":None},
    "ReadThroughput":{"type":"float", "value":None},
    "FreeStorageSpace":{"type":"float", "value":None}}
    
end = datetime.datetime.now()
start = end - datetime.timedelta(minutes=5)

conn = CloudWatchConnection(options.access_key, options.secret_key)
for k,vh in metrics.items():
    try:
        res = conn.get_metric_statistics(60, start, end, k, "AWS/RDS", "Average", {"DBInstanceIdentifier": options.instance_id})
    except Exception, e:
        print "status err Error running rds_stats: %s" % e.error_message
        sys.exit(1)
    average = res[-1]["Average"] # last item in result set
    if (k == "FreeStorageSpace" or k == "FreeableMemory"):
        average = average / 1024.0**3.0
    if vh["type"] == "float":
        metrics[k]["value"] = "%.4f" % average
    if vh["type"] == "int":
        metrics[k]["value"] = "%i" % average

# Iterating through the Array twice seems inelegant, but I don't know Python 
# well enough to do it the right way.
print "status ok rds success"
for k,vh in metrics.items():
    print "metric %s %s %s" % (k, vh["type"], vh["value"])
########NEW FILE########
__FILENAME__ = redis_stats
#!/usr/bin/env python

# Redis monitoring for Cloudkick
#
# Requirements:
#  1. redis-py (https://github.com/andymccurdy/redis-py)
#  2. Tested on redis 2.1.4
#
# Arguments:
#  --host   Redis host (defaults to localhost)
#  --port   Redis port (defaults to 6379)
#
# To install, copy script to /usr/lib/cloudkick-agent/plugins/
#
# Copyright (c) 2011 Brad Jasper <bjasper@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# 

import re
import optparse

from redis import Redis
from redis.exceptions import RedisError

parser = optparse.OptionParser()
parser.add_option('--host', help='Redis host', default='localhost')
parser.add_option('--port', help='Redis port', type='int', default=6379)
(options, args) = parser.parse_args()

dbregex = re.compile(r'db\d+')
metrics = {
    'blocked_clients': 'int',
    'changes_since_last_save': 'int',
    'connected_clients': 'int',
    'connected_slaves': 'int',
    'expired_keys': 'int',
    'used_memory': 'int',
    'pubsub_channels': 'int',
    'pubsub_patterns': 'int',

    'mem_fragmentation_ratio': 'float',
    'used_cpu_sys': 'float',
    'used_cpu_user': 'float',
    'used_cpu_sys_childrens': 'float',
    'used_cpu_user_childrens': 'float',

    'last_save_time': 'gauge',
    'total_commands_processed': 'gauge',
    'total_connections_received': 'gauge',
    'uptime_in_seconds': 'gauge'
}

try:
    db = Redis(host=options.host, port=options.port)
    info = db.info()
except RedisError, msg:
    print 'status err Error from Redis: %s' % msg
else:

    print 'status ok redis success'

    for metric, _type in metrics.iteritems():
        print 'metric %s %s %s' % (metric, _type, info.get(metric))

    # We also want to output the dbindex-specific metrics
    # Redis INFO returns these as
    #   'db0': {'expires': 0, 'keys': 935},
    #   'db1': {'expires': 4, 'keys': 100},
    #
    # These should be converted to db0_expires, db0_keys, etc...
    for key in info:
        if dbregex.match(key):
            for metric, value in info[key].iteritems():
                print 'metric %s_%s int %s' % (key, metric, value)

########NEW FILE########
__FILENAME__ = solr_status
#!/usr/bin/env python
#
# License: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
# Cloudkick plugin for monitoring a Solr core.
#
# Plugin takes the following arguments:
#
# 1 - URL to the Solr core stats.jsp page,
# 2. realm,
# 3. username,
# 4. password
#
# Arguments 2, 3 and 4 are optional and should only be specified if your Solr page is protected with a HTTP basic auth.
#

import sys
import socket
import urllib2
import xml.dom.minidom as minidom

DEFAULT_URL = 'http://localhost:8983/solr/core0/admin/stats.jsp'
DEFAULT_TIMEOUT = 4

METRICS = {
              'org.apache.solr.search.SolrIndexSearcher': ['numDocs', 'maxDocs'],
              'org.apache.solr.handler.ReplicationHandler': ['indexSize'],
              'org.apache.solr.handler.XmlUpdateRequestHandler': ['requests', 'errors', 'timeouts'],
}

METRIC_MAPPINGS = {
                  'numDocs': {'type': 'int', 'display_name': 'documents_number'},
                  'maxDocs': {'type': 'int', 'display_name': 'maximum_documents'},
                  'indexSize': {'type': 'float', 'display_name': 'index_size'},
                  'requests': {'type': 'gauge', 'display_name': 'update_handler_requests'},
                  'errors':  {'type': 'gauge', 'display_name': 'update_handler_errors'},
                  'timeouts': {'type': 'gauge', 'display_name': 'update_handler_timeouts'}
}

def main():
  arg_len = len(sys.argv)

  if arg_len >= 2:
    solr_url = sys.argv[1]
  else:
    solr_url = DEFAULT_URL

  if arg_len == 5:
    realm = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]

    auth_handler = urllib2.HTTPBasicAuthHandler()
    auth_handler.add_password(realm = realm, uri = solr_url, user = username, passwd = password)
    opener = urllib2.build_opener(auth_handler)

    urllib2.install_opener(opener)

  socket.setdefaulttimeout(DEFAULT_TIMEOUT)
  try:
    response = urllib2.urlopen(solr_url)
    body = response.read()
  except  urllib2.HTTPError, e:
    print 'status err Failed to retrieve stats - status code: %s' % (e.code)
    sys.exit(1)
  except (urllib2.URLError, Exception), e:
    print 'status err Failed to retrieve stats: %s' % (str(e)[:23])
    sys.exit(1)

  try:
    metric_values = parse_response(body)
  except Exception, e:
    print 'status err Failed to parse metrics: %s' % (str(e)[:23])
    sys.exit(1)

  if not metric_values:
    print 'status err Failed to retrieve metrics %s' % (', ' .join(METRIC_MAPPINGS.keys())[:21])
    sys.exit(1)

  print_METRICS(metric_values)

def parse_response(response):
  root = minidom.parseString(response)
  stat_elements = root.getElementsByTagName('stat');

  metric_values = {}
  for element in stat_elements:
    class_name = element.parentNode.parentNode.getElementsByTagName('class')[0].childNodes[0].data.strip()

    if class_name in METRICS.keys():
      child_nodes = element.childNodes
      if child_nodes and child_nodes[0].nodeType == element.TEXT_NODE:
        name = element.getAttribute('name')
        value = child_nodes[0].data.strip()

        if name in METRICS[class_name]:
          metric_values[name] = string_value_to_mb(value)

  return metric_values

def print_METRICS(metric_values):
  print 'status ok successfully retrieved metrics'
  for key, value in metric_values.items():
    type = METRIC_MAPPINGS.get(key).get('type')
    display_name = METRIC_MAPPINGS.get(key).get('display_name')
    print 'metric %s %s %s' % (display_name, METRIC_MAPPINGS.get(key).get('type'), value)

def string_value_to_mb(value):
  units = [('b', (1 / 1024.0 / 1024.0)), ('kb', (1 / 1024.0)), ('mb', 1), ('gb', 1024), ('tb', 1024 * 1024)]

  value = value.lower()
  for (unit, factor) in units:
    if value.find(' %s' % (unit)) != -1:
      value = value.replace(unit, '').strip()
      value = int(float(value))
      value = value * factor
      break

  return value

main()

########NEW FILE########
__FILENAME__ = sqs
#!/usr/bin/env python
"""
Count the approximate number of messaages in your Amazon SQS queue(s).
Requires the boto python library (http://code.google.com/p/boto/).

Set the aws_key and aws_secret values before using the plugin.

Usage:
  sqs.py [minimum_count] [maximum_count]

LICENSE: http://www.opensource.org/licenses/mit-license.php
AUTHOR:  Caleb Groom <http://github.com/calebgroom>
"""

from boto.sqs.connection import SQSConnection
from boto.exception import SQSError
import sys

MAX_MESSAGES = 100
MIN_MESSAGES = 0
aws_key = ''
aws_secret = ''

# The alerting thresholds can be overridden via command line arguments
limits = [MIN_MESSAGES, MAX_MESSAGES]
for i in [2,3]:
    if len(sys.argv) >= i:
      try:
          limits[i-2] = int(sys.argv[i-1])
      except ValueError:
          print 'status err argument "%s" is not a valid integer' % sys.argv[i-1]
          sys.exit(1)

try:
    conn = SQSConnection(aws_key, aws_secret)
    queues = conn.get_all_queues()
    error_queues = []
    total = 0
    for queue in queues:
        count = queue.count()
        total += count
        if count < limits[0] or count > limits[1]:
            error_queues.append(queue.name)
        print 'metric %s int %d' % (queue.name, count)

    if len(error_queues) == 0:
        print 'status ok %d messages in all queues' % total
    else:
        s = '/'.join(error_queues)
        print 'status err %s contains an unexpected number of messages' % s

except SQSError as e:
    print 'status err SQS error:', e.reason  
except:
    print 'status err Unhandled error'

########NEW FILE########
__FILENAME__ = turkey
#!/usr/bin/python
#
# License: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
#                  _<_< > 
#      ____________/_/ _/
#    _/ turkey.py _/  /_
#   / custom    /     \ >
#  (   plugin   \_____//
#   \________________/ 
# 
#  First used with a Backwoods smoker to monitor
#  the temp of a turkey during cook time. You will
#  need to adjust the temp thresholds to match your
#  specific cooking requirements. Enjoy! 
#
#  ~Team Cloudkick, Thanksgiving 2010

import time
import struct
import sys

ldusb = file("/dev/ldusb0")

time.sleep(0.5)

# This reads the payload off of the Go!Temp USB drive
pkt = ldusb.read(8)
parsed_pkt = list(struct.unpack("<BBHHH", pkt))
num_samples = parsed_pkt.pop(0)
seqno = parsed_pkt.pop(0)
for sample in range(num_samples):
  c =  parsed_pkt[sample]/128.0

  # Convert to Fahrenheit since this is for Thanksgiving
  f = 9.0 / 5.0 * c + 32

# This is the actual alerting threshold,
# tweak as needed
if f > 200 and f < 300:
  status = 'ok'
else:
  status = 'err'
print 'status %s temp at %d' % (status, f)
print 'metric temp int %d' % (f)

########NEW FILE########
__FILENAME__ = users_logged_in
#!/usr/bin/python -tt
# CloudKick Plugin to see who's logged into the system.
# 
# By default, assumes that no one should be logged into the system.
# 
# Can specify --min and --max to adjust the acceptable range.
# If number of users outside of the acceptable range, a warning
# is raised. If inside the acceptable range, an ok status is raised.
#
# Copyright (C) 2011  James Bair <james.d.bair@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import commands
import sys

from optparse import OptionParser

def getUsersLoggedIn():
    """
    Find all users that are logged
    into the local system and return
    either a list or a None object.
    """

    # Best way I can find to find users logged in
    commStatus, userData = commands.getstatusoutput('who')

    # Make sure it exits gracefully
    if commStatus != 0:
        sys.stderr.write('status err Unable to execute "who" command.\n')
        sys.exit(1)

    # "who" returns an empty string if no one is logged in
    if userData == '':
        users = None
    else:
        # We're going to add each user we find to a list
        users = []
        # Split up our string by lines
        userLines = userData.split('\n')
        for line in userLines:
            # Username should be the first item on the line
            users.append(line.split()[0])

    return users

def main():
    """
    Main function for users_logged_in.py
    """

    minUsers=0
    maxUsers=0

    parser = OptionParser()

    parser.add_option("-m", "--min",
                      action="store", type="int",
                      help="Minimum number of users", metavar="N")
    parser.add_option("-M", "--max",
                      action="store", type="int",
                      help="Maximum number of users", metavar="N")

    (options, args) = parser.parse_args()

    # Overwrite default values if they exist
    # Specify "not None" since 0 will return False
    if options.min is not None:
        minUsers = options.min
    if options.max is not None:
        maxUsers = options.max

    # If only min users is passed, make them match.
    # If both are passed, then this is a user error.
    if minUsers > maxUsers:
        if options.min is not None and options.max is not None:
            msg = "Error: --min cannot exceed --max\n"
            sys.stderr.write(msg)
            sys.exit(1)
        else:
            maxUsers = minUsers

    # Find our users
    users = getUsersLoggedIn()

    # If object is None, no users logged in.
    if users is None:
        userMsg="No users logged in."
        userNum = 0
    # Anything else, we have users
    else:
        # Find out the number of users and
        #if we're saying "user" or "users"
        userNum = len(users)
        if userNum == 1:
            userWord = 'user'
        else:
            userWord = 'users'

        # Build our users logged in message.
        userMsg = "%d %s logged in: " % (userNum, userWord)
        userMsg += ", ".join(users)

        # Plugin spec limits status string to 48 chars.
        #
        # I have tested with over 100 chars and CloudKick
        # works just fine. Adjust/remove as you see fit, but
        # for the sake of being "correct", this line is here.
        userMsg = userMsg[:48]

    # Now, find out if we are in error or not
    if userNum < minUsers or userNum > maxUsers:
        statusMsg = 'status warn'
    else:
        statusMsg = 'status ok'

    # All done, build our strings and repot the data
    ourStatus = '%s %s\n' % (statusMsg, userMsg)
    # And build our number of users
    ourMetric = "metric users_logged_in int %d\n" % (userNum,)

    # All done.
    sys.stdout.write(ourStatus + ourMetric)
    sys.exit(0)

# Let's do this
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = varnish
#!/usr/bin/env python
"""
Cloudkick Varnish plugin
Developed by Christopher Groskopf for The Chicago Tribune News Applications Team
http://apps.chicagotribune.com
https://github.com/newsapps

Source released under the MIT license.

Description:

This plugin will pipe all output from the command "varnishstat -1"
up to Cloudkick.  In addition, it will store the cache_hit and cache_miss stats
in a tmp file on each execution so that it can compute a hit_rate stat, which will
also be reported to Cloudkick.

Error reporting:

This plugin will report an error only if varnishstat fails to
execute (generally this would only be the case if Varnish is not running).

Warn reporting:

This plugin will report a warning anytime that it fails to parse
varnishstat's output.

TODO:

Support custom warnings and errors when the hit_rate stat falls below a
specified threshold.
"""

from __future__ import with_statement

import os
import re
import subprocess
import sys

HIT_RATE_FILE = '/tmp/cloudkick-agent-varnish.tmp'

result = subprocess.Popen(['varnishstat', '-1'], stdout=subprocess.PIPE).communicate()[0]

if not result:
    print 'status err Varnish is not running.'
    sys.exit()

data = []
hits = None
misses = None

try:
    for r in result.split('\n'):
        if not r:
            continue

        parts = re.split('\s+', r.strip())

        data.append('metric %s int %s' % (parts[0], parts[1]))

        if parts[0] == 'cache_hit':
            hits = int(parts[1])
        elif parts[0] == 'cache_miss':
            misses = int(parts[1])

    if hits and misses:
        if os.path.exists(HIT_RATE_FILE):
            with open(HIT_RATE_FILE, 'r') as f:
                parts = f.read().split(',')
                last_hits = int(parts[0])
                last_misses = int(parts[1])

            delta_hits = hits - last_hits
            delta_misses = misses - last_misses

            if delta_misses == 0:
                hit_rate = float(1.0)
            else:
                hit_rate = float(delta_hits) / (delta_hits + delta_misses)

            data.append('metric hit_rate float %1.3f' % hit_rate)

        with open(HIT_RATE_FILE, 'w') as f:
            f.write('%i,%i' % (hits, misses))
except Exception, e:
    print 'status warn Error parsing varnishstat output (%s)' % (str(e))
    sys.exit()

print 'status ok Varnish is running.'

for d in data:
    print d

########NEW FILE########
