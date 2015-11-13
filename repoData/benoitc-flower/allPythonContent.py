__FILENAME__ = actor_example
from flower import spawn, receive, send, run

messages = []
sources = []
def consumer():
    # wait for coming message in the current actor
    while True:
        source, msg = receive()
        if not msg:
            break
        print("got message from %s: %s" % (source.ref, msg))

def publisher1(ref):
    # an actor sending messages to the consumer
    msg = ['hello', 'world']
    for s in msg:
        send(ref, s)

def publisher2(ref):
    msg = ['brave', 'new', 'world', '']
    for s in msg:
        send(ref, s)

ref_consumer = spawn(consumer)
spawn(publisher1, ref_consumer)
spawn(publisher2, ref_consumer)

run()

########NEW FILE########
__FILENAME__ = echo_client
from flower import tasklet, run, schedule
from flower.net import Dial


# connect to the remote server
conn = Dial("tcp", ('127.0.0.1', 8000))

# start to handle the connection
# we send a string to the server and fetch the
# response back

for i in range(3):
    msg = "hello"
    print("sent %s" % msg)
    resp = conn.write(msg)
    ret = conn.read()
    print("echo: %s" % ret)

conn.close()
run()

########NEW FILE########
__FILENAME__ = echo_server
# Echo server program
from flower import tasklet, run
from flower.net import Listen


# handle the connection. It return data to the sender.
def handle_connection(conn):
    while True:
        data = conn.read()
        if not data:
            break

        conn.write(data)


# Listen on tcp port 8000 on localhost
l = Listen(('127.0.0.1', 8000), "tcp")
try:
    while True:
        try:

            # wait for new connections (it doesn't block other tasks)
            conn, err = l.accept()

            # Handle the connection in a new task.
            # The loop then returns to accepting, so that
            # multiple connections may be served concurrently.

            t = tasklet(handle_connection)(conn)
        except KeyboardInterrupt:
            break
finally:
    l.close()

run()

########NEW FILE########
__FILENAME__ = echo_sockserver
# Echo server program
from flower import tasklet, run
from flower.net import Listen


# handle the connection. It return data to the sender.
def handle_connection(conn):
    while True:
        data = conn.read()
        if not data:
            break

        conn.write(data)


# Listen on tcp port 8000 on localhost using the python socket module.
l = Listen(('127.0.0.1', 8000), "socktcp")
try:
    while True:
        try:

            # wait for new connections (it doesn't block other tasks)
            conn, err = l.accept()

            # Handle the connection in a new task.
            # The loop then returns to accepting, so that
            # multiple connections may be served concurrently.

            t = tasklet(handle_connection)(conn)
        except KeyboardInterrupt:
            break
finally:
    l.close()

run()

########NEW FILE########
__FILENAME__ = hello
from flower import run, schedule, tasklet

def say(s):
    for i in range(5):
        schedule()
        print(s)

def main():
    tasklet(say)("world")
    say("hello")

    run()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = stackless_scheduler_thread
import threading
from flower import schedule, run, getruncount, schedule, tasklet

try:
    from thread import get_ident
except ImportError: #python 3
    from _thread import get_ident

def secondary_thread_func():
    runcount = getruncount()
    print("THREAD(2): Has", runcount, "tasklets in its scheduler")

def main_thread_func():
    print("THREAD(1): Waiting for death of THREAD(2)")
    while thread.is_alive():
        schedule()
    print("THREAD(1): Death of THREAD(2) detected")

mainThreadTasklet = tasklet(main_thread_func)()

thread = threading.Thread(target=secondary_thread_func)
thread.start()

print("we are in %s" % get_ident())
run()

########NEW FILE########
__FILENAME__ = stackless_threadsafe_channels
import threading
import sys
if sys.version_info[0] <= 2:
    import thread
else:
    import _thread as thread


import flower

commandChannel = flower.channel()

def master_func():
    commandChannel.send("ECHO 1")
    commandChannel.send("ECHO 2")
    commandChannel.send("ECHO 3")
    commandChannel.send("QUIT")

def slave_func():
    print("SLAVE STARTING")
    while 1:
        command = commandChannel.receive()
        print("SLAVE:", command)
        if command == "QUIT":
            break
    print("SLAVE ENDING")

def scheduler_run(tasklet_func):
    t = flower.tasklet(tasklet_func)()
    while t.alive:
        flower.run()

th = threading.Thread(target=scheduler_run, args=(master_func,))
th.start()

scheduler_run(slave_func)

########NEW FILE########
__FILENAME__ = actor
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from collections import deque
import inspect
import operator
import sys
import threading
import weakref

import six

from flower import core
from flower.registry import registry
from flower.time import sleep, after_func


def self():
    return core.getcurrent()


class ActorRef(object):

    __slots__ = ['ref', '_actor_ref', 'is_alive', '__dict__', 'actor']

    __shared_state__ = dict(
            _ref_count = 0
    )

    def __init__(self, actor):
        self.__dict__ = self.__shared_state__
        self._actor_ref = weakref.ref(actor)

        # increment the ref counter
        with threading.RLock():
            self.ref = self._ref_count
            self._ref_count += 1

    def __str__(self):
        return "<actor:%s>" % self.ref

    @property
    def actor(self):
        return self._actor_ref()

    @property
    def is_alive(self):
        return self.actor is not None

class Message(object):

    def __init__(self, source, dest, msg):
        self.source = source
        self.dest = dest
        self.msg = msg

    def send(self):
        target = self.dest.actor
        if not target:
            registry.unregister(self.dest)
            return

        target.send((self.source.ref, self.msg))

    def send_after(self, seconds):
        after_func(seconds, self.send)



class Mailbox(object):
    """ a mailbox can accept any message from other actors.
    This is different from a channel since it doesn't block the sender.

    Each actors have an attached mailbox used to send him some any
    messages.
    """

    def __init__(self):
        self.messages = deque()
        self.channel = core.channel()
        self._lock = threading.RLock()

    def send(self, msg):
        """ append a message to the queue or if the actor is accepting
        messages send it directly to it """

        if self.channel is not None and self.channel.balance < 0:
            self.channel.send(msg)
        else:
            # no waiters append to the queue and return
            self.messages.append(msg)
            return

    def receive(self):
        """ fetch a message from the queue or wait for a new one """
        try:
            return self.messages.popleft()
        except IndexError:
            pass
        return self.channel.receive()

    def flush(self):
        with self._lock:
            while True:
                try:
                    yield self.messages.popleft()
                except IndexError:
                    raise StopIteration

    def clear(self):
        self.messages.clear()

class Actor(core.tasklet):

    """ An actor is like a tasklet but with a mailbox. """

    def __init__(self):
        core.tasklet.__init__(self)
        self.ref = ActorRef(self)
        self.links = []
        self.mailbox = Mailbox()

    @classmethod
    def spawn(cls, func, *args, **kwargs):
        instance = cls()

        # wrap func to be scheduled immediately
        def _func():
            func(*args, **kwargs)
            sleep(0.0)
        instance.bind(_func)
        instance.setup()
        return instance.ref

    @classmethod
    def spawn_link(cls, func, *args, **kwargs):
        curr = core.getcurrent()
        if not hasattr(curr, 'mailbox'):
            curr = cls.wrap(curr)

        if operator.indexOf(self.links, curr.ref) < 0:
            self.links.append(curr.ref)

        return cls.spawn(func, *args, **kwargs)

    @classmethod
    def spawn_after(cls, seconds, func, *args, **kwargs):
        instance = cls()

        # wrap func to be scheduled immediately
        def _func():
            func(*args, **kwargs)
            sleep(0.0)

        def _deferred_spawn():
            instance.bind(_func)
            instance.setup()

        after_func(seconds, _deferred_spawn)
        return instance.ref

    def unlink(self, ref):
        idx = operator.indexOf(self.links, ref)
        if idx < 0:
            return
        with self._lock:
            del self.links[idx]

    @classmethod
    def wrap(cls, task):
        """ method to wrap a task to an actor """

        if hasattr(task, 'mailbox'):
            return

        actor = cls()
        task.__class__ = Actor
        for n, m in inspect.getmembers(actor):
            if not hasattr(task, n):
                setattr(task, n, m)

        setattr(task, 'mailbox', actor.mailbox)
        setattr(task, 'ref', actor.ref)
        setattr(task, 'links', actor.links)
        return task

    def send(self, msg):
        self.mailbox.send(msg)

    def receive(self):
        return self.mailbox.receive()

    def flush(self):
        return self.mailbox.flush()



spawn = Actor.spawn
spawn_link = Actor.spawn_link
spawn_after = Actor.spawn_after
wrap = Actor.wrap

def maybe_wrap(actor):
    if not hasattr(actor, 'mailbox'):
        return wrap(actor)
    return actor

def send(dest, msg):
    """ send a message to the destination """
    source = maybe_wrap(core.getcurrent())

    if isinstance(dest, six.string_types):
        dest = registry[dest]
    elif isinstance(dest, core.tasklet):
        dest = maybe_wrap(dest)

    mail = Message(source, dest, msg)
    mail.send()

def send_after(seconds, dest, msg):
    """ send a message after n seconds """

    if not seconds:
        return send(dest, msg)

    source = maybe_wrap(core.getcurrent())
    if isinstance(dest, six.string_types):
        dest = registry[dest]
    elif isinstance(dest, core.tasklet):
        dest = maybe_wrap(dest)

    mail = Message(source, dest, msg)
    mail.send_after(seconds)

def receive():
    curr = maybe_wrap(core.getcurrent())
    return curr.receive()

def flush():
    curr = maybe_wrap(core.getcurrent())
    curr.flush()

########NEW FILE########
__FILENAME__ = channel
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from collections import deque
import sys
import threading

import six

from flower.core.sched import (
    schedule, getcurrent, get_scheduler,
    schedrem, thread_ident
)

class bomb(object):
    def __init__(self, exp_type=None, exp_value=None, exp_traceback=None):
        self.type = exp_type
        self.value = exp_value
        self.traceback = exp_traceback

    def raise_(self):
        six.reraise(self.type, self.value, self.traceback)

class ChannelWaiter(object):

    __slots__ = ['scheduler', 'task', 'thread_id', 'arg']

    def __init__(self, task, scheduler, arg):
        self.task = task
        self.scheduler = scheduler
        self.arg = arg
        self.thread_id = thread_ident()

    def __str__(self):
        "waiter: %s" % str(self.task)

class channel(object):
    """
    A channel provides a mechanism for two concurrently executing
    functions to synchronize execution and communicate by passing a
    value of a specified element type. A channel is the only thread-safe
    operation.

    The capacity, in number of elements, sets the size of the buffer in
    the channel. If the capacity is greater than zero, the channel is
    asynchronous: communication operations succeed without blocking if
    the buffer is not full (sends) or not empty (receives), and elements
    are received in the order they are sent. If the capacity is zero or
    absent, the communication succeeds only when both a sender and
    receiver are ready.
    """


    def __init__(self, capacity=None, label=''):
        self.capacity = capacity
        self.closing = False
        self.recvq = deque()
        self.sendq = deque()
        self._lock = threading.Lock()
        self.label = label
        self.preference = -1
        self.schedule_all = False

    def __str__(self):
        return 'channel[%s](%s,%s)' % (self.label, self.balance, self.queue)

    def close(self):
        """
        channel.close() -- stops the channel from enlarging its queue.

        If the channel is not empty, the flag 'closing' becomes true.
        If the channel is empty, the flag 'closed' becomes true.
        """
        self.closing = True

    @property
    def balance(self):
        return len(self.sendq) - len(self.recvq)

    @property
    def closed(self):
        return self.closing and not self.queue

    def open(self):
        """
        channel.open() -- reopen a channel. See channel.close.
        """
        self.closing = False

    def enqueue(self, d, waiter):
        if d > 0:
            return self.sendq.append(waiter)
        else:
            return self.recvq.append(waiter)

    def dequeue(self, d):
        if d > 0:
            return self.recvq.popleft()
        else:
            return self.sendq.popleft()

    def _channel_action(self, arg, d):
        """
        d == -1 : receive
        d ==  1 : send

        the original CStackless has an argument 'stackl' which is not used
        here.

        'target' is the peer tasklet to the current one
        """

        assert abs(d) == 1

        do_schedule = False
        curr = getcurrent()
        source = ChannelWaiter(curr, get_scheduler(), arg)

        if d > 0:
            if not self.capacity:
                cando = self.balance < 0
            else:
                cando = len(self.recvq) <= self.capacity
            dir = d
        else:
            if not self.capacity:
                cando = self.balance > 0
            else:
                cando = len(self.sendq) <= self.capacity
            dir = 0

        if _channel_callback is not None:
            with self._lock:
                _channel_callback(self, getcurrent(), dir, not cando)

        if cando:
            # there is somebody waiting
            try:
                target = self.dequeue(d)
            except IndexError:
                # capacity is not None but nobody is waiting
                if d > 0:
                    self.enqueue(dir, ChannelWaiter(None, None, arg))
                return None

            source.arg, target.arg = target.arg, source.arg
            if target.task is not None:
                if self.schedule_all:
                    target.scheduler.unblock(target.task)
                    do_schedule = True
                elif self.preference == -d:
                    target.scheduler.unblock(target.task, False)
                    do_schedule = True
                else:
                    target.scheduler.unblock(target.task)
        else:
            # nobody is waiting
            source.task.blocked == 1
            self.enqueue(dir, source)
            schedrem(source.task)
            do_schedule = True

        if do_schedule:
            schedule()


        if isinstance(source.arg, bomb):
            source.arg.raise_()
        return source.arg

    def receive(self):
        """
        channel.receive() -- receive a value over the channel.
        If no other tasklet is already sending on the channel,
        the receiver will be blocked. Otherwise, the receiver will
        continue immediately, and the sender is put at the end of
        the runnables list.
        The above policy can be changed by setting channel flags.
        """
        return self._channel_action(None, -1)

    def send_exception(self, exp_type, msg):
        self.send(bomb(exp_type, exp_type(msg)))

    def send_sequence(self, iterable):
        for item in iterable:
            self.send(item)

    def send(self, msg):
        """
        channel.send(value) -- send a value over the channel.
        If no other tasklet is already receiving on the channel,
        the sender will be blocked. Otherwise, the receiver will
        be activated immediately, and the sender is put at the end of
        the runnables list.
        """
        return self._channel_action(msg, 1)


_channel_callback = None

def set_channel_callback(channel_cb):
    global _channel_callback
    _channel_callback = channel_cb

########NEW FILE########
__FILENAME__ = sched
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.


from collections import deque
import operator
import threading
import time

_tls = threading.local()

import greenlet
import six

from .util import thread_ident


class TaskletExit(Exception):
    pass

try:
    import __builtin__
    __builtin__.TaskletExit = TaskletExit
except ImportError:
    import builtins
    setattr(builtins, 'TaskletExit', TaskletExit)

CoroutineExit = TaskletExit
_global_task_id = 0

def _coroutine_getcurrent():
    try:
        return _tls.current_coroutine
    except AttributeError:
        return _coroutine_getmain()

def _coroutine_getmain():
    try:
        return _tls.main_coroutine
    except AttributeError:
        main = coroutine()
        main._is_started = -1
        main._greenlet = greenlet.getcurrent()
        _tls.main_coroutine = main
        return _tls.main_coroutine

class coroutine(object):
    """ simple wrapper to bind lazily a greenlet to a function """

    _is_started = 0

    def __init__(self):
        self._greenlet = greenlet

    def bind(self, func, *args, **kwargs):
        def _run():
            _tls.current_coroutine = self
            self._is_started = 1
            func(*args, **kwargs)
        self._is_started = 0
        self._greenlet = greenlet.greenlet(_run)

    def switch(self):
        current = _coroutine_getcurrent()
        try:
            self._greenlet.switch()
        finally:
            _tls.current_coroutine = current

    def kill(self):
        current = _coroutine_getcurrent()
        if self is current:
            raise CoroutineExit
        self.throw(CoroutineExit)

    def throw(self, *args):
        current = _coroutine_getcurrent()
        try:
            self._greenlet.throw(*args)
        finally:
            _tls.current_coroutine = current

    @property
    def is_alive(self):
        return self._is_started < 0 or bool(self._greenlet)

    @property
    def is_zombie(self):
        return self._is_started > 0 and bool(self._greenlet.dead)

    getcurrent = staticmethod(_coroutine_getcurrent)



def _scheduler_contains(value):
    scheduler = get_scheduler()
    return value in scheduler

def _scheduler_switch(current, next):
    scheduler = get_scheduler()
    return scheduler.switch(current, next)

class tasklet(coroutine):
    """
    A tasklet object represents a tiny task in a Python thread.
    At program start, there is always one running main tasklet.
    New tasklets can be created with methods from the stackless
    module.
    """
    tempval = None

    def __new__(cls, func=None, label=''):
        res = coroutine.__new__(cls)
        res.label = label
        res._task_id = None
        return res


    def __init__(self, func=None, label=''):
        coroutine.__init__(self)
        self._init(func, label)

    def _init(self, func=None, label=''):
        global _global_task_id
        self.func = func
        self.label = label
        self.alive = False
        self.blocked = False
        self.sched = None
        self.thread_id = thread_ident()
        self._task_id = _global_task_id
        _global_task_id += 1

    def __str__(self):
        return '<tasklet[%s, %s]>' % (self.label,self._task_id)

    __repr__ = __str__

    def __call__(self, *argl, **argd):
        return self.setup(*argl, **argd)

    def bind(self, func):
        """
        Binding a tasklet to a callable object.
        The callable is usually passed in to the constructor.
        In some cases, it makes sense to be able to re-bind a tasklet,
        after it has been run, in order to keep its identity.
        Note that a tasklet can only be bound when it doesn't have a frame.
        """
        if not six.callable(func):
            raise TypeError('tasklet function must be a callable')
        self.func = func


    def setup(self, *argl, **argd):
        """
        supply the parameters for the callable
        """
        if self.func is None:
            raise TypeError('tasklet function must be callable')
        func = self.func
        sched = self.sched = get_scheduler()

        def _func():

            try:
                try:
                    func(*argl, **argd)
                except TaskletExit:
                    pass
            finally:
                sched.remove(self)
                self.alive = False

        self.func = None
        coroutine.bind(self, _func)
        self.alive = True
        sched.append(self)
        return self

    def run(self):
        self.insert()
        _scheduler_switch(getcurrent(), self)

    def kill(self):
        if self.is_alive:
            # Killing the tasklet by throwing TaskletExit exception.
            coroutine.kill(self)

        schedrem(self)
        self.alive = False

    def raise_exception(self, exc, *args):
        if not self.is_alive:
            return
        schedrem(self)
        coroutine.throw(self, exc, *args)


    def insert(self):
        if self.blocked:
            raise RuntimeError("You cannot run a blocked tasklet")
            if not self.alive:
                raise RuntimeError("You cannot run an unbound(dead) tasklet")
        schedpush(self)

    def remove(self):
        if self.blocked:
            raise RuntimeError("You cannot remove a blocked tasklet.")
        if self is getcurrent():
            raise RuntimeError("The current tasklet cannot be removed.")
        schedrem(self)

class Scheduler(object):

    def __init__(self):
        # define the main tasklet
        self._main_coroutine = _coroutine_getmain()
        self._main_tasklet = _coroutine_getcurrent()
        self._main_tasklet.__class__ = tasklet
        six.get_method_function(self._main_tasklet._init)(self._main_tasklet,
                label='main')
        self._last_task = self._main_tasklet

        self.thread_id = thread_ident() # the scheduler thread id
        self._lock = threading.Lock() # global scheduler lock

        self._callback = None # scheduler callback
        self._run_calls = [] # runcalls. (tasks where run apply
        self.runnable = deque() # runnable tasks
        self.blocked = 0 # number of blocked/sleeping tasks
        self.append(self._main_tasklet)

    def send(self):
        self._async.send()

    def wakeup(self, handle):
        self.schedule()

    def set_callback(self, cb):
        self._callback = cb

    def append(self, value, normal=True):
        if normal:
            self.runnable.append(value)
        else:
            self.runnable.rotate(-1)
            self.runnable.appendleft(value)
            self.runnable.rotate(1)

    def appendleft(self, task):
        self.runnable.appendleft(task)

    def remove(self, task):
        """ remove a task from the runnable """

        # the scheduler need to be locked here
        with self._lock:
            try:
                self.runnable.remove(task)
                # if the task is blocked increment their number
                if task.blocked:
                    self.blocked += 1
            except ValueError:
                pass

    def unblock(self, task, normal=True):
        """ unblock a task (put back from sleep)"""
        with self._lock:
            task.blocked = 0
            self.blocked -= 1
        self.append(task, normal)

    def taskwakeup(self, task):
        if task is None:
            return

        # the scheduler need to be locked here
        with self._lock:
            try:
                self.runnable.remove(task)
            except ValueError:
                pass

        # eventually unblock the tasj
        self.unblock(task)

    def switch(self, current, next):
        prev = self._last_task
        if (self._callback is not None and prev is not next):
            self._callback(prev, next)
        self._last_task = next


        assert not next.blocked

        if next is not current:
            next.switch()

        return current

    def schedule(self, retval=None):
        curr = self.getcurrent()
        main = self.getmain()

        if retval is None:
            retval = curr

        while True:
            if self.runnable:
                if self.runnable[0] is curr:
                    self.runnable.rotate(-1)
                task = self.runnable[0]
            elif self._run_calls:
                task = self._run_calls.pop()
            else:
                raise RuntimeError("no more tasks are sleeping")


            # switch to next task
            self.switch(curr, task)

            # exit the loop if there are no more tasks
            if curr is self._last_task:
                return retval

    def run(self):
        curr = self.getcurrent()
        self._run_calls.append(curr)
        self.remove(curr)
        try:
            while True:
                self.schedule()
                if not curr.blocked:
                    break
                time.sleep(0.0001)
        finally:
            self.append(curr)

    def runcount(self):
        return len(self.runnable)

    def getmain(self):
        return self._main_tasklet

    def getcurrent(self):
        curr = _coroutine_getcurrent()
        if curr == self._main_coroutine:
            return self._main_tasklet
        else:
            return curr

    def __contains__(self, value):
        try:
            operator.indexOf(self.runnable, value)
            return True
        except ValueError:
            return False

_channel_callback = None

def set_channel_callback(channel_cb):
    global _channel_callback
    _channel_callback = channel_cb


def get_scheduler():
    global _tls
    try:
        return _tls.scheduler
    except AttributeError:
        scheduler = _tls.scheduler = Scheduler()
        return scheduler


def taskwakeup(task):
    sched = get_scheduler()
    sched.taskwakeup(task)

def getruncount():
    sched = get_scheduler()
    return sched.runcount()

def getcurrent():
    return get_scheduler().getcurrent()

def getmain():
    return get_scheduler().getmain()

def set_schedule_callback(scheduler_cb):
    sched = get_scheduler()
    sched.set_callback(scheduler_cb)

def schedule(retval=None):
    scheduler = get_scheduler()
    return scheduler.schedule(retval=retval)

def schedule_remove(retval=None):
    scheduler = get_scheduler()
    scheduler.remove(scheduler.getcurrent())
    return scheduler.schedule(retval=retval)

def schedpush(task):
    scheduler = get_scheduler()
    scheduler.append(task)

def schedrem(task):
    scheduler = get_scheduler()
    scheduler.remove(task)

def run():
    sched = get_scheduler()
    sched.run()

# bootstrap the scheduler
def _bootstrap():
    get_scheduler()
_bootstrap()

########NEW FILE########
__FILENAME__ = timer
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import heapq
import operator
import threading

import six

from .util import nanotime
from .sched import (tasklet, schedule, schedule_remove, get_scheduler,
        getcurrent, taskwakeup, getmain)
from .channel import channel

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


    def add(self, t):
        with self._lock:
            self._add_timer(t)

            if self.sleeping:
                self.sleeping = False
                taskwakeup(self._timerproc)

            if self._timerproc is None or not self._timerproc.alive:
                self._timerproc = tasklet(self.timerproc)()

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

            while True:
                if not len(self._heap):
                    delta = -1
                    break

                t = heapq.heappop(self._heap)
                now = nanotime()
                delta = t.when - now
                if delta > 0:
                    heapq.heappush(self._heap, t)
                    break
                else:
                    # repeat ? reinsert the timer
                    if t.period is not None and t.period > 0:
                        np = nanotime(t.period)
                        t.when += np * (1 - delta/np)
                        heapq.heappush(self._heap, t)

                    # run
                    self._lock.release()
                    t.callback(now, t, *t.args, **t.kwargs)
                    self._lock.acquire()


            if delta < 0:
                self.sleeping = True
                self._lock.release()
                schedule_remove()
            else:
                self._lock.release()
                schedule()

timers = Timers()
add_timer = timers.add
remove_timer = timers.remove


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
        self.when = nanotime() + nanotime(self.interval)
        add_timer(self)

    def stop(self):
        remove_timer(self)
        self.active = False

    def __lt__(self, other):
        return self.when < other.when

    __cmp__ = __lt__

def sleep(seconds=0):
    if not seconds:
        return

    sched = get_scheduler()
    curr = getcurrent()

    c = channel()
    def ready(now, t):
        c.send(None)

    t = Timer(ready, seconds)
    t.start()
    c.receive()

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import time

try:
    from thread import get_ident as thread_ident
except ImportError:
    from _thread import get_ident as thread_ident


def nanotime(s=None):
    """ convert seconds to nanoseconds. If s is None, current time is
    returned """
    if s is not None:
        return s * 1000000000
    return time.time() * 1000000000

def from_nanotime(n):
    """ convert from nanotime to seconds """
    return n / 1.0e9

########NEW FILE########
__FILENAME__ = uv
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import sys
import threading

_tls = threading.local()

import pyuv

from flower.core.channel import channel
from flower.core.sched import tasklet, getcurrent, schedule

def get_fd(io):
    if not isinstance(io, int):
        if hasattr(io, 'fileno'):
            if callable(io.fileno):
                fd = io.fileno()
            else:
                fd = io.fileno
        else:
            raise ValueError("invalid file descriptor number")
    else:
        fd = io
    return fd


def uv_mode(m):
    if m == 0:
        return pyuv.UV_READABLE
    elif m == 1:
        return pyuv.UV_WRITABLE
    else:
        return pyuv.UV_READABLE | pyuv.UV_WRITABLE

class UVExit(Exception):
    pass


class UV(object):

    def __init__(self):
        self.loop = pyuv.Loop()
        self._async = pyuv.Async(self.loop, self._wakeloop)
        self._async.unref()
        self.fds = {}
        self._lock = threading.RLock()
        self.running = False

        # start the server task
        self._runtask = tasklet(self.run, "uv_server")()

    def _wakeloop(self, handle):
        self.loop.update_time()

    def wakeup(self):
        self._async.send()

    def switch(self):
        if not self.running:
            self._runtask = tasklet(self.run)()

        getcurrent().remove()
        self._runtask.switch()

    def idle(self, handle):
        if getcurrent() is self._runtask:
            schedule()

    def run(self):
        t = pyuv.Timer(self.loop)
        t.start(self.idle, 0.0001, 0.0001)
        t.unref()
        self.running = True
        try:
            self.loop.run()
        finally:
            self.running = False

def uv_server():
    global _tls

    try:
        return _tls.uv_server
    except AttributeError:
        uv_server = _tls.uv_server = UV()
        return uv_server

def uv_sleep(seconds, ref=True):
    """ use the event loop for sleep. This an alternative to our own
    time events scheduler """

    uv = uv_server()
    c = channel()
    def _sleep_cb(handle):
        handle.stop()
        c.send(None)

    sleep = pyuv.Timer(uv.loop)
    sleep.start(_sleep_cb, seconds, seconds)
    if not ref:
        sleep.unref()

    c.receive()

def uv_idle(ref=True):
    """ use the event loop for idling. This an alternative to our own
    time events scheduler """

    uv = uv_server()
    c = channel()
    def _sleep_cb(handle):
        handle.stop()
        c.send(True)


    idle = pyuv.Idle(uv.loop)
    idle.start(_sleep_cb)
    if not ref:
        idle.unref()

    return c.receive()

########NEW FILE########
__FILENAME__ = io
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pyuv
from flower.core import channel
from flower.core.uv import get_fd, uv_mode, uv_server

from pyuv import errno

class IOChannel(channel):
    """ channel to wait on IO events for a specific fd. It now use the UV server
    facility.

        mode:
        0: read
        1: write
        2: read & write"""

    def __init__(self, io, mode=0, label=''):
        super(IOChannel, self).__init__(label=label)

        fno = get_fd(io)
        self.io = io
        uv = uv_server()
        self._poller = pyuv.Poll(uv.loop, fno)
        self._poller.start(uv_mode(mode), self._tick)

    def _tick(self, handle, events, error):
        if error:
            if error == errno.UV_EBADF:
                self.handle.close()
                self.send(events)
            else:
                self.send_exception(IOError, "uv error: %s" % errno)
        else:
            self.send(events)

    def stop(self):
        self._poller.stop()
        self.close()

def wait_read(io):
    """ wrapper around IOChannel to only wait when a device become
    readable """
    c = IOChannel(io)
    try:
        return c.receive()
    finally:
        c.close()

def wait_write(io):
    """ wrapper around IOChannel to only wait when a device become
    writable """
    c = IOChannel(io, 1)
    try:
        return c.receive()
    finally:
        c.close()

########NEW FILE########
__FILENAME__ = local
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import weakref
from flower.core import getcurrent


class local(object):
    """ a local class working like a thread.local class to keep local
    attributes for a given tasklet """

    class _local_attr(object): pass

    def __init__(self):
        self._d = weakref.WeakKeyDictionary()

    def __getattr__(self, key):
        d = self._d
        curr = getcurrent()
        if not curr in d or not hasattr(d[curr], key):
            raise AttributeError(key)
        return getattr(d[curr], key)

    def __setattr__(self, key, value):
        if key == '_d':
            self.__dict__[key] = value
            object.__setattr__(self, key, value)
        else:
            d = self._d
            curr = getcurrent()
            if not curr in d:
                d[curr] = self._local_attr()
            setattr(d[curr], key, value)

    def __delattr__(self, key):
        d = self._d
        curr = getcurrent()
        if not curr in d or not hasattr(d[curr], key):
            raise AttributeError(key)
        delattr(d[curr], key)

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from flower.core import channel, getcurrent, get_scheduler
from flower.core.uv import uv_server

class NoMoreListener(Exception):
    pass

class Listener(object):

    def __init__(self):
        self.task = getcurrent()
        self.uv = uv_server()
        self.sched = get_scheduler()
        self.c = channel()


    @property
    def loop(self):
        return self.uv.loop


class IConn(object):
    """ connection interface """

    def read(self):
        """ return data """

    def write(self, data):
        """ send data to the remote connection """

    def writelines(self, seq):
        """ send data using a list or an iterator to the remote
        connection """

    def local_addr(self):
        """ return the local address """

    def remote_addr(self):
        """ return the remote address """

    @property
    def status(self):
        """ return current status """
        if self.client.closed:
            return "closed"
        elif self.client.readable and self.client.writable:
            return "open"
        elif self.client.readable and not self.client.writable:
            return "readonly"
        elif not self.client.readable and self.client.writable:
            return "writeonly"
        else:
            return "closed"


class IListen(object):

    def accept(self):
        """ accept a connection. Return a Conn instance. It always
        block the current task """

    def close(self):
        """ stop listening """

    def addr(self):
        " return the bound address """

class IDial(object):

    """ base interface for Dial class """

########NEW FILE########
__FILENAME__ = pipe
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pyuv

from flower.core import channel
from flower.core.uv import uv_server
from flower.net.tcp import TCPListen, TCPConn

class PipeConn(TCPConn):
    """ A Pipe connection """


class PipeListen(TCPListen):
    """ A Pipe listener """

    CONN_CLASS = PipeConn
    HANDLER_CLASS = pyuv.Pipe

def dial_pipe(addr):
    uv = uv_server()
    h = pyuv.Pipe(uv.loop)

    c = channel()
    def _on_connect(handle, error):
        c.send((handle, error))

    h.connect(addr, _on_connect)
    h1, error = c.receive()
    return (PipeConn(h1), error)

########NEW FILE########
__FILENAME__ = sock
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from collections import deque
from io import DEFAULT_BUFFER_SIZE
import os
import threading

import socket
import sys

import pyuv

from flower.core import (channel, schedule, getcurrent, bomb)
from flower.core.uv import uv_server
from flower.net.base import IConn, Listener, IListen, NoMoreListener
from flower.net.util import parse_address, is_ipv6

IS_WINDOW = sys.platform == 'win32'

if IS_WINDOW:
    from errno import WSAEWOULDBLOCK as EWOULDBLOCK
    EAGAIN = EWOULDBLOCK
else:
    from errno import EWOULDBLOCK

try:
    from errno import EBADF
except ImportError:
    EBADF = 9

# sys.exc_clear was removed in Python3 as the except block of a try/except
# performs the same task. Add it as a no-op method.
try:
    sys.exc_clear
except AttributeError:
    def exc_clear():
        return
    sys.exc_clear = exc_clear

if sys.version_info < (2, 7, 0, 'final'):
    # in python 2.6 socket.recv_into doesn't support bytesarray
    def recv_into(sock, b):
        l = max(len(b), DEFAULT_BUFFER_SIZE)
        buf = sock.recv(l)
        recved = len(buf)
        b[0:recved] = buf
        return recved
else:
    def recv_into(sock, b):
        return sock.recv_into(b)

# from gevent code
if sys.version_info[:2] < (2, 7):
    _get_memory = buffer
elif sys.version_info[:2] < (3, 0):
    def _get_memory(string, offset):
        try:
            return memoryview(string)[offset:]
        except TypeError:
            return buffer(string, offset)
else:
    def _get_memory(string, offset):
        return memoryview(string)[offset:]


class SockConn(IConn):

    def __init__(self, client, laddr, addr):
        # set connection info
        self.client = client
        self.client.setblocking(0)
        self.timeout = socket.getdefaulttimeout()
        self.laddr = laddr
        self.addr = addr

        # utilies used to fetch & send ata
        self.cr = channel() # channel keeping readers waiters
        self.cw = channel() # channel keeping writers waiters
        self.queue = deque() # queue of readable data
        self.uv = uv_server()
        self.rpoller = None
        self.wpoller = None
        self._lock = threading.RLock()
        self.ncr = 0 # reader refcount
        self.ncw = 0 # writer refcount

        self.closing = False


    def read(self):
        if self.closing:
            return ""

        while True:
            try:
                retval = self.queue.popleft()
                if self.cr.balance < 0:
                    self.cr.send(retval)

                if isinstance(retval, bomb):
                    retval.raise_()

                return retval
            except IndexError:
                pass

            msg = None
            buf = bytearray(DEFAULT_BUFFER_SIZE)
            try:
                recvd = recv_into(self.client, buf)
                msg =  bytes(buf[0:recvd])
            except socket.error:
                ex = sys.exc_info()[1]
                if ex.args[0] == EBADF:
                    msg = ""
                    self.closing = True
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    msg = bomb(ex, sys.exc_info()[2])
                    self.closing = True
                exc_clear()

            if msg is None:
                res = self._watch_read()
                if res is not None:
                    self.queue.append(res)

            else:
                self.queue.append(msg)

    def write(self, data):
        data_sent = 0
        while data_sent < len(data):
            data_sent += self._send(_get_memory(data, data_sent))

    def writelines(self, seq):
        for data in seq:
            self.write(data)

    def local_addr(self):
        return self.laddr

    def remote_addr(self):
        return self.addr

    def close(self):
        self.client.close()

        # stop polling
        if self.wpoller is not None:
            self.wpoller.stop()
            self.wpoller = None

        if self.rpoller is not None:
            self.rpoller.stop()
            self.rpoller = None

    def _watch_read(self):
        self._lock.acquire()
        if not self.rpoller:
            self.rpoller = pyuv.Poll(self.uv.loop, self.client.fileno())
            self.rpoller.start(pyuv.UV_READABLE, self._on_read)

        # increase the reader refcount
        self.ncr += 1
        self._lock.release()
        try:
            self.cr.receive()
        finally:
            self._lock.acquire()
            # decrease the refcount
            self.ncr -= 1
            # if no more waiters, close the poller
            if self.ncr <= 0:
                self.rpoller.stop()
                self.rpoller = None
            self._lock.release()

    def _on_read(self, handle, events, error):
        if error and error is not None:
            self.readable = False
            if error == 1:
                self.closing = True
                msg = ""
            else:
                msg = bomb(IOError, IOError("uv error: %s" % error))
        else:
            self.readable = True
            msg = None
        self.cr.send(msg)

    def _send(self, data):
        while True:
            try:
               return self.client.send(data)
            except socket.error:
                ex = sys.exc_info()[1]
                if ex.args[0] == EBADF:
                    self.closing = True
                    return
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    raise
                exc_clear()

            # wait for newt write
            self._watch_write()

    def _watch_write(self):
        self._lock.acquire()

        # create a new poller
        if not self.wpoller:
            self.wpoller = pyuv.Poll(self.uv.loop, self.client.fileno())
            self.wpoller.start(pyuv.UV_WRITABLE, self._on_write)

        # increase the writer refcount
        self.ncw += 1

        self._lock.release()

        try:
            self.cw.receive()
        finally:
            self._lock.acquire()
            self.ncw -= 1
            if self.ncw <= 0:
                self.wpoller.stop()
                self.wpoller = None
            self._lock.release()


    def _on_write(self, handle, events, errors):
        if not errors:
            self.cw.send()

    def _read(self):
        buf = bytearray(DEFAULT_BUFFER_SIZE)
        try:
            recvd = recv_into(self.client, buf)
            msg =  bytes(buf[0:recvd])
        except socket.error:
            ex = sys.exc_info()[1]
            if ex.args[0] == EBADF:
                msg =  ""
            if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                msg = bomb(ex, sys.exc_info()[2])
            exc_clear()
        return msg


class TCPSockListen(IListen):

    def __init__(self, addr, *args, **kwargs):

        sock = None
        fd = None
        if "sock" in kwargs:
            # we passed a socket in the kwargs, just use it
            sock = kwargs['sock']
            fd = sock.fileno()
        elif isinstance(addr, int):
            # we are reusing a socket here
            fd = addr
            if "family" not in kwargs:
                family = socket.AF_INET
            else:
                family = kwargs['family']
            sock = socket.fromfd(fd, family, socket.SOCK_STREAM)
        else:
            # new socket
            addr = parse_address(addr)
            if is_ipv6(addr[0]):
                family = socket.AF_INET6
            else:
                family = socket.AF_INET

            sock = socket.socket(family, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            nodelay = kwargs.get('nodelay', True)
            if family == socket.AF_INET and nodelay:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            sock.bind(addr)
            sock.setblocking(0)
            fd = sock.fileno()

        self.sock = sock
        self.fd = fd
        self.addr = addr
        self.backlog = kwargs.get('backlog', 128)
        self.timeout = socket.getdefaulttimeout()
        self.uv = uv_server()
        self.poller = None
        self.listeners = deque()
        self.task = getcurrent()

        # start to listen
        self.sock.listen(self.backlog)

    def accept(self):
        """ start the accept loop. Let the OS handle accepting balancing
        between listeners """

        if self.poller is None:
            self.poller = pyuv.Poll(self.uv.loop, self.fd)
            self.poller.start(pyuv.UV_READABLE, self._on_read)

        listener = Listener()
        self.listeners.append(listener)
        return listener.c.receive()

    def addr(self):
        return self.addr

    def close(self):
        if self.poller is not None:
            self.poller.stop()
        self.sock.close()

    def _on_read(self, handle, events, error):
        if error:
            handle.stop()
            self.poller = None
        else:
            res = None
            try:
                res = self.sock.accept()
            except socket.error:
                exc_info = sys.exc_info()
                ex = exc_info[1]
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    self.task.throw(*exc_info)
                exc_clear()

            if res is not None:
                client, addr = res
                self._on_connection(client, addr)

    def _on_connection(self, client, addr):
        if len(self.listeners):
            listener = self.listeners.popleft()

            self.uv.wakeup()

            # return a new connection object to the listener
            conn =  SockConn(client, self.addr, addr)
            listener.c.send((conn, None))
            schedule()
        else:
            # we should probably do something there to drop connections
            self.task.throw(NoMoreListener)

class PipeSockListen(TCPSockListen):

    def __init__(self, addr, *args, **kwargs):
        fd = kwargs.get('fd')
        if fd is None:
            try:
                os.remove(addr)
            except OSError:
                pass

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if fd is None:
            sock.bind(addr)
        sock.setblocking(0)

        self.sock = sock
        self.fd = fd
        self.addr = addr
        self.backlog = kwargs.get('backlog', 128)
        self.timeout = socket.getdefaulttimeout()

        # start to listen
        self.sock.listen(self.backlog)

########NEW FILE########
__FILENAME__ = tcp
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from collections import deque
import pyuv


from flower.core.uv import uv_server
from flower.core import (channel, schedule, getcurrent, get_scheduler,
        bomb)
from flower.net.base import IConn, Listener, IListen, NoMoreListener

class TCPConn(IConn):

    def __init__(self, client):
        self.client = client
        self.reading = False
        self.cr = channel()
        self.queue = deque()

    def read(self):
        if not self.reading:
            self.reading = True
            self.client.start_read(self._on_read)

        self.client.loop.update_time()
        try:
            retval = self.queue.popleft()
            if self.cr.balance < 0:
                self.cr.send(retval)

            if isinstance(retval, bomb):
                retval.raise_()
            return retval
        except IndexError:
            pass

        return self.cr.receive()

    def write(self, data):
        return self.client.write(data)

    def writelines(self, seq):
        return self.client.writelines(seq)

    def _wait_write(self, func, data):
        c = channel()
        def _wait_cb(handle, err):
            c.send(True)

        func(data, _wait_cb)
        c.receive()


    def local_address(self):
        return self.client.getsockame()

    def remote_address(self):
        return self.client.getpeername()

    def close(self):
        self.client.close()

    def _on_read(self, handle, data, error):
        if error:
            if error == 1: # EOF
                msg = ""
            else:
                msg = bomb(IOError, IOError("uv error: %s" % error))
        else:
            msg = data

        # append the message to the queue
        self.queue.append(msg)

        if self.cr.balance < 0:
            # someone is waiting, return last message
            self.cr.send(self.queue.popleft())

class TCPListen(IListen):
    """ A TCP listener """

    CONN_CLASS = TCPConn # connection object returned
    HANDLER_CLASS = pyuv.TCP # pyuv class used to handle the conenction

    def __init__(self, addr=('0.0.0.0', 0)):
        # listeners are all couroutines waiting for a connections
        self.listeners = deque()
        self.uv = uv_server()
        self.sched = get_scheduler()
        self.task = getcurrent()
        self.listening = False

        self.handler = self.HANDLER_CLASS(self.uv.loop)
        self.handler.bind(addr)

    def accept(self):
        listener = Listener()
        self.listeners.append(listener)

        if not self.listening:
            self.handler.listen(self.on_connection)
        return listener.c.receive()

    def close(self):
        self.handler.close()

    def on_connection(self, server, error):
        if len(self.listeners):
            listener = self.listeners.popleft()

            # accept the connection
            client = pyuv.TCP(server.loop)
            server.accept(client)

            self.uv.wakeup()
            # return a new connection object to the listener
            conn = self.CONN_CLASS(client)
            listener.c.send((conn, error))
            schedule()
        else:
            # we should probably do something there to drop connections
            self.task.throw(NoMoreListener)


def dial_tcp(addr):
    uv = uv_server()
    h = pyuv.TCP(uv.loop)

    c = channel()
    def _on_connect(handle, error):
        if error:
            c.send_exception(IOError, "uv error: %s" % error)
        else:
            c.send(handle)

    h.connect(addr, _on_connect)
    h1 = c.receive()
    return TCPConn(h1)

########NEW FILE########
__FILENAME__ = udp
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from collections import deque

from flower.core import channel, schedule, getcurrent, bomb
from flower.core.uv import uv_server
from flower.net.base import Listener, IConn, IListen, NoMoreListener

import pyuv

class UDPConn(IConn):

    def __init__(self, addr, raddr, client=None):
        self.uv = uv_server()
        if client is None:
            self.client = pyuv.UDP(self.uv.loop)
            self.client.bind(raddr)
        else:
            self.client = client
        self.reading = True
        self.queue = deque()
        self.cr = channel
        self._raddr = raddr
        self.addr = addr

    def read(self):
        try:
            retval = self.queue.popleft()
            if self.cr.balance < 0:
                self.cr.send(retval)

            if isinstance(retval, bomb):
                retval.raise_()
            return retval
        except IndexError:
            pass

        return self.cr.receive()

    def write(self, data):
        self.client.send(self._remote_addr, data)

    def writelines(self, seq):
        self.client.sendlines(self._remote_addr, seq)

    def local_addr(self):
        return self.client.getsockame()

    def remote_addr(self):
        return self.remote_addr

class UDPListen(IListen):

    def __init__(self, addr=('0.0.0.0', 0)):
        # listeners are all couroutines waiting for a connections
        self.listeners = deque()

        self.conns = {}
        self.uv = uv_server()
        self.task = getcurrent()
        self.listening = False
        self.handler = pyuv.UDP(self.uv.loop)
        self.handler.bind(addr)

    def accept(self):
        listener = Listener()
        self.listeners.append(listener)

        if not self.listening:
            self.handler.start_recv(self.on_recv)

        return listener.c.receive()

    def on_recv(self, handler, addr, data, error):
        with self._lock:
            if addr in self.conns:
                conn = self.conns[addr]

                if error:
                    if error == 1:
                        msg = ""
                    else:
                        msg = bomb(IOError, IOError("uv error: %s" % error))
                else:
                    msg = data

                # emit last message
                conn.queue.append(msg)
                if conn.cr.balance < 0:
                    # someone is waiting, return last message
                    conn.cr.send(self.queue.popleft())

            elif len(self.listeners):
                listener = self.listeners.popleft()
                if error:
                    listener.c.send_exception(IOError, "uv error: %s" % error)
                else:
                    conn = UDPConn(addr)
                    conn.queue.append(data)
                    self.conns[addr] = conn
                    listener.c.send(conn, error)
            else:
                # we should probably do something there to drop connections
                self.task.throw(NoMoreListener)


            schedule()

    def addr(self):
        return self.handler.getsockname()

def dial_udp(laddr, raddr):
    uv = uv_server()
    h = pyuv.UDP(uv.loop)
    h.bind(laddr)

    return (UDPConn(laddr, raddr, h), None)

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import socket

def is_ipv6(addr):
    try:
        socket.inet_pton(socket.AF_INET6, addr)
    except socket.error: # not a valid address
        return False
    return True

def parse_address(netloc, default_port=0):
    if isinstance(netloc, tuple):
        return netloc

    # get host
    if '[' in netloc and ']' in netloc:
        host = netloc.split(']')[0][1:].lower()
    elif ':' in netloc:
        host = netloc.split(':')[0].lower()
    elif netloc == "":
        host = "0.0.0.0"
    else:
        host = netloc.lower()

    #get port
    netloc = netloc.split(']')[-1]
    if ":" in netloc:
        port = netloc.split(':', 1)[1]
        if not port.isdigit():
            raise RuntimeError("%r is not a valid port number." % port)
        port = int(port)
    else:
        port = default_port
    return (host, port)


########NEW FILE########
__FILENAME__ = registry
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import operator
import threading

import six

from flower import core
from flower.local import local

_local = local()

class Registry(object):
    """ actors registry. This rgistry is used to keep a trace of created
    actors """

    __slots__ = ['__dict__', '_lock']

    # share state between instances
    __shared_state__ = dict(
            _registered_names = {},
            _by_ref = {}
    )

    def __init__(self):
        self.__dict__ = self.__shared_state__
        self._lock = threading.RLock()


    def register(self, name, ref):
        """ register an actor ref with a name in the registry """
        with self._lock:

            if name in self._registered_names:
                if self._registered_names[name] == ref:
                    return
                raise KeyError("An actor is already registered for this name")

            self._registered_names[name] = ref
            if not ref in self._by_ref:
                self._by_ref[ref] = [name]
            else:
                self._by_ref[ref].append(name)

    def unregister(self, ref_or_name):
        """ unregister a name in the registery. If the name doesn't
        exist we safely ignore it. """
        try:
            if isinstance(ref_or_name, six.string_types):
                with self._lock:
                    ref = self._registered_names[ref_or_name]
                    names = self._by_ref[ref]
                    del names[operator.indexOf(names, ref_or_name)]
                    del self._registered_names[ref_or_name]
            else:
                with self._lock:
                    names = self._by_ref[ref_or_name]
                    for name in names:
                        del self._registered_names[name]
        except (KeyError, IndexError):
            pass

    def registered(self, ref=None):
        """ get an actor by it's ref """
        print(type(core.getcurrent()))
        if ref is None:
            try:
                ref = core.getcurrent().ref
            except AttributeError:
                return []


        print(ref)
        print(self._by_ref)

        if ref not in self._by_ref:
            return []
        print(self._by_ref[ref])
        return sorted(self._by_ref[ref])

    def by_name(self, name):
        """ get an actor by name """
        try:
            return self._registered_names[name]
        except KeyError:
            return None

    def __getitem__(self, ref_or_name):
        if isinstance(ref_or_name, six.string_types):
            return self.by_name(ref_or_name)
        else:
            return self.registered(ref_or_name)

    def __delitem__(self, ref_or_name):
        self.unregister(ref_or_name)

    def __contains__(self, ref_or_name):
        with self._lock:
            if isinstance(ref_or_name, six.string_types):
                return ref_or_name in self._registered_names
            else:
                return ref_or_name in self._by_ref

    def __iter__(self):
        return iter(self._registered_name.items())


registry = Registry()
register = registry.register
unregister = registry.unregister
registered = registry.registered

########NEW FILE########
__FILENAME__ = time
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information


time = __import__('time').time

from flower import core
from flower.core import timer
from flower.core.util import from_nanotime

class Ticker(core.channel):
    """A Ticker holds a synchronous channel that delivers `ticks' of a
    clock at intervals."""

    def __init__(self, interval, label=''):
        super(Ticker, self).__init__(label=label)
        self._interval = interval
        self._timer = timer.Timer(self._tick, interval, interval)
        self._timer.start()

    def _tick(self, now, h):
        self.send(from_nanotime(now))

    def stop(self):
        self._timer.stop()

def idle():
    """ By using this function the current tasklet will be scheduled asap"""

    sched = core.get_scheduler()
    curr = core.getcurrent()
    def ready(now, h):
        curr.blocked = False
        sched.append(curr)
        core.schedule()

    t = timer.Timer(ready, 0.0001)
    t.start()

    curr.blocked = True
    core.schedule_remove()

def sleep(seconds=0):
    """ sleep the current tasklet for a while"""
    if not seconds:
        idle()
    else:
        timer.sleep(seconds)

def after_func(d, f, *args, **kwargs):
    """ AfterFunc waits for the duration to elapse and then calls f in
    its own coroutine. It returns a Timer that can be used to cancel the
    call using its stop method. """

    def _func(now, handle):
        core.tasklet(f)(*args, **kwargs)
        core.schedule()

    t = timer.Timer(_func, d)
    t.start()
    return t

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import os
import sys


def cpu_count():
    '''
    Returns the number of CPUs in the system
    '''
    if sys.platform == 'win32':
        try:
            num = int(os.environ['NUMBER_OF_PROCESSORS'])
        except (ValueError, KeyError):
            num = 0
    elif 'bsd' in sys.platform or sys.platform == 'darwin':
        comm = '/sbin/sysctl -n hw.ncpu'
        if sys.platform == 'darwin':
            comm = '/usr' + comm
        try:
            with os.popen(comm) as p:
                num = int(p.read())
        except ValueError:
            num = 0
    else:
        try:
            num = os.sysconf('SC_NPROCESSORS_ONLN')
        except (ValueError, OSError, AttributeError):
            num = 0

    if num >= 1:
        return num
    else:
        raise NotImplementedError('cannot determine number of cpus')

########NEW FILE########
__FILENAME__ = test_actor
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from flower.actor import (receive, send, spawn, spawn_after, ActorRef,
        send_after, wrap, Actor)
from flower import core
from flower.time import sleep
import time

class Test_Actor:

    def test_simple(self):
        r_list = []
        def f():
            r_list.append(True)

        pid = spawn(f)
        assert isinstance(pid, ActorRef)
        assert pid.ref == 0
        assert hasattr(pid.actor, 'mailbox')

        sleep(0.1)
        core.run()

        assert r_list == [True]
        assert pid.actor is None
        assert pid.is_alive is False

    def test_wrap(self):
        r_list = []
        def f():
            r_list.append(True)

        t = core.tasklet(f)()
        assert not hasattr(t, 'mailbox')
        wrap(t)
        assert isinstance(t, Actor)
        assert hasattr(t, 'mailbox')
        assert hasattr(t, 'ref')

        pid = t.ref
        assert isinstance(pid, ActorRef)
        assert pid.ref == 1

        core.run()
        assert r_list == [True]
        assert pid.actor is None
        assert pid.is_alive is False


    def test_mailbox(self):
        messages = []
        sources = []
        def f():
            while True:
                source, msg = receive()
                if not msg:
                    break
                if source.ref not in sources:
                    sources.append(source.ref)
                messages.append(msg)

        def f1(ref):
            msg = ['hello', ' ', 'world']
            for s in msg:
                send(ref, s)

        pid0 = spawn(f)
        pid1 = spawn(f1, pid0)

        core.run()

        assert messages == ['hello', ' ', 'world']
        assert sources == [3]

    def test_multiple_producers(self):
        messages = []
        sources = []
        def f():
            while True:
                source, msg = receive()
                if not msg:
                    break
                if source.ref not in sources:
                    sources.append(source.ref)
                messages.append(msg)

        def f1(ref):
            msg = ['hello', 'world']
            for s in msg:
                send(ref, s)

        def f2(ref):
            msg = ['brave', 'new', 'world', '']
            for s in msg:
                send(ref, s)

        pid0 = spawn(f)
        pid1 = spawn(f1, pid0)
        pid2 = spawn(f2, pid0)

        core.run()

        assert len(messages) == 5
        assert sources == [5, 6]

    def test_spawn_after(self):
        r_list = []
        def f():
            r_list.append(time.time())

        start = time.time()
        spawn_after(0.3, f)

        core.run()

        end = r_list[0]
        diff = end - start
        assert 0.29 <= diff <= 0.31

    def test_send_after(self):
        r_list = []
        def f():
            receive()
            r_list.append(time.time())

        ref = spawn(f)
        start = time.time()
        send_after(0.3, ref, None)

        core.run()

        end = r_list[0]
        diff = end - start
        assert 0.29 <= diff <= 0.31

########NEW FILE########
__FILENAME__ = test_channel
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from __future__ import absolute_import

import time
from py.test import skip
from flower import core

SHOW_STRANGE = False


import six
from six.moves import xrange

def dprint(txt):
    if SHOW_STRANGE:
        print(txt)

class Test_Channel:

    def test_simple_channel(self):
        output = []
        def print_(*args):
            output.append(args)

        def Sending(channel):
            print_("sending")
            channel.send("foo")

        def Receiving(channel):
            print_("receiving")
            print_(channel.receive())

        ch=core.channel()

        task=core.tasklet(Sending)(ch)

        # Note: the argument, schedule is taking is the value,
        # schedule returns, not the task that runs next

        #core.schedule(task)
        core.schedule()
        task2=core.tasklet(Receiving)(ch)
        #core.schedule(task2)
        core.schedule()

        core.run()

        assert output == [('sending',), ('receiving',), ('foo',)]

    def test_task_with_channel(self):
        pref = {}
        pref[-1] = ['s0', 'r0', 's1', 'r1', 's2', 'r2',
                    's3', 'r3', 's4', 'r4', 's5', 'r5',
                    's6', 'r6', 's7', 'r7', 's8', 'r8',
                    's9', 'r9']
        pref[0] =  ['s0', 'r0', 's1', 's2', 'r1', 'r2',
                    's3', 's4', 'r3', 'r4', 's5', 's6',
                    'r5', 'r6', 's7', 's8', 'r7', 'r8',
                    's9', 'r9']
        pref[1] =  ['s0', 's1', 'r0', 's2', 'r1', 's3',
                    'r2', 's4', 'r3', 's5', 'r4', 's6',
                    'r5', 's7', 'r6', 's8', 'r7', 's9',
                    'r8', 'r9']
        rlist = []

        def f(outchan):
            for i in range(10):
                rlist.append('s%s' % i)
                outchan.send(i)
            outchan.send(-1)

        def g(inchan):
            while 1:
                val = inchan.receive()
                if val == -1:
                    break
                rlist.append('r%s' % val)

        for preference in [-1, 0, 1]:
            rlist = []
            ch = core.channel()
            ch.preference = preference
            t1 = core.tasklet(f)(ch)
            t2 = core.tasklet(g)(ch)

            core.run()

            assert len(rlist) == 20
            assert rlist == pref[preference]

    def test_send_counter(self):
        import random

        numbers = list(range(20))
        random.shuffle(numbers)

        def counter(n, ch):
            for i in xrange(n):
                core.schedule()
            ch.send(n)

        ch = core.channel()
        for each in numbers:
            core.tasklet(counter)(each, ch)

        core.run()

        rlist = []
        while ch.balance:
            rlist.append(ch.receive())

        numbers.sort()
        assert rlist == numbers

    def test_receive_counter(self):
        import random

        numbers = list(range(20))
        random.shuffle(numbers)

        rlist = []
        def counter(n, ch):
            for i in xrange(n):
                core.schedule()
            ch.receive()
            rlist.append(n)

        ch = core.channel()
        for each in numbers:
            core.tasklet(counter)(each, ch)

        core.run()

        while ch.balance:
            ch.send(None)

        numbers.sort()
        assert rlist == numbers



    def test_balance_zero(self):
        ch=core.channel()
        assert ch.balance == 0

    def test_balance_send(self):
        def Sending(channel):
            channel.send("foo")

        ch=core.channel()

        task=core.tasklet(Sending)(ch)
        core.run()

        assert ch.balance == 1

    def test_balance_recv(self):
        def Receiving(channel):
            channel.receive()

        ch=core.channel()

        task=core.tasklet(Receiving)(ch)
        core.run()

        assert ch.balance == -1

    def test_channel_callback(self):
        res = []
        cb = []
        def callback_function(chan, task, sending, willblock):
            cb.append((chan, task, sending, willblock))
        core.set_channel_callback(callback_function)
        def f(chan):
            chan.send('hello')
            val = chan.receive()
            res.append(val)

        chan = core.channel()
        task = core.tasklet(f)(chan)
        val = chan.receive()
        res.append(val)
        chan.send('world')
        assert res == ['hello','world']
        maintask = core.getmain()
        assert cb == [
            (chan, maintask, 0, 1),
            (chan, task, 1, 0),
            (chan, maintask, 1, 1),
            (chan, task, 0, 0)
        ]

    def test_bomb(self):
        try:
            1/0
        except:
            import sys
            b = core.bomb(*sys.exc_info())
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
                val = chan.receive()
            except Exception as exp:
                assert exp.__class__ is Exception
                assert str(exp) == 'test'

        chan = core.channel()
        t1 = core.tasklet(exp_recv)(chan)
        t2 = core.tasklet(exp_sender)(chan)
        core.run()

    def test_send_sequence(self):
        res = []
        lst = [1,2,3,4,5,6,None]
        iterable = iter(lst)
        chan = core.channel()
        def f(chan):
            r = chan.receive()
            while r:
                res.append(r)
                r = chan.receive()

        t = core.tasklet(f)(chan)
        chan.send_sequence(iterable)
        assert res == [1,2,3,4,5,6]

    def test_getruncount(self):
        assert core.getruncount() == 1
        def with_schedule():
            assert core.getruncount() == 2

        t1 = core.tasklet(with_schedule)()
        assert core.getruncount() == 2
        core.schedule()
        def with_run():
            assert core.getruncount() == 1

        t2 = core.tasklet(with_run)()
        core.run()

    def test_simple_pipe(self):
        def pipe(X_in, X_out):
            foo = X_in.receive()
            X_out.send(foo)

        X, Y = core.channel(), core.channel()
        t = core.tasklet(pipe)(X, Y)
        core.run()
        X.send(42)
        assert Y.receive() == 42

    def test_nested_pipe(self):
        dprint('tnp ==== 1')
        def pipe(X, Y):
            dprint('tnp_P ==== 1')
            foo = X.receive()
            dprint('tnp_P ==== 2')
            Y.send(foo)
            dprint('tnp_P ==== 3')

        def nest(X, Y):
            X2, Y2 = core.channel(), core.channel()
            t = core.tasklet(pipe)(X2, Y2)
            dprint('tnp_N ==== 1')
            X_Val = X.receive()
            dprint('tnp_N ==== 2')
            X2.send(X_Val)
            dprint('tnp_N ==== 3')
            Y2_Val = Y2.receive()
            dprint('tnp_N ==== 4')
            Y.send(Y2_Val)
            dprint('tnp_N ==== 5')

        X, Y = core.channel(), core.channel()
        t1 = core.tasklet(nest)(X, Y)
        X.send(13)
        dprint('tnp ==== 2')
        res = Y.receive()
        dprint('tnp ==== 3')
        assert res == 13
        if SHOW_STRANGE:
            raise Exception('force prints')

    def test_wait_two(self):
        """
        A tasklets/channels adaptation of the test_wait_two from the
        logic object space
        """
        def sleep(X, Y):
            dprint('twt_S ==== 1')
            value = X.receive()
            dprint('twt_S ==== 2')
            Y.send((X, value))
            dprint('twt_S ==== 3')

        def wait_two(X, Y, Ret_chan):
            Barrier = core.channel()
            core.tasklet(sleep)(X, Barrier)
            core.tasklet(sleep)(Y, Barrier)
            dprint('twt_W ==== 1')
            ret = Barrier.receive()
            dprint('twt_W ==== 2')
            if ret[0] == X:
                Ret_chan.send((1, ret[1]))
            else:
                Ret_chan.send((2, ret[1]))
            dprint('twt_W ==== 3')

        X = core.channel()
        Y = core.channel()
        Ret_chan = core.channel()

        core.tasklet(wait_two)(X, Y, Ret_chan)

        dprint('twt ==== 1')
        Y.send(42)

        dprint('twt ==== 2')
        X.send(42)
        dprint('twt ==== 3')
        value = Ret_chan.receive()
        dprint('twt ==== 4')
        assert value == (2, 42)


    def test_schedule_return_value(self):

        def task(val):
            value = core.schedule(val)
            assert value == val

        core.tasklet(task)(10)
        core.tasklet(task)(5)

        core.run()

    def test_nonblocking_channel(self):
        c = core.channel(100)
        r1 = c.receive()
        r2 = c.send(True)
        r3 = c.receive()
        r4 = c.receive()

        assert r1 is None
        assert r2 is None
        assert r3 == True
        assert r4 is None

    def test_async_channel(self):
        c = core.channel(100)

        unblocked_sent = 0
        for i in range(100):
            c.send(True)
            unblocked_sent += 1

        assert unblocked_sent == 100
        assert c.balance == 100

        unblocked_recv = []
        for i in range(100):
            unblocked_recv.append(c.receive())

        assert len(unblocked_recv) == 100

    def test_async_with_blocking_channel(self):

        c = core.channel(10)

        unblocked_sent = 0
        for i in range(10):
            c.send(True)
            unblocked_sent += 1

        assert unblocked_sent == 10
        assert c.balance == 10

        r_list = []
        def f():
            start = time.time()
            c.send(True)
            r_list.append(start)

        core.tasklet(f)()


        unblocked_recv = []
        for i in range(11):
            time.sleep(0.01)
            unblocked_recv.append(c.receive())
            core.schedule()


        core.run()

        diff = time.time() - r_list[0]

        assert len(unblocked_recv) == 11
        assert diff > 0.1

########NEW FILE########
__FILENAME__ = test_io
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import os
import tempfile

from py.test import skip
from flower import core
from flower.io import IOChannel

class Test_IO:

    def test_readable(self):
        (r, w) = os.pipe()

        ret = []
        def _read(fd):
            c = IOChannel(r, mode=0)
            c.receive()
            ret.append(os.read(fd, 10))
            c.stop()

        def _write(fd):
            os.write(fd, b"TEST")

        core.tasklet(_read)(r)
        core.tasklet(_write)(w)
        core.run()

        assert ret == [b"TEST"]

########NEW FILE########
__FILENAME__ = test_local
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pytest
from py.test import skip
from flower.local import local
from flower import core

class Test_Local:

    def test_simple(self):
        d = local()
        d.a = 1
        assert d.a == 1
        d.a = 2
        assert d.a == 2

    def test_simple_delete(self):
        d = local()
        d.a = 1
        assert d.a == 1
        del d.a
        def f(): return d.a
        with pytest.raises(AttributeError):
            f()

    def test_simple_delete2(self):
        d = local()
        d.a = 1
        d.b = 2
        assert d.a == 1
        assert d.b == 2
        del d.a
        def f(): return d.a
        with pytest.raises(AttributeError):
            f()
        assert d.b == 2

    def test_local(self):
        d = local()
        d.a = 1

        r_list = []
        def f():
            try:
                d.a
            except AttributeError:
                r_list.append(True)

        core.tasklet(f)()
        core.schedule()

        assert r_list == [True]

    def test_local2(self):
        d = local()
        d.a = 1

        r_list = []
        def f():
            try:
                d.a
            except AttributeError:
                r_list.append(True)
            d.a = 2
            if d.a == 2:
                r_list.append(True)

        core.tasklet(f)()
        core.schedule()

        assert r_list == [True, True]
        assert d.a == 1




########NEW FILE########
__FILENAME__ = test_registry
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import pytest

from flower.actor import spawn, ActorRef
from flower.registry import (registry, register, unregister,
        registered, Registry)
from flower import core



class Test_Registry:

    def test_simple(self):
        def f(): return

        pid = spawn(f)
        register("test", pid)

        assert pid in registry
        assert "test" in registry
        assert registry["test"] ==  pid
        assert registry[pid] == ["test"]

        del registry[pid]
        assert registry["test"] is None

        core.run()

    def test_registered(self):
        r_list = []
        def f():
            print("ici %s" % registered())
            print(registry._by_ref)
            [r_list.append(r) for r in registered()]

        pid = spawn(f)
        register("b", pid)
        register("a", pid)



        assert 'a' in registry
        assert 'b' in registry
        assert registered(pid) == ['a', 'b']

        pid.actor.switch()
        assert r_list == ['a', 'b']


    def test_share_registry(self):
        r = Registry()

        def f(): return
        pid = spawn(f)
        register("test1", pid)

        assert "test1" in registry
        assert registry["test1"] is pid
        assert "test1" in r
        assert r["test1"] == registry["test1"]

########NEW FILE########
__FILENAME__ = test_scheduler
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

from __future__ import absolute_import

import time
from py.test import skip
from flower import core

SHOW_STRANGE = False


import six
from six.moves import xrange

def dprint(txt):
    if SHOW_STRANGE:
        print(txt)

class Test_Stackless:

    def test_simple(self):
        rlist = []

        def f():
            rlist.append('f')

        def g():
            rlist.append('g')
            core.schedule()

        def main():
            rlist.append('m')
            cg = core.tasklet(g)()
            cf = core.tasklet(f)()
            core.run()
            rlist.append('m')

        main()

        assert core.getcurrent() is core.getmain()
        assert rlist == 'm g f m'.split()

    def test_run(self):
        output = []
        def print_(*args):
            output.append(args)

        def f(i):
            print_(i)

        core.tasklet(f)(1)
        core.tasklet(f)(2)
        core.run()

        assert output == [(1,), (2,)]

    def test_scheduling_cleanup(self):
        rlist = []
        def f():
            rlist.append('fb')
            core.schedule()
            rlist.append('fa')

        def g():
            rlist.append('gb')
            core.schedule()
            rlist.append('ga')

        def h():
            rlist.append('hb')
            core.schedule()
            rlist.append('ha')

        tf = core.tasklet(f)()
        tg = core.tasklet(g)()
        th = core.tasklet(h)()

        rlist.append('mb')
        core.run()
        rlist.append('ma')

        assert rlist == 'mb fb gb hb fa ga ha ma'.split()

    def test_except(self):
        rlist = []
        def f():
            rlist.append('f')
            return 1/0

        def g():
            rlist.append('bg')
            core.schedule()
            rlist.append('ag')

        def h():
            rlist.append('bh')
            core.schedule()
            rlist.append('ah')

        tg = core.tasklet(g)()
        tf = core.tasklet(f)()
        th = core.tasklet(h)()

        try:
            core.run()
            # cheating, can't test for ZeroDivisionError
        except ZeroDivisionError:
            rlist.append('E')
        core.schedule()
        core.schedule()

        assert rlist == "bg f E bh ag ah".split()

    def test_except_full(self):
        rlist = []
        def f():
            rlist.append('f')
            return 1/0

        def g():
            rlist.append('bg')
            core.schedule()
            rlist.append('ag')

        def h():
            rlist.append('bh')
            core.schedule()
            rlist.append('ah')

        tg = core.tasklet(g)()
        tf = core.tasklet(f)()
        th = core.tasklet(h)()

        try:
            core.run()
        except ZeroDivisionError:
            rlist.append('E')
        core.schedule()
        core.schedule()

        assert rlist == "bg f E bh ag ah".split()

    def test_kill(self):
        def f():pass
        t =  core.tasklet(f)()
        t.kill()
        assert not t.alive

    def test_catch_taskletexit(self):
        # Tests if TaskletExit can be caught in the tasklet being killed.
        global taskletexit
        taskletexit = False

        def f():
            try:
                core.schedule()
            except TaskletExit:
                global TaskletExit
                taskletexit = True
                raise

            t =  core.tasklet(f)()
            t.run()
            assert t.alive
            t.kill()
            assert not t.alive
            assert taskletexit

    def test_autocatch_taskletexit(self):
        # Tests if TaskletExit is caught correctly in core.tasklet.setup().
        def f():
            core.schedule()

        t = core.tasklet(f)()
        t.run()
        t.kill()


    # tests inspired from simple core.com examples

    def test_construction(self):
        output = []
        def print_(*args):
            output.append(args)

        def aCallable(value):
            print_("aCallable:", value)

        task = core.tasklet(aCallable)
        task.setup('Inline using setup')

        core.run()
        assert output == [("aCallable:", 'Inline using setup')]


        del output[:]
        task = core.tasklet(aCallable)
        task('Inline using ()')

        core.run()
        assert output == [("aCallable:", 'Inline using ()')]

        del output[:]
        task = core.tasklet()
        task.bind(aCallable)
        task('Bind using ()')

        core.run()
        assert output == [("aCallable:", 'Bind using ()')]

    def test_run(self):
        output = []
        def print_(*args):
            output.append(args)

        def f(i):
            print_(i)

        core.tasklet(f)(1)
        core.tasklet(f)(2)
        core.run()

        assert output == [(1,), (2,)]

    def test_schedule(self):
        output = []
        def print_(*args):
            output.append(args)

        def f(i):
            print_(i)

        core.tasklet(f)(1)
        core.tasklet(f)(2)
        core.schedule()

        assert output == [(1,), (2,)]


    def test_cooperative(self):
        output = []
        def print_(*args):
            output.append(args)

        def Loop(i):
            for x in range(3):
                core.schedule()
                print_("schedule", i)

        core.tasklet(Loop)(1)
        core.tasklet(Loop)(2)
        core.run()

        assert output == [('schedule', 1), ('schedule', 2),
                          ('schedule', 1), ('schedule', 2),
                          ('schedule', 1), ('schedule', 2),]


    def test_schedule_callback(self):
        res = []
        cb = []
        def schedule_cb(prev, next):
            cb.append((prev, next))

        core.set_schedule_callback(schedule_cb)
        def f(i):
            res.append('A_%s' % i)
            core.schedule()
            res.append('B_%s' % i)

        t1 = core.tasklet(f)(1)
        t2 = core.tasklet(f)(2)
        maintask = core.getmain()
        core.run()
        assert res == ['A_1', 'A_2', 'B_1', 'B_2']
        assert len(cb) == 5
        assert cb[0] == (maintask, t1)
        assert cb[1] == (t1, t2)
        assert cb[2] == (t2, t1)
        assert cb[3] == (t1, t2)
        assert cb[4] == (t2, maintask)

    def test_getruncount(self):
        assert core.getruncount() == 1
        def with_schedule():
            assert core.getruncount() == 2

        t1 = core.tasklet(with_schedule)()
        assert core.getruncount() == 2
        core.schedule()
        def with_run():
            assert core.getruncount() == 1

        t2 = core.tasklet(with_run)()
        core.run()

    def test_schedule_return(self):
        def f():pass
        t1= core.tasklet(f)()
        r = core.schedule()
        assert r is core.getmain()
        t2 = core.tasklet(f)()
        r = core.schedule('test')
        assert r == 'test'

    def test_schedule_return_value(self):

        def task(val):
            value = core.schedule(val)
            assert value == val

        core.tasklet(task)(10)
        core.tasklet(task)(5)

        core.run()

########NEW FILE########
__FILENAME__ = test_sync

from flower.core.sync import *

def test_increment():
    i = 0
    i = increment(i)
    assert i == 1

    i = increment(i)
    assert i == 2


def test_decrement():
    i = 0
    i = decrement(i)
    assert i == -1

    i = decrement(i)
    assert i == -2

def test_combine():
    i = 1
    i = decrement(i)
    assert i == 0
    i = increment(i)
    assert i == 1


def test_read():
    i = 10
    v = atomic_read(i)
    assert i == v

def test_compare_and_swap():
    a, b = 1, 2
    a = compare_and_swap(a, b)

    assert a == b

    a, b = 1, 1
    r = compare_and_swap(a, b)
    assert a == 1

########NEW FILE########
__FILENAME__ = test_time
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import os
import time

import pytest
from py.test import skip

from flower import core
from flower.time import Ticker, sleep

IS_TRAVIS = False

if os.environ.get('TRAVIS') and os.environ.get('TRAVIS') is not None:
    IS_TRAVIS = True

class Test_Time:

    def test_ticker(self):
        rlist = []

        def f():
            ticker = Ticker(0.1)
            i = 0
            while True:
                if i == 3: break
                t = ticker.receive()
                rlist.append(t)
                i += 1
            ticker.stop()

        tf = core.tasklet(f)()
        core.run()

        assert len(rlist) == 3


    def test_simple_sleep(self):
        if IS_TRAVIS:
            skip()
        start = time.time()
        sleep(0.02)
        delay = time.time() - start
        assert 0.02 - 0.004 <= delay < 0.02 + 0.02, delay


    def test_sleep(self):
        rlist = []

        def f():
            sleep(0.2)
            rlist.append('a')

        def f1():
            rlist.append('b')

        core.tasklet(f)()
        core.tasklet(f1)()
        core.run()

        assert rlist == ['b', 'a']


    def test_sleep2(self):
        rlist = []

        def f():
            sleep()
            rlist.append('a')

        def f1():
            rlist.append('b')

        core.tasklet(f)()
        core.tasklet(f1)()
        core.run()

        assert rlist == ['b', 'a']




########NEW FILE########
__FILENAME__ = test_timer
# -*- coding: utf-8 -
#
# This file is part of flower. See the NOTICE for more information.

import time

from flower.core.util import from_nanotime
from flower.core import run, tasklet
from flower.core.timer import Timer, sleep

def _wait():
    time.sleep(0.01)


def test_simple_timer():
    r_list = []
    def _func(now, t):
        r_list.append(from_nanotime(now))

    now = time.time()
    t = Timer(_func, 0.1)
    t.start()
    run()
    delay = r_list[0]
    assert (now + 0.09) <= delay <= (now + 0.11), delay


def test_multiple_timer():
    r1 = []
    def f(now, t):
        r1.append(from_nanotime(now))

    r2 = []
    def f1(now, t):
        r2.append(from_nanotime(now))

    now = time.time()

    t = Timer(f, 0.4)
    t.start()

    t1 = Timer(f1, 0.1)
    t1.start()

    run()
    assert r1[0] > r2[0]
    assert (now + 0.39) <= r1[0] <= (now + 0.41), r1[0]
    assert (now + 0.09) <= r2[0] <= (now + 0.11), r2[0]


def test_repeat():
    r = []
    def f(now, t):
        if len(r) == 3:
            t.stop()
            return
        r.append(now)

    t = Timer(f, 0.01, 0.01)
    t.start()
    run()
    assert len(r) == 3
    assert r[2] > r[1]
    assert r[1] > r[0]

def test_sleep():
    start = time.time()
    sleep(0.1)
    diff = time.time() - start
    assert 0.09 <= diff <= 0.11


def test_multiple_sleep():
    r1 = []
    def f():
        sleep(0.4)
        r1.append(time.time())

    r2 = []
    def f1():
        sleep(0.1)
        r2.append(time.time())

    tasklet(f)()
    tasklet(f1)()

    now = time.time()
    run()
    assert r1[0] > r2[0]
    assert (now + 0.39) <= r1[0] <= (now + 0.41), r1[0]
    assert (now + 0.09) <= r2[0] <= (now + 0.11), r2[0]

########NEW FILE########
