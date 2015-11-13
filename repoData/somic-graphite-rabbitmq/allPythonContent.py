__FILENAME__ = carbon-agent-rabbitmq
#!/usr/bin/env python
"""Copyright 2008 Orbitz WorldWide
   Copyright 2009 Dmitriy Samovskiy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import sys
if sys.version_info[0] != 2 or sys.version_info[1] < 4:
  print 'Python version >= 2.4 and < 3.0 is required'
  sys.exit(1)

try:
  import graphite
except:
  print "Failed to import the graphite package. Please verify that this package"
  print "was properly installed and that your PYTHONPATH environment variable"
  print "includes the directory in which it is installed."
  print "\nFor example, you may need to run the following command:\n"
  print "export PYTHONPATH=\"/home/myusername/lib/python/:$PYTHONPATH\"\n"
  sys.exit(1)

import os, socket, time, traceback
from getopt import getopt
from signal import signal, SIGTERM
from subprocess import *
from select import select
from schemalib import loadStorageSchemas
from utils import daemonize, dropprivs, logify
import amqplib.client_0_8 as amqp
from graphite_rabbitmq_config import RABBITMQ_BROKER_DATA, GRAPHITE_QUEUE

debug = False
user = 'apache'

try:
  (opts,args) = getopt(sys.argv[1:],"du:h")
  assert ('-h','') not in opts
except:
  print """Usage: %s [options]

Options:
    -d          Debug mode
    -u user     Drop privileges to run as user
    -h          Display this help message
""" % os.path.basename(sys.argv[0])
  sys.exit(1)

for opt,val in opts:
  if opt == '-d':
    debug = True
  elif opt == '-u':
    user = val

if debug:
  logify()
else:
  daemonize()
  logify('log/agent.log')
  pf = open('pid/agent.pid','w')
  pf.write( str(os.getpid()) )
  pf.close()
  try: dropprivs(user)
  except: pass
print 'carbon-agent started (pid=%d)' % os.getpid()

def handleDeath(signum,frame):
  print 'Received SIGTERM, killing children'
  try:
    os.kill( persisterProcess.pid, SIGTERM )
    print 'Sent SIGTERM to carbon-persister'
    os.wait()
    print 'wait() complete, exitting'
  except OSError:
    print 'carbon-persister appears to already be dead'
  sys.exit(0)

signal(SIGTERM,handleDeath)

devnullr = open('/dev/null','r')
devnullw = open('/dev/null','w')

persisterPipe = map( str, os.pipe() )
print 'created persister pipe, fds=%s' % str(persisterPipe)

args = ['./carbon-persister.py',persisterPipe[0]]
persisterProcess = Popen(args,stdin=devnullr,stdout=devnullw,stderr=devnullw)
print 'carbon-persister started with pid %d' % persisterProcess.pid
pf = open('pid/persister.pid','w')
pf.write( str(persisterProcess.pid) )
pf.close()

writeFD = int(persisterPipe[1])

def write_to_persister(msg):
  data = "%s" % msg.body
  if not data.endswith("\n"): data += "\n"
  written = os.write(writeFD, data)
  msg.channel.basic_ack(msg.delivery_tag)
  assert written == len(data), "write_to_persister: wrote only %d of %d" \
                               % (written, len(data))

while True:
  try:
    conn = amqp.Connection(**RABBITMQ_BROKER_DATA)
    ch = conn.channel()
    ch.basic_consume(GRAPHITE_QUEUE, callback=write_to_persister)
    while ch.callbacks: ch.wait()
  except Exception, e:
    print '%s Got exception in loop: %s' % (time.asctime(), str(e))
    try: conn.close()
    except: pass
    time.sleep(1)



########NEW FILE########
__FILENAME__ = eth0_traf
#!/usr/bin/env python

"""

Parses Linux /proc/net/dev to get RX and TX bytes on interface IFACE

"""

import sys, os, time
sys.path += [ os.path.dirname(os.path.dirname(os.path.abspath(__file__))) ]
from graphite_rabbitmq_publish import GraphiteRabbitMQPublisher

try:
    iface = sys.argv[1]
    metric_prefix = sys.argv[2]
except:
    print "Usage: %s iface metric_prefix" % sys.argv[0]
    sys.exit(1)

def parse_proc_net_dev(iface):
    f = open('/proc/net/dev')
    r = 0
    t = 0
    for l in f:
        if l.find("%s:" % iface) == -1: continue
        spl = l.split()
        r, t = int(spl[0].split(':')[1]), int(spl[8])
    f.close()
    return r, t

rx = 0
tx = 0
first_sample = True
while True:
    try:
        pub = GraphiteRabbitMQPublisher()
        while True:
            new_rx, new_tx = parse_proc_net_dev(iface)
            if not first_sample:
                pub.publish([
                    "%s.rx %d" % (metric_prefix, new_rx-rx),
                    "%s.tx %d" % (metric_prefix, new_tx-tx)
                ])
            print "%s rx:%d tx:%d" % (time.asctime(), new_rx-rx, new_tx-tx)
            rx, tx = new_rx, new_tx
            first_sample = False
            time.sleep(60)
    except Exception, e:
        print e
        time.sleep(20)


########NEW FILE########
__FILENAME__ = rabbit_queues
#!/usr/bin/env python
#
# graphite publisher for some basic info on rabbitmq queues
#
# requires py-interface:
# http://www.lysator.liu.se/~tab/erlang/py_interface/
#

COOKIE = 'PQDZQNHHATKKMBYYBHSS'
METRIC_PREFIX = 'rabbitmq.homeserver.queues'
RABBIT_NODE = 'rabbit@home'

metrics = [ "messages_ready", "messages_unacknowledged",
    "messages_uncommitted", "messages", "consumers", "memory" ]

import sys, os, time
sys.path += [ os.path.dirname(os.path.dirname(os.path.abspath(__file__))) ]
from graphite_rabbitmq_publish import GraphiteRabbitMQPublisher

from py_interface import erl_node, erl_eventhandler
from py_interface.erl_opts import ErlNodeOpts
from py_interface.erl_term import ErlAtom, ErlBinary

#from py_interface import erl_common
#erl_common.DebugOnAll()

rpc_args = [ ErlAtom('name') ] + [ ErlAtom(x) for x in metrics ]

def __msg_handler_list_queues(msg):
    data_lines = [ ]
    for q in msg:
        name = q[0][1][-1].contents
        for atoms_tuple in q[1:]:
                data_lines.append("%s.%s.%s %d" % \
                    (METRIC_PREFIX, name, atoms_tuple[0].atomText,
                    atoms_tuple[1]))
    print data_lines
    pub.publish(data_lines)
    erl_eventhandler.GetEventHandler().AddTimerEvent(60,
        rpc_list_queues, mbox=mbox)

def start_pyrabbitmqctl_node():
    node = erl_node.ErlNode("pyrabbitmqctl%d" % os.getpid(),
                            ErlNodeOpts(cookie=COOKIE))
    mbox = node.CreateMBox()
    return node, mbox

def rpc_list_queues(mbox, vhost="/"):
    mbox.SendRPC(
        ErlAtom(RABBIT_NODE),
        ErlAtom('rabbit_amqqueue'),
        ErlAtom('info_all'),
        [ ErlBinary(vhost), rpc_args ],
        __msg_handler_list_queues
    )

global pub
pub = GraphiteRabbitMQPublisher()

node, mbox = start_pyrabbitmqctl_node()
rpc_list_queues(mbox)
erl_eventhandler.GetEventHandler().Loop()


########NEW FILE########
__FILENAME__ = graphite_rabbitmq_config
#!/usr/bin/env python

"""

Defines common configuration data + tool to create graphite queue.

"""


RABBITMQ_BROKER_DATA = {
    'host': 'localhost:5672',
    'userid': 'guest',
    'password': 'guest'
}

GRAPHITE_EXCHANGE = 'amq.direct'
GRAPHITE_ROUTING_KEY = 'graphite'
GRAPHITE_QUEUE = 'graphite_data'

if __name__ == '__main__':
    import sys
    import amqplib.client_0_8 as amqp

    conn = amqp.Connection(**RABBITMQ_BROKER_DATA)
    ch = conn.channel()
    try:
        ch.queue_declare(queue=GRAPHITE_QUEUE, passive=True)
        print "Queue %s already exists." % GRAPHITE_QUEUE
    except:
        ch = conn.channel()
        ch.queue_declare(queue=GRAPHITE_QUEUE, durable=True, auto_delete=False)
        ch.queue_bind(GRAPHITE_QUEUE, GRAPHITE_EXCHANGE, GRAPHITE_ROUTING_KEY)
        ch.close()
        conn.close()
        print "Queue %s created." % GRAPHITE_QUEUE




########NEW FILE########
__FILENAME__ = graphite_rabbitmq_publish
#!/usr/bin/env python

import time
import sys
import amqplib.client_0_8 as amqp
from graphite_rabbitmq_config import RABBITMQ_BROKER_DATA, \
  GRAPHITE_EXCHANGE, GRAPHITE_ROUTING_KEY

class GraphiteRabbitMQPublisher:
  def __init__(self, rabbitmq_broker_data=RABBITMQ_BROKER_DATA,
                exchange=GRAPHITE_EXCHANGE,
                routing_key=GRAPHITE_ROUTING_KEY):
    self.rabbitmq_broker_data = rabbitmq_broker_data
    self.exchange = exchange
    self.routing_key=routing_key
    self.__channel = None

  def channel(self):
    if self.__channel is None:
        self.conn = amqp.Connection(**self.rabbitmq_broker_data)
        self.__channel = self.conn.channel()
    return self.__channel
              
  def publish(self, data, **defaults):
    """
    data can be a dict {metric:value, ...}
    data can be a list ["metric value", "value", "metric value timestamp", ...]

    defaults can include timestamp and metric

    """
    try: defaults['timestamp']
    except KeyError: defaults['timestamp'] = int(time.time())

    payload_lines = [ ]
    if type(data) == dict:
        for k in data:
            payload_lines.append("%s %s %d" % (k, str(data[k]), 
                defaults['timestamp']))
    elif type(data) == list:
        for k in data:
            parts = str(k).strip().split()
            m = None    # metric
            v = None    # value
            t = None    # timestamp
            if len(parts) == 1:
                m = defaults['metric']
                v = k
                t = defaults['timestamp']
            elif len(parts) == 2:
                m,v = parts[:2]
                t = defaults['timestamp']
            elif len(parts) == 3:
                m, v, t = parts
            else:
                raise ArgumentError, "bad line: %s" % k

            payload_lines.append("%s %s %d" % (m, v, t))
    elif type(data) == str:
        if not len(data.strip().split()) == 3:
            raise ArgumentError, "bad line %s" % data
        payload_lines.append(data)

    self.channel().basic_publish(
        amqp.Message("\n".join(payload_lines), delivery_mode=2),
        exchange=self.exchange, routing_key=self.routing_key)


if __name__ == '__main__':
    try:
        assert len(sys.argv[1:]) > 0, "Nothing to send"
        GraphiteRabbitMQPublisher().publish(sys.argv[1:])
    except Exception, e:
        print "Error: %s" % str(e)
        print "Usage: %s 'metric value timestamp' ..." % sys.argv[0]



########NEW FILE########
