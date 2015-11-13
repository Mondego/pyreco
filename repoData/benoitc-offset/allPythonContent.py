__FILENAME__ = buffered_channel
from offset import makechan, maintask, run


@maintask
def main():
    c = makechan(2)
    c.send(1)
    c.send(2)
    print(c.recv())
    print(c.recv())


if __name__ == "__main__":
    run()

########NEW FILE########
__FILENAME__ = demo_channel
# example inspired from http://tour.golang.org/#64

from offset import makechan, go, maintask, run

def sum(a, c):
    s = 0
    for v in a:
        s += v
    c.send(s)

@maintask
def main():
    a = [7, 2, 8, -9, 4, 0]

    c = makechan()
    go(sum, a[:int(len(a)/2)], c)
    go(sum, a[int(len(a)/2):], c)
    x, y = c.recv(), c.recv()

    print(x, y, x+y)

if __name__ == "__main__":
    run()

########NEW FILE########
__FILENAME__ = demo_goroutines
# inspired from http://tour.golang.org/#63


from offset import go, maintask, run
from offset import time

def say(s):
    for i in range(5):
        time.sleep(100 * time.MILLISECOND)
        print(s)

@maintask
def main():
    go(say, "world")
    say("hello")

if __name__ == "__main__":
    run()

########NEW FILE########
__FILENAME__ = demo_polling
from offset import go, maintask, run
from offset.net import sock


import signal
from offset.core import kernel
@maintask
def main():
    fd = sock.bind_socket("tcp", ('127.0.0.1', 0))
    print(fd.name())
    while True:
        fd1 = fd.accept()
        print("accepted %s" % fd1.name())
        fd1.write(b"ok\n")
        fd1.close()

run()

########NEW FILE########
__FILENAME__ = demo_select
# demo inspired from http://tour.golang.org/#67

from offset import makechan, select, go, run, maintask

def fibonacci(c, quit):
    x, y = 0, 1
    while True:
        ret = select(c.if_send(x), quit.if_recv())
        if ret == c.if_send(x):
            x, y = y, x+y
        elif ret == quit.if_recv():
            print("quit")
            return

@maintask
def main():
    c = makechan()
    quit = makechan()
    def f():
        for i in range(10):
            print(c.recv())

        quit.send(0)

    go(f)
    fibonacci(c, quit)

if __name__ == "__main__":
    run()

########NEW FILE########
__FILENAME__ = demo_select_buffered
from offset import *

def test(c, quit):
    x = 0
    while True:
        ret = select(c.if_send(x), quit.if_recv())
        if ret == c.if_send(x):
            x = x + 1
        elif ret == quit.if_recv():
            print("quit")
            return

@maintask
def main():
    c = makechan(5, label="c")
    quit = makechan(label="quit")
    def f():
        for i in range(5):
            print(c.recv())
        quit.send(0)

    go(f)
    test(c, quit)
run()

########NEW FILE########
__FILENAME__ = demo_signal
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from offset import makechan, run, maintask
from offset import os
from offset.os import signal
import sys

from offset.core.proc import current
from offset.core.kernel import kernel

@maintask
def main():
    print(current)
    c = makechan(1)
    signal.notify(c, os.SIGINT, os.SIGTERM, os.SIGQUIT)
    s = c.recv()
    print("got signal: %s" % s)
    print(kernel.runq)

run()
print("after run")
print(kernel.running)

########NEW FILE########
__FILENAME__ = demo_ticker
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from offset import run, maintask
from offset.time import Ticker, SECOND


@maintask
def main():
    ticker = Ticker(0.1 * SECOND)
    for i in range(3):
        print(ticker.c.recv())
    ticker.stop()

run()

########NEW FILE########
__FILENAME__ = chan
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from collections import deque
import random

from .context import Context
from .exc import ChannelError
from ..util import six
from . import proc


class bomb(object):
    def __init__(self, exp_type=None, exp_value=None, exp_traceback=None):
        self.type = exp_type
        self.value = exp_value
        self.traceback = exp_traceback

    def raise_(self):
        six.reraise(self.type, self.value, self.traceback)


class SudoG(object):

    def __init__(self, g, elem):
        self.g = g
        self.elem = elem


class scase(object):
    """ select case.

    op = 0 if recv, 1 if send, -1 if default
    """

    def __init__(self, op, chan, elem=None):
        self.op = op
        self.ch = chan
        self.elem = elem
        self.sg = None
        self.ok = True
        self.value = None

    def __str__(self):
        if self.op == 0:
            cas_str = "recv"
        elif self.op == 1:
            cas_str = "send"
        else:
            cas_str = "default"

        return "scase:%s %s(%s)" % (str(self.ch), cas_str,
                str(self.elem))

    @classmethod
    def recv(cls, chan):
        """ case recv

        in go: ``val  <- elem``
        """
        return cls(0, chan)

    @classmethod
    def send(cls, chan, elem):
        """ case send
-
        in go: ``chan <- elem``
        """
        return cls(1, chan, elem=elem)

    def __eq__(self, other):
        if other is None:
            return

        if self.elem is not None:
            return (self.ch == other.ch and self.op == other.op
                    and self.elem == other.elem)

        return self.ch == other.ch and self.op == other.op

    def __ne__(self, other):
        if other is None:
            return

        if self.elem is not None:
            return not (self.ch == other.ch and self.op == other.op
                    and self.elem == other.elem)

        return not(self.ch == other.ch and self.op == other.op)


class CaseDefault(scase):

    def __init__(self):
        self.op = - 1
        self.chan = None
        self.elem = None
        self.ch = None
        self.value = None
        self.sg = None


default = CaseDefault()


class Channel(object):

    def __init__(self, size=None, label=None):
        self.size = size or 0

        self._buf = None
        if self.size > 0:
            self._buf = deque()

        self.closed = False
        self.label = label

        self.recvq = deque() # list of receive waiters
        self.sendq = deque() # list of send waiters

    def __str__(self):
        if self.label is not None:
            return "<channel:%s>" % self.label
        return object.__str__(self)

    def close(self):
        self.closed = True

        # release all receivers
        while True:
            try:
                sg = self.recvq.popleft()
            except IndexError:
                break

            gp = sg.g
            gp.param = None
            gp.ready()

        # release all senders
        while True:
            try:
                sg = self.sendq.popleft()
            except IndexError:
                break

            gp = sg.g
            gp.param = None
            gp.ready()

    def open(self):
        self.closed = False

    def send(self, val):
        g = proc.current()

        if self.closed:
            raise ChannelError("send on a closed channel")

        if self.size > 0:
            # the buffer is full, wait until we can fill it
            while len(self._buf) >= self.size:
                mysg = SudoG(g, None)
                self.sendq.append(mysg)
                g.park()

            # fill the buffer
            self._buf.append(val)

            # eventually trigger a receiver
            sg = None
            try:
                sg = self.recvq.popleft()
            except IndexError:
                return

            if sg is not None:
                gp = sg.g
                gp.ready()

        else:
            sg = None
            # is the someone receiving?
            try:
                sg = self.recvq.popleft()
            except IndexError:
                pass

            if sg is not None:
                # yes, add the result and activate it
                gp = sg.g
                sg.elem = val
                gp.param = sg

                # activate the receive process
                gp.ready()
                return

            # noone is receiving, add the process to sendq and remove us from
            # the receive q
            mysg = SudoG(g, val)
            g.param = None
            self.sendq.append(mysg)
            g.park()

            if g.param is None:
                if not self.closed:
                    raise ChannelError("chansend: spurious wakeup")

    def recv(self):
        sg = None
        g = proc.current()

        if self.size > 0:
            while len(self._buf) <= 0:
                mysg = SudoG(g, None)
                self.recvq.append(mysg)
                g.park()

            val = self._buf.popleft()

            # thread safe way to recv on a buffered channel
            try:
                sg = self.sendq.popleft()
            except IndexError:
                pass

            if sg is not None:
                # yes someone is sending, unblock it and return the result
                gp = sg.g
                gp.ready()

                if sg.elem is not None:
                    self._buf.append(sg.elem)

            Context.instance().schedule()

            if isinstance(val, bomb):
                val.raise_()

            return val

        # sync recv
        try:
            sg = self.sendq.popleft()
        except IndexError:
            pass

        if sg is not None:
            gp = sg.g
            gp.param = sg
            gp.ready()

            if isinstance(sg.elem, bomb):
                sg.elem.raise_()

            return sg.elem

        # noone is sending, we have to wait. Append the current process to
        # receiveq, remove us from the run queue and switch
        mysg = SudoG(g, None)
        g.param = None
        self.recvq.append(mysg)
        g.park()

        if g.param is None:
            if not self.closed:
                raise ChannelError("chanrecv: spurious wakeup")
            return

        # we are back in the process, return the current value
        if isinstance(g.param.elem, bomb):
            g.param.elem.raise_()

        return g.param.elem

    def send_exception(self, exp_type, msg):
        self.send(bomb(exp_type, exp_type(msg)))

    def if_recv(self):
        return scase.recv(self)

    def if_send(self, elem):
        return scase.send(self, elem)


def select(*cases):
    """ A select function lets a goroutine wait on multiple
    communication operations.

    A select blocks until one of its cases can run, then it
    executes that case. It chooses one at random if multiple are ready"""

    # reorder cases


    c_ordered = [(i, cas) for i, cas in enumerate(cases)]
    random.shuffle(c_ordered)
    cases = [cas for _, cas in c_ordered]

    while True:
        # pass 1 - look for something already waiting
        for cas in cases:
            if cas.op == 0:
                # RECV
                if cas.ch.size > 0 and len(cas.ch._buf) > 0:
                    # buffered channel
                    cas.value = cas.ch._buf.popleft()

                    # dequeue from the sendq
                    sg = None
                    try:
                        sg = cas.ch.sendq.popleft()
                    except IndexError:
                        pass

                    if sg is not None:
                        gp = sg.g
                        gp.ready()

                    # return the case
                    return cas
                else:
                    #
                    sg = None
                    try:
                        sg = cas.ch.sendq.popleft()
                    except IndexError:
                        pass

                    if sg is not None:
                        gp = sg.g
                        gp.param = sg
                        gp.ready()
                        cas.elem = sg.elem
                        return cas

                    if cas.ch.closed:
                        return

            elif cas.op == 1:
                if cas.ch.closed:
                    return

                # SEND
                if cas.ch.size > 0 and len(cas.ch._buf) < cas.ch.size:
                    # buffered channnel, we can fill the buffer
                    cas.ch._buf.append(cas.elem)

                    # eventually trigger a receiver
                    sg = None
                    try:
                        sg = cas.ch.recvq.popleft()
                    except IndexError:
                        pass

                    if sg is not None:
                        gp = sg.g
                        gp.ready()

                    # return
                    return cas
                else:
                    sg = None
                    try:
                        sg = cas.ch.recvq.popleft()
                    except IndexError:
                        pass

                    if sg is not None:
                        gp = sg.g
                        sg.elem = cas.elem
                        gp.param = sg
                        gp.ready()
                        return cas
            else:
                # default case
                return cas

        # pass 2 - enqueue on all channels
        g = proc.current()
        g.param = None
        g.sleeping = True
        for cas in cases:
            sg = SudoG(g, cas.elem)
            cas.sg = sg
            if cas.op == 0:
                cas.ch.recvq.append(sg)
            else:
                cas.ch.sendq.append(sg)

        # sleep until a communication happen
        g.park()

        sg = g.param

        # pass 3 - dequeue from unsucessful channels
        # to not iddle in them
        selected = None
        for cas in cases:
            if cas.sg != sg:
                try:
                    if cas.op == 0:
                        cas.ch.recvq.remove(cas.sg)
                    else:
                        cas.ch.sendq.remove(cas.sg)
                except ValueError:
                    pass
            else:
                selected = cas

        if sg is None:
            continue

        if selected.ch.size > 0:
            raise RuntimeError("select shouldn't happen")

        if selected.op == 0:
            selected.value = sg.elem

        return selected

def makechan(size=None, label=None):
    return Channel(size=size, label=label)

########NEW FILE########
__FILENAME__ = context
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from collections import deque
from concurrent import futures
import sys
import threading

try:
    import thread  # py2
except ImportError:
    import _thread as thread  # py3

from .exc import KernelError
from . import proc
from .util import getmaxthreads


# increase the recursion limit
sys.setrecursionlimit(1000000)


class Context(object):

    _instance_lock = threading.Lock()

    def __init__(self):
        self.runq = deque()
        self.running = deque()
        self.sleeping = {}
        self.lock = threading.Lock()
        self._thread_ident = None
        self._run_calls = []

        # initialize the thread executor pool used for background processing
        # like syscall
        self.maxthreads = getmaxthreads()
        self.tpool = futures.ThreadPoolExecutor(self.maxthreads)

    @staticmethod
    def instance():
        """Returns a global `Context` instance.
        """
        if not hasattr(Context, "_instance"):
            with Context._instance_lock:
                if not hasattr(Context, "_instance"):
                    # New instance after double check
                    Context._instance = Context()
        return Context._instance

    def newproc(self, func, *args, **kwargs):
        # wrap the function so we know when it ends
        # create the coroutine
        g = proc.Proc(self, func, args, kwargs)
        # add the coroutine at the end of the runq
        self.runq.append(g)
        # register the goroutine
        self.running.append(g)
        # return the coroutine
        return g

    def removeg(self, g=None):
        # get the current proc
        g = g or proc.current()
        # remove it from the run queue
        try:
            self.runq.remove(g)
        except ValueError:
            pass

        # unregister the goroutine
        try:
            self.running.remove(g)
        except ValueError:
            pass

    def park(self, g=None):
        g = g or proc.current()
        g.sleeping = True
        try:
            self.runq.remove(g)
        except ValueError:
            pass
        self.schedule()

    def ready(self, g):
        if not g.sleeping:
            raise KernelError("bad goroutine status")

        g.sleeping = False
        self.runq.append(g)

    def schedule(self):
        gcurrent = proc.current()

        while True:
            gnext = None
            if len(self.runq):
                if self.runq[0] == gcurrent:
                    self.runq.rotate(-1)
                gnext = self.runq[0]
            elif len(self.sleeping) > 0:
                self.wait_syscalls(0.05)
                continue
            elif self._run_calls:
                gnext = self._run_calls.pop(0)

            if not gnext:
                return

            # switch
            self._last_task = gnext
            if gnext != gcurrent:
                gnext.switch()

            if gcurrent == self._last_task:
                return

    def run(self):
        # append the run to the run calls
        self._run_calls.append(proc.current())
        # set current thread
        self._thread_ident = thread.get_ident()
        # start scheduling
        self.schedule()

    def stop(self):
        # kill all running goroutines
        while True:
            try:
                p = self.running.popleft()
            except IndexError:
                break

            p.terminate()

        # stop the pool
        self.tpool.shutdown(wait=False)

    def wait_syscalls(self, timeout):
        with self.lock:
            fs = [f for f in self.sleeping]

        futures.wait(fs, timeout, return_when=futures.FIRST_COMPLETED)

    def enter_syscall(self, fn, *args, **kwargs):
        # get current coroutine
        gt = proc.current()
        gt.sleeping = True

        # init the futures
        f = self.tpool.submit(fn, *args, **kwargs)

        # add the goroutine to sleeping functions
        with self.lock:
            self.sleeping[f] = gt

        f.add_done_callback(self.exit_syscall)

        # schedule, switch to another coroutine
        self.park()

        if f.exception() is not None:
            raise f.exception()
        return f.result()

    def exit_syscall(self, f):
        # get the  goroutine associated to this syscall
        with self.lock:
            g = self.sleeping.pop(f)

        # we exited
        if f.cancelled():
            return

        if not g.is_alive():
            return

        g.sleeping = False

        # put the goroutine back at the top of the running queue
        self.runq.appendleft(g)


def park():
    g = proc.current()
    g.park()

def ready(g):
    g.ready(g)

def enter_syscall(fn, *args, **kwargs):
    ctx = Context.instance()
    return ctx.enter_syscall(fn, *args, **kwargs)

########NEW FILE########
__FILENAME__ = exc
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


class PanicError(Exception):
    """ panic error raised """

class ChannelError(Exception):
    """ excption raised on channel error """

class KernelError(Exception):
    """ unexpected error in the kernel """

########NEW FILE########
__FILENAME__ = kernel
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from concurrent import futures
from collections import deque
import signal
import sys
import time

from .context import Context
from .sigqueue import SigQueue

# increase the recursion limit
sys.setrecursionlimit(1000000)

class Kernel(object):

    def __init__(self):

        # we have for now only one context
        self.ctx = Context.instance()

        # init signals
        self.init_signals()


        # init signal global queue used to handle all signals from the
        # app
        self.sig_queue = SigQueue(self)

    def init_signals(self):
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)

    def handle_quit(self, *args):
        self.ctx.stop()

    def run(self):
        self.ctx.run()

    def signal_enable(self, sig):
        self.sig_queue.signal_enable(sig)

    def signal_disable(self, sig):
        self.sig_queue.signal_disable(sig)

    def signal_recv(self, s):
        self.sig_queue.signal_recv(s)

        def callback():
            while True:
                if s.value != 0:
                    return s.value
                time.sleep(0.05)

        return self.ctx.enter_syscall(callback)


kernel = Kernel()
run = kernel.run


signal_enable = kernel.signal_enable
signal_disable = kernel.signal_disable
signal_recv = kernel.signal_recv

########NEW FILE########
__FILENAME__ = proc
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import threading
import time

try:
    import fibers
except ImportError:
    raise RuntimeError("Platform not supported")

_tls = threading.local()


class ProcExit(Exception):
    """ exception raised when the proc is asked to exit """

def current():
    try:
        return _tls.current_proc
    except AttributeError:
        _create_main_proc()
        return _tls.current_proc


class Proc(object):

    def __init__(self, m, func, args, kwargs):

        def _run():
            _tls.current_proc = self
            self._is_started = 1
            try:
                return func(*args, **kwargs)
            except ProcExit:
                pass
            finally:
                m.removeg()

        self.m = m
        self.fiber = fibers.Fiber(_run)
        self.waiting = False
        self.sleeping = False
        self.param = None
        self._is_started = 0

    def switch(self):
        curr = current()
        try:
            self.fiber.switch()
        finally:
            _tls.current_proc = curr

    def throw(self, *args):
        curr = current()
        try:
            self.fiber.throw(*args)
        finally:
            _tls.current_proc = curr

    def park(self):
        self.m.park(self)

    def ready(self):
        self.m.ready(self)

    def is_alive(self):
        return self._is_started < 0 or self.fiber.is_alive()

    def terminate(self):
        self.throw(ProcExit, ProcExit("exit"))
        time.sleep(0.1)

    def __eq__(self, other):
        return self.fiber == other.fiber


def _create_main_proc():
    main_proc = Proc.__new__(Proc)
    main_proc.fiber = fibers.current()
    main_proc._is_started = True
    main_proc.sleeping = True

    _tls.main_proc = main_proc
    _tls.current_proc = main_proc

########NEW FILE########
__FILENAME__ = sigqueue
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


from collections import deque
import copy
import signal
import threading
import weakref


NUMSIG=65

class SigQueue(object):

    def __init__(self, kernel):
        self.kernel = kernel
        self.queue = deque()
        self.receivers = []
        self.lock = threading.Lock()

        self.sigtable = {}
        for i in range(NUMSIG):
            self.sigtable[i] = 0

    def signal_enable(self, sig):
        with self.lock:
            if not self.sigtable[sig]:
                signal.signal(sig, self.signal_handler)

            self.sigtable[sig] += 1


    def signal_disable(self, sig):
        with self.lock:
            if self.sigtable[sig] == 0:
                return

            self.sigtable[sig] -= 1

            if self.sigtable[sig] == 0:
                signal.signal(sig, signal.SIG_DFL)

    def signal_recv(self, s):
        with self.lock:
            self.receivers.append(s)

    def signal_handler(self, sig, frame):
        with self.lock:
            receivers = copy.copy(self.receivers)
            self.receivers = []

        for recv in receivers:
            recv.value = sig

########NEW FILE########
__FILENAME__ = timer
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import heapq
import operator
import threading

from ..util import six

from .context import Context, park, enter_syscall
from . import proc
from .util import nanotime, nanosleep


def _ready(now, t, g):
    g.ready()


def sleep(d):
    g = proc.current()
    g.sleeping = True
    t = Timer(_ready, interval=d, args=(g,))
    t.start()
    g.park()


class Timer(object):

    def __init__(self, callback, interval=None, period=None, args=None,
            kwargs=None):
        if not six.callable(callback):
            raise ValueError("callback must be a callable")

        self.callback = callback
        self.interval = interval
        self.period = period
        self.args = args or []
        self.kwargs = kwargs or {}
        self.when = 0
        self.active = False

    def start(self):
        global timers
        self.active = True
        if not self.when:
            self.when = nanotime() + self.interval
        add_timer(self)

    def stop(self):
        remove_timer(self)
        self.active = False

    def __lt__(self, other):
        return self.when < other.when

    __cmp__ = __lt__


class Timers(object):

    __slots__ = ['__dict__', '_lock', 'sleeping']

    __shared_state__ = dict(
            _timers = {},
            _heap = [],
            _timerproc = None
    )

    def __init__(self):
        self.__dict__ = self.__shared_state__
        self._lock = threading.RLock()
        self.sleeping = False
        self.rescheduling = False

    def add(self, t):
        with self._lock:
            self._add_timer(t)

            if self.sleeping:
                self.sleeping = False
                self._timerproc.ready()

            if self._timerproc is None or not self._timerproc.is_alive:
                self._timerproc = Context.instance().newproc(self.timerproc)

    def _add_timer(self, t):
        if not t.interval:
            return
        heapq.heappush(self._heap, t)

    def remove(self, t):
        with self._lock:
            try:
                del self._heap[operator.indexOf(self._heap, t)]
            except (KeyError, IndexError):
                pass

    def timerproc(self):
        while True:
            self._lock.acquire()
            now = nanotime()

            while True:
                if not len(self._heap):
                    delta = -1
                    break

                t = heapq.heappop(self._heap)
                delta = t.when - now
                if delta > 0:
                    heapq.heappush(self._heap, t)
                    break
                else:
                    # repeat ? reinsert the timer
                    if t.period is not None and t.period > 0:
                        np = t.period
                        t.when += np * (1 - delta/np)
                        heapq.heappush(self._heap, t)

                    # run
                    self._lock.release()
                    t.callback(now, t, *t.args, **t.kwargs)
                    self._lock.acquire()

            if delta < 0:
                self.sleeping = True
                self._lock.release()
                park()
            else:
                self._lock.release()
                # one time is pending sleep until
                enter_syscall(nanosleep, delta)


timers = Timers()
add_timer = timers.add
remove_timer = timers.remove

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import multiprocessing
import os
import time


def getmaxthreads():
    if 'OFFSET_MAX_THREADS' in os.environ:
        return int(os.environ['OFFSET_MAX_THREADS'])

    n = 0
    try:
        n = multiprocessing.cpu_count()
    except NotImplementedError:
        pass

    # use a minimum of 2 threads
    return max(n, 2)

def nanotime(s=None):
    """ convert seconds to nanoseconds. If s is None, current time is
    returned """
    if s is not None:
        return s * 1000000000
    return time.time() * 1000000000

def from_nanotime(n):
    """ convert from nanotime to seconds """
    return n / 1.0e9


# TODO: implement this function with libc nanosleep function when
# available.
def nanosleep(n):
    time.sleep(from_nanotime(n))

########NEW FILE########
__FILENAME__ = dial
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.



########NEW FILE########
__FILENAME__ = exc
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


class Timeout(Exception):
    """ error raised when a timeout happen """

class FdClosing(Exception):
    """ Error raised while trying to achieve an FD closing """

########NEW FILE########
__FILENAME__ = fd
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


_os = __import__('os')

import errno

from .. import os
from .. import syscall
from ..syscall import socket
from ..sync import Mutex
from ..time import sleep

from .fd_pollserver import PollDesc
from .exc import FdClosing


class NetFd(object):

    def __init__(self, sock, familly, sotype, net):
        self.sysfd = sock.fileno()
        self.familly = familly
        self.sotype = sotype
        self.net = net

        # socket object
        self.sock = sock
        #_os.close(fd)

        self.pd = PollDesc(self)

        self.closing = False
        self.isConnected = False
        self.rio = Mutex()
        self.wio = Mutex()
        self.sysmu = Mutex()
        self.sysref = 0
        self.addr = None
        self.sysfile = None

    def name(self):
        return "%s: %s -> %s" % (self.net, self.addr[0], self.addr[1])

    def setaddr(self, addr):
        self.addr = addr

    def connect(self, address):
        with self.wio:
            self.pd.prepare_write()
            while True:
                try:
                    self.sock.connect(address)
                except socket.error as e:
                    if e.args[0] == errno.EISCONN:
                        break
                    if e.args[0] not in (errno.EINPROGRESS, errno.EALREADY,
                            errno.EINTR,):
                        raise

                    self.pd.wait_write()
                    continue

                break

            self.isConnected = True

    def incref(self, closing=False):
        with self.sysmu:
            if self.closing:
                raise FdClosing()

            self.sysref += 1
            if closing:
                self.closing = True

    def decref(self):
        with self.sysmu:
            self.sysref -= 1
            if self.closing and self.sysref == 0:
                self.pd.close()

                # close the socket
                self.sock.close()
                self.sysfd = -1

    def close(self):
        self.pd.lock()
        try:
            self.incref(True)
            self.pd.evict()
        finally:
            self.pd.unlock()

        self.decref()

    def shutdown(self, how):
        self.incref()

        try:
            self.sock.shutdown(how)
        finally:
            self.decref()

    def close_read(self):
        self.shutdown(socket.SHUT_RD)

    def close_write(self):
        self.shutdown(socket.SHUT_WR)

    def read(self, n):
        with self.rio:
            self.incref()
            try:
                self.pd.prepare_read()
                while True:
                    try:
                        return self.sock.recv(n)
                    except socket.error as e:
                        if e.args[0] == errno.EAGAIN:
                            self.pd.wait_read()
                            continue
                        else:
                            raise
            finally:
                self.decref()

    def readfrom(self, n, *flags):
        with self.rio:
            self.incref()
            try:
                self.pd.prepare_read()
                while True:
                    try:
                        return self.sock.recvfrom(n, **flags)
                    except socket.error as e:
                        if e.args[0] == errno.EAGAIN:
                            self.pd.wait_read()
                            continue
                        else:
                            raise
            finally:
                self.decref()


    if hasattr(socket, 'recvmsg'):
        def readmsg(self, p, oob):
            with self.rio:
                self.incref()
                try:
                    self.pd.prepare_read()
                    while True:
                        try:
                            return self.sock.recvmsg(p, oob, 0)
                        except socket.error as e:
                            if e.args[0] == errno.EAGAIN:
                                self.pd.wait_read()
                                continue
                            else:
                                raise
                finally:
                    self.decref()


    def write(self, data):
        with self.wio:
            self.incref()
            try:
                self.pd.prepare_write()
                while True:
                    try:
                        return self.sock.send(data)
                    except socket.error as e:
                        if e.args[0] == errno.EAGAIN:
                            self.pd.wait_write()
                            continue
                        else:
                            raise
            finally:
                self.decref()

    def writeto(self, data, addr):
        with self.wio:
            self.incref()
            try:
                self.pd.prepare_write()
                while True:
                    try:
                        return self.sock.sendto(data, addr)
                    except socket.error as e:
                        if e.args[0] == errno.EAGAIN:
                            self.pd.wait_write()
                            continue
                        else:
                            raise
            finally:
                self.decref()

    if hasattr(socket, 'sendmsg'):
        def writemsg(self, p, oob, addr):
            with self.wio:
                self.incref()
                try:
                    self.pd.prepare_write()
                    while True:
                        try:
                            return self.sock.sendmsg(p, oob, 0, addr)
                        except socket.error as e:
                            if e.args[0] == errno.EAGAIN:
                                self.pd.wait_write()
                                continue
                            else:
                                raise
                finally:
                    self.decref()


    def accept(self):
        with self.rio:
            self.incref()
            try:
                self.pd.prepare_read()
                while True:
                    try:
                        fd, addr = accept(self.sock)
                    except socket.error as e:
                        if e.args[0] == errno.EAGAIN:
                            self.pd.wait_read()
                            continue
                        elif e.args[0] == errno.ECONNABORTED:
                            continue
                        else:
                            raise

                    break

                cls = self.__class__
                obj = cls(fd, self.familly, self.sotype,
                        self.net)
                obj.setaddr(addr)
                return obj
            finally:
                self.decref()

    def dup(self):
        syscall.ForkLock.rlock()
        try:
            fd = _os.dup(self.sock.fileno())
            syscall.closeonexec(fd)

        finally:
            syscall.ForkLock.runlock()

        syscall.setnonblock(fd)
        return os.File(fd, self.name())


def accept(sock):
    conn, addr = sock.accept()
    syscall.ForkLock.rlock()
    try:
        syscall.closeonexec(conn.fileno())

    finally:
        syscall.ForkLock.runlock()

    conn.setblocking(0)
    return conn, addr

########NEW FILE########
__FILENAME__ = fd_bsd
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import errno
import sys

from .util import fd_
from .. import syscall
from ..syscall import select

if not hasattr(select, "kqueue"):
    raise RuntimeError('kqueue is not supported')


class Pollster(object):

    def __init__(self):
        self.kq = select.kqueue()
        syscall.closeonexec(self.kq.fileno())
        self.events = []

    def addfd(self, fd, mode, repeat=True):
        if mode == 'r':
            kmode = select.KQ_FILTER_READ
        else:
            kmode = select.KQ_FILTER_WRITE

        flags = select.KQ_EV_ADD

        if sys.platform.startswith("darwin"):
            flags |= select.KQ_EV_ENABLE

        if not repeat:
            flags |= select.KQ_EV_ONESHOT

        ev = select.kevent(fd_(fd), kmode, flags)
        self.kq.control([ev], 0)

    def delfd(self, fd, mode):
        if mode == 'r':
            kmode = select.KQ_FILTER_READ
        else:
            kmode = select.KQ_FILTER_WRITE

        ev = select.kevent(fd_(fd), select.KQ_FILTER_READ,
                select.KQ_EV_DELETE)
        self.kq.control([ev], 0)

    def waitfd(self, pollserver, nsec=0):
        while len(self.events) == 0:
            pollserver.unlock()
            try:
                events = self.kq.control(None, 0, nsec)
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise
            finally:
                pollserver.lock()

            self.events.extend(events)

        ev = self.events.pop(0)
        if ev.filter == select.KQ_FILTER_READ:
            mode = 'r'
        else:
            mode = 'w'

        return (fd_(ev.ident), mode)

    def close(self):
        self.kq.close()

########NEW FILE########
__FILENAME__ = fd_epoll
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import errno

from .util import fd_
from .. import syscall
from ..syscall import select


if not hasattr(select, "epoll"):
    raise RuntimeError("epoll is not supported")


class Pollster(object):

    def __init__(self):
        self.poll = select.epoll()
        syscall.closeonexec(self.poll.fileno())
        self.fds = {}
        self.events = []

    def addfd(self, fd, mode, repeat=True):
        if mode == 'r':
            mode = (select.EPOLLIN, repeat)
        else:
            mode = (select.EPOLLOUT, repeat)

        if fd in self.fds:
            modes = self.fds[fd]
            if mode in self.fds[fd]:
                # already registered for this mode
                return
            modes.append(mode)
            addfd_ = self.poll.modify
        else:
            modes = [mode]
            addfd_ = self.poll.register

        # append the new mode to fds
        self.fds[fd] = modes

        mask = 0
        for mode, r in modes:
            mask |= mode

        if not repeat:
            mask |= select.EPOLLONESHOT

        addfd_(fd, mask)

    def delfd(self, fd, mode):
        if mode == 'r':
            mode = select.POLLIN | select.POLLPRI
        else:
            mode = select.POLLOUT

        if fd not in self.fds:
            return

        modes = []
        for m, r in self.fds[fd]:
            if mode != m:
                modes.append((m, r))

        if not modes:
            # del the fd from the poll
            self.poll.unregister(fd)
            del self.fds[fd]
        else:
            # modify the fd in the poll
            self.fds[fd] = modes
            m, r = modes[0]
            mask = m[0]
            if r:
                mask |= select.EPOLLONESHOT

            self.poll.modify(fd, mask)

    def waitfd(self, pollserver, nsec=0):
        # wait for the events
        while len(self.events) == 0:
            pollserver.unlock()
            try:
                events = self.poll.poll(nsec)
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise
            finally:
                pollserver.lock()

            self.events.extend(events)

        (fd, ev) = self.events.pop(0)
        fd = fd_(fd)

        if ev == select.EPOLLIN:
            mode = 'r'
        else:
            mode = 'w'

        # eventually remove the mode from the list if repeat was set to
        # False and modify the poll if needed.
        modes = []
        for m, r in self.fds[fd]:
            if not r:
                continue
            modes.append(m, r)

        if modes != self.fds[fd]:
            self.fds[fd] = mode

            mask = 0
            for m, r in modes:
                mask |= m

            self.poll.modify(fd, mask)

        return (fd_(fd), mode)

    def close(self):
        self.poll.close()

########NEW FILE########
__FILENAME__ = fd_poll
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .fd_poll_base import PollerBase
from ..syscall import select

if hasattr(select, "devpoll"):
    # solaris

    class Pollster(PollerBase):
        POLL_IMPL = select.devpoll

elif hasattr(select, "poll"):
    # other posix system supporting poll
    class Pollster(PollerBase):
        POLL_IMPL = select.poll
else:
    raise RuntimeError("poll is not supported")

########NEW FILE########
__FILENAME__ = fd_pollserver
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import errno

from .. import os
from ..core import go, makechan
from ..core.util import getmaxthreads
from ..syscall import select
from ..syscall import fexec
from ..sync import Mutex, Once
from ..time import nano

from .exc import Timeout
from .util import Deadline


if hasattr(select, "kqueue"):
    from .fd_bsd import Pollster
elif hasattr(select, "epoll"):
    from .fd_epoll import Pollster
elif hasattr(select, "poll") or hasattr(select, "devpoll"):
    from .fd_poll import Pollster
else:
    from .fd_select import Pollster


class PollServer(object):

    def __init__(self):
        self.m = Mutex()

        self.poll = Pollster()

        self.pr, self.pw = os.pipe()
        fexec.setnonblock(self.pr)
        fexec.setnonblock(self.pw)
        self.poll.addfd(self.pr, 'r')

        self.pending = {}
        self.deadline = 0

        go(self.run)

    def lock(self):
        self.m.lock()

    def unlock(self):
        self.m.unlock()

    def addfd(self, pd, mode):
        self.lock()
        if pd.sysfd < 0 or pd.closing:
            self.unlock()
            raise ValueError("fd closing")

        key = pd.sysfd << 1
        t = 0
        if mode == 'r':
            pd.ncr += 1
            t = pd.rdeadline.value
        else:
            pd.ncw += 1
            key += 1
            t = pd.wdeadline.value

        self.pending[key] = pd
        do_wakeup = False
        if t > 0 and (self.deadline == 0 or self.deadline < t):
            self.deadline = t
            do_wakeup = True

        self.poll.addfd(pd.sysfd, mode, False)
        self.unlock()

        if do_wakeup:
            self.wakeup()

    def evict(self, pd):
        pd.closing = True

        try:
            if self.pending[pd.sysfd << 1] == pd:
                self.wakefd(pd, 'r')
                self.poll.delfd(pd.sysfd)
                del self.pending[pd.sysfd << 1]
        except KeyError:
            pass

        try:
            if self.pending[pd.sysfd << 1 | 1]:
                self.wakefd(pd, 'w')
                self.poll.delfd(pd.sysfd, 'w')
                del self.pending[pd.sysfd << 1 | 1]
        except KeyError:
            pass

    def wakeup(self):
        self.pw.write(b'.')

        try:
            os.write(self.pw, b'.')
        except IOError as e:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise

    def lookupfd(self, fd, mode):
        key = fd << 1
        if mode == 'w':
           key += 1

        try:
            netfd = self.pending.pop(key)
        except KeyError:
            return None

        return netfd

    def wakefd(self, pd, mode):
        if mode == 'r':
            while pd.ncr > 0:
                pd.ncr -= 1
                pd.cr.send(True)
        else:
            while pd.ncw > 0:
                pd.ncw -= 1
                pd.cw.send(True)

    def check_deadline(self):
        now = nano()

        next_deadline = 0
        pending = self.pending.copy()
        for key, pd in pending.items():
            if key & 1 == 0:
                mode = 'r'
            else:
                mode = 'w'

            if mode == 'r':
                t = pd.rdeadline.value()
            else:
                t = pd.wdeadline.value()

            if t > 0:
                if t <= now:
                    del self.pending[key]
                    self.poll.delfd(pd.sysfd, mode)
                    self.wakefd(pd, mode)
                elif next_deadline == 0 or t < next_deadline:
                    next_deadline = t

        self.deadline = next_deadline

    def run(self):
        self.lock()
        try:
            while True:
                timeout = 0.1
                if self.deadline > 0:
                    timeout = self.deadline - nano()
                    if timeout <= 0:
                        self.check_deadline()
                        continue

                fd, mode = self.poll.waitfd(self, timeout)
                if fd < 0:
                    self.check_deadline()
                    continue

                if fd == self.pr.fileno():
                    os.read(self.pr, 1)
                    self.check_deadline()

                else:
                    pd = self.lookupfd(fd, mode)
                    if not pd:
                        continue
                    self.wakefd(pd, mode)
        finally:
            self.unlock()


pollservers = {}
startserveronce = Once()

@startserveronce.do
def startservers():
    global pollservers

    for i in range(getmaxthreads()):
        pollservers[i] = PollServer()


class PollDesc(object):

    def __init__(self, fd):

        # init pollservers
        startservers()

        polln = len(pollservers)
        k = fd.sysfd % polln
        self.sysfd = fd.sysfd
        self.pollserver = pollservers[k]

        self.cr = makechan(1)
        self.cw = makechan(1)
        self.ncr = 0
        self.ncw = 0
        self.rdeadline = Deadline()
        self.wdeadline = Deadline()

    def close(self):
        pass

    def lock(self):
        self.pollserver.lock()

    def unlock(self):
        self.pollserver.unlock()

    def wakeup(self):
        self.pollserver.wakeup()

    def prepare_read(self):
        if self.rdeadline.expired():
            raise Timeout

    def prepare_write(self):
        if self.wdeadline.expired():
            raise Timeout

    def wait_read(self):
        self.pollserver.addfd(self, 'r')
        return self.cr.recv()

    def wait_write(self):
        self.pollserver.addfd(self, 'w')
        return self.cw.recv()

    def evict(self):
        return self.pollserver.evict(self)

########NEW FILE########
__FILENAME__ = fd_poll_base
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import errno

from .util import fd_
from .. import syscall
from ..syscall import select

class PollerBase(object):

    POLL_IMPL = None

    def __init__(self):
        self.poll = self.POLL_IMPL()
        self.fds = {}
        self.events = []

    def addfd(self, fd, mode, repeat=True):
        fd = fd_(fd)
        if mode == 'r':
            mode = (select.POLLIN, repeat)
        else:
            mode = (select.POLLOUT, repeat)

        if fd in self.fds:
            modes = self.fds[fd]
            if mode in modes:
                # already registered for this mode
                return
            modes.append(mode)
            addfd_ = self.poll.modify
        else:
            modes = [mode]
            addfd_ = self.poll.register

        # append the new mode to fds
        self.fds[fd] = modes

        mask = 0
        for mode, r in modes:
            mask |= mode

        addfd_(fd, mask)

    def delfd(self, fd, mode):
        fd = fd_(fd)

        if mode == 'r':
            mode = select.POLLIN | select.POLLPRI
        else:
            mode = select.POLLOUT

        if fd not in self.fds:
            return

        modes = []
        for m, r in self.fds[fd]:
            if mode != m:
                modes.append((m, r))

        if not modes:
            # del the fd from the poll
            self.poll.unregister(fd)
            del self.fds[fd]
        else:
            # modify the fd in the poll
            self.fds[fd] = modes
            m, r = modes[0]
            mask = m[0]
            self.poll.modify(fd, mask)

    def waitfd(self, pollserver, nsec=0):
        # wait for the events
        while len(self.events) == 0:
            pollserver.unlock()
            try:
                events = self.poll.poll(nsec)
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise
            finally:
                pollserver.lock()

            self.events.extend(events)

        (fd, ev) = self.events.pop(0)
        fd = fd_(fd)

        if fd not in self.fds:
            return None, None


        if ev == select.POLLIN or ev == select.POLLPRI:
            mode = 'r'
        else:
            mode = 'w'

        # eventually remove the mode from the list if repeat was set to
        # False and modify the poll if needed.
        modes = []
        for m, r in self.fds[fd]:
            if not r:
                continue
            modes.append(m, r)

        if not modes:
            self.poll.unregister(fd)
        else:
            mask = 0
            if modes != self.fds[fd]:
                mask |= m
                self.poll.modify(fd, mask)

        return (fd_(fd), mode)

    def close(self):
        for fd in self.fds:
            self.poll.unregister(fd)

        self.fds = []
        self.poll = None

########NEW FILE########
__FILENAME__ = fd_select
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import errno

from .util import fd_
from ..syscall import select


class Pollster(object):

    def __init__(self):
        self.read_fds = {}
        self.write_fds = {}
        self.events = []

    def addfd(self, fd, mode, repeat=True):
        fd = fd_(fd)

        if mode == 'r':
            self.read_fds[fd] = repeat
        else:
            self.write_fds[fd] = repeat

    def delfd(self, fd, mode):
        if mode == 'r' and fd in self.read_fds:
            del self.read_fds[fd]
        elif fd in self.write_fds:
            del self.write_fds[fd]

    def waitfd(self, pollserver, nsec):
        read_fds = [fd for fd in self.read_fds]
        write_fds = [fd for fd in self.write_fds]

        while len(self.events) == 0:
            pollserver.unlock()
            try:
                r, w, e = select.select(read_fds, write_fds, [], nsec)
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise
            finally:
                pollserver.lock()

            events = []
            for fd in r:
                if fd in self.read_fds:
                    if self.read_fds[fd] == False:
                        del self.read_fds[fd]
                    events.append((fd, 'r'))

            for fd in w:
                if fd in self.write_fds:
                    if self.write_fds[fd] == False:
                        del self.write_fds[fd]
                    events.append((fd, 'w'))

            self.events.extend(events)

        return self.evens.pop(0)

    def close(self):
        self.read_fds = []
        self.write_fds = []

########NEW FILE########
__FILENAME__ = sock

import sys

from ..syscall import socket

try:
    from ..syscall.sysctl import sysctlbyname
    from ctypes import c_int
except ImportError:
    sysctlbyname = None

from .fd import NetFd
from . import util

def maxListenerBacklog():
    if sys.platform.startswith('linux'):
        try:
            f = open("/proc/sys/net/core/somaxconn")
        except OSError:
            return socket.SOMAXCONN

        try:
            n = int(f.read().split('\n')[0])
        except ValueError:
            return socket.SOMAXCONN

        if n > 1<<16-1:
            n = 1<<16 - 1

        return n
    elif sysctlbyname is not None:
        n = 0
        if (sys.platform.startswith('darwin') or
                sys.platform.startswith('freebsd')):
            n = sysctlbyname('kern.ipc.somaxconn', c_int)
        elif sys.platform.startswith('openbsd'):
            n = sysctlbyname('kern.somaxconn', c_int)

        if n == 0:
            return socket.SOMAXCONN

        if n > 1<<16-1:
            n = 1<<16-1

        return n
    else:
        return socket.SOMAXCONN

# return a bounded socket
def bind_socket(net, addr):
    if net == "tcp" or net == "udp":
        if util.is_ipv6(addr[0]):
            family = socket.AF_INET6
        else:
            family = socket.AF_INET
    else:
        # net == "unix"
        family = socket.AF_UNIX

    if net == "udp":
        sotype = socket.socket.SOCK_DGRAM
    else:
        # net == "unix" or net == "tcp"
        sotype = socket.SOCK_STREAM

    # bind and listen the socket
    sock = socket.socket(family, sotype)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(addr)
    sock.listen(maxListenerBacklog())

    # return the NetFd instance
    netfd = NetFd(sock, family, sotype, net)
    netfd.setaddr(sock.getsockname())
    return netfd

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from ..sync import Mutex
from ..sync.atomic import AtomicLong
from ..syscall import socket
from ..time import nano

def fd_(fd):
    if hasattr(fd, "fileno"):
        return int(fd.fileno())
    return fd


class Deadline(object):

    def __init__(self):
        self.m = Mutex()
        self.val = 0

    def expired(self):
        t = self.value()
        return t > 0 and nano() >= t

    def value(self):
        with self.m:
            v = self.val

        return v

    def set(self, v):
        with self.m:
            self.val = v

    def settime(self, t=None):
        self.set(t or nano())


def is_ipv6(addr):
    try:
        socket.inet_pton(socket.AF_INET6, addr)
    except socket.error:  # not a valid address
        return False
    except ValueError: # ipv6 not supported on this platform
        return False
    return True

########NEW FILE########
__FILENAME__ = file
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.#

from .. import syscall
from ..syscall import os


class File(object):

    def __init__(self, fd, name):
        self.fd = fd
        self.name = name

    def close(self):
        syscall.close(self.fd)
        self.fd = -1

    def read(self):
        return syscall.read(self.fd)


def pipe():
    syscall.ForkLock.rlock()
    p = os.pipe()
    syscall.closeonexec(p[0])
    syscall.closeonexec(p[1])
    syscall.ForkLock.runlock()
    return p

########NEW FILE########
__FILENAME__ = signal

import weakref

from ..core import default, go, gosched, select
from ..core.kernel import signal_enable, signal_disable
from ..core.sigqueue import NUMSIG
from ..sync import Mutex
from ..sync.atomic import AtomicLong
from ..syscall import signal

class Handler(object):

    def __init__(self):
        self.mask = set()

    def set(self, sig):
        self.mask.add(sig)

    def want(self, sig):
        return sig in self.mask


class Handlers(object):

    def __init__(self):
        self.m = Mutex()
        self.handlers = {}
        self.ref = {}

        # init signals
        for i in range(NUMSIG):
            self.ref[i] = 0

        self.signal_recv = AtomicLong(0)
        go(self.loop)


    def notify(self, c, *sigs):
        with self.m:
            if c not in self.handlers:
                h = Handler()
            else:
                h = self.handlers[c]

            for sig in sigs:
                h.set(sig)
                if not self.ref[sig]:
                    signal_enable(sig)

                self.ref[sig] += 1
            self.handlers[c] = h


    def stop(self, c):
        with self.m:
            if c not in self.handlers:
                return

            h = self.handlers.pop(c)
            for sig in h.mask:
                self.ref[sig] -= 1
                if self.ref[sig] == 0:
                    signal_disable(sig)


    def loop(self):
        while True:
            self.process(signal(self.signal_recv))

    def process(self, sig):
        with self.m:
            for c, h in self.handlers.items():
                if h.want(sig):
                    ret = select(c.if_send(sig))
                    if ret:
                        continue

            self.signal_recv.value = 0

_handlers = Handlers()
notify = _handlers.notify
stop = _handlers.stop

########NEW FILE########
__FILENAME__ = atomic
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.
# copyright (c) 2013 David Reid under the MIT License.

from cffi import FFI

from functools import total_ordering

ffi = FFI()

ffi.cdef("""
long long_add_and_fetch(long *, long);
long long_sub_and_fetch(long *, long);
long long_bool_compare_and_swap(long *, long, long);
""")

lib = ffi.verify("""
long long_add_and_fetch(long *v, long l) {
    return __sync_add_and_fetch(v, l);
};

long long_sub_and_fetch(long *v, long l) {
    return __sync_sub_and_fetch(v, l);
};

long long_bool_compare_and_swap(long *v, long o, long n) {
    return __sync_bool_compare_and_swap(v, o, n);
};
""")

@total_ordering
class AtomicLong(object):
    def __init__(self, initial_value):
        self._storage = ffi.new('long *', initial_value)

    def __repr__(self):
        return '<{0} at 0x{1:x}: {2!r}>'.format(
            self.__class__.__name__, id(self), self.value)

    @property
    def value(self):
        return self._storage[0]

    @value.setter
    def value(self, new):
        lib.long_bool_compare_and_swap(self._storage, self.value, new)

    def add(self, delta):
        """ atomically adds delta and returns the new value """
        if delta >= 0:
            lib.long_add_and_fetch(self._storage, delta)
        else:
            lib.long_sub_and_fetch(self._storage, abs(delta))

        return self._storage[0]


    def __iadd__(self, inc):
        lib.long_add_and_fetch(self._storage, inc)
        return self

    def __isub__(self, dec):
        lib.long_sub_and_fetch(self._storage, dec)
        return self

    def __eq__(self, other):
        if isinstance(other, AtomicLong):
            return self.value == other.value
        else:
            return self.value == other

    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        if isinstance(other, AtomicLong):
            return self.value < other.value
        else:
            return self.value < other

########NEW FILE########
__FILENAME__ = cond


from .mutex import Mutex
from .sema import Semaphore

class Cond(object):
    """ Cond implements a condition variable, a rendezvous point for coroutines
    waiting for or announcing the occurrence of an event.

    Each Cond has an associated Locker L (often a Mutex or RWMutex), which
    must be held when changing the condition and when calling the ``wait`` method.
    """


    def __init__(self, l):
        self.l = l
        self.m = Mutex()

        # We must be careful to make sure that when ``signal``
        # releases a semaphore, the corresponding acquire is
        # executed by a coroutine that was already waiting at
        # the time of the call to ``signal``, not one that arrived later.
        # To ensure this, we segment waiting coroutines into
        # generations punctuated by calls to ``signal``.  Each call to
        # ``signal`` begins another generation if there are no coroutines
        # left in older generations for it to wake.  Because of this
        # optimization (only begin another generation if there
        # are no older coroutines left), we only need to keep track
        # of the two most recent generations, which we call old
        # and new.

        self.old_waiters = 0 # number of waiters in old generation...
        self.old_sema = Semaphore() # ... waiting on this semaphore

        self.new_waiters = 0 # number of waiters in new generation...
        self.new_sema = Semaphore() # ... waiting on this semaphore

    def wait(self):
        """``wait`` atomically unlocks cond.l and suspends execution of the calling
        coroutine.  After later resuming execution, ``wait`` locks cond.l before
        returning.  Unlike in other systems, ``wait`` cannot return unless awoken by
        Broadcast or ``signal``.

        Because cond.l is not locked when ``wait`` first resumes, the caller typically
        cannot assume that the condition is true when ``wait`` returns.  Instead,
        the caller should ``wait`` in a loop::

            with m:
                while True:
                    if not condition():
                        cond.wait()

                    # ... handle the condition

        """

        self.m.lock()

        if self.new_sema is None:
            self.new_sema = Semaphore()

        self.new_waiters += 1
        self.m.unlock()
        self.l.unlock()
        self.new_sema.acquire()
        self.l.lock()

    def signal(self):
        """  ``signal`` wakes one coroutine waiting on cond, if there is any.

        It is allowed but not required for the caller to hold cond.l
        during the call.
        """
        self.m.lock()

        if self.old_waiters == 0 and self.new_waiters > 0:
            self.old_waiters = self.new_waiters
            self.old_sema = self.new_sema
            self.new_waiters = 0
            self.new_sema = None

        if self.old_waiters > 0:
            self.old_waiters -= 1
            self.old_sema.release()

        self.m.unlock()

    def broadcast(self):
        """  Broadcast wakes all coroutines waiting on cond.

        It is allowed but not required for the caller to hold cond.l
        during the call.
        """
        self.m.lock()

        if self.old_waiters > 0:
            for i in range(self.new_waiters):
                self.new_sema.release()
            self.new_waiters = 0
            self.new_sema = None

        self.m.unlock()

########NEW FILE########
__FILENAME__ = mutex
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .atomic import ffi, lib
from .sema import Semaphore

MUTEX_LOCKED = 1
MUTEX_WOKEN = 2
MUTEX_WAITER_SHIFT = 2

class Locker(object):

    def lock(self):
        raise NotImplementedError

    def unlock(self):
        raise NotImplementedError


class Mutex(Locker):
    """  A Mutex is a mutual exclusion lock. """

    def __init__(self):
        self.state =  ffi.new('long *', 0)
        self.sema = Semaphore(0)


    def lock(self):
        """ locks the coroutine """

        if lib.long_bool_compare_and_swap(self.state, 0, MUTEX_LOCKED):
            return

        awoke = False
        while True:
            old = self.state[0]
            new = old | MUTEX_LOCKED

            if old & MUTEX_LOCKED:
                new = old + 1<<MUTEX_WAITER_SHIFT

            if awoke:
                new &= ~(1<<MUTEX_WOKEN)


            if lib.long_bool_compare_and_swap(self.state, old, new):
                if old & MUTEX_LOCKED == 0:
                    break

                self.sema.acquire()
                awoke = True

    def __enter__(self):
        return self.lock()

    def unlock(self):
        new = lib.long_add_and_fetch(self.state, -MUTEX_LOCKED)
        if (new + MUTEX_LOCKED) & MUTEX_LOCKED == 0:
            raise RuntimeError("sync: unlock of unlocked mutex")

        old = new
        while True:
            if (old >> MUTEX_WAITER_SHIFT == 0
                    or old & (MUTEX_LOCKED | MUTEX_WOKEN) != 0):
                return

            new = (old - 1 << MUTEX_WAITER_SHIFT) | MUTEX_WOKEN
            if lib.long_bool_compare_and_swap(self.state, old, new):
                self.sema.release()
                return
            old = self.state[0]

    def __exit__(self, t, v, tb):
        self.unlock()

########NEW FILE########
__FILENAME__ = once
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import functools

from .atomic import AtomicLong
from .mutex import Mutex

class Once(object):
    """ Once is an object that will perform exactly one action. """

    def __init__(self):
        self.m = Mutex()
        self.done = AtomicLong(0)

    def do(self, func):
        """ Do calls the function f if and only if the method is being called for the

        ex::

            once = Once

            @once.do
            def f():
                return

            # or
            once.do(f)()

        if once.do(f) is called multiple times, only the first call will invoke
        f.
        """

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            if self.done == 1:
                return

            with self.m:
                if self.done == 0:
                    func(*args, **kwargs)
                    self.done.value = 1

        return _wrapper

########NEW FILE########
__FILENAME__ = rwmutex
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .atomic import AtomicLong
from .mutex import Locker, Mutex
from .sema import Semaphore

RWMUTEX_MAX_READERS = 1 << 30

class RWMutex(object):
    """ An RWMutex is a reader/writer mutual exclusion lock.

    The lock can be held by an arbitrary number of readers of a single writer
    """

    def __init__(self):
        self.w = Mutex() # held if there are pending writers
        self.writer_sem = Semaphore() # semaphore to wait for completing readers
        self.reader_sem = Semaphore() #semaphore to wait for complering writers
        self.reader_count = AtomicLong(0) # number of pending readers
        self.reader_wait = AtomicLong(0) # number of departing readers

    def rlock(self):
        """ lock reading

        """
        if self.reader_count.add(1) < 0:
            # a writer is pending, wait for it
            self.reader_sem.acquire()

    def runlock(self):
        """ unlock reading

        it does not affect other simultaneous readers.
        """
        if self.reader_count.add(-1) < 0:
            # a writer is pending
            if self.reader_wait.add(-1) == 0:
                # the last reader unblock the writer
                self.writer_sem.release()

    def lock(self):
        """ lock for writing

        If the lock is already locked for reading or writing, it blocks until
        the lock is available. To ensure that the lock eventually becomes
        available, a blocked lock call excludes new readers from acquiring.
        """
        self.w.lock()

        r = self.reader_count.add(-RWMUTEX_MAX_READERS) + RWMUTEX_MAX_READERS
        if r != 0 and self.reader_wait.add(r) != 0:
            self.writer_sem.acquire()

    def unlock(self):
        """ unlock writing

        As with Mutexes, a locked RWMutex is not associated with a particular
        coroutine.  One coroutine may rLock (lock) an RWMutex and then arrange
        for another goroutine to rUnlock (unlock) it.
        """
        r = self.reader_count.add(RWMUTEX_MAX_READERS)
        for i in range(r):
            self.reader_sem.release()

        self.w.unlock()

    def RLocker(self):
        return RLocker(self)

class RLocker(Locker):
    """ RLocker returns a Locker instance that implements the lock and unnlock
    methods of RWMutex. """

    def __init__(self, rw):
        self.rw = rw

    def lock(self):
        return self.rw.lock()

    __enter__ = lock

    def unlock(self):
        return self.rw.unlock()

    def __exit__(self, t, v, tb):
        self.unlock()


########NEW FILE########
__FILENAME__ = sema
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from collections import deque

from .atomic import AtomicLong
from ..core.context import park
from ..core import proc


class Semaphore(object):
    """ Semaphore implementation exposed to offset

    Intended use is provide a sleep and wakeup primitive that can be used in the
    contended case of other synchronization primitives.

    Thus it targets the same goal as Linux's futex, but it has much simpler
    semantics.

    That is, don't think of these as semaphores. Think of them as a way to
    implement sleep and wakeup such that every sleep is paired with a single
    wakeup, even if, due to races, the wakeup happens before the sleep.

    See Mullender and Cox, ``Semaphores in Plan 9,''
    http://swtch.com/semaphore.pdf

    Comment and code based on the Go code:
    http://golang.org/src/pkg/runtime/sema.goc
    """

    def __init__(self, value=0):
        self.sema = AtomicLong(value)
        self.nwait = AtomicLong(1)
        self.waiters = deque()

    def can_acquire(self):
        if self.sema > 0:
            self.sema -= 1
            return True
        return False

    def acquire(self):
        if self.can_acquire():
            return

        t0 = 0
        releasetime = 0

        while True:
            self.nwait += 1
            self.waiters.append(proc.current())

            if self.can_acquire():
                self.nwait -= 1
                self.waiters.remove(proc.current())
                return

            park()

    __enter__ = acquire

    def release(self):
        self.sema += 1

        if self.nwait == 0:
            return

        try:
            waiter = self.waiters.pop()
        except IndexError:
            return

        self.nwait -= 1
        waiter.ready()

    def __exit__(self, t, v, tb):
        return self.release()

########NEW FILE########
__FILENAME__ = waitgroup
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from ..core import PanicError

from .atomic import AtomicLong
from .mutex import Mutex
from .sema import Semaphore


class WaitGroup(object):
    """ A WaitGroup waits for a collection of goroutines to finish.
    The main goroutine calls ``add`` to set the number of goroutines to wait for.
    Then each of the goroutines  runs and calls Done when finished.  At the same
    time, ``wait`` can be used to block until all goroutines have finished.
    """

    def __init__(self):
        self.m = Mutex()
        self.counter = AtomicLong(0)
        self.waiters = AtomicLong(0)
        self.sema = Semaphore()

    def add(self, delta):
        """  Add adds delta, which may be negative, to the WaitGroup counter. If
        the counter becomes zero, all goroutines blocked on Wait are released.
        If the counter goes negative, raise an error.

        Note that calls with positive delta must happen before the call to
        ``wait``, or else ``wait`` may wait for too small a group. Typically
        this means the calls to add should execute before the statement creating
        the goroutine or other event to be waited for. See the WaitGroup example.
        """
        v = self.counter.add(delta)
        if v < 0:
            raise PanicError("sync: negative waitgroup counter")

        if v > 0 or self.waiters == 0:
            return

        with self.m:
            for i in range(self.waiters.value):
                self.sema.release()
            self.waiters = 0
            self.sema = None

    def done(self):
        """ decrement the WaitGroup counter """
        self.add(-1)

    def wait(self):
        """ blocks until the WaitGroup counter is zero. """
        if self.counter == 0:
            return

        self.m.lock()
        self.waiters += 1
        if self.counter == 0:
            self.waiters -= 1
            self.m.unlock()
            return

        if self.sema is None:
            self.sema = Semaphore()

        self.m.unlock()
        self.sema.acquire()

########NEW FILE########
__FILENAME__ = fexec
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import fcntl
import os

from ..sync import RWMutex

ForkLock = RWMutex()

def closeonexec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, flags)


def setnonblock(fd, nonblocking=True):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    if nonblocking:
        flags |= os.O_NONBLOCK
    else:
        flags &= ~os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)

########NEW FILE########
__FILENAME__ = proxy
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


__os_mod__ = __import__("os")
__select_mod__ = __import__("select")
__socket_mod__ = __import__("socket")
_socket = __import__("socket")

import io
import wrapt
from ..core import syscall, enter_syscall

__all__ = ['OsProxy', 'SelectProxy']


# proxy the OS module

class OsProxy(wrapt.ObjectProxy):
    """ proxy the os module """

    _OS_SYSCALLS =  ("chown", "fchown", "close", "dup", "dup2", "read",
            "pread","write", "pwrite", "sendfile", "readv", "writev", "stat",
            "lstat", "truncate", "sync", "lseek", "open", "posix_fallocate",
            "posix_fadvise", "chmod", "chflags", )

    def __init__(self):
        super(OsProxy, self).__init__(__os_mod__)

    def __getattr__(self, name):
        # wrap syscalls
        if name in self._OS_SYSCALLS:
            return syscall(getattr(self.__wrapped__, name))
        return getattr(self.__wrapped__, name)


if hasattr(_socket, "SocketIO"):
    SocketIO = _socket.SocketIO
else:
    from _socketio import SocketIO

class socket(object):
    """A subclass of _socket.socket wrapping the makefile() method and
    patching blocking calls. """

    __slots__ = ('_io_refs', '_sock', '_closed', )

    _BL_SYSCALLS = ('accept', 'getpeername', 'getsockname',
            'getsockopt', 'ioctl', 'recv', 'recvfrom', 'recvmsg',
            'recvmsg_into', 'recvfrom_into', 'recv_into', 'send',
            'sendall', 'sendto', 'sendmsg', )

    def __init__(self, family=_socket.AF_INET, type=_socket.SOCK_STREAM,
            proto=0, fileno=None):

        if fileno is not None:
            if hasattr(_socket.socket, 'detach'):
                self._sock = _socket.socket(family, type, proto, fileno)
            else:
                self._sock = _socket.fromfd(fileno, family, type, proto)
        else:
            self._sock = _socket.socket(family, type, proto)

        self._io_refs = 0
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if not self._closed:
            self.close()

    def __getattr__(self, name):
        # wrap syscalls
        if name in self._BL_SYSCALLS:
            return syscall(getattr(self._sock, name))

        return getattr(self._sock, name)


    def makefile(self, mode="r", buffering=None, encoding=None,
            errors=None, newline=None):
        """makefile(...) -> an I/O stream connected to the socket

        The arguments are as for io.open() after the filename,
        except the only mode characters supported are 'r', 'w' and 'b'.
        The semantics are similar too.  (XXX refactor to share code?)
        """
        for c in mode:
            if c not in {"r", "w", "b"}:
                raise ValueError("invalid mode %r (only r, w, b allowed)")
        writing = "w" in mode
        reading = "r" in mode or not writing
        assert reading or writing
        binary = "b" in mode
        rawmode = ""
        if reading:
            rawmode += "r"
        if writing:
            rawmode += "w"
        raw = SocketIO(self, rawmode)
        self._io_refs += 1
        if buffering is None:
            buffering = -1
        if buffering < 0:
            buffering = io.DEFAULT_BUFFER_SIZE
        if buffering == 0:
            if not binary:
                raise ValueError("unbuffered streams must be binary")
            return raw
        if reading and writing:
            buffer = io.BufferedRWPair(raw, raw, buffering)
        elif reading:
            buffer = io.BufferedReader(raw, buffering)
        else:
            assert writing
            buffer = io.BufferedWriter(raw, buffering)
        if binary:
            return buffer
        text = io.TextIOWrapper(buffer, encoding, errors, newline)
        text.mode = mode
        return text

    def _decref_socketios(self):
        if self._io_refs > 0:
            self._io_refs -= 1
        if self._closed:
            self._sock.close()

    def close(self):
        self._closed = True
        if self._io_refs <= 0:
            """
            # socket shutdown
            try:
                self._sock.shutdown(_socket.SHUT_RDWR)
            except:
                pass
            """

            self._sock.close()

    def detach(self):
        self._closed = True
        if hasattr(self._sock, 'detach'):
            return self._sock.detach()

        new_fd = os.dup(self._sock.fileno())
        self._sock.close()

        # python 2.7 has no detach method, fake it
        return new_fd


class SocketProxy(wrapt.ObjectProxy):

    def __init__(self):
        super(SocketProxy, self).__init__(__socket_mod__)

    def socket(self, *args, **kwargs):
        return socket(*args, **kwargs)


    def fromfd(self, fd, family, type, proto=0):
        return socket(family, type, fileno=fd)

    if hasattr(socket, "share"):
        def fromshare(self, info):
            return socket(0, 0, 0, info)

    if hasattr(_socket, "socketpair"):
        def socketpair(self, family=None, type=__socket_mod__.SOCK_STREAM,
                proto=0):

            if family is None:
                try:
                    family = self.__wrapped__.AF_UNIX
                except NameError:
                    family = self.__wrapped__.AF_INET
            a, b = self.__wrapped__.socketpair(family, type, proto)

            if hasattr(a, 'detach'):
                a = socket(family, type, proto, a.detach())
                b = socket(family, type, proto, b.detach())
            else:
                a = socket(family, type, proto, a.fileno())
                b = socket(family, type, proto, b.fileno())

            return a, b


# proxy the socket proxy


class _Poll(object):

    def register(self, *args):
        return self.p.register(*args)

    def modify(self, *args):
        return self.p.modify(*args)

    def unregister(self, *args):
        return self.p.unregister(*args)

    def poll(self, *args, **kwargs):
        return enter_syscall(self.p.poll, *args)


if hasattr(__select_mod__, "devpoll"):

    class devpoll(_Poll):

        def __init__(self):
            self.p = __select_mod__.devpoll()

if hasattr(__select_mod__, "epoll"):

    class epoll(_Poll):

        def __init__(self):
            self.p = __select_mod__.epoll()

        def close(self):
            return self.p.close()

        def fileno(self):
            return self.p.fileno()

        def fromfd(self, fd):
            return self.p.fromfd(fd)

if hasattr(__select_mod__, "poll"):

    class poll(_Poll):

        def __init__(self):
            self.p = __select_mod__.poll()

if hasattr(__select_mod__, "kqueue"):

    class kqueue(object):

        def __init__(self):
            self.kq = __select_mod__.kqueue()

        def fileno(self):
            return self.kq.fileno()

        def fromfd(self, fd):
            return self.kq.fromfd(fd)

        def close(self):
            return self.kq.close()

        def control(self, *args, **kwargs):
            return enter_syscall(self.kq.control, *args, **kwargs)



class SelectProxy(wrapt.ObjectProxy):

    def __init__(self):
        super(SelectProxy, self).__init__(__select_mod__)

    if hasattr(__select_mod__, "devpoll"):
        def devpoll(self):
            return devpoll()

    if hasattr(__select_mod__, "epoll"):
        def epoll(self):
            return epoll()

    if hasattr(__select_mod__, "poll"):
        def poll(self):
            return poll()

    if hasattr(__select_mod__, "kqueue"):
        def kqueue(self):
            return kqueue()

    def select(self, *args, **kwargs):
        return enter_syscall(self.__wrapped__.select, *args, **kwargs)

########NEW FILE########
__FILENAME__ = sysctl
import sys
from ctypes import *
from ctypes.util import find_library

libc = cdll.LoadLibrary(find_library("c"))

def sysctl(mib_t, c_type=None):
    mib = (c_int * len(mib_t))()
    for i, v in enumerate(mib_t):
        mib[i] = c_int(v)
    if c_type == None:
        size = c_size_t(0)
        libc.sysctl(mib, len(mib), None, byref(sz), None, 0)
        buf = create_string_buffer(size.value)
    else:
        buf = c_type()
        size = c_size_t(sizeof(buf))
    size = libc.sysctl(mib, len(mib), byref(buf), byref(size), None, 0)
    if st != 0:
        raise OSError('sysctl() returned with error %d' % st)
    try:
        return buf.value
    except AttributeError:
        return buf

def sysctlbyname(name, c_type=None):
    if c_type == None:
        size = c_size_t(0)
        libc.sysctlbyname(name, None, byref(sz), None, 0)
        buf = create_string_buffer(size.value)
    else:
        buf = c_type()
        size = c_size_t(sizeof(buf))
    st = libc.sysctlbyname(name, byref(buf), byref(size), None, 0)
    if st != 0:
        raise OSError('sysctlbyname() returned with error %d' % st)
    try:
        return buf.value
    except AttributeError:
        return buf

########NEW FILE########
__FILENAME__ = _socketio
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

"""
socketio taken from the python3 stdlib
"""

import io
import sys
from errno import EINTR, EAGAIN, EWOULDBLOCK

_socket = __import__('socket')
_blocking_errnos = EAGAIN, EWOULDBLOCK


# python2.6 fixes

def _recv_into_sock_py26(sock, buf):
    data = sock.recv(len(buf))
    l = len(data)
    buf[:l] = data
    return l


if sys.version_info < (2, 7, 0, 'final'):
    _recv_into_sock = _recv_into_sock_py26
else:
    _recv_into_sock = lambda sock, buf: sock.recv_into(buf)


class SocketIO(io.RawIOBase):

    """Raw I/O implementation for stream sockets.

    This class supports the makefile() method on sockets.  It provides
    the raw I/O interface on top of a socket object.
    """

    # One might wonder why not let FileIO do the job instead.  There are two
    # main reasons why FileIO is not adapted:
    # - it wouldn't work under Windows (where you can't used read() and
    #   write() on a socket handle)
    # - it wouldn't work with socket timeouts (FileIO would ignore the
    #   timeout and consider the socket non-blocking)

    # XXX More docs

    def __init__(self, sock, mode):
        if mode not in ("r", "w", "rw", "rb", "wb", "rwb"):
            raise ValueError("invalid mode: %r" % mode)
        io.RawIOBase.__init__(self)
        self._sock = sock
        if "b" not in mode:
            mode += "b"
        self._mode = mode
        self._reading = "r" in mode
        self._writing = "w" in mode
        self._timeout_occurred = False

    def readinto(self, b):
        """Read up to len(b) bytes into the writable buffer *b* and return
        the number of bytes read.  If the socket is non-blocking and no bytes
        are available, None is returned.

        If *b* is non-empty, a 0 return value indicates that the connection
        was shutdown at the other end.
        """
        self._checkClosed()
        self._checkReadable()
        if self._timeout_occurred:
            raise IOError("cannot read from timed out object")
        while True:
            try:
                return _recv_into_sock(self._sock, b)
            except _socket.timeout:
                self._timeout_occurred = True
                raise
            except _socket.error as e:
                n = e.args[0]
                if n == EINTR:
                    continue
                if n in _blocking_errnos:
                    return None
                raise

    def write(self, b):
        """Write the given bytes or bytearray object *b* to the socket
        and return the number of bytes written.  This can be less than
        len(b) if not all data could be written.  If the socket is
        non-blocking and no bytes could be written None is returned.
        """
        self._checkClosed()
        self._checkWritable()
        try:
            return self._sock.send(b)
        except _socket.error as e:
            # XXX what about EINTR?
            if e.args[0] in _blocking_errnos:
                return None
            raise

    def readable(self):
        """True if the SocketIO is open for reading.
        """
        return self._reading and not self.closed

    def writable(self):
        """True if the SocketIO is open for writing.
        """
        return self._writing and not self.closed

    def fileno(self):
        """Return the file descriptor of the underlying socket.
        """
        self._checkClosed()
        return self._sock.fileno()

    @property
    def name(self):
        if not self.closed:
            return self.fileno()
        else:
            return -1

    @property
    def mode(self):
        return self._mode

    def close(self):
        """Close the SocketIO object.  This doesn't close the underlying
        socket, except if all references to it have disappeared.
        """
        if self.closed:
            return
        io.RawIOBase.close(self)
        self._sock._decref_socketios()
        self._sock = None

    def _checkClosed(self, msg=None):
        """Internal: raise an ValueError if file is closed
        """
        if self.closed:
            raise ValueError("I/O operation on closed file."
                             if msg is None else msg)

########NEW FILE########
__FILENAME__ = time
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .core.util import nanotime, from_nanotime
from .core import timer
from .core.chan import makechan, select


NANOSECOND = 1
MICROSECOND = 1000 * NANOSECOND
MILLISECOND = 1000 * MICROSECOND
SECOND = 1000 * MILLISECOND
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE

nano = nanotime
sleep = timer.sleep

def _sendtime(now, t, c):
    select(c.if_send(from_nanotime(now)))

class Timer(object):
    """ The Timer instance represents a single event.
    When the timer expires, the current time will be sent on c """

    def __init__(self, interval):
        self.c = makechan(1)
        self.t = timer.Timer(_sendtime, interval, args=(self.c,))
        self.t.start()

    def reset(self, interval):
        """ reset the timer interval """
        w = nanotime() + interval
        self.t.stop()
        self.t.when = w
        self.t.start()

    def stop(self):
        self.t.stop()
        self.c.close()


def After(interval):
    """ After waits for the duration to elapse and then sends the current time
    on the returned channel.
    It is equivalent to Timer(interval).c
    """

    return Timer(interval).c

def AfterFunc(interval, func, args=None, kwargs=None):
    """ AfterFunc waits for the duration to elapse and then calls f in its own
    goroutine. It returns a Timer that can be used to cancel the call using its
    Stop method. """

    t = timer.Timer(func, interval, args=args, kwargs=kwargs)
    t.start()
    return t


class Ticker(object):
    """ returns a new Ticker containing a channel that will send the
    time with a period specified by the duration argument.

    It adjusts the intervals or drops ticks to make up for slow receivers.
    The duration d must be greater than zero.
    """

    def __init__(self, interval):
        if interval < 0:
            raise ValueError("non-positive interval")

        self.c = makechan(1)

        # set the runtime timer
        self.t = timer.Timer(_sendtime, interval, interval, args=(self.c,))
        self.t.start()

    def stop(self):
        self.c.close()
        self.t.stop()


def Tick(interval):
    """ Tick is a convenience wrapper for Ticker providing access
    to the ticking channel. Useful for clients that no need to shutdown
    the ticker """

    if interval <= 0:
        return

    return Ticker(interval).c

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2013 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.4.1"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("filterfalse", "itertools", "itertools", "ifilterfalse", "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute("zip_longest", "itertools", "itertools", "izip_longest", "zip_longest"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_parse", __name__ + ".moves.urllib_parse", "urllib.parse"),
    MovedModule("urllib_error", __name__ + ".moves.urllib_error", "urllib.error"),
    MovedModule("urllib", __name__ + ".moves.urllib", __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules[__name__ + ".moves"] = _MovedItems(__name__ + ".moves")



class Module_six_moves_urllib_parse(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib_parse")
sys.modules[__name__ + ".moves.urllib.parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib.parse")


class Module_six_moves_urllib_error(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib_error")
sys.modules[__name__ + ".moves.urllib.error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib.error")


class Module_six_moves_urllib_request(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgrWithDefaultRealm", "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib_request")
sys.modules[__name__ + ".moves.urllib.request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib.request")


class Module_six_moves_urllib_response(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib_response")
sys.modules[__name__ + ".moves.urllib.response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib.response")


class Module_six_moves_urllib_robotparser(types.ModuleType):
    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

sys.modules[__name__ + ".moves.urllib_robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib_robotparser")
sys.modules[__name__ + ".moves.urllib.robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):
    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""
    parse = sys.modules[__name__ + ".moves.urllib_parse"]
    error = sys.modules[__name__ + ".moves.urllib_error"]
    request = sys.modules[__name__ + ".moves.urllib_request"]
    response = sys.modules[__name__ + ".moves.urllib_response"]
    robotparser = sys.modules[__name__ + ".moves.urllib_robotparser"]


sys.modules[__name__ + ".moves.urllib"] = Module_six_moves_urllib(__name__ + ".moves.urllib")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))

def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))

def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))

def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    unichr = chr
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    unichr = unichr
    int2byte = chr
    def byte2int(bs):
        return ord(bs[0])
    def indexbytes(buf, i):
        return ord(buf[i])
    def iterbytes(buf):
        return (ord(byte) for byte in buf)
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        for slots_var in orig_vars.get('__slots__', ()):
            orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

version_info = (0, 1, 0)
__version__ = ".".join([str(v) for v in version_info])

########NEW FILE########
__FILENAME__ = test_atomic
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.
# copyright (c) 2013 David Reid under the MIT License.


from offset.sync.atomic import AtomicLong, ffi, lib

def test_long_add_and_fetch():
    l = ffi.new('long *', 0)
    assert lib.long_add_and_fetch(l, 1) == 1
    assert lib.long_add_and_fetch(l, 10) == 11

def test_long_sub_and_fetch():
    l = ffi.new('long *', 0)
    assert lib.long_sub_and_fetch(l, 1) == -1
    assert lib.long_sub_and_fetch(l, 10) == -11

def test_long_bool_compare_and_swap():
    l = ffi.new('long *', 0)
    assert lib.long_bool_compare_and_swap(l, 0, 10) == True
    assert lib.long_bool_compare_and_swap(l, 1, 20) == False

def test_atomiclong_repr():
    l = AtomicLong(123456789)
    assert '<AtomicLong at ' in repr(l)
    assert '123456789>' in repr(l)

def test_atomiclong_value():
    l = AtomicLong(0)
    assert l.value == 0
    l.value = 10
    assert l.value == 10

def test_atomiclong_iadd():
    l = AtomicLong(0)
    l += 10
    assert l.value == 10

def test_atomiclong_isub():
    l = AtomicLong(0)
    l -= 10
    assert l.value == -10

def test_atomiclong_eq():
    l1 = AtomicLong(0)
    l2 = AtomicLong(1)
    l3 = AtomicLong(0)
    assert l1 == 0
    assert l1 != 1
    assert not (l2 == 0)
    assert not (l2 != 1)
    assert l1 == l3
    assert not (l1 != l3)
    assert l1 != l2
    assert not (l1 == l2)

def test_atomiclong_ordering():
    l1 = AtomicLong(0)
    l2 = AtomicLong(1)
    l3 = AtomicLong(0)

    assert l1 < l2
    assert l1 <= l2
    assert l1 <= l3
    assert l2 > l1
    assert l2 >= l3
    assert l2 >= l2

    assert l1 < 1
    assert l1 <= 0
    assert l1 <= 1
    assert l1 > -1
    assert l1 >= -1
    assert l1 >= 0

########NEW FILE########
__FILENAME__ = test_channel
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from __future__ import absolute_import

import time
from py.test import skip


from offset import makechan, go, gosched, run, maintask, select
from offset.core.chan import bomb

SHOW_STRANGE = False

from offset.util import six

def dprint(txt):
    if SHOW_STRANGE:
        print(txt)

class Test_Channel:

    def test_simple_channel(self):
        output = []
        def print_(*args):
            output.append(args)

        def sending(channel):
            print_("sending")
            channel.send("foo")

        def receiving(channel):
            print_("receiving")
            print_(channel.recv())

        @maintask
        def main():
            ch = makechan()
            go(sending, ch)
            go(receiving, ch)

        run()

        assert output == [('sending',), ('receiving',), ('foo',)]


    def test_send_counter(self):
        import random

        numbers = list(range(20))
        random.shuffle(numbers)

        def counter(n, ch):
            ch.send(n)

        rlist = []


        @maintask
        def main():
            ch = makechan()
            for each in numbers:
                go(counter, each, ch)
            for each in numbers:
                rlist.append(ch.recv())

        run()

        rlist.sort()
        numbers.sort()
        assert rlist == numbers

    def test_recv_counter(self):
        import random

        numbers = list(range(20))
        random.shuffle(numbers)

        rlist = []
        def counter(n, ch):
            ch.recv()
            rlist.append(n)

        @maintask
        def main():
            ch = makechan()

            for each in numbers:
                go(counter, each, ch)

            for each in numbers:
                ch.send(None)
        run()

        numbers.sort()
        rlist.sort()
        assert rlist == numbers

    def test_bomb(self):
        try:
            1/0
        except:
            import sys
            b = bomb(*sys.exc_info())
        assert b.type is ZeroDivisionError
        if six.PY3:
            assert (str(b.value).startswith('division by zero') or
                    str(b.value).startswith('int division'))
        else:
            assert str(b.value).startswith('integer division')
        assert b.traceback is not None

    def test_send_exception(self):
        def exp_sender(chan):
            chan.send_exception(Exception, 'test')

        def exp_recv(chan):
            try:
                val = chan.recv()
            except Exception as exp:
                assert exp.__class__ is Exception
                assert str(exp) == 'test'

        @maintask
        def main():
            chan = makechan()
            go(exp_recv, chan)
            go(exp_sender, chan)
        run()


    def test_simple_pipe(self):
        def pipe(X_in, X_out):
            foo = X_in.recv()
            X_out.send(foo)

        @maintask
        def main():
            X, Y = makechan(), makechan()
            go(pipe, X, Y)

            X.send(42)
            assert Y.recv() == 42
        run()


    def test_nested_pipe(self):
        dprint('tnp ==== 1')
        def pipe(X, Y):
            dprint('tnp_P ==== 1')
            foo = X.recv()
            dprint('tnp_P ==== 2')
            Y.send(foo)
            dprint('tnp_P ==== 3')

        def nest(X, Y):
            X2, Y2 = makechan(), makechan()
            go(pipe, X2, Y2)
            dprint('tnp_N ==== 1')
            X_Val = X.recv()
            dprint('tnp_N ==== 2')
            X2.send(X_Val)
            dprint('tnp_N ==== 3')
            Y2_Val = Y2.recv()
            dprint('tnp_N ==== 4')
            Y.send(Y2_Val)
            dprint('tnp_N ==== 5')


        @maintask
        def main():
            X, Y = makechan(), makechan()
            go(nest, X, Y)
            X.send(13)
            dprint('tnp ==== 2')
            res = Y.recv()
            dprint('tnp ==== 3')
            assert res == 13
            if SHOW_STRANGE:
                raise Exception('force prints')

        run()

    def test_wait_two(self):
        """
        A tasklets/channels adaptation of the test_wait_two from the
        logic object space
        """
        def sleep(X, Y):
            dprint('twt_S ==== 1')
            value = X.recv()
            dprint('twt_S ==== 2')
            Y.send((X, value))
            dprint('twt_S ==== 3')

        def wait_two(X, Y, Ret_chan):
            Barrier = makechan()
            go(sleep, X, Barrier)
            go(sleep, Y, Barrier)
            dprint('twt_W ==== 1')
            ret = Barrier.recv()
            dprint('twt_W ==== 2')
            if ret[0] == X:
                Ret_chan.send((1, ret[1]))
            else:
                Ret_chan.send((2, ret[1]))
            dprint('twt_W ==== 3')

        @maintask
        def main():
            X, Y = makechan(), makechan()
            Ret_chan = makechan()

            go(wait_two, X, Y, Ret_chan)

            dprint('twt ==== 1')
            Y.send(42)

            dprint('twt ==== 2')
            X.send(42)
            dprint('twt ==== 3')
            value = Ret_chan.recv()
            dprint('twt ==== 4')
            assert value == (2, 42)

        run()


    def test_async_channel(self):

        @maintask
        def main():
            c = makechan(100)

            unblocked_sent = 0
            for i in range(100):
                c.send(True)
                unblocked_sent += 1

            assert unblocked_sent == 100

            unblocked_recv = []
            for i in range(100):
                unblocked_recv.append(c.recv())

            assert len(unblocked_recv) == 100

        run()

    def test_async_with_blocking_channel(self):

        def sender(c):
            unblocked_sent = 0
            for i in range(10):
                c.send(True)
                unblocked_sent += 1

            assert unblocked_sent == 10

            c.send(True)

        @maintask
        def main():
            c = makechan(10)

            go(sender, c)
            unblocked_recv = []
            for i in range(11):
                unblocked_recv.append(c.recv())


            assert len(unblocked_recv) == 11


        run()

    def test_multiple_sender(self):
        rlist = []
        sent = []

        def f(c):
            c.send("ok")

        def f1(c):
            c.send("eof")

        def f2(c):
            while True:
                data = c.recv()
                sent.append(data)
                if data == "eof":
                    return
                rlist.append(data)

        @maintask
        def main():
            c = makechan()
            go(f, c)
            go(f1, c)
            go(f2, c)

        run()

        assert rlist == ['ok']
        assert len(sent) == 2
        assert "eof" in sent


def test_select_simple():
    rlist = []
    def fibonacci(c, quit):
        x, y = 0, 1
        while True:
            ret = select(c.if_send(x), quit.if_recv())
            if ret == c.if_send(x):
                x, y = y, x+y
            elif ret == quit.if_recv():
                return

    @maintask
    def main():
        c = makechan()
        quit = makechan()
        def f():
            for i in range(10):
                rlist.append(c.recv())
            print(rlist)
            quit.send(0)

        go(f)
        fibonacci(c, quit)

    run()

    assert rlist == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

def test_select_buffer():
    rlist = []
    def test(c, quit):
        x = 0
        while True:
            ret = select(c.if_send(x), quit.if_recv())
            if ret == c.if_send(x):
                x = x + 1
            elif ret == quit.if_recv():
                return

    @maintask
    def main():
        c = makechan(5, label="c")
        quit = makechan(label="quit")
        def f():
            for i in range(5):
                v = c.recv()
                rlist.append(v)
            quit.send(0)

        go(f)
        test(c, quit)
    run()

    assert rlist == [0, 1, 2, 3, 4]

def test_select_buffer2():
    rlist = []

    def test(c):
        while True:
            ret = select(c.if_recv())
            if ret == c.if_recv():

                if ret.value == "QUIT":
                    break
                rlist.append(ret.value)

    @maintask
    def main():
        c = makechan(5, label="c")
        go(test, c)

        for i in range(5):
            c.send(i)

        c.send("QUIT")

    run()
    assert rlist == [0, 1, 2, 3, 4]

########NEW FILE########
__FILENAME__ = test_core_timer
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import time

from offset import run, go, maintask
from offset.core.context import park
from offset.core import proc
from offset.core.util import nanotime
from offset.core.timer import Timer, sleep
from offset.time import SECOND

DELTA0 = 0.06 * SECOND
DELTA = 0.06 * SECOND


def _wait():
    time.sleep(0.01)


def test_simple_timer():

    def _func(now, t, rlist, g):
        rlist.append(now)
        g.ready()

    @maintask
    def main():
        rlist = []
        period = 0.1 * SECOND
        t = Timer(_func, period, args=(rlist, proc.current()))
        now = nanotime()
        t.start()
        park()
        delay = rlist[0]

        assert (now + period - DELTA0) <= delay <= (now + period + DELTA), delay

    run()


def test_multiple_timer():
    r1 = []
    def f1(now, t, g):
        r1.append(now)
        g.ready()

    r2 = []
    def f2(now, t):
        r2.append(now)

    @maintask
    def main():
        T1 = 0.4 * SECOND
        T2 = 0.1 * SECOND
        t1 = Timer(f1, T1, args=(proc.current(),))
        t2 = Timer(f2, T2)

        now = nanotime()
        t1.start()
        t2.start()

        park()

        assert r1[0] > r2[0]

        assert (now + T1 - DELTA0) <= r1[0] <= (now + T1 + DELTA), r1[0]
        assert (now + T2 - DELTA0) <= r2[0] <= (now + T2 + DELTA), r2[0]

    run()


def test_repeat():
    r = []
    def f(now, t, g):
        if len(r) == 3:
            t.stop()
            g.ready()
        else:
            r.append(now)


    @maintask
    def main():
        t = Timer(f, 0.01 * SECOND, 0.01 * SECOND, args=(proc.current(),))
        t.start()
        park()

        assert len(r) == 3
        assert r[2] > r[1]
        assert r[1] > r[0]

    run()


def test_sleep():
    @maintask
    def main():
        PERIOD = 0.1 * SECOND
        start = nanotime()
        sleep(PERIOD)
        diff = nanotime() - start
        assert PERIOD - DELTA0 <= diff <= PERIOD + DELTA

    run()


def test_multiple_sleep():
    T1 = 0.4 * SECOND
    T2 = 0.1 * SECOND

    r1 = []
    def f1():
        sleep(T1)
        r1.append(nanotime())

    r2 = []
    def f2():
        sleep(T2)
        r2.append(nanotime())

    go(f1)
    go(f2)
    now = nanotime()
    run()
    assert r1[0] > r2[0]
    assert (now + T1 - DELTA0) <= r1[0] <= (now + T1 + DELTA), r1[0]
    assert (now + T2 - DELTA0) <= r2[0] <= (now + T2 + DELTA), r2[0]

########NEW FILE########
__FILENAME__ = test_kernel
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from __future__ import absolute_import

import time
from py.test import skip

from offset import makechan, go, gosched, run, maintask

SHOW_STRANGE = False


def dprint(txt):
    if SHOW_STRANGE:
        print(txt)

def test_simple():
    rlist = []

    def f():
        rlist.append('f')

    def g():
        rlist.append('g')
        gosched()

    @maintask
    def main():
        rlist.append('m')
        cg = go(g)
        cf = go(f)
        gosched()
        rlist.append('m')

    run()

    assert rlist == 'm g f m'.split()

def test_run():
    output = []
    def print_(*args):
        output.append(args)

    def f(i):
        print_(i)

    go(f, 1)
    go(f, 2)
    run()

    assert output == [(1,), (2,)]


def test_run_class():
    output = []
    def print_(*args):
        output.append(args)

    class Test(object):

        def __call__(self, i):
            print_(i)

    t = Test()

    go(t, 1)
    go(t, 2)
    run()

    assert output == [(1,), (2,)]


# tests inspired from simple core.com examples

def test_construction():
    output = []
    def print_(*args):
        output.append(args)

    def aCallable(value):
        print_("aCallable:", value)

    go(aCallable, 'Inline using setup')

    run()
    assert output == [("aCallable:", 'Inline using setup')]


    del output[:]
    go(aCallable, 'Inline using ()')

    run()
    assert output == [("aCallable:", 'Inline using ()')]

def test_run():
    output = []
    def print_(*args):
        output.append(args)

    def f(i):
        print_(i)

    @maintask
    def main():
        go(f, 1)
        go(f, 2)

    run()

    assert output == [(1,), (2,)]

def test_schedule():
    output = []
    def print_(*args):
        output.append(args)

    def f(i):
        print_(i)

    go(f, 1)
    go(f, 2)
    gosched()

    assert output == [(1,), (2,)]


def test_cooperative():
    output = []
    def print_(*args):
        output.append(args)

    def Loop(i):
        for x in range(3):
            gosched()
            print_("schedule", i)

    @maintask
    def main():
        go(Loop, 1)
        go(Loop, 2)
    run()

    assert output == [('schedule', 1), ('schedule', 2),
                      ('schedule', 1), ('schedule', 2),
                      ('schedule', 1), ('schedule', 2),]

########NEW FILE########
__FILENAME__ = test_sync
# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from offset import go, run, maintask, makechan, select, default, PanicError

from pytest import raises

from offset.sync.atomic import AtomicLong
from offset.sync.cond import Cond
from offset.sync.mutex import Mutex
from offset.sync.once import Once
from offset.sync.rwmutex import RWMutex
from offset.sync.waitgroup import WaitGroup


def test_Mutex():

    def hammer_mutex(m, loops, cdone):
        for i in range(loops):
            m.lock()
            m.unlock()

        cdone.send(True)

    @maintask
    def main():
        m = Mutex()
        c = makechan()
        for i in range(10):
            go(hammer_mutex, m, 1000, c)

        for i in range(10):
            c.recv()

    run()

def test_Mutex():

    def hammer_mutex(m, loops, cdone):
        for i in range(loops):
            m.lock()
            m.unlock()

        cdone.send(True)

    @maintask
    def main():
        m = Mutex()
        c = makechan()
        for i in range(10):
            go(hammer_mutex, m, 1000, c)

        for i in range(10):
            c.recv()

    run()

def test_Once():

    def f(o):
        o += 1

    def test(once, o, c):
        once.do(f)(o)
        assert o == 1
        c.send(True)

    @maintask
    def main():
        c = makechan()
        once = Once()
        o = AtomicLong(0)
        for i in range(10):
            go(test, once, o, c)

        for i in range(10):
            c.recv()

        assert o == 1

    run()

def test_RWMutex_concurrent_readers():

    def reader(m, clocked, cunlock, cdone):
        m.rlock()
        clocked.send(True)
        cunlock.recv()
        m.runlock()
        cdone.send(True)

    def test_readers(num):
        m = RWMutex()
        clocked = makechan()
        cunlock = makechan()
        cdone = makechan()

        for i in range(num):
            go(reader, m, clocked, cunlock, cdone)

        for i in range(num):
            clocked.recv()

        for i in range(num):
            cunlock.send(True)

        for i in range(num):
            cdone.recv()

    @maintask
    def main():
        test_readers(1)
        test_readers(3)
        test_readers(4)

    run()

def test_RWMutex():

    activity = AtomicLong(0)

    def reader(rwm, num_iterations, activity, cdone):
        print("reader")
        for i in range(num_iterations):
            rwm.rlock()
            n = activity.add(1)
            assert n >= 1 and n < 10000, "rlock %d" % n

            for i in range(100):
                continue

            activity.add(-1)
            rwm.runlock()
        cdone.send(True)

    def writer(rwm, num_iterations, activity, cdone):
        for i in range(num_iterations):
            rwm.lock()
            n = activity.add(10000)
            assert n == 10000, "wlock %d" % n
            for i in range(100):
                continue
            activity.add(-10000)
            rwm.unlock()
        cdone.send(True)

    def hammer_rwmutex(num_readers, num_iterations):
        activity = AtomicLong(0)
        rwm = RWMutex()
        cdone = makechan()

        go(writer, rwm, num_iterations, activity, cdone)

        for i in range(int(num_readers / 2)):
            go(reader, rwm, num_iterations, activity, cdone)

        go(writer, rwm, num_iterations, activity, cdone)

        for i in range(num_readers):
            go(reader, rwm, num_iterations, activity, cdone)

        for i in range(2 + num_readers):
            cdone.recv()

    @maintask
    def main():
        n = 1000
        hammer_rwmutex(1, n)
        hammer_rwmutex(3, n)
        hammer_rwmutex(10, n)

    run()

def test_RLocker():
    wl = RWMutex()
    rl = wl.RLocker()
    wlocked = makechan(1)
    rlocked = makechan(1)

    n = 10

    def test():
        for i in range(n):
            rl.lock()
            rl.lock()
            rlocked.send(True)
            wl.lock()
            wlocked.send(True)

    @maintask
    def main():
        go(test)
        for i in range(n):
            rlocked.recv()
            rl.unlock()
            ret = select(wlocked.if_recv(), default)
            assert ret != wlocked.if_recv(), "RLocker didn't read-lock it"
            rl.unlock()
            wlocked.recv()
            ret = select(rlocked.if_recv(), default)
            assert ret != rlocked.if_recv(), "RLocker didn't respect the write lock"
            wl.unlock()

    run()

def test_Cond_signal():

    def test(m, c, running, awake):
        with m:
            running.send(True)
            c.wait()
            awake.send(True)


    @maintask
    def main():
        m = Mutex()
        c = Cond(m)
        n = 2
        running = makechan(n)
        awake = makechan(n)

        for i in range(n):
            go(test, m, c, running, awake)

        for i in range(n):
            running.recv()

        while n > 0:
            ret = select(awake.if_recv(), default)
            assert ret != awake.if_recv(), "coroutine not asleep"

            m.lock()
            c.signal()
            awake.recv()
            ret = select(awake.if_recv(), default)
            assert ret != awake.if_recv(), "too many coroutines awakes"
            n -= 1
        c.signal()

    run()

def test_Cond_signal_generation():

    def test(i, m, c, running, awake):
        m.lock()
        running.send(True)
        c.wait()
        awake.send(i)
        m.unlock()

    @maintask
    def main():
        m = Mutex()
        c = Cond(m)
        n = 100
        running = makechan(n)
        awake = makechan(n)

        for i in range(n):
            go(test, i, m, c, running, awake)

            if i > 0:
                a = awake.recv()
                assert a == (i - 1), "wrong coroutine woke up: want %d, got %d" % (i-1, a)

            running.recv()
            with m:
                c.signal()

    run()

def test_Cond_broadcast():
    m = Mutex()
    c = Cond(m)
    n = 200
    running = makechan(n)
    awake = makechan(n)
    exit = False

    def test(i):
        m.lock()
        while not exit:
            running.send(i)
            c.wait()
            awake.send(i)
        m.unlock()

    @maintask
    def main():
        for i in range(n):
            go(test, i)

        for i in range(n):
            for i in range(n):
                running.recv()
            if i == n -1:
                m.lock()
                exit = True
                m.unlock()

            ret = select(awake.if_recv(), default)
            assert ret != awake.if_recv(), "coroutine not asleep"

            m.lock()
            c.broadcast()
            m.unlock()

            seen = {}
            for i in range(n):
                g = awake.recv()
                assert g not in seen, "coroutine woke up twice"
                seen[g] = True

        ret = select(running.if_recv(), default)
        assert ret != running.if_recv(), "coroutine did not exist"
        c.broadcast()

    run()

def test_WaitGroup():

    def test_waitgroup(wg1, wg2):
        n = 16
        wg1.add(n)
        wg2.add(n)
        exited = makechan(n)

        def f(i):
            wg1.done()
            wg2.wait()
            exited.send(True)

        for i in range(n):
            go(f, i)

        wg1.wait()

        for i in range(n):
            ret = select(exited.if_recv(), default)
            assert ret != exited.if_recv(), "WaitGroup released group too soon"
            wg2.done()

            for i in range(16):
                exited.recv()

    @maintask
    def main():
        wg1 = WaitGroup()
        wg2 = WaitGroup()
        for i in range(8):
            test_waitgroup(wg1, wg2)

    run()

def test_WaitGroup_raises():

    @maintask
    def main():
        wg = WaitGroup()
        with raises(PanicError):
            wg.add(1)
            wg.done()
            wg.done()
    run()

########NEW FILE########
__FILENAME__ = test_time

from offset import go, run, maintask, makechan
from offset.time import (SECOND, sleep, Ticker, Tick, nanotime, Timer, After,
        AfterFunc)

DELTA0 = 0.06 * SECOND
DELTA = 0.06 * SECOND


def test_sleep():
    @maintask
    def main():
        PERIOD = 0.1 * SECOND

        start = nanotime()
        sleep(PERIOD)
        diff = nanotime() - start
        assert PERIOD - DELTA0 <= diff <= PERIOD + DELTA

    run()

def test_Ticker():
    rlist = []

    @maintask
    def main():
        ticker = Ticker(0.1 * SECOND)
        for i in range(3):
            rlist.append(ticker.c.recv())

        ticker.stop()

    run()

    assert len(rlist) == 3

def test_Tick():
    rlist = []

    @maintask
    def main():
        ticker_chan = Tick(0.1 * SECOND)
        for i in range(3):
            rlist.append(ticker_chan.recv())

    run()

    assert len(rlist) == 3


def test_Timer():
    rlist = []

    @maintask
    def main():
        PERIOD = 0.1 * SECOND
        now = nanotime()
        t = Timer(PERIOD)
        rlist.append(t.c.recv())

        diff = nanotime() - rlist[0]
        assert PERIOD - DELTA0 <= diff <= PERIOD + DELTA

    run()

def test_Timer_reset():
    rlist = []

    @maintask
    def main():
        PERIOD = 10 * SECOND
        t = Timer(PERIOD)
        now = nanotime()
        t.reset(0.1 * SECOND)

        rlist.append(t.c.recv())

        diff = nanotime() - rlist[0]
        assert PERIOD - DELTA0 <= diff <= PERIOD + DELTA

    run()


def test_After():
    rlist = []

    @maintask
    def main():
        PERIOD = 0.1 * SECOND
        now = nanotime()
        c = After(PERIOD)
        rlist.append(c.recv())

        diff = nanotime() - rlist[0]
        assert PERIOD - DELTA0 <= diff <= PERIOD + DELTA

    run()

def test_AfterFunc():
    rlist = []

    @maintask
    def main():
        i = 10
        c = makechan()

        def f():
            i -= 1
            if i >= 0:
                AfterFunc(0, f)
                sleep(1 * SECOND)
            else:
                c.send(True)

        AfterFunc(0, f)
        c.recv()

        assert i == 0

    run()

########NEW FILE########
