__FILENAME__ = inferior
#! /usr/bin/env python
#
# Copyright 2014 Google Inc.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Module handling communication with gdb.

Users of this module probably want to use the Inferior class, as it provides a
clean interface for communicating with gdb and a couple of functions for
performing common tasks (e.g. listing threads, moving around the stack, etc.)
"""
# TODO: split this file in two, with GdbProxy in a separate file.

import collections
import errno
import functools
import json
import logging
import os
import re
import select
import signal
import subprocess
import tempfile
import time


# Setting these overrides the defaults. See _SymbolFilePath.
SYMBOL_FILE = None  # default: <PAYLOAD_DIR>/python2.7.debug
PAYLOAD_DIR = os.path.join(os.path.dirname(__file__), 'payload')
TIMEOUT_DEFAULT = 3
TIMEOUT_FOREVER = None

_GDB_STARTUP_FILES = [
    'importsetup.py',
    'gdb_service.py',
]
_GDB_ARGS = ['gdb', '--nw', '--quiet', '--batch-silent']


def _SymbolFilePath():
  return SYMBOL_FILE or os.path.join(PAYLOAD_DIR, 'python2.7.debug')


class Error(Exception):
  pass


class ProxyError(Error):
  """A proxy for an exception that happened within gdb."""


class TimeoutError(Error):
  pass


class PositionError(Error):
  """Raised when a nonsensical debugger position is requested."""


class GdbProcessError(Error):
  """Thrown when attempting to start gdb when it's already running."""


### RPC protocol for gdb service ###
#
# In order to ensure compatibility with all versions of python JSON was
# chosen as the main data format for the communication protocol between
# the gdb-internal python process and the process using this module.
# RPC requests to GdbService ('the service') are JSON objects containing exactly
# two keys:
# * 'func' : the name of the function to be called in the service. RPCs for
#            function names starting with _ will be rejected by the service.
# * 'args' : An array containing all the parameters for the function. Due to
#            JSON's limitations, only positional arguments work. Most API
#            functions require a 'position' argument which is required to be a
#            3-element array specifying the selected pid, python thread id and
#            depth of the selected frame in the stack (where 0 is the outermost
#            frame).
# The session is terminated upon sending an RPC request for the function
# '__kill__' (upon which args are ignored).
#
# RPC return values are not wrapped in JSON objects, but are bare JSON
# representations of return values.
# Python class instances (old and new-style) will also be serialized to JSON
# objects with keys '__pyringe_type_name__' and '__pyringe_address__', which
# carry the expected meaning. The remaining keys in these objects are simple
# JSON representations of the attributes visible in the instance (this means the
# object includes class-level attributes, but these are overshadowed by any
# instance attributes. (There is currently no recursion in this representation,
# only one level of object references is serialized in this way.)
# Should an exception be raised to the top level within the service, it will
# write a JSON-representation of the traceback string to stderr

# TODO: add message-id to the protocol to make sure that canceled operations
# that never had their output read don't end up supplying output for the wrong
# command


class ProxyObject(object):

  def __init__(self, attrdict):
    self.__dict__ = attrdict

  def __repr__(self):
    return ('<proxy of %s object at remote 0x%x>'
            % (self.__pyringe_type_name__, self.__pyringe_address__))


class GdbProxy(object):
  """The gdb that is being run as a service for the inferior.

  Most of the logic of this service is actually run from within gdb, this being
  a stub which handles RPC for that service. Communication with that service
  is done by pushing around JSON encoded dicts specifying RPC requests and
  their results. Automatic respawning is not handled by this class and must be
  implemented on top of this if it is to be available.
  """

  firstrun = True

  def __init__(self, args=None, arch=None):
    super(GdbProxy, self).__init__()
    gdb_version = GdbProxy.Version()
    if gdb_version < (7, 4, None) and GdbProxy.firstrun:
      # The user may have a custom-built version, so we only warn them
      logging.warning('Your version of gdb may be unsupported (< 7.4), '
                      'proceed with caution.')
      GdbProxy.firstrun = False

    arglist = _GDB_ARGS
    # Due to a design flaw in the C part of the gdb python API, setting the
    # target architecture from within a running script doesn't work, so we have
    # to do this with a command line flag.
    if arch:
        arglist = arglist + ['--eval-command', 'set architecture ' + arch]
    arglist = (arglist +
               ['--command=' + os.path.join(PAYLOAD_DIR, fname)
                for fname in _GDB_STARTUP_FILES])

    # Add version-specific args
    if gdb_version >= (7, 6, 1):
      # We want as little interference from user settings as possible,
      # but --nh was only introduced in 7.6.1
      arglist.append('--nh')

    if args:
      arglist.extend(args)

    # We use a temporary file for pushing IO between pyringe and gdb so we
    # don't have to worry about writes larger than the capacity of one pipe
    # buffer and handling partial writes/reads.
    # Since file position is automatically advanced by file writes (so writing
    # then reading from the same file will yield an 'empty' read), we need to
    # reopen the file to get different file offset. We can't use os.dup for
    # this because of the way os.dup is implemented.
    outfile_w = tempfile.NamedTemporaryFile(mode='w', bufsize=1)
    errfile_w = tempfile.NamedTemporaryFile(mode='w', bufsize=1)
    self._outfile_r = open(outfile_w.name)
    self._errfile_r = open(errfile_w.name)

    logging.debug('Starting new gdb process...')
    self._process = subprocess.Popen(
        bufsize=0,
        args=arglist,
        stdin=subprocess.PIPE,
        stdout=outfile_w.file,
        stderr=errfile_w.file,
        close_fds=True,
        preexec_fn=os.setpgrp,
        )
    outfile_w.close()
    errfile_w.close()

    self._poller = select.poll()
    self._poller.register(self._outfile_r.fileno(),
                          select.POLLIN | select.POLLPRI)
    self._poller.register(self._errfile_r.fileno(),
                          select.POLLIN | select.POLLPRI)

  def __getattr__(self, name):
    """Handles transparent proxying to gdb subprocess.

    This returns a lambda which, when called, sends an RPC request to gdb
    Args:
      name: The method to call within GdbService
    Returns:
      The result of the RPC.
    """
    return lambda *args, **kwargs: self._Execute(name, *args, **kwargs)

  def Kill(self):
    """Send death pill to Gdb and forcefully kill it if that doesn't work."""
    try:
      if self.is_running:
        self.Detach()
      if self._Execute('__kill__') == '__kill_ack__':
        # acknowledged, let's give it some time to die in peace
        time.sleep(0.1)
    except (TimeoutError, ProxyError):
      logging.debug('Termination request not acknowledged, killing gdb.')
    if self.is_running:
      # death pill didn't seem to work. We don't want the inferior to get killed
      # the next time it hits a dangling breakpoint, so we send a SIGINT to gdb,
      # which makes it disable instruction breakpoints for the time being.
      os.kill(self._process.pid, signal.SIGINT)
      # Since SIGINT has higher priority (with signal number 2) than SIGTERM
      # (signal 15), SIGTERM cannot preempt the signal handler for SIGINT.
      self._process.terminate()
      self._process.wait()
    self._errfile_r.close()
    self._outfile_r.close()

  @property
  def is_running(self):
    return self._process.poll() is None

  @staticmethod
  def Version():
    """Gets the version of gdb as a 3-tuple.

    The gdb devs seem to think it's a good idea to make --version
    output multiple lines of welcome text instead of just the actual version,
    so we ignore everything it outputs after the first line.
    Returns:
      The installed version of gdb in the form
      (<major>, <minor or None>, <micro or None>)
      gdb 7.7 would hence show up as version (7,7)
    """
    output = subprocess.check_output(['gdb', '--version']).split('\n')[0]
    # Example output (Arch linux):
    # GNU gdb (GDB) 7.7
    # Example output (Debian sid):
    # GNU gdb (GDB) 7.6.2 (Debian 7.6.2-1)
    # Example output (Debian wheezy):
    # GNU gdb (GDB) 7.4.1-debian
    # Example output (centos 2.6.32):
    # GNU gdb (GDB) Red Hat Enterprise Linux (7.2-56.el6)

    # As we've seen in the examples above, versions may be named very liberally
    # So we assume every part of that string may be the "real" version string
    # and try to parse them all. This too isn't perfect (later strings will
    # overwrite information gathered from previous ones), but it should be
    # flexible enough for everything out there.
    major = None
    minor = None
    micro = None
    for potential_versionstring in output.split():
      version = re.split('[^0-9]', potential_versionstring)
      try:
        major = int(version[0])
      except (IndexError, ValueError):
        pass
      try:
        minor = int(version[1])
      except (IndexError, ValueError):
        pass
      try:
        micro = int(version[2])
      except (IndexError, ValueError):
        pass
    return (major, minor, micro)

  # On JSON handling:
  # The python2 json module ignores the difference between unicode and str
  # objects, emitting only unicode objects (as JSON is defined as
  # only having unicode strings). In most cases, this is the wrong
  # representation for data we were sent from the inferior, so we try to convert
  # the unicode objects to normal python strings to make debugger output more
  # readable and to make "real" unicode objects stand out.
  # Luckily, the json module just throws an exception when trying to serialize
  # binary data (that is, bytearray in py2, byte in py3).
  # The only piece of information deemed relevant that is lost is the type of
  # non-string dict keys, as these are not supported in JSON. {1: 1} in the
  # inferior will thus show up as {"1": 1} in the REPL.
  # Properly transmitting python objects would require either substantially
  # building on top of JSON or switching to another serialization scheme.

  def _TryStr(self, maybe_unicode):
    try:
      return str(maybe_unicode)
    except UnicodeEncodeError:
      return maybe_unicode

  def _JsonDecodeList(self, data):
    rv = []
    for item in data:
      if isinstance(item, unicode):
        item = self._TryStr(item)
      elif isinstance(item, list):
        item = self._JsonDecodeList(item)
      rv.append(item)
    return rv

  def _JsonDecodeDict(self, data):
    """Json object decode hook that automatically converts unicode objects."""
    rv = {}
    for key, value in data.iteritems():
      if isinstance(key, unicode):
        key = self._TryStr(key)
      if isinstance(value, unicode):
        value = self._TryStr(value)
      elif isinstance(value, list):
        value = self._JsonDecodeList(value)
      rv[key] = value
    if '__pyringe_type_name__' in data:
      # We're looking at a proxyobject
      rv = ProxyObject(rv)
    return rv

  # There is a reason for this messy method signature, it's got to do with
  # python 2's handling of function arguments, how this class is expected to
  # behave and the responsibilities of __getattr__. Suffice it to say that if
  # this were python 3, we wouldn't have to do this.
  def _Execute(self, funcname, *args, **kwargs):
    """Send an RPC request to the gdb-internal python.

    Blocks for 3 seconds by default and returns any results.
    Args:
      funcname: the name of the function to call.
      *args: the function's arguments.
      **kwargs: Only the key 'wait_for_completion' is inspected, which decides
        whether to wait forever for completion or just 3 seconds.
    Returns:
      The result of the function call.
    """
    wait_for_completion = kwargs.get('wait_for_completion', False)
    rpc_dict = {'func': funcname, 'args': args}
    self._Send(json.dumps(rpc_dict))
    timeout = TIMEOUT_FOREVER if wait_for_completion else TIMEOUT_DEFAULT

    result_string = self._Recv(timeout)

    try:
      result = json.loads(result_string, object_hook=self._JsonDecodeDict)
      if isinstance(result, unicode):
        result = self._TryStr(result)
      elif isinstance(result, list):
        result = self._JsonDecodeList(result)
    except ValueError:
      raise ValueError('Response JSON invalid: ' + str(result_string))
    except TypeError:
      raise ValueError('Response JSON invalid: ' + str(result_string))

    return result

  def _Send(self, string):
    """Write a string of data to the gdb-internal python interpreter."""
    self._process.stdin.write(string + '\n')

  def _Recv(self, timeout):
    """Receive output from gdb.

    This reads gdb's stdout and stderr streams, returns a single line of gdb's
    stdout or rethrows any exceptions thrown from within gdb as well as it can.

    Args:
      timeout: floating point number of seconds after which to abort.
          A value of None or TIMEOUT_FOREVER means "there is no timeout", i.e.
          this might block forever.
    Raises:
      ProxyError: All exceptions received from the gdb service are generically
          reraised as this.
      TimeoutError: Raised if no answer is received from gdb in after the
          specified time.
    Returns:
      The current contents of gdb's stdout buffer, read until the next newline,
      or `None`, should the read fail or timeout.
    """

    buf = ''
    # The messiness of this stems from the "duck-typiness" of this function.
    # The timeout parameter of poll has different semantics depending on whether
    # it's <=0, >0, or None. Yay.

    wait_for_line = timeout is TIMEOUT_FOREVER
    deadline = time.time() + (timeout if not wait_for_line else 0)

    def TimeLeft():
      return max(1000 * (deadline - time.time()), 0)

    continue_reading = True

    while continue_reading:
      poll_timeout = None if wait_for_line else TimeLeft()

      fd_list = [event[0] for event in self._poller.poll(poll_timeout)
                 if event[1] & (select.POLLIN | select.POLLPRI)]
      if not wait_for_line and TimeLeft() == 0:
        continue_reading = False
      if self._outfile_r.fileno() in fd_list:
        buf += self._outfile_r.readline()
        if buf.endswith('\n'):
          return buf

      # GDB-internal exception passing
      if self._errfile_r.fileno() in fd_list:
        exc = self._errfile_r.readline()
        if exc:
          exc_text = '\n-----------------------------------\n'
          exc_text += 'Error occurred within GdbService:\n'
          try:
            exc_text += json.loads(exc)
          except ValueError:
            # whatever we got back wasn't valid JSON.
            # This usually means we've run into an exception before the special
            # exception handling was turned on. The first line we read up there
            # will have been "Traceback (most recent call last):". Obviously, we
            # want the rest, too, so we wait a bit and read it.
            deadline = time.time() + 0.5
            while self.is_running and TimeLeft() > 0:
              exc += self._errfile_r.read()
            try:
              exc_text += json.loads(exc)
            except ValueError:
              exc_text = exc
          raise ProxyError(exc_text)
    # timeout
    raise TimeoutError()


class Inferior(object):
  """Class modeling the inferior process.

  Defines the interface for communication with the inferior and handles
  debugging context and automatic respawning of the underlying gdb service.
  """

  _gdb = None
  _Position = collections.namedtuple('Position', 'pid tid frame_depth')  # pylint: disable=invalid-name
  # tid is the thread ident as reported by threading.current_thread().ident
  # frame_depth is the 'depth' (as measured from the outermost frame) of the
  # requested frame. A value of -1 will hence mean the most recent frame.

  def __init__(self, pid, auto_symfile_loading=True, architecture='i386:x86-64'):
    super(Inferior, self).__init__()
    self.position = self._Position(pid=pid, tid=None, frame_depth=-1)
    self._symbol_file = None
    self.arch = architecture
    self.auto_symfile_loading = auto_symfile_loading

    # Inferior objects are created before the user ever issues the 'attach'
    # command, but since this is used by `Reinit`, we call upon gdb to do this
    # for us.
    if pid:
      self.StartGdb()

  def needsattached(func):
    """Decorator to prevent commands from being used when not attached."""

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
      if not self.attached:
        raise PositionError('Not attached to any process.')
      return func(self, *args, **kwargs)
    return wrap

  @needsattached
  def Cancel(self):
    self.ShutDownGdb()

  def Reinit(self, pid, auto_symfile_loading=True):
    """Reinitializes the object with a new pid.

    Since all modes might need access to this object at any time, this object
    needs to be long-lived. To make this clear in the API, this shorthand is
    supplied.
    Args:
      pid: the pid of the target process
      auto_symfile_loading: whether the symbol file should automatically be
        loaded by gdb.
    """
    self.ShutDownGdb()
    self.__init__(pid, auto_symfile_loading, architecture=self.arch)

  @property
  def gdb(self):
    # when requested, make sure we have a gdb session to return
    # (in case it crashed at some point)
    if not self._gdb or not self._gdb.is_running:
      self.StartGdb()
    return self._gdb

  def StartGdb(self):
    """Starts gdb and attempts to auto-load symbol file (unless turned off).

    Raises:
      GdbProcessError: if gdb is already running
    """
    if self.attached:
      raise GdbProcessError('Gdb is already running.')
    self._gdb = GdbProxy(arch=self.arch)
    self._gdb.Attach(self.position)

    if self.auto_symfile_loading:
      try:
        self.LoadSymbolFile()
      except (ProxyError, TimeoutError) as err:
        self._gdb = GdbProxy(arch=self.arch)
        self._gdb.Attach(self.position)
        if not self.gdb.IsSymbolFileSane(self.position):
          logging.warning('Failed to automatically load a sane symbol file, '
                          'most functionality will be unavailable until symbol'
                          'file is provided.')
          logging.debug(err.message)

  def ShutDownGdb(self):
    if self._gdb and self._gdb.is_running:
      self._gdb.Kill()
    self._gdb = None

  def LoadSymbolFile(self, path=None):
    # As automatic respawning of gdb may happen between calls to this, we have
    # to remember which symbol file we're supposed to load.
    if path:
      self._symbol_file = path
    s_path = self._symbol_file or _SymbolFilePath()
    logging.debug('Trying to load symbol file: %s' % s_path)
    if self.attached:
      self.gdb.LoadSymbolFile(self.position, s_path)
      if not self.gdb.IsSymbolFileSane(self.position):
        logging.warning('Symbol file failed sanity check, '
                        'proceed at your own risk')

  @needsattached
  def Backtrace(self):
    return self.gdb.BacktraceAt(self.position)

  @needsattached
  def Up(self):
    depth = self.position.frame_depth
    if self.position.frame_depth < 0:
      depth = self.gdb.StackDepth(self.position) + self.position.frame_depth
    if not depth:
      raise PositionError('Already at outermost stack frame')
    self.position = self._Position(pid=self.position.pid,
                                   tid=self.position.tid,
                                   frame_depth=depth-1)

  @needsattached
  def Down(self):
    if (self.position.frame_depth + 1 >= self.gdb.StackDepth(self.position)
        or self.position.frame_depth == -1):
      raise PositionError('Already at innermost stack frame')
    frame_depth = self.position.frame_depth + 1
    self.position = self._Position(pid=self.position.pid,
                                   tid=self.position.tid,
                                   frame_depth=frame_depth)

  @needsattached
  def Lookup(self, var_name):
    return self.gdb.LookupInFrame(self.position, var_name)

  @needsattached
  def InferiorLocals(self):
    return self.gdb.InferiorLocals(self.position)

  @needsattached
  def InferiorGlobals(self):
    return self.gdb.InferiorGlobals(self.position)

  @needsattached
  def InferiorBuiltins(self):
    return self.gdb.InferiorBuiltins(self.position)

  @property
  def is_running(self):
    if not self.position.pid:
      return False
    try:
      # sending a 0 signal to a process does nothing
      os.kill(self.position.pid, 0)
      return True
    except OSError as err:
      # We might (for whatever reason) simply not be permitted to do this.
      if err.errno == errno.EPERM:
        logging.debug('Reveived EPERM when trying to signal inferior.')
        return True
      return False

  @property
  def pid(self):
    return self.position.pid

  @property
  @needsattached
  def threads(self):
    # return array of python thread idents. Unfortunately, we can't easily
    # access the given thread names without taking the GIL.
    return self.gdb.ThreadIds(self.position)

  @property
  @needsattached
  def current_thread(self):
    threads = self.threads
    if not threads:
      self.position = self._Position(pid=self.position.pid, tid=None,
                                     frame_depth=-1)
      return None
    if not self.position.tid or self.position.tid not in threads:
      self.position = self._Position(pid=self.position.pid, tid=self.threads[0],
                                     frame_depth=-1)
    return self.position.tid

  @needsattached
  def SelectThread(self, tid):
    if tid in self.gdb.ThreadIds(self.position):
      self.position = self._Position(self.position.pid, tid, frame_depth=-1)
    else:
      logging.error('Thread ' + str(tid) + ' does not exist')

  @needsattached
  def Continue(self):
    self.gdb.Continue(self.position)

  @needsattached
  def Interrupt(self):
    return self.gdb.Interrupt(self.position)

  @property
  def attached(self):
    if (self.position.pid
        and self.is_running
        and self._gdb
        and self._gdb.is_running):
      return True
    return False

########NEW FILE########
__FILENAME__ = exec_socket
#! /usr/bin/env python
#
# Copyright 2014 Google Inc.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Listens on a socket in /tmp and execs what it reads from it."""

import json
import os
import socket
import threading


def StartExecServer():
  """Opens a socket in /tmp, execs data from it and writes results back."""
  sockdir = '/tmp/pyringe_%s' % os.getpid()
  if not os.path.isdir(sockdir):
    os.mkdir(sockdir)
  socket_path = ('%s/%s.execsock' %
                 (sockdir, threading.current_thread().ident))

  if os.path.exists(socket_path):
    os.remove(socket_path)

  exec_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
  exec_sock.bind(socket_path)
  exec_sock.listen(5)
  shutdown = False
  while not shutdown:
    conn, _ = exec_sock.accept()

    data = conn.recv(1024)
    if data:
      if data == '__kill__':
        shutdown = True
        conn.send('__kill_ack__')
        break
      data = json.loads(data)
      try:
        conn.sendall(json.dumps(eval(data)))
      except SyntaxError:
        # Okay, so it probably wasn't an expression
        try:
          exec data  # pylint: disable=exec-used
        except:  # pylint: disable=bare-except
          # Whatever goes wrong when exec'ing this, we don't want to crash.
          # TODO: think of a way to properly tunnel exceptions, if
          # possible without introducing more magic strings.
          pass
        finally:
          conn.sendall(json.dumps(None))
  exec_sock.shutdown(socket.SHUT_RDWR)
  exec_sock.close()
  os.remove(socket_path)

if __name__ == '__main__':
  StartExecServer()

########NEW FILE########
__FILENAME__ = gdb_service
#! /usr/bin/env python
#
# Copyright 2014 Google Inc.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Logic for interacting with the inferior run from within gdb.

This needs to be run from within gdb so we have access to the gdb module.
As we can't make any assumptions about which python version gdb has been
compiled to use, this shouldn't use any fancy py3k constructs.
Interaction with the REPL part of the debugger is done through a simple RPC
mechanism based on JSON dicts shoved through stdin/stdout.
"""

import collections
import json
import os
import re
import sys
import traceback
import zipfile
# GDB already imports this for us, but this shuts up lint
import gdb
import libpython

Position = collections.namedtuple('Position', 'pid tid frame_depth')


class Error(Exception):
  pass


class PositionUnavailableException(Error):
  pass


class RpcException(Error):
  pass


class GdbCache(object):
  """Cache of gdb objects for common symbols."""

  # Work around the fact that when this gets bound, we don't yet have symbols
  DICT = None
  TYPE = None
  INTERP_HEAD = None
  PENDINGBUSY = None
  PENDINGCALLS_TO_DO = None

  @staticmethod
  def Refresh():
    """looks up symbols within the inferior and caches their names / values.

    If debugging information is only partial, this method does its best to
    find as much information as it can, validation can be done using
    IsSymbolFileSane.
    """
    try:
      GdbCache.DICT = gdb.lookup_type('PyDictObject').pointer()
      GdbCache.TYPE = gdb.lookup_type('PyTypeObject').pointer()
    except gdb.error as err:
      # The symbol file we're using doesn't seem to provide type information.
      pass
    interp_head_name = GdbCache.FuzzySymbolLookup('interp_head')
    if interp_head_name:
      GdbCache.INTERP_HEAD = gdb.parse_and_eval(interp_head_name)
    else:
      # As a last resort, ask the inferior about it.
      GdbCache.INTERP_HEAD = gdb.parse_and_eval('PyInterpreterState_Head()')
    GdbCache.PENDINGBUSY = GdbCache.FuzzySymbolLookup('pendingbusy')
    GdbCache.PENDINGCALLS_TO_DO = GdbCache.FuzzySymbolLookup('pendingcalls_to_do')

  @staticmethod
  def FuzzySymbolLookup(symbol_name):
    try:
      gdb.parse_and_eval(symbol_name)
      return symbol_name
    except gdb.error as err:
      # No symbol in current context. We might be dealing with static symbol
      # disambiguation employed by compilers. For example, on debian's current
      # python build, the 'interp_head' symbol (which we need) has been renamed
      # to 'interp_head.42174'. This mangling is of course compiler-specific.
      # We try to get around it by using gdb's built-in regex support when
      # looking up variables
      # Format:
      # All variables matching regular expression "<symbol_name>":
      #
      # File <source_file>:
      # <Type><real_symbol_name>;
      #
      # Non-debugging symbols:
      # 0x<address>  <real_symbol_name>

      # We're only interested in <real_symbol_name>. The latter part
      # ('Non-debugging symbols') is only relevant if debugging info is partial.
      listing = gdb.execute('info variables %s' % symbol_name, to_string=True)
      # sigh... We want whatever was in front of ;, but barring any *s.
      # If you are a compiler dev who mangles symbols using ';' and '*',
      # you deserve this breakage.
      mangled_name = (re.search(r'\**(\S+);$', listing, re.MULTILINE)
                      or re.search(r'^0x[0-9a-fA-F]+\s+(\S+)$', listing, re.MULTILINE))
      if not mangled_name:
        raise err
      try:
        gdb.parse_and_eval('\'%s\'' % mangled_name.group(1))
        return '\'%s\'' % mangled_name.group(1)
      except gdb.error:
        # We could raise this, but the original exception will likely describe
        # the problem better
        raise err


class PyFrameObjectPtr(libpython.PyFrameObjectPtr):
  """Patched version of PyFrameObjectPtr that handles reading zip files."""

  def current_line_num(self):
    try:
      return super(PyFrameObjectPtr, self).current_line_num()
    except ValueError:
      # Work around libpython.py's mishandling of oner-liners
      return libpython.int_from_int(self.co.field('co_firstlineno'))

  def OpenFile(self, filepath):
    """open()-replacement that automatically handles zip files.

    This assumes there is at most one .zip in the file path.
    Args:
      filepath: the path to the file to open.
    Returns:
      An open file-like object.
    """
    archive = False
    if '.zip/' in filepath:
      archive = True
      archive_type = '.zip'
    if '.par/' in filepath:
      archive = True
      archive_type = '.par'
    if archive:
      path, archived_file = filepath.split(archive_type)
      path += archive_type
      zip_file = zipfile.ZipFile(path)
      return zip_file.open(archived_file.strip('/'))
    return open(filepath)

  def extract_filename(self):
    """Alternative way of getting the executed file which inspects globals."""
    globals_gdbval = self._gdbval['f_globals'].cast(GdbCache.DICT)
    global_dict = libpython.PyDictObjectPtr(globals_gdbval)
    for key, value in global_dict.iteritems():
      if str(key.proxyval(set())) == '__file__':
        return str(value.proxyval(set()))

  def current_line(self):
    if self.is_optimized_out():
      return '(frame information optimized out)'
    filename = self.filename()
    inferior_cwd = '/proc/%d/cwd' % gdb.selected_inferior().pid
    if filename.startswith('/dev/fd/'):
      filename.replace('/dev/fd/',
                       '/proc/%d/fd/' % gdb.selected_inferior().pid,
                       1)
    else:
      filename = os.path.join(inferior_cwd, filename)
    try:
      sourcefile = self.OpenFile(filename)
    except IOError:
      # couldn't find the file, let's try extracting the path from the frame
      filename = self.extract_filename()
      if filename.endswith('.pyc'):
        filename = filename[:-1]
      try:
        sourcefile = self.OpenFile(filename)
      except IOError:
        return '<file not available>'
    for _ in xrange(self.current_line_num()):
      line = sourcefile.readline()
    sourcefile.close()
    return line if line else '<file not available>'


class GdbService(object):
  """JSON-based RPC Service for commanding gdb."""

  def __init__(self, stdin=None, stdout=None, stderr=None):
    self.stdin = stdin or sys.stdin
    self.stdout = stdout or sys.stdout
    self.stderr = stderr or sys.stderr

  @property
  def breakpoints(self):
    # work around API weirdness
    if gdb.breakpoints():
      return gdb.breakpoints()
    return ()

  def _UnserializableObjectFallback(self, obj):
    """Handles sanitizing of unserializable objects for Json.

    For instances of heap types, we take the class dict, augment it with the
    instance's __dict__, tag it and transmit it over to the RPC client to be
    reconstructed there. (Works with both old and new style classes)
    Args:
      obj: The object to Json-serialize
    Returns:
      A Json-serializable version of the parameter
    """
    if isinstance(obj, libpython.PyInstanceObjectPtr):
      # old-style classes use 'classobj'/'instance'
      # get class attribute dictionary
      in_class = obj.pyop_field('in_class')
      result_dict = in_class.pyop_field('cl_dict').proxyval(set())

      # let libpython.py do the work of getting the instance dict
      instanceproxy = obj.proxyval(set())
      result_dict.update(instanceproxy.attrdict)
      result_dict['__pyringe_type_name__'] = instanceproxy.cl_name
      result_dict['__pyringe_address__'] = instanceproxy.address
      return result_dict

    if isinstance(obj, libpython.HeapTypeObjectPtr):
      # interestingly enough, HeapTypeObjectPtr seems to handle all pointers to
      # heap type PyObjects, not only pointers to PyHeapTypeObject. This
      # corresponds to new-style class instances. However, as all instances of
      # new-style classes are simple PyObject pointers to the interpreter,
      # libpython.py tends to give us HeapTypeObjectPtrs for things we can't
      # handle properly.

      try:
        # get class attribute dictionary
        type_ptr = obj.field('ob_type')
        tp_dict = type_ptr.cast(GdbCache.TYPE)['tp_dict'].cast(GdbCache.DICT)
        result_dict = libpython.PyDictObjectPtr(tp_dict).proxyval(set())
      except gdb.error:
        # There was probably a type mismatch triggered by wrong assumptions in
        # libpython.py
        result_dict = {}

      try:
        # get instance attributes
        result_dict.update(obj.get_attr_dict().proxyval(set()))
        result_dict['__pyringe_type_name__'] = obj.safe_tp_name()
        result_dict['__pyringe_address__'] = long(obj._gdbval)  # pylint: disable=protected-access
        return result_dict
      except TypeError:
        # This happens in the case where we're not really looking at a heap type
        # instance. There isn't really anything we can do, so we fall back to
        # the default handling.
        pass
    # Default handler -- this does not result in proxy objects or fancy dicts,
    # but most of the time, we end up emitting strings of the format
    # '<object at remote 0x345a235>'
    try:
      proxy = obj.proxyval(set())
      # json doesn't accept non-strings as keys, so we're helping along
      if isinstance(proxy, dict):
        return {str(key): val for key, val in proxy.iteritems()}
      return proxy
    except AttributeError:
      return str(obj)

  def _Read(self):
    return self.stdin.readline()

  def _Write(self, string):
    self.stdout.write(string + '\n')

  def _WriteObject(self, obj):
    self._Write(json.dumps(obj, default=self._UnserializableObjectFallback))

  def _ReadObject(self):
    try:
      obj = json.loads(self._Read().strip())
      return obj
    except ValueError:
      pass

  def EvalLoop(self):
    while self._AcceptRPC():
      pass

  def _AcceptRPC(self):
    """Reads RPC request from stdin and processes it, writing result to stdout.

    Returns:
      True as long as execution is to be continued, False otherwise.
    Raises:
      RpcException: if no function was specified in the RPC or no such API
          function exists.
    """
    request = self._ReadObject()
    if request['func'] == '__kill__':
      self.ClearBreakpoints()
      self._WriteObject('__kill_ack__')
      return False
    if 'func' not in request or request['func'].startswith('_'):
      raise RpcException('Not a valid public API function.')
    rpc_result = getattr(self, request['func'])(*request['args'])
    self._WriteObject(rpc_result)
    return True

  def _UnpackGdbVal(self, gdb_value):
    """Unpacks gdb.Value objects and returns the best-matched python object."""
    val_type = gdb_value.type.code
    if val_type == gdb.TYPE_CODE_INT or val_type == gdb.TYPE_CODE_ENUM:
      return int(gdb_value)
    if val_type == gdb.TYPE_CODE_VOID:
      return None
    if val_type == gdb.TYPE_CODE_PTR:
      return long(gdb_value)
    if val_type == gdb.TYPE_CODE_ARRAY:
      # This is probably a string
      return str(gdb_value)
    # I'm out of ideas, let's return it as a string
    return str(gdb_value)

  def _IterateChainedList(self, head, next_item):
    while self._UnpackGdbVal(head):
      yield head
      head = head[next_item]

  # ----- gdb command api below -----

  def EnsureGdbPosition(self, pid, tid, frame_depth):
    """Make sure our position matches the request.

    Args:
      pid: The process ID of the target process
      tid: The python thread ident of the target thread
      frame_depth: The 'depth' of the requested frame in the frame stack
    Raises:
      PositionUnavailableException: If the requested process, thread or frame
          can't be found or accessed.
    """
    position = [pid, tid, frame_depth]
    if not pid:
      return
    if not self.IsAttached():
      try:
        self.Attach(position)
      except gdb.error as exc:
        raise PositionUnavailableException(exc.message)
    if gdb.selected_inferior().pid != pid:
      self.Detach()
      try:
        self.Attach(position)
      except gdb.error as exc:
        raise PositionUnavailableException(exc.message)

    if tid:
      tstate_head = GdbCache.INTERP_HEAD['tstate_head']
      for tstate in self._IterateChainedList(tstate_head, 'next'):
        if tid == tstate['thread_id']:
          self.selected_tstate = tstate
          break
      else:
        raise PositionUnavailableException('Thread %s does not exist.' %
                                           str(tid))
      stack_head = self.selected_tstate['frame']
      if frame_depth is not None:
        frames = list(self._IterateChainedList(stack_head, 'f_back'))
        frames.reverse()
        try:
          self.selected_frame = frames[frame_depth]
        except IndexError:
          raise PositionUnavailableException('Stack is not %s frames deep' %
                                             str(frame_depth + 1))

  def IsAttached(self):
    # The gdb python api is somewhat... weird.
    inf = gdb.selected_inferior()
    if inf.is_valid() and inf.pid and inf.threads():
      return True
    return False

  def LoadSymbolFile(self, position, path):
    pos = [position[0], None, None]
    self.ExecuteRaw(pos, 'symbol-file ' + path)
    GdbCache.Refresh()

  def IsSymbolFileSane(self, position):
    """Performs basic sanity check by trying to look up a bunch of symbols."""
    pos = [position[0], None, None]
    self.EnsureGdbPosition(*pos)
    try:
      if GdbCache.DICT and GdbCache.TYPE and GdbCache.INTERP_HEAD:
        # pylint: disable=pointless-statement
        tstate = GdbCache.INTERP_HEAD['tstate_head']
        tstate['thread_id']
        frame = tstate['frame']
        frame_attrs = ['f_back',
                       'f_locals',
                       'f_localsplus',
                       'f_globals',
                       'f_builtins',
                       'f_lineno',
                       'f_lasti']
        for attr_name in frame_attrs:
          # This lookup shouldn't throw an exception
          frame[attr_name]
        code = frame['f_code']
        code_attrs = ['co_name',
                      'co_filename',
                      'co_nlocals',
                      'co_varnames',
                      'co_lnotab',
                      'co_firstlineno']
        for attr_name in code_attrs:
          # Same as above, just checking whether the lookup succeeds.
          code[attr_name]
        # if we've gotten this far, we should be fine, as it means gdb managed
        # to look up values for all of these. They might still be null, the
        # symbol file might still be bogus, but making gdb check for null values
        # and letting it run into access violations is the best we can do. We
        # haven't checked any of the python types (dict, etc.), but this symbol
        # file seems to be useful for some things, so let's give it our seal of
        # approval.
        return True
    except gdb.error:
      return False
    # looks like the initial GdbCache refresh failed. That's no good.
    return False

  def Attach(self, position):
    pos = [position[0], position[1], None]
    # Using ExecuteRaw here would throw us into an infinite recursion, we have
    # to side-step it.
    gdb.execute('attach ' + str(pos[0]), to_string=True)

    try:
      # Shortcut for handling single-threaded python applications if we've got
      # the right symbol file loaded already
      GdbCache.Refresh()
      self.selected_tstate = self._ThreadPtrs(pos)[0]
    except gdb.error:
      pass

  def Detach(self):
    """Detaches from the inferior. If not attached, this is a no-op."""
    # We have to work around the python APIs weirdness :\
    if not self.IsAttached():
      return None
    # Gdb doesn't drain any pending SIGINTs it may have sent to the inferior
    # when it simply detaches. We can do this by letting the inferior continue,
    # and gdb will intercept any SIGINT that's still to-be-delivered; as soon as
    # we do so however, we may lose control of gdb (if we're running in
    # synchronous mode). So we queue an interruption and continue gdb right
    # afterwards, it will waitpid() for its inferior and collect all signals
    # that may have been queued.
    pid = gdb.selected_inferior().pid
    self.Interrupt([pid, None, None])
    self.Continue([pid, None, None])
    result = gdb.execute('detach', to_string=True)
    if not result:
      return None
    return result

  def _ThreadPtrs(self, position):
    self.EnsureGdbPosition(position[0], None, None)
    tstate_head = GdbCache.INTERP_HEAD['tstate_head']
    return [tstate for tstate in self._IterateChainedList(tstate_head, 'next')]

  def ThreadIds(self, position):
    # This corresponds to
    # [thr.ident for thr in threading.enumerate()]
    # except we don't need the GIL for this.
    return [self._UnpackGdbVal(tstate['thread_id'])
            for tstate in self._ThreadPtrs(position)]

  def ClearBreakpoints(self):
    for bkp in self.breakpoints:
      bkp.enabled = False
      bkp.delete()

  def Continue(self, position):
    return self.ExecuteRaw(position, 'continue')

  def Interrupt(self, position):
    return self.ExecuteRaw(position, 'interrupt')

  def Call(self, position, function_call):
    """Perform a function call in the inferior.

    WARNING: Since Gdb's concept of threads can't be directly identified with
    python threads, the function call will be made from what has to be assumed
    is an arbitrary thread. This *will* interrupt the inferior. Continuing it
    after the call is the responsibility of the caller.

    Args:
      position: the context of the inferior to call the function from.
      function_call: A string corresponding to a function call. Format:
        'foo(0,0)'
    Returns:
      Thre return value of the called function.
    """
    self.EnsureGdbPosition(position[0], None, None)
    if not gdb.selected_thread().is_stopped():
      self.Interrupt(position)
    result_value = gdb.parse_and_eval(function_call)
    return self._UnpackGdbVal(result_value)

  def ExecuteRaw(self, position, command):
    """Send a command string to gdb."""
    self.EnsureGdbPosition(position[0], None, None)
    return gdb.execute(command, to_string=True)

  def _GetGdbThreadMapping(self, position):
    """Gets a mapping from python tid to gdb thread num.

    There's no way to get the thread ident from a gdb thread.  We only get the
    "ID of the thread, as assigned by GDB", which is completely useless for
    everything except talking to gdb.  So in order to translate between these
    two, we have to execute 'info threads' and parse its output. Note that this
    may only work on linux, and only when python was compiled to use pthreads.
    It may work elsewhere, but we won't guarantee it.

    Args:
      position: array of pid, tid, framedepth specifying the requested position.
    Returns:
      A dictionary of the form {python_tid: gdb_threadnum}.
    """

    if len(gdb.selected_inferior().threads()) == 1:
      # gdb's output for info threads changes and only displays PID. We cheat.
      return {position[1]: 1}
    # example:
    #   8    Thread 0x7f0a637fe700 (LWP 11894) "test.py" 0x00007f0a69563e63 in
    #   select () from /usr/lib64/libc.so.6
    thread_line_regexp = r'\s*\**\s*([0-9]+)\s+[a-zA-Z]+\s+([x0-9a-fA-F]+)\s.*'
    output = gdb.execute('info threads', to_string=True)
    matches = [re.match(thread_line_regexp, line) for line
               in output.split('\n')[1:]]
    return {int(match.group(2), 16): int(match.group(1))
            for match in matches if match}

  def InjectFile(self, position, filepath):
    file_ptr = self.Call(position, 'fopen(%s, "r")' % json.dumps(filepath))
    invoc = ('PyRun_SimpleFile(%s, %s)' % (str(file_ptr), json.dumps(filepath)))
    self._Inject(position, invoc)
    self.Call(position, 'fclose(%s)' % str(file_ptr))

  def InjectString(self, position, code):
    invoc = 'PyRun_SimpleString(%s)' % json.dumps(code)
    self._Inject(position, invoc)

  def _Inject(self, position, call):
    """Injects evaluation of 'call' in a safe location in the inferior.

    Due to the way these injected function calls work, gdb must not be killed
    until the call has returned. If that happens, the inferior will be sent
    SIGTRAP upon attempting to return from the dummy frame gdb constructs for
    us, and will most probably crash.
    Args:
      position: array of pid, tid, framedepth specifying the requested position.
      call: Any expression gdb can evaluate. Usually a function call.
    Raises:
      RuntimeError: if gdb is not being run in synchronous exec mode.
    """
    self.EnsureGdbPosition(position[0], position[1], None)
    self.ClearBreakpoints()
    self._AddThreadSpecificBreakpoint(position)
    gdb.parse_and_eval('%s = 1' % GdbCache.PENDINGCALLS_TO_DO)
    gdb.parse_and_eval('%s = 1' % GdbCache.PENDINGBUSY)
    try:
      # We're "armed", risk the blocking call to Continue
      self.Continue(position)
      # Breakpoint was hit!
      if not gdb.selected_thread().is_stopped():
        # This should not happen. Depending on how gdb is being used, the
        # semantics of self.Continue change, so I'd rather leave this check in
        # here, in case we ever *do* end up changing to async mode.
        raise RuntimeError('Gdb is not acting as expected, is it being run in '
                           'async mode?')
    finally:
      gdb.parse_and_eval('%s = 0' % GdbCache.PENDINGBUSY)
    self.Call(position, call)

  def _AddThreadSpecificBreakpoint(self, position):
    self.EnsureGdbPosition(position[0], None, None)
    tid_map = self._GetGdbThreadMapping(position)
    gdb_threadnum = tid_map[position[1]]
    # Since not all versions of gdb's python API support support creation of
    # temporary breakpoint via the API, we're back to exec'ing CLI commands
    gdb.execute('tbreak Py_MakePendingCalls thread %s' % gdb_threadnum)

  def _BacktraceFromFramePtr(self, frame_ptr):
    """Assembles and returns what looks exactly like python's backtraces."""
    # expects frame_ptr to be a gdb.Value
    frame_objs = [PyFrameObjectPtr(frame) for frame
                  in self._IterateChainedList(frame_ptr, 'f_back')]

    # We want to output tracebacks in the same format python uses, so we have to
    # reverse the stack
    frame_objs.reverse()
    tb_strings = ['Traceback (most recent call last):']
    for frame in frame_objs:
      line_string = ('  File "%s", line %s, in %s' %
                     (frame.filename(),
                      str(frame.current_line_num()),
                      frame.co_name.proxyval(set())))
      tb_strings.append(line_string)
      line_string = '    %s' % frame.current_line().strip()
      tb_strings.append(line_string)
    return '\n'.join(tb_strings)

  def StackDepth(self, position):
    self.EnsureGdbPosition(position[0], position[1], None)
    stack_head = self.selected_tstate['frame']
    return len(list(self._IterateChainedList(stack_head, 'f_back')))

  def BacktraceAt(self, position):
    self.EnsureGdbPosition(*position)
    return self._BacktraceFromFramePtr(self.selected_frame)

  def LookupInFrame(self, position, var_name):
    self.EnsureGdbPosition(*position)
    frame = PyFrameObjectPtr(self.selected_frame)
    value = frame.get_var_by_name(var_name)[0]
    return value

  def _CreateProxyValFromIterator(self, iterator):
    result_dict = {}
    for key, value in iterator():
      native_key = key.proxyval(set()) if key else key
      result_dict[native_key] = value
    return result_dict

  def InferiorLocals(self, position):
    self.EnsureGdbPosition(*position)
    frame = PyFrameObjectPtr(self.selected_frame)
    return self._CreateProxyValFromIterator(frame.iter_locals)

  def InferiorGlobals(self, position):
    self.EnsureGdbPosition(*position)
    frame = PyFrameObjectPtr(self.selected_frame)
    return self._CreateProxyValFromIterator(frame.iter_globals)

  def InferiorBuiltins(self, position):
    self.EnsureGdbPosition(*position)
    frame = PyFrameObjectPtr(self.selected_frame)
    return self._CreateProxyValFromIterator(frame.iter_builtins)


if __name__ == '__main__':

  UNBUF_STDIN = open('/dev/stdin', 'r', buffering=1)
  UNBUF_STDOUT = open('/dev/stdout', 'w', buffering=1)
  UNBUF_STDERR = open('/dev/stderr', 'w', buffering=1)

  def Excepthook(exc_type, value, trace):
    exc_string = ''.join(traceback.format_tb(trace))
    exc_string += '%s: %s' % (exc_type.__name__, value)
    UNBUF_STDERR.write(json.dumps(exc_string) + '\n')

  sys.excepthook = Excepthook
  serv = GdbService(UNBUF_STDIN, UNBUF_STDOUT, UNBUF_STDERR)
  serv.EvalLoop()

########NEW FILE########
__FILENAME__ = libpython
#!/usr/bin/python
# NOTE: This file is taken unmodified (save for this note) from the Python
# project. It can be found in their source tree under Tools/gdb/libpython.py.
# As this file is needed by the debugger, it has been reproduced here. Also
# note that this version may be specific to python 2.7.3.
'''
From gdb 7 onwards, gdb's build can be configured --with-python, allowing gdb
to be extended with Python code e.g. for library-specific data visualizations,
such as for the C++ STL types.  Documentation on this API can be seen at:
http://sourceware.org/gdb/current/onlinedocs/gdb/Python-API.html


This python module deals with the case when the process being debugged (the
"inferior process" in gdb parlance) is itself python, or more specifically,
linked against libpython.  In this situation, almost every item of data is a
(PyObject*), and having the debugger merely print their addresses is not very
enlightening.

This module embeds knowledge about the implementation details of libpython so
that we can emit useful visualizations e.g. a string, a list, a dict, a frame
giving file/line information and the state of local variables

In particular, given a gdb.Value corresponding to a PyObject* in the inferior
process, we can generate a "proxy value" within the gdb process.  For example,
given a PyObject* in the inferior process that is in fact a PyListObject*
holding three PyObject* that turn out to be PyStringObject* instances, we can
generate a proxy value within the gdb process that is a list of strings:
  ["foo", "bar", "baz"]

Doing so can be expensive for complicated graphs of objects, and could take
some time, so we also have a "write_repr" method that writes a representation
of the data to a file-like object.  This allows us to stop the traversal by
having the file-like object raise an exception if it gets too much data.

With both "proxyval" and "write_repr" we keep track of the set of all addresses
visited so far in the traversal, to avoid infinite recursion due to cycles in
the graph of object references.

We try to defer gdb.lookup_type() invocations for python types until as late as
possible: for a dynamically linked python binary, when the process starts in
the debugger, the libpython.so hasn't been dynamically loaded yet, so none of
the type names are known to the debugger

The module also extends gdb with some python-specific commands.
'''
from __future__ import with_statement
import gdb
import sys

# Look up the gdb.Type for some standard types:
_type_char_ptr = gdb.lookup_type('char').pointer() # char*
_type_unsigned_char_ptr = gdb.lookup_type('unsigned char').pointer() # unsigned char*
_type_void_ptr = gdb.lookup_type('void').pointer() # void*

SIZEOF_VOID_P = _type_void_ptr.sizeof


Py_TPFLAGS_HEAPTYPE = (1L << 9)

Py_TPFLAGS_INT_SUBCLASS      = (1L << 23)
Py_TPFLAGS_LONG_SUBCLASS     = (1L << 24)
Py_TPFLAGS_LIST_SUBCLASS     = (1L << 25)
Py_TPFLAGS_TUPLE_SUBCLASS    = (1L << 26)
Py_TPFLAGS_STRING_SUBCLASS   = (1L << 27)
Py_TPFLAGS_UNICODE_SUBCLASS  = (1L << 28)
Py_TPFLAGS_DICT_SUBCLASS     = (1L << 29)
Py_TPFLAGS_BASE_EXC_SUBCLASS = (1L << 30)
Py_TPFLAGS_TYPE_SUBCLASS     = (1L << 31)


MAX_OUTPUT_LEN=1024

class NullPyObjectPtr(RuntimeError):
    pass


def safety_limit(val):
    # Given a integer value from the process being debugged, limit it to some
    # safety threshold so that arbitrary breakage within said process doesn't
    # break the gdb process too much (e.g. sizes of iterations, sizes of lists)
    return min(val, 1000)


def safe_range(val):
    # As per range, but don't trust the value too much: cap it to a safety
    # threshold in case the data was corrupted
    return xrange(safety_limit(val))


class StringTruncated(RuntimeError):
    pass

class TruncatedStringIO(object):
    '''Similar to cStringIO, but can truncate the output by raising a
    StringTruncated exception'''
    def __init__(self, maxlen=None):
        self._val = ''
        self.maxlen = maxlen

    def write(self, data):
        if self.maxlen:
            if len(data) + len(self._val) > self.maxlen:
                # Truncation:
                self._val += data[0:self.maxlen - len(self._val)]
                raise StringTruncated()

        self._val += data

    def getvalue(self):
        return self._val

class PyObjectPtr(object):
    """
    Class wrapping a gdb.Value that's a either a (PyObject*) within the
    inferior process, or some subclass pointer e.g. (PyStringObject*)

    There will be a subclass for every refined PyObject type that we care
    about.

    Note that at every stage the underlying pointer could be NULL, point
    to corrupt data, etc; this is the debugger, after all.
    """
    _typename = 'PyObject'

    def __init__(self, gdbval, cast_to=None):
        if cast_to:
            self._gdbval = gdbval.cast(cast_to)
        else:
            self._gdbval = gdbval

    def field(self, name):
        '''
        Get the gdb.Value for the given field within the PyObject, coping with
        some python 2 versus python 3 differences.

        Various libpython types are defined using the "PyObject_HEAD" and
        "PyObject_VAR_HEAD" macros.

        In Python 2, this these are defined so that "ob_type" and (for a var
        object) "ob_size" are fields of the type in question.

        In Python 3, this is defined as an embedded PyVarObject type thus:
           PyVarObject ob_base;
        so that the "ob_size" field is located insize the "ob_base" field, and
        the "ob_type" is most easily accessed by casting back to a (PyObject*).
        '''
        if self.is_null():
            raise NullPyObjectPtr(self)

        if name == 'ob_type':
            pyo_ptr = self._gdbval.cast(PyObjectPtr.get_gdb_type())
            return pyo_ptr.dereference()[name]

        if name == 'ob_size':
            try:
            # Python 2:
                return self._gdbval.dereference()[name]
            except RuntimeError:
                # Python 3:
                return self._gdbval.dereference()['ob_base'][name]

        # General case: look it up inside the object:
        return self._gdbval.dereference()[name]

    def pyop_field(self, name):
        '''
        Get a PyObjectPtr for the given PyObject* field within this PyObject,
        coping with some python 2 versus python 3 differences.
        '''
        return PyObjectPtr.from_pyobject_ptr(self.field(name))

    def write_field_repr(self, name, out, visited):
        '''
        Extract the PyObject* field named "name", and write its representation
        to file-like object "out"
        '''
        field_obj = self.pyop_field(name)
        field_obj.write_repr(out, visited)

    def get_truncated_repr(self, maxlen):
        '''
        Get a repr-like string for the data, but truncate it at "maxlen" bytes
        (ending the object graph traversal as soon as you do)
        '''
        out = TruncatedStringIO(maxlen)
        try:
            self.write_repr(out, set())
        except StringTruncated:
            # Truncation occurred:
            return out.getvalue() + '...(truncated)'

        # No truncation occurred:
        return out.getvalue()

    def type(self):
        return PyTypeObjectPtr(self.field('ob_type'))

    def is_null(self):
        return 0 == long(self._gdbval)

    def is_optimized_out(self):
        '''
        Is the value of the underlying PyObject* visible to the debugger?

        This can vary with the precise version of the compiler used to build
        Python, and the precise version of gdb.

        See e.g. https://bugzilla.redhat.com/show_bug.cgi?id=556975 with
        PyEval_EvalFrameEx's "f"
        '''
        return self._gdbval.is_optimized_out

    def safe_tp_name(self):
        try:
            return self.type().field('tp_name').string()
        except NullPyObjectPtr:
            # NULL tp_name?
            return 'unknown'
        except RuntimeError:
            # Can't even read the object at all?
            return 'unknown'

    def proxyval(self, visited):
        '''
        Scrape a value from the inferior process, and try to represent it
        within the gdb process, whilst (hopefully) avoiding crashes when
        the remote data is corrupt.

        Derived classes will override this.

        For example, a PyIntObject* with ob_ival 42 in the inferior process
        should result in an int(42) in this process.

        visited: a set of all gdb.Value pyobject pointers already visited
        whilst generating this value (to guard against infinite recursion when
        visiting object graphs with loops).  Analogous to Py_ReprEnter and
        Py_ReprLeave
        '''

        class FakeRepr(object):
            """
            Class representing a non-descript PyObject* value in the inferior
            process for when we don't have a custom scraper, intended to have
            a sane repr().
            """

            def __init__(self, tp_name, address):
                self.tp_name = tp_name
                self.address = address

            def __repr__(self):
                # For the NULL pointer, we have no way of knowing a type, so
                # special-case it as per
                # http://bugs.python.org/issue8032#msg100882
                if self.address == 0:
                    return '0x0'
                return '<%s at remote 0x%x>' % (self.tp_name, self.address)

        return FakeRepr(self.safe_tp_name(),
                        long(self._gdbval))

    def write_repr(self, out, visited):
        '''
        Write a string representation of the value scraped from the inferior
        process to "out", a file-like object.
        '''
        # Default implementation: generate a proxy value and write its repr
        # However, this could involve a lot of work for complicated objects,
        # so for derived classes we specialize this
        return out.write(repr(self.proxyval(visited)))

    @classmethod
    def subclass_from_type(cls, t):
        '''
        Given a PyTypeObjectPtr instance wrapping a gdb.Value that's a
        (PyTypeObject*), determine the corresponding subclass of PyObjectPtr
        to use

        Ideally, we would look up the symbols for the global types, but that
        isn't working yet:
          (gdb) python print gdb.lookup_symbol('PyList_Type')[0].value
          Traceback (most recent call last):
            File "<string>", line 1, in <module>
          NotImplementedError: Symbol type not yet supported in Python scripts.
          Error while executing Python code.

        For now, we use tp_flags, after doing some string comparisons on the
        tp_name for some special-cases that don't seem to be visible through
        flags
        '''
        try:
            tp_name = t.field('tp_name').string()
            tp_flags = int(t.field('tp_flags'))
        except RuntimeError:
            # Handle any kind of error e.g. NULL ptrs by simply using the base
            # class
            return cls

        #print 'tp_flags = 0x%08x' % tp_flags
        #print 'tp_name = %r' % tp_name

        name_map = {'bool': PyBoolObjectPtr,
                    'classobj': PyClassObjectPtr,
                    'instance': PyInstanceObjectPtr,
                    'NoneType': PyNoneStructPtr,
                    'frame': PyFrameObjectPtr,
                    'set' : PySetObjectPtr,
                    'frozenset' : PySetObjectPtr,
                    'builtin_function_or_method' : PyCFunctionObjectPtr,
                    }
        if tp_name in name_map:
            return name_map[tp_name]

        if tp_flags & Py_TPFLAGS_HEAPTYPE:
            return HeapTypeObjectPtr

        if tp_flags & Py_TPFLAGS_INT_SUBCLASS:
            return PyIntObjectPtr
        if tp_flags & Py_TPFLAGS_LONG_SUBCLASS:
            return PyLongObjectPtr
        if tp_flags & Py_TPFLAGS_LIST_SUBCLASS:
            return PyListObjectPtr
        if tp_flags & Py_TPFLAGS_TUPLE_SUBCLASS:
            return PyTupleObjectPtr
        if tp_flags & Py_TPFLAGS_STRING_SUBCLASS:
            return PyStringObjectPtr
        if tp_flags & Py_TPFLAGS_UNICODE_SUBCLASS:
            return PyUnicodeObjectPtr
        if tp_flags & Py_TPFLAGS_DICT_SUBCLASS:
            return PyDictObjectPtr
        if tp_flags & Py_TPFLAGS_BASE_EXC_SUBCLASS:
            return PyBaseExceptionObjectPtr
        #if tp_flags & Py_TPFLAGS_TYPE_SUBCLASS:
        #    return PyTypeObjectPtr

        # Use the base class:
        return cls

    @classmethod
    def from_pyobject_ptr(cls, gdbval):
        '''
        Try to locate the appropriate derived class dynamically, and cast
        the pointer accordingly.
        '''
        try:
            p = PyObjectPtr(gdbval)
            cls = cls.subclass_from_type(p.type())
            return cls(gdbval, cast_to=cls.get_gdb_type())
        except RuntimeError:
            # Handle any kind of error e.g. NULL ptrs by simply using the base
            # class
            pass
        return cls(gdbval)

    @classmethod
    def get_gdb_type(cls):
        return gdb.lookup_type(cls._typename).pointer()

    def as_address(self):
        return long(self._gdbval)


class ProxyAlreadyVisited(object):
    '''
    Placeholder proxy to use when protecting against infinite recursion due to
    loops in the object graph.

    Analogous to the values emitted by the users of Py_ReprEnter and Py_ReprLeave
    '''
    def __init__(self, rep):
        self._rep = rep

    def __repr__(self):
        return self._rep


def _write_instance_repr(out, visited, name, pyop_attrdict, address):
    '''Shared code for use by old-style and new-style classes:
    write a representation to file-like object "out"'''
    out.write('<')
    out.write(name)

    # Write dictionary of instance attributes:
    if isinstance(pyop_attrdict, PyDictObjectPtr):
        out.write('(')
        first = True
        for pyop_arg, pyop_val in pyop_attrdict.iteritems():
            if not first:
                out.write(', ')
            first = False
            out.write(pyop_arg.proxyval(visited))
            out.write('=')
            pyop_val.write_repr(out, visited)
        out.write(')')
    out.write(' at remote 0x%x>' % address)


class InstanceProxy(object):

    def __init__(self, cl_name, attrdict, address):
        self.cl_name = cl_name
        self.attrdict = attrdict
        self.address = address

    def __repr__(self):
        if isinstance(self.attrdict, dict):
            kwargs = ', '.join(["%s=%r" % (arg, val)
                                for arg, val in self.attrdict.iteritems()])
            return '<%s(%s) at remote 0x%x>' % (self.cl_name,
                                                kwargs, self.address)
        else:
            return '<%s at remote 0x%x>' % (self.cl_name,
                                            self.address)

def _PyObject_VAR_SIZE(typeobj, nitems):
    if _PyObject_VAR_SIZE._type_size_t is None:
        _PyObject_VAR_SIZE._type_size_t = gdb.lookup_type('size_t')

    return ( ( typeobj.field('tp_basicsize') +
               nitems * typeobj.field('tp_itemsize') +
               (SIZEOF_VOID_P - 1)
             ) & ~(SIZEOF_VOID_P - 1)
           ).cast(_PyObject_VAR_SIZE._type_size_t)
_PyObject_VAR_SIZE._type_size_t = None

class HeapTypeObjectPtr(PyObjectPtr):
    _typename = 'PyObject'

    def get_attr_dict(self):
        '''
        Get the PyDictObject ptr representing the attribute dictionary
        (or None if there's a problem)
        '''
        try:
            typeobj = self.type()
            dictoffset = int_from_int(typeobj.field('tp_dictoffset'))
            if dictoffset != 0:
                if dictoffset < 0:
                    type_PyVarObject_ptr = gdb.lookup_type('PyVarObject').pointer()
                    tsize = int_from_int(self._gdbval.cast(type_PyVarObject_ptr)['ob_size'])
                    if tsize < 0:
                        tsize = -tsize
                    size = _PyObject_VAR_SIZE(typeobj, tsize)
                    dictoffset += size
                    assert dictoffset > 0
                    assert dictoffset % SIZEOF_VOID_P == 0

                dictptr = self._gdbval.cast(_type_char_ptr) + dictoffset
                PyObjectPtrPtr = PyObjectPtr.get_gdb_type().pointer()
                dictptr = dictptr.cast(PyObjectPtrPtr)
                return PyObjectPtr.from_pyobject_ptr(dictptr.dereference())
        except RuntimeError:
            # Corrupt data somewhere; fail safe
            pass

        # Not found, or some kind of error:
        return None

    def proxyval(self, visited):
        '''
        Support for new-style classes.

        Currently we just locate the dictionary using a transliteration to
        python of _PyObject_GetDictPtr, ignoring descriptors
        '''
        # Guard against infinite loops:
        if self.as_address() in visited:
            return ProxyAlreadyVisited('<...>')
        visited.add(self.as_address())

        pyop_attr_dict = self.get_attr_dict()
        if pyop_attr_dict:
            attr_dict = pyop_attr_dict.proxyval(visited)
        else:
            attr_dict = {}
        tp_name = self.safe_tp_name()

        # New-style class:
        return InstanceProxy(tp_name, attr_dict, long(self._gdbval))

    def write_repr(self, out, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            out.write('<...>')
            return
        visited.add(self.as_address())

        pyop_attrdict = self.get_attr_dict()
        _write_instance_repr(out, visited,
                             self.safe_tp_name(), pyop_attrdict, self.as_address())

class ProxyException(Exception):
    def __init__(self, tp_name, args):
        self.tp_name = tp_name
        self.args = args

    def __repr__(self):
        return '%s%r' % (self.tp_name, self.args)

class PyBaseExceptionObjectPtr(PyObjectPtr):
    """
    Class wrapping a gdb.Value that's a PyBaseExceptionObject* i.e. an exception
    within the process being debugged.
    """
    _typename = 'PyBaseExceptionObject'

    def proxyval(self, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            return ProxyAlreadyVisited('(...)')
        visited.add(self.as_address())
        arg_proxy = self.pyop_field('args').proxyval(visited)
        return ProxyException(self.safe_tp_name(),
                              arg_proxy)

    def write_repr(self, out, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            out.write('(...)')
            return
        visited.add(self.as_address())

        out.write(self.safe_tp_name())
        self.write_field_repr('args', out, visited)

class PyBoolObjectPtr(PyObjectPtr):
    """
    Class wrapping a gdb.Value that's a PyBoolObject* i.e. one of the two
    <bool> instances (Py_True/Py_False) within the process being debugged.
    """
    _typename = 'PyBoolObject'

    def proxyval(self, visited):
        if int_from_int(self.field('ob_ival')):
            return True
        else:
            return False


class PyClassObjectPtr(PyObjectPtr):
    """
    Class wrapping a gdb.Value that's a PyClassObject* i.e. a <classobj>
    instance within the process being debugged.
    """
    _typename = 'PyClassObject'


class BuiltInFunctionProxy(object):
    def __init__(self, ml_name):
        self.ml_name = ml_name

    def __repr__(self):
        return "<built-in function %s>" % self.ml_name

class BuiltInMethodProxy(object):
    def __init__(self, ml_name, pyop_m_self):
        self.ml_name = ml_name
        self.pyop_m_self = pyop_m_self

    def __repr__(self):
        return ('<built-in method %s of %s object at remote 0x%x>'
                % (self.ml_name,
                   self.pyop_m_self.safe_tp_name(),
                   self.pyop_m_self.as_address())
                )

class PyCFunctionObjectPtr(PyObjectPtr):
    """
    Class wrapping a gdb.Value that's a PyCFunctionObject*
    (see Include/methodobject.h and Objects/methodobject.c)
    """
    _typename = 'PyCFunctionObject'

    def proxyval(self, visited):
        m_ml = self.field('m_ml') # m_ml is a (PyMethodDef*)
        ml_name = m_ml['ml_name'].string()

        pyop_m_self = self.pyop_field('m_self')
        if pyop_m_self.is_null():
            return BuiltInFunctionProxy(ml_name)
        else:
            return BuiltInMethodProxy(ml_name, pyop_m_self)


class PyCodeObjectPtr(PyObjectPtr):
    """
    Class wrapping a gdb.Value that's a PyCodeObject* i.e. a <code> instance
    within the process being debugged.
    """
    _typename = 'PyCodeObject'

    def addr2line(self, addrq):
        '''
        Get the line number for a given bytecode offset

        Analogous to PyCode_Addr2Line; translated from pseudocode in
        Objects/lnotab_notes.txt
        '''
        co_lnotab = self.pyop_field('co_lnotab').proxyval(set())

        # Initialize lineno to co_firstlineno as per PyCode_Addr2Line
        # not 0, as lnotab_notes.txt has it:
        lineno = int_from_int(self.field('co_firstlineno'))

        addr = 0
        for addr_incr, line_incr in zip(co_lnotab[::2], co_lnotab[1::2]):
            addr += ord(addr_incr)
            if addr > addrq:
                return lineno
            lineno += ord(line_incr)
        return lineno


class PyDictObjectPtr(PyObjectPtr):
    """
    Class wrapping a gdb.Value that's a PyDictObject* i.e. a dict instance
    within the process being debugged.
    """
    _typename = 'PyDictObject'

    def iteritems(self):
        '''
        Yields a sequence of (PyObjectPtr key, PyObjectPtr value) pairs,
        analagous to dict.iteritems()
        '''
        for i in safe_range(self.field('ma_mask') + 1):
            ep = self.field('ma_table') + i
            pyop_value = PyObjectPtr.from_pyobject_ptr(ep['me_value'])
            if not pyop_value.is_null():
                pyop_key = PyObjectPtr.from_pyobject_ptr(ep['me_key'])
                yield (pyop_key, pyop_value)

    def proxyval(self, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            return ProxyAlreadyVisited('{...}')
        visited.add(self.as_address())

        result = {}
        for pyop_key, pyop_value in self.iteritems():
            proxy_key = pyop_key.proxyval(visited)
            proxy_value = pyop_value.proxyval(visited)
            result[proxy_key] = proxy_value
        return result

    def write_repr(self, out, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            out.write('{...}')
            return
        visited.add(self.as_address())

        out.write('{')
        first = True
        for pyop_key, pyop_value in self.iteritems():
            if not first:
                out.write(', ')
            first = False
            pyop_key.write_repr(out, visited)
            out.write(': ')
            pyop_value.write_repr(out, visited)
        out.write('}')

class PyInstanceObjectPtr(PyObjectPtr):
    _typename = 'PyInstanceObject'

    def proxyval(self, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            return ProxyAlreadyVisited('<...>')
        visited.add(self.as_address())

        # Get name of class:
        in_class = self.pyop_field('in_class')
        cl_name = in_class.pyop_field('cl_name').proxyval(visited)

        # Get dictionary of instance attributes:
        in_dict = self.pyop_field('in_dict').proxyval(visited)

        # Old-style class:
        return InstanceProxy(cl_name, in_dict, long(self._gdbval))

    def write_repr(self, out, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            out.write('<...>')
            return
        visited.add(self.as_address())

        # Old-style class:

        # Get name of class:
        in_class = self.pyop_field('in_class')
        cl_name = in_class.pyop_field('cl_name').proxyval(visited)

        # Get dictionary of instance attributes:
        pyop_in_dict = self.pyop_field('in_dict')

        _write_instance_repr(out, visited,
                             cl_name, pyop_in_dict, self.as_address())

class PyIntObjectPtr(PyObjectPtr):
    _typename = 'PyIntObject'

    def proxyval(self, visited):
        result = int_from_int(self.field('ob_ival'))
        return result

class PyListObjectPtr(PyObjectPtr):
    _typename = 'PyListObject'

    def __getitem__(self, i):
        # Get the gdb.Value for the (PyObject*) with the given index:
        field_ob_item = self.field('ob_item')
        return field_ob_item[i]

    def proxyval(self, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            return ProxyAlreadyVisited('[...]')
        visited.add(self.as_address())

        result = [PyObjectPtr.from_pyobject_ptr(self[i]).proxyval(visited)
                  for i in safe_range(int_from_int(self.field('ob_size')))]
        return result

    def write_repr(self, out, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            out.write('[...]')
            return
        visited.add(self.as_address())

        out.write('[')
        for i in safe_range(int_from_int(self.field('ob_size'))):
            if i > 0:
                out.write(', ')
            element = PyObjectPtr.from_pyobject_ptr(self[i])
            element.write_repr(out, visited)
        out.write(']')

class PyLongObjectPtr(PyObjectPtr):
    _typename = 'PyLongObject'

    def proxyval(self, visited):
        '''
        Python's Include/longobjrep.h has this declaration:
           struct _longobject {
               PyObject_VAR_HEAD
               digit ob_digit[1];
           };

        with this description:
            The absolute value of a number is equal to
                 SUM(for i=0 through abs(ob_size)-1) ob_digit[i] * 2**(SHIFT*i)
            Negative numbers are represented with ob_size < 0;
            zero is represented by ob_size == 0.

        where SHIFT can be either:
            #define PyLong_SHIFT        30
            #define PyLong_SHIFT        15
        '''
        ob_size = long(self.field('ob_size'))
        if ob_size == 0:
            return 0L

        ob_digit = self.field('ob_digit')

        if gdb.lookup_type('digit').sizeof == 2:
            SHIFT = 15L
        else:
            SHIFT = 30L

        digits = [long(ob_digit[i]) * 2**(SHIFT*i)
                  for i in safe_range(abs(ob_size))]
        result = sum(digits)
        if ob_size < 0:
            result = -result
        return result


class PyNoneStructPtr(PyObjectPtr):
    """
    Class wrapping a gdb.Value that's a PyObject* pointing to the
    singleton (we hope) _Py_NoneStruct with ob_type PyNone_Type
    """
    _typename = 'PyObject'

    def proxyval(self, visited):
        return None


class PyFrameObjectPtr(PyObjectPtr):
    _typename = 'PyFrameObject'

    def __init__(self, gdbval, cast_to=None):
        PyObjectPtr.__init__(self, gdbval, cast_to)

        if not self.is_optimized_out():
            self.co = PyCodeObjectPtr.from_pyobject_ptr(self.field('f_code'))
            self.co_name = self.co.pyop_field('co_name')
            self.co_filename = self.co.pyop_field('co_filename')

            self.f_lineno = int_from_int(self.field('f_lineno'))
            self.f_lasti = int_from_int(self.field('f_lasti'))
            self.co_nlocals = int_from_int(self.co.field('co_nlocals'))
            self.co_varnames = PyTupleObjectPtr.from_pyobject_ptr(self.co.field('co_varnames'))

    def iter_locals(self):
        '''
        Yield a sequence of (name,value) pairs of PyObjectPtr instances, for
        the local variables of this frame
        '''
        if self.is_optimized_out():
            return

        f_localsplus = self.field('f_localsplus')
        for i in safe_range(self.co_nlocals):
            pyop_value = PyObjectPtr.from_pyobject_ptr(f_localsplus[i])
            if not pyop_value.is_null():
                pyop_name = PyObjectPtr.from_pyobject_ptr(self.co_varnames[i])
                yield (pyop_name, pyop_value)

    def iter_globals(self):
        '''
        Yield a sequence of (name,value) pairs of PyObjectPtr instances, for
        the global variables of this frame
        '''
        if self.is_optimized_out():
            return ()

        pyop_globals = self.pyop_field('f_globals')
        return pyop_globals.iteritems()

    def iter_builtins(self):
        '''
        Yield a sequence of (name,value) pairs of PyObjectPtr instances, for
        the builtin variables
        '''
        if self.is_optimized_out():
            return ()

        pyop_builtins = self.pyop_field('f_builtins')
        return pyop_builtins.iteritems()

    def get_var_by_name(self, name):
        '''
        Look for the named local variable, returning a (PyObjectPtr, scope) pair
        where scope is a string 'local', 'global', 'builtin'

        If not found, return (None, None)
        '''
        for pyop_name, pyop_value in self.iter_locals():
            if name == pyop_name.proxyval(set()):
                return pyop_value, 'local'
        for pyop_name, pyop_value in self.iter_globals():
            if name == pyop_name.proxyval(set()):
                return pyop_value, 'global'
        for pyop_name, pyop_value in self.iter_builtins():
            if name == pyop_name.proxyval(set()):
                return pyop_value, 'builtin'
        return None, None

    def filename(self):
        '''Get the path of the current Python source file, as a string'''
        if self.is_optimized_out():
            return '(frame information optimized out)'
        return self.co_filename.proxyval(set())

    def current_line_num(self):
        '''Get current line number as an integer (1-based)

        Translated from PyFrame_GetLineNumber and PyCode_Addr2Line

        See Objects/lnotab_notes.txt
        '''
        if self.is_optimized_out():
            return None
        f_trace = self.field('f_trace')
        if long(f_trace) != 0:
            # we have a non-NULL f_trace:
            return self.f_lineno
        else:
            #try:
            return self.co.addr2line(self.f_lasti)
            #except ValueError:
            #    return self.f_lineno

    def current_line(self):
        '''Get the text of the current source line as a string, with a trailing
        newline character'''
        if self.is_optimized_out():
            return '(frame information optimized out)'
        with open(self.filename(), 'r') as f:
            all_lines = f.readlines()
            # Convert from 1-based current_line_num to 0-based list offset:
            return all_lines[self.current_line_num()-1]

    def write_repr(self, out, visited):
        if self.is_optimized_out():
            out.write('(frame information optimized out)')
            return
        out.write('Frame 0x%x, for file %s, line %i, in %s ('
                  % (self.as_address(),
                     self.co_filename,
                     self.current_line_num(),
                     self.co_name))
        first = True
        for pyop_name, pyop_value in self.iter_locals():
            if not first:
                out.write(', ')
            first = False

            out.write(pyop_name.proxyval(visited))
            out.write('=')
            pyop_value.write_repr(out, visited)

        out.write(')')

class PySetObjectPtr(PyObjectPtr):
    _typename = 'PySetObject'

    def proxyval(self, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            return ProxyAlreadyVisited('%s(...)' % self.safe_tp_name())
        visited.add(self.as_address())

        members = []
        table = self.field('table')
        for i in safe_range(self.field('mask')+1):
            setentry = table[i]
            key = setentry['key']
            if key != 0:
                key_proxy = PyObjectPtr.from_pyobject_ptr(key).proxyval(visited)
                if key_proxy != '<dummy key>':
                    members.append(key_proxy)
        if self.safe_tp_name() == 'frozenset':
            return frozenset(members)
        else:
            return set(members)

    def write_repr(self, out, visited):
        out.write(self.safe_tp_name())

        # Guard against infinite loops:
        if self.as_address() in visited:
            out.write('(...)')
            return
        visited.add(self.as_address())

        out.write('([')
        first = True
        table = self.field('table')
        for i in safe_range(self.field('mask')+1):
            setentry = table[i]
            key = setentry['key']
            if key != 0:
                pyop_key = PyObjectPtr.from_pyobject_ptr(key)
                key_proxy = pyop_key.proxyval(visited) # FIXME!
                if key_proxy != '<dummy key>':
                    if not first:
                        out.write(', ')
                    first = False
                    pyop_key.write_repr(out, visited)
        out.write('])')


class PyStringObjectPtr(PyObjectPtr):
    _typename = 'PyStringObject'

    def __str__(self):
        field_ob_size = self.field('ob_size')
        field_ob_sval = self.field('ob_sval')
        char_ptr = field_ob_sval.address.cast(_type_unsigned_char_ptr)
        return ''.join([chr(char_ptr[i]) for i in safe_range(field_ob_size)])

    def proxyval(self, visited):
        return str(self)

class PyTupleObjectPtr(PyObjectPtr):
    _typename = 'PyTupleObject'

    def __getitem__(self, i):
        # Get the gdb.Value for the (PyObject*) with the given index:
        field_ob_item = self.field('ob_item')
        return field_ob_item[i]

    def proxyval(self, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            return ProxyAlreadyVisited('(...)')
        visited.add(self.as_address())

        result = tuple([PyObjectPtr.from_pyobject_ptr(self[i]).proxyval(visited)
                        for i in safe_range(int_from_int(self.field('ob_size')))])
        return result

    def write_repr(self, out, visited):
        # Guard against infinite loops:
        if self.as_address() in visited:
            out.write('(...)')
            return
        visited.add(self.as_address())

        out.write('(')
        for i in safe_range(int_from_int(self.field('ob_size'))):
            if i > 0:
                out.write(', ')
            element = PyObjectPtr.from_pyobject_ptr(self[i])
            element.write_repr(out, visited)
        if self.field('ob_size') == 1:
            out.write(',)')
        else:
            out.write(')')

class PyTypeObjectPtr(PyObjectPtr):
    _typename = 'PyTypeObject'


if sys.maxunicode >= 0x10000:
    _unichr = unichr
else:
    # Needed for proper surrogate support if sizeof(Py_UNICODE) is 2 in gdb
    def _unichr(x):
        if x < 0x10000:
            return unichr(x)
        x -= 0x10000
        ch1 = 0xD800 | (x >> 10)
        ch2 = 0xDC00 | (x & 0x3FF)
        return unichr(ch1) + unichr(ch2)

class PyUnicodeObjectPtr(PyObjectPtr):
    _typename = 'PyUnicodeObject'

    def char_width(self):
        _type_Py_UNICODE = gdb.lookup_type('Py_UNICODE')
        return _type_Py_UNICODE.sizeof

    def proxyval(self, visited):
        # From unicodeobject.h:
        #     Py_ssize_t length;  /* Length of raw Unicode data in buffer */
        #     Py_UNICODE *str;    /* Raw Unicode buffer */
        field_length = long(self.field('length'))
        field_str = self.field('str')

        # Gather a list of ints from the Py_UNICODE array; these are either
        # UCS-2 or UCS-4 code points:
        if self.char_width() > 2:
            Py_UNICODEs = [int(field_str[i]) for i in safe_range(field_length)]
        else:
            # A more elaborate routine if sizeof(Py_UNICODE) is 2 in the
            # inferior process: we must join surrogate pairs.
            Py_UNICODEs = []
            i = 0
            limit = safety_limit(field_length)
            while i < limit:
                ucs = int(field_str[i])
                i += 1
                if ucs < 0xD800 or ucs >= 0xDC00 or i == field_length:
                    Py_UNICODEs.append(ucs)
                    continue
                # This could be a surrogate pair.
                ucs2 = int(field_str[i])
                if ucs2 < 0xDC00 or ucs2 > 0xDFFF:
                    continue
                code = (ucs & 0x03FF) << 10
                code |= ucs2 & 0x03FF
                code += 0x00010000
                Py_UNICODEs.append(code)
                i += 1

        # Convert the int code points to unicode characters, and generate a
        # local unicode instance.
        # This splits surrogate pairs if sizeof(Py_UNICODE) is 2 here (in gdb).
        result = u''.join([_unichr(ucs) for ucs in Py_UNICODEs])
        return result


def int_from_int(gdbval):
    return int(str(gdbval))


def stringify(val):
    # TODO: repr() puts everything on one line; pformat can be nicer, but
    # can lead to v.long results; this function isolates the choice
    if True:
        return repr(val)
    else:
        from pprint import pformat
        return pformat(val)


class PyObjectPtrPrinter:
    "Prints a (PyObject*)"

    def __init__ (self, gdbval):
        self.gdbval = gdbval

    def to_string (self):
        pyop = PyObjectPtr.from_pyobject_ptr(self.gdbval)
        if True:
            return pyop.get_truncated_repr(MAX_OUTPUT_LEN)
        else:
            # Generate full proxy value then stringify it.
            # Doing so could be expensive
            proxyval = pyop.proxyval(set())
            return stringify(proxyval)

def pretty_printer_lookup(gdbval):
    type = gdbval.type.unqualified()
    if type.code == gdb.TYPE_CODE_PTR:
        type = type.target().unqualified()
        t = str(type)
        if t in ("PyObject", "PyFrameObject"):
            return PyObjectPtrPrinter(gdbval)

"""
During development, I've been manually invoking the code in this way:
(gdb) python

import sys
sys.path.append('/home/david/coding/python-gdb')
import libpython
end

then reloading it after each edit like this:
(gdb) python reload(libpython)

The following code should ensure that the prettyprinter is registered
if the code is autoloaded by gdb when visiting libpython.so, provided
that this python file is installed to the same path as the library (or its
.debug file) plus a "-gdb.py" suffix, e.g:
  /usr/lib/libpython2.6.so.1.0-gdb.py
  /usr/lib/debug/usr/lib/libpython2.6.so.1.0.debug-gdb.py
"""
def register (obj):
    if obj == None:
        obj = gdb

    # Wire up the pretty-printer
    obj.pretty_printers.append(pretty_printer_lookup)

register (gdb.current_objfile ())



# Unfortunately, the exact API exposed by the gdb module varies somewhat
# from build to build
# See http://bugs.python.org/issue8279?#msg102276

class Frame(object):
    '''
    Wrapper for gdb.Frame, adding various methods
    '''
    def __init__(self, gdbframe):
        self._gdbframe = gdbframe

    def older(self):
        older = self._gdbframe.older()
        if older:
            return Frame(older)
        else:
            return None

    def newer(self):
        newer = self._gdbframe.newer()
        if newer:
            return Frame(newer)
        else:
            return None

    def select(self):
        '''If supported, select this frame and return True; return False if unsupported

        Not all builds have a gdb.Frame.select method; seems to be present on Fedora 12
        onwards, but absent on Ubuntu buildbot'''
        if not hasattr(self._gdbframe, 'select'):
            print ('Unable to select frame: '
                   'this build of gdb does not expose a gdb.Frame.select method')
            return False
        self._gdbframe.select()
        return True

    def get_index(self):
        '''Calculate index of frame, starting at 0 for the newest frame within
        this thread'''
        index = 0
        # Go down until you reach the newest frame:
        iter_frame = self
        while iter_frame.newer():
            index += 1
            iter_frame = iter_frame.newer()
        return index

    def is_evalframeex(self):
        '''Is this a PyEval_EvalFrameEx frame?'''
        if self._gdbframe.name() == 'PyEval_EvalFrameEx':
            '''
            I believe we also need to filter on the inline
            struct frame_id.inline_depth, only regarding frames with
            an inline depth of 0 as actually being this function

            So we reject those with type gdb.INLINE_FRAME
            '''
            if self._gdbframe.type() == gdb.NORMAL_FRAME:
                # We have a PyEval_EvalFrameEx frame:
                return True

        return False

    def get_pyop(self):
        try:
            f = self._gdbframe.read_var('f')
            frame = PyFrameObjectPtr.from_pyobject_ptr(f)
            if not frame.is_optimized_out():
                return frame
            # gdb is unable to get the "f" argument of PyEval_EvalFrameEx()
            # because it was "optimized out". Try to get "f" from the frame
            # of the caller, PyEval_EvalCodeEx().
            orig_frame = frame
            caller = self._gdbframe.older()
            if caller:
                f = caller.read_var('f')
                frame = PyFrameObjectPtr.from_pyobject_ptr(f)
                if not frame.is_optimized_out():
                    return frame
            return orig_frame
        except ValueError:
            return None

    @classmethod
    def get_selected_frame(cls):
        _gdbframe = gdb.selected_frame()
        if _gdbframe:
            return Frame(_gdbframe)
        return None

    @classmethod
    def get_selected_python_frame(cls):
        '''Try to obtain the Frame for the python code in the selected frame,
        or None'''
        frame = cls.get_selected_frame()

        while frame:
            if frame.is_evalframeex():
                return frame
            frame = frame.older()

        # Not found:
        return None

    def print_summary(self):
        if self.is_evalframeex():
            pyop = self.get_pyop()
            if pyop:
                sys.stdout.write('#%i %s\n' % (self.get_index(), pyop.get_truncated_repr(MAX_OUTPUT_LEN)))
                if not pyop.is_optimized_out():
                    line = pyop.current_line()
                    sys.stdout.write('    %s\n' % line.strip())
            else:
                sys.stdout.write('#%i (unable to read python frame information)\n' % self.get_index())
        else:
            sys.stdout.write('#%i\n' % self.get_index())

class PyList(gdb.Command):
    '''List the current Python source code, if any

    Use
       py-list START
    to list at a different line number within the python source.

    Use
       py-list START, END
    to list a specific range of lines within the python source.
    '''

    def __init__(self):
        gdb.Command.__init__ (self,
                              "py-list",
                              gdb.COMMAND_FILES,
                              gdb.COMPLETE_NONE)


    def invoke(self, args, from_tty):
        import re

        start = None
        end = None

        m = re.match(r'\s*(\d+)\s*', args)
        if m:
            start = int(m.group(0))
            end = start + 10

        m = re.match(r'\s*(\d+)\s*,\s*(\d+)\s*', args)
        if m:
            start, end = map(int, m.groups())

        frame = Frame.get_selected_python_frame()
        if not frame:
            print 'Unable to locate python frame'
            return

        pyop = frame.get_pyop()
        if not pyop or pyop.is_optimized_out():
            print 'Unable to read information on python frame'
            return

        filename = pyop.filename()
        lineno = pyop.current_line_num()

        if start is None:
            start = lineno - 5
            end = lineno + 5

        if start<1:
            start = 1

        with open(filename, 'r') as f:
            all_lines = f.readlines()
            # start and end are 1-based, all_lines is 0-based;
            # so [start-1:end] as a python slice gives us [start, end] as a
            # closed interval
            for i, line in enumerate(all_lines[start-1:end]):
                linestr = str(i+start)
                # Highlight current line:
                if i + start == lineno:
                    linestr = '>' + linestr
                sys.stdout.write('%4s    %s' % (linestr, line))


# ...and register the command:
PyList()

def move_in_stack(move_up):
    '''Move up or down the stack (for the py-up/py-down command)'''
    frame = Frame.get_selected_python_frame()
    while frame:
        if move_up:
            iter_frame = frame.older()
        else:
            iter_frame = frame.newer()

        if not iter_frame:
            break

        if iter_frame.is_evalframeex():
            # Result:
            if iter_frame.select():
                iter_frame.print_summary()
            return

        frame = iter_frame

    if move_up:
        print 'Unable to find an older python frame'
    else:
        print 'Unable to find a newer python frame'

class PyUp(gdb.Command):
    'Select and print the python stack frame that called this one (if any)'
    def __init__(self):
        gdb.Command.__init__ (self,
                              "py-up",
                              gdb.COMMAND_STACK,
                              gdb.COMPLETE_NONE)


    def invoke(self, args, from_tty):
        move_in_stack(move_up=True)

class PyDown(gdb.Command):
    'Select and print the python stack frame called by this one (if any)'
    def __init__(self):
        gdb.Command.__init__ (self,
                              "py-down",
                              gdb.COMMAND_STACK,
                              gdb.COMPLETE_NONE)


    def invoke(self, args, from_tty):
        move_in_stack(move_up=False)

# Not all builds of gdb have gdb.Frame.select
if hasattr(gdb.Frame, 'select'):
    PyUp()
    PyDown()

class PyBacktrace(gdb.Command):
    'Display the current python frame and all the frames within its call stack (if any)'
    def __init__(self):
        gdb.Command.__init__ (self,
                              "py-bt",
                              gdb.COMMAND_STACK,
                              gdb.COMPLETE_NONE)


    def invoke(self, args, from_tty):
        frame = Frame.get_selected_python_frame()
        while frame:
            if frame.is_evalframeex():
                frame.print_summary()
            frame = frame.older()

PyBacktrace()

class PyPrint(gdb.Command):
    'Look up the given python variable name, and print it'
    def __init__(self):
        gdb.Command.__init__ (self,
                              "py-print",
                              gdb.COMMAND_DATA,
                              gdb.COMPLETE_NONE)


    def invoke(self, args, from_tty):
        name = str(args)

        frame = Frame.get_selected_python_frame()
        if not frame:
            print 'Unable to locate python frame'
            return

        pyop_frame = frame.get_pyop()
        if not pyop_frame:
            print 'Unable to read information on python frame'
            return

        pyop_var, scope = pyop_frame.get_var_by_name(name)

        if pyop_var:
            print ('%s %r = %s'
                   % (scope,
                      name,
                      pyop_var.get_truncated_repr(MAX_OUTPUT_LEN)))
        else:
            print '%r not found' % name

PyPrint()

class PyLocals(gdb.Command):
    'Look up the given python variable name, and print it'
    def __init__(self):
        gdb.Command.__init__ (self,
                              "py-locals",
                              gdb.COMMAND_DATA,
                              gdb.COMPLETE_NONE)


    def invoke(self, args, from_tty):
        name = str(args)

        frame = Frame.get_selected_python_frame()
        if not frame:
            print 'Unable to locate python frame'
            return

        pyop_frame = frame.get_pyop()
        if not pyop_frame:
            print 'Unable to read information on python frame'
            return

        for pyop_name, pyop_value in pyop_frame.iter_locals():
            print ('%s = %s'
                   % (pyop_name.proxyval(set()),
                      pyop_value.get_truncated_repr(MAX_OUTPUT_LEN)))

PyLocals()

########NEW FILE########
__FILENAME__ = gdb_shell
#! /usr/bin/env python
#
# Copyright 2014 Google Inc.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Plugin which drops the user to a raw gdb prompt."""


import os

from pyringe.plugins import mod_base


class GdbPlugin(mod_base.DebuggingPlugin):
  """Plugin which can drop the user to a raw gdb prompt."""

  gdb_args = []

  def __init__(self, inferior, name='gdb'):
    super(GdbPlugin, self).__init__(inferior, name)

  @property
  def commands(self):
    return (super(GdbPlugin, self).commands +
            [('gdb', self.StartGdb),
             ('setgdbargs', self.SetGdbArgs)])

  def StartGdb(self):
    """Hands control over to a new gdb process."""
    if self.inferior.is_running:
      self.inferior.ShutDownGdb()
      program_arg = 'program %d ' % self.inferior.pid
    else:
      program_arg = ''
    os.system('gdb ' + program_arg + ' '.join(self.gdb_args))
    reset_position = raw_input('Reset debugger position? [y]/n ')
    if not reset_position or reset_position == 'y' or reset_position == 'yes':
      self.position = None

  def SetGdbArgs(self, newargs):
    """Set additional custom arguments for Gdb."""
    self.gdb_args = newargs


########NEW FILE########
__FILENAME__ = inject
#! /usr/bin/env python
#
# Copyright 2014 Google Inc.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Python code injection into arbitrary threads."""


import logging
import sys
import traceback

import inject_sentinel


class InjectPlugin(inject_sentinel.SentinelInjectPlugin):
  """Python code injection into arbitrary threads."""

  def __init__(self, inferior, name='inj'):
    super(InjectPlugin, self).__init__(inferior, name)

  @property
  def commands(self):
    return (super(InjectPlugin, self).commands +
            [('inject', self.InjectString),
             ('injectsentinel', self.InjectSentinel),
             ('_pdb', self.InjectPdb),
            ])

  def InjectString(self, codestring, wait_for_completion=True):
    """Try to inject python code into current thread.

    Args:
      codestring: Python snippet to execute in inferior. (may contain newlines)
      wait_for_completion: Block until execution of snippet has completed.
    """
    if self.inferior.is_running and self.inferior.gdb.IsAttached():
      try:
        self.inferior.gdb.InjectString(
            self.inferior.position,
            codestring,
            wait_for_completion=wait_for_completion)
      except RuntimeError:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
    else:
      logging.error('Not attached to any process.')

  def InjectSentinel(self):
    """Try to inject code that starts the code injection helper thread."""
    raise NotImplementedError

  def InjectPdb(self):
    """Try to inject a pdb shell into the current thread."""
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = inject_sentinel
#! /usr/bin/env python
#
# Copyright 2014 Google Inc.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Python code injection into helper thread."""


import json
import logging
import os
import socket
import read_only


class SentinelInjectPlugin(read_only.ReadonlyPlugin):
  """Python code injection into helper (sentinel) thread.

  Note that while the command interface of this mode is the same as that of
  InjectPlugin, the `inject` and `pdb` commands are always executed in the
  context of the helper thread.
  """

  def __init__(self, inferior, name='sent'):
    super(SentinelInjectPlugin, self).__init__(inferior, name)

  @property
  def commands(self):
    return (super(SentinelInjectPlugin, self).commands +
            [('execsocks', self.ThreadsWithRunningExecServers),
             ('send', self.SendToExecSocket),
             ('closesock', self.CloseExecSocket),
             ('pdb', self.InjectPdb),
            ])

  def ThreadsWithRunningExecServers(self):
    """Returns a list of tids of inferior threads with open exec servers."""
    socket_dir = '/tmp/pyringe_%s' % self.inferior.pid
    if os.path.isdir(socket_dir):
      return [int(fname[:-9])
              for fname in os.listdir(socket_dir)
              if fname.endswith('.execsock')]
    return []

  def SendToExecSocket(self, code, tid=None):
    """Inject python code into exec socket."""
    response = self._SendToExecSocketRaw(json.dumps(code), tid)
    return json.loads(response)

  def _SendToExecSocketRaw(self, string, tid=None):
    if not tid:
      tid = self.inferior.current_thread
    socket_dir = '/tmp/pyringe_%s' % self.inferior.pid
    if tid not in self.ThreadsWithRunningExecServers():
      logging.error('Couldn\'t find socket for thread ' + str(tid))
      return
    # We have to make sure the inferior can process the request
    # TODO: replace this gdb kill with a call to the continue command when we
    # add async command execution
    self.inferior.ShutDownGdb()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect('%s/%s.execsock' % (socket_dir, tid))
    sock.sendall(string)
    response = sock.recv(1024)
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()
    return response

  def CloseExecSocket(self, tid=None):
    """Send closing request to exec socket."""
    response = self._SendToExecSocketRaw('__kill__', tid)
    if response != '__kill_ack__':
      logging.warning('May not have succeeded in closing socket, make sure '
                      'using execsocks().')

  def InjectPdb(self):
    """Start pdb in the context of the helper thread."""
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = mod_base
#! /usr/bin/env python
#
# Copyright 2014 Google Inc.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Provides basic testing modes for the remote debugger."""


import abc


class DebuggingPlugin(object):
  """Superclass for all debugging plugins."""

  __metaclass__ = abc.ABCMeta

  def __init__(self, inferior, name):
    self.name = name
    self.position = None
    self.inferior = inferior
    super(DebuggingPlugin, self).__init__()

  @abc.abstractproperty
  def commands(self):
    return []


########NEW FILE########
__FILENAME__ = read_only
#! /usr/bin/env python
#
# Copyright 2014 Google Inc.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Read-only python thread inspection mode."""

import logging

import gdb_shell


class ReadonlyPlugin(gdb_shell.GdbPlugin):
  """Read-only inspection of inferior.

  This class doesn't do much more than wrap the functionality from within GDB
  and hide irrelevant implementation details.
  """

  def __init__(self, inferior, name='ro'):
    super(ReadonlyPlugin, self).__init__(inferior, name)

  @property
  def commands(self):
    return (super(ReadonlyPlugin, self).commands +
            [('bt', self.Backtrace),
             ('up', self.Up),
             ('down', self.Down),
             ('inflocals', self.InferiorLocals),
             ('infglobals', self.InferiorGlobals),
             ('infbuiltins', self.InferiorBuiltins),
             ('p', self.Lookup),
             ('threads', self.ListThreads),
             ('current_thread', self.SelectedThread),
             ('thread', self.SelectThread),
             ('c', self.Cancel),
             ('_cont', self.Continue),
             ('_interrupt', self.InterruptInferior),
             ('setsymbols', self.LoadSymbolFile),
            ])

  def Backtrace(self, to_string=False):
    """Get a backtrace of the current position."""
    if self.inferior.is_running:
      res = self.inferior.Backtrace()
      if to_string:
        return res
      print res
    else:
      logging.error('Not attached to any process.')

  def Up(self):
    """Move one frame up in the call stack."""
    return self.inferior.Up()

  def Down(self):
    """Move one frame down in the call stack."""
    return self.inferior.Down()

  def InferiorLocals(self):
    """Print the inferior's local identifiers in the current context."""
    return self.inferior.InferiorLocals()

  def InferiorGlobals(self):
    """Print the inferior's global identifiers in the current context."""
    return self.inferior.InferiorGlobals()

  def InferiorBuiltins(self):
    """Print the inferior's builtins in the current context."""
    return self.inferior.InferiorBuiltins()

  def Lookup(self, var_name):
    """Look up a value in the current context."""
    return self.inferior.Lookup(var_name)

  def ListThreads(self):
    """List the currently running python threads.

    Returns:
      A list of the inferior's thread idents, or None if the debugger is not
      attached to any process.
    """
    if self.inferior.is_running:
      return self.inferior.threads
    logging.error('Not attached to any process.')
    return []

  def SelectThread(self, tid):
    """Select a thread by ID."""
    return self.inferior.SelectThread(tid)

  def SelectedThread(self):
    """Returns the ID of the currently selected thread.

    Note that this has no correlation with the thread that the inferior is
    currently executing, but rather what the debugger considers to be the
    current command context.

    Returns:
      The ID of the currenly selected thread.
    """
    if self.inferior.is_running:
      return self.inferior.current_thread

  def Cancel(self):
    """Cancel a running command that has timeouted."""
    return self.inferior.Cancel()

  def Continue(self):
    """Continue execution of the inferior."""
    return self.inferior.Continue()

  def InterruptInferior(self):
    """Interrupt execution of the inferior."""
    return self.inferior.Interrupt()

  def LoadSymbolFile(self, path):
    """Attempt to load new symbol file from given path."""
    return self.inferior.LoadSymbolFile(path)

########NEW FILE########
__FILENAME__ = repl
#! /usr/bin/env python
#
# Copyright 2014 Google Inc.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Extensible remote python debugger.

Upon running, presents the user with an augmented python REPL able to load
plugins providing more advanced debugging capabilities.
"""

import code
import logging
import readline
import rlcompleter  # pylint: disable=unused-import
import sys
import inferior
from plugins import inject


# Optionally support colorama
try:
  import colorama  # pylint: disable=g-import-not-at-top
except ImportError:

  # mock the whole thing
  class EmptyStringStruct(object):

    def __getattr__(self, name):
      return ''

  class colorama(object):
    _mock = EmptyStringStruct()
    Fore = _mock
    Back = _mock
    Style = _mock

    @staticmethod
    def init():
      pass


_WELCOME_MSG = ('For a list of debugger commands, try "help()". '
                '(python\'s help is available as pyhelp.)')


class Error(Exception):
  """Base error class for this project."""
  pass


class DebuggingConsole(code.InteractiveConsole):
  """Provides a python REPL augmented with debugging capabilities.

  Attributes:
    commands: A dictionary containing the debugger's base commands.
    plugins: A list of currently loaded plugins
    inferior: The pid of the inferior process
  """

  def __init__(self):
    self.inferior = inferior.Inferior(None)
    self.commands = {'help': self.ListCommands,
                     'pyhelp': help,  # we shouldn't completely hide this
                     'attach': self.Attach,
                     'detach': self.Detach,
                     'setarch': self.SetArchitecture,
                     'setloglevel': self.SetLogLevel,
                     'loadplugin': self.LoadCommandPlugin,
                     'quit': self.Quit,
                    }
    self.plugins = [inject.InjectPlugin(self.inferior)]
    readline.parse_and_bind('tab: complete')
    colorama.init()

    locals_dir = dict([
        # This being a debugger, we trust the user knows what she's
        # doing when she messes with this key.
        ('__repl__', self),
        ('__doc__', __doc__),
        ('__name__', '__pyringe__')
    ])
    locals_dir.update(self.commands)
    code.InteractiveConsole.__init__(self)
    self.locals = locals_dir
    self.LoadCommandPlugin(inject.InjectPlugin(self.inferior))

  def LoadCommandPlugin(self, plugin):
    """Load a command plugin."""
    self.locals.update(plugin.commands)

  def ListCommands(self):
    """Print a list of currently available commands and their descriptions."""
    print 'Available commands:'
    commands = dict(self.commands)
    for plugin in self.plugins:
      commands.update(plugin.commands)
    for com in sorted(commands):
      if not com.startswith('_'):
        self.PrintHelpTextLine(com, commands[com])

  def PrintHelpTextLine(self, title, obj):
    if obj.__doc__:
      # only print the first line of the object's docstring
      docstring = obj.__doc__.splitlines()[0]
    else:
      docstring = 'No description available.'
    print ' %s%s%s: %s' % (colorama.Style.BRIGHT, title,
                           colorama.Style.RESET_ALL, docstring)

  def StatusLine(self):
    """Generate the colored line indicating plugin status."""
    pid = self.inferior.pid
    curthread = None
    threadnum = 0
    if pid:
      if not self.inferior.is_running:
        logging.warning('Inferior is not running.')
        self.Detach()
        pid = None
      else:
        try:
          # get a gdb running if it wasn't already.
          if not self.inferior.attached:
            self.inferior.StartGdb()
          curthread = self.inferior.current_thread
          threadnum = len(self.inferior.threads)
        except (inferior.ProxyError,
                inferior.TimeoutError,
                inferior.PositionError) as err:
          # This is not the kind of thing we want to be held up by
          logging.debug('Error while getting information in status line:%s'
                        % err.message)
          pass
    status = ('==> pid:[%s] #threads:[%s] current thread:[%s]' %
              (pid, threadnum, curthread))
    return status

  def Attach(self, pid):
    """Attach to the process with the given pid."""
    if self.inferior.is_running:
      answer = raw_input('Already attached to process ' +
                         str(self.inferior.pid) +
                         '. Detach? [y]/n ')
      if answer and answer != 'y' and answer != 'yes':
        return None
      self.Detach()
    # Whatever position we had before will not make any sense now
    for plugin in self.plugins:
      plugin.position = None
    self.inferior.Reinit(pid)

  def Detach(self):
    """Detach from the inferior (Will exit current mode)."""
    for plugin in self.plugins:
      plugin.position = None
    self.inferior.Reinit(None)

  def SetArchitecture(self, arch):
    """Set inferior target architecture

    This is directly forwarded to gdb via its command line, so
    possible values are defined by what the installed gdb supports.
    Only takes effect after gdb has been restarted.

    Args:
      arch: The target architecture to set gdb to.
    """
    self.inferior.arch = arch

  def SetLogLevel(self, level):
    """Set log level. Corresponds to levels from logging module."""
    # This is mostly here to jog people into enabling logging without
    # requiring them to have looked at the pyringe code.
    return logging.getLogger().setLevel(level)

  def runcode(self, co):
    try:
      exec co in self.locals  # pylint: disable=exec-used
    except SystemExit:
      self.inferior.Cancel()
      raise
    except KeyboardInterrupt:
      raise
    except inferior.PositionError as err:
      print 'PositionError: %s' % err.message
    except:
      self.showtraceback()
    else:
      if code.softspace(sys.stdout, 0):
        print

  def Quit(self):
    """Raises SystemExit, thereby quitting the debugger."""
    raise SystemExit

  def interact(self, banner=None):
    """Closely emulate the interactive Python console.

    This method overwrites its superclass' method to specify a different help
    text and to enable proper handling of the debugger status line.

    Args:
      banner: Text to be displayed on interpreter startup.
    """
    sys.ps1 = getattr(sys, 'ps1', '>>> ')
    sys.ps2 = getattr(sys, 'ps2', '... ')
    if banner is None:
      print ('Pyringe (Python %s.%s.%s) on %s\n%s' %
             (sys.version_info.major, sys.version_info.minor,
              sys.version_info.micro, sys.platform, _WELCOME_MSG))
    else:
      print banner
    more = False
    while True:
      try:
        if more:
          prompt = sys.ps2
        else:
          prompt = self.StatusLine() + '\n' + sys.ps1
        try:
          line = self.raw_input(prompt)
        except EOFError:
          print ''
          break
        else:
          more = self.push(line)
      except KeyboardInterrupt:
        print '\nKeyboardInterrupt'
        self.resetbuffer()
        more = False



########NEW FILE########
__FILENAME__ = __main__
#! /usr/bin/env python
#
# Copyright 2014 Google Inc.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pyringe

pyringe.interact()

########NEW FILE########
