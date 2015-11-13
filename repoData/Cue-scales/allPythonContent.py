__FILENAME__ = aggregation
# Copyright 2011 The scales Authors.
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

"""Utilities for multi-server stat aggregation."""

from collections import defaultdict
import datetime
try:
  # Prefer simplejson for speed.
  import simplejson as json
except ImportError:
  import json
import os
import re

import six

class DefaultFormat(object):
  """The default format"""

  def getCount(self, data):
    """Get the count"""
    return data['count']


  def getValue(self, data):
    """Get the value"""
    return data['average']



class DirectFormat(object):
  """The direct format (pointed straight at the field we want)"""

  def getCount(self, _):
    "The count"
    return 1


  def getValue(self, data):
    "The value"
    return data



class TimerFormat(object):
  """A Yammer Metrics Timer datum"""

  def getCount(self, data):
    """Get the count"""
    assert data['type'] == "timer"
    return data['rate']['count']


  def getValue(self, data):
    """Get the value"""
    assert data['type'] == "timer"
    return data['duration']['median']



class TimerMeanFormat(object):
  """A Yammer Metrics Timer datum"""

  def getCount(self, data):
    """Get the count"""
    assert data['type'] == "timer"
    return data['rate']['count']


  def getValue(self, data):
    """Get the value"""
    assert data['type'] == "timer"
    return data['duration']['mean']



class CounterFormat(object):
  """A Yammer Metrics Counter datum"""

  def getCount(self, data):
    """Get the count"""
    assert data['type'] == "counter"
    return data['count']


  def getValue(self, data):
    """Get the value of a count (just the count)"""
    assert data['type'] == "counter"
    return data['count']



class MeterFormat(object):
  """A Yammer Metrics Meter datum"""

  def getCount(self, data):
    """Get the count"""
    assert data['type'] == "meter"
    return data['count']


  def getValue(self, data):
    """Get the value"""
    assert data['type'] == "meter"
    return data['mean']



class GaugeFormat(object):
  """A Yammer Metrics Gauge datum"""

  def getValue(self, data):
    """Get the value"""
    assert data['type'] == 'gauge'
    return data['value']



class DataFormats(object):
  """Different ways data can be formatted"""

  DEFAULT = DefaultFormat()
  DIRECT = DirectFormat()
  TIMER = TimerFormat()
  TIMER_MEAN = TimerMeanFormat()
  COUNTER = CounterFormat()
  METER = MeterFormat()
  GAUGE = GaugeFormat()



class Aggregator(object):
  """Base class for stat aggregators."""

  def __init__(self, name = None, dataFormat = DataFormats.DEFAULT):
    self.name = name or self.DEFAULT_NAME
    self._dataFormat = dataFormat


  def clone(self):
    """Creates a clone of this aggregator."""
    return type(self)(name = self.name, dataFormat = self._dataFormat)



class Average(Aggregator):
  """Aggregate average values of a stat."""

  DEFAULT_NAME = "average"
  _count = 0
  _total = 0


  def addValue(self, _, value):
    """Adds a value from the given source."""
    if value is not None:
      try:
        self._count += self._dataFormat.getCount(value)
        self._total += self._dataFormat.getValue(value) * self._dataFormat.getCount(value)
      except TypeError:
        self._count += 1
        self._total += value


  def result(self):
    """Formats the result."""
    return {
      "count": self._count,
      "total": self._total,
      "average": float(self._total) / self._count if self._count else 0
    }



class Sum(Aggregator):
  """Aggregate sum of a stat."""

  DEFAULT_NAME = "sum"

  total = 0


  def addValue(self, _, value):
    """Adds a value from the given source."""
    self.total += self._dataFormat.getValue(value)


  def result(self):
    """Formats the result."""
    return self.total


def _humanSortKey(s):
  """Sort strings with numbers in a way that makes sense to humans (e.g., 5 < 20)"""
  if isinstance(s, str):
    return [w.isdigit() and int(w) or w for w in re.split(r'(\d+)', s)]
  else:
    return s




class InverseMap(Aggregator):
  """Aggregate sum of a stat."""

  DEFAULT_NAME = "inverse"


  def __init__(self, *args, **kw):
    Aggregator.__init__(self, *args, **kw)
    self.__result = defaultdict(list)


  def addValue(self, source, data):
    """Adds a value from the given source."""
    self.__result[self._dataFormat.getValue(data)].append(source)


  def result(self):
    """Formats the result."""
    for value in six.itervalues(self.__result):
      value.sort(key = _humanSortKey)
    return self.__result



class Sorted(Aggregator):
  """Aggregate sorted version of a stat."""

  DEFAULT_NAME = "sorted"


  # pylint: disable=W0622
  def __init__(self, cmp=None, key=None, reverse=False, *args, **kw):
    Aggregator.__init__(self, *args, **kw)
    self.__result = []
    self.__cmp = cmp
    self.__key = key
    self.__reverse = reverse


  def addValue(self, source, data):
    """Adds a value from the given source."""
    self.__result.append((source, self._dataFormat.getValue(data)))


  def result(self):
    """Formats the result."""
    self.__result.sort(cmp = self.__cmp, key = self.__key, reverse = self.__reverse)
    return self.__result


  def clone(self):
    """Creates a clone of this aggregator."""
    return type(self)(self.__cmp, self.__key, self.__reverse, name = self.name, dataFormat = self._dataFormat)



class Highlight(Aggregator):
  """Picks a single value across all sources and highlights it."""

  value = None
  source = None


  def __init__(self, name, fn, dataFormat = DataFormats.DEFAULT):
    """Creates a highlight aggregator - this will pick one of the values to highlight.

    Args:
      name: The name of this aggregator.
      fn: Callable that takes (a, b) and returns True if b should be selected as the highlight, where as is the
          previous chosen highlight.
    """
    Aggregator.__init__(self, name)
    self.fn = fn


  def addValue(self, source, value):
    """Adds a value from the given source."""
    if self.source is None or self.fn(self.value, value):
      self.value = value
      self.source = source


  def result(self):
    """Formats the result."""
    return {
      "source": self.source,
      "value": self.value
    }


  def clone(self):
    """Creates a clone of this aggregator."""
    return Highlight(self.name, self.fn)



class Aggregation(object):
  """Aggregates stat dictionaries."""

  def __init__(self, aggregators):
    """Creates a stat aggregation object from a hierarchical dict representation:

      agg = aggregation.Aggregation({
        'http_hits' : {
          '200': [aggregation.Sum(dataFormat=aggregation.DataFormats.DIRECT)],
          '404': [aggregation.Sum(dataFormat=aggregation.DataFormats.DIRECT)]
      }})

    Also supports regular expression in aggregations keys:

      agg = aggregation.Aggregation({
        'http_hits' : {
          ('ok', re.compile("[1-3][0-9][0-9]")): [aggregation.Sum(dataFormat=aggregation.DataFormats.DIRECT)],
          ('err', re.compile("[4-5][0-9][0-9]")):  [aggregation.Sum(dataFormat=aggregation.DataFormats.DIRECT)]
      }})

    """
    self._aggregators = aggregators
    self._result = {}


  def addSource(self, source, data):
    """Adds the given source's stats."""
    self._aggregate(source, self._aggregators, data, self._result)


  def addJsonDirectory(self, directory, test=None):
    """Adds data from json files in the given directory."""

    for filename in os.listdir(directory):
      try:
        fullPath = os.path.join(directory, filename)
        if not test or test(filename, fullPath):
          with open(fullPath) as f:
            jsonData = json.load(f)
            name, _ = os.path.splitext(filename)
            self.addSource(name, jsonData)

      except ValueError:
        continue


  def _clone(self, aggregators):
    """Clones a list of aggregators."""
    return [x.clone() for x in aggregators]


  def _aggregate(self, source, aggregators, data, result):
    """Performs aggregation at a specific node in the data/aggregator tree."""
    if data is None:
      return

    # Checks for both a python 2 or python 3 dictionary
    if hasattr(aggregators, 'iteritems') or hasattr(aggregators, 'items'):
      # Keep walking the tree.
      for key, value in six.iteritems(aggregators):
        if isinstance(key, tuple):
          key, regex = key
          for dataKey, dataValue in six.iteritems(data):
            if regex.match(dataKey):
              result.setdefault(key, {})
              self._aggregate(source, value, dataValue, result[key])
        else:
          if key == '*':
            for dataKey, dataValue in six.iteritems(data):
              result.setdefault(dataKey, {})
              self._aggregate(source, value, dataValue, result[dataKey])
          elif key in data:
            result.setdefault(key, {})
            self._aggregate(source, value, data[key], result[key])

    else:
      # We found a leaf.
      for aggregator in aggregators:
        if aggregator.name not in result:
          result[aggregator.name] = aggregator.clone()
        result[aggregator.name].addValue(source, data)


  def result(self, root = None):
    """Formats the result."""
    root = root or self._result
    if isinstance(root, Aggregator):
      return root.result()
    else:
      result = {}
      for key, value in six.iteritems(root):
        if value:
          result[key] = self.result(value)
      return result



class FileInclusionTest(object):
  """Object to help create good file inclusion tests."""

  def __init__(self, ignoreByName = None, maxAge = None):
    self.ignoreByName = ignoreByName
    self.maxAge = maxAge


  def __call__(self, _, fullPath):
    """Tests if a file should be included in the aggregation."""
    try:
      # Ignore incoming files
      if self.ignoreByName and self.ignoreByName(fullPath):
        return False

      # Ignore old, dead files.
      if self.maxAge:
        stat = os.stat(fullPath)
        age = datetime.datetime.now() - datetime.datetime.fromtimestamp(stat.st_mtime)
        if age > self.maxAge:
          return False

      return True

    except: # pylint: disable=W0702
      return False

########NEW FILE########
__FILENAME__ = aggregation_test
# Copyright 2011 The scales Authors.
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

"""Stat aggregation tests."""

import re

from greplin.scales import aggregation

import unittest



class AggregationTest(unittest.TestCase):
  """Test cases for stat aggregation classes."""

  def testNoData(self):
    "This used to infinite loop."
    agg = aggregation.Aggregation({
      'a': {
        '*': [aggregation.Sum()]
      }
    })
    agg.addSource('source1', {'a': {}})
    agg.result()


  def testRegex(self):
    "Test regexes in aggregation keys"
    agg = aggregation.Aggregation({
        'a' : {
            ('success', re.compile("[1-3][0-9][0-9]")):  [aggregation.Sum(dataFormat = aggregation.DataFormats.DIRECT)],
            ('error', re.compile("[4-5][0-9][0-9]")):  [aggregation.Sum(dataFormat = aggregation.DataFormats.DIRECT)]
        }})
    agg.addSource('source1', {'a': {'200': 10, '302': 10, '404': 1, '500': 3}})
    result = agg.result()
    self.assertEquals(result['a']['success']['sum'], 20)
    self.assertEquals(result['a']['error']['sum'], 4)



if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = bottlehandler

from six import StringIO

from greplin import scales
from greplin.scales import formats, util

from bottle import abort, request, response, run, Bottle
import functools

def bottlestats(server_name, path=''):
    """Renders a GET request, by showing this nodes stats and children."""
    path = path.lstrip('/')
    parts = path.split('/')
    if not parts[0]:
        parts = parts[1:]
    stat_dict = util.lookup(scales.getStats(), parts)

    if stat_dict is None:
        abort(404, "Not Found")
        return

    output = StringIO()
    output_format = request.query.get('format', 'html')
    query = request.query.get('query', None)
    if output_format == 'json':
        response.content_type = "application/json"
        formats.jsonFormat(output, stat_dict, query)
    elif output_format == 'prettyjson':
        formats.jsonFormat(output, stat_dict, query, pretty=True)
        response.content_type = "application/json"
    else:
        formats.htmlHeader(output, '/' + path, server_name, query)
        formats.htmlFormat(output, tuple(parts), stat_dict, query)
        response.content_type = "text/html"

    return output.getvalue()

def register_stats_handler(app, server_name, prefix='/status/'):
    """Register the stats handler with a Flask app, serving routes
    with a given prefix. The prefix defaults to '/_stats/', which is
    generally what you want."""
    if not prefix.endswith('/'):
        prefix += '/'
    handler = functools.partial(bottlestats, server_name)

    app.get(prefix, callback=handler)
    app.get(prefix + '<path:path>', callback=handler)



########NEW FILE########
__FILENAME__ = clock
import time

class BasicClock(object):
  """ Abstraction between things that use sources of time and the rest of the system
      this allows for independent clocks to be integrated with potentially different
      levels of granularity """

  def time(self):
    return time.time()

def getClock():
    """ Returns the best, most accurate clock possible """
    return BasicClock()

########NEW FILE########
__FILENAME__ = flaskhandler
# Copyright 2011 The scales Authors.
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

"""Defines a Flask request handler for status reporting."""


from greplin import scales
from greplin.scales import formats, util

from flask import request, abort

from six import StringIO

import functools


def statsHandler(serverName, path=''):
  """Renders a GET request, by showing this nodes stats and children."""
  path = path.lstrip('/')
  parts = path.split('/')
  if not parts[0]:
    parts = parts[1:]
  statDict = util.lookup(scales.getStats(), parts)

  if statDict is None:
    abort(404, 'No stats found with path /%s' % '/'.join(parts))

  output = StringIO()
  outputFormat = request.args.get('format', 'html')
  query = request.args.get('query', None)
  if outputFormat == 'json':
    formats.jsonFormat(output, statDict, query)
  elif outputFormat == 'prettyjson':
    formats.jsonFormat(output, statDict, query, pretty=True)
  else:
    formats.htmlHeader(output, '/' + path, serverName, query)
    formats.htmlFormat(output, tuple(parts), statDict, query)

  return output.getvalue()


def registerStatsHandler(app, serverName, prefix='/status/'):
  """Register the stats handler with a Flask app, serving routes
  with a given prefix. The prefix defaults to '/status/', which is
  generally what you want."""
  if prefix[-1] != '/':
    prefix += '/'
  handler = functools.partial(statsHandler, serverName)
  app.add_url_rule(prefix, 'statsHandler', handler, methods=['GET'])
  app.add_url_rule(prefix + '<path:path>', 'statsHandler', handler, methods=['GET'])


def serveInBackground(port, serverName, prefix='/status/'):
  """Convenience function: spawn a background server thread that will
  serve HTTP requests to get the status. Returns the thread."""
  import flask, threading
  from wsgiref.simple_server import make_server
  app = flask.Flask(__name__)
  registerStatsHandler(app, serverName, prefix)
  server = threading.Thread(target=make_server('', port, app).serve_forever)
  server.daemon = True
  server.start()
  return server

########NEW FILE########
__FILENAME__ = formats
# Copyright 2011 The scales Authors.
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

"""Formatting methods for stats."""

from greplin import scales

import cgi
import six
try:
  import simplejson as json
except ImportError:
  import json
import operator
import re

OPERATORS = {
  '>=': operator.ge,
  '>': operator.gt,
  '<': operator.lt,
  '<=': operator.le,
  '=': operator.eq,
  '==': operator.eq,
  '!=': operator.ne
}

OPERATOR = re.compile('(%s)' % '|'.join(list(OPERATORS.keys())))


def runQuery(statDict, query):
  """Filters for the given query."""
  parts = [x.strip() for x in OPERATOR.split(query)]
  assert len(parts) in (1, 3)
  queryKey = parts[0]

  result = {}
  for key, value in six.iteritems(statDict):
    if key == queryKey:
      if len(parts) == 3:
        op = OPERATORS[parts[1]]
        try:
          queryValue = type(value)(parts[2]) if value else parts[2]
        except (TypeError, ValueError):
          continue
        if not op(value, queryValue):
          continue
      result[key] = value
    elif isinstance(value, scales.StatContainer) or isinstance(value, dict):
      child = runQuery(value, query)
      if child:
        result[key] = child
  return result


def htmlHeader(output, path, serverName, query = None):
  """Writes an HTML header."""
  if path and path != '/':
    output.write('<title>%s - Status: %s</title>' % (serverName, path))
  else:
    output.write('<title>%s - Status</title>' % serverName)
  output.write('''
<style>
body,td { font-family: monospace }
.level div {
  padding-bottom: 4px;
}
.level .level {
  margin-left: 2em;
  padding: 1px 0;
}
span { color: #090; vertical-align: top }
.key { color: black; font-weight: bold }
.int, .float { color: #00c }
</style>
  ''')
  output.write('<h1 style="margin: 0">Stats</h1>')
  output.write('<h3 style="margin: 3px 0 18px">%s</h3>' % serverName)
  output.write(
      '<p><form action="#" method="GET">Filter: <input type="text" name="query" size="20" value="%s"></form></p>' %
      (query or ''))


def htmlFormat(output, pathParts = (), statDict = None, query = None):
  """Formats as HTML, writing to the given object."""
  statDict = statDict or scales.getStats()
  if query:
    statDict = runQuery(statDict, query)
  _htmlRenderDict(pathParts, statDict, output)


def _htmlRenderDict(pathParts, statDict, output):
  """Render a dictionary as a table - recursing as necessary."""
  keys = list(statDict.keys())
  keys.sort()

  links = []

  output.write('<div class="level">')
  for key in keys:
    keyStr = cgi.escape(_utf8str(key))
    value = statDict[key]
    if hasattr(value, '__call__'):
      value = value()
    if hasattr(value, 'keys'):
      valuePath = pathParts + (keyStr,)
      if isinstance(value, scales.StatContainer) and value.isCollapsed():
        link = '/status/' + '/'.join(valuePath)
        links.append('<div class="key"><a href="%s">%s</a></div>' % (link, keyStr))
      else:
        output.write('<div class="key">%s</div>' % keyStr)
        _htmlRenderDict(valuePath, value, output)
    else:
      output.write('<div><span class="key">%s</span> <span class="%s">%s</span></div>' %
                   (keyStr, type(value).__name__, cgi.escape(_utf8str(value)).replace('\n', '<br/>')))

  if links:
    for link in links:
      output.write(link)

  output.write('</div>')


def _utf8str(x):
  """Like str(x), but returns UTF8."""
  if six.PY3:
    return str(x)
  if isinstance(x, six.binary_type):
    return x
  elif isinstance(x, six.text_type):
    return x.encode('utf-8')
  else:
    return six.binary_type(x)


def jsonFormat(output, statDict = None, query = None, pretty = False):
  """Formats as JSON, writing to the given object."""
  statDict = statDict or scales.getStats()
  if query:
    statDict = runQuery(statDict, query)
  indent = 2 if pretty else None
  # At first, assume that strings are in UTF-8. If this fails -- if, for example, we have
  # crazy binary data -- then in order to get *something* out, we assume ISO-8859-1,
  # which maps each byte to a unicode code point.
  try:
    serialized = json.dumps(statDict, cls=scales.StatContainerEncoder, indent=indent)
  except UnicodeDecodeError:
    serialized = json.dumps(statDict, cls=scales.StatContainerEncoder, indent=indent, encoding='iso-8859-1')

  output.write(serialized)
  output.write('\n')

########NEW FILE########
__FILENAME__ = formats_test
# Copyright 2011 The scales Authors.
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

"""Tests for stat formatting."""

from greplin import scales
from greplin.scales import formats

import six
import unittest

try:
  import simplejson as json
except ImportError:
  import json



class Root(object):
  """Root level test class."""

  def __init__(self):
    scales.init(self)


  def getChild(self, name, collapsed):
    """Creates a child."""
    return Child(name, collapsed)



class Child(object):
  """Child test class."""

  countStat = scales.IntStat('count')


  def __init__(self, name, collapsed):
    scales.initChild(self, name).setCollapsed(collapsed)



class StatsTest(unittest.TestCase):
  """Test cases for stats classes."""

  def setUp(self):
    """Reset global state."""
    scales.reset()


  def testJsonCollapse(self):
    """Tests for collapsed child stats."""
    r = Root()
    r.getChild('here', False).countStat += 1
    r.getChild('not', True).countStat += 100

    out = six.StringIO()
    formats.jsonFormat(out)

    self.assertEquals('{"here": {"count": 1}}\n', out.getvalue())



class UnicodeFormatTest(unittest.TestCase):
  """Test cases for Unicode stat formatting."""

  UNICODE_VALUE = six.u('\u842c\u77e5\u5802')


  def testHtmlFormat(self):
    """Test generating HTML with Unicode values."""
    out = six.StringIO()
    formats.htmlFormat(out, statDict={'name': self.UNICODE_VALUE})
    result = out.getvalue()
    if six.PY2:
        value = self.UNICODE_VALUE.encode('utf8')
    else:
        value = self.UNICODE_VALUE
    self.assertTrue(value in result)


  def testJsonFormat(self):
    """Test generating JSON with Unicode values."""
    out = six.StringIO()
    stats = {'name': self.UNICODE_VALUE}
    formats.jsonFormat(out, statDict=stats)
    self.assertEquals(stats, json.loads(out.getvalue()))


  def testJsonFormatBinaryGarbage(self):
    """Make sure that JSON formatting of binary junk does not crash."""
    out = six.StringIO()
    stats = {'garbage': '\xc2\xc2 ROAR!! \0\0'}
    formats.jsonFormat(out, statDict=stats)
    self.assertEquals(json.loads(out.getvalue()), {'garbage': six.u('\xc2\xc2 ROAR!! \0\0')})



########NEW FILE########
__FILENAME__ = graphite
# Copyright 2011 The scales Authors.
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

"""Tools for pushing stat values to graphite."""

from greplin import scales
from greplin.scales import util

import os
import threading
import logging
import time
from fnmatch import fnmatch
from socket import gethostname

import six

class GraphitePusher(object):
  """A class that pushes all stat values to Graphite on-demand."""

  def __init__(self, host, port, prefix=None):
    """If prefix is given, it will be prepended to all Graphite
    stats. If it is not given, then a prefix will be derived from the
    hostname."""
    self.rules = []
    self.pruneRules = []

    self.prefix = prefix or gethostname().lower()

    if self.prefix and self.prefix[-1] != '.':
      self.prefix += '.'

    self.graphite = util.GraphiteReporter(host, port)


  def _sanitize(self, name):
    """Sanitize a name for graphite."""
    return name.strip().replace(' ', '-').replace('.', '-').replace('/', '_')


  def _forbidden(self, path, value):
    """Is a stat forbidden? Goes through the rules to find one that
    applies. Chronologically newer rules are higher-precedence than
    older ones. If no rule applies, the stat is forbidden by default."""
    if path[0] == '/':
      path = path[1:]
    for rule in reversed(self.rules):
      if isinstance(rule[1], six.string_types):
        if fnmatch(path, rule[1]):
          return not rule[0]
      elif rule[1](path, value):
        return not rule[0]
    return True # do not log by default


  def _pruned(self, path):
    """Is a stat tree node pruned?  Goes through the list of prune rules
    to find one that applies.  Chronologically newer rules are
    higher-precedence than older ones. If no rule applies, the stat is
    not pruned by default."""
    if path[0] == '/':
      path = path[1:]
    for rule in reversed(self.pruneRules):
      if isinstance(rule, six.string_types):
        if fnmatch(path, rule):
          return True
      elif rule(path):
        return True
    return False # Do not prune by default


  def push(self, statsDict=None, prefix=None, path=None):
    """Push stat values out to Graphite."""
    if statsDict is None:
      statsDict = scales.getStats()
    prefix = prefix or self.prefix
    path = path or '/'

    for name, value in list(statsDict.items()):
      name = str(name)
      subpath = os.path.join(path, name)

      if self._pruned(subpath):
        continue

      if hasattr(value, '__call__'):
        try:
          value = value()
        except:                       # pylint: disable=W0702
          value = None
          logging.exception('Error when calling stat function for graphite push')

      if hasattr(value, 'iteritems'):
        self.push(value, '%s%s.' % (prefix, self._sanitize(name)), subpath)
      elif self._forbidden(subpath, value):
        continue

      if six.PY3:
        type_values = (int, float)
      else:
        type_values = (int, long, float)

      if type(value) in type_values and len(name) < 500:
        self.graphite.log(prefix + self._sanitize(name), value)


  def _addRule(self, isWhitelist, rule):
    """Add an (isWhitelist, rule) pair to the rule list."""
    if isinstance(rule, six.string_types) or hasattr(rule, '__call__'):
      self.rules.append((isWhitelist, rule))
    else:
      raise TypeError('Graphite logging rules must be glob pattern or callable. Invalid: %r' % rule)


  def allow(self, rule):
    """Append a whitelisting rule to the chain. The rule is either a function (called
    with the stat name and its value, returns True if it matches), or a Bash-style
    wildcard pattern, such as 'foo.*.bar'."""
    self._addRule(True, rule)


  def forbid(self, rule):
    """Append a blacklisting rule to the chain. The rule is either a function (called
    with the stat name and its value, returns True if it matches), or a Bash-style
    wildcard pattern, such as 'foo.*.bar'."""
    self._addRule(False, rule)


  def prune(self, rule):
    """Append a rule that stops traversal at a branch node."""
    self.pruneRules.append(rule)



class GraphitePeriodicPusher(threading.Thread, GraphitePusher):
  """A thread that periodically pushes all stat values to Graphite."""

  def __init__(self, host, port, prefix=None, period=60):
    """If prefix is given, it will be prepended to all Graphite
    stats. If it is not given, then a prefix will be derived from the
    hostname."""
    GraphitePusher.__init__(self, host, port, prefix)
    threading.Thread.__init__(self)
    self.daemon = True

    self.period = period


  def run(self):
    """Loop forever, pushing out stats."""
    self.graphite.start()
    while True:
      logging.info('Graphite pusher is sleeping for %d seconds', self.period)
      time.sleep(self.period)
      logging.info('Pushing stats to Graphite')
      try:
        self.push()
        logging.info('Done pushing stats to Graphite')
      except:
        logging.exception('Exception while pushing stats to Graphite')
        raise

########NEW FILE########
__FILENAME__ = loop
# Copyright 2011 The scales Authors.
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

"""Twisted specific stats utilities."""

from greplin import scales

from twisted.internet import reactor


def installStatsLoop(statsFile, statsDelay):
  """Installs an interval loop that dumps stats to a file."""

  def dumpStats():
    """Actual stats dump function."""
    scales.dumpStatsTo(statsFile)
    reactor.callLater(statsDelay, dumpStats)

  def startStats():
    """Starts the stats dump in "statsDelay" seconds."""
    reactor.callLater(statsDelay, dumpStats)

  reactor.callWhenRunning(startStats)

########NEW FILE########
__FILENAME__ = meter
# Copyright 2011 The scales Authors.
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

"""Classes for metering values"""

try:
  from UserDict import UserDict
except ImportError:
  from collections import UserDict
from greplin.scales import Stat
from greplin.scales.timer import RepeatTimer
from greplin.scales.util import EWMA

TICKERS = []
TICKER_THREAD = RepeatTimer(5, lambda: [t() for t in TICKERS])



class MeterStatDict(UserDict):
  """Stores the meters for MeterStat. Expects to be ticked every 5 seconds."""

  def __init__(self):
    UserDict.__init__(self)
    self._m1 = EWMA.oneMinute()
    self._m5 = EWMA.fiveMinute()
    self._m15 = EWMA.fifteenMinute()
    self._meters = (self._m1, self._m5, self._m15)
    TICKERS.append(self.tick)

    self['unit'] = 'per second'
    self['count'] = 0


  def __getitem__(self, item):
    if item in self:
      return UserDict.__getitem__(self, item)
    else:
      return 0.0


  def tick(self):
    """Updates meters"""
    for m in self._meters:
      m.tick()
    self['m1'] = self._m1.rate
    self['m5'] = self._m5.rate
    self['m15'] = self._m15.rate


  def mark(self, value=1):
    """Updates the dictionary."""

    self['count'] += value
    for m in self._meters:
      m.update(value)



class MeterStat(Stat):
  """A stat that stores m1, m5, m15. Updated every 5 seconds via TICKER_THREAD."""

  def __init__(self, name, _=None):
    Stat.__init__(self, name, None)


  def _getDefault(self, _):
    """Returns a default MeterStatDict"""
    return MeterStatDict()


  def __set__(self, instance, value):
    self.__get__(instance, None).mark(value)



class MeterDict(UserDict):
  """Dictionary of meters."""

  def __init__(self, parent, instance):
    UserDict.__init__(self)
    self.parent = parent
    self.instance = instance


  def __getitem__(self, item):
    if item in self:
      return UserDict.__getitem__(self, item)
    else:
      meter = MeterStatDict()
      self[item] = meter
      return meter



class MeterDictStat(Stat):
  """Dictionary stat value class."""

  def _getDefault(self, instance):
    return MeterDict(self, instance)

########NEW FILE########
__FILENAME__ = samplestats
# Copyright 2011 The scales Authors.
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

"""Sample statistics. Based on the Java code in Yammer metrics."""

import random
from math import sqrt, floor, exp

from .clock import getClock

def _bounded_exp(value):
  """ Emulate the Java version of exp """
  try:
    return exp(value)
  except OverflowError:
    return float("inf")

class Sampler(object):
  """Class to do simple sampling over values"""
  def __init__(self):
    self.min = float('inf')
    self.max = float('-inf')

  def __len__(self):
    return 0

  def samples(self):
    return []

  def update(self, value):
    self.min = min(self.min, value)
    self.max = max(self.max, value)

  @property
  def mean(self):
    """Return the sample mean."""
    if len(self) == 0:
      return float('NaN')
    arr = self.samples()
    return sum(arr) / float(len(arr))


  @property
  def stddev(self):
    """Return the sample standard deviation."""
    if len(self) < 2:
      return float('NaN')
    # The stupidest algorithm, but it works fine.
    arr = self.samples()
    mean = sum(arr) / len(arr)
    bigsum = 0.0
    for x in arr:
      bigsum += (x - mean)**2
    return sqrt(bigsum / (len(arr) - 1))


  def percentiles(self, percentiles):
    """Given a list of percentiles (floats between 0 and 1), return a
    list of the values at those percentiles, interpolating if
    necessary."""
    try:
      scores = [0.0]*len(percentiles)

      if self.count > 0:
        values = self.samples()
        values.sort()

        for i in range(len(percentiles)):
          p = percentiles[i]
          pos = p * (len(values) + 1)
          if pos < 1:
            scores[i] = values[0]
          elif pos > len(values):
            scores[i] = values[-1]
          else:
            upper, lower = values[int(pos - 1)], values[int(pos)]
            scores[i] = lower + (pos - floor(pos)) * (upper - lower)

      return scores
    except IndexError:
      return [float('NaN')] * len(percentiles)


class ExponentiallyDecayingReservoir(Sampler):
  """
    An exponentially-decaying random reservoir of. Uses Cormode et al's
    forward-decaying priority reservoir sampling method to produce a statistically representative
    sampling reservoir, exponentially biased towards newer entries.

    `Cormode et al. Forward Decay: A Practical Time Decay Model for Streaming Systems. ICDE '09
      http://dimacs.rutgers.edu/~graham/pubs/papers/fwddecay.pdf`

    This is a straight transliteration of the Yammer metrics version from java to python, whilst
    staring gently at the Cormode paper.
  """

  DEFAULT_SIZE = 1028
  DEFAULT_ALPHA = 0.015
  DEFAULT_RESCALE_THRESHOLD = 3600

  def __init__(self, size=DEFAULT_SIZE, alpha=DEFAULT_ALPHA, rescale_threshold=DEFAULT_RESCALE_THRESHOLD, clock=getClock()):
    """
      Creates a new ExponentiallyDecayingReservoir of 1028 elements, which offers a 99.9%
      confidence level with a 5% margin of error assuming a normal distribution, and an alpha
      factor of 0.015, which heavily biases the reservoir to the past 5 minutes of measurements.

      @param size  the number of samples to keep in the sampling reservoir
      @param alpha the exponential decay factor; the higher this is, the more biased the reservoir
                will be towards newer values
      @param rescale_threshold the time period over which to decay
    """
    super(ExponentiallyDecayingReservoir, self).__init__()

    self.values = {}
    self.alpha = alpha
    self.size = size
    self.clock = clock
    self.rescale_threshold = rescale_threshold
    self.count = 0
    self.startTime = self.clock.time()
    self.nextScaleTime = self.clock.time() + self.rescale_threshold

  def __len__(self):
    return min(self.size, self.count)

  def clear(self):
    """ Clear the samples. """
    self.__init__(size=self.size, alpha=self.alpha, clock=self.clock)

  def update(self, value):
    """
      Adds an old value with a fixed timestamp to the reservoir.
      @param value     the value to be added
    """
    super(ExponentiallyDecayingReservoir, self).update(value)

    timestamp = self.clock.time()

    self.__rescaleIfNeeded()
    priority = self.__weight(timestamp - self.startTime) / random.random()

    self.count += 1
    if (self.count <= self.size):
      self.values[priority] = value
    else:
      first = min(self.values)

      if first < priority and priority not in self.values:
        self.values[priority] = value
        while first not in self.values:
          first = min(self.values)

        del self.values[first]

  def __rescaleIfNeeded(self):
    now = self.clock.time()
    nextTick = self.nextScaleTime
    if now >= nextTick:
      self.__rescale(now, nextTick)

  def __weight(self, t):
    weight = self.alpha * t
    return _bounded_exp(weight)

  def __rescale(self, now, nextValue):
    if self.nextScaleTime == nextValue:
      self.nextScaleTime = now + self.rescale_threshold
      oldStartTime = self.startTime;
      self.startTime = self.clock.time()
      keys = list(self.values.keys())
      keys.sort()
      delKeys = []

      for key in keys:
        value = self.values[key]
        delKeys.append(key)
        newKey = key * _bounded_exp(-self.alpha * (self.startTime - oldStartTime))
        self.values[newKey] = value

      for key in delKeys:
        del self.values[key]

      self.count = len(self.values)

  def samples(self):
    return list(self.values.values())[:len(self)]

class UniformSample(Sampler):
  """A uniform sample of values over time."""

  def __init__(self):
    """Create an empty sample."""
    super(UniformSample, self).__init__()

    self.sample = [0.0] * 1028
    self.count = 0

  def clear(self):
    """Clear the sample."""
    for i in range(len(self.sample)):
      self.sample[i] = 0.0
    self.count = 0

  def __len__(self):
    """Number of samples stored."""
    return min(len(self.sample), self.count)

  def update(self, value):
    """Add a value to the sample."""
    super(UniformSample, self).update(value)

    self.count += 1
    c = self.count
    if c < len(self.sample):
      self.sample[c-1] = value
    else:
      r = random.randint(0, c)
      if r < len(self.sample):
        self.sample[r] = value


  def __iter__(self):
    """Return an iterator of the values in the sample."""
    return iter(self.sample[:len(self)])

  def samples(self):
    return self.sample[:len(self)]

# vim: set et fenc=utf-8 ff=unix sts=2 sw=2 ts=2 :

########NEW FILE########
__FILENAME__ = samplestats_test
# Copyright 2011 The scales Authors.
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

"""Sample statistics tests."""

from greplin.scales.samplestats import UniformSample, ExponentiallyDecayingReservoir
import random
import unittest

class UniformSampleTest(unittest.TestCase):
  """Test cases for uniform sample stats."""

  def testGaussian(self):
    """Test with gaussian random numbers."""
    random.seed(42)

    us = UniformSample()
    for _ in range(300):
      us.update(random.gauss(42.0, 13.0))
    self.assertAlmostEqual(us.mean, 43.143067271195235, places=5)
    self.assertAlmostEqual(us.stddev, 13.008553229943168, places=5)

    us.clear()
    for _ in range(30000):
      us.update(random.gauss(0.0012, 0.00005))
    self.assertAlmostEqual(us.mean, 0.0012015284549517493, places=5)
    self.assertAlmostEqual(us.stddev, 4.9776450250869146e-05, places=5)


class ExponentiallyDecayingReservoirTest(unittest.TestCase):
  """Test cases for exponentially decaying reservoir sample stats."""

  def testGaussian(self):
    """Test with gaussian random numbers."""
    random.seed(42)

    sample = ExponentiallyDecayingReservoir()
    for _ in range(300):
      sample.update(random.gauss(42.0, 13.0))
    self.assertAlmostEqual(sample.mean, 41.974069434931714, places=5)
    self.assertAlmostEqual(sample.stddev, 12.982363860393766, places=5)


  def testWithRescale(self):
    """Excercise rescaling."""
    # Not a good test, but at least we cover a little more of the code.
    random.seed(42)

    sample = ExponentiallyDecayingReservoir(rescale_threshold=-1)
    sample.update(random.gauss(42.0, 13.0))
    self.assertAlmostEqual(sample.mean, 40.12682571548693, places=5)





if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = scales_test
# Copyright 2011 The scales Authors.
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

"""Tests for the stats module."""

from greplin import scales

import unittest



class Root1(object):
  """Root level test class."""

  stateStat = scales.Stat('state')
  errorsStat = scales.IntDictStat('errors')
  activeUrlsStat = scales.IntDictStat('activeUrls', autoDelete=True)


  def __init__(self):
    scales.init(self, 'path/to/A')


  def getChild(self, cls, *args):
    """Creates a child."""
    return cls(*args)



class Root2(object):
  """Root level test class."""

  def __init__(self):
    scales.init(self, 'B')


  def getChild(self, cls):
    """Creates a child."""
    return cls()



class AggregatingRoot(object):
  """Root level test class with aggregation."""

  countStat = scales.SumAggregationStat('count')
  stateStat = scales.HistogramAggregationStat('state')
  errorsStat = scales.IntDictSumAggregationStat('errors')


  def __init__(self):
    scales.init(self, 'Root')


  def getChild(self, cls, *args):
    """Creates a child."""
    return cls(*args)



class AggregatingRootSubclass(AggregatingRoot):
  """Subclass of a class with aggregates."""



class TypedChild(object):
  """Child level test class."""

  countStat = scales.IntStat('count')


  def __init__(self):
    scales.initChildOfType(self, 'C')



class Child(object):
  """Child level test class."""

  countStat = scales.IntStat('count')
  stateStat = scales.Stat('state')
  errorsStat = scales.IntDictStat('errors')


  def __init__(self, name='C'):
    scales.initChild(self, name)



class DynamicRoot(object):
  """Root class with a dynamic stat."""

  value = 100
  dynamicStat = scales.Stat('dynamic')


  def __init__(self):
    scales.init(self)
    self.dynamicStat = lambda: DynamicRoot.value



class StatsTest(unittest.TestCase):
  """Test cases for stats classes."""


  def setUp(self):
    """Reset global state."""
    scales.reset()


  def testChildTypeStats(self):
    """Tests for child stats with typed children (auto-numbered)."""
    a = Root1()
    a.stateStat = 'abc'
    c = a.getChild(TypedChild)
    c.countStat += 1
    b = Root2()
    c = b.getChild(TypedChild)
    c.countStat += 2

    self.assertEquals({
      'path': {
        'to': {
          'A': {
            'state': 'abc',
            'C': {
              '1': {'count': 1}
            }
          }
        }
      },
      'B': {
        'C': {
          '2': {'count': 2}
        },
      }
    }, scales.getStats())


  def testChildStats(self):
    """Tests for child scales."""
    a = Root1()
    a.stateStat = 'abc'
    c = a.getChild(Child)
    c.countStat += 1
    b = Root2()
    c = b.getChild(Child)
    c.countStat += 2

    self.assertEquals({
      'path': {
        'to': {
          'A': {
            'state': 'abc',
            'C': {
              'count': 1
            }
          }
        }
      },
      'B': {
        'C': {
          'count': 2
        },
      }
    }, scales.getStats())


  def testMultilevelChild(self):
    """Tests for multi-level child stats."""
    a = Root1()
    c = a.getChild(Child, 'sub/path')
    c.countStat += 1

    self.assertEquals({
      'path': {
        'to': {
          'A': {
            'sub': {
              'path': {
                'count': 1
              }
            }
          }
        }
      }
    }, scales.getStats())


  def testStatSum(self):
    """Tests for summed stats."""
    self.helpTestStatSum(AggregatingRoot())


  def testStatSumWithSubclassRoot(self):
    """Tests for summed stats."""
    self.helpTestStatSum(AggregatingRootSubclass())


  def helpTestStatSum(self, a):
    """Helps test summed stats."""
    c = a.getChild(Child)

    self.assertEquals({
      'Root': {
        'C': {},
      }
    }, scales.getStats())

    c.countStat += 2

    self.assertEquals({
      'Root': {
        'count': 2,
        'C': {
          'count': 2
        },
      }
    }, scales.getStats())

    d = a.getChild(Child, 'D')
    self.assertEquals({
      'Root': {
        'count': 2,
        'C': {
          'count': 2
        },
        'D': {}
      }
    }, scales.getStats())

    c.countStat -= 1
    d.countStat += 5
    self.assertEquals({
      'Root': {
        'count': 6,
        'C': {
          'count': 1
        },
        'D': {
          'count': 5
        }
      }
    }, scales.getStats())


  def testStatHistogram(self):
    """Tests for stats aggregated in to a histogram."""
    a = AggregatingRoot()
    c = a.getChild(Child)
    d = a.getChild(Child, 'D')

    # Do it twice to make sure its idempotent.
    for _ in range(2):
      c.stateStat = 'good'
      d.stateStat = 'bad'
      self.assertEquals({
        'Root': {
          'state': {
            'good': 1,
            'bad': 1
          },
          'C': {
            'state': 'good'
          },
          'D': {
            'state': 'bad'
          }
        }
      }, scales.getStats())

    c.stateStat = 'great'
    d.stateStat = 'great'
    self.assertEquals({
      'Root': {
        'state': {
          'great': 2,
          'good': 0,
          'bad': 0
        },
        'C': {
          'state': 'great'
        },
        'D': {
          'state': 'great'
        }
      }
    }, scales.getStats())



  def testIntDictStats(self):
    """Tests for int dict stats."""
    a = Root1()
    a.errorsStat['400'] += 1
    a.errorsStat['400'] += 2
    a.errorsStat['404'] += 100
    a.errorsStat['400'] -= 3

    a.activeUrlsStat['http://www.greplin.com'] += 1
    a.activeUrlsStat['http://www.google.com'] += 2
    a.activeUrlsStat['http://www.greplin.com'] -= 1

    self.assertEquals({
      'path': {
        'to': {
          'A': {
            'errors': {
              '400': 0,
              '404': 100
            },
            'activeUrls': {
              'http://www.google.com': 2
            }
          }
        }
      }
    }, scales.getStats())


  def testIntDictStatsAggregation(self):
    """Tests for int dict stats."""
    root = AggregatingRoot()

    errorHolder = root.getChild(Child)

    errorHolder.errorsStat['400'] += 1
    errorHolder.errorsStat['400'] += 2
    errorHolder.errorsStat['404'] += 100
    errorHolder.errorsStat['400'] += 1

    self.assertEquals({
      'Root': {
        'errors': {
          '400': 4,
          '404': 100
        },
        'C': {
          'errors': {
            '400': 4,
            '404': 100
          }
        }
      }
    }, scales.getStats())


  def testDynamic(self):
    """Tests for dynamic stats."""
    DynamicRoot()
    self.assertEquals(100, scales.getStats()['dynamic']())

    DynamicRoot.value = 200
    self.assertEquals(200, scales.getStats()['dynamic']())


  def testCollection(self):
    """Tests for a stat collection."""
    collection = scales.collection('/thePath', scales.IntStat('count'), scales.IntDictStat('histo'))
    collection.count += 100
    collection.histo['cheese'] += 12300
    collection.histo['cheese'] += 45

    self.assertEquals({
      'thePath': {
        'count': 100,
        'histo': {
          'cheese': 12345
        }
      }
    }, scales.getStats())

########NEW FILE########
__FILENAME__ = timer
# Copyright (c) 2009 Geoffrey Foster. Portions by the Scales Authors.
# pylint: disable=W9921, C0103
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.


"""
A Timer implementation that repeats every interval. Vaguely based on

http://g-off.net/software/a-python-repeatable-threadingtimer-class

Modified to remove the Event signal as we never intend to cancel it.
This was done primarily for compatibility with libraries like gevent.
"""

from six.moves._thread import start_new_thread
from time import sleep


def RepeatTimer(interval, function, iterations=0, *args, **kwargs):
  """Repeating timer. Returns a thread id."""

  def __repeat_timer(interval, function, iterations, args, kwargs):
    """Inner function, run in background thread."""
    count = 0
    while iterations <= 0 or count < iterations:
      sleep(interval)
      function(*args, **kwargs)
      count += 1

  return start_new_thread(__repeat_timer, (interval, function, iterations, args, kwargs))

########NEW FILE########
__FILENAME__ = tornadohandler
# Copyright 2011 The scales Authors.
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

"""Defines a Tornado request handler for status reporting."""


from greplin import scales
from greplin.scales import formats, util

import tornado.web



class StatsHandler(tornado.web.RequestHandler):
  """Tornado request handler for a status page."""

  serverName = None


  def initialize(self, serverName): # pylint: disable=W0221
    """Initializes the handler."""
    self.serverName = serverName


  def get(self, path): # pylint: disable=W0221
    """Renders a GET request, by showing this nodes stats and children."""
    path = path or ''
    path = path.lstrip('/')
    parts = path.split('/')
    if not parts[0]:
      parts = parts[1:]
    statDict = util.lookup(scales.getStats(), parts)

    if statDict is None:
      self.set_status(404)
      self.finish('Path not found.')
      return

    outputFormat = self.get_argument('format', default='html')
    query = self.get_argument('query', default=None)
    if outputFormat == 'json':
      formats.jsonFormat(self, statDict, query)
    elif outputFormat == 'prettyjson':
      formats.jsonFormat(self, statDict, query, pretty=True)
    else:
      formats.htmlHeader(self, '/' + path, self.serverName, query)
      formats.htmlFormat(self, tuple(parts), statDict, query)

    return None

########NEW FILE########
__FILENAME__ = twistedweb
# Copyright 2011 The scales Authors.
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

"""Defines Twisted Web resources for status reporting."""


from greplin import scales
from greplin.scales import formats, util

from twisted.web import resource



class StatsResource(resource.Resource):
  """Twisted web resource for a status page."""

  isLeaf = True


  def __init__(self, serverName):
    resource.Resource.__init__(self)
    self.serverName = serverName


  def render_GET(self, request):
    """Renders a GET request, by showing this nodes stats and children."""
    fullPath = request.path.split('/')
    if not fullPath[-1]:
      fullPath = fullPath[:-1]
    parts = fullPath[2:]
    statDict = util.lookup(scales.getStats(), parts)

    if statDict is None:
      request.setResponseCode(404)
      return "Path not found."

    if 'query' in request.args:
      query = request.args['query'][0]
    else:
      query = None

    if 'format' in request.args and request.args['format'][0] == 'json':
      request.headers['content-type'] = 'text/javascript; charset=UTF-8'
      formats.jsonFormat(request, statDict, query)
    elif 'format' in request.args and request.args['format'][0] == 'prettyjson':
      request.headers['content-type'] = 'text/javascript; charset=UTF-8'
      formats.jsonFormat(request, statDict, query, pretty=True)
    else:
      formats.htmlHeader(request, '/' + '/'.join(parts), self.serverName, query)
      formats.htmlFormat(request, tuple(parts), statDict, query)

    return ''

########NEW FILE########
__FILENAME__ = util
# Copyright 2011 The scales Authors.
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

"""Useful utility functions and objects."""

from six.moves.queue import Queue
from math import exp

import logging
import random
import socket
import threading
import time


def lookup(source, keys, fallback = None):
  """Traverses the source, looking up each key.  Returns None if can't find anything instead of raising an exception."""
  try:
    for key in keys:
      source = source[key]
    return source
  except (KeyError, AttributeError, TypeError):
    return fallback



class GraphiteReporter(threading.Thread):
  """A graphite reporter thread."""

  def __init__(self, host, port, maxQueueSize=10000):
    """Connect to a Graphite server on host:port."""
    threading.Thread.__init__(self)

    self.host, self.port = host, port
    self.sock = None
    self.queue = Queue()
    self.maxQueueSize = maxQueueSize
    self.daemon = True


  def run(self):
    """Run the thread."""
    while True:
      try:
        try:
          name, value, valueType, stamp = self.queue.get()
        except TypeError:
          break
        self.log(name, value, valueType, stamp)
      finally:
        self.queue.task_done()


  def connect(self):
    """Connects to the Graphite server if not already connected."""
    if self.sock is not None:
      return
    backoff = 0.01
    while True:
      try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((self.host, self.port))
        self.sock = sock
        return
      except socket.error:
        time.sleep(random.uniform(0, 2.0*backoff))
        backoff = min(backoff*2.0, 5.0)


  def disconnect(self):
    """Disconnect from the Graphite server if connected."""
    if self.sock is not None:
      try:
        self.sock.close()
      except socket.error:
        pass
      finally:
        self.sock = None


  def _sendMsg(self, msg):
    """Send a line to graphite. Retry with exponential backoff."""
    if not self.sock:
      self.connect()
    backoff = 0.001
    while True:
      try:
        self.sock.sendall(msg)
        break
      except socket.error:
        logging.warning('Graphite connection error', exc_info = True)
        self.disconnect()
        time.sleep(random.uniform(0, 2.0*backoff))
        backoff = min(backoff*2.0, 5.0)
        self.connect()


  def _sanitizeName(self, name):
    """Sanitize a metric name."""
    return name.replace(' ', '-')


  def log(self, name, value, valueType=None, stamp=None):
    """Log a named numeric value. The value type may be 'value',
    'count', or None."""
    if type(value) == float:
      form = "%s%s %2.2f %d\n"
    else:
      form = "%s%s %s %d\n"

    if valueType is not None and len(valueType) > 0 and valueType[0] != '.':
      valueType = '.' + valueType

    if not stamp:
      stamp = time.time()

    self._sendMsg(form % (self._sanitizeName(name), valueType or '', value, stamp))


  def enqueue(self, name, value, valueType=None, stamp=None):
    """Enqueue a call to log."""
    # If queue is too large, refuse to log.
    if self.maxQueueSize and self.queue.qsize() > self.maxQueueSize:
      return
    # Stick arguments into the queue
    self.queue.put((name, value, valueType, stamp))


  def flush(self):
    """Block until all stats have been sent to Graphite."""
    self.queue.join()


  def shutdown(self):
    """Shut down the background thread."""
    self.queue.put(None)
    self.flush()



class AtomicValue(object):
  """Stores a value, atomically."""

  def __init__(self, val):
    self.lock = threading.RLock()
    self.value = val


  def update(self, function):
    """Atomically apply function to the value, and return the old and new values."""
    with self.lock:
      oldValue = self.value
      self.value = function(oldValue)
      return oldValue, self.value


  def getAndSet(self, newVal):
    """Sets a new value while returning the old value"""
    return self.update(lambda _: newVal)[0]


  def addAndGet(self, val):
    """Adds val to the value and returns the result"""
    return self.update(lambda x: x + val)[1]



class EWMA(object):
  """
  An exponentially-weighted moving average.

  Ported from Yammer metrics.
  """

  M1_ALPHA = 1 - exp(-5 / 60.0)
  M5_ALPHA = 1 - exp(-5 / 60.0 / 5)
  M15_ALPHA = 1 - exp(-5 / 60.0 / 15)

  TICK_RATE = 5 # Every 5 seconds


  @classmethod
  def oneMinute(cls):
    """Creates an EWMA configured for a 1 min decay with a 5s tick"""
    return EWMA(cls.M1_ALPHA, 5)


  @classmethod
  def fiveMinute(cls):
    """Creates an EWMA configured for a 5 min decay with a 5s tick"""
    return EWMA(cls.M5_ALPHA, 5)


  @classmethod
  def fifteenMinute(cls):
    """Creates an EWMA configured for a 15 min decay with a 5s tick"""
    return EWMA(cls.M15_ALPHA, 5)


  def __init__(self, alpha, interval):
    self.alpha = alpha
    self.interval = interval
    self.rate = 0
    self._uncounted = AtomicValue(0)
    self._initialized = False


  def update(self, val):
    """Adds this value to the count to be averaged"""
    self._uncounted.addAndGet(val)


  def tick(self):
    """Updates rates and decays"""
    count = self._uncounted.getAndSet(0)
    instantRate = float(count) / self.interval

    if self._initialized:
      self.rate += (self.alpha * (instantRate - self.rate))
    else:
      self.rate = instantRate
      self._initialized = True

########NEW FILE########
__FILENAME__ = util_test
# Copyright 2012 The scales Authors.
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

"""Tests for the util module."""

from greplin.scales import util

import unittest



class AtomicValueTest(unittest.TestCase):
  """Tests for atomic values."""

  def testUpdate(self):
    """Test update functions."""
    v = util.AtomicValue('hello, world')
    self.assertEqual(v.update(len), ('hello, world', len('hello, world')))
    self.assertEqual(v.value, len('hello, world'))


  def testGetAndSet(self):
    """Test get-and-set."""
    v = util.AtomicValue(42)
    self.assertEqual(v.getAndSet(666), 42)
    self.assertEqual(v.value, 666)


  def testAddAndGet(self):
    """Test add-and-get."""
    v = util.AtomicValue(42)
    self.assertEqual(v.addAndGet(8), 50)
    self.assertEqual(v.value, 50)

########NEW FILE########
