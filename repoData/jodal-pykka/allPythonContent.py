__FILENAME__ = conf
# encoding: utf-8

"""Pykka documentation build configuration file"""

from __future__ import unicode_literals

import os
import re
import sys


# -- Workarounds to have autodoc generate API docs ----------------------------

sys.path.insert(0, os.path.abspath('..'))


class Mock(object):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    @classmethod
    def __getattr__(self, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        elif name[0] == name[0].upper():
            return type(name, (), {})
        else:
            return Mock()


MOCK_MODULES = [
    'gevent',
    'gevent.event',
    'gevent.queue',
    'eventlet',
    'eventlet.event',
    'eventlet.queue',
]
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = Mock()


# -- General configuration ----------------------------------------------------

needs_sphinx = '1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.extlinks',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = u'Pykka'
copyright = u'2010-2014, Stein Magnus Jodal'


def get_version():
    init_py = open('../pykka/__init__.py').read()
    metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", init_py))
    return metadata['version']


release = get_version()
version = '.'.join(release.split('.')[:2])

exclude_patterns = ['_build']

pygments_style = 'sphinx'

modindex_common_prefix = ['pykka.']


# -- Options for HTML output --------------------------------------------------

html_theme = 'default'
html_static_path = ['_static']

html_use_modindex = True
html_use_index = True
html_split_index = False
html_show_sourcelink = True

htmlhelp_basename = 'Pykka'


# -- Options for LaTeX output -------------------------------------------------

latex_documents = [
    (
        'index',
        'Pykka.tex',
        'Pykka Documentation',
        'Stein Magnus Jodal',
        'manual',
    ),
]


# -- Options for manual page output -------------------------------------------

man_pages = []


# -- Options for autodoc extension --------------------------------------------

autodoc_member_order = 'bysource'


# -- Options for extlink extension --------------------------------------------

extlinks = {
    'issue': ('https://github.com/jodal/pykka/issues/%s', '#'),
}

########NEW FILE########
__FILENAME__ = counter
#! /usr/bin/env python

import pykka


class Adder(pykka.ThreadingActor):
    def add_one(self, i):
        print('{} is increasing {}'.format(self, i))
        return i + 1


class Bookkeeper(pykka.ThreadingActor):
    def __init__(self, adder):
        super(Bookkeeper, self).__init__()
        self.adder = adder

    def count_to(self, target):
        i = 0
        while i < target:
            i = self.adder.add_one(i).get()
            print('{} got {} back'.format(self, i))


if __name__ == '__main__':
    adder = Adder.start().proxy()
    bookkeeper = Bookkeeper.start(adder).proxy()
    bookkeeper.count_to(10).get()
    pykka.ActorRegistry.stop_all()

########NEW FILE########
__FILENAME__ = deadlock_debugging
#! /usr/bin/env python

import logging
import os
import signal
import time

import pykka
import pykka.debug


class DeadlockActorA(pykka.ThreadingActor):
    def foo(self, b):
        logging.debug('This is foo calling bar')
        return b.bar().get()


class DeadlockActorB(pykka.ThreadingActor):
    def __init__(self, a):
        super(DeadlockActorB, self).__init__()
        self.a = a

    def bar(self):
        logging.debug('This is bar calling foo; BOOM!')
        return self.a.foo().get()


if __name__ == '__main__':
    print('Setting up logging to get output from signal handler...')
    logging.basicConfig(level=logging.DEBUG)

    print('Registering signal handler...')
    signal.signal(signal.SIGUSR1, pykka.debug.log_thread_tracebacks)

    print('Starting actors...')
    a = DeadlockActorA.start().proxy()
    b = DeadlockActorB.start(a).proxy()

    print('Now doing something stupid that will deadlock the actors...')
    a.foo(b)

    time.sleep(0.01)  # Yield to actors, so we get output in a readable order

    print('Making main thread relax; not block, not quit')
    print('1) Use `kill -SIGUSR1 %d` to log thread tracebacks' % os.getpid())
    print('2) Then `kill %d` to terminate the process' % os.getpid())
    while True:
        time.sleep(1)

########NEW FILE########
__FILENAME__ = plain_actor
#! /usr/bin/env python

import pykka


class PlainActor(pykka.ThreadingActor):
    def __init__(self):
        super(PlainActor, self).__init__()
        self.stored_messages = []

    def on_receive(self, message):
        if message.get('command') == 'get_messages':
            return self.stored_messages
        else:
            self.stored_messages.append(message)


if __name__ == '__main__':
    actor = PlainActor.start()
    actor.tell({'no': 'Norway', 'se': 'Sweden'})
    actor.tell({'a': 3, 'b': 4, 'c': 5})
    print(actor.ask({'command': 'get_messages'}))
    actor.stop()

########NEW FILE########
__FILENAME__ = resolver
#! /usr/bin/env python

"""
Resolve a bunch of IP addresses using a pool of resolver actors.

Based on example contributed by Kristian Klette <klette@klette.us>.

Either run without arguments:

    ./resolver.py

Or specify pool size and IPs to resolve:

    ./resolver.py 3 129.240.2.{1,2,3,4,5,6,7,8,9}
"""

import pprint
import socket
import sys

import pykka


class Resolver(pykka.ThreadingActor):
    def resolve(self, ip):
        try:
            info = socket.gethostbyaddr(ip)
            print('Finished resolving {}'.format(ip))
            return info[0]
        except:
            print('Failed resolving {}'.format(ip))
            return None


def run(pool_size, *ips):
    # Start resolvers
    resolvers = [Resolver.start().proxy() for _ in range(pool_size)]

    # Distribute work by mapping IPs to resolvers (not blocking)
    hosts = []
    for i, ip in enumerate(ips):
        hosts.append(resolvers[i % len(resolvers)].resolve(ip))

    # Gather results (blocking)
    ip_to_host = zip(ips, pykka.get_all(hosts))
    pprint.pprint(list(ip_to_host))

    # Clean up
    pykka.ActorRegistry.stop_all()


if __name__ == '__main__':
    if len(sys.argv[1:]) >= 2:
        run(int(sys.argv[1]), *sys.argv[2:])
    else:
        ips = ['129.241.93.%s' % i for i in range(1, 50)]
        run(10, *ips)

########NEW FILE########
__FILENAME__ = typed_actor
#! /usr/bin/env python

import pykka

import threading
import time


class AnActor(pykka.ThreadingActor):
    field = 'this is the value of AnActor.field'

    def proc(self):
        log('this was printed by AnActor.proc()')

    def func(self):
        time.sleep(0.5)  # Block a bit to make it realistic
        return 'this was returned by AnActor.func() after a delay'


def log(s):
    print('{}: {}'.format(threading.current_thread().name, s))


if __name__ == '__main__':
    actor = AnActor.start().proxy()
    for i in range(3):
        # Method with side effect
        log('calling AnActor.proc() ...')
        actor.proc()

        # Method with return value
        log('calling AnActor.func() ...')
        result = actor.func()  # Does not block, returns a future
        log('printing result ... (blocking)')
        log(result.get())  # Blocks until ready

        # Field reading
        log('reading AnActor.field ...')
        result = actor.field  # Does not block, returns a future
        log('printing result ... (blocking)')
        log(result.get())  # Blocks until ready

        # Field writing
        log('writing AnActor.field ...')
        actor.field = 'new value'  # Assignment does not block
        result = actor.field  # Does not block, returns a future
        log('printing new field value ... (blocking)')
        log(result.get())  # Blocks until ready
    actor.stop()

########NEW FILE########
__FILENAME__ = actor
import logging as _logging
import sys as _sys
import threading as _threading
import uuid as _uuid

try:
    # Python 2.x
    import Queue as _queue
except ImportError:
    # Python 3.x
    import queue as _queue  # noqa

from pykka.exceptions import ActorDeadError as _ActorDeadError
from pykka.future import ThreadingFuture as _ThreadingFuture
from pykka.proxy import ActorProxy as _ActorProxy
from pykka.registry import ActorRegistry as _ActorRegistry

_logger = _logging.getLogger('pykka')


class Actor(object):
    """
    To create an actor:

    1. subclass one of the :class:`Actor` implementations, e.g.
       :class:`GeventActor <pykka.gevent.GeventActor>` or
       :class:`ThreadingActor`,
    2. implement your methods, including :meth:`__init__`, as usual,
    3. call :meth:`Actor.start` on your actor class, passing the method any
       arguments for your constructor.

    To stop an actor, call :meth:`Actor.stop()` or :meth:`ActorRef.stop()`.

    For example::

        import pykka

        class MyActor(pykka.ThreadingActor):
            def __init__(self, my_arg=None):
                super(MyActor, self).__init__()
                ... # My optional init code with access to start() arguments

            def on_start(self):
                ... # My optional setup code in same context as on_receive()

            def on_stop(self):
                ... # My optional cleanup code in same context as on_receive()

            def on_failure(self, exception_type, exception_value, traceback):
                ... # My optional cleanup code in same context as on_receive()

            def on_receive(self, message):
                ... # My optional message handling code for a plain actor

            def a_method(self, ...):
                ... # My regular method to be used through an ActorProxy

        my_actor_ref = MyActor.start(my_arg=...)
        my_actor_ref.stop()
    """

    @classmethod
    def start(cls, *args, **kwargs):
        """
        Start an actor and register it in the
        :class:`ActorRegistry <pykka.ActorRegistry>`.

        Any arguments passed to :meth:`start` will be passed on to the class
        constructor.

        Behind the scenes, the following is happening when you call
        :meth:`start`:

        1. The actor is created:

           1. :attr:`actor_urn` is initialized with the assigned URN.

           2. :attr:`actor_inbox` is initialized with a new actor inbox.

           3. :attr:`actor_ref` is initialized with a :class:`pykka.ActorRef`
              object for safely communicating with the actor.

           4. At this point, your :meth:`__init__()` code can run.

        2. The actor is registered in :class:`pykka.ActorRegistry`.

        3. The actor receive loop is started by the actor's associated
           thread/greenlet.

        :returns: a :class:`ActorRef` which can be used to access the actor in
            a safe manner
        """
        obj = cls(*args, **kwargs)
        assert obj.actor_ref is not None, (
            'Actor.__init__() have not been called. '
            'Did you forget to call super() in your override?')
        _ActorRegistry.register(obj.actor_ref)
        _logger.debug('Starting %s', obj)
        obj._start_actor_loop()
        return obj.actor_ref

    @staticmethod
    def _create_actor_inbox():
        """Internal method for implementors of new actor types."""
        raise NotImplementedError('Use a subclass of Actor')

    @staticmethod
    def _create_future():
        """Internal method for implementors of new actor types."""
        raise NotImplementedError('Use a subclass of Actor')

    def _start_actor_loop(self):
        """Internal method for implementors of new actor types."""
        raise NotImplementedError('Use a subclass of Actor')

    #: The actor URN string is a universally unique identifier for the actor.
    #: It may be used for looking up a specific actor using
    #: :meth:`ActorRegistry.get_by_urn
    #: <pykka.ActorRegistry.get_by_urn>`.
    actor_urn = None

    #: The actor's inbox. Use :meth:`ActorRef.tell`, :meth:`ActorRef.ask`, and
    #: friends to put messages in the inbox.
    actor_inbox = None

    #: The actor's :class:`ActorRef` instance.
    actor_ref = None

    #: A :class:`threading.Event` representing whether or not the actor should
    #: continue processing messages. Use :meth:`stop` to change it.
    actor_stopped = None

    def __init__(self, *args, **kwargs):
        """
        Your are free to override :meth:`__init__`, but you must call your
        superclass' :meth:`__init__` to ensure that fields :attr:`actor_urn`,
        :attr:`actor_inbox`, and :attr:`actor_ref` are initialized.

        You can use :func:`super`::

            super(MyActor, self).__init__()

        Or call you superclass directly::

            pykka.ThreadingActor.__init__(self)
            # or
            pykka.gevent.GeventActor.__init__(self)

        :meth:`__init__` is called before the actor is started and registered
        in :class:`ActorRegistry <pykka.ActorRegistry>`.
        """
        self.actor_urn = _uuid.uuid4().urn
        self.actor_inbox = self._create_actor_inbox()
        self.actor_stopped = _threading.Event()

        self.actor_ref = ActorRef(self)

    def __str__(self):
        return '%(class)s (%(urn)s)' % {
            'class': self.__class__.__name__,
            'urn': self.actor_urn,
        }

    def stop(self):
        """
        Stop the actor.

        It's equivalent to calling :meth:`ActorRef.stop` with ``block=False``.
        """
        self.actor_ref.tell({'command': 'pykka_stop'})

    def _stop(self):
        """
        Stops the actor immediately without processing the rest of the inbox.
        """
        _ActorRegistry.unregister(self.actor_ref)
        self.actor_stopped.set()
        _logger.debug('Stopped %s', self)
        try:
            self.on_stop()
        except Exception:
            self._handle_failure(*_sys.exc_info())

    def _actor_loop(self):
        """
        The actor's event loop.

        This is the method that will be executed by the thread or greenlet.
        """
        try:
            self.on_start()
        except Exception:
            self._handle_failure(*_sys.exc_info())

        while not self.actor_stopped.is_set():
            message = self.actor_inbox.get()
            reply_to = None
            try:
                reply_to = message.pop('pykka_reply_to', None)
                response = self._handle_receive(message)
                if reply_to:
                    reply_to.set(response)
            except Exception:
                if reply_to:
                    _logger.debug(
                        'Exception returned from %s to caller:' % self,
                        exc_info=_sys.exc_info())
                    reply_to.set_exception()
                else:
                    self._handle_failure(*_sys.exc_info())
                    try:
                        self.on_failure(*_sys.exc_info())
                    except Exception:
                        self._handle_failure(*_sys.exc_info())
            except BaseException:
                exception_value = _sys.exc_info()[1]
                _logger.debug(
                    '%s in %s. Stopping all actors.' %
                    (repr(exception_value), self))
                self._stop()
                _ActorRegistry.stop_all()

        while not self.actor_inbox.empty():
            msg = self.actor_inbox.get()
            reply_to = msg.pop('pykka_reply_to', None)
            if reply_to:
                if msg.get('command') == 'pykka_stop':
                    reply_to.set(None)
                else:
                    reply_to.set_exception(_ActorDeadError(
                        '%s stopped before handling the message' %
                        self.actor_ref))

    def on_start(self):
        """
        Hook for doing any setup that should be done *after* the actor is
        started, but *before* it starts processing messages.

        For :class:`ThreadingActor`, this method is executed in the actor's own
        thread, while :meth:`__init__` is executed in the thread that created
        the actor.

        If an exception is raised by this method the stack trace will be
        logged, and the actor will stop.
        """
        pass

    def on_stop(self):
        """
        Hook for doing any cleanup that should be done *after* the actor has
        processed the last message, and *before* the actor stops.

        This hook is *not* called when the actor stops because of an unhandled
        exception. In that case, the :meth:`on_failure` hook is called instead.

        For :class:`ThreadingActor` this method is executed in the actor's own
        thread, immediately before the thread exits.

        If an exception is raised by this method the stack trace will be
        logged, and the actor will stop.
        """
        pass

    def _handle_failure(self, exception_type, exception_value, traceback):
        """Logs unexpected failures, unregisters and stops the actor."""
        _logger.error(
            'Unhandled exception in %s:' % self,
            exc_info=(exception_type, exception_value, traceback))
        _ActorRegistry.unregister(self.actor_ref)
        self.actor_stopped.set()

    def on_failure(self, exception_type, exception_value, traceback):
        """
        Hook for doing any cleanup *after* an unhandled exception is raised,
        and *before* the actor stops.

        For :class:`ThreadingActor` this method is executed in the actor's own
        thread, immediately before the thread exits.

        The method's arguments are the relevant information from
        :func:`sys.exc_info`.

        If an exception is raised by this method the stack trace will be
        logged, and the actor will stop.
        """
        pass

    def _handle_receive(self, message):
        """Handles messages sent to the actor."""
        if message.get('command') == 'pykka_stop':
            return self._stop()
        if message.get('command') == 'pykka_call':
            callee = self._get_attribute_from_path(message['attr_path'])
            return callee(*message['args'], **message['kwargs'])
        if message.get('command') == 'pykka_getattr':
            attr = self._get_attribute_from_path(message['attr_path'])
            return attr
        if message.get('command') == 'pykka_setattr':
            parent_attr = self._get_attribute_from_path(
                message['attr_path'][:-1])
            attr_name = message['attr_path'][-1]
            return setattr(parent_attr, attr_name, message['value'])
        return self.on_receive(message)

    def on_receive(self, message):
        """
        May be implemented for the actor to handle regular non-proxy messages.

        Messages where the value of the "command" key matches "pykka_*" are
        reserved for internal use in Pykka.

        :param message: the message to handle
        :type message: picklable dict

        :returns: anything that should be sent as a reply to the sender
        """
        _logger.warning('Unexpected message received by %s: %s', self, message)

    def _get_attribute_from_path(self, attr_path):
        """
        Traverses the path and returns the attribute at the end of the path.
        """
        attr = self
        for attr_name in attr_path:
            attr = getattr(attr, attr_name)
        return attr


class ThreadingActor(Actor):
    """
    :class:`ThreadingActor` implements :class:`Actor` using regular Python
    threads.

    This implementation is slower than :class:`GeventActor
    <pykka.gevent.GeventActor>`, but can be used in a process with other
    threads that are not Pykka actors.
    """

    use_daemon_thread = False
    """
    A boolean value indicating whether this actor is executed on a thread that
    is a daemon thread (:class:`True`) or not (:class:`False`). This must be
    set before :meth:`pykka.Actor.start` is called, otherwise
    :exc:`RuntimeError` is raised.

    The entire Python program exits when no alive non-daemon threads are left.
    This means that an actor running on a daemon thread may be interrupted at
    any time, and there is no guarantee that cleanup will be done or that
    :meth:`pykka.Actor.on_stop` will be called.

    Actors do not inherit the daemon flag from the actor that made it. It
    always has to be set explicitly for the actor to run on a daemonic thread.
    """

    @staticmethod
    def _create_actor_inbox():
        return _queue.Queue()

    @staticmethod
    def _create_future():
        return _ThreadingFuture()

    def _start_actor_loop(self):
        thread = _threading.Thread(target=self._actor_loop)
        thread.name = thread.name.replace('Thread', self.__class__.__name__)
        thread.daemon = self.use_daemon_thread
        thread.start()


class ActorRef(object):
    """
    Reference to a running actor which may safely be passed around.

    :class:`ActorRef` instances are returned by :meth:`Actor.start` and the
    lookup methods in :class:`ActorRegistry <pykka.ActorRegistry>`. You should
    never need to create :class:`ActorRef` instances yourself.

    :param actor: the actor to wrap
    :type actor: :class:`Actor`
    """

    #: The class of the referenced actor.
    actor_class = None

    #: See :attr:`Actor.actor_urn`.
    actor_urn = None

    #: See :attr:`Actor.actor_inbox`.
    actor_inbox = None

    #: See :attr:`Actor.actor_stopped`.
    actor_stopped = None

    def __init__(self, actor):
        self._actor = actor
        self.actor_class = actor.__class__
        self.actor_urn = actor.actor_urn
        self.actor_inbox = actor.actor_inbox
        self.actor_stopped = actor.actor_stopped

    def __repr__(self):
        return '<ActorRef for %s>' % str(self)

    def __str__(self):
        return '%(class)s (%(urn)s)' % {
            'urn': self.actor_urn,
            'class': self.actor_class.__name__,
        }

    def is_alive(self):
        """
        Check if actor is alive.

        This is based on the actor's stopped flag. The actor is not guaranteed
        to be alive and responding even though :meth:`is_alive` returns
        :class:`True`.

        :return:
            Returns :class:`True` if actor is alive, :class:`False` otherwise.
        """
        return not self.actor_stopped.is_set()

    def tell(self, message):
        """
        Send message to actor without waiting for any response.

        Will generally not block, but if the underlying queue is full it will
        block until a free slot is available.

        :param message: message to send
        :type message: picklable dict

        :raise: :exc:`pykka.ActorDeadError` if actor is not available
        :return: nothing
        """
        if not self.is_alive():
            raise _ActorDeadError('%s not found' % self)
        self.actor_inbox.put(message)

    def ask(self, message, block=True, timeout=None):
        """
        Send message to actor and wait for the reply.

        The message must be a picklable dict.
        If ``block`` is :class:`False`, it will immediately return a
        :class:`Future <pykka.Future>` instead of blocking.

        If ``block`` is :class:`True`, and ``timeout`` is :class:`None`, as
        default, the method will block until it gets a reply, potentially
        forever. If ``timeout`` is an integer or float, the method will wait
        for a reply for ``timeout`` seconds, and then raise
        :exc:`pykka.Timeout`.

        :param message: message to send
        :type message: picklable dict

        :param block: whether to block while waiting for a reply
        :type block: boolean

        :param timeout: seconds to wait before timeout if blocking
        :type timeout: float or :class:`None`

        :raise: :exc:`pykka.Timeout` if timeout is reached if blocking
        :raise: any exception returned by the receiving actor if blocking
        :return: :class:`pykka.Future`, or response if blocking
        """
        future = self.actor_class._create_future()
        message['pykka_reply_to'] = future
        try:
            self.tell(message)
        except _ActorDeadError:
            future.set_exception()
        if block:
            return future.get(timeout=timeout)
        else:
            return future

    def stop(self, block=True, timeout=None):
        """
        Send a message to the actor, asking it to stop.

        Returns :class:`True` if actor is stopped or was being stopped at the
        time of the call. :class:`False` if actor was already dead. If
        ``block`` is :class:`False`, it returns a future wrapping the result.

        Messages sent to the actor before the actor is asked to stop will
        be processed normally before it stops.

        Messages sent to the actor after the actor is asked to stop will
        be replied to with :exc:`pykka.ActorDeadError` after it stops.

        The actor may not be restarted.

        ``block`` and ``timeout`` works as for :meth:`ask`.

        :return: :class:`pykka.Future`, or a boolean result if blocking
        """
        ask_future = self.ask({'command': 'pykka_stop'}, block=False)

        def _stop_result_converter(timeout):
            try:
                ask_future.get(timeout=timeout)
                return True
            except _ActorDeadError:
                return False

        converted_future = ask_future.__class__()
        converted_future.set_get_hook(_stop_result_converter)

        if block:
            return converted_future.get(timeout=timeout)
        else:
            return converted_future

    def proxy(self):
        """
        Wraps the :class:`ActorRef` in an :class:`ActorProxy
        <pykka.ActorProxy>`.

        Using this method like this::

            proxy = AnActor.start().proxy()

        is analogous to::

            proxy = ActorProxy(AnActor.start())

        :raise: :exc:`pykka.ActorDeadError` if actor is not available
        :return: :class:`pykka.ActorProxy`
        """
        return _ActorProxy(self)

########NEW FILE########
__FILENAME__ = debug
import logging as _logging
import sys as _sys
import threading as _threading
import traceback as _traceback


_logger = _logging.getLogger('pykka')


def log_thread_tracebacks(*args, **kwargs):
    """Logs at ``CRITICAL`` level a traceback for each running thread.

    This can be a convenient tool for debugging deadlocks.

    The function accepts any arguments so that it can easily be used as e.g. a
    signal handler, but it does not use the arguments for anything.

    To use this function as a signal handler, setup logging with a
    :attr:`logging.CRITICAL` threshold or lower and make your main thread
    register this with the :mod:`signal` module::

        import logging
        import signal

        import pykka.debug

        logging.basicConfig(level=logging.DEBUG)
        signal.signal(signal.SIGUSR1, pykka.debug.log_thread_tracebacks)

    If your application deadlocks, send the `SIGUSR1` signal to the process::

        kill -SIGUSR1 <pid of your process>

    Signal handler caveats:

    - The function *must* be registered as a signal handler by your main
      thread. If not, :func:`signal.signal` will raise a :exc:`ValueError`.

    - All signals in Python are handled by the main thread. Thus, the signal
      will only be handled, and the tracebacks logged, if your main thread is
      available to do some work. Making your main thread idle using
      :func:`time.sleep` is OK. The signal will awaken your main thread.
      Blocking your main thread on e.g. :func:`Queue.Queue.get` or
      :meth:`pykka.Future.get` will break signal handling, and thus you won't
      be able to signal your process to print the thread tracebacks.

    The morale is: setup signals using your main thread, start your actors,
    then let your main thread relax for the rest of your application's life
    cycle.

    For a complete example of how to use this, see
    ``examples/deadlock_debugging.py`` in Pykka's source code.

    .. versionadded:: 1.1
    """

    thread_names = dict((t.ident, t.name) for t in _threading.enumerate())

    for ident, frame in _sys._current_frames().items():
        name = thread_names.get(ident, '?')
        stack = ''.join(_traceback.format_stack(frame))
        _logger.critical(
            'Current state of %s (ident: %s):\n%s', name, ident, stack)

########NEW FILE########
__FILENAME__ = eventlet
from __future__ import absolute_import

import sys as _sys

import eventlet as _eventlet
import eventlet.event as _eventlet_event
import eventlet.queue as _eventlet_queue

from pykka import Timeout as _Timeout
from pykka.actor import Actor as _Actor
from pykka.future import Future as _Future


class EventletEvent(_eventlet_event.Event):
    """
    :class:`EventletEvent` adapts :class:`eventlet.event.Event` to
    :class:`threading.Event` interface.
    """

    def set(self):
        if self.ready():
            self.reset()
        self.send()

    def is_set(self):
        return self.ready()

    isSet = is_set

    def clear(self):
        if self.ready():
            self.reset()

    def wait(self, timeout):
        if timeout is not None:
            wait_timeout = _eventlet.Timeout(timeout)

            try:
                with wait_timeout:
                    super(EventletEvent, self).wait()
            except _eventlet.Timeout as t:
                if t is not wait_timeout:
                    raise
                return False
        else:
            self.event.wait()

        return True


class EventletFuture(_Future):
    """
    :class:`EventletFuture` implements :class:`pykka.Future` for use with
    :class:`EventletActor`.
    """

    event = None

    def __init__(self):
        super(EventletFuture, self).__init__()
        self.event = _eventlet_event.Event()

    def get(self, timeout=None):
        try:
            return super(EventletFuture, self).get(timeout=timeout)
        except NotImplementedError:
            pass

        if timeout is not None:
            wait_timeout = _eventlet.Timeout(timeout)
            try:
                with wait_timeout:
                    return self.event.wait()
            except _eventlet.Timeout as t:
                if t is not wait_timeout:
                    raise
                raise _Timeout(t)
        else:
            return self.event.wait()

    def set(self, value=None):
        self.event.send(value)

    def set_exception(self, exc_info=None):
        if isinstance(exc_info, BaseException):
            exc_info = (exc_info,)
        self.event.send_exception(*(exc_info or _sys.exc_info()))


class EventletActor(_Actor):
    """
    :class:`EventletActor` implements :class:`pykka.Actor` using the `eventlet
    <http://eventlet.net/>`_ library.

    This implementation uses eventlet green threads.
    """

    @staticmethod
    def _create_actor_inbox():
        return _eventlet_queue.Queue()

    @staticmethod
    def _create_future():
        return EventletFuture()

    def _start_actor_loop(self):
        _eventlet.greenthread.spawn(self._actor_loop)

########NEW FILE########
__FILENAME__ = exceptions
class ActorDeadError(Exception):
    """Exception raised when trying to use a dead or unavailable actor."""
    pass


class Timeout(Exception):
    """Exception raised at future timeout."""
    pass

########NEW FILE########
__FILENAME__ = future
import collections as _collections
import functools as _functools
import sys as _sys

try:
    # Python 2.x
    import Queue as _queue
    _basestring = basestring  # noqa
    PY3 = False
except ImportError:
    # Python 3.x
    import queue as _queue  # noqa
    _basestring = str
    PY3 = True

from pykka.exceptions import Timeout as _Timeout


def _is_iterable(x):
    return (
        isinstance(x, _collections.Iterable) and
        not isinstance(x, _basestring))


def _map(func, *iterables):
    if len(iterables) == 1 and not _is_iterable(iterables[0]):
        return func(iterables[0])
    else:
        return list(map(func, *iterables))


class Future(object):
    """
    A :class:`Future` is a handle to a value which are available or will be
    available in the future.

    Typically returned by calls to actor methods or accesses to actor fields.

    To get hold of the encapsulated value, call :meth:`Future.get`.
    """

    def __init__(self):
        super(Future, self).__init__()
        self._get_hook = None

    def get(self, timeout=None):
        """
        Get the value encapsulated by the future.

        If the encapsulated value is an exception, it is raised instead of
        returned.

        If ``timeout`` is :class:`None`, as default, the method will block
        until it gets a reply, potentially forever. If ``timeout`` is an
        integer or float, the method will wait for a reply for ``timeout``
        seconds, and then raise :exc:`pykka.Timeout`.

        The encapsulated value can be retrieved multiple times. The future will
        only block the first time the value is accessed.

        :param timeout: seconds to wait before timeout
        :type timeout: float or :class:`None`

        :raise: :exc:`pykka.Timeout` if timeout is reached
        :raise: encapsulated value if it is an exception
        :return: encapsulated value if it is not an exception
        """
        if self._get_hook is not None:
            return self._get_hook(timeout)
        raise NotImplementedError

    def set(self, value=None):
        """
        Set the encapsulated value.

        :param value: the encapsulated value or nothing
        :type value: any picklable object or :class:`None`
        :raise: an exception if set is called multiple times
        """
        raise NotImplementedError

    def set_exception(self, exc_info=None):
        """
        Set an exception as the encapsulated value.

        You can pass an ``exc_info`` three-tuple, as returned by
        :func:`sys.exc_info`. If you don't pass ``exc_info``,
        :func:`sys.exc_info` will be called and the value returned by it used.

        In other words, if you're calling :meth:`set_exception`, without any
        arguments, from an except block, the exception you're currently
        handling will automatically be set on the future.

        .. versionchanged:: 0.15
            Previously, :meth:`set_exception` accepted an exception
            instance as its only argument. This still works, but it is
            deprecated and will be removed in a future release.

        :param exc_info: the encapsulated exception
        :type exc_info: three-tuple of (exc_class, exc_instance, traceback)
        """
        raise NotImplementedError

    def set_get_hook(self, func):
        """
        Set a function to be executed when :meth:`get` is called.

        The function will be called when :meth:`get` is called, with the
        ``timeout`` value as the only argument. The function's return value
        will be returned from :meth:`get`.

        .. versionadded:: 1.2

        :param func: called to produce return value of :meth:`get`
        :type func: function accepting a timeout value
        """
        self._get_hook = func

    def filter(self, func):
        """
        Return a new future with only the items passing the predicate function.

        If the future's value is an iterable, :meth:`filter` will return a new
        future whose value is another iterable with only the items from the
        first iterable for which ``func(item)`` is true. If the future's value
        isn't an iterable, a :exc:`TypeError` will be raised when :meth:`get`
        is called.

        Example::

            >>> import pykka
            >>> f = pykka.ThreadingFuture()
            >>> g = f.filter(lambda x: x > 10)
            >>> g
            <pykka.future.ThreadingFuture at ...>
            >>> f.set(range(5, 15))
            >>> f.get()
            [5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
            >>> g.get()
            [11, 12, 13, 14]

        .. versionadded:: 1.2
        """
        future = self.__class__()
        future.set_get_hook(lambda timeout: list(filter(
            func, self.get(timeout))))
        return future

    def join(self, *futures):
        """
        Return a new future with a list of the result of multiple futures.

        One or more futures can be passed as arguments to :meth:`join`. The new
        future returns a list with the results from all the joined futures.

        Example::

            >>> import pykka
            >>> a = pykka.ThreadingFuture()
            >>> b = pykka.ThreadingFuture()
            >>> c = pykka.ThreadingFuture()
            >>> f = a.join(b, c)
            >>> a.set('def')
            >>> b.set(123)
            >>> c.set(False)
            >>> f.get()
            ['def', 123, False]

        .. versionadded:: 1.2
        """
        future = self.__class__()
        future.set_get_hook(lambda timeout: [
            f.get(timeout) for f in [self] + list(futures)])
        return future

    def map(self, func):
        """
        Return a new future with the result of the future passed through a
        function.

        If the future's result is a single value, it is simply passed to the
        function. If the future's result is an iterable, the function is
        applied to each item in the iterable.

        Example::

            >>> import pykka
            >>> f = pykka.ThreadingFuture()
            >>> g = f.map(lambda x: x + 10)
            >>> f.set(30)
            >>> g.get()
            40

            >>> f = pykka.ThreadingFuture()
            >>> g = f.map(lambda x: x + 10)
            >>> f.set([30, 300, 3000])
            >>> g.get()
            [40, 310, 3010]

        .. versionadded:: 1.2
        """
        future = self.__class__()
        future.set_get_hook(lambda timeout: _map(func, self.get(timeout)))
        return future

    def reduce(self, func, *args):
        """
        reduce(func[, initial])

        Return a new future with the result of reducing the future's iterable
        into a single value.

        The function of two arguments is applied cumulatively to the items of
        the iterable, from left to right. The result of the first function call
        is used as the first argument to the second function call, and so on,
        until the end of the iterable. If the future's value isn't an iterable,
        a :exc:`TypeError` is raised.

        :meth:`reduce` accepts an optional second argument, which will be used
        as an initial value in the first function call. If the iterable is
        empty, the initial value is returned.

        Example::

            >>> import pykka
            >>> f = pykka.ThreadingFuture()
            >>> g = f.reduce(lambda x, y: x + y)
            >>> f.set(['a', 'b', 'c'])
            >>> g.get()
            'abc'

            >>> f = pykka.ThreadingFuture()
            >>> g = f.reduce(lambda x, y: x + y)
            >>> f.set([1, 2, 3])
            >>> (1 + 2) + 3
            6
            >>> g.get()
            6

            >>> f = pykka.ThreadingFuture()
            >>> g = f.reduce(lambda x, y: x + y, 5)
            >>> f.set([1, 2, 3])
            >>> ((5 + 1) + 2) + 3
            11
            >>> g.get()
            11

            >>> f = pykka.ThreadingFuture()
            >>> g = f.reduce(lambda x, y: x + y, 5)
            >>> f.set([])
            >>> g.get()
            5

        .. versionadded:: 1.2
        """
        future = self.__class__()
        future.set_get_hook(lambda timeout: _functools.reduce(
            func, self.get(timeout), *args))
        return future


class ThreadingFuture(Future):
    """
    :class:`ThreadingFuture` implements :class:`Future` for use with
    :class:`ThreadingActor <pykka.ThreadingActor>`.

    The future is implemented using a :class:`Queue.Queue`.

    The future does *not* make a copy of the object which is :meth:`set()
    <pykka.Future.set>` on it. It is the setters responsibility to only pass
    immutable objects or make a copy of the object before setting it on the
    future.

    .. versionchanged:: 0.14
        Previously, the encapsulated value was a copy made with
        :func:`copy.deepcopy`, unless the encapsulated value was a future, in
        which case the original future was encapsulated.
    """

    def __init__(self):
        super(ThreadingFuture, self).__init__()
        self._queue = _queue.Queue(maxsize=1)
        self._data = None

    def get(self, timeout=None):
        try:
            return super(ThreadingFuture, self).get(timeout=timeout)
        except NotImplementedError:
            pass

        try:
            if self._data is None:
                self._data = self._queue.get(True, timeout)
            if 'exc_info' in self._data:
                exc_info = self._data['exc_info']
                if PY3:
                    raise exc_info[1].with_traceback(exc_info[2])
                else:
                    exec('raise exc_info[0], exc_info[1], exc_info[2]')
            else:
                return self._data['value']
        except _queue.Empty:
            raise _Timeout('%s seconds' % timeout)

    def set(self, value=None):
        self._queue.put({'value': value}, block=False)

    def set_exception(self, exc_info=None):
        if isinstance(exc_info, BaseException):
            exc_info = (exc_info.__class__, exc_info, None)
        self._queue.put({'exc_info': exc_info or _sys.exc_info()})


def get_all(futures, timeout=None):
    """
    Collect all values encapsulated in the list of futures.

    If ``timeout`` is not :class:`None`, the method will wait for a reply for
    ``timeout`` seconds, and then raise :exc:`pykka.Timeout`.

    :param futures: futures for the results to collect
    :type futures: list of :class:`pykka.Future`

    :param timeout: seconds to wait before timeout
    :type timeout: float or :class:`None`

    :raise: :exc:`pykka.Timeout` if timeout is reached
    :returns: list of results
    """
    return [future.get(timeout=timeout) for future in futures]

########NEW FILE########
__FILENAME__ = gevent
from __future__ import absolute_import

import sys as _sys

import gevent as _gevent
import gevent.event as _gevent_event
import gevent.queue as _gevent_queue

from pykka import Timeout as _Timeout
from pykka.actor import Actor as _Actor
from pykka.future import Future as _Future


class GeventFuture(_Future):
    """
    :class:`GeventFuture` implements :class:`pykka.Future` for use with
    :class:`GeventActor`.

    It encapsulates a :class:`gevent.event.AsyncResult` object which may be
    used directly, though it will couple your code with gevent.
    """

    #: The encapsulated :class:`gevent.event.AsyncResult`
    async_result = None

    def __init__(self, async_result=None):
        super(GeventFuture, self).__init__()
        if async_result is not None:
            self.async_result = async_result
        else:
            self.async_result = _gevent_event.AsyncResult()

    def get(self, timeout=None):
        try:
            return super(GeventFuture, self).get(timeout=timeout)
        except NotImplementedError:
            pass

        try:
            return self.async_result.get(timeout=timeout)
        except _gevent.Timeout as e:
            raise _Timeout(e)

    def set(self, value=None):
        assert not self.async_result.ready(), 'value has already been set'
        self.async_result.set(value)

    def set_exception(self, exc_info=None):
        if isinstance(exc_info, BaseException):
            exception = exc_info
        else:
            exc_info = exc_info or _sys.exc_info()
            exception = exc_info[1]
        self.async_result.set_exception(exception)


class GeventActor(_Actor):
    """
    :class:`GeventActor` implements :class:`pykka.Actor` using the `gevent
    <http://www.gevent.org/>`_ library. gevent is a coroutine-based Python
    networking library that uses greenlet to provide a high-level synchronous
    API on top of libevent event loop.

    This is a very fast implementation, but as of gevent 0.13.x it does not
    work in combination with other threads.
    """

    @staticmethod
    def _create_actor_inbox():
        return _gevent_queue.Queue()

    @staticmethod
    def _create_future():
        return GeventFuture()

    def _start_actor_loop(self):
        _gevent.Greenlet.spawn(self._actor_loop)

########NEW FILE########
__FILENAME__ = proxy
import collections as _collections
import sys as _sys

from pykka.exceptions import ActorDeadError as _ActorDeadError


class ActorProxy(object):
    """
    An :class:`ActorProxy` wraps an :class:`ActorRef <pykka.ActorRef>`
    instance. The proxy allows the referenced actor to be used through regular
    method calls and field access.

    You can create an :class:`ActorProxy` from any :class:`ActorRef
    <pykka.ActorRef>`::

        actor_ref = MyActor.start()
        actor_proxy = ActorProxy(actor_ref)

    You can also get an :class:`ActorProxy` by using :meth:`proxy()
    <pykka.ActorRef.proxy>`::

        actor_proxy = MyActor.start().proxy()

    When reading an attribute or getting a return value from a method, you get
    a :class:`Future <pykka.Future>` object back. To get the enclosed value
    from the future, you must call :meth:`get() <pykka.Future.get>` on the
    returned future::

        print actor_proxy.string_attribute.get()
        print actor_proxy.count().get() + 1

    If you call a method just for it's side effects and do not care about the
    return value, you do not need to accept the returned future or call
    :meth:`get() <pykka.Future.get>` on the future. Simply call the method, and
    it will be executed concurrently with your own code::

        actor_proxy.method_with_side_effect()

    If you want to block your own code from continuing while the other method
    is processing, you can use :meth:`get() <pykka.Future.get>` to block until
    it completes::

        actor_proxy.method_with_side_effect().get()

    An actor can use a proxy to itself to schedule work for itself. The
    scheduled work will only be done after the current message and all messages
    already in the inbox are processed.

    For example, if an actor can split a time consuming task into multiple
    parts, and after completing each part can ask itself to start on the next
    part using proxied calls or messages to itself, it can react faster to
    other incoming messages as they will be interleaved with the parts of the
    time consuming task. This is especially useful for being able to stop the
    actor in the middle of a time consuming task.

    To create a proxy to yourself, use the actor's :attr:`actor_ref
    <pykka.Actor.actor_ref>` attribute::

        proxy_to_myself_in_the_future = self.actor_ref.proxy()

    If you create a proxy in your actor's constructor or :meth:`on_start
    <pykka.Actor.on_start>` method, you can create a nice API for deferring
    work to yourself in the future::

        def __init__(self):
            ...
            self.in_future = self.actor_ref.proxy()
            ...

        def do_work(self):
            ...
            self.in_future.do_more_work()
            ...

        def do_more_work(self):
            ...

    An example of :class:`ActorProxy` usage:

    .. literalinclude:: ../examples/counter.py

    :param actor_ref: reference to the actor to proxy
    :type actor_ref: :class:`pykka.ActorRef`

    :raise: :exc:`pykka.ActorDeadError` if actor is not available
    """

    #: The actor's :class:`pykka.ActorRef` instance.
    actor_ref = None

    def __init__(self, actor_ref, attr_path=None):
        if not actor_ref.is_alive():
            raise _ActorDeadError('%s not found' % actor_ref)
        self.actor_ref = actor_ref
        self._actor = actor_ref._actor
        self._attr_path = attr_path or tuple()
        self._known_attrs = self._get_attributes()
        self._actor_proxies = {}
        self._callable_proxies = {}

    def _get_attributes(self):
        """Gathers actor attributes needed to proxy the actor"""
        result = {}
        attr_paths_to_visit = [[attr_name] for attr_name in dir(self._actor)]
        while attr_paths_to_visit:
            attr_path = attr_paths_to_visit.pop(0)
            if self._is_exposable_attribute(attr_path[-1]):
                attr = self._actor._get_attribute_from_path(attr_path)
                result[tuple(attr_path)] = {
                    'callable': self._is_callable_attribute(attr),
                    'traversable': self._is_traversable_attribute(attr),
                }
                if self._is_traversable_attribute(attr):
                    for attr_name in dir(attr):
                        attr_paths_to_visit.append(attr_path + [attr_name])
        return result

    def _is_exposable_attribute(self, attr_name):
        """
        Returns true for any attribute name that may be exposed through
        :class:`ActorProxy`.
        """
        return not attr_name.startswith('_')

    def _is_callable_attribute(self, attr):
        """Returns true for any attribute that is callable."""
        # isinstance(attr, collections.Callable), as recommended by 2to3, does
        # not work on CPython 2.6.4 if the attribute is an Queue.Queue, but
        # works on 2.6.6.
        if _sys.version_info < (3,):
            return callable(attr)
        else:
            return isinstance(attr, _collections.Callable)

    def _is_traversable_attribute(self, attr):
        """
        Returns true for any attribute that may be traversed from another
        actor through a proxy.
        """
        return hasattr(attr, 'pykka_traversable')

    def __repr__(self):
        return '<ActorProxy for %s, attr_path=%s>' % (
            self.actor_ref, self._attr_path)

    def __dir__(self):
        result = ['__class__']
        result += list(self.__class__.__dict__.keys())
        result += list(self.__dict__.keys())
        result += [
            attr_path[0] for attr_path in list(self._known_attrs.keys())]
        return sorted(result)

    def __getattr__(self, name):
        """Get a field or callable from the actor."""
        attr_path = self._attr_path + (name,)
        if attr_path not in self._known_attrs:
            self._known_attrs = self._get_attributes()
        attr_info = self._known_attrs.get(attr_path)
        if attr_info is None:
            raise AttributeError('%s has no attribute "%s"' % (self, name))
        if attr_info['callable']:
            if attr_path not in self._callable_proxies:
                self._callable_proxies[attr_path] = _CallableProxy(
                    self.actor_ref, attr_path)
            return self._callable_proxies[attr_path]
        elif attr_info['traversable']:
            if attr_path not in self._actor_proxies:
                self._actor_proxies[attr_path] = ActorProxy(
                    self.actor_ref, attr_path)
            return self._actor_proxies[attr_path]
        else:
            message = {
                'command': 'pykka_getattr',
                'attr_path': attr_path,
            }
            return self.actor_ref.ask(message, block=False)

    def __setattr__(self, name, value):
        """
        Set a field on the actor.

        Blocks until the field is set to check if any exceptions was raised.
        """
        if name == 'actor_ref' or name.startswith('_'):
            return super(ActorProxy, self).__setattr__(name, value)
        attr_path = self._attr_path + (name,)
        message = {
            'command': 'pykka_setattr',
            'attr_path': attr_path,
            'value': value,
        }
        return self.actor_ref.ask(message)


class _CallableProxy(object):
    """Internal helper class for proxying callables."""
    def __init__(self, ref, attr_path):
        self.actor_ref = ref
        self._attr_path = attr_path

    def __call__(self, *args, **kwargs):
        message = {
            'command': 'pykka_call',
            'attr_path': self._attr_path,
            'args': args,
            'kwargs': kwargs,
        }
        return self.actor_ref.ask(message, block=False)

########NEW FILE########
__FILENAME__ = registry
import logging as _logging
import threading as _threading

try:
    _basestring = basestring
except NameError:
    # Python 3
    _basestring = str

_logger = _logging.getLogger('pykka')


class ActorRegistry(object):
    """
    Registry which provides easy access to all running actors.

    Contains global state, but should be thread-safe.
    """

    _actor_refs = []
    _actor_refs_lock = _threading.RLock()

    @classmethod
    def broadcast(cls, message, target_class=None):
        """
        Broadcast ``message`` to all actors of the specified ``target_class``.

        If no ``target_class`` is specified, the message is broadcasted to all
        actors.

        :param message: the message to send
        :type message: picklable dict

        :param target_class: optional actor class to broadcast the message to
        :type target_class: class or class name
        """
        if isinstance(target_class, _basestring):
            targets = cls.get_by_class_name(target_class)
        elif target_class is not None:
            targets = cls.get_by_class(target_class)
        else:
            targets = cls.get_all()
        for ref in targets:
            ref.tell(message)

    @classmethod
    def get_all(cls):
        """
        Get :class:`ActorRef <pykka.ActorRef>` for all running actors.

        :returns: list of :class:`pykka.ActorRef`
        """
        with cls._actor_refs_lock:
            return cls._actor_refs[:]

    @classmethod
    def get_by_class(cls, actor_class):
        """
        Get :class:`ActorRef` for all running actors of the given class, or of
        any subclass of the given class.

        :param actor_class: actor class, or any superclass of the actor
        :type actor_class: class

        :returns: list of :class:`pykka.ActorRef`
        """
        with cls._actor_refs_lock:
            return [
                ref for ref in cls._actor_refs
                if issubclass(ref.actor_class, actor_class)]

    @classmethod
    def get_by_class_name(cls, actor_class_name):
        """
        Get :class:`ActorRef` for all running actors of the given class
        name.

        :param actor_class_name: actor class name
        :type actor_class_name: string

        :returns: list of :class:`pykka.ActorRef`
        """
        with cls._actor_refs_lock:
            return [
                ref for ref in cls._actor_refs
                if ref.actor_class.__name__ == actor_class_name]

    @classmethod
    def get_by_urn(cls, actor_urn):
        """
        Get an actor by its universally unique URN.

        :param actor_urn: actor URN
        :type actor_urn: string

        :returns: :class:`pykka.ActorRef` or :class:`None` if not found
        """
        with cls._actor_refs_lock:
            refs = [
                ref for ref in cls._actor_refs
                if ref.actor_urn == actor_urn]
            if refs:
                return refs[0]

    @classmethod
    def register(cls, actor_ref):
        """
        Register an :class:`ActorRef` in the registry.

        This is done automatically when an actor is started, e.g. by calling
        :meth:`Actor.start() <pykka.Actor.start>`.

        :param actor_ref: reference to the actor to register
        :type actor_ref: :class:`pykka.ActorRef`
        """
        with cls._actor_refs_lock:
            cls._actor_refs.append(actor_ref)
        _logger.debug('Registered %s', actor_ref)

    @classmethod
    def stop_all(cls, block=True, timeout=None):
        """
        Stop all running actors.

        ``block`` and ``timeout`` works as for
        :meth:`ActorRef.stop() <pykka.ActorRef.stop>`.

        If ``block`` is :class:`True`, the actors are guaranteed to be stopped
        in the reverse of the order they were started in. This is helpful if
        you have simple dependencies in between your actors, where it is
        sufficient to shut down actors in a LIFO manner: last started, first
        stopped.

        If you have more complex dependencies in between your actors, you
        should take care to shut them down in the required order yourself, e.g.
        by stopping dependees from a dependency's
        :meth:`on_stop() <pykka.Actor.on_stop>` method.

        :returns: If not blocking, a list with a future for each stop action.
            If blocking, a list of return values from
            :meth:`pykka.ActorRef.stop`.
        """
        return [ref.stop(block, timeout) for ref in reversed(cls.get_all())]

    @classmethod
    def unregister(cls, actor_ref):
        """
        Remove an :class:`ActorRef <pykka.ActorRef>` from the registry.

        This is done automatically when an actor is stopped, e.g. by calling
        :meth:`Actor.stop() <pykka.Actor.stop>`.

        :param actor_ref: reference to the actor to unregister
        :type actor_ref: :class:`pykka.ActorRef`
        """
        removed = False
        with cls._actor_refs_lock:
            if actor_ref in cls._actor_refs:
                cls._actor_refs.remove(actor_ref)
                removed = True
        if removed:
            _logger.debug('Unregistered %s', actor_ref)
        else:
            _logger.debug(
                'Unregistered %s (not found in registry)', actor_ref)

########NEW FILE########
__FILENAME__ = actor_test
import threading
import unittest
import uuid

from pykka.actor import ThreadingActor
from pykka.exceptions import ActorDeadError
from pykka.registry import ActorRegistry


class AnActor(object):
    def __init__(self, **events):
        super(AnActor, self).__init__()
        self.on_start_was_called = events['on_start_was_called']
        self.on_stop_was_called = events['on_stop_was_called']
        self.on_failure_was_called = events['on_failure_was_called']
        self.actor_was_registered_before_on_start_was_called = events[
            'actor_was_registered_before_on_start_was_called']
        self.greetings_was_received = events['greetings_was_received']

    def on_start(self):
        self.on_start_was_called.set()
        if ActorRegistry.get_by_urn(self.actor_urn) is not None:
            self.actor_was_registered_before_on_start_was_called.set()

    def on_stop(self):
        self.on_stop_was_called.set()

    def on_failure(self, *args):
        self.on_failure_was_called.set()

    def on_receive(self, message):
        if message.get('command') == 'raise exception':
            raise Exception('foo')
        elif message.get('command') == 'raise base exception':
            raise BaseException()
        elif message.get('command') == 'stop twice':
            self.stop()
            self.stop()
        elif message.get('command') == 'message self then stop':
            self.actor_ref.tell({'command': 'greetings'})
            self.stop()
        elif message.get('command') == 'greetings':
            self.greetings_was_received.set()
        elif message.get('command') == 'callback':
            message['callback']()
        else:
            super(AnActor, self).on_receive(message)


class EarlyStoppingActor(object):
    def __init__(self, on_stop_was_called):
        super(EarlyStoppingActor, self).__init__()
        self.on_stop_was_called = on_stop_was_called

    def on_start(self):
        self.stop()

    def on_stop(self):
        self.on_stop_was_called.set()


class EarlyFailingActor(object):
    def __init__(self, on_start_was_called):
        super(EarlyFailingActor, self).__init__()
        self.on_start_was_called = on_start_was_called

    def on_start(self):
        try:
            raise RuntimeError('on_start failure')
        finally:
            self.on_start_was_called.set()


class LateFailingActor(object):
    def __init__(self, on_stop_was_called):
        super(LateFailingActor, self).__init__()
        self.on_stop_was_called = on_stop_was_called

    def on_start(self):
        self.stop()

    def on_stop(self):
        try:
            raise RuntimeError('on_stop failure')
        finally:
            self.on_stop_was_called.set()


class FailingOnFailureActor(object):
    def __init__(self, on_failure_was_called):
        super(FailingOnFailureActor, self).__init__()
        self.on_failure_was_called = on_failure_was_called

    def on_receive(self, message):
        if message.get('command') == 'raise exception':
            raise Exception('on_receive failure')
        else:
            super(FailingOnFailureActor, self).on_receive(message)

    def on_failure(self, *args):
        try:
            raise RuntimeError('on_failure failure')
        finally:
            self.on_failure_was_called.set()


class ActorTest(object):
    def setUp(self):
        self.on_start_was_called = self.event_class()
        self.on_stop_was_called = self.event_class()
        self.on_failure_was_called = self.event_class()
        self.actor_was_registered_before_on_start_was_called = (
            self.event_class())
        self.greetings_was_received = self.event_class()

        self.actor_ref = self.AnActor.start(
            on_start_was_called=self.on_start_was_called,
            on_stop_was_called=self.on_stop_was_called,
            on_failure_was_called=self.on_failure_was_called,
            actor_was_registered_before_on_start_was_called=(
                self.actor_was_registered_before_on_start_was_called),
            greetings_was_received=self.greetings_was_received)
        self.actor_proxy = self.actor_ref.proxy()

    def tearDown(self):
        ActorRegistry.stop_all()

    def test_messages_left_in_queue_after_actor_stops_receive_an_error(self):
        event = self.event_class()
        self.actor_ref.tell({'command': 'callback', 'callback': event.wait})
        self.actor_ref.stop(block=False)
        response = self.actor_ref.ask({'command': 'irrelevant'}, block=False)
        event.set()

        self.assertRaises(ActorDeadError, response.get, timeout=0.5)

    def test_stop_requests_left_in_queue_after_actor_stops_are_handled(self):
        event = self.event_class()
        self.actor_ref.tell({'command': 'callback', 'callback': event.wait})
        self.actor_ref.stop(block=False)
        response = self.actor_ref.ask({'command': 'pykka_stop'}, block=False)
        event.set()

        response.get(timeout=0.5)

    def test_actor_has_an_uuid4_based_urn(self):
        self.assertEqual(4, uuid.UUID(self.actor_ref.actor_urn).version)

    def test_actor_has_unique_uuid(self):
        event = self.event_class()
        actors = [
            self.AnActor.start(
                on_start_was_called=event,
                on_stop_was_called=event,
                on_failure_was_called=event,
                actor_was_registered_before_on_start_was_called=event,
                greetings_was_received=event)
            for _ in range(3)]

        self.assertNotEqual(actors[0].actor_urn, actors[1].actor_urn)
        self.assertNotEqual(actors[1].actor_urn, actors[2].actor_urn)
        self.assertNotEqual(actors[2].actor_urn, actors[0].actor_urn)

    def test_str_on_raw_actor_contains_actor_class_name(self):
        event = self.event_class()
        unstarted_actor = self.AnActor(
            on_start_was_called=event,
            on_stop_was_called=event,
            on_failure_was_called=event,
            actor_was_registered_before_on_start_was_called=event,
            greetings_was_received=event)
        self.assert_('AnActor' in str(unstarted_actor))

    def test_str_on_raw_actor_contains_actor_urn(self):
        event = self.event_class()
        unstarted_actor = self.AnActor(
            on_start_was_called=event,
            on_stop_was_called=event,
            on_failure_was_called=event,
            actor_was_registered_before_on_start_was_called=event,
            greetings_was_received=event)
        self.assert_(unstarted_actor.actor_urn in str(unstarted_actor))

    def test_init_can_be_called_with_arbitrary_arguments(self):
        self.SuperInitActor(1, 2, 3, foo='bar')

    def test_on_start_is_called_before_first_message_is_processed(self):
        self.on_start_was_called.wait(5)
        self.assertTrue(self.on_start_was_called.is_set())

    def test_on_start_is_called_after_the_actor_is_registered(self):
        # NOTE: If the actor is registered after the actor is started, this
        # test may still occasionally pass, as it is dependant on the exact
        # timing of events. When the actor is first registered and then
        # started, this test should always pass.
        self.on_start_was_called.wait(5)
        self.assertTrue(self.on_start_was_called.is_set())
        self.actor_was_registered_before_on_start_was_called.wait(0.1)
        self.assertTrue(
            self.actor_was_registered_before_on_start_was_called.is_set())

    def test_on_start_can_stop_actor_before_receive_loop_is_started(self):
        # NOTE: This test will pass even if the actor is allowed to start the
        # receive loop, but it will cause the test suite to hang, as the actor
        # thread is blocking on receiving messages to the actor inbox forever.
        # If one made this test specifically for ThreadingActor, one could add
        # an assertFalse(actor_thread.is_alive()), which would cause the test
        # to fail properly.
        stop_event = self.event_class()
        another_actor = self.EarlyStoppingActor.start(stop_event)
        stop_event.wait(5)
        self.assertTrue(stop_event.is_set())
        self.assertFalse(another_actor.is_alive())

    def test_on_start_failure_causes_actor_to_stop(self):
        # Actor should not be alive if on_start fails.
        start_event = self.event_class()
        actor_ref = self.EarlyFailingActor.start(start_event)
        start_event.wait(5)
        actor_ref.actor_stopped.wait(5)
        self.assertFalse(actor_ref.is_alive())

    def test_on_stop_is_called_when_actor_is_stopped(self):
        self.assertFalse(self.on_stop_was_called.is_set())
        self.actor_ref.stop()
        self.on_stop_was_called.wait(5)
        self.assertTrue(self.on_stop_was_called.is_set())

    def test_on_stop_failure_causes_actor_to_stop(self):
        stop_event = self.event_class()
        actor = self.LateFailingActor.start(stop_event)
        stop_event.wait(5)
        self.assertFalse(actor.is_alive())

    def test_on_failure_is_called_when_exception_cannot_be_returned(self):
        self.assertFalse(self.on_failure_was_called.is_set())
        self.actor_ref.tell({'command': 'raise exception'})
        self.on_failure_was_called.wait(5)
        self.assertTrue(self.on_failure_was_called.is_set())
        self.assertFalse(self.on_stop_was_called.is_set())

    def test_on_failure_failure_causes_actor_to_stop(self):
        failure_event = self.event_class()
        actor = self.FailingOnFailureActor.start(failure_event)
        actor.tell({'command': 'raise exception'})
        failure_event.wait(5)
        self.assertFalse(actor.is_alive())

    def test_actor_is_stopped_when_unhandled_exceptions_are_raised(self):
        self.assertFalse(self.on_failure_was_called.is_set())
        self.actor_ref.tell({'command': 'raise exception'})
        self.on_failure_was_called.wait(5)
        self.assertTrue(self.on_failure_was_called.is_set())
        self.assertEqual(0, len(ActorRegistry.get_all()))

    def test_all_actors_are_stopped_on_base_exception(self):
        start_event = self.event_class()
        stop_event = self.event_class()
        fail_event = self.event_class()
        registered_event = self.event_class()
        greetings_event = self.event_class()
        self.AnActor.start(
            on_start_was_called=start_event,
            on_stop_was_called=stop_event,
            on_failure_was_called=fail_event,
            actor_was_registered_before_on_start_was_called=registered_event,
            greetings_was_received=greetings_event)

        self.assertEqual(2, len(ActorRegistry.get_all()))
        self.assertFalse(self.on_stop_was_called.is_set())
        self.actor_ref.tell({'command': 'raise base exception'})
        self.on_stop_was_called.wait(5)
        self.assertTrue(self.on_stop_was_called.is_set())
        self.assert_(1 >= len(ActorRegistry.get_all()))
        stop_event.wait(5)
        self.assertTrue(stop_event.is_set())
        self.assertEqual(0, len(ActorRegistry.get_all()))

    def test_actor_can_call_stop_on_self_multiple_times(self):
        self.actor_ref.ask({'command': 'stop twice'})

    def test_actor_processes_all_messages_before_stop_on_self_stops_it(self):
        self.actor_ref.ask({'command': 'message self then stop'})

        self.greetings_was_received.wait(5)
        self.assertTrue(self.greetings_was_received.is_set())

        self.on_stop_was_called.wait(5)

        self.assertEqual(0, len(ActorRegistry.get_all()))


def ConcreteActorTest(actor_class, event_class):
    class C(ActorTest, unittest.TestCase):
        class AnActor(AnActor, actor_class):
            pass

        class EarlyStoppingActor(EarlyStoppingActor, actor_class):
            pass

        class EarlyFailingActor(EarlyFailingActor, actor_class):
            pass

        class LateFailingActor(LateFailingActor, actor_class):
            pass

        class FailingOnFailureActor(FailingOnFailureActor, actor_class):
            pass

        class SuperInitActor(actor_class):
            pass

    C.__name__ = '%sTest' % actor_class.__name__
    C.event_class = event_class
    return C


class ThreadingActorTest(ConcreteActorTest(ThreadingActor, threading.Event)):
    class DaemonActor(ThreadingActor):
        use_daemon_thread = True

    def test_actor_thread_is_named_after_pykka_actor_class(self):
        alive_threads = threading.enumerate()
        alive_thread_names = [t.name for t in alive_threads]
        named_correctly = [
            name.startswith(AnActor.__name__) for name in alive_thread_names]
        self.assert_(any(named_correctly))

    def test_actor_thread_is_not_daemonic_by_default(self):
        alive_threads = threading.enumerate()
        actor_threads = [
            t for t in alive_threads if t.name.startswith('AnActor')]
        self.assertEqual(1, len(actor_threads))
        self.assertFalse(actor_threads[0].daemon)

    def test_actor_thread_is_daemonic_if_use_daemon_thread_flag_is_set(self):
        actor_ref = self.DaemonActor.start()
        alive_threads = threading.enumerate()
        actor_threads = [
            t for t in alive_threads if t.name.startswith('DaemonActor')]
        self.assertEqual(1, len(actor_threads))
        self.assertTrue(actor_threads[0].daemon)
        actor_ref.stop()


try:
    import gevent.event
    from pykka.gevent import GeventActor
    GeventActorTest = ConcreteActorTest(GeventActor, gevent.event.Event)
except ImportError:
    pass

try:
    import eventlet  # noqa
    from pykka.eventlet import EventletActor, EventletEvent
    EventletActorTest = ConcreteActorTest(EventletActor, EventletEvent)
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = field_access_test
import unittest

from pykka.actor import ThreadingActor


class SomeObject(object):
    pykka_traversable = False
    baz = 'bar.baz'

    _private_field = 'secret'


class ActorWithFields(object):
    foo = 'foo'

    bar = SomeObject()
    bar.pykka_traversable = True

    _private_field = 'secret'


class FieldAccessTest(object):
    def setUp(self):
        self.proxy = self.ActorWithFields.start().proxy()

    def tearDown(self):
        self.proxy.stop()

    def test_actor_field_can_be_read_using_get_postfix(self):
        self.assertEqual('foo', self.proxy.foo.get())

    def test_actor_field_can_be_set_using_assignment(self):
        self.assertEqual('foo', self.proxy.foo.get())
        self.proxy.foo = 'foo2'
        self.assertEqual('foo2', self.proxy.foo.get())

    def test_private_field_access_raises_exception(self):
        try:
            self.proxy._private_field.get()
            self.fail('Should raise AttributeError exception')
        except AttributeError:
            pass
        except Exception:
            self.fail('Should raise AttributeError exception')

    def test_attr_of_traversable_attr_can_be_read(self):
        self.assertEqual('bar.baz', self.proxy.bar.baz.get())


def ConcreteFieldAccessTest(actor_class):
    class C(FieldAccessTest, unittest.TestCase):
        class ActorWithFields(ActorWithFields, actor_class):
            pass
    C.__name__ = '%sFieldAccessTest' % actor_class.__name__
    return C


ThreadingFieldAccessTest = ConcreteFieldAccessTest(ThreadingActor)


try:
    from pykka.gevent import GeventActor
    GeventFieldAccessTest = ConcreteFieldAccessTest(GeventActor)
except ImportError:
    pass


try:
    from pykka.eventlet import EventletActor
    EventletFieldAccessTest = ConcreteFieldAccessTest(EventletActor)
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = future_test
import sys
import traceback
import unittest

from pykka import Timeout
from pykka.future import Future, ThreadingFuture, get_all


class FutureBaseTest(unittest.TestCase):
    def setUp(self):
        self.future = Future()

    def test_future_get_is_not_implemented(self):
        self.assertRaises(NotImplementedError, self.future.get)

    def test_future_set_is_not_implemented(self):
        self.assertRaises(NotImplementedError, self.future.set, None)

    def test_future_set_exception_is_not_implemented(self):
        self.assertRaises(NotImplementedError, self.future.set_exception, None)


class FutureTest(object):
    def setUp(self):
        self.results = [self.future_class() for _ in range(3)]

    def test_set_multiple_times_fails(self):
        self.results[0].set(0)
        self.assertRaises(Exception, self.results[0].set, 0)

    def test_get_all_blocks_until_all_futures_are_available(self):
        self.results[0].set(0)
        self.results[1].set(1)
        self.results[2].set(2)
        result = get_all(self.results)
        self.assertEqual(result, [0, 1, 2])

    def test_get_all_raises_timeout_if_not_all_futures_are_available(self):
        self.results[0].set(0)
        self.results[1].set(1)

        self.assertRaises(Timeout, get_all, self.results, timeout=0)

    def test_get_all_can_be_called_multiple_times(self):
        self.results[0].set(0)
        self.results[1].set(1)
        self.results[2].set(2)
        result1 = get_all(self.results)
        result2 = get_all(self.results)
        self.assertEqual(result1, result2)

    def test_future_in_future_works(self):
        inner_future = self.future_class()
        inner_future.set('foo')
        outer_future = self.future_class()
        outer_future.set(inner_future)
        self.assertEqual(outer_future.get().get(), 'foo')

    def test_get_raises_exception_with_full_traceback(self):
        exc_class_get = None
        exc_class_set = None
        exc_instance_get = None
        exc_instance_set = None
        exc_traceback_get = None
        exc_traceback_set = None
        future = self.future_class()

        try:
            raise NameError('foo')
        except NameError:
            exc_class_set, exc_instance_set, exc_traceback_set = sys.exc_info()
            future.set_exception()

        # We could move to another thread at this point

        try:
            future.get()
        except NameError:
            exc_class_get, exc_instance_get, exc_traceback_get = sys.exc_info()

        self.assertEqual(exc_class_set, exc_class_get)
        self.assertEqual(exc_instance_set, exc_instance_get)

        exc_traceback_list_set = list(reversed(
            traceback.extract_tb(exc_traceback_set)))
        exc_traceback_list_get = list(reversed(
            traceback.extract_tb(exc_traceback_get)))

        # All frames from the first traceback should be included in the
        # traceback from the future.get() reraise
        self.assert_(len(exc_traceback_list_set) < len(exc_traceback_list_get))
        for i, frame in enumerate(exc_traceback_list_set):
            self.assertEquals(frame, exc_traceback_list_get[i])

    def test_filter_excludes_items_not_matching_predicate(self):
        future = self.results[0].filter(lambda x: x > 10)
        self.results[0].set([1, 3, 5, 7, 9, 11, 13, 15, 17, 19])

        self.assertEqual(future.get(timeout=0), [11, 13, 15, 17, 19])

    def test_filter_on_noniterable(self):
        future = self.results[0].filter(lambda x: x > 10)
        self.results[0].set(1)

        self.assertRaises(TypeError, future.get, timeout=0)

    def test_filter_preserves_the_timeout_kwarg(self):
        future = self.results[0].filter(lambda x: x > 10)

        self.assertRaises(Timeout, future.get, timeout=0)

    def test_join_combines_multiple_futures_into_one(self):
        future = self.results[0].join(self.results[1], self.results[2])
        self.results[0].set(0)
        self.results[1].set(1)
        self.results[2].set(2)

        self.assertEqual(future.get(timeout=0), [0, 1, 2])

    def test_join_preserves_timeout_kwarg(self):
        future = self.results[0].join(self.results[1], self.results[2])
        self.results[0].set(0)
        self.results[1].set(1)

        self.assertRaises(Timeout, future.get, timeout=0)

    def test_map_returns_future_which_passes_noniterable_through_func(self):
        future = self.results[0].map(lambda x: x + 10)
        self.results[0].set(30)

        self.assertEqual(future.get(timeout=0), 40)

    def test_map_returns_future_which_maps_iterable_through_func(self):
        future = self.results[0].map(lambda x: x + 10)
        self.results[0].set([10, 20, 30])

        self.assertEqual(future.get(timeout=0), [20, 30, 40])

    def test_map_preserves_timeout_kwarg(self):
        future = self.results[0].map(lambda x: x + 10)

        self.assertRaises(Timeout, future.get, timeout=0)

    def test_reduce_applies_function_cumulatively_from_the_left(self):
        future = self.results[0].reduce(lambda x, y: x + y)
        self.results[0].set([1, 2, 3, 4])

        self.assertEqual(future.get(timeout=0), 10)

    def test_reduce_accepts_an_initial_value(self):
        future = self.results[0].reduce(lambda x, y: x + y, 5)
        self.results[0].set([1, 2, 3, 4])

        self.assertEqual(future.get(timeout=0), 15)

    def test_reduce_on_noniterable(self):
        future = self.results[0].reduce(lambda x, y: x + y)
        self.results[0].set(1)

        self.assertRaises(TypeError, future.get, timeout=0)

    def test_reduce_preserves_the_timeout_kwarg(self):
        future = self.results[0].reduce(lambda x, y: x + y)

        self.assertRaises(Timeout, future.get, timeout=0)


class ThreadingFutureTest(FutureTest, unittest.TestCase):
    future_class = ThreadingFuture


try:
    from gevent.event import AsyncResult
    from pykka.gevent import GeventFuture

    class GeventFutureTest(FutureTest, unittest.TestCase):
        future_class = GeventFuture

        def test_can_wrap_existing_async_result(self):
            async_result = AsyncResult()
            future = GeventFuture(async_result)
            self.assertEquals(async_result, future.async_result)

        def test_get_raises_exception_with_full_traceback(self):
            # gevent prints the first half of the traceback instead of
            # passing it through to the other side of the AsyncResult
            pass
except ImportError:
    pass


try:
    from pykka.eventlet import EventletFuture

    class EventletFutureTest(FutureTest, unittest.TestCase):
        future_class = EventletFuture
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = logging_test
import logging
import threading
import unittest

from pykka.actor import ThreadingActor
from pykka.registry import ActorRegistry

from tests import TestLogHandler
from tests.actor_test import (
    EarlyFailingActor, LateFailingActor, FailingOnFailureActor)


class LoggingNullHandlerTest(unittest.TestCase):
    def test_null_handler_is_added_to_avoid_warnings(self):
        logger = logging.getLogger('pykka')
        handler_names = [h.__class__.__name__ for h in logger.handlers]
        self.assert_('NullHandler' in handler_names)


class ActorLoggingTest(object):
    def setUp(self):
        self.on_stop_was_called = self.event_class()
        self.on_failure_was_called = self.event_class()

        self.actor_ref = self.AnActor.start(
            self.on_stop_was_called, self.on_failure_was_called)
        self.actor_proxy = self.actor_ref.proxy()

        self.log_handler = TestLogHandler(logging.DEBUG)
        self.root_logger = logging.getLogger()
        self.root_logger.addHandler(self.log_handler)

    def tearDown(self):
        self.log_handler.close()
        ActorRegistry.stop_all()

    def test_unexpected_messages_are_logged(self):
        self.actor_ref.ask({'unhandled': 'message'})
        self.log_handler.wait_for_message('warning')
        with self.log_handler.lock:
            self.assertEqual(1, len(self.log_handler.messages['warning']))
            log_record = self.log_handler.messages['warning'][0]
        self.assertEqual(
            'Unexpected message received by %s' % self.actor_ref,
            log_record.getMessage().split(': ')[0])

    def test_exception_is_logged_when_returned_to_caller(self):
        try:
            self.actor_proxy.raise_exception().get()
            self.fail('Should raise exception')
        except Exception:
            pass
        self.log_handler.wait_for_message('debug')
        with self.log_handler.lock:
            self.assertEqual(1, len(self.log_handler.messages['debug']))
            log_record = self.log_handler.messages['debug'][0]
        self.assertEqual(
            'Exception returned from %s to caller:' % self.actor_ref,
            log_record.getMessage())
        self.assertEqual(Exception, log_record.exc_info[0])
        self.assertEqual('foo', str(log_record.exc_info[1]))

    def test_exception_is_logged_when_not_reply_requested(self):
        self.on_failure_was_called.clear()
        self.actor_ref.tell({'command': 'raise exception'})
        self.on_failure_was_called.wait(5)
        self.assertTrue(self.on_failure_was_called.is_set())
        self.log_handler.wait_for_message('error')
        with self.log_handler.lock:
            self.assertEqual(1, len(self.log_handler.messages['error']))
            log_record = self.log_handler.messages['error'][0]
        self.assertEqual(
            'Unhandled exception in %s:' % self.actor_ref,
            log_record.getMessage())
        self.assertEqual(Exception, log_record.exc_info[0])
        self.assertEqual('foo', str(log_record.exc_info[1]))

    def test_base_exception_is_logged(self):
        self.log_handler.reset()
        self.on_stop_was_called.clear()
        self.actor_ref.tell({'command': 'raise base exception'})
        self.on_stop_was_called.wait(5)
        self.assertTrue(self.on_stop_was_called.is_set())
        self.log_handler.wait_for_message('debug', num_messages=3)
        with self.log_handler.lock:
            self.assertEqual(3, len(self.log_handler.messages['debug']))
            log_record = self.log_handler.messages['debug'][0]
        self.assertEqual(
            'BaseException() in %s. Stopping all actors.' % self.actor_ref,
            log_record.getMessage())

    def test_exception_in_on_start_is_logged(self):
        self.log_handler.reset()
        start_event = self.event_class()
        actor_ref = self.EarlyFailingActor.start(start_event)
        start_event.wait(5)
        self.log_handler.wait_for_message('error')
        with self.log_handler.lock:
            self.assertEqual(1, len(self.log_handler.messages['error']))
            log_record = self.log_handler.messages['error'][0]
        self.assertEqual(
            'Unhandled exception in %s:' % actor_ref,
            log_record.getMessage())

    def test_exception_in_on_stop_is_logged(self):
        self.log_handler.reset()
        stop_event = self.event_class()
        actor_ref = self.LateFailingActor.start(stop_event)
        stop_event.wait(5)
        self.log_handler.wait_for_message('error')
        with self.log_handler.lock:
            self.assertEqual(1, len(self.log_handler.messages['error']))
            log_record = self.log_handler.messages['error'][0]
        self.assertEqual(
            'Unhandled exception in %s:' % actor_ref,
            log_record.getMessage())

    def test_exception_in_on_failure_is_logged(self):
        self.log_handler.reset()
        failure_event = self.event_class()
        actor_ref = self.FailingOnFailureActor.start(failure_event)
        actor_ref.tell({'command': 'raise exception'})
        failure_event.wait(5)
        self.log_handler.wait_for_message('error', num_messages=2)
        with self.log_handler.lock:
            self.assertEqual(2, len(self.log_handler.messages['error']))
            log_record = self.log_handler.messages['error'][0]
        self.assertEqual(
            'Unhandled exception in %s:' % actor_ref,
            log_record.getMessage())


class AnActor(object):
    def __init__(self, on_stop_was_called, on_failure_was_called):
        super(AnActor, self).__init__()
        self.on_stop_was_called = on_stop_was_called
        self.on_failure_was_called = on_failure_was_called

    def on_stop(self):
        self.on_stop_was_called.set()

    def on_failure(self, exception_type, exception_value, traceback):
        self.on_failure_was_called.set()

    def on_receive(self, message):
        if message.get('command') == 'raise exception':
            return self.raise_exception()
        elif message.get('command') == 'raise base exception':
            raise BaseException()
        else:
            super(AnActor, self).on_receive(message)

    def raise_exception(self):
        raise Exception('foo')


def ConcreteActorLoggingTest(actor_class, event_class):
    class C(ActorLoggingTest, unittest.TestCase):
        class AnActor(AnActor, actor_class):
            pass

        class EarlyFailingActor(EarlyFailingActor, actor_class):
            pass

        class LateFailingActor(LateFailingActor, actor_class):
            pass

        class FailingOnFailureActor(FailingOnFailureActor, actor_class):
            pass

    C.event_class = event_class
    C.__name__ = '%sLoggingTest' % actor_class.__name__
    return C


ThreadingActorLoggingTest = ConcreteActorLoggingTest(
    ThreadingActor, threading.Event)


try:
    import gevent.event
    from pykka.gevent import GeventActor

    GeventActorLoggingTest = ConcreteActorLoggingTest(
        GeventActor, gevent.event.Event)
except ImportError:
    pass


try:
    from pykka.eventlet import EventletActor, EventletEvent

    EventletActorLoggingTest = ConcreteActorLoggingTest(
        EventletActor, EventletEvent)
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = method_call_test
import unittest

from pykka.actor import ThreadingActor


class ActorWithMethods(object):
    cat = 'dog'

    def functional_hello(self, s):
        return 'Hello, %s!' % s

    def set_cat(self, s):
        self.cat = s

    def raise_keyboard_interrupt(self):
        raise KeyboardInterrupt

    def talk_with_self(self):
        return self.actor_ref.proxy().functional_hello('from the future')


class ActorExtendableAtRuntime(object):
    def add_method(self, name):
        setattr(self, name, lambda: 'returned by ' + name)

    def use_foo_through_self_proxy(self):
        return self.actor_ref.proxy().foo()


class StaticMethodCallTest(object):
    def setUp(self):
        self.proxy = self.ActorWithMethods.start().proxy()

    def tearDown(self):
        self.proxy.stop()

    def test_functional_method_call_returns_correct_value(self):
        self.assertEqual(
            'Hello, world!',
            self.proxy.functional_hello('world').get())
        self.assertEqual(
            'Hello, moon!',
            self.proxy.functional_hello('moon').get())

    def test_side_effect_of_method_is_observable(self):
        self.assertEqual('dog', self.proxy.cat.get())
        self.proxy.set_cat('eagle')
        self.assertEqual('eagle', self.proxy.cat.get())

    def test_calling_unknown_method_raises_attribute_error(self):
        try:
            self.proxy.unknown_method()
            self.fail('Should raise AttributeError')
        except AttributeError as e:
            result = str(e)
            self.assert_(result.startswith('<ActorProxy for ActorWithMethods'))
            self.assert_(result.endswith('has no attribute "unknown_method"'))

    def test_can_proxy_itself_for_offloading_work_to_the_future(self):
        outer_future = self.proxy.talk_with_self()
        inner_future = outer_future.get(timeout=1)
        result = inner_future.get(timeout=1)
        self.assertEqual('Hello, from the future!', result)


class DynamicMethodCallTest(object):
    def setUp(self):
        self.proxy = self.ActorExtendableAtRuntime.start().proxy()

    def tearDown(self):
        self.proxy.stop()

    def test_can_call_method_that_was_added_at_runtime(self):
        # We need to .get() after .add_method() to be sure that the method has
        # been added before we try to use it through the proxy.
        self.proxy.add_method('foo').get()
        self.assertEqual('returned by foo', self.proxy.foo().get())

    def test_can_proxy_itself_and_use_attrs_added_at_runtime(self):
        # We don't need to .get() after .add_method() here, because the actor
        # will process the .add_method() call before processing the
        # .use_foo_through_self_proxy() call, which again will use the new
        # method, .foo().
        self.proxy.add_method('foo')
        outer_future = self.proxy.use_foo_through_self_proxy()
        inner_future = outer_future.get(timeout=1)
        result = inner_future.get(timeout=1)
        self.assertEqual('returned by foo', result)


class ThreadingStaticMethodCallTest(StaticMethodCallTest, unittest.TestCase):
    class ActorWithMethods(ActorWithMethods, ThreadingActor):
        pass


class ThreadingDynamicMethodCallTest(DynamicMethodCallTest, unittest.TestCase):
    class ActorExtendableAtRuntime(ActorExtendableAtRuntime, ThreadingActor):
        pass


try:
    from pygga.gevent import GeventActor

    class GeventStaticMethodCallTest(StaticMethodCallTest, unittest.TestCase):
        class ActorWithMethods(ActorWithMethods, GeventActor):
            pass

    class GeventDynamicMethodCallTest(
            DynamicMethodCallTest, unittest.TestCase):
        class ActorExtendableAtRuntime(ActorExtendableAtRuntime, GeventActor):
            pass
except ImportError:
    pass


try:
    from pygga.eventlet import EventletActor

    class EventletStaticMethodCallTest(
            StaticMethodCallTest, unittest.TestCase):
        class ActorWithMethods(ActorWithMethods, EventletActor):
            pass

    class EventletDynamicMethodCallTest(
            DynamicMethodCallTest, unittest.TestCase):
        class ActorExtendableAtRuntime(
                ActorExtendableAtRuntime, EventletActor):
            pass
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = namespace_test
import unittest


class NamespaceTest(unittest.TestCase):
    def test_actor_dead_error_import(self):
        from pykka import ActorDeadError as ActorDeadError1
        from pykka.exceptions import ActorDeadError as ActorDeadError2
        self.assertEqual(ActorDeadError1, ActorDeadError2)

    def test_timeout_import(self):
        from pykka import Timeout as Timeout1
        from pykka.exceptions import Timeout as Timeout2
        self.assertEqual(Timeout1, Timeout2)

    def test_actor_import(self):
        from pykka import Actor as Actor1
        from pykka.actor import Actor as Actor2
        self.assertEqual(Actor1, Actor2)

    def test_actor_ref_import(self):
        from pykka import ActorRef as ActorRef1
        from pykka.actor import ActorRef as ActorRef2
        self.assertEqual(ActorRef1, ActorRef2)

    def test_threading_actor_import(self):
        from pykka import ThreadingActor as ThreadingActor1
        from pykka.actor import ThreadingActor as ThreadingActor2
        self.assertEqual(ThreadingActor1, ThreadingActor2)

    def test_future_import(self):
        from pykka import Future as Future1
        from pykka.future import Future as Future2
        self.assertEqual(Future1, Future2)

    def test_get_all_import(self):
        from pykka import get_all as get_all1
        from pykka.future import get_all as get_all2
        self.assertEqual(get_all1, get_all2)

    def test_threading_future_import(self):
        from pykka import ThreadingFuture as ThreadingFuture1
        from pykka.future import ThreadingFuture as ThreadingFuture2
        self.assertEqual(ThreadingFuture1, ThreadingFuture2)

    def test_actor_proxy_import(self):
        from pykka import ActorProxy as ActorProxy1
        from pykka.proxy import ActorProxy as ActorProxy2
        self.assertEqual(ActorProxy1, ActorProxy2)

    def test_actor_registry_import(self):
        from pykka import ActorRegistry as ActorRegistry1
        from pykka.registry import ActorRegistry as ActorRegistry2
        self.assertEqual(ActorRegistry1, ActorRegistry2)

########NEW FILE########
__FILENAME__ = performance
import time

from pykka.actor import ThreadingActor
from pykka.registry import ActorRegistry


def time_it(func):
    start = time.time()
    func()
    print('%s took %.3fs' % (func.func_name, time.time() - start))


class SomeObject(object):
    pykka_traversable = False
    cat = 'bar.cat'

    def func(self):
        pass


class AnActor(ThreadingActor):
    bar = SomeObject()
    bar.pykka_traversable = True

    foo = 'foo'

    def __init__(self):
        super(AnActor, self).__init__()
        self.cat = 'quox'

    def func(self):
        pass


def test_direct_plain_attribute_access():
    actor = AnActor.start().proxy()
    for _ in range(10000):
        actor.foo.get()


def test_direct_callable_attribute_access():
    actor = AnActor.start().proxy()
    for _ in range(10000):
        actor.func().get()


def test_traversible_plain_attribute_access():
    actor = AnActor.start().proxy()
    for _ in range(10000):
        actor.bar.cat.get()


def test_traversible_callable_attribute_access():
    actor = AnActor.start().proxy()
    for _ in range(10000):
        actor.bar.func().get()


if __name__ == '__main__':
    try:
        time_it(test_direct_plain_attribute_access)
        time_it(test_direct_callable_attribute_access)
        time_it(test_traversible_plain_attribute_access)
        time_it(test_traversible_callable_attribute_access)
    finally:
        ActorRegistry.stop_all()

########NEW FILE########
__FILENAME__ = proxy_test
import unittest

from pykka import ActorDeadError
from pykka.actor import ThreadingActor
from pykka.proxy import ActorProxy


class SomeObject(object):
    cat = 'bar.cat'
    pykka_traversable = False


class AnActor(object):
    bar = SomeObject()
    bar.pykka_traversable = True

    foo = 'foo'

    def __init__(self):
        super(AnActor, self).__init__()
        self.cat = 'quox'

    def func(self):
        pass


class ProxyTest(object):
    def setUp(self):
        self.proxy = ActorProxy(self.AnActor.start())

    def tearDown(self):
        try:
            self.proxy.stop()
        except ActorDeadError:
            pass

    def test_repr_is_wrapped_in_lt_and_gt(self):
        result = repr(self.proxy)
        self.assert_(result.startswith('<'))
        self.assert_(result.endswith('>'))

    def test_repr_reveals_that_this_is_a_proxy(self):
        self.assert_('ActorProxy' in repr(self.proxy))

    def test_repr_contains_actor_class_name(self):
        self.assert_('AnActor' in repr(self.proxy))

    def test_repr_contains_actor_urn(self):
        self.assert_(self.proxy.actor_ref.actor_urn in repr(self.proxy))

    def test_repr_contains_attr_path(self):
        self.assert_('bar' in repr(self.proxy.bar))

    def test_str_contains_actor_class_name(self):
        self.assert_('AnActor' in str(self.proxy))

    def test_str_contains_actor_urn(self):
        self.assert_(self.proxy.actor_ref.actor_urn in str(self.proxy))

    def test_dir_on_proxy_lists_attributes_of_the_actor(self):
        result = dir(self.proxy)
        self.assert_('foo' in result)
        self.assert_('cat' in result)
        self.assert_('func' in result)

    def test_dir_on_proxy_lists_private_attributes_of_the_proxy(self):
        result = dir(self.proxy)
        self.assert_('__class__' in result)
        self.assert_('__dict__' in result)
        self.assert_('__getattr__' in result)
        self.assert_('__setattr__' in result)

    def test_refs_proxy_method_returns_a_proxy(self):
        proxy_from_ref_proxy = self.AnActor.start().proxy()
        self.assert_(isinstance(proxy_from_ref_proxy, ActorProxy))
        proxy_from_ref_proxy.stop().get()

    def test_proxy_constructor_raises_exception_if_actor_is_dead(self):
        actor_ref = self.AnActor.start()
        actor_ref.stop()
        try:
            ActorProxy(actor_ref)
            self.fail('Should raise ActorDeadError')
        except ActorDeadError as exception:
            self.assertEqual('%s not found' % actor_ref, str(exception))

    def test_actor_ref_may_be_retrieved_from_proxy_if_actor_is_dead(self):
        self.proxy.actor_ref.stop()
        self.assertFalse(self.proxy.actor_ref.is_alive())


def ConcreteProxyTest(actor_class):
    class C(ProxyTest, unittest.TestCase):
        class AnActor(AnActor, actor_class):
            pass
    C.__name__ = '%sProxyTest' % actor_class.__name__
    return C


ThreadingActorProxyTest = ConcreteProxyTest(ThreadingActor)


try:
    from pykka.gevent import GeventActor
    GeventActorProxyTest = ConcreteProxyTest(GeventActor)
except ImportError:
    pass


try:
    from pykka.eventlet import EventletActor
    EventletActorProxyTest = ConcreteProxyTest(EventletActor)
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = ref_test
import time
import unittest

from pykka import ActorDeadError, Timeout
from pykka.actor import ThreadingActor
from pykka.future import ThreadingFuture


class AnActor(object):
    def __init__(self, received_message):
        super(AnActor, self).__init__()
        self.received_message = received_message

    def on_receive(self, message):
        if message.get('command') == 'ping':
            self.sleep(0.01)
            return 'pong'
        else:
            self.received_message.set(message)


class RefTest(object):
    def setUp(self):
        self.received_message = self.future_class()
        self.ref = self.AnActor.start(self.received_message)

    def tearDown(self):
        self.ref.stop()

    def test_repr_is_wrapped_in_lt_and_gt(self):
        result = repr(self.ref)
        self.assert_(result.startswith('<'))
        self.assert_(result.endswith('>'))

    def test_repr_reveals_that_this_is_a_ref(self):
        self.assert_('ActorRef' in repr(self.ref))

    def test_repr_contains_actor_class_name(self):
        self.assert_('AnActor' in repr(self.ref))

    def test_repr_contains_actor_urn(self):
        self.assert_(self.ref.actor_urn in repr(self.ref))

    def test_str_contains_actor_class_name(self):
        self.assert_('AnActor' in str(self.ref))

    def test_str_contains_actor_urn(self):
        self.assert_(self.ref.actor_urn in str(self.ref))

    def test_is_alive_returns_true_for_running_actor(self):
        self.assertTrue(self.ref.is_alive())

    def test_is_alive_returns_false_for_dead_actor(self):
        self.ref.stop()
        self.assertFalse(self.ref.is_alive())

    def test_stop_returns_true_if_actor_is_stopped(self):
        self.assertTrue(self.ref.stop())

    def test_stop_does_not_stop_already_dead_actor(self):
        self.ref.stop()
        try:
            self.assertFalse(self.ref.stop())
        except ActorDeadError:
            self.fail('Should never raise ActorDeadError')

    def test_tell_delivers_message_to_actors_custom_on_receive(self):
        self.ref.tell({'command': 'a custom message'})
        self.assertEqual(
            {'command': 'a custom message'}, self.received_message.get())

    def test_tell_fails_if_actor_is_stopped(self):
        self.ref.stop()
        try:
            self.ref.tell({'command': 'a custom message'})
            self.fail('Should raise ActorDeadError')
        except ActorDeadError as exception:
            self.assertEqual('%s not found' % self.ref, str(exception))

    def test_ask_blocks_until_response_arrives(self):
        result = self.ref.ask({'command': 'ping'})
        self.assertEqual('pong', result)

    def test_ask_can_timeout_if_blocked_too_long(self):
        try:
            self.ref.ask({'command': 'ping'}, timeout=0)
            self.fail('Should raise Timeout exception')
        except Timeout:
            pass

    def test_ask_can_return_future_instead_of_blocking(self):
        future = self.ref.ask({'command': 'ping'}, block=False)
        self.assertEqual('pong', future.get())

    def test_ask_fails_if_actor_is_stopped(self):
        self.ref.stop()
        try:
            self.ref.ask({'command': 'ping'})
            self.fail('Should raise ActorDeadError')
        except ActorDeadError as exception:
            self.assertEqual('%s not found' % self.ref, str(exception))

    def test_ask_nonblocking_fails_future_if_actor_is_stopped(self):
        self.ref.stop()
        future = self.ref.ask({'command': 'ping'}, block=False)
        try:
            future.get()
            self.fail('Should raise ActorDeadError')
        except ActorDeadError as exception:
            self.assertEqual('%s not found' % self.ref, str(exception))


def ConcreteRefTest(actor_class, future_class, sleep_function):
    class C(RefTest, unittest.TestCase):
        class AnActor(AnActor, actor_class):
            def sleep(self, seconds):
                sleep_function(seconds)

    C.__name__ = '%sRefTest' % (actor_class.__name__,)
    C.future_class = future_class
    return C

ThreadingActorRefTest = ConcreteRefTest(
    ThreadingActor, ThreadingFuture, time.sleep)

try:
    import gevent
    from pykka.gevent import GeventActor, GeventFuture

    GeventActorRefTest = ConcreteRefTest(
        GeventActor, GeventFuture, gevent.sleep)
except ImportError:
    pass

try:
    import eventlet
    from pykka.eventlet import EventletActor, EventletFuture

    EventletActorRefTest = ConcreteRefTest(
        EventletActor, EventletFuture, eventlet.sleep)
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = registry_test
import mock
import unittest

from pykka.actor import ThreadingActor
from pykka.registry import ActorRegistry


class ActorRegistryTest(object):
    def setUp(self):
        self.ref = self.AnActor.start()
        self.a_actors = [self.AnActor.start() for _ in range(3)]
        self.b_actors = [self.BeeActor.start() for _ in range(5)]
        self.a_actor_0_urn = self.a_actors[0].actor_urn

    def tearDown(self):
        ActorRegistry.stop_all()

    def test_actor_is_registered_when_started(self):
        self.assert_(self.ref in ActorRegistry.get_all())

    def test_actor_is_unregistered_when_stopped(self):
        self.assert_(self.ref in ActorRegistry.get_all())
        self.ref.stop()
        self.assert_(self.ref not in ActorRegistry.get_all())

    def test_actor_may_be_registered_manually(self):
        ActorRegistry.unregister(self.ref)
        self.assert_(self.ref not in ActorRegistry.get_all())
        ActorRegistry.register(self.ref)
        self.assert_(self.ref in ActorRegistry.get_all())

    def test_actor_may_be_unregistered_multiple_times_without_error(self):
        ActorRegistry.unregister(self.ref)
        self.assert_(self.ref not in ActorRegistry.get_all())
        ActorRegistry.unregister(self.ref)
        self.assert_(self.ref not in ActorRegistry.get_all())
        ActorRegistry.register(self.ref)
        self.assert_(self.ref in ActorRegistry.get_all())

    def test_all_actors_can_be_stopped_through_registry(self):
        self.assertEquals(9, len(ActorRegistry.get_all()))
        ActorRegistry.stop_all(block=True)
        self.assertEquals(0, len(ActorRegistry.get_all()))

    @mock.patch.object(ActorRegistry, 'get_all')
    def test_stop_all_stops_last_started_actor_first_if_blocking(
            self, mock_method):
        stopped_actors = []
        started_actors = [mock.Mock(name=i) for i in range(3)]
        started_actors[0].stop.side_effect = lambda *a, **kw: \
            stopped_actors.append(started_actors[0])
        started_actors[1].stop.side_effect = lambda *a, **kw: \
            stopped_actors.append(started_actors[1])
        started_actors[2].stop.side_effect = lambda *a, **kw: \
            stopped_actors.append(started_actors[2])
        ActorRegistry.get_all.return_value = started_actors

        ActorRegistry.stop_all(block=True)

        self.assertEqual(stopped_actors[0], started_actors[2])
        self.assertEqual(stopped_actors[1], started_actors[1])
        self.assertEqual(stopped_actors[2], started_actors[0])

    def test_actors_may_be_looked_up_by_class(self):
        result = ActorRegistry.get_by_class(self.AnActor)
        for a_actor in self.a_actors:
            self.assert_(a_actor in result)
        for b_actor in self.b_actors:
            self.assert_(b_actor not in result)

    def test_actors_may_be_looked_up_by_superclass(self):
        result = ActorRegistry.get_by_class(AnActor)
        for a_actor in self.a_actors:
            self.assert_(a_actor in result)
        for b_actor in self.b_actors:
            self.assert_(b_actor not in result)

    def test_actors_may_be_looked_up_by_class_name(self):
        result = ActorRegistry.get_by_class_name('AnActor')
        for a_actor in self.a_actors:
            self.assert_(a_actor in result)
        for b_actor in self.b_actors:
            self.assert_(b_actor not in result)

    def test_actors_may_be_looked_up_by_urn(self):
        result = ActorRegistry.get_by_urn(self.a_actor_0_urn)
        self.assertEqual(self.a_actors[0], result)

    def test_get_by_urn_returns_none_if_not_found(self):
        result = ActorRegistry.get_by_urn('urn:foo:bar')
        self.assertEqual(None, result)

    def test_broadcast_sends_message_to_all_actors_if_no_target(self):
        ActorRegistry.broadcast({'command': 'foo'})
        for actor_ref in ActorRegistry.get_all():
            received_messages = actor_ref.proxy().received_messages.get()
            self.assert_({'command': 'foo'} in received_messages)

    def test_broadcast_sends_message_to_all_actors_of_given_class(self):
        ActorRegistry.broadcast({'command': 'foo'}, target_class=self.AnActor)
        for actor_ref in ActorRegistry.get_by_class(self.AnActor):
            received_messages = actor_ref.proxy().received_messages.get()
            self.assert_({'command': 'foo'} in received_messages)
        for actor_ref in ActorRegistry.get_by_class(self.BeeActor):
            received_messages = actor_ref.proxy().received_messages.get()
            self.assert_({'command': 'foo'} not in received_messages)

    def test_broadcast_sends_message_to_all_actors_of_given_class_name(self):
        ActorRegistry.broadcast({'command': 'foo'}, target_class='AnActor')
        for actor_ref in ActorRegistry.get_by_class(self.AnActor):
            received_messages = actor_ref.proxy().received_messages.get()
            self.assert_({'command': 'foo'} in received_messages)
        for actor_ref in ActorRegistry.get_by_class(self.BeeActor):
            received_messages = actor_ref.proxy().received_messages.get()
            self.assert_({'command': 'foo'} not in received_messages)


class AnActor(object):
    received_messages = None

    def __init__(self):
        super(AnActor, self).__init__()
        self.received_messages = []

    def on_receive(self, message):
        self.received_messages.append(message)


class BeeActor(object):
    received_messages = None

    def __init__(self):
        super(BeeActor, self).__init__()
        self.received_messages = []

    def on_receive(self, message):
        self.received_messages.append(message)


def ConcreteRegistryTest(actor_class):
    class C(ActorRegistryTest, unittest.TestCase):
        class AnActor(AnActor, actor_class):
            pass

        class BeeActor(BeeActor, actor_class):
            pass

    C.__name__ = '%sRegistryTest' % (actor_class.__name__,)
    return C

ThreadingActorRegistryTest = ConcreteRegistryTest(ThreadingActor)


try:
    from pykka.gevent import GeventActor

    GeventActorRegistryTest = ConcreteRegistryTest(GeventActor)
except ImportError:
    pass

try:
    from pykka.eventlet import EventletActor

    EventletActorRegistryTest = ConcreteRegistryTest(EventletActor)
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = __main__
import nose
import yappi

try:
    yappi.start()
    nose.main()
finally:
    yappi.print_stats()

########NEW FILE########
