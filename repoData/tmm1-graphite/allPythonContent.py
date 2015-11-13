__FILENAME__ = run-graphite-devel-server
#!/usr/bin/env python

import sys, os
import subprocess
from optparse import OptionParser

option_parser = OptionParser(usage='''
%prog [options] GRAPHITE_ROOT
''')
option_parser.add_option('--port', default=8080, action='store', type=int, help='Port to listen on')
option_parser.add_option('--libs', default=None, help='Path to the directory containing the graphite python package')
option_parser.add_option('--noreload', action='store_true', help='Disable monitoring for changes')

(options, args) = option_parser.parse_args()

if not args:
  option_parser.print_usage()
  sys.exit(1)

graphite_root = args[0]

django_admin = None
for name in ('django-admin', 'django-admin.py'):
  process = subprocess.Popen(['which', name], stdout=subprocess.PIPE)
  output = process.stdout.read().strip()
  if process.wait() == 0:
    django_admin = output
    break

if not django_admin:
  print "Could not find a django-admin script!"
  sys.exit(1)

python_path = os.path.join(graphite_root, 'webapp')

if options.libs:
  libdir = os.path.expanduser(options.libs)
  print 'Adding %s to your PYTHONPATH' % libdir
  os.environ['PYTHONPATH'] = libdir + ':' + os.environ.get('PYTHONPATH','')

print "Running Graphite from %s under django development server\n" % graphite_root

command = [
  django_admin,
  'runserver',
  '--pythonpath', python_path,
  '--settings', 'graphite.settings',
  '0.0.0.0:%d' % options.port
]

if options.noreload:
  command.append('--noreload')

print ' '.join(command)
os.execvp(django_admin, command)

########NEW FILE########
__FILENAME__ = carbon-aggregator
#!/usr/bin/env python
"""Copyright 2009 Chris Davis

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
from os.path import dirname, join, abspath

# Figure out where we're installed
BIN_DIR = dirname(abspath(__file__))
ROOT_DIR = dirname(BIN_DIR)

# Make sure that carbon's 'lib' dir is in the $PYTHONPATH if we're running from
# source.
LIB_DIR = join(ROOT_DIR, 'lib')
sys.path.insert(0, LIB_DIR)

from carbon.util import run_twistd_plugin

run_twistd_plugin(__file__)

########NEW FILE########
__FILENAME__ = carbon-cache
#!/usr/bin/env python
"""Copyright 2009 Chris Davis

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
from os.path import dirname, join, abspath

# Figure out where we're installed
BIN_DIR = dirname(abspath(__file__))
ROOT_DIR = dirname(BIN_DIR)

# Make sure that carbon's 'lib' dir is in the $PYTHONPATH if we're running from
# source.
LIB_DIR = join(ROOT_DIR, 'lib')
sys.path.insert(0, LIB_DIR)

from carbon.util import run_twistd_plugin

run_twistd_plugin(__file__)

########NEW FILE########
__FILENAME__ = carbon-client
#!/usr/bin/env python
"""Copyright 2009 Chris Davis

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
import imp
from os.path import dirname, join, abspath, exists
from optparse import OptionParser

# Figure out where we're installed
BIN_DIR = dirname(abspath(__file__))
ROOT_DIR = dirname(BIN_DIR)
CONF_DIR = join(ROOT_DIR, 'conf')
default_relayrules = join(CONF_DIR, 'relay-rules.conf')

# Make sure that carbon's 'lib' dir is in the $PYTHONPATH if we're running from
# source.
LIB_DIR = join(ROOT_DIR, 'lib')
sys.path.insert(0, LIB_DIR)

try:
  from twisted.internet import epollreactor
  epollreactor.install()
except ImportError:
  pass

from twisted.internet import stdio, reactor, defer
from twisted.protocols.basic import LineReceiver
from carbon.routers import ConsistentHashingRouter, RelayRulesRouter
from carbon.client import CarbonClientManager
from carbon import log, events


option_parser = OptionParser(usage="%prog [options] <host:port:instance> <host:port:instance> ...")
option_parser.add_option('--debug', action='store_true', help="Log debug info to stdout")
option_parser.add_option('--keyfunc', help="Use a custom key function (path/to/module.py:myFunc)")
option_parser.add_option('--replication', type='int', default=1, help='Replication factor')
option_parser.add_option('--routing', default='consistent-hashing',
  help='Routing method: "consistent-hashing" (default) or "relay"')
option_parser.add_option('--relayrules', default=default_relayrules,
  help='relay-rules.conf file to use for relay routing')

options, args = option_parser.parse_args()

if not args:
  print 'At least one host:port destination required\n'
  option_parser.print_usage()
  raise SystemExit(1)

if options.routing not in ('consistent-hashing', 'relay'):
  print "Invalid --routing value, must be one of:"
  print "  consistent-hashing"
  print "  relay"
  raise SystemExit(1)

destinations = []
for arg in args:
  parts = arg.split(':', 2)
  host = parts[0]
  port = int(parts[1])
  if len(parts) > 2:
    instance = parts[2]
  else:
    instance = None
  destinations.append( (host, port, instance) )

if options.debug:
  log.logToStdout()
  log.setDebugEnabled(True)
  defer.setDebugging(True)

if options.routing == 'consistent-hashing':
  router = ConsistentHashingRouter(options.replication)
elif options.routing == 'relay':
  if exists(options.relayrules):
    router = RelayRulesRouter(options.relayrules)
  else:
    print "relay rules file %s does not exist" % options.relayrules
    raise SystemExit(1)

client_manager = CarbonClientManager(router)
reactor.callWhenRunning(client_manager.startService)

if options.keyfunc:
  router.setKeyFunctionFromModule(options.keyfunc)

firstConnectAttempts = [client_manager.startClient(dest) for dest in destinations]
firstConnectsAttempted = defer.DeferredList(firstConnectAttempts)


class StdinMetricsReader(LineReceiver):
  delimiter = '\n'

  def lineReceived(self, line):
    #log.msg("[DEBUG] lineReceived(): %s" % line)
    try:
      (metric, value, timestamp) = line.split()
      datapoint = (float(timestamp), float(value))
      assert datapoint[1] == datapoint[1] # filter out NaNs
      client_manager.sendDatapoint(metric, datapoint)
    except:
      log.err(None, 'Dropping invalid line: %s' % line)

  def connectionLost(self, reason):
    log.msg('stdin disconnected')
    def startShutdown(results):
      log.msg("startShutdown(%s)" % str(results))
      allStopped = client_manager.stopAllClients()
      allStopped.addCallback(shutdown)
    firstConnectsAttempted.addCallback(startShutdown)

stdio.StandardIO( StdinMetricsReader() )

exitCode = 0
def shutdown(results):
  global exitCode
  for success, result in results:
    if not success:
      exitCode = 1
      break
  if reactor.running:
    reactor.stop()

reactor.run()
raise SystemExit(exitCode)

########NEW FILE########
__FILENAME__ = carbon-relay
#!/usr/bin/env python
"""Copyright 2009 Chris Davis

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
from os.path import dirname, join, abspath

# Figure out where we're installed
BIN_DIR = dirname(abspath(__file__))
ROOT_DIR = dirname(BIN_DIR)

# Make sure that carbon's 'lib' dir is in the $PYTHONPATH if we're running from
# source.
LIB_DIR = join(ROOT_DIR, 'lib')
sys.path.insert(0, LIB_DIR)

from carbon.util import run_twistd_plugin

run_twistd_plugin(__file__)

########NEW FILE########
__FILENAME__ = validate-storage-schemas
#!/usr/bin/env python
"""Copyright 2009 Chris Davis

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
import whisper
from os.path import dirname, exists, join, realpath
from ConfigParser import ConfigParser

if len(sys.argv) == 2:
  SCHEMAS_FILE = sys.argv[1]
  print "Loading storage-schemas configuration from: '%s'" % SCHEMAS_FILE
else:
  SCHEMAS_FILE = realpath(join(dirname(__file__), '..', 'conf', 'storage-schemas.conf'))
  print "Loading storage-schemas configuration from default location at: '%s'" % SCHEMAS_FILE

config_parser = ConfigParser()
if not config_parser.read(SCHEMAS_FILE):
  print "Error: Couldn't read config file: %s" % SCHEMAS_FILE
  sys.exit(1)

errors_found = 0

for section in config_parser.sections():
  print "Section '%s':" % section
  options = dict(config_parser.items(section))
  retentions = options['retentions'].split(',')

  archives = []
  section_failed = False
  for retention in retentions:
    try:
      archives.append(whisper.parseRetentionDef(retention))
    except ValueError, e:
      print "  - Error: Section '%s' contains an invalid item in its retention definition ('%s')" % \
        (section, retention)
      print "    %s" % e.message
      section_failed = True

  if not section_failed:
    try:
      whisper.validateArchiveList(archives)
    except whisper.InvalidConfiguration, e:
      print "  - Error: Section '%s' contains an invalid retention definition ('%s')" % \
        (section, ','.join(retentions))
      print "    %s" % e.message

  if section_failed:
    errors_found += 1
  else:
    print "  OK"

if errors_found:
  print
  print "Storage-schemas configuration '%s' failed validation" % SCHEMAS_FILE
  sys.exit(1)

print
print "Storage-schemas configuration '%s' is valid" % SCHEMAS_FILE

########NEW FILE########
__FILENAME__ = buffers
import time
from twisted.internet.task import LoopingCall
from carbon.conf import settings
from carbon import log


class BufferManager:
  def __init__(self):
    self.buffers = {}

  def __len__(self):
    return len(self.buffers)

  def get_buffer(self, metric_path):
    if metric_path not in self.buffers:
      log.aggregator("Allocating new metric buffer for %s" % metric_path)
      self.buffers[metric_path] = MetricBuffer(metric_path)

    return self.buffers[metric_path]

  def clear(self):
    for buffer in self.buffers.values():
      buffer.close()

    self.buffers.clear()


class MetricBuffer:
  __slots__ = ('metric_path', 'interval_buffers', 'compute_task', 'configured',
               'aggregation_frequency', 'aggregation_func')

  def __init__(self, metric_path):
    self.metric_path = metric_path
    self.interval_buffers = {}
    self.compute_task = None
    self.configured = False
    self.aggregation_frequency = None
    self.aggregation_func = None

  def input(self, datapoint):
    (timestamp, value) = datapoint
    interval = timestamp - (timestamp % self.aggregation_frequency)
    if interval in self.interval_buffers:
      buffer = self.interval_buffers[interval]
    else:
      buffer = self.interval_buffers[interval] = IntervalBuffer(interval)

    buffer.input(datapoint)

  def configure_aggregation(self, frequency, func):
    self.aggregation_frequency = int(frequency)
    self.aggregation_func = func
    self.compute_task = LoopingCall(self.compute_value)
    self.compute_task.start(frequency, now=False)
    self.configured = True

  def compute_value(self):
    now = int( time.time() )
    current_interval = now - (now % self.aggregation_frequency)
    age_threshold = current_interval - (settings['MAX_AGGREGATION_INTERVALS'] * self.aggregation_frequency)

    for buffer in self.interval_buffers.values():
      if buffer.active:
        value = self.aggregation_func(buffer.values)
        datapoint = (buffer.interval, value)
        state.events.metricGenerated(self.metric_path, datapoint)
        state.instrumentation.increment('aggregateDatapointsSent')
        buffer.mark_inactive()

      if buffer.interval < age_threshold:
        del self.interval_buffers[buffer.interval]

  def close(self):
    if self.compute_task and self.compute_task.running:
      self.compute_task.stop()

  @property
  def size(self):
    return sum([len(buf.values) for buf in self.interval_buffers.values()])


class IntervalBuffer:
  __slots__ = ('interval', 'values', 'active')

  def __init__(self, interval):
    self.interval = interval
    self.values = []
    self.active = True

  def input(self, datapoint):
    self.values.append( datapoint[1] )
    self.active = True

  def mark_inactive(self):
    self.active = False


# Shared importable singleton
BufferManager = BufferManager()

# Avoid import circularity
from carbon import state

########NEW FILE########
__FILENAME__ = receiver
from carbon.instrumentation import increment
from carbon.aggregator.rules import RuleManager
from carbon.aggregator.buffers import BufferManager
from carbon.rewrite import RewriteRuleManager
from carbon import events


def process(metric, datapoint):
  increment('datapointsReceived')

  for rule in RewriteRuleManager.preRules:
    metric = rule.apply(metric)

  aggregate_metrics = []

  for rule in RuleManager.rules:
    aggregate_metric = rule.get_aggregate_metric(metric)

    if aggregate_metric is None:
      continue
    else:
      aggregate_metrics.append(aggregate_metric)

    buffer = BufferManager.get_buffer(aggregate_metric)

    if not buffer.configured:
      buffer.configure_aggregation(rule.frequency, rule.aggregation_func)

    buffer.input(datapoint)

  for rule in RewriteRuleManager.postRules:
    metric = rule.apply(metric)

  if metric not in aggregate_metrics:
    events.metricGenerated(metric, datapoint)

########NEW FILE########
__FILENAME__ = rules
import time
import re
from os.path import exists, getmtime
from twisted.internet.task import LoopingCall
from carbon import log
from carbon.aggregator.buffers import BufferManager


class RuleManager:
  def __init__(self):
    self.rules = []
    self.rules_file = None
    self.read_task = LoopingCall(self.read_rules)
    self.rules_last_read = 0.0

  def clear(self):
    self.rules = []

  def read_from(self, rules_file):
    self.rules_file = rules_file
    self.read_rules()
    self.read_task.start(10, now=False)

  def read_rules(self):
    if not exists(self.rules_file):
      self.clear()
      return

    # Only read if the rules file has been modified
    try:
      mtime = getmtime(self.rules_file)
    except:
      log.err("Failed to get mtime of %s" % self.rules_file)
      return
    if mtime <= self.rules_last_read:
      return

    # Read new rules
    log.aggregator("reading new aggregation rules from %s" % self.rules_file)
    new_rules = []
    for line in open(self.rules_file):
      line = line.strip()
      if line.startswith('#') or not line:
        continue

      rule = self.parse_definition(line)
      new_rules.append(rule)

    log.aggregator("clearing aggregation buffers")
    BufferManager.clear()
    self.rules = new_rules
    self.rules_last_read = mtime

  def parse_definition(self, line):
    try:
      left_side, right_side = line.split('=', 1)
      output_pattern, frequency = left_side.split()
      method, input_pattern = right_side.split()
      frequency = int( frequency.lstrip('(').rstrip(')') )
      return AggregationRule(input_pattern, output_pattern, method, frequency)

    except:
      log.err("Failed to parse line: %s" % line)
      raise


class AggregationRule:
  def __init__(self, input_pattern, output_pattern, method, frequency):
    self.input_pattern = input_pattern
    self.output_pattern = output_pattern
    self.method = method
    self.frequency = int(frequency)

    if method not in AGGREGATION_METHODS:
      raise ValueError("Invalid aggregation method '%s'" % method)

    self.aggregation_func = AGGREGATION_METHODS[method]
    self.build_regex()
    self.build_template()
    self.cache = {}

  def get_aggregate_metric(self, metric_path):
    if metric_path in self.cache:
      return self.cache[metric_path]

    match = self.regex.match(metric_path)
    result = None

    if match:
      extracted_fields = match.groupdict()
      try:
        result = self.output_template % extracted_fields
      except:
        log.err("Failed to interpolate template %s with fields %s" % (self.output_template, extracted_fields))

    self.cache[metric_path] = result
    return result

  def build_regex(self):
    input_pattern_parts = self.input_pattern.split('.')
    regex_pattern_parts = []

    for input_part in input_pattern_parts:
      if '<<' in input_part and '>>' in input_part:
        i = input_part.find('<<')
        j = input_part.find('>>')
        pre = input_part[:i]
        post = input_part[j+2:]
        field_name = input_part[i+2:j]
        regex_part = '%s(?P<%s>.+)%s' % (pre, field_name, post)

      else:
        i = input_part.find('<')
        j = input_part.find('>')
        if i > -1 and j > i:
          pre = input_part[:i]
          post = input_part[j+1:]
          field_name = input_part[i+1:j]
          regex_part = '%s(?P<%s>[^.]+)%s' % (pre, field_name, post)
        elif input_part == '*':
          regex_part = '[^.]+'
        else:
          regex_part = input_part.replace('*', '[^.]*')

      regex_pattern_parts.append(regex_part)

    regex_pattern = '\\.'.join(regex_pattern_parts)
    self.regex = re.compile(regex_pattern)

  def build_template(self):
    self.output_template = self.output_pattern.replace('<', '%(').replace('>', ')s')


def avg(values):
  if values:
    return float( sum(values) ) / len(values)


AGGREGATION_METHODS = {
  'sum' : sum,
  'avg' : avg,
}

# Importable singleton
RuleManager = RuleManager()

########NEW FILE########
__FILENAME__ = amqp_listener
#!/usr/bin/env python
"""
Copyright 2009 Lucio Torre <lucio.torre@canonical.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This is an AMQP client that will connect to the specified broker and read
messages, parse them, and post them as metrics.

Each message's routing key should be a metric name.
The message body should be one or more lines of the form:

<value> <timestamp>\n
<value> <timestamp>\n
...

Where each <value> is a real number and <timestamp> is a UNIX epoch time.


This program can be started standalone for testing or using carbon-cache.py
(see example config file provided)
"""
import sys
import os
import socket
from optparse import OptionParser

from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor
from twisted.internet.protocol import ReconnectingClientFactory
from txamqp.protocol import AMQClient
from txamqp.client import TwistedDelegate
import txamqp.spec

try:
    import carbon
except:
    # this is being run directly, carbon is not installed
    LIB_DIR = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, LIB_DIR)

import carbon.protocols #satisfy import order requirements
from carbon.conf import settings
from carbon import log, events, instrumentation


HOSTNAME = socket.gethostname().split('.')[0]


class AMQPGraphiteProtocol(AMQClient):
    """This is the protocol instance that will receive and post metrics."""

    consumer_tag = "graphite_consumer"

    @inlineCallbacks
    def connectionMade(self):
        yield AMQClient.connectionMade(self)
        log.listener("New AMQP connection made")
        yield self.setup()
        yield self.receive_loop()

    @inlineCallbacks
    def setup(self):
        exchange = self.factory.exchange_name

        yield self.authenticate(self.factory.username, self.factory.password)
        chan = yield self.channel(1)
        yield chan.channel_open()

        # declare the exchange and queue
        yield chan.exchange_declare(exchange=exchange, type="topic",
                                    durable=True, auto_delete=False)

        # we use a private queue to avoid conflicting with existing bindings
        reply = yield chan.queue_declare(exclusive=True)
        my_queue = reply.queue

        # bind each configured metric pattern
        for bind_pattern in settings.BIND_PATTERNS:
            log.listener("binding exchange '%s' to queue '%s' with pattern %s" \
                         % (exchange, my_queue, bind_pattern))
            yield chan.queue_bind(exchange=exchange, queue=my_queue,
                                  routing_key=bind_pattern)

        yield chan.basic_consume(queue=my_queue, no_ack=True,
                                 consumer_tag=self.consumer_tag)
    @inlineCallbacks
    def receive_loop(self):
        queue = yield self.queue(self.consumer_tag)

        while True:
            msg = yield queue.get()
            self.processMessage(msg)

    def processMessage(self, message):
        """Parse a message and post it as a metric."""

        if self.factory.verbose:
            log.listener("Message received: %s" % (message,))

        metric = message.routing_key

        for line in message.content.body.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                if settings.get("AMQP_METRIC_NAME_IN_BODY", False):
                    metric, value, timestamp = line.split()
                else:
                    value, timestamp = line.split()
                datapoint = ( float(timestamp), float(value) )
            except ValueError:
                log.listener("invalid message line: %s" % (line,))
                continue

            events.metricReceived(metric, datapoint)

            if self.factory.verbose:
                log.listener("Metric posted: %s %s %s" %
                             (metric, value, timestamp,))


class AMQPReconnectingFactory(ReconnectingClientFactory):
    """The reconnecting factory.

    Knows how to create the extended client and how to keep trying to
    connect in case of errors."""

    protocol = AMQPGraphiteProtocol

    def __init__(self, username, password, delegate, vhost, spec, channel,
                 exchange_name, verbose):
        self.username = username
        self.password = password
        self.delegate = delegate
        self.vhost = vhost
        self.spec = spec
        self.channel = channel
        self.exchange_name = exchange_name
        self.verbose = verbose

    def buildProtocol(self, addr):
        p = self.protocol(self.delegate, self.vhost, self.spec)
        p.factory = self
        return p


def createAMQPListener(username, password, vhost, exchange_name,
                       spec=None, channel=1, verbose=False):
    """
    Create an C{AMQPReconnectingFactory} configured with the specified options.
    """
    # use provided spec if not specified
    if not spec:
        spec = txamqp.spec.load(os.path.normpath(
            os.path.join(os.path.dirname(__file__), 'amqp0-8.xml')))

    delegate = TwistedDelegate()
    factory = AMQPReconnectingFactory(username, password, delegate, vhost,
                                      spec, channel, exchange_name,
                                      verbose=verbose)
    return factory


def startReceiver(host, port, username, password, vhost, exchange_name,
                  spec=None, channel=1, verbose=False):
    """
    Starts a twisted process that will read messages on the amqp broker and
    post them as metrics.
    """
    factory = createAMQPListener(username, password, vhost, exchange_name,
                                 spec=spec, channel=channel, verbose=verbose)
    reactor.connectTCP(host, port, factory)


def main():
    parser = OptionParser()
    parser.add_option("-t", "--host", dest="host",
                      help="host name", metavar="HOST", default="localhost")

    parser.add_option("-p", "--port", dest="port", type=int,
                      help="port number", metavar="PORT",
                      default=5672)

    parser.add_option("-u", "--user", dest="username",
                      help="username", metavar="USERNAME",
                      default="guest")

    parser.add_option("-w", "--password", dest="password",
                      help="password", metavar="PASSWORD",
                      default="guest")

    parser.add_option("-V", "--vhost", dest="vhost",
                      help="vhost", metavar="VHOST",
                      default="/")

    parser.add_option("-e", "--exchange", dest="exchange",
                      help="exchange", metavar="EXCHANGE",
                      default="graphite")

    parser.add_option("-v", "--verbose", dest="verbose",
                      help="verbose",
                      default=False, action="store_true")

    (options, args) = parser.parse_args()


    startReceiver(options.host, options.port, options.username,
                  options.password, vhost=options.vhost,
                  exchange_name=options.exchange, verbose=options.verbose)
    reactor.run()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = amqp_publisher
#!/usr/bin/env python
"""
Copyright 2009 Lucio Torre <lucio.torre@canonical.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Will publish metrics over AMQP
"""
import os
import time
from optparse import OptionParser

from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor, task
from twisted.internet.protocol import ClientCreator
from txamqp.protocol import AMQClient
from txamqp.client import TwistedDelegate
from txamqp.content import Content
import txamqp.spec


@inlineCallbacks
def writeMetric(metric_path, value, timestamp, host, port, username, password,
                vhost, exchange, spec=None, channel_number=1, ssl=False):

    if not spec:
        spec = txamqp.spec.load(os.path.normpath(
            os.path.join(os.path.dirname(__file__), 'amqp0-8.xml')))

    delegate = TwistedDelegate()

    connector = ClientCreator(reactor, AMQClient, delegate=delegate,
                              vhost=vhost, spec=spec)
    if ssl:
        from twisted.internet.ssl import ClientContextFactory
        conn = yield connector.connectSSL(host, port, ClientContextFactory())
    else:
        conn = yield connector.connectTCP(host, port)

    yield conn.authenticate(username, password)
    channel = yield conn.channel(channel_number)
    yield channel.channel_open()

    yield channel.exchange_declare(exchange=exchange, type="topic",
                                   durable=True, auto_delete=False)

    message = Content( "%f %d" % (value, timestamp) )
    message["delivery mode"] = 2

    channel.basic_publish(exchange=exchange, content=message, routing_key=metric_path)
    yield channel.channel_close()


def main():
    parser = OptionParser(usage="%prog [options] <metric> <value> [timestamp]")
    parser.add_option("-t", "--host", dest="host",
                      help="host name", metavar="HOST", default="localhost")

    parser.add_option("-p", "--port", dest="port", type=int,
                      help="port number", metavar="PORT",
                      default=5672)

    parser.add_option("-u", "--user", dest="username",
                      help="username", metavar="USERNAME",
                      default="guest")

    parser.add_option("-w", "--password", dest="password",
                      help="password", metavar="PASSWORD",
                      default="guest")

    parser.add_option("-v", "--vhost", dest="vhost",
                      help="vhost", metavar="VHOST",
                      default="/")

    parser.add_option("-s", "--ssl", dest="ssl",
                      help="ssl", metavar="SSL", action="store_true",
                      default=False)

    parser.add_option("-e", "--exchange", dest="exchange",
                      help="exchange", metavar="EXCHANGE",
                      default="graphite")

    (options, args) = parser.parse_args()

    try:
      metric_path = args[0]
      value = float(args[1])

      if len(args) > 2:
        timestamp = int(args[2])
      else:
        timestamp = time.time()

    except:
      parser.print_usage()
      raise SystemExit(1)

    d = writeMetric(metric_path, value, timestamp, options.host, options.port,
                    options.username, options.password, vhost=options.vhost,
                    exchange=options.exchange, ssl=options.ssl)
    d.addErrback(lambda f: f.printTraceback())
    d.addBoth(lambda _: reactor.stop())
    reactor.run()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = cache
"""Copyright 2009 Chris Davis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from threading import Lock
from carbon.conf import settings


class MetricCache(dict):
  def __init__(self):
    self.size = 0
    self.lock = Lock()

  def __setitem__(self, key, value):
    raise TypeError("Use store() method instead!")

  def store(self, metric, datapoint):
    try:
      self.lock.acquire()
      self.setdefault(metric, []).append(datapoint)
      self.size += 1
    finally:
      self.lock.release()

    if self.isFull():
      log.msg("MetricCache is full: self.size=%d" % self.size)
      state.events.cacheFull()

  def isFull(self):
    return self.size >= settings.MAX_CACHE_SIZE

  def pop(self, metric):
    try:
      self.lock.acquire()
      datapoints = dict.pop(self, metric)
      self.size -= len(datapoints)
      return datapoints
    finally:
      self.lock.release()

  def counts(self):
    try:
      self.lock.acquire()
      return [ (metric, len(datapoints)) for (metric, datapoints) in self.items() ]
    finally:
      self.lock.release()


# Ghetto singleton
MetricCache = MetricCache()


# Avoid import circularities
from carbon import log, state

########NEW FILE########
__FILENAME__ = client
from twisted.application.service import Service
from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import Int32StringReceiver
from carbon.conf import settings
from carbon.util import pickle
from carbon import log, state, events, instrumentation


SEND_QUEUE_LOW_WATERMARK = settings.MAX_QUEUE_SIZE * 0.8


class CarbonClientProtocol(Int32StringReceiver):
  def connectionMade(self):
    log.clients("%s::connectionMade" % self)
    self.paused = False
    self.connected = True
    self.transport.registerProducer(self, streaming=True)
    # Define internal metric names
    self.destinationName = self.factory.destinationName
    self.queuedUntilReady = 'destinations.%s.queuedUntilReady' % self.destinationName
    self.sent = 'destinations.%s.sent' % self.destinationName

    self.factory.connectionMade.callback(self)
    self.factory.connectionMade = Deferred()
    self.sendQueued()

  def connectionLost(self, reason):
    log.clients("%s::connectionLost %s" % (self, reason.getErrorMessage()))
    self.connected = False

  def pauseProducing(self):
    self.paused = True

  def resumeProducing(self):
    self.paused = False
    self.sendQueued()

  def stopProducing(self):
    self.disconnect()

  def disconnect(self):
    if self.connected:
      self.transport.unregisterProducer()
      self.transport.loseConnection()
      self.connected = False

  def sendDatapoint(self, metric, datapoint):
    if self.paused:
      self.factory.enqueue(metric, datapoint)
      instrumentation.increment(self.queuedUntilReady)

    elif self.factory.hasQueuedDatapoints():
      self.factory.enqueue(metric, datapoint)
      self.sendQueued()

    else:
      self._sendDatapoints([(metric, datapoint)])

  def _sendDatapoints(self, datapoints):
      self.sendString(pickle.dumps(datapoints, protocol=-1))
      instrumentation.increment(self.sent, len(datapoints))
      self.factory.checkQueue()

  def sendQueued(self):
    while (not self.paused) and self.factory.hasQueuedDatapoints():
      datapoints = self.factory.takeSomeFromQueue()
      self._sendDatapoints(datapoints)

      queueSize = self.factory.queueSize
      if (self.factory.queueFull.called and
          queueSize < SEND_QUEUE_LOW_WATERMARK):
        self.factory.queueHasSpace.callback(queueSize)

        if (settings.USE_FLOW_CONTROL and
            state.metricReceiversPaused):
          log.clients('%s resuming paused clients' % self)
          events.resumeReceivingMetrics()

  def __str__(self):
    return 'CarbonClientProtocol(%s:%d:%s)' % (self.factory.destination)
  __repr__ = __str__


class CarbonClientFactory(ReconnectingClientFactory):
  maxDelay = 5

  def __init__(self, destination):
    self.destination = destination
    self.destinationName = ('%s:%d:%s' % destination).replace('.', '_')
    self.host, self.port, self.carbon_instance = destination
    self.addr = (self.host, self.port)
    self.started = False
    # This factory maintains protocol state across reconnects
    self.queue = [] # including datapoints that still need to be sent
    self.connectedProtocol = None
    self.queueEmpty = Deferred()
    self.queueFull = Deferred()
    self.queueFull.addCallback(self.queueFullCallback)
    self.queueHasSpace = Deferred()
    self.queueHasSpace.addCallback(self.queueSpaceCallback)
    self.connectFailed = Deferred()
    self.connectionMade = Deferred()
    self.connectionLost = Deferred()
    # Define internal metric names
    self.attemptedRelays = 'destinations.%s.attemptedRelays' % self.destinationName
    self.fullQueueDrops = 'destinations.%s.fullQueueDrops' % self.destinationName
    self.queuedUntilConnected = 'destinations.%s.queuedUntilConnected' % self.destinationName

  def queueFullCallback(self, result):
    log.clients('%s send queue is full (%d datapoints)' % (self, result))
    
  def queueSpaceCallback(self, result):
    if self.queueFull.called:
      log.clients('%s send queue has space available' % self.connectedProtocol)
      self.queueFull = Deferred()
      self.queueFull.addCallback(self.queueFullCallback)
    self.queueHasSpace = Deferred()
    self.queueHasSpace.addCallback(self.queueSpaceCallback)

  def buildProtocol(self, addr):
    self.connectedProtocol = CarbonClientProtocol()
    self.connectedProtocol.factory = self
    return self.connectedProtocol

  def startConnecting(self): # calling this startFactory yields recursion problems
    self.started = True
    self.connector = reactor.connectTCP(self.host, self.port, self)

  def stopConnecting(self):
    self.started = False
    self.stopTrying()
    if self.connectedProtocol and self.connectedProtocol.connected:
      return self.connectedProtocol.disconnect()

  @property
  def queueSize(self):
    return len(self.queue)

  def hasQueuedDatapoints(self):
    return bool(self.queue)

  def takeSomeFromQueue(self):
    datapoints = self.queue[:settings.MAX_DATAPOINTS_PER_MESSAGE]
    self.queue = self.queue[settings.MAX_DATAPOINTS_PER_MESSAGE:]
    return datapoints

  def checkQueue(self):
    if not self.queue:
      self.queueEmpty.callback(0)
      self.queueEmpty = Deferred()

  def enqueue(self, metric, datapoint):
    self.queue.append((metric, datapoint))

  def sendDatapoint(self, metric, datapoint):
    instrumentation.increment(self.attemptedRelays)
    queueSize = self.queueSize
    if queueSize >= settings.MAX_QUEUE_SIZE:
      if not self.queueFull.called:
        self.queueFull.callback(queueSize)
      instrumentation.increment(self.fullQueueDrops)
    elif self.connectedProtocol:
      self.connectedProtocol.sendDatapoint(metric, datapoint)
    else:
      self.enqueue(metric, datapoint)
      instrumentation.increment(self.queuedUntilConnected)

  def startedConnecting(self, connector):
    log.clients("%s::startedConnecting (%s:%d)" % (self, connector.host, connector.port))

  def clientConnectionLost(self, connector, reason):
    ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
    log.clients("%s::clientConnectionLost (%s:%d) %s" % (self, connector.host, connector.port, reason.getErrorMessage()))
    self.connectedProtocol = None
    self.connectionLost.callback(0)
    self.connectionLost = Deferred()

  def clientConnectionFailed(self, connector, reason):
    ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
    log.clients("%s::clientConnectionFailed (%s:%d) %s" % (self, connector.host, connector.port, reason.getErrorMessage()))
    self.connectFailed.callback(dict(connector=connector, reason=reason))
    self.connectFailed = Deferred()

  def disconnect(self):
    self.queueEmpty.addCallback(lambda result: self.stopConnecting())
    readyToStop = DeferredList(
      [self.connectionLost, self.connectFailed],
      fireOnOneCallback=True,
      fireOnOneErrback=True)
    self.checkQueue()

    # This can happen if the client is stopped before a connection is ever made
    if (not readyToStop.called) and (not self.started):
      readyToStop.callback(None)

    return readyToStop

  def __str__(self):
    return 'CarbonClientFactory(%s:%d:%s)' % self.destination
  __repr__ = __str__


class CarbonClientManager(Service):
  def __init__(self, router):
    self.router = router
    self.client_factories = {} # { destination : CarbonClientFactory() }

  def startService(self):
    Service.startService(self)
    for factory in self.client_factories.values():
      if not factory.started:
        factory.startConnecting()

  def stopService(self):
    Service.stopService(self)
    self.stopAllClients()

  def startClient(self, destination):
    if destination in self.client_factories:
      return

    log.clients("connecting to carbon daemon at %s:%d:%s" % destination)
    self.router.addDestination(destination)
    factory = self.client_factories[destination] = CarbonClientFactory(destination)
    connectAttempted = DeferredList(
        [factory.connectionMade, factory.connectFailed],
        fireOnOneCallback=True,
        fireOnOneErrback=True)
    if self.running:
      factory.startConnecting() # this can trigger & replace connectFailed

    return connectAttempted

  def stopClient(self, destination):
    factory = self.client_factories.get(destination)
    if factory is None:
      return

    self.router.removeDestination(destination)
    stopCompleted = factory.disconnect()
    stopCompleted.addCallback(lambda result: self.disconnectClient(destination))
    return stopCompleted

  def disconnectClient(self, destination):
    factory = self.client_factories.pop(destination)
    c = factory.connector
    if c and c.state == 'connecting' and not factory.hasQueuedDatapoints():
      c.stopConnecting()

  def stopAllClients(self):
    deferreds = []
    for destination in list(self.client_factories):
      deferreds.append( self.stopClient(destination) )
    return DeferredList(deferreds)

  def sendDatapoint(self, metric, datapoint):
    for destination in self.router.getDestinations(metric):
      self.client_factories[destination].sendDatapoint(metric, datapoint)

  def __str__(self):
    return "<%s[%x]>" % (self.__class__.__name__, id(self))

########NEW FILE########
__FILENAME__ = conf
"""Copyright 2009 Chris Davis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import os
import sys
import pwd
import errno

from os.path import join, dirname, normpath, exists, isdir
from optparse import OptionParser
from ConfigParser import ConfigParser

import whisper
from carbon import log

from twisted.python import usage


defaults = dict(
  USER="",
  MAX_CACHE_SIZE=float('inf'),
  MAX_UPDATES_PER_SECOND=500,
  MAX_CREATES_PER_MINUTE=float('inf'),
  LINE_RECEIVER_INTERFACE='0.0.0.0',
  LINE_RECEIVER_PORT=2003,
  ENABLE_UDP_LISTENER=False,
  UDP_RECEIVER_INTERFACE='0.0.0.0',
  UDP_RECEIVER_PORT=2003,
  PICKLE_RECEIVER_INTERFACE='0.0.0.0',
  PICKLE_RECEIVER_PORT=2004,
  CACHE_QUERY_INTERFACE='0.0.0.0',
  CACHE_QUERY_PORT=7002,
  LOG_UPDATES=True,
  WHISPER_AUTOFLUSH=False,
  WHISPER_SPARSE_CREATE=False,
  WHISPER_LOCK_WRITES=False,
  MAX_DATAPOINTS_PER_MESSAGE=500,
  MAX_AGGREGATION_INTERVALS=5,
  MAX_QUEUE_SIZE=1000,
  ENABLE_AMQP=False,
  AMQP_VERBOSE=False,
  BIND_PATTERNS=['#'],
  ENABLE_MANHOLE=False,
  MANHOLE_INTERFACE='127.0.0.1',
  MANHOLE_PORT=7222,
  MANHOLE_USER="",
  MANHOLE_PUBLIC_KEY="",
  RELAY_METHOD='rules',
  REPLICATION_FACTOR=1,
  DESTINATIONS=[],
  USE_FLOW_CONTROL=True,
  USE_INSECURE_UNPICKLER=False,
  USE_WHITELIST=False,
)


def _umask(value):
    return int(value, 8)

def _process_alive(pid):
    if exists("/proc"):
        return exists("/proc/%d" % pid)
    else:
        try:
            os.kill(int(pid), 0)
            return True
        except OSError, err:
            return err.errno == errno.EPERM


class OrderedConfigParser(ConfigParser):
  """Hacky workaround to ensure sections are always returned in the order
   they are defined in. Note that this does *not* make any guarantees about
   the order of options within a section or the order in which sections get
   written back to disk on write()."""
  _ordered_sections = []

  def read(self, path):
    result = ConfigParser.read(self, path)

    sections = []
    for line in open(path):
      line = line.strip()

      if line.startswith('[') and line.endswith(']'):
        sections.append( line[1:-1] )

    self._ordered_sections = sections

    return result

  def sections(self):
    return list( self._ordered_sections ) # return a copy for safety


class Settings(dict):
  __getattr__ = dict.__getitem__

  def __init__(self):
    dict.__init__(self)
    self.update(defaults)

  def readFrom(self, path, section):
    parser = ConfigParser()
    if not parser.read(path):
      raise Exception("Failed to read config file %s" % path)

    if not parser.has_section(section):
      return

    for key,value in parser.items(section):
      key = key.upper()

      # Detect type from defaults dict
      if key in defaults:
        valueType = type( defaults[key] )
      else:
        valueType = str

      if valueType is list:
        value = [ v.strip() for v in value.split(',') ]

      elif valueType is bool:
        value = parser.getboolean(section, key)

      else:
        # Attempt to figure out numeric types automatically
        try:
          value = int(value)
        except:
          try:
            value = float(value)
          except:
            pass

      self[key] = value


settings = Settings()
settings.update(defaults)


class CarbonCacheOptions(usage.Options):

    optFlags = [
        ["debug", "", "Run in debug mode."],
        ]

    optParameters = [
        ["config", "c", None, "Use the given config file."],
        ["instance", "", "a", "Manage a specific carbon instance."],
        ["logdir", "", None, "Write logs to the given directory."],
        ["whitelist", "", None, "List of metric patterns to allow."],
        ["blacklist", "", None, "List of metric patterns to disallow."],
        ]

    def postOptions(self):
        global settings

        program = self.parent.subCommand

        # Use provided pidfile (if any) as default for configuration. If it's
        # set to 'twistd.pid', that means no value was provided and the default
        # was used.
        pidfile = self.parent["pidfile"]
        if pidfile.endswith("twistd.pid"):
            pidfile = None
        self["pidfile"] = pidfile

        # Enforce a default umask of '022' if none was set.
        if not self.parent.has_key("umask") or self.parent["umask"] is None:
            self.parent["umask"] = 022

        # Read extra settings from the configuration file.
        program_settings = read_config(program, self)
        settings.update(program_settings)
        settings["program"] = program

        # Set process uid/gid by changing the parent config, if a user was
        # provided in the configuration file.
        if settings.USER:
            self.parent["uid"], self.parent["gid"] = (
                pwd.getpwnam(settings.USER)[2:4])

        # Set the pidfile in parent config to the value that was computed by
        # C{read_config}.
        self.parent["pidfile"] = settings["pidfile"]

        storage_schemas = join(settings["CONF_DIR"], "storage-schemas.conf")
        if not exists(storage_schemas):
            print "Error: missing required config %s" % storage_schemas
            sys.exit(1)

        if settings.WHISPER_AUTOFLUSH:
            log.msg("Enabling Whisper autoflush")
            whisper.AUTOFLUSH = True

        if settings.WHISPER_LOCK_WRITES:
            if whisper.CAN_LOCK:
                log.msg("Enabling Whisper file locking")
                whisper.LOCK = True
            else:
                log.err("WHISPER_LOCK_WRITES is enabled but import of fcntl module failed.")

        if not "action" in self:
            self["action"] = "start"
        self.handleAction()

        # If we are not running in debug mode or non-daemon mode, then log to a
        # directory, otherwise log output will go to stdout. If parent options
        # are set to log to syslog, then use that instead.
        if not self["debug"]:
            if self.parent.get("syslog", None):
                log.logToSyslog(self.parent["prefix"])
            elif not self.parent["nodaemon"]:
                logdir = settings.LOG_DIR
                if not isdir(logdir):
                    os.makedirs(logdir)
                log.logToDir(logdir)

        if self["whitelist"] is None:
            self["whitelist"] = join(settings["CONF_DIR"], "whitelist.conf")
        settings["whitelist"] = self["whitelist"]

        if self["blacklist"] is None:
            self["blacklist"] = join(settings["CONF_DIR"], "blacklist.conf")
        settings["blacklist"] = self["blacklist"]

    def parseArgs(self, *action):
        """If an action was provided, store it for further processing."""
        if len(action) == 1:
            self["action"] = action[0]

    def handleAction(self):
        """Handle extra argument for backwards-compatibility.

        * C{start} will simply do minimal pid checking and otherwise let twistd
              take over.
        * C{stop} will kill an existing running process if it matches the
              C{pidfile} contents.
        * C{status} will simply report if the process is up or not.
        """
        action = self["action"]
        pidfile = self.parent["pidfile"]
        program = settings["program"]
        instance = self["instance"]

        if action == "stop":
            if not exists(pidfile):
                print "Pidfile %s does not exist" % pidfile
                raise SystemExit(0)
            pf = open(pidfile, 'r')
            try:
                pid = int(pf.read().strip())
                pf.close()
            except:
                print "Could not read pidfile %s" % pidfile
                raise SystemExit(1)
            print "Sending kill signal to pid %d" % pid
            try:
                os.kill(pid, 15)
            except OSError, e:
                if e.errno == errno.ESRCH:
                    print "No process with pid %d running" % pid
                else:
                    raise

            raise SystemExit(0)

        elif action == "status":
            if not exists(pidfile):
                print "%s (instance %s) is not running" % (program, instance)
                raise SystemExit(1)
            pf = open(pidfile, "r")
            try:
                pid = int(pf.read().strip())
                pf.close()
            except:
                print "Failed to read pid from %s" % pidfile
                raise SystemExit(1)

            if _process_alive(pid):
                print ("%s (instance %s) is running with pid %d" %
                       (program, instance, pid))
                raise SystemExit(0)
            else:
                print "%s (instance %s) is not running" % (program, instance)
                raise SystemExit(1)

        elif action == "start":
            if exists(pidfile):
                pf = open(pidfile, 'r')
                try:
                    pid = int(pf.read().strip())
                    pf.close()
                except:
                    print "Could not read pidfile %s" % pidfile
                    raise SystemExit(1)
                if _process_alive(pid):
                    print ("%s (instance %s) is already running with pid %d" %
                           (program, instance, pid))
                    raise SystemExit(1)
                else:
                    print "Removing stale pidfile %s" % pidfile
                    try:
                        os.unlink(pidfile)
                    except:
                        print "Could not remove pidfile %s" % pidfile

            print "Starting %s (instance %s)" % (program, instance)

        else:
            print "Invalid action '%s'" % action
            print "Valid actions: start stop status"
            raise SystemExit(1)


class CarbonAggregatorOptions(CarbonCacheOptions):

    optParameters = [
        ["rules", "", None, "Use the given aggregation rules file."],
        ["rewrite-rules", "", None, "Use the given rewrite rules file."],
        ] + CarbonCacheOptions.optParameters

    def postOptions(self):
        CarbonCacheOptions.postOptions(self)
        if self["rules"] is None:
            self["rules"] = join(settings["CONF_DIR"], "aggregation-rules.conf")
        settings["aggregation-rules"] = self["rules"]

        if self["rewrite-rules"] is None:
            self["rewrite-rules"] = join(settings["CONF_DIR"],
                                         "rewrite-rules.conf")
        settings["rewrite-rules"] = self["rewrite-rules"]


class CarbonRelayOptions(CarbonCacheOptions):

    optParameters = [
        ["rules", "", None, "Use the given relay rules file."],
        ] + CarbonCacheOptions.optParameters

    def postOptions(self):
        CarbonCacheOptions.postOptions(self)
        if self["rules"] is None:
            self["rules"] = join(settings["CONF_DIR"], "relay-rules.conf")
        settings["relay-rules"] = self["rules"]

        if settings["RELAY_METHOD"] not in ("rules", "consistent-hashing"):
            print ("In carbon.conf, RELAY_METHOD must be either 'rules' or "
                   "'consistent-hashing'. Invalid value: '%s'" %
                   settings.RELAY_METHOD)
            sys.exit(1)


def get_default_parser(usage="%prog [options] <start|stop|status>"):
    """Create a parser for command line options."""
    parser = OptionParser(usage=usage)
    parser.add_option(
        "--debug", action="store_true",
        help="Run in the foreground, log to stdout")
    parser.add_option(
        "--profile",
        help="Record performance profile data to the given file")
    parser.add_option(
        "--pidfile", default=None,
        help="Write pid to the given file")
    parser.add_option(
        "--config",
        default=None,
        help="Use the given config file")
    parser.add_option(
      "--whitelist",
      default=None,
      help="Use the given whitelist file")
    parser.add_option(
      "--blacklist",
      default=None,
      help="Use the given blacklist file")
    parser.add_option(
        "--logdir",
        default=None,
        help="Write logs in the given directory")
    parser.add_option(
        "--instance",
        default='a',
        help="Manage a specific carbon instance")

    return parser


def get_parser(name):
    parser = get_default_parser()
    if name == "carbon-aggregator":
        parser.add_option(
            "--rules",
            default=None,
            help="Use the given aggregation rules file.")
        parser.add_option(
            "--rewrite-rules",
            default=None,
            help="Use the given rewrite rules file.")
    elif name == "carbon-relay":
        parser.add_option(
            "--rules",
            default=None,
            help="Use the given relay rules file.")
    return parser


def parse_options(parser, args):
    """
    Parse command line options and print usage message if no arguments were
    provided for the command.
    """
    (options, args) = parser.parse_args(args)

    if not args:
        parser.print_usage()
        raise SystemExit(1)

    if args[0] not in ("start", "stop", "status"):
        parser.print_usage()
        raise SystemExit(1)

    return options, args


def read_config(program, options, **kwargs):
    """
    Read settings for 'program' from configuration file specified by
    'options["config"]', with missing values provided by 'defaults'.
    """
    settings = Settings()
    settings.update(defaults)

    # Initialize default values if not set yet.
    for name, value in kwargs.items():
        settings.setdefault(name, value)

    graphite_root = os.environ['GRAPHITE_ROOT']

    # Default config directory to root-relative, unless overriden by the
    # 'GRAPHITE_CONF_DIR' environment variable.
    settings.setdefault("CONF_DIR",
                        os.environ.get("GRAPHITE_CONF_DIR",
                                       join(graphite_root, "conf")))
    if options["config"] is None:
        options["config"] = join(settings["CONF_DIR"], "carbon.conf")
    else:
        # Set 'CONF_DIR' to the parent directory of the 'carbon.conf' config
        # file.
        settings["CONF_DIR"] = dirname(normpath(options["config"]))

    # Storage directory can be overriden by the 'GRAPHITE_STORAGE_DIR'
    # environment variable. It defaults to a path relative to GRAPHITE_ROOT
    # for backwards compatibility though.
    settings.setdefault("STORAGE_DIR",
                        os.environ.get("GRAPHITE_STORAGE_DIR",
                                       join(graphite_root, "storage")))

    # By default, everything is written to subdirectories of the storage dir.
    settings.setdefault(
        "PID_DIR", settings["STORAGE_DIR"])
    settings.setdefault(
        "LOG_DIR", join(settings["STORAGE_DIR"], "log", program))
    settings.setdefault(
        "LOCAL_DATA_DIR", join(settings["STORAGE_DIR"], "whisper"))
    settings.setdefault(
        "WHITELISTS_DIR", join(settings["STORAGE_DIR"], "lists"))

    # Read configuration options from program-specific section.
    section = program[len("carbon-"):]
    config = options["config"]

    if not exists(config):
        print "Error: missing required config %s" % config
        sys.exit(1)

    settings.readFrom(config, section)
    settings.setdefault("instance", options["instance"])

    # If a specific instance of the program is specified, augment the settings
    # with the instance-specific settings and provide sane defaults for
    # optional settings.
    if options["instance"]:
        settings.readFrom(config,
                          "%s:%s" % (section, options["instance"]))
        settings["pidfile"] = (
            options["pidfile"] or
            join(settings["PID_DIR"], "%s-%s.pid" %
                 (program, options["instance"])))
        settings["LOG_DIR"] = (options["logdir"] or
                              join(settings["LOG_DIR"],
                                "%s-%s" % (program ,options["instance"])))
    else:
        settings["pidfile"] = (
            options["pidfile"] or
            join(settings["PID_DIR"], '%s.pid' % program))
        settings["LOG_DIR"] = (options["logdir"] or settings["LOG_DIR"])

    return settings

########NEW FILE########
__FILENAME__ = events
from twisted.python.failure import Failure


class Event:
  def __init__(self, name):
    self.name = name
    self.handlers = []

  def addHandler(self, handler):
    if handler not in self.handlers:
      self.handlers.append(handler)

  def removeHandler(self, handler):
    if handler in self.handlers:
      self.handlers.remove(handler)

  def __call__(self, *args, **kwargs):
    for handler in self.handlers:
      try:
        handler(*args, **kwargs)
      except:
        log.err(None, "Exception in %s event handler: args=%s kwargs=%s" % (self.name, args, kwargs))


metricReceived = Event('metricReceived')
metricGenerated = Event('metricGenerated')
cacheFull = Event('cacheFull')
cacheSpaceAvailable = Event('cacheSpaceAvailable')
pauseReceivingMetrics = Event('pauseReceivingMetrics')
resumeReceivingMetrics = Event('resumeReceivingMetrics')

# Default handlers
metricReceived.addHandler(lambda metric, datapoint: state.instrumentation.increment('metricsReceived'))

cacheFull.addHandler(lambda: state.instrumentation.increment('cache.overflow'))
cacheFull.addHandler(lambda: setattr(state, 'cacheTooFull', True))
cacheSpaceAvailable.addHandler(lambda: setattr(state, 'cacheTooFull', False))

pauseReceivingMetrics.addHandler(lambda: setattr(state, 'metricReceiversPaused', True))
resumeReceivingMetrics.addHandler(lambda: setattr(state, 'metricReceiversPaused', False))


# Avoid import circularities
from carbon import log, state

########NEW FILE########
__FILENAME__ = hashing
try:
  from hashlib import md5
except ImportError:
  from md5 import md5
import bisect
from carbon.conf import settings


class ConsistentHashRing:
  def __init__(self, nodes, replica_count=100):
    self.ring = []
    self.nodes = set()
    self.replica_count = replica_count
    for node in nodes:
      self.add_node(node)

  def compute_ring_position(self, key):
    big_hash = md5( str(key) ).hexdigest()
    small_hash = int(big_hash[:4], 16)
    return small_hash

  def add_node(self, node):
    self.nodes.add(node)
    for i in range(self.replica_count):
      replica_key = "%s:%d" % (node, i)
      position = self.compute_ring_position(replica_key)
      entry = (position, node)
      bisect.insort(self.ring, entry)

  def remove_node(self, node):
    self.nodes.discard(node)
    self.ring = [entry for entry in self.ring if entry[1] != node]

  def get_node(self, key):
    assert self.ring
    position = self.compute_ring_position(key)
    search_entry = (position, None)
    index = bisect.bisect_left(self.ring, search_entry) % len(self.ring)
    entry = self.ring[index]
    return entry[1]

  def get_nodes(self, key):
    nodes = []
    position = self.compute_ring_position(key)
    search_entry = (position, None)
    index = bisect.bisect_left(self.ring, search_entry) % len(self.ring)
    last_index = (index - 1) % len(self.ring)
    while len(nodes) < len(self.nodes) and index != last_index:
      next_entry = self.ring[index]
      (position, next_node) = next_entry
      if next_node not in nodes:
        nodes.append(next_node)

      index = (index + 1) % len(self.ring)

    return nodes

########NEW FILE########
__FILENAME__ = instrumentation
import os
import time
import socket
from resource import getrusage, RUSAGE_SELF

from twisted.application.service import Service
from twisted.internet.task import LoopingCall
from carbon.conf import settings


stats = {}
HOSTNAME = socket.gethostname().replace('.','_')
PAGESIZE = os.sysconf('SC_PAGESIZE')
rusage = getrusage(RUSAGE_SELF)
lastUsage = rusage.ru_utime + rusage.ru_stime
lastUsageTime = time.time()

# TODO(chrismd) refactor the graphite metrics hierarchy to be cleaner,
# more consistent, and make room for frontend metrics.
#metric_prefix = "Graphite.backend.%(program)s.%(instance)s." % settings


def increment(stat, increase=1):
  try:
    stats[stat] += increase
  except KeyError:
    stats[stat] = increase


def append(stat, value):
  try:
    stats[stat].append(value)
  except KeyError:
    stats[stat] = [value]


def getCpuUsage():
  global lastUsage, lastUsageTime

  rusage = getrusage(RUSAGE_SELF)
  currentUsage = rusage.ru_utime + rusage.ru_stime
  currentTime = time.time()

  usageDiff = currentUsage - lastUsage
  timeDiff = currentTime - lastUsageTime

  if timeDiff == 0: #shouldn't be possible, but I've actually seen a ZeroDivisionError from this
    timeDiff = 0.000001

  cpuUsagePercent = (usageDiff / timeDiff) * 100.0

  lastUsage = currentUsage
  lastUsageTime = currentTime

  return cpuUsagePercent


def getMemUsage():
  rss_pages = int( open('/proc/self/statm').read().split()[1] )
  return rss_pages * PAGESIZE


def recordMetrics():
  global lastUsage
  myStats = stats.copy()
  stats.clear()

  # cache metrics
  if settings.program == 'carbon-cache':
    record = cache_record
    updateTimes = myStats.get('updateTimes', [])
    committedPoints = myStats.get('committedPoints', 0)
    creates = myStats.get('creates', 0)
    errors = myStats.get('errors', 0)
    cacheQueries = myStats.get('cacheQueries', 0)
    cacheOverflow = myStats.get('cache.overflow', 0)

    if updateTimes:
      avgUpdateTime = sum(updateTimes) / len(updateTimes)
      record('avgUpdateTime', avgUpdateTime)

    if committedPoints:
      pointsPerUpdate = float(committedPoints) / len(updateTimes)
      record('pointsPerUpdate', pointsPerUpdate)

    record('updateOperations', len(updateTimes))
    record('committedPoints', committedPoints)
    record('creates', creates)
    record('errors', errors)
    record('cache.queries', cacheQueries)
    record('cache.queues', len(cache.MetricCache))
    record('cache.size', cache.MetricCache.size)
    record('cache.overflow', cacheOverflow)

  # aggregator metrics
  elif settings.program == 'carbon-aggregator':
    record = aggregator_record
    record('allocatedBuffers', len(BufferManager))
    record('bufferedDatapoints',
           sum([b.size for b in BufferManager.buffers.values()]))
    record('aggregateDatapointsSent', myStats.get('aggregateDatapointsSent', 0))

  # relay metrics
  else:
    record = relay_record

  # common metrics
  record('metricsReceived', myStats.get('metricsReceived', 0))
  record('cpuUsage', getCpuUsage())
  try: # This only works on Linux
    record('memUsage', getMemUsage())
  except:
    pass


def cache_record(metric, value):
    if settings.instance is None:
      fullMetric = 'carbon.agents.%s.%s' % (HOSTNAME, metric)
    else:
      fullMetric = 'carbon.agents.%s-%s.%s' % (HOSTNAME, settings.instance, metric)
    datapoint = (time.time(), value)
    cache.MetricCache.store(fullMetric, datapoint)

def relay_record(metric, value):
    if settings.instance is None:
      fullMetric = 'carbon.relays.%s.%s' % (HOSTNAME, metric)
    else:
      fullMetric = 'carbon.relays.%s-%s.%s' % (HOSTNAME, settings.instance, metric)
    datapoint = (time.time(), value)
    events.metricGenerated(fullMetric, datapoint)

def aggregator_record(metric, value):
    if settings.instance is None:
      fullMetric = 'carbon.aggregator.%s.%s' % (HOSTNAME, metric)
    else:
      fullMetric = 'carbon.aggregator.%s-%s.%s' % (HOSTNAME, settings.instance, metric)
    datapoint = (time.time(), value)
    events.metricGenerated(fullMetric, datapoint)


class InstrumentationService(Service):
    def __init__(self):
        self.record_task = LoopingCall(recordMetrics)

    def startService(self):
        self.record_task.start(60, False)
        Service.startService(self)

    def stopService(self):
        self.record_task.stop()
        Service.stopService(self)


# Avoid import circularities
from carbon import state, events, cache
from carbon.aggregator.buffers import BufferManager

########NEW FILE########
__FILENAME__ = log
import time
from sys import stdout, stderr
from zope.interface import implements
from twisted.python.log import startLoggingWithObserver, textFromEventDict, msg, err, ILogObserver
from twisted.python.syslog import SyslogObserver
from twisted.python.logfile import DailyLogFile

class CarbonLogObserver(object):
  implements(ILogObserver)

  def log_to_dir(self, logdir):
    self.logdir = logdir
    self.console_logfile = DailyLogFile('console.log', logdir)
    self.custom_logs = {}
    self.observer = self.logdir_observer

  def log_to_syslog(self, prefix):
    observer = SyslogObserver(prefix).emit
    def syslog_observer(event):
      event["system"] = event.get("type", "console")
      observer(event)
    self.observer = syslog_observer

  def __call__(self, event):
    return self.observer(event)

  def stdout_observer(self, event):
    stdout.write( formatEvent(event, includeType=True) + '\n' )
    stdout.flush()

  def logdir_observer(self, event):
    message = formatEvent(event)
    log_type = event.get('type')

    if log_type is not None and log_type not in self.custom_logs:
      self.custom_logs[log_type] = DailyLogFile(log_type + '.log', self.logdir)

    logfile = self.custom_logs.get(log_type, self.console_logfile)
    logfile.write(message + '\n')
    logfile.flush()

  # Default to stdout
  observer = stdout_observer
   

carbonLogObserver = CarbonLogObserver()


def formatEvent(event, includeType=False):
  event['isError'] = 'failure' in event
  message = textFromEventDict(event)

  if includeType:
    typeTag = '[%s] ' % event.get('type', 'console')
  else:
    typeTag = ''

  timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
  return "%s :: %s%s" % (timestamp, typeTag, message)


logToDir = carbonLogObserver.log_to_dir

logToSyslog = carbonLogObserver.log_to_syslog

def logToStdout():
  startLoggingWithObserver(carbonLogObserver)

def cache(message, **context):
  context['type'] = 'cache'
  msg(message, **context)

def clients(message, **context):
  context['type'] = 'clients'
  msg(message, **context)

def creates(message, **context):
  context['type'] = 'creates'
  msg(message, **context)

def updates(message, **context):
  context['type'] = 'updates'
  msg(message, **context)

def listener(message, **context):
  context['type'] = 'listener'
  msg(message, **context)

def relay(message, **context):
  context['type'] = 'relay'
  msg(message, **context)

def aggregator(message, **context):
  context['type'] = 'aggregator'
  msg(message, **context)

def query(message, **context):
  context['type'] = 'query'
  msg(message, **context)

def debug(message, **context):
  if debugEnabled:
    msg(message, **context)

debugEnabled = False
def setDebugEnabled(enabled):
  global debugEnabled
  debugEnabled = enabled

########NEW FILE########
__FILENAME__ = management
import traceback
import whisper
from carbon import log
from carbon.storage import getFilesystemPath



def getMetadata(metric, key):
  if key != 'aggregationMethod':
    return dict(error="Unsupported metadata key \"%s\"" % key)

  wsp_path = getFilesystemPath(metric)
  try:
    value = whisper.info(wsp_path)['aggregationMethod']
    return dict(value=value)
  except:
    log.err()
    return dict(error=traceback.format_exc())


def setMetadata(metric, key, value):
  if key != 'aggregationMethod':
    return dict(error="Unsupported metadata key \"%s\"" % key)

  wsp_path = getFilesystemPath(metric)
  try:
    old_value = whisper.setAggregationMethod(wsp_path, value)
    return dict(old_value=old_value, new_value=value)
  except:
    log.err()
    return dict(error=traceback.format_exc())

########NEW FILE########
__FILENAME__ = manhole
from twisted.cred import portal, checkers
from twisted.conch.ssh import keys
from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.conch.manhole import Manhole
from twisted.conch.manhole_ssh import TerminalRealm, ConchFactory
from twisted.internet import reactor
from carbon.conf import settings


namespace = {}


class PublicKeyChecker(SSHPublicKeyDatabase):
  def __init__(self, userKeys):
    self.userKeys = {}
    for username, keyData in userKeys.items():
      self.userKeys[username] = keys.Key.fromString(data=keyData).blob()

  def checkKey(self, credentials):
    if credentials.username in self.userKeys:
      keyBlob = self.userKeys[credentials.username]
      return keyBlob == credentials.blob

def createManholeListener():
  sshRealm = TerminalRealm()
  sshRealm.chainedProtocolFactory.protocolFactory = lambda _: Manhole(namespace)

  # You can uncomment this if you're lazy and want insecure authentication instead
  # of setting up keys.
  #credChecker = checkers.InMemoryUsernamePasswordDatabaseDontUse(carbon='')
  userKeys = {
    settings.MANHOLE_USER : settings.MANHOLE_PUBLIC_KEY,
  }
  credChecker = PublicKeyChecker(userKeys)

  sshPortal = portal.Portal(sshRealm)
  sshPortal.registerChecker(credChecker)
  sessionFactory = ConchFactory(sshPortal)
  return sessionFactory

def start():
    sessionFactory = createManholeListener()
    reactor.listenTCP(settings.MANHOLE_PORT, sessionFactory, interface=settings.MANHOLE_INTERFACE)

########NEW FILE########
__FILENAME__ = protocols
from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.error import ConnectionDone
from twisted.protocols.basic import LineOnlyReceiver, Int32StringReceiver
from carbon import log, events, state, management
from carbon.conf import settings
from carbon.regexlist import WhiteList, BlackList
from carbon.util import pickle, get_unpickler


class MetricReceiver:
  """ Base class for all metric receiving protocols, handles flow
  control events and connection state logging.
  """
  def connectionMade(self):
    self.peerName = self.getPeerName()
    log.listener("%s connection with %s established" % (self.__class__.__name__, self.peerName))

    if state.metricReceiversPaused:
      self.pauseReceiving()

    state.connectedMetricReceiverProtocols.add(self)
    events.pauseReceivingMetrics.addHandler(self.pauseReceiving)
    events.resumeReceivingMetrics.addHandler(self.resumeReceiving)

  def getPeerName(self):
    if hasattr(self.transport, 'getPeer'):
      peer = self.transport.getPeer()
      return "%s:%d" % (peer.host, peer.port)
    else:
      return "peer"

  def pauseReceiving(self):
    self.transport.pauseProducing()

  def resumeReceiving(self):
    self.transport.resumeProducing()

  def connectionLost(self, reason):
    if reason.check(ConnectionDone):
      log.listener("%s connection with %s closed cleanly" % (self.__class__.__name__, self.peerName))
    else:
      log.listener("%s connection with %s lost: %s" % (self.__class__.__name__, self.peerName, reason.value))

    state.connectedMetricReceiverProtocols.remove(self)
    events.pauseReceivingMetrics.removeHandler(self.pauseReceiving)
    events.resumeReceivingMetrics.removeHandler(self.resumeReceiving)

  def metricReceived(self, metric, datapoint):
    if BlackList and metric in BlackList:
      instrumentation.increment('blacklistMatches')
      return
    if WhiteList and metric not in WhiteList:
      instrumentation.increment('whitelistRejects')
      return
    if datapoint[1] == datapoint[1]: # filter out NaN values
      events.metricReceived(metric, datapoint)


class MetricLineReceiver(MetricReceiver, LineOnlyReceiver):
  delimiter = '\n'

  def lineReceived(self, line):
    try:
      metric, value, timestamp = line.strip().split()
      datapoint = ( float(timestamp), float(value) )
    except:
      log.listener('invalid line received from client %s, ignoring' % self.peerName)
      return

    self.metricReceived(metric, datapoint)


class MetricDatagramReceiver(MetricReceiver, DatagramProtocol):
  def datagramReceived(self, data, (host, port)):
    for line in data.splitlines():
      try:
        metric, value, timestamp = line.strip().split()
        datapoint = ( float(timestamp), float(value) )

        self.metricReceived(metric, datapoint)
      except:
        log.listener('invalid line received from %s, ignoring' % host)


class MetricPickleReceiver(MetricReceiver, Int32StringReceiver):
  MAX_LENGTH = 2 ** 20

  def connectionMade(self):
    MetricReceiver.connectionMade(self)
    self.unpickler = get_unpickler(insecure=settings.USE_INSECURE_UNPICKLER)

  def stringReceived(self, data):
    try:
      datapoints = self.unpickler.loads(data)
    except:
      log.listener('invalid pickle received from %s, ignoring' % self.peerName)
      return

    for (metric, datapoint) in datapoints:
      try:
        datapoint = ( float(datapoint[0]), float(datapoint[1]) ) #force proper types
      except:
        continue

      self.metricReceived(metric, datapoint)


class CacheManagementHandler(Int32StringReceiver):
  def connectionMade(self):
    peer = self.transport.getPeer()
    self.peerAddr = "%s:%d" % (peer.host, peer.port)
    log.query("%s connected" % self.peerAddr)
    self.unpickler = get_unpickler(insecure=settings.USE_INSECURE_UNPICKLER)

  def connectionLost(self, reason):
    if reason.check(ConnectionDone):
      log.query("%s disconnected" % self.peerAddr)
    else:
      log.query("%s connection lost: %s" % (self.peerAddr, reason.value))

  def stringReceived(self, rawRequest):
    request = self.unpickler.loads(rawRequest)
    if request['type'] == 'cache-query':
      metric = request['metric']
      datapoints = MetricCache.get(metric, [])
      result = dict(datapoints=datapoints)
      log.query('[%s] cache query for \"%s\" returned %d values' % (self.peerAddr, metric, len(datapoints)))
      instrumentation.increment('cacheQueries')

    elif request['type'] == 'get-metadata':
      result = management.getMetadata(request['metric'], request['key'])

    elif request['type'] == 'set-metadata':
      result = management.setMetadata(request['metric'], request['key'], request['value'])

    else:
      result = dict(error="Invalid request type \"%s\"" % request['type'])

    response = pickle.dumps(result, protocol=-1)
    self.sendString(response)


# Avoid import circularities
from carbon.cache import MetricCache
from carbon import instrumentation

########NEW FILE########
__FILENAME__ = regexlist
import time
import re
import os.path
from carbon import log
from twisted.internet.task import LoopingCall


class RegexList:
  """ Maintain a list of regex for matching whitelist and blacklist """

  def __init__(self):
    self.regex_list = []
    self.list_file = None
    self.read_task = LoopingCall(self.read_list)
    self.rules_last_read = 0.0

  def read_from(self, list_file):
    self.list_file = list_file
    self.read_list()
    self.read_task.start(10, now=False)

  def read_list(self):
    # Clear rules and move on if file isn't there
    if not os.path.exists(self.list_file):
      self.regex_list = []
      return

    try:
      mtime = os.path.getmtime(self.list_file)
    except:
      log.err("Failed to get mtime of %s" % self.list_file)
      return

    if mtime <= self.rules_last_read:
      return

    # Begin read
    new_regex_list = []
    for line in open(self.list_file):
      pattern = line.strip()
      if line.startswith('#') or not line:
        continue
      try:
        new_regex_list.append(re.compile(pattern))
      except:
        log.err("Failed to parse '%s' in '%s'. Ignoring line" % (pattern, self.list_file))

    self.regex_list = new_regex_list
    self.rules_last_read = mtime

  def __contains__(self, value):
    for regex in self.regex_list:
      if regex.search(value):
        return True
    return False

  def __nonzero__(self):
    return bool(self.regex_list)


WhiteList = RegexList()
BlackList = RegexList()

########NEW FILE########
__FILENAME__ = relayrules
import re
from carbon.conf import OrderedConfigParser
from carbon.util import parseDestinations


class RelayRule:
  def __init__(self, condition, destinations, continue_matching=False):
    self.condition = condition
    self.destinations = destinations
    self.continue_matching = continue_matching

  def matches(self, metric):
    return bool( self.condition(metric) )


def loadRelayRules(path):
  rules = []
  parser = OrderedConfigParser()

  if not parser.read(path):
    raise Exception("Could not read rules file %s" % path)

  defaultRule = None
  for section in parser.sections():
    if not parser.has_option(section, 'destinations'):
      raise ValueError("Rules file %s section %s does not define a "
                       "'destinations' list" % (path, section))

    destination_strings = parser.get(section, 'destinations').split(',')
    destinations = parseDestinations(destination_strings)

    if parser.has_option(section, 'pattern'):
      if parser.has_option(section, 'default'):
        raise Exception("Section %s contains both 'pattern' and "
                        "'default'. You must use one or the other." % section)
      pattern = parser.get(section, 'pattern')
      regex = re.compile(pattern, re.I)

      continue_matching = False
      if parser.has_option(section, 'continue'):
        continue_matching = parser.getboolean(section, 'continue')
      rule = RelayRule(condition=regex.search, destinations=destinations, continue_matching=continue_matching)
      rules.append(rule)
      continue

    if parser.has_option(section, 'default'):
      if not parser.getboolean(section, 'default'):
        continue # just ignore default = false
      if defaultRule:
        raise Exception("Only one default rule can be specified")
      defaultRule = RelayRule(condition=lambda metric: True,
                              destinations=destinations)

  if not defaultRule:
    raise Exception("No default rule defined. You must specify exactly one "
                    "rule with 'default = true' instead of a pattern.")

  rules.append(defaultRule)
  return rules

########NEW FILE########
__FILENAME__ = rewrite
import time
import re
from os.path import exists, getmtime
from twisted.internet.task import LoopingCall
from carbon import log


class RewriteRuleManager:
  def __init__(self):
    self.preRules = []
    self.postRules = []
    self.read_task = LoopingCall(self.read_rules)
    self.rules_last_read = 0.0

  def clear(self):
    self.preRules = []
    self.postRules = []

  def read_from(self, rules_file):
    self.rules_file = rules_file
    self.read_rules()
    self.read_task.start(10, now=False)

  def read_rules(self):
    if not exists(self.rules_file):
      self.clear()
      return

    # Only read if the rules file has been modified
    try:
      mtime = getmtime(self.rules_file)
    except:
      log.err("Failed to get mtime of %s" % self.rules_file)
      return
    if mtime <= self.rules_last_read:
      return

    pre = []
    post = []

    section = None
    for line in open(self.rules_file):
      line = line.strip()
      if line.startswith('#') or not line:
        continue

      if line.startswith('[') and line.endswith(']'):
        section = line[1:-1].lower()

      else:
        pattern, replacement = line.split('=', 1)
        pattern, replacement = pattern.strip(), replacement.strip()
        rule = RewriteRule(pattern, replacement)

        if section == 'pre':
          pre.append(rule)
        elif section == 'post':
          post.append(rule)

    self.preRules = pre
    self.postRules = post
    self.rules_last_read = mtime


class RewriteRule:
  def __init__(self, pattern, replacement):
    self.pattern = pattern
    self.replacement = replacement
    self.regex = re.compile(pattern)

  def apply(self, metric):
    return self.regex.sub(self.replacement, metric)


# Ghetto singleton
RewriteRuleManager = RewriteRuleManager()

########NEW FILE########
__FILENAME__ = routers
import imp
from carbon.relayrules import loadRelayRules
from carbon.hashing import ConsistentHashRing


class DatapointRouter:
  "Interface for datapoint routing logic implementations"

  def addDestination(self, destination):
    "destination is a (host, port, instance) triple"

  def removeDestination(self, destination):
    "destination is a (host, port, instance) triple"

  def getDestinations(self, key):
    """Generate the destinations where the given routing key should map to. Only
    destinations which are configured (addDestination has been called for it)
    may be generated by this method."""


class RelayRulesRouter(DatapointRouter):
  def __init__(self, rules_path):
    self.rules_path = rules_path
    self.rules = loadRelayRules(rules_path)
    self.destinations = set()

  def addDestination(self, destination):
    self.destinations.add(destination)

  def removeDestination(self, destination):
    self.destinations.discard(destination)

  def getDestinations(self, key):
    for rule in self.rules:
      if rule.matches(key):
        for destination in rule.destinations:
          if destination in self.destinations:
            yield destination
        if not rule.continue_matching:
          return


class ConsistentHashingRouter(DatapointRouter):
  def __init__(self, replication_factor=1):
    self.replication_factor = int(replication_factor)
    self.instance_ports = {} # { (server, instance) : port }
    self.ring = ConsistentHashRing([])

  def addDestination(self, destination):
    (server, port, instance) = destination
    if (server, instance) in self.instance_ports:
      raise Exception("destination instance (%s, %s) already configured" % (server, instance))
    self.instance_ports[ (server, instance) ] = port
    self.ring.add_node( (server, instance) )

  def removeDestination(self, destination):
    (server, port, instance) = destination
    if (server, instance) not in self.instance_ports:
      raise Exception("destination instance (%s, %s) not configured" % (server, instance))
    del self.instance_ports[ (server, instance) ]
    self.ring.remove_node( (server, instance) )

  def getDestinations(self, metric):
    key = self.getKey(metric)

    used_servers = set()
    for (server, instance) in self.ring.get_nodes(key):
      if server in used_servers:
        continue
      else:
        used_servers.add(server)
        port = self.instance_ports[ (server, instance) ]
        yield (server, port, instance)

      if len(used_servers) >= self.replication_factor:
        return

  def getKey(self, metric):
    return metric

  def setKeyFunction(self, func):
    self.getKey = func

  def setKeyFunctionFromModule(self, keyfunc_spec):
    module_path, func_name = keyfunc_spec.rsplit(':', 1)
    module_file = open(module_path, 'U')
    description = ('.py', 'U', imp.PY_SOURCE)
    module = imp.load_module('keyfunc_module', module_file, module_path, description)
    keyfunc = getattr(module, func_name)
    self.setKeyFunction(keyfunc)

########NEW FILE########
__FILENAME__ = service
#!/usr/bin/env python
"""Copyright 2009 Chris Davis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from os.path import exists

from twisted.application.service import MultiService
from twisted.application.internet import TCPServer, TCPClient, UDPServer
from twisted.internet.protocol import ServerFactory
from twisted.python.components import Componentized
from twisted.python.log import ILogObserver
# Attaching modules to the global state module simplifies import order hassles
from carbon import util, state, events, instrumentation
from carbon.log import carbonLogObserver
state.events = events
state.instrumentation = instrumentation


class CarbonRootService(MultiService):
  """Root Service that properly configures twistd logging"""

  def setServiceParent(self, parent):
    MultiService.setServiceParent(self, parent)
    if isinstance(parent, Componentized):
      parent.setComponent(ILogObserver, carbonLogObserver)



def createBaseService(config):
    from carbon.conf import settings
    from carbon.protocols import (MetricLineReceiver, MetricPickleReceiver,
                                  MetricDatagramReceiver)

    root_service = CarbonRootService()
    root_service.setName(settings.program)

    use_amqp = settings.get("ENABLE_AMQP", False)
    if use_amqp:
        from carbon import amqp_listener

        amqp_host = settings.get("AMQP_HOST", "localhost")
        amqp_port = settings.get("AMQP_PORT", 5672)
        amqp_user = settings.get("AMQP_USER", "guest")
        amqp_password = settings.get("AMQP_PASSWORD", "guest")
        amqp_verbose  = settings.get("AMQP_VERBOSE", False)
        amqp_vhost    = settings.get("AMQP_VHOST", "/")
        amqp_spec     = settings.get("AMQP_SPEC", None)
        amqp_exchange_name = settings.get("AMQP_EXCHANGE", "graphite")


    for interface, port, protocol in ((settings.LINE_RECEIVER_INTERFACE,
                                       settings.LINE_RECEIVER_PORT,
                                       MetricLineReceiver),
                                      (settings.PICKLE_RECEIVER_INTERFACE,
                                       settings.PICKLE_RECEIVER_PORT,
                                       MetricPickleReceiver)):
        if port:
            factory = ServerFactory()
            factory.protocol = protocol
            service = TCPServer(int(port), factory, interface=interface)
            service.setServiceParent(root_service)

    if settings.ENABLE_UDP_LISTENER:
        service = UDPServer(int(settings.UDP_RECEIVER_PORT),
                            MetricDatagramReceiver(),
                            interface=settings.UDP_RECEIVER_INTERFACE)
        service.setServiceParent(root_service)

    if use_amqp:
        factory = amqp_listener.createAMQPListener(
            amqp_user, amqp_password,
            vhost=amqp_vhost, spec=amqp_spec,
            exchange_name=amqp_exchange_name,
            verbose=amqp_verbose)
        service = TCPClient(amqp_host, int(amqp_port), factory)
        service.setServiceParent(root_service)

    if settings.ENABLE_MANHOLE:
        from carbon import manhole

        factory = manhole.createManholeListener()
        service = TCPServer(int(settings.MANHOLE_PORT), factory,
                            interface=settings.MANHOLE_INTERFACE)
        service.setServiceParent(root_service)

    if settings.USE_WHITELIST:
      from carbon.regexlist import WhiteList,BlackList
      WhiteList.read_from(settings["whitelist"])
      BlackList.read_from(settings["blacklist"])

    # Instantiate an instrumentation service that will record metrics about
    # this service.
    from carbon.instrumentation import InstrumentationService

    service = InstrumentationService()
    service.setServiceParent(root_service)

    return root_service


def createCacheService(config):
    from carbon.cache import MetricCache
    from carbon.conf import settings
    from carbon.protocols import CacheManagementHandler

    # Configure application components
    events.metricReceived.addHandler(MetricCache.store)

    root_service = createBaseService(config)
    factory = ServerFactory()
    factory.protocol = CacheManagementHandler
    service = TCPServer(int(settings.CACHE_QUERY_PORT), factory,
                        interface=settings.CACHE_QUERY_INTERFACE)
    service.setServiceParent(root_service)

    # have to import this *after* settings are defined
    from carbon.writer import WriterService

    service = WriterService()
    service.setServiceParent(root_service)

    if settings.USE_FLOW_CONTROL:
      events.cacheFull.addHandler(events.pauseReceivingMetrics)
      events.cacheSpaceAvailable.addHandler(events.resumeReceivingMetrics)

    return root_service


def createAggregatorService(config):
    from carbon.aggregator import receiver
    from carbon.aggregator.rules import RuleManager
    from carbon.routers import ConsistentHashingRouter
    from carbon.client import CarbonClientManager
    from carbon.rewrite import RewriteRuleManager
    from carbon.conf import settings
    from carbon import events

    root_service = createBaseService(config)

    # Configure application components
    router = ConsistentHashingRouter()
    client_manager = CarbonClientManager(router)
    client_manager.setServiceParent(root_service)

    events.metricReceived.addHandler(receiver.process)
    events.metricGenerated.addHandler(client_manager.sendDatapoint)

    RuleManager.read_from(settings["aggregation-rules"])
    if exists(settings["rewrite-rules"]):
        RewriteRuleManager.read_from(settings["rewrite-rules"])

    if not settings.DESTINATIONS:
      raise Exception("Required setting DESTINATIONS is missing from carbon.conf")

    for destination in util.parseDestinations(settings.DESTINATIONS):
      client_manager.startClient(destination)

    return root_service


def createRelayService(config):
    from carbon.routers import RelayRulesRouter, ConsistentHashingRouter
    from carbon.client import CarbonClientManager
    from carbon.conf import settings
    from carbon import events

    root_service = createBaseService(config)

    # Configure application components
    if settings.RELAY_METHOD == 'rules':
      router = RelayRulesRouter(settings["relay-rules"])
    elif settings.RELAY_METHOD == 'consistent-hashing':
      router = ConsistentHashingRouter(settings.REPLICATION_FACTOR)

    client_manager = CarbonClientManager(router)
    client_manager.setServiceParent(root_service)

    events.metricReceived.addHandler(client_manager.sendDatapoint)
    events.metricGenerated.addHandler(client_manager.sendDatapoint)

    if not settings.DESTINATIONS:
      raise Exception("Required setting DESTINATIONS is missing from carbon.conf")

    for destination in util.parseDestinations(settings.DESTINATIONS):
      client_manager.startClient(destination)

    return root_service

########NEW FILE########
__FILENAME__ = state
__doc__ = """
This module exists for the purpose of tracking global state used across
several modules.
"""

metricReceiversPaused = False
cacheTooFull = False
connectedMetricReceiverProtocols = set()

########NEW FILE########
__FILENAME__ = storage
"""Copyright 2009 Chris Davis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import os, re
import whisper

from os.path import join, exists
from carbon.conf import OrderedConfigParser, settings
from carbon.util import pickle
from carbon import log


STORAGE_SCHEMAS_CONFIG = join(settings.CONF_DIR, 'storage-schemas.conf')
STORAGE_AGGREGATION_CONFIG = join(settings.CONF_DIR, 'storage-aggregation.conf')
STORAGE_LISTS_DIR = join(settings.CONF_DIR, 'lists')

def getFilesystemPath(metric):
  return join(settings.LOCAL_DATA_DIR, metric.replace('.','/')) + '.wsp'


class Schema:
  def test(self, metric):
    raise NotImplementedError()

  def matches(self, metric):
    return bool( self.test(metric) )


class DefaultSchema(Schema):

  def __init__(self, name, archives):
    self.name = name
    self.archives = archives

  def test(self, metric):
    return True


class PatternSchema(Schema):

  def __init__(self, name, pattern, archives):
    self.name = name
    self.pattern = pattern
    self.regex = re.compile(pattern)
    self.archives = archives

  def test(self, metric):
    return self.regex.search(metric)


class ListSchema(Schema):

  def __init__(self, name, listName, archives):
    self.name = name
    self.listName = listName
    self.archives = archives
    self.path = join(settings.WHITELISTS_DIR, listName)

    if exists(self.path):
      self.mtime = os.stat(self.path).st_mtime
      fh = open(self.path, 'rb')
      self.members = pickle.load(fh)
      fh.close()

    else:
      self.mtime = 0
      self.members = frozenset()

  def test(self, metric):
    if exists(self.path):
      current_mtime = os.stat(self.path).st_mtime

      if current_mtime > self.mtime:
        self.mtime = current_mtime
        fh = open(self.path, 'rb')
        self.members = pickle.load(fh)
        fh.close()

    return metric in self.members


class Archive:

  def __init__(self,secondsPerPoint,points):
    self.secondsPerPoint = int(secondsPerPoint)
    self.points = int(points)

  def __str__(self):
    return "Archive = (Seconds per point: %d, Datapoints to save: %d)" % (self.secondsPerPoint, self.points) 

  def getTuple(self):
    return (self.secondsPerPoint,self.points)

  @staticmethod
  def fromString(retentionDef):
    (secondsPerPoint, points) = whisper.parseRetentionDef(retentionDef)
    return Archive(secondsPerPoint, points)


def loadStorageSchemas():
  schemaList = []
  config = OrderedConfigParser()
  config.read(STORAGE_SCHEMAS_CONFIG)

  for section in config.sections():
    options = dict( config.items(section) )
    matchAll = options.get('match-all')
    pattern = options.get('pattern')
    listName = options.get('list')

    retentions = options['retentions'].split(',')
    archives = [ Archive.fromString(s) for s in retentions ]
    
    if matchAll:
      mySchema = DefaultSchema(section, archives)

    elif pattern:
      mySchema = PatternSchema(section, pattern, archives)

    elif listName:
      mySchema = ListSchema(section, listName, archives)
    
    archiveList = [a.getTuple() for a in archives]

    try:
      whisper.validateArchiveList(archiveList)
      schemaList.append(mySchema)
    except InvalidConfiguration, e:
      log.msg("Invalid schemas found in %s: %s" % (section, e.message) )
  
  schemaList.append(defaultSchema)
  return schemaList


def loadAggregationSchemas():
  # NOTE: This abuses the Schema classes above, and should probably be refactored.
  schemaList = []
  config = OrderedConfigParser()

  try:
    config.read(STORAGE_AGGREGATION_CONFIG)
  except IOError:
    log.msg("%s not found, ignoring." % STORAGE_AGGREGATION_CONFIG)

  for section in config.sections():
    options = dict( config.items(section) )
    matchAll = options.get('match-all')
    pattern = options.get('pattern')
    listName = options.get('list')

    xFilesFactor = options.get('xfilesfactor')
    aggregationMethod = options.get('aggregationmethod')

    try:
      if xFilesFactor is not None:
        xFilesFactor = float(xFilesFactor)
        assert 0 <= xFilesFactor <= 1
      if aggregationMethod is not None:
        assert aggregationMethod in whisper.aggregationMethods
    except:
      log.msg("Invalid schemas found in %s." % section )
      continue

    archives = (xFilesFactor, aggregationMethod)

    if matchAll:
      mySchema = DefaultSchema(section, archives)

    elif pattern:
      mySchema = PatternSchema(section, pattern, archives)

    elif listName:
      mySchema = ListSchema(section, listName, archives)

    schemaList.append(mySchema)

  schemaList.append(defaultAggregation)
  return schemaList

defaultArchive = Archive(60, 60 * 24 * 7) #default retention for unclassified data (7 days of minutely data)
defaultSchema = DefaultSchema('default', [defaultArchive])
defaultAggregation = DefaultSchema('default', (None, None))

########NEW FILE########
__FILENAME__ = test_conf
import os
from os import makedirs
from os.path import dirname, join
from unittest import TestCase
from mocker import MockerTestCase
from carbon.conf import get_default_parser, parse_options, read_config


class FakeParser(object):

    def __init__(self):
        self.called = []

    def parse_args(self, args):
        return object(), args

    def print_usage(self):
        self.called.append("print_usage")


class FakeOptions(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class DefaultParserTest(TestCase):

    def test_default_parser(self):
        """Check default parser settings."""
        parser = get_default_parser()
        self.assertTrue(parser.has_option("--debug"))
        self.assertEqual(None, parser.defaults["debug"])
        self.assertTrue(parser.has_option("--profile"))
        self.assertEqual(None, parser.defaults["profile"])
        self.assertTrue(parser.has_option("--pidfile"))
        self.assertEqual(None, parser.defaults["pidfile"])
        self.assertTrue(parser.has_option("--config"))
        self.assertEqual(None, parser.defaults["config"])
        self.assertTrue(parser.has_option("--logdir"))
        self.assertEqual(None, parser.defaults["logdir"])
        self.assertTrue(parser.has_option("--instance"))
        self.assertEqual(None, parser.defaults["instance"])


class ParseOptionsTest(TestCase):

    def test_no_args_prints_usage_and_exit(self):
        """
        If no arguments are provided, the usage help will be printed and a
        SystemExit exception will be raised.
        """
        parser = FakeParser()
        self.assertRaises(SystemExit, parse_options, parser, ())
        self.assertEqual(["print_usage"], parser.called)

    def test_no_valid_args_prints_usage_and_exit(self):
        """
        If an argument which isn't a valid command was provided, 'print_usage'
        will be called and a SystemExit exception will be raised.
        """
        parser = FakeParser()
        self.assertRaises(SystemExit, parse_options, parser, ("bazinga!",))
        self.assertEqual(["print_usage"], parser.called)

    def test_valid_args(self):
        """
        If a valid argument is provided, it will be returned along with
        options.
        """
        parser = FakeParser()
        options, args = parser.parse_args(("start",))
        self.assertEqual(("start",), args)


class ReadConfigTest(MockerTestCase):

    def test_root_dir_is_required(self):
        """
        At minimum, the caller must provide a 'ROOT_DIR' setting.
        """
        try:
            read_config("carbon-foo", FakeOptions())
        except ValueError, e:
            self.assertEqual("ROOT_DIR needs to be provided.", e.message)
        else:
            self.fail("Did not raise exception.")

    def test_config_is_not_required(self):
        """
        If the '--config' option is not provided, it will default to the
        'carbon.conf' file inside 'ROOT_DIR/conf'.
        """
        root_dir = self.makeDir()
        conf_dir = join(root_dir, "conf")
        makedirs(conf_dir)
        self.makeFile(content="[foo]",
                      basename="carbon.conf",
                      dirname=conf_dir)
        settings = read_config("carbon-foo",
                               FakeOptions(config=None, instance=None,
                                           pidfile=None, logdir=None),
                               ROOT_DIR=root_dir)
        self.assertEqual(conf_dir, settings.CONF_DIR)

    def test_config_dir_from_environment(self):
        """
        If the 'GRAPHITE_CONFIG_DIR' variable is set in the environment, then
        'CONFIG_DIR' will be set to that directory.
        """
        root_dir = self.makeDir()
        conf_dir = join(root_dir, "configs", "production")
        makedirs(conf_dir)
        self.makeFile(content="[foo]",
                      basename="carbon.conf",
                      dirname=conf_dir)
        orig_value = os.environ.get("GRAPHITE_CONF_DIR", None)
        if orig_value is not None:
            self.addCleanup(os.environ.__setitem__,
                            "GRAPHITE_CONF_DIR",
                            orig_value)
        else:
            self.addCleanup(os.environ.__delitem__, "GRAPHITE_CONF_DIR")
        os.environ["GRAPHITE_CONF_DIR"] = conf_dir
        settings = read_config("carbon-foo",
                               FakeOptions(config=None, instance=None,
                                           pidfile=None, logdir=None),
                               ROOT_DIR=root_dir)
        self.assertEqual(conf_dir, settings.CONF_DIR)

    def test_conf_dir_defaults_to_config_dirname(self):
        """
        The 'CONF_DIR' setting defaults to the parent directory of the
        provided configuration file.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance=None,
                        pidfile=None, logdir=None),
            ROOT_DIR="foo")
        self.assertEqual(dirname(config), settings.CONF_DIR)

    def test_storage_dir_relative_to_root_dir(self):
        """
        The 'STORAGE_DIR' setting defaults to the 'storage' directory relative
        to the 'ROOT_DIR' setting.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance=None,
                        pidfile=None, logdir=None),
            ROOT_DIR="foo")
        self.assertEqual(join("foo", "storage"), settings.STORAGE_DIR)

    def test_log_dir_relative_to_storage_dir(self):
        """
        The 'LOG_DIR' setting defaults to a program-specific directory relative
        to the 'STORAGE_DIR' setting.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance=None,
                        pidfile=None, logdir=None),
            ROOT_DIR="foo")
        self.assertEqual(join("foo", "storage", "log", "carbon-foo"),
                         settings.LOG_DIR)

    def test_log_dir_relative_to_provided_storage_dir(self):
        """
        Providing a different 'STORAGE_DIR' in defaults overrides the default
        of being relative to 'ROOT_DIR'.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance=None,
                        pidfile=None, logdir=None),
            ROOT_DIR="foo", STORAGE_DIR="bar")
        self.assertEqual(join("bar", "log", "carbon-foo"),
                         settings.LOG_DIR)

    def test_log_dir_for_instance_relative_to_storage_dir(self):
        """
        The 'LOG_DIR' setting defaults to a program-specific directory relative
        to the 'STORAGE_DIR' setting. In the case of an instance, the instance
        name is appended to the directory.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance="x",
                        pidfile=None, logdir=None),
            ROOT_DIR="foo")
        self.assertEqual(join("foo", "storage", "log", "carbon-foo-x"),
                         settings.LOG_DIR)

    def test_log_dir_for_instance_relative_to_provided_storage_dir(self):
        """
        Providing a different 'STORAGE_DIR' in defaults overrides the default
        of being relative to 'ROOT_DIR'. In the case of an instance, the
        instance name is appended to the directory.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance="x",
                        pidfile=None, logdir=None),
            ROOT_DIR="foo", STORAGE_DIR="bar")
        self.assertEqual(join("bar", "log", "carbon-foo-x"),
                         settings.LOG_DIR)

    def test_pidfile_relative_to_storage_dir(self):
        """
        The 'pidfile' setting defaults to a program-specific filename relative
        to the 'STORAGE_DIR' setting.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance=None,
                        pidfile=None, logdir=None),
            ROOT_DIR="foo")
        self.assertEqual(join("foo", "storage", "carbon-foo.pid"),
                         settings.pidfile)

    def test_pidfile_in_options_has_precedence(self):
        """
        The 'pidfile' option from command line overrides the default setting.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance=None,
                        pidfile="foo.pid", logdir=None),
            ROOT_DIR="foo")
        self.assertEqual("foo.pid", settings.pidfile)

    def test_pidfile_for_instance_in_options_has_precedence(self):
        """
        The 'pidfile' option from command line overrides the default setting
        for the instance, if one is specified.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance="x",
                        pidfile="foo.pid", logdir=None),
            ROOT_DIR="foo")
        self.assertEqual("foo.pid", settings.pidfile)

    def test_storage_dir_as_provided(self):
        """
        Providing a 'STORAGE_DIR' in defaults overrides the root-relative
        default.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance=None,
                        pidfile=None, logdir=None),
            ROOT_DIR="foo", STORAGE_DIR="bar")
        self.assertEqual("bar", settings.STORAGE_DIR)

    def test_log_dir_as_provided(self):
        """
        Providing a 'LOG_DIR' in defaults overrides the storage-relative
        default.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance=None,
                        pidfile=None, logdir=None),
            ROOT_DIR="foo", STORAGE_DIR="bar", LOG_DIR='baz')
        self.assertEqual("baz", settings.LOG_DIR)

    def test_log_dir_from_options(self):
        """
        Providing a 'LOG_DIR' in the command line overrides the
        storage-relative default.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance=None,
                        pidfile=None, logdir="baz"),
            ROOT_DIR="foo")
        self.assertEqual("baz", settings.LOG_DIR)

    def test_log_dir_for_instance_from_options(self):
        """
        Providing a 'LOG_DIR' in the command line overrides the
        storage-relative default for the instance.
        """
        config = self.makeFile(content="[foo]")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance="x",
                        pidfile=None, logdir="baz"),
            ROOT_DIR="foo")
        self.assertEqual("baz", settings.LOG_DIR)

    def test_storage_dir_from_config(self):
        """
        Providing a 'STORAGE_DIR' in the configuration file overrides the
        root-relative default.
        """
        config = self.makeFile(content="[foo]\nSTORAGE_DIR = bar")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance=None,
                        pidfile=None, logdir=None),
            ROOT_DIR="foo")
        self.assertEqual("bar", settings.STORAGE_DIR)

    def test_log_dir_from_config(self):
        """
        Providing a 'LOG_DIR' in the configuration file overrides the
        storage-relative default.
        """
        config = self.makeFile(content="[foo]\nLOG_DIR = baz")
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance=None,
                        pidfile=None, logdir=None),
            ROOT_DIR="foo")
        self.assertEqual("baz", settings.LOG_DIR)

    def test_log_dir_from_instance_config(self):
        """
        Providing a 'LOG_DIR' for the specific instance in the configuration
        file overrides the storage-relative default. The actual value will have
        the instance name appended to it and ends with a forward slash.
        """
        config = self.makeFile(
            content=("[foo]\nLOG_DIR = baz\n"
                     "[foo:x]\nLOG_DIR = boo"))
        settings = read_config(
            "carbon-foo",
            FakeOptions(config=config, instance="x",
                        pidfile=None, logdir=None),
            ROOT_DIR="foo")
        self.assertEqual("boo-x", settings.LOG_DIR)

########NEW FILE########
__FILENAME__ = util
import sys
import os
import pwd

from os.path import abspath, basename, dirname, join
try:
  from cStringIO import StringIO
except ImportError:
  from StringIO import StringIO
try:
  import cPickle as pickle
  USING_CPICKLE = True
except:
  import pickle
  USING_CPICKLE = False

from twisted.python.util import initgroups
from twisted.scripts.twistd import runApp
from twisted.scripts._twistd_unix import daemonize


daemonize = daemonize # Backwards compatibility


def dropprivs(user):
  uid, gid = pwd.getpwnam(user)[2:4]
  initgroups(uid, gid)
  os.setregid(gid, gid)
  os.setreuid(uid, uid)
  return (uid, gid)


def run_twistd_plugin(filename):
    from carbon.conf import get_parser
    from twisted.scripts.twistd import ServerOptions

    bin_dir = dirname(abspath(filename))
    root_dir = dirname(bin_dir)
    os.environ.setdefault('GRAPHITE_ROOT', root_dir)

    program = basename(filename).split('.')[0]

    # First, parse command line options as the legacy carbon scripts used to
    # do.
    parser = get_parser(program)
    (options, args) = parser.parse_args()

    if not args:
      parser.print_usage()
      return

    # This isn't as evil as you might think
    __builtins__["instance"] = options.instance
    __builtins__["program"] = program

    # Then forward applicable options to either twistd or to the plugin itself.
    twistd_options = ["--no_save"]

    # If no reactor was selected yet, try to use the epoll reactor if
    # available.
    try:
        from twisted.internet import epollreactor
        twistd_options.append("--reactor=epoll")
    except:
        pass

    if options.debug:
        twistd_options.extend(["--nodaemon"])
    if options.profile:
        twistd_options.append("--profile")
    if options.pidfile:
        twistd_options.extend(["--pidfile", options.pidfile])

    # Now for the plugin-specific options.
    twistd_options.append(program)

    if options.debug:
        twistd_options.append("--debug")

    for option_name, option_value in vars(options).items():
        if (option_value is not None and
            option_name not in ("debug", "profile", "pidfile")):
            twistd_options.extend(["--%s" % option_name.replace("_", "-"),
                                   option_value])

    # Finally, append extra args so that twistd has a chance to process them.
    twistd_options.extend(args)

    config = ServerOptions()
    config.parseOptions(twistd_options)

    runApp(config)


def parseDestinations(destination_strings):
  destinations = []

  for dest_string in destination_strings:
    parts = dest_string.strip().split(':')
    if len(parts) == 2:
      server, port = parts
      instance = None
    elif len(parts) == 3:
      server, port, instance = parts
    else:
      raise ValueError("Invalid destination string \"%s\"" % dest_string)

    destinations.append( (server, int(port), instance) )

  return destinations



# This whole song & dance is due to pickle being insecure
# yet performance critical for carbon. We leave the insecure
# mode (which is faster) as an option (USE_INSECURE_UNPICKLER).
# The SafeUnpickler classes were largely derived from
# http://nadiana.com/python-pickle-insecure
if USING_CPICKLE:
  class SafeUnpickler(object):
    PICKLE_SAFE = {
      'copy_reg' : set(['_reconstructor']),
      '__builtin__' : set(['object']),
    }

    @classmethod
    def find_class(cls, module, name):
      if not module in cls.PICKLE_SAFE:
        raise pickle.UnpicklingError('Attempting to unpickle unsafe module %s' % module)
      __import__(module)
      mod = sys.modules[module]
      if not name in cls.PICKLE_SAFE[module]:
        raise pickle.UnpicklingError('Attempting to unpickle unsafe class %s' % name)
      return getattr(mod, name)

    @classmethod
    def loads(cls, pickle_string):
      pickle_obj = pickle.Unpickler(StringIO(pickle_string))
      pickle_obj.find_global = cls.find_class
      return pickle_obj.load()

else:
  class SafeUnpickler(pickle.Unpickler):
    PICKLE_SAFE = {
      'copy_reg' : set(['_reconstructor']),
      '__builtin__' : set(['object']),
    }
    def find_class(self, module, name):
      if not module in self.PICKLE_SAFE:
        raise pickle.UnpicklingError('Attempting to unpickle unsafe module %s' % module)
      __import__(module)
      mod = sys.modules[module]
      if not name in self.PICKLE_SAFE[module]:
        raise pickle.UnpicklingError('Attempting to unpickle unsafe class %s' % name)
      return getattr(mod, name)
 
    @classmethod
    def loads(cls, pickle_string):
      return cls(StringIO(pickle_string)).load()
 

def get_unpickler(insecure=False):
  if insecure:
    return pickle
  else:
    return SafeUnpickler

########NEW FILE########
__FILENAME__ = writer
"""Copyright 2009 Chris Davis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""


import os
import time
from os.path import join, exists, dirname, basename

import whisper
from carbon import state
from carbon.cache import MetricCache
from carbon.storage import getFilesystemPath, loadStorageSchemas, loadAggregationSchemas
from carbon.conf import settings
from carbon import log, events, instrumentation

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.application.service import Service


lastCreateInterval = 0
createCount = 0
schemas = loadStorageSchemas()
agg_schemas = loadAggregationSchemas()
CACHE_SIZE_LOW_WATERMARK = settings.MAX_CACHE_SIZE * 0.95


def optimalWriteOrder():
  "Generates metrics with the most cached values first and applies a soft rate limit on new metrics"
  global lastCreateInterval
  global createCount
  metrics = MetricCache.counts()

  t = time.time()
  metrics.sort(key=lambda item: item[1], reverse=True) # by queue size, descending
  log.msg("Sorted %d cache queues in %.6f seconds" % (len(metrics), time.time() - t))

  for metric, queueSize in metrics:
    if state.cacheTooFull and MetricCache.size < CACHE_SIZE_LOW_WATERMARK:
      events.cacheSpaceAvailable()

    dbFilePath = getFilesystemPath(metric)
    dbFileExists = exists(dbFilePath)

    if not dbFileExists:
      createCount += 1
      now = time.time()

      if now - lastCreateInterval >= 60:
        lastCreateInterval = now
        createCount = 1

      elif createCount >= settings.MAX_CREATES_PER_MINUTE:
        # dropping queued up datapoints for new metrics prevents filling up the entire cache
        # when a bunch of new metrics are received.
        try:
          MetricCache.pop(metric)
        except KeyError:
          pass

        continue

    try: # metrics can momentarily disappear from the MetricCache due to the implementation of MetricCache.store()
      datapoints = MetricCache.pop(metric)
    except KeyError:
      log.msg("MetricCache contention, skipping %s update for now" % metric)
      continue # we simply move on to the next metric when this race condition occurs

    yield (metric, datapoints, dbFilePath, dbFileExists)


def writeCachedDataPoints():
  "Write datapoints until the MetricCache is completely empty"
  updates = 0
  lastSecond = 0

  while MetricCache:
    dataWritten = False

    for (metric, datapoints, dbFilePath, dbFileExists) in optimalWriteOrder():
      dataWritten = True

      if not dbFileExists:
        archiveConfig = None
        xFilesFactor, aggregationMethod = None, None

        for schema in schemas:
          if schema.matches(metric):
            log.creates('new metric %s matched schema %s' % (metric, schema.name))
            archiveConfig = [archive.getTuple() for archive in schema.archives]
            break

        for schema in agg_schemas:
          if schema.matches(metric):
            log.creates('new metric %s matched aggregation schema %s' % (metric, schema.name))
            xFilesFactor, aggregationMethod = schema.archives
            break

        if not archiveConfig:
          raise Exception("No storage schema matched the metric '%s', check your storage-schemas.conf file." % metric)

        dbDir = dirname(dbFilePath)
        os.system("mkdir -p -m 755 '%s'" % dbDir)

        log.creates("creating database file %s (archive=%s xff=%s agg=%s)" % 
                    (dbFilePath, archiveConfig, xFilesFactor, aggregationMethod))
        whisper.create(dbFilePath, archiveConfig, xFilesFactor, aggregationMethod, settings.WHISPER_SPARSE_CREATE)
        os.chmod(dbFilePath, 0755)
        instrumentation.increment('creates')

      try:
        t1 = time.time()
        whisper.update_many(dbFilePath, datapoints)
        t2 = time.time()
        updateTime = t2 - t1
      except:
        log.msg("Error writing to %s" % (dbFilePath))
        log.err()
        instrumentation.increment('errors')
      else:
        pointCount = len(datapoints)
        instrumentation.increment('committedPoints', pointCount)
        instrumentation.append('updateTimes', updateTime)

        if settings.LOG_UPDATES:
          log.updates("wrote %d datapoints for %s in %.5f seconds" % (pointCount, metric, updateTime))

        # Rate limit update operations
        thisSecond = int(t2)

        if thisSecond != lastSecond:
          lastSecond = thisSecond
          updates = 0
        else:
          updates += 1
          if updates >= settings.MAX_UPDATES_PER_SECOND:
            time.sleep( int(t2 + 1) - t2 )

    # Avoid churning CPU when only new metrics are in the cache
    if not dataWritten:
      time.sleep(0.1)


def writeForever():
  while reactor.running:
    try:
      writeCachedDataPoints()
    except:
      log.err()

    time.sleep(1) # The writer thread only sleeps when the cache is empty or an error occurs


def reloadStorageSchemas():
  global schemas
  try:
    schemas = loadStorageSchemas()
  except:
    log.msg("Failed to reload storage schemas")
    log.err()

def reloadAggregationSchemas():
  global agg_schemas
  try:
    schemas = loadAggregationSchemas()
  except:
    log.msg("Failed to reload aggregation schemas")
    log.err()


class WriterService(Service):

    def __init__(self):
        self.storage_reload_task = LoopingCall(reloadStorageSchemas)
        self.aggregation_reload_task = LoopingCall(reloadAggregationSchemas)

    def startService(self):
        self.storage_reload_task.start(60, False)
        self.aggregation_reload_task.start(60, False)
        reactor.callInThread(writeForever)
        Service.startService(self)

    def stopService(self):
        self.reload_task.stop()
        Service.stopService(self)

########NEW FILE########
__FILENAME__ = carbon_aggregator_plugin
from zope.interface import implements

from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

from carbon import service
from carbon import conf


class CarbonAggregatorServiceMaker(object):

    implements(IServiceMaker, IPlugin)
    tapname = "carbon-aggregator"
    description = "Aggregate stats for graphite."
    options = conf.CarbonAggregatorOptions

    def makeService(self, options):
        """
        Construct a C{carbon-aggregator} service.
        """
        return service.createAggregatorService(options)


# Now construct an object which *provides* the relevant interfaces
serviceMaker = CarbonAggregatorServiceMaker()

########NEW FILE########
__FILENAME__ = carbon_cache_plugin
from zope.interface import implements

from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

from carbon import service
from carbon import conf


class CarbonCacheServiceMaker(object):

    implements(IServiceMaker, IPlugin)
    tapname = "carbon-cache"
    description = "Collect stats for graphite."
    options = conf.CarbonCacheOptions

    def makeService(self, options):
        """
        Construct a C{carbon-cache} service.
        """
        return service.createCacheService(options)


# Now construct an object which *provides* the relevant interfaces
serviceMaker = CarbonCacheServiceMaker()

########NEW FILE########
__FILENAME__ = carbon_relay_plugin
from zope.interface import implements

from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

from carbon import service
from carbon import conf


class CarbonRelayServiceMaker(object):

    implements(IServiceMaker, IPlugin)
    tapname = "carbon-relay"
    description = "Relay stats for graphite."
    options = conf.CarbonRelayOptions

    def makeService(self, options):
        """
        Construct a C{carbon-relay} service.
        """
        return service.createRelayService(options)


# Now construct an object which *provides* the relevant interfaces
serviceMaker = CarbonRelayServiceMaker()

########NEW FILE########
__FILENAME__ = check-dependencies
#!/usr/bin/env python

import sys


# Simple python version test
major,minor = sys.version_info[:2]
py_version = sys.version.split()[0]
if major != 2 or minor < 4:
  print "You are using python %s, but version 2.4 or greater is required" % py_version
  raise SystemExit(1)

fatal = 0
warning = 0


# Test for whisper
try:
  import whisper
except:
  print "[FATAL] Unable to import the 'whisper' module, please download this package from the Graphite project page and install it."
  fatal += 1


# Test for pycairo
try:
  import cairo
except:
  print "[FATAL] Unable to import the 'cairo' module, do you have pycairo installed for python %s?" % py_version
  cairo = None
  fatal += 1


# Test that pycairo has the PNG backend
try:
  if cairo:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
    del surface
except:
  print "[FATAL] Failed to create an ImageSurface with cairo, you probably need to recompile cairo with PNG support"
  fatal += 1

# Test that cairo can find fonts
try:
  if cairo:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
    context = cairo.Context(surface)
    context.font_extents()
    del surface, context
except:
  print "[FATAL] Failed to create text with cairo, this probably means cairo cant find any fonts. Install some system fonts and try again"

# Test for django
try:
  import django
except:
  print "[FATAL] Unable to import the 'django' module, do you have Django installed for python %s?" % py_version
  django = None
  fatal += 1


# Test for django-tagging
try:
  import tagging
except:
  print "[FATAL] Unable to import the 'tagging' module, do you have django-tagging installed for python %s?" % py_version
  fatal += 1


# Verify django version
if django and django.VERSION[:2] < (1,1):
  print "[FATAL] You have django version %s installed, but version 1.1 or greater is required" % django.get_version()
  fatal += 1


# Test for a json module
try:
  import json
except ImportError:
  try:
    import simplejson
  except ImportError:
    print "[FATAL] Unable to import either the 'json' or 'simplejson' module, at least one is required."
    fatal += 1


# Test for zope.interface
try:
  from zope.interface import Interface
except ImportError:
  print "[WARNING] Unable to import Interface from zope.interface."
  print "Without it, you will be unable to run carbon on this server."
  warning +=1



# Test for mod_python
try:
  import mod_python
except:
  print "[WARNING] Unable to import the 'mod_python' module, do you have mod_python installed for python %s?" % py_version
  print "mod_python is one of the most common ways to run graphite-web under apache."
  print "Without mod_python you will still be able to use the built in development server; which is not"
  print "recommended for production use."
  print "wsgi or other approaches for production scale use are also possible without mod_python"
  warning += 1


# Test for python-memcached
try:
  import memcache
except:
  print "[WARNING]"
  print "Unable to import the 'memcache' module, do you have python-memcached installed for python %s?" % py_version
  print "This feature is not required but greatly improves performance.\n"
  warning += 1


# Test for sqlite
try:
  try:
    import sqlite3 #python 2.5+
  except:
    from pysqlite2 import dbapi2 #python 2.4
except:
  print "[WARNING]"
  print "Unable to import the sqlite module, do you have python-sqlite2 installed for python %s?" % py_version
  print "If you plan on using another database backend that Django supports (such as mysql or postgres)"
  print "then don't worry about this. However if you do not want to setup the database yourself, you will"
  print "need to install sqlite2 and python-sqlite2.\n"
  warning += 1


# Test for python-ldap
try:
  import ldap
except:
  print "[WARNING]"
  print "Unable to import the 'ldap' module, do you have python-ldap installed for python %s?" % py_version
  print "Without python-ldap, you will not be able to use LDAP authentication in the graphite webapp.\n"
  warning += 1


# Test for Twisted python
try:
  import twisted
except:
  print "[WARNING]"
  print "Unable to import the 'twisted' package, do you have Twisted installed for python %s?" % py_version
  print "Without Twisted, you cannot run carbon on this server."
  warning += 1
else:
  tv = []
  tv = twisted.__version__.split('.')
  if int(tv[0]) < 8 or (int(tv[0]) == 8 and int(tv[1]) < 2):
    print "[WARNING]"
    print "Your version of Twisted is too old to run carbon."
    print "You will not be able to run carbon on this server until you upgrade Twisted >= 8.2."
    warning += 1

# Test for txamqp
try:
  import txamqp
except:
  print "[WARNING]"
  print "Unable to import the 'txamqp' module, this is required if you want to use AMQP."
  print "Note that txamqp requires python 2.5 or greater."
  warning += 1


if fatal:
  print "%d necessary dependencies not met. Graphite will not function until these dependencies are fulfilled." % fatal

else:
  print "All necessary dependencies are met."

if warning:
  print "%d optional dependencies not met. Please consider the warning messages before proceeding." % warning

else:
  print "All optional dependencies are met."

########NEW FILE########
__FILENAME__ = demo-collector
#!/usr/bin/env python
from commands import getstatusoutput
from platform import node
from socket import socket, AF_INET, SOCK_STREAM
from sys import argv, exit
from time import sleep, time

DELAY = 60
CARBON_SERVER = 'localhost'
CARBON_PORT = 2003

class Carbon:
    def __init__(self, hostname, port):
        self.s = socket(AF_INET, SOCK_STREAM)
        self.hostname = hostname
        self.port = int(port)
        self.connect()
    def connect(self):
        try:
            self.s.connect((self.hostname, self.port))
        except IOError, e:
            print "connect: ", e
            return
    def disconnect(self): self.s.close()
    def send(self, data):
        try:
            self.s.sendall(data + "\n")
        except:
            self.connect()
            self.s.sendall(data + "\n")

class Host:
    def __init__(self):
        self.historical = {}

    def get_all(self):
        data = []
        functions = dir(self)
        for function in functions:
            if not function.startswith("fetch_"): continue
            for metric in eval("self.%s()" % (function)):
                data.append(metric)
        return data

    def read_file(self, filename):
        file_handle = open(filename)
        contents = file_handle.readlines()
        file_handle.close()
        return contents

    def delta_analyzer(self, measurements, data, now):
        result = []
        for line in data:
            for measurement, loc in measurements.iteritems():
                metric_name = "%s.%s" % (line[0], measurement)
                try: value = line[loc]
                except: continue
                if self.historical.has_key(metric_name):
                    current = value
                    delta = int(value) - int(self.historical[metric_name][1])
                    timedelta = time() - self.historical[metric_name][0]
                    self.historical[metric_name] = (time(), current)
                    if timedelta < 1:
                        continue
                    value = int( delta / timedelta )
                    if value > 0:
                        result.append("%s %d %d" % (metric_name, value, now))
                else:
                    self.historical[metric_name] = (time(), value)
        return result

    def fetch_loadavg(self):
        data = []
        now = int(time())
        (loadavg_1, loadavg_5, loadavg_15) = self.read_file("/proc/loadavg")[0].strip().split()[:3]
        data.append("load.1min %s %d" % (loadavg_1,now))
        data.append("load.5min %s %d" % (loadavg_5,now))
        data.append("load.15min %s %d" % (loadavg_15,now))
        return data

    def fetch_network_io(self):
        measurements = {"rx_bytes": 1, "rx_packets": 2, "rx_errors": 3, "rx_dropped": 4, "tx_bytes": 9, "tx_packets": 10, "tx_errors": 11, "tx_dropped": 12}
        now = int(time())
        raw_data = self.read_file("/proc/net/dev")
        prepared_data = []
        for line in raw_data[2:]:
            (interface, values) = line.strip().split(":")
            values = values.split()
            if interface == "lo": continue
            values.insert(0, "network." + interface)
            prepared_data.append(values)
        return self.delta_analyzer(measurements, prepared_data, now)

    def fetch_disk_usage(self):
        data = []
        now = int(time())
        (status, raw_data) = getstatusoutput("mount")
        if status != 0: return data
        for line in raw_data.split("\n"):
            if not (line.startswith("/") or line.find("@o2ib") >= 0): continue
            device = line.split()[2]
            device_name = line.split()[0].split('/')[-1]
            (status, device_data) = getstatusoutput("stat -c '%s %a %b %c %d %f' -f " + device)
            if status != 0: continue
            block_size, free_blocks_nonsu, total_blocks, total_file_nodes, free_file_nodes, free_blocks = [a.isdigit() and int(a) or 0 for a in device_data.split()]
            data.append("disk.%s.available %d %d" % (device_name, free_blocks*block_size, now))
            data.append("disk.%s.free_inodes %d %d" % (device_name, free_file_nodes, now))
            data.append("disk.%s.available_percent %f %d" % (device_name, float(free_blocks)/total_blocks*100, now))
        return data

    def fetch_disk_io(self):
        measurements = {"reads_issued": 3, "ms_spent_reading": 6, "writes_completed": 7, "ms_spent_writing": 10, "ios_in_progress": 11, "ms_spent_doing_io": 12, "weighted_ms_spent_doing_io": 13}
        now = int(time())
        raw_data = self.read_file("/proc/diskstats")
        prepared_data = []
        for line in raw_data:
            values = line.split()
            values[0] = "disk." + values[2]
            prepared_data.append(values)
        return self.delta_analyzer(measurements, prepared_data, now)

    def fetch_memory_usage(self):
        metrics = {"MemFree": "memory_free", "Buffers": "buffers", "Cached": "cached", "SwapFree": "swap_free", "Slab": "slab"}
        data = []
        now = int(time())
        raw_data = self.read_file("/proc/meminfo")
        for line in raw_data:
            metric, i = line.split(":")
            value = int(i.strip().strip(" kB")) * 1024
            if metric in metrics.keys():
                data.append("memory.%s %d %d" % (metrics[metric], value, now))
        return data

    def fetch_smb_statistics(self):
        measurements = {0: "clients", 2: "file_locks"}
        data = []
        now = int(time())
        this_node = None
        (status, raw_data) = getstatusoutput("/usr/bin/ctdb status")
        if status == 0:
            for line in raw_data.split("\n"):
                if line.find("THIS NODE") > 0:
                    this_node = line.split()[0].split(":")[1]
            if this_node is None: return
        (status, raw_data) = getstatusoutput("/usr/bin/smbstatus")
        if status != 0: return data
        for i, block in enumerate(raw_data.split("\n\n")):
            if i not in measurements.keys(): continue
            raw_data = block.split("\n")
            if this_node is not None: 
                this_node_count = [line.startswith(this_node + ":") for line in raw_data].count(True)
            else:
                this_node_count = len(raw_data) - 4
            if this_node_count < 0: this_node_count = 0
            data.append("smb.%s %d %d" % (measurements[i], this_node_count, now))
        return data


def main():
    host = Host()
    hostname = node().split('.')[0]

    graphite = Carbon(CARBON_SERVER, CARBON_PORT);

    while True:
        data = host.get_all()
        for datum in data:
            metric = "system.%s.%s" % (hostname, datum)
            if "-debug" in argv: print metric
            graphite.send(metric)
        sleep(DELAY)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = memcache_whisper
#!/usr/bin/env python
# Copyright 2008 Orbitz WorldWide
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# This module is an implementation of the Whisper database API
# Here is the basic layout of a whisper data file
#
# File = Header,Data
#	Header = Metadata,ArchiveInfo+
#		Metadata = lastUpdate,maxRetention,xFilesFactor,archiveCount
#		ArchiveInfo = Offset,SecondsPerPoint,Points
#	Data = Archive+
#		Archive = Point+
#			Point = timestamp,value

"""
NOTE: This is a modified version of whisper.py
For details on the modification, read https://bugs.launchpad.net/graphite/+bug/245835
"""

import os, struct, time
try:
  import fcntl
  CAN_LOCK = True
except ImportError:
  CAN_LOCK = False

LOCK = False
CACHE_HEADERS = False
__headerCache = {}

longFormat = "!L"
longSize = struct.calcsize(longFormat)
floatFormat = "!f"
floatSize = struct.calcsize(floatFormat)
timestampFormat = "!L"
timestampSize = struct.calcsize(timestampFormat)
valueFormat = "!d"
valueSize = struct.calcsize(valueFormat)
pointFormat = "!Ld"
pointSize = struct.calcsize(pointFormat)
metadataFormat = "!2LfL"
metadataSize = struct.calcsize(metadataFormat)
archiveInfoFormat = "!3L"
archiveInfoSize = struct.calcsize(archiveInfoFormat)

debug = startBlock = endBlock = lambda *a,**k: None

def exists(path):
  return os.path.exists(path)

def drop(path):
  os.remove(path)

def enableMemcache(servers = ['127.0.0.1:11211'], min_compress_len = 0):
  from StringIO import StringIO
  import memcache
  global open, exists, drop

  MC = memcache.Client(servers)

  class open(StringIO):
    def __init__(self,*args,**kwargs):
      self.name = args[0]
      self.mode = args[1]
      if self.mode == "r+b" or self.mode == "rb":
        StringIO.__init__(self, MC.get(self.name))
      else:
        StringIO.__init__(self)

    def close(self):
      if self.mode == "r+b" or self.mode == "wb":
        MC.set(self.name, self.getvalue(), min_compress_len = min_compress_len)
      StringIO.close(self)
      
  def exists(path):
    return MC.get(path) != None

  def drop(path):
    MC.delete(path)

def enableDebug():
  global open, debug, startBlock, endBlock
  class open(file):
    def __init__(self,*args,**kwargs):
      file.__init__(self,*args,**kwargs)
      self.writeCount = 0
      self.readCount = 0

    def write(self,data):
      self.writeCount += 1
      debug('WRITE %d bytes #%d' % (len(data),self.writeCount))
      return file.write(self,data)

    def read(self,bytes):
      self.readCount += 1
      debug('READ %d bytes #%d' % (bytes,self.readCount))
      return file.read(self,bytes)

  def debug(message):
    print 'DEBUG :: %s' % message

  __timingBlocks = {}

  def startBlock(name):
    __timingBlocks[name] = time.time()

  def endBlock(name):
    debug("%s took %.5f seconds" % (name,time.time() - __timingBlocks.pop(name)))


def __readHeader(fh):
  info = __headerCache.get(fh.name)
  if info: return info
  #startBlock('__readHeader')
  originalOffset = fh.tell()
  fh.seek(0)
  packedMetadata = fh.read(metadataSize)
  (lastUpdate,maxRetention,xff,archiveCount) = struct.unpack(metadataFormat,packedMetadata)
  archives = []
  for i in xrange(archiveCount):
    packedArchiveInfo = fh.read(archiveInfoSize)
    (offset,secondsPerPoint,points) = struct.unpack(archiveInfoFormat,packedArchiveInfo)
    archiveInfo = {
      'offset' : offset,
      'secondsPerPoint' : secondsPerPoint,
      'points' : points,
      'retention' : secondsPerPoint * points,
      'size' : points * pointSize,
    }
    archives.append(archiveInfo)
  fh.seek(originalOffset)
  info = {
    'lastUpdate' : lastUpdate,
    'maxRetention' : maxRetention,
    'xFilesFactor' : xff,
    'archives' : archives,
  }
  if CACHE_HEADERS:
    __headerCache[fh.name] = info
  #endBlock('__readHeader')
  return info


def __changeLastUpdate(fh):
  return #XXX Make this a NOP, use os.stat(filename).st_mtime instead
  startBlock('__changeLastUpdate()')
  originalOffset = fh.tell()
  fh.seek(0) #Based on assumption that first field is lastUpdate
  now = int( time.time() )
  packedTime = struct.pack(timestampFormat,now)
  fh.write(packedTime)
  fh.seek(originalOffset)
  endBlock('__changeLastUpdate()')


def create(path,archiveList,xFilesFactor=0.5):
  """create(path,archiveList,xFilesFactor=0.5)

path is a string
archiveList is a list of archives, each of which is of the form (secondsPerPoint,numberOfPoints)
xFilesFactor specifies the fraction of data points in a propagation interval that must have known values for a propagation to occur
"""
  #Validate archive configurations...
  assert archiveList, "You must specify at least one archive configuration!"
  archiveList.sort(key=lambda a: a[0]) #sort by precision (secondsPerPoint)
  for i,archive in enumerate(archiveList):
    if i == len(archiveList) - 1: break
    next = archiveList[i+1]
    assert archive[0] < next[0],\
    "You cannot configure two archives with the same precision %s,%s" % (archive,next)
    assert (next[0] % archive[0]) == 0,\
    "Higher precision archives' precision must evenly divide all lower precision archives' precision %s,%s" % (archive[0],next[0])
    retention = archive[0] * archive[1]
    nextRetention = next[0] * next[1]
    assert nextRetention > retention,\
    "Lower precision archives must cover larger time intervals than higher precision archives %s,%s" % (archive,next)
  #Looks good, now we create the file and write the header
  assert not exists(path), "File %s already exists!" % path
  fh = open(path,'wb')
  if LOCK: fcntl.flock( fh.fileno(), fcntl.LOCK_EX )
  lastUpdate = struct.pack( timestampFormat, int(time.time()) )
  oldest = sorted([secondsPerPoint * points for secondsPerPoint,points in archiveList])[-1]
  maxRetention = struct.pack( longFormat, oldest )
  xFilesFactor = struct.pack( floatFormat, float(xFilesFactor) )
  archiveCount = struct.pack(longFormat, len(archiveList))
  packedMetadata = lastUpdate + maxRetention + xFilesFactor + archiveCount
  fh.write(packedMetadata)
  headerSize = metadataSize + (archiveInfoSize * len(archiveList))
  archiveOffsetPointer = headerSize
  for secondsPerPoint,points in archiveList:
    archiveInfo = struct.pack(archiveInfoFormat, archiveOffsetPointer, secondsPerPoint, points)
    fh.write(archiveInfo)
    archiveOffsetPointer += (points * pointSize)
  zeroes = '\x00' * (archiveOffsetPointer - headerSize)
  fh.write(zeroes)
  fh.close()


def __propagate(fh,timestamp,xff,higher,lower):
  lowerIntervalStart = timestamp - (timestamp % lower['secondsPerPoint'])
  lowerIntervalEnd = lowerIntervalStart + lower['secondsPerPoint']
  fh.seek(higher['offset'])
  packedPoint = fh.read(pointSize)
  (higherBaseInterval,higherBaseValue) = struct.unpack(pointFormat,packedPoint)
  if higherBaseInterval == 0:
    higherFirstOffset = higher['offset']
  else:
    timeDistance = lowerIntervalStart - higherBaseInterval
    pointDistance = timeDistance / higher['secondsPerPoint']
    byteDistance = pointDistance * pointSize
    higherFirstOffset = higher['offset'] + (byteDistance % higher['size'])
  higherPoints = lower['secondsPerPoint'] / higher['secondsPerPoint']
  higherSize = higherPoints * pointSize
  higherLastOffset = higherFirstOffset + (higherSize % higher['size'])
  fh.seek(higherFirstOffset)
  if higherFirstOffset < higherLastOffset: #we don't wrap the archive
    seriesString = fh.read(higherLastOffset - higherFirstOffset)
  else: #We do wrap the archive
    higherEnd = higher['offset'] + higher['size']
    seriesString = fh.read(higherEnd - higherFirstOffset)
    fh.seek(higher['offset'])
    seriesString += fh.read(higherLastOffset - higher['offset'])
  #Now we unpack the series data we just read
  byteOrder,pointTypes = pointFormat[0],pointFormat[1:]
  points = len(seriesString) / pointSize
  seriesFormat = byteOrder + (pointTypes * points)
  unpackedSeries = struct.unpack(seriesFormat, seriesString)
  #And finally we construct a list of values
  neighborValues = [None] * points
  currentInterval = lowerIntervalStart
  step = higher['secondsPerPoint']
  for i in xrange(0,len(unpackedSeries),2):
    pointTime = unpackedSeries[i]
    if pointTime == currentInterval:
      neighborValues[i/2] = unpackedSeries[i+1]
    currentInterval += step
  #Propagate aggregateValue to propagate from neighborValues if we have enough known points
  knownValues = [v for v in neighborValues if v is not None]
  knownPercent = float(len(knownValues)) / float(len(neighborValues))
  if knownPercent >= xff: #we have enough data to propagate a value!
    aggregateValue = float(sum(knownValues)) / float(len(knownValues)) #TODO another CF besides average?
    myPackedPoint = struct.pack(pointFormat,lowerIntervalStart,aggregateValue)
    fh.seek(lower['offset'])
    packedPoint = fh.read(pointSize)
    (lowerBaseInterval,lowerBaseValue) = struct.unpack(pointFormat,packedPoint)
    if lowerBaseInterval == 0: #First propagated update to this lower archive
      fh.seek(lower['offset'])
      fh.write(myPackedPoint)
    else: #Not our first propagated update to this lower archive
      timeDistance = lowerIntervalStart - lowerBaseInterval
      pointDistance = timeDistance / lower['secondsPerPoint']
      byteDistance = pointDistance * pointSize
      lowerOffset = lower['offset'] + (byteDistance % lower['size'])
      fh.seek(lowerOffset)
      fh.write(myPackedPoint)
    return True
  else:
    return False


def update(path,value,timestamp=None):
  """update(path,value,timestamp=None)

path is a string
value is a float
timestamp is either an int or float
"""
  #startBlock('complete update')
  value = float(value)
  fh = open(path,'r+b')
  if LOCK: fcntl.flock( fh.fileno(), fcntl.LOCK_EX )
  header = __readHeader(fh)
  now = int( time.time() )
  if timestamp is None: timestamp = now
  timestamp = int(timestamp)
  diff = now - timestamp
  assert diff < header['maxRetention'] and diff >= 0, "Timestamp not covered by any archives in this database"
  for i,archive in enumerate(header['archives']): #Find the highest-precision archive that covers timestamp
    if archive['retention'] < diff: continue
    lowerArchives = header['archives'][i+1:] #We'll pass on the update to these lower precision archives later
    break
  #First we update the highest-precision archive
  myInterval = timestamp - (timestamp % archive['secondsPerPoint'])
  myPackedPoint = struct.pack(pointFormat,myInterval,value)
  fh.seek(archive['offset'])
  packedPoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedPoint)
  if baseInterval == 0: #This file's first update
    fh.seek(archive['offset'])
    fh.write(myPackedPoint)
    baseInterval,baseValue = myInterval,value
  else: #Not our first update
    timeDistance = myInterval - baseInterval
    pointDistance = timeDistance / archive['secondsPerPoint']
    byteDistance = pointDistance * pointSize
    myOffset = archive['offset'] + (byteDistance % archive['size'])
    fh.seek(myOffset)
    fh.write(myPackedPoint)
  #Now we propagate the update to lower-precision archives
  #startBlock('update propagation')
  higher = archive
  for lower in lowerArchives:
    if not __propagate(fh,myInterval,header['xFilesFactor'],higher,lower): break
    higher = lower
  #endBlock('update propagation')
  __changeLastUpdate(fh)
  fh.close()
  #endBlock('complete update')


def update_many(path,points):
  """update_many(path,points)

path is a string
points is a list of (timestamp,value) points
"""
  #startBlock('complete update_many path=%s points=%d' % (path,len(points)))
  if not points: return
  points = [ (int(t),float(v)) for (t,v) in points]
  points.sort(key=lambda p: p[0],reverse=True) #order points by timestamp, newest first
  fh = open(path,'r+b')
  if LOCK: fcntl.flock( fh.fileno(), fcntl.LOCK_EX )
  header = __readHeader(fh)
  now = int( time.time() )
  archives = iter( header['archives'] )
  currentArchive = archives.next()
  #debug('  update_many currentArchive=%s' % str(currentArchive))
  currentPoints = []
  for point in points:
    age = now - point[0]
    #debug('  update_many iterating points, point=%s age=%d' % (str(point),age))
    while currentArchive['retention'] < age: #we can't fit any more points in this archive
      #debug('  update_many this point is too old to fit here, currentPoints=%d' % len(currentPoints))
      if currentPoints: #commit all the points we've found that it can fit
        currentPoints.reverse() #put points in chronological order
        __archive_update_many(fh,header,currentArchive,currentPoints)
        currentPoints = []
      try:
        currentArchive = archives.next()
        #debug('  update_many using next archive %s' % str(currentArchive))
      except StopIteration:
        #debug('  update_many no more archives!')
        currentArchive = None
        break
    if not currentArchive: break #drop remaining points that don't fit in the database
    #debug('  update_many adding point=%s' % str(point))
    currentPoints.append(point)
  #debug('  update_many done iterating points')
  if currentArchive and currentPoints: #don't forget to commit after we've checked all the archives
    currentPoints.reverse()
    __archive_update_many(fh,header,currentArchive,currentPoints)
  __changeLastUpdate(fh)
  fh.close()
  #endBlock('complete update_many path=%s points=%d' % (path,len(points)))


def __archive_update_many(fh,header,archive,points):
  step = archive['secondsPerPoint']
  #startBlock('__archive_update_many file=%s archive=%s points=%d' % (fh.name,step,len(points)))
  alignedPoints = [ (timestamp - (timestamp % step), value)
                    for (timestamp,value) in points ]
  #Create a packed string for each contiguous sequence of points
  #startBlock('__archive_update_many string packing')
  packedStrings = []
  previousInterval = None
  currentString = ""
  for (interval,value) in alignedPoints:
    #debug('__archive_update_many  iterating alignedPoint at %s' % interval)
    if (not previousInterval) or (interval == previousInterval + step):
      #debug('__archive_update_many  was expected, packing onto currentString')
      currentString += struct.pack(pointFormat,interval,value)
      previousInterval = interval
    else:
      numberOfPoints = len(currentString) / pointSize
      startInterval = previousInterval - (step * (numberOfPoints-1))
      #debug('__archive_update_many  was NOT expected, appending to packedStrings startInterval=%s currentString=%d bytes' % (startInterval,len(currentString)))
      packedStrings.append( (startInterval,currentString) )
      currentString = struct.pack(pointFormat,interval,value)
      previousInterval = interval
  if currentString:
    #startInterval = previousInterval - (step * len(currentString) / pointSize) + step
    numberOfPoints = len(currentString) / pointSize
    startInterval = previousInterval - (step * (numberOfPoints-1))
    #debug('__archive_update_many  done iterating alignedPoints, remainder currentString of %d bytes, startInterval=%s' % (len(currentString),startInterval))
    packedStrings.append( (startInterval,currentString) )
  #endBlock('__archive_update_many string packing')

  #Read base point and determine where our writes will start
  fh.seek(archive['offset'])
  packedBasePoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedBasePoint)
  if baseInterval == 0: #This file's first update
    #debug('__archive_update_many  first update')
    baseInterval = packedStrings[0][0] #use our first string as the base, so we start at the start
  #debug('__archive_update_many  baseInterval is %s' % baseInterval)

  #Write all of our packed strings in locations determined by the baseInterval
  #startBlock('__archive_update_many write() operations')
  for (interval,packedString) in packedStrings:
    timeDistance = interval - baseInterval
    pointDistance = timeDistance / step
    byteDistance = pointDistance * pointSize
    myOffset = archive['offset'] + (byteDistance % archive['size'])
    fh.seek(myOffset)
    archiveEnd = archive['offset'] + archive['size']
    bytesBeyond = (myOffset + len(packedString)) - archiveEnd
    #debug('  __archive_update_many myOffset=%d packedString=%d archiveEnd=%d bytesBeyond=%d' % (myOffset,len(packedString),archiveEnd,bytesBeyond))
    if bytesBeyond > 0:
      fh.write( packedString[:-bytesBeyond] )
      #debug('We wrapped an archive!')
      assert fh.tell() == archiveEnd, "archiveEnd=%d fh.tell=%d bytesBeyond=%d len(packedString)=%d" % (archiveEnd,fh.tell(),bytesBeyond,len(packedString))
      fh.seek( archive['offset'] )
      fh.write( packedString[-bytesBeyond:] ) #safe because it can't exceed the archive (retention checking logic above)
    else:
      fh.write(packedString)
  #endBlock('__archive_update_many write() operations')

  #Now we propagate the updates to lower-precision archives
  #startBlock('__archive_update_many propagation')
  higher = archive
  lowerArchives = [arc for arc in header['archives'] if arc['secondsPerPoint'] > archive['secondsPerPoint']]
  #debug('__archive_update_many I have %d lower archives' % len(lowerArchives))
  for lower in lowerArchives:
    fit = lambda i: i - (i % lower['secondsPerPoint'])
    lowerIntervals = [fit(p[0]) for p in alignedPoints]
    uniqueLowerIntervals = set(lowerIntervals)
    #debug('  __archive_update_many points=%d unique=%d' % (len(alignedPoints),len(uniqueLowerIntervals)))
    propagateFurther = False
    for interval in uniqueLowerIntervals:
      #debug('  __archive_update_many propagating from %d to %d, interval=%d' % (higher['secondsPerPoint'],lower['secondsPerPoint'],interval))
      if __propagate(fh,interval,header['xFilesFactor'],higher,lower):
        propagateFurther = True
        #debug('  __archive_update_many Successful propagation!')
    #debug('  __archive_update_many propagateFurther=%s' % propagateFurther)
    if not propagateFurther: break
    higher = lower
  #endBlock('__archive_update_many propagation')
  #endBlock('__archive_update_many file=%s archive=%s points=%d' % (fh.name,step,len(points)))


def info(path):
  """info(path)

path is a string
"""
  fh = open(path,'rb')
  info = __readHeader(fh)
  fh.close()
  return info


def fetch(path,fromTime,untilTime=None):
  """fetch(path,fromTime,untilTime=None)

path is a string
fromTime is an epoch time
untilTime is also an epoch time, but defaults to now
"""
  fh = open(path,'rb')
  header = __readHeader(fh)
  now = int( time.time() )
  if untilTime is None or untilTime > now:
    untilTime = now
  if fromTime < (now - header['maxRetention']):
    fromTime = now - header['maxRetention']
  assert fromTime < untilTime, "Invalid time interval"
  diff = now - fromTime
  for archive in header['archives']:
    if archive['retention'] >= diff: break
  fromInterval = int( fromTime - (fromTime % archive['secondsPerPoint']) )
  untilInterval = int( untilTime - (untilTime % archive['secondsPerPoint']) )
  fh.seek(archive['offset'])
  packedPoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedPoint)
  if baseInterval == 0:
    step = archive['secondsPerPoint']
    points = (untilInterval - fromInterval) / step
    timeInfo = (fromInterval,untilInterval,step)
    valueList = [None] * points
    return (timeInfo,valueList)
  #Determine fromOffset
  timeDistance = fromInterval - baseInterval
  pointDistance = timeDistance / archive['secondsPerPoint']
  byteDistance = pointDistance * pointSize
  fromOffset = archive['offset'] + (byteDistance % archive['size'])
  #Determine untilOffset
  timeDistance = untilInterval - baseInterval
  pointDistance = timeDistance / archive['secondsPerPoint']
  byteDistance = pointDistance * pointSize
  untilOffset = archive['offset'] + (byteDistance % archive['size'])
  #Read all the points in the interval
  fh.seek(fromOffset)
  if fromOffset < untilOffset: #If we don't wrap around the archive
    seriesString = fh.read(untilOffset - fromOffset)
  else: #We do wrap around the archive, so we need two reads
    archiveEnd = archive['offset'] + archive['size']
    seriesString = fh.read(archiveEnd - fromOffset)
    fh.seek(archive['offset'])
    seriesString += fh.read(untilOffset - archive['offset'])
  #Now we unpack the series data we just read (anything faster than unpack?)
  byteOrder,pointTypes = pointFormat[0],pointFormat[1:]
  points = len(seriesString) / pointSize
  seriesFormat = byteOrder + (pointTypes * points)
  unpackedSeries = struct.unpack(seriesFormat, seriesString)
  #And finally we construct a list of values (optimize this!)
  valueList = [None] * points #pre-allocate entire list for speed
  currentInterval = fromInterval
  step = archive['secondsPerPoint']
  for i in xrange(0,len(unpackedSeries),2):
    pointTime = unpackedSeries[i]
    if pointTime == currentInterval:
      pointValue = unpackedSeries[i+1]
      valueList[i/2] = pointValue #in-place reassignment is faster than append()
    currentInterval += step
  fh.close()
  timeInfo = (fromInterval,untilInterval,step)
  return (timeInfo,valueList)

########NEW FILE########
__FILENAME__ = test_aggregator_rules
import sys
from os.path import dirname, join, abspath

# Figure out where we're installed
ROOT_DIR = dirname(dirname(abspath(__file__)))

# Make sure that carbon's 'lib' dir is in the $PYTHONPATH if we're running from source.
LIB_DIR = join(ROOT_DIR, 'graphite', 'lib')
sys.path.insert(0, LIB_DIR)

from carbon.aggregator.rules import RuleManager

### Basic usage
if len(sys.argv) != 3:
  print "Usage: %s 'aggregator rule' 'line item'" % (__file__)
  print "\nSample invocation: %s %s %s" % \
    (__file__, "'<prefix>.<env>.<key>.sum.all (10) = sum <prefix>.<env>.<<key>>.sum.<node>'", 'stats.prod.js.ktime_sum.sum.host2' )
  sys.exit(42)

### cli arguments
me, raw_rule, raw_metric = sys.argv


### XXX rather whitebox, by reading the source ;(
rm   = RuleManager
rule = rm.parse_definition( raw_rule )

### rule/parsed rule
print "Raw rule: %s" % raw_rule
print "Parsed rule: %s" % rule.regex.pattern

print "\n======\n"

### run the parse
match = rule.regex.match( raw_metric )

print "Raw metric: %s" % raw_metric
if match:
  print "Match dict: %s" % match.groupdict()
  print "Result: %s" % rule.output_template % match.groupdict()

else:
  print "ERROR: NO MATCH"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Graphite documentation build configuration file, created by
# sphinx-quickstart on Mon Mar 21 12:31:35 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath('../webapp'))
sys.path.append(os.path.abspath('../whisper'))
sys.path.append(os.path.abspath('../carbon'))
os.environ['DJANGO_SETTINGS_MODULE'] = "graphite.settings"

# Prevent graphite logger from complaining about missing log dir.
from graphite import settings
settings.LOG_DIR = os.path.abspath('.')

# Define a custom autodoc documenter for the render.functions module
# This will remove the requestContext parameter which doesnt make sense in the context of the docs
import re
from sphinx.ext import autodoc
class RenderFunctionDocumenter(autodoc.FunctionDocumenter):
  priority = 10 # Override FunctionDocumenter

  @classmethod
  def can_document_member(cls, member, membername, isattr, parent):
    return autodoc.FunctionDocumenter.can_document_member(member, membername, isattr, parent) and \
      parent.name == 'graphite.render.functions'

  def format_args(self):
    args = autodoc.FunctionDocumenter.format_args(self)
    if args is not None:
      # Really, a regex sub here is by far the easiest way
      return re.sub('requestContext, ','',args)

def setup(app):
  app.add_autodocumenter(RenderFunctionDocumenter)

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# Mapping for external links such as Python standard lib
intersphinx_mapping = {
  'python': ('http://docs.python.org/', None)
}
# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Graphite'
copyright = u'2011, Chris Davis'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.9.9'
# The full version, including alpha/beta/rc tags.
release = '0.9.9'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Graphitedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Graphite.tex', u'Graphite Documentation',
   u'Chris Davis', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = example-client
#!/usr/bin/python
"""Copyright 2008 Orbitz WorldWide

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
import time
import os
import platform 
import subprocess
from socket import socket

CARBON_SERVER = '127.0.0.1'
CARBON_PORT = 2003

delay = 60 
if len(sys.argv) > 1:
  delay = int( sys.argv[1] )

def get_loadavg():
  # For more details, "man proc" and "man uptime"  
  if platform.system() == "Linux":
    return open('/proc/loadavg').read().strip().split()[:3]
  else:   
    command = "uptime"
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    os.waitpid(process.pid, 0)
    output = process.stdout.read().replace(',', ' ').strip().split()
    length = len(output)
    return output[length - 3:length]

sock = socket()
try:
  sock.connect( (CARBON_SERVER,CARBON_PORT) )
except:
  print "Couldn't connect to %(server)s on port %(port)d, is carbon-agent.py running?" % { 'server':CARBON_SERVER, 'port':CARBON_PORT }
  sys.exit(1)

while True:
  now = int( time.time() )
  lines = []
  #We're gonna report all three loadavg values
  loadavg = get_loadavg()
  lines.append("system.loadavg_1min %s %d" % (loadavg[0],now))
  lines.append("system.loadavg_5min %s %d" % (loadavg[1],now))
  lines.append("system.loadavg_15min %s %d" % (loadavg[2],now))
  message = '\n'.join(lines) + '\n' #all lines must end in a newline
  print "sending message\n"
  print '-' * 80
  print message
  print
  sock.sendall(message)
  time.sleep(delay)

########NEW FILE########
__FILENAME__ = carbon-load-test
#!/usr/bin/env python

import sys, os, time
from socket import socket
from random import random, choice


try:
  host = sys.argv[1]
  port = int(sys.argv[2])
  mpm = int(sys.argv[3])
except:
  print 'Usage: %s host port metrics-per-minute' % os.path.basename(sys.argv[0])
  sys.exit(1)

s = socket()
s.connect( (host,port) )

now = int( time.time() )
now -= now % 60

while True:
  start = time.time()
  count = 0
  for i in xrange(0, mpm):
    r = choice( (42,43) )
    metric = 'TEST%d.%d' % (r,i)
    value = random()
    s.sendall('%s %s %s\n' % (metric, value, now))
    count += 1

  print 'sent %d metrics in %.3f seconds' % (count, time.time() - start)

  now += 60

  diff = now - time.time()
  if diff > 0:
    print "sleeping for %d seconds" % diff
    time.sleep(diff)

########NEW FILE########
__FILENAME__ = agent
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import struct
from twisted.internet.protocol import ReconnectingClientFactory, Protocol
from twisted.internet.defer import Deferred
from twisted.application import internet

class AgentRelay:
  def __init__(self,host,port):
    self.host = host
    self.port = int(port)
    self.factory = AgentConnectionFactory(self)
    self.client = internet.TCPClient(self.host, self.port, self.factory)
    self.producer = None
    self.protocol = None

  def write(self,data):
    assert self.protocol, "No protocol connected!"
    self.protocol.write(data)

  def registerProducer(self,producer):
    self.producer = producer


class AgentConnectionFactory(ReconnectingClientFactory):
  def __init__(self,relay):
    self.relay = relay
    self.initialDelay = 5.0
    self.factor = 1.5
    self.maxDelay = 30.0
    self.clients = set()

  def buildProtocol(self,addr):
    print 'AgentConnectionFactory building new AgentProtocol'
    p = AgentProtocol(self.relay)
    p.factory = self
    return p


class AgentProtocol(Protocol):
  def __init__(self,relay):
    self.relay = relay

  def connectionMade(self):
    self.transport.setTcpKeepAlive(True)
    self.peer = self.transport.getPeer()
    self.relay.protocol = self #dangerous? maybe. stupid? probably. works? yes.
    self.factory.resetDelay()
    self.factory.clients.add(self)
    self.transport.registerProducer( self.relay.producer, streaming=False )

  def connectionLost(self,reason):
    self.factory.clients.discard(self)

  def write(self,data):
    lines = [' '.join(p) for p in data]
    #print 'Sending %d lines to agent %s' % (len(lines),self.peer.host)
    buffer = '\n'.join(lines) + '\n'
    self.transport.write(buffer)

########NEW FILE########
__FILENAME__ = cloud
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from twisted.internet.defer import Deferred


class AgentCloud:
  def __init__(self):
    self.relayQueues = {}
    self.busyDefer = None

  def input(self,key,value):
    queue = self.getQueue(key)
    if queue:
      queue.enqueue(key,value)
      if self.busyDefer:
        d = self.busyDefer
        self.busyDefer = None
        d.callback(0)
    else:
      if self.busyDefer: return self.busyDefer
      print 'All agents are busy, please hold the line and the next available representative will be with you shortly.'
      self.busyDefer = Deferred()
      return self.busyDefer

  def registerRelay(self,relay):
    queue = QueueProducer(relay)
    relay.registerProducer(queue)
    self.relayQueues[relay] = queue

  def getQueue(self,key):
    relays = self.relayQueues.keys()
    while relays:
      relay = relays[ hash(key) % len(relays) ]
      queue = self.relayQueues[relay]
      if queue.isFull():
        relays.remove(relay)
      else:
        return queue


class QueueProducer:
  def __init__(self,consumer):
    self.consumer = consumer
    self.queue = []
    self.maxSize = 100000
    self.produceSize = 25
    self.emptyDefer = None

  def isFull(self):
    return len(self.queue) >= self.maxSize

  def enqueue(self,key,value):
    self.queue.append( (key,value) )
    if self.emptyDefer:
      self.emptyDefer.callback(0)
      self.emptyDefer = None

  def resumeProducing(self):
    if not self.queue:
      self.emptyDefer = Deferred()
      self.emptyDefer.addCallback( lambda result: self.resumeProducing() )
      return

    data = self.queue[:self.produceSize]
    self.consumer.write(data)
    self.queue = self.queue[self.produceSize:]

  def stopProducing(self):
    pass #Kind of awkward, but whatever...


agentCloud = AgentCloud() #A shared importable singleton

########NEW FILE########
__FILENAME__ = pyped
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import struct, traceback
from cStringIO import StringIO
from cloud import agentCloud
from twisted.internet.protocol import ReconnectingClientFactory, Protocol
from twisted.application import internet

READY_STRING = "R"
HEADER_FORMAT = "!L"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
READY_SIGNAL = struct.pack(HEADER_FORMAT,len(READY_STRING)) + READY_STRING
POINT_FORMAT = "!Ld"

def valid_chars_only(char):
  code = ord(char)
  return code > 31 and code < 127


class PypeConsumer:
  def __init__(self,host,port):
    self.host = host
    self.port = int(port)
    self.simpleName = ("%s_%d" % (self.host,self.port)).replace('.','_')
    self.factory = PypeConnectionFactory(self)
    self.client = internet.TCPClient(self.host, self.port, self.factory)
    self.consumedMessages = 0
    self.logicalMessages = 0


class PypeConnectionFactory(ReconnectingClientFactory):
  def __init__(self,pype):
    self.pype = pype
    self.initialDelay = 5.0
    self.factor = 1.5
    self.maxDelay = 30.0
    self.clients = set()

  def buildProtocol(self,addr):
    print 'PypeConnectionFactory: building new ConsumerProtocol'
    p = ConsumerProtocol(self.pype)
    p.factory = self
    return p


class ConsumerProtocol(Protocol):
  def __init__(self,pype):
    self.pype = pype

  def connectionMade(self):
    self.transport.setTcpKeepAlive(True)
    self.peer = self.transport.getPeer()
    self.factory.resetDelay()
    self.factory.clients.add(self)
    self.hdrBuf = ""
    self.msgBuf = ""
    self.bytesLeft = 0
    self.sendReadySignal()

  def connectionLost(self,reason):
    self.factory.clients.discard(self)

  def sendReadySignal(self):
    self.transport.write(READY_SIGNAL)

  def dataReceived(self,data):
    s = StringIO(data)
    while True:
      if self.bytesLeft:
        chunk = s.read(self.bytesLeft)
        self.msgBuf += chunk
        self.bytesLeft -= len(chunk)
        if self.bytesLeft == 0:
          self.handleMessage( self.msgBuf )
          self.hdrBuf = ""
          self.msgBuf = ""
        else:
          s.close()
          return
      remainingHeader = HEADER_SIZE - len(self.hdrBuf)
      if remainingHeader == 0:
        s.close()
        return
      hdrChunk = s.read(remainingHeader)
      if not hdrChunk: break
      self.hdrBuf += hdrChunk
      if len(self.hdrBuf) == HEADER_SIZE:
        self.bytesLeft = struct.unpack(HEADER_FORMAT,self.hdrBuf)[0]

  def handleMessage(self,message): #Should break this out into a separate handler object
    self.pype.consumedMessages += 1
    rawLines = message.split('\n')
    #print 'Consumed %d line message from %s' % (len(rawLines),self.peer.host)
    self.processSomeLines(rawLines)

  def processSomeLines(self,rawLines):
    '''Attempt to process as many lines as possible.
       If our caches fill up we defer until its got room,
       continuing where we left off until we get through them all.
    '''
    for lineNum,rawLine in enumerate(rawLines):
      try:
        line = filter(valid_chars_only, rawLine)
        if not line: continue
        (name,value,timestamp) = line.split()
        value = float(value)
        timestamp = int(float(timestamp)) # int("1.0") raises a TypeError
        pointStr = "%f %d" % (value,timestamp)
        #Try to put it in the cache, if we get back a deferred, we add a callback to resume processing later
        deferred = agentCloud.input(name,pointStr)
        if deferred:
          remainingLines = rawLines[lineNum:]
          deferred.addCallback( lambda result: self.processSomeLines(remainingLines) )
          return
        self.pype.logicalMessages += 1
      except:
        print 'ConsumerProtocol.handleMessage() invalid line: %s' % rawLine
        traceback.print_exc()
        continue

    #Only once we've gotten through all the lines are we ready for another message
    self.sendReadySignal()

########NEW FILE########
__FILENAME__ = web
#!/usr/bin/env python
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import os, posix, time
from cPickle import dumps
from twisted.web.resource import Resource


class CacheQueryService(Resource):
  isLeaf = True
  def __init__(self,cluster):
    Resource.__init__(self)
    self.cluster = cluster
    for cache in self.cluster.caches.values():
      cache.cacheQueries = 0

  def render_GET(self,req):
    metric = req.path[1:]
    cache = self.cluster.selectCache(metric)
    points = cache.get(metric,[])
    print 'CacheQuery for %s returning %d points' % (metric,len(points))
    cache.cacheQueries += 1
    return dumps( points )


class WebConsole(Resource):
  isLeaf = True
  def __init__(self,pypes,cluster,agents):
    Resource.__init__(self)
    self.pypes = pypes
    self.cluster = cluster
    self.agents = agents
    self.cpuUsage = -1.0
    self.memUsage = 0
    self.lastCalcTime = time.time()
    self.lastCpuVal = 0.0
    self.templates = {}
    for tmpl in os.listdir('templates'):
      if not tmpl.endswith('.tmpl'): continue
      self.templates[ tmpl[:-5] ] = open('templates/%s' % tmpl).read()
  
  def render_GET(self,req):
    if req.path == '/':
      return self.mainPage()
    if req.path == '/web.css':
      return open('web.css').read()

  def mainPage(self):
    if self.cpuUsage > 100 or self.cpuUsage < 0:
      cpuUsage = "..."
    else:
      cpuUsage = "%%%.2f" % self.cpuUsage
    memUsage = self.memUsage
    page = self.templates['main'] % locals()
    return page

  def updateUsage(self):
    now = time.time()
    t = posix.times()
    curCpuVal = t[0] + t[1]
    dt = now - self.lastCalcTime
    dv = curCpuVal - self.lastCpuVal
    self.cpuUsage = (dv / dt) * 100.0
    self.lastCalcTime = now
    self.lastCpuVal = curCpuVal
    #self.memUsage = int(open('/proc/self/status').readlines()[12].split()[1])

########NEW FILE########
__FILENAME__ = generate-apache-config
#!/usr/bin/env python

import sys, os
from optparse import OptionParser

option_parser = OptionParser()
option_parser.add_option('--install-root',default='/opt/graphite/',
  help="The base directory of the graphite installation")
option_parser.add_option('--libs',default=None,
  help="The directory where the graphite python package is installed (default is system site-packages)")

(options,args) = option_parser.parse_args()

install_root = options.install_root
if not install_root.endswith('/'):
  install_root += '/'

if not os.path.isdir(install_root):
  print "Graphite does not appear to be installed at %s, do you need to specify a different --install-root?" % install_root
  sys.exit(1)

python_path = [ os.path.join(install_root,'webapp') ]
if options.libs:
  python_path.append( options.libs )

import django
django_root = django.__path__[0]

vhost = open('misc/template-vhost.conf').read()
vhost = vhost.replace('@INSTALL_ROOT@', install_root)
vhost = vhost.replace('@PYTHON_PATH@', str(python_path))
vhost = vhost.replace('@DJANGO_ROOT@', django_root)

fh = open('graphite-vhost.conf','w')
fh.write(vhost)
fh.close()

print "Generated graphite-vhost.conf"
print "Put this file in your apache installation's vhost include directory."
print "NOTE: you must ensure that mod_python is properly configured before using Graphite."

########NEW FILE########
__FILENAME__ = ldapBackend
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import ldap, traceback
from django.conf import settings
from django.contrib.auth.models import User


class LDAPBackend:
  def authenticate(self, username=None, password=None):
    try:
      conn = ldap.initialize(settings.LDAP_URI)
      conn.protocol_version = ldap.VERSION3
      conn.simple_bind_s( settings.LDAP_BASE_USER, settings.LDAP_BASE_PASS )
    except ldap.LDAPError:
      traceback.print_exc()
      return None

    scope = ldap.SCOPE_SUBTREE
    filter = settings.LDAP_USER_QUERY % username
    returnFields = ['dn','mail']
    try:
      resultID = conn.search( settings.LDAP_SEARCH_BASE, scope, filter, returnFields )
      resultType, resultData = conn.result( resultID, 0 )
      if len(resultData) != 1: #User does not exist
        return None

      userDN = resultData[0][0]
      try:
        userMail = resultData[0][1]['mail'][0]
      except:
        userMail = "Unknown"

      conn.simple_bind_s(userDN,password)
      try:
        user = User.objects.get(username=username)
      except: #First time login, not in django's database
        randomPasswd = User.objects.make_random_password(length=16) #To prevent login from django db user
        user = User.objects.create_user(username, userMail, randomPasswd)
        user.save()

      return user

    except ldap.INVALID_CREDENTIALS:
      traceback.print_exc()
      return None

  def get_user(self,user_id):
    try:
      return User.objects.get(pk=user_id)
    except User.DoesNotExist:
      return None

########NEW FILE########
__FILENAME__ = models
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from django.db import models
from django.contrib.auth import models as auth_models


class Profile(models.Model):
  class Admin: pass
  user = models.OneToOneField(auth_models.User)
  history = models.TextField(default="")
  advancedUI = models.BooleanField(default=False)
  __str__ = lambda self: "Profile for %s" % self.user

class Variable(models.Model):
  class Admin: pass
  profile = models.ForeignKey(Profile)
  name = models.CharField(max_length=64)
  value = models.CharField(max_length=64)

class View(models.Model):
  class Admin: pass
  profile = models.ForeignKey(Profile)
  name = models.CharField(max_length=64)
  
class Window(models.Model):
  class Admin: pass
  view = models.ForeignKey(View)
  name = models.CharField(max_length=64)
  top = models.IntegerField()
  left = models.IntegerField()
  width = models.IntegerField()
  height = models.IntegerField()
  url = models.TextField()
  interval = models.IntegerField(null=True)

class MyGraph(models.Model):
  class Admin: pass
  profile = models.ForeignKey(Profile)
  name = models.CharField(max_length=64)
  url = models.TextField()

########NEW FILE########
__FILENAME__ = urls
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from django.conf.urls.defaults import *

urlpatterns = patterns('graphite.account.views',
  ('^login/?$', 'loginView'),
  ('^logout/?$', 'logoutView'),
  ('^edit/?$', 'editProfile'),
  ('^update/?$','updateProfile'),
)

########NEW FILE########
__FILENAME__ = views
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from graphite.util import getProfile
from graphite.logger import log
from graphite.account.models import Profile


def loginView(request):
  username = request.POST.get('username')
  password = request.POST.get('password')
  if request.method == 'GET':
    nextPage = request.GET.get('nextPage','/')
  else:
    nextPage = request.POST.get('nextPage','/')
  if username and password:
    user = authenticate(username=username,password=password)
    if user is None:
      return render_to_response("login.html",{'authenticationFailed' : True, 'nextPage' : nextPage})
    elif not user.is_active:
      return render_to_response("login.html",{'accountDisabled' : True, 'nextPage' : nextPage})
    else:
      login(request,user)
      return HttpResponseRedirect(nextPage)
  else:
    return render_to_response("login.html",{'nextPage' : nextPage})

def logoutView(request):
  nextPage = request.GET.get('nextPage','/')
  logout(request)
  return HttpResponseRedirect(nextPage)

def editProfile(request):
  if not request.user.is_authenticated():
    return HttpResponseRedirect('../..')
  context = { 'profile' : getProfile(request) }
  return render_to_response("editProfile.html",context)

def updateProfile(request):
  profile = getProfile(request,allowDefault=False)
  if profile:
    profile.advancedUI = request.POST.get('advancedUI','off') == 'on'
    profile.save()
  nextPage = request.POST.get('nextPage','/')
  return HttpResponseRedirect(nextPage)

########NEW FILE########
__FILENAME__ = urls
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License."""

from django.conf.urls.defaults import *

urlpatterns = patterns('graphite.browser.views',
  ('^header/?$', 'header'),
  ('^search/?$', 'search'),
  ('^mygraph/?$', 'myGraphLookup'),
  ('^usergraph/?$', 'userGraphLookup'),
  ('^$', 'browser'),
)

########NEW FILE########
__FILENAME__ = views
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import re
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.conf import settings
from graphite.account.models import Profile
from graphite.util import getProfile, getProfileByUsername, defaultUser, json
from graphite.logger import log
import hashlib

try:
  import cPickle as pickle
except ImportError:
  import pickle


def header(request):
  "View for the header frame of the browser UI"
  context = {}
  context['user'] = request.user
  context['profile'] = getProfile(request)
  context['documentation_url'] = settings.DOCUMENTATION_URL
  context['login_url'] = settings.LOGIN_URL
  return render_to_response("browserHeader.html", context)


def browser(request):
  "View for the top-level frame of the browser UI"
  context = {
    'queryString' : request.GET.urlencode(),
    'target' : request.GET.get('target')
  }
  if context['queryString']:
    context['queryString'] = context['queryString'].replace('#','%23')
  if context['target']:
    context['target'] = context['target'].replace('#','%23') #js libs terminate a querystring on #
  return render_to_response("browser.html", context) 


def search(request):
  query = request.POST['query']
  if not query:
    return HttpResponse("")

  patterns = query.split()
  regexes = [re.compile(p,re.I) for p in patterns]
  def matches(s):
    for regex in regexes:
      if regex.search(s):
        return True
    return False

  results = []

  index_file = open(settings.INDEX_FILE)
  for line in index_file:
    if matches(line):
      results.append( line.strip() )
    if len(results) >= 100:
      break

  index_file.close()
  result_string = ','.join(results)
  return HttpResponse(result_string, mimetype='text/plain')


def myGraphLookup(request):
  "View for My Graphs navigation"
  profile = getProfile(request,allowDefault=False)
  assert profile

  nodes = []
  leafNode = {
    'allowChildren' : 0,
    'expandable' : 0,
    'leaf' : 1,
  }
  branchNode = {
    'allowChildren' : 1,
    'expandable' : 1,
    'leaf' : 0,
  }

  try:
    path = str( request.GET['path'] )

    if path:
      if path.endswith('.'):
        userpath_prefix = path

      else:
        userpath_prefix = path + '.'

    else:
      userpath_prefix = ""

    matches = [ graph for graph in profile.mygraph_set.all().order_by('name') if graph.name.startswith(userpath_prefix) ]

    log.info( "myGraphLookup: username=%s, path=%s, userpath_prefix=%s, %ld graph to process" % (profile.user.username, path, userpath_prefix, len(matches)) )
    branch_inserted = set()
    leaf_inserted = set()

    for graph in matches: #Now let's add the matching graph
      isBranch = False
      dotPos = graph.name.find( '.', len(userpath_prefix) )

      if dotPos >= 0:
        isBranch = True
        name = graph.name[ len(userpath_prefix) : dotPos ]
        if name in branch_inserted: continue
        branch_inserted.add(name)

      else:
         name = graph.name[ len(userpath_prefix): ]
         if name in leaf_inserted: continue
         leaf_inserted.add(name)

      node = {'text' : str(name) }

      if isBranch:
        node.update( { 'id' : str(userpath_prefix + name + '.') } )
        node.update(branchNode)

      else:
        m = hashlib.md5()
        m.update(name)
        md5 = m.hexdigest() 
        node.update( { 'id' : str(userpath_prefix + md5), 'graphUrl' : str(graph.url) } )
        node.update(leafNode)

      nodes.append(node)

  except:
    log.exception("browser.views.myGraphLookup(): could not complete request.")

  if not nodes:
    no_graphs = { 'text' : "No saved graphs", 'id' : 'no-click' }
    no_graphs.update(leafNode)
    nodes.append(no_graphs)

  return json_response(nodes, request)

def userGraphLookup(request):
  "View for User Graphs navigation"
  user = request.GET.get('user')
  path = request.GET['path']

  if user:
    username = user
    graphPath = path[len(username)+1:]
  elif '.' in path:
    username, graphPath = path.split('.', 1)
  else:
    username, graphPath = path, None

  nodes = []

  branchNode = {
    'allowChildren' : 1,
    'expandable' : 1,
    'leaf' : 0,
  }
  leafNode = {
    'allowChildren' : 0,
    'expandable' : 0,
    'leaf' : 1,
  }

  try:

    if not username:
      profiles = Profile.objects.exclude(user=defaultUser)

      for profile in profiles:
        if profile.mygraph_set.count():
          node = {
            'text' : str(profile.user.username),
            'id' : str(profile.user.username)
          }

          node.update(branchNode)
          nodes.append(node)

    else:
      profile = getProfileByUsername(username)
      assert profile, "No profile for username '%s'" % username

      if graphPath:
        prefix = graphPath.rstrip('.') + '.'
      else:
        prefix = ''

      matches = [ graph for graph in profile.mygraph_set.all().order_by('name') if graph.name.startswith(prefix) ]
      inserted = set()

      for graph in matches:
        relativePath = graph.name[ len(prefix): ]
        nodeName = relativePath.split('.')[0]

        if nodeName in inserted:
          continue
        inserted.add(nodeName)

        if '.' in relativePath: # branch
          node = {
            'text' : str(nodeName),
            'id' : str(username + '.' + prefix + nodeName + '.'),
          }
          node.update(branchNode)
        else: # leaf
          m = hashlib.md5()
          m.update(nodeName)
          md5 = m.hexdigest() 

          node = {
            'text' : str(nodeName ),
            'id' : str(username + '.' + prefix + md5),
            'graphUrl' : str(graph.url),
          }
          node.update(leafNode)

        nodes.append(node)

  except:
    log.exception("browser.views.userLookup(): could not complete request for %s" % username)

  if not nodes:
    no_graphs = { 'text' : "No saved graphs", 'id' : 'no-click' }
    no_graphs.update(leafNode)
    nodes.append(no_graphs)

  return json_response(nodes, request)


def json_response(nodes, request=None):
  if request:
    jsonp = request.REQUEST.get('jsonp', False)
  else:
    jsonp = False
  #json = str(nodes) #poor man's json encoder for simple types
  json_data = json.dumps(nodes)
  if jsonp:
    response = HttpResponse("%s(%s)" % (jsonp, json_data),mimetype="text/javascript")
  else:
    response = HttpResponse(json_data,mimetype="application/json")
  response['Pragma'] = 'no-cache'
  response['Cache-Control'] = 'no-cache'
  return response


def any(iterable): #python2.4 compatibility
  for i in iterable:
    if i:
      return True
  return False

########NEW FILE########
__FILENAME__ = commands
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import sys, os, urllib, time, traceback, cgi, re, socket
from cPickle import load,dump
from itertools import chain
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from graphite.util import getProfile, getProfileByUsername
from graphite.logger import log
from graphite.account.models import Profile, MyGraph, Variable, View, Window

#Utility functions
def printException():
  out = "<pre style='color: red'>"
  out += traceback.format_exc()
  out += "</pre>"
  return stdout(out)

def stdout(text,lineBreak=True):
  text = text.replace('"',"'")
  text = text.replace('\n','<br/>')
  br = ''
  if lineBreak: br = "<br/>"
  return """$('output').innerHTML += "%s%s"; """ % (text,br)

def stderr(text):
  return """$('output').innerHTML += "<font color='red'><b>%s</b></font><br/>"; """ % text.replace('"',"'")

#Commands
def _set(request,name,value):
  profile = getProfile(request)
  try:
    variable = profile.variable_set.get(name=name)
    variable.value = value
  except ObjectDoesNotExist:
    variable = Variable(profile=profile,name=name,value=value)
  variable.save()
  return ''

def _unset(request,name):
  profile = getProfile(request)
  try:
    variable = profile.variable_set.get(name=name)
    variable.delete()
  except ObjectDoesNotExist:
    return stderr("Unknown variable %s" % name)
  return ''

def _echo(request,args):
  return stdout(args)

def _vars(request):
  profile = getProfile(request)
  out = '<font color="#77ddcc">'
  for variable in profile.variable_set.all():
    out += '%s = %s<br/>' % (variable.name,variable.value)
  out += '</font>'
  return stdout(out)

def _clear(request):
  return "$('output').innerHTML = '';\n"

def _create(request,window):
  out = ''
  w = window.replace('.', '_')
  #Basic window creation
  out += "%s_win = new Window('%s_win', {title: '%s',width: 350, height: 225, maximizable: false});\n" % (w,w,w)
  out += "center = Builder.node( 'center', [Builder.node('img', {id: '%s_img',src: '/content/img/graphite.png'} )] );\n" % w
  out += "%s_win.getContent().appendChild( center );\n" % w
  out += "%s_win.setDestroyOnClose();\n" % w
  out += "%s_win.showCenter();\n" % w
  #Useful redraw function
  out += "function %s_redraw() {\n" % w
  out += "  if (window.%s_timer) { clearTimeout(window.%s_timer); }\n" % (w,w)
  out += "  img = $('%s_img');\n" % w
  out += "  if (!img) { return false; }\n"
  out += "  url = img.src;\n"
  out += "  i = url.indexOf('&uniq=');\n"
  out += "  if (i == -1) {\n"
  out += "    url += '&uniq=' + Math.random();\n"
  out += "  } else {\n"
  out += "    url = url.replace(/&uniq=[^&]+/,'&uniq=' + Math.random());\n"
  out += "  }\n"
  out += "  img.src = url;\n"
  out += "  window.%s_timer = setTimeout('window.%s_redraw()', window.%s_interval);\n" % (w,w,w)
  out += "}\n"
  out += "window.%s_redraw = %s_redraw;\n" % (w,w)
  return out

def _draw(request,targets,_from=None,until=None,template=None,window=None,interval=None):
    out = ''
    params = [ ('target',t) for t in targets ]
    if _from: params.append( ('from',_from) )
    if until: params.append( ('until',until) )
    if template: params.append( ('template',template) )
    url = '/render?' + urllib.urlencode(params)
    if window:
      w = window
      out += "win = %s_win;\n" % w
      out += "img_id = '%s_img';\n" % w
      out += "img = $(img_id);\n"
      out += "if (!win) {\n"
      out += "  alert('No such window %s');\n" % w
      out += "} else {\n"
      out += "  url = '%s';\n" % url
      out += "  size = win.getSize();\n"
      out += "  if (size['height'] < 100 || size['width'] < 100) {\n"
      out += "     alert('Window is too small!');\n"
      out += "  } else {\n"
      out += "    url += '&height=' + (size['height']) + '&' + 'width=' + (size['width']);\n"
      out += "    window.changeImage(win,url);\n"
      out += "  }\n"
      out += "}\n"
      if interval:
        i = int(interval)
	out += "window.%s_interval = %d * 60000;\n" % (w,i)
        out += "window.%s_timer = setTimeout('window.%s_redraw()', window.%s_interval);\n" % (w,w,w)
    else:
      return stdout("<img src='%s' onload='scrollBy(0,this.height + 1000);'>" % url)
    return out

def _redraw(request,window,interval):
  out = ''
  w = window
  i = int(interval)
  out += "img = $('%s_img');\n" % w
  out += "if (!img) {\n"
  out += "  alert('No such window %s');\n" % w
  out += "} else {\n"
  out += "  if (window.%s_timer) { clearTimeout(window.%s_timer); }\n" % (w,w)
  out += "  window.%s_interval = %d * 60000;\n" % (w,i)
  out += "  window.%s_timer = setTimeout('window.%s_redraw()', window.%s_interval);\n" % (w,w,w)
  out += "}\n"
  return out

def _email(request,window,addressList):
  out = ''
  w = window
  addrList = ','.join(addressList)
  params = { 'commandInput' : 'doemail', 'recipients' : addrList, 'title' : w}
  paramStr = urllib.urlencode(params)
  out += "img = $('%s_img');\n" % w
  out += "if (!img) {\n"
  out += "  alert('No such window %s');\n" % w
  out += "} else {\n"
  out += "  url = img.src;\n"
  out += "  params = '%s' + '&url=' + escape(url);\n" % paramStr
  out += "  emailreq = new Ajax.Request('/cli/eval', {method: 'get', parameters: params, onException: handleException, onComplete: handleResponse});\n"
  out += "}\n"
  return out

def _doemail(request):
  cgiParams = request.GET
  assert 'recipients' in cgiParams and 'url' in cgiParams and 'title' in cgiParams, "Incomplete doemail, requires recipients, url, and title"
  import smtplib, httplib, urlparse
  from email.MIMEMultipart import MIMEMultipart
  from email.MIMEText import MIMEText
  from email.MIMEImage import MIMEImage
  url = cgiParams['url']
  title = cgiParams['title']
  recipients = cgiParams['recipients'].split(',')
  proto, server, path, query, frag = urlparse.urlsplit(url)
  if query: path += '?' + query
  conn = httplib.HTTPConnection(server)
  conn.request('GET',path)
  resp = conn.getresponse()
  assert resp.status == 200, "Failed HTTP response %s %s" % (resp.status, resp.reason)
  rawData = resp.read()
  conn.close()
  message = MIMEMultipart()
  message['Subject'] = "Graphite Image"
  message['To'] = ', '.join(recipients)
  message['From'] = 'frontend@%s' % socket.gethostname()
  text = MIMEText( "Image generated by the following graphite URL at %s\r\n\r\n%s" % (time.ctime(),url) )
  image = MIMEImage( rawData )
  image.add_header('Content-Disposition', 'attachment', filename=title + time.strftime("_%b%d_%I%M%p.png"))
  message.attach(text)
  message.attach(image)
  server = smtplib.SMTP(settings.SMTP_SERVER)
  server.sendmail('frontend@%s' % socket.gethostname(),recipients,message.as_string())
  server.quit()
  return stdout("Successfully sent %s to %s" % (url,cgiParams['recipients']))

def _code(request,code):
  return code

def _url(request,window):
  out = ''
  w = window
  out += "img = $('%s_img');\n" % w
  out += "if (!img) {\n"
  out += "  alert('No such window %s');\n" % w
  out += "} else {\n"
  out += "  url = img.src;\n"
  out += "  $('output').innerHTML += '%s URL is ' + url + '<br/>';\n" % w
  out += "}\n"
  return out

def _help(request):
  return "window.open('%s','doc');" % settings.DOCUMENTATION_URL

def _change(request,window,var,value):
  out = ''
  out += "function changeWindow(win) {\n"
  out += "  var img = $(win + '_img');\n"
  out += "  if (!img) {\n"
  out += "    alert('No such window ' + win);\n"
  out += "  } else {\n"
  out += "    var url = new String(img.src);\n"
  out += "    var i = url.indexOf('?');\n"
  out += "    if (i == -1) {\n"
  out += "      alert('Invalid url in image! url=' + url);\n"
  out += "    } else {\n"
  out += "      var base = url.substring(0,i);\n"
  out += "      var qs = url.substring(i+1,url.length+1);\n"
  out += "      var found = false;\n"
  out += "      var pairs = qs.split('&').collect( function(pair) {\n"
  out += "        var p = pair.split('=');\n"
  out += "        if (p[0] == '%s') {\n" % var
  out += "          found = true;\n"
  out += "          return p[0] + '=' + escape('%s');\n" % value
  out += "        }\n"
  out += "        return pair;\n"
  out += "      });\n"
  out += "      var newqs = pairs.join('&');\n"
  out += "      if (!found) { newqs += '&%s=' + escape('%s'); }\n" % (var,value)
  out += "      img.src = base + '?' + newqs;\n"
  out += "    }\n"
  out += "  }\n"
  out += "}\n"
  if window == '*':
    out += "Windows.windows.each( function(winObject) {\n"
    out += "  var name = winObject.getId().replace('_win','');\n"
    out += "  changeWindow(name);\n"
    out += "});\n"
  else:
    out += "changeWindow('%s');" % window
  return out

def _add(request,target,window):
  out = ''
  out += "img = $('%s_img');\n" % window
  out += "if (!img) {\n"
  out += "  alert('No such window %s');\n" % window
  out += "} else {\n"
  out += "  if (img.src.indexOf('/render') == -1) {\n"
  out += "    img.src = '/render?';\n"
  out += "  }\n"
  out += "  img.src = img.src + '&target=' + encodeURIComponent('%s');\n" % target
  out += "}\n"
  return out

def _remove(request,target,window):
  out = ''
  out += "img = $('%s_img');\n" % window
  out += "if (!img) {\n"
  out += "  alert('No such window %s');\n" % window
  out += "} else {\n"
  out += "  var url = new String(img.src);\n"
  out += "  var beginningTarget = '?target=' + encodeURIComponent('%s');\n" % target
  out += "  var newurl = url.replace(beginningTarget,'?');\n"
  out += "  var laterTarget = '&target=' + escape('%s');\n" % target
  out += "  newurl = newurl.replace(laterTarget,'');\n"
  out += "  img.src = newurl;\n"
  out += "}\n"
  return out

def _find(request,pattern):
  pattern = pattern.strip()
  r = re.compile(pattern,re.I)
  out = ''
  found = 0
  displayMax = 100
  rrdIndex = open(settings.STORAGE_DIR + '/rrd_index')
  wspIndex = open(settings.STORAGE_DIR + '/wsp_index')
  for line in chain(wspIndex,rrdIndex):
    if r.search(line):
      found += 1
      if found <= displayMax:
        out += line.replace('/','.')
  if found >= displayMax:
    out += '<font color="red">Displaying %d out of %d matches, try refining your search</font>' % (displayMax,found)
  else:
    out += 'Found %d matches' % found
  return stdout(out)

def _save(request,view):
  if not settings.ALLOW_ANONYMOUS_CLI and not request.user.is_authenticated():
    return stderr("You must be logged in to use this functionality.")
  out = ''
  out += "allParams = {};\n"
  out += "Windows.windows.each( function(winObject) {\n"
  out += "  name = winObject.getId().replace('_win','');\n"
  out += "  winElement = $(name + '_win');\n"
  out += "  img_id = name + '_img';\n"
  out += "  img = $(img_id);\n"
  out += "  url = img.src;\n"
  out += "  _top = winElement.style.top\n"
  out += "  left = winElement.style.left\n"
  out += "  size = winObject.getSize();\n"
  out += "  width = size.width;\n"
  out += "  height = size.height;\n"
  out += "  myParams = 'top=' + _top + '&left=' + left + '&width=' + width + '&height=' + height + '&url=' + escape(url);\n"
  out += "  if (window[name+'_interval']) { myParams += '&interval=' + window[name+'_interval']; }\n"
  out += "  allParams[name] = escape(myParams);\n"
  out += "});\n"
  out += "if (allParams) {\n"
  out += "  queryString = 'commandInput=dosave%%20%s&' + $H(allParams).toQueryString();\n" % view
  out += "  savereq = new Ajax.Request('/cli/eval', {method: 'get', parameters: queryString, onException: handleException, onComplete: handleResponse});\n"
  out += "}\n"
  return out

def _dosave(request,viewName):
  profile = getProfile(request)
  #First find our View
  log.info("Saving view '%s' under profile '%s'" % (viewName,profile.user.username))
  try:
    view = profile.view_set.get(name=viewName)
  except ObjectDoesNotExist:
    view = View(profile=profile,name=viewName)
    view.save()
  #Now re-associate the view with the correct Windows
  view.window_set.all().delete()
  for windowName,encodedString in request.GET.items():
    try:
      if windowName in ('_','commandInput'): continue
      paramString = urllib.unquote_plus(encodedString)
      queryParams = cgi.parse_qs(paramString)
      modelParams = {}
      for key,value in queryParams.items(): #Clean up the window params
        key = str(key)
        value = str(value[0])
        if key in ('top','left'):
          value = int(float( value.replace('px','') ))
        if key in ('width','height','interval'):
          value = int(float(value))
        modelParams[key] = value
      if 'interval' not in modelParams:
        modelParams['interval'] = None
      win = Window(view=view,name=windowName,**modelParams)
      win.save()
    except:
      log.exception("Failed to process parameters for window '%s'" % windowName)
  return stdout('Saved view %s' % viewName)

def _load(request,viewName,above=None):
  if above:
    out = stdout("Loading view %s above the current view" % viewName)
  else:
    out = stdout("Loading view %s" % viewName)
  profile = getProfile(request)
  try:
    view = profile.view_set.get(name=viewName)
  except ObjectDoesNotExist:
    return stderr("Unknown view %s" % viewName)
  if not above:
    out += "Windows.windows.each( function(w) {w.destroy();} );"
  for window in view.window_set.all():
    out += _create(request,window.name)
    out += "win = %s_win;" % window.name
    out += "$('%s_img').src = '%s';" % (window.name,window.url)
    out += "win.show();"
    out += "win.setLocation(%d,%d);" % (window.top,window.left)
    out += "win.setSize(%d,%d);" % (window.width,window.height)
    if window.interval:
      out += "window.%s_interval = %d;" % (window.name,window.interval)
      out += "window.%s_timer = setTimeout('window.%s_redraw()', window.%s_interval);" % ((window.name,) * 3)
  return out

def _gsave(request,graphName):
  profile = getProfile(request,allowDefault=False)
  if not profile: return stderr("You must be logged in to save graphs")
  out =  "img = $('%s_img');\n" % graphName
  out += "if (!img) {\n"
  out += "  alert('No such window');\n"
  out += "} else {\n"
  out += "  queryString = 'commandInput=dogsave%%20%s&url=' + escape(img.src);\n" % graphName
  out += "  savereq = new Ajax.Request('/cli/eval', {method: 'get', parameters: queryString, onException: handleException, onComplete: handleResponse});\n"
  out += "}\n"
  return out

def _dogsave(request,graphName):
  profile = getProfile(request,allowDefault=False)
  if not profile: return stderr("You must be logged in to save graphs")
  url = request.GET.get('url')
  if not url: return stderr("No url specified!")
  try:
    existingGraph = profile.mygraph_set.get(name=graphName)
    existingGraph.url = url
    existingGraph.save()
  except ObjectDoesNotExist:
    try:
      newGraph = MyGraph(profile=profile,name=graphName,url=url)
      newGraph.save()
    except:
      log.exception("Failed to create new MyGraph in _dogsave(), graphName=%s" % graphName)
      return stderr("Failed to save graph %s" % graphName)
  return stdout("Saved graph %s" % graphName)

def _gload(request,user=None,graphName=None):
  if not user:
    profile = getProfile(request,allowDefault=False)
    if not profile: return stderr("You are not logged in so you must specify a username")
  else:
    try:
      profile = getProfileByUsername(user)
    except ObjectDoesNotExist:
      return stderr("User does not exist")
  try:
    myGraph = profile.mygraph_set.get(name=graphName)
  except ObjectDoesNotExist:
    return stderr("Graph does not exist")
  out = _create(request,myGraph.name)
  out += "changeImage(%s_win,'%s');\n" % (myGraph.name.replace('.', '_'), myGraph.url)
  return out

def _graphs(request,user=None):
  if not user:
    profile = getProfile(request,allowDefault=False)
    if not profile: return stderr("You are not logged in so you must specify a username")
  else:
    try:
      profile = getProfileByUsername(user)
    except ObjectDoesNotExist:
      return stderr("User does not exist")
  out = ""
  if user:
    prefix = "~%s/" % user
  else:
    prefix = ""
  for graph in profile.mygraph_set.all():
    out += stdout(prefix + graph.name)
  return out

def _views(request):
  out = ''
  profile = getProfile(request)
  for view in profile.view_set.all():
    windowList = ','.join([window.name for window in view.window_set.all()])
    out += stdout("%s: %s" % (view.name,windowList))
  return out

def _rmview(request,viewName):
  profile = getProfile(request)
  try:
    view = profile.view_set.get(name=viewName)
  except ObjectDoesNotExist:
    return stderr("No such view '%s'" % viewName)
  view.delete()
  return stdout("Deleted view %s" % viewName)

def _rmgraph(request,graphName):
  profile = getProfile(request,allowDefault=False)
  try:
    graph = profile.mygraph_set.get(name=graphName)
  except ObjectDoesNotExist:
    return stderr("No such graph %s" % graphName)
  graph.delete()
  return stdout("Deleted graph %s" % graphName)

def _compose(request,window):
  out  = "var url = $('%s_img').src;\n" % window
  out += "var re = /target=([^&]+)/;\n"
  out += "if ( url.match(re) == null ) {\n"
  out += "  alert('Image has no targets!');\n"
  out += "} else {\n"
  out += "  composerURL = '/?' + url.substr(url.indexOf('?') + 1);\n";
  out += "  composerWin = window.open(composerURL, 'GraphiteComposer');\n"
  out += stdout('A new composer window has been opened.')
  #out += "  var i = 0;"
  #out += "  var m = true;\n"
  #out += "  while ( m = url.substr(i).match(re) ) {\n"
  #out += "    setTimeout(\"composerWin.Composer.toggleTarget('\" + m[1] + \"')\",2500);\n"
  #out += "    i += m.index + m[1].length;\n"
  #out += "  }\n"
  out += "}\n"
  return out

def _login(request):
  if request.user.is_authenticated():
    return stderr("You are already logged in as %s" % request.user.username)
  else:
    return "window.location = '/account/login/?nextPage=' + encodeURIComponent('/cli/');"

def _logout(request):
  if not request.user.is_authenticated():
    return stderr("You are not logged in!")
  else:
    return "window.location = '/account/logout/?nextPage=' + encodeURIComponent('/cli/');"

def _id(request):
  if request.user.is_authenticated():
    return stdout("You are logged in as %s" % request.user.username)
  else:
    return stdout("You are not logged in.")
_whoami = _id

########NEW FILE########
__FILENAME__ = completer
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import sys, os, re
from django.conf import settings
from graphite.util import getProfile
from graphite.logger import log
from graphite.storage import STORE


def completeHistory(path, profile):
  html = ''
  if path[:1] == '!': path = path[1:]
  html += "<ul>"
  history = profile.history.split('\n')
  for line in history:
    line = line.strip()
    if not line: continue
    if line.startswith(path):
      html += "<li>" + line + "</li>"
  html += "</ul>"
  return html

def completePath(path, shortnames=False):
  # Have to extract the path expression from the command
  for prefix in ('draw ','add ','remove '):
    if path.startswith(prefix):
      path = path[len(prefix):]
      break

  pattern = re.sub('\w+\(','',path).replace(')','') + '*'

  results = []
  
  for match in STORE.find(pattern):
    if shortnames:
      results.append(match.name)
    else:
      results.append(match.metric_path)

  list_items = ["<li>%s</li>" % r for r in results]
  list_element = "<ul>" + '\n'.join(list_items) + "</ul>"
  return list_element

########NEW FILE########
__FILENAME__ = parser
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from graphite.thirdparty.pyparsing import *

grammar = Forward()

#common stuff
dash = Literal('-')
nondash = Word(printables.replace('-',''),max=1)
path = Word(printables).setResultsName('path')

#set/unset
_set = Keyword('set').setResultsName('command')
set_cmd = _set + Word(alphas).setResultsName('name') + Word(printables).setResultsName('value')
unset = Keyword('unset').setResultsName('command')
unset_cmd = unset + Word(alphas).setResultsName('name')

#echo
echo = Keyword('echo').setResultsName('command')
echo_cmd = echo + Word(printables).setResultsName('args')

#vars
vars_cmd = Keyword('vars').setResultsName('command')

#clear
clear_cmd = Keyword('clear').setResultsName('command')

#create window [style]
window = Word(alphanums+'_').setResultsName('window')
create_cmd = Keyword('create').setResultsName('command') + window

#draw
draw = Keyword('draw').setResultsName('command')

gpath = Word(alphanums + '._-+*?[]#:')
fcall = Forward()
expr = Word( printables.replace('(','').replace(')','').replace(',','') )
arg = fcall | expr
fcall << Combine( Word(alphas) + Literal('(') + arg + ZeroOrMore(',' + arg) + Literal(')') )
target = fcall | gpath
targetList = delimitedList(target).setResultsName('targets')
_from = Literal('from') + Word(printables).setResultsName('_from')
until = Literal('until') + Word(printables).setResultsName('until')
redrawspec = Literal('every') + Word(nums).setResultsName('interval')
winspec = Literal('in') + window
tempspec = Literal('using') + Word(printables).setResultsName('template')
options = Each( [Optional(_from), Optional(until), Optional(winspec), Optional(redrawspec), Optional(tempspec)] )
draw_cmd = draw + targetList + options

#change
var = Word(printables).setResultsName('var')
value = restOfLine.setResultsName('value')
change_cmd = Keyword('change').setResultsName('command') + Word(alphanums+'_*').setResultsName('window') + var + Literal('to ').suppress() + value

#add/remove
add_cmd = Keyword('add').setResultsName('command') + target.setResultsName('target') + Literal('to').suppress() + window
remove_cmd = Keyword('remove').setResultsName('command') + target.setResultsName('target') + Literal('from').suppress() + window

#help
help_cmd = Keyword('help').setResultsName('command')

#redraw
redraw_cmd = Keyword('redraw').setResultsName('command') + window + Literal('every') + Word(nums).setResultsName('interval')

#code
code_cmd = Keyword('code').setResultsName('command') + restOfLine.setResultsName('code')

#email
email_cmd = Keyword('email').setResultsName('command') + window + Literal('to') + commaSeparatedList.setResultsName('addressList')
doemail_cmd = Keyword('doemail').setResultsName('command')

#url
url_cmd = Keyword('url').setResultsName('command') + window
  
#find
find_cmd = Keyword('find').setResultsName('command') + restOfLine.setResultsName('pattern')

#save/load
view = Word(alphanums+'-_.')
save_cmd = Keyword('save').setResultsName('command') + view.setResultsName('view')
dosave_cmd = Keyword('dosave').setResultsName('command') + view.setResultsName('viewName')
load_cmd = Keyword('load').setResultsName('command') + view.setResultsName('viewName') + Optional( Keyword('above').setResultsName('above') )

#views
views_cmd = Keyword('views').setResultsName('command')

#gsave/gload
tilde = Literal('~').suppress()
slash = Literal('/').suppress()
user = Word(alphanums+'_')
graph = Word(alphanums+'_.')
gsave_cmd = Keyword('gsave').setResultsName('command') + graph.setResultsName('graphName')
dogsave_cmd = Keyword('dogsave').setResultsName('command') + graph.setResultsName('graphName')
gload_cmd = Keyword('gload').setResultsName('command') + Optional(tilde + user.setResultsName('user') + slash) + graph.setResultsName('graphName')

#graphs
graphs_cmd = Keyword('graphs').setResultsName('command') + Optional(user.setResultsName('user'))

#rmview
rmview_cmd = Keyword('rmview').setResultsName('command') + view.setResultsName('viewName')

#rmgraph
rmgraph_cmd = Keyword('rmgraph').setResultsName('command') + graph.setResultsName('graphName')

#compose
compose_cmd = Keyword('compose').setResultsName('command') + window

#login
login_cmd = Keyword('login').setResultsName('command')

#logout
logout_cmd = Keyword('logout').setResultsName('command')

#id/whoami
id_cmd = Keyword('id').setResultsName('command')
whoami_cmd = Keyword('whoami').setResultsName('command')

grammar << ( set_cmd | unset_cmd | add_cmd | remove_cmd | \
             draw_cmd | echo_cmd | vars_cmd | clear_cmd | \
             create_cmd | code_cmd | redraw_cmd | email_cmd | doemail_cmd | \
             url_cmd | change_cmd | help_cmd | find_cmd | save_cmd | \
             load_cmd | dosave_cmd | views_cmd | rmview_cmd | compose_cmd | \
             login_cmd | logout_cmd | id_cmd | whoami_cmd | \
             gsave_cmd | dogsave_cmd | gload_cmd | graphs_cmd | rmgraph_cmd | Empty() \
)

def parseInput(s):
  return grammar.parseString(s)

########NEW FILE########
__FILENAME__ = urls
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from django.conf.urls.defaults import *

urlpatterns = patterns('graphite.cli.views',
     (r'^autocomplete/?$', 'autocomplete'),
     (r'^eval/?$', 'evaluate'),
     (r'', 'cli'),
)

########NEW FILE########
__FILENAME__ = views
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from string import letters
from django.http import HttpResponse
from django.shortcuts import render_to_response
from graphite.util import getProfile
from graphite.cli import completer, commands, parser

def cli(request):
  context = dict( request.GET.items() )
  context['user'] = request.user
  context['profile'] = getProfile(request)
  return render_to_response("cli.html", context)

def autocomplete(request):
  assert 'path' in request.GET, "Invalid request, no 'path' parameter!"
  path = request.GET['path']
  shortnames = bool( request.GET.get('short') )

  if request.GET['path'][:1] == '!':
    profile = getProfile(request)
    html = completer.completeHistory(path, profile)
  else:
    html = completer.completePath(path, shortnames=shortnames)

  return HttpResponse( html )

def evaluate(request):
  if 'commandInput' not in request.GET:
    output = commands.stderr("No commandInput parameter!")
    return HttpResponse(output, mimetype='text/plain')

  #Variable substitution
  profile = getProfile(request)
  my_vars = {}
  for variable in profile.variable_set.all():
    my_vars[variable.name] = variable.value
  cmd = request.GET['commandInput']
  while '$' in cmd and not cmd.startswith('code'):
    i = cmd.find('$')
    j = i+1
    for char in cmd[i+1:]:
      if char not in letters: break
      j += 1
    var = cmd[i+1:j]
    if var in my_vars:
      cmd = cmd[:i] + my_vars[var] + cmd[j:]
    else:
      output = commands.stderr("Unknown variable %s" % var)
      return HttpResponse(output, mimetype='text/plain')

  if cmd == '?': cmd = 'help'

  try:
    tokens = parser.parseInput(cmd)

    if not tokens.command:
      output = commands.stderr("Invalid syntax")
      return HttpResponse(output, mimetype='text/plain')

    handler_name = '_' + tokens.command
    handler = vars(commands).get(handler_name)
    if handler is None:
      output = commands.stderr("Unknown command")
      return HttpResponse(output, mimetype='text/plain')

    args = dict( tokens.items() )
    del args['command']
    output = handler(request, **args)
  except:
    output = commands.printException()

  #Save command to history
  history = profile.history.split('\n')
  history.insert(0,cmd)
  while len(history) > 30: history.pop()
  profile.history = '\n'.join(history)
  profile.save()

  return HttpResponse(output, mimetype='text/plain')

########NEW FILE########
__FILENAME__ = urls
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from django.conf.urls.defaults import *

urlpatterns = patterns('graphite.composer.views',
  ('send_email','send_email'),
  ('mygraph', 'mygraph'),
  ('', 'composer'),
)

########NEW FILE########
__FILENAME__ = views
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import os
from smtplib import SMTP
from socket import gethostname
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from httplib import HTTPConnection
from urlparse import urlsplit
from time import ctime, strftime
from traceback import format_exc
from graphite.util import getProfile
from graphite.logger import log
from graphite.account.models import MyGraph

from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

def composer(request):
  profile = getProfile(request)
  context = {
    'queryString' : request.GET.urlencode().replace('+','%20'),
    'showTarget' : request.GET.get('showTarget',''),
    'user' : request.user,
    'profile' : profile,
    'showMyGraphs' : int( profile.user.username != 'default' ),
    'searchEnabled' : int( os.access(settings.INDEX_FILE, os.R_OK) ),
    'debug' : settings.DEBUG,
    'jsdebug' : settings.DEBUG,
  }
  return render_to_response("composer.html",context)


def mygraph(request):
  profile = getProfile(request, allowDefault=False)

  if not profile:
    return HttpResponse( "You are not logged in!" )

  action = request.GET['action']
  graphName = request.GET['graphName']

  if not graphName:
    return HttpResponse("You must type in a graph name.")

  if action == 'save':
    url = request.GET['url']

    try:
      existingGraph = profile.mygraph_set.get(name=graphName)
      existingGraph.url = url
      existingGraph.save()

    except ObjectDoesNotExist:
      try:
        newGraph = MyGraph(profile=profile,name=graphName,url=url)
        newGraph.save()

      except:
        log.exception("Failed to create new MyGraph in /composer/mygraph/, graphName=%s" % graphName)
        return HttpResponse("Failed to save graph %s" % graphName)

    return HttpResponse("SAVED")

  elif action == 'delete':
    try:
      existingGraph = profile.mygraph_set.get(name=graphName)
      existingGraph.delete()

    except ObjectDoesNotExist:
      return HttpResponse("No such graph '%s'" % graphName)

    return HttpResponse("DELETED")

  else:
    return HttpResponse("Invalid operation '%s'" % action)


def send_email(request):
  try:
    recipients = request.GET['to'].split(',')
    url = request.GET['url']
    proto, server, path, query, frag = urlsplit(url)
    if query: path += '?' + query
    conn = HTTPConnection(server)
    conn.request('GET',path)
    resp = conn.getresponse()
    assert resp.status == 200, "Failed HTTP response %s %s" % (resp.status, resp.reason)
    rawData = resp.read()
    conn.close()
    message = MIMEMultipart()
    message['Subject'] = "Graphite Image"
    message['To'] = ', '.join(recipients)
    message['From'] = 'composer@%s' % gethostname()
    text = MIMEText( "Image generated by the following graphite URL at %s\r\n\r\n%s" % (ctime(),url) )
    image = MIMEImage( rawData )
    image.add_header('Content-Disposition', 'attachment', filename="composer_" + strftime("%b%d_%I%M%p.png"))
    message.attach(text)
    message.attach(image)
    s = SMTP(settings.SMTP_SERVER)
    s.sendmail('composer@%s' % gethostname(),recipients,message.as_string())
    s.quit()
    return HttpResponse( "OK" )
  except:
    return HttpResponse( format_exc() )

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth import models as auth_models
from graphite.account.models import Profile


class Dashboard(models.Model):
  class Admin: pass
  name = models.CharField(primary_key=True, max_length=128)
  owners = models.ManyToManyField(Profile, related_name='dashboards')
  state = models.TextField()
  __str__ = lambda self: "Dashboard [%s]" % self.name

########NEW FILE########
__FILENAME__ = send_graph
from django.core.mail import EmailMessage
from graphite.logger import log

def send_graph_email(subject, sender, recipients, attachments=None, body=None):
    """
    :param str sender: sender's email address
    :param list recipients: list of recipient emails
    :param list attachments: list of triples of the form:
        (filename, content, mimetype). See the django docs
        https://docs.djangoproject.com/en/1.3/topics/email/#django.core.mail.EmailMessage
    """
    attachments = attachments or []
    msg = EmailMessage(subject=subject, 
		       from_email=sender, 
                       to=recipients, 
		       body=body,
                       attachments=attachments)
    msg.send()

	

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('graphite.dashboard.views',
  ('^save/(?P<name>[^/]+)', 'save'),
  ('^load/(?P<name>[^/]+)', 'load'),
  ('^delete/(?P<name>[^/]+)', 'delete'),
  ('^create-temporary/?', 'create_temporary'),
  ('^email', 'email'),
  ('^find/', 'find'),
  ('^help/', 'help'),
  ('^(?P<name>[^/]+)', 'dashboard'),
  ('', 'dashboard'),
)

########NEW FILE########
__FILENAME__ = views
import re
import errno
import json
from os.path import getmtime, join, exists
from urllib import urlencode
from ConfigParser import ConfigParser
from django.shortcuts import render_to_response
from django.http import HttpResponse, QueryDict
from django.conf import settings
from graphite.util import json
from graphite.dashboard.models import Dashboard
from graphite.render.views import renderView
from send_graph import send_graph_email


fieldRegex = re.compile(r'<([^>]+)>')
defaultScheme = {
  'name' : 'Everything',
  'pattern' : '<category>',
  'fields' : [ dict(name='category', label='Category') ],
}
defaultUIConfig = {
  'default_graph_width'  : 400,
  'default_graph_height' : 250,
  'refresh_interval'     :  60,
  'autocomplete_delay'   : 375,
  'merge_hover_delay'    : 700,
  'theme'                : 'default',
}
defaultKeyboardShortcuts = {
  'toggle_toolbar' : 'ctrl-z',
  'toggle_metrics_panel' : 'ctrl-space',
  'erase_all_graphs' : 'alt-x',
  'save_dashboard' : 'alt-s',
  'completer_add_metrics' : 'alt-enter',
  'completer_del_metrics' : 'alt-backspace',
  'give_completer_focus' : 'shift-space',
}


class DashboardConfig:
  def __init__(self):
    self.last_read = 0
    self.schemes = [defaultScheme]
    self.ui_config = defaultUIConfig.copy()

  def check(self):
    if getmtime(settings.DASHBOARD_CONF) > self.last_read:
      self.load()

  def load(self):
    schemes = [defaultScheme]
    parser = ConfigParser()
    parser.read(settings.DASHBOARD_CONF)

    for option, default_value in defaultUIConfig.items():
      if parser.has_option('ui', option):
        try:
          self.ui_config[option] = parser.getint('ui', option)
        except ValueError:
          self.ui_config[option] = parser.get('ui', option)
      else:
        self.ui_config[option] = default_value

    if parser.has_option('ui', 'automatic_variants'):
      self.ui_config['automatic_variants']   = parser.getboolean('ui', 'automatic_variants')
    else:
      self.ui_config['automatic_variants'] = True

    self.ui_config['keyboard_shortcuts'] = defaultKeyboardShortcuts.copy()
    if parser.has_section('keyboard-shortcuts'):
      self.ui_config['keyboard_shortcuts'].update( parser.items('keyboard-shortcuts') )

    for section in parser.sections():
      if section in ('ui', 'keyboard-shortcuts'):
        continue

      scheme = parser.get(section, 'scheme')
      fields = []

      for match in fieldRegex.finditer(scheme):
        field = match.group(1)
        if parser.has_option(section, '%s.label' % field):
          label = parser.get(section, '%s.label' % field)
        else:
          label = field

        fields.append({
          'name' : field,
          'label' : label
        })

      schemes.append({
        'name' : section,
        'pattern' : scheme,
        'fields' : fields,
      })

    self.schemes = schemes


config = DashboardConfig()


def dashboard(request, name=None):
  dashboard_conf_missing = False

  try:
    config.check()
  except OSError, e:
    if e.errno == errno.ENOENT:
      dashboard_conf_missing = True
    else:
      raise

  initialError = None
  debug = request.GET.get('debug', False)
  theme = request.GET.get('theme', config.ui_config['theme'])
  css_file = join(settings.CSS_DIR, 'dashboard-%s.css' % theme)
  if not exists(css_file):
    initialError = "Invalid theme '%s'" % theme
    theme = config.ui_config['theme']

  context = {
    'schemes_json' : json.dumps(config.schemes),
    'ui_config_json' : json.dumps(config.ui_config),
    'jsdebug' : debug or settings.JAVASCRIPT_DEBUG,
    'debug' : debug,
    'theme' : theme,
    'initialError' : initialError,
    'querystring' : json.dumps( dict( request.GET.items() ) ),
    'dashboard_conf_missing' : dashboard_conf_missing,
  }

  if name is not None:
    try:
      dashboard = Dashboard.objects.get(name=name)
    except Dashboard.DoesNotExist:
      context['initialError'] = "Dashboard '%s' does not exist." % name
    else:
      context['initialState'] = dashboard.state

  return render_to_response("dashboard.html", context)


def save(request, name):
  # Deserialize and reserialize as a validation step
  state = str( json.dumps( json.loads( request.POST['state'] ) ) )

  try:
    dashboard = Dashboard.objects.get(name=name)
  except Dashboard.DoesNotExist:
    dashboard = Dashboard.objects.create(name=name, state=state)
  else:
    dashboard.state = state
    dashboard.save();

  return json_response( dict(success=True) )


def load(request, name):
  try:
    dashboard = Dashboard.objects.get(name=name)
  except Dashboard.DoesNotExist:
    return json_response( dict(error="Dashboard '%s' does not exist. " % name) )

  return json_response( dict(state=json.loads(dashboard.state)) )


def delete(request, name):
  try:
    dashboard = Dashboard.objects.get(name=name)
  except Dashboard.DoesNotExist:
    return json_response( dict(error="Dashboard '%s' does not exist. " % name) )
  else:
    dashboard.delete()
    return json_response( dict(success=True) )


def find(request):
  query = request.REQUEST['query']
  query_terms = set( query.lower().split() )
  results = []

  # Find all dashboard names that contain each of our query terms as a substring
  for dashboard in Dashboard.objects.all():
    name = dashboard.name.lower()
    if name.startswith('temporary-'):
      continue

    found = True # blank queries return everything
    for term in query_terms:
      if term in name:
        found = True
      else:
        found = False
        break

    if found:
      results.append( dict(name=dashboard.name) )

  return json_response( dict(dashboards=results) )


def help(request):
  context = {}
  return render_to_response("dashboardHelp.html", context)

def email(request):
    sender = request.POST['sender']
    recipients = request.POST['recipients'].split()
    subject = request.POST['subject']
    message = request.POST['message']

    # these need to be passed to the render function in an HTTP request.
    graph_params = json.loads(request.POST['graph_params'], parse_int=str)
    target = QueryDict(graph_params.pop('target'))
    graph_params = QueryDict(urlencode(graph_params))

    new_post = request.POST.copy()
    new_post.update(graph_params)
    new_post.update(target)
    request.POST = new_post

    resp = renderView(request)
    img = resp.content

    if img:
        attachments = [('graph.png', img, 'image/png')]
        send_graph_email(subject, sender, recipients, attachments, message)

    return json_response(dict(success=True))


def create_temporary(request):
  state = str( json.dumps( json.loads( request.POST['state'] ) ) )
  i = 0
  while True:
    name = "temporary-%d" % i
    try:
      Dashboard.objects.get(name=name)
    except Dashboard.DoesNotExist:
      dashboard = Dashboard.objects.create(name=name, state=state)
      break
    else:
      i += 1

  return json_response( dict(name=dashboard.name) )


def json_response(obj):
  return HttpResponse(mimetype='application/json', content=json.dumps(obj))

########NEW FILE########
__FILENAME__ = models
import time
import os

from django.db import models
from django.contrib import admin

if os.environ.get('READTHEDOCS'):
    TagField = lambda *args, **kwargs: None
else:
    from tagging.fields import TagField

class Event(models.Model):
    class Admin: pass

    when = models.DateTimeField()
    what = models.CharField(max_length=255)
    data = models.TextField(blank=True)
    tags = TagField(default="")

    def get_tags(self):
        return Tag.objects.get_for_object(self)

    def __str__(self):
        return "%s: %s" % (self.when, self.what)

    @staticmethod
    def find_events(time_from=None, time_until=None, tags=None):
        query = Event.objects.all()

        if time_from is not None:
            query = query.filter(when__gte=time_from)

        if time_until is not None:
            query = query.filter(when__lte=time_until)

        if tags is not None:
            for tag in tags:
                query = query.filter(tags__iregex=r'\b%s\b' % tag)

        result = list(query.order_by("when"))
        return result

    def as_dict(self):
        return dict(
            when=self.when,
            what=self.what,
            data=self.data,
            tags=self.tags,
            id=self.id,
        )

admin.site.register(Event)

########NEW FILE########
__FILENAME__ = urls
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License."""

from django.conf.urls.defaults import *

urlpatterns = patterns('graphite.events.views',
  ('^get_data?$', 'get_data'),
  (r'(?P<event_id>\d+)/$', 'detail'),
  ('^$', 'view_events'),
)

########NEW FILE########
__FILENAME__ = views
import datetime
import time

import simplejson

from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404

from graphite.events import models
from graphite.render.attime import parseATTime
from django.core.urlresolvers import get_script_prefix



def to_timestamp(dt):
    return time.mktime(dt.timetuple())


class EventEncoder(simplejson.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return to_timestamp(obj)
        return simplejson.JSONEncoder.default(self, obj)


def view_events(request):
    if request.method == "GET":
        context = { 'events' : fetch(request),
            'slash' : get_script_prefix()
        }
        return render_to_response("events.html", context)
    else:
        return post_event(request)

def detail(request, event_id):
    e = get_object_or_404(models.Event, pk=event_id)
    context = { 'event' : e,
       'slash' : get_script_prefix()
    }
    return render_to_response("event.html", context)


def post_event(request):
    if request.method == 'POST':
        event = simplejson.loads(request.raw_post_data)
        assert isinstance(event, dict)

        values = {}
        values["what"] = event["what"]
        values["tags"] = event.get("tags", None)
        values["when"] = datetime.datetime.fromtimestamp(
            event.get("when", time.time()))
        if "data" in event:
            values["data"] = event["data"]

        e = models.Event(**values)
        e.save()

        return HttpResponse(status=200)
    else:
        return HttpResponse(status=405)

def get_data(request):
    return HttpResponse(simplejson.dumps(fetch(request), cls=EventEncoder),
                        mimetype="application/json")

def fetch(request):
    if request.GET.get("from", None) is not None:
        time_from = parseATTime(request.GET["from"])
    else:
        time_from = datetime.datetime.fromtimestamp(0)

    if request.GET.get("until", None) is not None:
        time_until = parseATTime(request.GET["until"])
    else:
        time_until = datetime.datetime.now()

    tags = request.GET.get("tags", None)
    if tags is not None:
        tags = request.GET.get("tags").split(" ")

    return [x.as_dict() for x in
            models.Event.find_events(time_from, time_until, tags=tags)]

########NEW FILE########
__FILENAME__ = urls
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License."""

from django.conf.urls.defaults import *

urlpatterns = patterns('graphite.graphlot.views',
  ('^rawdata/?$', 'get_data'),
  ('^findmetric/?$', 'find_metric'),
  ('', 'graphlot_render'),
)

########NEW FILE########
__FILENAME__ = views
import re

from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.conf import settings
import simplejson

from graphite.render.views import parseOptions
from graphite.render.evaluator import evaluateTarget
from graphite.storage import STORE
from django.core.urlresolvers import get_script_prefix



def graphlot_render(request):
    """Render the main graphlot view."""
    metrics = []
    for target in request.GET.getlist('target'):
        metrics.append(dict(name=target, yaxis="one"))
    for target in request.GET.getlist('y2target'):
        metrics.append(dict(name=target, yaxis="two"))

    untiltime = request.GET.get('until', "-0hour")
    fromtime = request.GET.get('from', "-24hour")
    events = request.GET.get('events', "")
    context = {
      'metric_list' : metrics,
      'fromtime' : fromtime,
      'untiltime' : untiltime,
      'events' : events,
      'slash' : get_script_prefix()
    }
    return render_to_response("graphlot.html", context)

def get_data(request):
    """Get the data for one series."""
    (graphOptions, requestOptions) = parseOptions(request)
    requestContext = {
        'startTime' : requestOptions['startTime'],
        'endTime' : requestOptions['endTime'],
        'localOnly' : False,
        'data' : []
    }
    target = requestOptions['targets'][0]
    seriesList = evaluateTarget(requestContext, target)
    result = [ dict(
            name=timeseries.name,
            data=[ x for x in timeseries ],
            start=timeseries.start,
            end=timeseries.end,
            step=timeseries.step,
            ) for timeseries in seriesList ]
    if not result:
        raise Http404
    return HttpResponse(simplejson.dumps(result), mimetype="application/json")


def find_metric(request):
    """Autocomplete helper on metric names."""
    try:
        query = str( request.REQUEST['q'] )
    except:
        return HttpResponseBadRequest(
            content="Missing required parameter 'q'", mimetype="text/plain")

    matches = list( STORE.find(query+"*") )
    content = "\n".join([node.metric_path for node in matches ])
    response = HttpResponse(content, mimetype='text/plain')

    return response

def header(request):
  "View for the header frame of the browser UI"
  context = {
    'user' : request.user,
    'profile' : getProfile(request),
    'documentation_url' : settings.DOCUMENTATION_URL,
    'slash' : get_script_prefix()
  }
  return render_to_response("browserHeader.html", context)


def browser(request):
  "View for the top-level frame of the browser UI"
  context = {
    'queryString' : request.GET.urlencode(),
    'target' : request.GET.get('target'),
    'slash' : get_script_prefix()
  }
  if context['queryString']:
    context['queryString'] = context['queryString'].replace('#','%23')
  if context['target']:
    context['target'] = context['target'].replace('#','%23') #js libs terminate a querystring on #
  return render_to_response("browser.html", context)


def search(request):
  query = request.POST['query']
  if not query:
    return HttpResponse("")

  patterns = query.split()
  regexes = [re.compile(p,re.I) for p in patterns]
  def matches(s):
    for regex in regexes:
      if regex.search(s):
        return True
    return False

  results = []

  index_file = open(settings.INDEX_FILE)
  for line in index_file:
    if matches(line):
      results.append( line.strip() )
    if len(results) >= 100:
      break

  index_file.close()
  result_string = ','.join(results)
  return HttpResponse(result_string, mimetype='text/plain')


def myGraphLookup(request):
  "View for My Graphs navigation"
  profile = getProfile(request,allowDefault=False)
  assert profile

  nodes = []
  leafNode = {
    'allowChildren' : 0,
    'expandable' : 0,
    'leaf' : 1,
  }
  branchNode = {
    'allowChildren' : 1,
    'expandable' : 1,
    'leaf' : 0,
  }

  try:
    path = str( request.GET['path'] )

    if path:
      if path.endswith('.'):
        userpath_prefix = path

      else:
        userpath_prefix = path + '.'

    else:
      userpath_prefix = ""

    matches = [ graph for graph in profile.mygraph_set.all().order_by('name') if graph.name.startswith(userpath_prefix) ]

    log.info( "myGraphLookup: username=%s, path=%s, userpath_prefix=%s, %ld graph to process" % (profile.user.username, path, userpath_prefix, len(matches)) )
    branch_inserted = set()
    leaf_inserted = set()

    for graph in matches: #Now let's add the matching graph
      isBranch = False
      dotPos = graph.name.find( '.', len(userpath_prefix) )

      if dotPos >= 0:
        isBranch = True
        name = graph.name[ len(userpath_prefix) : dotPos ]
        if name in branch_inserted: continue
        branch_inserted.add(name)

      else:
         name = graph.name[ len(userpath_prefix): ]
         if name in leaf_inserted: continue
         leaf_inserted.add(name)

      node = {'text' : str(name) }

      if isBranch:
        node.update( { 'id' : str(userpath_prefix + name + '.') } )
        node.update(branchNode)

      else:
        node.update( { 'id' : str(userpath_prefix + name), 'graphUrl' : str(graph.url) } )
        node.update(leafNode)

      nodes.append(node)

  except:
    log.exception("browser.views.myGraphLookup(): could not complete request.")

  if not nodes:
    no_graphs = { 'text' : "No saved graphs", 'id' : 'no-click' }
    no_graphs.update(leafNode)
    nodes.append(no_graphs)

  return json_response(nodes, request)

def userGraphLookup(request):
  "View for User Graphs navigation"
  username = request.GET['path']
  nodes = []

  branchNode = {
    'allowChildren' : 1,
    'expandable' : 1,
    'leaf' : 0,
  }
  leafNode = {
    'allowChildren' : 0,
    'expandable' : 0,
    'leaf' : 1,
  }

  try:

    if not username:
      profiles = Profile.objects.exclude(user=defaultUser)

      for profile in profiles:
        if profile.mygraph_set.count():
          node = {
            'text' : str(profile.user.username),
            'id' : str(profile.user.username)
          }

          node.update(branchNode)
          nodes.append(node)

    else:
      profile = getProfileByUsername(username)
      assert profile, "No profile for username '%s'" % username

      for graph in profile.mygraph_set.all().order_by('name'):
        node = {
          'text' : str(graph.name),
          'id' : str(graph.name),
          'graphUrl' : str(graph.url)
        }
        node.update(leafNode)
        nodes.append(node)

  except:
    log.exception("browser.views.userLookup(): could not complete request for %s" % username)

  if not nodes:
    no_graphs = { 'text' : "No saved graphs", 'id' : 'no-click' }
    no_graphs.update(leafNode)
    nodes.append(no_graphs)

  return json_response(nodes, request)


def json_response(nodes, request=None):
  if request:
    jsonp = request.REQUEST.get('jsonp', False)
  else:
    jsonp = False
  json_data = json.dumps(nodes)
  if jsonp:
    response = HttpResponse("%s(%s)" % (jsonp, json_data),mimetype="text/javascript")
  else:
    response = HttpResponse(json_data,mimetype="application/json")
  response['Pragma'] = 'no-cache'
  response['Cache-Control'] = 'no-cache'
  return response


def any(iterable): #python2.4 compatibility
  for i in iterable:
    if i:
      return True
  return False

########NEW FILE########
__FILENAME__ = logger
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import os, logging
from logging.handlers import TimedRotatingFileHandler as Rotater
from django.conf import settings

logging.addLevelName(30,"rendering")
logging.addLevelName(30,"cache")
logging.addLevelName(30,"metric_access")

class GraphiteLogger:
  def __init__(self):
    #Setup log files
    self.infoLogFile = os.path.join(settings.LOG_DIR,"info.log")
    self.exceptionLogFile = os.path.join(settings.LOG_DIR,"exception.log")
    self.cacheLogFile = os.path.join(settings.LOG_DIR,"cache.log")
    self.renderingLogFile = os.path.join(settings.LOG_DIR,"rendering.log")
    self.metricAccessLogFile = os.path.join(settings.LOG_DIR,"metricaccess.log")
    #Setup loggers
    self.infoLogger = logging.getLogger("info")
    self.infoLogger.setLevel(logging.INFO)
    self.exceptionLogger = logging.getLogger("exception")
    self.cacheLogger = logging.getLogger("cache")
    self.renderingLogger = logging.getLogger("rendering")
    self.metricAccessLogger = logging.getLogger("metric_access")
    #Setup formatter & handlers
    self.formatter = logging.Formatter("%(asctime)s :: %(message)s","%a %b %d %H:%M:%S %Y")
    self.infoHandler = Rotater(self.infoLogFile,when="midnight",backupCount=1)
    self.infoHandler.setFormatter(self.formatter)
    self.infoLogger.addHandler(self.infoHandler)
    self.exceptionHandler = Rotater(self.exceptionLogFile,when="midnight",backupCount=1)
    self.exceptionHandler.setFormatter(self.formatter)
    self.exceptionLogger.addHandler(self.exceptionHandler)
    if settings.LOG_CACHE_PERFORMANCE:
      self.cacheHandler = Rotater(self.cacheLogFile,when="midnight",backupCount=1)
      self.cacheHandler.setFormatter(self.formatter)
      self.cacheLogger.addHandler(self.cacheHandler)
    if settings.LOG_RENDERING_PERFORMANCE:
      self.renderingHandler = Rotater(self.renderingLogFile,when="midnight",backupCount=1)
      self.renderingHandler.setFormatter(self.formatter)
      self.renderingLogger.addHandler(self.renderingHandler)
    if settings.LOG_METRIC_ACCESS:
      self.metricAccessHandler = Rotater(self.metricAccessLogFile,when="midnight",backupCount=10)
      self.metricAccessHandler.setFormatter(self.formatter)
      self.metricAccessLogger.addHandler(self.metricAccessHandler)

  def info(self,msg,*args,**kwargs):
    return self.infoLogger.info(msg,*args,**kwargs)

  def exception(self,msg="Exception Caught",**kwargs):
    return self.exceptionLogger.exception(msg,**kwargs)

  def cache(self,msg,*args,**kwargs):
    return self.cacheLogger.log(30,msg,*args,**kwargs)

  def rendering(self,msg,*args,**kwargs):
    return self.renderingLogger.log(30,msg,*args,**kwargs)

  def metric_access(self,msg,*args,**kwargs):
    return self.metricAccessLogger.log(30,msg,*args,**kwargs)


log = GraphiteLogger() # import-shared logger instance

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = search
import time
import subprocess
import os.path
from django.conf import settings
from graphite.logger import log
from graphite.storage import is_pattern, match_entries


class IndexSearcher:
  def __init__(self, index_path):
    self.index_path = index_path
    if not os.path.exists(index_path):
      open(index_path, 'w').close() # touch the file to prevent re-entry down this code path
      build_index_path = os.path.join(settings.GRAPHITE_ROOT, "bin/build-index.sh")
      retcode = subprocess.call(build_index_path)
      if retcode != 0:
        log.exception("Couldn't build index file %s" % index_path)
        raise RuntimeError("Couldn't build index file %s" % index_path)
    self.last_mtime = 0
    self._tree = (None, {}) # (data, children)
    log.info("[IndexSearcher] performing initial index load")
    self.reload()

  @property
  def tree(self):
    current_mtime = os.path.getmtime(self.index_path)
    if current_mtime > self.last_mtime:
      log.info("[IndexSearcher] reloading stale index, current_mtime=%s last_mtime=%s" %
               (current_mtime, self.last_mtime))
      self.reload()

    return self._tree

  def reload(self):
    log.info("[IndexSearcher] reading index data from %s" % self.index_path)
    t = time.time()
    total_entries = 0
    tree = (None, {}) # (data, children)
    for line in open(self.index_path):
      line = line.strip()
      if not line:
        continue

      branches = line.split('.')
      leaf = branches.pop()
      parent = None
      cursor = tree
      for branch in branches:
        if branch not in cursor[1]:
          cursor[1][branch] = (None, {}) # (data, children)
        parent = cursor
        cursor = cursor[1][branch]

      cursor[1][leaf] = (line, {})
      total_entries += 1

    self._tree = tree
    self.last_mtime = os.path.getmtime(self.index_path)
    log.info("[IndexSearcher] index reload took %.6f seconds (%d entries)" % (time.time() - t, total_entries))

  def search(self, query, max_results=None, keep_query_pattern=False):
    query_parts = query.split('.')
    metrics_found = set()
    for result in self.subtree_query(self.tree, query_parts):
      # Overlay the query pattern on the resulting paths
      if keep_query_pattern:
        path_parts = result['path'].split('.')
        result['path'] = '.'.join(query_parts) + result['path'][len(query_parts):]

      if result['path'] in metrics_found:
        continue
      yield result

      metrics_found.add(result['path'])
      if max_results is not None and len(metrics_found) >= max_results:
        return

  def subtree_query(self, root, query_parts):
    if query_parts:
      my_query = query_parts[0]
      if is_pattern(my_query):
        matches = [root[1][node] for node in match_entries(root[1], my_query)]
      elif my_query in root[1]:
        matches = [ root[1][my_query] ]
      else:
        matches = []

    else:
      matches = root[1].values()

    for child_node in matches:
      result = {
        'path' : child_node[0],
        'is_leaf' : bool(child_node[0]),
      }
      if result['path'] is not None and not result['is_leaf']:
        result['path'] += '.'
      yield result

      if query_parts:
        for result in self.subtree_query(child_node, query_parts[1:]):
          yield result


class SearchIndexCorrupt(StandardError):
  pass


searcher = IndexSearcher(settings.INDEX_FILE)

########NEW FILE########
__FILENAME__ = urls
"""Copyright 2009 Chris Davis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License."""

from django.conf.urls.defaults import *

urlpatterns = patterns('graphite.metrics.views',
  ('^index\.json$', 'index_json'),
  ('^search/?$', 'search_view'),
  ('^find/?$', 'find_view'),
  ('^expand/?$', 'expand_view'),
  ('^context/?$', 'context_view'),
  ('^get-metadata/?$', 'get_metadata_view'),
  ('^set-metadata/?$', 'set_metadata_view'),
  ('', 'find_view'),
)

########NEW FILE########
__FILENAME__ = views
"""Copyright 2009 Chris Davis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import traceback
from django.http import HttpResponse, HttpResponseBadRequest
from django.conf import settings
from graphite.account.models import Profile
from graphite.util import getProfile, getProfileByUsername, defaultUser, json
from graphite.logger import log
from graphite.storage import STORE, LOCAL_STORE
from graphite.metrics.search import searcher
from graphite.render.datalib import CarbonLink
import fnmatch, os

try:
  import cPickle as pickle
except ImportError:
  import pickle


def index_json(request):
  jsonp = request.REQUEST.get('jsonp', False)
  matches = []

  for root, dirs, files in os.walk(settings.WHISPER_DIR):
    root = root.replace(settings.WHISPER_DIR, '')
    for basename in files:
      if fnmatch.fnmatch(basename, '*.wsp'):
        matches.append(os.path.join(root, basename))

  matches = [ m.replace('.wsp','').replace('/', '.') for m in sorted(matches) ]
  if jsonp:
    return HttpResponse("%s(%s)" % (jsonp, json.dumps(matches)), mimetype='text/javascript')
  else:
    return HttpResponse(json.dumps(matches), mimetype='application/json')


def search_view(request):
  query = str(request.REQUEST['query'].strip())
  search_request = {
    'query' : query,
    'max_results' : int( request.REQUEST.get('max_results', 25) ),
    'keep_query_pattern' : int(request.REQUEST.get('keep_query_pattern', 0)),
  }
  #if not search_request['query'].endswith('*'):
  #  search_request['query'] += '*'

  results = sorted(searcher.search(**search_request))
  result_data = json.dumps( dict(metrics=results) )
  return HttpResponse(result_data, mimetype='application/json')


def context_view(request):
  if request.method == 'GET':
    contexts = []

    if not 'metric' not in request.GET:
      return HttpResponse('{ "error" : "missing required parameter \"metric\"" }', mimetype='application/json')

    for metric in request.GET.getlist('metric'):
      try:
        context = STORE.get(metric).context
      except:
        contexts.append({ 'metric' : metric, 'error' : 'failed to retrieve context', 'traceback' : traceback.format_exc() })
      else:
        contexts.append({ 'metric' : metric, 'context' : context })

    content = json.dumps( { 'contexts' : contexts } )
    return HttpResponse(content, mimetype='application/json')

  elif request.method == 'POST':

    if 'metric' not in request.POST:
      return HttpResponse('{ "error" : "missing required parameter \"metric\"" }', mimetype='application/json')

    newContext = dict( item for item in request.POST.items() if item[0] != 'metric' )

    for metric in request.POST.getlist('metric'):
      STORE.get(metric).updateContext(newContext)

    return HttpResponse('{ "success" : true }', mimetype='application/json')

  else:
    return HttpResponseBadRequest("invalid method, must be GET or POST")


def find_view(request):
  "View for finding metrics matching a given pattern"
  profile = getProfile(request)
  format = request.REQUEST.get('format', 'treejson')
  local_only = int( request.REQUEST.get('local', 0) )
  contexts = int( request.REQUEST.get('contexts', 0) )
  wildcards = int( request.REQUEST.get('wildcards', 0) )
  automatic_variants = int( request.REQUEST.get('automatic_variants', 0) )

  try:
    query = str( request.REQUEST['query'] )
  except:
    return HttpResponseBadRequest(content="Missing required parameter 'query'", mimetype="text/plain")

  if '.' in query:
    base_path = query.rsplit('.', 1)[0] + '.'
  else:
    base_path = ''

  if local_only:
    store = LOCAL_STORE
  else:
    store = STORE

  if format == 'completer':
    query = query.replace('..', '*.')
    if not query.endswith('*'):
      query += '*'

    if automatic_variants:
      query_parts = query.split('.')
      for i,part in enumerate(query_parts):
        if ',' in part and '{' not in part:
          query_parts[i] = '{%s}' % part
      query = '.'.join(query_parts)

  try:
    matches = list( store.find(query) )
  except:
    log.exception()
    raise

  log.info('find_view query=%s local_only=%s matches=%d' % (query, local_only, len(matches)))
  matches.sort(key=lambda node: node.name)

  if format == 'treejson':
    content = tree_json(matches, base_path, wildcards=profile.advancedUI or wildcards, contexts=contexts)
    response = HttpResponse(content, mimetype='application/json')

  elif format == 'pickle':
    content = pickle_nodes(matches, contexts=contexts)
    response = HttpResponse(content, mimetype='application/pickle')

  elif format == 'completer':
    #if len(matches) == 1 and (not matches[0].isLeaf()) and query == matches[0].metric_path + '*': # auto-complete children
    #  matches = list( store.find(query + '.*') )
    results = []
    for node in matches:
      node_info = dict(path=node.metric_path, name=node.name, is_leaf=str(int(node.isLeaf())))
      if not node.isLeaf():
        node_info['path'] += '.'
      results.append(node_info)

    if len(results) > 1 and wildcards:
      wildcardNode = {'name' : '*'}
      results.append(wildcardNode)

    content = json.dumps({ 'metrics' : results })
    response = HttpResponse(content, mimetype='application/json')

  else:
    return HttpResponseBadRequest(content="Invalid value for 'format' parameter", mimetype="text/plain")

  response['Pragma'] = 'no-cache'
  response['Cache-Control'] = 'no-cache'
  return response


def expand_view(request):
  "View for expanding a pattern into matching metric paths"
  local_only    = int( request.REQUEST.get('local', 0) )
  group_by_expr = int( request.REQUEST.get('groupByExpr', 0) )
  leaves_only   = int( request.REQUEST.get('leavesOnly', 0) )

  if local_only:
    store = LOCAL_STORE
  else:
    store = STORE

  results = {}
  for query in request.REQUEST.getlist('query'):
    results[query] = set()
    for node in store.find(query):
      if node.isLeaf() or not leaves_only:
        results[query].add( node.metric_path )

  # Convert our results to sorted lists because sets aren't json-friendly
  if group_by_expr:
    for query, matches in results.items():
      results[query] = sorted(matches)
  else:
    results = sorted( reduce(set.union, results.values(), set()) )

  result = {
    'results' : results
  }

  response = HttpResponse(json.dumps(result), mimetype='application/json')
  response['Pragma'] = 'no-cache'
  response['Cache-Control'] = 'no-cache'
  return response


def get_metadata_view(request):
  key = request.REQUEST['key']
  metrics = request.REQUEST.getlist('metric')
  results = {}
  for metric in metrics:
    try:
      results[metric] = CarbonLink.get_metadata(metric, key)
    except:
      log.exception()
      results[metric] = dict(error="Unexpected error occurred in CarbonLink.get_metadata(%s, %s)" % (metric, key))

  return HttpResponse(json.dumps(results), mimetype='application/json')


def set_metadata_view(request):
  results = {}

  if request.method == 'GET':
    metric = request.GET['metric']
    key = request.GET['key']
    value = request.GET['value']
    try:
      results[metric] = CarbonLink.set_metadata(metric, key, value)
    except:
      log.exception()
      results[metric] = dict(error="Unexpected error occurred in CarbonLink.set_metadata(%s, %s)" % (metric, key))

  elif request.method == 'POST':
    if request.META.get('CONTENT_TYPE') == 'application/json':
      operations = json.loads( request.raw_post_data )
    else:
      operations = json.loads( request.POST['operations'] )

    for op in operations:
      metric = None
      try:
        metric, key, value = op['metric'], op['key'], op['value']
        results[metric] = CarbonLink.set_metadata(metric, key, value)
      except:
        log.exception()
        if metric:
          results[metric] = dict(error="Unexpected error occurred in bulk CarbonLink.set_metadata(%s)" % metric)

  else:
    results = dict(error="Invalid request method")

  return HttpResponse(json.dumps(results), mimetype='application/json')


def tree_json(nodes, base_path, wildcards=False, contexts=False):
  results = []

  branchNode = {
    'allowChildren': 1,
    'expandable': 1,
    'leaf': 0,
  }
  leafNode = {
    'allowChildren': 0,
    'expandable': 0,
    'leaf': 1,
  }

  #Add a wildcard node if appropriate
  if len(nodes) > 1 and wildcards:
    wildcardNode = {'text' : '*', 'id' : base_path + '*'}

    if any(not n.isLeaf() for n in nodes):
      wildcardNode.update(branchNode)

    else:
      wildcardNode.update(leafNode)

    results.append(wildcardNode)

  found = set()
  results_leaf = []
  results_branch = []
  for node in nodes: #Now let's add the matching children
    if node.name in found:
      continue

    found.add(node.name)
    resultNode = {
      'text' : str(node.name),
      'id' : base_path + str(node.name),
    }

    if contexts:
      resultNode['context'] = node.context
    else:
      resultNode['context'] = {}

    if node.isLeaf():
      resultNode.update(leafNode)
      results_leaf.append(resultNode)
    else:
      resultNode.update(branchNode)
      results_branch.append(resultNode)

  results.extend(results_branch)
  results.extend(results_leaf)
  return json.dumps(results)


def pickle_nodes(nodes, contexts=False):
  if contexts:
    return pickle.dumps([ { 'metric_path' : n.metric_path, 'isLeaf' : n.isLeaf(), 'intervals' : n.getIntervals(), 'context' : n.context } for n in nodes ])

  else:
    return pickle.dumps([ { 'metric_path' : n.metric_path, 'isLeaf' : n.isLeaf(), 'intervals' : n.getIntervals()} for n in nodes ])


def any(iterable): #python2.4 compatibility
  for i in iterable:
    if i:
      return True
  return False

########NEW FILE########
__FILENAME__ = remote_storage
import socket
import time
import httplib
from urllib import urlencode
from django.core.cache import cache
from django.conf import settings
from graphite.render.hashing import compactHash

try:
  import cPickle as pickle
except ImportError:
  import pickle



class RemoteStore(object):
  lastFailure = 0.0
  retryDelay = settings.REMOTE_STORE_RETRY_DELAY
  available = property(lambda self: time.time() - self.lastFailure > self.retryDelay)

  def __init__(self, host):
    self.host = host


  def find(self, query):
    request = FindRequest(self, query)
    request.send()
    return request


  def fail(self):
    self.lastFailure = time.time()



class FindRequest:
  suppressErrors = True

  def __init__(self, store, query):
    self.store = store
    self.query = query
    self.connection = None
    self.cacheKey = compactHash('find:%s:%s' % (self.store.host, query))
    self.cachedResults = None


  def send(self):
    self.cachedResults = cache.get(self.cacheKey)

    if self.cachedResults:
      return

    self.connection = HTTPConnectionWithTimeout(self.store.host)
    self.connection.timeout = settings.REMOTE_STORE_FIND_TIMEOUT

    query_params = [
      ('local', '1'),
      ('format', 'pickle'),
      ('query', self.query),
    ]
    query_string = urlencode(query_params)

    try:
      self.connection.request('GET', '/metrics/find/?' + query_string)
    except:
      self.store.fail()
      if not self.suppressErrors:
        raise


  def get_results(self):
    if self.cachedResults:
      return self.cachedResults

    if not self.connection:
      self.send()

    try:
      response = self.connection.getresponse()
      assert response.status == 200, "received error response %s - %s" % (response.status, response.reason)
      result_data = response.read()
      results = pickle.loads(result_data)

    except:
      self.store.fail()
      if not self.suppressErrors:
        raise
      else:
        results = []

    resultNodes = [ RemoteNode(self.store, node['metric_path'], node['isLeaf']) for node in results ]
    cache.set(self.cacheKey, resultNodes, settings.REMOTE_FIND_CACHE_DURATION)
    self.cachedResults = resultNodes
    return resultNodes



class RemoteNode:
  context = {}

  def __init__(self, store, metric_path, isLeaf):
    self.store = store
    self.fs_path = None
    self.metric_path = metric_path
    self.real_metric = metric_path
    self.name = metric_path.split('.')[-1]
    self.__isLeaf = isLeaf


  def fetch(self, startTime, endTime):
    if not self.__isLeaf:
      return []

    query_params = [
      ('target', self.metric_path),
      ('pickle', 'true'),
      ('from', str( int(startTime) )),
      ('until', str( int(endTime) ))
    ]
    query_string = urlencode(query_params)

    connection = HTTPConnectionWithTimeout(self.store.host)
    connection.timeout = settings.REMOTE_STORE_FETCH_TIMEOUT
    connection.request('GET', '/render/?' + query_string)
    response = connection.getresponse()
    assert response.status == 200, "Failed to retrieve remote data: %d %s" % (response.status, response.reason)
    rawData = response.read()

    seriesList = pickle.loads(rawData)
    assert len(seriesList) == 1, "Invalid result: seriesList=%s" % str(seriesList)
    series = seriesList[0]

    timeInfo = (series['start'], series['end'], series['step'])
    return (timeInfo, series['values'])


  def isLeaf(self):
    return self.__isLeaf



# This is a hack to put a timeout in the connect() of an HTTP request.
# Python 2.6 supports this already, but many Graphite installations
# are not on 2.6 yet.

class HTTPConnectionWithTimeout(httplib.HTTPConnection):
  timeout = 30

  def connect(self):
    msg = "getaddrinfo returns an empty list"
    for res in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):
      af, socktype, proto, canonname, sa = res
      try:
        self.sock = socket.socket(af, socktype, proto)
        try:
          self.sock.settimeout( float(self.timeout) ) # default self.timeout is an object() in 2.6
        except:
          pass
        self.sock.connect(sa)
        self.sock.settimeout(None)
      except socket.error, msg:
        if self.sock:
          self.sock.close()
          self.sock = None
          continue
      break
    if not self.sock:
      raise socket.error, msg

########NEW FILE########
__FILENAME__ = attime
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from datetime import datetime,timedelta
from time import daylight
from django.conf import settings

try: # See if there is a system installation of pytz first
  import pytz
except ImportError: # Otherwise we fall back to Graphite's bundled version
  from graphite.thirdparty import pytz


months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
weekdays = ['sun','mon','tue','wed','thu','fri','sat']

tzinfo = pytz.timezone(settings.TIME_ZONE)

def parseATTime(s):
  s = s.strip().lower().replace('_','').replace(',','').replace(' ','')
  if s.isdigit():
    if len(s) == 8 and int(s[:4]) > 1900 and int(s[4:6]) < 13 and int(s[6:]) < 32:
      pass #Fall back because its not a timestamp, its YYYYMMDD form
    else:
      return datetime.fromtimestamp(int(s),tzinfo)
  if '+' in s:
    ref,offset = s.split('+',1)
    offset = '+' + offset
  elif '-' in s:
    ref,offset = s.split('-',1)
    offset = '-' + offset
  else:
    ref,offset = s,''
  return tzinfo.localize(parseTimeReference(ref), daylight) + parseTimeOffset(offset)


def parseTimeReference(ref):
  if not ref or ref == 'now': return datetime.now()

  #Time-of-day reference
  i = ref.find(':')
  hour,min = 0,0
  if i != -1:
    hour = int( ref[:i] )
    min = int( ref[i+1:i+3] )
    ref = ref[i+3:]
    if ref[:2] == 'am': ref = ref[2:]
    elif ref[:2] == 'pm':
      hour = (hour + 12) % 24
      ref = ref[2:]
  if ref.startswith('noon'):
    hour,min = 12,0
    ref = ref[4:]
  elif ref.startswith('midnight'):
    hour,min = 0,0
    ref = ref[8:]
  elif ref.startswith('teatime'):
    hour,min = 16,0
    ref = ref[7:]

  refDate = datetime.now().replace(hour=hour,minute=min,second=0)

  #Day reference
  if ref in ('yesterday','today','tomorrow'): #yesterday, today, tomorrow
    if ref == 'yesterday':
      refDate = refDate - timedelta(days=1)
    if ref == 'tomorrow':
      refDate = refDate + timedelta(days=1)
  elif ref.count('/') == 2: #MM/DD/YY[YY]
    m,d,y = map(int,ref.split('/'))
    if y < 1900: y += 1900
    if y < 1970: y += 100
    refDate = refDate.replace(year=y)

    try: # Fix for Bug #551771
      refDate = refDate.replace(month=m)
      refDate = refDate.replace(day=d)
    except:
      refDate = refDate.replace(day=d)
      refDate = refDate.replace(month=m)

  elif len(ref) == 8 and ref.isdigit(): #YYYYMMDD
    refDate = refDate.replace(year= int(ref[:4]))

    try: # Fix for Bug #551771
      refDate = refDate.replace(month= int(ref[4:6]))
      refDate = refDate.replace(day= int(ref[6:8]))
    except:
      refDate = refDate.replace(day= int(ref[6:8]))
      refDate = refDate.replace(month= int(ref[4:6]))

  elif ref[:3] in months: #MonthName DayOfMonth
    refDate = refDate.replace(month= months.index(ref[:3]) + 1)
    if ref[-2:].isdigit():
      refDate = refDate.replace(day= int(ref[-2:]))
    elif ref[-1:].isdigit():
      refDate = refDate.replace(day= int(ref[-1:]))
    else:
      raise Exception, "Day of month required after month name"
  elif ref[:3] in weekdays: #DayOfWeek (Monday, etc)
    todayDayName = refDate.strftime("%a").lower()[:3]
    today = weekdays.index( todayDayName )
    twoWeeks = weekdays * 2
    dayOffset = today - twoWeeks.index(ref[:3])
    if dayOffset < 0: dayOffset += 7
    refDate -= timedelta(days=dayOffset)
  elif ref:
    raise Exception, "Unknown day reference"
  return refDate


def parseTimeOffset(offset):
  if not offset:
    return timedelta()

  t = timedelta()

  if offset[0].isdigit():
    sign = 1
  else:
    sign = { '+' : 1, '-' : -1 }[offset[0]]
    offset = offset[1:]

  while offset:
    i = 1
    while offset[:i].isdigit() and i <= len(offset): i += 1
    num = int(offset[:i-1])
    offset = offset[i-1:]
    i = 1
    while offset[:i].isalpha() and i <= len(offset): i += 1
    unit = offset[:i-1]
    offset = offset[i-1:]
    unitString = getUnitString(unit)
    if unitString == 'months':
      unitString = 'days'
      num = num * 30
    if unitString == 'years':
      unitString = 'days'
      num = num * 365
    t += timedelta(**{ unitString : sign * num})

  return t


def getUnitString(s):
  if s.startswith('s'): return 'seconds'
  if s.startswith('min'): return 'minutes'
  if s.startswith('h'): return 'hours'
  if s.startswith('d'): return 'days'
  if s.startswith('w'): return 'weeks'
  if s.startswith('mon'): return 'months'
  if s.startswith('y'): return 'years'
  raise Exception, "Invalid offset unit '%s'" % s

########NEW FILE########
__FILENAME__ = datalib
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import socket
import struct
import time
from django.conf import settings
from graphite.logger import log
from graphite.storage import STORE, LOCAL_STORE
from graphite.render.hashing import ConsistentHashRing

try:
  import cPickle as pickle
except ImportError:
  import pickle


class TimeSeries(list):
  def __init__(self, name, start, end, step, values, consolidate='average'):
    self.name = name
    self.start = start
    self.end = end
    self.step = step
    list.__init__(self,values)
    self.consolidationFunc = consolidate
    self.valuesPerPoint = 1
    self.options = {}


  def __iter__(self):
    if self.valuesPerPoint > 1:
      return self.__consolidatingGenerator( list.__iter__(self) )
    else:
      return list.__iter__(self)


  def consolidate(self, valuesPerPoint):
    self.valuesPerPoint = int(valuesPerPoint)


  def __consolidatingGenerator(self, gen):
    buf = []
    for x in gen:
      buf.append(x)
      if len(buf) == self.valuesPerPoint:
        while None in buf: buf.remove(None)
        if buf:
          yield self.__consolidate(buf)
          buf = []
        else:
          yield None
    while None in buf: buf.remove(None)
    if buf: yield self.__consolidate(buf)
    else: yield None
    raise StopIteration


  def __consolidate(self, values):
    usable = [v for v in values if v is not None]
    if not usable: return None
    if self.consolidationFunc == 'sum':
      return sum(usable)
    if self.consolidationFunc == 'average':
      return float(sum(usable)) / len(usable)
    raise Exception, "Invalid consolidation function!"


  def __repr__(self):
    return 'TimeSeries(name=%s, start=%s, end=%s, step=%s)' % (self.name, self.start, self.end, self.step)


  def getInfo(self):
    """Pickle-friendly representation of the series"""
    return {
      'name' : self.name,
      'start' : self.start,
      'end' : self.end,
      'step' : self.step,
      'values' : list(self),
    }



class CarbonLinkPool:
  def __init__(self, hosts, timeout):
    self.hosts = [ (server, instance) for (server, port, instance) in hosts ]
    self.ports = dict( ((server, instance), port) for (server, port, instance) in hosts )
    self.timeout = float(timeout)
    self.hash_ring = ConsistentHashRing(self.hosts)
    self.connections = {}
    self.last_failure = {}
    # Create a connection pool for each host
    for host in self.hosts:
      self.connections[host] = set()

  def select_host(self, metric):
    "Returns the carbon host that has data for the given metric"
    return self.hash_ring.get_node(metric)

  def get_connection(self, host):
    # First try to take one out of the pool for this host
    (server, instance) = host
    port = self.ports[host]
    connectionPool = self.connections[host]
    try:
      return connectionPool.pop()
    except KeyError:
      pass #nothing left in the pool, gotta make a new connection

    log.cache("CarbonLink creating a new socket for %s" % str(host))
    connection = socket.socket()
    connection.settimeout(self.timeout)
    try:
      connection.connect( (server, port) )
    except:
      self.last_failure[host] = time.time()
      raise
    else:
      connection.setsockopt( socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1 )
      return connection

  def query(self, metric):
    request = dict(type='cache-query', metric=metric)
    results = self.send_request(request)
    log.cache("CarbonLink cache-query request for %s returned %d datapoints" % (metric, len(results)))
    return results['datapoints']

  def get_metadata(self, metric, key):
    request = dict(type='get-metadata', metric=metric, key=key)
    results = self.send_request(request)
    log.cache("CarbonLink get-metadata request received for %s:%s" % (metric, key))
    return results['value']

  def set_metadata(self, metric, key, value):
    request = dict(type='set-metadata', metric=metric, key=key, value=value)
    results = self.send_request(request)
    log.cache("CarbonLink set-metadata request received for %s:%s" % (metric, key))
    return results

  def send_request(self, request):
    metric = request['metric']
    serialized_request = pickle.dumps(request, protocol=-1)
    len_prefix = struct.pack("!L", len(serialized_request))
    request_packet = len_prefix + serialized_request

    host = self.select_host(metric)
    conn = self.get_connection(host)
    try:
      conn.sendall(request_packet)
      result = self.recv_response(conn)
    except:
      self.last_failure[host] = time.time()
      raise
    else:
      self.connections[host].add(conn)
      if 'error' in result:
        raise CarbonLinkRequestError(result['error'])
      else:
        return result

  def recv_response(self, conn):
    len_prefix = recv_exactly(conn, 4)
    body_size = struct.unpack("!L", len_prefix)[0]
    body = recv_exactly(conn, body_size)
    return pickle.loads(body)


# Utilities
class CarbonLinkRequestError(Exception):
  pass

def recv_exactly(conn, num_bytes):
  buf = ''
  while len(buf) < num_bytes:
    data = conn.recv( num_bytes - len(buf) )
    if not data:
      raise Exception("Connection lost")
    buf += data

  return buf

#parse hosts from local_settings.py
hosts = []
for host in settings.CARBONLINK_HOSTS:
  parts = host.split(':')
  server = parts[0]
  port = int( parts[1] )
  if len(parts) > 2:
    instance = parts[2]
  else:
    instance = None

  hosts.append( (server, int(port), instance) )


#A shared importable singleton
CarbonLink = CarbonLinkPool(hosts, settings.CARBONLINK_TIMEOUT)


# Data retrieval API
def fetchData(requestContext, pathExpr):
  seriesList = []
  startTime = requestContext['startTime']
  endTime = requestContext['endTime']

  if requestContext['localOnly']:
    store = LOCAL_STORE
  else:
    store = STORE

  for dbFile in store.find(pathExpr):
    log.metric_access(dbFile.metric_path)
    dbResults = dbFile.fetch( timestamp(startTime), timestamp(endTime) )
    try:
      cachedResults = CarbonLink.query(dbFile.real_metric)
      results = mergeResults(dbResults, cachedResults)
    except:
      log.exception()
      results = dbResults

    if not results:
      continue

    (timeInfo,values) = results
    (start,end,step) = timeInfo
    series = TimeSeries(dbFile.metric_path, start, end, step, values)
    series.pathExpression = pathExpr #hack to pass expressions through to render functions
    seriesList.append(series)

  return seriesList


def mergeResults(dbResults, cacheResults):
  cacheResults = list(cacheResults)

  if not dbResults:
    return cacheResults
  elif not cacheResults:
    return dbResults

  (timeInfo,values) = dbResults
  (start,end,step) = timeInfo

  for (timestamp, value) in cacheResults:
    interval = timestamp - (timestamp % step)

    try:
      i = int(interval - start) / step
      values[i] = value
    except:
      pass

  return (timeInfo,values)


def timestamp(datetime):
  "Convert a datetime object into epoch time"
  return time.mktime( datetime.timetuple() )

########NEW FILE########
__FILENAME__ = evaluator
import datetime
import time
from django.conf import settings
from graphite.render.grammar import grammar
from graphite.render.datalib import fetchData, TimeSeries


def evaluateTarget(requestContext, target):
  tokens = grammar.parseString(target)
  result = evaluateTokens(requestContext, tokens)

  if type(result) is TimeSeries:
    return [result] #we have to return a list of TimeSeries objects

  else:
    return result


def evaluateTokens(requestContext, tokens):
  if tokens.expression:
    return evaluateTokens(requestContext, tokens.expression)

  elif tokens.pathExpression:
    return fetchData(requestContext, tokens.pathExpression)

  elif tokens.call:
    func = SeriesFunctions[tokens.call.func]
    args = [evaluateTokens(requestContext, arg) for arg in tokens.call.args]
    return func(requestContext, *args)

  elif tokens.number:
    if tokens.number.integer:
      return int(tokens.number.integer)

    elif tokens.number.float:
      return float(tokens.number.float)

  elif tokens.string:
    return str(tokens.string)[1:-1]

  elif tokens.boolean:
    return tokens.boolean[0] == 'true'


#Avoid import circularities
from graphite.render.functions import SeriesFunctions

########NEW FILE########
__FILENAME__ = functions
#Copyright 2008 Orbitz WorldWide
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.


from datetime import date, datetime, timedelta
from itertools import izip, imap
import math
import re
import random
import time

from graphite.logger import log
from graphite.render.datalib import fetchData, TimeSeries, timestamp
from graphite.render.attime import parseTimeOffset

from graphite.events import models
from graphite.render.glyph import format_units

NAN = float('NaN')
INF = float('inf')
DAY = 86400
HOUR = 3600
MINUTE = 60

#Utility functions
def safeSum(values):
  safeValues = [v for v in values if v is not None]
  if safeValues:
    return sum(safeValues)

def safeDiff(values):
  safeValues = [v for v in values if v is not None]
  if safeValues:
    values = map(lambda x: x*-1, safeValues[1:])
    values.insert(0, safeValues[0])
    return sum(values)

def safeLen(values):
  return len([v for v in values if v is not None])

def safeDiv(a,b):
  if a is None: return None
  if b in (0,None): return None
  return float(a) / float(b)

def safeMul(*factors):
  if None in factors:
    return None

  factors = map(float, factors)
  product = reduce(lambda x,y: x*y, factors)
  return product

def safeSubtract(a,b):
    if a is None or b is None: return None
    return float(a) - float(b)

def safeLast(values):
  for v in reversed(values):
    if v is not None: return v

def safeMin(values):
  safeValues = [v for v in values if v is not None]
  if safeValues:
    return min(safeValues)

def safeMax(values):
  safeValues = [v for v in values if v is not None]
  if safeValues:
    return max(safeValues)

def safeMap(function, values):
  safeValues = [v for v in values if v is not None]
  if safeValues:
    return map(function, values)

def lcm(a,b):
  if a == b: return a
  if a < b: (a,b) = (b,a) #ensure a > b
  for i in xrange(1,a * b):
    if a % (b * i) == 0 or (b * i) % a == 0: #probably inefficient
      return max(a,b * i)
  return a * b

def normalize(seriesLists):
  seriesList = reduce(lambda L1,L2: L1+L2,seriesLists)
  step = reduce(lcm,[s.step for s in seriesList])
  for s in seriesList:
    s.consolidate( step / s.step )
  start = min([s.start for s in seriesList])
  end = max([s.end for s in seriesList])
  end -= (end - start) % step
  return (seriesList,start,end,step)

# Series Functions

#NOTE: Some of the functions below use izip, which may be problematic.
#izip stops when it hits the end of the shortest series
#in practice this *shouldn't* matter because all series will cover
#the same interval, despite having possibly different steps...

def sumSeries(requestContext, *seriesLists):
  """
  Short form: sum()

  This will add metrics together and return the sum at each datapoint. (See
  integral for a sum over time)

  Example:

  .. code-block:: none

    &target=sum(company.server.application*.requestsHandled)

  This would show the sum of all requests handled per minute (provided
  requestsHandled are collected once a minute).   If metrics with different
  retention rates are combined, the coarsest metric is graphed, and the sum
  of the other metrics is averaged for the metrics with finer retention rates.

  """

  try:
    (seriesList,start,end,step) = normalize(seriesLists)
  except:
    return []
  #name = "sumSeries(%s)" % ','.join((s.name for s in seriesList))
  name = "sumSeries(%s)" % ','.join(set([s.pathExpression for s in seriesList]))
  values = ( safeSum(row) for row in izip(*seriesList) )
  series = TimeSeries(name,start,end,step,values)
  series.pathExpression = name
  return [series]

def sumSeriesWithWildcards(requestContext, seriesList, *position): #XXX
  """
  Call sumSeries after inserting wildcards at the given position(s).

  Example:

  .. code-block:: none

    &target=sumSeriesWithWildcards(host.cpu-[0-7].cpu-{user,system}.value, 1)

  This would be the equivalent of
  ``target=sumSeries(host.*.cpu-user.value)&target=sumSeries(host.*.cpu-system.value)``

  """
  if type(position) is int:
    positions = [position]
  else:
    positions = position

  newSeries = {}
  newNames = list()

  for series in seriesList:
    newname = '.'.join(map(lambda x: x[1], filter(lambda i: i[0] not in positions, enumerate(series.name.split('.')))))
    if newname in newSeries.keys():
      newSeries[newname] = sumSeries(requestContext, (series, newSeries[newname]))[0]
    else:
      newSeries[newname] = series
      newNames.append(newname)
    newSeries[newname].name = newname

  return [newSeries[name] for name in newNames]

def averageSeriesWithWildcards(requestContext, seriesList, *position): #XXX
  """
  Call averageSeries after inserting wildcards at the given position(s).

  Example:

  .. code-block:: none

    &target=averageSeriesWithWildcards(host.cpu-[0-7].cpu-{user,system}.value, 1)

  This would be the equivalent of
  ``target=averageSeries(host.*.cpu-user.value)&target=averageSeries(host.*.cpu-system.value)``

  """
  if type(position) is int:
    positions = [position]
  else:
    positions = position
  result = []
  matchedList = {}
  for series in seriesList:
    newname = '.'.join(map(lambda x: x[1], filter(lambda i: i[0] not in positions, enumerate(series.name.split('.')))))
    if not matchedList.has_key(newname):
      matchedList[newname] = []
    matchedList[newname].append(series)
  for name in matchedList.keys():
    result.append( averageSeries(requestContext, (matchedList[name]))[0] )
    result[-1].name = name
  return result

def diffSeries(requestContext, *seriesLists):
  """
  Can take two or more metrics, or a single metric and a constant.
  Subtracts parameters 2 through n from parameter 1.

  Example:

  .. code-block:: none

    &target=diffSeries(service.connections.total,service.connections.failed)
    &target=diffSeries(service.connections.total,5)

  """
  (seriesList,start,end,step) = normalize(seriesLists)
  name = "diffSeries(%s)" % ','.join(set([s.pathExpression for s in seriesList]))
  values = ( safeDiff(row) for row in izip(*seriesList) )
  series = TimeSeries(name,start,end,step,values)
  series.pathExpression = name
  return [series]

def averageSeries(requestContext, *seriesLists):
  """
  Short Alias: avg()

  Takes one metric or a wildcard seriesList.
  Draws the average value of all metrics passed at each time.

  Example:

  .. code-block:: none

    &target=averageSeries(company.server.*.threads.busy)

  """
  (seriesList,start,end,step) = normalize(seriesLists)
  #name = "averageSeries(%s)" % ','.join((s.name for s in seriesList))
  name = "averageSeries(%s)" % ','.join(set([s.pathExpression for s in seriesList]))
  values = ( safeDiv(safeSum(row),safeLen(row)) for row in izip(*seriesList) )
  series = TimeSeries(name,start,end,step,values)
  series.pathExpression = name
  return [series]

def minSeries(requestContext, *seriesLists):
  """
  Takes one metric or a wildcard seriesList.
  For each datapoint from each metric passed in, pick the minimum value and graph it.

  Example:

  .. code-block:: none

    &target=minSeries(Server*.connections.total)
  """
  (seriesList, start, end, step) = normalize(seriesLists)
  pathExprs = list( set([s.pathExpression for s in seriesList]) )
  name = "minSeries(%s)" % ','.join(pathExprs)
  values = ( safeMin(row) for row in izip(*seriesList) )
  series = TimeSeries(name, start, end, step, values)
  series.pathExpression = name
  return [series]

def maxSeries(requestContext, *seriesLists):
  """
  Takes one metric or a wildcard seriesList.
  For each datapoint from each metric passed in, pick the maximum value and graph it.

  Example:

  .. code-block:: none

    &target=maxSeries(Server*.connections.total)

  """
  (seriesList, start, end, step) = normalize(seriesLists)
  pathExprs = list( set([s.pathExpression for s in seriesList]) )
  name = "maxSeries(%s)" % ','.join(pathExprs)
  values = ( safeMax(row) for row in izip(*seriesList) )
  series = TimeSeries(name, start, end, step, values)
  series.pathExpression = name
  return [series]

def rangeOfSeries(requestContext, *seriesLists):
    """
    Takes a wildcard seriesList.
    Distills down a set of inputs into the range of the series

    Example:

    .. code-block:: none

        &target=rangeOfSeries(Server*.connections.total)

    """
    (seriesList,start,end,step) = normalize(seriesLists)
    name = "rangeOfSeries(%s)" % ','.join(set([s.pathExpression for s in seriesList]))
    values = ( safeSubtract(max(row), min(row)) for row in izip(*seriesList) )
    series = TimeSeries(name,start,end,step,values)
    series.pathExpression = name
    return [series]

def percentileOfSeries(requestContext, seriesList, n, interpolate=False):
  """
  percentileOfSeries returns a single series which is composed of the n-percentile
  values taken across a wildcard series at each point. Unless `interpolate` is
  set to True, percentile values are actual values contained in one of the
  supplied series.
  """
  if n <= 0:
    raise ValueError('The requested percent is required to be greater than 0')

  name = 'percentilesOfSeries(%s, %.1f)' % (seriesList[0].pathExpression, n)
  (start, end, step) = normalize([seriesList])[1:]
  values = [ _getPercentile(row, n, interpolate) for row in izip(*seriesList) ]
  resultSeries = TimeSeries(name, start, end, step, values)

  return [resultSeries]

def keepLastValue(requestContext, seriesList):
  """
  Takes one metric or a wildcard seriesList.
  Continues the line with the last received value when gaps ('None' values) appear in your data, rather than breaking your line.

  Example:

  .. code-block:: none

    &target=keepLastValue(Server01.connections.handled)

  """
  for series in seriesList:
    series.name = "keepLastValue(%s)" % (series.name)
    for i,value in enumerate(series):
      if value is None and i != 0:
        value = series[i-1]
      series[i] = value
  return seriesList

def asPercent(requestContext, seriesList, total=None):
  """

  Calculates a percentage of the total of a wildcard series. If `total` is specified,
  each series will be calculated as a percentage of that total. If `total` is not specified,
  the sum of all points in the wildcard series will be used instead.

  The `total` parameter may be a single series or a numeric value.

  Example:

  .. code-block:: none

    &target=asPercent(Server01.connections.{failed,succeeded}, Server01.connections.attempted)
    &target=asPercent(apache01.threads.busy,1500)
    &target=asPercent(Server01.cpu.*.jiffies)

  """

  normalize([seriesList])

  if total is None:
    totalValues = [ safeSum(row) for row in izip(*seriesList) ]
    totalText = None # series.pathExpression
  elif type(total) is list:
    if len(total) != 1:
      raise ValueError("asPercent second argument must reference exactly 1 series")
    normalize([seriesList, total])
    totalValues = total[0]
    totalText = totalValues.name
  else:
    totalValues = [total] * len(seriesList[0])
    totalText = str(total)

  resultList = []
  for series in seriesList:
    resultValues = [ safeMul(safeDiv(val, totalVal), 100.0) for val,totalVal in izip(series,totalValues) ]

    name = "asPercent(%s, %s)" % (series.name, totalText or series.pathExpression)
    resultSeries = TimeSeries(name,series.start,series.end,series.step,resultValues)
    resultList.append(resultSeries)

  return resultList

def divideSeries(requestContext, dividendSeriesList, divisorSeriesList):
  """
  Takes a dividend metric and a divisor metric and draws the division result.
  A constant may *not* be passed. To divide by a constant, use the scale()
  function (which is essentially a multiplication operation) and use the inverse
  of the dividend. (Division by 8 = multiplication by 1/8 or 0.125)

  Example:

  .. code-block:: none

    &target=divideSeries(Series.dividends,Series.divisors)


  """
  if len(divisorSeriesList) != 1:
    raise ValueError("divideSeries second argument must reference exactly 1 series")

  divisorSeries = divisorSeriesList[0]
  results = []

  for dividendSeries in dividendSeriesList:
    name = "divideSeries(%s,%s)" % (dividendSeries.name, divisorSeries.name)
    bothSeries = (dividendSeries, divisorSeries)
    step = reduce(lcm,[s.step for s in bothSeries])

    for s in bothSeries:
      s.consolidate( step / s.step )

    start = min([s.start for s in bothSeries])
    end = max([s.end for s in bothSeries])
    end -= (end - start) % step

    values = ( safeDiv(v1,v2) for v1,v2 in izip(*bothSeries) )

    quotientSeries = TimeSeries(name, start, end, step, values)
    quotientSeries.pathExpression = name
    results.append(quotientSeries)

  return results

def multiplySeries(requestContext, *seriesLists):
  """
  Takes two or more series and multiplies their points. A constant may not be
  used. To multiply by a constant, use the scale() function.

  Example:

  .. code-block:: none

    &target=multiplySeries(Series.dividends,Series.divisors)


  """
  (seriesList,start,end,step) = normalize(seriesLists)

  if len(seriesList) == 1:
    return seriesList

  name = "multiplySeries(%s)" % ','.join([s.name for s in seriesList])
  product = imap(lambda x: safeMul(*x), izip(*seriesList))
  return [TimeSeries(name, start, end, step, product)]

def movingMedian(requestContext, seriesList, windowSize):
  """
  Takes one metric or a wildcard seriesList followed by a number N of datapoints and graphs
  the median of N previous datapoints.  N-1 datapoints are set to None at the
  beginning of the graph.

  .. code-block:: none

    &target=movingMedian(Server.instance01.threads.busy,10)

  """
  for seriesIndex, series in enumerate(seriesList):
    newName = "movingMedian(%s,%.1f)" % (series.name, float(windowSize))
    newSeries = TimeSeries(newName, series.start, series.end, series.step, [])
    newSeries.pathExpression = newName

    windowIndex = windowSize - 1

    for i in range( len(series) ):
      if i < windowIndex: # Pad the beginning with None's since we don't have enough data
        newSeries.append( None )

      else:
        window = series[i - windowIndex : i + 1]
        nonNull = [ v for v in window if v is not None ]
        if nonNull:
          m_index = len(nonNull) / 2
          newSeries.append(sorted(nonNull)[m_index])
        else:
          newSeries.append(None)

    seriesList[ seriesIndex ] = newSeries

  return seriesList

def scale(requestContext, seriesList, factor):
  """
  Takes one metric or a wildcard seriesList followed by a constant, and multiplies the datapoint
  by the constant provided at each point.

  Example:

  .. code-block:: none

    &target=scale(Server.instance01.threads.busy,10)
    &target=scale(Server.instance*.threads.busy,10)

  """
  for series in seriesList:
    series.name = "scale(%s,%.1f)" % (series.name,float(factor))
    for i,value in enumerate(series):
      series[i] = safeMul(value,factor)
  return seriesList

def scaleToSeconds(requestContext, seriesList, seconds):
  """
  Takes one metric or a wildcard seriesList and returns "value per seconds" where
  seconds is a last argument to this functions.

  Useful in conjunction with derivative or integral function if you want
  to normalize its result to a known resolution for arbitrary retentions
  """

  for series in seriesList:
    series.name = "scaleToSeconds(%s,%d)" % (series.name,seconds)
    for i,value in enumerate(series):
      factor = seconds * 1.0 / series.step
      series[i] = safeMul(value,factor)
  return seriesList

def offset(requestContext, seriesList, factor):
  """
  Takes one metric or a wildcard seriesList followed by a constant, and adds the constant to
  each datapoint.

  Example:

  .. code-block:: none

    &target=offset(Server.instance01.threads.busy,10)

  """
  for series in seriesList:
    series.name = "offset(%s,%.1f)" % (series.name,float(factor))
    for i,value in enumerate(series):
      if value is not None:
        series[i] = value + factor
  return seriesList

def movingAverage(requestContext, seriesList, windowSize):
  """
  Takes one metric or a wildcard seriesList followed by a number N of datapoints and graphs
  the average of N previous datapoints.  N-1 datapoints are set to None at the
  beginning of the graph.

  .. code-block:: none

    &target=movingAverage(Server.instance01.threads.busy,10)

  """
  for seriesIndex, series in enumerate(seriesList):
    newName = "movingAverage(%s,%d)" % (series.name, windowSize)
    newSeries = TimeSeries(newName, series.start, series.end, series.step, [])
    newSeries.pathExpression = newName

    windowIndex = int(windowSize) - 1

    for i in range( len(series) ):
      if i < windowIndex: # Pad the beginning with None's since we don't have enough data
        newSeries.append( None )

      else:
        window = series[i - windowIndex : i + 1]
        nonNull = [ v for v in window if v is not None ]
        if nonNull:
          newSeries.append( sum(nonNull) / len(nonNull) )
        else:
          newSeries.append(None)

    seriesList[ seriesIndex ] = newSeries

  return seriesList

def cumulative(requestContext, seriesList):
  """
  Takes one metric or a wildcard seriesList.

  By default, when a graph is drawn, and the width of the graph in pixels is
  smaller than the number of datapoints to be graphed, Graphite averages the
  value at each pixel.  The cumulative() function changes the consolidation
  function to sum from average.  This is especially useful in sales graphs,
  where fractional values make no sense (How can you have half of a sale?)

  .. code-block:: none

    &target=cumulative(Sales.widgets.largeBlue)

  """
  for series in seriesList:
    series.consolidationFunc = 'sum'
    series.name = 'cumulative(%s)' % series.name
  return seriesList

def derivative(requestContext, seriesList):
  """
  This is the opposite of the integral function.  This is useful for taking a
  running total metric and showing how many requests per minute were handled.

  Example:

  .. code-block:: none

    &target=derivative(company.server.application01.ifconfig.TXPackets)

  Each time you run ifconfig, the RX and TXPackets are higher (assuming there
  is network traffic.) By applying the derivative function, you can get an
  idea of the packets per minute sent or received, even though you're only
  recording the total.
  """
  results = []
  for series in seriesList:
    newValues = []
    prev = None
    for val in series:
      if None in (prev,val):
        newValues.append(None)
        prev = val
        continue
      newValues.append(val - prev)
      prev = val
    newName = "derivative(%s)" % series.name
    newSeries = TimeSeries(newName, series.start, series.end, series.step, newValues)
    newSeries.pathExpression = newName
    results.append(newSeries)
  return results

def integral(requestContext, seriesList):
  """
  This will show the sum over time, sort of like a continuous addition function.
  Useful for finding totals or trends in metrics that are collected per minute.

  Example:

  .. code-block:: none

    &target=integral(company.sales.perMinute)

  This would start at zero on the left side of the graph, adding the sales each
  minute, and show the total sales for the time period selected at the right
  side, (time now, or the time specified by '&until=').
  """
  results = []
  for series in seriesList:
    newValues = []
    current = 0.0
    for val in series:
      if val is None:
        newValues.append(None)
      else:
        current += val
        newValues.append(current)
    newName = "integral(%s)" % series.name
    newSeries = TimeSeries(newName, series.start, series.end, series.step, newValues)
    newSeries.pathExpression = newName
    results.append(newSeries)
  return results


def nonNegativeDerivative(requestContext, seriesList, maxValue=None):
  """
  Same as the derivative function above, but ignores datapoints that trend
  down.  Useful for counters that increase for a long time, then wrap or
  reset. (Such as if a network interface is destroyed and recreated by unloading
  and re-loading a kernel module, common with USB / WiFi cards.

  Example:

  .. code-block:: none

    &target=derivative(company.server.application01.ifconfig.TXPackets)

  """
  results = []

  for series in seriesList:
    newValues = []
    prev = None

    for val in series:
      if None in (prev, val):
        newValues.append(None)
        prev = val
        continue

      diff = val - prev
      if diff >= 0:
        newValues.append(diff)
      elif maxValue is not None and maxValue >= val:
        newValues.append( (maxValue - prev) + val  + 1 )
      else:
        newValues.append(None)

      prev = val

    newName = "nonNegativeDerivative(%s)" % series.name
    newSeries = TimeSeries(newName, series.start, series.end, series.step, newValues)
    newSeries.pathExpression = newName
    results.append(newSeries)

  return results

def stacked(requestContext,seriesLists,stackName='__DEFAULT__'):
  """
  Takes one metric or a wildcard seriesList and change them so they are
  stacked. This is a way of stacking just a couple of metrics without having
  to use the stacked area mode (that stacks everything). By means of this a mixed
  stacked and non stacked graph can be made

  It can also take an optional argument with a name of the stack, in case there is
  more than one, e.g. for input and output metrics.

  Example:

  .. code-block:: none

    &target=stacked(company.server.application01.ifconfig.TXPackets, 'tx')

  """
  if 'totalStack' in requestContext:
    totalStack = requestContext['totalStack'].get(stackName, [])
  else:
    requestContext['totalStack'] = {}
    totalStack = [];
  results = []
  for series in seriesLists:
    newValues = []
    for i in range(len(series)):
      if len(totalStack) <= i: totalStack.append(0)

      if series[i] is not None:
        totalStack[i] += series[i]
        newValues.append(totalStack[i])
      else:
        newValues.append(None)

    # Work-around for the case when legend is set
    if stackName=='__DEFAULT__':
      newName = "stacked(%s)" % series.name
    else:
      newName = series.name

    newSeries = TimeSeries(newName, series.start, series.end, series.step, newValues)
    newSeries.options['stacked'] = True
    newSeries.pathExpression = newName
    results.append(newSeries)
  requestContext['totalStack'][stackName] = totalStack
  return results


def areaBetween(requestContext, seriesList):
  """
  Draws the area in between the two series in seriesList
  """
  assert len(seriesList) == 2, "areaBetween series argument must reference *exactly* 2 series"
  lower = seriesList[0]
  upper = seriesList[1]

  lower.options['stacked'] = True
  lower.options['invisible'] = True

  upper.options['stacked'] = True
  lower.name = upper.name = "areaBetween(%s)" % upper.pathExpression
  return seriesList


def aliasSub(requestContext, seriesList, search, replace):
  """
  Runs series names through a regex search/replace.

  .. code-block:: none

    &target=aliasSub(ip.*TCP*,"^.*TCP(\d+)","\\1")
  """
  for series in seriesList:
    series.name = re.sub(search, replace, series.name)
  return seriesList


def alias(requestContext, seriesList, newName):
  """
  Takes one metric or a wildcard seriesList and a string in quotes.
  Prints the string instead of the metric name in the legend.

  .. code-block:: none

    &target=alias(Sales.widgets.largeBlue,"Large Blue Widgets")

  """
  for series in seriesList:
    series.name = newName
  return seriesList

def cactiStyle(requestContext, seriesList):
  """
  Takes a series list and modifies the aliases to provide column aligned
  output with Current, Max, and Min values in the style of cacti.
  NOTE: column alignment only works with monospace fonts such as terminus.

  .. code-block:: none

    &target=cactiStyle(ganglia.*.net.bytes_out)

  """
  nameLen = max([len(getattr(series,"name")) for series in seriesList])
  lastLen = max([len(repr(int(safeLast(series) or 3))) for series in seriesList]) + 3
  maxLen = max([len(repr(int(safeMax(series) or 3))) for series in seriesList]) + 3
  minLen = max([len(repr(int(safeMin(series) or 3))) for series in seriesList]) + 3
  for series in seriesList:
      name = series.name
      last = safeLast(series)
      maximum = safeMax(series)
      minimum = safeMin(series)
      if last is None:
        last = NAN
      if maximum is None:
        maximum = NAN
      if minimum is None:
        minimum = NAN

      series.name = "%*s Current:%*.2f Max:%*.2f Min:%*.2f" % \
          (-nameLen, series.name,
          lastLen, last,
          maxLen, maximum,
          minLen, minimum)
  return seriesList

def aliasByNode(requestContext, seriesList, *nodes):
  """
  Takes a seriesList and applies an alias derived from one or more "node"
  portion/s of the target name. Node indices are 0 indexed.

  .. code-block:: none

    &target=aliasByNode(ganglia.*.cpu.load5,1)

  """
  if type(nodes) is int:
    nodes=[nodes]
  for series in seriesList:
    metric_pieces = re.search('(?:.*\()?(?P<name>[-\w*\.]+)(?:,|\)?.*)?',series.name).groups()[0].split('.')
    series.name = '.'.join(metric_pieces[n] for n in nodes)
  return seriesList

def aliasByMetric(requestContext, seriesList):
  """
  Takes a seriesList and applies an alias derived from the base metric name.

  .. code-block:: none

    &target=aliasByMetric(carbon.agents.graphite.creates)

  """
  for series in seriesList:
    series.name = series.name.split('.')[-1]
  return seriesList

def legendValue(requestContext, seriesList, *valueTypes):
  """
  Takes one metric or a wildcard seriesList and a string in quotes.
  Appends a value to the metric name in the legend.  Currently one or several of: `last`, `avg`,
  `total`, `min`, `max`.
  The last argument can be `si` (default) or `binary`, in that case values will be formatted in the
  corresponding system.

  .. code-block:: none

  &target=legendValue(Sales.widgets.largeBlue, 'avg', 'max', 'si')

  """
  def last(s):
    "Work-around for the missing last point"
    v = s[-1]
    if v is None:
      return s[-2]
    return v

  valueFuncs = {
    'avg':   lambda s: safeDiv(safeSum(s), safeLen(s)),
    'total': safeSum,
    'min':   safeMin,
    'max':   safeMax,
    'last':  last
  }
  system = None
  if valueTypes[-1] in ('si', 'binary'):
    system = valueTypes[-1]
    valueTypes = valueTypes[:-1]
  for valueType in valueTypes:
    valueFunc = valueFuncs.get(valueType, lambda s: '(?)')
    if system is None:
      for series in seriesList:
        series.name += " (%s: %s)" % (valueType, valueFunc(series))
    else:
      for series in seriesList:
        value = valueFunc(series)
        formatted = None
        if value is not None:
          formatted = "%.2f%s" % format_units(abs(value), system=system)
        series.name = "%-20s%-5s%-10s" % (series.name, valueType, formatted)
  return seriesList

def alpha(requestContext, seriesList, alpha):
  """
  Assigns the given alpha transparency setting to the series. Takes a float value between 0 and 1.
  """
  for series in seriesList:
    series.options['alpha'] = alpha
  return seriesList

def color(requestContext, seriesList, theColor):
  """
  Assigns the given color to the seriesList

  Example:

  .. code-block:: none

    &target=color(collectd.hostname.cpu.0.user, 'green')
    &target=color(collectd.hostname.cpu.0.system, 'ff0000')
    &target=color(collectd.hostname.cpu.0.idle, 'gray')
    &target=color(collectd.hostname.cpu.0.idle, '6464ffaa')

  """
  for series in seriesList:
    series.color = theColor
  return seriesList

def substr(requestContext, seriesList, start=0, stop=0):
  """
  Takes one metric or a wildcard seriesList followed by 1 or 2 integers.  Assume that the
  metric name is a list or array, with each element separated by dots.  Prints
  n - length elements of the array (if only one integer n is passed) or n - m
  elements of the array (if two integers n and m are passed).  The list starts
  with element 0 and ends with element (length - 1).

  Example:

  .. code-block:: none

    &target=substr(carbon.agents.hostname.avgUpdateTime,2,4)

  The label would be printed as "hostname.avgUpdateTime".

  """
  for series in seriesList:
    left = series.name.rfind('(') + 1
    right = series.name.find(')')
    if right < 0:
      right = len(series.name)+1
    cleanName = series.name[left:right:]
    if int(stop) == 0:
      series.name = '.'.join(cleanName.split('.')[int(start)::])
    else:
      series.name = '.'.join(cleanName.split('.')[int(start):int(stop):])

    # substr(func(a.b,'c'),1) becomes b instead of b,'c'
    series.name = re.sub(',.*$', '', series.name)
  return seriesList


def logarithm(requestContext, seriesList, base=10):
  """
  Takes one metric or a wildcard seriesList, a base, and draws the y-axis in logarithmic
  format.  If base is omitted, the function defaults to base 10.

  Example:

  .. code-block:: none

    &target=log(carbon.agents.hostname.avgUpdateTime,2)

  """
  results = []
  for series in seriesList:
    newValues = []
    for val in series:
      if val is None:
        newValues.append(None)
      elif val <= 0:
        newValues.append(None)
      else:
        newValues.append(math.log(val, base))
    newName = "log(%s, %s)" % (series.name, base)
    newSeries = TimeSeries(newName, series.start, series.end, series.step, newValues)
    newSeries.pathExpression = newName
    results.append(newSeries)
  return results


def maximumAbove(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by a constant n.
  Draws only the metrics with a maximum value above n.

  Example:

  .. code-block:: none

    &target=maximumAbove(system.interface.eth*.packetsSent,1000)

  This would only display interfaces which sent more than 1000 packets/min.
  """
  results = []
  for series in seriesList:
    if max(series) > n:
      results.append(series)
  return results


def minimumAbove(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by a constant n.
  Draws only the metrics with a minimum value above n.

  Example:

  .. code-block:: none

    &target=minimumAbove(system.interface.eth*.packetsSent,1000)

  This would only display interfaces which sent more than 1000 packets/min.
  """
  results = []
  for series in seriesList:
    if min(series) > n:
      results.append(series)
  return results


def maximumBelow(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by a constant n.
  Draws only the metrics with a maximum value below n.

  Example:

  .. code-block:: none

    &target=maximumBelow(system.interface.eth*.packetsSent,1000)

  This would only display interfaces which sent less than 1000 packets/min.
  """

  result = []
  for series in seriesList:
    if max(series) <= n:
      result.append(series)
  return result


def highestCurrent(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by an integer N.
  Out of all metrics passed, draws only the N metrics with the highest value
  at the end of the time period specified.

  Example:

  .. code-block:: none

    &target=highestCurrent(server*.instance*.threads.busy,5)

  Draws the 5 servers with the highest busy threads.

  """
  return sorted( seriesList, key=safeLast )[-n:]

def highestMax(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by an integer N.

  Out of all metrics passed, draws only the N metrics with the highest maximum
  value in the time period specified.

  Example:

  .. code-block:: none

    &target=highestCurrent(server*.instance*.threads.busy,5)

  Draws the top 5 servers who have had the most busy threads during the time
  period specified.

  """
  result_list = sorted( seriesList, key=lambda s: max(s) )[-n:]

  return sorted(result_list, key=lambda s: max(s), reverse=True)

def lowestCurrent(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by an integer N.
  Out of all metrics passed, draws only the N metrics with the lowest value at
  the end of the time period specified.

  Example:

  .. code-block:: none

    &target=lowestCurrent(server*.instance*.threads.busy,5)

  Draws the 5 servers with the least busy threads right now.

  """

  return sorted( seriesList, key=safeLast )[:n]

def currentAbove(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by an integer N.
  Out of all metrics passed, draws only the  metrics whose value is above N
  at the end of the time period specified.

  Example:

  .. code-block:: none

    &target=highestAbove(server*.instance*.threads.busy,50)

  Draws the servers with more than 50 busy threads.

  """
  return [ series for series in seriesList if safeLast(series) >= n ]

def currentBelow(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by an integer N.
  Out of all metrics passed, draws only the  metrics whose value is below N
  at the end of the time period specified.

  Example:

  .. code-block:: none

    &target=currentBelow(server*.instance*.threads.busy,3)

  Draws the servers with less than 3 busy threads.

  """
  return [ series for series in seriesList if safeLast(series) <= n ]

def highestAverage(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by an integer N.
  Out of all metrics passed, draws only the top N metrics with the highest
  average value for the time period specified.

  Example:

  .. code-block:: none

    &target=highestAverage(server*.instance*.threads.busy,5)

  Draws the top 5 servers with the highest average value.

  """

  return sorted( seriesList, key=lambda s: safeDiv(safeSum(s),safeLen(s)) )[-n:]

def lowestAverage(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by an integer N.
  Out of all metrics passed, draws only the bottom N metrics with the lowest
  average value for the time period specified.

  Example:

  .. code-block:: none

    &target=lowestAverage(server*.instance*.threads.busy,5)

  Draws the bottom 5 servers with the lowest average value.

  """

  return sorted( seriesList, key=lambda s: safeDiv(safeSum(s),safeLen(s)) )[:n]

def averageAbove(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by an integer N.
  Out of all metrics passed, draws only the metrics with an average value
  above N for the time period specified.

  Example:

  .. code-block:: none

    &target=averageAbove(server*.instance*.threads.busy,25)

  Draws the servers with average values above 25.

  """
  return [ series for series in seriesList if safeDiv(safeSum(series),safeLen(series)) >= n ]

def averageBelow(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by an integer N.
  Out of all metrics passed, draws only the metrics with an average value
  below N for the time period specified.

  Example:

  .. code-block:: none

    &target=averageBelow(server*.instance*.threads.busy,25)

  Draws the servers with average values below 25.

  """
  return [ series for series in seriesList if safeDiv(safeSum(series),safeLen(series)) <= n ]

def _getPercentile(points, n, interpolate=False):
  """
  Percentile is calculated using the method outlined in the NIST Engineering
  Statistics Handbook:
  http://www.itl.nist.gov/div898/handbook/prc/section2/prc252.htm
  """
  sortedPoints = sorted([ p for p in points if points is not None])
  if len(sortedPoints) == 0:
    return None
  fractionalRank = (n/100.0) * (len(sortedPoints) + 1)
  rank = int(fractionalRank)
  rankFraction = fractionalRank - rank

  if not interpolate:
    rank += int(math.ceil(rankFraction))

  if rank == 0:
    percentile = sortedPoints[0]
  elif rank - 1 == len(sortedPoints):
    percentile = sortedPoints[-1]
  else:
    percentile = sortedPoints[rank - 1] # Adjust for 0-index

  if interpolate:
    if rank != len(sortedPoints): # if a next value exists
      nextValue = sortedPoints[rank]
      percentile = percentile + rankFraction * (nextValue - percentile)

  return percentile

def nPercentile(requestContext, seriesList, n):
  """Returns n-percent of each series in the seriesList."""
  assert n, 'The requested percent is required to be greater than 0'

  results = []
  for s in seriesList:
    # Create a sorted copy of the TimeSeries excluding None values in the values list.
    s_copy = TimeSeries( s.name, s.start, s.end, s.step, sorted( [item for item in s if item is not None] ) )
    if not s_copy:
      continue  # Skip this series because it is empty.

    perc_val = _getPercentile(s_copy, n)
    if perc_val:
      results.append( TimeSeries( '%dth Percentile(%s, %.1f)' % ( n, s_copy.name, perc_val ),
                                  s_copy.start, s_copy.end, s_copy.step, [perc_val] ) )
  return results

def removeAbovePercentile(requestContext, seriesList, n):
  """
  Removes data above the nth percentile from the series or list of series provided.
  Values below this percentile are assigned a value of None.
  """
  for s in seriesList:
    s.name = 'removeAbovePercentile(%s, %d)' % (s.name, n)
    percentile = nPercentile(requestContext, [s], n)[0][0]
    for (index, val) in enumerate(s):
      if val > percentile:
        s[index] = None

  return seriesList

def removeAboveValue(requestContext, seriesList, n):
  """
  Removes data above the given threshold from the series or list of series provided.
  Values below this threshole are assigned a value of None
  """
  for s in seriesList:
    s.name = 'removeAboveValue(%s, %d)' % (s.name, n)
    for (index, val) in enumerate(s):
      if val > n:
        s[index] = None

  return seriesList

def removeBelowPercentile(requestContext, seriesList, n):
  """
  Removes data above the nth percentile from the series or list of series provided.
  Values below this percentile are assigned a value of None.
  """
  for s in seriesList:
    s.name = 'removeBelowPercentile(%s, %d)' % (s.name, n)
    percentile = nPercentile(requestContext, [s], n)[0][0]
    for (index, val) in enumerate(s):
      if val < percentile:
        s[index] = None

  return seriesList

def removeBelowValue(requestContext, seriesList, n):
  """
  Removes data above the given threshold from the series or list of series provided.
  Values below this threshole are assigned a value of None
  """
  for s in seriesList:
    s.name = 'removeBelowValue(%s, %d)' % (s.name, n)
    for (index, val) in enumerate(s):
      if val < n:
        s[index] = None

  return seriesList

def limit(requestContext, seriesList, n):
  """
  Takes one metric or a wildcard seriesList followed by an integer N.

  Only draw the first N metrics.  Useful when testing a wildcard in a metric.

  Example:

  .. code-block:: none

    &target=limit(server*.instance*.memory.free,5)

  Draws only the first 5 instance's memory free.

  """
  return seriesList[0:n]

def sortByMaxima(requestContext, seriesList):
  """
  Takes one metric or a wildcard seriesList.

  Sorts the list of metrics by the maximum value across the time period
  specified.  Useful with the &areaMode=all parameter, to keep the
  lowest value lines visible.

  Example:

  .. code-block:: none

    &target=sortByMaxima(server*.instance*.memory.free)

  """
  def compare(x,y):
    return cmp(max(y), max(x))
  seriesList.sort(compare)
  return seriesList

def sortByMinima(requestContext, seriesList):
  """
  Takes one metric or a wildcard seriesList.

  Sorts the list of metrics by the lowest value across the time period
  specified.

  Example:

  .. code-block:: none

    &target=sortByMinima(server*.instance*.memory.free)

  """
  def compare(x,y):
    return cmp(min(x), min(y))
  newSeries = [series for series in seriesList if max(series) > 0]
  newSeries.sort(compare)
  return newSeries

def mostDeviant(requestContext, n, seriesList):
  """
  Takes an integer N followed by one metric or a wildcard seriesList.
  Draws the N most deviant metrics.
  To find the deviant, the average across all metrics passed is determined,
  and then the average of each metric is compared to the overall average.

    Example:

  .. code-block:: none

    &target=mostDeviant(5, server*.instance*.memory.free)

  Draws the 5 instances furthest from the average memory free.

  """

  deviants = []
  for series in seriesList:
    mean = safeDiv( safeSum(series), safeLen(series) )
    if mean is None: continue
    square_sum = sum([ (value - mean) ** 2 for value in series if value is not None ])
    sigma = safeDiv(square_sum, safeLen(series))
    if sigma is None: continue
    deviants.append( (sigma, series) )
  deviants.sort(key=lambda i: i[0], reverse=True) #sort by sigma
  return [ series for (sigma,series) in deviants ][:n] #return the n most deviant series


def stdev(requestContext, seriesList, points, windowTolerance=0.1):
  """
  Takes one metric or a wildcard seriesList followed by an integer N.
  Draw the Standard Deviation of all metrics passed for the past N datapoints.
  If the ratio of null points in the window is greater than windowTolerance,
  skip the calculation. The default for windowTolerance is 0.1 (up to 10% of points
  in the window can be missing). Note that if this is set to 0.0, it will cause large
  gaps in the output anywhere a single point is missing.

  Example:

  .. code-block:: none

    &target=stdev(server*.instance*.threads.busy,30)
    &target=stdev(server*.instance*.cpu.system,30,0.0)

  """

  # For this we take the standard deviation in terms of the moving average
  # and the moving average of series squares.
  for (seriesIndex,series) in enumerate(seriesList):
    stddevSeries = TimeSeries("stddev(%s,%.1f)" % (series.name, float(points)), series.start, series.end, series.step, [])
    stddevSeries.pathExpression = "stddev(%s,%.1f)" % (series.name, float(points))

    validPoints = 0
    currentSum = 0
    currentSumOfSquares = 0
    for (index, newValue) in enumerate(series):
      # Mark whether we've reached our window size - dont drop points out otherwise
      if index < points:
        bootstrapping = True
        droppedValue = None
      else:
        bootstrapping = False
        droppedValue = series[index - points]

      # Track non-None points in window
      if not bootstrapping and droppedValue is not None:
        validPoints -= 1
      if newValue is not None:
        validPoints += 1

      # Remove the value that just dropped out of the window
      if not bootstrapping and droppedValue is not None:
        currentSum -= droppedValue
        currentSumOfSquares -= droppedValue**2

      # Add in the value that just popped in the window
      if newValue is not None:
        currentSum += newValue
        currentSumOfSquares += newValue**2

      if validPoints > 0 and \
        float(validPoints)/points >= windowTolerance:

        try:
          deviation = math.sqrt(validPoints * currentSumOfSquares - currentSum**2)/validPoints
        except ValueError:
          deviation = None
        stddevSeries.append(deviation)
      else:
        stddevSeries.append(None)

    seriesList[seriesIndex] = stddevSeries

  return seriesList

def secondYAxis(requestContext, seriesList):
  """
  Graph the series on the secondary Y axis.
  """
  for series in seriesList:
    series.options['secondYAxis'] = True
    series.name= 'secondYAxis(%s)' % series.name
  return seriesList

def _fetchWithBootstrap(requestContext, series, days=7):
  'Request the same data but with a bootstrap period at the beginning'
  previousContext = requestContext.copy()
  # go back 1 week to get a solid bootstrap
  previousContext['startTime'] = requestContext['startTime'] - timedelta(days)
  previousContext['endTime'] = requestContext['startTime']
  oldSeries = evaluateTarget(previousContext, series.pathExpression)[0]

  newValues = []
  if oldSeries.step != series.step:
    ratio = oldSeries.step / series.step
    for value in oldSeries:
      newValues.extend([ value ] * ratio)
  else:
    newValues.extend(oldSeries)
  newValues.extend(series)

  newSeries = TimeSeries(series.name, oldSeries.start, series.end, series.step, newValues)
  newSeries.pathExpression = series.name
  return newSeries

def _trimBootstrap(bootstrap, original):
  'Trim the bootstrap period off the front of this series so it matches the original'
  original_len = len(original)
  bootstrap_len = len(bootstrap)
  length_limit = (original_len * original.step) / bootstrap.step
  trim_start = bootstrap.end - (length_limit * bootstrap.step)
  trimmed = TimeSeries(bootstrap.name, trim_start, bootstrap.end, bootstrap.step,
        bootstrap[-length_limit:])
  return trimmed

def holtWintersIntercept(alpha,actual,last_season,last_intercept,last_slope):
  return alpha * (actual - last_season) \
          + (1 - alpha) * (last_intercept + last_slope)

def holtWintersSlope(beta,intercept,last_intercept,last_slope):
  return beta * (intercept - last_intercept) + (1 - beta) * last_slope

def holtWintersSeasonal(gamma,actual,intercept,last_season):
  return gamma * (actual - intercept) + (1 - gamma) * last_season

def holtWintersDeviation(gamma,actual,prediction,last_seasonal_dev):
  if prediction is None:
    prediction = 0
  return gamma * math.fabs(actual - prediction) + (1 - gamma) * last_seasonal_dev

def holtWintersAnalysis(series):
  alpha = gamma = 0.1
  beta = 0.0035
  # season is currently one day
  season_length = (24*60*60) / series.step
  intercept = 0
  slope = 0
  pred = 0
  intercepts = list()
  slopes = list()
  seasonals = list()
  predictions = list()
  deviations = list()

  def getLastSeasonal(i):
    j = i - season_length
    if j >= 0:
      return seasonals[j]
    return 0

  def getLastDeviation(i):
    j = i - season_length
    if j >= 0:
      return deviations[j]
    return 0

  last_seasonal = 0
  last_seasonal_dev = 0
  next_last_seasonal = 0
  next_pred = None

  for i,actual in enumerate(series):
    if actual is None:
      # missing input values break all the math
      # do the best we can and move on
      intercepts.append(None)
      slopes.append(0)
      seasonals.append(0)
      predictions.append(next_pred)
      deviations.append(0)
      next_pred = None
      continue

    if i == 0:
      last_intercept = actual
      last_slope = 0
      # seed the first prediction as the first actual
      prediction = actual
    else:
      last_intercept = intercepts[-1]
      last_slope = slopes[-1]
      if last_intercept is None:
        last_intercept = actual
      prediction = next_pred

    last_seasonal = getLastSeasonal(i)
    next_last_seasonal = getLastSeasonal(i+1)
    last_seasonal_dev = getLastDeviation(i)

    intercept = holtWintersIntercept(alpha,actual,last_seasonal
            ,last_intercept,last_slope)
    slope = holtWintersSlope(beta,intercept,last_intercept,last_slope)
    seasonal = holtWintersSeasonal(gamma,actual,intercept,last_seasonal)
    next_pred = intercept + slope + next_last_seasonal
    deviation = holtWintersDeviation(gamma,actual,prediction,last_seasonal_dev)

    intercepts.append(intercept)
    slopes.append(slope)
    seasonals.append(seasonal)
    predictions.append(prediction)
    deviations.append(deviation)

  # make the new forecast series
  forecastName = "holtWintersForecast(%s)" % series.name
  forecastSeries = TimeSeries(forecastName, series.start, series.end
    , series.step, predictions)
  forecastSeries.pathExpression = forecastName

  # make the new deviation series
  deviationName = "holtWintersDeviation(%s)" % series.name
  deviationSeries = TimeSeries(deviationName, series.start, series.end
          , series.step, deviations)
  deviationSeries.pathExpression = deviationName

  results = { 'predictions': forecastSeries
        , 'deviations': deviationSeries
        , 'intercepts': intercepts
        , 'slopes': slopes
        , 'seasonals': seasonals
        }
  return results

def holtWintersForecast(requestContext, seriesList):
  """
  Performs a Holt-Winters forecast using the series as input data. Data from
  one week previous to the series is used to bootstrap the initial forecast.
  """
  results = []
  for series in seriesList:
    withBootstrap = _fetchWithBootstrap(requestContext, series)
    analysis = holtWintersAnalysis(withBootstrap)
    results.append(_trimBootstrap(analysis['predictions'], series))
  return results

def holtWintersConfidenceBands(requestContext, seriesList, delta=3):
  """
  Performs a Holt-Winters forecast using the series as input data and plots
  upper and lower bands with the predicted forecast deviations.
  """
  results = []
  for series in seriesList:
    bootstrap = _fetchWithBootstrap(requestContext, series)
    analysis = holtWintersAnalysis(bootstrap)
    forecast = _trimBootstrap(analysis['predictions'], series)
    deviation = _trimBootstrap(analysis['deviations'], series)
    seriesLength = len(forecast)
    i = 0
    upperBand = list()
    lowerBand = list()
    while i < seriesLength:
      forecast_item = forecast[i]
      deviation_item = deviation[i]
      i = i + 1
      if forecast_item is None or deviation_item is None:
        upperBand.append(None)
        lowerBand.append(None)
      else:
        scaled_deviation = delta * deviation_item
        upperBand.append(forecast_item + scaled_deviation)
        lowerBand.append(forecast_item - scaled_deviation)

    upperName = "holtWintersConfidenceUpper(%s)" % series.name
    lowerName = "holtWintersConfidenceLower(%s)" % series.name
    upperSeries = TimeSeries(upperName, forecast.start, forecast.end
            , forecast.step, upperBand)
    lowerSeries = TimeSeries(lowerName, forecast.start, forecast.end
            , forecast.step, lowerBand)
    upperSeries.pathExpression = series.pathExpression
    lowerSeries.pathExpression = series.pathExpression
    results.append(lowerSeries)
    results.append(upperSeries)
  return results

def holtWintersAberration(requestContext, seriesList, delta=3):
  """
  Performs a Holt-Winters forecast using the series as input data and plots the
  positive or negative deviation of the series data from the forecast.
  """
  results = []
  for series in seriesList:
    confidenceBands = holtWintersConfidenceBands(requestContext, [series], delta)
    bootstrapped = _fetchWithBootstrap(requestContext, series)
    series = _trimBootstrap(bootstrapped, series)
    lowerBand = confidenceBands[0]
    upperBand = confidenceBands[1]
    aberration = list()
    for i, actual in enumerate(series):
      if series[i] is None:
        aberration.append(0)
      elif series[i] > upperBand[i]:
        aberration.append(series[i] - upperBand[i])
      elif series[i] < lowerBand[i]:
        aberration.append(series[i] - lowerBand[i])
      else:
        aberration.append(0)

    newName = "holtWintersAberration(%s)" % series.name
    results.append(TimeSeries(newName, series.start, series.end
            , series.step, aberration))
  return results

def holtWintersConfidenceArea(requestContext, seriesList, delta=3):
  """
  Performs a Holt-Winters forecast using the series as input data and plots the
  area between the upper and lower bands of the predicted forecast deviations.
  """
  bands = holtWintersConfidenceBands(requestContext, seriesList, delta)
  results = areaBetween(requestContext, bands)
  for series in results:
    series.name = series.name.replace('areaBetween', 'holtWintersConfidenceArea')
  return results


def drawAsInfinite(requestContext, seriesList):
  """
  Takes one metric or a wildcard seriesList.
  If the value is zero, draw the line at 0.  If the value is above zero, draw
  the line at infinity. If the value is null or less than zero, do not draw
  the line.

  Useful for displaying on/off metrics, such as exit codes. (0 = success,
  anything else = failure.)

  Example:

  .. code-block:: none

    drawAsInfinite(Testing.script.exitCode)

  """
  for series in seriesList:
    series.options['drawAsInfinite'] = True
    series.name = 'drawAsInfinite(%s)' % series.name
  return seriesList

def lineWidth(requestContext, seriesList, width):
  """
  Takes one metric or a wildcard seriesList, followed by a float F.

  Draw the selected metrics with a line width of F, overriding the default
  value of 1, or the &lineWidth=X.X parameter.

  Useful for highlighting a single metric out of many, or having multiple
  line widths in one graph.

  Example:

  .. code-block:: none

    &target=lineWidth(server01.instance01.memory.free,5)

  """
  for series in seriesList:
    series.options['lineWidth'] = width
  return seriesList

def dashed(requestContext, *seriesList):
  """
  Takes one metric or a wildcard seriesList, followed by a float F.

  Draw the selected metrics with a dotted line with segments of length F
  If omitted, the default length of the segments is 5.0

  Example:

  .. code-block:: none

    &target=dashed(server01.instance01.memory.free,2.5)

  """

  if len(seriesList) == 2:
    dashLength = seriesList[1]
  else:
    dashLength = 5
  for series in seriesList[0]:
    series.name = 'dashed(%s, %d)' % (series.name, dashLength)
    series.options['dashed'] = dashLength
  return seriesList[0]


def timeShift(requestContext, seriesList, timeShift):
  """
  Takes one metric or a wildcard seriesList, followed by a quoted string with the
  length of time (See `from / until`_. in the `URL API`_ for examples of time formats).

  Draws the selected metrics shifted in time. If no sign is given, a minus sign ( - ) is
  implied which will shift the metric back in time. If a plus sign ( + ) is given, the
  metric will be shifted forward in time.

  Useful for comparing a metric against itself at a past periods or correcting data
  stored at an offset.

  Example:

  .. code-block:: none

    &target=timeShift(Sales.widgets.largeBlue,"7d")
    &target=timeShift(Sales.widgets.largeBlue,"-7d")
    &target=timeShift(Sales.widgets.largeBlue,"+1h")

  """
  # Default to negative. parseTimeOffset defaults to +
  if timeShift[0].isdigit():
    timeShift = '-' + timeShift
  delta = parseTimeOffset(timeShift)
  myContext = requestContext.copy()
  myContext['startTime'] = requestContext['startTime'] + delta
  myContext['endTime'] = requestContext['endTime'] + delta
  series = seriesList[0] # if len(seriesList) > 1, they will all have the same pathExpression, which is all we care about.
  results = []

  for shiftedSeries in evaluateTarget(myContext, series.pathExpression):
    shiftedSeries.name = 'timeShift(%s, %s)' % (shiftedSeries.name, timeShift)
    shiftedSeries.start = series.start
    shiftedSeries.end = series.end
    results.append(shiftedSeries)

  return results


def constantLine(requestContext, value):
  """
  Takes a float F.

  Draws a horizontal line at value F across the graph.

  Example:

  .. code-block:: none

    &target=constantLine(123.456)

  """
  start = timestamp( requestContext['startTime'] )
  end = timestamp( requestContext['endTime'] )
  step = (end - start) / 2.0
  series = TimeSeries(str(value), start, end, step, [value, value])
  return [series]


def threshold(requestContext, value, label=None, color=None):
  """
  Takes a float F, followed by a label (in double quotes) and a color.
  (See URL API for valid color names & formats.)

  Draws a horizontal line at value F across the graph.

  Example:

  .. code-block:: none

    &target=threshold(123.456, "omgwtfbbq", red)

  """

  series = constantLine(requestContext, value)[0]
  if label:
    series.name = label
  if color:
    series.color = color

  return [series]

def transformNull(requestContext, seriesList, default=0):
  """
  Takes a metric or wild card seriesList and an optional value
  to transform Nulls to. Default is 0. This method compliments
  drawNullAsZero flag in graphical mode but also works in text only
  mode.
  Example:

  .. code-block:: none

    &target=transformNull(webapp.pages.*.views,-1)

  This would take any page that didn't have values and supply negative 1 as a default.
  Any other numeric value may be used as well.
  """
  def transform(v):
    if v is None: return default
    else: return v

  for series in seriesList:
    values = [transform(v) for v in series]
    series.extend(values)
    del series[:len(values)]
  return seriesList

def group(requestContext, *seriesLists):
  """
  Takes an arbitrary number of seriesLists and adds them to a single seriesList. This is used
  to pass multiple seriesLists to a function which only takes one
  """
  seriesGroup = []
  for s in seriesLists:
    seriesGroup.extend(s)

  return seriesGroup


def groupByNode(requestContext, seriesList, nodeNum, callback):
  """
  Takes a serieslist and maps a callback to subgroups within as defined by a common node

  .. code-block:: none

    &target=groupByNode(ganglia.by-function.*.*.cpu.load5,2,"sumSeries")

    Would return multiple series which are each the result of applying the "sumSeries" function
    to groups joined on the second node (0 indexed) resulting in a list of targets like
    sumSeries(ganglia.by-function.server1.*.cpu.load5),sumSeries(ganglia.by-function.server2.*.cpu.load5),...

  """
  metaSeries = {}
  keys = []
  for series in seriesList:
    key = series.name.split(".")[nodeNum]
    if key not in metaSeries.keys():
      metaSeries[key] = [series]
      keys.append(key)
    else:
      metaSeries[key].append(series)
  for key in metaSeries.keys():
    metaSeries[key] = SeriesFunctions[callback](requestContext,
        metaSeries[key])[0]
    metaSeries[key].name = key
  return [ metaSeries[key] for key in keys ]


def exclude(requestContext, seriesList, pattern):
  """
  Takes a metric or a wildcard seriesList, followed by a regular expression
  in double quotes.  Excludes metrics that match the regular expression.

  Example:

  .. code-block:: none

    &target=exclude(servers*.instance*.threads.busy,"server02")
  """
  regex = re.compile(pattern)
  return [s for s in seriesList if not regex.search(s.name)]


def smartSummarize(requestContext, seriesList, intervalString, func='sum', alignToFrom=False):
  """
  Smarter experimental version of summarize.

  The alignToFrom parameter has been deprecated, it no longer has any effect.
  Alignment happens automatically for days, hours, and minutes.
  """
  if alignToFrom:
    log.info("Deprecated parameter 'alignToFrom' is being ignored.")

  results = []
  delta = parseTimeOffset(intervalString)
  interval = delta.seconds + (delta.days * 86400)

  # Adjust the start time to fit an entire day for intervals >= 1 day
  requestContext = requestContext.copy()
  s = requestContext['startTime']
  if interval >= DAY:
    requestContext['startTime'] = datetime(s.year, s.month, s.day)
  elif interval >= HOUR:
    requestContext['startTime'] = datetime(s.year, s.month, s.day, s.hour)
  elif interval >= MINUTE:
    requestContext['startTime'] = datetime(s.year, s.month, s.day, s.hour, s.minute)

  for i,series in enumerate(seriesList):
    # XXX: breaks with summarize(metric.{a,b})
    #      each series.pathExpression == metric.{a,b}
    newSeries = evaluateTarget(requestContext, series.pathExpression)[0]
    series[0:len(series)] = newSeries
    series.start = newSeries.start
    series.end = newSeries.end
    series.step = newSeries.step

  for series in seriesList:
    buckets = {} # { timestamp: [values] }

    timestamps = range( int(series.start), int(series.end), int(series.step) )
    datapoints = zip(timestamps, series)

    # Populate buckets
    for (timestamp, value) in datapoints:
      bucketInterval = int((timestamp - series.start) / interval)

      if bucketInterval not in buckets:
        buckets[bucketInterval] = []

      if value is not None:
        buckets[bucketInterval].append(value)


    newValues = []
    for timestamp in range(series.start, series.end, interval):
      bucketInterval = int((timestamp - series.start) / interval)
      bucket = buckets.get(bucketInterval, [])

      if bucket:
        if func == 'avg':
          newValues.append( float(sum(bucket)) / float(len(bucket)) )
        elif func == 'last':
          newValues.append( bucket[len(bucket)-1] )
        elif func == 'max':
          newValues.append( max(bucket) )
        elif func == 'min':
          newValues.append( min(bucket) )
        else:
          newValues.append( sum(bucket) )
      else:
        newValues.append( None )

    newName = "smartSummarize(%s, \"%s\", \"%s\")" % (series.name, intervalString, func)
    alignedEnd = series.start + (bucketInterval * interval) + interval
    newSeries = TimeSeries(newName, series.start, alignedEnd, interval, newValues)
    newSeries.pathExpression = newName
    results.append(newSeries)

  return results


def summarize(requestContext, seriesList, intervalString, func='sum', alignToFrom=False):
  """
  Summarize the data into interval buckets of a certain size.

  By default, the contents of each interval bucket are summed together. This is
  useful for counters where each increment represents a discrete event and
  retrieving a "per X" value requires summing all the events in that interval.

  Specifying 'avg' instead will return the mean for each bucket, which can be more
  useful when the value is a gauge that represents a certain value in time.

  'max', 'min' or 'last' can also be specified.

  By default, buckets are caculated by rounding to the nearest interval. This
  works well for intervals smaller than a day. For example, 22:32 will end up
  in the bucket 22:00-23:00 when the interval=1hour.

  Passing alignToFrom=true will instead create buckets starting at the from
  time. In this case, the bucket for 22:32 depends on the from time. If
  from=6:30 then the 1hour bucket for 22:32 is 22:30-23:30.

  Example:

  .. code-block:: none

    &target=summarize(counter.errors, "1hour") # total errors per hour
    &target=summarize(nonNegativeDerivative(gauge.num_users), "1week") # new users per week
    &target=summarize(queue.size, "1hour", "avg") # average queue size per hour
    &target=summarize(queue.size, "1hour", "max") # maximum queue size during each hour
    &target=summarize(metric, "13week", "avg", true)&from=midnight+20100101 # 2010 Q1-4
  """
  results = []
  delta = parseTimeOffset(intervalString)
  interval = delta.seconds + (delta.days * 86400)

  for series in seriesList:
    buckets = {}

    timestamps = range( int(series.start), int(series.end), int(series.step) )
    datapoints = zip(timestamps, series)

    for (timestamp, value) in datapoints:
      if alignToFrom:
        bucketInterval = int((timestamp - series.start) / interval)
      else:
        bucketInterval = timestamp - (timestamp % interval)

      if bucketInterval not in buckets:
        buckets[bucketInterval] = []

      if value is not None:
        buckets[bucketInterval].append(value)

    if alignToFrom:
      newStart = series.start
      newEnd = series.end
    else:
      newStart = series.start - (series.start % interval)
      newEnd = series.end - (series.end % interval) + interval

    newValues = []
    for timestamp in range(newStart, newEnd, interval):
      if alignToFrom:
        newEnd = timestamp
        bucketInterval = int((timestamp - series.start) / interval)
      else:
        bucketInterval = timestamp - (timestamp % interval)

      bucket = buckets.get(bucketInterval, [])

      if bucket:
        if func == 'avg':
          newValues.append( float(sum(bucket)) / float(len(bucket)) )
        elif func == 'last':
          newValues.append( bucket[len(bucket)-1] )
        elif func == 'max':
          newValues.append( max(bucket) )
        elif func == 'min':
          newValues.append( min(bucket) )
        else:
          newValues.append( sum(bucket) )
      else:
        newValues.append( None )

    if alignToFrom:
      newEnd += interval

    newName = "summarize(%s, \"%s\", \"%s\"%s)" % (series.name, intervalString, func, alignToFrom and ", true" or "")
    newSeries = TimeSeries(newName, newStart, newEnd, interval, newValues)
    newSeries.pathExpression = newName
    results.append(newSeries)

  return results


def hitcount(requestContext, seriesList, intervalString, alignToInterval = False):
  """
  Estimate hit counts from a list of time series.

  This function assumes the values in each time series represent
  hits per second.  It calculates hits per some larger interval
  such as per day or per hour.  This function is like summarize(),
  except that it compensates automatically for different time scales
  (so that a similar graph results from using either fine-grained
  or coarse-grained records) and handles rarely-occurring events
  gracefully.
  """
  results = []
  delta = parseTimeOffset(intervalString)
  interval = int(delta.seconds + (delta.days * 86400))

  if alignToInterval:
    requestContext = requestContext.copy()
    s = requestContext['startTime']
    if interval >= DAY:
      requestContext['startTime'] = datetime(s.year, s.month, s.day)
    elif interval >= HOUR:
      requestContext['startTime'] = datetime(s.year, s.month, s.day, s.hour)
    elif interval >= MINUTE:
      requestContext['startTime'] = datetime(s.year, s.month, s.day, s.hour, s.minute)

    for i,series in enumerate(seriesList):
      newSeries = evaluateTarget(requestContext, series.pathExpression)[0]
      intervalCount = int((series.end - series.start) / interval)
      series[0:len(series)] = newSeries
      series.start = newSeries.start
      series.end =  newSeries.start + (intervalCount * interval) + interval
      series.step = newSeries.step

  for series in seriesList:
    length = len(series)
    step = int(series.step)
    bucket_count = int(math.ceil(float(series.end - series.start) / interval))
    buckets = [[] for _ in range(bucket_count)]
    newStart = int(series.end - bucket_count * interval)

    for i, value in enumerate(series):
      if value is None:
        continue

      start_time = int(series.start + i * step)
      start_bucket, start_mod = divmod(start_time - newStart, interval)
      end_time = start_time + step
      end_bucket, end_mod = divmod(end_time - newStart, interval)

      if end_bucket >= bucket_count:
        end_bucket = bucket_count - 1
        end_mod = interval

      if start_bucket == end_bucket:
        # All of the hits go to a single bucket.
        if start_bucket >= 0:
          buckets[start_bucket].append(value * (end_mod - start_mod))

      else:
        # Spread the hits among 2 or more buckets.
        if start_bucket >= 0:
          buckets[start_bucket].append(value * (interval - start_mod))
        hits_per_bucket = value * interval
        for j in range(start_bucket + 1, end_bucket):
          buckets[j].append(hits_per_bucket)
        if end_mod > 0:
          buckets[end_bucket].append(value * end_mod)

    newValues = []
    for bucket in buckets:
      if bucket:
        newValues.append( sum(bucket) )
      else:
        newValues.append(None)

    newName = 'hitcount(%s, "%s"%s)' % (series.name, intervalString, alignToInterval and ", true" or "")
    newSeries = TimeSeries(newName, newStart, series.end, interval, newValues)    
    newSeries.pathExpression = newName
    results.append(newSeries)

  return results


def timeFunction(requestContext, name):
  """
  Short Alias: time()

  Just returns the timestamp for each X value. T

  Example:

  .. code-block:: none

    &target=time("The.time.series")

  This would create a series named "The.time.series" that contains in Y the same
  value (in seconds) as X.

  """

  step = 60
  delta = timedelta(seconds=step)
  when = requestContext["startTime"]
  values = []

  while when < requestContext["endTime"]:
    values.append(time.mktime(when.timetuple()))
    when += delta

  return [TimeSeries(name,
            time.mktime(requestContext["startTime"].timetuple()),
            time.mktime(requestContext["endTime"].timetuple()),
            step, values)]


def sinFunction(requestContext, name, amplitude=1):
  """
  Short Alias: sin()

  Just returns the sine of the current time. The optional amplitude parameter
  changes the amplitude of the wave.

  Example:

  .. code-block:: none

    &target=sin("The.time.series", 2)

  This would create a series named "The.time.series" that contains sin(x)*2.
  """
  step = 60
  delta = timedelta(seconds=step)
  when = requestContext["startTime"]
  values = []

  while when < requestContext["endTime"]:
    values.append(math.sin(time.mktime(when.timetuple()))*amplitude)
    when += delta

  return [TimeSeries(name,
            time.mktime(requestContext["startTime"].timetuple()),
            time.mktime(requestContext["endTime"].timetuple()),
            step, values)]

def randomWalkFunction(requestContext, name):
  """
  Short Alias: randomWalk()

  Returns a random walk starting at 0. This is great for testing when there is
  no real data in whisper.

  Example:

  .. code-block:: none

    &target=randomWalk("The.time.series")

  This would create a series named "The.time.series" that contains points where
  x(t) == x(t-1)+random()-0.5, and x(0) == 0.
  """
  step = 60
  delta = timedelta(seconds=step)
  when = requestContext["startTime"]
  values = []
  current = 0
  while when < requestContext["endTime"]:
    values.append(current)
    current += random.random() - 0.5
    when += delta

  return [TimeSeries(name,
            time.mktime(requestContext["startTime"].timetuple()),
            time.mktime(requestContext["endTime"].timetuple()),
            step, values)]

def events(requestContext, *tags):
  """
  Returns the number of events at this point in time. Usable with
  drawAsInfinite.

  Example:

  .. code-block:: none

    &target=events("tag-one", "tag-two")
    &target=events("*")

  Returns all events tagged as "tag-one" and "tag-two" and the second one
  returns all events.
  """
  step = 60
  name = "events(" + ", ".join(tags) + ")"
  delta = timedelta(seconds=step)
  when = requestContext["startTime"]
  values = []
  current = 0
  if tags == ("*",):
    tags = None
  events = models.Event.find_events(requestContext["startTime"],
                                    requestContext["endTime"], tags=tags)
  eventsp = 0

  while when < requestContext["endTime"]:
    count = 0
    if events:
      while eventsp < len(events) and events[eventsp].when >= when \
          and events[eventsp].when < (when + delta):
        count += 1
        eventsp += 1

    values.append(count)
    when += delta

  return [TimeSeries(name,
            time.mktime(requestContext["startTime"].timetuple()),
            time.mktime(requestContext["endTime"].timetuple()),
            step, values)]

def pieAverage(requestContext, series):
  return safeDiv(safeSum(series),safeLen(series))

def pieMaximum(requestContext, series):
  return max(series)

def pieMinimum(requestContext, series):
  return min(series)

PieFunctions = {
  'average' : pieAverage,
  'maximum' : pieMaximum,
  'minimum' : pieMinimum,
}

SeriesFunctions = {
  # Combine functions
  'sumSeries' : sumSeries,
  'sum' : sumSeries,
  'diffSeries' : diffSeries,
  'divideSeries' : divideSeries,
  'multiplySeries' : multiplySeries,
  'averageSeries' : averageSeries,
  'avg' : averageSeries,
  'sumSeriesWithWildcards': sumSeriesWithWildcards,
  'averageSeriesWithWildcards': averageSeriesWithWildcards,
  'minSeries' : minSeries,
  'maxSeries' : maxSeries,
  'rangeOfSeries': rangeOfSeries,
  'percentileOfSeries': percentileOfSeries,

  # Transform functions
  'scale' : scale,
  'scaleToSeconds' : scaleToSeconds,
  'offset' : offset,
  'derivative' : derivative,
  'integral' : integral,
  'nonNegativeDerivative' : nonNegativeDerivative,
  'log' : logarithm,
  'timeShift': timeShift,
  'summarize' : summarize,
  'smartSummarize' : smartSummarize,
  'hitcount'  : hitcount,

  # Calculate functions
  'movingAverage' : movingAverage,
  'movingMedian' : movingMedian,
  'stdev' : stdev,
  'holtWintersForecast': holtWintersForecast,
  'holtWintersConfidenceBands': holtWintersConfidenceBands,
  'holtWintersConfidenceArea': holtWintersConfidenceArea,
  'holtWintersAberration': holtWintersAberration,
  'asPercent' : asPercent,
  'pct' : asPercent,

  # Series Filter functions
  'mostDeviant' : mostDeviant,
  'highestCurrent' : highestCurrent,
  'lowestCurrent' : lowestCurrent,
  'highestMax' : highestMax,
  'currentAbove' : currentAbove,
  'currentBelow' : currentBelow,
  'highestAverage' : highestAverage,
  'lowestAverage' : lowestAverage,
  'averageAbove' : averageAbove,
  'averageBelow' : averageBelow,
  'maximumAbove' : maximumAbove,
  'minimumAbove' : minimumAbove,
  'maximumBelow' : maximumBelow,
  'nPercentile' : nPercentile,
  'limit' : limit,
  'sortByMaxima' : sortByMaxima,
  'sortByMinima' : sortByMinima,

  # Data Filter functions
  'removeAbovePercentile' : removeAbovePercentile,
  'removeAboveValue' : removeAboveValue,
  'removeBelowPercentile' : removeAbovePercentile,
  'removeBelowValue' : removeBelowValue,

  # Special functions
  'legendValue' : legendValue,
  'alias' : alias,
  'aliasSub' : aliasSub,
  'aliasByNode' : aliasByNode,
  'aliasByMetric' : aliasByMetric,
  'cactiStyle' : cactiStyle,
  'color' : color,
  'alpha' : alpha,
  'cumulative' : cumulative,
  'keepLastValue' : keepLastValue,
  'drawAsInfinite' : drawAsInfinite,
  'secondYAxis': secondYAxis,
  'lineWidth' : lineWidth,
  'dashed' : dashed,
  'substr' : substr,
  'group' : group,
  'groupByNode' : groupByNode,
  'exclude' : exclude,
  'constantLine' : constantLine,
  'stacked' : stacked,
  'areaBetween' : areaBetween,
  'threshold' : threshold,
  'transformNull' : transformNull,

  # test functions
  'time': timeFunction,
  "sin": sinFunction,
  "randomWalk": randomWalkFunction,
  'timeFunction': timeFunction,
  "sinFunction": sinFunction,
  "randomWalkFunction": randomWalkFunction,

  #events
  'events': events,
}


#Avoid import circularity
from graphite.render.evaluator import evaluateTarget

########NEW FILE########
__FILENAME__ = functions_test
import unittest

from django.conf import settings
# This line has to occur before importing functions and datalib.
settings.configure(
    LOG_DIR='.',
    LOG_CACHE_PERFORMANCE='',
    LOG_RENDERING_PERFORMANCE='',
    LOG_METRIC_ACCESS='',
    DATA_DIRS='.',
    CLUSTER_SERVERS='',
    CARBONLINK_HOSTS='',
    CARBONLINK_TIMEOUT=0,
    REMOTE_STORE_RETRY_DELAY=60)

from graphite.render.datalib import TimeSeries
import graphite.render.functions as functions


class FunctionsTest(unittest.TestCase):

    def testHighestMax(self):
        config = [ 20, 50, 30, 40 ]
        seriesList = [range(max_val) for max_val in config]

        # Expect the test results to be returned in decending order
        expected = [
          [seriesList[1]],
          [seriesList[1], seriesList[3]],
          [seriesList[1], seriesList[3], seriesList[2]],
          [seriesList[1], seriesList[3], seriesList[2], seriesList[0]],  # Test where num_return == len(seriesList)
          [seriesList[1], seriesList[3], seriesList[2], seriesList[0]],  # Test where num_return > len(seriesList)
        ]
        num_return = 1
        for test in expected:
          results = functions.highestMax({}, seriesList, num_return)
          self.assertEquals(test, results)
          num_return += 1

    def testHighestMaxEmptySeriesList(self):
        # Test the function works properly with an empty seriesList provided.
        self.assertEquals([], functions.highestMax({}, [], 1))

    def percCount(self, series, perc):
      if perc:
        return int(len(series) * (perc / 100.0))
      else:
        return 0

    def testGetPercentile(self):
      seriesList = [
        ([15, 20, 35, 40, 50], 20),
        (range(100), 30),
        (range(200), 60),
        (range(300), 90),
        (range(1, 101), 31),
        (range(1, 201), 61),
        (range(1, 301), 91),
        (range(0, 102), 30),
        (range(1, 203), 61),
        (range(1, 303), 91),
      ]
      for index, conf in enumerate(seriesList):
        series, expected = conf
        sorted_series = sorted( series )
        result = functions._getPercentile(series, 30)
        self.assertEquals(expected, result, 'For series index <%s> the 30th percentile ordinal is not %d, but %d ' % (index, expected, result))

    def testNPercentile(self):
        seriesList = []
        config = [
            [15, 35, 20, 40, 50],
            range(1, 101),
            range(1, 201),
            range(1, 301),
            range(0, 100),
            range(0, 200),
            range(0, 300),
            [None, None, None] + range(0, 300),  # Ensure None values in list has no affect.
        ]

        for i, c in enumerate(config):
          seriesList.append( TimeSeries('Test(%d)' % i, 0, 0, 0, c) )

        def TestNPercentile(perc, expected):
          result =  functions.nPercentile({}, seriesList, perc)
          self.assertEquals(expected, result)

        TestNPercentile(30, [ [20], [31], [61], [91], [30], [60], [90], [90] ])
        TestNPercentile(90, [ [50], [91], [181], [271], [90], [180], [270], [270] ])
        TestNPercentile(95, [ [50], [96], [191], [286], [95], [190], [285], [285] ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = glyph
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import os, cairo, math, itertools, re
import StringIO
from datetime import datetime, timedelta
from urllib import unquote_plus
from ConfigParser import SafeConfigParser
from django.conf import settings
from graphite.render.datalib import TimeSeries
from graphite.util import json


try: # See if there is a system installation of pytz first
  import pytz
except ImportError: # Otherwise we fall back to Graphite's bundled version
  from graphite.thirdparty import pytz

INFINITY = float('inf')

colorAliases = {
  'black' : (0,0,0),
  'white' : (255,255,255),
  'blue' : (100,100,255),
  'green' : (0,200,0),
  'red' : (200,00,50),
  'yellow' : (255,255,0),
  'orange' : (255, 165, 0),
  'purple' : (200,100,255),
  'brown' : (150,100,50),
  'cyan' : (0,255,255),
  'aqua' : (0,150,150),
  'gray' : (175,175,175),
  'grey' : (175,175,175),
  'magenta' : (255,0,255),
  'pink' : (255,100,100),
  'gold' : (200,200,0),
  'rose' : (200,150,200),
  'darkblue' : (0,0,255),
  'darkgreen' : (0,255,0),
  'darkred' : (255,0,0),
  'darkgray' : (111,111,111),
  'darkgrey' : (111,111,111),
}

# This gets overriden by graphTemplates.conf
defaultGraphOptions = dict(
  background='black',
  foreground='white',
  majorline='white',
  minorline='grey',
  linecolors='blue,green,red,purple,brown,yellow,aqua,grey,magenta,pink,gold,rose',
  fontname='Sans',
  fontsize=10,
  fontbold='false',
  fontitalic='false',
)

#X-axis configurations (copied from rrdtool, this technique is evil & ugly but effective)
SEC = 1
MIN = 60
HOUR = MIN * 60
DAY = HOUR * 24
WEEK = DAY * 7
MONTH = DAY * 31
YEAR = DAY * 365
xAxisConfigs = (
  dict(seconds=0.00,  minorGridUnit=SEC,  minorGridStep=5,  majorGridUnit=MIN,  majorGridStep=1,  labelUnit=SEC,  labelStep=5,  format="%H:%M:%S", maxInterval=10*MIN),
  dict(seconds=0.07,  minorGridUnit=SEC,  minorGridStep=10, majorGridUnit=MIN,  majorGridStep=1,  labelUnit=SEC,  labelStep=10, format="%H:%M:%S", maxInterval=20*MIN),
  dict(seconds=0.14,  minorGridUnit=SEC,  minorGridStep=15, majorGridUnit=MIN,  majorGridStep=1,  labelUnit=SEC,  labelStep=15, format="%H:%M:%S", maxInterval=30*MIN),
  dict(seconds=0.27,  minorGridUnit=SEC,  minorGridStep=30, majorGridUnit=MIN,  majorGridStep=2,  labelUnit=MIN,  labelStep=1,  format="%H:%M", maxInterval=2*HOUR),
  dict(seconds=0.5,   minorGridUnit=MIN,  minorGridStep=1,  majorGridUnit=MIN,  majorGridStep=2,  labelUnit=MIN,  labelStep=1,  format="%H:%M", maxInterval=2*HOUR),
  dict(seconds=1.2,   minorGridUnit=MIN,  minorGridStep=1,  majorGridUnit=MIN,  majorGridStep=4,  labelUnit=MIN,  labelStep=2,  format="%H:%M", maxInterval=3*HOUR),
  dict(seconds=2,     minorGridUnit=MIN,  minorGridStep=1,  majorGridUnit=MIN,  majorGridStep=10, labelUnit=MIN,  labelStep=5,  format="%H:%M", maxInterval=6*HOUR),
  dict(seconds=5,     minorGridUnit=MIN,  minorGridStep=2,  majorGridUnit=MIN,  majorGridStep=10, labelUnit=MIN,  labelStep=10, format="%H:%M", maxInterval=12*HOUR),
  dict(seconds=10,    minorGridUnit=MIN,  minorGridStep=5,  majorGridUnit=MIN,  majorGridStep=20, labelUnit=MIN,  labelStep=20, format="%H:%M", maxInterval=1*DAY),
  dict(seconds=30,    minorGridUnit=MIN,  minorGridStep=10, majorGridUnit=HOUR, majorGridStep=1,  labelUnit=HOUR, labelStep=1,  format="%H:%M", maxInterval=2*DAY),
  dict(seconds=60,    minorGridUnit=MIN,  minorGridStep=30, majorGridUnit=HOUR, majorGridStep=2,  labelUnit=HOUR, labelStep=2,  format="%H:%M", maxInterval=2*DAY),
  dict(seconds=100,   minorGridUnit=HOUR, minorGridStep=2,  majorGridUnit=HOUR, majorGridStep=4,  labelUnit=HOUR, labelStep=4,  format="%a %l%p", maxInterval=6*DAY),
  dict(seconds=255,   minorGridUnit=HOUR, minorGridStep=6,  majorGridUnit=HOUR, majorGridStep=12, labelUnit=HOUR, labelStep=12, format="%m/%d %l%p"),
  dict(seconds=600,   minorGridUnit=HOUR, minorGridStep=6,  majorGridUnit=DAY,  majorGridStep=1,  labelUnit=DAY,  labelStep=1,  format="%m/%d", maxInterval=14*DAY),
  dict(seconds=600,   minorGridUnit=HOUR, minorGridStep=12, majorGridUnit=DAY,  majorGridStep=1,  labelUnit=DAY,  labelStep=1,  format="%m/%d", maxInterval=365*DAY),
  dict(seconds=2000,  minorGridUnit=DAY,  minorGridStep=1,  majorGridUnit=DAY,  majorGridStep=2,  labelUnit=DAY,  labelStep=2,  format="%m/%d", maxInterval=365*DAY),
  dict(seconds=4000,  minorGridUnit=DAY,  minorGridStep=2,  majorGridUnit=DAY,  majorGridStep=4,  labelUnit=DAY,  labelStep=4,  format="%m/%d", maxInterval=365*DAY),
  dict(seconds=8000,  minorGridUnit=DAY,  minorGridStep=3.5,majorGridUnit=DAY,  majorGridStep=7,  labelUnit=DAY,  labelStep=7,  format="%m/%d", maxInterval=365*DAY),
  dict(seconds=16000, minorGridUnit=DAY,  minorGridStep=7,  majorGridUnit=DAY,  majorGridStep=14, labelUnit=DAY,  labelStep=14, format="%m/%d", maxInterval=365*DAY),
  dict(seconds=32000, minorGridUnit=DAY,  minorGridStep=15, majorGridUnit=DAY,  majorGridStep=30, labelUnit=DAY,  labelStep=30, format="%m/%d", maxInterval=365*DAY),
  dict(seconds=64000, minorGridUnit=DAY,  minorGridStep=30, majorGridUnit=DAY,  majorGridStep=60, labelUnit=DAY,  labelStep=60, format="%m/%d %Y"),
)

UnitSystems = {
  'binary': (
    ('Pi', 1024.0**5),
    ('Ti', 1024.0**4),
    ('Gi', 1024.0**3),
    ('Mi', 1024.0**2),
    ('Ki', 1024.0   )),
  'si': (
    ('P', 1000.0**5),
    ('T', 1000.0**4),
    ('G', 1000.0**3),
    ('M', 1000.0**2),
    ('K', 1000.0   )),
  'none' : [],
}


class GraphError(Exception):
  pass


class Graph:
  customizable = ('width','height','margin','bgcolor','fgcolor', \
                 'fontName','fontSize','fontBold','fontItalic', \
                 'colorList','template','yAxisSide','outputFormat')

  def __init__(self,**params):
    self.params = params
    self.data = params['data']
    self.dataLeft = []
    self.dataRight = []
    self.secondYAxis = False
    self.width = int( params.get('width',200) )
    self.height = int( params.get('height',200) )
    self.margin = int( params.get('margin',10) )
    self.userTimeZone = params.get('tz')
    self.logBase = params.get('logBase', None)
    self.minorY = int(params.get('minorY', 1))
    if self.logBase:
      if self.logBase == 'e':
        self.logBase = math.e
      elif self.logBase <= 0:
        self.logBase = None
        params['logBase'] = None
      else:
        self.logBase = float(self.logBase)

    if self.margin < 0:
      self.margin = 10

    self.area = {
      'xmin' : self.margin + 10, # Need extra room when the time is near the left edge
      'xmax' : self.width - self.margin,
      'ymin' : self.margin,
      'ymax' : self.height - self.margin,
    }

    self.loadTemplate( params.get('template','default') )

    self.setupCairo( params.get('outputFormat','png').lower() )

    opts = self.ctx.get_font_options()
    opts.set_antialias( cairo.ANTIALIAS_NONE )
    self.ctx.set_font_options( opts )

    self.foregroundColor = params.get('fgcolor',self.defaultForeground)
    self.backgroundColor = params.get('bgcolor',self.defaultBackground)
    self.setColor( self.backgroundColor )
    self.drawRectangle( 0, 0, self.width, self.height )

    if 'colorList' in params:
      colorList = unquote_plus( params['colorList'] ).split(',')
    else:
      colorList = self.defaultColorList
    self.colors = itertools.cycle( colorList )

    self.drawGraph(**params)

  def setupCairo(self,outputFormat='png'):
    self.outputFormat = outputFormat
    if outputFormat == 'png':
      self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
    else:
      self.surfaceData = StringIO.StringIO()
      self.surface = cairo.SVGSurface(self.surfaceData, self.width, self.height)
    self.ctx = cairo.Context(self.surface)

  def setColor(self, value, alpha=1.0, forceAlpha=False):
    if type(value) is tuple and len(value) == 3:
      r,g,b = value
    elif value in colorAliases:
      r,g,b = colorAliases[value]
    elif type(value) in (str,unicode) and len(value) >= 6:
      s = value
      if s[0] == '#': s = s[1:]
      r,g,b = ( int(s[0:2],base=16), int(s[2:4],base=16), int(s[4:6],base=16) )
      if len(s) == 8 and not forceAlpha:
        alpha = float( int(s[6:8],base=16) ) / 255.0
    else:
      raise ValueError, "Must specify an RGB 3-tuple, an html color string, or a known color alias!"
    r,g,b = [float(c) / 255.0 for c in (r,g,b)]
    self.ctx.set_source_rgba(r,g,b,alpha)

  def setFont(self, **params):
    p = self.defaultFontParams.copy()
    p.update(params)
    self.ctx.select_font_face(p['name'], p['italic'], p['bold'])
    self.ctx.set_font_size( float(p['size']) )

  def getExtents(self,text=None,fontOptions={}):
    if fontOptions:
      self.setFont(**fontOptions)
    F = self.ctx.font_extents()
    extents = { 'maxHeight' : F[2], 'maxAscent' : F[0], 'maxDescent' : F[1] }
    if text:
      T = self.ctx.text_extents(text)
      extents['width'] = T[4]
      extents['height'] = T[3]
    return extents

  def drawRectangle(self, x, y, w, h, fill=True, dash=False):
    if not fill:
      o = self.ctx.get_line_width() / 2.0 #offset for borders so they are drawn as lines would be
      x += o
      y += o
      w -= o
      h -= o
    self.ctx.rectangle(x,y,w,h)
    if fill:
      self.ctx.fill()
    else:
      if dash:
        self.ctx.set_dash(dash,1)
      else:
        self.ctx.set_dash([],0)
      self.ctx.stroke()

  def drawText(self,text,x,y,font={},color={},align='left',valign='top',border=False,rotate=0):
    if font: self.setFont(**font)
    if color: self.setColor(**color)
    extents = self.getExtents(text)
    angle = math.radians(rotate)
    origMatrix = self.ctx.get_matrix()

    horizontal = {
      'left' : 0,
      'center' : extents['width'] / 2,
      'right' : extents['width'],
    }[align.lower()]
    vertical = {
      'top' : extents['maxAscent'],
      'middle' : extents['maxHeight'] / 2 - extents['maxDescent'],
      'bottom' : -extents['maxDescent'],
      'baseline' : 0,
    }[valign.lower()]

    self.ctx.move_to(x,y)
    self.ctx.rel_move_to( math.sin(angle) * -vertical, math.cos(angle) * vertical)
    self.ctx.rotate(angle)
    self.ctx.rel_move_to( -horizontal, 0 )
    bx, by = self.ctx.get_current_point()
    by -= extents['maxAscent']
    self.ctx.text_path(text)
    self.ctx.fill()
    if border:
      self.drawRectangle(bx, by, extents['width'], extents['maxHeight'], fill=False)
    else:
      self.ctx.set_matrix(origMatrix)

  def drawTitle(self,text):
    self.encodeHeader('title')

    y = self.area['ymin']
    x = self.width / 2
    lineHeight = self.getExtents()['maxHeight']
    for line in text.split('\n'):
      self.drawText(line, x, y, align='center')
      y += lineHeight
    if self.params.get('yAxisSide') == 'right':
      self.area['ymin'] = y
    else:
      self.area['ymin'] = y + self.margin


  def drawLegend(self, elements, unique=False): #elements is [ (name,color,rightSide), (name,color,rightSide), ... ]
    self.encodeHeader('legend')

    if unique:
      # remove duplicate names
      namesSeen = []
      newElements = []
      for e in elements:
        if e[0] not in namesSeen:
          namesSeen.append(e[0])
          newElements.append(e)
      elements = newElements

    # Check if there's enough room to use two columns.
    rightSideLabels = False
    padding = 5
    longestName = sorted([e[0] for e in elements],key=len)[-1]
    testSizeName = longestName + " " + longestName # Double it to check if there's enough room for 2 columns
    testExt = self.getExtents(testSizeName)
    testBoxSize = testExt['maxHeight'] - 1
    testWidth = testExt['width'] + 2 * (testBoxSize + padding)
    if testWidth + 50 < self.width:
      rightSideLabels = True
    
    if(self.secondYAxis and rightSideLabels):
      extents = self.getExtents(longestName)
      padding = 5
      boxSize = extents['maxHeight'] - 1
      lineHeight = extents['maxHeight'] + 1
      labelWidth = extents['width'] + 2 * (boxSize + padding)
      columns = max(1, math.floor( (self.width - self.area['xmin']) / labelWidth ))
      numRight = len([name for (name,color,rightSide) in elements if rightSide])
      numberOfLines = max(len(elements) - numRight, numRight)
      columns = math.floor(columns / 2.0) 
      if columns < 1: columns = 1
      legendHeight = numberOfLines * (lineHeight + padding)
      self.area['ymax'] -= legendHeight #scoot the drawing area up to fit the legend
      self.ctx.set_line_width(1.0)
      x = self.area['xmin']
      y = self.area['ymax'] + (2 * padding)
      n = 0
      xRight = self.area['xmax'] - self.area['xmin']
      yRight = y
      nRight = 0
      for (name,color,rightSide) in elements:
        self.setColor( color )
        if rightSide:
          nRight += 1 
          self.drawRectangle(xRight - padding,yRight,boxSize,boxSize)
          self.setColor( 'darkgrey' )
          self.drawRectangle(xRight - padding,yRight,boxSize,boxSize,fill=False)
          self.setColor( self.foregroundColor )
          self.drawText(name, xRight - boxSize, yRight, align='right')
          xRight -= labelWidth
          if nRight % columns == 0:
            xRight = self.area['xmax'] - self.area['xmin']
            yRight += lineHeight
        else:
          n += 1 
          self.drawRectangle(x,y,boxSize,boxSize)
          self.setColor( 'darkgrey' )
          self.drawRectangle(x,y,boxSize,boxSize,fill=False)
          self.setColor( self.foregroundColor )
          self.drawText(name, x + boxSize + padding, y, align='left')
          x += labelWidth
          if n % columns == 0:
            x = self.area['xmin']
            y += lineHeight
    else:
      extents = self.getExtents(longestName)
      boxSize = extents['maxHeight'] - 1
      lineHeight = extents['maxHeight'] + 1
      labelWidth = extents['width'] + 2 * (boxSize + padding)
      columns = math.floor( self.width / labelWidth )
      if columns < 1: columns = 1
      numberOfLines = math.ceil( float(len(elements)) / columns )
      legendHeight = numberOfLines * (lineHeight + padding)
      self.area['ymax'] -= legendHeight #scoot the drawing area up to fit the legend
      self.ctx.set_line_width(1.0)
      x = self.area['xmin']
      y = self.area['ymax'] + (2 * padding)
      for i,(name,color,rightSide) in enumerate(elements):
        if rightSide:
          self.setColor( color )
          self.drawRectangle(x + labelWidth + padding,y,boxSize,boxSize)
          self.setColor( 'darkgrey' )
          self.drawRectangle(x + labelWidth + padding,y,boxSize,boxSize,fill=False)
          self.setColor( self.foregroundColor )
          self.drawText(name, x + labelWidth, y, align='right')
          x += labelWidth
        else:
          self.setColor( color )
          self.drawRectangle(x,y,boxSize,boxSize)
          self.setColor( 'darkgrey' )
          self.drawRectangle(x,y,boxSize,boxSize,fill=False)
          self.setColor( self.foregroundColor )
          self.drawText(name, x + boxSize + padding, y, align='left')
          x += labelWidth
        if (i + 1) % columns == 0:
          x = self.area['xmin']
          y += lineHeight

  def encodeHeader(self,text):
    self.ctx.save()
    self.setColor( self.backgroundColor )
    self.ctx.move_to(-88,-88) # identifier
    for i, char in enumerate(text):
      self.ctx.line_to(-ord(char), -i-1)
    self.ctx.stroke()
    self.ctx.restore()

  def loadTemplate(self,template):
    conf = SafeConfigParser()
    if conf.read(settings.GRAPHTEMPLATES_CONF):
      defaults = dict( conf.items('default') )
      if template in conf.sections():
        opts = dict( conf.items(template) )
      else:
        opts = defaults
    else:
      opts = defaults = defaultGraphOptions

    self.defaultBackground = opts.get('background', defaults['background'])
    self.defaultForeground = opts.get('foreground', defaults['foreground'])
    self.defaultMajorGridLineColor = opts.get('majorline', defaults['majorline'])
    self.defaultMinorGridLineColor = opts.get('minorline', defaults['minorline'])
    self.defaultColorList = [c.strip() for c in opts.get('linecolors', defaults['linecolors']).split(',')]
    fontName = opts.get('fontname', defaults['fontname'])
    fontSize = float( opts.get('fontsize', defaults['fontsize']) )
    fontBold = opts.get('fontbold', defaults['fontbold']).lower() == 'true'
    fontItalic = opts.get('fontitalic', defaults['fontitalic']).lower() == 'true'
    self.defaultFontParams = {
      'name' : self.params.get('fontName',fontName),
      'size' : int( self.params.get('fontSize',fontSize) ),
      'bold' : self.params.get('fontBold',fontBold),
      'italic' : self.params.get('fontItalic',fontItalic),
    }

  def output(self, fileObj):
    if self.outputFormat == 'png':
      self.surface.write_to_png(fileObj)
    else:
      metaData = {
        'x': {
          'start': self.startTime,
          'end': self.endTime
        },
        'y': {
          'top': self.yTop,
          'bottom': self.yBottom,
          'step': self.yStep,
          'labels': self.yLabels,
          'labelValues': self.yLabelValues
        },
        'options': {
          'lineWidth': self.lineWidth
        },
        'font': self.defaultFontParams,
        'area': self.area,
        'series': []
      }

      for series in self.data:
        if 'stacked' not in series.options:
          metaData['series'].append({
            'name': series.name,
            'start': series.start,
            'end': series.end,
            'step': series.step,
            'valuesPerPoint': series.valuesPerPoint,
            'color': series.color,
            'data': series,
            'options': series.options
          })

      self.surface.finish()
      svgData = self.surfaceData.getvalue()
      self.surfaceData.close()

      svgData = svgData.replace('pt"', 'px"', 2) # we expect height/width in pixels, not points
      svgData = svgData.replace('</svg>\n', '', 1)
      svgData = svgData.replace('</defs>\n<g', '</defs>\n<g class="graphite"', 1)

      # We encode headers using special paths with d^="M -88 -88"
      # Find these, and turn them into <g> wrappers instead
      def onHeaderPath(match):
        name = ''
        for char in re.findall(r'L -(\d+) -\d+', match.group(1)):
          name += chr(int(char))
        return '</g><g data-header="true" class="%s">' % name
      svgData = re.sub(r'<path.+?d="M -88 -88 (.+?)"/>', onHeaderPath, svgData)

      # Replace the first </g><g> with <g>, and close out the last </g> at the end
      svgData = svgData.replace('</g><g data-header','<g data-header',1) + "</g>"
      svgData = svgData.replace(' data-header="true"','')

      fileObj.write(svgData)
      fileObj.write("""<script>
  <![CDATA[
    metadata = %s
  ]]>
</script>
</svg>""" % json.dumps(metaData))


class LineGraph(Graph):
  customizable = Graph.customizable + \
                 ('title','vtitle','lineMode','lineWidth','hideLegend', \
                  'hideAxes','minXStep','hideGrid','majorGridLineColor', \
                  'minorGridLineColor','thickness','min','max', \
                  'graphOnly','yMin','yMax','yLimit','yStep','areaMode', \
                  'areaAlpha','drawNullAsZero','tz', 'yAxisSide','pieMode', \
                  'yUnitSystem', 'logBase','yMinLeft','yMinRight','yMaxLeft', \
                  'yMaxRight', 'yLimitLeft', 'yLimitRight', 'yStepLeft', \
                  'yStepRight', 'rightWidth', 'rightColor', 'rightDashed', \
                  'leftWidth', 'leftColor', 'leftDashed', 'xFormat', 'minorY', \
                  'hideYAxis', 'uniqueLegend')
  validLineModes = ('staircase','slope','connected')
  validAreaModes = ('none','first','all','stacked')
  validPieModes = ('maximum', 'minimum', 'average')

  def drawGraph(self,**params):
    # Make sure we've got datapoints to draw
    if self.data:
      startTime = min([series.start for series in self.data])
      endTime = max([series.end for series in self.data])
      timeRange = endTime - startTime
    else:
      timeRange = None

    if not timeRange:
      x = self.width / 2
      y = self.height / 2
      self.setColor('red')
      self.setFont(size=math.log(self.width * self.height) )
      self.drawText("No Data", x, y, align='center')
      return

    # Determine if we're doing a 2 y-axis graph.
    for series in self.data:
      if 'secondYAxis' in series.options:
        self.dataRight.append(series)
      else:
        self.dataLeft.append(series)
    if len(self.dataRight) > 0:
      self.secondYAxis = True

    #API compatibilty hacks
    if params.get('graphOnly',False):
      params['hideLegend'] = True
      params['hideGrid'] = True
      params['hideAxes'] = True
      params['hideYAxis'] = False
      params['yAxisSide'] = 'left'
      params['title'] = ''
      params['vtitle'] = ''
      params['margin'] = 0
      params['tz'] = ''
      self.margin = 0
      self.area['xmin'] = 0
      self.area['xmax'] = self.width
      self.area['ymin'] = 0
      self.area['ymax'] = self.height
    if 'yMin' not in params and 'min' in params:
      params['yMin'] = params['min']
    if 'yMax' not in params and 'max' in params:
      params['yMax'] = params['max']
    if 'lineWidth' not in params and 'thickness' in params:
      params['lineWidth'] = params['thickness']
    if 'yAxisSide' not in params:
      params['yAxisSide'] = 'left'
    if 'yUnitSystem' not in params:
      params['yUnitSystem'] = 'si'
    else:
      params['yUnitSystem'] = str(params['yUnitSystem']).lower()
      if params['yUnitSystem'] not in UnitSystems.keys():
        params['yUnitSystem'] = 'si'

    self.params = params
    
    # Don't do any of the special right y-axis stuff if we're drawing 2 y-axes.
    if self.secondYAxis:
      params['yAxisSide'] = 'left'
    
    # When Y Axis is labeled on the right, we subtract x-axis positions from the max,
    # instead of adding to the minimum
    if self.params.get('yAxisSide') == 'right':
      self.margin = self.width
    #Now to setup our LineGraph specific options
    self.lineWidth = float( params.get('lineWidth', 1.2) )
    self.lineMode = params.get('lineMode','slope').lower()
    assert self.lineMode in self.validLineModes, "Invalid line mode!"
    self.areaMode = params.get('areaMode','none').lower()
    assert self.areaMode in self.validAreaModes, "Invalid area mode!"
    self.pieMode = params.get('pieMode', 'maximum').lower()
    assert self.pieMode in self.validPieModes, "Invalid pie mode!"

    # Line mode slope does not work (or even make sense) for series that have
    # only one datapoint. So if any series have one datapoint we force staircase mode.
    if self.lineMode == 'slope':
      for series in self.data:
        if len(series) == 1:
          self.lineMode = 'staircase'
          break

    if self.secondYAxis:
      for series in self.data:
        if 'secondYAxis' in series.options:
          if 'rightWidth' in params:
            series.options['lineWidth'] = params['rightWidth']
          if 'rightDashed' in params:
            series.options['dashed'] = params['rightDashed']
          if 'rightColor' in params:
            series.color = params['rightColor']
        else:
          if 'leftWidth' in params:
            series.options['lineWidth'] = params['leftWidth']
          if 'leftDashed' in params:
            series.options['dashed'] = params['leftDashed']
          if 'leftColor' in params:
            series.color = params['leftColor']
    
    for series in self.data:
      if not hasattr(series, 'color'):
        series.color = self.colors.next()

    titleSize = self.defaultFontParams['size'] + math.floor( math.log(self.defaultFontParams['size']) )
    self.setFont( size=titleSize )
    self.setColor( self.foregroundColor )

    if params.get('title'):
      self.drawTitle( str(params['title']) )
    if params.get('vtitle'):
      self.drawVTitle( str(params['vtitle']) )
    self.setFont()

    if not params.get('hideLegend', len(self.data) > settings.LEGEND_MAX_ITEMS):
      elements = [ (series.name,series.color,series.options.get('secondYAxis')) for series in self.data if series.name ]
      self.drawLegend(elements, params.get('uniqueLegend', False))

    #Setup axes, labels, and grid
    #First we adjust the drawing area size to fit X-axis labels
    if not self.params.get('hideAxes',False):
      self.area['ymax'] -= self.getExtents()['maxAscent'] * 2

    #Now we consolidate our data points to fit in the currently estimated drawing area
    self.consolidateDataPoints()

    self.encodeHeader('axes')

    #Now its time to fully configure the Y-axis and determine the space required for Y-axis labels
    #Since we'll probably have to squeeze the drawing area to fit the Y labels, we may need to
    #reconsolidate our data points, which in turn means re-scaling the Y axis, this process will
    #repeat until we have accurate Y labels and enough space to fit our data points
    currentXMin = self.area['xmin']
    currentXMax = self.area['xmax']
    if self.secondYAxis:
      self.setupTwoYAxes()
    else:
      self.setupYAxis()
    while currentXMin != self.area['xmin'] or currentXMax != self.area['xmax']: #see if the Y-labels require more space
      self.consolidateDataPoints() #this can cause the Y values to change
      currentXMin = self.area['xmin'] #so let's keep track of the previous Y-label space requirements
      currentXMax = self.area['xmax']
      if self.secondYAxis: #and recalculate their new requirements 
        self.setupTwoYAxes()
      else:
        self.setupYAxis()

    #Now that our Y-axis is finalized, let's determine our X labels (this won't affect the drawing area)
    self.setupXAxis()

    if not self.params.get('hideAxes',False):
      self.drawLabels()
      if not self.params.get('hideGrid',False): #hideAxes implies hideGrid
        self.encodeHeader('grid')
        self.drawGridLines()

    #Finally, draw the graph lines
    self.encodeHeader('lines')
    self.drawLines()

  def drawVTitle(self,text):
    self.encodeHeader('vtitle')

    lineHeight = self.getExtents()['maxHeight']
    x = self.area['xmin'] + lineHeight
    y = self.height / 2
    for line in text.split('\n'):
      self.drawText(line, x, y, align='center', valign='baseline', rotate=270)
      x += lineHeight
    self.area['xmin'] = x + self.margin + lineHeight

  def getYCoord(self, value, side=None):
    if "left" == side:
      yLabelValues = self.yLabelValuesL
      yTop = self.yTopL
      yBottom = self.yBottomL
    elif "right" == side:
      yLabelValues = self.yLabelValuesR
      yTop = self.yTopR
      yBottom = self.yBottomR
    else:
      yLabelValues = self.yLabelValues
      yTop = self.yTop
      yBottom = self.yBottom

    try:
      highestValue = max(yLabelValues)
      lowestValue = min(yLabelValues)
    except ValueError:
      highestValue = yTop
      lowestValue = yBottom

    pixelRange = self.area['ymax'] - self.area['ymin']

    relativeValue = value - lowestValue
    valueRange = highestValue - lowestValue

    if self.logBase:
        if value <= 0:
            return None
        relativeValue = math.log(value, self.logBase) - math.log(lowestValue, self.logBase)
        valueRange = math.log(highestValue, self.logBase) - math.log(lowestValue, self.logBase)

    pixelToValueRatio = pixelRange / valueRange
    valueInPixels = pixelToValueRatio * relativeValue
    return self.area['ymax'] - valueInPixels


  def drawLines(self, width=None, dash=None, linecap='butt', linejoin='miter'):
    if not width: width = self.lineWidth
    self.ctx.set_line_width(width)
    originalWidth = width
    width = float(int(width) % 2) / 2
    if dash:
      self.ctx.set_dash(dash,1)
    else:
      self.ctx.set_dash([],0)
    self.ctx.set_line_cap({
      'butt' : cairo.LINE_CAP_BUTT,
      'round' : cairo.LINE_CAP_ROUND,
      'square' : cairo.LINE_CAP_SQUARE,
    }[linecap])
    self.ctx.set_line_join({
      'miter' : cairo.LINE_JOIN_MITER,
      'round' : cairo.LINE_JOIN_ROUND,
      'bevel' : cairo.LINE_JOIN_BEVEL,
    }[linejoin])

    # stack the values
    if self.areaMode == 'stacked' and not self.secondYAxis: #TODO Allow stacked area mode with secondYAxis
      total = []
      for series in self.data:
        for i in range(len(series)):
          if len(total) <= i: total.append(0)

          if series[i] is not None:
            original = series[i]
            series[i] += total[i]
            total[i] += original

    # check whether there is an stacked metric
    singleStacked = False
    for series in self.data:
      if 'stacked' in series.options:
        singleStacked = True
    if singleStacked:
      self.data = sort_stacked(self.data)

    # apply stacked setting on series based on areaMode
    if self.areaMode == 'first':
      self.data[0].options['stacked'] = True
    elif self.areaMode != 'none':
      for series in self.data:
        series.options['stacked'] = True

    # apply alpha channel and create separate stroke series
    if self.params.get('areaAlpha'):
      try:
        alpha = float(self.params['areaAlpha'])
      except ValueError:
        alpha = 0.5
        pass

      strokeSeries = []
      for series in self.data:
        if 'stacked' in series.options:
          series.options['alpha'] = alpha

          newSeries = TimeSeries(series.name, series.start, series.end, series.step*series.valuesPerPoint, [x for x in series])
          newSeries.xStep = series.xStep
          newSeries.color = series.color
          if 'secondYAxis' in series.options:
            newSeries.options['secondYAxis'] = True
          strokeSeries.append(newSeries)
      self.data += strokeSeries

    # setup the clip region
    self.ctx.set_line_width(1.0)
    self.ctx.rectangle(self.area['xmin'], self.area['ymin'], self.area['xmax'] - self.area['xmin'], self.area['ymax'] - self.area['ymin'])
    self.ctx.clip()
    self.ctx.set_line_width(originalWidth)

    # save clip to restore once stacked areas are drawn
    self.ctx.save()
    clipRestored = False

    for series in self.data:

      if 'stacked' not in series.options:
        # stacked areas are always drawn first. if this series is not stacked, we finished stacking.
        # reset the clip region so lines can show up on top of the stacked areas.
        if not clipRestored:
          clipRestored = True
          self.ctx.restore()

      if 'lineWidth' in series.options:
        self.ctx.set_line_width(series.options['lineWidth'])

      if 'dashed' in series.options:
        self.ctx.set_dash([ series.options['dashed'] ], 1)
      else:
        self.ctx.set_dash([], 0)

      x = float(self.area['xmin']) + (self.lineWidth / 2.0)
      y = float(self.area['ymin'])

      startX = x

      if series.options.get('invisible'):
        self.setColor( series.color, 0, True )
      else:
        self.setColor( series.color, series.options.get('alpha') or 1.0 )

      fromNone = True

      for value in series:
        if value != value: # convert NaN to None
          value = None

        if value is None and self.params.get('drawNullAsZero'):
          value = 0.0

        if value is None:
          if not fromNone:
            self.ctx.line_to(x, y)
            if 'stacked' in series.options: #Close off and fill area before unknown interval
              self.fillAreaAndClip(x, y, startX)

          x += series.xStep
          fromNone = True

        else:
          if self.secondYAxis:
            if 'secondYAxis' in series.options:
              y = self.getYCoord(value, "right")
            else:
              y = self.getYCoord(value, "left")
          else:
            y = self.getYCoord(value)

          if y is None:
            value = None
          elif y < 0:
              y = 0

          if 'drawAsInfinite' in series.options and value > 0:
            self.ctx.move_to(x, self.area['ymax'])
            self.ctx.line_to(x, self.area['ymin'])
            self.ctx.stroke()
            x += series.xStep
            continue

          if fromNone:
            startX = x

          if self.lineMode == 'staircase':
            if fromNone:
              self.ctx.move_to(x, y)
            else:
              self.ctx.line_to(x, y)

            x += series.xStep
            self.ctx.line_to(x, y)

          elif self.lineMode == 'slope':
            if fromNone:
              self.ctx.move_to(x, y)

            self.ctx.line_to(x, y)
            x += series.xStep

          elif self.lineMode == 'connected':
            self.ctx.line_to(x, y)
            x += series.xStep

          fromNone = False

      if 'stacked' in series.options:
        self.fillAreaAndClip(x-series.xStep, y, startX)
      else:
        self.ctx.stroke()

      self.ctx.set_line_width(originalWidth) # return to the original line width
      if 'dash' in series.options: # if we changed the dash setting before, change it back now
        if dash:
          self.ctx.set_dash(dash,1)
        else:
          self.ctx.set_dash([],0)

  def fillAreaAndClip(self, x, y, startX=None):
    startX = (startX or self.area['xmin'])
    pattern = self.ctx.copy_path()

    self.ctx.line_to(x, self.area['ymax'])                  # bottom endX
    self.ctx.line_to(startX, self.area['ymax'])             # bottom startX
    self.ctx.close_path()
    self.ctx.fill()

    self.ctx.append_path(pattern)
    self.ctx.line_to(x, self.area['ymax'])                  # bottom endX
    self.ctx.line_to(self.area['xmax'], self.area['ymax'])  # bottom right
    self.ctx.line_to(self.area['xmax'], self.area['ymin'])  # top right
    self.ctx.line_to(self.area['xmin'], self.area['ymin'])  # top left
    self.ctx.line_to(self.area['xmin'], self.area['ymax'])  # bottom left
    self.ctx.line_to(startX, self.area['ymax'])             # bottom startX
    self.ctx.close_path()
    self.ctx.clip()

  def consolidateDataPoints(self):
    numberOfPixels = self.graphWidth = self.area['xmax'] - self.area['xmin'] - (self.lineWidth + 1)
    for series in self.data:
      numberOfDataPoints = len(series)
      minXStep = float( self.params.get('minXStep',1.0) )
      if self.lineMode == 'staircase':
        divisor = numberOfDataPoints
      else:
        divisor = ((numberOfDataPoints - 1) or 1)
      bestXStep = numberOfPixels / divisor
      if bestXStep < minXStep:
        drawableDataPoints = int( numberOfPixels / minXStep )
        pointsPerPixel = math.ceil( float(numberOfDataPoints) / float(drawableDataPoints) )
        series.consolidate(pointsPerPixel)
        series.xStep = (numberOfPixels * pointsPerPixel) / numberOfDataPoints
      else:
        series.xStep = bestXStep

  def setupYAxis(self):
    seriesWithMissingValues = [ series for series in self.data if None in series ]

    if self.params.get('drawNullAsZero') and seriesWithMissingValues:
      yMinValue = 0.0
    else:
      yMinValue = safeMin( [safeMin(series) for series in self.data if not series.options.get('drawAsInfinite')] )

    if self.areaMode == 'stacked':
      length = safeMin( [len(series) for series in self.data if not series.options.get('drawAsInfinite')] )
      sumSeries = []

      for i in xrange(0, length):
        sumSeries.append( safeSum( [series[i] for series in self.data if not series.options.get('drawAsInfinite')] ) )
      yMaxValue = safeMax( sumSeries )
    else:
      yMaxValue = safeMax( [safeMax(series) for series in self.data if not series.options.get('drawAsInfinite')] )

    if yMinValue is None:
      yMinValue = 0.0

    if yMaxValue is None:
      yMaxValue = 1.0

    if 'yMax' in self.params:
      if self.params['yMax'] != 'max':
        yMaxValue = self.params['yMax']

    if 'yLimit' in self.params and self.params['yLimit'] < yMaxValue:
      yMaxValue = self.params['yLimit']

    if 'yMin' in self.params:
      yMinValue = self.params['yMin']

    if yMaxValue <= yMinValue:
      yMaxValue = yMinValue + 1

    yVariance = yMaxValue - yMinValue
    if 'yUnitSystem' in self.params and self.params['yUnitSystem'] == 'binary':
      order = math.log(yVariance, 2)
      orderFactor = 2 ** math.floor(order)
    else:
      order = math.log10(yVariance)
      orderFactor = 10 ** math.floor(order)
    v = yVariance / orderFactor #we work with a scaled down yVariance for simplicity

    divisors = (4,5,6) #different ways to divide-up the y-axis with labels
    prettyValues = (0.1,0.2,0.25,0.5,1.0,1.2,1.25,1.5,2.0,2.25,2.5)
    divisorInfo = []

    for d in divisors:
      q = v / d #our scaled down quotient, must be in the open interval (0,10)
      p = closest(q, prettyValues) #the prettyValue our quotient is closest to
      divisorInfo.append( ( p,abs(q-p)) ) #make a list so we can find the prettiest of the pretty

    divisorInfo.sort(key=lambda i: i[1]) #sort our pretty values by "closeness to a factor"
    prettyValue = divisorInfo[0][0] #our winner! Y-axis will have labels placed at multiples of our prettyValue
    self.yStep = prettyValue * orderFactor #scale it back up to the order of yVariance

    if 'yStep' in self.params:
      self.yStep = self.params['yStep']

    self.yBottom = self.yStep * math.floor( yMinValue / self.yStep ) #start labels at the greatest multiple of yStep <= yMinValue
    self.yTop = self.yStep * math.ceil( yMaxValue / self.yStep ) #Extend the top of our graph to the lowest yStep multiple >= yMaxValue

    if self.logBase and yMinValue > 0:
      self.yBottom = math.pow(self.logBase, math.floor(math.log(yMinValue, self.logBase)))
      self.yTop = math.pow(self.logBase, math.ceil(math.log(yMaxValue, self.logBase)))
    elif self.logBase and yMinValue <= 0:
        raise GraphError('Logarithmic scale specified with a dataset with a '
                         'minimum value less than or equal to zero')

    if 'yMax' in self.params:
      if self.params['yMax'] == 'max':
        scale = 1.0 * yMaxValue / self.yTop
        self.yStep *= (scale - 0.000001)
        self.yTop = yMaxValue
      else:
        self.yTop = self.params['yMax'] * 1.0
    if 'yMin' in self.params:
      self.yBottom = self.params['yMin']

    self.ySpan = self.yTop - self.yBottom

    if self.ySpan == 0:
      self.yTop += 1
      self.ySpan += 1

    self.graphHeight = self.area['ymax'] - self.area['ymin']
    self.yScaleFactor = float(self.graphHeight) / float(self.ySpan)

    if not self.params.get('hideAxes',False):
      #Create and measure the Y-labels

      def makeLabel(yValue):
        yValue, prefix = format_units(yValue, self.yStep,
                system=self.params.get('yUnitSystem'))
        ySpan, spanPrefix = format_units(self.ySpan, self.yStep,
                system=self.params.get('yUnitSystem'))
        if yValue < 0.1:
          return "%g %s" % (float(yValue), prefix)
        elif yValue < 1.0:
          return "%.2f %s" % (float(yValue), prefix)
        if ySpan > 10 or spanPrefix != prefix:
          if type(yValue) is float:
            return "%.1f %s" % (float(yValue), prefix)
          else:
            return "%d %s " % (int(yValue), prefix)
        elif ySpan > 3:
          return "%.1f %s " % (float(yValue), prefix)
        elif ySpan > 0.1:
          return "%.2f %s " % (float(yValue), prefix)
        else:
          return "%g %s" % (float(yValue), prefix)

      self.yLabelValues = self.getYLabelValues(self.yBottom, self.yTop, self.yStep)
      self.yLabels = map(makeLabel,self.yLabelValues)
      self.yLabelWidth = max([self.getExtents(label)['width'] for label in self.yLabels])

      if not self.params.get('hideYAxis'):
        if self.params.get('yAxisSide') == 'left': #scoot the graph over to the left just enough to fit the y-labels
          xMin = self.margin + (self.yLabelWidth * 1.02)
          if self.area['xmin'] < xMin:
            self.area['xmin'] = xMin
        else: #scoot the graph over to the right just enough to fit the y-labels
          xMin = 0
          xMax = self.margin - (self.yLabelWidth * 1.02)
          if self.area['xmax'] >= xMax:
            self.area['xmax'] = xMax
    else:
      self.yLabelValues = []
      self.yLabels = []
      self.yLabelWidth = 0.0

  def setupTwoYAxes(self):
    # I am Lazy.
    Ldata = []
    Rdata = []
    seriesWithMissingValuesL = []
    seriesWithMissingValuesR = []
    self.yLabelsL = []
    self.yLabelsR = []

    Ldata += self.dataLeft
    Rdata += self.dataRight

    # Lots of coupled lines ahead.  Will operate on Left data first then Right. 

    seriesWithMissingValuesL = [ series for series in Ldata if None in series ]
    seriesWithMissingValuesR = [ series for series in Rdata if None in series ]
    
    if self.params.get('drawNullAsZero') and seriesWithMissingValuesL:
      yMinValueL = 0.0
    else:
      yMinValueL = safeMin( [safeMin(series) for series in Ldata if not series.options.get('drawAsInfinite')] )
    if self.params.get('drawNullAsZero') and seriesWithMissingValuesR:
      yMinValueR = 0.0
    else:
      yMinValueR = safeMin( [safeMin(series) for series in Rdata if not series.options.get('drawAsInfinite')] )

    if self.areaMode == 'stacked':
      yMaxValueL = safeSum( [safeMax(series) for series in Ldata] )
      yMaxValueR = safeSum( [safeMax(series) for series in Rdata] )
    else:
      yMaxValueL = safeMax( [safeMax(series) for series in Ldata] )
      yMaxValueR = safeMax( [safeMax(series) for series in Rdata] )

    if yMinValueL is None:
      yMinValueL = 0.0
    if yMinValueR is None:
      yMinValueR = 0.0

    if yMaxValueL is None:
      yMaxValueL = 1.0
    if yMaxValueR is None:
      yMaxValueR = 1.0

    if 'yMaxLeft' in self.params: 
      yMaxValueL = self.params['yMaxLeft']
    if 'yMaxRight' in self.params: 
      yMaxValueR = self.params['yMaxRight']

    if 'yLimitLeft' in self.params and self.params['yLimitLeft'] < yMaxValueL: 
      yMaxValueL = self.params['yLimitLeft']
    if 'yLimitRight' in self.params and self.params['yLimitRight'] < yMaxValueR: 
      yMaxValueR = self.params['yLimitRight']

    if 'yMinLeft' in self.params: 
      yMinValueL = self.params['yMinLeft']
    if 'yMinRight' in self.params: 
      yMinValueR = self.params['yMinRight']

    if yMaxValueL <= yMinValueL:
      yMaxValueL = yMinValueL + 1
    if yMaxValueR <= yMinValueR:
      yMaxValueR = yMinValueR + 1

    yVarianceL = yMaxValueL - yMinValueL
    yVarianceR = yMaxValueR - yMinValueR
    orderL = math.log10(yVarianceL)
    orderR = math.log10(yVarianceR)
    orderFactorL = 10 ** math.floor(orderL)
    orderFactorR = 10 ** math.floor(orderR)
    vL = yVarianceL / orderFactorL #we work with a scaled down yVariance for simplicity
    vR = yVarianceR / orderFactorR

    divisors = (4,5,6) #different ways to divide-up the y-axis with labels
    prettyValues = (0.1,0.2,0.25,0.5,1.0,1.2,1.25,1.5,2.0,2.25,2.5)
    divisorInfoL = []
    divisorInfoR = []

    for d in divisors:
      qL = vL / d #our scaled down quotient, must be in the open interval (0,10)
      qR = vR / d
      pL = closest(qL, prettyValues) #the prettyValue our quotient is closest to
      pR = closest(qR, prettyValues) 
      divisorInfoL.append( ( pL,abs(qL-pL)) ) #make a list so we can find the prettiest of the pretty
      divisorInfoR.append( ( pR,abs(qR-pR)) ) 

    divisorInfoL.sort(key=lambda i: i[1]) #sort our pretty values by "closeness to a factor"
    divisorInfoR.sort(key=lambda i: i[1]) 
    prettyValueL = divisorInfoL[0][0] #our winner! Y-axis will have labels placed at multiples of our prettyValue
    prettyValueR = divisorInfoR[0][0] 
    self.yStepL = prettyValueL * orderFactorL #scale it back up to the order of yVariance
    self.yStepR = prettyValueR * orderFactorR 

    if 'yStepLeft' in self.params: 
      self.yStepL = self.params['yStepLeft']
    if 'yStepRight' in self.params: 
      self.yStepR = self.params['yStepRight']

    self.yBottomL = self.yStepL * math.floor( yMinValueL / self.yStepL ) #start labels at the greatest multiple of yStepL <= yMinValue
    self.yBottomR = self.yStepR * math.floor( yMinValueR / self.yStepR ) #start labels at the greatest multiple of yStepR <= yMinValue
    self.yTopL = self.yStepL * math.ceil( yMaxValueL / self.yStepL ) #Extend the top of our graph to the lowest yStepL multiple >= yMaxValue
    self.yTopR = self.yStepR * math.ceil( yMaxValueR / self.yStepR ) #Extend the top of our graph to the lowest yStepR multiple >= yMaxValue

    if self.logBase and yMinValueL > 0 and yMinValueR > 0: #TODO: Allow separate bases for L & R Axes.
      self.yBottomL = math.pow(self.logBase, math.floor(math.log(yMinValueL, self.logBase)))
      self.yTopL = math.pow(self.logBase, math.ceil(math.log(yMaxValueL, self.logBase)))
      self.yBottomR = math.pow(self.logBase, math.floor(math.log(yMinValueR, self.logBase)))
      self.yTopR = math.pow(self.logBase, math.ceil(math.log(yMaxValueR, self.logBase)))
    elif self.logBase and ( yMinValueL <= 0 or yMinValueR <=0 ) :
        raise GraphError('Logarithmic scale specified with a dataset with a '
                         'minimum value less than or equal to zero')

    if 'yMaxLeft' in self.params:
      self.yTopL = self.params['yMaxLeft']
    if 'yMaxRight' in self.params:
      self.yTopR = self.params['yMaxRight']
    if 'yMinLeft' in self.params:
      self.yBottomL = self.params['yMinLeft']
    if 'yMinRight' in self.params:
      self.yBottomR = self.params['yMinRight']

    self.ySpanL = self.yTopL - self.yBottomL
    self.ySpanR = self.yTopR - self.yBottomR

    if self.ySpanL == 0:
      self.yTopL += 1
      self.ySpanL += 1
    if self.ySpanR == 0:
      self.yTopR += 1
      self.ySpanR += 1

    self.graphHeight = self.area['ymax'] - self.area['ymin']
    self.yScaleFactorL = float(self.graphHeight) / float(self.ySpanL)
    self.yScaleFactorR = float(self.graphHeight) / float(self.ySpanR)

    #Create and measure the Y-labels
    def makeLabel(yValue, yStep=None, ySpan=None):
      yValue, prefix = format_units(yValue,yStep,system=self.params.get('yUnitSystem'))
      ySpan, spanPrefix = format_units(ySpan,yStep,system=self.params.get('yUnitSystem'))
      if yValue < 0.1:
        return "%g %s" % (float(yValue), prefix)
      elif yValue < 1.0:
        return "%.2f %s" % (float(yValue), prefix)
      if ySpan > 10 or spanPrefix != prefix:
        if type(yValue) is float:
          return "%.1f %s " % (float(yValue), prefix)
        else:
          return "%d %s " % (int(yValue), prefix)
      elif ySpan > 3:
        return "%.1f %s " % (float(yValue), prefix)
      elif ySpan > 0.1:
        return "%.2f %s " % (float(yValue), prefix)
      else:
        return "%g %s" % (float(yValue), prefix)

    self.yLabelValuesL = self.getYLabelValues(self.yBottomL, self.yTopL, self.yStepL)
    self.yLabelValuesR = self.getYLabelValues(self.yBottomR, self.yTopR, self.yStepR)
    for value in self.yLabelValuesL: #can't use map() here self.yStepL and self.ySpanL are not iterable
      self.yLabelsL.append( makeLabel(value,self.yStepL,self.ySpanL))
    for value in self.yLabelValuesR: 
      self.yLabelsR.append( makeLabel(value,self.yStepR,self.ySpanR) )
    self.yLabelWidthL = max([self.getExtents(label)['width'] for label in self.yLabelsL])
    self.yLabelWidthR = max([self.getExtents(label)['width'] for label in self.yLabelsR])
    #scoot the graph over to the left just enough to fit the y-labels
        
    #xMin = self.margin + self.margin + (self.yLabelWidthL * 1.02)
    xMin = self.margin + (self.yLabelWidthL * 1.02)
    if self.area['xmin'] < xMin:
      self.area['xmin'] = xMin
    #scoot the graph over to the right just enough to fit the y-labels
    xMax = self.width - (self.yLabelWidthR * 1.02)
    if self.area['xmax'] >= xMax:
      self.area['xmax'] = xMax

  def getYLabelValues(self, minYValue, maxYValue, yStep=None):
    vals = []
    if self.logBase:
      vals = list( logrange(self.logBase, minYValue, maxYValue) )
    else:
      vals = list( frange(minYValue, maxYValue, yStep) )
    return vals

  def setupXAxis(self):
    self.startTime = min([series.start for series in self.data])
    if self.lineMode == 'staircase':
      self.endTime = max([series.end for series in self.data])
    else:
      self.endTime = max([(series.end - series.step) for series in self.data])
    timeRange = self.endTime - self.startTime

    if self.userTimeZone:
      tzinfo = pytz.timezone(self.userTimeZone)
    else:
      tzinfo = pytz.timezone(settings.TIME_ZONE)

    self.start_dt = datetime.fromtimestamp(self.startTime, tzinfo)
    self.end_dt = datetime.fromtimestamp(self.endTime, tzinfo)

    secondsPerPixel = float(timeRange) / float(self.graphWidth)
    self.xScaleFactor = float(self.graphWidth) / float(timeRange) #pixels per second

    potential = [c for c in xAxisConfigs if c['seconds'] <= secondsPerPixel and c.get('maxInterval', timeRange + 1) >= timeRange]
    if potential:
      self.xConf = potential[-1]
    else:
      self.xConf = xAxisConfigs[-1]

    self.xLabelStep = self.xConf['labelUnit'] * self.xConf['labelStep']
    self.xMinorGridStep = self.xConf['minorGridUnit'] * self.xConf['minorGridStep']
    self.xMajorGridStep = self.xConf['majorGridUnit'] * self.xConf['majorGridStep']


  def drawLabels(self):
    #Draw the Y-labels
    if not self.params.get('hideYAxis'):
      if not self.secondYAxis:
        for value,label in zip(self.yLabelValues,self.yLabels):
          if self.params.get('yAxisSide') == 'left':
            x = self.area['xmin'] - (self.yLabelWidth * 0.02)
          else:
            x = self.area['xmax'] + (self.yLabelWidth * 0.02) #Inverted for right side Y Axis

          y = self.getYCoord(value)
          if y is None:
              value = None
          elif y < 0:
              y = 0

          if self.params.get('yAxisSide') == 'left':
            self.drawText(label, x, y, align='right', valign='middle')
          else:
            self.drawText(label, x, y, align='left', valign='middle') #Inverted for right side Y Axis
      else: #Draws a right side and a Left side axis
        for valueL,labelL in zip(self.yLabelValuesL,self.yLabelsL):
          xL = self.area['xmin'] - (self.yLabelWidthL * 0.02)
          yL = self.getYCoord(valueL, "left")
          if yL is None:
            value = None
          elif yL < 0:
            yL = 0
          self.drawText(labelL, xL, yL, align='right', valign='middle')
          
          ### Right Side
        for valueR,labelR in zip(self.yLabelValuesR,self.yLabelsR):
          xR = self.area['xmax'] + (self.yLabelWidthR * 0.02) + 3 #Inverted for right side Y Axis
          yR = self.getYCoord(valueR, "right")
          if yR is None:
            valueR = None
          elif yR < 0:
            yR = 0
          self.drawText(labelR, xR, yR, align='left', valign='middle') #Inverted for right side Y Axis
      
    (dt, x_label_delta) = find_x_times(self.start_dt, self.xConf['labelUnit'], self.xConf['labelStep'])

    #Draw the X-labels
    xFormat = self.params.get('xFormat', self.xConf['format'])
    while dt < self.end_dt:
      label = dt.strftime(xFormat)
      x = self.area['xmin'] + (toSeconds(dt - self.start_dt) * self.xScaleFactor)
      y = self.area['ymax'] + self.getExtents()['maxAscent']
      self.drawText(label, x, y, align='center', valign='top')
      dt += x_label_delta

  def drawGridLines(self):
    # Not sure how to handle this for 2 y-axes
    # Just using the left side info for the grid.  

    #Horizontal grid lines
    leftSide = self.area['xmin']
    rightSide = self.area['xmax']
    labels = []
    if self.secondYAxis:
      labels = self.yLabelValuesL
    else:
      labels = self.yLabelValues
    if self.logBase:
      labels.append(self.logBase * max(labels))

    for i, value in enumerate(labels):
      self.ctx.set_line_width(0.4)
      self.setColor( self.params.get('majorGridLineColor',self.defaultMajorGridLineColor) )

      if self.secondYAxis:
        y = self.getYCoord(value,"left")
      else:
        y = self.getYCoord(value)

      if y is None or y < 0:
          continue
      self.ctx.move_to(leftSide, y)
      self.ctx.line_to(rightSide, y)
      self.ctx.stroke()

      # draw minor gridlines if this isn't the last label
      if self.minorY >= 1 and i < (len(labels) - 1):
        # in case graphite supports inverted Y axis now or someday
        (valueLower, valueUpper) = sorted((value, labels[i+1]))

        # each minor gridline is 1/minorY apart from the nearby gridlines.
        # we calculate that distance, for adding to the value in the loop.
        distance = ((valueUpper - valueLower) / float(1 + self.minorY))

        # starting from the initial valueLower, we add the minor distance
        # for each minor gridline that we wish to draw, and then draw it.
        for minor in range(self.minorY):
          self.ctx.set_line_width(0.3)
          self.setColor( self.params.get('minorGridLineColor',self.defaultMinorGridLineColor) )

          # the current minor gridline value is halfway between the current and next major gridline values
          value = (valueLower + ((1+minor) * distance))

          if self.logBase:
            yTopFactor = self.logBase * self.logBase
          else:
            yTopFactor = 1

          if self.secondYAxis:
            if value >= (yTopFactor * self.yTopL):
              continue
          else:
            if value >= (yTopFactor * self.yTop):
              continue

          if self.secondYAxis:
            y = self.getYCoord(value,"left")
          else:
            y = self.getYCoord(value)
          if y is None or y < 0:
              continue

          self.ctx.move_to(leftSide, y)
          self.ctx.line_to(rightSide, y)
          self.ctx.stroke()

    #Vertical grid lines
    top = self.area['ymin']
    bottom = self.area['ymax']

    # First we do the minor grid lines (majors will paint over them)
    self.ctx.set_line_width(0.25)
    self.setColor( self.params.get('minorGridLineColor',self.defaultMinorGridLineColor) )
    (dt, x_minor_delta) = find_x_times(self.start_dt, self.xConf['minorGridUnit'], self.xConf['minorGridStep'])

    while dt < self.end_dt:
      x = self.area['xmin'] + (toSeconds(dt - self.start_dt) * self.xScaleFactor)

      if x < self.area['xmax']:
        self.ctx.move_to(x, bottom)
        self.ctx.line_to(x, top)
        self.ctx.stroke()

      dt += x_minor_delta

    # Now we do the major grid lines
    self.ctx.set_line_width(0.33)
    self.setColor( self.params.get('majorGridLineColor',self.defaultMajorGridLineColor) )
    (dt, x_major_delta) = find_x_times(self.start_dt, self.xConf['majorGridUnit'], self.xConf['majorGridStep'])

    while dt < self.end_dt:
      x = self.area['xmin'] + (toSeconds(dt - self.start_dt) * self.xScaleFactor)

      if x < self.area['xmax']:
        self.ctx.move_to(x, bottom)
        self.ctx.line_to(x, top)
        self.ctx.stroke()

      dt += x_major_delta

    #Draw side borders for our graph area
    self.ctx.set_line_width(0.5)
    self.ctx.move_to(self.area['xmax'], bottom)
    self.ctx.line_to(self.area['xmax'], top)
    self.ctx.move_to(self.area['xmin'], bottom)
    self.ctx.line_to(self.area['xmin'], top)
    self.ctx.stroke()



class PieGraph(Graph):
  customizable = Graph.customizable + \
                 ('title','valueLabels','valueLabelsMin','hideLegend','pieLabels')
  validValueLabels = ('none','number','percent')

  def drawGraph(self,**params):
    self.pieLabels = params.get('pieLabels', 'horizontal')
    self.total = sum( [t[1] for t in self.data] )

    self.slices = []
    for name,value in self.data:
      self.slices.append({
        'name' : name,
        'value' : value,
        'percent' : value / self.total,
        'color' : self.colors.next(),
      })

    titleSize = self.defaultFontParams['size'] + math.floor( math.log(self.defaultFontParams['size']) )
    self.setFont( size=titleSize )
    self.setColor( self.foregroundColor )
    if params.get('title'):
      self.drawTitle( params['title'] )
    self.setFont()

    if not params.get('hideLegend',False):
      elements = [ (slice['name'],slice['color'],None) for slice in self.slices ]
      self.drawLegend(elements)

    self.drawSlices()

    self.valueLabelsMin = float( params.get('valueLabelsMin',5) )
    self.valueLabels = params.get('valueLabels','percent')
    assert self.valueLabels in self.validValueLabels, \
    "valueLabels=%s must be one of %s" % (self.valueLabels,self.validValueLabels)
    if self.valueLabels != 'none':
      self.drawLabels()

  def drawSlices(self):
    theta = 3.0 * math.pi / 2.0
    halfX = (self.area['xmax'] - self.area['xmin']) / 2.0
    halfY = (self.area['ymax'] - self.area['ymin']) / 2.0
    self.x0 = x0 = self.area['xmin'] + halfX
    self.y0 = y0 = self.area['ymin'] + halfY
    self.radius = radius = min(halfX,halfY) * 0.95
    for slice in self.slices:
      self.setColor( slice['color'] )
      self.ctx.move_to(x0,y0)
      phi = theta + (2 * math.pi) * slice['percent']
      self.ctx.arc( x0, y0, radius, theta, phi )
      self.ctx.line_to(x0,y0)
      self.ctx.fill()
      slice['midAngle'] = (theta + phi) / 2.0
      slice['midAngle'] %= 2.0 * math.pi
      theta = phi

  def drawLabels(self):
    self.setFont()
    self.setColor( 'black' )
    for slice in self.slices:
      if self.valueLabels == 'percent':
        if (slice['percent'] * 100.0) < self.valueLabelsMin: continue
        label = "%%%.2f" % (slice['percent'] * 100.0)
      elif self.valueLabels == 'number':
        if slice['value'] < self.valueLabelsMin: continue
        if slice['value'] < 10 and slice['value'] != int(slice['value']):
          label = "%.2f" % slice['value']
        else:
          label = str(int(slice['value']))
      extents = self.getExtents(label)
      theta = slice['midAngle']
      x = self.x0 + (self.radius / 2.0 * math.cos(theta))
      y = self.y0 + (self.radius / 2.0 * math.sin(theta))

      if self.pieLabels == 'rotated':
        if theta > (math.pi / 2.0) and theta <= (3.0 * math.pi / 2.0):
          theta -= math.pi
        self.drawText( label, x, y, align='center', valign='middle', rotate=math.degrees(theta) )
      else:
        self.drawText( label, x, y, align='center', valign='middle')


GraphTypes = {
  'line' : LineGraph,
  'pie' : PieGraph,
}


#Convience functions
def closest(number,neighbors):
  distance = None
  closestNeighbor = None
  for neighbor in neighbors:
    d = abs(neighbor - number)
    if distance is None or d < distance:
      distance = d
      closestNeighbor = neighbor
  return closestNeighbor


def frange(start,end,step):
  f = start
  while f <= end:
    yield f
    f += step
    # Protect against rounding errors on very small float ranges
    if f == start:
      yield end
      return


def toSeconds(t):
  return (t.days * 86400) + t.seconds


def safeMin(args):
  args = [arg for arg in args if arg not in (None, INFINITY)]
  if args:
    return min(args)


def safeMax(args):
  args = [arg for arg in args if arg not in (None, INFINITY)]
  if args:
    return max(args)


def safeSum(values):
  return sum([v for v in values if v not in (None, INFINITY)])


def any(args):
  for arg in args:
    if arg:
      return True
  return False


def sort_stacked(series_list):
  stacked = [s for s in series_list if 'stacked' in s.options]
  not_stacked = [s for s in series_list if 'stacked' not in s.options]
  return stacked + not_stacked

def format_units(v, step=None, system="si"):
  """Format the given value in standardized units.

  ``system`` is either 'binary' or 'si'

  For more info, see:
    http://en.wikipedia.org/wiki/SI_prefix
    http://en.wikipedia.org/wiki/Binary_prefix
  """

  if step is None:
    condition = lambda size: abs(v) >= size
  else:
    condition = lambda size: abs(v) >= size and step >= size

  for prefix, size in UnitSystems[system]:
    if condition(size):
      v2 = v / size
      if (v2 - math.floor(v2)) < 0.00000000001 and v > 1:
        v2 = math.floor(v2)
      return v2, prefix

  if (v - math.floor(v)) < 0.00000000001 and v > 1 :
    v = math.floor(v)
  return v, ""


def find_x_times(start_dt, unit, step):
  if unit == SEC:
    dt = start_dt.replace(second=start_dt.second - (start_dt.second % step))
    x_delta = timedelta(seconds=step)

  elif unit == MIN:
    dt = start_dt.replace(second=0, minute=start_dt.minute - (start_dt.minute % step))
    x_delta = timedelta(minutes=step)

  elif unit == HOUR:
    dt = start_dt.replace(second=0, minute=0, hour=start_dt.hour - (start_dt.hour % step))
    x_delta = timedelta(hours=step)

  elif unit == DAY:
    dt = start_dt.replace(second=0, minute=0, hour=0)
    x_delta = timedelta(days=step)

  else:
    raise ValueError("Invalid unit: %s" % unit)

  while dt < start_dt:
    dt += x_delta

  return (dt, x_delta)


def logrange(base, scale_min, scale_max):
  current = scale_min
  if scale_min > 0:
      current = math.floor(math.log(scale_min, base))
  factor = current
  while current <= scale_max:
     current = math.pow(base, factor)
     yield current
     factor += 1

########NEW FILE########
__FILENAME__ = grammar
from graphite.thirdparty.pyparsing import *

ParserElement.enablePackrat()
grammar = Forward()

expression = Forward()

# Literals
intNumber = Combine(
  Optional('-') + Word(nums)
)('integer')

floatNumber = Combine(
  Optional('-') + Word(nums) + Literal('.') + Word(nums)
)('float')

aString = quotedString('string')

# Use lookahead to match only numbers in a list (can't remember why this is necessary)
afterNumber = FollowedBy(",") ^ FollowedBy(")") ^ FollowedBy(LineEnd())
number = Group(
  (floatNumber + afterNumber) |
  (intNumber + afterNumber)
)('number')

boolean = Group(
  CaselessKeyword("true") |
  CaselessKeyword("false")
)('boolean')

# Function calls
arg = Group(
  boolean |
  number |
  aString |
  expression
)
args = delimitedList(arg)('args')

func = Word(alphas+'_', alphanums+'_')('func')
call = Group(
  func + Literal('(').suppress() +
  args + Literal(')').suppress()
)('call')

# Metric pattern (aka. pathExpression)
validMetricChars = alphanums + r'''!#$%&"'*+-.:;<=>?@[\]^_`|~'''
pathExpression = Combine(
  Optional(Word(validMetricChars)) +
  Combine(
    ZeroOrMore(
      Group(
        Literal('{') +
        Word(validMetricChars + ',') +
        Literal('}') + Optional( Word(validMetricChars) )
      )
    )
  )
)('pathExpression')

expression << Group(call | pathExpression)('expression')

grammar << expression

def enableDebug():
  for name,obj in globals().items():
    try:
      obj.setName(name)
      obj.setDebug(True)
    except:
      pass

########NEW FILE########
__FILENAME__ = hashing
"""Copyright 2008 Orbitz WorldWide
   Copyright 2011 Chris Davis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from graphite.logger import log
import time
try:
  from hashlib import md5
except ImportError:
  from md5 import md5
import bisect

def hashRequest(request):
  # Normalize the request parameters so ensure we're deterministic
  queryParams = ["%s=%s" % (key, '&'.join(values))
                 for (key,values) in request.GET.lists()
                 if not key.startswith('_')]

  normalizedParams = ','.join( sorted(queryParams) ) or 'noParam'
  myHash = stripControlChars(normalizedParams) #memcached doesn't like unprintable characters in its keys

  return compactHash(myHash)


def hashData(targets, startTime, endTime):
  targetsString = ','.join(targets)
  startTimeString = startTime.strftime("%Y%m%d_%H%M")
  endTimeString = endTime.strftime("%Y%m%d_%H%M")
  myHash = targetsString + '@' + startTimeString + ':' + endTimeString
  myHash = stripControlChars(myHash)

  return compactHash(myHash)


def stripControlChars(string):
  return filter(lambda char: ord(char) >= 33, string)


def compactHash(string):
  hash = md5()
  hash.update(string)
  return hash.hexdigest()



class ConsistentHashRing:
  def __init__(self, nodes, replica_count=100):
    self.ring = []
    self.replica_count = replica_count
    for node in nodes:
      self.add_node(node)

  def compute_ring_position(self, key):
    big_hash = md5( str(key) ).hexdigest()
    small_hash = int(big_hash[:4], 16)
    return small_hash

  def add_node(self, key):
    for i in range(self.replica_count):
      replica_key = "%s:%d" % (key, i)
      position = self.compute_ring_position(replica_key)
      entry = (position, key)
      bisect.insort(self.ring, entry)

  def remove_node(self, key):
    self.ring = [entry for entry in self.ring if entry[1] != key]

  def get_node(self, key):
    position = self.compute_ring_position(key)
    search_entry = (position, None)
    index = bisect.bisect_left(self.ring, search_entry)
    index %= len(self.ring)
    entry = self.ring[index]
    return entry[1]

########NEW FILE########
__FILENAME__ = urls
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from django.conf.urls.defaults import *

urlpatterns = patterns('graphite.render.views',
  ('local/?$','renderLocalView'),
  ('~(?P<username>[^/]+)/(?P<graphName>[^/]+)/?','renderMyGraphView'),
  ('', 'renderView'),
)

########NEW FILE########
__FILENAME__ = views
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""
import csv
from time import time, strftime, localtime
from random import shuffle
from httplib import CannotSendRequest
from urllib import urlencode
from urlparse import urlsplit, urlunsplit
from cgi import parse_qs
from cStringIO import StringIO
try:
  import cPickle as pickle
except ImportError:
  import pickle

from graphite.util import getProfileByUsername, json
from graphite.remote_storage import HTTPConnectionWithTimeout
from graphite.logger import log
from graphite.render.evaluator import evaluateTarget
from graphite.render.attime import parseATTime
from graphite.render.functions import PieFunctions
from graphite.render.hashing import hashRequest, hashData
from graphite.render.glyph import GraphTypes

from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect
from django.template import Context, loader
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings


def renderView(request):
  start = time()
  (graphOptions, requestOptions) = parseOptions(request)
  useCache = 'noCache' not in requestOptions
  cacheTimeout = requestOptions['cacheTimeout']
  requestContext = {
    'startTime' : requestOptions['startTime'],
    'endTime' : requestOptions['endTime'],
    'localOnly' : requestOptions['localOnly'],
    'data' : []
  }
  data = requestContext['data']

  # First we check the request cache
  if useCache:
    requestKey = hashRequest(request)
    cachedResponse = cache.get(requestKey)
    if cachedResponse:
      log.cache('Request-Cache hit [%s]' % requestKey)
      log.rendering('Returned cached response in %.6f' % (time() - start))
      return cachedResponse
    else:
      log.cache('Request-Cache miss [%s]' % requestKey)

  # Now we prepare the requested data
  if requestOptions['graphType'] == 'pie':
    for target in requestOptions['targets']:
      if target.find(':') >= 0:
        try:
          name,value = target.split(':',1)
          value = float(value)
        except:
          raise ValueError, "Invalid target '%s'" % target
        data.append( (name,value) )
      else:
        seriesList = evaluateTarget(requestContext, target)

        for series in seriesList:
          func = PieFunctions[requestOptions['pieMode']]
          data.append( (series.name, func(requestContext, series) or 0 ))

  elif requestOptions['graphType'] == 'line':
    # Let's see if at least our data is cached
    if useCache:
      targets = requestOptions['targets']
      startTime = requestOptions['startTime']
      endTime = requestOptions['endTime']
      dataKey = hashData(targets, startTime, endTime)
      cachedData = cache.get(dataKey)
      if cachedData:
        log.cache("Data-Cache hit [%s]" % dataKey)
      else:
        log.cache("Data-Cache miss [%s]" % dataKey)
    else:
      cachedData = None

    if cachedData is not None:
      requestContext['data'] = data = cachedData
    else: # Have to actually retrieve the data now
      for target in requestOptions['targets']:
        t = time()
        seriesList = evaluateTarget(requestContext, target)
        log.rendering("Retrieval of %s took %.6f" % (target, time() - t))
        data.extend(seriesList)

    if useCache:
      cache.set(dataKey, data, cacheTimeout)

    # If data is all we needed, we're done
    if 'pickle' in requestOptions:
      response = HttpResponse(mimetype='application/pickle')
      seriesInfo = [series.getInfo() for series in data]
      pickle.dump(seriesInfo, response, protocol=-1)

      log.rendering('Total pickle rendering time %.6f' % (time() - start))
      return response

    format = requestOptions.get('format')
    if format == 'csv':
      response = HttpResponse(mimetype='text/csv')
      writer = csv.writer(response, dialect='excel')

      for series in data:
        for i, value in enumerate(series):
          timestamp = localtime( series.start + (i * series.step) )
          writer.writerow( (series.name, strftime("%Y-%m-%d %H:%M:%S", timestamp), value) )

      return response

    if format == 'json':
      series_data = []
      for series in data:
        timestamps = range(series.start, series.end, series.step)
        datapoints = zip(series, timestamps)
        series_data.append( dict(target=series.name, datapoints=datapoints) )

      if 'jsonp' in requestOptions:
        response = HttpResponse(
          content="%s(%s)" % (requestOptions['jsonp'], json.dumps(series_data)),
          mimetype='text/javascript')
      else:
        response = HttpResponse(content=json.dumps(series_data), mimetype='application/json')

      response['Pragma'] = 'no-cache'
      response['Cache-Control'] = 'no-cache'
      return response

    if format == 'raw':
      response = HttpResponse(mimetype='text/plain')
      for series in data:
        response.write( "%s,%d,%d,%d|" % (series.name, series.start, series.end, series.step) )
        response.write( ','.join(map(str,series)) )
        response.write('\n')

      log.rendering('Total rawData rendering time %.6f' % (time() - start))
      return response

    if format == 'svg':
      graphOptions['outputFormat'] = 'svg'

  # We've got the data, now to render it
  graphOptions['data'] = data
  if settings.REMOTE_RENDERING: # Rendering on other machines is faster in some situations
    image = delegateRendering(requestOptions['graphType'], graphOptions)
  else:
    image = doImageRender(requestOptions['graphClass'], graphOptions)

  useSVG = graphOptions.get('outputFormat') == 'svg'
  if useSVG and 'jsonp' in requestOptions:
    response = HttpResponse(
      content="%s(%s)" % (requestOptions['jsonp'], json.dumps(image)),
      mimetype='text/javascript')
  else:
    response = buildResponse(image, useSVG and 'image/svg+xml' or 'image/png')

  if useCache:
    cache.set(requestKey, response, cacheTimeout)

  log.rendering('Total rendering time %.6f seconds' % (time() - start))
  return response


def parseOptions(request):
  queryParams = request.REQUEST

  # Start with some defaults
  graphOptions = {'width' : 330, 'height' : 250}
  requestOptions = {}

  graphType = queryParams.get('graphType','line')
  assert graphType in GraphTypes, "Invalid graphType '%s', must be one of %s" % (graphType,GraphTypes.keys())
  graphClass = GraphTypes[graphType]

  # Fill in the requestOptions
  requestOptions['graphType'] = graphType
  requestOptions['graphClass'] = graphClass
  requestOptions['pieMode'] = queryParams.get('pieMode', 'average')
  requestOptions['cacheTimeout'] = int( queryParams.get('cacheTimeout', settings.DEFAULT_CACHE_DURATION) )
  requestOptions['targets'] = []
  for target in queryParams.getlist('target'):
    requestOptions['targets'].append(target)

  if 'pickle' in queryParams:
    requestOptions['pickle'] = True
  if 'rawData' in queryParams:
    requestOptions['format'] = 'raw'
  if 'format' in queryParams:
    requestOptions['format'] = queryParams['format']
    if 'jsonp' in queryParams:
      requestOptions['jsonp'] = queryParams['jsonp']
  if 'noCache' in queryParams:
    requestOptions['noCache'] = True

  requestOptions['localOnly'] = queryParams.get('local') == '1'

  # Fill in the graphOptions
  for opt in graphClass.customizable:
    if opt in queryParams:
      val = queryParams[opt]
      if (val.isdigit() or (val.startswith('-') and val[1:].isdigit())) and opt not in ('fgcolor','bgcolor','fontColor'):
        val = int(val)
      elif '.' in val and (val.replace('.','',1).isdigit() or (val.startswith('-') and val[1:].replace('.','',1).isdigit())):
        val = float(val)
      elif val.lower() in ('true','false'):
        val = val.lower() == 'true'
      elif val.lower() == 'default' or val == '':
        continue
      graphOptions[opt] = val

  # Get the time interval for time-oriented graph types
  if graphType == 'line' or graphType == 'pie':
    if 'until' in queryParams:
      untilTime = parseATTime( queryParams['until'] )
    else:
      untilTime = parseATTime('now')
    if 'from' in queryParams:
      fromTime = parseATTime( queryParams['from'] )
    else:
      fromTime = parseATTime('-1d')

    startTime = min(fromTime, untilTime)
    endTime = max(fromTime, untilTime)
    assert startTime != endTime, "Invalid empty time range"
    
    requestOptions['startTime'] = startTime
    requestOptions['endTime'] = endTime

  return (graphOptions, requestOptions)


connectionPools = {}

def delegateRendering(graphType, graphOptions):
  start = time()
  postData = graphType + '\n' + pickle.dumps(graphOptions)
  servers = settings.RENDERING_HOSTS[:] #make a copy so we can shuffle it safely
  shuffle(servers)
  for server in servers:
    start2 = time()
    try:
      # Get a connection
      try:
        pool = connectionPools[server]
      except KeyError: #happens the first time
        pool = connectionPools[server] = set()
      try:
        connection = pool.pop()
      except KeyError: #No available connections, have to make a new one
        connection = HTTPConnectionWithTimeout(server)
        connection.timeout = settings.REMOTE_RENDER_CONNECT_TIMEOUT
      # Send the request
      try:
        connection.request('POST','/render/local/', postData)
      except CannotSendRequest:
        connection = HTTPConnectionWithTimeout(server) #retry once
        connection.timeout = settings.REMOTE_RENDER_CONNECT_TIMEOUT
        connection.request('POST', '/render/local/', postData)
      # Read the response
      response = connection.getresponse()
      assert response.status == 200, "Bad response code %d from %s" % (response.status,server)
      contentType = response.getheader('Content-Type')
      imageData = response.read()
      assert contentType == 'image/png', "Bad content type: \"%s\" from %s" % (contentType,server)
      assert imageData, "Received empty response from %s" % server
      # Wrap things up
      log.rendering('Remotely rendered image on %s in %.6f seconds' % (server,time() - start2))
      log.rendering('Spent a total of %.6f seconds doing remote rendering work' % (time() - start))
      pool.add(connection)
      return imageData
    except:
      log.exception("Exception while attempting remote rendering request on %s" % server)
      log.rendering('Exception while remotely rendering on %s wasted %.6f' % (server,time() - start2))
      continue


def renderLocalView(request):
  try:
    start = time()
    reqParams = StringIO(request.raw_post_data)
    graphType = reqParams.readline().strip()
    optionsPickle = reqParams.read()
    reqParams.close()
    graphClass = GraphTypes[graphType]
    options = pickle.loads(optionsPickle)
    image = doImageRender(graphClass, options)
    log.rendering("Delegated rendering request took %.6f seconds" % (time() -  start))
    return buildResponse(image)
  except:
    log.exception("Exception in graphite.render.views.rawrender")
    return HttpResponseServerError()


def renderMyGraphView(request,username,graphName):
  profile = getProfileByUsername(username)
  if not profile:
    return errorPage("No such user '%s'" % username)
  try:
    graph = profile.mygraph_set.get(name=graphName)
  except ObjectDoesNotExist:
    return errorPage("User %s doesn't have a MyGraph named '%s'" % (username,graphName))

  request_params = dict(request.REQUEST.items())
  if request_params:
    url_parts = urlsplit(graph.url)
    query_string = url_parts[3]
    if query_string:
      url_params = parse_qs(query_string)
      # Remove lists so that we can do an update() on the dict
      for param, value in url_params.items():
        if isinstance(value, list) and param != 'target':
          url_params[param] = value[-1]
      url_params.update(request_params)
      # Handle 'target' being a list - we want duplicate &target params out of it
      url_param_pairs = []
      for key,val in url_params.items():
        if isinstance(val, list):
          for v in val:
            url_param_pairs.append( (key,v) )
        else:
          url_param_pairs.append( (key,val) )

      query_string = urlencode(url_param_pairs)
    url = urlunsplit(url_parts[:3] + (query_string,) + url_parts[4:])
  else:
    url = graph.url
  return HttpResponseRedirect(url)


def doImageRender(graphClass, graphOptions):
  pngData = StringIO()
  t = time()
  img = graphClass(**graphOptions)
  img.output(pngData)
  log.rendering('Rendered PNG in %.6f seconds' % (time() - t))
  imageData = pngData.getvalue()
  pngData.close()
  return imageData


def buildResponse(imageData, mimetype="image/png"):
  response = HttpResponse(imageData, mimetype=mimetype)
  response['Cache-Control'] = 'no-cache'
  response['Pragma'] = 'no-cache'
  return response


def errorPage(message):
  template = loader.get_template('500.html')
  context = Context(dict(message=message))
  return HttpResponseServerError( template.render(context) )

########NEW FILE########
__FILENAME__ = settings
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""
# Django settings for graphite project.
# DO NOT MODIFY THIS FILE DIRECTLY - use local_settings.py instead
import sys, os
from django import VERSION as DJANGO_VERSION
from os.path import join, dirname, abspath

try:
  import rrdtool
except ImportError:
  rrdtool = False

WEBAPP_VERSION = '0.9.9'
DEBUG = False
JAVASCRIPT_DEBUG = False

# Filesystem layout
WEB_DIR = dirname( abspath(__file__) )
WEBAPP_DIR = dirname(WEB_DIR)
GRAPHITE_ROOT = dirname(WEBAPP_DIR)
THIRDPARTY_DIR = join(WEB_DIR,'thirdparty')
# Initialize additional path variables
# Defaults for these are set after local_settings is imported
CONTENT_DIR = ''
CSS_DIR = ''
CONF_DIR = ''
DASHBOARD_CONF = ''
GRAPHTEMPLATES_CONF = ''
STORAGE_DIR = ''
WHITELIST_FILE = ''
INDEX_FILE = ''
LOG_DIR = ''
WHISPER_DIR = ''
RRD_DIR = ''
DATA_DIRS = []

CLUSTER_SERVERS = []

sys.path.insert(0, WEBAPP_DIR)
# Allow local versions of the libs shipped in thirdparty to take precedence
sys.path.append(THIRDPARTY_DIR)

# Memcache settings
MEMCACHE_HOSTS = []
DEFAULT_CACHE_DURATION = 60 #metric data and graphs are cached for one minute by default
LOG_CACHE_PERFORMANCE = False

# Remote store settings
REMOTE_STORE_FETCH_TIMEOUT = 6
REMOTE_STORE_FIND_TIMEOUT = 2.5
REMOTE_STORE_RETRY_DELAY = 60
REMOTE_FIND_CACHE_DURATION = 300

#Remote rendering settings
REMOTE_RENDERING = False #if True, rendering is delegated to RENDERING_HOSTS
RENDERING_HOSTS = []
REMOTE_RENDER_CONNECT_TIMEOUT = 1.0
LOG_RENDERING_PERFORMANCE = False

#Miscellaneous settings
CARBONLINK_HOSTS = ["127.0.0.1:7002"]
CARBONLINK_TIMEOUT = 1.0
SMTP_SERVER = "localhost"
DOCUMENTATION_URL = "http://graphite.readthedocs.org/"
ALLOW_ANONYMOUS_CLI = True
LOG_METRIC_ACCESS = False
LEGEND_MAX_ITEMS = 10

#Authentication settings
USE_LDAP_AUTH = False
LDAP_SERVER = "" # "ldapserver.mydomain.com"
LDAP_PORT = 389
LDAP_SEARCH_BASE = "" # "OU=users,DC=mydomain,DC=com"
LDAP_BASE_USER = "" # "CN=some_readonly_account,DC=mydomain,DC=com"
LDAP_BASE_PASS = "" # "my_password"
LDAP_USER_QUERY = "" # "(username=%s)"  For Active Directory use "(sAMAccountName=%s)"
LDAP_URI = None

#Set this to True to delegate authentication to the web server
USE_REMOTE_USER_AUTHENTICATION = False

# Override to link a different URL for login (e.g. for django_openid_auth)
LOGIN_URL = '/account/login'

#Additional authentication backends to prepend
ADDITIONAL_AUTHENTICATION_BACKENDS = []

#Initialize database settings - Old style (pre 1.2)
DATABASE_ENGINE = 'django.db.backends.sqlite3'	# 'postgresql', 'mysql', 'sqlite3' or 'ado_mssql'.
DATABASE_NAME = ''				# Or path to database file if using sqlite3.
DATABASE_USER = ''				# Not used with sqlite3.
DATABASE_PASSWORD = ''				# Not used with sqlite3.
DATABASE_HOST = ''				# Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''				# Set to empty string for default. Not used with sqlite3.

ADMINS = ()
MANAGERS = ADMINS

TEMPLATE_DIRS = (
  join(WEB_DIR, 'templates'),
)

# If using rrdcached, set to the address or socket of the daemon
FLUSHRRDCACHED = ''

#Django settings below, do not touch!
APPEND_SLASH = False
TEMPLATE_DEBUG = DEBUG
CACHE_BACKEND = "dummy:///"

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# Absolute path to the directory that holds media.

MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
#XXX Compatibility for Django 1.1. To be removed after 0.9.10
if DJANGO_VERSION < (1,2):
  TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
  )
else:
  TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
  )

MIDDLEWARE_CLASSES = (
  'django.middleware.common.CommonMiddleware',
  'django.middleware.gzip.GZipMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'graphite.urls'

INSTALLED_APPS = (
  'graphite.metrics',
  'graphite.render',
  'graphite.cli',
  'graphite.browser',
  'graphite.composer',
  'graphite.account',
  'graphite.dashboard',
  'graphite.whitelist',
  'graphite.events',
  'django.contrib.auth',
  'django.contrib.sessions',
  'django.contrib.admin',
  'django.contrib.contenttypes',
  'tagging',
)

AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']


## Pull in overrides from local_settings.py
try:
  from graphite.local_settings import *
except ImportError:
  print >> sys.stderr, "Could not import graphite.local_settings, using defaults!"


## Set config dependent on flags set in local_settings
# Path configuration
if not CONTENT_DIR:
  CONTENT_DIR = join(WEBAPP_DIR, 'content')
if not CSS_DIR:
  CSS_DIR = join(CONTENT_DIR, 'css')

if not CONF_DIR:
  CONF_DIR = os.environ.get('GRAPHITE_CONF_DIR', join(GRAPHITE_ROOT, 'conf'))
if not DASHBOARD_CONF:
  DASHBOARD_CONF = join(CONF_DIR, 'dashboard.conf')
if not GRAPHTEMPLATES_CONF:
  GRAPHTEMPLATES_CONF = join(CONF_DIR, 'graphTemplates.conf')

if not STORAGE_DIR:
  STORAGE_DIR = os.environ.get('GRAPHITE_STORAGE_DIR', join(GRAPHITE_ROOT, 'storage'))
if not WHITELIST_FILE:
  WHITELIST_FILE = join(STORAGE_DIR, 'lists', 'whitelist')
if not INDEX_FILE:
  INDEX_FILE = join(STORAGE_DIR, 'index')
if not LOG_DIR:
  LOG_DIR = join(STORAGE_DIR, 'log', 'webapp')
if not WHISPER_DIR:
  WHISPER_DIR = join(STORAGE_DIR, 'whisper/')
if not RRD_DIR:
  RRD_DIR = join(STORAGE_DIR, 'rrd/')
if not DATA_DIRS:
  if rrdtool and os.path.exists(RRD_DIR):
    DATA_DIRS = [WHISPER_DIR, RRD_DIR]
  else:
    DATA_DIRS = [WHISPER_DIR]

# Default sqlite db file
# This is set here so that a user-set STORAGE_DIR is available
if 'sqlite3' in DATABASE_ENGINE \
    and not DATABASE_NAME:
  DATABASE_NAME = join(STORAGE_DIR, 'graphite.db')

# Caching shortcuts
if MEMCACHE_HOSTS:
  CACHE_BACKEND = 'memcached://' + ';'.join(MEMCACHE_HOSTS) + ('/?timeout=%d' % DEFAULT_CACHE_DURATION)

# Authentication shortcuts
if USE_LDAP_AUTH and LDAP_URI is None:
  LDAP_URI = "ldap://%s:%d/" % (LDAP_SERVER, LDAP_PORT)

if USE_REMOTE_USER_AUTHENTICATION:
  MIDDLEWARE_CLASSES += ('django.contrib.auth.middleware.RemoteUserMiddleware',)
  AUTHENTICATION_BACKENDS.insert(0,'django.contrib.auth.backends.RemoteUserBackend')

if USE_LDAP_AUTH:
  AUTHENTICATION_BACKENDS.insert(0,'graphite.account.ldapBackend.LDAPBackend')


########NEW FILE########
__FILENAME__ = storage
import os, time, fnmatch, socket, errno
from os.path import isdir, isfile, join, exists, splitext, basename, realpath
import whisper
from graphite.remote_storage import RemoteStore
from django.conf import settings

try:
  import rrdtool
except ImportError:
  rrdtool = False

try:
  import gzip
except ImportError:
  gzip = False

try:
  import cPickle as pickle
except ImportError:
  import pickle


DATASOURCE_DELIMETER = '::RRD_DATASOURCE::'



class Store:
  def __init__(self, directories=[], remote_hosts=[]):
    self.directories = directories
    self.remote_hosts = remote_hosts
    self.remote_stores = [ RemoteStore(host) for host in remote_hosts if not is_local_interface(host) ]

    if not (directories or remote_hosts):
      raise valueError("directories and remote_hosts cannot both be empty")


  def get(self, metric_path): #Deprecated
    for directory in self.directories:
      relative_fs_path = metric_path.replace('.', '/') + '.wsp'
      absolute_fs_path = join(directory, relative_fs_path)

      if exists(absolute_fs_path):
        return WhisperFile(absolute_fs_path, metric_path)


  def find(self, query):
    if is_pattern(query):

      for match in self.find_all(query):
        yield match

    else:
      match = self.find_first(query)

      if match is not None:
        yield match


  def find_first(self, query):
    # Search locally first
    for directory in self.directories:
      for match in find(directory, query):
        return match

    # If nothing found earch remotely
    remote_requests = [ r.find(query) for r in self.remote_stores if r.available ]

    for request in remote_requests:
      for match in request.get_results():
        return match


  def find_all(self, query):
    # Start remote searches
    found = set()
    remote_requests = [ r.find(query) for r in self.remote_stores if r.available ]

    # Search locally
    for directory in self.directories:
      for match in find(directory, query):
        if match.metric_path not in found:
          yield match
          found.add(match.metric_path)

    # Gather remote search results
    for request in remote_requests:
      for match in request.get_results():

        if match.metric_path not in found:
          yield match
          found.add(match.metric_path)


def is_local_interface(host):
  if ':' in host:
    host = host.split(':',1)[0]

  for port in xrange(1025, 65535):
    try:
      sock = socket.socket()
      sock.bind( (host,port) )
      sock.close()

    except socket.error, e:
      if e.args[0] == errno.EADDRNOTAVAIL:
        return False
      else:
        continue

    else:
      return True

  raise Exception("Failed all attempts at binding to interface %s, last exception was %s" % (host, e))


def is_pattern(s):
  return '*' in s or '?' in s or '[' in s or '{' in s

def is_escaped_pattern(s):
  for symbol in '*?[{':
    i = s.find(symbol)
    if i > 0:
      if s[i-1] == '\\':
        return True
  return False

def find_escaped_pattern_fields(pattern_string):
  pattern_parts = pattern_string.split('.')
  for index,part in enumerate(pattern_parts):
    if is_escaped_pattern(part):
      yield index


def find(root_dir, pattern):
  "Generates nodes beneath root_dir matching the given pattern"
  clean_pattern = pattern.replace('\\', '')
  pattern_parts = clean_pattern.split('.')

  for absolute_path in _find(root_dir, pattern_parts):

    if DATASOURCE_DELIMETER in basename(absolute_path):
      (absolute_path,datasource_pattern) = absolute_path.rsplit(DATASOURCE_DELIMETER,1)
    else:
      datasource_pattern = None

    relative_path = absolute_path[ len(root_dir): ].lstrip('/')
    metric_path = relative_path.replace('/','.')

    # Preserve pattern in resulting path for escaped query pattern elements
    metric_path_parts = metric_path.split('.')
    for field_index in find_escaped_pattern_fields(pattern):
      metric_path_parts[field_index] = pattern_parts[field_index].replace('\\', '')
    metric_path = '.'.join(metric_path_parts)

    if isdir(absolute_path):
      yield Branch(absolute_path, metric_path)

    elif isfile(absolute_path):
      (metric_path,extension) = splitext(metric_path)

      if extension == '.wsp':
        yield WhisperFile(absolute_path, metric_path)

      elif extension == '.gz' and metric_path.endswith('.wsp'):
        metric_path = splitext(metric_path)[0]
        yield GzippedWhisperFile(absolute_path, metric_path)

      elif rrdtool and extension == '.rrd':
        rrd = RRDFile(absolute_path, metric_path)

        if datasource_pattern is None:
          yield rrd

        else:
          for source in rrd.getDataSources():
            if fnmatch.fnmatch(source.name, datasource_pattern):
              yield source


def _find(current_dir, patterns):
  """Recursively generates absolute paths whose components underneath current_dir
  match the corresponding pattern in patterns"""
  pattern = patterns[0]
  patterns = patterns[1:]
  entries = os.listdir(current_dir)

  subdirs = [e for e in entries if isdir( join(current_dir,e) )]
  matching_subdirs = match_entries(subdirs, pattern)

  if len(patterns) == 1 and rrdtool: #the last pattern may apply to RRD data sources
    files = [e for e in entries if isfile( join(current_dir,e) )]
    rrd_files = match_entries(files, pattern + ".rrd")

    if rrd_files: #let's assume it does
      datasource_pattern = patterns[0]

      for rrd_file in rrd_files:
        absolute_path = join(current_dir, rrd_file)
        yield absolute_path + DATASOURCE_DELIMETER + datasource_pattern

  if patterns: #we've still got more directories to traverse
    for subdir in matching_subdirs:

      absolute_path = join(current_dir, subdir)
      for match in _find(absolute_path, patterns):
        yield match

  else: #we've got the last pattern
    files = [e for e in entries if isfile( join(current_dir,e) )]
    matching_files = match_entries(files, pattern + '.*')

    for basename in matching_subdirs + matching_files:
      yield join(current_dir, basename)


def _deduplicate(entries):
  yielded = set()
  for entry in entries:
    if entry not in yielded:
      yielded.add(entry)
      yield entry


def match_entries(entries, pattern):
  # First we check for pattern variants (ie. {foo,bar}baz = foobaz or barbaz)
  v1, v2 = pattern.find('{'), pattern.find('}')

  if v1 > -1 and v2 > v1:
    variations = pattern[v1+1:v2].split(',')
    variants = [ pattern[:v1] + v + pattern[v2+1:] for v in variations ]
    matching = []

    for variant in variants:
      matching.extend( fnmatch.filter(entries, variant) )

    return list( _deduplicate(matching) ) #remove dupes without changing order

  else:
    matching = fnmatch.filter(entries, pattern)
    matching.sort()
    return matching


# Node classes
class Node:
  context = {}

  def __init__(self, fs_path, metric_path):
    self.fs_path = str(fs_path)
    self.metric_path = str(metric_path)
    self.real_metric = str(metric_path)
    self.name = self.metric_path.split('.')[-1]

  def getIntervals(self):
    return []

  def updateContext(self, newContext):
    raise NotImplementedError()


class Branch(Node):
  "Node with children"
  def fetch(self, startTime, endTime):
    "No-op to make all Node's fetch-able"
    return []

  def isLeaf(self):
    return False


class Leaf(Node):
  "(Abstract) Node that stores data"
  def isLeaf(self):
    return True


# Database File classes
class WhisperFile(Leaf):
  cached_context_data = None
  extension = '.wsp'

  def __init__(self, *args, **kwargs):
    Leaf.__init__(self, *args, **kwargs)
    real_fs_path = realpath(self.fs_path)

    if real_fs_path != self.fs_path:
      relative_fs_path = self.metric_path.replace('.', '/') + self.extension
      base_fs_path = realpath(self.fs_path[ :-len(relative_fs_path) ])
      relative_real_fs_path = real_fs_path[ len(base_fs_path)+1: ]
      self.real_metric = relative_real_fs_path[ :-len(self.extension) ].replace('/', '.')

  def getIntervals(self):
    start = time.time() - whisper.info(self.fs_path)['maxRetention']
    end = max( os.stat(self.fs_path).st_mtime, start )
    return [ (start, end) ]

  def fetch(self, startTime, endTime):
    (timeInfo,values) = whisper.fetch(self.fs_path, startTime, endTime)
    return (timeInfo,values)

  @property
  def context(self):
    if self.cached_context_data is not None:
      return self.cached_context_data

    context_path = self.fs_path[ :-len(self.extension) ] + '.context.pickle'

    if exists(context_path):
      fh = open(context_path, 'rb')
      context_data = pickle.load(fh)
      fh.close()
    else:
      context_data = {}

    self.cached_context_data = context_data
    return context_data

  def updateContext(self, newContext):
    self.context.update(newContext)
    context_path = self.fs_path[ :-len(self.extension) ] + '.context.pickle'

    fh = open(context_path, 'wb')
    pickle.dump(self.context, fh)
    fh.close()


class GzippedWhisperFile(WhisperFile):
  extension = '.wsp.gz'

  def fetch(self, startTime, endTime):
    if not gzip:
      raise Exception("gzip module not available, GzippedWhisperFile not supported")

    fh = gzip.GzipFile(self.fs_path, 'rb')
    try:
      return whisper.file_fetch(fh, startTime, endTime)
    finally:
      fh.close()

  def getIntervals(self):
    if not gzip:
      return []

    fh = gzip.GzipFile(self.fs_path, 'rb')
    try:
      start = time.time() - whisper.__readHeader(fh)['maxRetention']
      end = max( os.stat(self.fs_path).st_mtime, start )
    finally:
      fh.close()
    return [ (start, end) ]


class RRDFile(Branch):
  def getDataSources(self):
    info = rrdtool.info(self.fs_path)
    if 'ds' in info:
      return [RRDDataSource(self, datasource_name) for datasource_name in info['ds']]
    else:
      ds_keys = [ key for key in info if key.startswith('ds[') ]
      datasources = set( key[3:].split(']')[0] for key in ds_keys )
      return [ RRDDataSource(self, ds) for ds in datasources ]

  def getRetention(self):
    info = rrdtool.info(self.fs_path)
    if 'rra' in info:
      rras = info['rra']
    else:
      # Ugh, I like the old python-rrdtool api better..
      rra_keys = max([ int(key[4]) for key in info if key.startswith('rra[') ]) + 1
      rras = [{}] * rra_count
      for i in range(rra_count):
        rras[i]['pdp_per_row'] = info['rra[%d].pdp_per_row' % i]
        rras[i]['rows'] = info['rra[%d].rows' % i]

    retention_points = 0
    for rra in rras:
      points = rra['pdp_per_row'] * rra['rows']
      if points > retention_points:
        retention_points = points

    return  retention_points * info['step']


class RRDDataSource(Leaf):
  def __init__(self, rrd_file, name):
    Leaf.__init__(self, rrd_file.fs_path, rrd_file.metric_path + '.' + name)
    self.rrd_file = rrd_file

  def getIntervals(self):
    start = time.time() - self.rrd_file.getRetention()
    end = max( os.stat(self.rrd_file.fs_path).st_mtime, start )
    return [ (start, end) ]

  def fetch(self, startTime, endTime):
    startString = time.strftime("%H:%M_%Y%m%d+%Ss", time.localtime(startTime))
    endString = time.strftime("%H:%M_%Y%m%d+%Ss", time.localtime(endTime))

    if settings.FLUSHRRDCACHED:
      rrdtool.flushcached(self.fs_path, '--daemon', settings.FLUSHRRDCACHED)
    (timeInfo,columns,rows) = rrdtool.fetch(self.fs_path,'AVERAGE','-s' + startString,'-e' + endString)
    colIndex = list(columns).index(self.name)
    rows.pop() #chop off the latest value because RRD returns crazy last values sometimes
    values = (row[colIndex] for row in rows)

    return (timeInfo,values)



# Exposed Storage API
LOCAL_STORE = Store(settings.DATA_DIRS)
STORE = Store(settings.DATA_DIRS, remote_hosts=settings.CLUSTER_SERVERS)

########NEW FILE########
__FILENAME__ = pyparsing
# module pyparsing.py
#
# Copyright (c) 2003-2008  Paul T. McGuire
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#from __future__ import generators

__doc__ = \
"""
pyparsing module - Classes and methods to define and execute parsing grammars

The pyparsing module is an alternative approach to creating and executing simple grammars,
vs. the traditional lex/yacc approach, or the use of regular expressions.  With pyparsing, you
don't need to learn a new syntax for defining grammars or matching expressions - the parsing module
provides a library of classes that you use to construct the grammar directly in Python.

Here is a program to parse "Hello, World!" (or any greeting of the form "<salutation>, <addressee>!")::

    from pyparsing import Word, alphas

    # define grammar of a greeting
    greet = Word( alphas ) + "," + Word( alphas ) + "!"

    hello = "Hello, World!"
    print hello, "->", greet.parseString( hello )

The program outputs the following::

    Hello, World! -> ['Hello', ',', 'World', '!']

The Python representation of the grammar is quite readable, owing to the self-explanatory
class names, and the use of '+', '|' and '^' operators.

The parsed results returned from parseString() can be accessed as a nested list, a dictionary, or an
object with named attributes.

The pyparsing module handles some of the problems that are typically vexing when writing text parsers:
 - extra or missing whitespace (the above program will also handle "Hello,World!", "Hello  ,  World  !", etc.)
 - quoted strings
 - embedded comments
"""

__version__ = "1.5.0"
__versionTime__ = "28 May 2008 10:05"
__author__ = "Paul McGuire <ptmcg@users.sourceforge.net>"

import string
from weakref import ref as wkref
import copy,sys
import warnings
import re
import sre_constants
import xml.sax.saxutils
#~ sys.stderr.write( "testing pyparsing module, version %s, %s\n" % (__version__,__versionTime__ ) )

__all__ = [
'And', 'CaselessKeyword', 'CaselessLiteral', 'CharsNotIn', 'Combine', 'Dict', 'Each', 'Empty',
'FollowedBy', 'Forward', 'GoToColumn', 'Group', 'Keyword', 'LineEnd', 'LineStart', 'Literal',
'MatchFirst', 'NoMatch', 'NotAny', 'OneOrMore', 'OnlyOnce', 'Optional', 'Or',
'ParseBaseException', 'ParseElementEnhance', 'ParseException', 'ParseExpression', 'ParseFatalException',
'ParseResults', 'ParseSyntaxException', 'ParserElement', 'QuotedString', 'RecursiveGrammarException',
'Regex', 'SkipTo', 'StringEnd', 'StringStart', 'Suppress', 'Token', 'TokenConverter', 'Upcase',
'White', 'Word', 'WordEnd', 'WordStart', 'ZeroOrMore',
'alphanums', 'alphas', 'alphas8bit', 'anyCloseTag', 'anyOpenTag', 'cStyleComment', 'col',
'commaSeparatedList', 'commonHTMLEntity', 'countedArray', 'cppStyleComment', 'dblQuotedString',
'dblSlashComment', 'delimitedList', 'dictOf', 'downcaseTokens', 'empty', 'getTokensEndLoc', 'hexnums',
'htmlComment', 'javaStyleComment', 'keepOriginalText', 'line', 'lineEnd', 'lineStart', 'lineno',
'makeHTMLTags', 'makeXMLTags', 'matchOnlyAtCol', 'matchPreviousExpr', 'matchPreviousLiteral',
'nestedExpr', 'nullDebugAction', 'nums', 'oneOf', 'opAssoc', 'operatorPrecedence', 'printables',
'punc8bit', 'pythonStyleComment', 'quotedString', 'removeQuotes', 'replaceHTMLEntity',
'replaceWith', 'restOfLine', 'sglQuotedString', 'srange', 'stringEnd',
'stringStart', 'traceParseAction', 'unicodeString', 'upcaseTokens', 'withAttribute',
'indentedBlock',
]


"""
Detect if we are running version 3.X and make appropriate changes
Robert A. Clark
"""
if sys.version_info[0] > 2:
    _PY3K = True
    _MAX_INT = sys.maxsize
    basestring = str
else:
    _PY3K = False
    _MAX_INT = sys.maxint

if not _PY3K:
    def _ustr(obj):
        """Drop-in replacement for str(obj) that tries to be Unicode friendly. It first tries
           str(obj). If that fails with a UnicodeEncodeError, then it tries unicode(obj). It
           then < returns the unicode object | encodes it with the default encoding | ... >.
        """
        try:
            # If this works, then _ustr(obj) has the same behaviour as str(obj), so
            # it won't break any existing code.
            return str(obj)

        except UnicodeEncodeError:
            # The Python docs (http://docs.python.org/ref/customization.html#l2h-182)
            # state that "The return value must be a string object". However, does a
            # unicode object (being a subclass of basestring) count as a "string
            # object"?
            # If so, then return a unicode object:
            return unicode(obj)
            # Else encode it... but how? There are many choices... :)
            # Replace unprintables with escape codes?
            #return unicode(obj).encode(sys.getdefaultencoding(), 'backslashreplace_errors')
            # Replace unprintables with question marks?
            #return unicode(obj).encode(sys.getdefaultencoding(), 'replace')
            # ...
else:
    _ustr = str

def _str2dict(strg):
    return dict( [(c,0) for c in strg] )
    #~ return set( [c for c in strg] )

class _Constants(object):
    pass

if not _PY3K:
    alphas     = string.lowercase + string.uppercase
else:
    alphas     = string.ascii_lowercase + string.ascii_uppercase
nums       = string.digits
hexnums    = nums + "ABCDEFabcdef"
alphanums  = alphas + nums
_bslash = "\\"
printables = "".join( [ c for c in string.printable if c not in string.whitespace ] )

class ParseBaseException(Exception):
    """base exception class for all parsing runtime exceptions"""
    __slots__ = ( "loc","msg","pstr","parserElement" )
    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, pstr, loc=0, msg=None, elem=None ):
        self.loc = loc
        if msg is None:
            self.msg = pstr
            self.pstr = ""
        else:
            self.msg = msg
            self.pstr = pstr
        self.parserElement = elem

    def __getattr__( self, aname ):
        """supported attributes by name are:
            - lineno - returns the line number of the exception text
            - col - returns the column number of the exception text
            - line - returns the line containing the exception text
        """
        if( aname == "lineno" ):
            return lineno( self.loc, self.pstr )
        elif( aname in ("col", "column") ):
            return col( self.loc, self.pstr )
        elif( aname == "line" ):
            return line( self.loc, self.pstr )
        else:
            raise AttributeError(aname)

    def __str__( self ):
        return "%s (at char %d), (line:%d, col:%d)" % \
                ( self.msg, self.loc, self.lineno, self.column )
    def __repr__( self ):
        return _ustr(self)
    def markInputline( self, markerString = ">!<" ):
        """Extracts the exception line from the input string, and marks
           the location of the exception with a special symbol.
        """
        line_str = self.line
        line_column = self.column - 1
        if markerString:
            line_str = "".join( [line_str[:line_column],
                                markerString, line_str[line_column:]])
        return line_str.strip()

class ParseException(ParseBaseException):
    """exception thrown when parse expressions don't match class;
       supported attributes by name are:
        - lineno - returns the line number of the exception text
        - col - returns the column number of the exception text
        - line - returns the line containing the exception text
    """
    pass

class ParseFatalException(ParseBaseException):
    """user-throwable exception thrown when inconsistent parse content
       is found; stops all parsing immediately"""
    pass

class ParseSyntaxException(ParseFatalException):
    """just like ParseFatalException, but thrown internally when an
       ErrorStop indicates that parsing is to stop immediately because
       an unbacktrackable syntax error has been found"""
    def __init__(self, pe):
        super(ParseSyntaxException, self).__init__(
                                    pe.pstr, pe.loc, pe.msg, pe.parserElement)

#~ class ReparseException(ParseBaseException):
    #~ """Experimental class - parse actions can raise this exception to cause
       #~ pyparsing to reparse the input string:
        #~ - with a modified input string, and/or
        #~ - with a modified start location
       #~ Set the values of the ReparseException in the constructor, and raise the
       #~ exception in a parse action to cause pyparsing to use the new string/location.
       #~ Setting the values as None causes no change to be made.
       #~ """
    #~ def __init_( self, newstring, restartLoc ):
        #~ self.newParseText = newstring
        #~ self.reparseLoc = restartLoc

class RecursiveGrammarException(Exception):
    """exception thrown by validate() if the grammar could be improperly recursive"""
    def __init__( self, parseElementList ):
        self.parseElementTrace = parseElementList

    def __str__( self ):
        return "RecursiveGrammarException: %s" % self.parseElementTrace

class _ParseResultsWithOffset(object):
    def __init__(self,p1,p2):
        self.tup = (p1,p2)
    def __getitem__(self,i):
        return self.tup[i]
    def __repr__(self):
        return repr(self.tup)

class ParseResults(object):
    """Structured parse results, to provide multiple means of access to the parsed data:
       - as a list (len(results))
       - by list index (results[0], results[1], etc.)
       - by attribute (results.<resultsName>)
       """
    __slots__ = ( "__toklist", "__tokdict", "__doinit", "__name", "__parent", "__accumNames", "__weakref__" )
    def __new__(cls, toklist, name=None, asList=True, modal=True ):
        if isinstance(toklist, cls):
            return toklist
        retobj = object.__new__(cls)
        retobj.__doinit = True
        return retobj

    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, toklist, name=None, asList=True, modal=True ):
        if self.__doinit:
            self.__doinit = False
            self.__name = None
            self.__parent = None
            self.__accumNames = {}
            if isinstance(toklist, list):
                self.__toklist = toklist[:]
            else:
                self.__toklist = [toklist]
            self.__tokdict = dict()

        # this line is related to debugging the asXML bug
        #~ asList = False

        if name:
            if not modal:
                self.__accumNames[name] = 0
            if isinstance(name,int):
                name = _ustr(name) # will always return a str, but use _ustr for consistency
            self.__name = name
            if not toklist in (None,'',[]):
                if isinstance(toklist,basestring):
                    toklist = [ toklist ]
                if asList:
                    if isinstance(toklist,ParseResults):
                        self[name] = _ParseResultsWithOffset(toklist.copy(),-1)
                    else:
                        self[name] = _ParseResultsWithOffset(ParseResults(toklist[0]),-1)
                    self[name].__name = name
                else:
                    try:
                        self[name] = toklist[0]
                    except (KeyError,TypeError):
                        self[name] = toklist

    def __getitem__( self, i ):
        if isinstance( i, (int,slice) ):
            return self.__toklist[i]
        else:
            if i not in self.__accumNames:
                return self.__tokdict[i][-1][0]
            else:
                return ParseResults([ v[0] for v in self.__tokdict[i] ])

    def __setitem__( self, k, v ):
        if isinstance(v,_ParseResultsWithOffset):
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [v]
            sub = v[0]
        elif isinstance(k,int):
            self.__toklist[k] = v
            sub = v
        else:
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [_ParseResultsWithOffset(v,0)]
            sub = v
        if isinstance(sub,ParseResults):
            sub.__parent = wkref(self)

    def __delitem__( self, i ):
        if isinstance(i,(int,slice)):
            mylen = len( self.__toklist )
            del self.__toklist[i]

            # convert int to slice
            if isinstance(i, int):
                if i < 0:
                    i += mylen
                i = slice(i, i+1)
            # get removed indices
            removed = list(range(*i.indices(mylen)))
            removed.reverse()
            # fixup indices in token dictionary
            for name in self.__tokdict:
                occurrences = self.__tokdict[name]
                for j in removed:
                    for k, (value, position) in enumerate(occurrences):
                        occurrences[k] = _ParseResultsWithOffset(value, position - (position > j))
        else:
            del self.__tokdict[i]

    def __contains__( self, k ):
        return k in self.__tokdict

    def __len__( self ): return len( self.__toklist )
    def __bool__(self): return len( self.__toklist ) > 0
    __nonzero__ = __bool__
    def __iter__( self ): return iter( self.__toklist )
    def __reversed__( self ): return iter( reversed(self.__toklist) )
    def keys( self ):
        """Returns all named result keys."""
        return self.__tokdict.keys()

    def pop( self, index=-1 ):
        """Removes and returns item at specified index (default=last).
           Will work with either numeric indices or dict-key indicies."""
        ret = self[index]
        del self[index]
        return ret

    def get(self, key, defaultValue=None):
        """Returns named result matching the given key, or if there is no
           such name, then returns the given defaultValue or None if no
           defaultValue is specified."""
        if key in self:
            return self[key]
        else:
            return defaultValue

    def insert( self, index, insStr ):
        self.__toklist.insert(index, insStr)
        # fixup indices in token dictionary
        for name in self.__tokdict:
            occurrences = self.__tokdict[name]
            for k, (value, position) in enumerate(occurrences):
                occurrences[k] = _ParseResultsWithOffset(value, position + (position > j))

    def items( self ):
        """Returns all named result keys and values as a list of tuples."""
        return [(k,self[k]) for k in self.__tokdict]

    def values( self ):
        """Returns all named result values."""
        return [ v[-1][0] for v in self.__tokdict.values() ]

    def __getattr__( self, name ):
        if name not in self.__slots__:
            if name in self.__tokdict:
                if name not in self.__accumNames:
                    return self.__tokdict[name][-1][0]
                else:
                    return ParseResults([ v[0] for v in self.__tokdict[name] ])
            else:
                return ""
        return None

    def __add__( self, other ):
        ret = self.copy()
        ret += other
        return ret

    def __iadd__( self, other ):
        if other.__tokdict:
            offset = len(self.__toklist)
            addoffset = ( lambda a: (a<0 and offset) or (a+offset) )
            otheritems = other.__tokdict.items()
            otherdictitems = [(k, _ParseResultsWithOffset(v[0],addoffset(v[1])) )
                                for (k,vlist) in otheritems for v in vlist]
            for k,v in otherdictitems:
                self[k] = v
                if isinstance(v[0],ParseResults):
                    v[0].__parent = wkref(self)
        self.__toklist += other.__toklist
        self.__accumNames.update( other.__accumNames )
        del other
        return self

    def __repr__( self ):
        return "(%s, %s)" % ( repr( self.__toklist ), repr( self.__tokdict ) )

    def __str__( self ):
        out = "["
        sep = ""
        for i in self.__toklist:
            if isinstance(i, ParseResults):
                out += sep + _ustr(i)
            else:
                out += sep + repr(i)
            sep = ", "
        out += "]"
        return out

    def _asStringList( self, sep='' ):
        out = []
        for item in self.__toklist:
            if out and sep:
                out.append(sep)
            if isinstance( item, ParseResults ):
                out += item._asStringList()
            else:
                out.append( _ustr(item) )
        return out

    def asList( self ):
        """Returns the parse results as a nested list of matching tokens, all converted to strings."""
        out = []
        for res in self.__toklist:
            if isinstance(res,ParseResults):
                out.append( res.asList() )
            else:
                out.append( res )
        return out

    def asDict( self ):
        """Returns the named parse results as dictionary."""
        return dict( self.items() )

    def copy( self ):
        """Returns a new copy of a ParseResults object."""
        ret = ParseResults( self.__toklist )
        ret.__tokdict = self.__tokdict.copy()
        ret.__parent = self.__parent
        ret.__accumNames.update( self.__accumNames )
        ret.__name = self.__name
        return ret

    def asXML( self, doctag=None, namedItemsOnly=False, indent="", formatted=True ):
        """Returns the parse results as XML. Tags are created for tokens and lists that have defined results names."""
        nl = "\n"
        out = []
        namedItems = dict( [ (v[1],k) for (k,vlist) in self.__tokdict.items()
                                                            for v in vlist ] )
        nextLevelIndent = indent + "  "

        # collapse out indents if formatting is not desired
        if not formatted:
            indent = ""
            nextLevelIndent = ""
            nl = ""

        selfTag = None
        if doctag is not None:
            selfTag = doctag
        else:
            if self.__name:
                selfTag = self.__name

        if not selfTag:
            if namedItemsOnly:
                return ""
            else:
                selfTag = "ITEM"

        out += [ nl, indent, "<", selfTag, ">" ]

        worklist = self.__toklist
        for i,res in enumerate(worklist):
            if isinstance(res,ParseResults):
                if i in namedItems:
                    out += [ res.asXML(namedItems[i],
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
                else:
                    out += [ res.asXML(None,
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
            else:
                # individual token, see if there is a name for it
                resTag = None
                if i in namedItems:
                    resTag = namedItems[i]
                if not resTag:
                    if namedItemsOnly:
                        continue
                    else:
                        resTag = "ITEM"
                xmlBodyText = xml.sax.saxutils.escape(_ustr(res))
                out += [ nl, nextLevelIndent, "<", resTag, ">",
                                                xmlBodyText,
                                                "</", resTag, ">" ]

        out += [ nl, indent, "</", selfTag, ">" ]
        return "".join(out)

    def __lookup(self,sub):
        for k,vlist in self.__tokdict.items():
            for v,loc in vlist:
                if sub is v:
                    return k
        return None

    def getName(self):
        """Returns the results name for this token expression."""
        if self.__name:
            return self.__name
        elif self.__parent:
            par = self.__parent()
            if par:
                return par.__lookup(self)
            else:
                return None
        elif (len(self) == 1 and
               len(self.__tokdict) == 1 and
               self.__tokdict.values()[0][0][1] in (0,-1)):
            return self.__tokdict.keys()[0]
        else:
            return None

    def dump(self,indent='',depth=0):
        """Diagnostic method for listing out the contents of a ParseResults.
           Accepts an optional indent argument so that this string can be embedded
           in a nested display of other data."""
        out = []
        out.append( indent+_ustr(self.asList()) )
        keys = self.items()
        keys.sort()
        for k,v in keys:
            if out:
                out.append('\n')
            out.append( "%s%s- %s: " % (indent,('  '*depth), k) )
            if isinstance(v,ParseResults):
                if v.keys():
                    #~ out.append('\n')
                    out.append( v.dump(indent,depth+1) )
                    #~ out.append('\n')
                else:
                    out.append(_ustr(v))
            else:
                out.append(_ustr(v))
        #~ out.append('\n')
        return "".join(out)

    # add support for pickle protocol
    def __getstate__(self):
        return ( self.__toklist,
                 ( self.__tokdict.copy(),
                   self.__parent is not None and self.__parent() or None,
                   self.__accumNames,
                   self.__name ) )

    def __setstate__(self,state):
        self.__toklist = state[0]
        self.__tokdict, \
        par, \
        inAccumNames, \
        self.__name = state[1]
        self.__accumNames = {}
        self.__accumNames.update(inAccumNames)
        if par is not None:
            self.__parent = wkref(par)
        else:
            self.__parent = None


def col (loc,strg):
    """Returns current column within a string, counting newlines as line separators.
   The first column is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See L{I{ParserElement.parseString}<ParserElement.parseString>} for more information
   on parsing strings containing <TAB>s, and suggested methods to maintain a
   consistent view of the parsed string, the parse location, and line and column
   positions within the parsed string.
   """
    return (loc<len(strg) and strg[loc] == '\n') and 1 or loc - strg.rfind("\n", 0, loc)

def lineno(loc,strg):
    """Returns current line number within a string, counting newlines as line separators.
   The first line is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See L{I{ParserElement.parseString}<ParserElement.parseString>} for more information
   on parsing strings containing <TAB>s, and suggested methods to maintain a
   consistent view of the parsed string, the parse location, and line and column
   positions within the parsed string.
   """
    return strg.count("\n",0,loc) + 1

def line( loc, strg ):
    """Returns the line of text containing loc within a string, counting newlines as line separators.
       """
    lastCR = strg.rfind("\n", 0, loc)
    nextCR = strg.find("\n", loc)
    if nextCR > 0:
        return strg[lastCR+1:nextCR]
    else:
        return strg[lastCR+1:]

def _defaultStartDebugAction( instring, loc, expr ):
    print ("Match " + _ustr(expr) + " at loc " + _ustr(loc) + "(%d,%d)" % ( lineno(loc,instring), col(loc,instring) ))

def _defaultSuccessDebugAction( instring, startloc, endloc, expr, toks ):
    print ("Matched " + _ustr(expr) + " -> " + str(toks.asList()))

def _defaultExceptionDebugAction( instring, loc, expr, exc ):
    print ("Exception raised:" + _ustr(exc))

def nullDebugAction(*args):
    """'Do-nothing' debug action, to suppress debugging output during parsing."""
    pass

class ParserElement(object):
    """Abstract base level parser element class."""
    DEFAULT_WHITE_CHARS = " \n\t\r"

    def setDefaultWhitespaceChars( chars ):
        """Overrides the default whitespace chars
        """
        ParserElement.DEFAULT_WHITE_CHARS = chars
    setDefaultWhitespaceChars = staticmethod(setDefaultWhitespaceChars)

    def __init__( self, savelist=False ):
        self.parseAction = list()
        self.failAction = None
        #~ self.name = "<unknown>"  # don't define self.name, let subclasses try/except upcall
        self.strRepr = None
        self.resultsName = None
        self.saveAsList = savelist
        self.skipWhitespace = True
        self.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        self.copyDefaultWhiteChars = True
        self.mayReturnEmpty = False # used when checking for left-recursion
        self.keepTabs = False
        self.ignoreExprs = list()
        self.debug = False
        self.streamlined = False
        self.mayIndexError = True # used to optimize exception handling for subclasses that don't advance parse index
        self.errmsg = ""
        self.modalResults = True # used to mark results names as modal (report only last) or cumulative (list all)
        self.debugActions = ( None, None, None ) #custom debug actions
        self.re = None
        self.callPreparse = True # used to avoid redundant calls to preParse
        self.callDuringTry = False

    def copy( self ):
        """Make a copy of this ParserElement.  Useful for defining different parse actions
           for the same parsing pattern, using copies of the original parse element."""
        cpy = copy.copy( self )
        cpy.parseAction = self.parseAction[:]
        cpy.ignoreExprs = self.ignoreExprs[:]
        if self.copyDefaultWhiteChars:
            cpy.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        return cpy

    def setName( self, name ):
        """Define name for this expression, for use in debugging."""
        self.name = name
        self.errmsg = "Expected " + self.name
        if hasattr(self,"exception"):
            self.exception.msg = self.errmsg
        return self

    def setResultsName( self, name, listAllMatches=False ):
        """Define name for referencing matching tokens as a nested attribute
           of the returned parse results.
           NOTE: this returns a *copy* of the original ParserElement object;
           this is so that the client can define a basic element, such as an
           integer, and reference it in multiple places with different names.
        """
        newself = self.copy()
        newself.resultsName = name
        newself.modalResults = not listAllMatches
        return newself

    def setBreak(self,breakFlag = True):
        """Method to invoke the Python pdb debugger when this element is
           about to be parsed. Set breakFlag to True to enable, False to
           disable.
        """
        if breakFlag:
            _parseMethod = self._parse
            def breaker(instring, loc, doActions=True, callPreParse=True):
                import pdb
                pdb.set_trace()
                _parseMethod( instring, loc, doActions, callPreParse )
            breaker._originalParseMethod = _parseMethod
            self._parse = breaker
        else:
            if hasattr(self._parse,"_originalParseMethod"):
                self._parse = self._parse._originalParseMethod
        return self

    def _normalizeParseActionArgs( f ):
        """Internal method used to decorate parse actions that take fewer than 3 arguments,
           so that all parse actions can be called as f(s,l,t)."""
        STAR_ARGS = 4

        try:
            restore = None
            if isinstance(f,type):
                restore = f
                f = f.__init__
            if not _PY3K:
                codeObj = f.func_code
            else:
                codeObj = f.code
            if codeObj.co_flags & STAR_ARGS:
                return f
            numargs = codeObj.co_argcount
            if not _PY3K:
                if hasattr(f,"im_self"):
                    numargs -= 1
            else:
                if hasattr(f,"__self__"):
                    numargs -= 1
            if restore:
                f = restore
        except AttributeError:
            try:
                if not _PY3K:
                    call_im_func_code = f.__call__.im_func.func_code
                else:
                    call_im_func_code = f.__code__

                # not a function, must be a callable object, get info from the
                # im_func binding of its bound __call__ method
                if call_im_func_code.co_flags & STAR_ARGS:
                    return f
                numargs = call_im_func_code.co_argcount
                if not _PY3K:
                    if hasattr(f.__call__,"im_self"):
                        numargs -= 1
                else:
                    if hasattr(f.__call__,"__self__"):
                        numargs -= 0
            except AttributeError:
                if not _PY3K:
                    call_func_code = f.__call__.func_code
                else:
                    call_func_code = f.__call__.__code__
                # not a bound method, get info directly from __call__ method
                if call_func_code.co_flags & STAR_ARGS:
                    return f
                numargs = call_func_code.co_argcount
                if not _PY3K:
                    if hasattr(f.__call__,"im_self"):
                        numargs -= 1
                else:
                    if hasattr(f.__call__,"__self__"):
                        numargs -= 1


        #~ print ("adding function %s with %d args" % (f.func_name,numargs))
        if numargs == 3:
            return f
        else:
            if numargs > 3:
                def tmp(s,l,t):
                    return f(f.__call__.__self__, s,l,t)
            if numargs == 2:
                def tmp(s,l,t):
                    return f(l,t)
            elif numargs == 1:
                def tmp(s,l,t):
                    return f(t)
            else: #~ numargs == 0:
                def tmp(s,l,t):
                    return f()
            try:
                tmp.__name__ = f.__name__
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            try:
                tmp.__doc__ = f.__doc__
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            try:
                tmp.__dict__.update(f.__dict__)
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            return tmp
    _normalizeParseActionArgs = staticmethod(_normalizeParseActionArgs)

    def setParseAction( self, *fns, **kwargs ):
        """Define action to perform when successfully matching parse element definition.
           Parse action fn is a callable method with 0-3 arguments, called as fn(s,loc,toks),
           fn(loc,toks), fn(toks), or just fn(), where:
            - s   = the original string being parsed (see note below)
            - loc = the location of the matching substring
            - toks = a list of the matched tokens, packaged as a ParseResults object
           If the functions in fns modify the tokens, they can return them as the return
           value from fn, and the modified list of tokens will replace the original.
           Otherwise, fn does not need to return any value.

           Note: the default parsing behavior is to expand tabs in the input string
           before starting the parsing process.  See L{I{parseString}<parseString>} for more information
           on parsing strings containing <TAB>s, and suggested methods to maintain a
           consistent view of the parsed string, the parse location, and line and column
           positions within the parsed string.
           """
        self.parseAction = list(map(self._normalizeParseActionArgs, list(fns)))
        self.callDuringTry = ("callDuringTry" in kwargs and kwargs["callDuringTry"])
        return self

    def addParseAction( self, *fns, **kwargs ):
        """Add parse action to expression's list of parse actions. See L{I{setParseAction}<setParseAction>}."""
        self.parseAction += list(map(self._normalizeParseActionArgs, list(fns)))
        self.callDuringTry = self.callDuringTry or ("callDuringTry" in kwargs and kwargs["callDuringTry"])
        return self

    def setFailAction( self, fn ):
        """Define action to perform if parsing fails at this expression.
           Fail acton fn is a callable function that takes the arguments
           fn(s,loc,expr,err) where:
            - s = string being parsed
            - loc = location where expression match was attempted and failed
            - expr = the parse expression that failed
            - err = the exception thrown
           The function returns no value.  It may throw ParseFatalException
           if it is desired to stop parsing immediately."""
        self.failAction = fn
        return self

    def _skipIgnorables( self, instring, loc ):
        exprsFound = True
        while exprsFound:
            exprsFound = False
            for e in self.ignoreExprs:
                try:
                    while 1:
                        loc,dummy = e._parse( instring, loc )
                        exprsFound = True
                except ParseException:
                    pass
        return loc

    def preParse( self, instring, loc ):
        if self.ignoreExprs:
            loc = self._skipIgnorables( instring, loc )

        if self.skipWhitespace:
            wt = self.whiteChars
            instrlen = len(instring)
            while loc < instrlen and instring[loc] in wt:
                loc += 1

        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        return loc, []

    def postParse( self, instring, loc, tokenlist ):
        return tokenlist

    #~ @profile
    def _parseNoCache( self, instring, loc, doActions=True, callPreParse=True ):
        debugging = ( self.debug ) #and doActions )

        if debugging or self.failAction:
            #~ print ("Match",self,"at loc",loc,"(%d,%d)" % ( lineno(loc,instring), col(loc,instring) ))
            if (self.debugActions[0] ):
                self.debugActions[0]( instring, loc, self )
            if callPreParse and self.callPreparse:
                preloc = self.preParse( instring, loc )
            else:
                preloc = loc
            tokensStart = loc
            try:
                try:
                    loc,tokens = self.parseImpl( instring, preloc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            except ParseBaseException, err:
                #~ print ("Exception raised:", err)
                if self.debugActions[2]:
                    self.debugActions[2]( instring, tokensStart, self, err )
                if self.failAction:
                    self.failAction( instring, tokensStart, self, err )
                raise
        else:
            if callPreParse and self.callPreparse:
                preloc = self.preParse( instring, loc )
            else:
                preloc = loc
            tokensStart = loc
            if self.mayIndexError or loc >= len(instring):
                try:
                    loc,tokens = self.parseImpl( instring, preloc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            else:
                loc,tokens = self.parseImpl( instring, preloc, doActions )

        tokens = self.postParse( instring, loc, tokens )

        retTokens = ParseResults( tokens, self.resultsName, asList=self.saveAsList, modal=self.modalResults )
        if self.parseAction and (doActions or self.callDuringTry):
            if debugging:
                try:
                    for fn in self.parseAction:
                        tokens = fn( instring, tokensStart, retTokens )
                        if tokens is not None:
                            retTokens = ParseResults( tokens,
                                                      self.resultsName,
                                                      asList=self.saveAsList and isinstance(tokens,(ParseResults,list)),
                                                      modal=self.modalResults )
                except ParseBaseException, err:
                    #~ print "Exception raised in user parse action:", err
                    if (self.debugActions[2] ):
                        self.debugActions[2]( instring, tokensStart, self, err )
                    raise
            else:
                for fn in self.parseAction:
                    tokens = fn( instring, tokensStart, retTokens )
                    if tokens is not None:
                        retTokens = ParseResults( tokens,
                                                  self.resultsName,
                                                  asList=self.saveAsList and isinstance(tokens,(ParseResults,list)),
                                                  modal=self.modalResults )

        if debugging:
            #~ print ("Matched",self,"->",retTokens.asList())
            if (self.debugActions[1] ):
                self.debugActions[1]( instring, tokensStart, loc, self, retTokens )

        return loc, retTokens

    def tryParse( self, instring, loc ):
        try:
            return self._parse( instring, loc, doActions=False )[0]
        except ParseFatalException:
            raise ParseException( instring, loc, self.errmsg, self)

    # this method gets repeatedly called during backtracking with the same arguments -
    # we can cache these arguments and save ourselves the trouble of re-parsing the contained expression
    def _parseCache( self, instring, loc, doActions=True, callPreParse=True ):
        lookup = (self,instring,loc,callPreParse,doActions)
        if lookup in ParserElement._exprArgCache:
            value = ParserElement._exprArgCache[ lookup ]
            if isinstance(value,Exception):
                raise value
            return value
        else:
            try:
                value = self._parseNoCache( instring, loc, doActions, callPreParse )
                ParserElement._exprArgCache[ lookup ] = (value[0],value[1].copy())
                return value
            except ParseBaseException, pe:
                ParserElement._exprArgCache[ lookup ] = pe
                raise

    _parse = _parseNoCache

    # argument cache for optimizing repeated calls when backtracking through recursive expressions
    _exprArgCache = {}
    def resetCache():
        ParserElement._exprArgCache.clear()
    resetCache = staticmethod(resetCache)

    _packratEnabled = False
    def enablePackrat():
        """Enables "packrat" parsing, which adds memoizing to the parsing logic.
           Repeated parse attempts at the same string location (which happens
           often in many complex grammars) can immediately return a cached value,
           instead of re-executing parsing/validating code.  Memoizing is done of
           both valid results and parsing exceptions.

           This speedup may break existing programs that use parse actions that
           have side-effects.  For this reason, packrat parsing is disabled when
           you first import pyparsing.  To activate the packrat feature, your
           program must call the class method ParserElement.enablePackrat().  If
           your program uses psyco to "compile as you go", you must call
           enablePackrat before calling psyco.full().  If you do not do this,
           Python will crash.  For best results, call enablePackrat() immediately
           after importing pyparsing.
        """
        if not ParserElement._packratEnabled:
            ParserElement._packratEnabled = True
            ParserElement._parse = ParserElement._parseCache
    enablePackrat = staticmethod(enablePackrat)

    def parseString( self, instring, parseAll=False ):
        """Execute the parse expression with the given string.
           This is the main interface to the client code, once the complete
           expression has been built.

           If you want the grammar to require that the entire input string be
           successfully parsed, then set parseAll to True (equivalent to ending
           the grammar with StringEnd()).

           Note: parseString implicitly calls expandtabs() on the input string,
           in order to report proper column numbers in parse actions.
           If the input string contains tabs and
           the grammar uses parse actions that use the loc argument to index into the
           string being parsed, you can ensure you have a consistent view of the input
           string by:
            - calling parseWithTabs on your grammar before calling parseString
              (see L{I{parseWithTabs}<parseWithTabs>})
            - define your parse action using the full (s,loc,toks) signature, and
              reference the input string using the parse action's s argument
            - explictly expand the tabs in your input string before calling
              parseString
        """
        ParserElement.resetCache()
        if not self.streamlined:
            self.streamline()
            #~ self.saveAsList = True
        for e in self.ignoreExprs:
            e.streamline()
        if not self.keepTabs:
            instring = instring.expandtabs()
        loc, tokens = self._parse( instring, 0 )
        if parseAll:
            StringEnd()._parse( instring, loc )
        return tokens

    def scanString( self, instring, maxMatches=_MAX_INT ):
        """Scan the input string for expression matches.  Each match will return the
           matching tokens, start location, and end location.  May be called with optional
           maxMatches argument, to clip scanning after 'n' matches are found.

           Note that the start and end locations are reported relative to the string
           being parsed.  See L{I{parseString}<parseString>} for more information on parsing
           strings with embedded tabs."""
        if not self.streamlined:
            self.streamline()
        for e in self.ignoreExprs:
            e.streamline()

        if not self.keepTabs:
            instring = _ustr(instring).expandtabs()
        instrlen = len(instring)
        loc = 0
        preparseFn = self.preParse
        parseFn = self._parse
        ParserElement.resetCache()
        matches = 0
        while loc <= instrlen and matches < maxMatches:
            try:
                preloc = preparseFn( instring, loc )
                nextLoc,tokens = parseFn( instring, preloc, callPreParse=False )
            except ParseException:
                loc = preloc+1
            else:
                matches += 1
                yield tokens, preloc, nextLoc
                loc = nextLoc

    def transformString( self, instring ):
        """Extension to scanString, to modify matching text with modified tokens that may
           be returned from a parse action.  To use transformString, define a grammar and
           attach a parse action to it that modifies the returned token list.
           Invoking transformString() on a target string will then scan for matches,
           and replace the matched text patterns according to the logic in the parse
           action.  transformString() returns the resulting transformed string."""
        out = []
        lastE = 0
        # force preservation of <TAB>s, to minimize unwanted transformation of string, and to
        # keep string locs straight between transformString and scanString
        self.keepTabs = True
        for t,s,e in self.scanString( instring ):
            out.append( instring[lastE:s] )
            if t:
                if isinstance(t,ParseResults):
                    out += t.asList()
                elif isinstance(t,list):
                    out += t
                else:
                    out.append(t)
            lastE = e
        out.append(instring[lastE:])
        return "".join(map(_ustr,out))

    def searchString( self, instring, maxMatches=_MAX_INT ):
        """Another extension to scanString, simplifying the access to the tokens found
           to match the given parse expression.  May be called with optional
           maxMatches argument, to clip searching after 'n' matches are found.
        """
        return ParseResults([ t for t,s,e in self.scanString( instring, maxMatches ) ])

    def __add__(self, other ):
        """Implementation of + operator - returns And"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return And( [ self, other ] )

    def __radd__(self, other ):
        """Implementation of + operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other + self

    def __sub__(self, other):
        """Implementation of - operator, returns And with error stop"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return And( [ self, And._ErrorStop(), other ] )

    def __rsub__(self, other ):
        """Implementation of - operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other - self

    def __mul__(self,other):
        if isinstance(other,int):
            minElements, optElements = other,0
        elif isinstance(other,tuple):
            if len(other)==0:
                other = (None,None)
            elif len(other)==1:
                other = (other[0],None)
            if len(other)==2:
                if other[0] is None:
                    other = (0, other[1])
                if isinstance(other[0],int) and other[1] is None:
                    if other[0] == 0:
                        return ZeroOrMore(self)
                    if other[0] == 1:
                        return OneOrMore(self)
                    else:
                        return self*other[0] + ZeroOrMore(self)
                elif isinstance(other[0],int) and isinstance(other[1],int):
                    minElements, optElements = other
                    optElements -= minElements
                else:
                    raise TypeError("cannot multiply 'ParserElement' and ('%s','%s') objects", type(other[0]),type(other[1]))
            else:
                raise TypeError("can only multiply 'ParserElement' and int or (int,int) objects")
        else:
            raise TypeError("cannot multiply 'ParserElement' and '%s' objects", type(other))

        if minElements < 0:
            raise ValueError("cannot multiply ParserElement by negative value")
        if optElements < 0:
            raise ValueError("second tuple value must be greater or equal to first tuple value")
        if minElements == optElements == 0:
            raise ValueError("cannot multiply ParserElement by 0 or (0,0)")

        if (optElements):
            def makeOptionalList(n):
                if n>1:
                    return Optional(self + makeOptionalList(n-1))
                else:
                    return Optional(self)
            if minElements:
                if minElements == 1:
                    ret = self + makeOptionalList(optElements)
                else:
                    ret = And([self]*minElements) + makeOptionalList(optElements)
            else:
                ret = makeOptionalList(optElements)
        else:
            if minElements == 1:
                ret = self
            else:
                ret = And([self]*minElements)
        return ret

    def __rmul__(self, other):
        return self.__mul__(other)

    def __or__(self, other ):
        """Implementation of | operator - returns MatchFirst"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return MatchFirst( [ self, other ] )

    def __ror__(self, other ):
        """Implementation of | operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other | self

    def __xor__(self, other ):
        """Implementation of ^ operator - returns Or"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return Or( [ self, other ] )

    def __rxor__(self, other ):
        """Implementation of ^ operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other ^ self

    def __and__(self, other ):
        """Implementation of & operator - returns Each"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return Each( [ self, other ] )

    def __rand__(self, other ):
        """Implementation of & operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other & self

    def __invert__( self ):
        """Implementation of ~ operator - returns NotAny"""
        return NotAny( self )

    def __call__(self, name):
        """Shortcut for setResultsName, with listAllMatches=default::
             userdata = Word(alphas).setResultsName("name") + Word(nums+"-").setResultsName("socsecno")
           could be written as::
             userdata = Word(alphas)("name") + Word(nums+"-")("socsecno")
           """
        return self.setResultsName(name)

    def suppress( self ):
        """Suppresses the output of this ParserElement; useful to keep punctuation from
           cluttering up returned output.
        """
        return Suppress( self )

    def leaveWhitespace( self ):
        """Disables the skipping of whitespace before matching the characters in the
           ParserElement's defined pattern.  This is normally only used internally by
           the pyparsing module, but may be needed in some whitespace-sensitive grammars.
        """
        self.skipWhitespace = False
        return self

    def setWhitespaceChars( self, chars ):
        """Overrides the default whitespace chars
        """
        self.skipWhitespace = True
        self.whiteChars = chars
        self.copyDefaultWhiteChars = False
        return self

    def parseWithTabs( self ):
        """Overrides default behavior to expand <TAB>s to spaces before parsing the input string.
           Must be called before parseString when the input grammar contains elements that
           match <TAB> characters."""
        self.keepTabs = True
        return self

    def ignore( self, other ):
        """Define expression to be ignored (e.g., comments) while doing pattern
           matching; may be called repeatedly, to define multiple comment or other
           ignorable patterns.
        """
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                self.ignoreExprs.append( other )
        else:
            self.ignoreExprs.append( Suppress( other ) )
        return self

    def setDebugActions( self, startAction, successAction, exceptionAction ):
        """Enable display of debugging messages while doing pattern matching."""
        self.debugActions = (startAction or _defaultStartDebugAction,
                             successAction or _defaultSuccessDebugAction,
                             exceptionAction or _defaultExceptionDebugAction)
        self.debug = True
        return self

    def setDebug( self, flag=True ):
        """Enable display of debugging messages while doing pattern matching.
           Set flag to True to enable, False to disable."""
        if flag:
            self.setDebugActions( _defaultStartDebugAction, _defaultSuccessDebugAction, _defaultExceptionDebugAction )
        else:
            self.debug = False
        return self

    def __str__( self ):
        return self.name

    def __repr__( self ):
        return _ustr(self)

    def streamline( self ):
        self.streamlined = True
        self.strRepr = None
        return self

    def checkRecursion( self, parseElementList ):
        pass

    def validate( self, validateTrace=[] ):
        """Check defined expressions for valid structure, check for infinite recursive definitions."""
        self.checkRecursion( [] )

    def parseFile( self, file_or_filename ):
        """Execute the parse expression on the given file or filename.
           If a filename is specified (instead of a file object),
           the entire file is opened, read, and closed before parsing.
        """
        try:
            file_contents = file_or_filename.read()
        except AttributeError:
            f = open(file_or_filename, "rb")
            file_contents = f.read()
            f.close()
        return self.parseString(file_contents)

    def getException(self):
        return ParseException("",0,self.errmsg,self)

    def __getattr__(self,aname):
        if aname == "myException":
            self.myException = ret = self.getException();
            return ret;
        else:
            raise AttributeError("no such attribute " + aname)

    def __eq__(self,other):
        if isinstance(other, basestring):
            try:
                (self + StringEnd()).parseString(_ustr(other))
                return True
            except ParseBaseException:
                return False
        else:
            return super(ParserElement,self)==other

    def __hash__(self):
        return hash(id(self))

    def __req__(self,other):
        return self == other


class Token(ParserElement):
    """Abstract ParserElement subclass, for defining atomic matching patterns."""
    def __init__( self ):
        super(Token,self).__init__( savelist=False )
        #self.myException = ParseException("",0,"",self)

    def setName(self, name):
        s = super(Token,self).setName(name)
        self.errmsg = "Expected " + self.name
        #s.myException.msg = self.errmsg
        return s


class Empty(Token):
    """An empty token, will always match."""
    def __init__( self ):
        super(Empty,self).__init__()
        self.name = "Empty"
        self.mayReturnEmpty = True
        self.mayIndexError = False


class NoMatch(Token):
    """A token that will never match."""
    def __init__( self ):
        super(NoMatch,self).__init__()
        self.name = "NoMatch"
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.errmsg = "Unmatchable token"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc


class Literal(Token):
    """Token to exactly match a specified string."""
    def __init__( self, matchString ):
        super(Literal,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Literal; use Empty() instead",
                            SyntaxWarning, stacklevel=2)
            self.__class__ = Empty
        self.name = '"%s"' % _ustr(self.match)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        #self.myException.msg = self.errmsg
        self.mayIndexError = False

    # Performance tuning: this routine gets called a *lot*
    # if this is a single character match string  and the first character matches,
    # short-circuit as quickly as possible, and avoid calling startswith
    #~ @profile
    def parseImpl( self, instring, loc, doActions=True ):
        if (instring[loc] == self.firstMatchChar and
            (self.matchLen==1 or instring.startswith(self.match,loc)) ):
            return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc
_L = Literal

class Keyword(Token):
    """Token to exactly match a specified string as a keyword, that is, it must be
       immediately followed by a non-keyword character.  Compare with Literal::
         Literal("if") will match the leading 'if' in 'ifAndOnlyIf'.
         Keyword("if") will not; it will only match the leading 'if in 'if x=1', or 'if(y==2)'
       Accepts two optional constructor arguments in addition to the keyword string:
       identChars is a string of characters that would be valid identifier characters,
       defaulting to all alphanumerics + "_" and "$"; caseless allows case-insensitive
       matching, default is False.
    """
    DEFAULT_KEYWORD_CHARS = alphanums+"_$"

    def __init__( self, matchString, identChars=DEFAULT_KEYWORD_CHARS, caseless=False ):
        super(Keyword,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Keyword; use Empty() instead",
                            SyntaxWarning, stacklevel=2)
        self.name = '"%s"' % self.match
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.caseless = caseless
        if caseless:
            self.caselessmatch = matchString.upper()
            identChars = identChars.upper()
        self.identChars = _str2dict(identChars)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.caseless:
            if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
                 (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) and
                 (loc == 0 or instring[loc-1].upper() not in self.identChars) ):
                return loc+self.matchLen, self.match
        else:
            if (instring[loc] == self.firstMatchChar and
                (self.matchLen==1 or instring.startswith(self.match,loc)) and
                (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen] not in self.identChars) and
                (loc == 0 or instring[loc-1] not in self.identChars) ):
                return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

    def copy(self):
        c = super(Keyword,self).copy()
        c.identChars = Keyword.DEFAULT_KEYWORD_CHARS
        return c

    def setDefaultKeywordChars( chars ):
        """Overrides the default Keyword chars
        """
        Keyword.DEFAULT_KEYWORD_CHARS = chars
    setDefaultKeywordChars = staticmethod(setDefaultKeywordChars)


class CaselessLiteral(Literal):
    """Token to match a specified string, ignoring case of letters.
       Note: the matched results will always be in the case of the given
       match string, NOT the case of the input text.
    """
    def __init__( self, matchString ):
        super(CaselessLiteral,self).__init__( matchString.upper() )
        # Preserve the defining literal.
        self.returnString = matchString
        self.name = "'%s'" % self.returnString
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[ loc:loc+self.matchLen ].upper() == self.match:
            return loc+self.matchLen, self.returnString
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class CaselessKeyword(Keyword):
    def __init__( self, matchString, identChars=Keyword.DEFAULT_KEYWORD_CHARS ):
        super(CaselessKeyword,self).__init__( matchString, identChars, caseless=True )

    def parseImpl( self, instring, loc, doActions=True ):
        if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
             (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) ):
            return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class Word(Token):
    """Token for matching words composed of allowed character sets.
       Defined with string containing all allowed initial characters,
       an optional string containing allowed body characters (if omitted,
       defaults to the initial character set), and an optional minimum,
       maximum, and/or exact length.  The default value for min is 1 (a
       minimum value < 1 is not valid); the default values for max and exact
       are 0, meaning no maximum or exact length restriction.
    """
    def __init__( self, initChars, bodyChars=None, min=1, max=0, exact=0, asKeyword=False ):
        super(Word,self).__init__()
        self.initCharsOrig = initChars
        self.initChars = _str2dict(initChars)
        if bodyChars :
            self.bodyCharsOrig = bodyChars
            self.bodyChars = _str2dict(bodyChars)
        else:
            self.bodyCharsOrig = initChars
            self.bodyChars = _str2dict(initChars)

        self.maxSpecified = max > 0

        if min < 1:
            raise ValueError("cannot specify a minimum length < 1; use Optional(Word()) if zero-length word is permitted")

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.asKeyword = asKeyword

        if ' ' not in self.initCharsOrig+self.bodyCharsOrig and (min==1 and max==0 and exact==0):
            if self.bodyCharsOrig == self.initCharsOrig:
                self.reString = "[%s]+" % _escapeRegexRangeChars(self.initCharsOrig)
            elif len(self.bodyCharsOrig) == 1:
                self.reString = "%s[%s]*" % \
                                      (re.escape(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            else:
                self.reString = "[%s][%s]*" % \
                                      (_escapeRegexRangeChars(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            if self.asKeyword:
                self.reString = r"\b"+self.reString+r"\b"
            try:
                self.re = re.compile( self.reString )
            except:
                self.re = None

    def parseImpl( self, instring, loc, doActions=True ):
        if self.re:
            result = self.re.match(instring,loc)
            if not result:
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc

            loc = result.end()
            return loc,result.group()

        if not(instring[ loc ] in self.initChars):
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        start = loc
        loc += 1
        instrlen = len(instring)
        bodychars = self.bodyChars
        maxloc = start + self.maxLen
        maxloc = min( maxloc, instrlen )
        while loc < maxloc and instring[loc] in bodychars:
            loc += 1

        throwException = False
        if loc - start < self.minLen:
            throwException = True
        if self.maxSpecified and loc < instrlen and instring[loc] in bodychars:
            throwException = True
        if self.asKeyword:
            if (start>0 and instring[start-1] in bodychars) or (loc<instrlen and instring[loc] in bodychars):
                throwException = True

        if throwException:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(Word,self).__str__()
        except:
            pass


        if self.strRepr is None:

            def charsAsStr(s):
                if len(s)>4:
                    return s[:4]+"..."
                else:
                    return s

            if ( self.initCharsOrig != self.bodyCharsOrig ):
                self.strRepr = "W:(%s,%s)" % ( charsAsStr(self.initCharsOrig), charsAsStr(self.bodyCharsOrig) )
            else:
                self.strRepr = "W:(%s)" % charsAsStr(self.initCharsOrig)

        return self.strRepr


class Regex(Token):
    """Token for matching strings that match a given regular expression.
       Defined with string specifying the regular expression in a form recognized by the inbuilt Python re module.
    """
    def __init__( self, pattern, flags=0):
        """The parameters pattern and flags are passed to the re.compile() function as-is. See the Python re module for an explanation of the acceptable patterns and flags."""
        super(Regex,self).__init__()

        if len(pattern) == 0:
            warnings.warn("null string passed to Regex; use Empty() instead",
                    SyntaxWarning, stacklevel=2)

        self.pattern = pattern
        self.flags = flags

        try:
            self.re = re.compile(self.pattern, self.flags)
            self.reString = self.pattern
        except sre_constants.error:
            warnings.warn("invalid pattern (%s) passed to Regex" % pattern,
                SyntaxWarning, stacklevel=2)
            raise

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        result = self.re.match(instring,loc)
        if not result:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        loc = result.end()
        d = result.groupdict()
        ret = ParseResults(result.group())
        if d:
            for k in d:
                ret[k] = d[k]
        return loc,ret

    def __str__( self ):
        try:
            return super(Regex,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "Re:(%s)" % repr(self.pattern)

        return self.strRepr


class QuotedString(Token):
    """Token for matching strings that are delimited by quoting characters.
    """
    def __init__( self, quoteChar, escChar=None, escQuote=None, multiline=False, unquoteResults=True, endQuoteChar=None):
        """
           Defined with the following parameters:
            - quoteChar - string of one or more characters defining the quote delimiting string
            - escChar - character to escape quotes, typically backslash (default=None)
            - escQuote - special quote sequence to escape an embedded quote string (such as SQL's "" to escape an embedded ") (default=None)
            - multiline - boolean indicating whether quotes can span multiple lines (default=False)
            - unquoteResults - boolean indicating whether the matched text should be unquoted (default=True)
            - endQuoteChar - string of one or more characters defining the end of the quote delimited string (default=None => same as quoteChar)
        """
        super(QuotedString,self).__init__()

        # remove white space from quote chars - wont work anyway
        quoteChar = quoteChar.strip()
        if len(quoteChar) == 0:
            warnings.warn("quoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
            raise SyntaxError()

        if endQuoteChar is None:
            endQuoteChar = quoteChar
        else:
            endQuoteChar = endQuoteChar.strip()
            if len(endQuoteChar) == 0:
                warnings.warn("endQuoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
                raise SyntaxError()

        self.quoteChar = quoteChar
        self.quoteCharLen = len(quoteChar)
        self.firstQuoteChar = quoteChar[0]
        self.endQuoteChar = endQuoteChar
        self.endQuoteCharLen = len(endQuoteChar)
        self.escChar = escChar
        self.escQuote = escQuote
        self.unquoteResults = unquoteResults

        if multiline:
            self.flags = re.MULTILINE | re.DOTALL
            self.pattern = r'%s(?:[^%s%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        else:
            self.flags = 0
            self.pattern = r'%s(?:[^%s\n\r%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        if len(self.endQuoteChar) > 1:
            self.pattern += (
                '|(?:' + ')|(?:'.join(["%s[^%s]" % (re.escape(self.endQuoteChar[:i]),
                                               _escapeRegexRangeChars(self.endQuoteChar[i]))
                                    for i in range(len(self.endQuoteChar)-1,0,-1)]) + ')'
                )
        if escQuote:
            self.pattern += (r'|(?:%s)' % re.escape(escQuote))
        if escChar:
            self.pattern += (r'|(?:%s.)' % re.escape(escChar))
            self.escCharReplacePattern = re.escape(self.escChar)+"(.)"
        self.pattern += (r')*%s' % re.escape(self.endQuoteChar))

        try:
            self.re = re.compile(self.pattern, self.flags)
            self.reString = self.pattern
        except sre_constants.error:
            warnings.warn("invalid pattern (%s) passed to Regex" % self.pattern,
                SyntaxWarning, stacklevel=2)
            raise

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        result = instring[loc] == self.firstQuoteChar and self.re.match(instring,loc) or None
        if not result:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        loc = result.end()
        ret = result.group()

        if self.unquoteResults:

            # strip off quotes
            ret = ret[self.quoteCharLen:-self.endQuoteCharLen]

            if isinstance(ret,basestring):
                # replace escaped characters
                if self.escChar:
                    ret = re.sub(self.escCharReplacePattern,"\g<1>",ret)

                # replace escaped quotes
                if self.escQuote:
                    ret = ret.replace(self.escQuote, self.endQuoteChar)

        return loc, ret

    def __str__( self ):
        try:
            return super(QuotedString,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "quoted string, starting with %s ending with %s" % (self.quoteChar, self.endQuoteChar)

        return self.strRepr


class CharsNotIn(Token):
    """Token for matching words composed of characters *not* in a given set.
       Defined with string containing all disallowed characters, and an optional
       minimum, maximum, and/or exact length.  The default value for min is 1 (a
       minimum value < 1 is not valid); the default values for max and exact
       are 0, meaning no maximum or exact length restriction.
    """
    def __init__( self, notChars, min=1, max=0, exact=0 ):
        super(CharsNotIn,self).__init__()
        self.skipWhitespace = False
        self.notChars = notChars

        if min < 1:
            raise ValueError("cannot specify a minimum length < 1; use Optional(CharsNotIn()) if zero-length char group is permitted")

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = ( self.minLen == 0 )
        #self.myException.msg = self.errmsg
        self.mayIndexError = False

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[loc] in self.notChars:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        start = loc
        loc += 1
        notchars = self.notChars
        maxlen = min( start+self.maxLen, len(instring) )
        while loc < maxlen and \
              (instring[loc] not in notchars):
            loc += 1

        if loc - start < self.minLen:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(CharsNotIn, self).__str__()
        except:
            pass

        if self.strRepr is None:
            if len(self.notChars) > 4:
                self.strRepr = "!W:(%s...)" % self.notChars[:4]
            else:
                self.strRepr = "!W:(%s)" % self.notChars

        return self.strRepr

class White(Token):
    """Special matching class for matching whitespace.  Normally, whitespace is ignored
       by pyparsing grammars.  This class is included when some whitespace structures
       are significant.  Define with a string containing the whitespace characters to be
       matched; default is " \\t\\n".  Also takes optional min, max, and exact arguments,
       as defined for the Word class."""
    whiteStrs = {
        " " : "<SPC>",
        "\t": "<TAB>",
        "\n": "<LF>",
        "\r": "<CR>",
        "\f": "<FF>",
        }
    def __init__(self, ws=" \t\r\n", min=1, max=0, exact=0):
        super(White,self).__init__()
        self.matchWhite = ws
        self.setWhitespaceChars( "".join([c for c in self.whiteChars if c not in self.matchWhite]) )
        #~ self.leaveWhitespace()
        self.name = ("".join([White.whiteStrs[c] for c in self.matchWhite]))
        self.mayReturnEmpty = True
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

    def parseImpl( self, instring, loc, doActions=True ):
        if not(instring[ loc ] in self.matchWhite):
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        start = loc
        loc += 1
        maxloc = start + self.maxLen
        maxloc = min( maxloc, len(instring) )
        while loc < maxloc and instring[loc] in self.matchWhite:
            loc += 1

        if loc - start < self.minLen:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]


class _PositionToken(Token):
    def __init__( self ):
        super(_PositionToken,self).__init__()
        self.name=self.__class__.__name__
        self.mayReturnEmpty = True
        self.mayIndexError = False

class GoToColumn(_PositionToken):
    """Token to advance to a specific column of input text; useful for tabular report scraping."""
    def __init__( self, colno ):
        super(GoToColumn,self).__init__()
        self.col = colno

    def preParse( self, instring, loc ):
        if col(loc,instring) != self.col:
            instrlen = len(instring)
            if self.ignoreExprs:
                loc = self._skipIgnorables( instring, loc )
            while loc < instrlen and instring[loc].isspace() and col( loc, instring ) != self.col :
                loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        thiscol = col( loc, instring )
        if thiscol > self.col:
            raise ParseException( instring, loc, "Text not in expected column", self )
        newloc = loc + self.col - thiscol
        ret = instring[ loc: newloc ]
        return newloc, ret

class LineStart(_PositionToken):
    """Matches if current position is at the beginning of a line within the parse string"""
    def __init__( self ):
        super(LineStart,self).__init__()
        self.setWhitespaceChars( " \t" )
        self.errmsg = "Expected start of line"
        #self.myException.msg = self.errmsg

    def preParse( self, instring, loc ):
        preloc = super(LineStart,self).preParse(instring,loc)
        if instring[preloc] == "\n":
            loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        if not( loc==0 or
            (loc == self.preParse( instring, 0 )) or
            (instring[loc-1] == "\n") ): #col(loc, instring) != 1:
            #~ raise ParseException( instring, loc, "Expected start of line" )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        return loc, []

class LineEnd(_PositionToken):
    """Matches if current position is at the end of a line within the parse string"""
    def __init__( self ):
        super(LineEnd,self).__init__()
        self.setWhitespaceChars( " \t" )
        self.errmsg = "Expected end of line"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc<len(instring):
            if instring[loc] == "\n":
                return loc+1, "\n"
            else:
                #~ raise ParseException( instring, loc, "Expected end of line" )
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        elif loc == len(instring):
            return loc+1, []
        else:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

class StringStart(_PositionToken):
    """Matches if current position is at the beginning of the parse string"""
    def __init__( self ):
        super(StringStart,self).__init__()
        self.errmsg = "Expected start of text"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc != 0:
            # see if entire string up to here is just whitespace and ignoreables
            if loc != self.preParse( instring, 0 ):
                #~ raise ParseException( instring, loc, "Expected start of text" )
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        return loc, []

class StringEnd(_PositionToken):
    """Matches if current position is at the end of the parse string"""
    def __init__( self ):
        super(StringEnd,self).__init__()
        self.errmsg = "Expected end of text"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc < len(instring):
            #~ raise ParseException( instring, loc, "Expected end of text" )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        elif loc == len(instring):
            return loc+1, []
        elif loc > len(instring):
            return loc, []
        else:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

class WordStart(_PositionToken):
    """Matches if the current position is at the beginning of a Word, and
       is not preceded by any character in a given set of wordChars
       (default=printables). To emulate the \b behavior of regular expressions,
       use WordStart(alphanums). WordStart will also match at the beginning of
       the string being parsed, or at the beginning of a line.
    """
    def __init__(self, wordChars = printables):
        super(WordStart,self).__init__()
        self.wordChars = _str2dict(wordChars)
        self.errmsg = "Not at the start of a word"

    def parseImpl(self, instring, loc, doActions=True ):
        if loc != 0:
            if (instring[loc-1] in self.wordChars or
                instring[loc] not in self.wordChars):
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        return loc, []

class WordEnd(_PositionToken):
    """Matches if the current position is at the end of a Word, and
       is not followed by any character in a given set of wordChars
       (default=printables). To emulate the \b behavior of regular expressions,
       use WordEnd(alphanums). WordEnd will also match at the end of
       the string being parsed, or at the end of a line.
    """
    def __init__(self, wordChars = printables):
        super(WordEnd,self).__init__()
        self.wordChars = _str2dict(wordChars)
        self.skipWhitespace = False
        self.errmsg = "Not at the end of a word"

    def parseImpl(self, instring, loc, doActions=True ):
        instrlen = len(instring)
        if instrlen>0 and loc<instrlen:
            if (instring[loc] in self.wordChars or
                instring[loc-1] not in self.wordChars):
                #~ raise ParseException( instring, loc, "Expected end of word" )
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        return loc, []


class ParseExpression(ParserElement):
    """Abstract subclass of ParserElement, for combining and post-processing parsed tokens."""
    def __init__( self, exprs, savelist = False ):
        super(ParseExpression,self).__init__(savelist)
        if isinstance( exprs, list ):
            self.exprs = exprs
        elif isinstance( exprs, basestring ):
            self.exprs = [ Literal( exprs ) ]
        else:
            self.exprs = [ exprs ]
        self.callPreparse = False

    def __getitem__( self, i ):
        return self.exprs[i]

    def append( self, other ):
        self.exprs.append( other )
        self.strRepr = None
        return self

    def leaveWhitespace( self ):
        """Extends leaveWhitespace defined in base class, and also invokes leaveWhitespace on
           all contained expressions."""
        self.skipWhitespace = False
        self.exprs = [ e.copy() for e in self.exprs ]
        for e in self.exprs:
            e.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseExpression, self).ignore( other )
                for e in self.exprs:
                    e.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseExpression, self).ignore( other )
            for e in self.exprs:
                e.ignore( self.ignoreExprs[-1] )
        return self

    def __str__( self ):
        try:
            return super(ParseExpression,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.exprs) )
        return self.strRepr

    def streamline( self ):
        super(ParseExpression,self).streamline()

        for e in self.exprs:
            e.streamline()

        # collapse nested And's of the form And( And( And( a,b), c), d) to And( a,b,c,d )
        # but only if there are no parse actions or resultsNames on the nested And's
        # (likewise for Or's and MatchFirst's)
        if ( len(self.exprs) == 2 ):
            other = self.exprs[0]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = other.exprs[:] + [ self.exprs[1] ]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError  |= other.mayIndexError

            other = self.exprs[-1]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = self.exprs[:-1] + other.exprs[:]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError  |= other.mayIndexError

        return self

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(ParseExpression,self).setResultsName(name,listAllMatches)
        return ret

    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        for e in self.exprs:
            e.validate(tmp)
        self.checkRecursion( [] )

class And(ParseExpression):
    """Requires all given ParseExpressions to be found in the given order.
       Expressions may be separated by whitespace.
       May be constructed using the '+' operator.
    """

    class _ErrorStop(Empty):
        def __new__(cls,*args,**kwargs):
            return And._ErrorStop.instance
    _ErrorStop.instance = Empty()
    _ErrorStop.instance.leaveWhitespace()

    def __init__( self, exprs, savelist = True ):
        super(And,self).__init__(exprs, savelist)
        self.mayReturnEmpty = True
        for e in self.exprs:
            if not e.mayReturnEmpty:
                self.mayReturnEmpty = False
                break
        self.setWhitespaceChars( exprs[0].whiteChars )
        self.skipWhitespace = exprs[0].skipWhitespace
        self.callPreparse = True

    def parseImpl( self, instring, loc, doActions=True ):
        # pass False as last arg to _parse for first element, since we already
        # pre-parsed the string as part of our And pre-parsing
        loc, resultlist = self.exprs[0]._parse( instring, loc, doActions, callPreParse=False )
        errorStop = False
        for e in self.exprs[1:]:
            if e is And._ErrorStop.instance:
                errorStop = True
                continue
            if errorStop:
                try:
                    loc, exprtokens = e._parse( instring, loc, doActions )
                except ParseBaseException, pe:
                    raise ParseSyntaxException(pe)
                except IndexError, ie:
                    raise ParseSyntaxException( ParseException(instring, len(instring), self.errmsg, self) )
            else:
                loc, exprtokens = e._parse( instring, loc, doActions )
            if exprtokens or exprtokens.keys():
                resultlist += exprtokens
        return loc, resultlist

    def __iadd__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #And( [ self, other ] )

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )
            if not e.mayReturnEmpty:
                break

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr


class Or(ParseExpression):
    """Requires that at least one ParseExpression is found.
       If two expressions match, the expression that matches the longest string will be used.
       May be constructed using the '^' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(Or,self).__init__(exprs, savelist)
        self.mayReturnEmpty = False
        for e in self.exprs:
            if e.mayReturnEmpty:
                self.mayReturnEmpty = True
                break

    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        maxMatchLoc = -1
        maxException = None
        for e in self.exprs:
            try:
                loc2 = e.tryParse( instring, loc )
            except ParseException, err:
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)
            else:
                if loc2 > maxMatchLoc:
                    maxMatchLoc = loc2
                    maxMatchExp = e

        if maxMatchLoc < 0:
            if maxException is not None:
                raise maxException
            else:
                raise ParseException(instring, loc, "no defined alternatives to match", self)

        return maxMatchExp._parse( instring, loc, doActions )

    def __ixor__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #Or( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ^ ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class MatchFirst(ParseExpression):
    """Requires that at least one ParseExpression is found.
       If two expressions match, the first one listed is the one that will match.
       May be constructed using the '|' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(MatchFirst,self).__init__(exprs, savelist)
        if exprs:
            self.mayReturnEmpty = False
            for e in self.exprs:
                if e.mayReturnEmpty:
                    self.mayReturnEmpty = True
                    break
        else:
            self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        maxException = None
        for e in self.exprs:
            try:
                ret = e._parse( instring, loc, doActions )
                return ret
            except ParseException, err:
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)

        # only got here if no expression matched, raise exception for match that made it the furthest
        else:
            if maxException is not None:
                raise maxException
            else:
                raise ParseException(instring, loc, "no defined alternatives to match", self)

    def __ior__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #MatchFirst( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " | ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class Each(ParseExpression):
    """Requires all given ParseExpressions to be found, but in any order.
       Expressions may be separated by whitespace.
       May be constructed using the '&' operator.
    """
    def __init__( self, exprs, savelist = True ):
        super(Each,self).__init__(exprs, savelist)
        self.mayReturnEmpty = True
        for e in self.exprs:
            if not e.mayReturnEmpty:
                self.mayReturnEmpty = False
                break
        self.skipWhitespace = True
        self.initExprGroups = True

    def parseImpl( self, instring, loc, doActions=True ):
        if self.initExprGroups:
            self.optionals = [ e.expr for e in self.exprs if isinstance(e,Optional) ]
            self.multioptionals = [ e.expr for e in self.exprs if isinstance(e,ZeroOrMore) ]
            self.multirequired = [ e.expr for e in self.exprs if isinstance(e,OneOrMore) ]
            self.required = [ e for e in self.exprs if not isinstance(e,(Optional,ZeroOrMore,OneOrMore)) ]
            self.required += self.multirequired
            self.initExprGroups = False
        tmpLoc = loc
        tmpReqd = self.required[:]
        tmpOpt  = self.optionals[:]
        matchOrder = []

        keepMatching = True
        while keepMatching:
            tmpExprs = tmpReqd + tmpOpt + self.multioptionals + self.multirequired
            failed = []
            for e in tmpExprs:
                try:
                    tmpLoc = e.tryParse( instring, tmpLoc )
                except ParseException:
                    failed.append(e)
                else:
                    matchOrder.append(e)
                    if e in tmpReqd:
                        tmpReqd.remove(e)
                    elif e in tmpOpt:
                        tmpOpt.remove(e)
            if len(failed) == len(tmpExprs):
                keepMatching = False

        if tmpReqd:
            missing = ", ".join( [ _ustr(e) for e in tmpReqd ] )
            raise ParseException(instring,loc,"Missing one or more required elements (%s)" % missing )

        # add any unmatched Optionals, in case they have default values defined
        matchOrder += list(e for e in self.exprs if isinstance(e,Optional) and e.expr in tmpOpt)

        resultlist = []
        for e in matchOrder:
            loc,results = e._parse(instring,loc,doActions)
            resultlist.append(results)

        finalResults = ParseResults([])
        for r in resultlist:
            dups = {}
            for k in r.keys():
                if k in finalResults.keys():
                    tmp = ParseResults(finalResults[k])
                    tmp += ParseResults(r[k])
                    dups[k] = tmp
            finalResults += ParseResults(r)
            for k,v in dups.items():
                finalResults[k] = v
        return loc, finalResults

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " & ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class ParseElementEnhance(ParserElement):
    """Abstract subclass of ParserElement, for combining and post-processing parsed tokens."""
    def __init__( self, expr, savelist=False ):
        super(ParseElementEnhance,self).__init__(savelist)
        if isinstance( expr, basestring ):
            expr = Literal(expr)
        self.expr = expr
        self.strRepr = None
        if expr is not None:
            self.mayIndexError = expr.mayIndexError
            self.mayReturnEmpty = expr.mayReturnEmpty
            self.setWhitespaceChars( expr.whiteChars )
            self.skipWhitespace = expr.skipWhitespace
            self.saveAsList = expr.saveAsList
            self.callPreparse = expr.callPreparse
            self.ignoreExprs.extend(expr.ignoreExprs)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.expr is not None:
            return self.expr._parse( instring, loc, doActions, callPreParse=False )
        else:
            raise ParseException("",loc,self.errmsg,self)

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        self.expr = self.expr.copy()
        if self.expr is not None:
            self.expr.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseElementEnhance, self).ignore( other )
                if self.expr is not None:
                    self.expr.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseElementEnhance, self).ignore( other )
            if self.expr is not None:
                self.expr.ignore( self.ignoreExprs[-1] )
        return self

    def streamline( self ):
        super(ParseElementEnhance,self).streamline()
        if self.expr is not None:
            self.expr.streamline()
        return self

    def checkRecursion( self, parseElementList ):
        if self in parseElementList:
            raise RecursiveGrammarException( parseElementList+[self] )
        subRecCheckList = parseElementList[:] + [ self ]
        if self.expr is not None:
            self.expr.checkRecursion( subRecCheckList )

    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        if self.expr is not None:
            self.expr.validate(tmp)
        self.checkRecursion( [] )

    def __str__( self ):
        try:
            return super(ParseElementEnhance,self).__str__()
        except:
            pass

        if self.strRepr is None and self.expr is not None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.expr) )
        return self.strRepr


class FollowedBy(ParseElementEnhance):
    """Lookahead matching of the given parse expression.  FollowedBy
    does *not* advance the parsing position within the input string, it only
    verifies that the specified parse expression matches at the current
    position.  FollowedBy always returns a null token list."""
    def __init__( self, expr ):
        super(FollowedBy,self).__init__(expr)
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        self.expr.tryParse( instring, loc )
        return loc, []


class NotAny(ParseElementEnhance):
    """Lookahead to disallow matching with the given parse expression.  NotAny
    does *not* advance the parsing position within the input string, it only
    verifies that the specified parse expression does *not* match at the current
    position.  Also, NotAny does *not* skip over leading whitespace. NotAny
    always returns a null token list.  May be constructed using the '~' operator."""
    def __init__( self, expr ):
        super(NotAny,self).__init__(expr)
        #~ self.leaveWhitespace()
        self.skipWhitespace = False  # do NOT use self.leaveWhitespace(), don't want to propagate to exprs
        self.mayReturnEmpty = True
        self.errmsg = "Found unwanted token, "+_ustr(self.expr)
        #self.myException = ParseException("",0,self.errmsg,self)

    def parseImpl( self, instring, loc, doActions=True ):
        try:
            self.expr.tryParse( instring, loc )
        except (ParseException,IndexError):
            pass
        else:
            #~ raise ParseException(instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        return loc, []

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "~{" + _ustr(self.expr) + "}"

        return self.strRepr


class ZeroOrMore(ParseElementEnhance):
    """Optional repetition of zero or more of the given expression."""
    def __init__( self, expr ):
        super(ZeroOrMore,self).__init__(expr)
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        tokens = []
        try:
            loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    preloc = self._skipIgnorables( instring, loc )
                else:
                    preloc = loc
                loc, tmptokens = self.expr._parse( instring, preloc, doActions )
                if tmptokens or tmptokens.keys():
                    tokens += tmptokens
        except (ParseException,IndexError):
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]..."

        return self.strRepr

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(ZeroOrMore,self).setResultsName(name,listAllMatches)
        ret.saveAsList = True
        return ret


class OneOrMore(ParseElementEnhance):
    """Repetition of one or more of the given expression."""
    def parseImpl( self, instring, loc, doActions=True ):
        # must be at least one
        loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
        try:
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    preloc = self._skipIgnorables( instring, loc )
                else:
                    preloc = loc
                loc, tmptokens = self.expr._parse( instring, preloc, doActions )
                if tmptokens or tmptokens.keys():
                    tokens += tmptokens
        except (ParseException,IndexError):
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + _ustr(self.expr) + "}..."

        return self.strRepr

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(OneOrMore,self).setResultsName(name,listAllMatches)
        ret.saveAsList = True
        return ret

class _NullToken(object):
    def __bool__(self):
        return False
    __nonzero__ = __bool__
    def __str__(self):
        return ""

_optionalNotMatched = _NullToken()
class Optional(ParseElementEnhance):
    """Optional matching of the given expression.
       A default return string can also be specified, if the optional expression
       is not found.
    """
    def __init__( self, exprs, default=_optionalNotMatched ):
        super(Optional,self).__init__( exprs, savelist=False )
        self.defaultValue = default
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        try:
            loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
        except (ParseException,IndexError):
            if self.defaultValue is not _optionalNotMatched:
                if self.expr.resultsName:
                    tokens = ParseResults([ self.defaultValue ])
                    tokens[self.expr.resultsName] = self.defaultValue
                else:
                    tokens = [ self.defaultValue ]
            else:
                tokens = []
        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]"

        return self.strRepr


class SkipTo(ParseElementEnhance):
    """Token for skipping over all undefined text until the matched expression is found.
       If include is set to true, the matched expression is also consumed.  The ignore
       argument is used to define grammars (typically quoted strings and comments) that
       might contain false matches.
    """
    def __init__( self, other, include=False, ignore=None ):
        super( SkipTo, self ).__init__( other )
        if ignore is not None:
            self.expr = self.expr.copy()
            self.expr.ignore(ignore)
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.includeMatch = include
        self.asList = False
        self.errmsg = "No match found for "+_ustr(self.expr)
        #self.myException = ParseException("",0,self.errmsg,self)

    def parseImpl( self, instring, loc, doActions=True ):
        startLoc = loc
        instrlen = len(instring)
        expr = self.expr
        while loc <= instrlen:
            try:
                loc = expr._skipIgnorables( instring, loc )
                expr._parse( instring, loc, doActions=False, callPreParse=False )
                if self.includeMatch:
                    skipText = instring[startLoc:loc]
                    loc,mat = expr._parse(instring,loc,doActions,callPreParse=False)
                    if mat:
                        skipRes = ParseResults( skipText )
                        skipRes += mat
                        return loc, [ skipRes ]
                    else:
                        return loc, [ skipText ]
                else:
                    return loc, [ instring[startLoc:loc] ]
            except (ParseException,IndexError):
                loc += 1
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class Forward(ParseElementEnhance):
    """Forward declaration of an expression to be defined later -
       used for recursive grammars, such as algebraic infix notation.
       When the expression is known, it is assigned to the Forward variable using the '<<' operator.

       Note: take care when assigning to Forward not to overlook precedence of operators.
       Specifically, '|' has a lower precedence than '<<', so that::
          fwdExpr << a | b | c
       will actually be evaluated as::
          (fwdExpr << a) | b | c
       thereby leaving b and c out as parseable alternatives.  It is recommended that you
       explicitly group the values inserted into the Forward::
          fwdExpr << (a | b | c)
    """
    def __init__( self, other=None ):
        super(Forward,self).__init__( other, savelist=False )

    def __lshift__( self, other ):
        if isinstance( other, basestring ):
            other = Literal(other)
        self.expr = other
        self.mayReturnEmpty = other.mayReturnEmpty
        self.strRepr = None
        self.mayIndexError = self.expr.mayIndexError
        self.mayReturnEmpty = self.expr.mayReturnEmpty
        self.setWhitespaceChars( self.expr.whiteChars )
        self.skipWhitespace = self.expr.skipWhitespace
        self.saveAsList = self.expr.saveAsList
        self.ignoreExprs.extend(self.expr.ignoreExprs)
        return None

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        return self

    def streamline( self ):
        if not self.streamlined:
            self.streamlined = True
            if self.expr is not None:
                self.expr.streamline()
        return self

    def validate( self, validateTrace=[] ):
        if self not in validateTrace:
            tmp = validateTrace[:]+[self]
            if self.expr is not None:
                self.expr.validate(tmp)
        self.checkRecursion([])

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        self.__class__ = _ForwardNoRecurse
        try:
            if self.expr is not None:
                retString = _ustr(self.expr)
            else:
                retString = "None"
        finally:
            self.__class__ = Forward
        return "Forward: "+retString

    def copy(self):
        if self.expr is not None:
            return super(Forward,self).copy()
        else:
            ret = Forward()
            ret << self
            return ret

class _ForwardNoRecurse(Forward):
    def __str__( self ):
        return "..."

class TokenConverter(ParseElementEnhance):
    """Abstract subclass of ParseExpression, for converting parsed results."""
    def __init__( self, expr, savelist=False ):
        super(TokenConverter,self).__init__( expr )#, savelist )
        self.saveAsList = False

class Upcase(TokenConverter):
    """Converter to upper case all matching tokens."""
    def __init__(self, *args):
        super(Upcase,self).__init__(*args)
        warnings.warn("Upcase class is deprecated, use upcaseTokens parse action instead",
                       DeprecationWarning,stacklevel=2)

    def postParse( self, instring, loc, tokenlist ):
        return list(map( string.upper, tokenlist ))


class Combine(TokenConverter):
    """Converter to concatenate all matching tokens to a single string.
       By default, the matching patterns must also be contiguous in the input string;
       this can be disabled by specifying 'adjacent=False' in the constructor.
    """
    def __init__( self, expr, joinString="", adjacent=True ):
        super(Combine,self).__init__( expr )
        # suppress whitespace-stripping in contained parse expressions, but re-enable it on the Combine itself
        if adjacent:
            self.leaveWhitespace()
        self.adjacent = adjacent
        self.skipWhitespace = True
        self.joinString = joinString

    def ignore( self, other ):
        if self.adjacent:
            ParserElement.ignore(self, other)
        else:
            super( Combine, self).ignore( other )
        return self

    def postParse( self, instring, loc, tokenlist ):
        retToks = tokenlist.copy()
        del retToks[:]
        retToks += ParseResults([ "".join(tokenlist._asStringList(self.joinString)) ], modal=self.modalResults)

        if self.resultsName and len(retToks.keys())>0:
            return [ retToks ]
        else:
            return retToks

class Group(TokenConverter):
    """Converter to return the matched tokens as a list - useful for returning tokens of ZeroOrMore and OneOrMore expressions."""
    def __init__( self, expr ):
        super(Group,self).__init__( expr )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        return [ tokenlist ]

class Dict(TokenConverter):
    """Converter to return a repetitive expression as a list, but also as a dictionary.
       Each element can also be referenced using the first token in the expression as its key.
       Useful for tabular report scraping when the first column can be used as a item key.
    """
    def __init__( self, exprs ):
        super(Dict,self).__init__( exprs )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        for i,tok in enumerate(tokenlist):
            if len(tok) == 0:
                continue
            ikey = tok[0]
            if isinstance(ikey,int):
                ikey = _ustr(tok[0]).strip()
            if len(tok)==1:
                tokenlist[ikey] = _ParseResultsWithOffset("",i)
            elif len(tok)==2 and not isinstance(tok[1],ParseResults):
                tokenlist[ikey] = _ParseResultsWithOffset(tok[1],i)
            else:
                dictvalue = tok.copy() #ParseResults(i)
                del dictvalue[0]
                if len(dictvalue)!= 1 or (isinstance(dictvalue,ParseResults) and dictvalue.keys()):
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue,i)
                else:
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue[0],i)

        if self.resultsName:
            return [ tokenlist ]
        else:
            return tokenlist


class Suppress(TokenConverter):
    """Converter for ignoring the results of a parsed expression."""
    def postParse( self, instring, loc, tokenlist ):
        return []

    def suppress( self ):
        return self


class OnlyOnce(object):
    """Wrapper for parse actions, to ensure they are only called once."""
    def __init__(self, methodCall):
        self.callable = ParserElement._normalizeParseActionArgs(methodCall)
        self.called = False
    def __call__(self,s,l,t):
        if not self.called:
            results = self.callable(s,l,t)
            self.called = True
            return results
        raise ParseException(s,l,"")
    def reset(self):
        self.called = False

def traceParseAction(f):
    """Decorator for debugging parse actions."""
    f = ParserElement._normalizeParseActionArgs(f)
    def z(*paArgs):
        thisFunc = f.func_name
        s,l,t = paArgs[-3:]
        if len(paArgs)>3:
            thisFunc = paArgs[0].__class__.__name__ + '.' + thisFunc
        sys.stderr.write( ">>entering %s(line: '%s', %d, %s)\n" % (thisFunc,line(l,s),l,t) )
        try:
            ret = f(*paArgs)
        except Exception, exc:
            sys.stderr.write( "<<leaving %s (exception: %s)\n" % (thisFunc,exc) )
            raise
        sys.stderr.write( "<<leaving %s (ret: %s)\n" % (thisFunc,ret) )
        return ret
    try:
        z.__name__ = f.__name__
    except AttributeError:
        pass
    return z

#
# global helpers
#
def delimitedList( expr, delim=",", combine=False ):
    """Helper to define a delimited list of expressions - the delimiter defaults to ','.
       By default, the list elements and delimiters can have intervening whitespace, and
       comments, but this can be overridden by passing 'combine=True' in the constructor.
       If combine is set to True, the matching tokens are returned as a single token
       string, with the delimiters included; otherwise, the matching tokens are returned
       as a list of tokens, with the delimiters suppressed.
    """
    dlName = _ustr(expr)+" ["+_ustr(delim)+" "+_ustr(expr)+"]..."
    if combine:
        return Combine( expr + ZeroOrMore( delim + expr ) ).setName(dlName)
    else:
        return ( expr + ZeroOrMore( Suppress( delim ) + expr ) ).setName(dlName)

def countedArray( expr ):
    """Helper to define a counted list of expressions.
       This helper defines a pattern of the form::
           integer expr expr expr...
       where the leading integer tells how many expr expressions follow.
       The matched tokens returns the array of expr tokens as a list - the leading count token is suppressed.
    """
    arrayExpr = Forward()
    def countFieldParseAction(s,l,t):
        n = int(t[0])
        arrayExpr << (n and Group(And([expr]*n)) or Group(empty))
        return []
    return ( Word(nums).setName("arrayLen").setParseAction(countFieldParseAction, callDuringTry=True) + arrayExpr )

def _flatten(L):
    if type(L) is not list: return [L]
    if L == []: return L
    return _flatten(L[0]) + _flatten(L[1:])

def matchPreviousLiteral(expr):
    """Helper to define an expression that is indirectly defined from
       the tokens matched in a previous expression, that is, it looks
       for a 'repeat' of a previous expression.  For example::
           first = Word(nums)
           second = matchPreviousLiteral(first)
           matchExpr = first + ":" + second
       will match "1:1", but not "1:2".  Because this matches a
       previous literal, will also match the leading "1:1" in "1:10".
       If this is not desired, use matchPreviousExpr.
       Do *not* use with packrat parsing enabled.
    """
    rep = Forward()
    def copyTokenToRepeater(s,l,t):
        if t:
            if len(t) == 1:
                rep << t[0]
            else:
                # flatten t tokens
                tflat = _flatten(t.asList())
                rep << And( [ Literal(tt) for tt in tflat ] )
        else:
            rep << Empty()
    expr.addParseAction(copyTokenToRepeater, callDuringTry=True)
    return rep

def matchPreviousExpr(expr):
    """Helper to define an expression that is indirectly defined from
       the tokens matched in a previous expression, that is, it looks
       for a 'repeat' of a previous expression.  For example::
           first = Word(nums)
           second = matchPreviousExpr(first)
           matchExpr = first + ":" + second
       will match "1:1", but not "1:2".  Because this matches by
       expressions, will *not* match the leading "1:1" in "1:10";
       the expressions are evaluated first, and then compared, so
       "1" is compared with "10".
       Do *not* use with packrat parsing enabled.
    """
    rep = Forward()
    e2 = expr.copy()
    rep << e2
    def copyTokenToRepeater(s,l,t):
        matchTokens = _flatten(t.asList())
        def mustMatchTheseTokens(s,l,t):
            theseTokens = _flatten(t.asList())
            if  theseTokens != matchTokens:
                raise ParseException("",0,"")
        rep.setParseAction( mustMatchTheseTokens, callDuringTry=True )
    expr.addParseAction(copyTokenToRepeater, callDuringTry=True)
    return rep

def _escapeRegexRangeChars(s):
    #~  escape these chars: ^-]
    for c in r"\^-]":
        s = s.replace(c,"\\"+c)
    s = s.replace("\n",r"\n")
    s = s.replace("\t",r"\t")
    return _ustr(s)

def oneOf( strs, caseless=False, useRegex=True ):
    """Helper to quickly define a set of alternative Literals, and makes sure to do
       longest-first testing when there is a conflict, regardless of the input order,
       but returns a MatchFirst for best performance.

       Parameters:
        - strs - a string of space-delimited literals, or a list of string literals
        - caseless - (default=False) - treat all literals as caseless
        - useRegex - (default=True) - as an optimization, will generate a Regex
          object; otherwise, will generate a MatchFirst object (if caseless=True, or
          if creating a Regex raises an exception)
    """
    if caseless:
        isequal = ( lambda a,b: a.upper() == b.upper() )
        masks = ( lambda a,b: b.upper().startswith(a.upper()) )
        parseElementClass = CaselessLiteral
    else:
        isequal = ( lambda a,b: a == b )
        masks = ( lambda a,b: b.startswith(a) )
        parseElementClass = Literal

    if isinstance(strs,(list,tuple)):
        symbols = strs[:]
    elif isinstance(strs,basestring):
        symbols = strs.split()
    else:
        warnings.warn("Invalid argument to oneOf, expected string or list",
                SyntaxWarning, stacklevel=2)

    i = 0
    while i < len(symbols)-1:
        cur = symbols[i]
        for j,other in enumerate(symbols[i+1:]):
            if ( isequal(other, cur) ):
                del symbols[i+j+1]
                break
            elif ( masks(cur, other) ):
                del symbols[i+j+1]
                symbols.insert(i,other)
                cur = other
                break
        else:
            i += 1

    if not caseless and useRegex:
        #~ print (strs,"->", "|".join( [ _escapeRegexChars(sym) for sym in symbols] ))
        try:
            if len(symbols)==len("".join(symbols)):
                return Regex( "[%s]" % "".join( [ _escapeRegexRangeChars(sym) for sym in symbols] ) )
            else:
                return Regex( "|".join( [ re.escape(sym) for sym in symbols] ) )
        except:
            warnings.warn("Exception creating Regex for oneOf, building MatchFirst",
                    SyntaxWarning, stacklevel=2)


    # last resort, just use MatchFirst
    return MatchFirst( [ parseElementClass(sym) for sym in symbols ] )

def dictOf( key, value ):
    """Helper to easily and clearly define a dictionary by specifying the respective patterns
       for the key and value.  Takes care of defining the Dict, ZeroOrMore, and Group tokens
       in the proper order.  The key pattern can include delimiting markers or punctuation,
       as long as they are suppressed, thereby leaving the significant key text.  The value
       pattern can include named results, so that the Dict results can include named token
       fields.
    """
    return Dict( ZeroOrMore( Group ( key + value ) ) )

# convenience constants for positional expressions
empty       = Empty().setName("empty")
lineStart   = LineStart().setName("lineStart")
lineEnd     = LineEnd().setName("lineEnd")
stringStart = StringStart().setName("stringStart")
stringEnd   = StringEnd().setName("stringEnd")

_escapedPunc = Word( _bslash, r"\[]-*.$+^?()~ ", exact=2 ).setParseAction(lambda s,l,t:t[0][1])
_printables_less_backslash = "".join([ c for c in printables if c not in  r"\]" ])
_escapedHexChar = Combine( Suppress(_bslash + "0x") + Word(hexnums) ).setParseAction(lambda s,l,t:unichr(int(t[0],16)))
_escapedOctChar = Combine( Suppress(_bslash) + Word("0","01234567") ).setParseAction(lambda s,l,t:unichr(int(t[0],8)))
_singleChar = _escapedPunc | _escapedHexChar | _escapedOctChar | Word(_printables_less_backslash,exact=1)
_charRange = Group(_singleChar + Suppress("-") + _singleChar)
_reBracketExpr = Literal("[") + Optional("^").setResultsName("negate") + Group( OneOrMore( _charRange | _singleChar ) ).setResultsName("body") + "]"

_expanded = lambda p: (isinstance(p,ParseResults) and ''.join([ unichr(c) for c in range(ord(p[0]),ord(p[1])+1) ]) or p)

def srange(s):
    r"""Helper to easily define string ranges for use in Word construction.  Borrows
       syntax from regexp '[]' string range definitions::
          srange("[0-9]")   -> "0123456789"
          srange("[a-z]")   -> "abcdefghijklmnopqrstuvwxyz"
          srange("[a-z$_]") -> "abcdefghijklmnopqrstuvwxyz$_"
       The input string must be enclosed in []'s, and the returned string is the expanded
       character set joined into a single string.
       The values enclosed in the []'s may be::
          a single character
          an escaped character with a leading backslash (such as \- or \])
          an escaped hex character with a leading '\0x' (\0x21, which is a '!' character)
          an escaped octal character with a leading '\0' (\041, which is a '!' character)
          a range of any of the above, separated by a dash ('a-z', etc.)
          any combination of the above ('aeiouy', 'a-zA-Z0-9_$', etc.)
    """
    try:
        return "".join([_expanded(part) for part in _reBracketExpr.parseString(s).body])
    except:
        return ""

def matchOnlyAtCol(n):
    """Helper method for defining parse actions that require matching at a specific
       column in the input text.
    """
    def verifyCol(strg,locn,toks):
        if col(locn,strg) != n:
            raise ParseException(strg,locn,"matched token not at column %d" % n)
    return verifyCol

def replaceWith(replStr):
    """Helper method for common parse actions that simply return a literal value.  Especially
       useful when used with transformString().
    """
    def _replFunc(*args):
        return [replStr]
    return _replFunc

def removeQuotes(s,l,t):
    """Helper parse action for removing quotation marks from parsed quoted strings.
       To use, add this parse action to quoted string using::
         quotedString.setParseAction( removeQuotes )
    """
    return t[0][1:-1]

def upcaseTokens(s,l,t):
    """Helper parse action to convert tokens to upper case."""
    return [ tt.upper() for tt in map(_ustr,t) ]

def downcaseTokens(s,l,t):
    """Helper parse action to convert tokens to lower case."""
    return [ tt.lower() for tt in map(_ustr,t) ]

def keepOriginalText(s,startLoc,t):
    """Helper parse action to preserve original parsed text,
       overriding any nested parse actions."""
    try:
        endloc = getTokensEndLoc()
    except ParseException:
        raise ParseFatalException("incorrect usage of keepOriginalText - may only be called as a parse action")
    del t[:]
    t += ParseResults(s[startLoc:endloc])
    return t

def getTokensEndLoc():
    """Method to be called from within a parse action to determine the end
       location of the parsed tokens."""
    import inspect
    fstack = inspect.stack()
    try:
        # search up the stack (through intervening argument normalizers) for correct calling routine
        for f in fstack[2:]:
            if f[3] == "_parseNoCache":
                endloc = f[0].f_locals["loc"]
                return endloc
        else:
            raise ParseFatalException("incorrect usage of getTokensEndLoc - may only be called from within a parse action")
    finally:
        del fstack

def _makeTags(tagStr, xml):
    """Internal helper to construct opening and closing tag expressions, given a tag name"""
    if isinstance(tagStr,basestring):
        resname = tagStr
        tagStr = Keyword(tagStr, caseless=not xml)
    else:
        resname = tagStr.name

    tagAttrName = Word(alphas,alphanums+"_-:")
    if (xml):
        tagAttrValue = dblQuotedString.copy().setParseAction( removeQuotes )
        openTag = Suppress("<") + tagStr + \
                Dict(ZeroOrMore(Group( tagAttrName + Suppress("=") + tagAttrValue ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    else:
        printablesLessRAbrack = "".join( [ c for c in printables if c not in ">" ] )
        tagAttrValue = quotedString.copy().setParseAction( removeQuotes ) | Word(printablesLessRAbrack)
        openTag = Suppress("<") + tagStr + \
                Dict(ZeroOrMore(Group( tagAttrName.setParseAction(downcaseTokens) + \
                Optional( Suppress("=") + tagAttrValue ) ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    closeTag = Combine(_L("</") + tagStr + ">")

    openTag = openTag.setResultsName("start"+"".join(resname.replace(":"," ").title().split())).setName("<%s>" % tagStr)
    closeTag = closeTag.setResultsName("end"+"".join(resname.replace(":"," ").title().split())).setName("</%s>" % tagStr)

    return openTag, closeTag

def makeHTMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for HTML, given a tag name"""
    return _makeTags( tagStr, False )

def makeXMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for XML, given a tag name"""
    return _makeTags( tagStr, True )

def withAttribute(*args,**attrDict):
    """Helper to create a validating parse action to be used with start tags created
       with makeXMLTags or makeHTMLTags. Use withAttribute to qualify a starting tag
       with a required attribute value, to avoid false matches on common tags such as
       <TD> or <DIV>.

       Call withAttribute with a series of attribute names and values. Specify the list
       of filter attributes names and values as:
        - keyword arguments, as in (class="Customer",align="right"), or
        - a list of name-value tuples, as in ( ("ns1:class", "Customer"), ("ns2:align","right") )
       For attribute names with a namespace prefix, you must use the second form.  Attribute
       names are matched insensitive to upper/lower case.

       To verify that the attribute exists, but without specifying a value, pass
       withAttribute.ANY_VALUE as the value.
       """
    if args:
        attrs = args[:]
    else:
        attrs = attrDict.items()
    attrs = [(k,v) for k,v in attrs]
    def pa(s,l,tokens):
        for attrName,attrValue in attrs:
            if attrName not in tokens:
                raise ParseException(s,l,"no matching attribute " + attrName)
            if attrValue != withAttribute.ANY_VALUE and tokens[attrName] != attrValue:
                raise ParseException(s,l,"attribute '%s' has value '%s', must be '%s'" %
                                            (attrName, tokens[attrName], attrValue))
    return pa
withAttribute.ANY_VALUE = object()

opAssoc = _Constants()
opAssoc.LEFT = object()
opAssoc.RIGHT = object()

def operatorPrecedence( baseExpr, opList ):
    """Helper method for constructing grammars of expressions made up of
       operators working in a precedence hierarchy.  Operators may be unary or
       binary, left- or right-associative.  Parse actions can also be attached
       to operator expressions.

       Parameters:
        - baseExpr - expression representing the most basic element for the nested
        - opList - list of tuples, one for each operator precedence level in the
          expression grammar; each tuple is of the form
          (opExpr, numTerms, rightLeftAssoc, parseAction), where:
           - opExpr is the pyparsing expression for the operator;
              may also be a string, which will be converted to a Literal;
              if numTerms is 3, opExpr is a tuple of two expressions, for the
              two operators separating the 3 terms
           - numTerms is the number of terms for this operator (must
              be 1, 2, or 3)
           - rightLeftAssoc is the indicator whether the operator is
              right or left associative, using the pyparsing-defined
              constants opAssoc.RIGHT and opAssoc.LEFT.
           - parseAction is the parse action to be associated with
              expressions matching this operator expression (the
              parse action tuple member may be omitted)
    """
    ret = Forward()
    lastExpr = baseExpr | ( Suppress('(') + ret + Suppress(')') )
    for i,operDef in enumerate(opList):
        opExpr,arity,rightLeftAssoc,pa = (operDef + (None,))[:4]
        if arity == 3:
            if opExpr is None or len(opExpr) != 2:
                raise ValueError("if numterms=3, opExpr must be a tuple or list of two expressions")
            opExpr1, opExpr2 = opExpr
        thisExpr = Forward()#.setName("expr%d" % i)
        if rightLeftAssoc == opAssoc.LEFT:
            if arity == 1:
                matchExpr = FollowedBy(lastExpr + opExpr) + Group( lastExpr + OneOrMore( opExpr ) )
            elif arity == 2:
                if opExpr is not None:
                    matchExpr = FollowedBy(lastExpr + opExpr + lastExpr) + Group( lastExpr + OneOrMore( opExpr + lastExpr ) )
                else:
                    matchExpr = FollowedBy(lastExpr+lastExpr) + Group( lastExpr + OneOrMore(lastExpr) )
            elif arity == 3:
                matchExpr = FollowedBy(lastExpr + opExpr1 + lastExpr + opExpr2 + lastExpr) + \
                            Group( lastExpr + opExpr1 + lastExpr + opExpr2 + lastExpr )
            else:
                raise ValueError("operator must be unary (1), binary (2), or ternary (3)")
        elif rightLeftAssoc == opAssoc.RIGHT:
            if arity == 1:
                # try to avoid LR with this extra test
                if not isinstance(opExpr, Optional):
                    opExpr = Optional(opExpr)
                matchExpr = FollowedBy(opExpr.expr + thisExpr) + Group( opExpr + thisExpr )
            elif arity == 2:
                if opExpr is not None:
                    matchExpr = FollowedBy(lastExpr + opExpr + thisExpr) + Group( lastExpr + OneOrMore( opExpr + thisExpr ) )
                else:
                    matchExpr = FollowedBy(lastExpr + thisExpr) + Group( lastExpr + OneOrMore( thisExpr ) )
            elif arity == 3:
                matchExpr = FollowedBy(lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr) + \
                            Group( lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr )
            else:
                raise ValueError("operator must be unary (1), binary (2), or ternary (3)")
        else:
            raise ValueError("operator must indicate right or left associativity")
        if pa:
            matchExpr.setParseAction( pa )
        thisExpr << ( matchExpr | lastExpr )
        lastExpr = thisExpr
    ret << lastExpr
    return ret

dblQuotedString = Regex(r'"(?:[^"\n\r\\]|(?:"")|(?:\\x[0-9a-fA-F]+)|(?:\\.))*"').setName("string enclosed in double quotes")
sglQuotedString = Regex(r"'(?:[^'\n\r\\]|(?:'')|(?:\\x[0-9a-fA-F]+)|(?:\\.))*'").setName("string enclosed in single quotes")
quotedString = Regex(r'''(?:"(?:[^"\n\r\\]|(?:"")|(?:\\x[0-9a-fA-F]+)|(?:\\.))*")|(?:'(?:[^'\n\r\\]|(?:'')|(?:\\x[0-9a-fA-F]+)|(?:\\.))*')''').setName("quotedString using single or double quotes")
unicodeString = Combine(_L('u') + quotedString.copy())

def nestedExpr(opener="(", closer=")", content=None, ignoreExpr=quotedString):
    """Helper method for defining nested lists enclosed in opening and closing
       delimiters ("(" and ")" are the default).

       Parameters:
        - opener - opening character for a nested list (default="("); can also be a pyparsing expression
        - closer - closing character for a nested list (default=")"); can also be a pyparsing expression
        - content - expression for items within the nested lists (default=None)
        - ignoreExpr - expression for ignoring opening and closing delimiters (default=quotedString)

       If an expression is not provided for the content argument, the nested
       expression will capture all whitespace-delimited content between delimiters
       as a list of separate values.

       Use the ignoreExpr argument to define expressions that may contain
       opening or closing characters that should not be treated as opening
       or closing characters for nesting, such as quotedString or a comment
       expression.  Specify multiple expressions using an Or or MatchFirst.
       The default is quotedString, but if no expressions are to be ignored,
       then pass None for this argument.
    """
    if opener == closer:
        raise ValueError("opening and closing strings cannot be the same")
    if content is None:
        if isinstance(opener,basestring) and isinstance(closer,basestring):
            if ignoreExpr is not None:
                content = (Combine(OneOrMore(~ignoreExpr +
                                CharsNotIn(opener+closer+ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                            ).setParseAction(lambda t:t[0].strip()))
            else:
                content = (empty+CharsNotIn(opener+closer+ParserElement.DEFAULT_WHITE_CHARS).setParseAction(lambda t:t[0].strip()))
        else:
            raise ValueError("opening and closing arguments must be strings if no content expression is given")
    ret = Forward()
    if ignoreExpr is not None:
        ret << Group( Suppress(opener) + ZeroOrMore( ignoreExpr | ret | content ) + Suppress(closer) )
    else:
        ret << Group( Suppress(opener) + ZeroOrMore( ret | content )  + Suppress(closer) )
    return ret

def indentedBlock(blockStatementExpr, indentStack, indent=True):
    """Helper method for defining space-delimited indentation blocks, such as 
       those used to define block statements in Python source code.
       
       Parameters:
        - blockStatementExpr - expression defining syntax of statement that 
            is repeated within the indented block
        - indentStack - list created by caller to manage indentation stack
            (multiple statementWithIndentedBlock expressions within a single grammar
            should share a common indentStack)
        - indent - boolean indicating whether block must be indented beyond the 
            the current level; set to False for block of left-most statements
            (default=True)

       A valid block must contain at least one blockStatement.
    """
    def checkPeerIndent(s,l,t):
        if l >= len(s): return
        curCol = col(l,s)
        if curCol != indentStack[-1]:
            if curCol > indentStack[-1]:
                raise ParseFatalException(s,l,"illegal nesting")
            raise ParseException(s,l,"not a peer entry")

    def checkSubIndent(s,l,t):
        curCol = col(l,s)
        if curCol > indentStack[-1]:
            indentStack.append( curCol )
        else:
            raise ParseException(s,l,"not a subentry")

    def checkUnindent(s,l,t):
        if l >= len(s): return
        curCol = col(l,s)
        if not(indentStack and curCol < indentStack[-1] and curCol <= indentStack[-2]):
            raise ParseException(s,l,"not an unindent")
        indentStack.pop()

    NL = OneOrMore(LineEnd().setWhitespaceChars("\t ").suppress())
    INDENT = Empty() + Empty().setParseAction(checkSubIndent)
    PEER   = Empty().setParseAction(checkPeerIndent)
    UNDENT = Empty().setParseAction(checkUnindent)
    if indent:
        smExpr = Group( Optional(NL) +
            FollowedBy(blockStatementExpr) +
            INDENT + (OneOrMore( PEER + Group(blockStatementExpr) + Optional(NL) )) + UNDENT)
    else:
        smExpr = Group( Optional(NL) +
            (OneOrMore( PEER + Group(blockStatementExpr) + Optional(NL) )) )
    blockStatementExpr.ignore("\\" + LineEnd())
    return smExpr

alphas8bit = srange(r"[\0xc0-\0xd6\0xd8-\0xf6\0xf8-\0xff]")
punc8bit = srange(r"[\0xa1-\0xbf\0xd7\0xf7]")

anyOpenTag,anyCloseTag = makeHTMLTags(Word(alphas,alphanums+"_:"))
commonHTMLEntity = Combine(_L("&") + oneOf("gt lt amp nbsp quot").setResultsName("entity") +";")
_htmlEntityMap = dict(zip("gt lt amp nbsp quot".split(),"><& '"))
replaceHTMLEntity = lambda t : t.entity in _htmlEntityMap and _htmlEntityMap[t.entity] or None

# it's easy to get these comment structures wrong - they're very common, so may as well make them available
cStyleComment = Regex(r"/\*(?:[^*]*\*+)+?/").setName("C style comment")

htmlComment = Regex(r"<!--[\s\S]*?-->")
restOfLine = Regex(r".*").leaveWhitespace()
dblSlashComment = Regex(r"\/\/(\\\n|.)*").setName("// comment")
cppStyleComment = Regex(r"/(?:\*(?:[^*]*\*+)+?/|/[^\n]*(?:\n[^\n]*)*?(?:(?<!\\)|\Z))").setName("C++ style comment")

javaStyleComment = cppStyleComment
pythonStyleComment = Regex(r"#.*").setName("Python style comment")
_noncomma = "".join( [ c for c in printables if c != "," ] )
_commasepitem = Combine(OneOrMore(Word(_noncomma) +
                                  Optional( Word(" \t") +
                                            ~Literal(",") + ~LineEnd() ) ) ).streamline().setName("commaItem")
commaSeparatedList = delimitedList( Optional( quotedString | _commasepitem, default="") ).setName("commaSeparatedList")


if __name__ == "__main__":

    def test( teststring ):
        try:
            tokens = simpleSQL.parseString( teststring )
            tokenlist = tokens.asList()
            print (teststring + "->"   + str(tokenlist))
            print ("tokens = "         + str(tokens))
            print ("tokens.columns = " + str(tokens.columns))
            print ("tokens.tables = "  + str(tokens.tables))
            print (tokens.asXML("SQL",True))
        except ParseBaseException,err:
            print (teststring + "->")
            print (err.line)
            print (" "*(err.column-1) + "^")
            print (err)
        print()

    selectToken    = CaselessLiteral( "select" )
    fromToken      = CaselessLiteral( "from" )

    ident          = Word( alphas, alphanums + "_$" )
    columnName     = delimitedList( ident, ".", combine=True ).setParseAction( upcaseTokens )
    columnNameList = Group( delimitedList( columnName ) )#.setName("columns")
    tableName      = delimitedList( ident, ".", combine=True ).setParseAction( upcaseTokens )
    tableNameList  = Group( delimitedList( tableName ) )#.setName("tables")
    simpleSQL      = ( selectToken + \
                     ( '*' | columnNameList ).setResultsName( "columns" ) + \
                     fromToken + \
                     tableNameList.setResultsName( "tables" ) )

    test( "SELECT * from XYZZY, ABC" )
    test( "select * from SYS.XYZZY" )
    test( "Select A from Sys.dual" )
    test( "Select AA,BB,CC from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Xelect A, B, C from Sys.dual" )
    test( "Select A, B, C frox Sys.dual" )
    test( "Select" )
    test( "Select ^^^ frox Sys.dual" )
    test( "Select A, B, C from Sys.dual, Table2   " )

########NEW FILE########
__FILENAME__ = exceptions
'''
Custom exceptions raised by pytz.
'''

__all__ = [
    'UnknownTimeZoneError', 'InvalidTimeError', 'AmbiguousTimeError',
    'NonExistentTimeError',
    ]


class UnknownTimeZoneError(KeyError):
    '''Exception raised when pytz is passed an unknown timezone.

    >>> isinstance(UnknownTimeZoneError(), LookupError)
    True

    This class is actually a subclass of KeyError to provide backwards
    compatibility with code relying on the undocumented behavior of earlier
    pytz releases.

    >>> isinstance(UnknownTimeZoneError(), KeyError)
    True
    '''
    pass


class InvalidTimeError(Exception):
    '''Base class for invalid time exceptions.'''


class AmbiguousTimeError(InvalidTimeError):
    '''Exception raised when attempting to create an ambiguous wallclock time.

    At the end of a DST transition period, a particular wallclock time will
    occur twice (once before the clocks are set back, once after). Both
    possibilities may be correct, unless further information is supplied.

    See DstTzInfo.normalize() for more info
    '''


class NonExistentTimeError(InvalidTimeError):
    '''Exception raised when attempting to create a wallclock time that
    cannot exist.

    At the start of a DST transition period, the wallclock time jumps forward.
    The instants jumped over never occur.
    '''

########NEW FILE########
__FILENAME__ = reference
'''
Reference tzinfo implementations from the Python docs.
Used for testing against as they are only correct for the years
1987 to 2006. Do not use these for real code.
'''

from datetime import tzinfo, timedelta, datetime
from pytz import utc, UTC, HOUR, ZERO

# A class building tzinfo objects for fixed-offset time zones.
# Note that FixedOffset(0, "UTC") is a different way to build a
# UTC tzinfo object.

class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

# A class capturing the platform's idea of local time.

import time as _time

STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, -1)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

Local = LocalTimezone()

# A complete implementation of current DST rules for major US time zones.

def first_sunday_on_or_after(dt):
    days_to_go = 6 - dt.weekday()
    if days_to_go:
        dt += timedelta(days_to_go)
    return dt

# In the US, DST starts at 2am (standard time) on the first Sunday in April.
DSTSTART = datetime(1, 4, 1, 2)
# and ends at 2am (DST time; 1am standard time) on the last Sunday of Oct.
# which is the first Sunday on or after Oct 25.
DSTEND = datetime(1, 10, 25, 1)

class USTimeZone(tzinfo):

    def __init__(self, hours, reprname, stdname, dstname):
        self.stdoffset = timedelta(hours=hours)
        self.reprname = reprname
        self.stdname = stdname
        self.dstname = dstname

    def __repr__(self):
        return self.reprname

    def tzname(self, dt):
        if self.dst(dt):
            return self.dstname
        else:
            return self.stdname

    def utcoffset(self, dt):
        return self.stdoffset + self.dst(dt)

    def dst(self, dt):
        if dt is None or dt.tzinfo is None:
            # An exception may be sensible here, in one or both cases.
            # It depends on how you want to treat them.  The default
            # fromutc() implementation (called by the default astimezone()
            # implementation) passes a datetime with dt.tzinfo is self.
            return ZERO
        assert dt.tzinfo is self

        # Find first Sunday in April & the last in October.
        start = first_sunday_on_or_after(DSTSTART.replace(year=dt.year))
        end = first_sunday_on_or_after(DSTEND.replace(year=dt.year))

        # Can't compare naive to aware objects, so strip the timezone from
        # dt first.
        if start <= dt.replace(tzinfo=None) < end:
            return HOUR
        else:
            return ZERO

Eastern  = USTimeZone(-5, "Eastern",  "EST", "EDT")
Central  = USTimeZone(-6, "Central",  "CST", "CDT")
Mountain = USTimeZone(-7, "Mountain", "MST", "MDT")
Pacific  = USTimeZone(-8, "Pacific",  "PST", "PDT")


########NEW FILE########
__FILENAME__ = tzfile
#!/usr/bin/env python
'''
$Id: tzfile.py,v 1.8 2004/06/03 00:15:24 zenzen Exp $
'''

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
from datetime import datetime, timedelta
from struct import unpack, calcsize

from pytz.tzinfo import StaticTzInfo, DstTzInfo, memorized_ttinfo
from pytz.tzinfo import memorized_datetime, memorized_timedelta

def _byte_string(s):
    """Cast a string or byte string to an ASCII byte string."""
    return s.encode('US-ASCII')

_NULL = _byte_string('\0')

def _std_string(s):
    """Cast a string or byte string to an ASCII string."""
    return str(s.decode('US-ASCII'))

def build_tzinfo(zone, fp):
    head_fmt = '>4s c 15x 6l'
    head_size = calcsize(head_fmt)
    (magic, format, ttisgmtcnt, ttisstdcnt,leapcnt, timecnt,
        typecnt, charcnt) =  unpack(head_fmt, fp.read(head_size))

    # Make sure it is a tzfile(5) file
    assert magic == _byte_string('TZif'), 'Got magic %s' % repr(magic)

    # Read out the transition times, localtime indices and ttinfo structures.
    data_fmt = '>%(timecnt)dl %(timecnt)dB %(ttinfo)s %(charcnt)ds' % dict(
        timecnt=timecnt, ttinfo='lBB'*typecnt, charcnt=charcnt)
    data_size = calcsize(data_fmt)
    data = unpack(data_fmt, fp.read(data_size))

    # make sure we unpacked the right number of values
    assert len(data) == 2 * timecnt + 3 * typecnt + 1
    transitions = [memorized_datetime(trans)
                   for trans in data[:timecnt]]
    lindexes = list(data[timecnt:2 * timecnt])
    ttinfo_raw = data[2 * timecnt:-1]
    tznames_raw = data[-1]
    del data

    # Process ttinfo into separate structs
    ttinfo = []
    tznames = {}
    i = 0
    while i < len(ttinfo_raw):
        # have we looked up this timezone name yet?
        tzname_offset = ttinfo_raw[i+2]
        if tzname_offset not in tznames:
            nul = tznames_raw.find(_NULL, tzname_offset)
            if nul < 0:
                nul = len(tznames_raw)
            tznames[tzname_offset] = _std_string(
                tznames_raw[tzname_offset:nul])
        ttinfo.append((ttinfo_raw[i],
                       bool(ttinfo_raw[i+1]),
                       tznames[tzname_offset]))
        i += 3

    # Now build the timezone object
    if len(transitions) == 0:
        ttinfo[0][0], ttinfo[0][2]
        cls = type(zone, (StaticTzInfo,), dict(
            zone=zone,
            _utcoffset=memorized_timedelta(ttinfo[0][0]),
            _tzname=ttinfo[0][2]))
    else:
        # Early dates use the first standard time ttinfo
        i = 0
        while ttinfo[i][1]:
            i += 1
        if ttinfo[i] == ttinfo[lindexes[0]]:
            transitions[0] = datetime.min
        else:
            transitions.insert(0, datetime.min)
            lindexes.insert(0, i)

        # calculate transition info
        transition_info = []
        for i in range(len(transitions)):
            inf = ttinfo[lindexes[i]]
            utcoffset = inf[0]
            if not inf[1]:
                dst = 0
            else:
                for j in range(i-1, -1, -1):
                    prev_inf = ttinfo[lindexes[j]]
                    if not prev_inf[1]:
                        break
                dst = inf[0] - prev_inf[0] # dst offset

                # Bad dst? Look further. DST > 24 hours happens when
                # a timzone has moved across the international dateline.
                if dst <= 0 or dst > 3600*3:
                    for j in range(i+1, len(transitions)):
                        stdinf = ttinfo[lindexes[j]]
                        if not stdinf[1]:
                            dst = inf[0] - stdinf[0]
                            if dst > 0:
                                break # Found a useful std time.

            tzname = inf[2]

            # Round utcoffset and dst to the nearest minute or the
            # datetime library will complain. Conversions to these timezones
            # might be up to plus or minus 30 seconds out, but it is
            # the best we can do.
            utcoffset = int((utcoffset + 30) // 60) * 60
            dst = int((dst + 30) // 60) * 60
            transition_info.append(memorized_ttinfo(utcoffset, dst, tzname))

        cls = type(zone, (DstTzInfo,), dict(
            zone=zone,
            _utc_transition_times=transitions,
            _transition_info=transition_info))

    return cls()

if __name__ == '__main__':
    import os.path
    from pprint import pprint
    base = os.path.join(os.path.dirname(__file__), 'zoneinfo')
    tz = build_tzinfo('Australia/Melbourne',
                      open(os.path.join(base,'Australia','Melbourne'), 'rb'))
    tz = build_tzinfo('US/Eastern',
                      open(os.path.join(base,'US','Eastern'), 'rb'))
    pprint(tz._utc_transition_times)
    #print tz.asPython(4)
    #print tz.transitions_mapping

########NEW FILE########
__FILENAME__ = tzinfo
'''Base classes and helpers for building zone specific tzinfo classes'''

from datetime import datetime, timedelta, tzinfo
from bisect import bisect_right
try:
    set
except NameError:
    from sets import Set as set

import pytz
from pytz.exceptions import AmbiguousTimeError, NonExistentTimeError

__all__ = []

_timedelta_cache = {}
def memorized_timedelta(seconds):
    '''Create only one instance of each distinct timedelta'''
    try:
        return _timedelta_cache[seconds]
    except KeyError:
        delta = timedelta(seconds=seconds)
        _timedelta_cache[seconds] = delta
        return delta

_epoch = datetime.utcfromtimestamp(0)
_datetime_cache = {0: _epoch}
def memorized_datetime(seconds):
    '''Create only one instance of each distinct datetime'''
    try:
        return _datetime_cache[seconds]
    except KeyError:
        # NB. We can't just do datetime.utcfromtimestamp(seconds) as this
        # fails with negative values under Windows (Bug #90096)
        dt = _epoch + timedelta(seconds=seconds)
        _datetime_cache[seconds] = dt
        return dt

_ttinfo_cache = {}
def memorized_ttinfo(*args):
    '''Create only one instance of each distinct tuple'''
    try:
        return _ttinfo_cache[args]
    except KeyError:
        ttinfo = (
                memorized_timedelta(args[0]),
                memorized_timedelta(args[1]),
                args[2]
                )
        _ttinfo_cache[args] = ttinfo
        return ttinfo

_notime = memorized_timedelta(0)

def _to_seconds(td):
    '''Convert a timedelta to seconds'''
    return td.seconds + td.days * 24 * 60 * 60


class BaseTzInfo(tzinfo):
    # Overridden in subclass
    _utcoffset = None
    _tzname = None
    zone = None

    def __str__(self):
        return self.zone


class StaticTzInfo(BaseTzInfo):
    '''A timezone that has a constant offset from UTC

    These timezones are rare, as most locations have changed their
    offset at some point in their history
    '''
    def fromutc(self, dt):
        '''See datetime.tzinfo.fromutc'''
        if dt.tzinfo is not None and dt.tzinfo is not self:
            raise ValueError('fromutc: dt.tzinfo is not self')
        return (dt + self._utcoffset).replace(tzinfo=self)

    def utcoffset(self, dt, is_dst=None):
        '''See datetime.tzinfo.utcoffset

        is_dst is ignored for StaticTzInfo, and exists only to
        retain compatibility with DstTzInfo.
        '''
        return self._utcoffset

    def dst(self, dt, is_dst=None):
        '''See datetime.tzinfo.dst

        is_dst is ignored for StaticTzInfo, and exists only to
        retain compatibility with DstTzInfo.
        '''
        return _notime

    def tzname(self, dt, is_dst=None):
        '''See datetime.tzinfo.tzname

        is_dst is ignored for StaticTzInfo, and exists only to
        retain compatibility with DstTzInfo.
        '''
        return self._tzname

    def localize(self, dt, is_dst=False):
        '''Convert naive time to local time'''
        if dt.tzinfo is not None:
            raise ValueError('Not naive datetime (tzinfo is already set)')
        return dt.replace(tzinfo=self)

    def normalize(self, dt, is_dst=False):
        '''Correct the timezone information on the given datetime.

        This is normally a no-op, as StaticTzInfo timezones never have
        ambiguous cases to correct:

        >>> from pytz import timezone
        >>> gmt = timezone('GMT')
        >>> isinstance(gmt, StaticTzInfo)
        True
        >>> dt = datetime(2011, 5, 8, 1, 2, 3, tzinfo=gmt)
        >>> gmt.normalize(dt) is dt
        True

        The supported method of converting between timezones is to use
        datetime.astimezone(). Currently normalize() also works:

        >>> la = timezone('America/Los_Angeles')
        >>> dt = la.localize(datetime(2011, 5, 7, 1, 2, 3))
        >>> fmt = '%Y-%m-%d %H:%M:%S %Z (%z)'
        >>> gmt.normalize(dt).strftime(fmt)
        '2011-05-07 08:02:03 GMT (+0000)'
        '''
        if dt.tzinfo is self:
            return dt
        if dt.tzinfo is None:
            raise ValueError('Naive time - no tzinfo set')
        return dt.astimezone(self)

    def __repr__(self):
        return '<StaticTzInfo %r>' % (self.zone,)

    def __reduce__(self):
        # Special pickle to zone remains a singleton and to cope with
        # database changes. 
        return pytz._p, (self.zone,)


class DstTzInfo(BaseTzInfo):
    '''A timezone that has a variable offset from UTC

    The offset might change if daylight savings time comes into effect,
    or at a point in history when the region decides to change their
    timezone definition.
    '''
    # Overridden in subclass
    _utc_transition_times = None # Sorted list of DST transition times in UTC
    _transition_info = None # [(utcoffset, dstoffset, tzname)] corresponding
                            # to _utc_transition_times entries
    zone = None

    # Set in __init__
    _tzinfos = None
    _dst = None # DST offset

    def __init__(self, _inf=None, _tzinfos=None):
        if _inf:
            self._tzinfos = _tzinfos
            self._utcoffset, self._dst, self._tzname = _inf
        else:
            _tzinfos = {}
            self._tzinfos = _tzinfos
            self._utcoffset, self._dst, self._tzname = self._transition_info[0]
            _tzinfos[self._transition_info[0]] = self
            for inf in self._transition_info[1:]:
                if inf not in _tzinfos:
                    _tzinfos[inf] = self.__class__(inf, _tzinfos)

    def fromutc(self, dt):
        '''See datetime.tzinfo.fromutc'''
        if dt.tzinfo is not None and dt.tzinfo._tzinfos is not self._tzinfos:
            raise ValueError('fromutc: dt.tzinfo is not self')
        dt = dt.replace(tzinfo=None)
        idx = max(0, bisect_right(self._utc_transition_times, dt) - 1)
        inf = self._transition_info[idx]
        return (dt + inf[0]).replace(tzinfo=self._tzinfos[inf])

    def normalize(self, dt):
        '''Correct the timezone information on the given datetime

        If date arithmetic crosses DST boundaries, the tzinfo
        is not magically adjusted. This method normalizes the
        tzinfo to the correct one.

        To test, first we need to do some setup

        >>> from pytz import timezone
        >>> utc = timezone('UTC')
        >>> eastern = timezone('US/Eastern')
        >>> fmt = '%Y-%m-%d %H:%M:%S %Z (%z)'

        We next create a datetime right on an end-of-DST transition point,
        the instant when the wallclocks are wound back one hour.

        >>> utc_dt = datetime(2002, 10, 27, 6, 0, 0, tzinfo=utc)
        >>> loc_dt = utc_dt.astimezone(eastern)
        >>> loc_dt.strftime(fmt)
        '2002-10-27 01:00:00 EST (-0500)'

        Now, if we subtract a few minutes from it, note that the timezone
        information has not changed.

        >>> before = loc_dt - timedelta(minutes=10)
        >>> before.strftime(fmt)
        '2002-10-27 00:50:00 EST (-0500)'

        But we can fix that by calling the normalize method

        >>> before = eastern.normalize(before)
        >>> before.strftime(fmt)
        '2002-10-27 01:50:00 EDT (-0400)'

        The supported method of converting between timezones is to use
        datetime.astimezone(). Currently, normalize() also works:

        >>> th = timezone('Asia/Bangkok')
        >>> am = timezone('Europe/Amsterdam')
        >>> dt = th.localize(datetime(2011, 5, 7, 1, 2, 3))
        >>> fmt = '%Y-%m-%d %H:%M:%S %Z (%z)'
        >>> am.normalize(dt).strftime(fmt)
        '2011-05-06 20:02:03 CEST (+0200)'
        '''
        if dt.tzinfo is None:
            raise ValueError('Naive time - no tzinfo set')

        # Convert dt in localtime to UTC
        offset = dt.tzinfo._utcoffset
        dt = dt.replace(tzinfo=None)
        dt = dt - offset
        # convert it back, and return it
        return self.fromutc(dt)

    def localize(self, dt, is_dst=False):
        '''Convert naive time to local time.

        This method should be used to construct localtimes, rather
        than passing a tzinfo argument to a datetime constructor.

        is_dst is used to determine the correct timezone in the ambigous
        period at the end of daylight savings time.

        >>> from pytz import timezone
        >>> fmt = '%Y-%m-%d %H:%M:%S %Z (%z)'
        >>> amdam = timezone('Europe/Amsterdam')
        >>> dt  = datetime(2004, 10, 31, 2, 0, 0)
        >>> loc_dt1 = amdam.localize(dt, is_dst=True)
        >>> loc_dt2 = amdam.localize(dt, is_dst=False)
        >>> loc_dt1.strftime(fmt)
        '2004-10-31 02:00:00 CEST (+0200)'
        >>> loc_dt2.strftime(fmt)
        '2004-10-31 02:00:00 CET (+0100)'
        >>> str(loc_dt2 - loc_dt1)
        '1:00:00'

        Use is_dst=None to raise an AmbiguousTimeError for ambiguous
        times at the end of daylight savings

        >>> try:
        ...     loc_dt1 = amdam.localize(dt, is_dst=None)
        ... except AmbiguousTimeError:
        ...     print('Ambiguous')
        Ambiguous

        is_dst defaults to False

        >>> amdam.localize(dt) == amdam.localize(dt, False)
        True

        is_dst is also used to determine the correct timezone in the
        wallclock times jumped over at the start of daylight savings time.

        >>> pacific = timezone('US/Pacific')
        >>> dt = datetime(2008, 3, 9, 2, 0, 0)
        >>> ploc_dt1 = pacific.localize(dt, is_dst=True)
        >>> ploc_dt2 = pacific.localize(dt, is_dst=False)
        >>> ploc_dt1.strftime(fmt)
        '2008-03-09 02:00:00 PDT (-0700)'
        >>> ploc_dt2.strftime(fmt)
        '2008-03-09 02:00:00 PST (-0800)'
        >>> str(ploc_dt2 - ploc_dt1)
        '1:00:00'

        Use is_dst=None to raise a NonExistentTimeError for these skipped
        times.

        >>> try:
        ...     loc_dt1 = pacific.localize(dt, is_dst=None)
        ... except NonExistentTimeError:
        ...     print('Non-existent')
        Non-existent
        '''
        if dt.tzinfo is not None:
            raise ValueError('Not naive datetime (tzinfo is already set)')

        # Find the two best possibilities.
        possible_loc_dt = set()
        for delta in [timedelta(days=-1), timedelta(days=1)]:
            loc_dt = dt + delta
            idx = max(0, bisect_right(
                self._utc_transition_times, loc_dt) - 1)
            inf = self._transition_info[idx]
            tzinfo = self._tzinfos[inf]
            loc_dt = tzinfo.normalize(dt.replace(tzinfo=tzinfo))
            if loc_dt.replace(tzinfo=None) == dt:
                possible_loc_dt.add(loc_dt)

        if len(possible_loc_dt) == 1:
            return possible_loc_dt.pop()

        # If there are no possibly correct timezones, we are attempting
        # to convert a time that never happened - the time period jumped
        # during the start-of-DST transition period.
        if len(possible_loc_dt) == 0:
            # If we refuse to guess, raise an exception.
            if is_dst is None:
                raise NonExistentTimeError(dt)

            # If we are forcing the pre-DST side of the DST transition, we
            # obtain the correct timezone by winding the clock forward a few
            # hours.
            elif is_dst:
                return self.localize(
                    dt + timedelta(hours=6), is_dst=True) - timedelta(hours=6)

            # If we are forcing the post-DST side of the DST transition, we
            # obtain the correct timezone by winding the clock back.
            else:
                return self.localize(
                    dt - timedelta(hours=6), is_dst=False) + timedelta(hours=6)


        # If we get this far, we have multiple possible timezones - this
        # is an ambiguous case occuring during the end-of-DST transition.

        # If told to be strict, raise an exception since we have an
        # ambiguous case
        if is_dst is None:
            raise AmbiguousTimeError(dt)

        # Filter out the possiblilities that don't match the requested
        # is_dst
        filtered_possible_loc_dt = [
            p for p in possible_loc_dt
                if bool(p.tzinfo._dst) == is_dst
            ]

        # Hopefully we only have one possibility left. Return it.
        if len(filtered_possible_loc_dt) == 1:
            return filtered_possible_loc_dt[0]

        if len(filtered_possible_loc_dt) == 0:
            filtered_possible_loc_dt = list(possible_loc_dt)

        # If we get this far, we have in a wierd timezone transition
        # where the clocks have been wound back but is_dst is the same
        # in both (eg. Europe/Warsaw 1915 when they switched to CET).
        # At this point, we just have to guess unless we allow more
        # hints to be passed in (such as the UTC offset or abbreviation),
        # but that is just getting silly.
        #
        # Choose the earliest (by UTC) applicable timezone.
        sorting_keys = {}
        for local_dt in filtered_possible_loc_dt:
            key = local_dt.replace(tzinfo=None) - local_dt.tzinfo._utcoffset
            sorting_keys[key] = local_dt
        first_key = sorted(sorting_keys)[0]
        return sorting_keys[first_key]

    def utcoffset(self, dt, is_dst=None):
        '''See datetime.tzinfo.utcoffset

        The is_dst parameter may be used to remove ambiguity during DST
        transitions.

        >>> from pytz import timezone
        >>> tz = timezone('America/St_Johns')
        >>> ambiguous = datetime(2009, 10, 31, 23, 30)

        >>> tz.utcoffset(ambiguous, is_dst=False)
        datetime.timedelta(-1, 73800)

        >>> tz.utcoffset(ambiguous, is_dst=True)
        datetime.timedelta(-1, 77400)

        >>> try:
        ...     tz.utcoffset(ambiguous)
        ... except AmbiguousTimeError:
        ...     print('Ambiguous')
        Ambiguous

        '''
        if dt is None:
            return None
        elif dt.tzinfo is not self:
            dt = self.localize(dt, is_dst)
            return dt.tzinfo._utcoffset
        else:
            return self._utcoffset

    def dst(self, dt, is_dst=None):
        '''See datetime.tzinfo.dst

        The is_dst parameter may be used to remove ambiguity during DST
        transitions.

        >>> from pytz import timezone
        >>> tz = timezone('America/St_Johns')

        >>> normal = datetime(2009, 9, 1)

        >>> tz.dst(normal)
        datetime.timedelta(0, 3600)
        >>> tz.dst(normal, is_dst=False)
        datetime.timedelta(0, 3600)
        >>> tz.dst(normal, is_dst=True)
        datetime.timedelta(0, 3600)

        >>> ambiguous = datetime(2009, 10, 31, 23, 30)

        >>> tz.dst(ambiguous, is_dst=False)
        datetime.timedelta(0)
        >>> tz.dst(ambiguous, is_dst=True)
        datetime.timedelta(0, 3600)
        >>> try:
        ...     tz.dst(ambiguous)
        ... except AmbiguousTimeError:
        ...     print('Ambiguous')
        Ambiguous

        '''
        if dt is None:
            return None
        elif dt.tzinfo is not self:
            dt = self.localize(dt, is_dst)
            return dt.tzinfo._dst
        else:
            return self._dst

    def tzname(self, dt, is_dst=None):
        '''See datetime.tzinfo.tzname

        The is_dst parameter may be used to remove ambiguity during DST
        transitions.

        >>> from pytz import timezone
        >>> tz = timezone('America/St_Johns')

        >>> normal = datetime(2009, 9, 1)

        >>> tz.tzname(normal)
        'NDT'
        >>> tz.tzname(normal, is_dst=False)
        'NDT'
        >>> tz.tzname(normal, is_dst=True)
        'NDT'

        >>> ambiguous = datetime(2009, 10, 31, 23, 30)

        >>> tz.tzname(ambiguous, is_dst=False)
        'NST'
        >>> tz.tzname(ambiguous, is_dst=True)
        'NDT'
        >>> try:
        ...     tz.tzname(ambiguous)
        ... except AmbiguousTimeError:
        ...     print('Ambiguous')
        Ambiguous
        '''
        if dt is None:
            return self.zone
        elif dt.tzinfo is not self:
            dt = self.localize(dt, is_dst)
            return dt.tzinfo._tzname
        else:
            return self._tzname

    def __repr__(self):
        if self._dst:
            dst = 'DST'
        else:
            dst = 'STD'
        if self._utcoffset > _notime:
            return '<DstTzInfo %r %s+%s %s>' % (
                    self.zone, self._tzname, self._utcoffset, dst
                )
        else:
            return '<DstTzInfo %r %s%s %s>' % (
                    self.zone, self._tzname, self._utcoffset, dst
                )

    def __reduce__(self):
        # Special pickle to zone remains a singleton and to cope with
        # database changes.
        return pytz._p, (
                self.zone,
                _to_seconds(self._utcoffset),
                _to_seconds(self._dst),
                self._tzname
                )



def unpickler(zone, utcoffset=None, dstoffset=None, tzname=None):
    """Factory function for unpickling pytz tzinfo instances.

    This is shared for both StaticTzInfo and DstTzInfo instances, because
    database changes could cause a zones implementation to switch between
    these two base classes and we can't break pickles on a pytz version
    upgrade.
    """
    # Raises a KeyError if zone no longer exists, which should never happen
    # and would be a bug.
    tz = pytz.timezone(zone)

    # A StaticTzInfo - just return it
    if utcoffset is None:
        return tz

    # This pickle was created from a DstTzInfo. We need to
    # determine which of the list of tzinfo instances for this zone
    # to use in order to restore the state of any datetime instances using
    # it correctly.
    utcoffset = memorized_timedelta(utcoffset)
    dstoffset = memorized_timedelta(dstoffset)
    try:
        return tz._tzinfos[(utcoffset, dstoffset, tzname)]
    except KeyError:
        # The particular state requested in this timezone no longer exists.
        # This indicates a corrupt pickle, or the timezone database has been
        # corrected violently enough to make this particular
        # (utcoffset,dstoffset) no longer exist in the zone, or the
        # abbreviation has been changed.
        pass

    # See if we can find an entry differing only by tzname. Abbreviations
    # get changed from the initial guess by the database maintainers to
    # match reality when this information is discovered.
    for localized_tz in tz._tzinfos.values():
        if (localized_tz._utcoffset == utcoffset
                and localized_tz._dst == dstoffset):
            return localized_tz

    # This (utcoffset, dstoffset) information has been removed from the
    # zone. Add it back. This might occur when the database maintainers have
    # corrected incorrect information. datetime instances using this
    # incorrect information will continue to do so, exactly as they were
    # before being pickled. This is purely an overly paranoid safety net - I
    # doubt this will ever been needed in real life.
    inf = (utcoffset, dstoffset, tzname)
    tz._tzinfos[inf] = tz.__class__(inf, tz._tzinfos)
    return tz._tzinfos[inf]


########NEW FILE########
__FILENAME__ = urls
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
  ('^admin/', include(admin.site.urls)),
  ('^render/?', include('graphite.render.urls')),
  ('^cli/?', include('graphite.cli.urls')),
  ('^composer/?', include('graphite.composer.urls')),
  ('^metrics/?', include('graphite.metrics.urls')),
  ('^browser/?', include('graphite.browser.urls')),
  ('^account/?', include('graphite.account.urls')),
  ('^dashboard/?', include('graphite.dashboard.urls')),
  ('^whitelist/?', include('graphite.whitelist.urls')),
  ('^content/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.CONTENT_DIR}),
  ('graphlot/', include('graphite.graphlot.urls')),
  ('^version/', include('graphite.version.urls')),
  ('^events/', include('graphite.events.urls')),
  ('', 'graphite.browser.views.browser'),
)

handler500 = 'graphite.views.server_error'

########NEW FILE########
__FILENAME__ = util
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from graphite.account.models import Profile
from graphite.logger import log


# There are a couple different json modules floating around out there with
# different APIs. Hide the ugliness here.
try:
  import json
except ImportError:
  import simplejson as json

if hasattr(json, 'read') and not hasattr(json, 'loads'):
  json.loads = json.read
  json.dumps = json.write
  json.load = lambda file: json.read( file.read() )
  json.dump = lambda obj, file: file.write( json.write(obj) )


def getProfile(request,allowDefault=True):
  if request.user.is_authenticated():
    try:
      return request.user.profile
    except ObjectDoesNotExist:
      profile = Profile(user=request.user)
      profile.save()
      return profile
  elif allowDefault:
    return defaultProfile

def getProfileByUsername(username):
  try:
    user = User.objects.get(username=username)
    return Profile.objects.get(user=user)
  except ObjectDoesNotExist:
    return None


try:
  defaultUser = User.objects.get(username='default')
except User.DoesNotExist:
  log.info("Default user does not exist, creating it...")
  randomPassword = User.objects.make_random_password(length=16)
  defaultUser = User.objects.create_user('default','default@localhost.localdomain',randomPassword)
  defaultUser.save()

try:
  defaultProfile = Profile.objects.get(user=defaultUser)
except Profile.DoesNotExist:
  log.info("Default profile does not exist, creating it...")
  defaultProfile = Profile(user=defaultUser)
  defaultProfile.save()

########NEW FILE########
__FILENAME__ = urls
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License."""

from django.conf.urls.defaults import *

urlpatterns = patterns('graphite.version.views',
  ('', 'index'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from graphite import settings


def index(request):
  context = {
    'version' : settings.WEBAPP_VERSION,
  }
  return render_to_response('version.html', context)

########NEW FILE########
__FILENAME__ = views
import traceback
from django.conf import settings
from django.http import HttpResponseServerError
from django.template import Context, loader


def server_error(request, template_name='500.html'):
  template = loader.get_template(template_name)
  context = Context({
    'stacktrace' : traceback.format_exc()
  })
  return HttpResponseServerError( template.render(context) )

########NEW FILE########
__FILENAME__ = urls
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

from django.conf.urls.defaults import *

urlpatterns = patterns('graphite.whitelist.views',
  ('add','add'),
  ('remove','remove'),
  ('', 'show'),
)

########NEW FILE########
__FILENAME__ = views
"""Copyright 2008 Orbitz WorldWide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import os
try:
  import cPickle as pickle
except ImportError:
  import pickle
from random import randint
from django.http import HttpResponse
from django.conf import settings


def add(request):
  metrics = set( request.POST['metrics'].split() )
  whitelist = load_whitelist()
  new_whitelist = whitelist | metrics
  save_whitelist(new_whitelist)
  return HttpResponse(mimetype="text/plain", content="OK")

def remove(request):
  metrics = set( request.POST['metrics'].split() )
  whitelist = load_whitelist()
  new_whitelist = whitelist - metrics
  save_whitelist(new_whitelist)
  return HttpResponse(mimetype="text/plain", content="OK")

def show(request):
  whitelist = load_whitelist()
  members = '\n'.join( sorted(whitelist) )
  return HttpResponse(mimetype="text/plain", content=members)

def load_whitelist():
  fh = open(settings.WHITELIST_FILE, 'rb')
  whitelist = pickle.load(fh)
  fh.close()
  return whitelist

def save_whitelist(whitelist):
  serialized = pickle.dumps(whitelist, protocol=-1) #do this instead of dump() to raise potential exceptions before open()
  tmpfile = '%s-%d' % (settings.WHITELIST_FILE, randint(0, 100000))
  try:
    fh = open(tmpfile, 'wb')
    fh.write(serialized)
    fh.close()
    if os.path.exists(settings.WHITELIST_FILE):
      os.unlink(settings.WHITELIST_FILE)
    os.rename(tmpfile, settings.WHITELIST_FILE)
  finally:
    if os.path.exists(tmpfile):
      os.unlink(tmpfile)

########NEW FILE########
__FILENAME__ = rrd2whisper
#!/usr/bin/env python

import sys, os, time
import rrdtool
import whisper
from optparse import OptionParser

now = int( time.time() )

option_parser = OptionParser(usage='''%prog rrd_path''')
option_parser.add_option('--xFilesFactor', default=0.5, type='float')

(options, args) = option_parser.parse_args()

if len(args) < 1:
  option_parser.print_usage()
  sys.exit(1)

rrd_path = args[0]

rrd_info = rrdtool.info(rrd_path)

secondsPerPDP = rrd_info['step']

archives = []
for rra in rrd_info['rra']:
  secondsPerPoint = secondsPerPDP * rra['pdp_per_row']
  pointsToStore = rra['rows']
  archives.append( (secondsPerPoint,pointsToStore) )

for datasource,ds_info in rrd_info['ds'].items():
  path = rrd_path.replace('.rrd','_%s.wsp' % datasource)
  whisper.create(path, archives, xFilesFactor=options.xFilesFactor)
  size = os.stat(path).st_size
  print 'Created: %s (%d bytes)' % (path,size)

  print 'Migrating data'
  for rra in rrd_info['rra']:
    pointsToStore = rra['rows']
    secondsPerPoint = secondsPerPDP * rra['pdp_per_row']
    retention = secondsPerPoint * pointsToStore
    startTime = str(now - retention)
    endTime = str(now)
    (timeInfo,columns,rows) = rrdtool.fetch(rrd_path, 'AVERAGE', '-r', str(secondsPerPoint), '-s', startTime, '-e', endTime)
    rows.pop() #remove the last datapoint because RRD sometimes gives funky values
    i = list(columns).index(datasource)
    values = [row[i] for row in rows]
    timestamps = list(range(*timeInfo))
    datapoints = zip(timestamps,values)
    datapoints = filter(lambda p: p[1] is not None, datapoints)
    print ' migrating %d datapoints...' % len(datapoints)
    whisper.update_many(path, datapoints)

########NEW FILE########
__FILENAME__ = whisper-create
#!/usr/bin/env python

import sys, os
import whisper
from optparse import OptionParser

option_parser = OptionParser(
    usage='''%prog path timePerPoint:timeToStore [timePerPoint:timeToStore]*

timePerPoint and timeToStore specify lengths of time, for example:

60:1440      60 seconds per datapoint, 1440 datapoints = 1 day of retention
15m:8        15 minutes per datapoint, 8 datapoints = 2 hours of retention
1h:7d        1 hour per datapoint, 7 days of retention
12h:2y       12 hours per datapoint, 2 years of retention
''')
option_parser.add_option('--xFilesFactor', default=0.5, type='float')
option_parser.add_option('--aggregationMethod', default='average',
        type='string', help="Function to use when aggregating values (%s)" %
        ', '.join(whisper.aggregationMethods))
option_parser.add_option('--overwrite', default=False, action='store_true')

(options, args) = option_parser.parse_args()

if len(args) < 2:
  option_parser.print_usage()
  sys.exit(1)

path = args[0]
archives = [whisper.parseRetentionDef(retentionDef)
            for retentionDef in args[1:]]

if options.overwrite and os.path.exists(path):
  print 'Overwriting existing file: %s' % path
  os.unlink(path)

whisper.create(path, archives, xFilesFactor=options.xFilesFactor, aggregationMethod=options.aggregationMethod)

size = os.stat(path).st_size
print 'Created: %s (%d bytes)' % (path,size)

########NEW FILE########
__FILENAME__ = whisper-dump
#!/usr/bin/env python

import os
import struct
import whisper
import mmap
from optparse import OptionParser

option_parser = OptionParser(usage='''%prog path''')
(options, args) = option_parser.parse_args()

if len(args) != 1:
  option_parser.error("require one input file name")
else:
  path = args[0]

def mmap_file(filename):
  fd = os.open(filename, os.O_RDONLY) 
  map = mmap.mmap(fd, 0, prot=mmap.PROT_READ)
  os.close(fd)
  return map

def read_header(map):
  try:
    (aggregationType,maxRetention,xFilesFactor,archiveCount) = struct.unpack(whisper.metadataFormat,map[:whisper.metadataSize])
  except:
    raise CorruptWhisperFile("Unable to unpack header")

  archives = []
  archiveOffset = whisper.metadataSize

  for i in xrange(archiveCount):
    try:
      (offset, secondsPerPoint, points) = struct.unpack(whisper.archiveInfoFormat, map[archiveOffset:archiveOffset+whisper.archiveInfoSize])
    except:
      raise CorruptWhisperFile("Unable to reda archive %d metadata" % i)

    archiveInfo = {
      'offset' : offset,
      'secondsPerPoint' : secondsPerPoint,
      'points' : points,
      'retention' : secondsPerPoint * points,
      'size' : points * whisper.pointSize,
    }
    archives.append(archiveInfo)
    archiveOffset += whisper.archiveInfoSize

  header = {
    'aggregationMethod' : whisper.aggregationTypeToMethod.get(aggregationType, 'average'),
    'maxRetention' : maxRetention,
    'xFilesFactor' : xFilesFactor,
    'archives' : archives,
  }
  return header

def dump_header(header):
  print 'Meta data:'
  print '  aggregation method: %s' % header['aggregationMethod']
  print '  max retention: %d' % header['maxRetention']
  print '  xFilesFactor: %g' % header['xFilesFactor']
  print
  dump_archive_headers(header['archives'])

def dump_archive_headers(archives):
  for i,archive in enumerate(archives):
    print 'Archive %d info:' % i
    print '  offset: %d' % archive['offset']
    print '  seconds per point: %d' % archive['secondsPerPoint']
    print '  points: %d' % archive['points']
    print '  retention: %d' % archive['retention']
    print '  size: %d' % archive['size']
    print

def dump_archives(archives):
  for i,archive in enumerate(archives):
    print 'Archive %d data:' %i
    offset = archive['offset']
    for point in xrange(archive['points']):
      (timestamp, value) = struct.unpack(whisper.pointFormat, map[offset:offset+whisper.pointSize])
      print '%d: %d, %10.35g' % (point, timestamp, value)
      offset += whisper.pointSize
    print

map = mmap_file(path)
header = read_header(map)
dump_header(header)
dump_archives(header['archives'])

########NEW FILE########
__FILENAME__ = whisper-fetch
#!/usr/bin/env python

import sys, time
import whisper
from optparse import OptionParser

now = int( time.time() )
yesterday = now - (60 * 60 * 24)

option_parser = OptionParser(usage='''%prog [options] path''')
option_parser.add_option('--from', default=yesterday, type='int', dest='_from',
  help=("Unix epoch time of the beginning of "
        "your requested interval (default: 24 hours ago)"))
option_parser.add_option('--until', default=now, type='int',
  help="Unix epoch time of the end of your requested interval (default: now)")
option_parser.add_option('--json', default=False, action='store_true',
  help="Output results in JSON form")
option_parser.add_option('--pretty', default=False, action='store_true',
  help="Show human-readable timestamps instead of unix times")

(options, args) = option_parser.parse_args()

if len(args) != 1:
  option_parser.print_usage()
  sys.exit(1)

path = args[0]

from_time = int( options._from )
until_time = int( options.until )


(timeInfo, values) = whisper.fetch(path, from_time, until_time)

(start,end,step) = timeInfo

if options.json:
  values_json = str(values).replace('None','null')
  print '''{
    "start" : %d,
    "end" : %d,
    "step" : %d,
    "values" : %s
  }''' % (start,end,step,values_json)
  sys.exit(0)

t = start
for value in values:
  if options.pretty:
    timestr = time.ctime(t)
  else:
    timestr = str(t)
  if value is None:
    valuestr = "None"
  else:
    valuestr = "%f" % value
  print "%s\t%s" % (timestr,valuestr)
  t += step

########NEW FILE########
__FILENAME__ = whisper-info
#!/usr/bin/env python

import sys, os
import whisper
from optparse import OptionParser

option_parser = OptionParser(usage='''%prog path [field]''')
(options, args) = option_parser.parse_args()

if len(args) < 1:
  option_parser.print_usage()
  sys.exit(1)

path = args[0]
if len(args) > 1:
  field = args[1]
else:
  field = None

info = whisper.info(path)
info['fileSize'] = os.stat(path).st_size

if field:
  if field not in info:
    print 'Unknown field "%s". Valid fields are %s' % (field, ','.join(info))
    sys.exit(1)

  print info[field]
  sys.exit(0)


archives = info.pop('archives')
for key,value in info.items():
  print '%s: %s' % (key,value)
print

for i,archive in enumerate(archives):
  print 'Archive %d' % i
  for key,value in archive.items():
    print '%s: %s' % (key,value)
  print

########NEW FILE########
__FILENAME__ = whisper-merge
#!/usr/bin/env python

import sys
import whisper

from optparse import OptionParser

option_parser = OptionParser(
    usage='''%prog [options] from_path to_path''')

(options, args) = option_parser.parse_args()

if len(args) < 2:
  option_parser.print_usage()
  sys.exit(1)

path_from = args[0]
path_to = args[1]

whisper.merge(path_from, path_to)

########NEW FILE########
__FILENAME__ = whisper-resize
#!/usr/bin/env python

import sys, os, time, traceback
import whisper
from optparse import OptionParser

now = int(time.time())

option_parser = OptionParser(
    usage='''%prog path timePerPoint:timeToStore [timePerPoint:timeToStore]*

timePerPoint and timeToStore specify lengths of time, for example:

60:1440      60 seconds per datapoint, 1440 datapoints = 1 day of retention
15m:8        15 minutes per datapoint, 8 datapoints = 2 hours of retention
1h:7d        1 hour per datapoint, 7 days of retention
12h:2y       12 hours per datapoint, 2 years of retention
''')

option_parser.add_option(
    '--xFilesFactor', default=None,
    type='float', help="Change the xFilesFactor")
option_parser.add_option(
    '--aggregationMethod', default=None,
    type='string', help="Change the aggregation function (%s)" %
    ', '.join(whisper.aggregationMethods))
option_parser.add_option(
    '--force', default=False, action='store_true',
    help="Perform a destructive change")
option_parser.add_option(
    '--newfile', default=None, action='store',
    help="Create a new database file without removing the existing one")
option_parser.add_option(
    '--nobackup', action='store_true',
    help='Delete the .bak file after successful execution')

(options, args) = option_parser.parse_args()

if len(args) < 2:
  option_parser.print_usage()
  sys.exit(1)

path = args[0]
new_archives = [whisper.parseRetentionDef(retentionDef)
                for retentionDef in args[1:]]

info = whisper.info(path)
old_archives = info['archives']
# sort by precision, lowest to highest
old_archives.sort(key=lambda a: a['secondsPerPoint'], reverse=True)

if options.xFilesFactor is None:
  xff = info['xFilesFactor']
else:
  xff = options.xFilesFactor

if options.aggregationMethod is None:
  aggregationMethod = info['aggregationMethod']
else:
  aggregationMethod = options.aggregationMethod

print 'Retrieving all data from the archives'
for archive in old_archives:
  fromTime = now - archive['retention'] + archive['secondsPerPoint']
  untilTime = now
  timeinfo,values = whisper.fetch(path, fromTime, untilTime)
  archive['data'] = (timeinfo,values)

if options.newfile is None:
  tmpfile = path + '.tmp'
  if os.path.exists(tmpfile):
    print 'Removing previous temporary database file: %s' % tmpfile
    os.unlink(tmpfile)
  newfile = tmpfile
else:
  newfile = options.newfile

print 'Creating new whisper database: %s' % newfile
whisper.create(newfile, new_archives, xFilesFactor=xff, aggregationMethod=aggregationMethod)
size = os.stat(newfile).st_size
print 'Created: %s (%d bytes)' % (newfile,size)

print 'Migrating data...'
for archive in old_archives:
  timeinfo, values = archive['data']
  datapoints = zip( range(*timeinfo), values )
  datapoints = filter(lambda p: p[1] is not None, datapoints)
  whisper.update_many(newfile, datapoints)

if options.newfile is not None:
  sys.exit(0)

backup = path + '.bak'
print 'Renaming old database to: %s' % backup
os.rename(path, backup)

try:
  print 'Renaming new database to: %s' % path
  os.rename(tmpfile, path)
except:
  traceback.print_exc()
  print '\nOperation failed, restoring backup'
  os.rename(backup, path)
  sys.exit(1)

if options.nobackup:
  print "Unlinking backup: %s" % backup
  os.unlink(backup)

########NEW FILE########
__FILENAME__ = whisper-set-aggregation-method
#!/usr/bin/env python

import sys, os
import whisper
from optparse import OptionParser

option_parser = OptionParser(
    usage='%%prog path <%s>' % '|'.join(whisper.aggregationMethods))

(options, args) = option_parser.parse_args()

if len(args) < 2:
  option_parser.print_usage()
  sys.exit(1)

path = args[0]
aggregationMethod = args[1]

oldAggregationMethod = whisper.setAggregationMethod(path, aggregationMethod)

print 'Updated aggregation method: %s (%s -> %s)' % (path,oldAggregationMethod,aggregationMethod)

########NEW FILE########
__FILENAME__ = whisper-update
#!/usr/bin/env python

import sys, time
import whisper
from optparse import OptionParser

now = int( time.time() )

option_parser = OptionParser(
    usage='''%prog [options] path timestamp:value [timestamp:value]*''')

(options, args) = option_parser.parse_args()

if len(args) < 2:
  option_parser.print_usage()
  sys.exit(1)

path = args[0]
datapoint_strings = args[1:]
datapoint_strings = [point.replace('N:', '%d:' % now)
                     for point in datapoint_strings]
datapoints = [tuple(point.split(':')) for point in datapoint_strings]

if len(datapoints) == 1:
  timestamp,value = datapoints[0]
  whisper.update(path, value, timestamp)
else:
  print datapoints
  whisper.update_many(path, datapoints)

########NEW FILE########
__FILENAME__ = whisper
#!/usr/bin/env python
# Copyright 2008 Orbitz WorldWide
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# This module is an implementation of the Whisper database API
# Here is the basic layout of a whisper data file
#
# File = Header,Data
#	Header = Metadata,ArchiveInfo+
#		Metadata = aggregationType,maxRetention,xFilesFactor,archiveCount
#		ArchiveInfo = Offset,SecondsPerPoint,Points
#	Data = Archive+
#		Archive = Point+
#			Point = timestamp,value

import os, struct, time, operator, itertools

try:
  import fcntl
  CAN_LOCK = True
except ImportError:
  CAN_LOCK = False

LOCK = False
CACHE_HEADERS = False
AUTOFLUSH = False
__headerCache = {}

longFormat = "!L"
longSize = struct.calcsize(longFormat)
floatFormat = "!f"
floatSize = struct.calcsize(floatFormat)
valueFormat = "!d"
valueSize = struct.calcsize(valueFormat)
pointFormat = "!Ld"
pointSize = struct.calcsize(pointFormat)
metadataFormat = "!2LfL"
metadataSize = struct.calcsize(metadataFormat)
archiveInfoFormat = "!3L"
archiveInfoSize = struct.calcsize(archiveInfoFormat)

aggregationTypeToMethod = dict({
  1: 'average',
  2: 'sum',
  3: 'last',
  4: 'max',
  5: 'min'
})
aggregationMethodToType = dict([[v,k] for k,v in aggregationTypeToMethod.items()])
aggregationMethods = aggregationTypeToMethod.values()

debug = startBlock = endBlock = lambda *a,**k: None

UnitMultipliers = {
  'seconds' : 1,
  'minutes' : 60,
  'hours' : 3600,
  'days' : 86400,
  'weeks' : 86400 * 7,
  'years' : 86400 * 365
}


def getUnitString(s):
  if 'seconds'.startswith(s): return 'seconds'
  if 'minutes'.startswith(s): return 'minutes'
  if 'hours'.startswith(s): return 'hours'
  if 'days'.startswith(s): return 'days'
  if 'weeks'.startswith(s): return 'weeks'
  if 'years'.startswith(s): return 'years'
  raise ValueError("Invalid unit '%s'" % s)

def parseRetentionDef(retentionDef):
  import re
  (precision, points) = retentionDef.strip().split(':')

  if precision.isdigit():
    precision = int(precision) * UnitMultipliers[getUnitString('s')]
  else:
    precision_re = re.compile(r'^(\d+)([a-z]+)$')
    match = precision_re.match(precision)
    if match:
      precision = int(match.group(1)) * UnitMultipliers[getUnitString(match.group(2))]
    else:
      raise ValueError("Invalid precision specification '%s'" % precision)

  if points.isdigit():
    points = int(points)
  else:
    points_re = re.compile(r'^(\d+)([a-z]+)$')
    match = points_re.match(points)
    if match:
      points = int(match.group(1)) * UnitMultipliers[getUnitString(match.group(2))] / precision
    else:
      raise ValueError("Invalid retention specification '%s'" % points)

  return (precision, points)


class WhisperException(Exception):
    """Base class for whisper exceptions."""


class InvalidConfiguration(WhisperException):
    """Invalid configuration."""


class InvalidAggregationMethod(WhisperException):
    """Invalid aggregation method."""


class InvalidTimeInterval(WhisperException):
    """Invalid time interval."""


class TimestampNotCovered(WhisperException):
    """Timestamp not covered by any archives in this database."""

class CorruptWhisperFile(WhisperException):
  def __init__(self, error, path):
    Exception.__init__(self, error)
    self.error = error
    self.path = path

  def __repr__(self):
    return "<CorruptWhisperFile[%s] %s>" % (self.path, self.error)

  def __str__(self):
    return "%s (%s)" % (self.error, self.path)

def enableDebug():
  global open, debug, startBlock, endBlock
  class open(file):
    def __init__(self,*args,**kwargs):
      file.__init__(self,*args,**kwargs)
      self.writeCount = 0
      self.readCount = 0

    def write(self,data):
      self.writeCount += 1
      debug('WRITE %d bytes #%d' % (len(data),self.writeCount))
      return file.write(self,data)

    def read(self,bytes):
      self.readCount += 1
      debug('READ %d bytes #%d' % (bytes,self.readCount))
      return file.read(self,bytes)

  def debug(message):
    print 'DEBUG :: %s' % message

  __timingBlocks = {}

  def startBlock(name):
    __timingBlocks[name] = time.time()

  def endBlock(name):
    debug("%s took %.5f seconds" % (name,time.time() - __timingBlocks.pop(name)))


def __readHeader(fh):
  info = __headerCache.get(fh.name)
  if info:
    return info

  originalOffset = fh.tell()
  fh.seek(0)
  packedMetadata = fh.read(metadataSize)

  try:
    (aggregationType,maxRetention,xff,archiveCount) = struct.unpack(metadataFormat,packedMetadata)
  except:
    raise CorruptWhisperFile("Unable to read header", fh.name)

  archives = []

  for i in xrange(archiveCount):
    packedArchiveInfo = fh.read(archiveInfoSize)
    try:
      (offset,secondsPerPoint,points) = struct.unpack(archiveInfoFormat,packedArchiveInfo)
    except:
      raise CorruptWhisperFile("Unable to read archive%d metadata" % i, fh.name)

    archiveInfo = {
      'offset' : offset,
      'secondsPerPoint' : secondsPerPoint,
      'points' : points,
      'retention' : secondsPerPoint * points,
      'size' : points * pointSize,
    }
    archives.append(archiveInfo)

  fh.seek(originalOffset)
  info = {
    'aggregationMethod' : aggregationTypeToMethod.get(aggregationType, 'average'),
    'maxRetention' : maxRetention,
    'xFilesFactor' : xff,
    'archives' : archives,
  }
  if CACHE_HEADERS:
    __headerCache[fh.name] = info

  return info


def setAggregationMethod(path, aggregationMethod):
  """setAggregationMethod(path,aggregationMethod)

path is a string
aggregationMethod specifies the method to use when propogating data (see ``whisper.aggregationMethods``)
"""
  fh = open(path,'r+b')
  if LOCK:
    fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

  packedMetadata = fh.read(metadataSize)

  try:
    (aggregationType,maxRetention,xff,archiveCount) = struct.unpack(metadataFormat,packedMetadata)
  except:
    raise CorruptWhisperFile("Unable to read header", fh.name)

  try:
    newAggregationType = struct.pack( longFormat, aggregationMethodToType[aggregationMethod] )
  except KeyError:
    raise InvalidAggregationMethod("Unrecognized aggregation method: %s" %
          aggregationMethod)

  fh.seek(0)
  fh.write(newAggregationType)

  if AUTOFLUSH:
    fh.flush()
    os.fsync(fh.fileno())

  if CACHE_HEADERS and fh.name in __headerCache:
    del __headerCache[fh.name]

  fh.close()

  return aggregationTypeToMethod.get(aggregationType, 'average')


def validateArchiveList(archiveList):
  """ Validates an archiveList.
  An ArchiveList must:
  1. Have at least one archive config. Example: (60, 86400)
  2. No archive may be a duplicate of another.
  3. Higher precision archives' precision must evenly divide all lower precision archives' precision.
  4. Lower precision archives must cover larger time intervals than higher precision archives.
  5. Each archive must have at least enough points to consolidate to the next archive

  Returns True or False
  """

  if not archiveList:
    raise InvalidConfiguration("You must specify at least one archive configuration!")

  archiveList.sort(key=lambda a: a[0]) #sort by precision (secondsPerPoint)

  for i,archive in enumerate(archiveList):
    if i == len(archiveList) - 1:
      break

    nextArchive = archiveList[i+1]
    if not archive[0] < nextArchive[0]:
      raise InvalidConfiguration("A Whisper database may not configured having"
        "two archives with the same precision (archive%d: %s, archive%d: %s)" %
        (i, archive, i + 1, nextArchive))

    if nextArchive[0] % archive[0] != 0:
      raise InvalidConfiguration("Higher precision archives' precision "
        "must evenly divide all lower precision archives' precision "
        "(archive%d: %s, archive%d: %s)" %
        (i, archive[0], i + 1, nextArchive[0]))

    retention = archive[0] * archive[1]
    nextRetention = nextArchive[0] * nextArchive[1]

    if not nextRetention > retention:
      raise InvalidConfiguration("Lower precision archives must cover "
        "larger time intervals than higher precision archives "
        "(archive%d: %s seconds, archive%d: %s seconds)" %
        (i, archive[1], i + 1, nextArchive[1]))

    archivePoints = archive[1]
    pointsPerConsolidation = nextArchive[0] / archive[0]
    if not archivePoints >= pointsPerConsolidation:
      raise InvalidConfiguration("Each archive must have at least enough points "
        "to consolidate to the next archive (archive%d consolidates %d of "
        "archive%d's points but it has only %d total points)" %
        (i + 1, pointsPerConsolidation, i, archivePoints))


def create(path,archiveList,xFilesFactor=None,aggregationMethod=None,sparse=False):
  """create(path,archiveList,xFilesFactor=0.5,aggregationMethod='average')

path is a string
archiveList is a list of archives, each of which is of the form (secondsPerPoint,numberOfPoints)
xFilesFactor specifies the fraction of data points in a propagation interval that must have known values for a propagation to occur
aggregationMethod specifies the function to use when propogating data (see ``whisper.aggregationMethods``)
"""
  # Set default params
  if xFilesFactor is None:
    xFilesFactor = 0.5
  if aggregationMethod is None:
    aggregationMethod = 'average'

  #Validate archive configurations...
  validateArchiveList(archiveList)

  #Looks good, now we create the file and write the header
  if os.path.exists(path):
    raise InvalidConfiguration("File %s already exists!" % path)

  fh = open(path,'wb')
  if LOCK:
    fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

  aggregationType = struct.pack( longFormat, aggregationMethodToType.get(aggregationMethod, 1) )
  oldest = sorted([secondsPerPoint * points for secondsPerPoint,points in archiveList])[-1]
  maxRetention = struct.pack( longFormat, oldest )
  xFilesFactor = struct.pack( floatFormat, float(xFilesFactor) )
  archiveCount = struct.pack(longFormat, len(archiveList))
  packedMetadata = aggregationType + maxRetention + xFilesFactor + archiveCount
  fh.write(packedMetadata)
  headerSize = metadataSize + (archiveInfoSize * len(archiveList))
  archiveOffsetPointer = headerSize

  for secondsPerPoint,points in archiveList:
    archiveInfo = struct.pack(archiveInfoFormat, archiveOffsetPointer, secondsPerPoint, points)
    fh.write(archiveInfo)
    archiveOffsetPointer += (points * pointSize)

  if sparse:
    fh.seek(archiveOffsetPointer - headerSize - 1)
    fh.write("\0")
  else:
    # If not creating the file sparsely, then fill the rest of the file with
    # zeroes.
    remaining = archiveOffsetPointer - headerSize
    chunksize = 16384
    zeroes = '\x00' * chunksize
    while remaining > chunksize:
      fh.write(zeroes)
      remaining -= chunksize
    fh.write(zeroes[:remaining])

  if AUTOFLUSH:
    fh.flush()
    os.fsync(fh.fileno())

  fh.close()

def __aggregate(aggregationMethod, knownValues):
  if aggregationMethod == 'average':
    return float(sum(knownValues)) / float(len(knownValues))
  elif aggregationMethod == 'sum':
    return float(sum(knownValues))
  elif aggregationMethod == 'last':
    return knownValues[len(knownValues)-1]
  elif aggregationMethod == 'max':
    return max(knownValues)
  elif aggregationMethod == 'min':
    return min(knownValues)
  else:
    raise InvalidAggregationMethod("Unrecognized aggregation method %s" %
            aggregationMethod)


def __propagate(fh,header,timestamp,higher,lower):
  aggregationMethod = header['aggregationMethod']
  xff = header['xFilesFactor']

  lowerIntervalStart = timestamp - (timestamp % lower['secondsPerPoint'])
  lowerIntervalEnd = lowerIntervalStart + lower['secondsPerPoint']

  fh.seek(higher['offset'])
  packedPoint = fh.read(pointSize)
  (higherBaseInterval,higherBaseValue) = struct.unpack(pointFormat,packedPoint)

  if higherBaseInterval == 0:
    higherFirstOffset = higher['offset']
  else:
    timeDistance = lowerIntervalStart - higherBaseInterval
    pointDistance = timeDistance / higher['secondsPerPoint']
    byteDistance = pointDistance * pointSize
    higherFirstOffset = higher['offset'] + (byteDistance % higher['size'])

  higherPoints = lower['secondsPerPoint'] / higher['secondsPerPoint']
  higherSize = higherPoints * pointSize
  relativeFirstOffset = higherFirstOffset - higher['offset']
  relativeLastOffset = (relativeFirstOffset + higherSize) % higher['size']
  higherLastOffset = relativeLastOffset + higher['offset']
  fh.seek(higherFirstOffset)

  if higherFirstOffset < higherLastOffset: #we don't wrap the archive
    seriesString = fh.read(higherLastOffset - higherFirstOffset)
  else: #We do wrap the archive
    higherEnd = higher['offset'] + higher['size']
    seriesString = fh.read(higherEnd - higherFirstOffset)
    fh.seek(higher['offset'])
    seriesString += fh.read(higherLastOffset - higher['offset'])

  #Now we unpack the series data we just read
  byteOrder,pointTypes = pointFormat[0],pointFormat[1:]
  points = len(seriesString) / pointSize
  seriesFormat = byteOrder + (pointTypes * points)
  unpackedSeries = struct.unpack(seriesFormat, seriesString)

  #And finally we construct a list of values
  neighborValues = [None] * points
  currentInterval = lowerIntervalStart
  step = higher['secondsPerPoint']

  for i in xrange(0,len(unpackedSeries),2):
    pointTime = unpackedSeries[i]
    if pointTime == currentInterval:
      neighborValues[i/2] = unpackedSeries[i+1]
    currentInterval += step

  #Propagate aggregateValue to propagate from neighborValues if we have enough known points
  knownValues = [v for v in neighborValues if v is not None]
  if not knownValues:
    return False

  knownPercent = float(len(knownValues)) / float(len(neighborValues))
  if knownPercent >= xff: #we have enough data to propagate a value!
    aggregateValue = __aggregate(aggregationMethod, knownValues)
    myPackedPoint = struct.pack(pointFormat,lowerIntervalStart,aggregateValue)
    fh.seek(lower['offset'])
    packedPoint = fh.read(pointSize)
    (lowerBaseInterval,lowerBaseValue) = struct.unpack(pointFormat,packedPoint)

    if lowerBaseInterval == 0: #First propagated update to this lower archive
      fh.seek(lower['offset'])
      fh.write(myPackedPoint)
    else: #Not our first propagated update to this lower archive
      timeDistance = lowerIntervalStart - lowerBaseInterval
      pointDistance = timeDistance / lower['secondsPerPoint']
      byteDistance = pointDistance * pointSize
      lowerOffset = lower['offset'] + (byteDistance % lower['size'])
      fh.seek(lowerOffset)
      fh.write(myPackedPoint)

    return True

  else:
    return False


def update(path,value,timestamp=None):
  """update(path,value,timestamp=None)

path is a string
value is a float
timestamp is either an int or float
"""
  value = float(value)
  fh = open(path,'r+b')
  return file_update(fh, value, timestamp)


def file_update(fh, value, timestamp):
  if LOCK:
    fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

  header = __readHeader(fh)
  now = int( time.time() )
  if timestamp is None:
    timestamp = now

  timestamp = int(timestamp)
  diff = now - timestamp
  if not ((diff < header['maxRetention']) and diff >= 0):
    raise TimestampNotCovered("Timestamp not covered by any archives in "
      "this database.")

  for i,archive in enumerate(header['archives']): #Find the highest-precision archive that covers timestamp
    if archive['retention'] < diff: continue
    lowerArchives = header['archives'][i+1:] #We'll pass on the update to these lower precision archives later
    break

  #First we update the highest-precision archive
  myInterval = timestamp - (timestamp % archive['secondsPerPoint'])
  myPackedPoint = struct.pack(pointFormat,myInterval,value)
  fh.seek(archive['offset'])
  packedPoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedPoint)

  if baseInterval == 0: #This file's first update
    fh.seek(archive['offset'])
    fh.write(myPackedPoint)
    baseInterval,baseValue = myInterval,value
  else: #Not our first update
    timeDistance = myInterval - baseInterval
    pointDistance = timeDistance / archive['secondsPerPoint']
    byteDistance = pointDistance * pointSize
    myOffset = archive['offset'] + (byteDistance % archive['size'])
    fh.seek(myOffset)
    fh.write(myPackedPoint)

  #Now we propagate the update to lower-precision archives
  higher = archive
  for lower in lowerArchives:
    if not __propagate(fh, header, myInterval, higher, lower):
      break
    higher = lower

  if AUTOFLUSH:
    fh.flush()
    os.fsync(fh.fileno())

  fh.close()


def update_many(path,points):
  """update_many(path,points)

path is a string
points is a list of (timestamp,value) points
"""
  if not points: return
  points = [ (int(t),float(v)) for (t,v) in points]
  points.sort(key=lambda p: p[0],reverse=True) #order points by timestamp, newest first
  fh = open(path,'r+b')
  return file_update_many(fh, points)


def file_update_many(fh, points):
  if LOCK:
    fcntl.flock( fh.fileno(), fcntl.LOCK_EX )

  header = __readHeader(fh)
  now = int( time.time() )
  archives = iter( header['archives'] )
  currentArchive = archives.next()
  currentPoints = []

  for point in points:
    age = now - point[0]

    while currentArchive['retention'] < age: #we can't fit any more points in this archive
      if currentPoints: #commit all the points we've found that it can fit
        currentPoints.reverse() #put points in chronological order
        __archive_update_many(fh,header,currentArchive,currentPoints)
        currentPoints = []
      try:
        currentArchive = archives.next()
      except StopIteration:
        currentArchive = None
        break

    if not currentArchive:
      break #drop remaining points that don't fit in the database

    currentPoints.append(point)

  if currentArchive and currentPoints: #don't forget to commit after we've checked all the archives
    currentPoints.reverse()
    __archive_update_many(fh,header,currentArchive,currentPoints)

  if AUTOFLUSH:
    fh.flush()
    os.fsync(fh.fileno())

  fh.close()


def __archive_update_many(fh,header,archive,points):
  step = archive['secondsPerPoint']
  alignedPoints = [ (timestamp - (timestamp % step), value)
                    for (timestamp,value) in points ]
  #Create a packed string for each contiguous sequence of points
  packedStrings = []
  previousInterval = None
  currentString = ""
  for (interval,value) in alignedPoints:
    if interval == previousInterval: continue
    if (not previousInterval) or (interval == previousInterval + step):
      currentString += struct.pack(pointFormat,interval,value)
      previousInterval = interval
    else:
      numberOfPoints = len(currentString) / pointSize
      startInterval = previousInterval - (step * (numberOfPoints-1))
      packedStrings.append( (startInterval,currentString) )
      currentString = struct.pack(pointFormat,interval,value)
      previousInterval = interval
  if currentString:
    numberOfPoints = len(currentString) / pointSize
    startInterval = previousInterval - (step * (numberOfPoints-1))
    packedStrings.append( (startInterval,currentString) )

  #Read base point and determine where our writes will start
  fh.seek(archive['offset'])
  packedBasePoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedBasePoint)
  if baseInterval == 0: #This file's first update
    baseInterval = packedStrings[0][0] #use our first string as the base, so we start at the start

  #Write all of our packed strings in locations determined by the baseInterval
  for (interval,packedString) in packedStrings:
    timeDistance = interval - baseInterval
    pointDistance = timeDistance / step
    byteDistance = pointDistance * pointSize
    myOffset = archive['offset'] + (byteDistance % archive['size'])
    fh.seek(myOffset)
    archiveEnd = archive['offset'] + archive['size']
    bytesBeyond = (myOffset + len(packedString)) - archiveEnd

    if bytesBeyond > 0:
      fh.write( packedString[:-bytesBeyond] )
      assert fh.tell() == archiveEnd, "archiveEnd=%d fh.tell=%d bytesBeyond=%d len(packedString)=%d" % (archiveEnd,fh.tell(),bytesBeyond,len(packedString))
      fh.seek( archive['offset'] )
      fh.write( packedString[-bytesBeyond:] ) #safe because it can't exceed the archive (retention checking logic above)
    else:
      fh.write(packedString)

  #Now we propagate the updates to lower-precision archives
  higher = archive
  lowerArchives = [arc for arc in header['archives'] if arc['secondsPerPoint'] > archive['secondsPerPoint']]

  for lower in lowerArchives:
    fit = lambda i: i - (i % lower['secondsPerPoint'])
    lowerIntervals = [fit(p[0]) for p in alignedPoints]
    uniqueLowerIntervals = set(lowerIntervals)
    propagateFurther = False
    for interval in uniqueLowerIntervals:
      if __propagate(fh, header, interval, higher, lower):
        propagateFurther = True

    if not propagateFurther:
      break
    higher = lower


def info(path):
  """info(path)

path is a string
"""
  fh = open(path,'rb')
  info = __readHeader(fh)
  fh.close()
  return info


def fetch(path,fromTime,untilTime=None):
  """fetch(path,fromTime,untilTime=None)

path is a string
fromTime is an epoch time
untilTime is also an epoch time, but defaults to now
"""
  fh = open(path,'rb')
  return file_fetch(fh, fromTime, untilTime)


def file_fetch(fh, fromTime, untilTime):
  header = __readHeader(fh)
  now = int( time.time() )
  if untilTime is None:
    untilTime = now
  fromTime = int(fromTime)
  untilTime = int(untilTime)

  oldestTime = now - header['maxRetention']
  if fromTime < oldestTime:
    fromTime = oldestTime

  if not (fromTime < untilTime):
    raise InvalidTimeInterval("Invalid time interval")
  if untilTime > now:
    untilTime = now
  if untilTime < fromTime:
    untilTime = now

  diff = now - fromTime
  for archive in header['archives']:
    if archive['retention'] >= diff:
      break

  fromInterval = int( fromTime - (fromTime % archive['secondsPerPoint']) ) + archive['secondsPerPoint']
  untilInterval = int( untilTime - (untilTime % archive['secondsPerPoint']) ) + archive['secondsPerPoint']
  fh.seek(archive['offset'])
  packedPoint = fh.read(pointSize)
  (baseInterval,baseValue) = struct.unpack(pointFormat,packedPoint)

  if baseInterval == 0:
    step = archive['secondsPerPoint']
    points = (untilInterval - fromInterval) / step
    timeInfo = (fromInterval,untilInterval,step)
    valueList = [None] * points
    return (timeInfo,valueList)

  #Determine fromOffset
  timeDistance = fromInterval - baseInterval
  pointDistance = timeDistance / archive['secondsPerPoint']
  byteDistance = pointDistance * pointSize
  fromOffset = archive['offset'] + (byteDistance % archive['size'])

  #Determine untilOffset
  timeDistance = untilInterval - baseInterval
  pointDistance = timeDistance / archive['secondsPerPoint']
  byteDistance = pointDistance * pointSize
  untilOffset = archive['offset'] + (byteDistance % archive['size'])

  #Read all the points in the interval
  fh.seek(fromOffset)
  if fromOffset < untilOffset: #If we don't wrap around the archive
    seriesString = fh.read(untilOffset - fromOffset)
  else: #We do wrap around the archive, so we need two reads
    archiveEnd = archive['offset'] + archive['size']
    seriesString = fh.read(archiveEnd - fromOffset)
    fh.seek(archive['offset'])
    seriesString += fh.read(untilOffset - archive['offset'])

  #Now we unpack the series data we just read (anything faster than unpack?)
  byteOrder,pointTypes = pointFormat[0],pointFormat[1:]
  points = len(seriesString) / pointSize
  seriesFormat = byteOrder + (pointTypes * points)
  unpackedSeries = struct.unpack(seriesFormat, seriesString)

  #And finally we construct a list of values (optimize this!)
  valueList = [None] * points #pre-allocate entire list for speed
  currentInterval = fromInterval
  step = archive['secondsPerPoint']

  for i in xrange(0,len(unpackedSeries),2):
    pointTime = unpackedSeries[i]
    if pointTime == currentInterval:
      pointValue = unpackedSeries[i+1]
      valueList[i/2] = pointValue #in-place reassignment is faster than append()
    currentInterval += step

  fh.close()
  timeInfo = (fromInterval,untilInterval,step)
  return (timeInfo,valueList)

def merge(path_from, path_to, step=1<<12):
  headerFrom = info(path_from)

  archives = headerFrom['archives']
  archives.sort(key=operator.itemgetter('retention'), reverse=True)

  # Start from maxRetention of the oldest file, and skip forward at max 'step'
  # points at a time.
  fromTime = int(time.time()) - headerFrom['maxRetention']
  for archive in archives:
    pointsRemaining = archive['points']
    while pointsRemaining:
      pointsToRead = step
      if pointsRemaining < step:
        pointsToRead = pointsRemaining
      pointsRemaining -= pointsToRead
      untilTime = fromTime + (pointsToRead * archive['secondsPerPoint'])
      (timeInfo, values) = fetch(path_from, fromTime, untilTime)
      (start, end, archive_step) = timeInfo
      pointsToWrite = list(itertools.ifilter(
        lambda points: points[1] is not None,
        itertools.izip(xrange(start, end, archive_step), values)))
      pointsToWrite.sort(key=lambda p: p[0],reverse=True) #order points by timestamp, newest first
      update_many(path_to, pointsToWrite)
      fromTime = untilTime

########NEW FILE########
