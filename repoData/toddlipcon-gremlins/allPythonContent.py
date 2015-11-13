__FILENAME__ = faults
#!/usr/bin/env python
#
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from gremlins import procutils, iptables
import signal
import os
import subprocess
import logging
import time

def kill_daemons(daemons, signal, restart_after):
  """Kill the given daemons with the given signal, then
  restart them after the given number of seconds.

  @param daemons: the names of the daemon (eg HRegionServer)
  @param signal: signal to kill with
  @param restart_after: number of seconds to sleep before restarting
  """
  def do():
    # First kill
    for daemon in daemons:
      pid = procutils.find_jvm(daemon)
      if pid:
        logging.info("Killing %s pid %d with signal %d" % (daemon, pid, signal))
        os.kill(pid, signal)
      else:
        logging.info("There was no %s running!" % daemon)

    logging.info("Sleeping for %d seconds" % restart_after)
    time.sleep(restart_after)

    for daemon in daemons:
      logging.info("Restarting %s" % daemon);
      procutils.start_daemon(daemon)
  return do

def pause_daemons(jvm_names, seconds):
  """
  Pause the given daemons for some period of time using SIGSTOP/SIGCONT

  @param jvm_names: the names of the class to pause: eg ["DataNode"]
  @param seconds: the number of seconds to pause for
  """
  def do():
    # Stop all daemons, record their pids
    for jvm_name in jvm_names:
      pid = procutils.find_jvm(jvm_name)
      if not pid:
        logging.warn("No pid found for %s" % jvm_name)
        continue
      logging.warn("Suspending %s pid %d for %d seconds" % (jvm_name, pid, seconds))
      os.kill(pid, signal.SIGSTOP)

    # Pause for prescribed amount of time
    time.sleep(seconds)

    # Resume them
    for jvm_name in jvm_names:
      pid = procutils.find_jvm(jvm_name)
      if pid:
        logging.warn("Resuming %s pid %d" % (jvm_name, pid))
        os.kill(pid, signal.SIGCONT)
  return do

def drop_packets_to_daemons(daemons, seconds):
  """
  Determines which TCP ports the given daemons are listening on, and sets up
  an iptables firewall rule to drop all packets to any of those ports
  for a period of time.

  @param daemons: the JVM class names of the daemons
  @param seconds: how many seconds to drop packets for
  """
  def do():
    logging.info("Going to drop packets from %s for %d seconds..." %
                 (repr(daemons), seconds))

    # Figure out what ports the daemons are listening on
    all_ports = []
    for daemon in daemons:
      pid = procutils.find_jvm(daemon)
      if not pid:
        logging.warn("Daemon %s not running!" % daemon)
        continue
      ports = procutils.get_listening_ports(pid)
      logging.info("%s is listening on ports: %s" % (daemon, repr(ports)))
      all_ports.extend(ports)

    if not all_ports:
      logging.warn("No ports found for daemons: %s. Skipping fault." % repr(daemons))
      return

    # Set up a chain to drop the packets
    chain = iptables.create_gremlin_chain(all_ports)
    logging.info("Created iptables chain: %s" % chain)
    iptables.add_user_chain_to_input_chain(chain)

    logging.info("Gremlin chain %s installed, sleeping %d seconds" % (chain, seconds))
    time.sleep(seconds)

    logging.info("Removing gremlin chain %s" % chain)
    iptables.remove_user_chain_from_input_chain(chain)
    iptables.delete_user_chain(chain)
    logging.info("Removed gremlin chain %s" % chain)
  return do

def fail_network(bastion_host, seconds, restart_daemons=None, use_flush=False):
  """
  Cuts off all network traffic for this host, save ssh to/from a given bastion host,
  for a period of time.

  @param bastion_host: a host or ip to allow ssh with, just in case
  @param seconds: how many seconds to drop packets for
  @param restart_daemons: optional list of daemon processes to restart after network is restored
  @param use_flush: optional param to issue an iptables flush rather than manually remove chains from INPUT/OUTPUT
  """
  def do():
    logging.info("Going to drop all networking (save ssh with %s) for %d seconds..." %
                 (bastion_host, seconds))
    # TODO check connectivity, or atleast DNS resolution, for bastion_host
    chains = iptables.create_gremlin_network_failure(bastion_host)
    logging.info("Created iptables chains: %s" % repr(chains))
    iptables.add_user_chain_to_input_chain(chains[0])
    iptables.add_user_chain_to_output_chain(chains[1])

    logging.info("Gremlin chains %s installed, sleeping %d seconds" % (repr(chains), seconds))
    time.sleep(seconds)

    if use_flush:
      logging.info("Using flush to remove gremlin chains")
      iptables.flush()
    else:
      logging.info("Removing gremlin chains %s" % repr(chains))
      iptables.remove_user_chain_from_input_chain(chains[0])
      iptables.remove_user_chain_from_output_chain(chains[1])
    iptables.delete_user_chain(chains[0])
    iptables.delete_user_chain(chains[1])
    logging.info("Removed gremlin chains %s" % repr(chains))
    if restart_daemons:
      logging.info("Restarting daemons: %s", repr(restart_daemons))
      for daemon in restart_daemons:
        procutils.start_daemon(daemon)
  return do

########NEW FILE########
__FILENAME__ = gremlin
#!/usr/bin/env python
#
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random
import time
from gremlins import faults, profiles
import signal
import logging
from optparse import OptionParser
import sys

LOG_FORMAT='%(asctime)s %(module)-12s %(levelname)-8s %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

def run_profile(profile):
  for trigger in profile:
    trigger.start()

  logging.info("Started profile")
  while True:
    time.sleep(1)

  for trigger in profile:
    trigger.stop()
    trigger.join()


def main():
  parser = OptionParser()
  parser.add_option("-m", "--import-module", dest="modules",
    help="module to import", metavar="MODULE", action="append")
  parser.add_option("-p", "--profile", dest="profile",
    help="fault profile to run", metavar='PROFILE')
  parser.add_option("-f", "--fault", dest="faults", action="append",
    help="faults to run", metavar='FAULT')

  (options, args) = parser.parse_args()

  things_to_do = 0
  if options.profile: things_to_do += 1
  if options.faults: things_to_do += 1

  if len(args) > 0 or things_to_do != 1:
    parser.print_help(sys.stderr)
    sys.exit(1)

  print repr(options)
  imported_modules = {}
  for m in options.modules:
    name = m.split(".")[-1]
    imported = __import__(m, {}, {}, name)
    imported_modules[name] = imported

  def eval_arg(arg):
    eval_globals = dict(globals())
    eval_globals.update(imported_modules)
    return eval(arg, eval_globals)

  if options.profile:
    run_profile(eval_arg(options.profile))
  elif options.faults:
    for fault_arg in options.faults:
      fault = eval_arg(fault_arg)
      fault()

if __name__ == "__main__":
  main()



########NEW FILE########
__FILENAME__ = hostutils
#!/usr/bin/env python
#
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from gremlins import procutils, iptables

LASTCMD = "/usr/bin/last"

def guess_remote_host():
  """
  Attempt to find the host our current user last logged in from.
  """
  user = os.environ.get("USER")
  sudo_user = os.environ.get("SUDO_USER")
  if sudo_user:
    user = sudo_user
  if user:
    last = procutils.run([LASTCMD, "-a", user, "-n", "1"]).splitlines()[0]
    return last.rpartition(' ')[2]
  else:
    return None

########NEW FILE########
__FILENAME__ = iptables
#!/usr/bin/env python
#
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
from gremlins import procutils
import time

IPTABLES="/sbin/iptables"

def list_chains():
  """Return a list of the names of all iptables chains."""
  ret = procutils.run([IPTABLES, "-L"])
  chains = re.findall(r'^Chain (\S+)', ret, re.MULTILINE)
  return chains

def create_gremlin_chain(ports_to_drop):
  """
  Create a new iptables chain that drops all packets
  to the given list of ports.

  @param ports_to_drop: list of int port numbers to drop packets to
  @returns the name of the new chain
  """
  chain_id = "gremlin_%d" % int(time.time())
  
  # Create the chain
  procutils.run([IPTABLES, "-N", chain_id])

  # Add the drop rules
  for port in ports_to_drop:
    procutils.run([IPTABLES,
      "-A", chain_id,
      "-p", "tcp",
      "--dport", str(port),
      "-j", "DROP"])
  return chain_id

def create_gremlin_network_failure(bastion_host):
  """
  Create a new iptables chain that isolates the host we're on
  from all other hosts, save a single bastion.

  @param bastion_host: a hostname or ip to still allow ssh to/from
  @returns an array containing the name of the new chains [input, output]
  """
  chain_prefix = "gremlin_%d" % int(time.time())

  # Create INPUT chain
  chain_input = "%s_INPUT" % chain_prefix
  procutils.run([IPTABLES, "-N", chain_input])

  # Add rules to allow ssh to/from bastion
  procutils.run([IPTABLES, "-A", chain_input, "-p", "tcp",
    "--source", bastion_host, "--dport", "22",
    "-m", "state", "--state", "NEW,ESTABLISHED",
    "-j", "ACCEPT"])
  procutils.run([IPTABLES, "-A", chain_input, "-p", "tcp",
    "--sport", "22",
    "-m", "state", "--state", "ESTABLISHED",
    "-j", "ACCEPT"])

  # Add rule to allow ICMP to/from bastion
  procutils.run([IPTABLES, "-A", chain_input, "-p", "icmp",
    "--source", bastion_host,
    "-j", "ACCEPT"])
  # Drop everything else
  procutils.run([IPTABLES, "-A", chain_input,
    "-j", "DROP"])

  # Create OUTPUT chain
  chain_output = "%s_OUTPUT" % chain_prefix
  procutils.run([IPTABLES, "-N", chain_output])

  # Add rules to allow ssh to/from bastion
  procutils.run([IPTABLES, "-A", chain_output, "-p", "tcp",
    "--sport", "22",
    "-m", "state", "--state", "ESTABLISHED",
    "-j", "ACCEPT"])
  procutils.run([IPTABLES, "-A", chain_output, "-p", "tcp",
    "--destination", bastion_host, "--dport", "22",
    "-m", "state", "--state", "NEW,ESTABLISHED",
    "-j", "ACCEPT"])
  # Add rule to allow ICMP to/from bastion
  procutils.run([IPTABLES, "-A", chain_output, "-p", "icmp",
    "--destination", bastion_host,
    "-j", "ACCEPT"])
  # Drop everything else
  procutils.run([IPTABLES, "-A", chain_output,
    "-j", "DROP"])

  return [chain_input, chain_output]

def add_user_chain_to_input_chain(chain_id):
  """Insert the given user chain into the system INPUT chain"""
  procutils.run([IPTABLES, "-A", "INPUT", "-j", chain_id])

def remove_user_chain_from_input_chain(chain_id):
  """Remove the given user chain from the system INPUT chain"""
  procutils.run([IPTABLES, "-D", "INPUT", "-j", chain_id])

def add_user_chain_to_output_chain(chain_id):
  """Insert the given user chain into the system OUTPUT chain"""
  procutils.run([IPTABLES, "-A", "OUTPUT", "-j", chain_id])

def remove_user_chain_from_output_chain(chain_id):
  """Remove the given user chain from the system OUTPUT chain"""
  procutils.run([IPTABLES, "-D", "OUTPUT", "-j", chain_id])

def flush(chain_id=None):
  """
  Flush iptables chains. Defaults to all chains.

  @param chain_id optionally limit flushing to given chain
  """
  if chain_id:
    procutils.run([IPTABLES, "--flush", chain_id])
  else:
    procutils.run([IPTABLES, "--flush"])

def delete_user_chain(chain_id):
  """
  Delete a user chain.

  You must remove it from the system chains before this will succeed.
  """
  procutils.run([IPTABLES, "--flush", chain_id])
  procutils.run([IPTABLES, "--delete-chain", chain_id])

def remove_gremlin_chains():
  """
  Remove any gremlin chains that are found on the system.
  """
  output_chains = map((lambda entry: entry.partition(" ")[0]), procutils.run([IPTABLES, "-L", "OUTPUT"]).splitlines()[2:])

  for chain in list_chains():
    if chain.startswith("gremlin_"):
      if chain in output_chains:
        remove_user_chain_from_output_chain(chain)
      else:
        remove_user_chain_from_input_chain(chain)
      delete_user_chain(chain)


########NEW FILE########
__FILENAME__ = metafaults
#!/usr/bin/env python
#
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random
import logging

def pick_fault(fault_weights):
  def do():
    logging.info("pick_fault triggered")
    total_weight = sum( wt for wt,fault in fault_weights )
    pick = random.random() * total_weight
    accrued = 0
    for wt, fault in fault_weights:
      accrued += wt
      if pick <= accrued:
        fault()
        return
    assert "should not get here, pick=" + pick
  return do

def maybe_fault(likelyhood, fault):
  def do():
    logging.info("maybe_fault triggered, %3.2f likelyhood" % likelyhood)
    if random.random() <= likelyhood:
      fault()
    return
  return do

########NEW FILE########
__FILENAME__ = procutils
#!/usr/bin/env python
#
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
import signal
import os
import subprocess
import logging

HBASE_HOME=os.getenv("HBASE_HOME", "/home/todd/monster-cluster/hbase")
HADOOP_HOME=os.getenv("HADOOP_HOME", "/home/todd/monster-cluster/hadoop-0.20.1+169.66")
ACCUMULO_HOME=os.getenv("ACCUMULO_HOME", "/usr/lib/accumulo")
ACCUMULO_USER =os.getenv("ACCUMULO_USER", "accumulo")
SUDO=os.getenv("SUDO", "sudo")
LSOF=os.getenv("LSOF", "lsof")
JPS=os.getenv("JPS", "jps")

START_COMMANDS = {
  'HRegionServer': [HBASE_HOME + "/bin/hbase-daemon.sh", "start", "regionserver"],
  'DataNode': [HADOOP_HOME + "/bin/hadoop-daemon.sh", "start", "datanode"],
  'Accumulo-All': [SUDO, "-n",  "-u", ACCUMULO_USER, "-i", ACCUMULO_HOME + "/bin/start-here.sh"],
}


def run(cmdv):
  """Run a command.

  Throws an exception if it has a nonzero exit code.
  Returns the output of the command.
  """
  proc = subprocess.Popen(args=cmdv, stdout=subprocess.PIPE)
  (out, err) = proc.communicate()
  if proc.returncode != 0:
    raise Exception("Bad status code: %d" % proc.returncode)
  return out


def start_daemon(daemon):
  """Start the given daemon."""
  if daemon not in START_COMMANDS:
    raise Exception("Don't know how to start a %s" % daemon)
  cmd = START_COMMANDS[daemon]
  logging.info("Starting %s: %s" % (daemon, repr(cmd)))
  ret = subprocess.call(cmd)
  if ret != 0:
    logging.warn("Ret code %d starting %s" % (ret, daemon))

def find_jvm(java_command):
  """
  Find the jvm for the given java class by running jps

  Returns the pid of this JVM, or None if it is not running.
  """
  ret = run([JPS]).split("\n")
  for line in ret:
    if not line: continue
    pid, command = line.split(' ', 1)
    if command == java_command:
      logging.info("Found %s: pid %s" % (java_command, pid))
      return int(pid)
  logging.info("Found no running %s" % java_command)
  return None

def get_listening_ports(pid):
  """Given a pid, return a list of TCP ports it is listening on."""
  ports = []
  lsof_data = run([LSOF, "-p%d" % pid, "-n", "-a", "-itcp", "-P"]).split("\n")
  # first line is a header
  del lsof_data[0]
  # Parse out the LISTEN rows
  for record in lsof_data:
    m = re.search(r'TCP\s*.+?:(\d+)\s*\(LISTEN\)', record)
    if m:
      ports.append( int(m.group(1)) )
  return ports

########NEW FILE########
__FILENAME__ = accumulo
#!/usr/bin/env python
#
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os

from gremlins import faults, metafaults, triggers, hostutils

bastion = os.getenv("GREMLINS_BASTION_HOST", hostutils.guess_remote_host())

if not bastion:
  raise Exception("GREMLINS_BASTION_HOST not set, and I couldn't guess your remote host.")

logging.info("Using %s as bastion host for network failures. You should be able to ssh from that host at all times." % bastion)

fail_node_long = faults.fail_network(bastion_host=bastion, seconds=300, restart_daemons=["Accumulo-All"], use_flush=True)
# XXX make sure this is greater than ZK heartbeats
fail_node_short = faults.fail_network(bastion_host=bastion, seconds=45, restart_daemons=["Accumulo-All"], use_flush=True)
# XXX make sure this is less than ZK heartbeats
fail_node_transient = faults.fail_network(bastion_host=bastion, seconds=10, restart_daemons=["Accumulo-All"], use_flush=True)

profile = [
  triggers.Periodic(
# How often do you want a failure? for master nodes, you should probably give enough time for recovery ~5-15 minutes
    60,
    metafaults.maybe_fault(
# How likely do you want a failure? decreasing this will make failures line up across nodes less often.
      0.33,
      metafaults.pick_fault([
# You can change the weights here to see different kinds of flaky nodes
        (1, fail_node_long),
        (1, fail_node_short),
        (2, fail_node_transient),
      ]))
    ),
  ]


########NEW FILE########
__FILENAME__ = hbase
#!/usr/bin/env python
#
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import signal

from gremlins import faults, metafaults, triggers

rs_kill_long = faults.kill_daemons(["HRegionServer"], signal.SIGKILL, 100)
rs_kill_short = faults.kill_daemons(["HRegionServer"], signal.SIGKILL, 3)

dn_kill_long = faults.kill_daemons(["DataNode"], signal.SIGKILL, 100)
dn_kill_short = faults.kill_daemons(["DataNode"], signal.SIGKILL, 3)

rs_pause = faults.pause_daemons(["HRegionServer"], 62)
dn_pause = faults.pause_daemons(["DataNode"], 20)

# This fault isn't that useful yet, since it only drops inbound packets
# but outbound packets (eg, the ZK pings) keep going.
rs_drop_inbound_packets = faults.drop_packets_to_daemons(["HRegionServer"], 64)

profile = [
  triggers.Periodic(
    45,
    metafaults.pick_fault([
    # kill -9s
      (5, rs_kill_long),
      (1, dn_kill_long),
    # fast kill -9s
      (5, rs_kill_short),
      (1, dn_kill_short),

    # pauses (simulate GC?)
      (10, rs_pause),
      (1, dn_pause ),

    # drop packets (simulate network outage)
      #(1, faults.drop_packets_to_daemons(["DataNode"], 20)),
      #(1, rs_drop_inbound_packets),

      ])),
#  triggers.WebServerTrigger(12321)
  ]


########NEW FILE########
__FILENAME__ = triggers
#!/usr/bin/env python
#
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import threading
import time
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
import cgi

from gremlins import faults, metafaults

class Trigger(object):
  pass

class Periodic(Trigger):
  def __init__(self, period, fault):
    self.period = period
    self.fault = fault
    self.thread = threading.Thread(target=self._thread_body)
    self.thread.setDaemon(True)
    self.should_stop = False

  def start(self):
    self.thread.start()

  def stop(self):
    self.should_stop = True

  def join(self):
    self.thread.join()

  def _thread_body(self):
    logging.info("Periodic trigger starting")
    while not self.should_stop:
      logging.info("Periodic triggering fault " + repr(self.fault))
      self.fault()
      time.sleep(self.period)
    logging.info("Periodic trigger stopping")


class WebServerTrigger(Trigger):
  def __init__(self, port):
    self.port = port
    self.server = HTTPServer(('', port), WebServerTrigger.MyHandler)

  def start(self):
    self.thread = threading.Thread(target=self.server.serve_forever)
    self.thread.setDaemon(True)
    self.thread.start()
    time.sleep(60)

  def stop(self):
    self.server.shutdown()

  def join(self):
    self.thread.join()

  class MyHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
      ctype,pdict = cgi.parse_header(self.headers.getheader('Content-type'))
      if ctype != 'multipart/form-data':
        self.sendresponse(500)
        self.end_headers()
        self.wfile.write('Must post form with fault= data')
        return

      query = cgi.parse_multipart(self.rfile, pdict)
      print query

      try:
        code = query.get('fault', ["NO FAULT"])[0]
        print "code: " + code
        result = eval(code, globals())
        if not result or not callable(result):
          raise "Fault must be a callable!"
        result()
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Success! " + repr(result) + "\n")
      except Exception, e:
        self.send_response(500)
        self.end_headers()
        self.wfile.write('Error: ' + repr(e))

########NEW FILE########
