__FILENAME__ = common
# -*- coding: utf-8 -*-
"""
This module contains utilities added by billiard, to keep
"non-core" functionality out of ``.util``."""
from __future__ import absolute_import

import os
import signal
import sys

import pickle as pypickle
try:
    import cPickle as cpickle
except ImportError:  # pragma: no cover
    cpickle = None   # noqa

from .exceptions import RestartFreqExceeded
from .five import monotonic

if sys.version_info < (2, 6):  # pragma: no cover
    # cPickle does not use absolute_imports
    pickle = pypickle
    pickle_load = pypickle.load
    pickle_loads = pypickle.loads
else:
    pickle = cpickle or pypickle
    pickle_load = pickle.load
    pickle_loads = pickle.loads

# cPickle.loads does not support buffer() objects,
# but we can just create a StringIO and use load.
if sys.version_info[0] == 3:
    from io import BytesIO
else:
    try:
        from cStringIO import StringIO as BytesIO  # noqa
    except ImportError:
        from StringIO import StringIO as BytesIO  # noqa

EX_SOFTWARE = 70

TERMSIGS_DEFAULT = (
    'SIGHUP',
    'SIGQUIT',
    'SIGTERM',
    'SIGUSR1',
    'SIGUSR2'
)

TERMSIGS_FULL = (
    'SIGHUP',
    'SIGQUIT',
    'SIGTRAP',
    'SIGABRT',
    'SIGEMT',
    'SIGSYS',
    'SIGPIPE',
    'SIGALRM',
    'SIGTERM',
    'SIGXCPU',
    'SIGXFSZ',
    'SIGVTALRM',
    'SIGPROF',
    'SIGUSR1',
    'SIGUSR2',
)

#: set by signal handlers just before calling exit.
#: if this is true after the sighandler returns it means that something
#: went wrong while terminating the process, and :func:`os._exit`
#: must be called ASAP.
_should_have_exited = [False]


def pickle_loads(s, load=pickle_load):
    # used to support buffer objects
    return load(BytesIO(s))


def maybe_setsignal(signum, handler):
    try:
        signal.signal(signum, handler)
    except (OSError, AttributeError, ValueError, RuntimeError):
        pass


def _shutdown_cleanup(signum, frame):
    # we will exit here so if the signal is received a second time
    # we can be sure that something is very wrong and we may be in
    # a crashing loop.
    if _should_have_exited[0]:
        os._exit(EX_SOFTWARE)
    maybe_setsignal(signum, signal.SIG_DFL)
    _should_have_exited[0] = True
    sys.exit(-(256 - signum))


def reset_signals(handler=_shutdown_cleanup, full=False):
    for sig in TERMSIGS_FULL if full else TERMSIGS_DEFAULT:
        try:
            signum = getattr(signal, sig)
        except AttributeError:
            pass
        else:
            current = signal.getsignal(signum)
            if current is not None and current != signal.SIG_IGN:
                maybe_setsignal(signum, handler)


class restart_state(object):
    RestartFreqExceeded = RestartFreqExceeded

    def __init__(self, maxR, maxT):
        self.maxR, self.maxT = maxR, maxT
        self.R, self.T = 0, None

    def step(self, now=None):
        now = monotonic() if now is None else now
        R = self.R
        if self.T and now - self.T >= self.maxT:
            # maxT passed, reset counter and time passed.
            self.T, self.R = now, 0
        elif self.maxR and self.R >= self.maxR:
            # verify that R has a value as the result handler
            # resets this when a job is accepted. If a job is accepted
            # the startup probably went fine (startup restart burst
            # protection)
            if self.R:  # pragma: no cover
                self.R = 0  # reset in case someone catches the error
                raise self.RestartFreqExceeded("%r in %rs" % (R, self.maxT))
        # first run sets T
        if self.T is None:
            self.T = now
        self.R += 1

########NEW FILE########
__FILENAME__ = compat
from __future__ import absolute_import

import errno
import os
import sys

from .five import range

if sys.platform == 'win32':
    try:
        import _winapi  # noqa
    except ImportError:                            # pragma: no cover
        try:
            from _billiard import win32 as _winapi  # noqa
        except (ImportError, AttributeError):
            from _multiprocessing import win32 as _winapi  # noqa
else:
    _winapi = None  # noqa


if sys.version_info > (2, 7, 5):
    buf_t, is_new_buffer = memoryview, True  # noqa
else:
    buf_t, is_new_buffer = buffer, False  # noqa

if hasattr(os, 'write'):
    __write__ = os.write

    if is_new_buffer:

        def send_offset(fd, buf, offset):
            return __write__(fd, buf[offset:])

    else:  # Py<2.7.6

        def send_offset(fd, buf, offset):  # noqa
            return __write__(fd, buf_t(buf, offset))

else:  # non-posix platform

    def send_offset(fd, buf, offset):  # noqa
        raise NotImplementedError('send_offset')


if sys.version_info[0] == 3:
    bytes = bytes
else:
    _bytes = bytes

    # the 'bytes' alias in Python2 does not support an encoding argument.

    class bytes(_bytes):  # noqa

        def __new__(cls, *args):
            if len(args) > 1:
                return _bytes(args[0]).encode(*args[1:])
            return _bytes(*args)

try:
    closerange = os.closerange
except AttributeError:

    def closerange(fd_low, fd_high):  # noqa
        for fd in reversed(range(fd_low, fd_high)):
            try:
                os.close(fd)
            except OSError as exc:
                if exc.errno != errno.EBADF:
                    raise


def get_errno(exc):
    """:exc:`socket.error` and :exc:`IOError` first got
    the ``.errno`` attribute in Py2.7"""
    try:
        return exc.errno
    except AttributeError:
        try:
            # e.args = (errno, reason)
            if isinstance(exc.args, tuple) and len(exc.args) == 2:
                return exc.args[0]
        except AttributeError:
            pass
    return 0


if sys.platform == 'win32':

    def setblocking(handle, blocking):
        raise NotImplementedError('setblocking not implemented on win32')

    def isblocking(handle):
        raise NotImplementedError('isblocking not implemented on win32')

else:
    from os import O_NONBLOCK
    from fcntl import fcntl, F_GETFL, F_SETFL

    def isblocking(handle):  # noqa
        return not (fcntl(handle, F_GETFL) & O_NONBLOCK)

    def setblocking(handle, blocking):  # noqa
        flags = fcntl(handle, F_GETFL, 0)
        fcntl(
            handle, F_SETFL,
            flags & (~O_NONBLOCK) if blocking else flags | O_NONBLOCK,
        )

########NEW FILE########
__FILENAME__ = connection
from __future__ import absolute_import

import sys

is_pypy = hasattr(sys, 'pypy_version_info')

if sys.version_info[0] == 3:
    from .py3 import connection
else:
    from .py2 import connection  # noqa


if is_pypy:
    import _multiprocessing
    from .compat import setblocking, send_offset

    class Connection(_multiprocessing.Connection):

        def send_offset(self, buf, offset):
            return send_offset(self.fileno(), buf, offset)

        def setblocking(self, blocking):
            setblocking(self.fileno(), blocking)
    _multiprocessing.Connection = Connection


sys.modules[__name__] = connection

########NEW FILE########
__FILENAME__ = connection
#
# Analogue of `multiprocessing.connection` which uses queues instead of sockets
#
# multiprocessing/dummy/connection.py
#
# Copyright (c) 2006-2008, R Oudkerk
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of author nor the names of any contributors may be
#    used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
from __future__ import absolute_import

__all__ = ['Client', 'Listener', 'Pipe']

from billiard.five import Queue


families = [None]


class Listener(object):

    def __init__(self, address=None, family=None, backlog=1):
        self._backlog_queue = Queue(backlog)

    def accept(self):
        return Connection(*self._backlog_queue.get())

    def close(self):
        self._backlog_queue = None

    address = property(lambda self: self._backlog_queue)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


def Client(address):
    _in, _out = Queue(), Queue()
    address.put((_out, _in))
    return Connection(_in, _out)


def Pipe(duplex=True):
    a, b = Queue(), Queue()
    return Connection(a, b), Connection(b, a)


class Connection(object):

    def __init__(self, _in, _out):
        self._out = _out
        self._in = _in
        self.send = self.send_bytes = _out.put
        self.recv = self.recv_bytes = _in.get

    def poll(self, timeout=0.0):
        if self._in.qsize() > 0:
            return True
        if timeout <= 0.0:
            return False
        self._in.not_empty.acquire()
        self._in.not_empty.wait(timeout)
        self._in.not_empty.release()
        return self._in.qsize() > 0

    def close(self):
        pass

########NEW FILE########
__FILENAME__ = einfo
from __future__ import absolute_import

import sys
import traceback


class _Code(object):

    def __init__(self, code):
        self.co_filename = code.co_filename
        self.co_name = code.co_name


class _Frame(object):
    Code = _Code

    def __init__(self, frame):
        self.f_globals = {
            "__file__": frame.f_globals.get("__file__", "__main__"),
            "__name__": frame.f_globals.get("__name__"),
            "__loader__": None,
        }
        self.f_locals = fl = {}
        try:
            fl["__traceback_hide__"] = frame.f_locals["__traceback_hide__"]
        except KeyError:
            pass
        self.f_code = self.Code(frame.f_code)
        self.f_lineno = frame.f_lineno


class _Object(object):

    def __init__(self, **kw):
        [setattr(self, k, v) for k, v in kw.items()]


class _Truncated(object):

    def __init__(self):
        self.tb_lineno = -1
        self.tb_frame = _Object(
            f_globals={"__file__": "",
                       "__name__": "",
                       "__loader__": None},
            f_fileno=None,
            f_code=_Object(co_filename="...",
                           co_name="[rest of traceback truncated]"),
        )
        self.tb_next = None


class Traceback(object):
    Frame = _Frame

    tb_frame = tb_lineno = tb_next = None
    max_frames = sys.getrecursionlimit() // 8

    def __init__(self, tb, max_frames=None, depth=0):
        limit = self.max_frames = max_frames or self.max_frames
        self.tb_frame = self.Frame(tb.tb_frame)
        self.tb_lineno = tb.tb_lineno
        if tb.tb_next is not None:
            if depth <= limit:
                self.tb_next = Traceback(tb.tb_next, limit, depth + 1)
            else:
                self.tb_next = _Truncated()


class ExceptionInfo(object):
    """Exception wrapping an exception and its traceback.

    :param exc_info: The exception info tuple as returned by
        :func:`sys.exc_info`.

    """

    #: Exception type.
    type = None

    #: Exception instance.
    exception = None

    #: Pickleable traceback instance for use with :mod:`traceback`
    tb = None

    #: String representation of the traceback.
    traceback = None

    #: Set to true if this is an internal error.
    internal = False

    def __init__(self, exc_info=None, internal=False):
        self.type, self.exception, tb = exc_info or sys.exc_info()
        try:
            self.tb = Traceback(tb)
            self.traceback = ''.join(
                traceback.format_exception(self.type, self.exception, tb),
            )
            self.internal = internal
        finally:
            del(tb)

    def __str__(self):
        return self.traceback

    def __repr__(self):
        return "<ExceptionInfo: %r>" % (self.exception, )

    @property
    def exc_info(self):
        return self.type, self.exception, self.tb

########NEW FILE########
__FILENAME__ = exceptions
from __future__ import absolute_import

try:
    from multiprocessing import (
        ProcessError,
        BufferTooShort,
        TimeoutError,
        AuthenticationError,
    )
except ImportError:
    class ProcessError(Exception):          # noqa
        pass

    class BufferTooShort(Exception):        # noqa
        pass

    class TimeoutError(Exception):          # noqa
        pass

    class AuthenticationError(Exception):   # noqa
        pass


class TimeLimitExceeded(Exception):
    """The time limit has been exceeded and the job has been terminated."""

    def __str__(self):
        return "TimeLimitExceeded%s" % (self.args, )


class SoftTimeLimitExceeded(Exception):
    """The soft time limit has been exceeded. This exception is raised
    to give the task a chance to clean up."""

    def __str__(self):
        return "SoftTimeLimitExceeded%s" % (self.args, )


class WorkerLostError(Exception):
    """The worker processing a job has exited prematurely."""


class Terminated(Exception):
    """The worker processing a job has been terminated by user request."""


class RestartFreqExceeded(Exception):
    """Restarts too fast."""


class CoroStop(Exception):
    """Coroutine exit, as opposed to StopIteration which may
    mean it should be restarted."""
    pass

########NEW FILE########
__FILENAME__ = five
# -*- coding: utf-8 -*-
"""
    celery.five
    ~~~~~~~~~~~

    Compatibility implementations of features
    only available in newer Python versions.


"""
from __future__ import absolute_import

# ############# py3k #########################################################
import sys
PY3 = sys.version_info[0] == 3

try:
    reload = reload                         # noqa
except NameError:                           # pragma: no cover
    from imp import reload                  # noqa

try:
    from UserList import UserList           # noqa
except ImportError:                         # pragma: no cover
    from collections import UserList        # noqa

try:
    from UserDict import UserDict           # noqa
except ImportError:                         # pragma: no cover
    from collections import UserDict        # noqa

# ############# time.monotonic ###############################################

if sys.version_info < (3, 3):

    import platform
    SYSTEM = platform.system()

    if SYSTEM == 'Darwin':
        import ctypes
        from ctypes.util import find_library
        libSystem = ctypes.CDLL('libSystem.dylib')
        CoreServices = ctypes.CDLL(find_library('CoreServices'),
                                   use_errno=True)
        mach_absolute_time = libSystem.mach_absolute_time
        mach_absolute_time.restype = ctypes.c_uint64
        absolute_to_nanoseconds = CoreServices.AbsoluteToNanoseconds
        absolute_to_nanoseconds.restype = ctypes.c_uint64
        absolute_to_nanoseconds.argtypes = [ctypes.c_uint64]

        def _monotonic():
            return absolute_to_nanoseconds(mach_absolute_time()) * 1e-9

    elif SYSTEM == 'Linux':
        # from stackoverflow:
        # questions/1205722/how-do-i-get-monotonic-time-durations-in-python
        import ctypes
        import os

        CLOCK_MONOTONIC = 1  # see <linux/time.h>

        class timespec(ctypes.Structure):
            _fields_ = [
                ('tv_sec', ctypes.c_long),
                ('tv_nsec', ctypes.c_long),
            ]

        librt = ctypes.CDLL('librt.so.1', use_errno=True)
        clock_gettime = librt.clock_gettime
        clock_gettime.argtypes = [
            ctypes.c_int, ctypes.POINTER(timespec),
        ]

        def _monotonic():  # noqa
            t = timespec()
            if clock_gettime(CLOCK_MONOTONIC, ctypes.pointer(t)) != 0:
                errno_ = ctypes.get_errno()
                raise OSError(errno_, os.strerror(errno_))
            return t.tv_sec + t.tv_nsec * 1e-9
    else:
        from time import time as _monotonic

try:
    from time import monotonic
except ImportError:
    monotonic = _monotonic  # noqa

if PY3:
    import builtins

    from queue import Queue, Empty, Full
    from itertools import zip_longest
    from io import StringIO, BytesIO

    map = map
    string = str
    string_t = str
    long_t = int
    text_t = str
    range = range
    int_types = (int, )

    open_fqdn = 'builtins.open'

    def items(d):
        return d.items()

    def keys(d):
        return d.keys()

    def values(d):
        return d.values()

    def nextfun(it):
        return it.__next__

    exec_ = getattr(builtins, 'exec')

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    class WhateverIO(StringIO):

        def write(self, data):
            if isinstance(data, bytes):
                data = data.encode()
            StringIO.write(self, data)

else:
    import __builtin__ as builtins  # noqa
    from Queue import Queue, Empty, Full  # noqa
    from itertools import imap as map, izip_longest as zip_longest  # noqa
    from StringIO import StringIO   # noqa
    string = unicode                # noqa
    string_t = basestring           # noqa
    text_t = unicode
    long_t = long                   # noqa
    range = xrange
    int_types = (int, long)

    open_fqdn = '__builtin__.open'

    def items(d):                   # noqa
        return d.iteritems()

    def keys(d):                    # noqa
        return d.iterkeys()

    def values(d):                  # noqa
        return d.itervalues()

    def nextfun(it):                # noqa
        return it.next

    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")

    exec_("""def reraise(tp, value, tb=None): raise tp, value, tb""")

    BytesIO = WhateverIO = StringIO         # noqa


def with_metaclass(Type, skip_attrs=set(['__dict__', '__weakref__'])):
    """Class decorator to set metaclass.

    Works with both Python 3 and Python 3 and it does not add
    an extra class in the lookup order like ``six.with_metaclass`` does
    (that is -- it copies the original class instead of using inheritance).

    """

    def _clone_with_metaclass(Class):
        attrs = dict((key, value) for key, value in items(vars(Class))
                     if key not in skip_attrs)
        return Type(Class.__name__, Class.__bases__, attrs)

    return _clone_with_metaclass

########NEW FILE########
__FILENAME__ = forking
#
# Module for starting a process object using os.fork() or CreateProcess()
#
# multiprocessing/forking.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#

from __future__ import absolute_import

import os
import sys
import signal
import warnings

from pickle import load, HIGHEST_PROTOCOL
from billiard import util
from billiard import process
from billiard.five import int_types
from .reduction import dump
from .compat import _winapi as win32

__all__ = ['Popen', 'assert_spawning', 'exit',
           'duplicate', 'close']

try:
    WindowsError = WindowsError  # noqa
except NameError:
    class WindowsError(Exception):  # noqa
        pass

W_OLD_DJANGO_LAYOUT = """\
Will add directory %r to path! This is necessary to accommodate \
pre-Django 1.4 layouts using setup_environ.
You can skip this warning by adding a DJANGO_SETTINGS_MODULE=settings \
environment variable.
"""

#
# Choose whether to do a fork or spawn (fork+exec) on Unix.
# This affects how some shared resources should be created.
#

_forking_is_enabled = sys.platform != 'win32'

#
# Check that the current thread is spawning a child process
#


def assert_spawning(self):
    if not Popen.thread_is_spawning():
        raise RuntimeError(
            '%s objects should only be shared between processes'
            ' through inheritance' % type(self).__name__
        )


#
# Unix
#

if sys.platform != 'win32':
    try:
        import thread
    except ImportError:
        import _thread as thread  # noqa
    import select

    WINEXE = False
    WINSERVICE = False

    exit = os._exit
    duplicate = os.dup
    close = os.close
    _select = util._eintr_retry(select.select)

    #
    # We define a Popen class similar to the one from subprocess, but
    # whose constructor takes a process object as its argument.
    #

    class Popen(object):

        _tls = thread._local()

        def __init__(self, process_obj):
            # register reducers
            from billiard import connection  # noqa
            _Django_old_layout_hack__save()
            sys.stdout.flush()
            sys.stderr.flush()
            self.returncode = None
            r, w = os.pipe()
            self.sentinel = r

            if _forking_is_enabled:
                self.pid = os.fork()
                if self.pid == 0:
                    os.close(r)
                    if 'random' in sys.modules:
                        import random
                        random.seed()
                    code = process_obj._bootstrap()
                    os._exit(code)
            else:
                from_parent_fd, to_child_fd = os.pipe()
                cmd = get_command_line() + [str(from_parent_fd)]

                self.pid = os.fork()
                if self.pid == 0:
                    os.close(r)
                    os.close(to_child_fd)
                    os.execv(sys.executable, cmd)

                # send information to child
                prep_data = get_preparation_data(process_obj._name)
                os.close(from_parent_fd)
                to_child = os.fdopen(to_child_fd, 'wb')
                Popen._tls.process_handle = self.pid
                try:
                    dump(prep_data, to_child, HIGHEST_PROTOCOL)
                    dump(process_obj, to_child, HIGHEST_PROTOCOL)
                finally:
                    del(Popen._tls.process_handle)
                    to_child.close()

            # `w` will be closed when the child exits, at which point `r`
            # will become ready for reading (using e.g. select()).
            os.close(w)
            util.Finalize(self, os.close, (r,))

        def poll(self, flag=os.WNOHANG):
            if self.returncode is None:
                try:
                    pid, sts = os.waitpid(self.pid, flag)
                except os.error:
                    # Child process not yet created. See #1731717
                    # e.errno == errno.ECHILD == 10
                    return None
                if pid == self.pid:
                    if os.WIFSIGNALED(sts):
                        self.returncode = -os.WTERMSIG(sts)
                    else:
                        assert os.WIFEXITED(sts)
                        self.returncode = os.WEXITSTATUS(sts)
            return self.returncode

        def wait(self, timeout=None):
            if self.returncode is None:
                if timeout is not None:
                    r = _select([self.sentinel], [], [], timeout)[0]
                    if not r:
                        return None
                # This shouldn't block if select() returned successfully.
                return self.poll(os.WNOHANG if timeout == 0.0 else 0)
            return self.returncode

        def terminate(self):
            if self.returncode is None:
                try:
                    os.kill(self.pid, signal.SIGTERM)
                except OSError:
                    if self.wait(timeout=0.1) is None:
                        raise

        @staticmethod
        def thread_is_spawning():
            if _forking_is_enabled:
                return False
            else:
                return getattr(Popen._tls, 'process_handle', None) is not None

        @staticmethod
        def duplicate_for_child(handle):
            return handle

#
# Windows
#

else:
    try:
        import thread
    except ImportError:
        import _thread as thread  # noqa
    import msvcrt
    try:
        import _subprocess
    except ImportError:
        import _winapi as _subprocess  # noqa

    #
    #
    #

    TERMINATE = 0x10000
    WINEXE = (sys.platform == 'win32' and getattr(sys, 'frozen', False))
    WINSERVICE = sys.executable.lower().endswith("pythonservice.exe")

    exit = win32.ExitProcess
    close = win32.CloseHandle

    #
    #
    #

    def duplicate(handle, target_process=None, inheritable=False):
        if target_process is None:
            target_process = _subprocess.GetCurrentProcess()
        h = _subprocess.DuplicateHandle(
            _subprocess.GetCurrentProcess(), handle, target_process,
            0, inheritable, _subprocess.DUPLICATE_SAME_ACCESS
        )
        if sys.version_info[0] < 3 or (
                sys.version_info[0] == 3 and sys.version_info[1] < 3):
            h = h.Detach()
        return h

    #
    # We define a Popen class similar to the one from subprocess, but
    # whose constructor takes a process object as its argument.
    #

    class Popen(object):
        '''
        Start a subprocess to run the code of a process object
        '''
        _tls = thread._local()

        def __init__(self, process_obj):
            _Django_old_layout_hack__save()
            # create pipe for communication with child
            rfd, wfd = os.pipe()

            # get handle for read end of the pipe and make it inheritable
            rhandle = duplicate(msvcrt.get_osfhandle(rfd), inheritable=True)
            os.close(rfd)

            # start process
            cmd = get_command_line() + [rhandle]
            cmd = ' '.join('"%s"' % x for x in cmd)
            hp, ht, pid, tid = _subprocess.CreateProcess(
                _python_exe, cmd, None, None, 1, 0, None, None, None
            )
            close(ht) if isinstance(ht, int_types) else ht.Close()
            (close(rhandle) if isinstance(rhandle, int_types)
             else rhandle.Close())

            # set attributes of self
            self.pid = pid
            self.returncode = None
            self._handle = hp
            self.sentinel = int(hp)

            # send information to child
            prep_data = get_preparation_data(process_obj._name)
            to_child = os.fdopen(wfd, 'wb')
            Popen._tls.process_handle = int(hp)
            try:
                dump(prep_data, to_child, HIGHEST_PROTOCOL)
                dump(process_obj, to_child, HIGHEST_PROTOCOL)
            finally:
                del Popen._tls.process_handle
                to_child.close()

        @staticmethod
        def thread_is_spawning():
            return getattr(Popen._tls, 'process_handle', None) is not None

        @staticmethod
        def duplicate_for_child(handle):
            return duplicate(handle, Popen._tls.process_handle)

        def wait(self, timeout=None):
            if self.returncode is None:
                if timeout is None:
                    msecs = _subprocess.INFINITE
                else:
                    msecs = max(0, int(timeout * 1000 + 0.5))

                res = _subprocess.WaitForSingleObject(int(self._handle), msecs)
                if res == _subprocess.WAIT_OBJECT_0:
                    code = _subprocess.GetExitCodeProcess(self._handle)
                    if code == TERMINATE:
                        code = -signal.SIGTERM
                    self.returncode = code

            return self.returncode

        def poll(self):
            return self.wait(timeout=0)

        def terminate(self):
            if self.returncode is None:
                try:
                    _subprocess.TerminateProcess(int(self._handle), TERMINATE)
                except WindowsError:
                    if self.wait(timeout=0.1) is None:
                        raise

    #
    #
    #

if WINSERVICE:
    _python_exe = os.path.join(sys.exec_prefix, 'python.exe')
else:
    _python_exe = sys.executable


def set_executable(exe):
    global _python_exe
    _python_exe = exe


def is_forking(argv):
    '''
    Return whether commandline indicates we are forking
    '''
    if len(argv) >= 2 and argv[1] == '--billiard-fork':
        assert len(argv) == 3
        os.environ["FORKED_BY_MULTIPROCESSING"] = "1"
        return True
    else:
        return False


def freeze_support():
    '''
    Run code for process object if this in not the main process
    '''
    if is_forking(sys.argv):
        main()
        sys.exit()


def get_command_line():
    '''
    Returns prefix of command line used for spawning a child process
    '''
    if process.current_process()._identity == () and is_forking(sys.argv):
        raise RuntimeError('''
        Attempt to start a new process before the current process
        has finished its bootstrapping phase.

        This probably means that have forgotten to use the proper
        idiom in the main module:

            if __name__ == '__main__':
                freeze_support()
                ...

        The "freeze_support()" line can be omitted if the program
        is not going to be frozen to produce a Windows executable.''')

    if getattr(sys, 'frozen', False):
        return [sys.executable, '--billiard-fork']
    else:
        prog = 'from billiard.forking import main; main()'
        return [_python_exe, '-c', prog, '--billiard-fork']


def _Django_old_layout_hack__save():
    if 'DJANGO_PROJECT_DIR' not in os.environ:
        try:
            settings_name = os.environ['DJANGO_SETTINGS_MODULE']
        except KeyError:
            return  # not using Django.

        conf_settings = sys.modules.get('django.conf.settings')
        configured = conf_settings and conf_settings.configured
        try:
            project_name, _ = settings_name.split('.', 1)
        except ValueError:
            return  # not modified by setup_environ

        project = __import__(project_name)
        try:
            project_dir = os.path.normpath(_module_parent_dir(project))
        except AttributeError:
            return  # dynamically generated module (no __file__)
        if configured:
            warnings.warn(UserWarning(
                W_OLD_DJANGO_LAYOUT % os.path.realpath(project_dir)
            ))
        os.environ['DJANGO_PROJECT_DIR'] = project_dir


def _Django_old_layout_hack__load():
    try:
        sys.path.append(os.environ['DJANGO_PROJECT_DIR'])
    except KeyError:
        pass


def _module_parent_dir(mod):
    dir, filename = os.path.split(_module_dir(mod))
    if dir == os.curdir or not dir:
        dir = os.getcwd()
    return dir


def _module_dir(mod):
    if '__init__.py' in mod.__file__:
        return os.path.dirname(mod.__file__)
    return mod.__file__


def main():
    '''
    Run code specifed by data received over pipe
    '''
    global _forking_is_enabled
    _Django_old_layout_hack__load()

    assert is_forking(sys.argv)
    _forking_is_enabled = False

    handle = int(sys.argv[-1])
    if sys.platform == 'win32':
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY)
    else:
        fd = handle
    from_parent = os.fdopen(fd, 'rb')

    process.current_process()._inheriting = True
    preparation_data = load(from_parent)
    prepare(preparation_data)
    # Huge hack to make logging before Process.run work.
    try:
        os.environ["MP_MAIN_FILE"] = sys.modules["__main__"].__file__
    except KeyError:
        pass
    except AttributeError:
        pass
    loglevel = os.environ.get("_MP_FORK_LOGLEVEL_")
    logfile = os.environ.get("_MP_FORK_LOGFILE_") or None
    format = os.environ.get("_MP_FORK_LOGFORMAT_")
    if loglevel:
        from billiard import util
        import logging
        logger = util.get_logger()
        logger.setLevel(int(loglevel))
        if not logger.handlers:
            logger._rudimentary_setup = True
            logfile = logfile or sys.__stderr__
            if hasattr(logfile, "write"):
                handler = logging.StreamHandler(logfile)
            else:
                handler = logging.FileHandler(logfile)
            formatter = logging.Formatter(
                format or util.DEFAULT_LOGGING_FORMAT,
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    self = load(from_parent)
    process.current_process()._inheriting = False

    from_parent.close()

    exitcode = self._bootstrap()
    exit(exitcode)


def get_preparation_data(name):
    '''
    Return info about parent needed by child to unpickle process object
    '''
    from billiard.util import _logger, _log_to_stderr

    d = dict(
        name=name,
        sys_path=sys.path,
        sys_argv=sys.argv,
        log_to_stderr=_log_to_stderr,
        orig_dir=process.ORIGINAL_DIR,
        authkey=process.current_process().authkey,
    )

    if _logger is not None:
        d['log_level'] = _logger.getEffectiveLevel()

    if not WINEXE and not WINSERVICE:
        main_path = getattr(sys.modules['__main__'], '__file__', None)
        if not main_path and sys.argv[0] not in ('', '-c'):
            main_path = sys.argv[0]
        if main_path is not None:
            if (not os.path.isabs(main_path) and
                    process.ORIGINAL_DIR is not None):
                main_path = os.path.join(process.ORIGINAL_DIR, main_path)
            d['main_path'] = os.path.normpath(main_path)

    return d

#
# Prepare current process
#

old_main_modules = []


def prepare(data):
    '''
    Try to get current process ready to unpickle process object
    '''
    old_main_modules.append(sys.modules['__main__'])

    if 'name' in data:
        process.current_process().name = data['name']

    if 'authkey' in data:
        process.current_process()._authkey = data['authkey']

    if 'log_to_stderr' in data and data['log_to_stderr']:
        util.log_to_stderr()

    if 'log_level' in data:
        util.get_logger().setLevel(data['log_level'])

    if 'sys_path' in data:
        sys.path = data['sys_path']

    if 'sys_argv' in data:
        sys.argv = data['sys_argv']

    if 'dir' in data:
        os.chdir(data['dir'])

    if 'orig_dir' in data:
        process.ORIGINAL_DIR = data['orig_dir']

    if 'main_path' in data:
        main_path = data['main_path']
        main_name = os.path.splitext(os.path.basename(main_path))[0]
        if main_name == '__init__':
            main_name = os.path.basename(os.path.dirname(main_path))

        if main_name == '__main__':
            main_module = sys.modules['__main__']
            main_module.__file__ = main_path
        elif main_name != 'ipython':
            # Main modules not actually called __main__.py may
            # contain additional code that should still be executed
            import imp

            if main_path is None:
                dirs = None
            elif os.path.basename(main_path).startswith('__init__.py'):
                dirs = [os.path.dirname(os.path.dirname(main_path))]
            else:
                dirs = [os.path.dirname(main_path)]

            assert main_name not in sys.modules, main_name
            file, path_name, etc = imp.find_module(main_name, dirs)
            try:
                # We would like to do "imp.load_module('__main__', ...)"
                # here.  However, that would cause 'if __name__ ==
                # "__main__"' clauses to be executed.
                main_module = imp.load_module(
                    '__parents_main__', file, path_name, etc
                )
            finally:
                if file:
                    file.close()

            sys.modules['__main__'] = main_module
            main_module.__name__ = '__main__'

            # Try to make the potentially picklable objects in
            # sys.modules['__main__'] realize they are in the main
            # module -- somewhat ugly.
            for obj in list(main_module.__dict__.values()):
                try:
                    if obj.__module__ == '__parents_main__':
                        obj.__module__ = '__main__'
                except Exception:
                    pass

########NEW FILE########
__FILENAME__ = heap
#
# Module which supports allocation of memory from an mmap
#
# multiprocessing/heap.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#
from __future__ import absolute_import

import bisect
import mmap
import os
import sys
import threading
import itertools

from ._ext import _billiard, win32
from .util import Finalize, info, get_temp_dir
from .forking import assert_spawning
from .reduction import ForkingPickler

__all__ = ['BufferWrapper']

try:
    maxsize = sys.maxsize
except AttributeError:
    maxsize = sys.maxint

#
# Inheirtable class which wraps an mmap, and from which blocks can be allocated
#

if sys.platform == 'win32':

    class Arena(object):

        _counter = itertools.count()

        def __init__(self, size):
            self.size = size
            self.name = 'pym-%d-%d' % (os.getpid(), next(Arena._counter))
            self.buffer = mmap.mmap(-1, self.size, tagname=self.name)
            assert win32.GetLastError() == 0, 'tagname already in use'
            self._state = (self.size, self.name)

        def __getstate__(self):
            assert_spawning(self)
            return self._state

        def __setstate__(self, state):
            self.size, self.name = self._state = state
            self.buffer = mmap.mmap(-1, self.size, tagname=self.name)
            assert win32.GetLastError() == win32.ERROR_ALREADY_EXISTS

else:

    class Arena(object):

        _counter = itertools.count()

        def __init__(self, size, fileno=-1):
            from .forking import _forking_is_enabled
            self.size = size
            self.fileno = fileno
            if fileno == -1 and not _forking_is_enabled:
                name = os.path.join(
                    get_temp_dir(),
                    'pym-%d-%d' % (os.getpid(), next(self._counter)))
                self.fileno = os.open(
                    name, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
                os.unlink(name)
                os.ftruncate(self.fileno, size)
            self.buffer = mmap.mmap(self.fileno, self.size)

    def reduce_arena(a):
        if a.fileno == -1:
            raise ValueError('Arena is unpicklable because'
                             'forking was enabled when it was created')
        return Arena, (a.size, a.fileno)

    ForkingPickler.register(Arena, reduce_arena)

#
# Class allowing allocation of chunks of memory from arenas
#


class Heap(object):

    _alignment = 8

    def __init__(self, size=mmap.PAGESIZE):
        self._lastpid = os.getpid()
        self._lock = threading.Lock()
        self._size = size
        self._lengths = []
        self._len_to_seq = {}
        self._start_to_block = {}
        self._stop_to_block = {}
        self._allocated_blocks = set()
        self._arenas = []
        # list of pending blocks to free - see free() comment below
        self._pending_free_blocks = []

    @staticmethod
    def _roundup(n, alignment):
        # alignment must be a power of 2
        mask = alignment - 1
        return (n + mask) & ~mask

    def _malloc(self, size):
        # returns a large enough block -- it might be much larger
        i = bisect.bisect_left(self._lengths, size)
        if i == len(self._lengths):
            length = self._roundup(max(self._size, size), mmap.PAGESIZE)
            self._size *= 2
            info('allocating a new mmap of length %d', length)
            arena = Arena(length)
            self._arenas.append(arena)
            return (arena, 0, length)
        else:
            length = self._lengths[i]
            seq = self._len_to_seq[length]
            block = seq.pop()
            if not seq:
                del self._len_to_seq[length], self._lengths[i]

        (arena, start, stop) = block
        del self._start_to_block[(arena, start)]
        del self._stop_to_block[(arena, stop)]
        return block

    def _free(self, block):
        # free location and try to merge with neighbours
        (arena, start, stop) = block

        try:
            prev_block = self._stop_to_block[(arena, start)]
        except KeyError:
            pass
        else:
            start, _ = self._absorb(prev_block)

        try:
            next_block = self._start_to_block[(arena, stop)]
        except KeyError:
            pass
        else:
            _, stop = self._absorb(next_block)

        block = (arena, start, stop)
        length = stop - start

        try:
            self._len_to_seq[length].append(block)
        except KeyError:
            self._len_to_seq[length] = [block]
            bisect.insort(self._lengths, length)

        self._start_to_block[(arena, start)] = block
        self._stop_to_block[(arena, stop)] = block

    def _absorb(self, block):
        # deregister this block so it can be merged with a neighbour
        (arena, start, stop) = block
        del self._start_to_block[(arena, start)]
        del self._stop_to_block[(arena, stop)]

        length = stop - start
        seq = self._len_to_seq[length]
        seq.remove(block)
        if not seq:
            del self._len_to_seq[length]
            self._lengths.remove(length)

        return start, stop

    def _free_pending_blocks(self):
        # Free all the blocks in the pending list - called with the lock held
        while 1:
            try:
                block = self._pending_free_blocks.pop()
            except IndexError:
                break
            self._allocated_blocks.remove(block)
            self._free(block)

    def free(self, block):
        # free a block returned by malloc()
        # Since free() can be called asynchronously by the GC, it could happen
        # that it's called while self._lock is held: in that case,
        # self._lock.acquire() would deadlock (issue #12352). To avoid that, a
        # trylock is used instead, and if the lock can't be acquired
        # immediately, the block is added to a list of blocks to be freed
        # synchronously sometimes later from malloc() or free(), by calling
        # _free_pending_blocks() (appending and retrieving from a list is not
        # strictly thread-safe but under cPython it's atomic thanks
        # to the GIL).
        assert os.getpid() == self._lastpid
        if not self._lock.acquire(False):
            # can't aquire the lock right now, add the block to the list of
            # pending blocks to free
            self._pending_free_blocks.append(block)
        else:
            # we hold the lock
            try:
                self._free_pending_blocks()
                self._allocated_blocks.remove(block)
                self._free(block)
            finally:
                self._lock.release()

    def malloc(self, size):
        # return a block of right size (possibly rounded up)
        assert 0 <= size < maxsize
        if os.getpid() != self._lastpid:
            self.__init__()                     # reinitialize after fork
        self._lock.acquire()
        self._free_pending_blocks()
        try:
            size = self._roundup(max(size, 1), self._alignment)
            (arena, start, stop) = self._malloc(size)
            new_stop = start + size
            if new_stop < stop:
                self._free((arena, new_stop, stop))
            block = (arena, start, new_stop)
            self._allocated_blocks.add(block)
            return block
        finally:
            self._lock.release()

#
# Class representing a chunk of an mmap -- can be inherited
#


class BufferWrapper(object):

    _heap = Heap()

    def __init__(self, size):
        assert 0 <= size < maxsize
        block = BufferWrapper._heap.malloc(size)
        self._state = (block, size)
        Finalize(self, BufferWrapper._heap.free, args=(block,))

    def get_address(self):
        (arena, start, stop), size = self._state
        address, length = _billiard.address_of_buffer(arena.buffer)
        assert size <= length
        return address + start

    def get_size(self):
        return self._state[1]

########NEW FILE########
__FILENAME__ = managers
#
# Module providing the `SyncManager` class for dealing
# with shared objects
#
# multiprocessing/managers.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#
from __future__ import absolute_import

__all__ = ['BaseManager', 'SyncManager', 'BaseProxy', 'Token']

#
# Imports
#

import sys
import threading
import array

from traceback import format_exc

from . import Process, current_process, active_children, Pool, util, connection
from .five import Queue, items, monotonic
from .process import AuthenticationString
from .forking import exit, Popen
from .reduction import ForkingPickler
from .util import Finalize, error, info

#
# Register some things for pickling
#


def reduce_array(a):
    return array.array, (a.typecode, a.tostring())
ForkingPickler.register(array.array, reduce_array)

view_types = [type(getattr({}, name)())
              for name in ('items', 'keys', 'values')]
if view_types[0] is not list:  # only needed in Py3.0

    def rebuild_as_list(obj):
        return list, (list(obj), )
    for view_type in view_types:
        ForkingPickler.register(view_type, rebuild_as_list)
        try:
            import copyreg
        except ImportError:
            pass
        else:
            copyreg.pickle(view_type, rebuild_as_list)

#
# Type for identifying shared objects
#


class Token(object):
    '''
    Type to uniquely indentify a shared object
    '''
    __slots__ = ('typeid', 'address', 'id')

    def __init__(self, typeid, address, id):
        (self.typeid, self.address, self.id) = (typeid, address, id)

    def __getstate__(self):
        return (self.typeid, self.address, self.id)

    def __setstate__(self, state):
        (self.typeid, self.address, self.id) = state

    def __repr__(self):
        return 'Token(typeid=%r, address=%r, id=%r)' % \
               (self.typeid, self.address, self.id)

#
# Function for communication with a manager's server process
#


def dispatch(c, id, methodname, args=(), kwds={}):
    '''
    Send a message to manager using connection `c` and return response
    '''
    c.send((id, methodname, args, kwds))
    kind, result = c.recv()
    if kind == '#RETURN':
        return result
    raise convert_to_error(kind, result)


def convert_to_error(kind, result):
    if kind == '#ERROR':
        return result
    elif kind == '#TRACEBACK':
        assert type(result) is str
        return RemoteError(result)
    elif kind == '#UNSERIALIZABLE':
        assert type(result) is str
        return RemoteError('Unserializable message: %s\n' % result)
    else:
        return ValueError('Unrecognized message type')


class RemoteError(Exception):

    def __str__(self):
        return ('\n' + '-' * 75 + '\n' + str(self.args[0]) + '-' * 75)

#
# Functions for finding the method names of an object
#


def all_methods(obj):
    '''
    Return a list of names of methods of `obj`
    '''
    temp = []
    for name in dir(obj):
        func = getattr(obj, name)
        if callable(func):
            temp.append(name)
    return temp


def public_methods(obj):
    '''
    Return a list of names of methods of `obj` which do not start with '_'
    '''
    return [name for name in all_methods(obj) if name[0] != '_']

#
# Server which is run in a process controlled by a manager
#


class Server(object):
    '''
    Server class which runs in a process controlled by a manager object
    '''
    public = ['shutdown', 'create', 'accept_connection', 'get_methods',
              'debug_info', 'number_of_objects', 'dummy', 'incref', 'decref']

    def __init__(self, registry, address, authkey, serializer):
        assert isinstance(authkey, bytes)
        self.registry = registry
        self.authkey = AuthenticationString(authkey)
        Listener, Client = listener_client[serializer]

        # do authentication later
        self.listener = Listener(address=address, backlog=16)
        self.address = self.listener.address

        self.id_to_obj = {'0': (None, ())}
        self.id_to_refcount = {}
        self.mutex = threading.RLock()
        self.stop = 0

    def serve_forever(self):
        '''
        Run the server forever
        '''
        current_process()._manager_server = self
        try:
            try:
                while 1:
                    try:
                        c = self.listener.accept()
                    except (OSError, IOError):
                        continue
                    t = threading.Thread(target=self.handle_request, args=(c,))
                    t.daemon = True
                    t.start()
            except (KeyboardInterrupt, SystemExit):
                pass
        finally:
            self.stop = 999
            self.listener.close()

    def handle_request(self, c):
        '''
        Handle a new connection
        '''
        funcname = result = request = None
        try:
            connection.deliver_challenge(c, self.authkey)
            connection.answer_challenge(c, self.authkey)
            request = c.recv()
            ignore, funcname, args, kwds = request
            assert funcname in self.public, '%r unrecognized' % funcname
            func = getattr(self, funcname)
        except Exception:
            msg = ('#TRACEBACK', format_exc())
        else:
            try:
                result = func(c, *args, **kwds)
            except Exception:
                msg = ('#TRACEBACK', format_exc())
            else:
                msg = ('#RETURN', result)
        try:
            c.send(msg)
        except Exception as exc:
            try:
                c.send(('#TRACEBACK', format_exc()))
            except Exception:
                pass
            info('Failure to send message: %r', msg)
            info(' ... request was %r', request)
            info(' ... exception was %r', exc)

        c.close()

    def serve_client(self, conn):
        '''
        Handle requests from the proxies in a particular process/thread
        '''
        util.debug('starting server thread to service %r',
                   threading.currentThread().name)

        recv = conn.recv
        send = conn.send
        id_to_obj = self.id_to_obj

        while not self.stop:

            try:
                methodname = obj = None
                request = recv()
                ident, methodname, args, kwds = request
                obj, exposed, gettypeid = id_to_obj[ident]

                if methodname not in exposed:
                    raise AttributeError(
                        'method %r of %r object is not in exposed=%r' % (
                            methodname, type(obj), exposed)
                    )

                function = getattr(obj, methodname)

                try:
                    res = function(*args, **kwds)
                except Exception as exc:
                    msg = ('#ERROR', exc)
                else:
                    typeid = gettypeid and gettypeid.get(methodname, None)
                    if typeid:
                        rident, rexposed = self.create(conn, typeid, res)
                        token = Token(typeid, self.address, rident)
                        msg = ('#PROXY', (rexposed, token))
                    else:
                        msg = ('#RETURN', res)

            except AttributeError:
                if methodname is None:
                    msg = ('#TRACEBACK', format_exc())
                else:
                    try:
                        fallback_func = self.fallback_mapping[methodname]
                        result = fallback_func(
                            self, conn, ident, obj, *args, **kwds
                        )
                        msg = ('#RETURN', result)
                    except Exception:
                        msg = ('#TRACEBACK', format_exc())

            except EOFError:
                util.debug('got EOF -- exiting thread serving %r',
                           threading.currentThread().name)
                sys.exit(0)

            except Exception:
                msg = ('#TRACEBACK', format_exc())

            try:
                try:
                    send(msg)
                except Exception:
                    send(('#UNSERIALIZABLE', repr(msg)))
            except Exception as exc:
                info('exception in thread serving %r',
                     threading.currentThread().name)
                info(' ... message was %r', msg)
                info(' ... exception was %r', exc)
                conn.close()
                sys.exit(1)

    def fallback_getvalue(self, conn, ident, obj):
        return obj

    def fallback_str(self, conn, ident, obj):
        return str(obj)

    def fallback_repr(self, conn, ident, obj):
        return repr(obj)

    fallback_mapping = {
        '__str__': fallback_str,
        '__repr__': fallback_repr,
        '#GETVALUE': fallback_getvalue,
    }

    def dummy(self, c):
        pass

    def debug_info(self, c):
        '''
        Return some info --- useful to spot problems with refcounting
        '''
        with self.mutex:
            result = []
            keys = list(self.id_to_obj.keys())
            keys.sort()
            for ident in keys:
                if ident != '0':
                    result.append('  %s:       refcount=%s\n    %s' %
                                  (ident, self.id_to_refcount[ident],
                                   str(self.id_to_obj[ident][0])[:75]))
            return '\n'.join(result)

    def number_of_objects(self, c):
        '''
        Number of shared objects
        '''
        return len(self.id_to_obj) - 1      # don't count ident='0'

    def shutdown(self, c):
        '''
        Shutdown this process
        '''
        try:
            try:
                util.debug('manager received shutdown message')
                c.send(('#RETURN', None))

                if sys.stdout != sys.__stdout__:
                    util.debug('resetting stdout, stderr')
                    sys.stdout = sys.__stdout__
                    sys.stderr = sys.__stderr__

                util._run_finalizers(0)

                for p in active_children():
                    util.debug('terminating a child process of manager')
                    p.terminate()

                for p in active_children():
                    util.debug('terminating a child process of manager')
                    p.join()

                util._run_finalizers()
                info('manager exiting with exitcode 0')
            except:
                if not error("Error while manager shutdown", exc_info=True):
                    import traceback
                    traceback.print_exc()
        finally:
            exit(0)

    def create(self, c, typeid, *args, **kwds):
        '''
        Create a new shared object and return its id
        '''
        with self.mutex:
            callable, exposed, method_to_typeid, proxytype = \
                self.registry[typeid]

            if callable is None:
                assert len(args) == 1 and not kwds
                obj = args[0]
            else:
                obj = callable(*args, **kwds)

            if exposed is None:
                exposed = public_methods(obj)
            if method_to_typeid is not None:
                assert type(method_to_typeid) is dict
                exposed = list(exposed) + list(method_to_typeid)
            # convert to string because xmlrpclib
            # only has 32 bit signed integers
            ident = '%x' % id(obj)
            util.debug('%r callable returned object with id %r', typeid, ident)

            self.id_to_obj[ident] = (obj, set(exposed), method_to_typeid)
            if ident not in self.id_to_refcount:
                self.id_to_refcount[ident] = 0
            # increment the reference count immediately, to avoid
            # this object being garbage collected before a Proxy
            # object for it can be created.  The caller of create()
            # is responsible for doing a decref once the Proxy object
            # has been created.
            self.incref(c, ident)
            return ident, tuple(exposed)

    def get_methods(self, c, token):
        '''
        Return the methods of the shared object indicated by token
        '''
        return tuple(self.id_to_obj[token.id][1])

    def accept_connection(self, c, name):
        '''
        Spawn a new thread to serve this connection
        '''
        threading.currentThread().name = name
        c.send(('#RETURN', None))
        self.serve_client(c)

    def incref(self, c, ident):
        with self.mutex:
            self.id_to_refcount[ident] += 1

    def decref(self, c, ident):
        with self.mutex:
            assert self.id_to_refcount[ident] >= 1
            self.id_to_refcount[ident] -= 1
            if self.id_to_refcount[ident] == 0:
                del self.id_to_obj[ident], self.id_to_refcount[ident]
                util.debug('disposing of obj with id %r', ident)

#
# Class to represent state of a manager
#


class State(object):
    __slots__ = ['value']
    INITIAL = 0
    STARTED = 1
    SHUTDOWN = 2

#
# Mapping from serializer name to Listener and Client types
#

listener_client = {
    'pickle': (connection.Listener, connection.Client),
    'xmlrpclib': (connection.XmlListener, connection.XmlClient),
}

#
# Definition of BaseManager
#


class BaseManager(object):
    '''
    Base class for managers
    '''
    _registry = {}
    _Server = Server

    def __init__(self, address=None, authkey=None, serializer='pickle'):
        if authkey is None:
            authkey = current_process().authkey
        self._address = address     # XXX not final address if eg ('', 0)
        self._authkey = AuthenticationString(authkey)
        self._state = State()
        self._state.value = State.INITIAL
        self._serializer = serializer
        self._Listener, self._Client = listener_client[serializer]

    def __reduce__(self):
        return (type(self).from_address,
                (self._address, self._authkey, self._serializer))

    def get_server(self):
        '''
        Return server object with serve_forever() method and address attribute
        '''
        assert self._state.value == State.INITIAL
        return Server(self._registry, self._address,
                      self._authkey, self._serializer)

    def connect(self):
        '''
        Connect manager object to the server process
        '''
        Listener, Client = listener_client[self._serializer]
        conn = Client(self._address, authkey=self._authkey)
        dispatch(conn, None, 'dummy')
        self._state.value = State.STARTED

    def start(self, initializer=None, initargs=()):
        '''
        Spawn a server process for this manager object
        '''
        assert self._state.value == State.INITIAL

        if initializer is not None and not callable(initializer):
            raise TypeError('initializer must be a callable')

        # pipe over which we will retrieve address of server
        reader, writer = connection.Pipe(duplex=False)

        # spawn process which runs a server
        self._process = Process(
            target=type(self)._run_server,
            args=(self._registry, self._address, self._authkey,
                  self._serializer, writer, initializer, initargs),
        )
        ident = ':'.join(str(i) for i in self._process._identity)
        self._process.name = type(self).__name__ + '-' + ident
        self._process.start()

        # get address of server
        writer.close()
        self._address = reader.recv()
        reader.close()

        # register a finalizer
        self._state.value = State.STARTED
        self.shutdown = Finalize(
            self, type(self)._finalize_manager,
            args=(self._process, self._address, self._authkey,
                  self._state, self._Client),
            exitpriority=0
        )

    @classmethod
    def _run_server(cls, registry, address, authkey, serializer, writer,
                    initializer=None, initargs=()):
        '''
        Create a server, report its address and run it
        '''
        if initializer is not None:
            initializer(*initargs)

        # create server
        server = cls._Server(registry, address, authkey, serializer)

        # inform parent process of the server's address
        writer.send(server.address)
        writer.close()

        # run the manager
        info('manager serving at %r', server.address)
        server.serve_forever()

    def _create(self, typeid, *args, **kwds):
        '''
        Create a new shared object; return the token and exposed tuple
        '''
        assert self._state.value == State.STARTED, 'server not yet started'
        conn = self._Client(self._address, authkey=self._authkey)
        try:
            id, exposed = dispatch(conn, None, 'create',
                                   (typeid,) + args, kwds)
        finally:
            conn.close()
        return Token(typeid, self._address, id), exposed

    def join(self, timeout=None):
        '''
        Join the manager process (if it has been spawned)
        '''
        self._process.join(timeout)

    def _debug_info(self):
        '''
        Return some info about the servers shared objects and connections
        '''
        conn = self._Client(self._address, authkey=self._authkey)
        try:
            return dispatch(conn, None, 'debug_info')
        finally:
            conn.close()

    def _number_of_objects(self):
        '''
        Return the number of shared objects
        '''
        conn = self._Client(self._address, authkey=self._authkey)
        try:
            return dispatch(conn, None, 'number_of_objects')
        finally:
            conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    @staticmethod
    def _finalize_manager(process, address, authkey, state, _Client):
        '''
        Shutdown the manager process; will be registered as a finalizer
        '''
        if process.is_alive():
            info('sending shutdown message to manager')
            try:
                conn = _Client(address, authkey=authkey)
                try:
                    dispatch(conn, None, 'shutdown')
                finally:
                    conn.close()
            except Exception:
                pass

            process.join(timeout=0.2)
            if process.is_alive():
                info('manager still alive')
                if hasattr(process, 'terminate'):
                    info('trying to `terminate()` manager process')
                    process.terminate()
                    process.join(timeout=0.1)
                    if process.is_alive():
                        info('manager still alive after terminate')

        state.value = State.SHUTDOWN
        try:
            del BaseProxy._address_to_local[address]
        except KeyError:
            pass

    address = property(lambda self: self._address)

    @classmethod
    def register(cls, typeid, callable=None, proxytype=None, exposed=None,
                 method_to_typeid=None, create_method=True):
        '''
        Register a typeid with the manager type
        '''
        if '_registry' not in cls.__dict__:
            cls._registry = cls._registry.copy()

        if proxytype is None:
            proxytype = AutoProxy

        exposed = exposed or getattr(proxytype, '_exposed_', None)

        method_to_typeid = (
            method_to_typeid or
            getattr(proxytype, '_method_to_typeid_', None)
        )

        if method_to_typeid:
            for key, value in items(method_to_typeid):
                assert type(key) is str, '%r is not a string' % key
                assert type(value) is str, '%r is not a string' % value

        cls._registry[typeid] = (
            callable, exposed, method_to_typeid, proxytype
        )

        if create_method:
            def temp(self, *args, **kwds):
                util.debug('requesting creation of a shared %r object', typeid)
                token, exp = self._create(typeid, *args, **kwds)
                proxy = proxytype(
                    token, self._serializer, manager=self,
                    authkey=self._authkey, exposed=exp
                )
                conn = self._Client(token.address, authkey=self._authkey)
                dispatch(conn, None, 'decref', (token.id,))
                return proxy
            temp.__name__ = typeid
            setattr(cls, typeid, temp)

#
# Subclass of set which get cleared after a fork
#


class ProcessLocalSet(set):

    def __init__(self):
        util.register_after_fork(self, lambda obj: obj.clear())

    def __reduce__(self):
        return type(self), ()

#
# Definition of BaseProxy
#


class BaseProxy(object):
    '''
    A base for proxies of shared objects
    '''
    _address_to_local = {}
    _mutex = util.ForkAwareThreadLock()

    def __init__(self, token, serializer, manager=None,
                 authkey=None, exposed=None, incref=True):
        BaseProxy._mutex.acquire()
        try:
            tls_idset = BaseProxy._address_to_local.get(token.address, None)
            if tls_idset is None:
                tls_idset = util.ForkAwareLocal(), ProcessLocalSet()
                BaseProxy._address_to_local[token.address] = tls_idset
        finally:
            BaseProxy._mutex.release()

        # self._tls is used to record the connection used by this
        # thread to communicate with the manager at token.address
        self._tls = tls_idset[0]

        # self._idset is used to record the identities of all shared
        # objects for which the current process owns references and
        # which are in the manager at token.address
        self._idset = tls_idset[1]

        self._token = token
        self._id = self._token.id
        self._manager = manager
        self._serializer = serializer
        self._Client = listener_client[serializer][1]

        if authkey is not None:
            self._authkey = AuthenticationString(authkey)
        elif self._manager is not None:
            self._authkey = self._manager._authkey
        else:
            self._authkey = current_process().authkey

        if incref:
            self._incref()

        util.register_after_fork(self, BaseProxy._after_fork)

    def _connect(self):
        util.debug('making connection to manager')
        name = current_process().name
        if threading.currentThread().name != 'MainThread':
            name += '|' + threading.currentThread().name
        conn = self._Client(self._token.address, authkey=self._authkey)
        dispatch(conn, None, 'accept_connection', (name,))
        self._tls.connection = conn

    def _callmethod(self, methodname, args=(), kwds={}):
        '''
        Try to call a method of the referrent and return a copy of the result
        '''
        try:
            conn = self._tls.connection
        except AttributeError:
            util.debug('thread %r does not own a connection',
                       threading.currentThread().name)
            self._connect()
            conn = self._tls.connection

        conn.send((self._id, methodname, args, kwds))
        kind, result = conn.recv()

        if kind == '#RETURN':
            return result
        elif kind == '#PROXY':
            exposed, token = result
            proxytype = self._manager._registry[token.typeid][-1]
            proxy = proxytype(
                token, self._serializer, manager=self._manager,
                authkey=self._authkey, exposed=exposed
            )
            conn = self._Client(token.address, authkey=self._authkey)
            dispatch(conn, None, 'decref', (token.id,))
            return proxy
        raise convert_to_error(kind, result)

    def _getvalue(self):
        '''
        Get a copy of the value of the referent
        '''
        return self._callmethod('#GETVALUE')

    def _incref(self):
        conn = self._Client(self._token.address, authkey=self._authkey)
        dispatch(conn, None, 'incref', (self._id,))
        util.debug('INCREF %r', self._token.id)

        self._idset.add(self._id)

        state = self._manager and self._manager._state

        self._close = Finalize(
            self, BaseProxy._decref,
            args=(self._token, self._authkey, state,
                  self._tls, self._idset, self._Client),
            exitpriority=10
        )

    @staticmethod
    def _decref(token, authkey, state, tls, idset, _Client):
        idset.discard(token.id)

        # check whether manager is still alive
        if state is None or state.value == State.STARTED:
            # tell manager this process no longer cares about referent
            try:
                util.debug('DECREF %r', token.id)
                conn = _Client(token.address, authkey=authkey)
                dispatch(conn, None, 'decref', (token.id,))
            except Exception as exc:
                util.debug('... decref failed %s', exc)

        else:
            util.debug('DECREF %r -- manager already shutdown', token.id)

        # check whether we can close this thread's connection because
        # the process owns no more references to objects for this manager
        if not idset and hasattr(tls, 'connection'):
            util.debug('thread %r has no more proxies so closing conn',
                       threading.currentThread().name)
            tls.connection.close()
            del tls.connection

    def _after_fork(self):
        self._manager = None
        try:
            self._incref()
        except Exception as exc:
            # the proxy may just be for a manager which has shutdown
            info('incref failed: %s', exc)

    def __reduce__(self):
        kwds = {}
        if Popen.thread_is_spawning():
            kwds['authkey'] = self._authkey

        if getattr(self, '_isauto', False):
            kwds['exposed'] = self._exposed_
            return (RebuildProxy,
                    (AutoProxy, self._token, self._serializer, kwds))
        else:
            return (RebuildProxy,
                    (type(self), self._token, self._serializer, kwds))

    def __deepcopy__(self, memo):
        return self._getvalue()

    def __repr__(self):
        return '<%s object, typeid %r at %s>' % \
               (type(self).__name__, self._token.typeid, '0x%x' % id(self))

    def __str__(self):
        '''
        Return representation of the referent (or a fall-back if that fails)
        '''
        try:
            return self._callmethod('__repr__')
        except Exception:
            return repr(self)[:-1] + "; '__str__()' failed>"

#
# Function used for unpickling
#


def RebuildProxy(func, token, serializer, kwds):
    '''
    Function used for unpickling proxy objects.

    If possible the shared object is returned, or otherwise a proxy for it.
    '''
    server = getattr(current_process(), '_manager_server', None)

    if server and server.address == token.address:
        return server.id_to_obj[token.id][0]
    else:
        incref = (
            kwds.pop('incref', True) and
            not getattr(current_process(), '_inheriting', False)
        )
        return func(token, serializer, incref=incref, **kwds)

#
# Functions to create proxies and proxy types
#


def MakeProxyType(name, exposed, _cache={}):
    '''
    Return an proxy type whose methods are given by `exposed`
    '''
    exposed = tuple(exposed)
    try:
        return _cache[(name, exposed)]
    except KeyError:
        pass

    dic = {}

    for meth in exposed:
        exec('''def %s(self, *args, **kwds):
        return self._callmethod(%r, args, kwds)''' % (meth, meth), dic)

    ProxyType = type(name, (BaseProxy,), dic)
    ProxyType._exposed_ = exposed
    _cache[(name, exposed)] = ProxyType
    return ProxyType


def AutoProxy(token, serializer, manager=None, authkey=None,
              exposed=None, incref=True):
    '''
    Return an auto-proxy for `token`
    '''
    _Client = listener_client[serializer][1]

    if exposed is None:
        conn = _Client(token.address, authkey=authkey)
        try:
            exposed = dispatch(conn, None, 'get_methods', (token,))
        finally:
            conn.close()

    if authkey is None and manager is not None:
        authkey = manager._authkey
    if authkey is None:
        authkey = current_process().authkey

    ProxyType = MakeProxyType('AutoProxy[%s]' % token.typeid, exposed)
    proxy = ProxyType(token, serializer, manager=manager, authkey=authkey,
                      incref=incref)
    proxy._isauto = True
    return proxy

#
# Types/callables which we will register with SyncManager
#


class Namespace(object):

    def __init__(self, **kwds):
        self.__dict__.update(kwds)

    def __repr__(self):
        items = list(self.__dict__.items())
        temp = []
        for name, value in items:
            if not name.startswith('_'):
                temp.append('%s=%r' % (name, value))
        temp.sort()
        return 'Namespace(%s)' % str.join(', ', temp)


class Value(object):

    def __init__(self, typecode, value, lock=True):
        self._typecode = typecode
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def __repr__(self):
        return '%s(%r, %r)' % (type(self).__name__,
                               self._typecode, self._value)
    value = property(get, set)


def Array(typecode, sequence, lock=True):
    return array.array(typecode, sequence)

#
# Proxy types used by SyncManager
#


class IteratorProxy(BaseProxy):
    if sys.version_info[0] == 3:
        _exposed = ('__next__', 'send', 'throw', 'close')
    else:
        _exposed_ = ('__next__', 'next', 'send', 'throw', 'close')

        def next(self, *args):
            return self._callmethod('next', args)

    def __iter__(self):
        return self

    def __next__(self, *args):
        return self._callmethod('__next__', args)

    def send(self, *args):
        return self._callmethod('send', args)

    def throw(self, *args):
        return self._callmethod('throw', args)

    def close(self, *args):
        return self._callmethod('close', args)


class AcquirerProxy(BaseProxy):
    _exposed_ = ('acquire', 'release')

    def acquire(self, blocking=True):
        return self._callmethod('acquire', (blocking,))

    def release(self):
        return self._callmethod('release')

    def __enter__(self):
        return self._callmethod('acquire')

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._callmethod('release')


class ConditionProxy(AcquirerProxy):
    _exposed_ = ('acquire', 'release', 'wait', 'notify', 'notify_all')

    def wait(self, timeout=None):
        return self._callmethod('wait', (timeout,))

    def notify(self):
        return self._callmethod('notify')

    def notify_all(self):
        return self._callmethod('notify_all')

    def wait_for(self, predicate, timeout=None):
        result = predicate()
        if result:
            return result
        if timeout is not None:
            endtime = monotonic() + timeout
        else:
            endtime = None
            waittime = None
        while not result:
            if endtime is not None:
                waittime = endtime - monotonic()
                if waittime <= 0:
                    break
            self.wait(waittime)
            result = predicate()
        return result


class EventProxy(BaseProxy):
    _exposed_ = ('is_set', 'set', 'clear', 'wait')

    def is_set(self):
        return self._callmethod('is_set')

    def set(self):
        return self._callmethod('set')

    def clear(self):
        return self._callmethod('clear')

    def wait(self, timeout=None):
        return self._callmethod('wait', (timeout,))


class NamespaceProxy(BaseProxy):
    _exposed_ = ('__getattribute__', '__setattr__', '__delattr__')

    def __getattr__(self, key):
        if key[0] == '_':
            return object.__getattribute__(self, key)
        callmethod = object.__getattribute__(self, '_callmethod')
        return callmethod('__getattribute__', (key,))

    def __setattr__(self, key, value):
        if key[0] == '_':
            return object.__setattr__(self, key, value)
        callmethod = object.__getattribute__(self, '_callmethod')
        return callmethod('__setattr__', (key, value))

    def __delattr__(self, key):
        if key[0] == '_':
            return object.__delattr__(self, key)
        callmethod = object.__getattribute__(self, '_callmethod')
        return callmethod('__delattr__', (key,))


class ValueProxy(BaseProxy):
    _exposed_ = ('get', 'set')

    def get(self):
        return self._callmethod('get')

    def set(self, value):
        return self._callmethod('set', (value,))
    value = property(get, set)


BaseListProxy = MakeProxyType('BaseListProxy', (
    '__add__', '__contains__', '__delitem__', '__delslice__',
    '__getitem__', '__getslice__', '__len__', '__mul__',
    '__reversed__', '__rmul__', '__setitem__', '__setslice__',
    'append', 'count', 'extend', 'index', 'insert', 'pop', 'remove',
    'reverse', 'sort', '__imul__',
))  # XXX __getslice__ and __setslice__ unneeded in Py3.0


class ListProxy(BaseListProxy):

    def __iadd__(self, value):
        self._callmethod('extend', (value,))
        return self

    def __imul__(self, value):
        self._callmethod('__imul__', (value,))
        return self


DictProxy = MakeProxyType('DictProxy', (
    '__contains__', '__delitem__', '__getitem__', '__len__',
    '__setitem__', 'clear', 'copy', 'get', 'has_key', 'items',
    'keys', 'pop', 'popitem', 'setdefault', 'update', 'values',
))


ArrayProxy = MakeProxyType('ArrayProxy', (
    '__len__', '__getitem__', '__setitem__', '__getslice__', '__setslice__',
))  # XXX __getslice__ and __setslice__ unneeded in Py3.0


PoolProxy = MakeProxyType('PoolProxy', (
    'apply', 'apply_async', 'close', 'imap', 'imap_unordered', 'join',
    'map', 'map_async', 'starmap', 'starmap_async', 'terminate',
))
PoolProxy._method_to_typeid_ = {
    'apply_async': 'AsyncResult',
    'map_async': 'AsyncResult',
    'starmap_async': 'AsyncResult',
    'imap': 'Iterator',
    'imap_unordered': 'Iterator',
}

#
# Definition of SyncManager
#


class SyncManager(BaseManager):
    '''
    Subclass of `BaseManager` which supports a number of shared object types.

    The types registered are those intended for the synchronization
    of threads, plus `dict`, `list` and `Namespace`.

    The `billiard.Manager()` function creates started instances of
    this class.
    '''

SyncManager.register('Queue', Queue)
SyncManager.register('JoinableQueue', Queue)
SyncManager.register('Event', threading.Event, EventProxy)
SyncManager.register('Lock', threading.Lock, AcquirerProxy)
SyncManager.register('RLock', threading.RLock, AcquirerProxy)
SyncManager.register('Semaphore', threading.Semaphore, AcquirerProxy)
SyncManager.register('BoundedSemaphore', threading.BoundedSemaphore,
                     AcquirerProxy)
SyncManager.register('Condition', threading.Condition, ConditionProxy)
SyncManager.register('Pool', Pool, PoolProxy)
SyncManager.register('list', list, ListProxy)
SyncManager.register('dict', dict, DictProxy)
SyncManager.register('Value', Value, ValueProxy)
SyncManager.register('Array', Array, ArrayProxy)
SyncManager.register('Namespace', Namespace, NamespaceProxy)

# types returned by methods of PoolProxy
SyncManager.register('Iterator', proxytype=IteratorProxy, create_method=False)
SyncManager.register('AsyncResult', create_method=False)

########NEW FILE########
__FILENAME__ = pool
# -*- coding: utf-8 -*-
#
# Module providing the `Pool` class for managing a process pool
#
# multiprocessing/pool.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#
from __future__ import absolute_import

#
# Imports
#

import errno
import itertools
import os
import platform
import signal
import sys
import threading
import time
import warnings

from collections import deque
from functools import partial

from . import Event, Process, cpu_count
from . import util
from .common import pickle_loads, reset_signals, restart_state
from .compat import get_errno, send_offset
from .einfo import ExceptionInfo
from .exceptions import (
    CoroStop,
    RestartFreqExceeded,
    SoftTimeLimitExceeded,
    Terminated,
    TimeLimitExceeded,
    TimeoutError,
    WorkerLostError,
)
from .five import Empty, Queue, range, values, reraise, monotonic
from .util import Finalize, debug

PY3 = sys.version_info[0] == 3

if platform.system() == 'Windows':  # pragma: no cover
    # On Windows os.kill calls TerminateProcess which cannot be
    # handled by # any process, so this is needed to terminate the task
    # *and its children* (if any).
    from ._win import kill_processtree as _kill  # noqa
else:
    from os import kill as _kill                 # noqa


try:
    TIMEOUT_MAX = threading.TIMEOUT_MAX
except AttributeError:  # pragma: no cover
    TIMEOUT_MAX = 1e10  # noqa


if sys.version_info >= (3, 3):
    _Semaphore = threading.Semaphore
else:
    # Semaphore is a factory function pointing to _Semaphore
    _Semaphore = threading._Semaphore  # noqa

SIGMAP = dict(
    (getattr(signal, n), n) for n in dir(signal) if n.startswith('SIG')
)

#
# Constants representing the state of a pool
#

RUN = 0
CLOSE = 1
TERMINATE = 2

#
# Constants representing the state of a job
#

ACK = 0
READY = 1
TASK = 2
NACK = 3
DEATH = 4

#
# Exit code constants
#
EX_OK = 0
EX_FAILURE = 1
EX_RECYCLE = 0x9B


# Signal used for soft time limits.
SIG_SOFT_TIMEOUT = getattr(signal, "SIGUSR1", None)

#
# Miscellaneous
#

LOST_WORKER_TIMEOUT = 10.0
EX_OK = getattr(os, "EX_OK", 0)

job_counter = itertools.count()

Lock = threading.Lock


def _get_send_offset(connection):
    try:
        native = connection.send_offset
    except AttributeError:
        native = None
    if native is None:
        return partial(send_offset, connection.fileno())
    return native


def human_status(status):
    if status < 0:
        try:
            return 'signal {0} ({1})'.format(-status, SIGMAP[-status])
        except KeyError:
            return 'signal {0}'.format(-status)
    return 'exitcode {0}'.format(status)


def mapstar(args):
    return list(map(*args))


def starmapstar(args):
    return list(itertools.starmap(args[0], args[1]))


def error(msg, *args, **kwargs):
    if util._logger:
        util._logger.error(msg, *args, **kwargs)


def stop_if_not_current(thread, timeout=None):
    if thread is not threading.currentThread():
        thread.stop(timeout)


class LaxBoundedSemaphore(_Semaphore):
    """Semaphore that checks that # release is <= # acquires,
    but ignores if # releases >= value."""

    def __init__(self, value=1, verbose=None):
        if PY3:
            _Semaphore.__init__(self, value)
        else:
            _Semaphore.__init__(self, value, verbose)
        self._initial_value = value

    def grow(self):
        if PY3:
            cond = self._cond
        else:
            cond = self._Semaphore__cond
        with cond:
            self._initial_value += 1
            self._Semaphore__value += 1
            cond.notify()

    def shrink(self):
        self._initial_value -= 1
        self.acquire()

    if PY3:

        def release(self):
            cond = self._cond
            with cond:
                if self._value < self._initial_value:
                    self._value += 1
                    cond.notify_all()

        def clear(self):
            while self._value < self._initial_value:
                _Semaphore.release(self)
    else:

        def release(self):  # noqa
            cond = self._Semaphore__cond
            with cond:
                if self._Semaphore__value < self._initial_value:
                    self._Semaphore__value += 1
                    cond.notifyAll()

        def clear(self):  # noqa
            while self._Semaphore__value < self._initial_value:
                _Semaphore.release(self)

#
# Exceptions
#


class MaybeEncodingError(Exception):
    """Wraps possible unpickleable errors, so they can be
    safely sent through the socket."""

    def __init__(self, exc, value):
        self.exc = repr(exc)
        self.value = repr(value)
        super(MaybeEncodingError, self).__init__(self.exc, self.value)

    def __repr__(self):
        return "<MaybeEncodingError: %s>" % str(self)

    def __str__(self):
        return "Error sending result: '%r'. Reason: '%r'." % (
            self.value, self.exc)


class WorkersJoined(Exception):
    """All workers have terminated."""


def soft_timeout_sighandler(signum, frame):
    raise SoftTimeLimitExceeded()

#
# Code run by worker processes
#


class Worker(Process):
    _controlled_termination = False
    _job_terminated = False

    def __init__(self, inq, outq, synq=None, initializer=None, initargs=(),
                 maxtasks=None, sentinel=None, on_exit=None,
                 sigprotection=True):
        assert maxtasks is None or (type(maxtasks) == int and maxtasks > 0)
        self.initializer = initializer
        self.initargs = initargs
        self.maxtasks = maxtasks
        self._shutdown = sentinel
        self.on_exit = on_exit
        self.sigprotection = sigprotection
        self.inq, self.outq, self.synq = inq, outq, synq
        self._make_shortcuts()

        super(Worker, self).__init__()

    def __reduce__(self):
        return self.__class__, (
            self.inq, self.outq, self.synq, self.initializer,
            self.initargs, self.maxtasks, self._shutdown,
        )

    def _make_shortcuts(self):
        self.inqW_fd = self.inq._writer.fileno()    # inqueue write fd
        self.outqR_fd = self.outq._reader.fileno()  # outqueue read fd
        if self.synq:
            self.synqR_fd = self.synq._reader.fileno()  # synqueue read fd
            self.synqW_fd = self.synq._writer.fileno()  # synqueue write fd
            self.send_syn_offset = _get_send_offset(self.synq._writer)
        else:
            self.synqR_fd = self.synqW_fd = self._send_syn_offset = None
        self._quick_put = self.inq._writer.send
        self._quick_get = self.outq._reader.recv
        self.send_job_offset = _get_send_offset(self.inq._writer)

    def run(self):
        _exit = sys.exit
        _exitcode = [None]

        def exit(status=None):
            _exitcode[0] = status
            return _exit()
        sys.exit = exit

        pid = os.getpid()

        self._make_child_methods()
        self.after_fork()
        self.on_loop_start(pid=pid)  # callback on loop start
        try:
            sys.exit(self.workloop(pid=pid))
        except Exception as exc:
            error('Pool process %r error: %r', self, exc, exc_info=1)
            self._do_exit(pid, _exitcode[0], exc)
        finally:
            self._do_exit(pid, _exitcode[0], None)

    def _do_exit(self, pid, exitcode, exc=None):
        if exitcode is None:
            exitcode = EX_FAILURE if exc else EX_OK

        if self.on_exit is not None:
            self.on_exit(pid, exitcode)

        if sys.platform != 'win32':
            try:
                self.outq.put((DEATH, (pid, exitcode)))
                time.sleep(1)
            finally:
                os._exit(exitcode)
        else:
            os._exit(exitcode)

    def on_loop_start(self, pid):
        pass

    def terminate_controlled(self):
        self._controlled_termination = True
        self.terminate()

    def prepare_result(self, result):
        return result

    def workloop(self, debug=debug, now=monotonic, pid=None):
        pid = pid or os.getpid()
        put = self.outq.put
        inqW_fd = self.inqW_fd
        synqW_fd = self.synqW_fd
        maxtasks = self.maxtasks
        prepare_result = self.prepare_result

        wait_for_job = self.wait_for_job
        _wait_for_syn = self.wait_for_syn

        def wait_for_syn(jid):
            i = 0
            while 1:
                if i > 60:
                    error('!!!WAIT FOR ACK TIMEOUT: job:%r fd:%r!!!',
                          jid, self.synq._reader.fileno(), exc_info=1)
                req = _wait_for_syn()
                if req:
                    type_, args = req
                    if type_ == NACK:
                        return False
                    assert type_ == ACK
                    return True
                i += 1

        completed = 0
        while maxtasks is None or (maxtasks and completed < maxtasks):
            req = wait_for_job()
            if req:
                type_, args_ = req
                assert type_ == TASK
                job, i, fun, args, kwargs = args_
                put((ACK, (job, i, now(), pid, synqW_fd)))
                if _wait_for_syn:
                    confirm = wait_for_syn(job)
                    if not confirm:
                        continue  # received NACK
                try:
                    result = (True, prepare_result(fun(*args, **kwargs)))
                except Exception:
                    result = (False, ExceptionInfo())
                try:
                    put((READY, (job, i, result, inqW_fd)))
                except Exception as exc:
                    _, _, tb = sys.exc_info()
                    try:
                        wrapped = MaybeEncodingError(exc, result[1])
                        einfo = ExceptionInfo((
                            MaybeEncodingError, wrapped, tb,
                        ))
                        put((READY, (job, i, (False, einfo), inqW_fd)))
                    finally:
                        del(tb)
                completed += 1
        debug('worker exiting after %d tasks', completed)
        if maxtasks:
            return EX_RECYCLE if completed == maxtasks else EX_FAILURE
        return EX_OK

    def after_fork(self):
        if hasattr(self.inq, '_writer'):
            self.inq._writer.close()
        if hasattr(self.outq, '_reader'):
            self.outq._reader.close()

        if self.initializer is not None:
            self.initializer(*self.initargs)

        # Make sure all exiting signals call finally: blocks.
        # This is important for the semaphore to be released.
        reset_signals(full=self.sigprotection)

        # install signal handler for soft timeouts.
        if SIG_SOFT_TIMEOUT is not None:
            signal.signal(SIG_SOFT_TIMEOUT, soft_timeout_sighandler)

        try:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
        except AttributeError:
            pass

    def _make_recv_method(self, conn):
        get = conn.get

        if hasattr(conn, '_reader'):
            _poll = conn._reader.poll
            if hasattr(conn, 'get_payload') and conn.get_payload:
                get_payload = conn.get_payload

                def _recv(timeout, loads=pickle_loads):
                    return True, loads(get_payload())
            else:
                def _recv(timeout):  # noqa
                    if _poll(timeout):
                        return True, get()
                    return False, None
        else:
            def _recv(timeout):  # noqa
                try:
                    return True, get(timeout=timeout)
                except Queue.Empty:
                    return False, None
        return _recv

    def _make_child_methods(self, loads=pickle_loads):
        self.wait_for_job = self._make_protected_receive(self.inq)
        self.wait_for_syn = (self._make_protected_receive(self.synq)
                             if self.synq else None)

    def _make_protected_receive(self, conn):
        _receive = self._make_recv_method(conn)
        should_shutdown = self._shutdown.is_set if self._shutdown else None

        def receive(debug=debug):
            if should_shutdown and should_shutdown():
                debug('worker got sentinel -- exiting')
                raise SystemExit(EX_OK)
            try:
                ready, req = _receive(1.0)
                if not ready:
                    return None
            except (EOFError, IOError) as exc:
                if get_errno(exc) == errno.EINTR:
                    return None  # interrupted, maybe by gdb
                debug('worker got %s -- exiting', type(exc).__name__)
                raise SystemExit(EX_FAILURE)
            if req is None:
                debug('worker got sentinel -- exiting')
                raise SystemExit(EX_FAILURE)
            return req

        return receive


#
# Class representing a process pool
#


class PoolThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self._state = RUN
        self._was_started = False
        self.daemon = True

    def run(self):
        try:
            return self.body()
        except RestartFreqExceeded as exc:
            error("Thread %r crashed: %r", type(self).__name__, exc,
                  exc_info=1)
            _kill(os.getpid(), signal.SIGTERM)
            sys.exit()
        except Exception as exc:
            error("Thread %r crashed: %r", type(self).__name__, exc,
                  exc_info=1)
            os._exit(1)

    def start(self, *args, **kwargs):
        self._was_started = True
        super(PoolThread, self).start(*args, **kwargs)

    def on_stop_not_started(self):
        pass

    def stop(self, timeout=None):
        if self._was_started:
            self.join(timeout)
            return
        self.on_stop_not_started()

    def terminate(self):
        self._state = TERMINATE

    def close(self):
        self._state = CLOSE


class Supervisor(PoolThread):

    def __init__(self, pool):
        self.pool = pool
        super(Supervisor, self).__init__()

    def body(self):
        debug('worker handler starting')

        time.sleep(0.8)

        pool = self.pool

        try:
            # do a burst at startup to verify that we can start
            # our pool processes, and in that time we lower
            # the max restart frequency.
            prev_state = pool.restart_state
            pool.restart_state = restart_state(10 * pool._processes, 1)
            for _ in range(10):
                if self._state == RUN and pool._state == RUN:
                    pool._maintain_pool()
                    time.sleep(0.1)

            # Keep maintaing workers until the cache gets drained, unless
            # the pool is termianted
            pool.restart_state = prev_state
            while self._state == RUN and pool._state == RUN:
                pool._maintain_pool()
                time.sleep(0.8)
        except RestartFreqExceeded:
            pool.close()
            pool.join()
            raise
        debug('worker handler exiting')


class TaskHandler(PoolThread):

    def __init__(self, taskqueue, put, outqueue, pool):
        self.taskqueue = taskqueue
        self.put = put
        self.outqueue = outqueue
        self.pool = pool
        super(TaskHandler, self).__init__()

    def body(self):
        taskqueue = self.taskqueue
        put = self.put

        for taskseq, set_length in iter(taskqueue.get, None):
            try:
                i = -1
                for i, task in enumerate(taskseq):
                    if self._state:
                        debug('task handler found thread._state != RUN')
                        break
                    try:
                        put(task)
                    except IOError:
                        debug('could not put task on queue')
                        break
                else:
                    if set_length:
                        debug('doing set_length()')
                        set_length(i + 1)
                    continue
                break
            except Exception as exc:
                error('Task Handler ERROR: %r', exc, exc_info=1)
                break
        else:
            debug('task handler got sentinel')

        self.tell_others()

    def tell_others(self):
        outqueue = self.outqueue
        put = self.put
        pool = self.pool

        try:
            # tell result handler to finish when cache is empty
            debug('task handler sending sentinel to result handler')
            outqueue.put(None)

            # tell workers there is no more work
            debug('task handler sending sentinel to workers')
            for p in pool:
                put(None)
        except IOError:
            debug('task handler got IOError when sending sentinels')

        debug('task handler exiting')

    def on_stop_not_started(self):
        self.tell_others()


class TimeoutHandler(PoolThread):

    def __init__(self, processes, cache, t_soft, t_hard):
        self.processes = processes
        self.cache = cache
        self.t_soft = t_soft
        self.t_hard = t_hard
        self._it = None
        super(TimeoutHandler, self).__init__()

    def _process_by_pid(self, pid):
        return next((
            (proc, i) for i, proc in enumerate(self.processes)
            if proc.pid == pid
        ), (None, None))

    def on_soft_timeout(self, job):
        debug('soft time limit exceeded for %r', job)
        process, _index = self._process_by_pid(job._worker_pid)
        if not process:
            return

        # Run timeout callback
        if job._timeout_callback is not None:
            job._timeout_callback(soft=True, timeout=job._soft_timeout)

        try:
            _kill(job._worker_pid, SIG_SOFT_TIMEOUT)
        except OSError as exc:
            if get_errno(exc) != errno.ESRCH:
                raise

    def on_hard_timeout(self, job):
        if job.ready():
            return
        debug('hard time limit exceeded for %r', job)
        # Remove from cache and set return value to an exception
        try:
            raise TimeLimitExceeded(job._timeout)
        except TimeLimitExceeded:
            job._set(job._job, (False, ExceptionInfo()))
        else:  # pragma: no cover
            pass

        # Remove from _pool
        process, _index = self._process_by_pid(job._worker_pid)

        # Run timeout callback
        if job._timeout_callback is not None:
            job._timeout_callback(soft=False, timeout=job._timeout)
        if process:
            self._trywaitkill(process)

    def _trywaitkill(self, worker):
        debug('timeout: sending TERM to %s', worker._name)
        try:
            worker.terminate()
        except OSError:
            pass
        else:
            if worker._popen.wait(timeout=0.1):
                return
        debug('timeout: TERM timed-out, now sending KILL to %s', worker._name)
        try:
            _kill(worker.pid, signal.SIGKILL)
        except OSError:
            pass

    def handle_timeouts(self):
        cache = self.cache
        t_hard, t_soft = self.t_hard, self.t_soft
        dirty = set()
        on_soft_timeout = self.on_soft_timeout
        on_hard_timeout = self.on_hard_timeout

        def _timed_out(start, timeout):
            if not start or not timeout:
                return False
            if monotonic() >= start + timeout:
                return True

        # Inner-loop
        while self._state == RUN:

            # Remove dirty items not in cache anymore
            if dirty:
                dirty = set(k for k in dirty if k in cache)

            for i, job in list(cache.items()):
                ack_time = job._time_accepted
                soft_timeout = job._soft_timeout
                if soft_timeout is None:
                    soft_timeout = t_soft
                hard_timeout = job._timeout
                if hard_timeout is None:
                    hard_timeout = t_hard
                if _timed_out(ack_time, hard_timeout):
                    on_hard_timeout(job)
                elif i not in dirty and _timed_out(ack_time, soft_timeout):
                    on_soft_timeout(job)
                    dirty.add(i)
            yield

    def body(self):
        while self._state == RUN:
            try:
                for _ in self.handle_timeouts():
                    time.sleep(1.0)  # don't spin
            except CoroStop:
                break
        debug('timeout handler exiting')

    def handle_event(self, *args):
        if self._it is None:
            self._it = self.handle_timeouts()
        try:
            next(self._it)
        except StopIteration:
            self._it = None


class ResultHandler(PoolThread):

    def __init__(self, outqueue, get, cache, poll,
                 join_exited_workers, putlock, restart_state,
                 check_timeouts, on_job_ready):
        self.outqueue = outqueue
        self.get = get
        self.cache = cache
        self.poll = poll
        self.join_exited_workers = join_exited_workers
        self.putlock = putlock
        self.restart_state = restart_state
        self._it = None
        self._shutdown_complete = False
        self.check_timeouts = check_timeouts
        self.on_job_ready = on_job_ready
        self._make_methods()
        super(ResultHandler, self).__init__()

    def on_stop_not_started(self):
        # used when pool started without result handler thread.
        self.finish_at_shutdown(handle_timeouts=True)

    def _make_methods(self):
        cache = self.cache
        putlock = self.putlock
        restart_state = self.restart_state
        on_job_ready = self.on_job_ready

        def on_ack(job, i, time_accepted, pid, synqW_fd):
            restart_state.R = 0
            try:
                cache[job]._ack(i, time_accepted, pid, synqW_fd)
            except (KeyError, AttributeError):
                # Object gone or doesn't support _ack (e.g. IMAPIterator).
                pass

        def on_ready(job, i, obj, inqW_fd):
            if on_job_ready is not None:
                on_job_ready(job, i, obj, inqW_fd)
            try:
                item = cache[job]
            except KeyError:
                return
            if not item.ready():
                if putlock is not None:
                    putlock.release()
            try:
                item._set(i, obj)
            except KeyError:
                pass

        def on_death(pid, exitcode):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as exc:
                if get_errno(exc) != errno.ESRCH:
                    raise

        state_handlers = self.state_handlers = {
            ACK: on_ack, READY: on_ready, DEATH: on_death
        }

        def on_state_change(task):
            state, args = task
            try:
                state_handlers[state](*args)
            except KeyError:
                debug("Unknown job state: %s (args=%s)", state, args)
        self.on_state_change = on_state_change

    def _process_result(self, timeout=1.0):
        poll = self.poll
        on_state_change = self.on_state_change

        while 1:
            try:
                ready, task = poll(timeout)
            except (IOError, EOFError) as exc:
                debug('result handler got %r -- exiting', exc)
                raise CoroStop()

            if self._state:
                assert self._state == TERMINATE
                debug('result handler found thread._state=TERMINATE')
                raise CoroStop()

            if ready:
                if task is None:
                    debug('result handler got sentinel')
                    raise CoroStop()
                on_state_change(task)
                if timeout != 0:  # blocking
                    break
            else:
                break
            yield

    def handle_event(self, fileno=None, events=None):
        if self._state == RUN:
            if self._it is None:
                self._it = self._process_result(0)  # non-blocking
            try:
                next(self._it)
            except (StopIteration, CoroStop):
                self._it = None

    def body(self):
        debug('result handler starting')
        try:
            while self._state == RUN:
                try:
                    for _ in self._process_result(1.0):  # blocking
                        pass
                except CoroStop:
                    break
        finally:
            self.finish_at_shutdown()

    def finish_at_shutdown(self, handle_timeouts=False):
        self._shutdown_complete = True
        get = self.get
        outqueue = self.outqueue
        cache = self.cache
        poll = self.poll
        join_exited_workers = self.join_exited_workers
        check_timeouts = self.check_timeouts
        on_state_change = self.on_state_change

        time_terminate = None
        while cache and self._state != TERMINATE:
            if check_timeouts is not None:
                check_timeouts()
            try:
                ready, task = poll(1.0)
            except (IOError, EOFError) as exc:
                debug('result handler got %r -- exiting', exc)
                return

            if ready:
                if task is None:
                    debug('result handler ignoring extra sentinel')
                    continue

                on_state_change(task)
            try:
                join_exited_workers(shutdown=True)
            except WorkersJoined:
                now = monotonic()
                if not time_terminate:
                    time_terminate = now
                else:
                    if now - time_terminate > 5.0:
                        debug('result handler exiting: timed out')
                        break
                    debug('result handler: all workers terminated, '
                          'timeout in %ss',
                          abs(min(now - time_terminate - 5.0, 0)))

        if hasattr(outqueue, '_reader'):
            debug('ensuring that outqueue is not full')
            # If we don't make room available in outqueue then
            # attempts to add the sentinel (None) to outqueue may
            # block.  There is guaranteed to be no more than 2 sentinels.
            try:
                for i in range(10):
                    if not outqueue._reader.poll():
                        break
                    get()
            except (IOError, EOFError):
                pass

        debug('result handler exiting: len(cache)=%s, thread._state=%s',
              len(cache), self._state)


class Pool(object):
    '''
    Class which supports an async version of applying functions to arguments.
    '''
    Worker = Worker
    Supervisor = Supervisor
    TaskHandler = TaskHandler
    TimeoutHandler = TimeoutHandler
    ResultHandler = ResultHandler
    SoftTimeLimitExceeded = SoftTimeLimitExceeded

    def __init__(self, processes=None, initializer=None, initargs=(),
                 maxtasksperchild=None, timeout=None, soft_timeout=None,
                 lost_worker_timeout=None,
                 max_restarts=None, max_restart_freq=1,
                 on_process_up=None,
                 on_process_down=None,
                 on_timeout_set=None,
                 on_timeout_cancel=None,
                 threads=True,
                 semaphore=None,
                 putlocks=False,
                 allow_restart=False,
                 synack=False,
                 on_process_exit=None,
                 **kwargs):
        self.synack = synack
        self._setup_queues()
        self._taskqueue = Queue()
        self._cache = {}
        self._state = RUN
        self.timeout = timeout
        self.soft_timeout = soft_timeout
        self._maxtasksperchild = maxtasksperchild
        self._initializer = initializer
        self._initargs = initargs
        self._on_process_exit = on_process_exit
        self.lost_worker_timeout = lost_worker_timeout or LOST_WORKER_TIMEOUT
        self.on_process_up = on_process_up
        self.on_process_down = on_process_down
        self.on_timeout_set = on_timeout_set
        self.on_timeout_cancel = on_timeout_cancel
        self.threads = threads
        self.readers = {}
        self.allow_restart = allow_restart

        if soft_timeout and SIG_SOFT_TIMEOUT is None:
            warnings.warn(UserWarning(
                "Soft timeouts are not supported: "
                "on this platform: It does not have the SIGUSR1 signal.",
            ))
            soft_timeout = None

        self._processes = self.cpu_count() if processes is None else processes
        self.max_restarts = max_restarts or round(self._processes * 100)
        self.restart_state = restart_state(max_restarts, max_restart_freq or 1)

        if initializer is not None and not callable(initializer):
            raise TypeError('initializer must be a callable')

        if on_process_exit is not None and not callable(on_process_exit):
            raise TypeError('on_process_exit must be callable')

        self._pool = []
        self._poolctrl = {}
        self.putlocks = putlocks
        self._putlock = semaphore or LaxBoundedSemaphore(self._processes)
        for i in range(self._processes):
            self._create_worker_process(i)

        self._worker_handler = self.Supervisor(self)
        if threads:
            self._worker_handler.start()

        self._task_handler = self.TaskHandler(self._taskqueue,
                                              self._quick_put,
                                              self._outqueue,
                                              self._pool)
        if threads:
            self._task_handler.start()

        # Thread killing timedout jobs.
        self._timeout_handler = self.TimeoutHandler(
            self._pool, self._cache,
            self.soft_timeout, self.timeout,
        )
        self._timeout_handler_mutex = Lock()
        self._timeout_handler_started = False
        if self.timeout is not None or self.soft_timeout is not None:
            self._start_timeout_handler()

        # If running without threads, we need to check for timeouts
        # while waiting for unfinished work at shutdown.
        self.check_timeouts = None
        if not threads:
            self.check_timeouts = self._timeout_handler.handle_event

        # Thread processing results in the outqueue.
        self._result_handler = self.create_result_handler()
        self.handle_result_event = self._result_handler.handle_event

        if threads:
            self._result_handler.start()

        self._terminate = Finalize(
            self, self._terminate_pool,
            args=(self._taskqueue, self._inqueue, self._outqueue,
                  self._pool, self._worker_handler, self._task_handler,
                  self._result_handler, self._cache,
                  self._timeout_handler,
                  self._help_stuff_finish_args()),
            exitpriority=15,
        )

    def create_result_handler(self, **extra_kwargs):
        return self.ResultHandler(
            self._outqueue, self._quick_get, self._cache,
            self._poll_result, self._join_exited_workers,
            self._putlock, self.restart_state, self.check_timeouts,
            self.on_job_ready, **extra_kwargs
        )

    def on_job_ready(self, job, i, obj, inqW_fd):
        pass

    def _help_stuff_finish_args(self):
        return self._inqueue, self._task_handler, self._pool

    def cpu_count(self):
        try:
            return cpu_count()
        except NotImplementedError:
            return 1

    def handle_result_event(self, *args):
        return self._result_handler.handle_event(*args)

    def _process_register_queues(self, worker, queues):
        pass

    def _process_by_pid(self, pid):
        return next((
            (proc, i) for i, proc in enumerate(self._pool)
            if proc.pid == pid
        ), (None, None))

    def get_process_queues(self):
        return self._inqueue, self._outqueue, None

    def _create_worker_process(self, i):
        sentinel = Event() if self.allow_restart else None
        inq, outq, synq = self.get_process_queues()
        w = self.Worker(
            inq, outq, synq, self._initializer, self._initargs,
            self._maxtasksperchild, sentinel, self._on_process_exit,
            # Need to handle all signals if using the ipc semaphore,
            # to make sure the semaphore is released.
            sigprotection=self.threads,
        )
        self._pool.append(w)
        self._process_register_queues(w, (inq, outq, synq))
        w.name = w.name.replace('Process', 'PoolWorker')
        w.daemon = True
        w.index = i
        w.start()
        self._poolctrl[w.pid] = sentinel
        if self.on_process_up:
            self.on_process_up(w)
        return w

    def process_flush_queues(self, worker):
        pass

    def _join_exited_workers(self, shutdown=False):
        """Cleanup after any worker processes which have exited due to
        reaching their specified lifetime. Returns True if any workers were
        cleaned up.
        """
        now = None
        # The worker may have published a result before being terminated,
        # but we have no way to accurately tell if it did.  So we wait for
        # _lost_worker_timeout seconds before we mark the job with
        # WorkerLostError.
        for job in [job for job in list(self._cache.values())
                    if not job.ready() and job._worker_lost]:
            now = now or monotonic()
            lost_time, lost_ret = job._worker_lost
            if now - lost_time > job._lost_worker_timeout:
                self.mark_as_worker_lost(job, lost_ret)

        if shutdown and not len(self._pool):
            raise WorkersJoined()

        cleaned, exitcodes = {}, {}
        for i in reversed(range(len(self._pool))):
            worker = self._pool[i]
            exitcode = worker.exitcode
            popen = worker._popen
            if popen is None or exitcode is not None:
                # worker exited
                debug('Supervisor: cleaning up worker %d', i)
                if popen is not None:
                    worker.join()
                debug('Supervisor: worked %d joined', i)
                cleaned[worker.pid] = worker
                exitcodes[worker.pid] = exitcode
                if exitcode not in (EX_OK, EX_RECYCLE) and \
                        not getattr(worker, '_controlled_termination', False):
                    error(
                        'Process %r pid:%r exited with %r',
                        worker.name, worker.pid, human_status(exitcode),
                        exc_info=0,
                    )
                self.process_flush_queues(worker)
                del self._pool[i]
                del self._poolctrl[worker.pid]
        if cleaned:
            all_pids = [w.pid for w in self._pool]
            for job in list(self._cache.values()):
                acked_by_gone = next(
                    (pid for pid in job.worker_pids()
                     if pid in cleaned or pid not in all_pids),
                    None
                )
                # already accepted by process
                if acked_by_gone:
                    self.on_job_process_down(job, acked_by_gone)
                    if not job.ready():
                        exitcode = exitcodes.get(acked_by_gone) or 0
                        proc = cleaned.get(acked_by_gone)
                        if proc and getattr(proc, '_job_terminated', False):
                            job._set_terminated(exitcode)
                        else:
                            self.on_job_process_lost(
                                job, acked_by_gone, exitcode,
                            )
                else:
                    # started writing to
                    write_to = job._write_to
                    # was scheduled to write to
                    sched_for = job._scheduled_for

                    if write_to and not write_to._is_alive():
                        self.on_job_process_down(job, write_to.pid)
                    elif sched_for and not sched_for._is_alive():
                        self.on_job_process_down(job, sched_for.pid)

            for worker in values(cleaned):
                if self.on_process_down:
                    if not shutdown:
                        self._process_cleanup_queues(worker)
                    self.on_process_down(worker)
            return list(exitcodes.values())
        return []

    def on_partial_read(self, job, worker):
        pass

    def _process_cleanup_queues(self, worker):
        pass

    def on_job_process_down(self, job, pid_gone):
        pass

    def on_job_process_lost(self, job, pid, exitcode):
        job._worker_lost = (monotonic(), exitcode)

    def mark_as_worker_lost(self, job, exitcode):
        try:
            raise WorkerLostError(
                'Worker exited prematurely: {0}.'.format(
                    human_status(exitcode)),
            )
        except WorkerLostError:
            job._set(None, (False, ExceptionInfo()))
        else:  # pragma: no cover
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return self.terminate()

    def on_grow(self, n):
        pass

    def on_shrink(self, n):
        pass

    def shrink(self, n=1):
        for i, worker in enumerate(self._iterinactive()):
            self._processes -= 1
            if self._putlock:
                self._putlock.shrink()
            worker.terminate_controlled()
            self.on_shrink(1)
            if i >= n - 1:
                break
        else:
            raise ValueError("Can't shrink pool. All processes busy!")

    def grow(self, n=1):
        for i in range(n):
            self._processes += 1
            if self._putlock:
                self._putlock.grow()
        self.on_grow(n)

    def _iterinactive(self):
        for worker in self._pool:
            if not self._worker_active(worker):
                yield worker
        raise StopIteration()

    def _worker_active(self, worker):
        for job in values(self._cache):
            if worker.pid in job.worker_pids():
                return True
        return False

    def _repopulate_pool(self, exitcodes):
        """Bring the number of pool processes up to the specified number,
        for use after reaping workers which have exited.
        """
        for i in range(self._processes - len(self._pool)):
            if self._state != RUN:
                return
            try:
                if exitcodes and exitcodes[i] not in (EX_OK, EX_RECYCLE):
                    self.restart_state.step()
            except IndexError:
                self.restart_state.step()
            self._create_worker_process(self._avail_index())
            debug('added worker')

    def _avail_index(self):
        assert len(self._pool) < self._processes
        indices = set(p.index for p in self._pool)
        return next(i for i in range(self._processes) if i not in indices)

    def did_start_ok(self):
        return not self._join_exited_workers()

    def _maintain_pool(self):
        """"Clean up any exited workers and start replacements for them.
        """
        joined = self._join_exited_workers()
        self._repopulate_pool(joined)
        for i in range(len(joined)):
            if self._putlock is not None:
                self._putlock.release()

    def maintain_pool(self):
        if self._worker_handler._state == RUN and self._state == RUN:
            try:
                self._maintain_pool()
            except RestartFreqExceeded:
                self.close()
                self.join()
                raise
            except OSError as exc:
                if get_errno(exc) == errno.ENOMEM:
                    reraise(MemoryError,
                            MemoryError(str(exc)),
                            sys.exc_info()[2])
                raise

    def _setup_queues(self):
        from billiard.queues import SimpleQueue
        self._inqueue = SimpleQueue()
        self._outqueue = SimpleQueue()
        self._quick_put = self._inqueue._writer.send
        self._quick_get = self._outqueue._reader.recv

        def _poll_result(timeout):
            if self._outqueue._reader.poll(timeout):
                return True, self._quick_get()
            return False, None
        self._poll_result = _poll_result

    def _start_timeout_handler(self):
        # ensure more than one thread does not start the timeout handler
        # thread at once.
        if self.threads:
            with self._timeout_handler_mutex:
                if not self._timeout_handler_started:
                    self._timeout_handler_started = True
                    self._timeout_handler.start()

    def apply(self, func, args=(), kwds={}):
        '''
        Equivalent of `func(*args, **kwargs)`.
        '''
        if self._state == RUN:
            return self.apply_async(func, args, kwds).get()

    def starmap(self, func, iterable, chunksize=None):
        '''
        Like `map()` method but the elements of the `iterable` are expected to
        be iterables as well and will be unpacked as arguments. Hence
        `func` and (a, b) becomes func(a, b).
        '''
        if self._state == RUN:
            return self._map_async(func, iterable,
                                   starmapstar, chunksize).get()

    def starmap_async(self, func, iterable, chunksize=None,
                      callback=None, error_callback=None):
        '''
        Asynchronous version of `starmap()` method.
        '''
        if self._state == RUN:
            return self._map_async(func, iterable, starmapstar, chunksize,
                                   callback, error_callback)

    def map(self, func, iterable, chunksize=None):
        '''
        Apply `func` to each element in `iterable`, collecting the results
        in a list that is returned.
        '''
        if self._state == RUN:
            return self.map_async(func, iterable, chunksize).get()

    def imap(self, func, iterable, chunksize=1, lost_worker_timeout=None):
        '''
        Equivalent of `map()` -- can be MUCH slower than `Pool.map()`.
        '''
        if self._state != RUN:
            return
        lost_worker_timeout = lost_worker_timeout or self.lost_worker_timeout
        if chunksize == 1:
            result = IMapIterator(self._cache,
                                  lost_worker_timeout=lost_worker_timeout)
            self._taskqueue.put((
                ((TASK, (result._job, i, func, (x,), {}))
                 for i, x in enumerate(iterable)),
                result._set_length,
            ))
            return result
        else:
            assert chunksize > 1
            task_batches = Pool._get_tasks(func, iterable, chunksize)
            result = IMapIterator(self._cache,
                                  lost_worker_timeout=lost_worker_timeout)
            self._taskqueue.put((
                ((TASK, (result._job, i, mapstar, (x,), {}))
                 for i, x in enumerate(task_batches)),
                result._set_length,
            ))
            return (item for chunk in result for item in chunk)

    def imap_unordered(self, func, iterable, chunksize=1,
                       lost_worker_timeout=None):
        '''
        Like `imap()` method but ordering of results is arbitrary.
        '''
        if self._state != RUN:
            return
        lost_worker_timeout = lost_worker_timeout or self.lost_worker_timeout
        if chunksize == 1:
            result = IMapUnorderedIterator(
                self._cache, lost_worker_timeout=lost_worker_timeout,
            )
            self._taskqueue.put((
                ((TASK, (result._job, i, func, (x,), {}))
                 for i, x in enumerate(iterable)),
                result._set_length,
            ))
            return result
        else:
            assert chunksize > 1
            task_batches = Pool._get_tasks(func, iterable, chunksize)
            result = IMapUnorderedIterator(
                self._cache, lost_worker_timeout=lost_worker_timeout,
            )
            self._taskqueue.put((
                ((TASK, (result._job, i, mapstar, (x,), {}))
                 for i, x in enumerate(task_batches)),
                result._set_length,
            ))
            return (item for chunk in result for item in chunk)

    def apply_async(self, func, args=(), kwds={},
                    callback=None, error_callback=None, accept_callback=None,
                    timeout_callback=None, waitforslot=None,
                    soft_timeout=None, timeout=None, lost_worker_timeout=None,
                    callbacks_propagate=(),
                    correlation_id=None):
        '''
        Asynchronous equivalent of `apply()` method.

        Callback is called when the functions return value is ready.
        The accept callback is called when the job is accepted to be executed.

        Simplified the flow is like this:

            >>> def apply_async(func, args, kwds, callback, accept_callback):
            ...     if accept_callback:
            ...         accept_callback()
            ...     retval = func(*args, **kwds)
            ...     if callback:
            ...         callback(retval)

        '''
        if self._state != RUN:
            return
        soft_timeout = soft_timeout or self.soft_timeout
        timeout = timeout or self.timeout
        lost_worker_timeout = lost_worker_timeout or self.lost_worker_timeout
        if soft_timeout and SIG_SOFT_TIMEOUT is None:
            warnings.warn(UserWarning(
                "Soft timeouts are not supported: "
                "on this platform: It does not have the SIGUSR1 signal.",
            ))
            soft_timeout = None
        if self._state == RUN:
            waitforslot = self.putlocks if waitforslot is None else waitforslot
            if waitforslot and self._putlock is not None:
                self._putlock.acquire()
            result = ApplyResult(
                self._cache, callback, accept_callback, timeout_callback,
                error_callback, soft_timeout, timeout, lost_worker_timeout,
                on_timeout_set=self.on_timeout_set,
                on_timeout_cancel=self.on_timeout_cancel,
                callbacks_propagate=callbacks_propagate,
                send_ack=self.send_ack if self.synack else None,
                correlation_id=correlation_id,
            )
            if timeout or soft_timeout:
                # start the timeout handler thread when required.
                self._start_timeout_handler()
            if self.threads:
                self._taskqueue.put(([(TASK, (result._job, None,
                                    func, args, kwds))], None))
            else:
                self._quick_put((TASK, (result._job, None, func, args, kwds)))
            return result

    def send_ack(self, response, job, i, fd):
        pass

    def terminate_job(self, pid, sig=None):
        proc, _ = self._process_by_pid(pid)
        if proc is not None:
            try:
                _kill(pid, sig or signal.SIGTERM)
            except OSError as exc:
                if get_errno(exc) != errno.ESRCH:
                    raise
            else:
                proc._controlled_termination = True
                proc._job_terminated = True

    def map_async(self, func, iterable, chunksize=None,
                  callback=None, error_callback=None):
        '''
        Asynchronous equivalent of `map()` method.
        '''
        return self._map_async(
            func, iterable, mapstar, chunksize, callback, error_callback,
        )

    def _map_async(self, func, iterable, mapper, chunksize=None,
                   callback=None, error_callback=None):
        '''
        Helper function to implement map, starmap and their async counterparts.
        '''
        if self._state != RUN:
            return
        if not hasattr(iterable, '__len__'):
            iterable = list(iterable)

        if chunksize is None:
            chunksize, extra = divmod(len(iterable), len(self._pool) * 4)
            if extra:
                chunksize += 1
        if len(iterable) == 0:
            chunksize = 0

        task_batches = Pool._get_tasks(func, iterable, chunksize)
        result = MapResult(self._cache, chunksize, len(iterable), callback,
                           error_callback=error_callback)
        self._taskqueue.put((((TASK, (result._job, i, mapper, (x,), {}))
                              for i, x in enumerate(task_batches)), None))
        return result

    @staticmethod
    def _get_tasks(func, it, size):
        it = iter(it)
        while 1:
            x = tuple(itertools.islice(it, size))
            if not x:
                return
            yield (func, x)

    def __reduce__(self):
        raise NotImplementedError(
            'pool objects cannot be passed between processes or pickled',
        )

    def close(self):
        debug('closing pool')
        if self._state == RUN:
            self._state = CLOSE
            if self._putlock:
                self._putlock.clear()
            self._worker_handler.close()
            self._taskqueue.put(None)
            stop_if_not_current(self._worker_handler)

    def terminate(self):
        debug('terminating pool')
        self._state = TERMINATE
        self._worker_handler.terminate()
        self._terminate()

    @staticmethod
    def _stop_task_handler(task_handler):
        stop_if_not_current(task_handler)

    def join(self):
        assert self._state in (CLOSE, TERMINATE)
        debug('joining worker handler')
        stop_if_not_current(self._worker_handler)
        debug('joining task handler')
        self._stop_task_handler(self._task_handler)
        debug('joining result handler')
        stop_if_not_current(self._result_handler)
        debug('result handler joined')
        for i, p in enumerate(self._pool):
            debug('joining worker %s/%s (%r)', i+1, len(self._pool), p)
            if p._popen is not None:  # process started?
                p.join()
        debug('pool join complete')

    def restart(self):
        for e in values(self._poolctrl):
            e.set()

    @staticmethod
    def _help_stuff_finish(inqueue, task_handler, _pool):
        # task_handler may be blocked trying to put items on inqueue
        debug('removing tasks from inqueue until task handler finished')
        inqueue._rlock.acquire()
        while task_handler.is_alive() and inqueue._reader.poll():
            inqueue._reader.recv()
            time.sleep(0)

    @classmethod
    def _set_result_sentinel(cls, outqueue, pool):
        outqueue.put(None)

    @classmethod
    def _terminate_pool(cls, taskqueue, inqueue, outqueue, pool,
                        worker_handler, task_handler,
                        result_handler, cache, timeout_handler,
                        help_stuff_finish_args):

        # this is guaranteed to only be called once
        debug('finalizing pool')

        worker_handler.terminate()

        task_handler.terminate()
        taskqueue.put(None)                 # sentinel

        debug('helping task handler/workers to finish')
        cls._help_stuff_finish(*help_stuff_finish_args)

        result_handler.terminate()
        cls._set_result_sentinel(outqueue, pool)

        if timeout_handler is not None:
            timeout_handler.terminate()

        # Terminate workers which haven't already finished
        if pool and hasattr(pool[0], 'terminate'):
            debug('terminating workers')
            for p in pool:
                if p._is_alive():
                    p.terminate()

        debug('joining task handler')
        cls._stop_task_handler(task_handler)

        debug('joining result handler')
        result_handler.stop()

        if timeout_handler is not None:
            debug('joining timeout handler')
            timeout_handler.stop(TIMEOUT_MAX)

        if pool and hasattr(pool[0], 'terminate'):
            debug('joining pool workers')
            for p in pool:
                if p.is_alive():
                    # worker has not yet exited
                    debug('cleaning up worker %d', p.pid)
                    if p._popen is not None:
                        p.join()
            debug('pool workers joined')

    @property
    def process_sentinels(self):
        return [w._popen.sentinel for w in self._pool]

#
# Class whose instances are returned by `Pool.apply_async()`
#


class ApplyResult(object):
    _worker_lost = None
    _write_to = None
    _scheduled_for = None

    def __init__(self, cache, callback, accept_callback=None,
                 timeout_callback=None, error_callback=None, soft_timeout=None,
                 timeout=None, lost_worker_timeout=LOST_WORKER_TIMEOUT,
                 on_timeout_set=None, on_timeout_cancel=None,
                 callbacks_propagate=(), send_ack=None,
                 correlation_id=None):
        self.correlation_id = correlation_id
        self._mutex = Lock()
        self._event = threading.Event()
        self._job = next(job_counter)
        self._cache = cache
        self._callback = callback
        self._accept_callback = accept_callback
        self._error_callback = error_callback
        self._timeout_callback = timeout_callback
        self._timeout = timeout
        self._terminated = None
        self._soft_timeout = soft_timeout
        self._lost_worker_timeout = lost_worker_timeout
        self._on_timeout_set = on_timeout_set
        self._on_timeout_cancel = on_timeout_cancel
        self._callbacks_propagate = callbacks_propagate or ()
        self._send_ack = send_ack

        self._accepted = False
        self._cancelled = False
        self._worker_pid = None
        self._time_accepted = None
        cache[self._job] = self

    def __repr__(self):
        return '<Result: {id} ack:{ack} ready:{ready}>'.format(
            id=self._job, ack=self._accepted, ready=self.ready(),
        )

    def ready(self):
        return self._event.isSet()

    def accepted(self):
        return self._accepted

    def successful(self):
        assert self.ready()
        return self._success

    def _cancel(self):
        """Only works if synack is used."""
        self._cancelled = True

    def discard(self):
        self._cache.pop(self._job, None)

    def terminate(self, signum):
        self._terminated = signum

    def _set_terminated(self, signum=None):
        try:
            raise Terminated(-(signum or 0))
        except Terminated:
            self._set(None, (False, ExceptionInfo()))

    def worker_pids(self):
        return [self._worker_pid] if self._worker_pid else []

    def wait(self, timeout=None):
        self._event.wait(timeout)

    def get(self, timeout=None):
        self.wait(timeout)
        if not self.ready():
            raise TimeoutError
        if self._success:
            return self._value
        else:
            raise self._value.exception

    def safe_apply_callback(self, fun, *args):
        if fun:
            try:
                fun(*args)
            except self._callbacks_propagate:
                raise
            except Exception as exc:
                error('Pool callback raised exception: %r', exc,
                      exc_info=1)

    def _set(self, i, obj):
        with self._mutex:
            if self._on_timeout_cancel:
                self._on_timeout_cancel(self)
            self._success, self._value = obj
            self._event.set()
            if self._accepted:
                # if not accepted yet, then the set message
                # was received before the ack, which means
                # the ack will remove the entry.
                self._cache.pop(self._job, None)

            # apply callbacks last
            if self._callback and self._success:
                self.safe_apply_callback(
                    self._callback, self._value)
            if (self._value is not None and
                    self._error_callback and not self._success):
                self.safe_apply_callback(
                    self._error_callback, self._value)

    def _ack(self, i, time_accepted, pid, synqW_fd):
        with self._mutex:
            if self._cancelled and self._send_ack:
                self._accepted = True
                if synqW_fd:
                    return self._send_ack(NACK, pid, self._job, synqW_fd)
                return
            self._accepted = True
            self._time_accepted = time_accepted
            self._worker_pid = pid
            if self.ready():
                # ack received after set()
                self._cache.pop(self._job, None)
            if self._on_timeout_set:
                self._on_timeout_set(self, self._soft_timeout, self._timeout)
            response = ACK
            if self._accept_callback:
                try:
                    self._accept_callback(pid, time_accepted)
                except self._propagate_errors:
                    response = NACK
                    raise
                except Exception:
                    response = NACK
                    # ignore other errors
                finally:
                    if self._send_ack and synqW_fd:
                        return self._send_ack(
                            response, pid, self._job, synqW_fd
                        )
            if self._send_ack and synqW_fd:
                self._send_ack(response, pid, self._job, synqW_fd)

#
# Class whose instances are returned by `Pool.map_async()`
#


class MapResult(ApplyResult):

    def __init__(self, cache, chunksize, length, callback, error_callback):
        ApplyResult.__init__(
            self, cache, callback, error_callback=error_callback,
        )
        self._success = True
        self._length = length
        self._value = [None] * length
        self._accepted = [False] * length
        self._worker_pid = [None] * length
        self._time_accepted = [None] * length
        self._chunksize = chunksize
        if chunksize <= 0:
            self._number_left = 0
            self._event.set()
            del cache[self._job]
        else:
            self._number_left = length // chunksize + bool(length % chunksize)

    def _set(self, i, success_result):
        success, result = success_result
        if success:
            self._value[i * self._chunksize:(i + 1) * self._chunksize] = result
            self._number_left -= 1
            if self._number_left == 0:
                if self._callback:
                    self._callback(self._value)
                if self._accepted:
                    self._cache.pop(self._job, None)
                self._event.set()
        else:
            self._success = False
            self._value = result
            if self._error_callback:
                self._error_callback(self._value)
            if self._accepted:
                self._cache.pop(self._job, None)
            self._event.set()

    def _ack(self, i, time_accepted, pid):
        start = i * self._chunksize
        stop = (i + 1) * self._chunksize
        for j in range(start, stop):
            self._accepted[j] = True
            self._worker_pid[j] = pid
            self._time_accepted[j] = time_accepted
        if self.ready():
            self._cache.pop(self._job, None)

    def accepted(self):
        return all(self._accepted)

    def worker_pids(self):
        return [pid for pid in self._worker_pid if pid]

#
# Class whose instances are returned by `Pool.imap()`
#


class IMapIterator(object):
    _worker_lost = None

    def __init__(self, cache, lost_worker_timeout=LOST_WORKER_TIMEOUT):
        self._cond = threading.Condition(threading.Lock())
        self._job = next(job_counter)
        self._cache = cache
        self._items = deque()
        self._index = 0
        self._length = None
        self._ready = False
        self._unsorted = {}
        self._worker_pids = []
        self._lost_worker_timeout = lost_worker_timeout
        cache[self._job] = self

    def __iter__(self):
        return self

    def next(self, timeout=None):
        with self._cond:
            try:
                item = self._items.popleft()
            except IndexError:
                if self._index == self._length:
                    self._ready = True
                    raise StopIteration
                self._cond.wait(timeout)
                try:
                    item = self._items.popleft()
                except IndexError:
                    if self._index == self._length:
                        self._ready = True
                        raise StopIteration
                    raise TimeoutError

        success, value = item
        if success:
            return value
        raise Exception(value)

    __next__ = next                    # XXX

    def _set(self, i, obj):
        with self._cond:
            if self._index == i:
                self._items.append(obj)
                self._index += 1
                while self._index in self._unsorted:
                    obj = self._unsorted.pop(self._index)
                    self._items.append(obj)
                    self._index += 1
                self._cond.notify()
            else:
                self._unsorted[i] = obj

            if self._index == self._length:
                self._ready = True
                del self._cache[self._job]

    def _set_length(self, length):
        with self._cond:
            self._length = length
            if self._index == self._length:
                self._ready = True
                self._cond.notify()
                del self._cache[self._job]

    def _ack(self, i, time_accepted, pid):
        self._worker_pids.append(pid)

    def ready(self):
        return self._ready

    def worker_pids(self):
        return self._worker_pids

#
# Class whose instances are returned by `Pool.imap_unordered()`
#


class IMapUnorderedIterator(IMapIterator):

    def _set(self, i, obj):
        with self._cond:
            self._items.append(obj)
            self._index += 1
            self._cond.notify()
            if self._index == self._length:
                self._ready = True
                del self._cache[self._job]

#
#
#


class ThreadPool(Pool):

    from billiard.dummy import Process as DummyProcess
    Process = DummyProcess

    def __init__(self, processes=None, initializer=None, initargs=()):
        Pool.__init__(self, processes, initializer, initargs)

    def _setup_queues(self):
        self._inqueue = Queue()
        self._outqueue = Queue()
        self._quick_put = self._inqueue.put
        self._quick_get = self._outqueue.get

        def _poll_result(timeout):
            try:
                return True, self._quick_get(timeout=timeout)
            except Empty:
                return False, None
        self._poll_result = _poll_result

    @staticmethod
    def _help_stuff_finish(inqueue, task_handler, pool):
        # put sentinels at head of inqueue to make workers finish
        with inqueue.not_empty:
            inqueue.queue.clear()
            inqueue.queue.extend([None] * len(pool))
            inqueue.not_empty.notify_all()

########NEW FILE########
__FILENAME__ = process
#
# Module providing the `Process` class which emulates `threading.Thread`
#
# multiprocessing/process.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#
from __future__ import absolute_import

__all__ = ['Process', 'current_process', 'active_children']

#
# Imports
#

import os
import sys
import signal
import itertools
import binascii
import logging
import threading

from multiprocessing import process as _mproc

from .compat import bytes
try:
    from _weakrefset import WeakSet
except ImportError:
    WeakSet = None  # noqa
from .five import items, string_t

try:
    ORIGINAL_DIR = os.path.abspath(os.getcwd())
except OSError:
    ORIGINAL_DIR = None

#
# Public functions
#


def current_process():
    '''
    Return process object representing the current process
    '''
    return _current_process


def _set_current_process(process):
    global _current_process
    _current_process = _mproc._current_process = process


def _cleanup():
    # check for processes which have finished
    if _current_process is not None:
        for p in list(_current_process._children):
            if p._popen.poll() is not None:
                _current_process._children.discard(p)


def _maybe_flush(f):
    try:
        f.flush()
    except (AttributeError, EnvironmentError, NotImplementedError):
        pass


def active_children(_cleanup=_cleanup):
    '''
    Return list of process objects corresponding to live child processes
    '''
    try:
        _cleanup()
    except TypeError:
        # called after gc collect so _cleanup does not exist anymore
        return []
    if _current_process is not None:
        return list(_current_process._children)
    return []


class Process(object):
    '''
    Process objects represent activity that is run in a separate process

    The class is analagous to `threading.Thread`
    '''
    _Popen = None

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, daemon=None, **_kw):
        assert group is None, 'group argument must be None for now'
        count = next(_current_process._counter)
        self._identity = _current_process._identity + (count,)
        self._authkey = _current_process._authkey
        if daemon is not None:
            self._daemonic = daemon
        else:
            self._daemonic = _current_process._daemonic
        self._tempdir = _current_process._tempdir
        self._semprefix = _current_process._semprefix
        self._unlinkfd = _current_process._unlinkfd
        self._parent_pid = os.getpid()
        self._popen = None
        self._target = target
        self._args = tuple(args)
        self._kwargs = dict(kwargs)
        self._name = (
            name or type(self).__name__ + '-' +
            ':'.join(str(i) for i in self._identity)
        )
        if _dangling is not None:
            _dangling.add(self)

    def run(self):
        '''
        Method to be run in sub-process; can be overridden in sub-class
        '''
        if self._target:
            self._target(*self._args, **self._kwargs)

    def start(self):
        '''
        Start child process
        '''
        assert self._popen is None, 'cannot start a process twice'
        assert self._parent_pid == os.getpid(), \
            'can only start a process object created by current process'
        _cleanup()
        if self._Popen is not None:
            Popen = self._Popen
        else:
            from .forking import Popen
        self._popen = Popen(self)
        self._sentinel = self._popen.sentinel
        _current_process._children.add(self)

    def terminate(self):
        '''
        Terminate process; sends SIGTERM signal or uses TerminateProcess()
        '''
        self._popen.terminate()

    def join(self, timeout=None):
        '''
        Wait until child process terminates
        '''
        assert self._parent_pid == os.getpid(), 'can only join a child process'
        assert self._popen is not None, 'can only join a started process'
        res = self._popen.wait(timeout)
        if res is not None:
            _current_process._children.discard(self)

    def is_alive(self):
        '''
        Return whether process is alive
        '''
        if self is _current_process:
            return True
        assert self._parent_pid == os.getpid(), 'can only test a child process'
        if self._popen is None:
            return False
        self._popen.poll()
        return self._popen.returncode is None

    def _is_alive(self):
        if self._popen is None:
            return False
        return self._popen.poll() is None

    def _get_name(self):
        return self._name

    def _set_name(self, value):
        assert isinstance(name, string_t), 'name must be a string'
        self._name = value
    name = property(_get_name, _set_name)

    def _get_daemon(self):
        return self._daemonic

    def _set_daemon(self, daemonic):
        assert self._popen is None, 'process has already started'
        self._daemonic = daemonic
    daemon = property(_get_daemon, _set_daemon)

    def _get_authkey(self):
        return self._authkey

    def _set_authkey(self, authkey):
        self._authkey = AuthenticationString(authkey)
    authkey = property(_get_authkey, _set_authkey)

    @property
    def exitcode(self):
        '''
        Return exit code of process or `None` if it has yet to stop
        '''
        if self._popen is None:
            return self._popen
        return self._popen.poll()

    @property
    def ident(self):
        '''
        Return identifier (PID) of process or `None` if it has yet to start
        '''
        if self is _current_process:
            return os.getpid()
        else:
            return self._popen and self._popen.pid

    pid = ident

    @property
    def sentinel(self):
        '''
        Return a file descriptor (Unix) or handle (Windows) suitable for
        waiting for process termination.
        '''
        try:
            return self._sentinel
        except AttributeError:
            raise ValueError("process not started")

    def __repr__(self):
        if self is _current_process:
            status = 'started'
        elif self._parent_pid != os.getpid():
            status = 'unknown'
        elif self._popen is None:
            status = 'initial'
        else:
            if self._popen.poll() is not None:
                status = self.exitcode
            else:
                status = 'started'

        if type(status) is int:
            if status == 0:
                status = 'stopped'
            else:
                status = 'stopped[%s]' % _exitcode_to_name.get(status, status)

        return '<%s(%s, %s%s)>' % (type(self).__name__, self._name,
                                   status, self._daemonic and ' daemon' or '')

    ##

    def _bootstrap(self):
        from . import util
        global _current_process

        try:
            self._children = set()
            self._counter = itertools.count(1)
            if sys.stdin is not None:
                try:
                    sys.stdin.close()
                    sys.stdin = open(os.devnull)
                except (OSError, ValueError):
                    pass
            old_process = _current_process
            _set_current_process(self)

            # Re-init logging system.
            # Workaround for http://bugs.python.org/issue6721/#msg140215
            # Python logging module uses RLock() objects which are broken
            # after fork. This can result in a deadlock (Celery Issue #496).
            loggerDict = logging.Logger.manager.loggerDict
            logger_names = list(loggerDict.keys())
            logger_names.append(None)  # for root logger
            for name in logger_names:
                if not name or not isinstance(loggerDict[name],
                                              logging.PlaceHolder):
                    for handler in logging.getLogger(name).handlers:
                        handler.createLock()
            logging._lock = threading.RLock()

            try:
                util._finalizer_registry.clear()
                util._run_after_forkers()
            finally:
                # delay finalization of the old process object until after
                # _run_after_forkers() is executed
                del old_process
            util.info('child process %s calling self.run()', self.pid)
            try:
                self.run()
                exitcode = 0
            finally:
                util._exit_function()
        except SystemExit as exc:
            if not exc.args:
                exitcode = 1
            elif isinstance(exc.args[0], int):
                exitcode = exc.args[0]
            else:
                sys.stderr.write(str(exc.args[0]) + '\n')
                _maybe_flush(sys.stderr)
                exitcode = 0 if isinstance(exc.args[0], str) else 1
        except:
            exitcode = 1
            if not util.error('Process %s', self.name, exc_info=True):
                import traceback
                sys.stderr.write('Process %s:\n' % self.name)
                traceback.print_exc()
        finally:
            util.info('process %s exiting with exitcode %d',
                      self.pid, exitcode)
            _maybe_flush(sys.stdout)
            _maybe_flush(sys.stderr)
        return exitcode

#
# We subclass bytes to avoid accidental transmission of auth keys over network
#


class AuthenticationString(bytes):

    def __reduce__(self):
        from .forking import Popen

        if not Popen.thread_is_spawning():
            raise TypeError(
                'Pickling an AuthenticationString object is '
                'disallowed for security reasons')
        return AuthenticationString, (bytes(self),)

#
# Create object representing the main process
#


class _MainProcess(Process):

    def __init__(self):
        self._identity = ()
        self._daemonic = False
        self._name = 'MainProcess'
        self._parent_pid = None
        self._popen = None
        self._counter = itertools.count(1)
        self._children = set()
        self._authkey = AuthenticationString(os.urandom(32))
        self._tempdir = None
        self._semprefix = 'mp-' + binascii.hexlify(
            os.urandom(4)).decode('ascii')
        self._unlinkfd = None

_current_process = _MainProcess()
del _MainProcess

#
# Give names to some return codes
#

_exitcode_to_name = {}

for name, signum in items(signal.__dict__):
    if name[:3] == 'SIG' and '_' not in name:
        _exitcode_to_name[-signum] = name

_dangling = WeakSet() if WeakSet is not None else None

########NEW FILE########
__FILENAME__ = connection
#
# A higher level module for using sockets (or Windows named pipes)
#
# multiprocessing/connection.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#

from __future__ import absolute_import

__all__ = ['Client', 'Listener', 'Pipe']

import os
import sys
import socket
import errno
import time
import tempfile
import itertools

from .. import AuthenticationError
from .. import reduction
from .._ext import _billiard, win32
from ..compat import get_errno, setblocking, bytes as cbytes
from ..five import monotonic
from ..forking import duplicate, close
from ..reduction import ForkingPickler
from ..util import get_temp_dir, Finalize, sub_debug, debug

try:
    WindowsError = WindowsError  # noqa
except NameError:
    WindowsError = None  # noqa


# global set later
xmlrpclib = None

Connection = getattr(_billiard, 'Connection', None)
PipeConnection = getattr(_billiard, 'PipeConnection', None)


#
#
#

BUFSIZE = 8192
# A very generous timeout when it comes to local connections...
CONNECTION_TIMEOUT = 20.

_mmap_counter = itertools.count()

default_family = 'AF_INET'
families = ['AF_INET']

if hasattr(socket, 'AF_UNIX'):
    default_family = 'AF_UNIX'
    families += ['AF_UNIX']

if sys.platform == 'win32':
    default_family = 'AF_PIPE'
    families += ['AF_PIPE']


def _init_timeout(timeout=CONNECTION_TIMEOUT):
    return monotonic() + timeout


def _check_timeout(t):
    return monotonic() > t

#
#
#


def arbitrary_address(family):
    '''
    Return an arbitrary free address for the given family
    '''
    if family == 'AF_INET':
        return ('localhost', 0)
    elif family == 'AF_UNIX':
        return tempfile.mktemp(prefix='listener-', dir=get_temp_dir())
    elif family == 'AF_PIPE':
        return tempfile.mktemp(prefix=r'\\.\pipe\pyc-%d-%d-' %
                               (os.getpid(), next(_mmap_counter)))
    else:
        raise ValueError('unrecognized family')


def address_type(address):
    '''
    Return the types of the address

    This can be 'AF_INET', 'AF_UNIX', or 'AF_PIPE'
    '''
    if type(address) == tuple:
        return 'AF_INET'
    elif type(address) is str and address.startswith('\\\\'):
        return 'AF_PIPE'
    elif type(address) is str:
        return 'AF_UNIX'
    else:
        raise ValueError('address type of %r unrecognized' % address)

#
# Public functions
#


class Listener(object):
    '''
    Returns a listener object.

    This is a wrapper for a bound socket which is 'listening' for
    connections, or for a Windows named pipe.
    '''
    def __init__(self, address=None, family=None, backlog=1, authkey=None):
        family = (family or
                  (address and address_type(address)) or
                  default_family)
        address = address or arbitrary_address(family)

        if family == 'AF_PIPE':
            self._listener = PipeListener(address, backlog)
        else:
            self._listener = SocketListener(address, family, backlog)

        if authkey is not None and not isinstance(authkey, bytes):
            raise TypeError('authkey should be a byte string')

        self._authkey = authkey

    def accept(self):
        '''
        Accept a connection on the bound socket or named pipe of `self`.

        Returns a `Connection` object.
        '''
        if self._listener is None:
            raise IOError('listener is closed')
        c = self._listener.accept()
        if self._authkey:
            deliver_challenge(c, self._authkey)
            answer_challenge(c, self._authkey)
        return c

    def close(self):
        '''
        Close the bound socket or named pipe of `self`.
        '''
        if self._listener is not None:
            self._listener.close()
            self._listener = None

    address = property(lambda self: self._listener._address)
    last_accepted = property(lambda self: self._listener._last_accepted)

    def __enter__(self):
        return self

    def __exit__(self, *exc_args):
        self.close()


def Client(address, family=None, authkey=None):
    '''
    Returns a connection to the address of a `Listener`
    '''
    family = family or address_type(address)
    if family == 'AF_PIPE':
        c = PipeClient(address)
    else:
        c = SocketClient(address)

    if authkey is not None and not isinstance(authkey, bytes):
        raise TypeError('authkey should be a byte string')

    if authkey is not None:
        answer_challenge(c, authkey)
        deliver_challenge(c, authkey)

    return c


if sys.platform != 'win32':

    def Pipe(duplex=True, rnonblock=False, wnonblock=False):
        '''
        Returns pair of connection objects at either end of a pipe
        '''
        if duplex:
            s1, s2 = socket.socketpair()
            s1.setblocking(not rnonblock)
            s2.setblocking(not wnonblock)
            c1 = Connection(os.dup(s1.fileno()))
            c2 = Connection(os.dup(s2.fileno()))
            s1.close()
            s2.close()
        else:
            fd1, fd2 = os.pipe()
            if rnonblock:
                setblocking(fd1, 0)
            if wnonblock:
                setblocking(fd2, 0)
            c1 = Connection(fd1, writable=False)
            c2 = Connection(fd2, readable=False)

        return c1, c2

else:

    def Pipe(duplex=True, rnonblock=False, wnonblock=False):  # noqa
        '''
        Returns pair of connection objects at either end of a pipe
        '''
        address = arbitrary_address('AF_PIPE')
        if duplex:
            openmode = win32.PIPE_ACCESS_DUPLEX
            access = win32.GENERIC_READ | win32.GENERIC_WRITE
            obsize, ibsize = BUFSIZE, BUFSIZE
        else:
            openmode = win32.PIPE_ACCESS_INBOUND
            access = win32.GENERIC_WRITE
            obsize, ibsize = 0, BUFSIZE

        h1 = win32.CreateNamedPipe(
            address, openmode,
            win32.PIPE_TYPE_MESSAGE | win32.PIPE_READMODE_MESSAGE |
            win32.PIPE_WAIT,
            1, obsize, ibsize, win32.NMPWAIT_WAIT_FOREVER, win32.NULL
        )
        h2 = win32.CreateFile(
            address, access, 0, win32.NULL, win32.OPEN_EXISTING, 0, win32.NULL
        )
        win32.SetNamedPipeHandleState(
            h2, win32.PIPE_READMODE_MESSAGE, None, None
        )

        try:
            win32.ConnectNamedPipe(h1, win32.NULL)
        except WindowsError as exc:
            if exc.args[0] != win32.ERROR_PIPE_CONNECTED:
                raise

        c1 = PipeConnection(h1, writable=duplex)
        c2 = PipeConnection(h2, readable=duplex)

        return c1, c2

#
# Definitions for connections based on sockets
#


class SocketListener(object):
    '''
    Representation of a socket which is bound to an address and listening
    '''
    def __init__(self, address, family, backlog=1):
        self._socket = socket.socket(getattr(socket, family))
        try:
            # SO_REUSEADDR has different semantics on Windows (Issue #2550).
            if os.name == 'posix':
                self._socket.setsockopt(socket.SOL_SOCKET,
                                        socket.SO_REUSEADDR, 1)
            self._socket.bind(address)
            self._socket.listen(backlog)
            self._address = self._socket.getsockname()
        except OSError:
            self._socket.close()
            raise
        self._family = family
        self._last_accepted = None

        if family == 'AF_UNIX':
            self._unlink = Finalize(
                self, os.unlink, args=(address,), exitpriority=0
            )
        else:
            self._unlink = None

    def accept(self):
        s, self._last_accepted = self._socket.accept()
        fd = duplicate(s.fileno())
        conn = Connection(fd)
        s.close()
        return conn

    def close(self):
        self._socket.close()
        if self._unlink is not None:
            self._unlink()


def SocketClient(address):
    '''
    Return a connection object connected to the socket given by `address`
    '''
    family = address_type(address)
    s = socket.socket(getattr(socket, family))
    t = _init_timeout()

    while 1:
        try:
            s.connect(address)
        except socket.error as exc:
            if get_errno(exc) != errno.ECONNREFUSED or _check_timeout(t):
                debug('failed to connect to address %s', address)
                raise
            time.sleep(0.01)
        else:
            break
    else:
        raise

    fd = duplicate(s.fileno())
    conn = Connection(fd)
    s.close()
    return conn

#
# Definitions for connections based on named pipes
#

if sys.platform == 'win32':

    class PipeListener(object):
        '''
        Representation of a named pipe
        '''
        def __init__(self, address, backlog=None):
            self._address = address
            handle = win32.CreateNamedPipe(
                address, win32.PIPE_ACCESS_DUPLEX,
                win32.PIPE_TYPE_MESSAGE | win32.PIPE_READMODE_MESSAGE |
                win32.PIPE_WAIT,
                win32.PIPE_UNLIMITED_INSTANCES, BUFSIZE, BUFSIZE,
                win32.NMPWAIT_WAIT_FOREVER, win32.NULL
            )
            self._handle_queue = [handle]
            self._last_accepted = None

            sub_debug('listener created with address=%r', self._address)

            self.close = Finalize(
                self, PipeListener._finalize_pipe_listener,
                args=(self._handle_queue, self._address), exitpriority=0
            )

        def accept(self):
            newhandle = win32.CreateNamedPipe(
                self._address, win32.PIPE_ACCESS_DUPLEX,
                win32.PIPE_TYPE_MESSAGE | win32.PIPE_READMODE_MESSAGE |
                win32.PIPE_WAIT,
                win32.PIPE_UNLIMITED_INSTANCES, BUFSIZE, BUFSIZE,
                win32.NMPWAIT_WAIT_FOREVER, win32.NULL
            )
            self._handle_queue.append(newhandle)
            handle = self._handle_queue.pop(0)
            try:
                win32.ConnectNamedPipe(handle, win32.NULL)
            except WindowsError as exc:
                if exc.args[0] != win32.ERROR_PIPE_CONNECTED:
                    raise
            return PipeConnection(handle)

        @staticmethod
        def _finalize_pipe_listener(queue, address):
            sub_debug('closing listener with address=%r', address)
            for handle in queue:
                close(handle)

    def PipeClient(address):
        '''
        Return a connection object connected to the pipe given by `address`
        '''
        t = _init_timeout()
        while 1:
            try:
                win32.WaitNamedPipe(address, 1000)
                h = win32.CreateFile(
                    address, win32.GENERIC_READ | win32.GENERIC_WRITE,
                    0, win32.NULL, win32.OPEN_EXISTING, 0, win32.NULL,
                )
            except WindowsError as exc:
                if exc.args[0] not in (
                        win32.ERROR_SEM_TIMEOUT,
                        win32.ERROR_PIPE_BUSY) or _check_timeout(t):
                    raise
            else:
                break
        else:
            raise

        win32.SetNamedPipeHandleState(
            h, win32.PIPE_READMODE_MESSAGE, None, None
        )
        return PipeConnection(h)

#
# Authentication stuff
#

MESSAGE_LENGTH = 20

CHALLENGE = cbytes('#CHALLENGE#', 'ascii')
WELCOME = cbytes('#WELCOME#', 'ascii')
FAILURE = cbytes('#FAILURE#', 'ascii')


def deliver_challenge(connection, authkey):
    import hmac
    assert isinstance(authkey, bytes)
    message = os.urandom(MESSAGE_LENGTH)
    connection.send_bytes(CHALLENGE + message)
    digest = hmac.new(authkey, message).digest()
    response = connection.recv_bytes(256)        # reject large message
    if response == digest:
        connection.send_bytes(WELCOME)
    else:
        connection.send_bytes(FAILURE)
        raise AuthenticationError('digest received was wrong')


def answer_challenge(connection, authkey):
    import hmac
    assert isinstance(authkey, bytes)
    message = connection.recv_bytes(256)         # reject large message
    assert message[:len(CHALLENGE)] == CHALLENGE, 'message = %r' % message
    message = message[len(CHALLENGE):]
    digest = hmac.new(authkey, message).digest()
    connection.send_bytes(digest)
    response = connection.recv_bytes(256)        # reject large message
    if response != WELCOME:
        raise AuthenticationError('digest sent was rejected')

#
# Support for using xmlrpclib for serialization
#


class ConnectionWrapper(object):
    def __init__(self, conn, dumps, loads):
        self._conn = conn
        self._dumps = dumps
        self._loads = loads
        for attr in ('fileno', 'close', 'poll', 'recv_bytes', 'send_bytes'):
            obj = getattr(conn, attr)
            setattr(self, attr, obj)

    def send(self, obj):
        s = self._dumps(obj)
        self._conn.send_bytes(s)

    def recv(self):
        s = self._conn.recv_bytes()
        return self._loads(s)


def _xml_dumps(obj):
    return xmlrpclib.dumps((obj,), None, None, None, 1).encode('utf8')


def _xml_loads(s):
    (obj,), method = xmlrpclib.loads(s.decode('utf8'))
    return obj


class XmlListener(Listener):
    def accept(self):
        global xmlrpclib
        import xmlrpclib  # noqa
        obj = Listener.accept(self)
        return ConnectionWrapper(obj, _xml_dumps, _xml_loads)


def XmlClient(*args, **kwds):
    global xmlrpclib
    import xmlrpclib  # noqa
    return ConnectionWrapper(Client(*args, **kwds), _xml_dumps, _xml_loads)


if sys.platform == 'win32':
    ForkingPickler.register(socket.socket, reduction.reduce_socket)
    ForkingPickler.register(Connection, reduction.reduce_connection)
    ForkingPickler.register(PipeConnection, reduction.reduce_pipe_connection)
else:
    ForkingPickler.register(socket.socket, reduction.reduce_socket)
    ForkingPickler.register(Connection, reduction.reduce_connection)

########NEW FILE########
__FILENAME__ = reduction
#
# Module to allow connection and socket objects to be transferred
# between processes
#
# multiprocessing/reduction.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#

from __future__ import absolute_import

__all__ = []

import os
import sys
import socket
import threading

from pickle import Pickler

from .. import current_process
from .._ext import _billiard, win32
from ..util import register_after_fork, debug, sub_debug

is_win32 = sys.platform == 'win32'
is_pypy = hasattr(sys, 'pypy_version_info')
is_py3k = sys.version_info[0] == 3

if not(is_win32 or is_pypy or is_py3k or hasattr(_billiard, 'recvfd')):
    raise ImportError('pickling of connections not supported')

close = win32.CloseHandle if sys.platform == 'win32' else os.close

# globals set later
_listener = None
_lock = None
_cache = set()

#
# ForkingPickler
#


class ForkingPickler(Pickler):  # noqa
    dispatch = Pickler.dispatch.copy()

    @classmethod
    def register(cls, type, reduce):
        def dispatcher(self, obj):
            rv = reduce(obj)
            self.save_reduce(obj=obj, *rv)
        cls.dispatch[type] = dispatcher


def _reduce_method(m):  # noqa
    if m.__self__ is None:
        return getattr, (m.__self__.__class__, m.__func__.__name__)
    else:
        return getattr, (m.__self__, m.__func__.__name__)
ForkingPickler.register(type(ForkingPickler.save), _reduce_method)


def _reduce_method_descriptor(m):
    return getattr, (m.__objclass__, m.__name__)
ForkingPickler.register(type(list.append), _reduce_method_descriptor)
ForkingPickler.register(type(int.__add__), _reduce_method_descriptor)

try:
    from functools import partial
except ImportError:
    pass
else:

    def _reduce_partial(p):
        return _rebuild_partial, (p.func, p.args, p.keywords or {})

    def _rebuild_partial(func, args, keywords):
        return partial(func, *args, **keywords)
    ForkingPickler.register(partial, _reduce_partial)


def dump(obj, file, protocol=None):
    ForkingPickler(file, protocol).dump(obj)

#
# Platform specific definitions
#

if sys.platform == 'win32':
    # XXX Should this subprocess import be here?
    import _subprocess  # noqa

    def send_handle(conn, handle, destination_pid):
        from ..forking import duplicate
        process_handle = win32.OpenProcess(
            win32.PROCESS_ALL_ACCESS, False, destination_pid
        )
        try:
            new_handle = duplicate(handle, process_handle)
            conn.send(new_handle)
        finally:
            close(process_handle)

    def recv_handle(conn):
        return conn.recv()

else:
    def send_handle(conn, handle, destination_pid):  # noqa
        _billiard.sendfd(conn.fileno(), handle)

    def recv_handle(conn):  # noqa
        return _billiard.recvfd(conn.fileno())

#
# Support for a per-process server thread which caches pickled handles
#


def _reset(obj):
    global _lock, _listener, _cache
    for h in _cache:
        close(h)
    _cache.clear()
    _lock = threading.Lock()
    _listener = None

_reset(None)
register_after_fork(_reset, _reset)


def _get_listener():
    global _listener

    if _listener is None:
        _lock.acquire()
        try:
            if _listener is None:
                from ..connection import Listener
                debug('starting listener and thread for sending handles')
                _listener = Listener(authkey=current_process().authkey)
                t = threading.Thread(target=_serve)
                t.daemon = True
                t.start()
        finally:
            _lock.release()

    return _listener


def _serve():
    from ..util import is_exiting, sub_warning

    while 1:
        try:
            conn = _listener.accept()
            handle_wanted, destination_pid = conn.recv()
            _cache.remove(handle_wanted)
            send_handle(conn, handle_wanted, destination_pid)
            close(handle_wanted)
            conn.close()
        except:
            if not is_exiting():
                sub_warning('thread for sharing handles raised exception',
                            exc_info=True)

#
# Functions to be used for pickling/unpickling objects with handles
#


def reduce_handle(handle):
    from ..forking import Popen, duplicate
    if Popen.thread_is_spawning():
        return (None, Popen.duplicate_for_child(handle), True)
    dup_handle = duplicate(handle)
    _cache.add(dup_handle)
    sub_debug('reducing handle %d', handle)
    return (_get_listener().address, dup_handle, False)


def rebuild_handle(pickled_data):
    from ..connection import Client
    address, handle, inherited = pickled_data
    if inherited:
        return handle
    sub_debug('rebuilding handle %d', handle)
    conn = Client(address, authkey=current_process().authkey)
    conn.send((handle, os.getpid()))
    new_handle = recv_handle(conn)
    conn.close()
    return new_handle

#
# Register `_billiard.Connection` with `ForkingPickler`
#


def reduce_connection(conn):
    rh = reduce_handle(conn.fileno())
    return rebuild_connection, (rh, conn.readable, conn.writable)


def rebuild_connection(reduced_handle, readable, writable):
    handle = rebuild_handle(reduced_handle)
    return _billiard.Connection(
        handle, readable=readable, writable=writable
    )

# Register `socket.socket` with `ForkingPickler`
#


def fromfd(fd, family, type_, proto=0):
    s = socket.fromfd(fd, family, type_, proto)
    if s.__class__ is not socket.socket:
        s = socket.socket(_sock=s)
    return s


def reduce_socket(s):
    reduced_handle = reduce_handle(s.fileno())
    return rebuild_socket, (reduced_handle, s.family, s.type, s.proto)


def rebuild_socket(reduced_handle, family, type_, proto):
    fd = rebuild_handle(reduced_handle)
    _sock = fromfd(fd, family, type_, proto)
    close(fd)
    return _sock

ForkingPickler.register(socket.socket, reduce_socket)

#
# Register `_billiard.PipeConnection` with `ForkingPickler`
#

if sys.platform == 'win32':

    def reduce_pipe_connection(conn):
        rh = reduce_handle(conn.fileno())
        return rebuild_pipe_connection, (rh, conn.readable, conn.writable)

    def rebuild_pipe_connection(reduced_handle, readable, writable):
        handle = rebuild_handle(reduced_handle)
        return _billiard.PipeConnection(
            handle, readable=readable, writable=writable
        )

########NEW FILE########
__FILENAME__ = connection
#
# A higher level module for using sockets (or Windows named pipes)
#
# multiprocessing/connection.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#
from __future__ import absolute_import

__all__ = ['Client', 'Listener', 'Pipe', 'wait']

import io
import os
import sys
import select
import socket
import struct
import errno
import tempfile
import itertools

import _multiprocessing
from ..compat import setblocking
from ..exceptions import AuthenticationError, BufferTooShort
from ..five import monotonic
from ..util import get_temp_dir, Finalize, sub_debug
from ..reduction import ForkingPickler
try:
    import _winapi
    from _winapi import (
        WAIT_OBJECT_0,
        WAIT_TIMEOUT,
        INFINITE,
    )
    # if we got here, we seem to be running on Windows. Handle probably
    # missing WAIT_ABANDONED_0 constant:
    try:
        from _winapi import WAIT_ABANDONED_0
    except ImportError:
        # _winapi seems to be not exporting
        # this constant, fallback solution until
        # exported in _winapio
        WAIT_ABANDONED_0 = 128
except ImportError:
    if sys.platform == 'win32':
        raise
    _winapi = None

#
#
#

BUFSIZE = 8192
# A very generous timeout when it comes to local connections...
CONNECTION_TIMEOUT = 20.

_mmap_counter = itertools.count()

default_family = 'AF_INET'
families = ['AF_INET']

if hasattr(socket, 'AF_UNIX'):
    default_family = 'AF_UNIX'
    families += ['AF_UNIX']

if sys.platform == 'win32':
    default_family = 'AF_PIPE'
    families += ['AF_PIPE']


def _init_timeout(timeout=CONNECTION_TIMEOUT):
    return monotonic() + timeout


def _check_timeout(t):
    return monotonic() > t


def arbitrary_address(family):
    '''
    Return an arbitrary free address for the given family
    '''
    if family == 'AF_INET':
        return ('localhost', 0)
    elif family == 'AF_UNIX':
        return tempfile.mktemp(prefix='listener-', dir=get_temp_dir())
    elif family == 'AF_PIPE':
        return tempfile.mktemp(prefix=r'\\.\pipe\pyc-%d-%d-' %
                               (os.getpid(), next(_mmap_counter)))
    else:
        raise ValueError('unrecognized family')


def _validate_family(family):
    '''
    Checks if the family is valid for the current environment.
    '''
    if sys.platform != 'win32' and family == 'AF_PIPE':
        raise ValueError('Family %s is not recognized.' % family)

    if sys.platform == 'win32' and family == 'AF_UNIX':
        # double check
        if not hasattr(socket, family):
            raise ValueError('Family %s is not recognized.' % family)


def address_type(address):
    '''
    Return the types of the address

    This can be 'AF_INET', 'AF_UNIX', or 'AF_PIPE'
    '''
    if type(address) == tuple:
        return 'AF_INET'
    elif type(address) is str and address.startswith('\\\\'):
        return 'AF_PIPE'
    elif type(address) is str:
        return 'AF_UNIX'
    else:
        raise ValueError('address type of %r unrecognized' % address)

#
# Connection classes
#


class _ConnectionBase:
    _handle = None

    def __init__(self, handle, readable=True, writable=True):
        handle = handle.__index__()
        if handle < 0:
            raise ValueError("invalid handle")
        if not readable and not writable:
            raise ValueError(
                "at least one of `readable` and `writable` must be True")
        self._handle = handle
        self._readable = readable
        self._writable = writable

    # XXX should we use util.Finalize instead of a __del__?

    def __del__(self):
        if self._handle is not None:
            self._close()

    def _check_closed(self):
        if self._handle is None:
            raise OSError("handle is closed")

    def _check_readable(self):
        if not self._readable:
            raise OSError("connection is write-only")

    def _check_writable(self):
        if not self._writable:
            raise OSError("connection is read-only")

    def _bad_message_length(self):
        if self._writable:
            self._readable = False
        else:
            self.close()
        raise OSError("bad message length")

    @property
    def closed(self):
        """True if the connection is closed"""
        return self._handle is None

    @property
    def readable(self):
        """True if the connection is readable"""
        return self._readable

    @property
    def writable(self):
        """True if the connection is writable"""
        return self._writable

    def fileno(self):
        """File descriptor or handle of the connection"""
        self._check_closed()
        return self._handle

    def close(self):
        """Close the connection"""
        if self._handle is not None:
            try:
                self._close()
            finally:
                self._handle = None

    def send_bytes(self, buf, offset=0, size=None):
        """Send the bytes data from a bytes-like object"""
        self._check_closed()
        self._check_writable()
        m = memoryview(buf)
        # HACK for byte-indexing of non-bytewise buffers (e.g. array.array)
        if m.itemsize > 1:
            m = memoryview(bytes(m))
        n = len(m)
        if offset < 0:
            raise ValueError("offset is negative")
        if n < offset:
            raise ValueError("buffer length < offset")
        if size is None:
            size = n - offset
        elif size < 0:
            raise ValueError("size is negative")
        elif offset + size > n:
            raise ValueError("buffer length < offset + size")
        self._send_bytes(m[offset:offset + size])

    def send(self, obj):
        """Send a (picklable) object"""
        self._check_closed()
        self._check_writable()
        self._send_bytes(ForkingPickler.dumps(obj))

    def recv_bytes(self, maxlength=None):
        """
        Receive bytes data as a bytes object.
        """
        self._check_closed()
        self._check_readable()
        if maxlength is not None and maxlength < 0:
            raise ValueError("negative maxlength")
        buf = self._recv_bytes(maxlength)
        if buf is None:
            self._bad_message_length()
        return buf.getvalue()

    def recv_bytes_into(self, buf, offset=0):
        """
        Receive bytes data into a writeable buffer-like object.
        Return the number of bytes read.
        """
        self._check_closed()
        self._check_readable()
        with memoryview(buf) as m:
            # Get bytesize of arbitrary buffer
            itemsize = m.itemsize
            bytesize = itemsize * len(m)
            if offset < 0:
                raise ValueError("negative offset")
            elif offset > bytesize:
                raise ValueError("offset too large")
            result = self._recv_bytes()
            size = result.tell()
            if bytesize < offset + size:
                raise BufferTooShort(result.getvalue())
            # Message can fit in dest
            result.seek(0)
            result.readinto(
                m[offset // itemsize:(offset + size) // itemsize]
            )
            return size

    def recv_payload(self):
        return self._recv_bytes().getbuffer()

    def recv(self):
        """Receive a (picklable) object"""
        self._check_closed()
        self._check_readable()
        buf = self._recv_bytes()
        return ForkingPickler.loads(buf.getbuffer())

    def poll(self, timeout=0.0):
        """Whether there is any input available to be read"""
        self._check_closed()
        self._check_readable()
        return self._poll(timeout)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


if _winapi:

    class PipeConnection(_ConnectionBase):
        """
        Connection class based on a Windows named pipe.
        Overlapped I/O is used, so the handles must have been created
        with FILE_FLAG_OVERLAPPED.
        """
        _got_empty_message = False

        def _close(self, _CloseHandle=_winapi.CloseHandle):
            _CloseHandle(self._handle)

        def _send_bytes(self, buf):
            ov, err = _winapi.WriteFile(self._handle, buf, overlapped=True)
            try:
                if err == _winapi.ERROR_IO_PENDING:
                    waitres = _winapi.WaitForMultipleObjects(
                        [ov.event], False, INFINITE)
                    assert waitres == WAIT_OBJECT_0
            except:
                ov.cancel()
                raise
            finally:
                nwritten, err = ov.GetOverlappedResult(True)
            assert err == 0
            assert nwritten == len(buf)

        def _recv_bytes(self, maxsize=None):
            if self._got_empty_message:
                self._got_empty_message = False
                return io.BytesIO()
            else:
                bsize = 128 if maxsize is None else min(maxsize, 128)
                try:
                    ov, err = _winapi.ReadFile(self._handle, bsize,
                                               overlapped=True)
                    try:
                        if err == _winapi.ERROR_IO_PENDING:
                            waitres = _winapi.WaitForMultipleObjects(
                                [ov.event], False, INFINITE)
                            assert waitres == WAIT_OBJECT_0
                    except:
                        ov.cancel()
                        raise
                    finally:
                        nread, err = ov.GetOverlappedResult(True)
                        if err == 0:
                            f = io.BytesIO()
                            f.write(ov.getbuffer())
                            return f
                        elif err == _winapi.ERROR_MORE_DATA:
                            return self._get_more_data(ov, maxsize)
                except OSError as e:
                    if e.winerror == _winapi.ERROR_BROKEN_PIPE:
                        raise EOFError
                    else:
                        raise
            raise RuntimeError(
                "shouldn't get here; expected KeyboardInterrupt"
            )

        def _poll(self, timeout):
            if (self._got_empty_message or
                    _winapi.PeekNamedPipe(self._handle)[0] != 0):
                return True
            return bool(wait([self], timeout))

        def _get_more_data(self, ov, maxsize):
            buf = ov.getbuffer()
            f = io.BytesIO()
            f.write(buf)
            left = _winapi.PeekNamedPipe(self._handle)[1]
            assert left > 0
            if maxsize is not None and len(buf) + left > maxsize:
                self._bad_message_length()
            ov, err = _winapi.ReadFile(self._handle, left, overlapped=True)
            rbytes, err = ov.GetOverlappedResult(True)
            assert err == 0
            assert rbytes == left
            f.write(ov.getbuffer())
            return f


class Connection(_ConnectionBase):
    """
    Connection class based on an arbitrary file descriptor (Unix only), or
    a socket handle (Windows).
    """

    if _winapi:
        def _close(self, _close=_multiprocessing.closesocket):
            _close(self._handle)
        _write = _multiprocessing.send
        _read = _multiprocessing.recv
    else:
        def _close(self, _close=os.close):  # noqa
            _close(self._handle)
        _write = os.write
        _read = os.read

    def send_offset(self, buf, offset, write=_write):
        return write(self._handle, buf[offset:])

    def _send(self, buf, write=_write):
        remaining = len(buf)
        while True:
            try:
                n = write(self._handle, buf)
            except OSError as exc:
                if exc.errno == errno.EINTR:
                    continue
                raise
            remaining -= n
            if remaining == 0:
                break
            buf = buf[n:]

    def setblocking(self, blocking):
        setblocking(self._handle, blocking)

    def _recv(self, size, read=_read):
        buf = io.BytesIO()
        handle = self._handle
        remaining = size
        while remaining > 0:
            try:
                chunk = read(handle, remaining)
            except OSError as exc:
                if exc.errno == errno.EINTR:
                    continue
                raise
            n = len(chunk)
            if n == 0:
                if remaining == size:
                    raise EOFError
                else:
                    raise OSError("got end of file during message")
            buf.write(chunk)
            remaining -= n
        return buf

    def _send_bytes(self, buf):
        # For wire compatibility with 3.2 and lower
        n = len(buf)
        self._send(struct.pack("!i", n))
        # The condition is necessary to avoid "broken pipe" errors
        # when sending a 0-length buffer if the other end closed the pipe.
        if n > 0:
            self._send(buf)

    def _recv_bytes(self, maxsize=None):
        buf = self._recv(4)
        size, = struct.unpack("!i", buf.getvalue())
        if maxsize is not None and size > maxsize:
            return None
        return self._recv(size)

    def _poll(self, timeout):
        r = wait([self], timeout)
        return bool(r)


#
# Public functions
#

class Listener(object):
    '''
    Returns a listener object.

    This is a wrapper for a bound socket which is 'listening' for
    connections, or for a Windows named pipe.
    '''
    def __init__(self, address=None, family=None, backlog=1, authkey=None):
        family = (family or (address and address_type(address))
                  or default_family)
        address = address or arbitrary_address(family)

        _validate_family(family)
        if family == 'AF_PIPE':
            self._listener = PipeListener(address, backlog)
        else:
            self._listener = SocketListener(address, family, backlog)

        if authkey is not None and not isinstance(authkey, bytes):
            raise TypeError('authkey should be a byte string')

        self._authkey = authkey

    def accept(self):
        '''
        Accept a connection on the bound socket or named pipe of `self`.

        Returns a `Connection` object.
        '''
        if self._listener is None:
            raise OSError('listener is closed')
        c = self._listener.accept()
        if self._authkey:
            deliver_challenge(c, self._authkey)
            answer_challenge(c, self._authkey)
        return c

    def close(self):
        '''
        Close the bound socket or named pipe of `self`.
        '''
        if self._listener is not None:
            self._listener.close()
            self._listener = None

    address = property(lambda self: self._listener._address)
    last_accepted = property(lambda self: self._listener._last_accepted)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


def Client(address, family=None, authkey=None):
    '''
    Returns a connection to the address of a `Listener`
    '''
    family = family or address_type(address)
    _validate_family(family)
    if family == 'AF_PIPE':
        c = PipeClient(address)
    else:
        c = SocketClient(address)

    if authkey is not None and not isinstance(authkey, bytes):
        raise TypeError('authkey should be a byte string')

    if authkey is not None:
        answer_challenge(c, authkey)
        deliver_challenge(c, authkey)

    return c


if sys.platform != 'win32':

    def Pipe(duplex=True, rnonblock=False, wnonblock=False):
        '''
        Returns pair of connection objects at either end of a pipe
        '''
        if duplex:
            s1, s2 = socket.socketpair()
            s1.setblocking(not rnonblock)
            s2.setblocking(not wnonblock)
            c1 = Connection(s1.detach())
            c2 = Connection(s2.detach())
        else:
            fd1, fd2 = os.pipe()
            if rnonblock:
                setblocking(fd1, 0)
            if wnonblock:
                setblocking(fd2, 0)
            c1 = Connection(fd1, writable=False)
            c2 = Connection(fd2, readable=False)

        return c1, c2

else:
    from billiard.forking import duplicate

    def Pipe(duplex=True, rnonblock=False, wnonblock=False):  # noqa
        '''
        Returns pair of connection objects at either end of a pipe
        '''
        address = arbitrary_address('AF_PIPE')
        if duplex:
            openmode = _winapi.PIPE_ACCESS_DUPLEX
            access = _winapi.GENERIC_READ | _winapi.GENERIC_WRITE
            obsize, ibsize = BUFSIZE, BUFSIZE
        else:
            openmode = _winapi.PIPE_ACCESS_INBOUND
            access = _winapi.GENERIC_WRITE
            obsize, ibsize = 0, BUFSIZE

        h1 = _winapi.CreateNamedPipe(
            address, openmode | _winapi.FILE_FLAG_OVERLAPPED |
            _winapi.FILE_FLAG_FIRST_PIPE_INSTANCE,
            _winapi.PIPE_TYPE_MESSAGE | _winapi.PIPE_READMODE_MESSAGE |
            _winapi.PIPE_WAIT,
            1, obsize, ibsize, _winapi.NMPWAIT_WAIT_FOREVER, _winapi.NULL
        )
        h2 = _winapi.CreateFile(
            address, access, 0, _winapi.NULL, _winapi.OPEN_EXISTING,
            _winapi.FILE_FLAG_OVERLAPPED, _winapi.NULL
        )
        _winapi.SetNamedPipeHandleState(
            h2, _winapi.PIPE_READMODE_MESSAGE, None, None
        )

        overlapped = _winapi.ConnectNamedPipe(h1, overlapped=True)
        _, err = overlapped.GetOverlappedResult(True)
        assert err == 0

        c1 = PipeConnection(duplicate(h1, inheritable=True), writable=duplex)
        c2 = PipeConnection(duplicate(h2, inheritable=True), readable=duplex)
        _winapi.CloseHandle(h1)
        _winapi.CloseHandle(h2)
        return c1, c2

#
# Definitions for connections based on sockets
#


class SocketListener(object):
    '''
    Representation of a socket which is bound to an address and listening
    '''
    def __init__(self, address, family, backlog=1):
        self._socket = socket.socket(getattr(socket, family))
        try:
            # SO_REUSEADDR has different semantics on Windows (issue #2550).
            if os.name == 'posix':
                self._socket.setsockopt(socket.SOL_SOCKET,
                                        socket.SO_REUSEADDR, 1)
            self._socket.setblocking(True)
            self._socket.bind(address)
            self._socket.listen(backlog)
            self._address = self._socket.getsockname()
        except OSError:
            self._socket.close()
            raise
        self._family = family
        self._last_accepted = None

        if family == 'AF_UNIX':
            self._unlink = Finalize(
                self, os.unlink, args=(address, ), exitpriority=0
            )
        else:
            self._unlink = None

    def accept(self):
        while True:
            try:
                s, self._last_accepted = self._socket.accept()
            except OSError as exc:
                if exc.errno == errno.EINTR:
                    continue
                raise
            else:
                break
        s.setblocking(True)
        return Connection(s.detach())

    def close(self):
        self._socket.close()
        if self._unlink is not None:
            self._unlink()


def SocketClient(address):
    '''
    Return a connection object connected to the socket given by `address`
    '''
    family = address_type(address)
    with socket.socket(getattr(socket, family)) as s:
        s.setblocking(True)
        s.connect(address)
        return Connection(s.detach())

#
# Definitions for connections based on named pipes
#

if sys.platform == 'win32':

    class PipeListener(object):
        '''
        Representation of a named pipe
        '''
        def __init__(self, address, backlog=None):
            self._address = address
            self._handle_queue = [self._new_handle(first=True)]

            self._last_accepted = None
            sub_debug('listener created with address=%r', self._address)
            self.close = Finalize(
                self, PipeListener._finalize_pipe_listener,
                args=(self._handle_queue, self._address), exitpriority=0
            )

        def _new_handle(self, first=False):
            flags = _winapi.PIPE_ACCESS_DUPLEX | _winapi.FILE_FLAG_OVERLAPPED
            if first:
                flags |= _winapi.FILE_FLAG_FIRST_PIPE_INSTANCE
            return _winapi.CreateNamedPipe(
                self._address, flags,
                _winapi.PIPE_TYPE_MESSAGE | _winapi.PIPE_READMODE_MESSAGE |
                _winapi.PIPE_WAIT,
                _winapi.PIPE_UNLIMITED_INSTANCES, BUFSIZE, BUFSIZE,
                _winapi.NMPWAIT_WAIT_FOREVER, _winapi.NULL
            )

        def accept(self):
            self._handle_queue.append(self._new_handle())
            handle = self._handle_queue.pop(0)
            try:
                ov = _winapi.ConnectNamedPipe(handle, overlapped=True)
            except OSError as e:
                if e.winerror != _winapi.ERROR_NO_DATA:
                    raise
                # ERROR_NO_DATA can occur if a client has already connected,
                # written data and then disconnected -- see Issue 14725.
            else:
                try:
                    _winapi.WaitForMultipleObjects([ov.event], False, INFINITE)
                except:
                    ov.cancel()
                    _winapi.CloseHandle(handle)
                    raise
                finally:
                    _, err = ov.GetOverlappedResult(True)
                    assert err == 0
            return PipeConnection(handle)

        @staticmethod
        def _finalize_pipe_listener(queue, address):
            sub_debug('closing listener with address=%r', address)
            for handle in queue:
                _winapi.CloseHandle(handle)

    def PipeClient(address,
                   errors=(_winapi.ERROR_SEM_TIMEOUT,
                           _winapi.ERROR_PIPE_BUSY)):
        '''
        Return a connection object connected to the pipe given by `address`
        '''
        t = _init_timeout()
        while 1:
            try:
                _winapi.WaitNamedPipe(address, 1000)
                h = _winapi.CreateFile(
                    address, _winapi.GENERIC_READ | _winapi.GENERIC_WRITE,
                    0, _winapi.NULL, _winapi.OPEN_EXISTING,
                    _winapi.FILE_FLAG_OVERLAPPED, _winapi.NULL
                )
            except OSError as e:
                if e.winerror not in errors or _check_timeout(t):
                    raise
            else:
                break
        else:
            raise

        _winapi.SetNamedPipeHandleState(
            h, _winapi.PIPE_READMODE_MESSAGE, None, None
        )
        return PipeConnection(h)

#
# Authentication stuff
#

MESSAGE_LENGTH = 20

CHALLENGE = b'#CHALLENGE#'
WELCOME = b'#WELCOME#'
FAILURE = b'#FAILURE#'


def deliver_challenge(connection, authkey):
    import hmac
    assert isinstance(authkey, bytes)
    message = os.urandom(MESSAGE_LENGTH)
    connection.send_bytes(CHALLENGE + message)
    digest = hmac.new(authkey, message).digest()
    response = connection.recv_bytes(256)        # reject large message
    if response == digest:
        connection.send_bytes(WELCOME)
    else:
        connection.send_bytes(FAILURE)
        raise AuthenticationError('digest received was wrong')


def answer_challenge(connection, authkey):
    import hmac
    assert isinstance(authkey, bytes)
    message = connection.recv_bytes(256)         # reject large message
    assert message[:len(CHALLENGE)] == CHALLENGE, 'message = %r' % message
    message = message[len(CHALLENGE):]
    digest = hmac.new(authkey, message).digest()
    connection.send_bytes(digest)
    response = connection.recv_bytes(256)        # reject large message
    if response != WELCOME:
        raise AuthenticationError('digest sent was rejected')

#
# Support for using xmlrpclib for serialization
#


class ConnectionWrapper(object):

    def __init__(self, conn, dumps, loads):
        self._conn = conn
        self._dumps = dumps
        self._loads = loads
        for attr in ('fileno', 'close', 'poll', 'recv_bytes', 'send_bytes'):
            obj = getattr(conn, attr)
            setattr(self, attr, obj)

    def send(self, obj):
        s = self._dumps(obj)
        self._conn.send_bytes(s)

    def recv(self):
        s = self._conn.recv_bytes()
        return self._loads(s)


def _xml_dumps(obj):
    return xmlrpclib.dumps((obj,), None, None, None, 1).encode('utf-8')  # noqa


def _xml_loads(s):
    (obj,), method = xmlrpclib.loads(s.decode('utf-8'))  # noqa
    return obj


class XmlListener(Listener):
    def accept(self):
        global xmlrpclib
        import xmlrpc.client as xmlrpclib  # noqa
        obj = Listener.accept(self)
        return ConnectionWrapper(obj, _xml_dumps, _xml_loads)


def XmlClient(*args, **kwds):
    global xmlrpclib
    import xmlrpc.client as xmlrpclib  # noqa
    return ConnectionWrapper(Client(*args, **kwds), _xml_dumps, _xml_loads)

#
# Wait
#

if sys.platform == 'win32':

    def _exhaustive_wait(handles, timeout):
        # Return ALL handles which are currently signalled.  (Only
        # returning the first signalled might create starvation issues.)
        L = list(handles)
        ready = []
        while L:
            res = _winapi.WaitForMultipleObjects(L, False, timeout)
            if res == WAIT_TIMEOUT:
                break
            elif WAIT_OBJECT_0 <= res < WAIT_OBJECT_0 + len(L):
                res -= WAIT_OBJECT_0
            elif WAIT_ABANDONED_0 <= res < WAIT_ABANDONED_0 + len(L):
                res -= WAIT_ABANDONED_0
            else:
                raise RuntimeError('Should not get here')
            ready.append(L[res])
            L = L[res+1:]
            timeout = 0
        return ready

    _ready_errors = {_winapi.ERROR_BROKEN_PIPE, _winapi.ERROR_NETNAME_DELETED}

    def wait(object_list, timeout=None):
        '''
        Wait till an object in object_list is ready/readable.

        Returns list of those objects in object_list which are ready/readable.
        '''
        if timeout is None:
            timeout = INFINITE
        elif timeout < 0:
            timeout = 0
        else:
            timeout = int(timeout * 1000 + 0.5)

        object_list = list(object_list)
        waithandle_to_obj = {}
        ov_list = []
        ready_objects = set()
        ready_handles = set()

        try:
            for o in object_list:
                try:
                    fileno = getattr(o, 'fileno')
                except AttributeError:
                    waithandle_to_obj[o.__index__()] = o
                else:
                    # start an overlapped read of length zero
                    try:
                        ov, err = _winapi.ReadFile(fileno(), 0, True)
                    except OSError as e:
                        err = e.winerror
                        if err not in _ready_errors:
                            raise
                    if err == _winapi.ERROR_IO_PENDING:
                        ov_list.append(ov)
                        waithandle_to_obj[ov.event] = o
                    else:
                        # If o.fileno() is an overlapped pipe handle and
                        # err == 0 then there is a zero length message
                        # in the pipe, but it HAS NOT been consumed.
                        ready_objects.add(o)
                        timeout = 0

            ready_handles = _exhaustive_wait(waithandle_to_obj.keys(), timeout)
        finally:
            # request that overlapped reads stop
            for ov in ov_list:
                ov.cancel()

            # wait for all overlapped reads to stop
            for ov in ov_list:
                try:
                    _, err = ov.GetOverlappedResult(True)
                except OSError as e:
                    err = e.winerror
                    if err not in _ready_errors:
                        raise
                if err != _winapi.ERROR_OPERATION_ABORTED:
                    o = waithandle_to_obj[ov.event]
                    ready_objects.add(o)
                    if err == 0:
                        # If o.fileno() is an overlapped pipe handle then
                        # a zero length message HAS been consumed.
                        if hasattr(o, '_got_empty_message'):
                            o._got_empty_message = True

        ready_objects.update(waithandle_to_obj[h] for h in ready_handles)
        return [oj for oj in object_list if oj in ready_objects]

else:

    if hasattr(select, 'poll'):
        def _poll(fds, timeout):
            if timeout is not None:
                timeout = int(timeout * 1000)  # timeout is in milliseconds
            fd_map = {}
            pollster = select.poll()
            for fd in fds:
                pollster.register(fd, select.POLLIN)
                if hasattr(fd, 'fileno'):
                    fd_map[fd.fileno()] = fd
                else:
                    fd_map[fd] = fd
            ls = []
            for fd, event in pollster.poll(timeout):
                if event & select.POLLNVAL:
                    raise ValueError('invalid file descriptor %i' % fd)
                ls.append(fd_map[fd])
            return ls
    else:
        def _poll(fds, timeout):  # noqa
            return select.select(fds, [], [], timeout)[0]

    def wait(object_list, timeout=None):  # noqa
        '''
        Wait till an object in object_list is ready/readable.

        Returns list of those objects in object_list which are ready/readable.
        '''
        if timeout is not None:
            if timeout <= 0:
                return _poll(object_list, 0)
            else:
                deadline = monotonic() + timeout
        while True:
            try:
                return _poll(object_list, timeout)
            except OSError as e:
                if e.errno != errno.EINTR:
                    raise
            if timeout is not None:
                timeout = deadline - monotonic()

########NEW FILE########
__FILENAME__ = reduction
#
# Module which deals with pickling of objects.
#
# multiprocessing/reduction.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#
from __future__ import absolute_import

import copyreg
import functools
import io
import os
import pickle
import socket
import sys

__all__ = ['send_handle', 'recv_handle', 'ForkingPickler', 'register', 'dump']


HAVE_SEND_HANDLE = (sys.platform == 'win32' or
                    (hasattr(socket, 'CMSG_LEN') and
                     hasattr(socket, 'SCM_RIGHTS') and
                     hasattr(socket.socket, 'sendmsg')))

#
# Pickler subclass
#


class ForkingPickler(pickle.Pickler):
    '''Pickler subclass used by multiprocessing.'''
    _extra_reducers = {}
    _copyreg_dispatch_table = copyreg.dispatch_table

    def __init__(self, *args):
        super().__init__(*args)
        self.dispatch_table = self._copyreg_dispatch_table.copy()
        self.dispatch_table.update(self._extra_reducers)

    @classmethod
    def register(cls, type, reduce):
        '''Register a reduce function for a type.'''
        cls._extra_reducers[type] = reduce

    @classmethod
    def dumps(cls, obj, protocol=None):
        buf = io.BytesIO()
        cls(buf, protocol).dump(obj)
        return buf.getbuffer()

    loads = pickle.loads

register = ForkingPickler.register


def dump(obj, file, protocol=None):
    '''Replacement for pickle.dump() using ForkingPickler.'''
    ForkingPickler(file, protocol).dump(obj)

#
# Platform specific definitions
#

if sys.platform == 'win32':
    # Windows
    __all__ += ['DupHandle', 'duplicate', 'steal_handle']
    import _winapi

    def duplicate(handle, target_process=None, inheritable=False):
        '''Duplicate a handle.  (target_process is a handle not a pid!)'''
        if target_process is None:
            target_process = _winapi.GetCurrentProcess()
        return _winapi.DuplicateHandle(
            _winapi.GetCurrentProcess(), handle, target_process,
            0, inheritable, _winapi.DUPLICATE_SAME_ACCESS)

    def steal_handle(source_pid, handle):
        '''Steal a handle from process identified by source_pid.'''
        source_process_handle = _winapi.OpenProcess(
            _winapi.PROCESS_DUP_HANDLE, False, source_pid)
        try:
            return _winapi.DuplicateHandle(
                source_process_handle, handle,
                _winapi.GetCurrentProcess(), 0, False,
                _winapi.DUPLICATE_SAME_ACCESS | _winapi.DUPLICATE_CLOSE_SOURCE)
        finally:
            _winapi.CloseHandle(source_process_handle)

    def send_handle(conn, handle, destination_pid):
        '''Send a handle over a local connection.'''
        dh = DupHandle(handle, _winapi.DUPLICATE_SAME_ACCESS, destination_pid)
        conn.send(dh)

    def recv_handle(conn):
        '''Receive a handle over a local connection.'''
        return conn.recv().detach()

    class DupHandle(object):
        '''Picklable wrapper for a handle.'''
        def __init__(self, handle, access, pid=None):
            if pid is None:
                # We just duplicate the handle in the current process and
                # let the receiving process steal the handle.
                pid = os.getpid()
            proc = _winapi.OpenProcess(_winapi.PROCESS_DUP_HANDLE, False, pid)
            try:
                self._handle = _winapi.DuplicateHandle(
                    _winapi.GetCurrentProcess(),
                    handle, proc, access, False, 0)
            finally:
                _winapi.CloseHandle(proc)
            self._access = access
            self._pid = pid

        def detach(self):
            '''Get the handle.  This should only be called once.'''
            # retrieve handle from process which currently owns it
            if self._pid == os.getpid():
                # The handle has already been duplicated for this process.
                return self._handle
            # We must steal the handle from the process whose pid is self._pid.
            proc = _winapi.OpenProcess(_winapi.PROCESS_DUP_HANDLE, False,
                                       self._pid)
            try:
                return _winapi.DuplicateHandle(
                    proc, self._handle, _winapi.GetCurrentProcess(),
                    self._access, False, _winapi.DUPLICATE_CLOSE_SOURCE)
            finally:
                _winapi.CloseHandle(proc)

else:
    # Unix
    __all__ += ['DupFd', 'sendfds', 'recvfds']
    import array

    # On MacOSX we should acknowledge receipt of fds -- see Issue14669
    ACKNOWLEDGE = sys.platform == 'darwin'

    def sendfds(sock, fds):
        '''Send an array of fds over an AF_UNIX socket.'''
        fds = array.array('i', fds)
        msg = bytes([len(fds) % 256])
        sock.sendmsg([msg], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fds)])
        if ACKNOWLEDGE and sock.recv(1) != b'A':
            raise RuntimeError('did not receive acknowledgement of fd')

    def recvfds(sock, size):
        '''Receive an array of fds over an AF_UNIX socket.'''
        a = array.array('i')
        bytes_size = a.itemsize * size
        msg, ancdata, flags, addr = sock.recvmsg(
            1, socket.CMSG_LEN(bytes_size),
        )
        if not msg and not ancdata:
            raise EOFError
        try:
            if ACKNOWLEDGE:
                sock.send(b'A')
            if len(ancdata) != 1:
                raise RuntimeError(
                    'received %d items of ancdata' % len(ancdata),
                )
            cmsg_level, cmsg_type, cmsg_data = ancdata[0]
            if (cmsg_level == socket.SOL_SOCKET and
                    cmsg_type == socket.SCM_RIGHTS):
                if len(cmsg_data) % a.itemsize != 0:
                    raise ValueError
                a.frombytes(cmsg_data)
                assert len(a) % 256 == msg[0]
                return list(a)
        except (ValueError, IndexError):
            pass
        raise RuntimeError('Invalid data received')

    def send_handle(conn, handle, destination_pid):  # noqa
        '''Send a handle over a local connection.'''
        fd = conn.fileno()
        with socket.fromfd(fd, socket.AF_UNIX, socket.SOCK_STREAM) as s:
            sendfds(s, [handle])

    def recv_handle(conn):  # noqa
        '''Receive a handle over a local connection.'''
        fd = conn.fileno()
        with socket.fromfd(fd, socket.AF_UNIX, socket.SOCK_STREAM) as s:
            return recvfds(s, 1)[0]

    def DupFd(fd):
        '''Return a wrapper for an fd.'''
        from ..forking import Popen
        return Popen.duplicate_for_child(fd)

#
# Try making some callable types picklable
#


def _reduce_method(m):
    if m.__self__ is None:
        return getattr, (m.__class__, m.__func__.__name__)
    else:
        return getattr, (m.__self__, m.__func__.__name__)


class _C:
    def f(self):
        pass
register(type(_C().f), _reduce_method)


def _reduce_method_descriptor(m):
    return getattr, (m.__objclass__, m.__name__)
register(type(list.append), _reduce_method_descriptor)
register(type(int.__add__), _reduce_method_descriptor)


def _reduce_partial(p):
    return _rebuild_partial, (p.func, p.args, p.keywords or {})


def _rebuild_partial(func, args, keywords):
    return functools.partial(func, *args, **keywords)
register(functools.partial, _reduce_partial)

#
# Make sockets picklable
#

if sys.platform == 'win32':

    def _reduce_socket(s):
        from ..resource_sharer import DupSocket
        return _rebuild_socket, (DupSocket(s),)

    def _rebuild_socket(ds):
        return ds.detach()
    register(socket.socket, _reduce_socket)

else:

    def _reduce_socket(s):  # noqa
        df = DupFd(s.fileno())
        return _rebuild_socket, (df, s.family, s.type, s.proto)

    def _rebuild_socket(df, family, type, proto):  # noqa
        fd = df.detach()
        return socket.socket(family, type, proto, fileno=fd)
    register(socket.socket, _reduce_socket)

########NEW FILE########
__FILENAME__ = queues
#
# Module implementing queues
#
# multiprocessing/queues.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#
from __future__ import absolute_import

__all__ = ['Queue', 'SimpleQueue', 'JoinableQueue']

import sys
import os
import threading
import collections
import weakref
import errno

from . import Pipe
from ._ext import _billiard
from .compat import get_errno
from .five import monotonic
from .synchronize import Lock, BoundedSemaphore, Semaphore, Condition
from .util import debug, error, info, Finalize, register_after_fork
from .five import Empty, Full
from .forking import assert_spawning


class Queue(object):
    '''
    Queue type using a pipe, buffer and thread
    '''
    def __init__(self, maxsize=0):
        if maxsize <= 0:
            maxsize = _billiard.SemLock.SEM_VALUE_MAX
        self._maxsize = maxsize
        self._reader, self._writer = Pipe(duplex=False)
        self._rlock = Lock()
        self._opid = os.getpid()
        if sys.platform == 'win32':
            self._wlock = None
        else:
            self._wlock = Lock()
        self._sem = BoundedSemaphore(maxsize)
        # For use by concurrent.futures
        self._ignore_epipe = False

        self._after_fork()

        if sys.platform != 'win32':
            register_after_fork(self, Queue._after_fork)

    def __getstate__(self):
        assert_spawning(self)
        return (self._ignore_epipe, self._maxsize, self._reader, self._writer,
                self._rlock, self._wlock, self._sem, self._opid)

    def __setstate__(self, state):
        (self._ignore_epipe, self._maxsize, self._reader, self._writer,
         self._rlock, self._wlock, self._sem, self._opid) = state
        self._after_fork()

    def _after_fork(self):
        debug('Queue._after_fork()')
        self._notempty = threading.Condition(threading.Lock())
        self._buffer = collections.deque()
        self._thread = None
        self._jointhread = None
        self._joincancelled = False
        self._closed = False
        self._close = None
        self._send = self._writer.send
        self._recv = self._reader.recv
        self._poll = self._reader.poll

    def put(self, obj, block=True, timeout=None):
        assert not self._closed
        if not self._sem.acquire(block, timeout):
            raise Full

        with self._notempty:
            if self._thread is None:
                self._start_thread()
            self._buffer.append(obj)
            self._notempty.notify()

    def get(self, block=True, timeout=None):
        if block and timeout is None:
            with self._rlock:
                res = self._recv()
                self._sem.release()
                return res

        else:
            if block:
                deadline = monotonic() + timeout
            if not self._rlock.acquire(block, timeout):
                raise Empty
            try:
                if block:
                    timeout = deadline - monotonic()
                    if timeout < 0 or not self._poll(timeout):
                        raise Empty
                elif not self._poll():
                    raise Empty
                res = self._recv()
                self._sem.release()
                return res
            finally:
                self._rlock.release()

    def qsize(self):
        # Raises NotImplementedError on Mac OSX because
        # of broken sem_getvalue()
        return self._maxsize - self._sem._semlock._get_value()

    def empty(self):
        return not self._poll()

    def full(self):
        return self._sem._semlock._is_zero()

    def get_nowait(self):
        return self.get(False)

    def put_nowait(self, obj):
        return self.put(obj, False)

    def close(self):
        self._closed = True
        self._reader.close()
        if self._close:
            self._close()

    def join_thread(self):
        debug('Queue.join_thread()')
        assert self._closed
        if self._jointhread:
            self._jointhread()

    def cancel_join_thread(self):
        debug('Queue.cancel_join_thread()')
        self._joincancelled = True
        try:
            self._jointhread.cancel()
        except AttributeError:
            pass

    def _start_thread(self):
        debug('Queue._start_thread()')

        # Start thread which transfers data from buffer to pipe
        self._buffer.clear()
        self._thread = threading.Thread(
            target=Queue._feed,
            args=(self._buffer, self._notempty, self._send,
                  self._wlock, self._writer.close, self._ignore_epipe),
            name='QueueFeederThread'
        )
        self._thread.daemon = True

        debug('doing self._thread.start()')
        self._thread.start()
        debug('... done self._thread.start()')

        # On process exit we will wait for data to be flushed to pipe.
        #
        # However, if this process created the queue then all
        # processes which use the queue will be descendants of this
        # process.  Therefore waiting for the queue to be flushed
        # is pointless once all the child processes have been joined.
        created_by_this_process = (self._opid == os.getpid())
        if not self._joincancelled and not created_by_this_process:
            self._jointhread = Finalize(
                self._thread, Queue._finalize_join,
                [weakref.ref(self._thread)],
                exitpriority=-5
            )

        # Send sentinel to the thread queue object when garbage collected
        self._close = Finalize(
            self, Queue._finalize_close,
            [self._buffer, self._notempty],
            exitpriority=10
        )

    @staticmethod
    def _finalize_join(twr):
        debug('joining queue thread')
        thread = twr()
        if thread is not None:
            thread.join()
            debug('... queue thread joined')
        else:
            debug('... queue thread already dead')

    @staticmethod
    def _finalize_close(buffer, notempty):
        debug('telling queue thread to quit')
        with notempty:
            buffer.append(_sentinel)
            notempty.notify()

    @staticmethod
    def _feed(buffer, notempty, send, writelock, close, ignore_epipe):
        debug('starting thread to feed data to pipe')
        from .util import is_exiting

        ncond = notempty
        nwait = notempty.wait
        bpopleft = buffer.popleft
        sentinel = _sentinel
        if sys.platform != 'win32':
            wlock = writelock
        else:
            wlock = None

        try:
            while 1:
                with ncond:
                    if not buffer:
                        nwait()
                try:
                    while 1:
                        obj = bpopleft()
                        if obj is sentinel:
                            debug('feeder thread got sentinel -- exiting')
                            close()
                            return

                        if wlock is None:
                            send(obj)
                        else:
                            with wlock:
                                send(obj)
                except IndexError:
                    pass
        except Exception as exc:
            if ignore_epipe and get_errno(exc) == errno.EPIPE:
                return
            # Since this runs in a daemon thread the resources it uses
            # may be become unusable while the process is cleaning up.
            # We ignore errors which happen after the process has
            # started to cleanup.
            try:
                if is_exiting():
                    info('error in queue thread: %r', exc, exc_info=True)
                else:
                    if not error('error in queue thread: %r', exc,
                                 exc_info=True):
                        import traceback
                        traceback.print_exc()
            except Exception:
                pass

_sentinel = object()


class JoinableQueue(Queue):
    '''
    A queue type which also supports join() and task_done() methods

    Note that if you do not call task_done() for each finished task then
    eventually the counter's semaphore may overflow causing Bad Things
    to happen.
    '''

    def __init__(self, maxsize=0):
        Queue.__init__(self, maxsize)
        self._unfinished_tasks = Semaphore(0)
        self._cond = Condition()

    def __getstate__(self):
        return Queue.__getstate__(self) + (self._cond, self._unfinished_tasks)

    def __setstate__(self, state):
        Queue.__setstate__(self, state[:-2])
        self._cond, self._unfinished_tasks = state[-2:]

    def put(self, obj, block=True, timeout=None):
        assert not self._closed
        if not self._sem.acquire(block, timeout):
            raise Full

        with self._notempty:
            with self._cond:
                if self._thread is None:
                    self._start_thread()
                self._buffer.append(obj)
                self._unfinished_tasks.release()
                self._notempty.notify()

    def task_done(self):
        with self._cond:
            if not self._unfinished_tasks.acquire(False):
                raise ValueError('task_done() called too many times')
            if self._unfinished_tasks._semlock._is_zero():
                self._cond.notify_all()

    def join(self):
        with self._cond:
            if not self._unfinished_tasks._semlock._is_zero():
                self._cond.wait()


class _SimpleQueue(object):
    '''
    Simplified Queue type -- really just a locked pipe
    '''

    def __init__(self, rnonblock=False, wnonblock=False):
        self._reader, self._writer = Pipe(
            duplex=False, rnonblock=rnonblock, wnonblock=wnonblock,
        )
        self._poll = self._reader.poll
        self._rlock = self._wlock = None
        self._make_methods()

    def empty(self):
        return not self._poll()

    def __getstate__(self):
        assert_spawning(self)
        return (self._reader, self._writer, self._rlock, self._wlock)

    def __setstate__(self, state):
        (self._reader, self._writer, self._rlock, self._wlock) = state
        self._make_methods()

    def _make_methods(self):
        recv = self._reader.recv
        try:
            recv_payload = self._reader.recv_payload
        except AttributeError:
            recv_payload = self._reader.recv_bytes
        rlock = self._rlock

        if rlock is not None:
            def get():
                with rlock:
                    return recv()
            self.get = get

            def get_payload():
                with rlock:
                    return recv_payload()
            self.get_payload = get_payload
        else:
            self.get = recv
            self.get_payload = recv_payload

        if self._wlock is None:
            # writes to a message oriented win32 pipe are atomic
            self.put = self._writer.send
        else:
            send = self._writer.send
            wlock = self._wlock

            def put(obj):
                with wlock:
                    return send(obj)
            self.put = put


class SimpleQueue(_SimpleQueue):

    def __init__(self):
        self._reader, self._writer = Pipe(duplex=False)
        self._rlock = Lock()
        self._wlock = Lock() if sys.platform != 'win32' else None
        self._make_methods()

########NEW FILE########
__FILENAME__ = reduction
from __future__ import absolute_import

import sys

if sys.version_info[0] == 3:
    from .py3 import reduction
else:
    from .py2 import reduction  # noqa

sys.modules[__name__] = reduction

########NEW FILE########
__FILENAME__ = sharedctypes
#
# Module which supports allocation of ctypes objects from shared memory
#
# multiprocessing/sharedctypes.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#
from __future__ import absolute_import

import ctypes
import weakref

from . import heap, RLock
from .five import int_types
from .forking import assert_spawning
from .reduction import ForkingPickler

__all__ = ['RawValue', 'RawArray', 'Value', 'Array', 'copy', 'synchronized']

typecode_to_type = {
    'c': ctypes.c_char,  'u': ctypes.c_wchar,
    'b': ctypes.c_byte,  'B': ctypes.c_ubyte,
    'h': ctypes.c_short, 'H': ctypes.c_ushort,
    'i': ctypes.c_int,   'I': ctypes.c_uint,
    'l': ctypes.c_long,  'L': ctypes.c_ulong,
    'f': ctypes.c_float, 'd': ctypes.c_double
}


def _new_value(type_):
    size = ctypes.sizeof(type_)
    wrapper = heap.BufferWrapper(size)
    return rebuild_ctype(type_, wrapper, None)


def RawValue(typecode_or_type, *args):
    '''
    Returns a ctypes object allocated from shared memory
    '''
    type_ = typecode_to_type.get(typecode_or_type, typecode_or_type)
    obj = _new_value(type_)
    ctypes.memset(ctypes.addressof(obj), 0, ctypes.sizeof(obj))
    obj.__init__(*args)
    return obj


def RawArray(typecode_or_type, size_or_initializer):
    '''
    Returns a ctypes array allocated from shared memory
    '''
    type_ = typecode_to_type.get(typecode_or_type, typecode_or_type)
    if isinstance(size_or_initializer, int_types):
        type_ = type_ * size_or_initializer
        obj = _new_value(type_)
        ctypes.memset(ctypes.addressof(obj), 0, ctypes.sizeof(obj))
        return obj
    else:
        type_ = type_ * len(size_or_initializer)
        result = _new_value(type_)
        result.__init__(*size_or_initializer)
        return result


def Value(typecode_or_type, *args, **kwds):
    '''
    Return a synchronization wrapper for a Value
    '''
    lock = kwds.pop('lock', None)
    if kwds:
        raise ValueError(
            'unrecognized keyword argument(s): %s' % list(kwds.keys()))
    obj = RawValue(typecode_or_type, *args)
    if lock is False:
        return obj
    if lock in (True, None):
        lock = RLock()
    if not hasattr(lock, 'acquire'):
        raise AttributeError("'%r' has no method 'acquire'" % lock)
    return synchronized(obj, lock)


def Array(typecode_or_type, size_or_initializer, **kwds):
    '''
    Return a synchronization wrapper for a RawArray
    '''
    lock = kwds.pop('lock', None)
    if kwds:
        raise ValueError(
            'unrecognized keyword argument(s): %s' % list(kwds.keys()))
    obj = RawArray(typecode_or_type, size_or_initializer)
    if lock is False:
        return obj
    if lock in (True, None):
        lock = RLock()
    if not hasattr(lock, 'acquire'):
        raise AttributeError("'%r' has no method 'acquire'" % lock)
    return synchronized(obj, lock)


def copy(obj):
    new_obj = _new_value(type(obj))
    ctypes.pointer(new_obj)[0] = obj
    return new_obj


def synchronized(obj, lock=None):
    assert not isinstance(obj, SynchronizedBase), 'object already synchronized'

    if isinstance(obj, ctypes._SimpleCData):
        return Synchronized(obj, lock)
    elif isinstance(obj, ctypes.Array):
        if obj._type_ is ctypes.c_char:
            return SynchronizedString(obj, lock)
        return SynchronizedArray(obj, lock)
    else:
        cls = type(obj)
        try:
            scls = class_cache[cls]
        except KeyError:
            names = [field[0] for field in cls._fields_]
            d = dict((name, make_property(name)) for name in names)
            classname = 'Synchronized' + cls.__name__
            scls = class_cache[cls] = type(classname, (SynchronizedBase,), d)
        return scls(obj, lock)

#
# Functions for pickling/unpickling
#


def reduce_ctype(obj):
    assert_spawning(obj)
    if isinstance(obj, ctypes.Array):
        return rebuild_ctype, (obj._type_, obj._wrapper, obj._length_)
    else:
        return rebuild_ctype, (type(obj), obj._wrapper, None)


def rebuild_ctype(type_, wrapper, length):
    if length is not None:
        type_ = type_ * length
    ForkingPickler.register(type_, reduce_ctype)
    obj = type_.from_address(wrapper.get_address())
    obj._wrapper = wrapper
    return obj

#
# Function to create properties
#


def make_property(name):
    try:
        return prop_cache[name]
    except KeyError:
        d = {}
        exec(template % ((name, ) * 7), d)
        prop_cache[name] = d[name]
        return d[name]

template = '''
def get%s(self):
    self.acquire()
    try:
        return self._obj.%s
    finally:
        self.release()
def set%s(self, value):
    self.acquire()
    try:
        self._obj.%s = value
    finally:
        self.release()
%s = property(get%s, set%s)
'''

prop_cache = {}
class_cache = weakref.WeakKeyDictionary()

#
# Synchronized wrappers
#


class SynchronizedBase(object):

    def __init__(self, obj, lock=None):
        self._obj = obj
        self._lock = lock or RLock()
        self.acquire = self._lock.acquire
        self.release = self._lock.release

    def __reduce__(self):
        assert_spawning(self)
        return synchronized, (self._obj, self._lock)

    def get_obj(self):
        return self._obj

    def get_lock(self):
        return self._lock

    def __repr__(self):
        return '<%s wrapper for %s>' % (type(self).__name__, self._obj)


class Synchronized(SynchronizedBase):
    value = make_property('value')


class SynchronizedArray(SynchronizedBase):

    def __len__(self):
        return len(self._obj)

    def __getitem__(self, i):
        self.acquire()
        try:
            return self._obj[i]
        finally:
            self.release()

    def __setitem__(self, i, value):
        self.acquire()
        try:
            self._obj[i] = value
        finally:
            self.release()

    def __getslice__(self, start, stop):
        self.acquire()
        try:
            return self._obj[start:stop]
        finally:
            self.release()

    def __setslice__(self, start, stop, values):
        self.acquire()
        try:
            self._obj[start:stop] = values
        finally:
            self.release()


class SynchronizedString(SynchronizedArray):
    value = make_property('value')
    raw = make_property('raw')

########NEW FILE########
__FILENAME__ = synchronize
#
# Module implementing synchronization primitives
#
# multiprocessing/synchronize.py
#
# Copyright (c) 2006-2008, R Oudkerk
# Licensed to PSF under a Contributor Agreement.
#
from __future__ import absolute_import

__all__ = [
    'Lock', 'RLock', 'Semaphore', 'BoundedSemaphore', 'Condition', 'Event',
]

import itertools
import os
import signal
import sys
import threading


from ._ext import _billiard, ensure_SemLock
from .five import range, monotonic
from .process import current_process
from .util import Finalize, register_after_fork, debug
from .forking import assert_spawning, Popen
from .compat import bytes, closerange

# Try to import the mp.synchronize module cleanly, if it fails
# raise ImportError for platforms lacking a working sem_open implementation.
# See issue 3770
ensure_SemLock()

#
# Constants
#

RECURSIVE_MUTEX, SEMAPHORE = list(range(2))
SEM_VALUE_MAX = _billiard.SemLock.SEM_VALUE_MAX

try:
    sem_unlink = _billiard.SemLock.sem_unlink
except AttributeError:  # pragma: no cover
    try:
        # Py3.4+ implements sem_unlink and the semaphore must be named
        from _multiprocessing import sem_unlink  # noqa
    except ImportError:
        sem_unlink = None   # noqa

#
# Base class for semaphores and mutexes; wraps `_billiard.SemLock`
#


def _semname(sl):
    try:
        return sl.name
    except AttributeError:
        pass


class SemLock(object):
    _counter = itertools.count()

    def __init__(self, kind, value, maxvalue):
        from .forking import _forking_is_enabled
        unlink_immediately = _forking_is_enabled or sys.platform == 'win32'
        if sem_unlink:
            sl = self._semlock = _billiard.SemLock(
                kind, value, maxvalue, self._make_name(), unlink_immediately)
        else:
            sl = self._semlock = _billiard.SemLock(kind, value, maxvalue)

        debug('created semlock with handle %s', sl.handle)
        self._make_methods()

        if sem_unlink:

            if sys.platform != 'win32':
                def _after_fork(obj):
                    obj._semlock._after_fork()
                register_after_fork(self, _after_fork)

            if _semname(self._semlock) is not None:
                # We only get here if we are on Unix with forking
                # disabled.  When the object is garbage collected or the
                # process shuts down we unlink the semaphore name
                Finalize(self, sem_unlink, (self._semlock.name,),
                         exitpriority=0)
                # In case of abnormal termination unlink semaphore name
                _cleanup_semaphore_if_leaked(self._semlock.name)

    def _make_methods(self):
        self.acquire = self._semlock.acquire
        self.release = self._semlock.release

    def __enter__(self):
        return self._semlock.__enter__()

    def __exit__(self, *args):
        return self._semlock.__exit__(*args)

    def __getstate__(self):
        assert_spawning(self)
        sl = self._semlock
        state = (Popen.duplicate_for_child(sl.handle), sl.kind, sl.maxvalue)
        try:
            state += (sl.name, )
        except AttributeError:
            pass
        return state

    def __setstate__(self, state):
        self._semlock = _billiard.SemLock._rebuild(*state)
        debug('recreated blocker with handle %r', state[0])
        self._make_methods()

    @staticmethod
    def _make_name():
        return '/%s-%s-%s' % (current_process()._semprefix,
                              os.getpid(), next(SemLock._counter))


class Semaphore(SemLock):

    def __init__(self, value=1):
        SemLock.__init__(self, SEMAPHORE, value, SEM_VALUE_MAX)

    def get_value(self):
        return self._semlock._get_value()

    def __repr__(self):
        try:
            value = self._semlock._get_value()
        except Exception:
            value = 'unknown'
        return '<Semaphore(value=%s)>' % value


class BoundedSemaphore(Semaphore):

    def __init__(self, value=1):
        SemLock.__init__(self, SEMAPHORE, value, value)

    def __repr__(self):
        try:
            value = self._semlock._get_value()
        except Exception:
            value = 'unknown'
        return '<BoundedSemaphore(value=%s, maxvalue=%s)>' % \
               (value, self._semlock.maxvalue)


class Lock(SemLock):
    '''
    Non-recursive lock.
    '''

    def __init__(self):
        SemLock.__init__(self, SEMAPHORE, 1, 1)

    def __repr__(self):
        try:
            if self._semlock._is_mine():
                name = current_process().name
                if threading.currentThread().name != 'MainThread':
                    name += '|' + threading.currentThread().name
            elif self._semlock._get_value() == 1:
                name = 'None'
            elif self._semlock._count() > 0:
                name = 'SomeOtherThread'
            else:
                name = 'SomeOtherProcess'
        except Exception:
            name = 'unknown'
        return '<Lock(owner=%s)>' % name


class RLock(SemLock):
    '''
    Recursive lock
    '''

    def __init__(self):
        SemLock.__init__(self, RECURSIVE_MUTEX, 1, 1)

    def __repr__(self):
        try:
            if self._semlock._is_mine():
                name = current_process().name
                if threading.currentThread().name != 'MainThread':
                    name += '|' + threading.currentThread().name
                count = self._semlock._count()
            elif self._semlock._get_value() == 1:
                name, count = 'None', 0
            elif self._semlock._count() > 0:
                name, count = 'SomeOtherThread', 'nonzero'
            else:
                name, count = 'SomeOtherProcess', 'nonzero'
        except Exception:
            name, count = 'unknown', 'unknown'
        return '<RLock(%s, %s)>' % (name, count)


class Condition(object):
    '''
    Condition variable
    '''

    def __init__(self, lock=None):
        self._lock = lock or RLock()
        self._sleeping_count = Semaphore(0)
        self._woken_count = Semaphore(0)
        self._wait_semaphore = Semaphore(0)
        self._make_methods()

    def __getstate__(self):
        assert_spawning(self)
        return (self._lock, self._sleeping_count,
                self._woken_count, self._wait_semaphore)

    def __setstate__(self, state):
        (self._lock, self._sleeping_count,
         self._woken_count, self._wait_semaphore) = state
        self._make_methods()

    def __enter__(self):
        return self._lock.__enter__()

    def __exit__(self, *args):
        return self._lock.__exit__(*args)

    def _make_methods(self):
        self.acquire = self._lock.acquire
        self.release = self._lock.release

    def __repr__(self):
        try:
            num_waiters = (self._sleeping_count._semlock._get_value() -
                           self._woken_count._semlock._get_value())
        except Exception:
            num_waiters = 'unkown'
        return '<Condition(%s, %s)>' % (self._lock, num_waiters)

    def wait(self, timeout=None):
        assert self._lock._semlock._is_mine(), \
            'must acquire() condition before using wait()'

        # indicate that this thread is going to sleep
        self._sleeping_count.release()

        # release lock
        count = self._lock._semlock._count()
        for i in range(count):
            self._lock.release()

        try:
            # wait for notification or timeout
            ret = self._wait_semaphore.acquire(True, timeout)
        finally:
            # indicate that this thread has woken
            self._woken_count.release()

            # reacquire lock
            for i in range(count):
                self._lock.acquire()
            return ret

    def notify(self):
        assert self._lock._semlock._is_mine(), 'lock is not owned'
        assert not self._wait_semaphore.acquire(False)

        # to take account of timeouts since last notify() we subtract
        # woken_count from sleeping_count and rezero woken_count
        while self._woken_count.acquire(False):
            res = self._sleeping_count.acquire(False)
            assert res

        if self._sleeping_count.acquire(False):  # try grabbing a sleeper
            self._wait_semaphore.release()       # wake up one sleeper
            self._woken_count.acquire()          # wait for sleeper to wake

            # rezero _wait_semaphore in case a timeout just happened
            self._wait_semaphore.acquire(False)

    def notify_all(self):
        assert self._lock._semlock._is_mine(), 'lock is not owned'
        assert not self._wait_semaphore.acquire(False)

        # to take account of timeouts since last notify*() we subtract
        # woken_count from sleeping_count and rezero woken_count
        while self._woken_count.acquire(False):
            res = self._sleeping_count.acquire(False)
            assert res

        sleepers = 0
        while self._sleeping_count.acquire(False):
            self._wait_semaphore.release()        # wake up one sleeper
            sleepers += 1

        if sleepers:
            for i in range(sleepers):
                self._woken_count.acquire()       # wait for a sleeper to wake

            # rezero wait_semaphore in case some timeouts just happened
            while self._wait_semaphore.acquire(False):
                pass

    def wait_for(self, predicate, timeout=None):
        result = predicate()
        if result:
            return result
        if timeout is not None:
            endtime = monotonic() + timeout
        else:
            endtime = None
            waittime = None
        while not result:
            if endtime is not None:
                waittime = endtime - monotonic()
                if waittime <= 0:
                    break
            self.wait(waittime)
            result = predicate()
        return result


class Event(object):

    def __init__(self):
        self._cond = Condition(Lock())
        self._flag = Semaphore(0)

    def is_set(self):
        self._cond.acquire()
        try:
            if self._flag.acquire(False):
                self._flag.release()
                return True
            return False
        finally:
            self._cond.release()

    def set(self):
        self._cond.acquire()
        try:
            self._flag.acquire(False)
            self._flag.release()
            self._cond.notify_all()
        finally:
            self._cond.release()

    def clear(self):
        self._cond.acquire()
        try:
            self._flag.acquire(False)
        finally:
            self._cond.release()

    def wait(self, timeout=None):
        self._cond.acquire()
        try:
            if self._flag.acquire(False):
                self._flag.release()
            else:
                self._cond.wait(timeout)

            if self._flag.acquire(False):
                self._flag.release()
                return True
            return False
        finally:
            self._cond.release()


if sys.platform != 'win32':
    #
    # Protection against unlinked semaphores if the program ends abnormally
    # and forking has been disabled.
    #

    def _cleanup_semaphore_if_leaked(name):
        name = name.encode('ascii') + bytes('\0', 'ascii')
        if len(name) > 512:
            # posix guarantees that writes to a pipe of less than PIPE_BUF
            # bytes are atomic, and that PIPE_BUF >= 512
            raise ValueError('name too long')
        fd = _get_unlinkfd()
        bits = os.write(fd, name)
        assert bits == len(name)

    def _get_unlinkfd():
        cp = current_process()
        if cp._unlinkfd is None:
            r, w = os.pipe()
            pid = os.fork()
            if pid == 0:
                try:
                    from setproctitle import setproctitle
                    setproctitle("[sem_cleanup for %r]" % cp.pid)
                except:
                    pass

                # Fork a process which will survive until all other processes
                # which have a copy of the write end of the pipe have exited.
                # The forked process just collects names of semaphores until
                # EOF is indicated.  Then it tries unlinking all the names it
                # has collected.
                _collect_names_then_unlink(r)
                os._exit(0)
            os.close(r)
            cp._unlinkfd = w
        return cp._unlinkfd

    def _collect_names_then_unlink(r):
        # protect the process from ^C and "killall python" etc
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

        # close all fds except r
        try:
            MAXFD = os.sysconf("SC_OPEN_MAX")
        except:
            MAXFD = 256
        closerange(0, r)
        closerange(r + 1, MAXFD)

        # collect data written to pipe
        data = []
        while 1:
            try:
                s = os.read(r, 512)
            except:
                # XXX IO lock might be held at fork, so don't try
                # printing unexpected exception - see issue 6721
                pass
            else:
                if not s:
                    break
                data.append(s)

        # attempt to unlink each collected name
        for name in bytes('', 'ascii').join(data).split(bytes('\0', 'ascii')):
            try:
                sem_unlink(name.decode('ascii'))
            except:
                # XXX IO lock might be held at fork, so don't try
                # printing unexpected exception - see issue 6721
                pass

########NEW FILE########
__FILENAME__ = compat
from __future__ import absolute_import

import sys


class WarningMessage(object):

    """Holds the result of a single showwarning() call."""

    _WARNING_DETAILS = ('message', 'category', 'filename', 'lineno', 'file',
                        'line')

    def __init__(self, message, category, filename, lineno, file=None,
                 line=None):
        local_values = locals()
        for attr in self._WARNING_DETAILS:
            setattr(self, attr, local_values[attr])

        self._category_name = category and category.__name__ or None

    def __str__(self):
        return ('{message : %r, category : %r, filename : %r, lineno : %s, '
                'line : %r}' % (self.message, self._category_name,
                                self.filename, self.lineno, self.line))


class catch_warnings(object):

    """A context manager that copies and restores the warnings filter upon
    exiting the context.

    The 'record' argument specifies whether warnings should be captured by a
    custom implementation of warnings.showwarning() and be appended to a list
    returned by the context manager. Otherwise None is returned by the context
    manager. The objects appended to the list are arguments whose attributes
    mirror the arguments to showwarning().

    The 'module' argument is to specify an alternative module to the module
    named 'warnings' and imported under that name. This argument is only
    useful when testing the warnings module itself.

    """

    def __init__(self, record=False, module=None):
        """Specify whether to record warnings and if an alternative module
        should be used other than sys.modules['warnings'].

        For compatibility with Python 3.0, please consider all arguments to be
        keyword-only.

        """
        self._record = record
        self._module = module is None and sys.modules['warnings'] or module
        self._entered = False

    def __repr__(self):
        args = []
        if self._record:
            args.append('record=True')
        if self._module is not sys.modules['warnings']:
            args.append('module=%r' % self._module)
        name = type(self).__name__
        return '%s(%s)' % (name, ', '.join(args))

    def __enter__(self):
        if self._entered:
            raise RuntimeError('Cannot enter %r twice' % self)
        self._entered = True
        self._filters = self._module.filters
        self._module.filters = self._filters[:]
        self._showwarning = self._module.showwarning
        if self._record:
            log = []

            def showwarning(*args, **kwargs):
                log.append(WarningMessage(*args, **kwargs))

            self._module.showwarning = showwarning
            return log

    def __exit__(self, *exc_info):
        if not self._entered:
            raise RuntimeError('Cannot exit %r without entering first' % self)
        self._module.filters = self._filters
        self._module.showwarning = self._showwarning

########NEW FILE########
__FILENAME__ = test_common
from __future__ import absolute_import

import os
import signal

from contextlib import contextmanager
from mock import call, patch, Mock
from time import time

from billiard.common import (
    _shutdown_cleanup,
    reset_signals,
    restart_state,
)

from .utils import Case


def signo(name):
    return getattr(signal, name)


@contextmanager
def termsigs(default, full):
    from billiard import common
    prev_def, common.TERMSIGS_DEFAULT = common.TERMSIGS_DEFAULT, default
    prev_full, common.TERMSIGS_FULL = common.TERMSIGS_FULL, full
    try:
        yield
    finally:
        common.TERMSIGS_DEFAULT, common.TERMSIGS_FULL = prev_def, prev_full


class test_reset_signals(Case):

    def test_shutdown_handler(self):
        with patch('sys.exit') as exit:
            _shutdown_cleanup(15, Mock())
            self.assertTrue(exit.called)
            self.assertEqual(os.WTERMSIG(exit.call_args[0][0]), 15)

    def test_does_not_reset_ignored_signal(self, sigs=['SIGTERM']):
        with self.assert_context(sigs, [], signal.SIG_IGN) as (_, SET):
            self.assertFalse(SET.called)

    def test_does_not_reset_if_current_is_None(self, sigs=['SIGTERM']):
        with self.assert_context(sigs, [], None) as (_, SET):
            self.assertFalse(SET.called)

    def test_resets_for_SIG_DFL(self, sigs=['SIGTERM', 'SIGINT', 'SIGUSR1']):
        with self.assert_context(sigs, [], signal.SIG_DFL) as (_, SET):
            SET.assert_has_calls([
                call(signo(sig), _shutdown_cleanup) for sig in sigs
            ])

    def test_resets_for_obj(self, sigs=['SIGTERM', 'SIGINT', 'SIGUSR1']):
        with self.assert_context(sigs, [], object()) as (_, SET):
            SET.assert_has_calls([
                call(signo(sig), _shutdown_cleanup) for sig in sigs
            ])

    def test_handles_errors(self, sigs=['SIGTERM']):
        for exc in (OSError(), AttributeError(),
                    ValueError(), RuntimeError()):
            with self.assert_context(sigs, [], signal.SIG_DFL, exc) as (_, S):
                self.assertTrue(S.called)

    @contextmanager
    def assert_context(self, default, full, get_returns=None, set_effect=None):
        with termsigs(default, full):
            with patch('signal.getsignal') as GET:
                with patch('signal.signal') as SET:
                    GET.return_value = get_returns
                    SET.side_effect = set_effect
                    reset_signals()
                    GET.assert_has_calls([
                        call(signo(sig)) for sig in default
                    ])
                    yield GET, SET


class test_restart_state(Case):

    def test_raises(self):
        s = restart_state(100, 1)  # max 100 restarts in 1 second.
        s.R = 99
        s.step()
        with self.assertRaises(s.RestartFreqExceeded):
            s.step()

    def test_time_passed_resets_counter(self):
        s = restart_state(100, 10)
        s.R, s.T = 100, time()
        with self.assertRaises(s.RestartFreqExceeded):
            s.step()
        s.R, s.T = 100, time()
        s.step(time() + 20)
        self.assertEqual(s.R, 1)

########NEW FILE########
__FILENAME__ = test_package
from __future__ import absolute_import

import billiard

from .utils import Case


class test_billiard(Case):

    def test_has_version(self):
        self.assertTrue(billiard.__version__)
        self.assertIsInstance(billiard.__version__, str)

########NEW FILE########
__FILENAME__ = utils
from __future__ import absolute_import

import re
import sys
import warnings

try:
    import unittest  # noqa
    unittest.skip
    from unittest.util import safe_repr, unorderable_list_difference
except AttributeError:
    import unittest2 as unittest  # noqa
    from unittest2.util import safe_repr, unorderable_list_difference  # noqa

from billiard.five import string_t, items, values

from .compat import catch_warnings

# -- adds assertWarns from recent unittest2, not in Python 2.7.


class _AssertRaisesBaseContext(object):

    def __init__(self, expected, test_case, callable_obj=None,
                 expected_regex=None):
        self.expected = expected
        self.failureException = test_case.failureException
        self.obj_name = None
        if isinstance(expected_regex, string_t):
            expected_regex = re.compile(expected_regex)
        self.expected_regex = expected_regex


class _AssertWarnsContext(_AssertRaisesBaseContext):
    """A context manager used to implement TestCase.assertWarns* methods."""

    def __enter__(self):
        # The __warningregistry__'s need to be in a pristine state for tests
        # to work properly.
        warnings.resetwarnings()
        for v in values(sys.modules):
            if getattr(v, '__warningregistry__', None):
                v.__warningregistry__ = {}
        self.warnings_manager = catch_warnings(record=True)
        self.warnings = self.warnings_manager.__enter__()
        warnings.simplefilter('always', self.expected)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.warnings_manager.__exit__(exc_type, exc_value, tb)
        if exc_type is not None:
            # let unexpected exceptions pass through
            return
        try:
            exc_name = self.expected.__name__
        except AttributeError:
            exc_name = str(self.expected)
        first_matching = None
        for m in self.warnings:
            w = m.message
            if not isinstance(w, self.expected):
                continue
            if first_matching is None:
                first_matching = w
            if (self.expected_regex is not None and
                    not self.expected_regex.search(str(w))):
                continue
            # store warning for later retrieval
            self.warning = w
            self.filename = m.filename
            self.lineno = m.lineno
            return
        # Now we simply try to choose a helpful failure message
        if first_matching is not None:
            raise self.failureException(
                '%r does not match %r' % (
                    self.expected_regex.pattern, str(first_matching)))
        if self.obj_name:
            raise self.failureException(
                '%s not triggered by %s' % (exc_name, self.obj_name))
        else:
            raise self.failureException('%s not triggered' % exc_name)


class Case(unittest.TestCase):

    def assertWarns(self, expected_warning):
        return _AssertWarnsContext(expected_warning, self, None)

    def assertWarnsRegex(self, expected_warning, expected_regex):
        return _AssertWarnsContext(expected_warning, self,
                                   None, expected_regex)

    def assertDictContainsSubset(self, expected, actual, msg=None):
        missing, mismatched = [], []

        for key, value in items(expected):
            if key not in actual:
                missing.append(key)
            elif value != actual[key]:
                mismatched.append('%s, expected: %s, actual: %s' % (
                    safe_repr(key), safe_repr(value),
                    safe_repr(actual[key])))

        if not (missing or mismatched):
            return

        standard_msg = ''
        if missing:
            standard_msg = 'Missing: %s' % ','.join(map(safe_repr, missing))

        if mismatched:
            if standard_msg:
                standard_msg += '; '
            standard_msg += 'Mismatched values: %s' % (
                ','.join(mismatched))

        self.fail(self._formatMessage(msg, standard_msg))

    def assertItemsEqual(self, expected_seq, actual_seq, msg=None):
        missing = unexpected = None
        try:
            expected = sorted(expected_seq)
            actual = sorted(actual_seq)
        except TypeError:
            # Unsortable items (example: set(), complex(), ...)
            expected = list(expected_seq)
            actual = list(actual_seq)
            missing, unexpected = unorderable_list_difference(
                expected, actual)
        else:
            return self.assertSequenceEqual(expected, actual, msg=msg)

        errors = []
        if missing:
            errors.append(
                'Expected, but missing:\n    %s' % (safe_repr(missing), ),
            )
        if unexpected:
            errors.append(
                'Unexpected, but present:\n    %s' % (safe_repr(unexpected), ),
            )
        if errors:
            standardMsg = '\n'.join(errors)
            self.fail(self._formatMessage(msg, standardMsg))

########NEW FILE########
__FILENAME__ = util
#
# Module providing various facilities to other parts of the package
#
# billiard/util.py
#
# Copyright (c) 2006-2008, R Oudkerk --- see COPYING.txt
# Licensed to PSF under a Contributor Agreement.
#
from __future__ import absolute_import

import errno
import functools
import atexit

from multiprocessing.util import (  # noqa
    _afterfork_registry,
    _afterfork_counter,
    _exit_function,
    _finalizer_registry,
    _finalizer_counter,
    Finalize,
    ForkAwareLocal,
    ForkAwareThreadLock,
    get_temp_dir,
    is_exiting,
    register_after_fork,
    _run_after_forkers,
    _run_finalizers,
)

from .compat import get_errno

__all__ = [
    'sub_debug', 'debug', 'info', 'sub_warning', 'get_logger',
    'log_to_stderr', 'get_temp_dir', 'register_after_fork',
    'is_exiting', 'Finalize', 'ForkAwareThreadLock', 'ForkAwareLocal',
    'SUBDEBUG', 'SUBWARNING',
]

#
# Logging
#

NOTSET = 0
SUBDEBUG = 5
DEBUG = 10
INFO = 20
SUBWARNING = 25
ERROR = 40

LOGGER_NAME = 'multiprocessing'
DEFAULT_LOGGING_FORMAT = '[%(levelname)s/%(processName)s] %(message)s'

_logger = None
_log_to_stderr = False


def sub_debug(msg, *args, **kwargs):
    if _logger:
        _logger.log(SUBDEBUG, msg, *args, **kwargs)


def debug(msg, *args, **kwargs):
    if _logger:
        _logger.log(DEBUG, msg, *args, **kwargs)
        return True
    return False


def info(msg, *args, **kwargs):
    if _logger:
        _logger.log(INFO, msg, *args, **kwargs)
        return True
    return False


def sub_warning(msg, *args, **kwargs):
    if _logger:
        _logger.log(SUBWARNING, msg, *args, **kwargs)
        return True
    return False


def error(msg, *args, **kwargs):
    if _logger:
        _logger.log(ERROR, msg, *args, **kwargs)
        return True
    return False


def get_logger():
    '''
    Returns logger used by multiprocessing
    '''
    global _logger
    import logging

    logging._acquireLock()
    try:
        if not _logger:

            _logger = logging.getLogger(LOGGER_NAME)
            _logger.propagate = 0
            logging.addLevelName(SUBDEBUG, 'SUBDEBUG')
            logging.addLevelName(SUBWARNING, 'SUBWARNING')

            # XXX multiprocessing should cleanup before logging
            if hasattr(atexit, 'unregister'):
                atexit.unregister(_exit_function)
                atexit.register(_exit_function)
            else:
                atexit._exithandlers.remove((_exit_function, (), {}))
                atexit._exithandlers.append((_exit_function, (), {}))
    finally:
        logging._releaseLock()

    return _logger


def log_to_stderr(level=None):
    '''
    Turn on logging and add a handler which prints to stderr
    '''
    global _log_to_stderr
    import logging

    logger = get_logger()
    formatter = logging.Formatter(DEFAULT_LOGGING_FORMAT)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if level:
        logger.setLevel(level)
    _log_to_stderr = True
    return _logger


def _eintr_retry(func):
    '''
    Automatic retry after EINTR.
    '''

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        while 1:
            try:
                return func(*args, **kwargs)
            except OSError as exc:
                if get_errno(exc) != errno.EINTR:
                    raise
    return wrapped

########NEW FILE########
__FILENAME__ = _ext
from __future__ import absolute_import

import sys

supports_exec = True

from .compat import _winapi as win32  # noqa

if sys.platform.startswith("java"):
    _billiard = None
else:
    try:
        import _billiard                                # noqa
    except ImportError:
        import _multiprocessing as _billiard            # noqa
        supports_exec = False
    try:
        Connection = _billiard.Connection
    except AttributeError:  # Py3
        from billiard.connection import Connection  # noqa

    PipeConnection = getattr(_billiard, "PipeConnection", None)


def ensure_multiprocessing():
    if _billiard is None:
        raise NotImplementedError("multiprocessing not supported")


def ensure_SemLock():
    try:
        from _billiard import SemLock                   # noqa
    except ImportError:
        try:
            from _multiprocessing import SemLock        # noqa
        except ImportError:
            raise ImportError("""\
This platform lacks a functioning sem_open implementation, therefore,
the required synchronization primitives needed will not function,
see issue 3770.""")

########NEW FILE########
__FILENAME__ = _win
# -*- coding: utf-8 -*-
"""
    billiard._win
    ~~~~~~~~~~~~~

    Windows utilities to terminate process groups.

"""
from __future__ import absolute_import

import os

# psutil is painfully slow in win32. So to avoid adding big
# dependencies like pywin32 a ctypes based solution is preferred

# Code based on the winappdbg project http://winappdbg.sourceforge.net/
# (BSD License)
from ctypes import (
    byref, sizeof, windll,
    Structure, WinError, POINTER,
    c_size_t, c_char, c_void_p,
)
from ctypes.wintypes import DWORD, LONG

ERROR_NO_MORE_FILES = 18
INVALID_HANDLE_VALUE = c_void_p(-1).value


class PROCESSENTRY32(Structure):
    _fields_ = [
        ('dwSize',              DWORD),
        ('cntUsage',            DWORD),
        ('th32ProcessID',       DWORD),
        ('th32DefaultHeapID',   c_size_t),
        ('th32ModuleID',        DWORD),
        ('cntThreads',          DWORD),
        ('th32ParentProcessID', DWORD),
        ('pcPriClassBase',      LONG),
        ('dwFlags',             DWORD),
        ('szExeFile',           c_char * 260),
    ]
LPPROCESSENTRY32 = POINTER(PROCESSENTRY32)


def CreateToolhelp32Snapshot(dwFlags=2, th32ProcessID=0):
    hSnapshot = windll.kernel32.CreateToolhelp32Snapshot(dwFlags,
                                                         th32ProcessID)
    if hSnapshot == INVALID_HANDLE_VALUE:
        raise WinError()
    return hSnapshot


def Process32First(hSnapshot, pe=None):
    return _Process32n(windll.kernel32.Process32First, hSnapshot, pe)


def Process32Next(hSnapshot, pe=None):
    return _Process32n(windll.kernel32.Process32Next, hSnapshot, pe)


def _Process32n(fun, hSnapshot, pe=None):
    if pe is None:
        pe = PROCESSENTRY32()
    pe.dwSize = sizeof(PROCESSENTRY32)
    success = fun(hSnapshot, byref(pe))
    if not success:
        if windll.kernel32.GetLastError() == ERROR_NO_MORE_FILES:
            return
        raise WinError()
    return pe


def get_all_processes_pids():
    """Return a dictionary with all processes pids as keys and their
       parents as value. Ignore processes with no parents.
    """
    h = CreateToolhelp32Snapshot()
    parents = {}
    pe = Process32First(h)
    while pe:
        if pe.th32ParentProcessID:
            parents[pe.th32ProcessID] = pe.th32ParentProcessID
        pe = Process32Next(h, pe)

    return parents


def get_processtree_pids(pid, include_parent=True):
    """Return a list with all the pids of a process tree"""
    parents = get_all_processes_pids()
    all_pids = list(parents.keys())
    pids = set([pid])
    while 1:
        pids_new = pids.copy()

        for _pid in all_pids:
            if parents[_pid] in pids:
                pids_new.add(_pid)

        if pids_new == pids:
            break

        pids = pids_new.copy()

    if not include_parent:
        pids.remove(pid)

    return list(pids)


def kill_processtree(pid, signum):
    """Kill a process and all its descendants"""
    family_pids = get_processtree_pids(pid)

    for _pid in family_pids:
        os.kill(_pid, signum)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# multiprocessing documentation build configuration file, created by
# sphinx-quickstart on Wed Nov 26 12:47:00 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'multiprocessing'
copyright = u'2008, Python Software Foundation'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

import os
import sys
sys.path.insert(0, os.path.join(os.getcwd(), os.pardir))
import billiard
#
# The short X.Y version.
version = billiard.__version__
# The full version, including alpha/beta/rc tags.
release = billiard.__version__

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
exclude_trees = ['build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

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
html_static_path = ['static']

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

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'multiprocessingdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'multiprocessing.tex', ur'multiprocessing Documentation',
   ur'Python Software Foundation', 'manual'),
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
__FILENAME__ = mp_benchmarks
#
# Simple benchmarks for the multiprocessing package
#
# Copyright (c) 2006-2008, R Oudkerk
# All rights reserved.
#

import time, sys, multiprocessing, threading, Queue, gc

if sys.platform == 'win32':
    _timer = time.clock
else:
    _timer = time.time

delta = 1


#### TEST_QUEUESPEED

def queuespeed_func(q, c, iterations):
    a = '0' * 256
    c.acquire()
    c.notify()
    c.release()

    for i in xrange(iterations):
        q.put(a)

    q.put('STOP')

def test_queuespeed(Process, q, c):
    elapsed = 0
    iterations = 1

    while elapsed < delta:
        iterations *= 2

        p = Process(target=queuespeed_func, args=(q, c, iterations))
        c.acquire()
        p.start()
        c.wait()
        c.release()

        result = None
        t = _timer()

        while result != 'STOP':
            result = q.get()

        elapsed = _timer() - t

        p.join()

    print iterations, 'objects passed through the queue in', elapsed, 'seconds'
    print 'average number/sec:', iterations/elapsed


#### TEST_PIPESPEED

def pipe_func(c, cond, iterations):
    a = '0' * 256
    cond.acquire()
    cond.notify()
    cond.release()

    for i in xrange(iterations):
        c.send(a)

    c.send('STOP')

def test_pipespeed():
    c, d = multiprocessing.Pipe()
    cond = multiprocessing.Condition()
    elapsed = 0
    iterations = 1

    while elapsed < delta:
        iterations *= 2

        p = multiprocessing.Process(target=pipe_func,
                                    args=(d, cond, iterations))
        cond.acquire()
        p.start()
        cond.wait()
        cond.release()

        result = None
        t = _timer()

        while result != 'STOP':
            result = c.recv()

        elapsed = _timer() - t
        p.join()

    print iterations, 'objects passed through connection in',elapsed,'seconds'
    print 'average number/sec:', iterations/elapsed


#### TEST_SEQSPEED

def test_seqspeed(seq):
    elapsed = 0
    iterations = 1

    while elapsed < delta:
        iterations *= 2

        t = _timer()

        for i in xrange(iterations):
            a = seq[5]

        elapsed = _timer()-t

    print iterations, 'iterations in', elapsed, 'seconds'
    print 'average number/sec:', iterations/elapsed


#### TEST_LOCK

def test_lockspeed(l):
    elapsed = 0
    iterations = 1

    while elapsed < delta:
        iterations *= 2

        t = _timer()

        for i in xrange(iterations):
            l.acquire()
            l.release()

        elapsed = _timer()-t

    print iterations, 'iterations in', elapsed, 'seconds'
    print 'average number/sec:', iterations/elapsed


#### TEST_CONDITION

def conditionspeed_func(c, N):
    c.acquire()
    c.notify()

    for i in xrange(N):
        c.wait()
        c.notify()

    c.release()

def test_conditionspeed(Process, c):
    elapsed = 0
    iterations = 1

    while elapsed < delta:
        iterations *= 2

        c.acquire()
        p = Process(target=conditionspeed_func, args=(c, iterations))
        p.start()

        c.wait()

        t = _timer()

        for i in xrange(iterations):
            c.notify()
            c.wait()

        elapsed = _timer()-t

        c.release()
        p.join()

    print iterations * 2, 'waits in', elapsed, 'seconds'
    print 'average number/sec:', iterations * 2 / elapsed

####

def test():
    manager = multiprocessing.Manager()

    gc.disable()

    print '\n\t######## testing Queue.Queue\n'
    test_queuespeed(threading.Thread, Queue.Queue(),
                    threading.Condition())
    print '\n\t######## testing multiprocessing.Queue\n'
    test_queuespeed(multiprocessing.Process, multiprocessing.Queue(),
                    multiprocessing.Condition())
    print '\n\t######## testing Queue managed by server process\n'
    test_queuespeed(multiprocessing.Process, manager.Queue(),
                    manager.Condition())
    print '\n\t######## testing multiprocessing.Pipe\n'
    test_pipespeed()

    print

    print '\n\t######## testing list\n'
    test_seqspeed(range(10))
    print '\n\t######## testing list managed by server process\n'
    test_seqspeed(manager.list(range(10)))
    print '\n\t######## testing Array("i", ..., lock=False)\n'
    test_seqspeed(multiprocessing.Array('i', range(10), lock=False))
    print '\n\t######## testing Array("i", ..., lock=True)\n'
    test_seqspeed(multiprocessing.Array('i', range(10), lock=True))

    print

    print '\n\t######## testing threading.Lock\n'
    test_lockspeed(threading.Lock())
    print '\n\t######## testing threading.RLock\n'
    test_lockspeed(threading.RLock())
    print '\n\t######## testing multiprocessing.Lock\n'
    test_lockspeed(multiprocessing.Lock())
    print '\n\t######## testing multiprocessing.RLock\n'
    test_lockspeed(multiprocessing.RLock())
    print '\n\t######## testing lock managed by server process\n'
    test_lockspeed(manager.Lock())
    print '\n\t######## testing rlock managed by server process\n'
    test_lockspeed(manager.RLock())

    print

    print '\n\t######## testing threading.Condition\n'
    test_conditionspeed(threading.Thread, threading.Condition())
    print '\n\t######## testing multiprocessing.Condition\n'
    test_conditionspeed(multiprocessing.Process, multiprocessing.Condition())
    print '\n\t######## testing condition managed by a server process\n'
    test_conditionspeed(multiprocessing.Process, manager.Condition())

    gc.enable()

if __name__ == '__main__':
    multiprocessing.freeze_support()
    test()

########NEW FILE########
__FILENAME__ = mp_newtype
#
# This module shows how to use arbitrary callables with a subclass of
# `BaseManager`.
#
# Copyright (c) 2006-2008, R Oudkerk
# All rights reserved.
#

from multiprocessing import freeze_support
from multiprocessing.managers import BaseManager, BaseProxy
import operator

##

class Foo(object):
    def f(self):
        print 'you called Foo.f()'
    def g(self):
        print 'you called Foo.g()'
    def _h(self):
        print 'you called Foo._h()'

# A simple generator function
def baz():
    for i in xrange(10):
        yield i*i

# Proxy type for generator objects
class GeneratorProxy(BaseProxy):
    _exposed_ = ('next', '__next__')
    def __iter__(self):
        return self
    def next(self):
        return self._callmethod('next')
    def __next__(self):
        return self._callmethod('__next__')

# Function to return the operator module
def get_operator_module():
    return operator

##

class MyManager(BaseManager):
    pass

# register the Foo class; make `f()` and `g()` accessible via proxy
MyManager.register('Foo1', Foo)

# register the Foo class; make `g()` and `_h()` accessible via proxy
MyManager.register('Foo2', Foo, exposed=('g', '_h'))

# register the generator function baz; use `GeneratorProxy` to make proxies
MyManager.register('baz', baz, proxytype=GeneratorProxy)

# register get_operator_module(); make public functions accessible via proxy
MyManager.register('operator', get_operator_module)

##

def test():
    manager = MyManager()
    manager.start()

    print '-' * 20

    f1 = manager.Foo1()
    f1.f()
    f1.g()
    assert not hasattr(f1, '_h')
    assert sorted(f1._exposed_) == sorted(['f', 'g'])

    print '-' * 20

    f2 = manager.Foo2()
    f2.g()
    f2._h()
    assert not hasattr(f2, 'f')
    assert sorted(f2._exposed_) == sorted(['g', '_h'])

    print '-' * 20

    it = manager.baz()
    for i in it:
        print '<%d>' % i,
    print

    print '-' * 20

    op = manager.operator()
    print 'op.add(23, 45) =', op.add(23, 45)
    print 'op.pow(2, 94) =', op.pow(2, 94)
    print 'op.getslice(range(10), 2, 6) =', op.getslice(range(10), 2, 6)
    print 'op.repeat(range(5), 3) =', op.repeat(range(5), 3)
    print 'op._exposed_ =', op._exposed_

##

if __name__ == '__main__':
    freeze_support()
    test()

########NEW FILE########
__FILENAME__ = mp_pool
#
# A test of `multiprocessing.Pool` class
#
# Copyright (c) 2006-2008, R Oudkerk
# All rights reserved.
#

import multiprocessing
import time
import random
import sys

#
# Functions used by test code
#

def calculate(func, args):
    result = func(*args)
    return '%s says that %s%s = %s' % (
        multiprocessing.current_process().name,
        func.__name__, args, result
        )

def calculatestar(args):
    return calculate(*args)

def mul(a, b):
    time.sleep(0.5*random.random())
    return a * b

def plus(a, b):
    time.sleep(0.5*random.random())
    return a + b

def f(x):
    return 1.0 / (x-5.0)

def pow3(x):
    return x**3

def noop(x):
    pass

#
# Test code
#

def test():
    print 'cpu_count() = %d\n' % multiprocessing.cpu_count()

    #
    # Create pool
    #

    PROCESSES = 4
    print 'Creating pool with %d processes\n' % PROCESSES
    pool = multiprocessing.Pool(PROCESSES)
    print 'pool = %s' % pool
    print

    #
    # Tests
    #

    TASKS = [(mul, (i, 7)) for i in range(10)] + \
            [(plus, (i, 8)) for i in range(10)]

    results = [pool.apply_async(calculate, t) for t in TASKS]
    imap_it = pool.imap(calculatestar, TASKS)
    imap_unordered_it = pool.imap_unordered(calculatestar, TASKS)

    print 'Ordered results using pool.apply_async():'
    for r in results:
        print '\t', r.get()
    print

    print 'Ordered results using pool.imap():'
    for x in imap_it:
        print '\t', x
    print

    print 'Unordered results using pool.imap_unordered():'
    for x in imap_unordered_it:
        print '\t', x
    print

    print 'Ordered results using pool.map() --- will block till complete:'
    for x in pool.map(calculatestar, TASKS):
        print '\t', x
    print

    #
    # Simple benchmarks
    #

    N = 100000
    print 'def pow3(x): return x**3'

    t = time.time()
    A = map(pow3, xrange(N))
    print '\tmap(pow3, xrange(%d)):\n\t\t%s seconds' % \
          (N, time.time() - t)

    t = time.time()
    B = pool.map(pow3, xrange(N))
    print '\tpool.map(pow3, xrange(%d)):\n\t\t%s seconds' % \
          (N, time.time() - t)

    t = time.time()
    C = list(pool.imap(pow3, xrange(N), chunksize=N//8))
    print '\tlist(pool.imap(pow3, xrange(%d), chunksize=%d)):\n\t\t%s' \
          ' seconds' % (N, N//8, time.time() - t)

    assert A == B == C, (len(A), len(B), len(C))
    print

    L = [None] * 1000000
    print 'def noop(x): pass'
    print 'L = [None] * 1000000'

    t = time.time()
    A = map(noop, L)
    print '\tmap(noop, L):\n\t\t%s seconds' % \
          (time.time() - t)

    t = time.time()
    B = pool.map(noop, L)
    print '\tpool.map(noop, L):\n\t\t%s seconds' % \
          (time.time() - t)

    t = time.time()
    C = list(pool.imap(noop, L, chunksize=len(L)//8))
    print '\tlist(pool.imap(noop, L, chunksize=%d)):\n\t\t%s seconds' % \
          (len(L)//8, time.time() - t)

    assert A == B == C, (len(A), len(B), len(C))
    print

    del A, B, C, L

    #
    # Test error handling
    #

    print 'Testing error handling:'

    try:
        print pool.apply(f, (5,))
    except ZeroDivisionError:
        print '\tGot ZeroDivisionError as expected from pool.apply()'
    else:
        raise AssertionError, 'expected ZeroDivisionError'

    try:
        print pool.map(f, range(10))
    except ZeroDivisionError:
        print '\tGot ZeroDivisionError as expected from pool.map()'
    else:
        raise AssertionError, 'expected ZeroDivisionError'

    try:
        print list(pool.imap(f, range(10)))
    except ZeroDivisionError:
        print '\tGot ZeroDivisionError as expected from list(pool.imap())'
    else:
        raise AssertionError, 'expected ZeroDivisionError'

    it = pool.imap(f, range(10))
    for i in range(10):
        try:
            x = it.next()
        except ZeroDivisionError:
            if i == 5:
                pass
        except StopIteration:
            break
        else:
            if i == 5:
                raise AssertionError, 'expected ZeroDivisionError'

    assert i == 9
    print '\tGot ZeroDivisionError as expected from IMapIterator.next()'
    print

    #
    # Testing timeouts
    #

    print 'Testing ApplyResult.get() with timeout:',
    res = pool.apply_async(calculate, TASKS[0])
    while 1:
        sys.stdout.flush()
        try:
            sys.stdout.write('\n\t%s' % res.get(0.02))
            break
        except multiprocessing.TimeoutError:
            sys.stdout.write('.')
    print
    print

    print 'Testing IMapIterator.next() with timeout:',
    it = pool.imap(calculatestar, TASKS)
    while 1:
        sys.stdout.flush()
        try:
            sys.stdout.write('\n\t%s' % it.next(0.02))
        except StopIteration:
            break
        except multiprocessing.TimeoutError:
            sys.stdout.write('.')
    print
    print

    #
    # Testing callback
    #

    print 'Testing callback:'

    A = []
    B = [56, 0, 1, 8, 27, 64, 125, 216, 343, 512, 729]

    r = pool.apply_async(mul, (7, 8), callback=A.append)
    r.wait()

    r = pool.map_async(pow3, range(10), callback=A.extend)
    r.wait()

    if A == B:
        print '\tcallbacks succeeded\n'
    else:
        print '\t*** callbacks failed\n\t\t%s != %s\n' % (A, B)

    #
    # Check there are no outstanding tasks
    #

    assert not pool._cache, 'cache = %r' % pool._cache

    #
    # Check close() methods
    #

    print 'Testing close():'

    for worker in pool._pool:
        assert worker.is_alive()

    result = pool.apply_async(time.sleep, [0.5])
    pool.close()
    pool.join()

    assert result.get() is None

    for worker in pool._pool:
        assert not worker.is_alive()

    print '\tclose() succeeded\n'

    #
    # Check terminate() method
    #

    print 'Testing terminate():'

    pool = multiprocessing.Pool(2)
    DELTA = 0.1
    ignore = pool.apply(pow3, [2])
    results = [pool.apply_async(time.sleep, [DELTA]) for i in range(100)]
    pool.terminate()
    pool.join()

    for worker in pool._pool:
        assert not worker.is_alive()

    print '\tterminate() succeeded\n'

    #
    # Check garbage collection
    #

    print 'Testing garbage collection:'

    pool = multiprocessing.Pool(2)
    DELTA = 0.1
    processes = pool._pool
    ignore = pool.apply(pow3, [2])
    results = [pool.apply_async(time.sleep, [DELTA]) for i in range(100)]

    results = pool = None

    time.sleep(DELTA * 2)

    for worker in processes:
        assert not worker.is_alive()

    print '\tgarbage collection succeeded\n'


if __name__ == '__main__':
    multiprocessing.freeze_support()

    assert len(sys.argv) in (1, 2)

    if len(sys.argv) == 1 or sys.argv[1] == 'processes':
        print ' Using processes '.center(79, '-')
    elif sys.argv[1] == 'threads':
        print ' Using threads '.center(79, '-')
        import multiprocessing.dummy as multiprocessing
    else:
        print 'Usage:\n\t%s [processes | threads]' % sys.argv[0]
        raise SystemExit(2)

    test()

########NEW FILE########
__FILENAME__ = mp_synchronize
#
# A test file for the `multiprocessing` package
#
# Copyright (c) 2006-2008, R Oudkerk
# All rights reserved.
#

import time, sys, random
from Queue import Empty

import multiprocessing               # may get overwritten


#### TEST_VALUE

def value_func(running, mutex):
    random.seed()
    time.sleep(random.random()*4)

    mutex.acquire()
    print '\n\t\t\t' + str(multiprocessing.current_process()) + ' has finished'
    running.value -= 1
    mutex.release()

def test_value():
    TASKS = 10
    running = multiprocessing.Value('i', TASKS)
    mutex = multiprocessing.Lock()

    for i in range(TASKS):
        p = multiprocessing.Process(target=value_func, args=(running, mutex))
        p.start()

    while running.value > 0:
        time.sleep(0.08)
        mutex.acquire()
        print running.value,
        sys.stdout.flush()
        mutex.release()

    print
    print 'No more running processes'


#### TEST_QUEUE

def queue_func(queue):
    for i in range(30):
        time.sleep(0.5 * random.random())
        queue.put(i*i)
    queue.put('STOP')

def test_queue():
    q = multiprocessing.Queue()

    p = multiprocessing.Process(target=queue_func, args=(q,))
    p.start()

    o = None
    while o != 'STOP':
        try:
            o = q.get(timeout=0.3)
            print o,
            sys.stdout.flush()
        except Empty:
            print 'TIMEOUT'

    print


#### TEST_CONDITION

def condition_func(cond):
    cond.acquire()
    print '\t' + str(cond)
    time.sleep(2)
    print '\tchild is notifying'
    print '\t' + str(cond)
    cond.notify()
    cond.release()

def test_condition():
    cond = multiprocessing.Condition()

    p = multiprocessing.Process(target=condition_func, args=(cond,))
    print cond

    cond.acquire()
    print cond
    cond.acquire()
    print cond

    p.start()

    print 'main is waiting'
    cond.wait()
    print 'main has woken up'

    print cond
    cond.release()
    print cond
    cond.release()

    p.join()
    print cond


#### TEST_SEMAPHORE

def semaphore_func(sema, mutex, running):
    sema.acquire()

    mutex.acquire()
    running.value += 1
    print running.value, 'tasks are running'
    mutex.release()

    random.seed()
    time.sleep(random.random()*2)

    mutex.acquire()
    running.value -= 1
    print '%s has finished' % multiprocessing.current_process()
    mutex.release()

    sema.release()

def test_semaphore():
    sema = multiprocessing.Semaphore(3)
    mutex = multiprocessing.RLock()
    running = multiprocessing.Value('i', 0)

    processes = [
        multiprocessing.Process(target=semaphore_func,
                                args=(sema, mutex, running))
        for i in range(10)
        ]

    for p in processes:
        p.start()

    for p in processes:
        p.join()


#### TEST_JOIN_TIMEOUT

def join_timeout_func():
    print '\tchild sleeping'
    time.sleep(5.5)
    print '\n\tchild terminating'

def test_join_timeout():
    p = multiprocessing.Process(target=join_timeout_func)
    p.start()

    print 'waiting for process to finish'

    while 1:
        p.join(timeout=1)
        if not p.is_alive():
            break
        print '.',
        sys.stdout.flush()


#### TEST_EVENT

def event_func(event):
    print '\t%r is waiting' % multiprocessing.current_process()
    event.wait()
    print '\t%r has woken up' % multiprocessing.current_process()

def test_event():
    event = multiprocessing.Event()

    processes = [multiprocessing.Process(target=event_func, args=(event,))
                 for i in range(5)]

    for p in processes:
        p.start()

    print 'main is sleeping'
    time.sleep(2)

    print 'main is setting event'
    event.set()

    for p in processes:
        p.join()


#### TEST_SHAREDVALUES

def sharedvalues_func(values, arrays, shared_values, shared_arrays):
    for i in range(len(values)):
        v = values[i][1]
        sv = shared_values[i].value
        assert v == sv

    for i in range(len(values)):
        a = arrays[i][1]
        sa = list(shared_arrays[i][:])
        assert a == sa

    print 'Tests passed'

def test_sharedvalues():
    values = [
        ('i', 10),
        ('h', -2),
        ('d', 1.25)
        ]
    arrays = [
        ('i', range(100)),
        ('d', [0.25 * i for i in range(100)]),
        ('H', range(1000))
        ]

    shared_values = [multiprocessing.Value(id, v) for id, v in values]
    shared_arrays = [multiprocessing.Array(id, a) for id, a in arrays]

    p = multiprocessing.Process(
        target=sharedvalues_func,
        args=(values, arrays, shared_values, shared_arrays)
        )
    p.start()
    p.join()

    assert p.exitcode == 0


####

def test(namespace=multiprocessing):
    global multiprocessing

    multiprocessing = namespace

    for func in [ test_value, test_queue, test_condition,
                  test_semaphore, test_join_timeout, test_event,
                  test_sharedvalues ]:

        print '\n\t######## %s\n' % func.__name__
        func()

    ignore = multiprocessing.active_children()      # cleanup any old processes
    if hasattr(multiprocessing, '_debug_info'):
        info = multiprocessing._debug_info()
        if info:
            print info
            raise ValueError, 'there should be no positive refcounts left'


if __name__ == '__main__':
    multiprocessing.freeze_support()

    assert len(sys.argv) in (1, 2)

    if len(sys.argv) == 1 or sys.argv[1] == 'processes':
        print ' Using processes '.center(79, '-')
        namespace = multiprocessing
    elif sys.argv[1] == 'manager':
        print ' Using processes and a manager '.center(79, '-')
        namespace = multiprocessing.Manager()
        namespace.Process = multiprocessing.Process
        namespace.current_process = multiprocessing.current_process
        namespace.active_children = multiprocessing.active_children
    elif sys.argv[1] == 'threads':
        print ' Using threads '.center(79, '-')
        import multiprocessing.dummy as namespace
    else:
        print 'Usage:\n\t%s [processes | manager | threads]' % sys.argv[0]
        raise SystemExit, 2

    test(namespace)

########NEW FILE########
__FILENAME__ = mp_webserver
#
# Example where a pool of http servers share a single listening socket
#
# On Windows this module depends on the ability to pickle a socket
# object so that the worker processes can inherit a copy of the server
# object.  (We import `multiprocessing.reduction` to enable this pickling.)
#
# Not sure if we should synchronize access to `socket.accept()` method by
# using a process-shared lock -- does not seem to be necessary.
#
# Copyright (c) 2006-2008, R Oudkerk
# All rights reserved.
#

import os
import sys

from multiprocessing import Process, current_process, freeze_support
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler

if sys.platform == 'win32':
    import multiprocessing.reduction    # make sockets pickable/inheritable


def note(format, *args):
    sys.stderr.write('[%s]\t%s\n' % (current_process().name, format%args))


class RequestHandler(SimpleHTTPRequestHandler):
    # we override log_message() to show which process is handling the request
    def log_message(self, format, *args):
        note(format, *args)

def serve_forever(server):
    note('starting server')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def runpool(address, number_of_processes):
    # create a single server object -- children will each inherit a copy
    server = HTTPServer(address, RequestHandler)

    # create child processes to act as workers
    for i in range(number_of_processes-1):
        Process(target=serve_forever, args=(server,)).start()

    # main process also acts as a worker
    serve_forever(server)


def test():
    DIR = os.path.join(os.path.dirname(__file__), '..')
    ADDRESS = ('localhost', 8000)
    NUMBER_OF_PROCESSES = 4

    print 'Serving at http://%s:%d using %d worker processes' % \
          (ADDRESS[0], ADDRESS[1], NUMBER_OF_PROCESSES)
    print 'To exit press Ctrl-' + ['C', 'Break'][sys.platform=='win32']

    os.chdir(DIR)
    runpool(ADDRESS, NUMBER_OF_PROCESSES)


if __name__ == '__main__':
    freeze_support()
    test()

########NEW FILE########
__FILENAME__ = mp_workers
#
# Simple example which uses a pool of workers to carry out some tasks.
#
# Notice that the results will probably not come out of the output
# queue in the same in the same order as the corresponding tasks were
# put on the input queue.  If it is important to get the results back
# in the original order then consider using `Pool.map()` or
# `Pool.imap()` (which will save on the amount of code needed anyway).
#
# Copyright (c) 2006-2008, R Oudkerk
# All rights reserved.
#

import time
import random

from multiprocessing import Process, Queue, current_process, freeze_support

#
# Function run by worker processes
#

def worker(input, output):
    for func, args in iter(input.get, 'STOP'):
        result = calculate(func, args)
        output.put(result)

#
# Function used to calculate result
#

def calculate(func, args):
    result = func(*args)
    return '%s says that %s%s = %s' % \
        (current_process().name, func.__name__, args, result)

#
# Functions referenced by tasks
#

def mul(a, b):
    time.sleep(0.5*random.random())
    return a * b

def plus(a, b):
    time.sleep(0.5*random.random())
    return a + b

#
#
#

def test():
    NUMBER_OF_PROCESSES = 4
    TASKS1 = [(mul, (i, 7)) for i in range(20)]
    TASKS2 = [(plus, (i, 8)) for i in range(10)]

    # Create queues
    task_queue = Queue()
    done_queue = Queue()

    # Submit tasks
    for task in TASKS1:
        task_queue.put(task)

    # Start worker processes
    for i in range(NUMBER_OF_PROCESSES):
        Process(target=worker, args=(task_queue, done_queue)).start()

    # Get and print results
    print 'Unordered results:'
    for i in range(len(TASKS1)):
        print '\t', done_queue.get()

    # Add more tasks using `put()`
    for task in TASKS2:
        task_queue.put(task)

    # Get and print some more results
    for i in range(len(TASKS2)):
        print '\t', done_queue.get()

    # Tell child processes to stop
    for i in range(NUMBER_OF_PROCESSES):
        task_queue.put('STOP')


if __name__ == '__main__':
    freeze_support()
    test()

########NEW FILE########
__FILENAME__ = test_multiprocessing
#!/usr/bin/env python

from __future__ import absolute_import

#
# Unit tests for the multiprocessing package
#

import unittest
import Queue
import time
import sys
import os
import gc
import array
import random
import logging
from nose import SkipTest
from test import test_support
from StringIO import StringIO
try:
    from billiard._ext import _billiard
except ImportError as exc:
    raise SkipTest(exc)
# import threading after _billiard to raise a more revelant error
# message: "No module named _billiard". _billiard is not compiled
# without thread support.
import threading

# Work around broken sem_open implementations
try:
    import billiard.synchronize
except ImportError as exc:
    raise SkipTest(exc)

import billiard.dummy
import billiard.connection
import billiard.managers
import billiard.heap
import billiard.pool

from billiard import util
from billiard.compat import bytes

latin = str

# Constants
LOG_LEVEL = util.SUBWARNING

DELTA = 0.1

# making true makes tests take a lot longer
# and can sometimes cause some non-serious
# failures because some calls block a bit
# longer than expected
CHECK_TIMINGS = False

if CHECK_TIMINGS:
    TIMEOUT1, TIMEOUT2, TIMEOUT3 = 0.82, 0.35, 1.4
else:
    TIMEOUT1, TIMEOUT2, TIMEOUT3 = 0.1, 0.1, 0.1

HAVE_GETVALUE = not getattr(_billiard,
                            'HAVE_BROKEN_SEM_GETVALUE', False)

WIN32 = (sys.platform == "win32")

# Some tests require ctypes
try:
    from ctypes import Structure, c_int, c_double
except ImportError:
    Structure = object
    c_int = c_double = None

try:
    from ctypes import Value
except ImportError:
    Value = None

try:
    from ctypes import copy as ctypes_copy
except ImportError:
    ctypes_copy = None


class TimingWrapper(object):
    """Creates a wrapper for a function which records the
    time it takes to finish"""

    def __init__(self, func):
        self.func = func
        self.elapsed = None

    def __call__(self, *args, **kwds):
        t = time.time()
        try:
            return self.func(*args, **kwds)
        finally:
            self.elapsed = time.time() - t


class BaseTestCase(object):
    """Base class for test cases"""
    ALLOWED_TYPES = ('processes', 'manager', 'threads')

    def assertTimingAlmostEqual(self, a, b):
        if CHECK_TIMINGS:
            self.assertAlmostEqual(a, b, 1)

    def assertReturnsIfImplemented(self, value, func, *args):
        try:
            res = func(*args)
        except NotImplementedError:
            pass
        else:
            return self.assertEqual(value, res)


def get_value(self):
    """Return the value of a semaphore"""
    try:
        return self.get_value()
    except AttributeError:
        try:
            return self._Semaphore__value
        except AttributeError:
            try:
                return self._value
            except AttributeError:
                raise NotImplementedError


class _TestProcesses(BaseTestCase):

    ALLOWED_TYPES = ('processes', 'threads')

    def test_current(self):
        if self.TYPE == 'threads':
            return

        current = self.current_process()
        authkey = current.authkey

        self.assertTrue(current.is_alive())
        self.assertTrue(not current.daemon)
        self.assertIsInstance(authkey, bytes)
        self.assertTrue(len(authkey) > 0)
        self.assertEqual(current.ident, os.getpid())
        self.assertEqual(current.exitcode, None)

    def _test(self, q, *args, **kwds):
        current = self.current_process()
        q.put(args)
        q.put(kwds)
        q.put(current.name)
        if self.TYPE != 'threads':
            q.put(bytes(current.authkey, 'ascii'))
            q.put(current.pid)

    def test_process(self):
        q = self.Queue(1)
        e = self.Event()  # noqa
        args = (q, 1, 2)
        kwargs = {'hello': 23, 'bye': 2.54}
        name = 'SomeProcess'
        p = self.Process(
            target=self._test, args=args, kwargs=kwargs, name=name
        )
        p.daemon = True
        current = self.current_process()

        if self.TYPE != 'threads':
            self.assertEquals(p.authkey, current.authkey)
        self.assertEquals(p.is_alive(), False)
        self.assertEquals(p.daemon, True)
        self.assertNotIn(p, self.active_children())
        self.assertTrue(type(self.active_children()) is list)
        self.assertEqual(p.exitcode, None)

        p.start()

        self.assertEquals(p.exitcode, None)
        self.assertEquals(p.is_alive(), True)
        self.assertIn(p, self.active_children())

        self.assertEquals(q.get(), args[1:])
        self.assertEquals(q.get(), kwargs)
        self.assertEquals(q.get(), p.name)
        if self.TYPE != 'threads':
            self.assertEquals(q.get(), current.authkey)
            self.assertEquals(q.get(), p.pid)

        p.join()

        self.assertEquals(p.exitcode, 0)
        self.assertEquals(p.is_alive(), False)
        self.assertNotIn(p, self.active_children())

    def _test_terminate(self):
        time.sleep(1000)

    def test_terminate(self):
        if self.TYPE == 'threads':
            return

        p = self.Process(target=self._test_terminate)
        p.daemon = True
        p.start()

        self.assertEqual(p.is_alive(), True)
        self.assertIn(p, self.active_children())
        self.assertEqual(p.exitcode, None)

        p.terminate()

        join = TimingWrapper(p.join)
        self.assertEqual(join(), None)
        self.assertTimingAlmostEqual(join.elapsed, 0.0)

        self.assertEqual(p.is_alive(), False)
        self.assertNotIn(p, self.active_children())

        p.join()

        # XXX sometimes get p.exitcode == 0 on Windows ...
        # self.assertEqual(p.exitcode, -signal.SIGTERM)

    def test_cpu_count(self):
        try:
            cpus = billiard.cpu_count()
        except NotImplementedError:
            cpus = 1
        self.assertTrue(type(cpus) is int)
        self.assertTrue(cpus >= 1)

    def test_active_children(self):
        self.assertEqual(type(self.active_children()), list)

        p = self.Process(target=time.sleep, args=(DELTA,))
        self.assertNotIn(p, self.active_children())

        p.start()
        self.assertIn(p, self.active_children())

        p.join()
        self.assertNotIn(p, self.active_children())

    def _test_recursion(self, wconn, id):
        __import__('billiard.forking')
        wconn.send(id)
        if len(id) < 2:
            for i in range(2):
                p = self.Process(
                    target=self._test_recursion, args=(wconn, id + [i])
                )
                p.start()
                p.join()

    def test_recursion(self):
        rconn, wconn = self.Pipe(duplex=False)
        self._test_recursion(wconn, [])

        time.sleep(DELTA)
        result = []
        while rconn.poll():
            result.append(rconn.recv())

        expected = [
            [],
            [0],
            [0, 0],
            [0, 1],
            [1],
            [1, 0],
            [1, 1]
        ]
        self.assertEqual(result, expected)


class _UpperCaser(billiard.Process):

    def __init__(self):
        billiard.Process.__init__(self)
        self.child_conn, self.parent_conn = billiard.Pipe()

    def run(self):
        self.parent_conn.close()
        for s in iter(self.child_conn.recv, None):
            self.child_conn.send(s.upper())
        self.child_conn.close()

    def submit(self, s):
        assert type(s) is str
        self.parent_conn.send(s)
        return self.parent_conn.recv()

    def stop(self):
        self.parent_conn.send(None)
        self.parent_conn.close()
        self.child_conn.close()


class _TestSubclassingProcess(BaseTestCase):

    ALLOWED_TYPES = ('processes',)

    def test_subclassing(self):
        uppercaser = _UpperCaser()
        uppercaser.start()
        self.assertEqual(uppercaser.submit('hello'), 'HELLO')
        self.assertEqual(uppercaser.submit('world'), 'WORLD')
        uppercaser.stop()
        uppercaser.join()


def queue_empty(q):
    if hasattr(q, 'empty'):
        return q.empty()
    else:
        return q.qsize() == 0


def queue_full(q, maxsize):
    if hasattr(q, 'full'):
        return q.full()
    else:
        return q.qsize() == maxsize


class _TestQueue(BaseTestCase):

    def _test_put(self, queue, child_can_start, parent_can_continue):
        child_can_start.wait()
        for i in range(6):
            queue.get()
        parent_can_continue.set()

    def test_put(self):
        MAXSIZE = 6
        queue = self.Queue(maxsize=MAXSIZE)
        child_can_start = self.Event()
        parent_can_continue = self.Event()

        proc = self.Process(
            target=self._test_put,
            args=(queue, child_can_start, parent_can_continue)
        )
        proc.daemon = True
        proc.start()

        self.assertEqual(queue_empty(queue), True)
        self.assertEqual(queue_full(queue, MAXSIZE), False)

        queue.put(1)
        queue.put(2, True)
        queue.put(3, True, None)
        queue.put(4, False)
        queue.put(5, False, None)
        queue.put_nowait(6)

        # the values may be in buffer but not yet in pipe so sleep a bit
        time.sleep(DELTA)

        self.assertEqual(queue_empty(queue), False)
        self.assertEqual(queue_full(queue, MAXSIZE), True)

        put = TimingWrapper(queue.put)
        put_nowait = TimingWrapper(queue.put_nowait)

        self.assertRaises(Queue.Full, put, 7, False)
        self.assertTimingAlmostEqual(put.elapsed, 0)

        self.assertRaises(Queue.Full, put, 7, False, None)
        self.assertTimingAlmostEqual(put.elapsed, 0)

        self.assertRaises(Queue.Full, put_nowait, 7)
        self.assertTimingAlmostEqual(put_nowait.elapsed, 0)

        self.assertRaises(Queue.Full, put, 7, True, TIMEOUT1)
        self.assertTimingAlmostEqual(put.elapsed, TIMEOUT1)

        self.assertRaises(Queue.Full, put, 7, False, TIMEOUT2)
        self.assertTimingAlmostEqual(put.elapsed, 0)

        self.assertRaises(Queue.Full, put, 7, True, timeout=TIMEOUT3)
        self.assertTimingAlmostEqual(put.elapsed, TIMEOUT3)

        child_can_start.set()
        parent_can_continue.wait()

        self.assertEqual(queue_empty(queue), True)
        self.assertEqual(queue_full(queue, MAXSIZE), False)

        proc.join()

    def _test_get(self, queue, child_can_start, parent_can_continue):
        child_can_start.wait()
        queue.put(2)
        queue.put(3)
        queue.put(4)
        queue.put(5)
        parent_can_continue.set()

    def test_get(self):
        queue = self.Queue()
        child_can_start = self.Event()
        parent_can_continue = self.Event()

        proc = self.Process(
            target=self._test_get,
            args=(queue, child_can_start, parent_can_continue)
        )
        proc.daemon = True
        proc.start()

        self.assertEqual(queue_empty(queue), True)

        child_can_start.set()
        parent_can_continue.wait()

        time.sleep(DELTA)
        self.assertEqual(queue_empty(queue), False)

        # ## Hangs unexpectedly, remove for now
        # self.assertEqual(queue.get(), 1)
        self.assertEqual(queue.get(True, None), 2)
        self.assertEqual(queue.get(True), 3)
        self.assertEqual(queue.get(timeout=1), 4)
        self.assertEqual(queue.get_nowait(), 5)

        self.assertEqual(queue_empty(queue), True)

        get = TimingWrapper(queue.get)
        get_nowait = TimingWrapper(queue.get_nowait)

        self.assertRaises(Queue.Empty, get, False)
        self.assertTimingAlmostEqual(get.elapsed, 0)

        self.assertRaises(Queue.Empty, get, False, None)
        self.assertTimingAlmostEqual(get.elapsed, 0)

        self.assertRaises(Queue.Empty, get_nowait)
        self.assertTimingAlmostEqual(get_nowait.elapsed, 0)

        self.assertRaises(Queue.Empty, get, True, TIMEOUT1)
        self.assertTimingAlmostEqual(get.elapsed, TIMEOUT1)

        self.assertRaises(Queue.Empty, get, False, TIMEOUT2)
        self.assertTimingAlmostEqual(get.elapsed, 0)

        self.assertRaises(Queue.Empty, get, timeout=TIMEOUT3)
        self.assertTimingAlmostEqual(get.elapsed, TIMEOUT3)

        proc.join()

    def _test_fork(self, queue):
        for i in range(10, 20):
            queue.put(i)
        # note that at this point the items may only be buffered, so the
        # process cannot shutdown until the feeder thread has finished
        # pushing items onto the pipe.

    def test_fork(self):
        # Old versions of Queue would fail to create a new feeder
        # thread for a forked process if the original process had its
        # own feeder thread.  This test checks that this no longer
        # happens.

        queue = self.Queue()

        # put items on queue so that main process starts a feeder thread
        for i in range(10):
            queue.put(i)

        # wait to make sure thread starts before we fork a new process
        time.sleep(DELTA)

        # fork process
        p = self.Process(target=self._test_fork, args=(queue,))
        p.start()

        # check that all expected items are in the queue
        for i in range(20):
            self.assertEqual(queue.get(), i)
        self.assertRaises(Queue.Empty, queue.get, False)

        p.join()

    def test_qsize(self):
        q = self.Queue()
        try:
            self.assertEqual(q.qsize(), 0)
        except NotImplementedError:
            return
        q.put(1)
        self.assertEqual(q.qsize(), 1)
        q.put(5)
        self.assertEqual(q.qsize(), 2)
        q.get()
        self.assertEqual(q.qsize(), 1)
        q.get()
        self.assertEqual(q.qsize(), 0)

    def _test_task_done(self, q):
        for obj in iter(q.get, None):
            time.sleep(DELTA)
            q.task_done()

    def test_task_done(self):
        queue = self.JoinableQueue()

        if sys.version_info < (2, 5) and not hasattr(queue, 'task_done'):
            self.skipTest("requires 'queue.task_done()' method")

        workers = [self.Process(target=self._test_task_done, args=(queue,))
                   for i in xrange(4)]

        for p in workers:
            p.start()

        for i in xrange(10):
            queue.put(i)

        queue.join()

        for p in workers:
            queue.put(None)

        for p in workers:
            p.join()


class _TestLock(BaseTestCase):

    def test_lock(self):
        lock = self.Lock()
        self.assertEqual(lock.acquire(), True)
        self.assertEqual(lock.acquire(False), False)
        self.assertEqual(lock.release(), None)
        self.assertRaises((ValueError, threading.ThreadError), lock.release)

    def test_rlock(self):
        lock = self.RLock()
        self.assertEqual(lock.acquire(), True)
        self.assertEqual(lock.acquire(), True)
        self.assertEqual(lock.acquire(), True)
        self.assertEqual(lock.release(), None)
        self.assertEqual(lock.release(), None)
        self.assertEqual(lock.release(), None)
        self.assertRaises((AssertionError, RuntimeError), lock.release)

    def test_lock_context(self):
        with self.Lock():
            pass


class _TestSemaphore(BaseTestCase):

    def _test_semaphore(self, sem):
        self.assertReturnsIfImplemented(2, get_value, sem)
        self.assertEqual(sem.acquire(), True)
        self.assertReturnsIfImplemented(1, get_value, sem)
        self.assertEqual(sem.acquire(), True)
        self.assertReturnsIfImplemented(0, get_value, sem)
        self.assertEqual(sem.acquire(False), False)
        self.assertReturnsIfImplemented(0, get_value, sem)
        self.assertEqual(sem.release(), None)
        self.assertReturnsIfImplemented(1, get_value, sem)
        self.assertEqual(sem.release(), None)
        self.assertReturnsIfImplemented(2, get_value, sem)

    def test_semaphore(self):
        sem = self.Semaphore(2)
        self._test_semaphore(sem)
        self.assertEqual(sem.release(), None)
        self.assertReturnsIfImplemented(3, get_value, sem)
        self.assertEqual(sem.release(), None)
        self.assertReturnsIfImplemented(4, get_value, sem)

    def test_bounded_semaphore(self):
        sem = self.BoundedSemaphore(2)
        self._test_semaphore(sem)
        # ## Currently fails on OS/X
        # if HAVE_GETVALUE:
        #    self.assertRaises(ValueError, sem.release)
        #    self.assertReturnsIfImplemented(2, get_value, sem)

    def test_timeout(self):
        if self.TYPE != 'processes':
            return

        sem = self.Semaphore(0)
        acquire = TimingWrapper(sem.acquire)

        self.assertEqual(acquire(False), False)
        self.assertTimingAlmostEqual(acquire.elapsed, 0.0)

        self.assertEqual(acquire(False, None), False)
        self.assertTimingAlmostEqual(acquire.elapsed, 0.0)

        self.assertEqual(acquire(False, TIMEOUT1), False)
        self.assertTimingAlmostEqual(acquire.elapsed, 0)

        self.assertEqual(acquire(True, TIMEOUT2), False)
        self.assertTimingAlmostEqual(acquire.elapsed, TIMEOUT2)

        self.assertEqual(acquire(timeout=TIMEOUT3), False)
        self.assertTimingAlmostEqual(acquire.elapsed, TIMEOUT3)


class _TestCondition(BaseTestCase):

    def f(self, cond, sleeping, woken, timeout=None):
        cond.acquire()
        sleeping.release()
        cond.wait(timeout)
        woken.release()
        cond.release()

    def check_invariant(self, cond):
        # this is only supposed to succeed when there are no sleepers
        if self.TYPE == 'processes':
            try:
                sleepers = (cond._sleeping_count.get_value() -
                            cond._woken_count.get_value())
                self.assertEqual(sleepers, 0)
                self.assertEqual(cond._wait_semaphore.get_value(), 0)
            except NotImplementedError:
                pass

    def test_notify(self):
        cond = self.Condition()
        sleeping = self.Semaphore(0)
        woken = self.Semaphore(0)

        p = self.Process(target=self.f, args=(cond, sleeping, woken))
        p.daemon = True
        p.start()

        p = threading.Thread(target=self.f, args=(cond, sleeping, woken))
        p.daemon = True
        p.start()

        # wait for both children to start sleeping
        sleeping.acquire()
        sleeping.acquire()

        # check no process/thread has woken up
        time.sleep(DELTA)
        self.assertReturnsIfImplemented(0, get_value, woken)

        # wake up one process/thread
        cond.acquire()
        cond.notify()
        cond.release()

        # check one process/thread has woken up
        time.sleep(DELTA)
        self.assertReturnsIfImplemented(1, get_value, woken)

        # wake up another
        cond.acquire()
        cond.notify()
        cond.release()

        # check other has woken up
        time.sleep(DELTA)
        self.assertReturnsIfImplemented(2, get_value, woken)

        # check state is not mucked up
        self.check_invariant(cond)
        p.join()

    def test_notify_all(self):
        cond = self.Condition()
        sleeping = self.Semaphore(0)
        woken = self.Semaphore(0)

        # start some threads/processes which will timeout
        for i in range(3):
            p = self.Process(target=self.f,
                             args=(cond, sleeping, woken, TIMEOUT1))
            p.daemon = True
            p.start()

            t = threading.Thread(target=self.f,
                                 args=(cond, sleeping, woken, TIMEOUT1))
            t.daemon = True
            t.start()

        # wait for them all to sleep
        for i in xrange(6):
            sleeping.acquire()

        # check they have all timed out
        for i in xrange(6):
            woken.acquire()
        self.assertReturnsIfImplemented(0, get_value, woken)

        # check state is not mucked up
        self.check_invariant(cond)

        # start some more threads/processes
        for i in range(3):
            p = self.Process(target=self.f, args=(cond, sleeping, woken))
            p.daemon = True
            p.start()

            t = threading.Thread(target=self.f, args=(cond, sleeping, woken))
            t.daemon = True
            t.start()

        # wait for them to all sleep
        for i in xrange(6):
            sleeping.acquire()

        # check no process/thread has woken up
        time.sleep(DELTA)
        self.assertReturnsIfImplemented(0, get_value, woken)

        # wake them all up
        cond.acquire()
        cond.notify_all()
        cond.release()

        # check they have all woken
        time.sleep(DELTA)
        self.assertReturnsIfImplemented(6, get_value, woken)

        # check state is not mucked up
        self.check_invariant(cond)

    def test_timeout(self):
        cond = self.Condition()
        wait = TimingWrapper(cond.wait)
        cond.acquire()
        res = wait(TIMEOUT1)
        cond.release()
        self.assertEqual(res, None)
        self.assertTimingAlmostEqual(wait.elapsed, TIMEOUT1)


class _TestEvent(BaseTestCase):

    def _test_event(self, event):
        time.sleep(TIMEOUT2)
        event.set()

    def test_event(self):
        event = self.Event()
        wait = TimingWrapper(event.wait)

        # Removed temporaily, due to API shear, this does not
        # work with threading._Event objects. is_set == isSet
        self.assertEqual(event.is_set(), False)

        # Removed, threading.Event.wait() will return the value of the __flag
        # instead of None. API Shear with the semaphore backed mp.Event
        self.assertEqual(wait(0.0), False)
        self.assertTimingAlmostEqual(wait.elapsed, 0.0)
        self.assertEqual(wait(TIMEOUT1), False)
        self.assertTimingAlmostEqual(wait.elapsed, TIMEOUT1)

        event.set()

        # See note above on the API differences
        self.assertEqual(event.is_set(), True)
        self.assertEqual(wait(), True)
        self.assertTimingAlmostEqual(wait.elapsed, 0.0)
        self.assertEqual(wait(TIMEOUT1), True)
        self.assertTimingAlmostEqual(wait.elapsed, 0.0)
        # self.assertEqual(event.is_set(), True)

        event.clear()

        # self.assertEqual(event.is_set(), False)

        self.Process(target=self._test_event, args=(event,)).start()
        self.assertEqual(wait(), True)


class _TestValue(BaseTestCase):

    ALLOWED_TYPES = ('processes',)

    codes_values = [
        ('i', 4343, 24234),
        ('d', 3.625, -4.25),
        ('h', -232, 234),
        ('c', latin('x'), latin('y'))
    ]

    def _test(self, values):
        for sv, cv in zip(values, self.codes_values):
            sv.value = cv[2]

    @unittest.skipIf(c_int is None, "requires _ctypes")
    def test_value(self, raw=False):
        if raw:
            values = [self.RawValue(code, value)
                      for code, value, _ in self.codes_values]
        else:
            values = [self.Value(code, value)
                      for code, value, _ in self.codes_values]

        for sv, cv in zip(values, self.codes_values):
            self.assertEqual(sv.value, cv[1])

        proc = self.Process(target=self._test, args=(values,))
        proc.start()
        proc.join()

        for sv, cv in zip(values, self.codes_values):
            self.assertEqual(sv.value, cv[2])

    @unittest.skipIf(c_int is None, "requires _ctypes")
    def test_rawvalue(self):
        self.test_value(raw=True)

    @unittest.skipIf(c_int is None, "requires _ctypes")
    def test_getobj_getlock(self):
        val1 = self.Value('i', 5)
        lock1 = val1.get_lock()  # noqa
        obj1 = val1.get_obj()    # noqa

        val2 = self.Value('i', 5, lock=None)
        lock2 = val2.get_lock()  # noqa
        obj2 = val2.get_obj()    # noqa

        lock = self.Lock()
        val3 = self.Value('i', 5, lock=lock)
        lock3 = val3.get_lock()  # noqa
        obj3 = val3.get_obj()    # noqa
        self.assertEqual(lock, lock3)

        arr4 = self.Value('i', 5, lock=False)
        self.assertFalse(hasattr(arr4, 'get_lock'))
        self.assertFalse(hasattr(arr4, 'get_obj'))

        self.assertRaises(AttributeError, self.Value, 'i', 5, lock='navalue')

        arr5 = self.RawValue('i', 5)
        self.assertFalse(hasattr(arr5, 'get_lock'))
        self.assertFalse(hasattr(arr5, 'get_obj'))


class _TestArray(BaseTestCase):

    ALLOWED_TYPES = ('processes',)

    def f(self, seq):
        for i in range(1, len(seq)):
            seq[i] += seq[i - 1]

    @unittest.skipIf(c_int is None, "requires _ctypes")
    def test_array(self, raw=False):
        seq = [680, 626, 934, 821, 150, 233, 548, 982, 714, 831]
        if raw:
            arr = self.RawArray('i', seq)
        else:
            arr = self.Array('i', seq)

        self.assertEqual(len(arr), len(seq))
        self.assertEqual(arr[3], seq[3])
        self.assertEqual(list(arr[2:7]), list(seq[2:7]))

        arr[4:8] = seq[4:8] = array.array('i', [1, 2, 3, 4])

        self.assertEqual(list(arr[:]), seq)

        self.f(seq)

        p = self.Process(target=self.f, args=(arr,))
        p.start()
        p.join()

        self.assertEqual(list(arr[:]), seq)

    @unittest.skipIf(c_int is None, "requires _ctypes")
    def test_rawarray(self):
        self.test_array(raw=True)

    @unittest.skipIf(c_int is None, "requires _ctypes")
    def test_getobj_getlock_obj(self):
        arr1 = self.Array('i', range(10))
        lock1 = arr1.get_lock()  # noqa
        obj1 = arr1.get_obj()    # noqa

        arr2 = self.Array('i', range(10), lock=None)
        lock2 = arr2.get_lock()  # noqa
        obj2 = arr2.get_obj()    # noqa

        lock = self.Lock()
        arr3 = self.Array('i', range(10), lock=lock)
        lock3 = arr3.get_lock()
        obj3 = arr3.get_obj()    # noqa
        self.assertEqual(lock, lock3)

        arr4 = self.Array('i', range(10), lock=False)
        self.assertFalse(hasattr(arr4, 'get_lock'))
        self.assertFalse(hasattr(arr4, 'get_obj'))
        self.assertRaises(AttributeError,
                          self.Array, 'i', range(10), lock='notalock')

        arr5 = self.RawArray('i', range(10))
        self.assertFalse(hasattr(arr5, 'get_lock'))
        self.assertFalse(hasattr(arr5, 'get_obj'))


class _TestContainers(BaseTestCase):

    ALLOWED_TYPES = ('manager',)

    def test_list(self):
        a = self.list(range(10))
        self.assertEqual(a[:], range(10))

        b = self.list()
        self.assertEqual(b[:], [])

        b.extend(range(5))
        self.assertEqual(b[:], range(5))

        self.assertEqual(b[2], 2)
        self.assertEqual(b[2:10], [2, 3, 4])

        b *= 2
        self.assertEqual(b[:], [0, 1, 2, 3, 4, 0, 1, 2, 3, 4])

        self.assertEqual(b + [5, 6], [0, 1, 2, 3, 4, 0, 1, 2, 3, 4, 5, 6])

        self.assertEqual(a[:], range(10))

        d = [a, b]
        e = self.list(d)
        self.assertEqual(
            e[:],
            [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0, 1, 2, 3, 4, 0, 1, 2, 3, 4]]
        )

        f = self.list([a])
        a.append('hello')
        self.assertEqual(f[:], [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'hello']])

    def test_dict(self):
        d = self.dict()
        indices = range(65, 70)
        for i in indices:
            d[i] = chr(i)
        self.assertEqual(d.copy(), dict((j, chr(j)) for j in indices))
        self.assertEqual(sorted(d.keys()), indices)
        self.assertEqual(sorted(d.values()), [chr(z) for z in indices])
        self.assertEqual(sorted(d.items()), [(x, chr(x)) for x in indices])

    def test_namespace(self):
        n = self.Namespace()
        n.name = 'Bob'
        n.job = 'Builder'
        n._hidden = 'hidden'
        self.assertEqual((n.name, n.job), ('Bob', 'Builder'))
        del n.job
        self.assertEqual(str(n), "Namespace(name='Bob')")
        self.assertTrue(hasattr(n, 'name'))
        self.assertTrue(not hasattr(n, 'job'))


def sqr(x, wait=0.0):
    time.sleep(wait)
    return x * x


class _TestPool(BaseTestCase):

    def test_apply(self):
        papply = self.pool.apply
        self.assertEqual(papply(sqr, (5,)), sqr(5))
        self.assertEqual(papply(sqr, (), {'x': 3}), sqr(x=3))

    def test_map(self):
        pmap = self.pool.map
        self.assertEqual(pmap(sqr, range(10)), map(sqr, range(10)))
        self.assertEqual(pmap(sqr, range(100), chunksize=20),
                         map(sqr, range(100)))

    def test_map_chunksize(self):
        try:
            self.pool.map_async(sqr, [], chunksize=1).get(timeout=TIMEOUT1)
        except billiard.TimeoutError:
            self.fail("pool.map_async with chunksize stalled on null list")

    def test_async(self):
        res = self.pool.apply_async(sqr, (7, TIMEOUT1,))
        get = TimingWrapper(res.get)
        self.assertEqual(get(), 49)
        self.assertTimingAlmostEqual(get.elapsed, TIMEOUT1)

    def test_async_timeout(self):
        res = self.pool.apply_async(sqr, (6, TIMEOUT2 + 0.2))
        get = TimingWrapper(res.get)
        self.assertRaises(billiard.TimeoutError, get, timeout=TIMEOUT2)
        self.assertTimingAlmostEqual(get.elapsed, TIMEOUT2)

    def test_imap(self):
        it = self.pool.imap(sqr, range(10))
        self.assertEqual(list(it), map(sqr, range(10)))

        it = self.pool.imap(sqr, range(10))
        for i in range(10):
            self.assertEqual(it.next(), i * i)
        self.assertRaises(StopIteration, it.next)

        it = self.pool.imap(sqr, range(1000), chunksize=100)
        for i in range(1000):
            self.assertEqual(it.next(), i * i)
        self.assertRaises(StopIteration, it.next)

    def test_imap_unordered(self):
        it = self.pool.imap_unordered(sqr, range(1000))
        self.assertEqual(sorted(it), map(sqr, range(1000)))

        it = self.pool.imap_unordered(sqr, range(1000), chunksize=53)
        self.assertEqual(sorted(it), map(sqr, range(1000)))

    def test_make_pool(self):
        p = billiard.Pool(3)
        self.assertEqual(3, len(p._pool))
        p.close()
        p.join()

    def test_terminate(self):
        if self.TYPE == 'manager':
            # On Unix a forked process increfs each shared object to
            # which its parent process held a reference.  If the
            # forked process gets terminated then there is likely to
            # be a reference leak.  So to prevent
            # _TestZZZNumberOfObjects from failing we skip this test
            # when using a manager.
            return

        self.pool.map_async(
            time.sleep, [0.1 for i in range(10000)], chunksize=1
        )
        self.pool.terminate()
        join = TimingWrapper(self.pool.join)
        join()
        self.assertTrue(join.elapsed < 0.2)


class _TestPoolWorkerLifetime(BaseTestCase):
    ALLOWED_TYPES = ('processes', )

    def test_pool_worker_lifetime(self):
        p = billiard.Pool(3, maxtasksperchild=10)
        self.assertEqual(3, len(p._pool))
        origworkerpids = [w.pid for w in p._pool]
        # Run many tasks so each worker gets replaced (hopefully)
        results = []
        for i in range(100):
            results.append(p.apply_async(sqr, (i, )))
        # Fetch the results and verify we got the right answers,
        # also ensuring all the tasks have completed.
        for (j, res) in enumerate(results):
            self.assertEqual(res.get(), sqr(j))
        # Refill the pool
        p._repopulate_pool()
        # Wait until all workers are alive
        countdown = 5
        while countdown and not all(w.is_alive() for w in p._pool):
            countdown -= 1
            time.sleep(DELTA)
        finalworkerpids = [worker.pid for worker in p._pool]
        # All pids should be assigned.  See issue #7805.
        self.assertNotIn(None, origworkerpids)
        self.assertNotIn(None, finalworkerpids)
        # Finally, check that the worker pids have changed
        self.assertNotEqual(sorted(origworkerpids), sorted(finalworkerpids))
        p.close()
        p.join()


class _TestZZZNumberOfObjects(BaseTestCase):
    # Test that manager has expected number of shared objects left

    # Because test cases are sorted alphabetically, this one will get
    # run after all the other tests for the manager.  It tests that
    # there have been no "reference leaks" for the manager's shared
    # objects.  Note the comment in _TestPool.test_terminate().
    ALLOWED_TYPES = ('manager',)

    def test_number_of_objects(self):
        EXPECTED_NUMBER = 1                # the pool object is still alive
        billiard.active_children()         # discard dead process objs
        gc.collect()                       # do garbage collection
        refs = self.manager._number_of_objects()
        debug_info = self.manager._debug_info()
        if refs != EXPECTED_NUMBER:
            print(self.manager._debug_info())
            print(debug_info)

        self.assertEqual(refs, EXPECTED_NUMBER)

# Test of creating a customized manager class
from billiard.managers import BaseManager, BaseProxy, RemoteError


class FooBar(object):

    def f(self):
        return 'f()'

    def g(self):
        raise ValueError

    def _h(self):
        return '_h()'


def baz():
    for i in xrange(10):
        yield i * i


class IteratorProxy(BaseProxy):
    _exposed_ = ('next', '__next__')

    def __iter__(self):
        return self

    def next(self):
        return self._callmethod('next')

    def __next__(self):
        return self._callmethod('__next__')


class MyManager(BaseManager):
    pass

MyManager.register('Foo', callable=FooBar)
MyManager.register('Bar', callable=FooBar, exposed=('f', '_h'))
MyManager.register('baz', callable=baz, proxytype=IteratorProxy)


class _TestMyManager(BaseTestCase):

    ALLOWED_TYPES = ('manager',)

    def test_mymanager(self):
        manager = MyManager()
        manager.start()

        foo = manager.Foo()
        bar = manager.Bar()
        baz = manager.baz()

        foo_methods = [name for name in ('f', 'g', '_h') if hasattr(foo, name)]
        bar_methods = [name for name in ('f', 'g', '_h') if hasattr(bar, name)]

        self.assertEqual(foo_methods, ['f', 'g'])
        self.assertEqual(bar_methods, ['f', '_h'])

        self.assertEqual(foo.f(), 'f()')
        self.assertRaises(ValueError, foo.g)
        self.assertEqual(foo._callmethod('f'), 'f()')
        self.assertRaises(RemoteError, foo._callmethod, '_h')

        self.assertEqual(bar.f(), 'f()')
        self.assertEqual(bar._h(), '_h()')
        self.assertEqual(bar._callmethod('f'), 'f()')
        self.assertEqual(bar._callmethod('_h'), '_h()')

        self.assertEqual(list(baz), [i * i for i in range(10)])

        manager.shutdown()

_queue = Queue.Queue()


# Test of connecting to a remote server and using xmlrpclib for serialization
def get_queue():
    return _queue


class QueueManager(BaseManager):
    '''manager class used by server process'''
QueueManager.register('get_queue', callable=get_queue)


class QueueManager2(BaseManager):
    '''manager class which specifies the same interface as QueueManager'''
QueueManager2.register('get_queue')


SERIALIZER = 'xmlrpclib'


class _TestRemoteManager(BaseTestCase):

    ALLOWED_TYPES = ('manager',)

    def _putter(self, address, authkey):
        manager = QueueManager2(
            address=address, authkey=authkey, serializer=SERIALIZER
        )
        manager.connect()
        queue = manager.get_queue()
        queue.put(('hello world', None, True, 2.25))

    def test_remote(self):
        authkey = os.urandom(32)

        manager = QueueManager(
            address=('localhost', 0), authkey=authkey, serializer=SERIALIZER
        )
        manager.start()

        p = self.Process(target=self._putter, args=(manager.address, authkey))
        p.start()

        manager2 = QueueManager2(
            address=manager.address, authkey=authkey, serializer=SERIALIZER
        )
        manager2.connect()
        queue = manager2.get_queue()

        # Note that xmlrpclib will deserialize object as a list not a tuple
        self.assertEqual(queue.get(), ['hello world', None, True, 2.25])

        # Because we are using xmlrpclib for serialization instead of
        # pickle this will cause a serialization error.
        self.assertRaises(Exception, queue.put, time.sleep)

        # Make queue finalizer run before the server is stopped
        del queue
        manager.shutdown()


class _TestManagerRestart(BaseTestCase):

    def _putter(self, address, authkey):
        manager = QueueManager(
            address=address, authkey=authkey, serializer=SERIALIZER)
        manager.connect()
        queue = manager.get_queue()
        queue.put('hello world')

    def test_rapid_restart(self):
        authkey = os.urandom(32)
        manager = QueueManager(
            address=('localhost', 0), authkey=authkey, serializer=SERIALIZER)
        addr = manager.get_server().address
        manager.start()

        p = self.Process(target=self._putter, args=(manager.address, authkey))
        p.start()
        queue = manager.get_queue()
        self.assertEqual(queue.get(), 'hello world')
        del queue
        manager.shutdown()
        manager = QueueManager(
            address=addr, authkey=authkey, serializer=SERIALIZER)
        manager.start()
        manager.shutdown()

SENTINEL = latin('')


class _TestConnection(BaseTestCase):

    ALLOWED_TYPES = ('processes', 'threads')

    def _echo(self, conn):
        for msg in iter(conn.recv_bytes, SENTINEL):
            conn.send_bytes(msg)
        conn.close()

    def test_connection(self):
        conn, child_conn = self.Pipe()

        p = self.Process(target=self._echo, args=(child_conn,))
        p.daemon = True
        p.start()

        seq = [1, 2.25, None]
        msg = latin('hello world')
        longmsg = msg * 10
        arr = array.array('i', range(4))

        if self.TYPE == 'processes':
            self.assertEqual(type(conn.fileno()), int)

        self.assertEqual(conn.send(seq), None)
        self.assertEqual(conn.recv(), seq)

        self.assertEqual(conn.send_bytes(msg), None)
        self.assertEqual(conn.recv_bytes(), msg)

        if self.TYPE == 'processes':
            buffer = array.array('i', [0] * 10)
            expected = list(arr) + [0] * (10 - len(arr))
            self.assertEqual(conn.send_bytes(arr), None)
            self.assertEqual(conn.recv_bytes_into(buffer),
                             len(arr) * buffer.itemsize)
            self.assertEqual(list(buffer), expected)

            buffer = array.array('i', [0] * 10)
            expected = [0] * 3 + list(arr) + [0] * (10 - 3 - len(arr))
            self.assertEqual(conn.send_bytes(arr), None)
            self.assertEqual(conn.recv_bytes_into(buffer, 3 * buffer.itemsize),
                             len(arr) * buffer.itemsize)
            self.assertEqual(list(buffer), expected)

            buffer = bytearray(latin(' ' * 40))
            self.assertEqual(conn.send_bytes(longmsg), None)
            try:
                res = conn.recv_bytes_into(buffer)
            except billiard.BufferTooShort as exc:
                self.assertEqual(exc.args, (longmsg,))
            else:
                self.fail('expected BufferTooShort, got %s' % res)

        poll = TimingWrapper(conn.poll)

        self.assertEqual(poll(), False)
        self.assertTimingAlmostEqual(poll.elapsed, 0)

        self.assertEqual(poll(TIMEOUT1), False)
        self.assertTimingAlmostEqual(poll.elapsed, TIMEOUT1)

        conn.send(None)

        self.assertEqual(poll(TIMEOUT1), True)
        self.assertTimingAlmostEqual(poll.elapsed, 0)

        self.assertEqual(conn.recv(), None)

        really_big_msg = latin('X') * (1024 * 1024 * 16)   # 16Mb
        conn.send_bytes(really_big_msg)
        self.assertEqual(conn.recv_bytes(), really_big_msg)

        conn.send_bytes(SENTINEL)                          # tell child to quit
        child_conn.close()

        if self.TYPE == 'processes':
            self.assertEqual(conn.readable, True)
            self.assertEqual(conn.writable, True)
            self.assertRaises(EOFError, conn.recv)
            self.assertRaises(EOFError, conn.recv_bytes)

        p.join()

    def test_duplex_false(self):
        reader, writer = self.Pipe(duplex=False)
        self.assertEqual(writer.send(1), None)
        self.assertEqual(reader.recv(), 1)
        if self.TYPE == 'processes':
            self.assertEqual(reader.readable, True)
            self.assertEqual(reader.writable, False)
            self.assertEqual(writer.readable, False)
            self.assertEqual(writer.writable, True)
            self.assertRaises(IOError, reader.send, 2)
            self.assertRaises(IOError, writer.recv)
            self.assertRaises(IOError, writer.poll)

    def test_spawn_close(self):
        # We test that a pipe connection can be closed by parent
        # process immediately after child is spawned.  On Windows this
        # would have sometimes failed on old versions because
        # child_conn would be closed before the child got a chance to
        # duplicate it.
        conn, child_conn = self.Pipe()

        p = self.Process(target=self._echo, args=(child_conn,))
        p.start()
        child_conn.close()    # this might complete before child initializes

        msg = latin('hello')
        conn.send_bytes(msg)
        self.assertEqual(conn.recv_bytes(), msg)

        conn.send_bytes(SENTINEL)
        conn.close()
        p.join()

    def test_sendbytes(self):
        if self.TYPE != 'processes':
            return

        msg = latin('abcdefghijklmnopqrstuvwxyz')
        a, b = self.Pipe()

        a.send_bytes(msg)
        self.assertEqual(b.recv_bytes(), msg)

        a.send_bytes(msg, 5)
        self.assertEqual(b.recv_bytes(), msg[5:])

        a.send_bytes(msg, 7, 8)
        self.assertEqual(b.recv_bytes(), msg[7:7 + 8])

        a.send_bytes(msg, 26)
        self.assertEqual(b.recv_bytes(), latin(''))

        a.send_bytes(msg, 26, 0)
        self.assertEqual(b.recv_bytes(), latin(''))

        self.assertRaises(ValueError, a.send_bytes, msg, 27)
        self.assertRaises(ValueError, a.send_bytes, msg, 22, 5)
        self.assertRaises(ValueError, a.send_bytes, msg, 26, 1)
        self.assertRaises(ValueError, a.send_bytes, msg, -1)
        self.assertRaises(ValueError, a.send_bytes, msg, 4, -1)


class _TestListenerClient(BaseTestCase):

    ALLOWED_TYPES = ('processes', 'threads')

    def _test(self, address):
        conn = self.connection.Client(address)
        conn.send('hello')
        conn.close()

    def test_listener_client(self):
        for family in self.connection.families:
            l = self.connection.Listener(family=family)
            p = self.Process(target=self._test, args=(l.address,))
            p.daemon = True
            p.start()
            conn = l.accept()
            self.assertEqual(conn.recv(), 'hello')
            p.join()
            l.close()
'''
class _TestPicklingConnections(BaseTestCase):
    """Test of sending connection and socket objects between processes"""

    ALLOWED_TYPES = ('processes',)

    def _listener(self, conn, families):
        for fam in families:
            l = self.connection.Listener(family=fam)
            conn.send(l.address)
            new_conn = l.accept()
            conn.send(new_conn)

        if self.TYPE == 'processes':
            l = socket.socket()
            l.bind(('localhost', 0))
            conn.send(l.getsockname())
            l.listen(1)
            new_conn, addr = l.accept()
            conn.send(new_conn)

        conn.recv()

    def _remote(self, conn):
        for (address, msg) in iter(conn.recv, None):
            client = self.connection.Client(address)
            client.send(msg.upper())
            client.close()

        if self.TYPE == 'processes':
            address, msg = conn.recv()
            client = socket.socket()
            client.connect(address)
            client.sendall(msg.upper())
            client.close()

        conn.close()

    def test_pickling(self):
        try:
            billiard.allow_connection_pickling()
        except ImportError:
            return

        families = self.connection.families

        lconn, lconn0 = self.Pipe()
        lp = self.Process(target=self._listener, args=(lconn0, families))
        lp.start()
        lconn0.close()

        rconn, rconn0 = self.Pipe()
        rp = self.Process(target=self._remote, args=(rconn0,))
        rp.start()
        rconn0.close()

        for fam in families:
            msg = ('This connection uses family %s' % fam).encode('ascii')
            address = lconn.recv()
            rconn.send((address, msg))
            new_conn = lconn.recv()
            self.assertEqual(new_conn.recv(), msg.upper())

        rconn.send(None)

        if self.TYPE == 'processes':
            msg = latin('This connection uses a normal socket')
            address = lconn.recv()
            rconn.send((address, msg))
            if hasattr(socket, 'fromfd'):
                new_conn = lconn.recv()
                self.assertEqual(new_conn.recv(100), msg.upper())
            else:
                # XXX On Windows with Py2.6 need to backport fromfd()
                discard = lconn.recv_bytes()

        lconn.send(None)

        rconn.close()
        lconn.close()

        lp.join()
        rp.join()

'''


class _TestHeap(BaseTestCase):

    ALLOWED_TYPES = ('processes',)

    def test_heap(self):
        iterations = 5000
        maxblocks = 50
        blocks = []

        # create and destroy lots of blocks of different sizes
        for i in xrange(iterations):
            size = int(random.lognormvariate(0, 1) * 1000)
            b = billiard.heap.BufferWrapper(size)
            blocks.append(b)
            if len(blocks) > maxblocks:
                i = random.randrange(maxblocks)
                del blocks[i]

        # get the heap object
        heap = billiard.heap.BufferWrapper._heap

        # verify the state of the heap
        all = []
        occupied = 0
        for L in heap._len_to_seq.values():
            for arena, start, stop in L:
                all.append((heap._arenas.index(arena), start, stop,
                            stop - start, 'free'))
        for arena, start, stop in heap._allocated_blocks:
            all.append((heap._arenas.index(arena), start, stop,
                        stop - start, 'occupied'))
            occupied += stop - start

        all.sort()

        for i in range(len(all) - 1):
            (arena, start, stop) = all[i][:3]
            (narena, nstart, nstop) = all[i + 1][:3]
            self.assertTrue((arena != narena and nstart == 0) or
                            (stop == nstart))


class _Foo(Structure):
    _fields_ = [
        ('x', c_int),
        ('y', c_double)
    ]


class _TestSharedCTypes(BaseTestCase):

    ALLOWED_TYPES = ('processes', )

    def _double(self, x, y, foo, arr, string):
        x.value *= 2
        y.value *= 2
        foo.x *= 2
        foo.y *= 2
        string.value *= 2
        for i in range(len(arr)):
            arr[i] *= 2

    @unittest.skipIf(Value is None, "requires ctypes.Value")
    def test_sharedctypes(self, lock=False):
        x = Value('i', 7, lock=lock)
        y = Value(c_double, 1.0 / 3.0, lock=lock)
        foo = Value(_Foo, 3, 2, lock=lock)
        arr = self.Array('d', range(10), lock=lock)
        string = self.Array('c', 20, lock=lock)
        string.value = 'hello'

        p = self.Process(target=self._double, args=(x, y, foo, arr, string))
        p.start()
        p.join()

        self.assertEqual(x.value, 14)
        self.assertAlmostEqual(y.value, 2.0 / 3.0)
        self.assertEqual(foo.x, 6)
        self.assertAlmostEqual(foo.y, 4.0)
        for i in range(10):
            self.assertAlmostEqual(arr[i], i * 2)
        self.assertEqual(string.value, latin('hellohello'))

    @unittest.skipIf(Value is None, "requires ctypes.Value")
    def test_synchronize(self):
        self.test_sharedctypes(lock=True)

    @unittest.skipIf(ctypes_copy is None, "requires ctypes.copy")
    def test_copy(self):
        foo = _Foo(2, 5.0)
        bar = ctypes_copy(foo)
        foo.x = 0
        foo.y = 0
        self.assertEqual(bar.x, 2)
        self.assertAlmostEqual(bar.y, 5.0)


class _TestFinalize(BaseTestCase):

    ALLOWED_TYPES = ('processes',)

    def _test_finalize(self, conn):
        class Foo(object):
            pass

        a = Foo()
        util.Finalize(a, conn.send, args=('a',))
        del a           # triggers callback for a

        b = Foo()
        close_b = util.Finalize(b, conn.send, args=('b',))
        close_b()       # triggers callback for b
        close_b()       # does nothing because callback has already been called
        del b           # does nothing because callback has already been called

        c = Foo()
        util.Finalize(c, conn.send, args=('c',))

        d10 = Foo()
        util.Finalize(d10, conn.send, args=('d10',), exitpriority=1)

        d01 = Foo()
        util.Finalize(d01, conn.send, args=('d01',), exitpriority=0)
        d02 = Foo()
        util.Finalize(d02, conn.send, args=('d02',), exitpriority=0)
        d03 = Foo()
        util.Finalize(d03, conn.send, args=('d03',), exitpriority=0)

        util.Finalize(None, conn.send, args=('e',), exitpriority=-10)

        util.Finalize(None, conn.send, args=('STOP',), exitpriority=-100)

        # call mutliprocessing's cleanup function then exit process without
        # garbage collecting locals
        util._exit_function()
        conn.close()
        os._exit(0)

    def test_finalize(self):
        conn, child_conn = self.Pipe()

        p = self.Process(target=self._test_finalize, args=(child_conn,))
        p.start()
        p.join()

        result = [obj for obj in iter(conn.recv, 'STOP')]
        self.assertEqual(result, ['a', 'b', 'd10', 'd03', 'd02', 'd01', 'e'])


class _TestImportStar(BaseTestCase):
    """Test that from ... import * works for each module"""
    ALLOWED_TYPES = ('processes',)

    def test_import(self):
        modules = [
            'billiard', 'billiard.connection',
            'billiard.heap', 'billiard.managers',
            'billiard.pool', 'billiard.process',
            'billiard.reduction',
            'billiard.synchronize', 'billiard.util'
        ]

        if c_int is not None:
            # This module requires _ctypes
            modules.append('billiard.sharedctypes')

        for name in modules:
            __import__(name)
            mod = sys.modules[name]

            for attr in getattr(mod, '__all__', ()):
                self.assertTrue(
                    hasattr(mod, attr),
                    '%r does not have attribute %r' % (mod, attr)
                )


class _TestLogging(BaseTestCase):
    """Quick test that logging works -- does not test logging output"""
    ALLOWED_TYPES = ('processes',)

    def test_enable_logging(self):
        logger = billiard.get_logger()
        logger.setLevel(util.SUBWARNING)
        self.assertTrue(logger is not None)
        logger.debug('this will not be printed')
        logger.info('nor will this')
        logger.setLevel(LOG_LEVEL)

    def _test_level(self, conn):
        logger = billiard.get_logger()
        conn.send(logger.getEffectiveLevel())

    def test_level(self):
        LEVEL1 = 32
        LEVEL2 = 37

        logger = billiard.get_logger()
        root_logger = logging.getLogger()
        root_level = root_logger.level

        reader, writer = billiard.Pipe(duplex=False)

        logger.setLevel(LEVEL1)
        self.Process(target=self._test_level, args=(writer,)).start()
        self.assertEqual(LEVEL1, reader.recv())

        logger.setLevel(logging.NOTSET)
        root_logger.setLevel(LEVEL2)
        self.Process(target=self._test_level, args=(writer,)).start()
        self.assertEqual(LEVEL2, reader.recv())

        root_logger.setLevel(root_level)
        logger.setLevel(level=LOG_LEVEL)


# class _TestLoggingProcessName(BaseTestCase):
#
#     def handle(self, record):
#         assert record.processName == billiard.current_process().name
#         self.__handled = True
#
#     def test_logging(self):
#         handler = logging.Handler()
#         handler.handle = self.handle
#         self.__handled = False
#         # Bypass getLogger() and side-effects
#         logger = logging.getLoggerClass()(
#                 'billiard.test.TestLoggingProcessName')
#         logger.addHandler(handler)
#         logger.propagate = False
#
#         logger.warn('foo')
#         assert self.__handled

#
# Test to verify handle verification, see issue 3321
#


class TestInvalidHandle(unittest.TestCase):

    @unittest.skipIf(WIN32, "skipped on Windows")
    def test_invalid_handles(self):
        conn = _billiard.Connection(44977608)
        self.assertRaises(IOError, conn.poll)
        self.assertRaises(IOError, _billiard.Connection, -1)


def get_attributes(Source, names):
    d = {}
    for name in names:
        obj = getattr(Source, name)
        if type(obj) == type(get_attributes):
            obj = staticmethod(obj)
        d[name] = obj
    return d


def create_test_cases(Mixin, type):
    result = {}
    glob = globals()
    Type = type.capitalize()

    for name in glob.keys():
        if name.startswith('_Test'):
            base = glob[name]
            if type in base.ALLOWED_TYPES:
                newname = 'With' + Type + name[1:]

                class Temp(base, unittest.TestCase, Mixin):
                    pass

                result[newname] = Temp
                Temp.__name__ = newname
                Temp.__module__ = Mixin.__module__
    return result


class ProcessesMixin(object):
    TYPE = 'processes'
    Process = billiard.Process
    locals().update(get_attributes(billiard, (
        'Queue', 'Lock', 'RLock', 'Semaphore', 'BoundedSemaphore',
        'Condition', 'Event', 'Value', 'Array', 'RawValue',
        'RawArray', 'current_process', 'active_children', 'Pipe',
        'connection', 'JoinableQueue'
    )))

testcases_processes = create_test_cases(ProcessesMixin, type='processes')
globals().update(testcases_processes)


class ManagerMixin(object):
    TYPE = 'manager'
    Process = billiard.Process
    manager = object.__new__(billiard.managers.SyncManager)
    locals().update(get_attributes(manager, (
        'Queue', 'Lock', 'RLock', 'Semaphore', 'BoundedSemaphore',
        'Condition', 'Event', 'Value', 'Array', 'list', 'dict',
        'Namespace', 'JoinableQueue'
    )))

testcases_manager = create_test_cases(ManagerMixin, type='manager')
globals().update(testcases_manager)


class ThreadsMixin(object):
    TYPE = 'threads'
    Process = billiard.dummy.Process
    locals().update(get_attributes(billiard.dummy, (
        'Queue', 'Lock', 'RLock', 'Semaphore', 'BoundedSemaphore',
        'Condition', 'Event', 'Value', 'Array', 'current_process',
        'active_children', 'Pipe', 'connection', 'dict', 'list',
        'Namespace', 'JoinableQueue'
    )))

testcases_threads = create_test_cases(ThreadsMixin, type='threads')
globals().update(testcases_threads)


class OtherTest(unittest.TestCase):
    # TODO: add more tests for deliver/answer challenge.
    def test_deliver_challenge_auth_failure(self):

        class _FakeConnection(object):

            def recv_bytes(self, size):
                return bytes('something bogus')

            def send_bytes(self, data):
                pass
        self.assertRaises(billiard.AuthenticationError,
                          billiard.connection.deliver_challenge,
                          _FakeConnection(), bytes('abc'))

    def test_answer_challenge_auth_failure(self):

        class _FakeConnection(object):

            def __init__(self):
                self.count = 0

            def recv_bytes(self, size):
                self.count += 1
                if self.count == 1:
                    return billiard.connection.CHALLENGE
                elif self.count == 2:
                    return bytes('something bogus')
                return bytes('')

            def send_bytes(self, data):
                pass
        self.assertRaises(billiard.AuthenticationError,
                          billiard.connection.answer_challenge,
                          _FakeConnection(), bytes('abc'))


def initializer(ns):
    ns.test += 1


class TestInitializers(unittest.TestCase):
    """Test Manager.start()/Pool.__init__() initializer feature

    - see issue 5585

    """
    def setUp(self):
        self.mgr = billiard.Manager()
        self.ns = self.mgr.Namespace()
        self.ns.test = 0

    def tearDown(self):
        self.mgr.shutdown()

    def test_manager_initializer(self):
        m = billiard.managers.SyncManager()
        self.assertRaises(TypeError, m.start, 1)
        m.start(initializer, (self.ns,))
        self.assertEqual(self.ns.test, 1)
        m.shutdown()

    def test_pool_initializer(self):
        self.assertRaises(TypeError, billiard.Pool, initializer=1)
        p = billiard.Pool(1, initializer, (self.ns,))
        p.close()
        p.join()
        self.assertEqual(self.ns.test, 1)


def _ThisSubProcess(q):
    try:
        q.get(block=False)
    except Queue.Empty:
        pass


def _TestProcess(q):
    """Issue 5155, 5313, 5331: Test process in processes

    Verifies os.close(sys.stdin.fileno) vs. sys.stdin.close() behavior

    """
    queue = billiard.Queue()
    subProc = billiard.Process(target=_ThisSubProcess, args=(queue,))
    subProc.start()
    subProc.join()


def _afunc(x):
    return x * x


def pool_in_process():
    pool = billiard.Pool(processes=4)
    pool.map(_afunc, [1, 2, 3, 4, 5, 6, 7])


class _file_like(object):
    def __init__(self, delegate):
        self._delegate = delegate
        self._pid = None

    @property
    def cache(self):
        pid = os.getpid()
        # There are no race conditions since fork keeps only the running thread
        if pid != self._pid:
            self._pid = pid
            self._cache = []
        return self._cache

    def write(self, data):
        self.cache.append(data)

    def flush(self):
        self._delegate.write(''.join(self.cache))
        self._cache = []


class TestStdinBadfiledescriptor(unittest.TestCase):

    def test_queue_in_process(self):
        queue = billiard.Queue()
        proc = billiard.Process(target=_TestProcess, args=(queue,))
        proc.start()
        proc.join()

    def test_pool_in_process(self):
        p = billiard.Process(target=pool_in_process)
        p.start()
        p.join()

    def test_flushing(self):
        sio = StringIO()
        flike = _file_like(sio)
        flike.write('foo')
        proc = billiard.Process(target=lambda: flike.flush())
        self.assertTrue(proc)
        flike.flush()
        assert sio.getvalue() == 'foo'

testcases_other = [OtherTest, TestInvalidHandle, TestInitializers,
                   TestStdinBadfiledescriptor]


def test_main(run=None):
    if sys.platform.startswith("linux"):
        try:
            billiard.RLock()
        except OSError:
            raise SkipTest("OSError raises on RLock creation, see issue 3111!")

    if run is None:
        from test.test_support import run_unittest as run

    util.get_temp_dir()     # creates temp directory for use by all processes

    billiard.get_logger().setLevel(LOG_LEVEL)

    ProcessesMixin.pool = billiard.Pool(4)
    ThreadsMixin.pool = billiard.dummy.Pool(4)
    ManagerMixin.manager.__init__()
    ManagerMixin.manager.start()
    ManagerMixin.pool = ManagerMixin.manager.Pool(4)

    testcases = (
        sorted(testcases_processes.values(), key=lambda tc: tc.__name__) +
        sorted(testcases_threads.values(), key=lambda tc: tc.__name__) +
        sorted(testcases_manager.values(), key=lambda tc: tc.__name__) +
        testcases_other
    )

    loadTestsFromTestCase = unittest.defaultTestLoader.loadTestsFromTestCase
    suite = unittest.TestSuite(loadTestsFromTestCase(tc) for tc in testcases)
    # (ncoghlan): Whether or not sys.exc_clear is executed by the threading
    # module during these tests is at least platform dependent and possibly
    # non-deterministic on any given platform. So we don't mind if the listed
    # warnings aren't actually raised.
    with test_support.check_py3k_warnings(
            (".+__(get|set)slice__ has been removed", DeprecationWarning),
            (r"sys.exc_clear\(\) not supported", DeprecationWarning),
            quiet=True):
        run(suite)

    ThreadsMixin.pool.terminate()
    ProcessesMixin.pool.terminate()
    ManagerMixin.pool.terminate()
    ManagerMixin.manager.shutdown()

    del ProcessesMixin.pool, ThreadsMixin.pool, ManagerMixin.pool


def main():
    test_main(unittest.TextTestRunner(verbosity=2).run)

if __name__ == '__main__':
    main()

########NEW FILE########
