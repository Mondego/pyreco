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
import os.path

# Figure out where we're installed
BIN_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BIN_DIR)

# Make sure that carbon's 'lib' dir is in the $PYTHONPATH if we're running from
# source.
LIB_DIR = os.path.join(ROOT_DIR, "lib")
sys.path.insert(0, LIB_DIR)

from carbon.util import run_twistd_plugin
from carbon.exceptions import CarbonConfigException

try:
    run_twistd_plugin(__file__)
except CarbonConfigException, exc:
    raise SystemExit(str(exc))

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
import os.path

# Figure out where we're installed
BIN_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BIN_DIR)

# Make sure that carbon's 'lib' dir is in the $PYTHONPATH if we're running from
# source.
LIB_DIR = os.path.join(ROOT_DIR, "lib")
sys.path.insert(0, LIB_DIR)

from carbon.util import run_twistd_plugin
from carbon.exceptions import CarbonConfigException

try:
    run_twistd_plugin(__file__)
except CarbonConfigException, exc:
    raise SystemExit(str(exc))

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
import os.path

# Figure out where we're installed
BIN_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BIN_DIR)

# Make sure that carbon's 'lib' dir is in the $PYTHONPATH if we're running from
# source.
LIB_DIR = os.path.join(ROOT_DIR, "lib")
sys.path.insert(0, LIB_DIR)

from carbon.util import run_twistd_plugin
from carbon.exceptions import CarbonConfigException

try:
    run_twistd_plugin(__file__)
except CarbonConfigException, exc:
    raise SystemExit(str(exc))

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
  raise SystemExit("Error: Couldn't read config file: %s" % SCHEMAS_FILE)

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
  raise SystemExit( "Storage-schemas configuration '%s' failed validation" % SCHEMAS_FILE)

print "Storage-schemas configuration '%s' is valid" % SCHEMAS_FILE

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

import re
import sys
import time
import socket
import platform
import subprocess

CARBON_SERVER = '127.0.0.1'
CARBON_PORT = 2003
DELAY = 60

def get_loadavg():
    """
    Get the load average for a unix-like system.
    For more details, "man proc" and "man uptime"
    """
    if platform.system() == "Linux":
        return open('/proc/loadavg').read().split()[:3]
    else:
        command = "uptime"
        process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        stdout = process.communicate()[0].strip()
        # Split on whitespace and commas
        output = re.split("[\s,]+", stdout)
        return output[-3:]

def run(sock, delay):
    """Make the client go go go"""
    while True:
        now = int(time.time())
        lines = []
        #We're gonna report all three loadavg values
        loadavg = get_loadavg()
        lines.append("system.loadavg_1min %s %d" % (loadavg[0], now))
        lines.append("system.loadavg_5min %s %d" % (loadavg[1], now))
        lines.append("system.loadavg_15min %s %d" % (loadavg[2], now))
        message = '\n'.join(lines) + '\n' #all lines must end in a newline
        print "sending message"
        print '-' * 80
        print message
        sock.sendall(message)
        time.sleep(delay)

def main():
    """Wrap it all up together"""
    delay = DELAY
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.isdigit():
            delay = int(arg)
        else:
            sys.stderr.write("Ignoring non-integer argument. Using default: %ss\n" % delay)

    sock = socket.socket()
    try:
        sock.connect( (CARBON_SERVER, CARBON_PORT) )
    except socket.error:
        raise SystemExit("Couldn't connect to %(server)s on port %(port)d, is carbon-cache.py running?" % { 'server':CARBON_SERVER, 'port':CARBON_PORT })

    try:
        run(sock, delay)
    except KeyboardInterrupt:
        sys.stderr.write("\nExiting on CTRL-c\n")
        sys.exit(0)

if __name__ == "__main__":
    main()

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
    self.compute_task.start(settings['WRITE_BACK_FREQUENCY'] or frequency, now=False)
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
        if not self.interval_buffers:
          self.close()
          self.configured = False
          del BufferManager.buffers[self.metric_path]

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
from carbon import events, log


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
    log.msg("Couldn't match metric %s with any aggregation rule. Passing on un-aggregated." % metric)
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

    regex_pattern = '\\.'.join(regex_pattern_parts) + '$'
    self.regex = re.compile(regex_pattern)

  def build_template(self):
    self.output_template = self.output_pattern.replace('<', '%(').replace('>', ')s')


def avg(values):
  if values:
    return float( sum(values) ) / len(values)


AGGREGATION_METHODS = {
  'sum' : sum,
  'avg' : avg,
  'min' : min,
  'max' : max,
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
                if datapoint[1] != datapoint[1]:  # filter out NaN values
                    continue
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
        self.resetDelay()
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
from carbon import log, state, instrumentation
from collections import deque
from time import time


SEND_QUEUE_LOW_WATERMARK = settings.MAX_QUEUE_SIZE * settings.QUEUE_LOW_WATERMARK_PCT


class CarbonClientProtocol(Int32StringReceiver):
  def connectionMade(self):
    log.clients("%s::connectionMade" % self)
    self.paused = False
    self.connected = True
    self.transport.registerProducer(self, streaming=True)
    # Define internal metric names
    self.lastResetTime = time()
    self.destinationName = self.factory.destinationName
    self.queuedUntilReady = 'destinations.%s.queuedUntilReady' % self.destinationName
    self.sent = 'destinations.%s.sent' % self.destinationName
    self.relayMaxQueueLength = 'destinations.%s.relayMaxQueueLength' % self.destinationName
    self.batchesSent = 'destinations.%s.batchesSent' % self.destinationName

    self.slowConnectionReset = 'destinations.%s.slowConnectionReset' % self.destinationName

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
    self.factory.enqueue(metric, datapoint)
    reactor.callLater(settings.TIME_TO_DEFER_SENDING, self.sendQueued)

  def _sendDatapoints(self, datapoints):
      self.sendString(pickle.dumps(datapoints, protocol=-1))
      instrumentation.increment(self.sent, len(datapoints))
      instrumentation.increment(self.batchesSent)
      self.factory.checkQueue()

  def sendQueued(self):
    """This should be the only method that will be used to send stats.
    In order to not hold the event loop and prevent stats from flowing
    in while we send them out, this will process
    settings.MAX_DATAPOINTS_PER_MESSAGE stats, send them, and if there
    are still items in the queue, this will invoke reactor.callLater
    to schedule another run of sendQueued after a reasonable enough time
    for the destination to process what it has just received.

    Given a queue size of one million stats, and using a
    chained_invocation_delay of 0.0001 seconds, you'd get 1,000
    sendQueued() invocations/second max.  With a
    settings.MAX_DATAPOINTS_PER_MESSAGE of 100, the rate of stats being
    sent could theoretically be as high as 100,000 stats/sec, or
    6,000,000 stats/minute.  This is probably too high for a typical
    receiver to handle.

    In practice this theoretical max shouldn't be reached because
    network delays should add an extra delay - probably on the order
    of 10ms per send, so the queue should drain with an order of
    minutes, which seems more realistic.
    """
    chained_invocation_delay = 0.0001
    queueSize = self.factory.queueSize

    instrumentation.max(self.relayMaxQueueLength, queueSize)
    if self.paused:
      instrumentation.max(self.queuedUntilReady, queueSize)
      return
    if not self.factory.hasQueuedDatapoints():
      return
    
    if settings.USE_RATIO_RESET is True:
      if not self.connectionQualityMonitor():
        self.resetConnectionForQualityReasons("Sent: {0}, Received: {1}".format(
          instrumentation.prior_stats.get(self.sent, 0),
          instrumentation.prior_stats.get('metricsReceived', 0)))

    self._sendDatapoints(self.factory.takeSomeFromQueue())
    if (self.factory.queueFull.called and
        queueSize < SEND_QUEUE_LOW_WATERMARK):
      self.factory.queueHasSpace.callback(queueSize)
    if self.factory.hasQueuedDatapoints():
      reactor.callLater(chained_invocation_delay, self.sendQueued)


  def connectionQualityMonitor(self):
    """Checks to see if the connection for this factory appears to
    be delivering stats at a speed close to what we're receiving
    them at.

    This is open to other measures of connection quality.

    Returns a Bool

    True means that quality is good, OR
    True means that the total received is less than settings.MIN_RESET_STAT_FLOW

    False means that quality is bad

    """
    destination_sent = float(instrumentation.prior_stats.get(self.sent, 0))
    total_received = float(instrumentation.prior_stats.get('metricsReceived', 0))
    instrumentation.increment(self.slowConnectionReset, 0)
    if total_received < settings.MIN_RESET_STAT_FLOW:
      return True

    if (destination_sent / total_received) < settings.MIN_RESET_RATIO:
      return False
    else:
      return True

  def resetConnectionForQualityReasons(self, reason):
    """Only re-sets the connection if it's been
    settings.MIN_RESET_INTERVAL seconds since the last re-set.

    Reason should be a string containing the quality info that led to
    a re-set.
    """
    if (time() - self.lastResetTime) < float(settings.MIN_RESET_INTERVAL):
      return
    else:
      self.factory.connectedProtocol.disconnect()
      self.lastResetTime = time()
      instrumentation.increment(self.slowConnectionReset)
      log.clients("%s:: resetConnectionForQualityReasons: %s" % (self, reason))

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
    self.queue = deque() # Change to make this the sole source of metrics to be sent.
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
    state.events.cacheFull()
    log.clients('%s send queue is full (%d datapoints)' % (self, result))

  def queueSpaceCallback(self, result):
    if self.queueFull.called:
      log.clients('%s send queue has space available' % self.connectedProtocol)
      self.queueFull = Deferred()
      self.queueFull.addCallback(self.queueFullCallback)
      state.events.cacheSpaceAvailable()
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
    """Use self.queue, which is a collections.deque, to pop up to
    settings.MAX_DATAPOINTS_PER_MESSAGE items from the left of the
    queue.
    """
    def yield_max_datapoints():
      for count in range(settings.MAX_DATAPOINTS_PER_MESSAGE):
        try:
          yield self.queue.popleft()
        except IndexError:
          raise StopIteration
    return list(yield_max_datapoints())

  def checkQueue(self):
    """Check if the queue is empty. If the queue isn't empty or
    doesn't exist yet, then this will invoke the callback chain on the
    self.queryEmpty Deferred chain with the argument 0, and will
    re-set the queueEmpty callback chain with a new Deferred
    object.
    """
    if not self.queue:
      self.queueEmpty.callback(0)
      self.queueEmpty = Deferred()

  def enqueue(self, metric, datapoint):
    self.queue.append((metric, datapoint))

  def enqueue_from_left(self, metric, datapoint):
    self.queue.appendleft((metric, datapoint))

  def sendDatapoint(self, metric, datapoint):
    instrumentation.increment(self.attemptedRelays)
    if self.queueSize >= settings.MAX_QUEUE_SIZE:
      if not self.queueFull.called:
        self.queueFull.callback(self.queueSize)
      instrumentation.increment(self.fullQueueDrops)
    else:
      self.enqueue(metric, datapoint)

    if self.connectedProtocol:
      reactor.callLater(settings.TIME_TO_DEFER_SENDING, self.connectedProtocol.sendQueued)
    else:
      instrumentation.increment(self.queuedUntilConnected)

  def sendHighPriorityDatapoint(self, metric, datapoint):
    """The high priority datapoint is one relating to the carbon
    daemon itself.  It puts the datapoint on the left of the deque,
    ahead of other stats, so that when the carbon-relay, specifically,
    is overwhelmed its stats are more likely to make it through and
    expose the issue at hand.

    In addition, these stats go on the deque even when the max stats
    capacity has been reached.  This relies on not creating the deque
    with a fixed max size.
    """
    instrumentation.increment(self.attemptedRelays)
    self.enqueue_from_left(metric, datapoint)

    if self.connectedProtocol:
      reactor.callLater(settings.TIME_TO_DEFER_SENDING, self.connectedProtocol.sendQueued)
    else:
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

  def sendHighPriorityDatapoint(self, metric, datapoint):
    for destination in self.router.getDestinations(metric):
      self.client_factories[destination].sendHighPriorityDatapoint(metric, datapoint)

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
from carbon.exceptions import CarbonConfigException

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
  LOG_CACHE_HITS=True,
  WHISPER_AUTOFLUSH=False,
  WHISPER_SPARSE_CREATE=False,
  WHISPER_FALLOCATE_CREATE=False,
  WHISPER_LOCK_WRITES=False,
  MAX_DATAPOINTS_PER_MESSAGE=500,
  MAX_AGGREGATION_INTERVALS=5,
  MAX_QUEUE_SIZE=1000,
  QUEUE_LOW_WATERMARK_PCT=0.8,
  TIME_TO_DEFER_SENDING=0.0001,
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
  CARBON_METRIC_PREFIX='carbon',
  CARBON_METRIC_INTERVAL=60,
  WRITE_BACK_FREQUENCY=None,
  MIN_RESET_STAT_FLOW=1000,
  MIN_RESET_RATIO=0.9,
  MIN_RESET_INTERVAL=121,
  USE_RATIO_RESET=False,
  LOG_LISTENER_CONN_SUCCESS=True,
  AGGREGATION_RULES='aggregation-rules.conf',
  REWRITE_RULES='rewrite-rules.conf',
  RELAY_RULES='relay-rules.conf',
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
    # Verifies a file exists *and* is readable
    if not os.access(path, os.R_OK):
        raise CarbonConfigException("Error: Missing config file or wrong perms on %s" % path)

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
      raise CarbonConfigException("Failed to read config file %s" % path)

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

        if settings.WHISPER_FALLOCATE_CREATE:
            if whisper.CAN_FALLOCATE:
                log.msg("Enabling Whisper fallocate support")
            else:
                log.err("WHISPER_FALLOCATE_CREATE is enabled but linking failed.")

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
                    if settings.USER:
                        # We have not yet switched to the specified user,
                        # but that user must be able to create files in this
                        # directory.
                        os.chown(logdir, self.parent["uid"], self.parent["gid"])
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
            self["rules"] = join(settings["CONF_DIR"], settings['AGGREGATION_RULES'])
        settings["aggregation-rules"] = self["rules"]

        if self["rewrite-rules"] is None:
            self["rewrite-rules"] = join(settings["CONF_DIR"],
                                         settings['REWRITE_RULES'])
        settings["rewrite-rules"] = self["rewrite-rules"]


class CarbonRelayOptions(CarbonCacheOptions):

    optParameters = [
        ["rules", "", None, "Use the given relay rules file."],
        ["aggregation-rules", "", None, "Use the given aggregation rules file."],
        ] + CarbonCacheOptions.optParameters

    def postOptions(self):
        CarbonCacheOptions.postOptions(self)
        if self["rules"] is None:
            self["rules"] = join(settings["CONF_DIR"], settings['RELAY_RULES'])
        settings["relay-rules"] = self["rules"]

        if self["aggregation-rules"] is None:
            self["rules"] = join(settings["CONF_DIR"], settings['AGGREGATION_RULES'])
        settings["aggregation-rules"] = self["aggregation-rules"]

        if settings["RELAY_METHOD"] not in ("rules", "consistent-hashing", "aggregated-consistent-hashing"):
            print ("In carbon.conf, RELAY_METHOD must be either 'rules' or "
                   "'consistent-hashing' or 'aggregated-consistent-hashing'. Invalid value: '%s'" %
                   settings.RELAY_METHOD)
            sys.exit(1)


def get_default_parser(usage="%prog [options] <start|stop|status>"):
    """Create a parser for command line options."""
    parser = OptionParser(usage=usage)
    parser.add_option(
        "--debug", action="store_true",
        help="Run in the foreground, log to stdout")
    parser.add_option(
        "--nodaemon", action="store_true",
        help="Run in the foreground")
    parser.add_option(
        "--profile",
        help="Record performance profile data to the given file")
    parser.add_option(
        "--pidfile", default=None,
        help="Write pid to the given file")
    parser.add_option(
        "--umask", default=None,
        help="Use the given umask when creating files")
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

    graphite_root = kwargs.get("ROOT_DIR")
    if graphite_root is None:
        graphite_root = os.environ.get('GRAPHITE_ROOT')
    if graphite_root is None:
        raise CarbonConfigException("Either ROOT_DIR or GRAPHITE_ROOT "
                         "needs to be provided.")

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
        raise CarbonConfigException("Error: missing required config %r" % config)

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
specialMetricReceived = Event('specialMetricReceived')
specialMetricGenerated = Event('specialMetricGenerated')
cacheFull = Event('cacheFull')
cacheSpaceAvailable = Event('cacheSpaceAvailable')
pauseReceivingMetrics = Event('pauseReceivingMetrics')
resumeReceivingMetrics = Event('resumeReceivingMetrics')

# Default handlers
metricReceived.addHandler(lambda metric, datapoint: state.instrumentation.increment('metricsReceived'))
specialMetricReceived.addHandler(lambda metric, datapoint: state.instrumentation.increment('metricsReceived'))


cacheFull.addHandler(lambda: state.instrumentation.increment('cache.overflow'))
cacheFull.addHandler(lambda: setattr(state, 'cacheTooFull', True))
cacheSpaceAvailable.addHandler(lambda: setattr(state, 'cacheTooFull', False))

pauseReceivingMetrics.addHandler(lambda: setattr(state, 'metricReceiversPaused', True))
resumeReceivingMetrics.addHandler(lambda: setattr(state, 'metricReceiversPaused', False))


# Avoid import circularities
from carbon import log, state

########NEW FILE########
__FILENAME__ = exceptions
class CarbonConfigException(Exception):
    """Raised when a carbon daemon is improperly configured"""

########NEW FILE########
__FILENAME__ = hashing
try:
  from hashlib import md5
except ImportError:
  from md5 import md5
import bisect


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
      while position in [r[0] for r in self.ring]:
        position = position + 1
      entry = (position, node)
      bisect.insort(self.ring, entry)

  def remove_node(self, node):
    self.nodes.discard(node)
    self.ring = [entry for entry in self.ring if entry[1] != node]

  def get_node(self, key):
    assert self.ring
    node = None
    node_iter = self.get_nodes(key)
    node = node_iter.next()
    node_iter.close()
    return node

  def get_nodes(self, key):
    assert self.ring
    nodes = set()
    position = self.compute_ring_position(key)
    search_entry = (position, None)
    index = bisect.bisect_left(self.ring, search_entry) % len(self.ring)
    last_index = (index - 1) % len(self.ring)
    while len(nodes) < len(self.nodes) and index != last_index:
      next_entry = self.ring[index]
      (position, next_node) = next_entry
      if next_node not in nodes:
        nodes.add(next_node)
        yield next_node

      index = (index + 1) % len(self.ring)

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
prior_stats = {}
HOSTNAME = socket.gethostname().replace('.','_')
PAGESIZE = os.sysconf('SC_PAGESIZE')
rusage = getrusage(RUSAGE_SELF)
lastUsage = rusage.ru_utime + rusage.ru_stime
lastUsageTime = time.time()

# NOTE: Referencing settings in this *top level scope* will
# give you *defaults* only. Probably not what you wanted.

# TODO(chrismd) refactor the graphite metrics hierarchy to be cleaner,
# more consistent, and make room for frontend metrics.
#metric_prefix = "Graphite.backend.%(program)s.%(instance)s." % settings


def increment(stat, increase=1):
  try:
    stats[stat] += increase
  except KeyError:
    stats[stat] = increase

def max(stat, newval):
  try:
    if stats[stat] < newval:
      stats[stat] = newval
  except KeyError:
    stats[stat] = newval

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
  global prior_stats
  myStats = stats.copy()
  myPriorStats = {}
  stats.clear()

  # cache metrics
  if settings.program == 'carbon-cache':
    record = cache_record
    updateTimes = myStats.get('updateTimes', [])
    committedPoints = myStats.get('committedPoints', 0)
    creates = myStats.get('creates', 0)
    errors = myStats.get('errors', 0)
    cacheQueries = myStats.get('cacheQueries', 0)
    cacheBulkQueries = myStats.get('cacheBulkQueries', 0)
    cacheOverflow = myStats.get('cache.overflow', 0)
    cacheBulkQuerySizes = myStats.get('cacheBulkQuerySize', [])

    if updateTimes:
      avgUpdateTime = sum(updateTimes) / len(updateTimes)
      record('avgUpdateTime', avgUpdateTime)

    if committedPoints:
      pointsPerUpdate = float(committedPoints) / len(updateTimes)
      record('pointsPerUpdate', pointsPerUpdate)

    if cacheBulkQuerySizes:
      avgBulkSize = sum(cacheBulkQuerySizes) / len(cacheBulkQuerySizes)
      record('cache.bulk_queries_average_size', avgBulkSize)

    record('updateOperations', len(updateTimes))
    record('committedPoints', committedPoints)
    record('creates', creates)
    record('errors', errors)
    record('cache.queries', cacheQueries)
    record('cache.bulk_queries', cacheBulkQueries)
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
    prefix = 'destinations.'
    relay_stats =  [(k,v) for (k,v) in myStats.items() if k.startswith(prefix)]
    for stat_name, stat_value in relay_stats:
      record(stat_name, stat_value)
      # Preserve the count of sent metrics so that the ratio of
      # received : sent can be checked per-relay to determine the
      # health of the destination.
      if stat_name.endswith('.sent'):
        myPriorStats[stat_name] = stat_value

  # common metrics
  record('metricsReceived', myStats.get('metricsReceived', 0))
  record('cpuUsage', getCpuUsage())

  # And here preserve count of messages received in the prior periiod
  myPriorStats['metricsReceived'] = myStats.get('metricsReceived', 0)
  prior_stats.clear()
  prior_stats.update(myPriorStats)

  try: # This only works on Linux
    record('memUsage', getMemUsage())
  except:
    pass


def cache_record(metric, value):
    prefix = settings.CARBON_METRIC_PREFIX
    if settings.instance is None:
      fullMetric = '%s.agents.%s.%s' % (prefix, HOSTNAME, metric)
    else:
      fullMetric = '%s.agents.%s-%s.%s' % (prefix, HOSTNAME, settings.instance, metric)
    datapoint = (time.time(), value)
    cache.MetricCache.store(fullMetric, datapoint)

def relay_record(metric, value):
    prefix = settings.CARBON_METRIC_PREFIX
    if settings.instance is None:
      fullMetric = '%s.relays.%s.%s' % (prefix, HOSTNAME, metric)
    else:
      fullMetric = '%s.relays.%s-%s.%s' % (prefix, HOSTNAME, settings.instance, metric)
    datapoint = (time.time(), value)
    events.metricGenerated(fullMetric, datapoint)

def aggregator_record(metric, value):
    prefix = settings.CARBON_METRIC_PREFIX
    if settings.instance is None:
      fullMetric = '%s.aggregator.%s.%s' % (prefix, HOSTNAME, metric)
    else:
      fullMetric = '%s.aggregator.%s-%s.%s' % (prefix, HOSTNAME, settings.instance, metric)
    datapoint = (time.time(), value)
    events.metricGenerated(fullMetric, datapoint)


class InstrumentationService(Service):
    def __init__(self):
        self.record_task = LoopingCall(recordMetrics)

    def startService(self):
        if settings.CARBON_METRIC_INTERVAL > 0:
          self.record_task.start(settings.CARBON_METRIC_INTERVAL, False)
        Service.startService(self)

    def stopService(self):
        if settings.CARBON_METRIC_INTERVAL > 0:
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
import time

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
    if settings.LOG_LISTENER_CONN_SUCCESS:
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
      if settings.LOG_LISTENER_CONN_SUCCESS:
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
    if datapoint[1] != datapoint[1]: # filter out NaN values
      return
    if int(datapoint[0]) == -1: # use current time if none given: https://github.com/graphite-project/carbon/issues/54
      datapoint = (time.time(), datapoint[1])
    
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
  MAX_LENGTH = 1024 ** 3 # 1mb

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
      if settings.LOG_CACHE_HITS:
        log.query('[%s] cache query for \"%s\" returned %d values' % (self.peerAddr, metric, len(datapoints)))
      instrumentation.increment('cacheQueries')

    elif request['type'] == 'cache-query-bulk':
      datapointsByMetric = {}
      metrics = request['metrics']
      for metric in metrics:
        datapointsByMetric[metric] = MetricCache.get(metric, [])

      result = dict(datapointsByMetric=datapointsByMetric)

      if settings.LOG_CACHE_HITS:
        log.query('[%s] cache query bulk for \"%d\" metrics returned %d values' %
            (self.peerAddr, len(metrics), sum([len(datapoints) for datapoints in datapointsByMetric.values()])))
      instrumentation.increment('cacheBulkQueries')
      instrumentation.append('cacheBulkQuerySize', len(metrics))

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
      if line.startswith('#') or not pattern:
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
from carbon.exceptions import CarbonConfigException


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
    raise CarbonConfigException("Could not read rules file %s" % path)

  defaultRule = None
  for section in parser.sections():
    if not parser.has_option(section, 'destinations'):
      raise CarbonConfigException("Rules file %s section %s does not define a "
                       "'destinations' list" % (path, section))

    destination_strings = parser.get(section, 'destinations').split(',')
    destinations = parseDestinations(destination_strings)

    if parser.has_option(section, 'pattern'):
      if parser.has_option(section, 'default'):
        raise CarbonConfigException("Section %s contains both 'pattern' and "
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
        raise CarbonConfigException("Only one default rule can be specified")
      defaultRule = RelayRule(condition=lambda metric: True,
                              destinations=destinations)

  if not defaultRule:
    raise CarbonConfigException("No default rule defined. You must specify exactly one "
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

    for count,node in enumerate(self.ring.get_nodes(key)):
      if count == self.replication_factor:
        return
      (server, instance) = node
      port = self.instance_ports[ (server, instance) ]
      yield (server, port, instance)

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

class AggregatedConsistentHashingRouter(DatapointRouter):
  def __init__(self, agg_rules_manager, replication_factor=1):
    self.hash_router = ConsistentHashingRouter(replication_factor)
    self.agg_rules_manager = agg_rules_manager

  def addDestination(self, destination):
    self.hash_router.addDestination(destination)

  def removeDestination(self, destination):
    self.hash_router.removeDestination(destination)

  def getDestinations(self, key):
    # resolve metric to aggregate forms
    resolved_metrics = []
    for rule in self.agg_rules_manager.rules:
      aggregate_metric = rule.get_aggregate_metric(key)
      if aggregate_metric is None:
        continue
      else:
        resolved_metrics.append(aggregate_metric)

    # if the metric will not be aggregated, send it raw
    # (will pass through aggregation)
    if len(resolved_metrics) == 0:
      resolved_metrics.append(key)

    # get consistent hashing destinations based on aggregate forms
    destinations = set()
    for resolved_metric in resolved_metrics:
      for destination in self.hash_router.getDestinations(resolved_metric):
        destinations.add(destination)

    for destination in destinations:
      yield destination

########NEW FILE########
__FILENAME__ = service
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
from carbon.exceptions import CarbonConfigException
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
      raise CarbonConfigException("Required setting DESTINATIONS is missing from carbon.conf")

    for destination in util.parseDestinations(settings.DESTINATIONS):
      client_manager.startClient(destination)

    return root_service


def createRelayService(config):
    from carbon.routers import RelayRulesRouter, ConsistentHashingRouter, AggregatedConsistentHashingRouter
    from carbon.client import CarbonClientManager
    from carbon.conf import settings
    from carbon import events

    root_service = createBaseService(config)

    # Configure application components
    if settings.RELAY_METHOD == 'rules':
      router = RelayRulesRouter(settings["relay-rules"])
    elif settings.RELAY_METHOD == 'consistent-hashing':
      router = ConsistentHashingRouter(settings.REPLICATION_FACTOR)
    elif settings.RELAY_METHOD == 'aggregated-consistent-hashing':
      from carbon.aggregator.rules import RuleManager
      RuleManager.read_from(settings["aggregation-rules"])
      router = AggregatedConsistentHashingRouter(RuleManager, settings.REPLICATION_FACTOR)

    client_manager = CarbonClientManager(router)
    client_manager.setServiceParent(root_service)

    events.metricReceived.addHandler(client_manager.sendDatapoint)
    events.metricGenerated.addHandler(client_manager.sendDatapoint)
    events.specialMetricReceived.addHandler(client_manager.sendHighPriorityDatapoint)
    events.specialMetricGenerated.addHandler(client_manager.sendHighPriorityDatapoint)

    if not settings.DESTINATIONS:
      raise CarbonConfigException("Required setting DESTINATIONS is missing from carbon.conf")

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

from os.path import join, exists, sep
from carbon.conf import OrderedConfigParser, settings
from carbon.exceptions import CarbonConfigException
from carbon.util import pickle
from carbon import log


STORAGE_SCHEMAS_CONFIG = join(settings.CONF_DIR, 'storage-schemas.conf')
STORAGE_AGGREGATION_CONFIG = join(settings.CONF_DIR, 'storage-aggregation.conf')
STORAGE_LISTS_DIR = join(settings.CONF_DIR, 'lists')

def getFilesystemPath(metric):
  metric_path = metric.replace('.',sep).lstrip(sep) + '.wsp'
  return join(settings.LOCAL_DATA_DIR, metric_path)


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
    except whisper.InvalidConfiguration, e:
      log.msg("Invalid schemas found in %s: %s" % (section, e) )
  
  schemaList.append(defaultSchema)
  return schemaList


def loadAggregationSchemas():
  # NOTE: This abuses the Schema classes above, and should probably be refactored.
  schemaList = []
  config = OrderedConfigParser()

  try:
    config.read(STORAGE_AGGREGATION_CONFIG)
  except (IOError, CarbonConfigException):
    log.msg("%s not found or wrong perms, ignoring." % STORAGE_AGGREGATION_CONFIG)

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
__FILENAME__ = test_aggregator_rules
import os
import unittest
from carbon.aggregator.rules import AggregationRule

class AggregationRuleTest(unittest.TestCase):

    def test_inclusive_regexes(self):
        """
        Test case for https://github.com/graphite-project/carbon/pull/120

        Consider the two rules:

        aggregated.hist.p99        (10) = avg hosts.*.hist.p99
        aggregated.hist.p999       (10) = avg hosts.*.hist.p999

        Before the abovementioned patch the second rule would be treated as
        expected but the first rule would lead to an aggegated metric
        aggregated.hist.p99 which would in fact be equivalent to
        avgSeries(hosts.*.hist.p99,hosts.*.hist.p999).
        """

        method = 'avg'
        frequency = 10

        input_pattern = 'hosts.*.hist.p99'
        output_pattern = 'aggregated.hist.p99'
        rule99 = AggregationRule(input_pattern, output_pattern,
                                 method, frequency)

        input_pattern = 'hosts.*.hist.p999'
        output_pattern = 'aggregated.hist.p999'
        rule999 = AggregationRule(input_pattern, output_pattern,
                                  method, frequency)

        self.assertEqual(rule99.get_aggregate_metric('hosts.abc.hist.p99'),
                         'aggregated.hist.p99')
        self.assertEqual(rule99.get_aggregate_metric('hosts.abc.hist.p999'),
                         None)

        self.assertEqual(rule999.get_aggregate_metric('hosts.abc.hist.p99'),
                         None)
        self.assertEqual(rule999.get_aggregate_metric('hosts.abc.hist.p999'),
                         'aggregated.hist.p999')

########NEW FILE########
__FILENAME__ = test_conf
import os
from os import makedirs
from os.path import dirname, join
from unittest import TestCase
from mocker import MockerTestCase
from carbon.conf import get_default_parser, parse_options, read_config
from carbon.exceptions import CarbonConfigException


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

    def __getitem__(self, name):
        return self.__dict__[name]

    def __setitem__(self, name, value):
        self.__dict__[name] = value


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
        self.assertEqual("a", parser.defaults["instance"])


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
            read_config("carbon-foo", FakeOptions(config=None))
        except CarbonConfigException, e:
            self.assertEqual("Either ROOT_DIR or GRAPHITE_ROOT "
                             "needs to be provided.", str(e))
        else:
            self.fail("Did not raise exception.")

    def test_config_is_not_required(self):
        """
        If the '--config' option is not provided, it defaults to
        ROOT_DIR/conf/carbon.conf.
        """
        root_dir = self.makeDir()
        conf_dir = join(root_dir, "conf")
        makedirs(conf_dir)
        self.makeFile(content="[foo]",
                      basename="carbon.conf",
                      dirname=conf_dir)
        options = FakeOptions(config=None, instance=None,
                              pidfile=None, logdir=None)
        read_config("carbon-foo", options, ROOT_DIR=root_dir)
        self.assertEqual(join(root_dir, "conf", "carbon.conf"),
                         options["config"])

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
        self.assertEqual(join("foo", "storage", "log",
                              "carbon-foo", "carbon-foo-x"),
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
        self.assertEqual(join("bar", "log", "carbon-foo", "carbon-foo-x"),
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
        self.assertEqual("boo/carbon-foo-x", settings.LOG_DIR)

########NEW FILE########
__FILENAME__ = test_hashing
import os
import unittest
from carbon.hashing import ConsistentHashRing

class HashIntegrityTest(unittest.TestCase):

    def test_2_node_positional_itegrity(self):
        """Make a cluster, verify we don't have positional collisions"""
        ring = ConsistentHashRing([])
        for n in range(2):
            ring.add_node(("192.168.10.%s" % str(10+n),"%s" % str(10+n)))
        self.assertEqual(
                len([n[0] for n in ring.ring]),
            len(set([n[0] for n in ring.ring])))


    def test_3_node_positional_itegrity(self):
        """Make a cluster, verify we don't have positional collisions"""
        ring = ConsistentHashRing([])
        for n in range(3):
            ring.add_node(("192.168.10.%s" % str(10+n),"%s" % str(10+n)))
        self.assertEqual(
                len([n[0] for n in ring.ring]),
            len(set([n[0] for n in ring.ring])))


    def test_4_node_positional_itegrity(self):
        """Make a cluster, verify we don't have positional collisions"""
        ring = ConsistentHashRing([])
        for n in range(4):
            ring.add_node(("192.168.10.%s" % str(10+n),"%s" % str(10+n)))
        self.assertEqual(
                len([n[0] for n in ring.ring]),
            len(set([n[0] for n in ring.ring])))


    def test_5_node_positional_itegrity(self):
        """Make a cluster, verify we don't have positional collisions"""
        ring = ConsistentHashRing([])
        for n in range(5):
            ring.add_node(("192.168.10.%s" % str(10+n),"%s" % str(10+n)))
        self.assertEqual(
                len([n[0] for n in ring.ring]),
            len(set([n[0] for n in ring.ring])))


    def test_6_node_positional_itegrity(self):
        """Make a cluster, verify we don't have positional collisions"""
        ring = ConsistentHashRing([])
        for n in range(6):
            ring.add_node(("192.168.10.%s" % str(10+n),"%s" % str(10+n)))
        self.assertEqual(
                len([n[0] for n in ring.ring]),
            len(set([n[0] for n in ring.ring])))


    def test_7_node_positional_itegrity(self):
        """Make a cluster, verify we don't have positional collisions"""
        ring = ConsistentHashRing([])
        for n in range(7):
            ring.add_node(("192.168.10.%s" % str(10+n),"%s" % str(10+n)))
        self.assertEqual(
                len([n[0] for n in ring.ring]),
            len(set([n[0] for n in ring.ring])))


    def test_8_node_positional_itegrity(self):
        """Make a cluster, verify we don't have positional collisions"""
        ring = ConsistentHashRing([])
        for n in range(8):
            ring.add_node(("192.168.10.%s" % str(10+n),"%s" % str(10+n)))
        self.assertEqual(
                len([n[0] for n in ring.ring]),
            len(set([n[0] for n in ring.ring])))


    def test_9_node_positional_itegrity(self):
        """Make a cluster, verify we don't have positional collisions"""
        ring = ConsistentHashRing([])
        for n in range(9):
            ring.add_node(("192.168.10.%s" % str(10+n),"%s" % str(10+n)))
        self.assertEqual(
                len([n[0] for n in ring.ring]),
            len(set([n[0] for n in ring.ring])))

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

    if options.debug or options.nodaemon:
        twistd_options.extend(["--nodaemon"])
    if options.profile:
        twistd_options.append("--profile")
    if options.pidfile:
        twistd_options.extend(["--pidfile", options.pidfile])
    if options.umask:
        twistd_options.extend(["--umask", options.umask])

    # Now for the plugin-specific options.
    twistd_options.append(program)

    if options.debug:
        twistd_options.append("--debug")

    for option_name, option_value in vars(options).items():
        if (option_value is not None and
            option_name not in ("debug", "profile", "pidfile", "umask", "nodaemon")):
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
from os.path import exists, dirname
import errno

import whisper
from carbon import state
from carbon.cache import MetricCache
from carbon.storage import getFilesystemPath, loadStorageSchemas,\
    loadAggregationSchemas
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
  """Generates metrics with the most cached values first and applies a soft
  rate limit on new metrics"""
  global lastCreateInterval
  global createCount
  metrics = MetricCache.counts()

  t = time.time()
  metrics.sort(key=lambda item: item[1], reverse=True)  # by queue size, descending
  log.debug("Sorted %d cache queues in %.6f seconds" % (len(metrics),
                                                        time.time() - t))

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

    try:  # metrics can momentarily disappear from the MetricCache due to the implementation of MetricCache.store()
      datapoints = MetricCache.pop(metric)
    except KeyError:
      log.msg("MetricCache contention, skipping %s update for now" % metric)
      continue  # we simply move on to the next metric when this race condition occurs

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
        try:
          os.makedirs(dbDir, 0755)
        except OSError as e:
          if e.errno != errno.EEXIST:
            log.err("%s" % e)
        log.creates("creating database file %s (archive=%s xff=%s agg=%s)" %
                    (dbFilePath, archiveConfig, xFilesFactor, aggregationMethod))
        whisper.create(dbFilePath, archiveConfig, xFilesFactor, aggregationMethod, settings.WHISPER_SPARSE_CREATE, settings.WHISPER_FALLOCATE_CREATE)
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
            time.sleep(int(t2 + 1) - t2)

    # Avoid churning CPU when only new metrics are in the cache
    if not dataWritten:
      time.sleep(0.1)


def writeForever():
  while reactor.running:
    try:
      writeCachedDataPoints()
    except:
      log.err()

    time.sleep(1)  # The writer thread only sleeps when the cache is empty or an error occurs


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
    agg_schemas = loadAggregationSchemas()
  except:
    log.msg("Failed to reload aggregation schemas")
    log.err()


def shutdownModifyUpdateSpeed():
    try:
        settings.MAX_UPDATES_PER_SECOND = settings.MAX_UPDATES_PER_SECOND_ON_SHUTDOWN
        log.msg("Carbon shutting down.  Changed the update rate to: " + str(settings.MAX_UPDATES_PER_SECOND_ON_SHUTDOWN))
    except KeyError:
        log.msg("Carbon shutting down.  Update rate not changed")


class WriterService(Service):

    def __init__(self):
        self.storage_reload_task = LoopingCall(reloadStorageSchemas)
        self.aggregation_reload_task = LoopingCall(reloadAggregationSchemas)

    def startService(self):
        self.storage_reload_task.start(60, False)
        self.aggregation_reload_task.start(60, False)
        reactor.addSystemEventTrigger('before', 'shutdown', shutdownModifyUpdateSpeed)
        reactor.callInThread(writeForever)
        Service.startService(self)

    def stopService(self):
        self.storage_reload_task.stop()
        self.aggregation_reload_task.stop()
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
