__FILENAME__ = upload
#!/usr/bin/env python
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""
Cron for sending exception logs to greplin-exception-catcher.

Usage: upload.py http://server.com secretKey exceptionDirectory
"""

import json
import os
import time
import os.path
import sys
import urllib2, httplib
import fcntl
import signal
import traceback

# max field size
MAX_FIELD_SIZE = 1024 * 10

# HTTP request timeout
HTTP_TIMEOUT = 5

# Maximum time we should run for
MAX_RUN_TIME = 40

# Settings dict will be used to pass "server" and "secretKey" around.
SETTINGS = {}

# Documents processed and total. These are global stats.
DOCUMENTS_PROCESSED, DOCUMENTS_TOTAL = 0, '[unknown]'


def trimDict(obj):
  """Trim string elements in a dictionnary to MAX_FIELD_SIZE"""
  for k, v in obj.items():
    if isinstance(v, basestring) and len(v) > MAX_FIELD_SIZE:
      obj[k] = v[:MAX_FIELD_SIZE] + '(...)'
    elif isinstance(v, dict):
      trimDict(v)


def sendException(jsonData, filename):
  """Send an exception to the GEC server
     Returns True if sending succeeded"""

  request = urllib2.Request('%s/report?key=%s' % (SETTINGS["server"], SETTINGS["secretKey"]),
                            json.dumps(jsonData),
                            {'Content-Type': 'application/json'})
  try:
    response = urllib2.urlopen(request, timeout=HTTP_TIMEOUT)

  except urllib2.HTTPError, e:
    print >> sys.stderr, 'Error from server while uploading %s' % filename
    print >> sys.stderr, e.read()
    return False

  except urllib2.URLError, e:    
    if e.reason not in ('timed out', 'The read operation timed out'):
      print >> sys.stderr, 'Error while uploading %s' % filename
      print >> sys.stderr, e
      print >> sys.stderr, 'Reason: %s' % e.reason
    return False

  except httplib.BadStatusLine, e:
    print >> sys.stderr, 'Bad status line from server while uploading %s' % filename
    print >> sys.stderr, e
    print >> sys.stderr, 'Status line: %r' % e.line
    return False

  status = response.getcode()

  if status != 200:
    raise Exception('Unexpected status code: %d' % status)

  global DOCUMENTS_PROCESSED            # pylint: disable=W0603
  DOCUMENTS_PROCESSED += 1
  return True


def processFiles(files):
  """Send each exception file in files to GEC"""
  endTime = time.time() + MAX_RUN_TIME  
  
  for filename in files:
    if time.time() > endTime:
      return
    if not os.path.exists(filename):
      continue
    try:
      if processFile(filename):
        os.unlink(filename)
    except Exception, e: #pylint:disable=W0703
      print >> sys.stderr, e
      os.unlink(filename)


def processFile(filename):
  """Process and upload a file.
  Return True if the file has been processed as completely as it will ever be and can be deleted"""

  with open(filename, 'r+') as f:
    try:
      # make sure we're alone on that file
      fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
      return False

    try:
      result = json.load(f)
      st = os.stat(filename)
      result['timestamp'] = st.st_ctime
      trimDict(result)
      return sendException(result, filename)
    except ValueError, ex:
      print >> sys.stderr, "Could not read %s:" % filename
      print >> sys.stderr, '\n"""'
      f.seek(0)
      print >> sys.stderr, f.read()
      print >> sys.stderr, '"""\n'
      print >> sys.stderr, str(ex)
      return True # so this bogus file gets deleted
    finally:
      fcntl.lockf(f, fcntl.LOCK_UN)


        
def alarmHandler(_, frame):
  """SIGALRM handler"""
  print >> sys.stderr, "Maximum run time reached after processing %s of %s exceptions. Exiting." \
        % (DOCUMENTS_PROCESSED, DOCUMENTS_TOTAL)
  traceback.print_stack(frame, file=sys.stderr)
  sys.exit(0)


def main():
  """Runs the gec sender."""

  if len(sys.argv) not in (3, 4):
    print """USAGE: upload.py SERVER SECRET_KEY PATH [LOCKNAME]

LOCKNAME defaults to 'upload-lock'"""
    sys.exit(1)


  SETTINGS["server"] = sys.argv[1]
  SETTINGS["secretKey"] = sys.argv[2]
  path = sys.argv[3]

  signal.signal(signal.SIGALRM, alarmHandler)
  signal.alarm(int(MAX_RUN_TIME * 1.1))

  files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".gec.json")]

  global DOCUMENTS_TOTAL                # pylint: disable=W0603
  DOCUMENTS_TOTAL = len(files)
  processFiles(files)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = logHandler
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""Classes for logging exceptions to files suitable for sending to gec."""

import json
import os
import os.path
import uuid
import logging
import time
import random



class GecHandler(logging.Handler):
  """Log observer that writes exceptions to json files to be picked up by upload.py."""


  def __init__(self, path, project, environment, serverName, prepareMessage=None):
    self.__path = path
    self.__project = project
    self.__environment = environment
    self.__serverName = serverName
    self.__prepareMessage = prepareMessage
    logging.Handler.__init__(self)


  def emit(self, item):
    """Emit an error from the given event, if it was an error event."""
    if item.exc_info:
      formatted = self.formatException(item)
    else:
      formatted = self.formatLogMessage(item)
    result = {
      'project': self.__project,
      'environment': self.__environment,
      'serverName': self.__serverName,
      'errorLevel': item.levelname,
    }
    result.update(formatted)
    self.write(json.dumps(result))


  def write(self, output):
    """Write an exception to disk, possibly overwriting a previous one"""
    filename = os.path.join(self.__path, str(uuid.uuid4()) + '.gec.json')
    if not os.path.exists(filename):
      with open(filename, 'w') as f:
        f.write(output)


  def formatLogMessage(self, item):
    """Format a log message that got triggered without an exception"""
    try:
      itemMessage = item.getMessage()
    except TypeError:
      itemMessage = 'Error formatting message'

    log = {
      'type': "%s message" % item.levelname,
      'message': itemMessage,
      'backtrace': "%s:%d at %s" % (item.module, item.lineno, item.pathname)
    }
    if self.__prepareMessage:
      return self.__prepareMessage(log)
    return log


  def formatException(self, item):
    """Format an exception"""
    exception = {
      'type': item.exc_info[0].__module__ + '.' + item.exc_info[0].__name__,
      'message': str(item.exc_info[1]),
      'logMessage': getattr(item, 'message', None) or getattr(item, 'msg', None),
      'backtrace': item.exc_text,
      'loggedFrom': "%s:%d at %s" % (item.module, item.lineno, item.pathname)
    }
    if self.__prepareMessage:
      return self.__prepareMessage(exception)
    return exception


  def stop(self):
    """Stop observing log events."""
    logging.getLogger().removeHandler(self)



class GentleGecHandler(GecHandler):
  """A GEC Handler that conserves disk space by overwriting errors
  """

  MAX_BASENAME = 10
  MAX_ERRORS = 10000


  def __init__(self, path, project, environment, serverName, prepareException=None):
    GecHandler.__init__(self, path, project, environment, serverName, prepareException)
    self.baseName = random.randint(0, GentleGecHandler.MAX_BASENAME)
    self.errorId = random.randint(0, GentleGecHandler.MAX_ERRORS)


  def write(self, output):
    self.errorId = (self.errorId + 1) % GentleGecHandler.MAX_ERRORS
    filename = os.path.join(self._GecHandler__path, '%d-%d.gec.json' % (self.baseName, self.errorId))
    with open(filename, 'w') as f:
      f.write(output)



class SpaceAwareGecHandler(GecHandler):
  """A gec log handler that will stop logging when free disk space / inodes become too low
  """

  SPACE_CHECK_COUNTER_MAX = 128
  LIMITED_LOGGING_PC = 0.3
  NO_LOGGING_PC = 0.1


  def __init__(self, path, project, environment, serverName, prepareException=None):
    GecHandler.__init__(self, path, project, environment, serverName, prepareException)
    self.spaceCheckCounter = 0
    self.lastStatus = True


  def logDiskSpaceError(self):
    """Log an error message complaining about low disk space (instead of the original message)
    """
    noSpaceLeft = {'created': time.time(),
                   'process': os.getpid(),
                   'module': 'greplin.gec.logging.logHandler',
                   'levelno': 40,
                   'exc_text': None,
                   'lineno': 113,
                   'msg': 'Not enough free blocks/inodes on this disk',
                   'exc_info': None,
                   'funcName': 'checkSpace',
                   'levelname': 'ERROR'}
    GecHandler.emit(self, logging.makeLogRecord(noSpaceLeft))


  def doCheckSpace(self):
    """Check blocks/inodes and log an error if we're too low on either
    """
    vfsStat = os.statvfs(self._GecHandler__path)
    blocksLeft = float(vfsStat.f_bavail) / vfsStat.f_blocks
    inodesLeft = float(vfsStat.f_favail) / vfsStat.f_files
    if blocksLeft < self.LIMITED_LOGGING_PC or inodesLeft < self.LIMITED_LOGGING_PC:
      self.lastStatus = False
      if blocksLeft > self.NO_LOGGING_PC or inodesLeft > self.NO_LOGGING_PC:
        self.logDiskSpaceError()
    else:
      self.lastStatus = True


  def checkSpace(self):
    """Runs the actual disk space check only on every SPACE_CHECK_COUNTER_MAX calls
    """
    self.spaceCheckCounter -= 1
    if self.spaceCheckCounter < 0:
      self.spaceCheckCounter = GentleGecHandler.SPACE_CHECK_COUNTER_MAX
      self.doCheckSpace()
    return self.lastStatus


  def emit(self, item):
    """Log a message if we have enough disk resources.
    """
    if self.checkSpace():
      GecHandler.emit(self, item)



########NEW FILE########
__FILENAME__ = twistedLog
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""Classes for logging exceptions to files suitable for sending to gec."""

import json
import os.path
import traceback
import uuid
import random

from twisted.python import log, util

try:
  from greplin.defer import context
except ImportError:
  # pylint: disable=C0103
  context = None



class GecLogObserver(object):
  """Log observer that writes exceptions to json files to be picked up by upload.py."""

  BUILT_IN_KEYS = frozenset(['failure', 'message', 'time', 'why', 'isError', 'system'])


  def __init__(self, path, project, environment, serverName):
    self.__path = path
    self.__project = project
    self.__environment = environment
    self.__serverName = serverName


  def __formatFailure(self, failure, logMessage, extras):
    """Generates a dict from the given Failure object."""

    parts = ['Traceback (most recent call last):']
    if not failure.frames:
      parts += traceback.format_stack()
    else:
      for functionName, filename, lineNumber, _, _ in failure.frames:
        parts.append('File "%s", line %s, in %s' % (filename, lineNumber, functionName))
    backtrace = '\n'.join(parts)

    result = {
      'project': self.__project,
      'type': failure.type.__module__ + '.' + failure.type.__name__,
      'message': str(failure.value),
      'environment': self.__environment,
      'serverName': self.__serverName,
      'logMessage': logMessage,
      'backtrace': backtrace,
      'loggedFrom': '\n'.join(traceback.format_stack())
    }

    if extras and 'level' in extras:
      result['errorLevel'] = extras['level']
      del extras['level']

    if context and context.all():
      result['context'] = context.all()
      if extras:
        result['context'] = result['context'].copy()
        result['context'].update(extras)
    elif extras:
      result['context'] = extras

    return result


  def emit(self, eventDict):
    """Emit an error from the given event, if it was an error event."""
    if 'failure' in eventDict:
      extras = {}
      for key, value in eventDict.items():
        if key not in self.BUILT_IN_KEYS:
          extras[key] = value

      output = json.dumps(self.__formatFailure(eventDict['failure'], eventDict.get('why'), extras))
      self.write(output)


  def write(self, output):
    """Write a GEC error report, making sure we do not overwrite an existing one
    """
    while True:
      filename = os.path.join(self.__path, str(uuid.uuid4()) + '.gec.json')
      if not os.path.exists(filename):
        with open(filename, 'w') as f:
          util.untilConcludes(f.write, output)
          util.untilConcludes(f.flush)
        break


  def start(self):
    """Start observing log events."""
    log.addObserver(self.emit)


  def stop(self):
    """Stop observing log events."""
    log.removeObserver(self.emit)



class GentleGecLogObserver(GecLogObserver):
  """A GEC Handler that conserves disk space by overwriting errors."""

  MAX_BASENAME = 10
  MAX_ERRORS = 10000


  def __init__(self, path, project, environment, serverName):
    GecLogObserver.__init__(self, path, project, environment, serverName)
    self.baseName = random.randint(0, GentleGecLogObserver.MAX_BASENAME)
    self.errorId = random.randint(0, GentleGecLogObserver.MAX_ERRORS)


  def write(self, output):
    """Write a gec error report, possibly overwriting a previous one."""
    self.errorId = (self.errorId + 1) % GentleGecLogObserver.MAX_ERRORS
    filename = os.path.join(self._GecHandler__path, '%d-%d.gec.json' % (self.baseName, self.errorId))
    with open(filename, 'w') as f:
      util.untilConcludes(f.write, output)
      util.untilConcludes(f.flush)


########NEW FILE########
__FILENAME__ = aggregate
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""AppEngine server for aggregating exceptions."""

# pylint: disable=E0611
from google.appengine.dist import use_library
use_library('django', '1.2')

from datamodel import    LoggedErrorInstance, AggregatedStats
from datetime import datetime, timedelta

from google.appengine.api.datastore_errors import Timeout

import collections
try:
  from django.utils import simplejson as json
except ImportError:
  import json
import logging


def entry():
  """Creates an empty error entry."""
  return {
    'count': 0,
    'servers': collections.defaultdict(int),
    'environments': collections.defaultdict(int)
  }


def aggregate(aggregation, instance):
  """Aggregates an instance in to the global stats."""
  item = aggregation[str(instance.error.key())]
  item['count'] += 1
  item['servers'][instance.server] += 1
  item['environments'][instance.environment] += 1


def retryingIter(queryGenerator):
  """Iterator with retry logic."""
  lastCursor = None
  for i in range(100):
    query = queryGenerator()
    if lastCursor:
      query.with_cursor(lastCursor)
    try:
      for item in query:
        lastCursor = query.cursor()
        yield item
    except Timeout:
      logging.info('Attempt #%d failed', i)


def main():
  """Runs the aggregation."""
  logging.info('running the cron')
  now = datetime.now()
  oneDayAgo = now - timedelta(days = 1)

  aggregation = collections.defaultdict(entry)

  count = 0
  query = lambda: LoggedErrorInstance.all().filter('date >=', oneDayAgo)
  for instance in retryingIter(query):
    aggregate(aggregation, instance)
    count += 1
    if not count % 500:
      logging.info('Finished %d items', count)
  result = sorted(aggregation.items(), key=lambda item: item[1]['count'], reverse=True)

  logging.info('Finished first day of data')

#  query = lambda: LoggedErrorInstance.all().filter('date <', oneDayAgo).filter('date >=', oneWeekAgo)
#  for instance in retryingIter(query):
#    aggregate(aggregation, instance)
#    count += 1
#    if not count % 500:
#      logging.info('Finished %d items', count)
#  result['week'] = sorted(aggregation.items(), key=lambda item: item[1]['count'], reverse=True)
#
#  logging.info('Finished first week of data')

  stat = AggregatedStats()
  stat.date = now
  stat.json = json.dumps(result)
  stat.put()

  logging.info('Put aggregate')


if __name__ == '__main__':
  main()


########NEW FILE########
__FILENAME__ = backtrace
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""Backtrace normalization."""

import re


REMOVE_JAVA_MESSAGE = re.compile(r'(Caused by: [^:]+:).*$', re.MULTILINE)

REMOVE_PYTHON_MESSAGE = re.compile(r'^([a-zA-Z0-9_]+: ).*$', re.MULTILINE)

REMOVE_OBJECTIVE_C_ADDRESS = re.compile(r'0x[0-9a-f]{8} ')


def normalizeBacktrace(backtrace):
  """Normalizes a backtrace for more accurate aggregation."""
  lines = backtrace.splitlines()
  normalizedLines = []
  for line in lines:
    if not line.lstrip().startswith('at sun.reflect.'):
      line = REMOVE_JAVA_MESSAGE.sub(lambda match: match.group(1), line)
      line = REMOVE_PYTHON_MESSAGE.sub(lambda match: match.group(1), line)
      line = REMOVE_OBJECTIVE_C_ADDRESS.sub(' ', line)
      normalizedLines.append(line)
  return '\n'.join(normalizedLines)

########NEW FILE########
__FILENAME__ = backtrace_test
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""Tests for backtrace normalization."""

import unittest

import backtrace

EXAMPLE = """
java.lang.reflect.InvocationTargetException
	at sun.reflect.GeneratedMethodAccessor24.invoke(Unknown Source)
	at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
	at java.lang.reflect.Method.invoke(Method.java:616)
	at javax.servlet.http.HttpServlet.service(HttpServlet.java:637)
	at javax.servlet.http.HttpServlet.service(HttpServlet.java:717)
	at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:290)
	at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:206)
	at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:235)
	at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:206)
	at org.apache.catalina.core.ApplicationFilterChain.internalDoFilter(ApplicationFilterChain.java:235)
	at org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:206)
	at org.apache.catalina.core.StandardWrapperValve.invoke(StandardWrapperValve.java:233)
	at org.apache.catalina.core.StandardContextValve.invoke(StandardContextValve.java:191)
	at org.apache.catalina.core.StandardHostValve.invoke(StandardHostValve.java:127)
	at org.apache.catalina.valves.ErrorReportValve.invoke(ErrorReportValve.java:102)
	at org.apache.catalina.core.StandardEngineValve.invoke(StandardEngineValve.java:109)
	at org.apache.catalina.connector.CoyoteAdapter.service(CoyoteAdapter.java:298)
	at org.apache.coyote.http11.Http11AprProcessor.process(Http11AprProcessor.java:865)
	at org.apache.coyote.http11.Http11AprProtocol$Http11ConnectionHandler.process(Http11AprProtocol.java:579)
	at org.apache.tomcat.util.net.AprEndpoint$Worker.run(AprEndpoint.java:1555)
	at java.lang.Thread.run(Thread.java:636)
Caused by: com.whatever.InterestingException: Can't do something for user #12345
  at com.whatever.SomeClass.method1(SomeClass.java:123)
	at com.whatever.SomeClass.method2(SomeClass.java:1123)
	at com.whatever.SomeClass.method3(SomeClass.java:2123)
	at com.whatever.SomeClass.method4(SomeClass.java:3123)
	... 26 more
Caused by: java.io.IOException: Map failed
	at sun.nio.ch.FileChannelImpl.map(FileChannelImpl.java:803)
	... 30 more
Caused by: java.lang.OutOfMemoryError: Map failed
	at sun.nio.ch.FileChannelImpl.map0(Native Method)
	at sun.nio.ch.FileChannelImpl.map(FileChannelImpl.java:800)
	... 36 more
"""


PYTHON_EXAMPLE = """
Traceback (most recent call last):
  File "/usr/local/lib/python2.6/dist-packages/tornado/web.py", line 789, in wrapper
    return callback(*args, **kwargs)
  File "/var/blah/src/deedah/handler/kabam.py", line 109, in _on_result
    raise exceptions.HttpException(500, "HTTP error: %s" % response.error)
HttpException: (500, 'HTTP error: HTTP 599: Operation timed out after 20314 milliseconds with 0 bytes received')
"""


OBJECTIVE_C_EXAMPLE = """
0   Greplin                             0x0008f1d7 Greplin + 582103
1   Greplin                             0x0008f449 Greplin + 582729
2   Greplin                             0x0008f315 Greplin + 582421
3   Greplin                             0x0008f2ed Greplin + 582381
4   Greplin                             0x000ba757 Greplin + 759639
5   CoreFoundation                      0x36accf03 -[NSObject(NSObject) performSelector:withObject:] + 22
6   Foundation                          0x34f987a9 __NSThreadPerformPerform + 268
7   CoreFoundation                      0x36b36a79 __CFRUNLOOP_IS_CALLING_OUT_TO_A_SOURCE0_PERFORM_FUNCTION__ + 12
8   CoreFoundation                      0x36b3875f __CFRunLoopDoSources0 + 382
9   CoreFoundation                      0x36b394eb __CFRunLoopRun + 230
10  CoreFoundation                      0x36ac9ec3 CFRunLoopRunSpecific + 230
11  CoreFoundation                      0x36ac9dcb CFRunLoopRunInMode + 58
12  GraphicsServices                    0x3628341f GSEventRunModal + 114
13  GraphicsServices                    0x362834cb GSEventRun + 62
14  UIKit                               0x35973d69 -[UIApplication _run] + 404
15  UIKit                               0x35971807 UIApplicationMain + 670
16  Greplin                             0x000028a3 Greplin + 6307
17  Greplin                             0x00002780 Greplin + 6016
"""


OBJECTIVE_C_EXAMPLE_SAME = """
0   Greplin                             0x0008f1d7 Greplin + 582103
1   Greplin                             0x0008f449 Greplin + 582729
2   Greplin                             0x0008f315 Greplin + 582421
3   Greplin                             0x0008f2ed Greplin + 582381
4   Greplin                             0x000ba757 Greplin + 759639
5   CoreFoundation                      0x349e9f03 -[NSObject(NSObject) performSelector:withObject:] + 22
6   Foundation                          0x3608e7a9 __NSThreadPerformPerform + 268
7   CoreFoundation                      0x34a53a79 __CFRUNLOOP_IS_CALLING_OUT_TO_A_SOURCE0_PERFORM_FUNCTION__ + 12
8   CoreFoundation                      0x34a5575f __CFRunLoopDoSources0 + 382
9   CoreFoundation                      0x34a564eb __CFRunLoopRun + 230
10  CoreFoundation                      0x349e6ec3 CFRunLoopRunSpecific + 230
11  CoreFoundation                      0x349e6dcb CFRunLoopRunInMode + 58
12  GraphicsServices                    0x3360d41f GSEventRunModal + 114
13  GraphicsServices                    0x3360d4cb GSEventRun + 62
14  UIKit                               0x33644d69 -[UIApplication _run] + 404
15  UIKit                               0x33642807 UIApplicationMain + 670
16  Greplin                             0x000028a3 Greplin + 6307
17  Greplin                             0x00002780 Greplin + 6016
"""


OBJECTIVE_C_EXAMPLE_NOT_SAME = """
0   Greplin                             0x0008f1d7 Greplin + 582103
1   Greplin                             0x0008f449 Greplin + 582729
2   Greplin                             0x0008f401 Greplin + 582657
3   Greplin                             0x0000296b Greplin + 6507
4   libsystem_c.dylib                   0x33e3c727 _sigtramp + 34
5   libsystem_kernel.dylib              0x33df575f mach_msg + 50
6   CoreFoundation                      0x361272bf __CFRunLoopServiceMachPort + 94
7   CoreFoundation                      0x36129569 __CFRunLoopRun + 356
8   CoreFoundation                      0x360b9ec3 CFRunLoopRunSpecific + 230
9   CoreFoundation                      0x360b9dcb CFRunLoopRunInMode + 58
10  Foundation                          0x345237fd +[NSURLConnection(NSURLConnectionReallyInternal) _resourceLoadLoop:] + 212
11  Foundation                          0x34516389 -[NSThread main] + 44
12  Foundation                          0x345885cd __NSThread__main__ + 972
13  libsystem_c.dylib                   0x33e31311 _pthread_start + 248
14  libsystem_c.dylib                   0x33e32bbc start_wqthread + 0
"""



class BacktraceTestCase(unittest.TestCase):
  """Tests for backtrace normalization."""

  def testRemoveCauseMessage(self):
    """Test that cause messages are removed."""
    differentMessage = EXAMPLE.replace('12345', '23456')
    self.assertEquals(backtrace.normalizeBacktrace(EXAMPLE), backtrace.normalizeBacktrace(differentMessage))

    differentError = EXAMPLE.replace('SomeClass', 'SomeOtherClass')
    self.assertNotEquals(backtrace.normalizeBacktrace(EXAMPLE), backtrace.normalizeBacktrace(differentError))


  def testSlightlyDifferentInvokes(self):
    """Test that slightly different reflection based invocations lead to the same result."""
    differentMessage = EXAMPLE.replace('24.invoke', '24.invoke0')
    self.assertEquals(backtrace.normalizeBacktrace(EXAMPLE), backtrace.normalizeBacktrace(differentMessage))

    differentError = EXAMPLE.replace('.method4', '.methodNot4AtAll')
    self.assertNotEquals(backtrace.normalizeBacktrace(EXAMPLE), backtrace.normalizeBacktrace(differentError))


  def testPythonCauseMessage(self):
    """Test that cause messages are removed for Python."""
    differentMessage = PYTHON_EXAMPLE.replace('HTTP 599', 'HTTP 404')
    self.assertEquals(backtrace.normalizeBacktrace(PYTHON_EXAMPLE), backtrace.normalizeBacktrace(differentMessage))

    differentMessage = PYTHON_EXAMPLE.replace('HttpException:', 'OtherException:')
    self.assertNotEquals(backtrace.normalizeBacktrace(PYTHON_EXAMPLE), backtrace.normalizeBacktrace(differentMessage))


  def testObjectiveCAddresses(self):
    """Test that addresses are removed for Objective C."""
    self.assertEquals(backtrace.normalizeBacktrace(OBJECTIVE_C_EXAMPLE),
                      backtrace.normalizeBacktrace(OBJECTIVE_C_EXAMPLE_SAME))
    self.assertNotEquals(backtrace.normalizeBacktrace(OBJECTIVE_C_EXAMPLE),
                         backtrace.normalizeBacktrace(OBJECTIVE_C_EXAMPLE_NOT_SAME))
########NEW FILE########
__FILENAME__ = common
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""Common utility functions."""

# pylint: disable=E0611
from google.appengine.api import memcache
# pylint: disable=E0611
from google.appengine.ext import db

from datamodel import Project

import datetime
import os.path


def getProject(name):
  """Gets the project with the given name."""
  serialized = memcache.get(name, namespace = 'projects')
  if serialized:
    return db.model_from_protobuf(serialized)
  else:
    result = Project.get_or_insert(name)
    memcache.set(name, db.model_to_protobuf(result), namespace = 'projects')
    return result


def parseDate(string):
  """Parses an ISO format date string."""
  return datetime.datetime.strptime(string.split('.')[0], '%Y-%m-%d %H:%M:%S')


def getTemplatePath(name):
  """Gets a path to the named template."""
  return os.path.join(os.path.dirname(__file__), 'templates', name)



class AttrDict(dict):
  """A dict that is accessible as attributes."""

  def __getattr__(self, name):
    return self[name]


  def __setattr__(self, name, value):
    self[name] = value

########NEW FILE########
__FILENAME__ = config
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""Configuration utilities."""

try:
  from django.utils import simplejson as json
except ImportError:
  import json


def _loadConfig():
  """Loads application configuration."""
  f = open('config.json')
  try:
    return json.loads(f.read())
  finally:
    f.close()


CONFIG = _loadConfig()


def get(key, default = None):
  """Gets a configuration value."""
  return CONFIG.get(key, default)

########NEW FILE########
__FILENAME__ = datamodel
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""AppEngine data model for collecting exceptions."""

from google.appengine.ext import db

import config



class Queue(db.Model):
  """Model for a task in the queue."""

  payload = db.TextProperty()



class Project(db.Model):
  """Model for a project that contains errors."""



class LoggedError(db.Model):
  """Model for a logged error."""

  project = db.ReferenceProperty(Project)

  backtrace = db.TextProperty()

  type = db.StringProperty()

  hash = db.StringProperty()

  active = db.BooleanProperty()

  count = db.IntegerProperty()

  errorLevel = db.StringProperty(default = 'error')

  firstOccurrence = db.DateTimeProperty()

  lastOccurrence = db.DateTimeProperty()

  lastMessage = db.StringProperty(multiline=True)

  environments = db.StringListProperty()

  servers = db.StringListProperty()


  @classmethod
  def kind(cls):
    """Returns the datastore name for this model class."""
    return 'LoggedErrorV2_%d' % (config.get('datastoreVersion', 2))



class LoggedErrorInstance(db.Model):
  """Model for each occurrence of an error."""

  project = db.ReferenceProperty(Project)

  error = db.ReferenceProperty(LoggedError)

  environment = db.StringProperty()

  type = db.StringProperty()

  errorLevel = db.StringProperty(default = 'error')

  date = db.DateTimeProperty()

  message = db.TextProperty()

  server = db.StringProperty()

  logMessage = db.TextProperty()

  context = db.TextProperty()

  affectedUser = db.IntegerProperty()


  @classmethod
  def kind(cls):
    """Returns the datastore name for this model class."""
    return 'LoggedErrorInstanceV2_%d' % (config.get('datastoreVersion', 2))



class AggregatedStats(db.Model):
  """Stores aggregated stats."""

  date = db.DateTimeProperty()

  json = db.TextProperty()

########NEW FILE########
__FILENAME__ = deleteAll
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""Mapper that deletes everything."""

from mapreduce import operation as op


def process(entity):
  """Process an entity by deleting it."""
  yield op.db.Delete(entity)

########NEW FILE########
__FILENAME__ = emailCron
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""AppEngine server for emailing new exceptions."""

# pylint: disable=E0611
from google.appengine.dist import use_library
use_library('django', '1.2')

# pylint: disable=E0611
from google.appengine.api import mail
# pylint: disable=E0611
from google.appengine.ext.webapp import template

from common import getTemplatePath
import config
from datamodel import LoggedError

import collections
from datetime import datetime, timedelta
import logging



def main():
  """Runs the aggregation."""
  toEmail = config.get('toEmail')
  fromEmail = config.get('fromEmail')

  if toEmail and fromEmail:
    logging.info('running the email cron')

    errorQuery = (LoggedError.all().filter('active =', True)
        .filter('firstOccurrence >', datetime.now() - timedelta(hours = 24))
        .order('-firstOccurrence'))

    errors = errorQuery.fetch(500, 0)
    errors.sort(key = lambda x: x.count, reverse=True)

    projects = collections.defaultdict(list)
    for error in errors:
      projects[error.project.key().name()].append(error)

    context = {'projects': sorted(projects.items()), 'errorCount': len(errors), 'baseUrl': config.get('baseUrl')}

    body = template.render(getTemplatePath('dailymail.html'), context).strip()
    mail.send_mail(
        sender=fromEmail, to=toEmail, subject='Latest GEC reports', body='Only available in HTML', html=body)


if __name__ == '__main__':
  main()


########NEW FILE########
__FILENAME__ = queue
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""Queue system for aggregating exceptions.

DESIGN:

Step 1:

A new error instance is reported.  The instance is added to the Queue data store and the instances queue.
(this step is a remnant of an old strategy for dealing with incoming instances and will be removed in the future)

Step 2:

The "instances" queue handler is called.  It puts the LoggedErrorInstance, adds the instance key to the
"aggregation" queue, and adds a new task to the "aggregationWorker" queue.

Step 3:

The aggregationWorker queue handler is called.  It pulls from the "aggregation" queue, getting as many instances as
possible.  It groups them by the Error they are an Instance of.  New stats are computed, a lock is acquired on the
error, and a get/set is performed.  If the lock can't be acquired, the tasks are abandoned and should be picked up by
the next worker.  In this case, the worker throws an exception so that it is rerun.
"""

# pylint: disable=E0611
from google.appengine.api import memcache, taskqueue
# pylint: disable=E0611
from google.appengine.ext import webapp

import backtrace
import collections
from datetime import datetime
import hashlib
try:
  from django.utils import simplejson as json
except ImportError:
  import json
import logging

from common import AttrDict, getProject, parseDate
from datamodel import LoggedError, LoggedErrorInstance, Queue


AGGREGATION_ID = 'currentAggregationId'


def getEndpoints():
  """Returns endpoints needed for queue processing."""
  return [
    ('/reportWorker', ReportWorker),
    ('/aggregationWorker', AggregationWorker)
  ]


def generateHash(exceptionType, backtraceText):
  """Generates a hash for the given exception type and backtrace."""
  hasher = hashlib.md5()
  if exceptionType:
    hasher.update(exceptionType.encode('utf-8'))
  if backtraceText:
    hasher.update(backtrace.normalizeBacktrace(backtraceText.encode('utf-8')))
  return hasher.hexdigest()


def getAggregatedError(project, errorHash):
  """Gets (and updates) the error matching the given report, or None if no matching error is found."""
  error = None

  project = getProject(project)

  q = LoggedError.all().filter('project =', project).filter('hash =', errorHash).filter('active =', True)

  for possibility in q:
    return possibility

  return error


def aggregate(destination, count, first, last, lastMessage, backtraceText, environments, servers):
  """Aggregates in to the given destination."""
  destination.count += count

  if destination.firstOccurrence:
    destination.firstOccurrence = min(destination.firstOccurrence, first)
  else:
    destination.firstOccurrence = first

  if not destination.lastOccurrence or last > destination.lastOccurrence:
    destination.lastOccurrence = last
    destination.backtrace = backtraceText
    destination.lastMessage = lastMessage

  destination.environments = [str(x) for x in (set(destination.environments) | set(environments))]
  destination.servers = [str(x) for x in (set(destination.servers) | set(servers))]


def aggregateSingleInstance(instance, backtraceText):
  """Aggregates a single instance into an "aggregate" object."""
  return {
    'count': 1,
    'firstOccurrence': str(instance.date),
    'lastOccurrence': str(instance.date),
    'lastMessage': instance.message[:300],
    'backtrace': backtraceText,
    'environments': (instance.environment,),
    'servers': (instance.server,),
  }


def aggregateInstances(instances):
  """Aggregates instances in to a meta instance."""
  result = AttrDict(
    count = 0,
    firstOccurrence = None,
    lastOccurrence = None,
    lastMessage = None,
    backtrace = None,
    environments = set(),
    servers = set()
  )

  for instance in instances:
    aggregate(result,
              int(instance['count']),
              parseDate(instance['firstOccurrence']),
              parseDate(instance['lastOccurrence']),
              instance['lastMessage'],
              instance['backtrace'],
              instance['environments'],
              instance['servers'])

  return result


def queueException(serializedException):
  """Enqueues the given exception."""
  task = Queue(payload = serializedException)
  task.put()
  taskqueue.add(queue_name='instances', url='/reportWorker', params={'key': task.key()})


def queueAggregation(error, instance, backtraceText):
  """Enqueues a task to aggregate the given instance in to the given error."""
  payload = {'error': str(error.key()), 'instance': str(instance.key()), 'backtrace': backtraceText}
  taskqueue.Queue('aggregation').add([
    taskqueue.Task(payload = json.dumps(payload), method='PULL')
  ])
  queueAggregationWorker()


def queueAggregationWorker():
  """Enqueues a task to aggregate available instances."""
  workerId = memcache.incr(AGGREGATION_ID, initial_value=0)
  taskqueue.add(queue_name='aggregationWorker',
                url='/aggregationWorker',
                params={'id': workerId})


def _putInstance(exception):
  """Put an exception in the data store."""
  backtraceText = exception.get('backtrace') or ''
  environment = exception.get('environment', 'Unknown')
  message = exception['message'] or ''
  project = exception['project']
  server = exception['serverName']
  timestamp = datetime.fromtimestamp(exception['timestamp'])
  exceptionType = exception.get('type') or ''
  logMessage = exception.get('logMessage')
  context = exception.get('context')
  errorLevel = exception.get('errorLevel')

  errorHash = generateHash(exceptionType, backtraceText)

  error = getAggregatedError(project, errorHash)

  exceptionType = exceptionType.replace('\n', ' ')
  if len(exceptionType) > 500:
    exceptionType = exceptionType[:500]
  exceptionType = exceptionType.replace('\n', ' ')

  needsAggregation = True
  if not error:
    error = LoggedError(
        project = getProject(project),
        backtrace = backtraceText,
        type = exceptionType,
        hash = errorHash,
        active = True,
        errorLevel = errorLevel,
        count = 1,
        firstOccurrence = timestamp,
        lastOccurrence = timestamp,
        lastMessage = message[:300],
        environments = [str(environment)],
        servers = [server])
    error.put()
    needsAggregation = False

  instance = LoggedErrorInstance(
      project = error.project,
      error = error,
      environment = environment,
      type = exceptionType,
      errorLevel = errorLevel,
      date = timestamp,
      message = message,
      server = server,
      logMessage = logMessage)
  if context:
    instance.context = json.dumps(context)
    if 'userId' in context:
      try:
        instance.affectedUser = int(context['userId'])
      except (TypeError, ValueError):
        pass
  instance.put()

  if needsAggregation:
    queueAggregation(error, instance, backtraceText)



class ReportWorker(webapp.RequestHandler):
  """Worker handler for reporting a new exception."""

  def post(self):
    """Handles a new error report via POST."""
    task = Queue.get(self.request.get('key'))
    if not task:
      return

    exception = json.loads(task.payload)
    _putInstance(exception)
    task.delete()


def getInstanceMap(instanceKeys):
  """Gets a map from key to instance for the given keys."""
  instances = LoggedErrorInstance.get(instanceKeys)
  return dict(zip(instanceKeys, instances))


def _lockError(key):
  """Locks the given error."""
  # Since it's memcache, this technically can fail, but the failure case is just slightly inaccurate data.
  return memcache.add(key, True, time = 600, namespace = 'errorLocks')


def _unlockError(key):
  """Locks the given error."""
  return memcache.delete(key, namespace = 'errorLocks')


def _getTasks(q):
  """Get tasks in smaller chunks to try to work around GAE issues."""
  tasks = []
  while len(tasks) < 250:
    try:
      newTasks = q.lease_tasks(180, 25)
    except Exception: # pylint: disable=W0703
      if not tasks:
        raise
      logging.exception('Failed to lease all desired tasks')
      break
    tasks.extend(newTasks)
    if len(newTasks) < 25:
      break
  return tasks



class AggregationWorker(webapp.RequestHandler):
  """Worker handler for reporting a new exception."""

  def post(self): # pylint: disable=R0914, R0915
    """Handles a new error report via POST."""
    taskId = self.request.get('id', '0')
    currentId = memcache.get(AGGREGATION_ID)
    if taskId == 'None' or not (taskId == currentId or int(taskId) % 50 == 0):
      # Skip this task unless it is the most recently added or if it is one of every fifty tasks.
      logging.debug('Skipping task %s, current is %s', taskId, currentId)
      return

    q = taskqueue.Queue('aggregation')
    tasks = _getTasks(q)
    logging.info('Leased %d tasks', len(tasks))

    byError = collections.defaultdict(list)
    instanceKeys = []
    tasksByError = collections.defaultdict(list)
    for task in tasks:
      data = json.loads(task.payload)
      errorKey = data['error']
      if 'instance' in data and 'backtrace' in data:
        instanceKey = data['instance']
        byError[errorKey].append((instanceKey, data['backtrace']))
        instanceKeys.append(instanceKey)
        tasksByError[errorKey].append(task)
      elif 'aggregation' in data:
        byError[errorKey].append(data['aggregation'])
        tasksByError[errorKey].append(task)
      else:
        # Clean up any old tasks in the queue.
        logging.warn('Deleting an old task')
        q.delete_tasks([task])

    retries = 0
    instanceByKey = getInstanceMap(instanceKeys)
    for errorKey, instances in byError.items():
      instances = [keyOrDict
                      if isinstance(keyOrDict, dict)
                      else aggregateSingleInstance(instanceByKey[keyOrDict[0]], keyOrDict[1])
                   for keyOrDict in instances]
      aggregation = aggregateInstances(instances)

      success = False
      if _lockError(errorKey):
        try:
          error = LoggedError.get(errorKey)
          aggregate(
              error, aggregation.count, aggregation.firstOccurrence,
              aggregation.lastOccurrence, aggregation.lastMessage, aggregation.backtrace,
              aggregation.environments, aggregation.servers)
          error.put()
          logging.info('Successfully aggregated %r items for key %s', aggregation.count, errorKey)
          success = True
        except: # pylint: disable=W0702
          logging.exception('Error writing to data store for key %s.', errorKey)
        finally:
          _unlockError(errorKey)
      else:
        logging.info('Could not lock %s', errorKey)

      if not success:
        # Add a retry task.
        logging.info('Retrying aggregation for %d items for key %s', len(instances), errorKey)
        aggregation.firstOccurrence = str(aggregation.firstOccurrence)
        aggregation.lastOccurrence = str(aggregation.lastOccurrence)
        aggregation.environments = list(aggregation.environments)
        aggregation.servers = list(aggregation.servers)
        taskqueue.Queue('aggregation').add([
          taskqueue.Task(payload = json.dumps({'error': errorKey, 'aggregation': aggregation}), method='PULL')
        ])
        retries += 1

      q.delete_tasks(tasksByError[errorKey])

    if retries:
      logging.warn("Retrying %d tasks", retries)
      for _ in range(retries):
        queueAggregationWorker()

########NEW FILE########
__FILENAME__ = server
# Copyright 2011 The greplin-exception-catcher Authors.
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

"""AppEngine server for collecting exceptions."""

# pylint: disable=E0611
from google.appengine.dist import use_library
use_library('django', '1.2')

# pylint: disable=E0611
from google.appengine.api import users
# pylint: disable=E0611
from google.appengine.ext import db, webapp
# pylint: disable=E0611
from google.appengine.ext.webapp import template
# pylint: disable=E0611
from google.appengine.ext.webapp.util import run_wsgi_app

import config
import queue

from datetime import datetime, timedelta
try:
  from django.utils import simplejson as json
except ImportError:
  import json
import logging
import random
import sys
import time
import traceback

from common import getProject, getTemplatePath
from datamodel import LoggedError, LoggedErrorInstance, AggregatedStats


####### Parse the configuration. #######

NAME = config.get('name')

SECRET_KEY = config.get('secretKey')

REQUIRE_AUTH = config.get('requireAuth', True)



####### Utility methods. #######

INSTANCE_FILTERS = ('environment', 'server', 'affectedUser')

INTEGER_FILTERS = ('affectedUser',)


def getFilters(request):
  """Gets the filters applied to the given request."""
  filters = {}
  for key, value in request.params.items():
    if key in INSTANCE_FILTERS or key in ('project', 'errorLevel', 'maxAgeHours'):
      filters[key] = value
  return filters


def filterInstances(dataSet, key, value):
  """Filters a data set."""
  if key in INTEGER_FILTERS:
    return dataSet.filter(key + ' =', int(value))
  elif key == 'maxAgeHours':
    return dataSet
  else:
    return dataSet.filter(key + ' =', value)


def getErrors(filters, limit, offset):
  """Gets a list of errors, filtered by the given filters."""
  for key in filters:
    if key in INSTANCE_FILTERS:
      return None, getInstances(filters, limit=limit, offset=offset)

  errors = LoggedError.all().filter('active =', True)
  for key, value in filters.items():
    if key == 'maxAgeHours':
      errors = errors.filter('firstOccurrence >', datetime.now() - timedelta(hours = int(value)))
    elif key == 'project':
      errors = errors.filter('project =', getProject(value))
    else:
      errors = errors.filter(key, value)
  if 'maxAgeHours' in filters:
    errors = errors.order('-firstOccurrence')
  else:
    errors = errors.order('-lastOccurrence')

  return errors.fetch(limit, offset), None


def getInstances(filters, parent = None, limit = None, offset = None):
  """Gets a list of instances of the given parent error, filtered by the given filters."""

  query = LoggedErrorInstance.all()
  if parent:
    query = query.filter('error =', parent)

  if filters:
    for key, value in filters.items():
      if key in INSTANCE_FILTERS:
        query = filterInstances(query, key, value)
      elif key == 'project' and not parent:
        query = query.filter('project =', getProject(value))

  return query.order('-date').fetch(limit or 51, offset or 0)


####### Pages #######

class AuthPage(webapp.RequestHandler):
  """Base class for pages that require authentication."""

  def __getUser(self):
    """Gets a user."""
    return users.get_current_user()


  def get(self, *args):
    """Handles a get, ensuring the user is authenticated."""
    user = self.__getUser()
    if user or not REQUIRE_AUTH:
      self.doAuthenticatedGet(user, *args)
    else:
      self.redirect(users.create_login_url(self.request.uri))


  def doAuthenticatedGet(self, _, *__):
    """Performs a get with an authenticated user."""
    self.error(500)


  def post(self, *args):
    """Handles a post, ensuring the user is authenticated."""
    user = self.__getUser()
    if user or not REQUIRE_AUTH:
      self.doAuthenticatedPost(user, *args)
    else:
      self.redirect(users.create_login_url(self.request.uri))


  def doAuthenticatedPost(self, _, *__):
    """Performs a post with an authenticated user."""
    self.error(500)



class ReportPage(webapp.RequestHandler):
  """Page handler for reporting a new exception."""

  def post(self):
    """Handles a new error report via POST."""
    key = self.request.get('key')

    if key != SECRET_KEY:
      self.error(403)
      return

    # Add the task to the instances queue.
    queue.queueException(self.request.body)



class StatPage(webapp.RequestHandler):
  """Page handler for collecting error instance stats."""

  def get(self):
    """Handles a new error report via POST."""
    key = self.request.get('key')

    if key != SECRET_KEY:
      self.error(403)
      return

    counts = []
    project = self.request.get('project')
    if project:
      project = getProject(project)
      if not project:
        self.response.out.write(' '.join(['0' for _ in counts]))
    for minutes in self.request.get('minutes').split():
      query = LoggedErrorInstance.all()
      if project:
        query = query.ancestor(project)
      counts.append(query.filter('date >=', datetime.now() - timedelta(minutes = int(minutes))).count())

    self.response.out.write(' '.join((str(count) for count in counts)))



class AggregateViewPage(webapp.RequestHandler):
  """Page handler for collecting error instance stats."""

  def get(self, viewLength):
    """Handles a new error report via POST."""
    if viewLength != 'day':
      # TODO(robbyw): For viewLength == week or viewLength == month, aggregate the aggregates.
      viewLength = 'day'

    data = AggregatedStats.all().order('-date').get()
    data = json.loads(data.json)[:25]

    for _, row in data:
      logging.info(row)
      row['servers'] = sorted(row['servers'].items(), key = lambda x: x[1], reverse=True)
      row['environments'] = sorted(row['environments'].items(), key = lambda x: x[1], reverse=True)

    keys, values = zip(*data)
    errors = LoggedError.get([db.Key(key) for key in keys])

    context = {
      'title': 'Top 25 exceptions over the last %s' % viewLength,
      'errors': zip(errors, values),
      'total': len(data)
    }
    self.response.out.write(template.render(getTemplatePath('aggregation.html'), context))



class ListPage(AuthPage):
  """Page displaying a list of exceptions."""

  def doAuthenticatedGet(self, user):
    self.response.headers['Content-Type'] = 'text/html'

    filters = getFilters(self.request)

    page = int(self.request.get('page', 0))
    errors, instances = getErrors(filters, limit = 51, offset = page * 50)

    if errors is not None:
      hasMore = len(errors) == 51
      errors = errors[:50]
    else:
      hasMore = len(instances) == 51
      instances = instances[:50]

    context = {
      'title': NAME,
      'extraScripts': ['list'],
      'user': user,
      'filters': filters.items(),
      'errors': errors,
      'instances': instances,
      'hasMore': hasMore,
      'nextPage': page + 1
    }
    self.response.out.write(template.render(getTemplatePath('list.html'), context))



class ViewPage(AuthPage):
  """Page displaying a single exception."""

  def doAuthenticatedGet(self, user, *args):
    key, = args
    self.response.headers['Content-Type'] = 'text/html'
    error = LoggedError.get(key)
    filters = getFilters(self.request)
    context = {
      'title': '%s - %s' % (error.lastMessage, NAME),
      'extraScripts': ['view'],
      'user': user,
      'error': error,
      'filters': filters.items(),
      'instances': getInstances(filters, parent=error)[:100]
    }
    self.response.out.write(template.render(getTemplatePath('view.html'), context))



class ResolvePage(AuthPage):
  """Page that resolves an exception."""

  def doAuthenticatedGet(self, _, *args):
    key, = args
    self.response.headers['Content-Type'] = 'text/plain'
    error = LoggedError.get(key)
    error.active = False
    error.put()

    self.response.out.write('ok')



class ClearDatabasePage(AuthPage):
  """Page for clearing the database."""

  def doAuthenticatedGet(self, _):
    if users.is_current_user_admin():
      for error in LoggedError.all():
        error.delete()
      for instance in LoggedErrorInstance.all():
        instance.delete()
      self.response.out.write('Done')
    else:
      self.redirect(users.create_login_url(self.request.uri))



class ErrorPage(webapp.RequestHandler):
  """Page that generates demonstration errors."""

  def get(self):
    """Handles page get for the error page."""
    for _ in range(10):
      error = random.choice(range(4))
      errorLevel = 'error'
      project = 'frontend'
      try:
        if error == 0:
          project = 'backend'
          x = 10 / 0
        elif error == 1:
          errorLevel = 'warning'
          json.loads('{"abc", [1, 2')
        elif error == 2:
          x = {}
          x = x['y']
        elif error == 3:
          x = {}
          x = x['z']

      except (KeyError, ZeroDivisionError, ValueError):
        excInfo = sys.exc_info()
        stack = traceback.format_exc()
        env = random.choice(['dev', 'prod'])
        exception = {
          'timestamp': time.time(),
          'project': project,
          'serverName':'%s %s %d' % (env, project, random.choice(range(3))),
          'type': excInfo[0].__module__ + '.' + excInfo[0].__name__,
          'environment': env,
          'errorLevel': errorLevel,
          'message': str(excInfo[1]),
          'logMessage': 'Log message goes here',
          'backtrace': stack,
          'context':{'userId':random.choice(range(20))}
        }
        queue.queueException(json.dumps(exception))

    self.response.out.write('Done!')


####### Application. #######

def main():
  """Runs the server."""
  endpoints = [
    ('/', ListPage),

    ('/clear', ClearDatabasePage),

    ('/report', ReportPage),

    ('/view/(.*)', ViewPage),
    ('/resolve/(.*)', ResolvePage),

    ('/stats', StatPage),
    ('/review/(.*)', AggregateViewPage),
  ] + queue.getEndpoints()
  if config.get('demo'):
    endpoints.append(('/error', ErrorPage))
  application = webapp.WSGIApplication(endpoints, debug=True)

  run_wsgi_app(application)


if __name__ == "__main__":
  main()

########NEW FILE########
