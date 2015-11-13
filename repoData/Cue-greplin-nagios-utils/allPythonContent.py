__FILENAME__ = nagios
# Copyright 2011 The greplin-nagios-utils Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The Greplin monitoring package."""

import httplib
import json
import socket
import sys
import time
import threading


UNKNOWN = 3

CRITICAL = 2

WARNING = 1

OK = 0

STATUS_NAME = ['OK', 'WARN', 'CRIT', 'UNKNOWN']

# This is a thread-local variable so clients can override it per-thread.
GLOBAL_CONFIG = threading.local()
GLOBAL_CONFIG.outfile = sys.stdout


def output(msg):
  """Send output to output stream."""
  GLOBAL_CONFIG.outfile.write(msg)
  GLOBAL_CONFIG.outfile.write('\n')


def wgetWithTimeout(host, port, path, timeout, secure = False):
  """Gets an http page, but times out if it's too slow."""
  start = time.time()
  try:
    if secure:
      conn = httplib.HTTPSConnection(host, port, timeout=timeout)
    else:
      conn = httplib.HTTPConnection(host, port, timeout=timeout)
    conn.request('GET', path)
    body = conn.getresponse().read()
    return time.time() - start, body

  except (socket.gaierror, socket.error):
    output("CRIT: Could not connect to %s" % host)
    exit(CRITICAL)

  except socket.timeout:
    output("CRIT: Timed out after %s seconds" % timeout)
    exit(CRITICAL)


def parseJson(text):
  """Parses JSON, exiting with CRIT if the parse fails."""
  try:
    return json.loads(text)

  except ValueError, e:
    output('CRIT: %s (text was %r)' % (e, text))
    exit(CRITICAL)


def parseJsonFile(filename):
  """Parses JSON from a file, exiting with UNKNOWN if the file does not exist."""
  try:
    with open(filename) as f:
      return parseJson(f.read())
  except IOError, e:
    output('UNKNOWN: %s' % e)
    exit(UNKNOWN)


def lookup(source, *keys, **kw):
  """Successively looks up each key, returning the default keyword arg if a dead end is reached."""
  fallback = kw.get('default')
  try:
    for key in keys:
      source = source[key]
    return source
  except (KeyError, AttributeError, TypeError):
    return fallback


def statValue(data, *keys, **kw):
  """Returns the value of a stat."""
  return float(lookup(data, *keys, **kw))


def percent(value):
  """Formats the given float as a percentage."""
  return "%f%%" % (value * 100)


def parseArgs(scriptName, *args, **kw):
  """Parses arguments to the script."""
  argv = kw.get('argv', sys.argv)
  if len(argv) != len(args) + 1:
    output('USAGE: %s %s' % (scriptName, ' '.join([name for name, _ in args])))
    exit(UNKNOWN)

  result = {}
  idx = 0
  for name, fn in args:
    try:
      idx += 1
      result[name] = fn(argv[idx])
    except ValueError:
      output("Invalid value for %s: %r." % (name, argv[1]))
      exit(UNKNOWN)
  return result



class Rule(object):
  """A rule for when to warn or crit based on a stat value."""

  def check(self, value):
    """Checks if this rule should result in a WARN or CRIT."""
    raise NotImplementedError



class Minimum(Rule):
  """A rule that specifies minimum acceptable levels for a metric."""

  def __init__(self, warnLevel, critLevel, unit = ''):
    Rule.__init__(self)
    assert critLevel <= warnLevel
    self.warnLevel = warnLevel
    self.critLevel = critLevel
    self.unit = unit


  def check(self, value):
    """Checks if the given value is under the minimums."""
    if value < self.critLevel:
      return CRITICAL
    elif value < self.warnLevel:
      return WARNING
    else:
      return OK


  def format(self, name, value):
    """Formats as perf data."""
    return "'%s'=%.9g%s;%.9g;%.9g;;;" % (name, value, self.unit, self.warnLevel, self.critLevel)


  def message(self, name, value):
    """Create an error message."""
    if self.check(value) == CRITICAL:
      return ('%s: %.9g%s < %.9g%s') % (name, value, self.unit, self.critLevel, self.unit)
    elif self.check(value) == WARNING:
      return ('%s: %.9g%s < %.9g%s') % (name, value, self.unit, self.warnLevel, self.unit)



class Maximum(Rule):
  """A rule that specifies maximum acceptable levels for a metric."""

  def __init__(self, warnLevel, critLevel, unit = ''):
    Rule.__init__(self)
    assert critLevel >= warnLevel
    self.warnLevel = warnLevel
    self.critLevel = critLevel
    self.unit = unit


  def check(self, value):
    """Checks if the given value exceeds the maximums."""
    if value > self.critLevel:
      return CRITICAL
    elif value > self.warnLevel:
      return WARNING
    else:
      return OK


  def format(self, name, value):
    """Formats as perf data."""
    return "'%s'=%.9g%s;%.9g;%.9g;;;" % (name, value, self.unit, self.warnLevel, self.critLevel)


  def message(self, name, value):
    """Create an error message."""
    if self.check(value) == CRITICAL:
      return '%s: %.9g%s > %.9g%s' % (name, value, self.unit, self.critLevel, self.unit)
    elif self.check(value) == WARNING:
      return '%s: %.9g%s > %.9g%s' % (name, value, self.unit, self.warnLevel, self.unit)




class ResponseBuilder(object):
  """NRPE response builder."""

  def __init__(self):
    self._stats = []
    self._status = OK
    self._messages = [[], [], [], []]


  def addValue(self, name, value):
    """Adds a value to be tracked."""
    self._stats.append("'%s'=%s;;;;;" % (name, str(value)))
    return self


  def addStatLookup(self, name, data, *keys, **kw):
    """Adds a stat from a sequential key lookup."""
    value = lookup(data, *keys, **kw)
    return self.addValue(name, str(value) + kw.get('suffix', ''))


  def addStatChildren(self, name, data, *keys, **kw):
    """Adds a child for each child of the given dict."""
    values = lookup(data, *keys, **kw)
    if values:
      for childName, value in values.items():
        self.addValue(name % childName, str(value) + kw.get('suffix', ''))
    return self


  def addRule(self, name, rule, value):
    """Adds an alert rule and associated performance data."""
    status = rule.check(value)
    if status:
      ruleStatus = rule.check(value)
      self._status = max(self._status, ruleStatus)
      self._messages[ruleStatus].append(rule.message(name, value))
    self._stats.append(rule.format(name, value))
    return self


  def warnIf(self, condition, message=None):
    """Warn on a given condition."""
    if condition:
      self.warn(message)
    return self


  def critIf(self, condition, message=None):
    """Mark state as critical on the given condition."""
    if condition:
      self.crit(message)
    return self


  def unknownIf(self, condition, message=None):
    """Mark state as unknown on the given condition."""
    if condition:
      self.unknown(message)
    return self


  def warn(self, message=None):
    """Mark state as warning."""
    self._status = max(self._status, WARNING)
    if message is not None:
      self._messages[WARNING].append(message)
    return self


  def crit(self, message=None):
    """Mark state as critical."""
    self._status = max(self._status, CRITICAL)
    if message is not None:
      self._messages[CRITICAL].append(message)
    return self


  def unknown(self, message=None):
    """Mark state as unknown."""
    self._status = max(self._status, UNKNOWN)
    if message is not None:
      self._messages[UNKNOWN].append(message)
    return self


  def message(self, message):
    """Set the output message."""
    if message:
      self._messages[OK].append(message)
    return self


  def build(self):
    """Builds the response."""
    return ' '.join(self._stats)


  def finish(self):
    """Builds the response, prints it, and exits."""
    status = STATUS_NAME[self._status]
    messages = self._messages[UNKNOWN] + self._messages[CRITICAL] + self._messages[WARNING] + self._messages[OK]
    if messages:
      status += ': ' + (', '.join(messages))
    if self._stats:
      status += '|' + self.build()

    output(status)
    sys.exit(self._status)

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
# Copyright 2011 The greplin-nagios-utils Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Server that runs Python checks."""

from eventlet import wsgi, tpool
import eventlet
from flask import Flask, request, make_response, jsonify, abort
APP = Flask(__name__)

import imp
import os
import logging
from optparse import OptionParser
from collections import defaultdict
from cStringIO import StringIO
from eloise import nagios
from greplin.nagios import GLOBAL_CONFIG

# Cache mapping check names to checker modules
CHECK_CACHE = {}
# Arg parser options
OPTIONS = None
# Stats on how many times each checker has run
STATS = defaultdict(int)
# Graphite reporter
GRAPHITE = None


def runChecker(fun, name, args):
  """Run a checker function with the given args. Return a string."""
  outStream = StringIO()
  GLOBAL_CONFIG.outfile = outStream
  try:
    fun(args)
  except SystemExit:
    pass
  except Exception, e:
    logging.exception('Checker %s failed', name)
    return 'CRIT: Checker exception: %s' % e
  return outStream.getvalue()


def checker(name):
  """Get a checker function. Caches imports. Writes output to outfile."""
  if name not in CHECK_CACHE:
    filename = os.path.join(os.path.dirname(__file__), OPTIONS.checkdir, 'check_%s.py' % name)
    if os.path.exists(filename):
      CHECK_CACHE[name] = imp.load_source('check_%s' % name, filename)
    else:
      raise KeyError('No such file: %s' % filename)

  return lambda args: runChecker(CHECK_CACHE[name].check, name, args)


@APP.route('/')
def root():
  """Root request handler."""
  return jsonify(STATS)


@APP.route('/update/<name>')
def update(name):
  """Reload a check module."""
  if name in CHECK_CACHE:
    del CHECK_CACHE[name]
    return "Reloaded"
  else:
    abort(404)


@APP.route('/check/<name>')
def check(name):
  """Run a check."""
  try:
    checkFun = checker(name)
  except KeyError, e:
    print e
    return abort(404)

  args = request.args.getlist('arg')
  args.insert(0, 'check_%s' % name)

  output = tpool.execute(checkFun, args)
  if GRAPHITE:
    try:
      parsed = nagios.parseResponse(output)
    except Exception, e: # ok to catch generic error # pylint: disable=W0703
      print 'During %s: %r' % (name, e)
      parsed = None

    if parsed and parsed[2]:
      for k, v in parsed[2].iteritems():
        if isinstance(v, (int, long, float)):
          parts = ['checkserver', name]
          parts.extend(args[1:])
          parts.append(k)
          GRAPHITE.enqueue('.'.join(parts), v)
      if not GRAPHITE.isAlive():
        GRAPHITE.start()

  resp = make_response(output)
  STATS[name] += 1

  resp.headers['Content-Type'] = 'text/plain; charset=UTF-8'
  return resp


def main():
  """Run the server."""
  global OPTIONS # pylint: disable=W0603
  parser = OptionParser()
  parser.add_option("-d", "--checkdir", dest="checkdir", metavar="DIR",
                    default="/usr/lib/nagios/plugins", help="directory with check scripts")
  parser.add_option("-l", "--log-level", dest="loglevel", metavar="LEVEL",
                    help="logging level", default='info')
  parser.add_option("-g", "--graphite", dest="graphite", metavar="GRAPHITE_HOST",
                    help="graphite host, specify as host:post", default='')
  parser.add_option("-p", "--port", dest="port", metavar="PORT",
                    help="port to listen on", default=8111, type="int")
  OPTIONS = parser.parse_args()[0]

  levelName = {'debug': logging.DEBUG, 'info': logging.INFO, 'warn': logging.WARN, 'error': logging.ERROR}
  logging.basicConfig(level=levelName.get(OPTIONS.loglevel.lower(), logging.WARN))

  if OPTIONS.graphite:
    from greplin.scales import util

    host, port = OPTIONS.graphite.split(':')

    global GRAPHITE # pylint: disable=W0603
    GRAPHITE = util.GraphiteReporter(host, int(port))
    GRAPHITE.start()

  wsgi.server(eventlet.listen(('', int(OPTIONS.port))), APP)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = check_error
#!/usr/bin/env python
# Copyright 2012 The greplin-nagios-utils Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Status

nagios config:
use       regular-service
params    $HOSTNAME$
"""


from greplin.nagios import parseArgs, Maximum, ResponseBuilder


def check(argv):
  """Runs the check."""
  _ = parseArgs('check_fast.py', ('NAME', str), argv=argv) / 0 # Badness!


  (ResponseBuilder().addRule('seven', Maximum(8, 11), 7)).finish()


if __name__ == '__main__':
  import sys
  check(sys.argv)

########NEW FILE########
__FILENAME__ = check_fast
#!/usr/bin/env python
# Copyright 2012 The greplin-nagios-utils Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Status

nagios config:
use       regular-service
params    $HOSTNAME$
"""


from greplin.nagios import parseArgs, Maximum, ResponseBuilder


def check(argv):
  """Runs the check."""
  _ = parseArgs('check_fast.py', ('NAME', str), argv=argv)

  (ResponseBuilder().addRule('seven', Maximum(8, 11), 7)).finish()


if __name__ == '__main__':
  import sys
  check(sys.argv)

########NEW FILE########
__FILENAME__ = check_slow
#!/usr/bin/env python
# Copyright 2012 The greplin-nagios-utils Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Status

nagios config:
use       regular-service
params    $HOSTNAME$
"""


from greplin.nagios import parseArgs, Maximum, ResponseBuilder
import time


def check(argv):
  """Runs the check."""
  _ = parseArgs('check_slow.py', ('NAME', str), argv=argv)
  time.sleep(5)

  (ResponseBuilder().addRule('harrypotter', Maximum(42, 108), 69)).finish()


if __name__ == '__main__':
  import sys
  check(sys.argv)

########NEW FILE########
__FILENAME__ = nagiosconf
#!/usr/bin/env python
# Copyright 2011 The greplin-nagios-utils Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration generator for Nagios."""

import sys



class NagObj(object):
  """base nagios object
  """

  def __init__(self, name):
    object.__init__(self)
    self.name = name
    self.props = {}
    self.meta = {}


  def __repr__(self):
    assert self.typeName != None
    if not self.props:
      return "# skipped define for empty %s %s\n" % (self.typeName, self.name)

    ret = ["define %s {" % self.typeName ]
    mlen = max([ len(k) for k in self.props.keys()]) + 2
    for k, v in self.props.items():
      ret.append("  %s%s%s" % (k, ' ' * (mlen-len(k)), v))
    ret.append("}")
    return "\n".join(ret)



class NagBag(object):
  """bags of nagios objects - take care of creation, name uniqueness, ...
  """


  def __init__(self, klass):
    object.__init__(self)
    self.klass = klass
    self.bag = {}


  def create(self, name):
    """Create a new object with the given name
    """
    assert not name in self.bag

    inst = self.klass(name)
    self.bag[name] = inst
    return inst


  def get(self, name):
    """Get a object by name
    """
    return self.bag.get(name, None)


  def getOrCreate(self, name):
    """Create or get a new object with the given name
    """
    assert name is not None
    name = name.strip()
    assert len(name) > 0

    if name in self.bag:
      return self.bag[name]

    return self.create(name)


  def generate(self, out):
    """Write config fragemts for this bag to the given output stream
    """
    for item in sorted(self.bag.items()):
      out.write('%s\n' % repr(item[1]))




class HostGroup(NagObj):
  """Represent a nagios hostgroup
  """
  typeName = 'hostgroup'


  def __init__(self, name):
    NagObj.__init__(self, name)
    self.members = []


  def add(self, member):
    """Add a host to this group
    """
    self.members.append(member)
    

  def __repr__(self):
    self.props['hostgroup_name'] = self.name
    return NagObj.__repr__(self)



class HostGroupBag(NagBag):
  """The set of host groups
  """

  def __init__(self):
    NagBag.__init__(self, HostGroup)



HOSTGROUPS = HostGroupBag()



class Host(NagObj):
  """Represent a nagios host
  """

  typeName = 'host'


  def __init__(self, name):
    NagObj.__init__(self, name)
    self.hostgroups = set()


  def addGroup(self, name):
    """Mark this host as a member of the given group, creating the group if needed
    """
    hg = HOSTGROUPS.getOrCreate(name)
    self.hostgroups.add(hg)
    hg.add(self)


  def __repr__(self):
    self.props['host_name'] = self.name
    self.props['hostgroups'] = ','.join(sorted([hg.name for hg in self.hostgroups]))
    return NagObj.__repr__(self)



class HostBag(NagBag):
  """The set of hosts
  """

  def __init__(self):
    NagBag.__init__(self, Host)



HOSTS = HostBag()



class Service(NagObj):
  """Represent a nagios service
  """
  typeName = 'service'



class ServiceBag(NagBag):
  """The set of services
  """

  def __init__(self):
    NagBag.__init__(self, Service)


SERVICES = ServiceBag()


def generate(out=sys.stdout):
  """Print nagios configuration fragments to the given output stream
  """
  HOSTGROUPS.generate(out)
  HOSTS.generate(out)
  SERVICES.generate(out)

########NEW FILE########
