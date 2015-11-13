__FILENAME__ = cached_property
import weakref

__all__ = ['cached_property']


class CachedProperty(object):

    __slots__ = ('func', 'cache')

    def __init__(self, func):
        self.func = func
        self.cache = weakref.WeakKeyDictionary()

    def __get__(self, obj, type=None):
        if obj is None:  # the property was accessed on the class.
            return self
        if obj not in self.cache:
            self.cache[obj] = val = CachedPropertyValue(is_computed=True,
                                                        value=self.func(obj))
            return val.value
        val = self.cache[obj]
        if val.is_present:
            return val.value
        raise AttributeError('%r has no attribute %r' %
                             (obj, self.func.__name__))

    def __set__(self, obj, value):
        if obj not in self.cache:
            self.cache[obj] = CachedPropertyValue(is_computed=True,
                                                  value=value)
        else:
            val = self.cache[obj]
            val.is_computed = True
            val.value = value

    def __delete__(self, obj):
        self.cache[obj] = CachedPropertyValue(is_present=False)


# An alias, for naming consistency with `property`.
cached_property = CachedProperty


class CachedPropertyValue(object):

    __slots__ = ('is_present', 'is_computed', 'value')

    def __init__(self, is_present=True, is_computed=False, value=None):
        self.is_present = is_present
        self.is_computed = is_computed
        self.value = value

########NEW FILE########
__FILENAME__ = error
"""Easier handling of exceptions with error numbers."""

import __builtin__
import abc
import errno
import re
import sys


# Get a list of all named errors.
ERRORS = dict((name, value) for name, value in vars(errno).iteritems()
              if re.match(r'^E[A-Z]+$', name))


class Error(__builtin__.EnvironmentError):

    """
    An abstract base class which can be used to check for errors with errno.

    Example:

        >>> read_fd, write_fd = os.pipe()
        >>> try:
        ...     os.read(write_fd, 256)
        ... except Error.EBADF, exc:
        ...     print "EBADF raised: %r" % exc
        EBADF raised: OSError(9, 'Bad file descriptor')

    Other errors, of the same type but with a different errno, will not be
    caught:

        >>> read_fd, write_fd = os.pipe()
        >>> os.close(read_fd)
        >>> try:
        ...     os.write(write_fd, "Hello!\\n")
        ... except Error.EBADF, exc:
        ...     print "EBADF raised: %r" % exc
        Traceback (most recent call last):
        ...
        OSError: [Errno 32] Broken pipe

    You can catch several errors using the standard Python syntax:

        >>> try:
        ...     os.write(write_fd, "Hello!\\n")
        ... except (Error.EBADF, Error.EPIPE):
        ...     print "Problem writing to pipe"
        Problem writing to pipe

    And catch different errors on different lines:

        >>> try:
        ...     os.write(write_fd, "Hello!\\n")
        ... except Error.EBADF:
        ...     print "Pipe was closed at this end"
        ... except Error.EPIPE:
        ...     print "Pipe was closed at the other end"
        Pipe was closed at the other end
    """

    match_errno = None

    class __metaclass__(abc.ABCMeta):
        def __getattr__(cls, error_name):
            if cls.match_errno is None and error_name in ERRORS:
                return cls.matcher(error_name, ERRORS[error_name])
            raise AttributeError(error_name)

    def __init__(self):
        raise TypeError("Cannot create teena.Error instances")

    @classmethod
    def __subclasshook__(cls, exc_type):
        exc_type, exc_info, traceback = sys.exc_info()
        exc_errno = getattr(exc_info, 'errno', None)
        if cls.match_errno is None:
            return exc_errno is not None
        elif exc_errno is not None:
            return exc_errno == cls.match_errno
        return False

    @classmethod
    def matcher(cls, error_name, error_number):
        # Return a dynamically-created subclass of the current class with the
        # `match_errno` attribute set.
        return type(cls.__name__ + "." + error_name,
                    (cls,),
                    {'match_errno': error_number,
                     '__module__': cls.__module__})

########NEW FILE########
__FILENAME__ = fdutils
"""Utilities for dealing with file descriptors."""

import os

from teena import Error


def ensure_fd(fd):
    """Ensure an argument is a file descriptor."""
    if not isinstance(fd, int):
        if not hasattr(fd, 'fileno'):
            raise TypeError("Arguments must be file descriptors, or implement fileno()")
        return fd.fileno()
    return fd


def close_fd(fd):
    """Close a file descriptor, ignoring EBADF."""
    if os.isatty(fd):
        return
    try:
        os.close(fd)
    except Error.EBADF:
        pass


def try_remove_handler(loop, fd):
    """Remove a handler from a loop, ignoring EBADF or KeyError."""
    try:
        loop.remove_handler(fd)
    except (KeyError, Error.EBADF):
        pass

########NEW FILE########
__FILENAME__ = pipe
import errno
import os
import sys

from teena import DEFAULT_BUFSIZE, cached_property


__all__ = ['Pipe']


class Pipe(object):

    """
    An anonymous pipe, with named accessors for convenience.

        >>> pipe = Pipe()
        >>> pipe.write_file.write('hello\\n')
        >>> pipe.write_file.flush()  # Always remember to flush.
        >>> pipe.read_file.readline()
        'hello\\n'

    You can also open a pipe in non-blocking mode, if you're on POSIX:

        >>> pipe = Pipe(non_blocking=True)
        >>> pipe.read_file.readline()
        Traceback (most recent call last):
        ...
        IOError: [Errno 35] Resource temporarily unavailable

    Or use it as a context manager:

        >>> with Pipe() as pipe:
        ...    pipe.write_file.write('FOO\\n')
        ...    pipe.write_file.flush()
        ...    print repr(pipe.read_file.readline())
        'FOO\\n'
    """

    __slots__ = ('read_fd', 'write_fd', '__weakref__')

    def __init__(self, non_blocking=False):
        self.read_fd, self.write_fd = os.pipe()
        if non_blocking:
            self._set_nonblocking(self.read_fd)
            self._set_nonblocking(self.write_fd)

    def __repr__(self):
        return '<Pipe r:%d w:%d>' % (self.read_fd, self.write_fd)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def __del__(self):
        self.close()

    @staticmethod
    def _set_nonblocking(fd):
        """Set a file descriptor to non-blocking mode (POSIX-only)."""
        try:
            import fcntl
        except ImportError:
            raise NotImplementedError("Non-blocking pipes are not supported on this platform")
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    @staticmethod
    def _fd_closed(fd):
        try:
            os.fstat(fd)
        except (OSError, IOError), exc:
            if exc.errno == errno.EBADF:
                return True
            raise
        return False

    @staticmethod
    def _close_fd(fd):
        try:
            os.close(fd)
        except (OSError, IOError), exc:
            if exc.errno != errno.EBADF:
                raise

    @cached_property
    def read_file(self, buffering=DEFAULT_BUFSIZE):
        """Get a file-like object for the read end of the pipe."""
        return os.fdopen(self.read_fd, 'rb', buffering)

    @cached_property
    def write_file(self, buffering=DEFAULT_BUFSIZE):
        """Get a file-like object for the write end of the pipe."""
        return os.fdopen(self.write_fd, 'wb', buffering)

    @property
    def read_closed(self):
        """True if the read end of this pipe is already closed."""
        return self._fd_closed(self.read_fd)

    @property
    def write_closed(self):
        """True if the write end of this pipe is already closed."""
        return self._fd_closed(self.write_fd)

    def close_read(self):
        """Close the read end of this pipe."""
        self._close_fd(self.read_fd)

    def close_write(self):
        """Close the write end of this pipe."""
        self._close_fd(self.write_fd)

    def close(self):
        """
        Attempt to close both ends of this pipe.

        If an error occurs when closing both ends, the error from the write end
        will be raised in preference to that of the read end, and the traceback
        from the read end will be printed to stderr.
        """
        try:
            self.close_read()
        finally:
            read_exc = sys.exc_info()
            try:
                self.close_write()
            except Exception, exc:
                if read_exc[0] is not None:
                    write_unraisable(self.close, *read_exc)
                raise


def write_unraisable(obj, exc_type, exc_value, exc_traceback):
    """A port of PyErr_WriteUnraisable directly from the CPython source."""
    print >>sys.stderr, "Exception %s: %r in %r ignored" % (exc_type,
                                                            exc_value,
                                                            obj)

########NEW FILE########
__FILENAME__ = tee
"""
An efficient implementation of file descriptor tee-ing in pure Python.

Tee-ing is simply copying a stream of data from a single input to multiple
outputs.
"""

import collections
from functools import partial
import os
import sys

from teena import DEFAULT_BUFSIZE, Error
from teena.fdutils import ensure_fd, close_fd, try_remove_handler
from teena.thread_loop import ThreadLoop


def tee(input_fd, output_fds, bufsize=DEFAULT_BUFSIZE):

    """
    Create a ThreadLoop which tees from one input to many outputs.

    Example:

        >>> in_pipe, out_pipe = Pipe(), Pipe()
        >>> with tee(in_pipe.read_fd, (out_pipe.write_fd, sys.stdout)):
        ...     os.write(in_pipe.write_fd, "FooBar\n")
        ...     assert os.read(out_pipe.read_fd, 8192) == "FooBar\n"
        FooBar

    In this case, input written to one pipe is copied to both stdout *and*
    another pipe. This is useful for capturing output and having it display on
    the console in real-time.
    """

    loop = ThreadLoop()

    input_fd = ensure_fd(input_fd)
    # Every output file descriptor gets its own buffer, to begin with.
    buffers = {}
    for output_fd in output_fds:
        buffers[ensure_fd(output_fd)] = collections.deque()

    def schedule_clean_up_writers():
        for output_fd, output_buffer in buffers.iteritems():
            if not output_buffer:
                try_remove_handler(loop, output_fd)
                close_fd(output_fd)
            else:
                loop.add_handler(output_fd, partial(writer, terminating=True),
                                 loop.WRITE | loop.ERROR)

    def clean_up_reader(input_fd, close=False):
        try_remove_handler(loop, input_fd)
        if close:
            close_fd(input_fd)

    def reader(fd, events):
        # If there's an error on the input, flush the output buffers, close and
        # clean up the reader, and stop.
        if events & loop.ERROR:
            schedule_clean_up_writers()
            clean_up_reader(fd, close=True)
            return

        # If there are no file descriptors to write to any more, stop, but
        # don't close the input.
        if not buffers:
            clean_up_reader(fd, close=False)
            return

        # The loop is necessary for errors like EAGAIN and EINTR.
        while True:
            try:
                data = os.read(fd, bufsize)
            except (Error.EAGAIN, Error.EINTR):
                continue
            except (Error.EPIPE, Error.ECONNRESET, Error.EIO):
                schedule_clean_up_writers()
                clean_up_reader(fd, close=True)
                return
            break

        # The source of the data for the input FD has been closed.
        if not data:
            schedule_clean_up_writers()
            clean_up_reader(fd, close=True)
            return

        # Put the chunk of data in the buffer of every registered output.
        # If an output FD has been closed, remove it from the list of buffers.
        bad_fds = []
        for output_fd, buffer in buffers.iteritems():
            buffer.appendleft(data)
            try:
                loop.add_handler(output_fd, writer, loop.WRITE | loop.ERROR)
            except Error.EBADF:
                bad_fds.append(output_fd)
        for bad_fd in bad_fds:
            del buffers[bad_fd]

    def writer(fd, events, terminating=False):
        if events & loop.ERROR:
            try_remove_handler(loop, fd)
            del buffers[fd]
            return

        # There's no input -- unschedule the writer, it'll be rescheduled again
        # when there's something for it to write.
        if not buffers[fd]:
            try_remove_handler(loop, fd)
            if terminating:
                close_fd(fd)
            return

        data = buffers[fd].pop()
        while True:
            try:
                os.write(fd, data)
            except (Error.EPIPE, Error.ECONNRESET, Error.EIO, Error.EBADF):
                del buffers[fd]
                try_remove_handler(loop, fd)
            except (Error.EAGAIN, Error.EINTR):
                continue
            break

    # Start with just the reader.
    loop.add_handler(input_fd, reader, loop.READ | loop.ERROR)

    return loop

########NEW FILE########
__FILENAME__ = thread_loop
from contextlib import contextmanager
import threading

import tornado.ioloop


class ThreadLoop(tornado.ioloop.IOLoop):

    """
    An IOLoop that can be run in a background thread as a context manager.

    Example:

        >>> read_fd, write_fd = os.pipe()
        >>> loop = ThreadLoop()
        >>> loop.add_handler(read_fd, process_items, loop.READ)
        >>> with loop.background():
        ...     os.write(write_fd, 'some message\n')
        ...     os.close(write_fd)

    In this case, ``process_items`` should detect an empty string from
    `os.read()`, and shut down the loop.
    """

    @contextmanager
    def background(self):
        # If the loop ever reaches a point where the only handler is the
        # 'waker', terminate it (we're not a long-running web server, so we
        # get to do this).
        def callback():
            if self.running():
                if self._handlers.keys() == [self._waker.fileno()]:
                    self.stop()
                else:
                    self.add_callback(callback)
        self.add_callback(callback)

        thread = threading.Thread(target=self.start)
        thread.daemon = True
        thread.start()
        try:
            yield
        finally:
            thread.join()
            self.close()

########NEW FILE########
__FILENAME__ = test_cached_property
import uuid

from nose.tools import assert_raises

from teena import cached_property


class Counter(object):
    def __init__(self):
        self.state = {'value': 0}

    @cached_property
    def attr(self):
        self.state['value'] += 1
        return self.state['value']


def test_cached_property_is_computed_on_access():
    counter = Counter()
    initial_state = counter.state.copy()
    value = counter.attr
    final_state = counter.state.copy()
    assert value == 1
    assert initial_state['value'] == 0
    assert final_state['value'] == 1


def test_cached_property_is_only_computed_once():
    counter = Counter()
    assert counter.state['value'] == 0
    first_value = counter.attr
    assert first_value == 1
    assert counter.state['value'] == 1
    second_value = counter.attr
    assert second_value == 1
    assert counter.state['value'] == 1


def test_setting_a_cached_property_overwrites_its_value_entirely():
    # Access, set, access
    counter = Counter()
    first_value = counter.attr
    assert first_value == 1
    counter.attr = 123
    second_value = counter.attr
    assert second_value == 123
    assert counter.state['value'] == 1  # Not recomputed.

    # Set, access
    counter2 = Counter()
    counter2.attr = 123
    value = counter2.attr
    assert value == 123
    assert counter2.state['value'] == 0  # Never computed.


def test_deleting_a_cached_property_removes_it_from_the_instance():
    # Access, delete, access
    counter = Counter()
    counter.attr
    del counter.attr
    assert_raises(AttributeError, lambda: counter.attr)
    assert counter.state['value'] == 1  # Not recomputed.

    # Delete, access
    counter2 = Counter()
    del counter2.attr
    assert_raises(AttributeError, lambda: counter2.attr)
    assert counter2.state['value'] == 0  # Never computed.


def test_the_cached_property_descriptor_is_available_on_the_class():
    assert isinstance(Counter.attr, cached_property)


class MultiCounter(object):
    def __init__(self):
        self.state = {'foo': 0, 'bar': 0}

    @cached_property
    def foo(self):
        self.state['foo'] += 1
        return self.state['foo']

    @cached_property
    def bar(self):
        self.state['bar'] += 1
        return self.state['bar']


def test_can_put_multiple_cached_properties_on_one_instance():
    # Just a sanity check.
    counter = MultiCounter()

    assert counter.foo == 1
    assert counter.state == {'foo': 1, 'bar': 0}

    assert counter.bar == 1
    assert counter.state == {'foo': 1, 'bar': 1}

    counter.foo = 123
    assert counter.foo == 123
    assert counter.state == {'foo': 1, 'bar': 1}

    counter.bar = 456
    assert counter.bar == 456
    assert counter.state == {'foo': 1, 'bar': 1}

    del counter.foo
    assert_raises(AttributeError, lambda: counter.foo)
    assert counter.state == {'foo': 1, 'bar': 1}

    del counter.bar
    assert_raises(AttributeError, lambda: counter.bar)
    assert counter.state == {'foo': 1, 'bar': 1}


class Object(object):

    def __init__(self):
        self.deallocation_flag = [False]

    def __del__(self):
        self.deallocation_flag[0] = True

    @cached_property
    def some_property(self):
        return 123


def test_objects_with_cached_properties_can_be_garbage_collected():
    import gc
    obj = Object()
    ident = id(obj)
    dealloc_flag = obj.deallocation_flag

    # Invoke the cached_property.
    obj.some_property

    # The object is tracked by the garbage collector.
    assert any(id(tracked_obj) == ident for tracked_obj in gc.get_objects()), \
            "The object is not being tracked by the garbage collector"
    # The object has been deallocated.
    assert not dealloc_flag[0], "The object was already deallocated"

    # Delete the object and run a full garbage collection.
    del obj
    gc.collect()

    # The object is no longer tracked by the garbage collector.
    assert not any(id(tracked_obj) == ident for tracked_obj in gc.get_objects()), \
            "The object is still being tracked by the garbage collector"
    # The object has been deallocated.
    assert dealloc_flag[0], "The object was not deallocated"


class X(object):

    __slots__ = ('a', '__weakref__')

    @cached_property
    def incr_a(self):
        self.a += 1
        return self.a


class Y(object):
    __slots__ = ('b',)

    @cached_property
    def incr_b(self):
        self.b += 1
        return self.b


def test_cached_property_supports_objects_without_dict_but_with_weakref():
    x = X()
    x.a = 123
    assert x.incr_a == 124
    assert x.a == 124
    assert x.incr_a == 124
    assert x.a == 124


def test_cached_property_does_not_support_objects_without_weakref():
    y = Y()
    y.b = 456
    assert_raises(TypeError, lambda: y.incr_b)

########NEW FILE########
__FILENAME__ = test_error
import errno
import os

from nose.tools import assert_raises

from teena import Error


def test_Error_is_a_superclass_of_all_errors_with_an_errno():
    success = False
    try:
        raise OSError(errno.EBADF, os.strerror(errno.EBADF))
    except Error, exc:
        success = True
    assert success


def test_Error_ETYPE_is_a_superclass_of_all_ETYPE_errors():
    success = False
    try:
        raise OSError(errno.EBADF, os.strerror(errno.EBADF))
    except Error.EBADF, exc:
        success = True
    assert success

    success = False
    try:
        raise IOError(errno.EBADF, os.strerror(errno.EBADF))
    except Error.EBADF, exc:
        success = True
    assert success


def test_Error_ETYPE1_is_not_a_superclass_of_an_ETYPE2_error():
    success = False
    try:
        raise OSError(errno.EBADF, os.strerror(errno.EBADF))
    except Error.EPIPE, exc:
        success = False
    except OSError:
        success = True
    assert success


def test_can_check_for_multiple_error_types():
    # Result is not in the checked types
    success = False
    try:
        raise OSError(errno.EBADF, os.strerror(errno.EBADF))
    except (Error.EPIPE, Error.EIO), exc:
        success = False
    except OSError:
        success = True
    assert success

    # Result is in the checked types
    success = False
    try:
        raise OSError(errno.EBADF, os.strerror(errno.EBADF))
    except (Error.EPIPE, Error.EBADF), exc:
        success = True
    except OSError:
        success = False
    assert success

########NEW FILE########
__FILENAME__ = test_pipe
import gc
import errno
import os

from nose.tools import assert_raises

from teena.pipe import Pipe


def test_pipe_gets_read_and_write_file_descriptors():
    pipe = Pipe()
    assert isinstance(pipe.read_fd, int)
    assert isinstance(pipe.write_fd, int)


def test_pipe_gets_read_and_write_file_handles():
    pipe = Pipe()
    assert hasattr(pipe.read_file, 'read')
    assert hasattr(pipe.write_file, 'write')


# No pun intended. Kind of.
def test_smoke_test_pipe():
    pipe = Pipe()
    pipe.write_file.write('FooBar\n')
    pipe.write_file.flush()
    assert pipe.read_file.readline() == 'FooBar\n'


def test_non_blocking_pipes_raise_EAGAIN_when_no_data_are_ready_to_read():
    pipe = Pipe(non_blocking=True)
    with assert_raises(IOError) as cm:
        pipe.read_file.read()
    assert cm.exception.errno == errno.EAGAIN


## Closing

def ensure_fd_closed(fd):
    with assert_raises(OSError) as cm:
        os.fstat(fd)
    assert cm.exception.errno == errno.EBADF


def ensure_pipe_closed(pipe):
    ensure_fd_closed(pipe.read_fd)
    ensure_fd_closed(pipe.write_fd)


def test_pipe_as_context_manager_closes_its_file_descriptors():
    with Pipe() as pipe:
        pass
    ensure_pipe_closed(pipe)


def test_close_closes_both_fds():
    pipe = Pipe()
    pipe.close()
    ensure_pipe_closed(pipe)


def test_closed_indicates_whether_an_fd_is_closed():
    pipe = Pipe()
    os.close(pipe.read_fd)
    assert pipe.read_closed
    os.close(pipe.write_fd)
    assert pipe.write_closed


def test_multiple_closes_are_a_noop():
    pipe = Pipe()
    pipe.close()
    pipe.close()
    ensure_pipe_closed(pipe)


def object_exists(object_id):
    return any(id(obj) == object_id for obj in gc.get_objects())


def test_pipe_closes_fds_on_garbage_collection():
    pipe = Pipe()
    ident = id(pipe)
    read_fd, write_fd = pipe.read_fd, pipe.write_fd

    # Check that the pipe gets collected.
    assert object_exists(ident)
    del pipe
    gc.collect()
    assert not object_exists(ident)

    ensure_fd_closed(read_fd)
    ensure_fd_closed(write_fd)


def test_errors_on_one_pipe_do_not_prevent_the_other_one_from_being_closed():
    class ReadFailPipe(Pipe):
        def close_read(self):
            1/0

    class WriteFailPipe(Pipe):
        def close_write(self):
            1/0

    pipe = ReadFailPipe()
    with assert_raises(ZeroDivisionError):
        pipe.close()
    ensure_fd_closed(pipe.write_fd)

    pipe = WriteFailPipe()
    with assert_raises(ZeroDivisionError):
        pipe.close()
    ensure_fd_closed(pipe.read_fd)


def test_if_both_pipes_raise_errors_on_closing_the_write_pipes_error_is_returned():
    class BothFailPipe(Pipe):
        def close_read(self):
            raise Exception("FOO")

        def close_write(self):
            raise Exception("BAR")

    pipe = BothFailPipe()
    with assert_raises(Exception) as cm:
        pipe.close()
    assert cm.exception.args == ("BAR",)

########NEW FILE########
__FILENAME__ = test_tee
"""Tests for async-I/O file descriptor tee-ing."""

from contextlib import nested
import os
import subprocess
import sys

from teena import Pipe, tee


def test_can_tee_to_two_pipes():
    with nested(Pipe(), Pipe(), Pipe()) as (p1, p2, p3):
        with tee(p1.read_fd, (p2.write_fd, p3.write_fd)).background():
            # Write to input pipe, the output should show up on one output
            # pipe and stdout (though there's no easy way to check this)
            os.write(p1.write_fd, 'foobar')
            os.close(p1.write_fd)
            assert os.read(p2.read_fd, 6) == 'foobar'
            assert os.read(p3.read_fd, 6) == 'foobar'


def test_can_tee_to_stdout_and_a_simple_pipe():
    with nested(Pipe(), Pipe()) as (p1, p2):
        with tee(p1.read_fd, (sys.stdout.fileno(), p2.write_fd)).background():
            # Write to input pipe, the output should show up on one output
            # pipe and stdout (though there's no easy way to check this)
            os.write(p1.write_fd, 'foobar')
            os.close(p1.write_fd)
            assert os.read(p2.read_fd, 6) == 'foobar'


def test_tee_can_capture_subprocess_output_and_send_to_stdout():
    with nested(Pipe(), Pipe()) as (in_pipe, out_pipe):
        with tee(in_pipe.read_fd, (sys.stdout.fileno(), out_pipe.write_fd)).background():
            echo = subprocess.Popen(['echo', 'hello'], stdout=in_pipe.write_fd)
            echo.wait()
            os.close(in_pipe.write_fd)
            captured_output = os.read(out_pipe.read_fd, 8192)
            assert captured_output == 'hello\n'


def test_tee_can_handle_pipe_closures_gracefully():
    with nested(Pipe(), Pipe(), Pipe()) as (p1, p2, p3):
        with tee(p1.read_fd, (p2.write_fd, p3.write_fd)).background():
            os.write(p1.write_fd, "Hello!\n")
            p1.close_write()
        assert p2.write_closed
        assert p3.write_closed
        assert os.read(p2.read_fd, 100) == "Hello!\n"
        assert os.read(p3.read_fd, 100) == "Hello!\n"


def test_when_input_is_closed_reading_any_output_gives_empty_string():
    with nested(Pipe(), Pipe(), Pipe()) as (p1, p2, p3):
        with tee(p1.read_fd, (p2.write_fd, p3.write_fd)).background():
            p1.close_write()
            assert os.read(p2.read_fd, 4096) == ''
            assert os.read(p3.read_fd, 4096) == ''
        assert p2.write_closed
        assert p3.write_closed

########NEW FILE########
__FILENAME__ = test_thread_loop
import os

from teena import Error
from teena.thread_loop import ThreadLoop


def test_thread_loop_runs_in_background():
    # This is a high-level test, but with threads there's not much choice.
    read_fd, write_fd = os.pipe()
    strings = []
    def process_input(fd, events):
        while True:
            try:
                data = os.read(fd, 4096)
            except (Error.EAGAIN, Error.EINTR):
                continue
            except (Error.EPIPE, Error.ECONNRESET, Error.EIO):
                loop.stop()
                return
            break
        if not data:
            loop.stop()
        strings.append(data)

    loop = ThreadLoop()
    loop.add_handler(read_fd, process_input, loop.READ)
    with loop.background():
        os.write(write_fd, "Message 1\n")
        os.write(write_fd, "Message 2\n")
        os.close(write_fd)
    assert ''.join(strings) == "Message 1\nMessage 2\n"
    os.close(read_fd)

########NEW FILE########
