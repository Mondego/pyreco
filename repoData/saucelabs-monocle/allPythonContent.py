__FILENAME__ = basics
import monocle
from monocle import Return, InvalidYieldException

@monocle.o
def square(x):
    yield Return(x*x)
    print "not reached"

@monocle.o
def fail():
    raise Exception("boo")
    print (yield square(2))

@monocle.o
def invalid_yield():
    yield "this should fail"

@monocle.o
def main():
    value = yield square(5)
    print value
    try:
        yield fail()
    except Exception, e:
        print "Caught exception:", type(e), str(e)

    try:
        yield invalid_yield()
    except InvalidYieldException, e:
        print "Caught exception:", type(e), str(e)
    else:
        assert False

def func_fail():
    raise Exception("boo")

monocle.launch(fail)
monocle.launch(func_fail)
monocle.launch(main)

########NEW FILE########
__FILENAME__ = client_server
import sys
import time

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.stack.network import add_service, Service, Client, ConnectionLost

@_o
def handle_echo(conn):
    while True:
        try:
            message = yield conn.read_until('\r\n')
        except ConnectionLost:
            break
        yield conn.write("you said: %s\r\n" % message.strip())

@_o
def do_echos():
    try:
        client = Client()
        yield client.connect('localhost', 8000)
        t = time.time()
        for x in xrange(10000):
            msg = "hello, world #%s!" % x
            yield client.write(msg + '\r\n')
            echo_result = yield client.read_until("\r\n")
            assert echo_result.strip() == "you said: %s" % msg
        print '10000 loops in %.2fs' % (time.time() - t)
    finally:
        client.close()
        eventloop.halt()

add_service(Service(handle_echo, port=8000))
monocle.launch(do_echos)
eventloop.run()

########NEW FILE########
__FILENAME__ = client_timeouts
import sys
import monocle
from monocle import _o, Return
monocle.init(sys.argv[1])
from monocle.stack import eventloop
from monocle.stack.network import Client

@_o
def main():
    c = Client()
    """
    yield c.connect('google.com', 80)
    yield c.write("GET / HTTP/1.0\r\n\r\n")
    x = None
    c.timeout = 0
    try:
        x = yield c.read(40000)
    except Exception, e:
        print str(e)
    print x
    """
    c.timeout = 1
    yield c.connect('google.com', 80)
    c.timeout = 0
    x = yield c.read(40000)
    print x


monocle.launch(main)
eventloop.run()

########NEW FILE########
__FILENAME__ = echo_server
import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.stack.network import add_service, Service

@_o
def echo(conn):
    their_message = yield conn.readline()
    yield conn.write("you said: %s\r\n" % their_message.strip())

add_service(Service(echo, 7050))
eventloop.run()

########NEW FILE########
__FILENAME__ = eventloop
import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.util import sleep

@_o
def foo(x, z=1):
    yield sleep(1)
    print x

def bar(x, z=1):
    print x

@_o
def fail():
    raise Exception("whoo")
    yield sleep(1)

eventloop.queue_task(0, foo, x="oroutine worked")
eventloop.queue_task(0, bar, x="function worked")
eventloop.queue_task(0, fail)
eventloop.run()

########NEW FILE########
__FILENAME__ = http_client
import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.stack.network.http import HttpClient

@_o
def req():
    client = HttpClient()
    try:
        yield client.connect("www.google.com", 80)
        resp = yield client.request('/')
        print resp.code, repr(resp.body)
        resp = yield client.request('http://www.google.com/')
        print resp.code, repr(resp.body)
        client.close()
        yield client.connect("localhost", 80)
        resp = yield client.request('/')
        print resp.code, repr(resp.body)
        resp = yield client.request('http://localhost/')
        print resp.code, repr(resp.body)
    finally:
        eventloop.halt()

monocle.launch(req)
eventloop.run()

########NEW FILE########
__FILENAME__ = http_server
import sys

import monocle
from monocle import _o, Return
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.stack.network import add_service
from monocle.stack.network.http import HttpHeaders, HttpServer


@_o
def hello_http(req):
    content = "Hello, World!"
    headers = HttpHeaders()
    headers.add('Content-Length', len(content))
    headers.add('Content-Type', 'text/plain')
    headers.add('Connection', 'close')
    headers.add('Set-Cookie', 'test0=blar; Path=/')
    headers.add('Set-Cookie', 'test1=blar; Path=/')
    yield Return(200, headers, content)

add_service(HttpServer(8088, handler=hello_http))
eventloop.run()

########NEW FILE########
__FILENAME__ = service_error
import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.stack.network import add_service, Service

@_o
def lower_one(conn):
    raise Exception("testing")
    yield

@_o
def top_one(conn):
    yield lower_one(conn)

add_service(Service(top_one, 12345))
eventloop.run()

########NEW FILE########
__FILENAME__ = sieve
# Copyright (c) 2010 Sauce Labs Inc
# Copyright (c) 2009 The Go Authors. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#    * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#    * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Subject to the terms and conditions of this License, Google hereby
# grants to You a perpetual, worldwide, non-exclusive, no-charge,
# royalty-free, irrevocable (except as stated in this section) patent
# license to make, have made, use, offer to sell, sell, import, and
# otherwise transfer this implementation of Go, where such license
# applies only to those patent claims licensable by Google that are
# necessarily infringed by use of this implementation of Go. If You
# institute patent litigation against any entity (including a
# cross-claim or counterclaim in a lawsuit) alleging that this
# implementation of Go or a Contribution incorporated within this
# implementation of Go constitutes direct or contributory patent
# infringement, then any patent licenses granted to You under this
# License for this implementation of Go shall terminate as of the date
# such litigation is filed.

# This is a translation of sieve.go to Python with monocle.  It's a
# dangerous example, in that its memory footprint grows rapidly in
# both Go and Python.  It's indended here as a demonstration of the
# similarity of monocle's o-routines and experimental Channel class to
# Go's goroutines and channels.
# -sah

import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.experimental import Channel

# Send the sequence 2, 3, 4, ... to channel 'ch'.
@_o
def generate(ch):
    i = 2
    while True:
        yield ch.send(i)  # Send 'i' to channel 'ch'.
        i += 1

# Copy the values from channel 'inc' to channel 'outc',
# removing those divisible by 'prime'.
@_o
def filter(inc, outc, prime):
    while True:
        i = yield inc.recv()  # Receive value of new variable 'i' from 'in'.
        if i % prime != 0:
            yield outc.send(i)  # Send 'i' to channel 'outc'.

# The prime sieve: Daisy-chain filter processes together.
@_o
def main():
    ch = Channel()  # Create a new channel.
    monocle.launch(generate, ch)  # Start generate() as an o-routine.
    while True:
        prime = yield ch.recv()
        print prime
        ch1 = Channel()
        filter(ch, ch1, prime)
        ch = ch1

monocle.launch(main)
eventloop.run()

########NEW FILE########
__FILENAME__ = simplechan
import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.experimental import Channel

@_o
def main():
    s = 2
    ch = Channel(s)
    for i in xrange(s):
        print i
        yield ch.send(i)

    print ch.bufsize, len(ch._msgs)
    for i in xrange(s):
        print (yield ch.recv())
    print "done"

monocle.launch(main)
eventloop.run()

########NEW FILE########
__FILENAME__ = sleep
import sys

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.util import sleep

@_o
def print_every_second():
    for i in xrange(5):
        print "1"
        yield sleep(1)

@_o
def print_every_two_seconds():
    for i in xrange(5):
        print "2"
        yield sleep(2)
    eventloop.halt()

monocle.launch(print_every_second)
monocle.launch(print_every_two_seconds)
eventloop.run()

########NEW FILE########
__FILENAME__ = tb
import sys

import monocle
monocle.init(sys.argv[1])
from monocle import _o, launch
from monocle.util import sleep
from monocle.stack import eventloop
from monocle.stack.network.http import HttpClient

@_o
def req():
    client = HttpClient()
    yield client.connect("localhost", 12344, timeout=1)

def die():
  raise Exception("boom")

@_o
def fifth():
  die()

def fourth():
  return fifth()

@_o
def third():
  yield fourth()

def second():
  return third()

@_o
def first():
  yield second()

@_o
def first_evlp():
  try:
    yield sleep(1)
    yield req()
    yield launch(second)
  finally:
    eventloop.halt()

launch(first)
eventloop.queue_task(0, first_evlp)
eventloop.run()



########NEW FILE########
__FILENAME__ = tcp_proxy
import sys
import time

import monocle
from monocle import _o
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.stack.network import add_service, Service, Client, ConnectionLost

@_o
def pump(input, output):
    while True:
        try:
            message = yield input.read_some()
            yield output.write(message)
        except ConnectionLost:
            output.close()
            break

@_o
def handle_socks(conn):
    client = Client()
    yield client.connect('localhost', 8050)
    monocle.launch(pump, conn, client)
    yield pump(client, conn)

add_service(Service(handle_socks, port=7050))
eventloop.run()

########NEW FILE########
__FILENAME__ = webserver
import sys
import re
from collections import defaultdict

import monocle
from monocle import _o, Return
monocle.init(sys.argv[1])

from monocle.stack import eventloop
from monocle.stack.network import add_service
from monocle.stack.network.http import HttpServer


app = HttpServer(8888)


@app.get('/')
def index(req):
    yield Return(200, {'yes': 'indeed'}, "hello")


@app.post('/slashable/?')
def slashable(req):
    yield Return("slashable!")


@app.get('/first/:first/second/:second_what')
def params(req, first=None, second_what=None):
    yield Return("first: %s\nsecond: %s\n" % (first, second_what))


@app.get(re.compile('/re/[^x]'))
def regexp(req):
    yield Return("regexp!")


@app.get('/*/star/*')
def stars(req):
    yield Return("star!")


add_service(app)
eventloop.run()

########NEW FILE########
__FILENAME__ = eventloop
import asyncore
import time
import functools

from monocle import launch

class EventLoop(object):
    def __init__(self):
        self._running = True
        self._queue = []
        self._map = {}

    def queue_task(self, delay, callable, *args, **kw):
        now = time.time()
        when = now + delay
        self._queue.append((when, callable, args, kw))
        self._queue.sort(reverse=True)

    def run(self):
        while self._running:
            timeout = 0
            if self._queue:
                next = self._queue[-1][0] - time.time()
                if next <= 0:
                    task = self._queue.pop()
                    launch(task[1], *task[2], **task[3])
                else:
                    timeout = next
            if self._map:
                asyncore.loop(timeout=timeout, use_poll=True, count=1,
                              map=self._map)
            else:
                time.sleep(0.1)

    def halt(self):
        self._running = False

evlp = EventLoop()
queue_task = evlp.queue_task
run = evlp.run
halt = evlp.halt

########NEW FILE########
__FILENAME__ = callback
# Sort of like Twisted's Deferred, but simplified.  We don't do
# callback chaining, since oroutines replace that mechanism.
class Callback(object):
    def __init__(self):
        self._handlers = []

    def add(self, handler):
        if hasattr(self, 'result'):
            handler(self.result)
        else:
            if not callable(handler):
                raise TypeError("'%s' object is not callable" % type(handler).__name__)
            self._handlers.append(handler)

    def __call__(self, result):
        assert not hasattr(self, 'result'), "Already called back"
        for handler in self._handlers:
            handler(result)
        self.result = result


def defer(result):
    cb = Callback()
    cb(result)
    return cb

########NEW FILE########
__FILENAME__ = core
# This code is based heavily on inlineCallbacks from Twisted 10.0, see LICENSE.

import sys
import types
import logging
import traceback
import time
import inspect
import os.path
import functools

from callback import Callback, defer

try:
    from twisted.python.failure import Failure as TwistedFailure
    from twisted.internet.defer import Deferred as TwistedDeferred
except ImportError:
    class TwistedFailure: pass
    class TwistedDeferred: pass

logging.basicConfig(stream=sys.stderr,
                    format="%(message)s")
log = logging.getLogger("monocle")

blocking_warn_threshold = 500 # ms
tracebacks_elide_internals = True

class Return(object):
    def __init__(self, *args):
        # mimic the semantics of the return statement
        if len(args) == 0:
            self.value = None
        elif len(args) == 1:
            self.value = args[0]
        else:
            self.value = args

    def __repr__(self):
        return "<%s.%s object at 0x%x; value: %s>" % (self.__class__.__module__,
                                                      self.__class__.__name__,
                                                      id(self),
                                                      repr(self.value))


class InvalidYieldException(Exception):
    pass


def is_eventloop_stack(stack):
    this_dir = os.path.dirname(__file__)
    for file, line, context, code in stack:
        if (file.startswith(this_dir) and
            file.endswith("eventloop.py") and
            context == 'run'):
            return True
    return False


def format_stack_lines(stack, elide_internals=tracebacks_elide_internals):
    eliding = False
    lines = []
    for file, line, context, code in stack:
        this_file = __file__
        if this_file.endswith('.pyc'):
            this_file = this_file[:-1]
        if not file == this_file or not elide_internals:
            eliding = False
            lines.append("  File %s, line %s, in %s\n    %s" %
                         (file, line, context, code))
        else:
            if not eliding:
                eliding = True
                lines.append("  -- eliding monocle internals --")
    return lines


def format_tb(e, elide_internals=tracebacks_elide_internals):
    s = ""
    for i, (tb, stack) in enumerate(reversed(e._monocle['tracebacks'])):
        lines = tb.split('\n')

        first = lines[0] # "Traceback (most recent call last)"
        last = lines[-2] # Line describing the exception

        stack_lines = []
        if not is_eventloop_stack(stack):
            stack_lines = format_stack_lines(stack, elide_internals)

        # 3 because of the "Traceback (most recent call last)" line,
        # plus two lines describing the g.throw that got us the
        # exception
        lines = stack_lines + lines[3:-2]

        if is_eventloop_stack(stack):
            if elide_internals:
                lines += ["  -- trampolined off eventloop --"]
                if i + 1 == len(e._monocle['tracebacks']):
                    # the last one is details on how we got called
                    lines += format_stack_lines(stack[2:], elide_internals)
            else:
                lines += format_stack_lines(stack, elide_internals)

        s += "\n" + '\n'.join(lines)
    return first + s + "\n" + last


def _append_traceback(e, tb, stack):
    if not hasattr(e, "_monocle"):
        e._monocle = {'tracebacks': []}
    e._monocle['tracebacks'].append((tb, stack))
    return e


def _add_monocle_tb(e):
    tb = traceback.format_exc()
    stack = traceback.extract_stack()

    # if it's not an eventloop stack, the first one we get is
    # comprehensive and future ones are higher up the stack.  if it is
    # an eventloop stack, we need to add it to reconstruct how we got
    # to the first one.
    if is_eventloop_stack(stack) or not hasattr(e, "_monocle"):
        _append_traceback(e, tb, stack)
    return e


def _add_twisted_tb(f):
    tb = f.getTraceback(elideFrameworkCode=tracebacks_elide_internals)
    return _append_traceback(f.value, tb, None)


def _monocle_chain(to_gen, g, callback):
    # This function is complicated by the need to prevent unbounded recursion
    # arising from repeatedly yielding immediately ready callbacks.  This while
    # loop solves that by manually unfolding the recursion.

    while True:
        try:
            # Send the last result back as the result of the yield expression.
            start = time.time()
            try:
                if isinstance(to_gen, Exception):
                    from_gen = g.throw(type(to_gen), to_gen)
                elif isinstance(to_gen, TwistedFailure):
                    from_gen = g.throw(to_gen.type, to_gen.value, to_gen.tb)
                else:
                    from_gen = g.send(to_gen)
            finally:
                duration = (time.time() - start) * 1000
                if duration > blocking_warn_threshold:
                    if inspect.isframe(g.gi_frame):
                        fi = inspect.getframeinfo(g.gi_frame)
                        log.warn("oroutine '%s' blocked for %dms before %s:%s", g.__name__, duration, fi.filename, fi.lineno)
                    else:
                        log.warn("oroutine '%s' blocked for %dms", g.__name__, duration)
        except StopIteration:
            # "return" statement (or fell off the end of the generator)
            from_gen = Return()
        except Exception, e:
            callback(_add_monocle_tb(e))
            return callback

        if isinstance(from_gen, Return):
            try:
                g.close()
            except Exception, e:
                callback(_add_monocle_tb(e))
            else:
                callback(from_gen.value)
            return callback
        elif not isinstance(from_gen, Callback):
            if isinstance(from_gen, TwistedDeferred):
                cb = Callback()
                from_gen.addCallbacks(cb, lambda f: cb(_add_twisted_tb(f)))
                from_gen = cb
            else:
                e = InvalidYieldException("Unexpected value '%s' of type '%s' yielded from o-routine '%s'.  O-routines can only yield Callback and Return types." % (from_gen, type(from_gen), g))
                return _monocle_chain(e, g, callback)

        if not hasattr(from_gen, 'result'):
            def gotResult(r):
                _monocle_chain(r, g, callback)
            from_gen.add(gotResult)
            return callback

        to_gen = from_gen.result


def maybeCallbackGenerator(f, *args, **kw):
    try:
        result = f(*args, **kw)
    except Exception, e:
        return defer(_add_monocle_tb(e))

    if isinstance(result, types.GeneratorType):
        return _monocle_chain(None, result, Callback())
    elif isinstance(result, Callback):
        return result
    elif isinstance(result, TwistedDeferred):
        cb = Callback()
        result.addCallbacks(cb, lambda f: cb(_add_twisted_tb(f)))
        return cb
    return defer(result)


# @_o
def _o(f):
    """
    monocle helps you write Callback-using code that looks like a regular
    sequential function.  For example::

        @_o
        def foo():
            result = yield makeSomeRequestResultingInCallback()
            print result

    When you call anything that results in a Callback, you can simply yield it;
    your generator will automatically be resumed when the Callback's result is
    available. The generator will be sent the result of the Callback with the
    'send' method on generators, or if the result was a failure, 'throw'.

    Your coroutine-enabled generator will return a Callback object,
    which will result in the return value of the generator (or will
    fail with a failure object if your generator raises an unhandled
    exception). Note that you can't use "return result" to return a
    value; use "yield Return(result)" instead. Falling off the end of
    the generator, or simply using "return" will cause the Callback to
    have a result of None.  Yielding anything other and a Callback or
    a Return is not allowed, and will raise an exception.

    The Callback returned from your generator will call back with an
    exception if your generator raised an exception::

        @_o
        def foo():
            result = yield makeSomeRequestResultingInCallback()
            if result == 'foo':
                # this will become the result of the Callback
                yield Return('success')
            else:
                # this too
                raise Exception('fail')
    """
    @functools.wraps(f)
    def unwindGenerator(*args, **kwargs):
        return maybeCallbackGenerator(f, *args, **kwargs)
    return unwindGenerator
o = _o


def log_exception(msg="", elide_internals=tracebacks_elide_internals):
    e = sys.exc_info()[1]

    if hasattr(e, '_monocle'):
        log.error("%s\n%s", msg, format_tb(e, elide_internals=elide_internals))
    else:
        log.exception(msg)


@_o
def launch(oroutine, *args, **kwargs):
    try:
        cb = oroutine(*args, **kwargs)
        if not isinstance(cb, (Callback, TwistedDeferred)):
            yield Return(cb)

        r = yield cb
        yield Return(r)
    except GeneratorExit:
        raise
    except Exception:
        log_exception(elide_internals=kwargs.get('elide_internals',
                                                 tracebacks_elide_internals))

########NEW FILE########
__FILENAME__ = experimental
# -*- coding: utf-8 -*-
#
# by Steven Hazel

from collections import deque
from callback import Callback
from monocle.stack.eventloop import queue_task
from monocle import _o, Return


# Go-style channels
class Channel(object):
    def __init__(self, bufsize=0):
        self.bufsize = bufsize
        self._msgs = deque()
        self._recv_cbs = deque()
        self._send_cbs = deque()

    @_o
    def send(self, value):
        if self._recv_cbs:
            # if there are receivers waiting, send to the first one
            rcb = self._recv_cbs.popleft()
            queue_task(0, rcb, value)
        elif len(self._msgs) < self.bufsize:
            # if there's available buffer, use that
            self._msgs.append(value)
        else:
            # otherwise, wait for a receiver
            cb = Callback()
            self._send_cbs.append(cb)
            rcb = yield cb
            queue_task(0, rcb, value)

    @_o
    def recv(self):
        # if there's buffer, read it
        if self._msgs:
            value = self._msgs.popleft()
            yield Return(value)

        # otherwise we need a sender
        rcb = Callback()
        if self._send_cbs:
            # if there are senders waiting, wake up the first one
            cb = self._send_cbs.popleft()
            cb(rcb)
        else:
            # otherwise, wait for a sender
            self._recv_cbs.append(rcb)
        value = yield rcb
        yield Return(value)


# Some ideas from diesel:

# This is really not a very good idea without limiting it to a set of
# cancelable operations...
@_o
def first_of(*a):
    cb = Callback()
    cb.called = False
    for i, c in enumerate(a):
        def cb(result, i=i):
            if isinstance(result, Exception):
                raise result
            if not cb.called:
                cb.called = True
                cb((i, result))
        c.add(cb)
    x, r = yield cb
    yield Return([(True, r) if x == i else None for i in xrange(len(a))])


waits = {}

@_o
def fire(name, value):
    if name in waits:
        cb = waits[name]
        waits.pop(name)
        cb(value)

@_o
def wait(name):
    waits.setdefault(name, Callback())
    r = yield waits[name]
    yield Return(r)

########NEW FILE########
__FILENAME__ = repl
import sys
import code
import readline
import atexit
import os
import traceback
from threading import Thread

import monocle
from monocle import _o, Return
monocle.init(sys.argv[1])
from monocle.stack import eventloop
from monocle.callback import Callback

# it's annoying to ever see these warnings at the repl, so tolerate a lot
monocle.core.blocking_warn_threshold = 10000

class HistoryConsole(code.InteractiveConsole):
    def __init__(self, locals=None, filename="<console>",
                 histfile=os.path.expanduser("~/.console-history")):
        code.InteractiveConsole.__init__(self, locals, filename)
        self.init_history(histfile)

    def init_history(self, histfile):
        readline.parse_and_bind("tab: complete")
        if hasattr(readline, "read_history_file"):
            try:
                readline.read_history_file(histfile)
            except IOError:
                pass
            atexit.register(self.save_history, histfile)

    def save_history(self, histfile):
        readline.write_history_file(histfile)

@_o
def main():
    print "Monocle", monocle.VERSION, "/", "Python", sys.version
    print 'Type "help", "copyright", "credits" or "license" for more information.'
    print "You can yield to Monocle oroutines at the prompt."
    ic = HistoryConsole()
    gs = dict(globals())
    ls = {}
    source = ""
    while True:
        try:
            if source:
                source += "\n"

            cb = Callback()
            def wait_for_input():
                try:
                    prompt = ">>> "
                    if source:
                        prompt = "... "
                    s = ic.raw_input(prompt)
                except EOFError:
                    eventloop.queue_task(0, eventloop.halt)
                    return
                eventloop.queue_task(0, cb, s)

            Thread(target=wait_for_input).start()
            source += yield cb

            if "\n" in source and not source.endswith("\n"):
                continue

            try:
                _c = code.compile_command(source)
                if not _c:
                    continue
                eval(_c, gs, ls)
            except SyntaxError, e:
                if not "'yield' outside function" in str(e):
                    raise

                # it's a yield!

                try:
                    core_hack_source = "    __r = (" + source.replace("\n", "\n    ") + ")"
                    hack_source = "def __g():\n" + core_hack_source + "\n    yield Return(locals())\n\n"
                    _c = code.compile_command(hack_source)
                except SyntaxError:
                    # maybe the return value assignment wasn't okay
                    core_hack_source = "    " + source.replace("\n", "\n    ")
                    hack_source = "def __g():\n" + core_hack_source + "\n    yield Return(locals())\n\n"
                    _c = code.compile_command(hack_source)

                if not _c:
                    continue

                # make the locals global so __g can reach them
                g_gs = dict(gs)
                g_gs.update(ls)
                eval(_c, g_gs, ls)

                # now monoclize it and get the callback
                _c = code.compile_command("monocle.o(__g)()", symbol="eval")
                cb = eval(_c, gs, ls)
                ls.pop('__g')
                #print "=== waiting for %s ===" % cb
                g_ls = yield cb
                if '__r' in g_ls:
                    r = g_ls.pop('__r')
                    if r:
                        print r
                ls.update(g_ls)
        except Exception:
            traceback.print_exc()

        source = ""


if __name__ == '__main__':
    monocle.launch(main)
    eventloop.run()

########NEW FILE########
__FILENAME__ = eventloop
import monocle
if monocle._stack_name == 'twisted':
    from monocle.twisted_stack.eventloop import *
elif monocle._stack_name == 'tornado':
    from monocle.tornado_stack.eventloop import *
elif monocle._stack_name == 'asyncore':
    from monocle.asyncore_stack.eventloop import *

########NEW FILE########
__FILENAME__ = sync
# eventually this will be part of monocle

import select
import logging
import time
import socket
import cPickle as pickle
from multiprocessing import Process, Pipe
from functools import partial

try:
    import errno
except ImportError:
    errno = None
EINTR = getattr(errno, 'EINTR', 4)

import monocle
from monocle import _o, Return, launch
from monocle.core import Callback
from monocle.stack.network import add_service, Client
from monocle.stack.multiprocess import PipeChannel, SocketChannel, get_conn, make_subchannels, Service

log = logging.getLogger("monocle.stack.multiprocess.sync")
subproc_formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")


@_o
def log_receive(chan):
    root = logging.getLogger('')
    while True:
        levelno, msg = yield chan.recv()
        # python's logging module is ridiculous
        for h in root.handlers:
            h.old_formatter = h.formatter
            h.setFormatter(subproc_formatter)
        log.log(levelno, msg)
        for h in root.handlers:
            h.setFormatter(h.old_formatter)


### using sockets ###
class SyncSockChannel(object):
    def __init__(self, sock):
        self.sock = sock

    def _sendall(self, data):
        while data:
            try:
                r = self.sock.send(data)
            except socket.error, e:
                if e.args[0] == EINTR:
                    continue
                raise
            data = data[r:]

    def _recv(self, count):
        result = ""
        while count:
            try:
                data = self.sock.recv(min(count, 4096))
            except socket.error, e:
                if e.args[0] == EINTR:
                    continue
                raise
            else:
                count -= len(data)
                result += data
        return result

    def send(self, value):
        p = pickle.dumps(value)
        self._sendall(str(len(p)))
        self._sendall("\n")
        self._sendall(p)

    def recv(self):
        l = ""
        while True:
            x = self._recv(1)
            if x == "\n":
                break
            l += x
        l = int(l)
        p = self._recv(l)
        try:
            value = pickle.loads(p)
        except Exception:
            log.exception("Error loading pickle: %s", p)
            raise
        return value

    def poll(self):
        r, w, x = select.select([self.sock], [], [self.sock], 0)
        if r + x:
            log.info("poll triggered")
            return True
        else:
            return False


class SockChannelHandler(logging.Handler):
    def __init__(self, sock):
        logging.Handler.__init__(self)

        self.sock = sock

    def setFormatter(self, formatter):
        self.formatter = formatter

    def send(self, record):
        # ow, python logging is painful to work with
        if record.args and isinstance(record.args, tuple):
            args = record.args
            new_args = []
            for arg in args:
                if isinstance(arg, str):
                    new_args.append(arg.decode('utf-8', 'replace'))
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)
        self.sock.send((record.levelno, self.formatter.format(record)))

    def emit(self, record):
        try:
            self.send(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def close(self):
        logging.Handler.close(self)


class SyncSockSubchan(object):
    def __init__(self, chan, subchan):
        self.chan = chan
        self.subchan = subchan

    def send(self, value):
        return self.chan.send({'subchan': self.subchan,
                               'content': value})

    def recv(self):
        value = self.chan.recv()
        assert value['subchan'] == self.subchan
        return value['content']

    def poll(self):
        return self.chan.poll()


def _wrapper_with_sockets(target, port, *args, **kwargs):
    sock = socket.socket()
    while True:
        try:
            sock.connect(('127.0.0.1', port))
        except Exception, e:
            print "failed to connect to monocle multiprocess parent on port", port, type(e), str(e)
            time.sleep(0.2)
            sock.close()
            sock = socket.socket()
        else:
            break
    try:
        formatter = logging.Formatter("%(asctime)s - %(name)s[%(funcName)s:"
                                      "%(lineno)s] - %(levelname)s - %(message)s")
        chan = SyncSockChannel(sock)
        handler = SockChannelHandler(SyncSockSubchan(chan, 'log'))
        handler.setFormatter(formatter)
        root = logging.getLogger('')
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)

        target(SyncSockSubchan(chan, 'main'), *args, **kwargs)
    finally:
        log.info("subprocess finished, closing monocle socket")
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()


@_o
def launch_proc_with_sockets(target, port, *args, **kwargs):
    args = [target, port] + list(args)
    p = Process(target=_wrapper_with_sockets, args=args, kwargs=kwargs)
    p.start()
    cb = Callback()
    get_chan_service = partial(get_conn, cb)
    service = Service(get_chan_service, port, bindaddr="127.0.0.1", backlog=1)
    service._add()
    conn = yield cb
    yield service.stop()
    chan = SocketChannel(conn)
    main_chan, log_chan = make_subchannels(chan, ['main', 'log'])
    launch(log_receive, log_chan)
    yield Return(p, main_chan)


### using pipes ###
class PipeHandler(logging.Handler):
    def __init__(self, pipe):
        logging.Handler.__init__(self)

        self.pipe = pipe

    def setFormatter(self, formatter):
        self.formatter = formatter

    def send(self, record):
        # ow, python logging is painful to work with
        if record.args and isinstance(record.args, tuple):
            args = record.args
            new_args = []
            for arg in args:
                if isinstance(arg, str):
                    new_args.append(arg.decode('utf-8', 'replace'))
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)
        self.pipe.send(self.formatter.format(record))

    def emit(self, record):
        try:
            self.send(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def close(self):
        logging.Handler.close(self)


def _wrapper_with_pipes(target, log_pipe, pipe, *args, **kwargs):
    formatter = logging.Formatter("%(asctime)s - %(name)s[%(funcName)s:"
                                  "%(lineno)s] - %(levelname)s - %(message)s")
    pipehandler = PipeHandler(log_pipe)
    pipehandler.setFormatter(formatter)
    target(pipe, *args, **kwargs)


def launch_proc_with_pipes(target, *args, **kwargs):
    log_child, log_parent = Pipe()
    child, parent = Pipe()
    args = [target, log_child, child] + list(args)
    p = Process(target=_wrapper_with_pipes, args=args, kwargs=kwargs)
    p.start()
    launch(log_receive, PipeChannel(log_parent))
    return p, parent

########NEW FILE########
__FILENAME__ = http
import urlparse
import collections
import re
import urllib2

from functools import wraps

from monocle import _o, Return
from monocle.stack.network import ConnectionLost, Client, SSLClient


class HttpHeaders(collections.MutableMapping):
    def __init__(self, headers=None):
        self.headers = []
        self.keys = set()
        if hasattr(headers, 'iteritems'):
            for k, v in headers.iteritems():
                self.add(k, v)
        else:
            for k, v in headers or []:
                self.add(k, v)

    def __len__(self):
        return len(self.headers)

    def keys(self):
        return [k for k, v in self.headers]

    def add(self, key, value):
        key = key.lower()
        self.keys.add(key)
        self.headers.append((key, value))

    def items(self):
        return self.headers

    def __iter__(self):
        return (k for k, v in self.headers)

    def iteritems(self):
        return (x for x in self.headers)

    def __repr__(self):
        return repr(self.headers)

    def __getitem__(self, key):
        key = key.lower()
        if not key in self.keys:
            raise KeyError(key)
        vals = [v for k, v in self.headers if k == key]
        if len(vals) == 1:
            return vals[0]
        else:
            return vals

    def __setitem__(self, key, value):
        try:
            del self[key]
        except KeyError:
            pass
        return self.add(key, value)

    def __delitem__(self, key):
        key = key.lower()
        if not key in self.keys:
            raise KeyError(key)
        self.keys.remove(key)
        self.headers = [(k, v) for k, v in self.headers if k != key]


class HttpResponse(object):
    def __init__(self, code, msg=None, headers=None, body=None, proto=None):
        self.code = code
        self.msg = msg
        self.headers = headers or HttpHeaders()
        self.body = body
        self.proto = proto or 'HTTP/1.1'


def parse_headers(lines):
    headers = HttpHeaders()
    for line in lines:
        k, v = line.split(":", 1)
        headers.add(k, v.lstrip())
    return headers


def parse_request(data):
    data = data[:-4]
    lines = data.split("\r\n")
    method, path, proto = lines[0].split(" ", 2)
    headers = parse_headers(lines[1:])
    return method, path, proto, headers


def parse_response(data):
    data = data[:-4]
    lines = data.split("\r\n")
    parts = lines[0].split(" ")
    proto = parts[0]
    code = parts[1]
    if len(parts) > 2:
        msg = parts[2]
    else:
        msg = ""
    headers = parse_headers(lines[1:])
    return proto, code, msg, headers


@_o
def read_request(conn):
    data = yield conn.read_until("\r\n\r\n")
    method, path, proto, headers = parse_request(data)
    body = None
    if method in ["POST", "PUT"] and "Content-Length" in headers:
        cl = int(headers["Content-Length"])
        body = yield conn.read(cl)
    yield Return(method, path, proto, headers, body)


@_o
def write_request(conn, method, path, headers, body=None):
    yield conn.write("%s %s HTTP/1.1\r\n" % (method, path))
    for k, v in headers.iteritems():
        yield conn.write("%s: %s\r\n" % (k, v))
    yield conn.write("\r\n")
    if body:
        yield conn.write(body)


@_o
def read_response(conn):
    data = yield conn.read_until("\r\n\r\n")
    proto, code, msg, headers = parse_response(data)

    proto = proto.lower()
    content_length = int(headers.get('Content-Length', 0))
    body = ""

    # From rfc2616 section 4.4:
    # Messages MUST NOT include both a Content-Length header field and
    # a non-identity transfer-coding. If the message does include a
    # non- identity transfer-coding, the Content-Length MUST be
    # ignored.
    if headers.get('Transfer-Encoding', '').lower() == 'chunked':
        while True:
            line = yield conn.read_until("\r\n")
            line = line[:-2]
            parts = line.split(';')
            chunk_len = int(parts[0], 16)
            body += yield conn.read(chunk_len)
            yield conn.read_until("\r\n")
            if not chunk_len:
                break
    elif content_length:
        body = yield conn.read(content_length)
    elif ((proto == 'http/1.0' and
           not headers.get('Connection', '').lower() == 'keep-alive')
          or
          (proto == 'http/1.1' and
           headers.get('Connection', '').lower() == 'close')):
        while True:
            try:
                body += yield conn.read_some()
            except ConnectionLost:
                break

    yield Return(HttpResponse(code, msg, headers, body, proto))


@_o
def write_response(conn, resp):
    yield conn.write("%s %s %s\r\n" % (resp.proto.upper(), resp.code, resp.msg))
    for k, v in resp.headers.iteritems():
        yield conn.write("%s: %s\r\n" % (k, v))
    yield conn.write('\r\n')
    if resp.body:
        yield conn.write(resp.body)


class HttpClient(object):
    DEFAULT_PORTS = {'http': 80,
                     'https': 443}

    def __init__(self):
        self.client = None
        self.scheme = None
        self.host = None
        self.port = None
        self._timeout = None

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        self._timeout = value
        if self.client:
            self.client.timeout = value

    @_o
    def connect(self, host, port, scheme='http', timeout=None):
        if timeout is not None:
            # this parameter is deprecated
            self.timeout = None

        if self.client and not self.client.is_closed():
            self.client.close()

        if scheme == 'http':
            self.client = Client()
        elif scheme == 'https':
            self.client = SSLClient()
        else:
            raise HttpException('unsupported url scheme %s' % scheme)
        self.scheme = scheme
        self.host = host
        self.port = port
        self.client.timeout = self._timeout
        yield self.client.connect(self.host, self.port)

    @_o
    def request(self, url, headers=None, method='GET', body=None):
        parts = urlparse.urlsplit(url)
        scheme = parts.scheme or self.scheme
        if parts.scheme and parts.scheme not in ['http', 'https']:
            raise HttpException('unsupported url scheme %s' % parts.scheme)
        host = parts.hostname or self.host
        path = parts.path
        if parts.query:
            path += '?' + parts.query

        if scheme != self.scheme:
            raise HttpException("URL is %s but connection is %s" %
                                (scheme, self.scheme))

        if not headers:
            headers = HttpHeaders()
        headers.setdefault('User-Agent', 'monocle/%s' % VERSION)
        headers.setdefault('Host', host)
        if body is not None:
            headers['Content-Length'] = str(len(body))

        yield write_request(self.client, method, path, headers, body)
        response = yield read_response(self.client)
        yield Return(response)

    def close(self):
        self.client.close()

    def is_closed(self):
        return self.client is None or self.client.is_closed()

    @classmethod
    @_o
    def query(cls, url, headers=None, method='GET', body=None):
        self = cls()
        parts = urlparse.urlsplit(url)
        host = parts.hostname
        port = parts.port or self.DEFAULT_PORTS[parts.scheme]

        if not self.client or self.client.is_closed():
            yield self.connect(host, port, scheme=parts.scheme)
        elif not (self.host, self.port) == (host, port):
            self.client.close()
            yield self.connect(host, port, scheme=parts.scheme)

        result = yield self.request(url, headers, method, body)
        self.close()
        yield Return(result)


# Takes a response return value like:
# "this is a body"
# 404
# (200, "this is a body")
# (200, {"headers": "here"}, "this is a body")
#
# ...and converts that to a full (code, headers, body) tuple.
def extract_response(value):
    if isinstance(value, basestring):
        return (200, HttpHeaders(), value)
    if isinstance(value, int):
        return (value, HttpHeaders(), "")
    if len(value) == 2:
        return (value[0], HttpHeaders(), value[1])
    return value


class HttpRouter(object):
    named_param_re = re.compile(r':([^\/\?\*\:]+)')

    def __init__(self):
        self.routes = collections.defaultdict(list)

    @classmethod
    def path_matches(cls, path, pattern):
        m = pattern.match(path)
        if not m:
            return False, None
        if not m.end() == len(path):
            # must match the whole string
            return False, None
        return True, m.groupdict()

    def mk_decorator(self, method, pattern):
        if not hasattr(pattern, 'match'):
            pattern = re.escape(pattern)
            pattern = pattern.replace(r'\?', '?')
            pattern = pattern.replace(r'\:', ':')
            pattern = pattern.replace(r'\_', '_')
            pattern = pattern.replace(r'\/', '/')
            pattern = pattern.replace(r'\*', '.*')
            pattern = self.named_param_re.sub(r'(?P<\1>[^/]+)', pattern)
            pattern = re.compile("^" + pattern + "$")

        def decorator(f):
            @_o
            @wraps(f)
            def replacement(req, **kwargs):
                resp = yield _o(f)(req, **kwargs)
                yield Return(resp)
            self.routes[method].append((pattern, replacement))
            return replacement
        return decorator

    def get(self, pattern):
        return self.mk_decorator('GET', pattern)

    def post(self, pattern):
        return self.mk_decorator('POST', pattern)

    def put(self, pattern):
        return self.mk_decorator('PUT', pattern)

    def delete(self, pattern):
        return self.mk_decorator('DELETE', pattern)

    def head(self, pattern):
        return self.mk_decorator('HEAD', pattern)

    def options(self, pattern):
        return self.mk_decorator('OPTIONS', pattern)

    def patch(self, pattern):
        return self.mk_decorator('PATCH', pattern)

    @_o
    def handle_request(self, req):
        for pattern, handler in self.routes[req.method]:
            match, kwargs = self.path_matches(urllib2.unquote(req.path),
                                              pattern)
            if match:
                yield Return((yield handler(req, **kwargs)))
        if self.handler:
            resp = yield self.handler(req)
            yield Return(resp)
        yield Return(404, {}, "")


import monocle
if monocle._stack_name == 'twisted':
    from monocle.twisted_stack.network.http import *
elif monocle._stack_name == 'tornado':
    from monocle.tornado_stack.network.http import *

########NEW FILE########
__FILENAME__ = eventloop
import tornado.ioloop
import time
import thread

from monocle import launch


class Task(object):
    def __init__(self, tornado_ioloop, timeout):
        self._timeout = timeout
        self._tornado_ioloop = tornado_ioloop

    def cancel(self):
        self._tornado_ioloop.remove_timeout(self._timeout)


class EventLoop(object):
    def __init__(self):
        self._tornado_ioloop = tornado.ioloop.IOLoop.instance()
        self.READ = self._tornado_ioloop.READ
        self._thread_ident = thread.get_ident()

    def queue_task(self, delay, callable, *args, **kw):
        def task():
            return launch(callable, *args, **kw)
        def queue():
            now = time.time()
            timeout = self._tornado_ioloop.add_timeout(now + delay, task)
            return Task(self._tornado_ioloop, timeout)

        if thread.get_ident() != self._thread_ident:
            self._tornado_ioloop.add_callback(queue)
        else:
            return queue()

    def run(self):
        self._tornado_ioloop.start()

    def halt(self):
        self._tornado_ioloop.stop()

    def _add_handler(self, *a, **k):
        self._tornado_ioloop.add_handler(*a, **k)

    def _remove_handler(self, *a, **k):
        self._tornado_ioloop.remove_handler(*a, **k)

evlp = EventLoop()
queue_task = evlp.queue_task
run = evlp.run
halt = evlp.halt

########NEW FILE########
__FILENAME__ = http
# -*- coding: utf-8 -*-
#
# by Steven Hazel

import tornado.httpclient
import tornado.httpserver

from httplib import responses
from monocle import _o, Return, VERSION, launch
from monocle.callback import Callback
from monocle.stack.network.http import HttpHeaders, HttpClient, HttpRouter, extract_response


class HttpException(Exception): pass


class HttpClient(HttpClient):
    @classmethod
    @_o
    def query(self, url, headers=None, method='GET', body=None):
        _http_client = tornado.httpclient.AsyncHTTPClient()
        req = tornado.httpclient.HTTPRequest(url,
                                             method=method,
                                             headers=headers or {},
                                             body=body,
                                             # XXX: TODO
                                             #request_timeout=self.timeout
                                             )
        cb = Callback()
        _http_client.fetch(req, cb)
        response = yield cb
        yield Return(response)


class HttpServer(HttpRouter):
    def __init__(self, port, handler=None):
        HttpRouter.__init__(self)
        self.handler = handler
        self.port = port

    def _add(self, el):
        @_o
        def _handler(request):
            try:
                value = yield launch(self.handle_request, request)
                code, headers, content = extract_response(value)
            except:
                code, headers, content = 500, {}, "500 Internal Server Error"
            request.write("HTTP/1.1 %s %s\r\n" %
                          (code, responses.get(code, 'Unknown')))
            headers.setdefault('Server', 'monocle/%s' % VERSION)
            headers.setdefault('Content-Length', str(len(content)))
            for name, value in headers.iteritems():
                request.write("%s: %s\r\n" % (name, value))
            request.write("\r\n")
            request.write(content)
            request.finish()
        self._http_server = tornado.httpserver.HTTPServer(
            _handler,
            io_loop=el._tornado_ioloop)
        self._http_server.listen(self.port)

########NEW FILE########
__FILENAME__ = eventloop
import sys
import thread

from monocle import launch

# prefer fast reactors
# FIXME: this should optionally refuse to use slow ones
if not "twisted.internet.reactor" in sys.modules:
    try:
        from twisted.internet import epollreactor
        epollreactor.install()
    except:
        try:
            from twisted.internet import kqreactor
            kqreactor.install()
        except:
            try:
                from twisted.internet import pollreactor
                pollreactor.install()
            except:
                pass

from twisted.internet import reactor
try:
    from twisted.internet.error import ReactorNotRunning
except ImportError:
    ReactorNotRunning = RuntimeError


# thanks to Peter Norvig
def singleton(object, message="singleton class already instantiated",
              instantiated=[]):
    """
    Raise an exception if an object of this class has been instantiated before.
    """
    assert object.__class__ not in instantiated, message
    instantiated.append(object.__class__)


class Task(object):
    def __init__(self, df):
        self._df = df

    def cancel(self):
        self._df.cancel()


class EventLoop(object):
    def __init__(self):
        singleton(self, "Twisted can only have one EventLoop (reactor)")
        self._halted = False
        self._thread_ident = thread.get_ident()

    def queue_task(self, delay, callable, *args, **kw):
        if thread.get_ident() != self._thread_ident:
            reactor.callFromThread(reactor.callLater, delay, launch, callable, *args, **kw)
        else:
            df = reactor.callLater(delay, launch, callable, *args, **kw)
            return Task(df)

    def run(self):
        if not self._halted:
            self._thread_ident = thread.get_ident()
            reactor.run()

    def halt(self):
        try:
            reactor.stop()
        except ReactorNotRunning:
            self._halted = True
            pass

evlp = EventLoop()
queue_task = evlp.queue_task
run = evlp.run
halt = evlp.halt

########NEW FILE########
__FILENAME__ = multiprocess
from multiprocessing import Process, Pipe

from monocle.twisted_stack.network import add_service, Client, ConnectionLost, _Connection, Factory, reactor
from twisted.internet import ssl

from monocle.stack.multiprocess import launch_proc

log = logging.getLogger(__name__)


class PipeForTwisted(object):
    def __init__(self, pipe):
        self.pipe = pipe
        self.callback = Callback()

    def doRead(self):
        self.callback((False, None))

    def fileno(self):
        return self.pipe.fileno()

    def connectionLost(self, reason):
        self.callback((True, reason))

    def logPrefix(self):
        return "Pipe"

    def doWrite(self):
        self.callback((False, None))


class PipeChannel(object):
    def __init__(self, pipe):
        self.pipe = pipe

    @_o
    def send(self, value):
        w = PipeForTwisted(self.pipe)
        eventloop.reactor.addWriter(w)
        lost, reason = yield w.callback
        eventloop.reactor.removeWriter(w)

        if lost:
            raise Exception("connection lost: %s" % reason)
        self.pipe.send(value)

    @_o
    def recv(self):
        r = PipeForTwisted(self.pipe)
        eventloop.reactor.addReader(r)
        lost, reason = yield r.callback
        eventloop.reactor.removeReader(r)

        if lost:
            raise Exception("connection lost: %s" % reason)
        yield Return(self.pipe.recv())


def launch_proc_with_pipes(target, *args, **kwargs):
    child, parent = Pipe()
    pc = PipeChannel(parent)
    p = launch_proc(target, pc, *args, **kwargs)
    cc = PipeChannel(child)
    return p, cc

########NEW FILE########
__FILENAME__ = http
# -*- coding: utf-8 -*-
#
# by Steven Hazel

import urlparse
import logging

from monocle import _o, Return, VERSION, launch, log_exception
from monocle.callback import Callback
from monocle.stack.network.http import HttpHeaders, HttpResponse, HttpRouter, write_request, read_response, extract_response
from monocle.twisted_stack.eventloop import reactor
from monocle.twisted_stack.network import Service, SSLService, Client, SSLClient

from twisted.internet import ssl
from twisted.internet.protocol import ClientCreator
from twisted.web import server, resource

log = logging.getLogger("monocle.twisted_stack.network.http")

class HttpException(Exception): pass


class _HttpServerResource(resource.Resource):
    isLeaf = 1

    def __init__(self, handler):
        self.handler = handler

    def render(self, request):
        @_o
        def _handler(request):
            try:
                value = yield self.handler(request)
                code, headers, content = extract_response(value)
            except Exception:
                log_exception()
                code, headers, content = 500, {}, "500 Internal Server Error"
            try:
                if request._disconnected:
                    return

                request.setResponseCode(code)
                headers.setdefault('Server', 'monocle/%s' % VERSION)
                grouped_headers = {}
                for name, value in headers.iteritems():
                    if name in grouped_headers:
                        grouped_headers[name].append(value)
                    else:
                        grouped_headers[name] = [value]
                for name, value in grouped_headers.iteritems():
                    request.responseHeaders.setRawHeaders(name, value)
                request.write(content)

                # close connections with a 'close' header
                if headers.get('Connection', '').lower() == 'close':
                    request.channel.persistent = False

                request.finish()
            except Exception:
                log_exception()
                raise
        _handler(request)
        return server.NOT_DONE_YET


class HttpServer(Service, HttpRouter):
    def __init__(self, port, handler=None, bindaddr="", backlog=128):
        HttpRouter.__init__(self)
        self.port = port
        self.handler = handler
        self.bindaddr = bindaddr
        self.backlog = backlog
        self._twisted_listening_port = None
        self.factory = server.Site(_HttpServerResource(self.handle_request))


class HttpsServer(SSLService, HttpRouter):
    def __init__(self, port, ssl_options, handler=None, bindaddr="", backlog=128):
        HttpRouter.__init__(self)
        self.port = port
        self.ssl_options = ssl_options
        self.handler = handler
        self.bindaddr = bindaddr
        self.backlog = backlog
        self._twisted_listening_port = None
        self.factory = server.Site(_HttpServerResource(self.handle_request))

########NEW FILE########
__FILENAME__ = utils
from twisted.python.failure import Failure
from twisted.internet.defer import Deferred

def cb_to_df(cb):
    df = Deferred()
    def call_deferred_back(v, df=df):
        if isinstance(v, Exception):
            df.errback(Failure(v, type(v), None))
        else:
            df.callback(v)
    cb.add(call_deferred_back)
    return df

########NEW FILE########
__FILENAME__ = util
import new

from monocle.stack.eventloop import queue_task
from monocle.callback import Callback

def sleep(seconds):
    cb = Callback()
    queue_task(seconds, cb, None)
    return cb

def monkeypatch(cls):
    def decorator(f):
        orig_method = None
        method = getattr(cls, f.func_name, None)
        if method:
            orig_method = lambda *a, **k: method(*a, **k)
        def g(*a, **k):
            return f(orig_method, *a, **k)
        g.func_name = f.func_name
        setattr(cls, f.func_name,
                new.instancemethod(g, None, cls))
    return decorator

########NEW FILE########
__FILENAME__ = helper
import functools
import os

INIT = os.environ.get('BACKEND', 'twisted')
HOST = '127.0.0.1'
PORT = 5555

import monocle
monocle.init(INIT)

from monocle.twisted_stack.utils import cb_to_df
from twisted.trial.unittest import TestCase

def o(f):
    oroutine = monocle._o(f)
    return functools.update_wrapper(
        lambda *a, **k: cb_to_df(oroutine(*a, **k)), oroutine)

########NEW FILE########
__FILENAME__ = test_callback
import helper

from monocle import callback


class TestCase(helper.TestCase):

    def setUp(self):
        self.calls = []

    def call(self, result):
        self.calls.append(result)


class CallbackTestCase(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.cb = callback.Callback()

    def test_result(self):
        self.assertFalse(hasattr(self.cb, 'result'))
        self.cb('ok')
        self.assertEqual(self.cb.result, 'ok')

    def test_add(self):
        self.assertEqual(self.cb._handlers, [])
        self.cb.add(self.call)
        self.assertEqual(self.cb._handlers, [self.cb])
        self.assertRaises(TypeError, cb.add, False)
        self.assertEqual(self.cb._handlers, [self.cb])
        self.assertEqual(self.calls, [])
        self.cb('ok')
        self.assertEqual(self.calls, ['ok'])
        cb.add(self.call)
        self.assertEqual(self.calls, ['ok', 'ok'])
        self.assertRaises(TypeError, cb.add, False)


class DeferTestCase(TestCase):

    def test_callback(self):
        cb = callback.defer('ok')
        self.assertTrue(isinstance(cb, callback.Callback))
        self.assertEqual(cb.result, 'ok')
        self.assertEqual(self.calls, [])
        cb.add(self.call)
        self.assertEqual(self.calls, ['ok'])

########NEW FILE########
__FILENAME__ = test_core
import helper

import monocle
from monocle import core


class ReturnTestCase(helper.TestCase):

    def test_none(self):
        r = core.Return()
        self.assertEqual(r.value, None)

    def test_single(self):
        r = core.Return('ok')
        self.assertEqual(r.value, 'ok')

    def test_multi(self):
        r = core.Return('one', 'two')
        self.assertEqual(r.value, ('one', 'two'))

########NEW FILE########
__FILENAME__ = test_experimental
import helper

from collections import deque
from monocle import experimental


class ChannelTestCase(helper.TestCase):

    def setUp(self):
        self.bufsize = 2
        self.ch = experimental.Channel(self.bufsize)

    @helper.o
    def test_send_recv(self):
        for x in range(2):
            yield self.ch.send('ok%s' % x)
        for x in range(2):
            r = yield self.ch.recv()
            self.assertEqual(r, 'ok%s' % x)

########NEW FILE########
__FILENAME__ = test_stack_network
import helper

from monocle import _o
from monocle.callback import Callback
from monocle.stack import eventloop, network
from monocle.util import sleep

EOL = '\r\n'


class StackConnection(object):

    def __init__(self):
        self.buffer = ""
        self.is_closed = False
        self.is_reading = False
        self.read_cb = Callback()
        self.connect_cb = Callback()
        self.out = []
        self.disconnect_called = 0
        self.resume_called = 0

    def disconnect(self):
        self.disconnect_called += 1

    def closed(self):
        return self.is_closed

    def reading(self):
        return self.is_reading

    def resume(self):
        self.resume_called += 1

    def write(self, data):
        self.out.append(data)


class ConnectionTestCase(helper.TestCase):

    def setUp(self):
        self.stack_conn = StackConnection()
        self.conn = network.Connection(stack_conn=self.stack_conn)

    @property
    def buffer(self):
        return self.stack_conn.buffer

    @buffer.setter
    def buffer(self, value):
        self.stack_conn.buffer = value

    @helper.o
    def test(self):
        data = 'ok'
        self.buffer = data
        r = yield self.conn.read(2)
        self.assertEqual(r, data)
        self.assertEqual(self.buffer, '')
        self.assertEqual(self.stack_conn.resume_called, 0)

    @helper.o
    def test_read_delay(self):
        data = 'ok'
        self.buffer = 'o'
        self.conn.timeout = 0.2
        def populate():
            self.buffer += 'k'
            self.stack_conn.read_cb(None)
        eventloop.queue_task(0.1, populate)
        r = yield self.conn.read(2)
        self.assertEqual(r, data)
        self.assertEqual(self.stack_conn.resume_called, 1)
        yield sleep(0.2)  # ensure timeout has expired

    @helper.o
    def test_read_timeout(self):
        self.conn.timeout = 0.1
        try:
            yield self.conn.read(10)
        except network.ConnectionLost:
            pass
        else:
            raise Exception('ConnectionLost should be raised')
        self.assertEqual(self.stack_conn.resume_called, 1)

    @helper.o
    def test_read_some(self):
        data = 'ok'
        self.buffer = data
        r = yield self.conn.read_some()
        self.assertEqual(r, data)
        self.assertEqual(self.buffer, '')
        self.assertEqual(self.stack_conn.resume_called, 0)

    @helper.o
    def test_read_some_delay(self):
        data = 'ok'
        self.conn.timeout = 0.2
        def populate():
            self.buffer = data
            self.stack_conn.read_cb(None)
        eventloop.queue_task(0.1, populate)
        r = yield self.conn.read_some()
        self.assertEqual(r, data)
        self.assertEqual(self.stack_conn.resume_called, 1)
        yield sleep(0.2)  # ensure timeout has expired

    @helper.o
    def test_read_some_timeout(self):
        self.conn.timeout = 0.1
        try:
            yield self.conn.read_some()
        except network.ConnectionLost:
            pass
        else:
            raise Exception('ConnectionLost should be raised')
        self.assertEqual(self.stack_conn.resume_called, 1)

    @helper.o
    def test_read_util(self):
        data = 'hello.'
        self.buffer = 'hello.world'
        r = yield self.conn.read_until('.')
        self.assertEqual(r, data)
        self.assertEqual(self.buffer, 'world')
        self.assertEqual(self.stack_conn.resume_called, 0)

    @helper.o
    def test_readline(self):
        data = 'hello\n'
        self.buffer = 'hello\nworld'
        r = yield self.conn.readline()
        self.assertEqual(r, data)
        self.assertEqual(self.buffer, 'world')
        self.assertEqual(self.stack_conn.resume_called, 0)


class ClientServerTestCase(helper.TestCase):

    def setUp(self):
        self.client = network.Client()
        self.service = network.Service(self.handler, bindaddr=helper.HOST, port=helper.PORT)
        network.add_service(self.service)

    def tearDown(self):
        try:
            self.client.close()
        except:
            pass
        try:
            self.service.stop()
        except:
            pass
        helper.TestCase.tearDown(self)

    @_o
    def handler(self, conn):
        while True:
            try:
                msg = yield conn.read_until(EOL)
            except network.ConnectionLost:
                break
            yield conn.write('you said: ' + msg.strip() + EOL)

    @helper.o
    def test_client(self):
        msg = 'ok'
        yield self.client.connect(helper.HOST, helper.PORT)
        yield self.client.write(msg + EOL)
        result = yield self.client.read_until(EOL)
        self.assertEqual(result, 'you said: ' + msg + EOL)

########NEW FILE########
__FILENAME__ = test_stack_network_http
import helper

from monocle import _o, Return
from monocle.stack import network
from monocle.stack.network import http


class ClientServerTestCase(helper.TestCase):

    def setUp(self):
        self.client = http.HttpClient()
        self.service = http.HttpServer(helper.PORT, handler=self.handler)
        network.add_service(self.service)

    def tearDown(self):
        try:
            self.client.close()
        except:
            pass
        try:
            self.service.stop()
        except:
            pass
        helper.TestCase.tearDown(self)

    @_o
    def handler(self, conn):
        data = 'Hello, World!'
        headers = http.HttpHeaders()
        headers.add('Content-Length', len(data))
        headers.add('Content-Type', 'text/plain')
        headers.add('Connection', 'close')
        yield Return(200, headers, data)

    @helper.o
    def test_client(self):
        yield self.client.connect(helper.HOST, helper.PORT)
        r = yield self.client.request('/')
        self.assertEqual(r.code, '200')  # should this be an int?

########NEW FILE########
__FILENAME__ = test_util
import helper

import time
from monocle import util


class SleepTestCase(helper.TestCase):

    @helper.o
    def test_simple(self):
        t = time.time()
        yield util.sleep(0.01)
        dt = time.time() - t
        self.assertTrue(dt > 0.005 and dt < 0.015)

########NEW FILE########
