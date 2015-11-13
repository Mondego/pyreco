__FILENAME__ = test_api
"""
Tests for the crochet APIs.
"""

from __future__ import absolute_import

import threading
import subprocess
import time
import gc
import sys
import weakref
import tempfile
import os

from twisted.trial.unittest import TestCase
from twisted.internet.defer import succeed, Deferred, fail, CancelledError
from twisted.python.failure import Failure
from twisted.python import threadable
from twisted.python.runtime import platform
if platform.type == "posix":
    try:
        from twisted.internet.process import reapAllProcesses
    except (SyntaxError, ImportError):
        if sys.version_info < (3, 3, 0):
            raise
        else:
            # Process support is still not ported to Python 3 on some versions
            # of Twisted.
            reapAllProcesses = None
else:
    # waitpid() is only necessary on POSIX:
    reapAllProcesses = None

from .._eventloop import (EventLoop, EventualResult, TimeoutError,
                          ResultRegistry, ReactorStopped)
from .test_setup import FakeReactor
from .. import (_main, setup, in_reactor, retrieve_result, _store, no_setup,
                run_in_reactor, wait_for_reactor, wait_for)
from ..tests import crochet_directory


class ResultRegistryTests(TestCase):
    """
    Tests for ResultRegistry.
    """
    def test_stopped_registered(self):
        """
        ResultRegistery.stop() fires registered EventualResult with
        ReactorStopped.
        """
        registry = ResultRegistry(FakeReactor())
        er = EventualResult(None, None)
        registry.register(er)
        registry.stop()
        self.assertRaises(ReactorStopped, er.wait, timeout=0)

    def test_stopped_new_registration(self):
        """
        After ResultRegistery.stop() is called subsequent register() calls
        raise ReactorStopped.
        """
        registry = ResultRegistry(FakeReactor())
        er = EventualResult(None, None)
        registry.stop()
        self.assertRaises(ReactorStopped, registry.register, er)

    def test_stopped_already_have_result(self):
        """
        ResultRegistery.stop() has no impact on registered EventualResult
        which already have a result.
        """
        registry = ResultRegistry(FakeReactor())
        er = EventualResult(succeed(123), None)
        registry.register(er)
        registry.stop()
        self.assertEqual(er.wait(), 123)
        self.assertEqual(er.wait(), 123)
        self.assertEqual(er.wait(), 123)

    def test_weakref(self):
        """
        Registering an EventualResult with a ResultRegistry does not prevent
        it from being garbage collected.
        """
        registry = ResultRegistry(FakeReactor())
        er = EventualResult(None, None)
        registry.register(er)
        ref = weakref.ref(er)
        del er
        gc.collect()
        self.assertIdentical(ref(), None)

    def test_runs_with_lock(self):
        """
        All code in ResultRegistry.stop() and register() is protected by a
        lock.
        """
        self.assertTrue(ResultRegistry.stop.synchronized)
        self.assertTrue(ResultRegistry.register.synchronized)


class EventualResultTests(TestCase):
    """
    Tests for EventualResult.
    """

    def setUp(self):
        self.patch(threadable, "isInIOThread", lambda: False)

    def test_success_result(self):
        """
        wait() returns the value the Deferred fired with.
        """
        dr = EventualResult(succeed(123), None)
        self.assertEqual(dr.wait(), 123)

    def test_later_success_result(self):
        """
        wait() returns the value the Deferred fired with, in the case where
        the Deferred is fired after wait() is called.
        """
        d = Deferred()
        def fireSoon():
            import time; time.sleep(0.01)
            d.callback(345)
        threading.Thread(target=fireSoon).start()
        dr = EventualResult(d, None)
        self.assertEqual(dr.wait(), 345)

    def test_success_result_twice(self):
        """
        A second call to wait() returns same value as the first call.
        """
        dr = EventualResult(succeed(123), None)
        self.assertEqual(dr.wait(), 123)
        self.assertEqual(dr.wait(), 123)

    def test_failure_result(self):
        """
        wait() raises the exception the Deferred fired with.
        """
        dr = EventualResult(fail(RuntimeError()), None)
        self.assertRaises(RuntimeError, dr.wait)

    def test_later_failure_result(self):
        """
        wait() raises the exception the Deferred fired with, in the case
        where the Deferred is fired after wait() is called.
        """
        d = Deferred()
        def fireSoon():
            time.sleep(0.01)
            d.errback(RuntimeError())
        threading.Thread(target=fireSoon).start()
        dr = EventualResult(d, None)
        self.assertRaises(RuntimeError, dr.wait)

    def test_failure_result_twice(self):
        """
        A second call to wait() raises same value as the first call.
        """
        dr = EventualResult(fail(ZeroDivisionError()), None)
        self.assertRaises(ZeroDivisionError, dr.wait)
        self.assertRaises(ZeroDivisionError, dr.wait)

    def test_timeout(self):
        """
        If no result is available, wait(timeout) will throw a TimeoutError.
        """
        start = time.time()
        dr = EventualResult(Deferred(), None)
        self.assertRaises(TimeoutError, dr.wait, timeout=0.03)
        self.assertTrue(abs(time.time() - start - 0.03) < 0.005)

    def test_timeout_twice(self):
        """
        If no result is available, a second call to wait(timeout) will also
        result in a TimeoutError exception.
        """
        dr = EventualResult(Deferred(), None)
        self.assertRaises(TimeoutError, dr.wait, timeout=0.01)
        self.assertRaises(TimeoutError, dr.wait, timeout=0.01)

    def test_timeout_then_result(self):
        """
        If a result becomes available after a timeout, a second call to
        wait() will return it.
        """
        d = Deferred()
        dr = EventualResult(d, None)
        self.assertRaises(TimeoutError, dr.wait, timeout=0.01)
        d.callback(u"value")
        self.assertEqual(dr.wait(), u"value")
        self.assertEqual(dr.wait(), u"value")

    def test_reactor_thread_disallowed(self):
        """
        wait() cannot be called from the reactor thread.
        """
        self.patch(threadable, "isInIOThread", lambda: True)
        d = Deferred()
        dr = EventualResult(d, None)
        self.assertRaises(RuntimeError, dr.wait, 0)

    def test_cancel(self):
        """
        cancel() cancels the wrapped Deferred, running cancellation in the
        event loop thread.
        """
        reactor = FakeReactor()
        cancelled = []
        def error(f):
            cancelled.append(reactor.in_call_from_thread)
            cancelled.append(f)

        d = Deferred().addErrback(error)
        dr = EventualResult(d, _reactor=reactor)
        dr.cancel()
        self.assertTrue(cancelled[0])
        self.assertIsInstance(cancelled[1].value, CancelledError)

    def test_stash(self):
        """
        EventualResult.stash() stores the object in the global ResultStore.
        """
        dr = EventualResult(Deferred(), None)
        uid = dr.stash()
        self.assertIdentical(dr, _store.retrieve(uid))

    def test_original_failure(self):
        """
        original_failure() returns the underlying Failure of the Deferred
        wrapped by the EventualResult.
        """
        try:
            1/0
        except:
            f = Failure()
        dr = EventualResult(fail(f), None)
        self.assertIdentical(dr.original_failure(), f)

    def test_original_failure_no_result(self):
        """
        If there is no result yet, original_failure() returns None.
        """
        dr = EventualResult(Deferred(), None)
        self.assertIdentical(dr.original_failure(), None)

    def test_original_failure_not_error(self):
        """
        If the result is not an error, original_failure() returns None.
        """
        dr = EventualResult(succeed(3), None)
        self.assertIdentical(dr.original_failure(), None)

    def test_error_logged_no_wait(self):
        """
        If the result is an error and wait() was never called, the error will
        be logged once the EventualResult is garbage-collected.
        """
        dr = EventualResult(fail(ZeroDivisionError()), None)
        del dr
        gc.collect()
        excs = self.flushLoggedErrors(ZeroDivisionError)
        self.assertEqual(len(excs), 1)

    def test_error_logged_wait_timeout(self):
        """
        If the result is an error and wait() was called but timed out, the
        error will be logged once the EventualResult is garbage-collected.
        """
        d = Deferred()
        dr = EventualResult(d, None)
        try:
            dr.wait(0)
        except TimeoutError:
            pass
        d.errback(ZeroDivisionError())
        del dr
        if sys.version_info[0] == 2:
            sys.exc_clear()
        gc.collect()
        excs = self.flushLoggedErrors(ZeroDivisionError)
        self.assertEqual(len(excs), 1)

    def test_error_after_gc_logged(self):
        """
        If the result is an error that occurs after all user references to the
        EventualResult are lost, the error is still logged.
        """
        d = Deferred()
        dr = EventualResult(d, None)
        del dr
        d.errback(ZeroDivisionError())
        gc.collect()
        excs = self.flushLoggedErrors(ZeroDivisionError)
        self.assertEqual(len(excs), 1)

    def test_control_c_is_possible(self):
        """
        If you're wait()ing on an EventualResult in main thread, make sure the
        KeyboardInterrupt happens in timely manner.
        """
        program = """\
import os, threading, signal, time, sys
import crochet
crochet.setup()
from twisted.internet.defer import Deferred

if sys.platform.startswith('win'):
    signal.signal(signal.SIGBREAK, signal.default_int_handler)
    sig_int=signal.CTRL_BREAK_EVENT
    sig_kill=signal.SIGTERM
else:
    sig_int=signal.SIGINT
    sig_kill=signal.SIGKILL


def interrupt():
    time.sleep(0.1) # Make sure we've hit wait()
    os.kill(os.getpid(), sig_int)
    time.sleep(1)
    # Still running, test shall fail...
    os.kill(os.getpid(), sig_kill)

t = threading.Thread(target=interrupt)
t.setDaemon(True)
t.start()

d = Deferred()
e = crochet.EventualResult(d, None)

try:
    # Queue.get() has special non-interruptible behavior if not given timeout,
    # so don't give timeout here.
    e.wait()
except KeyboardInterrupt:
    sys.exit(23)
"""
        kw = { 'cwd': crochet_directory }
        # on Windows the only way to interrupt a subprocess reliably is to
        # create a new process group:
        # http://docs.python.org/2/library/subprocess.html#subprocess.CREATE_NEW_PROCESS_GROUP
        if platform.type.startswith('win'):
            kw['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        process = subprocess.Popen([sys.executable, "-c", program], **kw)
        self.assertEqual(process.wait(), 23)

    def test_connect_deferred(self):
        """
        If an EventualResult is created with None,
        EventualResult._connect_deferred can be called later to register a
        Deferred as the one it is wrapping.
        """
        er = EventualResult(None, None)
        self.assertRaises(TimeoutError, er.wait, 0)
        d = Deferred()
        er._connect_deferred(d)
        self.assertRaises(TimeoutError, er.wait, 0)
        d.callback(123)
        self.assertEqual(er.wait(), 123)

    def test_reactor_stop_unblocks_EventualResult(self):
        """
        Any EventualResult.wait() calls still waiting when the reactor has
        stopped will get a ReactorStopped exception.
        """
        program = """\
import os, threading, signal, time, sys

from twisted.internet.defer import Deferred
from twisted.internet import reactor

import crochet
crochet.setup()

@crochet.run_in_reactor
def run():
    reactor.callLater(0.1, reactor.stop)
    return Deferred()

er = run()
try:
    er.wait(timeout=10)
except crochet.ReactorStopped:
    sys.exit(23)
"""
        process = subprocess.Popen([sys.executable, "-c", program],
                                   cwd=crochet_directory)
        self.assertEqual(process.wait(), 23)

    def test_reactor_stop_unblocks_EventualResult_in_threadpool(self):
        """
        Any EventualResult.wait() calls still waiting when the reactor has
        stopped will get a ReactorStopped exception, even if it is running in
        Twisted's thread pool.
        """
        program = """\
import os, threading, signal, time, sys

from twisted.internet.defer import Deferred
from twisted.internet import reactor

import crochet
crochet.setup()

@crochet.run_in_reactor
def run():
    reactor.callLater(0.1, reactor.stop)
    return Deferred()

result = [13]
def inthread():
    er = run()
    try:
        er.wait(timeout=10)
    except crochet.ReactorStopped:
        result[0] = 23
reactor.callInThread(inthread)
time.sleep(1)
sys.exit(result[0])
"""
        process = subprocess.Popen([sys.executable, "-c", program],
                                   cwd=crochet_directory)
        self.assertEqual(process.wait(), 23)

    def test_immediate_cancel(self):
        """
        Immediately cancelling the result of @run_in_reactor function will
        still cancel the Deferred.
        """
        # This depends on the way reactor runs callFromThread calls, so need
        # real functional test.
        program = """\
import os, threading, signal, time, sys

from twisted.internet.defer import Deferred, CancelledError

import crochet
crochet.setup()

@crochet.run_in_reactor
def run():
    return Deferred()

er = run()
er.cancel()
try:
    er.wait(1)
except CancelledError:
    sys.exit(23)
else:
    sys.exit(3)
"""
        process = subprocess.Popen([sys.executable, "-c", program],
                                   cwd=crochet_directory,)
        self.assertEqual(process.wait(), 23)

    def test_noWaitingDuringImport(self):
        """
        EventualResult.wait() raises an exception if called while a module is
        being imported.

        This prevents the imports from taking a long time, preventing other
        imports from running in other threads. It also prevents deadlocks,
        which can happen if the code being waited on also tries to import
        something.
        """
        if sys.version_info[0] > 2:
            from unittest import SkipTest
            raise SkipTest("This test is too fragile (and insufficient) on "
                           "Python 3 - see "
                           "https://github.com/itamarst/crochet/issues/43")
        directory = tempfile.mktemp()
        os.mkdir(directory)
        sys.path.append(directory)
        self.addCleanup(sys.path.remove, directory)
        with open(os.path.join(directory, "shouldbeunimportable.py"), "w") as f:
            f.write("""\
from crochet import EventualResult
from twisted.internet.defer import Deferred

EventualResult(Deferred(), None).wait(1.0)
""")
        self.assertRaises(RuntimeError, __import__, "shouldbeunimportable")


class InReactorTests(TestCase):
    """
    Tests for the deprecated in_reactor decorator.
    """

    def test_name(self):
        """
        The function decorated with in_reactor has the same name as the
        original function.
        """
        c = EventLoop(lambda: FakeReactor(), lambda f, g: None)

        @c.in_reactor
        def some_name(reactor):
            pass
        self.assertEqual(some_name.__name__, "some_name")

    def test_in_reactor_thread(self):
        """
        The function decorated with in_reactor is run in the reactor
        thread, and takes the reactor as its first argument.
        """
        myreactor = FakeReactor()
        c = EventLoop(lambda: myreactor, lambda f, g: None)
        c.no_setup()

        calls = []

        @c.in_reactor
        def func(reactor, a, b, c):
            self.assertIdentical(reactor, myreactor)
            self.assertTrue(reactor.in_call_from_thread)
            calls.append((a, b, c))

        func(1, 2, c=3)
        self.assertEqual(calls, [(1, 2, 3)])

    def test_run_in_reactor_wrapper(self):
        """
        in_reactor is implemented on top of run_in_reactor.
        """
        wrapped = [False]

        def fake_run_in_reactor(function):
            def wrapper(*args, **kwargs):
                wrapped[0] = True
                result = function(*args, **kwargs)
                wrapped[0] = False
                return result
            return wrapper

        myreactor = FakeReactor()
        c = EventLoop(lambda: myreactor, lambda f, g: None)
        c.no_setup()
        c.run_in_reactor = fake_run_in_reactor


        @c.in_reactor
        def func(reactor):
            self.assertTrue(wrapped[0])
            return 17

        result = func()
        self.assertFalse(wrapped[0])
        self.assertEqual(result, 17)


class RunInReactorTests(TestCase):
    """
    Tests for the run_in_reactor decorator.
    """
    def test_name(self):
        """
        The function decorated with run_in_reactor has the same name as the
        original function.
        """
        c = EventLoop(lambda: FakeReactor(), lambda f, g: None)

        @c.run_in_reactor
        def some_name():
            pass
        self.assertEqual(some_name.__name__, "some_name")

    def test_run_in_reactor_thread(self):
        """
        The function decorated with run_in_reactor is run in the reactor
        thread.
        """
        myreactor = FakeReactor()
        c = EventLoop(lambda: myreactor, lambda f, g: None)
        c.no_setup()
        calls = []

        @c.run_in_reactor
        def func(a, b, c):
            self.assertTrue(myreactor.in_call_from_thread)
            calls.append((a, b, c))

        func(1, 2, c=3)
        self.assertEqual(calls, [(1, 2, 3)])

    def make_wrapped_function(self):
        """
        Return a function wrapped with run_in_reactor that returns its first
        argument.
        """
        myreactor = FakeReactor()
        c = EventLoop(lambda: myreactor, lambda f, g: None)
        c.no_setup()

        @c.run_in_reactor
        def passthrough(argument):
            return argument
        return passthrough

    def test_deferred_success_result(self):
        """
        If the underlying function returns a Deferred, the wrapper returns a
        EventualResult hooked up to the Deferred.
        """
        passthrough = self.make_wrapped_function()
        result = passthrough(succeed(123))
        self.assertIsInstance(result, EventualResult)
        self.assertEqual(result.wait(), 123)

    def test_deferred_failure_result(self):
        """
        If the underlying function returns a Deferred, the wrapper returns a
        EventualResult hooked up to the Deferred that can deal with failures
        as well.
        """
        passthrough = self.make_wrapped_function()
        result = passthrough(fail(ZeroDivisionError()))
        self.assertIsInstance(result, EventualResult)
        self.assertRaises(ZeroDivisionError, result.wait)

    def test_regular_result(self):
        """
        If the underlying function returns a non-Deferred, the wrapper returns
        a EventualResult hooked up to a Deferred wrapping the result.
        """
        passthrough = self.make_wrapped_function()
        result = passthrough(123)
        self.assertIsInstance(result, EventualResult)
        self.assertEqual(result.wait(), 123)

    def test_exception_result(self):
        """
        If the underlying function throws an exception, the wrapper returns a
        EventualResult hooked up to a Deferred wrapping the exception.
        """
        myreactor = FakeReactor()
        c = EventLoop(lambda: myreactor, lambda f, g: None)
        c.no_setup()

        @c.run_in_reactor
        def raiser():
            1/0

        result = raiser()
        self.assertIsInstance(result, EventualResult)
        self.assertRaises(ZeroDivisionError, result.wait)

    def test_registry(self):
        """
        @run_in_reactor registers the EventualResult in the ResultRegistry.
        """
        myreactor = FakeReactor()
        c = EventLoop(lambda: myreactor, lambda f, g: None)
        c.no_setup()

        @c.run_in_reactor
        def run():
            return

        result = run()
        self.assertIn(result, c._registry._results)

    def test_wrapped_function(self):
        """
        The function wrapped by @run_in_reactor can be accessed via the
        `wrapped_function` attribute.
        """
        c = EventLoop(lambda: None, lambda f, g: None)
        def func():
            pass
        wrapper = c.run_in_reactor(func)
        self.assertIdentical(wrapper.wrapped_function, func)


class WaitTestsMixin(object):
    """
    Tests mixin for the wait_for_reactor/wait_for decorators.
    """
    def setUp(self):
        self.reactor = FakeReactor()
        self.eventloop = EventLoop(lambda: self.reactor, lambda f, g: None)
        self.eventloop.no_setup()

    def decorator(self):
        """
        Return a callable that decorates a function, using the decorator being
        tested.
        """
        raise NotImplementedError()

    def make_wrapped_function(self):
        """
        Return a function wrapped with the decorator being tested that returns
        its first argument, or raises it if it's an exception.
        """
        decorator = self.decorator()
        @decorator
        def passthrough(argument):
            if isinstance(argument, Exception):
                raise argument
            return argument
        return passthrough

    def test_name(self):
        """
        The function decorated with the wait decorator has the same name as the
        original function.
        """
        decorator = self.decorator()
        @decorator
        def some_name(argument):
            pass
        self.assertEqual(some_name.__name__, "some_name")

    def test_wrapped_function(self):
        """
        The function wrapped by the wait decorator can be accessed via the
        `wrapped_function` attribute.
        """
        decorator = self.decorator()
        def func():
            pass
        wrapper = decorator(func)
        self.assertIdentical(wrapper.wrapped_function, func)

    def test_reactor_thread_disallowed(self):
        """
        Functions decorated with the wait decorator cannot be called from the
        reactor thread.
        """
        self.patch(threadable, "isInIOThread", lambda: True)
        f = self.make_wrapped_function()
        self.assertRaises(RuntimeError, f, None)

    def test_wait_for_reactor_thread(self):
        """
        The function decorated with the wait decorator is run in the reactor
        thread.
        """
        in_call_from_thread = []
        decorator = self.decorator()

        @decorator
        def func():
            in_call_from_thread.append(self.reactor.in_call_from_thread)

        in_call_from_thread.append(self.reactor.in_call_from_thread)
        func()
        in_call_from_thread.append(self.reactor.in_call_from_thread)
        self.assertEqual(in_call_from_thread, [False, True, False])

    def test_arguments(self):
        """
        The function decorated with wait decorator gets all arguments passed
        to the wrapper.
        """
        calls = []
        decorator = self.decorator()

        @decorator
        def func(a, b, c):
            calls.append((a, b, c))

        func(1, 2, c=3)
        self.assertEqual(calls, [(1, 2, 3)])

    def test_deferred_success_result(self):
        """
        If the underlying function returns a Deferred, the wrapper returns a
        the Deferred's result.
        """
        passthrough = self.make_wrapped_function()
        result = passthrough(succeed(123))
        self.assertEqual(result, 123)

    def test_deferred_failure_result(self):
        """
        If the underlying function returns a Deferred with an errback, the
        wrapper throws an exception.
        """
        passthrough = self.make_wrapped_function()
        self.assertRaises(
            ZeroDivisionError, passthrough, fail(ZeroDivisionError()))

    def test_regular_result(self):
        """
        If the underlying function returns a non-Deferred, the wrapper returns
        that result.
        """
        passthrough = self.make_wrapped_function()
        result = passthrough(123)
        self.assertEqual(result, 123)

    def test_exception_result(self):
        """
        If the underlying function throws an exception, the wrapper raises
        that exception.
        """
        raiser = self.make_wrapped_function()
        self.assertRaises(ZeroDivisionError, raiser, ZeroDivisionError())

    def test_control_c_is_possible(self):
        """
        A call to a decorated function responds to a Ctrl-C (i.e. with a
        KeyboardInterrupt) in a timely manner.
        """
        program = """\
import os, threading, signal, time, sys
import crochet
crochet.setup()
from twisted.internet.defer import Deferred

if sys.platform.startswith('win'):
    signal.signal(signal.SIGBREAK, signal.default_int_handler)
    sig_int=signal.CTRL_BREAK_EVENT
    sig_kill=signal.SIGTERM
else:
    sig_int=signal.SIGINT
    sig_kill=signal.SIGKILL


def interrupt():
    time.sleep(0.1) # Make sure we've hit wait()
    os.kill(os.getpid(), sig_int)
    time.sleep(1)
    # Still running, test shall fail...
    os.kill(os.getpid(), sig_kill)

t = threading.Thread(target=interrupt)
t.setDaemon(True)
t.start()

@crochet.%s
def wait():
    return Deferred()

try:
    wait()
except KeyboardInterrupt:
    sys.exit(23)
""" % (self.DECORATOR_CALL,)
        kw = { 'cwd': crochet_directory }
        if platform.type.startswith('win'):
            kw['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        process = subprocess.Popen([sys.executable, "-c", program], **kw)
        self.assertEqual(process.wait(), 23)

    def test_reactor_stop_unblocks(self):
        """
        Any @wait_for_reactor-decorated calls still waiting when the reactor
        has stopped will get a ReactorStopped exception.
        """
        program = """\
import os, threading, signal, time, sys

from twisted.internet.defer import Deferred
from twisted.internet import reactor

import crochet
crochet.setup()

@crochet.%s
def run():
    reactor.callLater(0.1, reactor.stop)
    return Deferred()

try:
    er = run()
except crochet.ReactorStopped:
    sys.exit(23)
"""  % (self.DECORATOR_CALL,)
        process = subprocess.Popen([sys.executable, "-c", program],
                                   cwd=crochet_directory)
        self.assertEqual(process.wait(), 23)


class WaitForReactorTests(WaitTestsMixin, TestCase):
    """
    Tests for the wait_for_reactor decorator.
    """
    DECORATOR_CALL = "wait_for_reactor"

    def decorator(self):
        return self.eventloop.wait_for_reactor


class WaitForTests(WaitTestsMixin, TestCase):
    """
    Tests for the wait_for_reactor decorator.
    """
    DECORATOR_CALL = "wait_for(timeout=5)"

    def decorator(self):
        return lambda func: self.eventloop.wait_for(timeout=5)(func)

    def test_timeoutRaises(self):
        """
        If a function wrapped with wait_for hits the timeout, it raises
        TimeoutError.
        """
        @self.eventloop.wait_for(timeout=0.5)
        def times_out():
            return Deferred().addErrback(lambda f: f.trap(CancelledError))

        start = time.time()
        self.assertRaises(TimeoutError, times_out)
        self.assertTrue(abs(time.time() - start - 0.5) < 0.1)

    def test_timeoutCancels(self):
        """
        If a function wrapped with wait_for hits the timeout, it cancels
        the underlying Deferred.
        """
        result = Deferred()
        error = []
        result.addErrback(error.append)

        @self.eventloop.wait_for(timeout=0.0)
        def times_out():
            return result
        self.assertRaises(TimeoutError, times_out)
        self.assertIsInstance(error[0].value, CancelledError)


class PublicAPITests(TestCase):
    """
    Tests for the public API.
    """
    def test_no_sideeffects(self):
        """
        Creating an EventLoop object, as is done in crochet.__init__, does not
        call any methods on the objects it is created with.
        """
        c = EventLoop(lambda: None, lambda f, g: 1/0, lambda *args: 1/0,
                      watchdog_thread=object(), reapAllProcesses=lambda: 1/0)
        del c

    def test_eventloop_api(self):
        """
        An EventLoop object configured with the real reactor and
        _shutdown.register is exposed via its public methods.
        """
        from twisted.python.log import startLoggingWithObserver
        from crochet import _shutdown
        self.assertIsInstance(_main, EventLoop)
        self.assertEqual(_main.setup, setup)
        self.assertEqual(_main.no_setup, no_setup)
        self.assertEqual(_main.in_reactor, in_reactor)
        self.assertEqual(_main.run_in_reactor, run_in_reactor)
        self.assertEqual(_main.wait_for_reactor, wait_for_reactor)
        self.assertEqual(_main.wait_for, wait_for)
        self.assertIdentical(_main._atexit_register, _shutdown.register)
        self.assertIdentical(_main._startLoggingWithObserver,
                             startLoggingWithObserver)
        self.assertIdentical(_main._watchdog_thread, _shutdown._watchdog)

    def test_eventloop_api_reactor(self):
        """
        The publicly exposed EventLoop will, when setup, use the global reactor.
        """
        from twisted.internet import reactor
        _main.no_setup()
        self.assertIdentical(_main._reactor, reactor)

    def test_retrieve_result(self):
        """
        retrieve_result() calls retrieve() on the global ResultStore.
        """
        dr = EventualResult(Deferred(), None)
        uid = dr.stash()
        self.assertIdentical(dr, retrieve_result(uid))

    def test_reapAllProcesses(self):
        """
        An EventLoop object configured with the real reapAllProcesses on POSIX
        plaforms.
        """
        self.assertIdentical(_main._reapAllProcesses, reapAllProcesses)
    if platform.type != "posix":
        test_reapAllProcesses.skip = "Only relevant on POSIX platforms"
    if reapAllProcesses is None:
        test_reapAllProcesses.skip = "Twisted does not yet support processes"

########NEW FILE########
__FILENAME__ = test_process
"""
Tests for IReactorProcess.
"""

import subprocess
import sys

from twisted.trial.unittest import TestCase
from twisted.python.runtime import platform

from ..tests import crochet_directory

class ProcessTests(TestCase):
    """
    Tests for process support.
    """
    def test_processExit(self):
        """
        A Crochet-managed reactor notice when a process it started exits.

        On POSIX platforms this requies waitpid() to be called, which in
        default Twisted implementation relies on a SIGCHLD handler which is not
        installed by Crochet at the moment.
        """
        program = """\
from crochet import setup, run_in_reactor
setup()

import sys
import os
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.defer import Deferred
from twisted.internet import reactor

class Waiter(ProcessProtocol):
    def __init__(self):
        self.result = Deferred()

    def processExited(self, reason):
        self.result.callback(None)


@run_in_reactor
def run():
    waiter = Waiter()
    # Closing FDs before exit forces us to rely on SIGCHLD to notice process
    # exit:
    reactor.spawnProcess(waiter, sys.executable,
                         [sys.executable, '-c',
                          'import os; os.close(0); os.close(1); os.close(2)'],
                         env=os.environ)
    return waiter.result

run().wait(10)
# If we don't notice process exit, TimeoutError will be thrown and we won't
# reach the next line:
sys.stdout.write("abc")
"""
        process = subprocess.Popen([sys.executable, "-c", program],
                                   cwd=crochet_directory,
                                   stdout=subprocess.PIPE)
        result = process.stdout.read()
        self.assertEqual(result, b"abc")
    if platform.type != "posix":
        test_processExit.skip = "SIGCHLD is a POSIX-specific issue"
    if sys.version_info >= (3, 0, 0):
        test_processExit.skip = "Twisted does not support processes on Python 3 yet"

########NEW FILE########
__FILENAME__ = test_resultstore
"""
Tests for _resultstore.
"""

from twisted.trial.unittest import TestCase
from twisted.internet.defer import Deferred, fail, succeed

from .._resultstore import ResultStore
from .._eventloop import EventualResult


class ResultStoreTests(TestCase):
    """
    Tests for ResultStore.
    """

    def test_store_and_retrieve(self):
        """
        EventualResult instances be be stored in a ResultStore and then
        retrieved using the id returned from store().
        """
        store = ResultStore()
        dr = EventualResult(Deferred(), None)
        uid = store.store(dr)
        self.assertIdentical(store.retrieve(uid), dr)

    def test_retrieve_only_once(self):
        """
        Once a result is retrieved, it can no longer be retrieved again.
        """
        store = ResultStore()
        dr = EventualResult(Deferred(), None)
        uid = store.store(dr)
        store.retrieve(uid)
        self.assertRaises(KeyError, store.retrieve, uid)

    def test_synchronized(self):
        """
        store() and retrieve() are synchronized.
        """
        self.assertTrue(ResultStore.store.synchronized)
        self.assertTrue(ResultStore.retrieve.synchronized)
        self.assertTrue(ResultStore.log_errors.synchronized)

    def test_uniqueness(self):
        """
        Each store() operation returns a larger number, ensuring uniqueness.
        """
        store = ResultStore()
        dr = EventualResult(Deferred(), None)
        previous = store.store(dr)
        for i in range(100):
            store.retrieve(previous)
            dr = EventualResult(Deferred(), None)
            uid = store.store(dr)
            self.assertTrue(uid > previous)
            previous = uid

    def test_log_errors(self):
        """
        Unretrieved EventualResults have their errors, if any, logged on
        shutdown.
        """
        store = ResultStore()
        store.store(EventualResult(Deferred(), None))
        store.store(EventualResult(fail(ZeroDivisionError()), None))
        store.store(EventualResult(succeed(1), None))
        store.store(EventualResult(fail(RuntimeError()), None))
        store.log_errors()
        excs = self.flushLoggedErrors(ZeroDivisionError)
        self.assertEqual(len(excs), 1)
        excs = self.flushLoggedErrors(RuntimeError)
        self.assertEqual(len(excs), 1)

########NEW FILE########
__FILENAME__ = test_shutdown
"""
Tests for _shutdown.
"""

from __future__ import absolute_import

import sys
import subprocess
import time

from twisted.trial.unittest import TestCase

from crochet._shutdown import (Watchdog, FunctionRegistry, _watchdog, register,
                               _registry)
from ..tests import crochet_directory


class ShutdownTests(TestCase):
    """
    Tests for shutdown registration.
    """
    def test_shutdown(self):
        """
        A function registered with _shutdown.register() is called when the
        main thread exits.
        """
        program = """\
import threading, sys

from crochet._shutdown import register, _watchdog
_watchdog.start()

end = False

def thread():
    while not end:
        pass
    sys.stdout.write("byebye")
    sys.stdout.flush()

def stop(x, y):
    # Move this into separate test at some point.
    assert x == 1
    assert y == 2
    global end
    end = True

threading.Thread(target=thread).start()
register(stop, 1, y=2)

sys.exit()
"""
        process = subprocess.Popen([sys.executable, "-c", program],
                                   cwd=crochet_directory,
                                   stdout=subprocess.PIPE)
        result = process.stdout.read()
        self.assertEqual(process.wait(), 0)
        self.assertEqual(result, b"byebye")

    def test_watchdog(self):
        """
        The watchdog thread exits when the thread it is watching exits, and
        calls its shutdown function.
        """
        done = []
        alive = True

        class FakeThread:
            def is_alive(self):
                return alive

        w = Watchdog(FakeThread(), lambda: done.append(True))
        w.start()
        time.sleep(0.2)
        self.assertTrue(w.is_alive())
        self.assertFalse(done)
        alive = False
        time.sleep(0.2)
        self.assertTrue(done)
        self.assertFalse(w.is_alive())

    def test_api(self):
        """
        The module exposes a shutdown thread that will call a global
        registry's run(), and a register function tied to the global registry.
        """
        self.assertIsInstance(_registry, FunctionRegistry)
        self.assertEqual(register, _registry.register)
        self.assertIsInstance(_watchdog, Watchdog)
        self.assertEqual(_watchdog._shutdown_function, _registry.run)


class FunctionRegistryTests(TestCase):
    """
    Tests for FunctionRegistry.
    """

    def test_called(self):
        """
        Functions registered with a FunctionRegistry are called in reverse
        order by run().
        """
        result = []
        registry = FunctionRegistry()
        registry.register(lambda: result.append(1))
        registry.register(lambda x: result.append(x), 2)
        registry.register(lambda y: result.append(y), y=3)
        registry.run()
        self.assertEqual(result, [3, 2, 1])

    def test_log_errors(self):
        """
        Registered functions that raise an error have the error logged, and
        run() continues processing.
        """
        result = []
        registry = FunctionRegistry()
        registry.register(lambda: result.append(2))
        registry.register(lambda: 1/0)
        registry.register(lambda: result.append(1))
        registry.run()
        self.assertEqual(result, [1, 2])
        excs = self.flushLoggedErrors(ZeroDivisionError)
        self.assertEqual(len(excs), 1)

########NEW FILE########
__FILENAME__ = test_util
"""
Tests for crochet._util.
"""

from __future__ import absolute_import

from twisted.trial.unittest import TestCase

from .._util import synchronized


class FakeLock(object):
    locked = False
    def __enter__(self):
        self.locked = True
    def __exit__(self, type, value, traceback):
        self.locked = False


class Lockable(object):
    def __init__(self):
        self._lock = FakeLock()

    @synchronized
    def check(self, x, y):
        if not self._lock.locked:
            raise RuntimeError()
        return x, y

    @synchronized
    def raiser(self):
        if not self._lock.locked:
            raise RuntimeError()
        raise ZeroDivisionError()


class SynchronizedTests(TestCase):
    """
    Tests for the synchronized decorator.
    """
    def test_return(self):
        """
        A method wrapped with @synchronized is called with the lock acquired,
        and it is released on return.
        """
        obj = Lockable()
        self.assertEqual(obj.check(1, y=2), (1, 2))
        self.assertFalse(obj._lock.locked)

    def test_raise(self):
        """
        A method wrapped with @synchronized is called with the lock acquired,
        and it is released on exception raise.
        """
        obj = Lockable()
        self.assertRaises(ZeroDivisionError, obj.raiser)
        self.assertFalse(obj._lock.locked)

    def test_name(self):
        """
        A method wrapped with @synchronized preserves its name.
        """
        self.assertEqual(Lockable.check.__name__, "check")

    def test_marked(self):
        """
        A method wrapped with @synchronized is marked as synchronized.
        """
        self.assertEqual(Lockable.check.synchronized, True)

########NEW FILE########
__FILENAME__ = _eventloop
"""
Expose Twisted's event loop to threaded programs.
"""

from __future__ import absolute_import

import select
import threading
import weakref
import warnings
from functools import wraps

import imp

from twisted.python import threadable
from twisted.python.runtime import platform
from twisted.python.failure import Failure
from twisted.python.log import PythonLoggingObserver, err
from twisted.internet.defer import maybeDeferred
from twisted.internet.task import LoopingCall

from ._util import synchronized
from ._resultstore import ResultStore

_store = ResultStore()


if hasattr(weakref, "WeakSet"):
    WeakSet = weakref.WeakSet
else:
    class WeakSet(object):
        """
        Minimal WeakSet emulation.
        """
        def __init__(self):
            self._items = weakref.WeakKeyDictionary()

        def add(self, value):
            self._items[value] = True

        def __iter__(self):
            return iter(self._items)


class TimeoutError(Exception):
    """
    A timeout has been hit.
    """


class ReactorStopped(Exception):
    """
    The reactor has stopped, and therefore no result will ever become
    available from this EventualResult.
    """


class ResultRegistry(object):
    """
    Keep track of EventualResults.

    Once the reactor has shutdown:

    1. Registering new EventualResult instances is an error, since no results
       will ever become available.
    2. Already registered EventualResult instances are "fired" with a
       ReactorStopped exception to unblock any remaining EventualResult.wait()
       calls.
    """
    def __init__(self, reactor):
        self._results = WeakSet()
        self._stopped = False
        self._lock = threading.Lock()

    @synchronized
    def register(self, result):
        """
        Register an EventualResult.

        May be called in any thread.
        """
        if self._stopped:
            raise ReactorStopped()
        self._results.add(result)

    @synchronized
    def stop(self):
        """
        Indicate no more results will get pushed into EventualResults, since
        the reactor has stopped.

        This should be called in the reactor thread.
        """
        self._stopped = True
        for result in self._results:
            result._set_result(Failure(ReactorStopped()))


class EventualResult(object):
    """
    A blocking interface to Deferred results.

    This allows you to access results from Twisted operations that may not be
    available immediately, using the wait() method.

    In general you should not create these directly; instead use functions
    decorated with @run_in_reactor.
    """

    def __init__(self, deferred, _reactor):
        """
        The deferred parameter should be a Deferred or None indicating
        _connect_deferred will be called separately later.
        """
        self._deferred = deferred
        self._reactor = _reactor
        self._value = None
        self._result_retrieved = False
        self._result_set = threading.Event()
        if deferred is not None:
            self._connect_deferred(deferred)

    def _connect_deferred(self, deferred):
        """
        Hook up the Deferred that that this will be the result of.

        Should only be run in Twisted thread, and only called once.
        """
        self._deferred = deferred
        # Because we use __del__, we need to make sure there are no cycles
        # involving this object, which is why we use a weakref:
        def put(result, eventual=weakref.ref(self)):
            eventual = eventual()
            if eventual:
                eventual._set_result(result)
            else:
                err(result, "Unhandled error in EventualResult")
        deferred.addBoth(put)

    def _set_result(self, result):
        """
        Set the result of the EventualResult, if not already set.

        This can only happen in the reactor thread, either as a result of
        Deferred firing, or as a result of ResultRegistry.stop(). So, no need
        for thread-safety.
        """
        if self._result_set.isSet():
            return
        self._value = result
        self._result_set.set()

    def __del__(self):
        if self._result_retrieved or not self._result_set.isSet():
            return
        if isinstance(self._value, Failure):
            err(self._value, "Unhandled error in EventualResult")

    def cancel(self):
        """
        Try to cancel the operation by cancelling the underlying Deferred.

        Cancellation of the operation may or may not happen depending on
        underlying cancellation support and whether the operation has already
        finished. In any case, however, the underlying Deferred will be fired.

        Multiple calls will have no additional effect.
        """
        self._reactor.callFromThread(lambda: self._deferred.cancel())

    def _result(self, timeout=None):
        """
        Return the result, if available.

        It may take an unknown amount of time to return the result, so a
        timeout option is provided. If the given number of seconds pass with
        no result, a TimeoutError will be thrown.

        If a previous call timed out, additional calls to this function will
        still wait for a result and return it if available. If a result was
        returned on one call, additional calls will return/raise the same
        result.
        """
        if timeout is None:
            warnings.warn("Unlimited timeouts are deprecated.",
                          DeprecationWarning, stacklevel=3)
            # Queue.get(None) won't get interrupted by Ctrl-C...
            timeout = 2 ** 31
        self._result_set.wait(timeout)
        # In Python 2.6 we can't rely on the return result of wait(), so we
        # have to check manually:
        if not self._result_set.is_set():
            raise TimeoutError()
        self._result_retrieved = True
        return self._value

    def wait(self, timeout=None):
        """
        Return the result, or throw the exception if result is a failure.

        It may take an unknown amount of time to return the result, so a
        timeout option is provided. If the given number of seconds pass with
        no result, a TimeoutError will be thrown.

        If a previous call timed out, additional calls to this function will
        still wait for a result and return it if available. If a result was
        returned or raised on one call, additional calls will return/raise the
        same result.
        """
        if threadable.isInIOThread():
            raise RuntimeError(
                "EventualResult.wait() must not be run in the reactor thread.")

        if imp.lock_held():
            # If EventualResult.wait() is run during module import, if the
            # Twisted code that is being run also imports something the result
            # will be a deadlock. Even if that is not an issue it would
            # prevent importing in other threads until the call returns.
            raise RuntimeError(
                "EventualResult.wait() must not be run at module import time.")

        result = self._result(timeout)
        if isinstance(result, Failure):
            result.raiseException()
        return result

    def stash(self):
        """
        Store the EventualResult in memory for later retrieval.

        Returns a integer uid which can be passed to crochet.retrieve_result()
        to retrieve the instance later on.
        """
        return _store.store(self)

    def original_failure(self):
        """
        Return the underlying Failure object, if the result is an error.

        If no result is yet available, or the result was not an error, None is
        returned.

        This method is useful if you want to get the original traceback for an
        error result.
        """
        try:
            result = self._result(0.0)
        except TimeoutError:
            return None
        if isinstance(result, Failure):
            return result
        else:
            return None


class ThreadLogObserver(object):
    """
    A log observer that wraps another observer, and calls it in a thread.

    In particular, used to wrap PythonLoggingObserver, so that blocking
    logging.py Handlers don't block the event loop.
    """
    def __init__(self, observer):
        self._observer = observer
        if getattr(select, "poll", None):
            from twisted.internet.pollreactor import PollReactor
            reactorFactory = PollReactor
        else:
            from twisted.internet.selectreactor import SelectReactor
            reactorFactory = SelectReactor
        self._logWritingReactor = reactorFactory()
        self._logWritingReactor._registerAsIOThread = False
        self._thread = threading.Thread(target=self._reader,
                                        name="CrochetLogWriter")
        self._thread.start()

    def _reader(self):
        """
        Runs in a thread, reads messages from a queue and writes them to
        the wrapped observer.
        """
        self._logWritingReactor.run(installSignalHandlers=False)

    def stop(self):
        """
        Stop the thread.
        """
        self._logWritingReactor.callFromThread(self._logWritingReactor.stop)

    def __call__(self, msg):
        """
        A log observer that writes to a queue.
        """
        self._logWritingReactor.callFromThread(self._observer, msg)


class EventLoop(object):
    """
    Initialization infrastructure for running a reactor in a thread.
    """
    def __init__(self, reactorFactory, atexit_register,
                 startLoggingWithObserver=None,
                 watchdog_thread=None,
                 reapAllProcesses=None):
        """
        reactorFactory: Zero-argument callable that returns a reactor.
        atexit_register: atexit.register, or look-alike.
        startLoggingWithObserver: Either None, or
            twisted.python.log.startLoggingWithObserver or lookalike.
        watchdog_thread: crochet._shutdown.Watchdog instance, or None.
        reapAllProcesses: twisted.internet.process.reapAllProcesses or
            lookalike.
        """
        self._reactorFactory = reactorFactory
        self._atexit_register = atexit_register
        self._startLoggingWithObserver = startLoggingWithObserver
        self._started = False
        self._lock = threading.Lock()
        self._watchdog_thread = watchdog_thread
        self._reapAllProcesses = reapAllProcesses

    def _startReapingProcesses(self):
        """
        Start a LoopingCall that calls reapAllProcesses.
        """
        lc = LoopingCall(self._reapAllProcesses)
        lc.clock = self._reactor
        lc.start(0.1, False)

    def _common_setup(self):
        """
        The minimal amount of setup done by both setup() and no_setup().
        """
        self._started = True
        self._reactor = self._reactorFactory()
        self._registry = ResultRegistry(self._reactor)
        # We want to unblock EventualResult regardless of how the reactor is
        # run, so we always register this:
        self._reactor.addSystemEventTrigger(
            "before", "shutdown", self._registry.stop)

    @synchronized
    def setup(self):
        """
        Initialize the crochet library.

        This starts the reactor in a thread, and connect's Twisted's logs to
        Python's standard library logging module.

        This must be called at least once before the library can be used, and
        can be called multiple times.
        """
        if self._started:
            return
        self._common_setup()
        if platform.type == "posix":
            self._reactor.callFromThread(self._startReapingProcesses)
        if self._startLoggingWithObserver:
            observer = ThreadLogObserver(PythonLoggingObserver().emit)
            def start():
                # Twisted is going to override warnings.showwarning; let's
                # make sure that has no effect:
                from twisted.python import log
                original = log.showwarning
                log.showwarning = warnings.showwarning
                self._startLoggingWithObserver(observer, False)
                log.showwarning = original
            self._reactor.callFromThread(start)

            # We only want to stop the logging thread once the reactor has
            # shut down:
            self._reactor.addSystemEventTrigger("after", "shutdown",
                                                observer.stop)
        t = threading.Thread(
            target=lambda: self._reactor.run(installSignalHandlers=False),
            name="CrochetReactor")
        t.start()
        self._atexit_register(self._reactor.callFromThread,
                              self._reactor.stop)
        self._atexit_register(_store.log_errors)
        if self._watchdog_thread is not None:
            self._watchdog_thread.start()

    @synchronized
    def no_setup(self):
        """
        Initialize the crochet library with no side effects.

        No reactor will be started, logging is uneffected, etc.. Future calls
        to setup() will have no effect. This is useful for applications that
        intend to run Twisted's reactor themselves, and so do not want
        libraries using crochet to attempt to start it on their own.

        If no_setup() is called after setup(), a RuntimeError is raised.
        """
        if self._started:
            raise RuntimeError("no_setup() is intended to be called once, by a"
                               " Twisted application, before any libraries "
                               "using crochet are imported and call setup().")
        self._common_setup()

    def run_in_reactor(self, function):
        """
        A decorator that ensures the wrapped function runs in the reactor thread.

        When the wrapped function is called, an EventualResult is returned.
        """
        def runs_in_reactor(result, args, kwargs):
            d = maybeDeferred(function, *args, **kwargs)
            result._connect_deferred(d)

        @wraps(function)
        def wrapper(*args, **kwargs):
            result = EventualResult(None, self._reactor)
            self._registry.register(result)
            self._reactor.callFromThread(runs_in_reactor, result, args, kwargs)
            return result
        wrapper.wrapped_function = function
        return wrapper

    def wait_for_reactor(self, function):
        """
        DEPRECATED, use wait_for(timeout) instead.

        A decorator that ensures the wrapped function runs in the reactor thread.

        When the wrapped function is called, its result is returned or its
        exception raised. Deferreds are handled transparently.
        """
        warnings.warn("@wait_for_reactor is deprecated, use @wait_for instead",
                      DeprecationWarning, stacklevel=2)
        # This will timeout, in theory. In practice the process will be dead
        # long before that.
        return self.wait_for(2 ** 31)(function)

    def wait_for(self, timeout):
        """
        A decorator factory that ensures the wrapped function runs in the
        reactor thread.

        When the wrapped function is called, its result is returned or its
        exception raised. Deferreds are handled transparently. Calls will
        timeout after the given number of seconds (a float), raising a
        crochet.TimeoutError, and cancelling the Deferred being waited on.
        """
        def decorator(function):
            @wraps(function)
            def wrapper(*args, **kwargs):
                @self.run_in_reactor
                def run():
                    return function(*args, **kwargs)
                eventual_result = run()
                try:
                    return eventual_result.wait(timeout)
                except TimeoutError:
                    eventual_result.cancel()
                    raise
            wrapper.wrapped_function = function
            return wrapper
        return decorator

    def in_reactor(self, function):
        """
        DEPRECATED, use run_in_reactor.

        A decorator that ensures the wrapped function runs in the reactor thread.

        The wrapped function will get the reactor passed in as a first
        argument, in addition to any arguments it is called with.

        When the wrapped function is called, an EventualResult is returned.
        """
        warnings.warn("@in_reactor is deprecated, use @run_in_reactor",
                      DeprecationWarning, stacklevel=2)
        @self.run_in_reactor
        @wraps(function)
        def add_reactor(*args, **kwargs):
            return function(self._reactor, *args, **kwargs)

        return add_reactor

########NEW FILE########
__FILENAME__ = _resultstore
"""
In-memory store for EventualResults.
"""

import threading

from twisted.python import log

from ._util import synchronized


class ResultStore(object):
    """
    An in-memory store for EventualResult instances.

    Each EventualResult put in the store gets a unique identifier, which can
    be used to retrieve it later. This is useful for referring to results in
    e.g. web sessions.

    EventualResults that are not retrieved by shutdown will be logged if they
    have an error result.
    """
    def __init__(self):
        self._counter = 0
        self._stored = {}
        self._lock = threading.Lock()

    @synchronized
    def store(self, deferred_result):
        """
        Store a EventualResult.

        Return an integer, a unique identifier that can be used to retrieve
        the object.
        """
        self._counter += 1
        self._stored[self._counter] = deferred_result
        return self._counter

    @synchronized
    def retrieve(self, result_id):
        """
        Return the given EventualResult, and remove it from the store.
        """
        return self._stored.pop(result_id)

    @synchronized
    def log_errors(self):
        """
        Log errors for all stored EventualResults that have error results.
        """
        for result in self._stored.values():
            failure = result.original_failure()
            if failure is not None:
                log.err(failure, "Unhandled error in stashed EventualResult:")


########NEW FILE########
__FILENAME__ = _shutdown
"""
Support for calling code when the main thread exits.

atexit cannot be used, since registered atexit functions only run after *all*
threads have exited.

The watchdog thread will be started by crochet.setup().
"""

import threading
import time

from twisted.python import log


class Watchdog(threading.Thread):
    """
    Watch a given thread, call a list of functions when that thread exits.
    """

    def __init__(self, canary, shutdown_function):
        threading.Thread.__init__(self, name="CrochetShutdownWatchdog")
        self._canary = canary
        self._shutdown_function = shutdown_function

    def run(self):
        while self._canary.is_alive():
            time.sleep(0.1)
        self._shutdown_function()


class FunctionRegistry(object):
    """
    A registry of functions that can be called all at once.
    """
    def __init__(self):
        self._functions = []

    def register(self, f, *args, **kwargs):
        """
        Register a function and arguments to be called later.
        """
        self._functions.append(lambda: f(*args, **kwargs))

    def run(self):
        """
        Run all registered functions in reverse order of registration.
        """
        for f in reversed(self._functions):
            try:
                f()
            except:
                log.err()


# This is... fragile. Not sure how else to do it though.
_registry = FunctionRegistry()
_watchdog = Watchdog([t for t in threading.enumerate()
                     if t.name == "MainThread"][0], _registry.run)
register = _registry.register

########NEW FILE########
__FILENAME__ = _util
"""
Utility functions and classes.
"""

from functools import wraps


def synchronized(method):
    """
    Decorator that wraps a method with an acquire/release of self._lock.
    """
    @wraps(method)
    def synced(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    synced.synchronized = True
    return synced

########NEW FILE########
__FILENAME__ = _version
"""
Store version in its own module so we can access it from both setup.py and
__init__.
"""
__version__ = "1.2.0"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Crochet documentation build configuration file, created by
# sphinx-quickstart on Mon Sep 16 19:37:18 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# Make sure local crochet is used when importing:
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Crochet'
copyright = u'2013, Itamar Turner-Trauring'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
import crochet
version = crochet.__version__
# The full version, including alpha/beta/rc tags.
release = crochet.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
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
#html_domain_indices = True

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'crochetdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Crochet.tex', u'Crochet Documentation',
   u'Itamar Turner-Trauring', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'crochet', u'Crochet Documentation',
     [u'Itamar Turner-Trauring'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Crochet', u'Crochet Documentation',
   u'Itamar Turner-Trauring', 'Crochet', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = blockingdns
#!/usr/bin/python
"""
Do a DNS lookup using Twisted's APIs.
"""
from __future__ import print_function

# The Twisted code we'll be using:
from twisted.names import client

from crochet import setup, wait_for
setup()


# Crochet layer, wrapping Twisted's DNS library in a blocking call.
@wait_for(timeout=5.0)
def gethostbyname(name):
    """Lookup the IP of a given hostname.

    Unlike socket.gethostbyname() which can take an arbitrary amount of time
    to finish, this function will raise crochet.TimeoutError if more than 5
    seconds elapse without an answer being received.
    """
    d = client.lookupAddress(name)
    d.addCallback(lambda result: result[0][0].payload.dottedQuad())
    return d


if __name__ == '__main__':
    # Application code using the public API - notice it works in a normal
    # blocking manner, with no event loop visible:
    import sys
    name = sys.argv[1]
    ip = gethostbyname(name)
    print(name, "->", ip)


########NEW FILE########
__FILENAME__ = downloader
#!/usr/bin/python
"""
A flask web application that downloads a page in the background.
"""

import logging
from flask import Flask, session, escape
from crochet import setup, run_in_reactor, retrieve_result, TimeoutError

# Can be called multiple times with no ill-effect:
setup()

app = Flask(__name__)


@run_in_reactor
def download_page(url):
    """
    Download a page.
    """
    from twisted.web.client import getPage
    return getPage(url)


@app.route('/')
def index():
    if 'download' not in session:
        # Calling an @run_in_reactor function returns an EventualResult:
        result = download_page('http://www.google.com')
        session['download'] = result.stash()
        return "Starting download, refresh to track progress."

    # Retrieval is a one-time operation, so the uid in the session cannot be
    # reused:
    result = retrieve_result(session.pop('download'))
    try:
        download = result.wait(timeout=0.1)
        return "Downloaded: " + escape(download)
    except TimeoutError:
        session['download'] = result.stash()
        return "Download in progress..."
    except:
        # The original traceback of the exception:
        return "Download failed:\n" + result.original_failure().getTraceback()


if __name__ == '__main__':
    import os, sys
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    app.secret_key = os.urandom(24)
    app.run()

########NEW FILE########
__FILENAME__ = fromtwisted
#!/usr/bin/python
"""
An example of using Crochet from a normal Twisted application.
"""

import sys

from crochet import no_setup, wait_for
# Tell Crochet not to run the reactor:
no_setup()

from twisted.internet import reactor
from twisted.python import log
from twisted.web.wsgi import WSGIResource
from twisted.web.server import Site
from twisted.names import client

# A WSGI application, will be run in thread pool:
def application(environ, start_response):
    start_response('200 OK', [])
    try:
        ip = gethostbyname('twistedmatrix.com')
        return "%s has IP %s" % ('twistedmatrix.com', ip)
    except Exception, e:
        return 'Error doing lookup: %s' % (e,)

# A blocking API that will be called from the WSGI application, but actually
# uses DNS:
@wait_for(timeout=10)
def gethostbyname(name):
    d = client.lookupAddress(name)
    d.addCallback(lambda result: result[0][0].payload.dottedQuad())
    return d

# Normal Twisted code, serving the WSGI application and running the reactor:
def main():
    log.startLogging(sys.stdout)
    pool = reactor.getThreadPool()
    reactor.listenTCP(5000, Site(WSGIResource(reactor, pool, application)))
    reactor.run()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = mxquery
#!/usr/bin/python
"""
A command-line application that uses Twisted to do an MX DNS query.
"""

from __future__ import print_function

from twisted.names.client import lookupMailExchange
from crochet import setup, wait_for
setup()


# Twisted code:
def _mx(domain):
    """
    Return Defered that fires with a list of (priority, MX domain) tuples for
    a given domain.
    """
    def got_records(result):
        return sorted(
            [(int(record.payload.preference), str(record.payload.name))
             for record in result[0]])
    d = lookupMailExchange(domain)
    d.addCallback(got_records)
    return d

# Blocking wrapper:
@wait_for(timeout=5)
def mx(domain):
    """
    Return list of (priority, MX domain) tuples for a given domain.
    """
    return _mx(domain)


# Application code:
def main(domain):
    print("Mail servers for %s:" % (domain,))
    for priority, mailserver in mx(domain):
        print(priority, mailserver)


if __name__ == '__main__':
    import sys
    main(sys.argv[1])

########NEW FILE########
__FILENAME__ = scheduling
#!/usr/bin/python
"""
An example of scheduling time-based events in the background.

Download the latest EUR/USD exchange rate from Yahoo every 30 seconds in the
background; the rendered Flask web page can use the latest value without
having to do the request itself.

Note this is example is for demonstration purposes only, and is not actually
used in the real world. You should not do this in a real application without
reading Yahoo's terms-of-service and following them.
"""

from __future__ import print_function

from flask import Flask

from twisted.internet.task import LoopingCall
from twisted.web.client import getPage
from twisted.python import log

from crochet import wait_for, run_in_reactor, setup
setup()


# Twisted code:
class _ExchangeRate(object):
    """Download an exchange rate from Yahoo Finance using Twisted."""

    def __init__(self, name):
        self._value = None
        self._name = name

    # External API:
    def latest_value(self):
        """Return the latest exchange rate value.

        May be None if no value is available.
        """
        return self._value

    def start(self):
        """Start the background process."""
        self._lc = LoopingCall(self._download)
        # Run immediately, and then every 30 seconds:
        self._lc.start(30, now=True)

    def _download(self):
        """Download the page."""
        print("Downloading!")
        def parse(result):
            print("Got %r back from Yahoo." % (result,))
            values = result.strip().split(",")
            self._value = float(values[1])
        d = getPage(
            "http://download.finance.yahoo.com/d/quotes.csv?e=.csv&f=c4l1&s=%s=X"
            % (self._name,))
        d.addCallback(parse)
        d.addErrback(log.err)
        return d


# Blocking wrapper:
class ExchangeRate(object):
    """Blocking API for downloading exchange rate."""

    def __init__(self, name):
        self._exchange = _ExchangeRate(name)

    @run_in_reactor
    def start(self):
        self._exchange.start()

    @wait_for(timeout=1)
    def latest_value(self):
        """Return the latest exchange rate value.

        May be None if no value is available.
        """
        return self._exchange.latest_value()


EURUSD = ExchangeRate("EURUSD")
app = Flask(__name__)

@app.route('/')
def index():
    rate = EURUSD.latest_value()
    if rate is None:
        rate = "unavailable, please refresh the page"
    return "Current EUR/USD exchange rate is %s." % (rate,)


if __name__ == '__main__':
    import sys, logging
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    EURUSD.start()
    app.run()

########NEW FILE########
__FILENAME__ = ssh
#!/usr/bin/python
"""
A demonstration of Conch, allowing you to SSH into a running Python server and
inspect objects at a Python prompt.

If you're using the system install of Twisted, you may need to install Conch
separately, e.g. on Ubuntu:

   $ sudo apt-get install python-twisted-conch

Once you've started the program, you can ssh in by doing:

    $ ssh admin@localhost -p 5022

The password is 'secret'. Once you've reached the Python prompt, you have
access to the app object, and can import code, etc.:

    >>> 3 + 4
    7
    >>> print(app)
    <flask.app.Flask object at 0x18e1690>

"""

import logging

from flask import Flask
from crochet import setup, run_in_reactor
setup()

# Web server:
app = Flask(__name__)

@app.route('/')
def index():
    return "Welcome to my boring web server!"


@run_in_reactor
def start_ssh_server(port, username, password, namespace):
    """
    Start an SSH server on the given port, exposing a Python prompt with the
    given namespace.
    """
    # This is a lot of boilerplate, see http://tm.tl/6429 for a ticket to
    # provide a utility function that simplifies this.
    from twisted.internet import reactor
    from twisted.conch.insults import insults
    from twisted.conch import manhole, manhole_ssh
    from twisted.cred.checkers import (
        InMemoryUsernamePasswordDatabaseDontUse as MemoryDB)
    from twisted.cred.portal import Portal

    sshRealm = manhole_ssh.TerminalRealm()
    def chainedProtocolFactory():
        return insults.ServerProtocol(manhole.Manhole, namespace)
    sshRealm.chainedProtocolFactory = chainedProtocolFactory

    sshPortal = Portal(sshRealm, [MemoryDB(**{username: password})])
    reactor.listenTCP(port, manhole_ssh.ConchFactory(sshPortal),
                      interface="127.0.0.1")


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    start_ssh_server(5022, "admin", "secret", {"app": app})
    app.run()

########NEW FILE########
__FILENAME__ = testing
#!/usr/bin/python
"""
Demonstration of accessing wrapped functions for testing.
"""

from __future__ import print_function

from crochet import setup, run_in_reactor
setup()

@run_in_reactor
def add(x, y):
    return x + y


if __name__ == '__main__':
    print("add() returns EventualResult:")
    print("    ", add(1, 2))
    print("add.wrapped_function() returns result of underlying function:")
    print("    ", add.wrapped_function(1, 2))

########NEW FILE########
