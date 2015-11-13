__FILENAME__ = poll
import gevent
from gevent_zeromq import zmq

# Connect to both receiving sockets and send 10 messages
def sender():

	sender = context.socket(zmq.PUSH)
	sender.connect('inproc://polltest1')
	sender.connect('inproc://polltest2')

	for i in xrange(10):
		sender.send('test %d' % i)
		gevent.sleep(1)


# create zmq context, and bind to pull sockets
context = zmq.Context()
receiver1 = context.socket(zmq.PULL)
receiver1.bind('inproc://polltest1')
receiver2 = context.socket(zmq.PULL)
receiver2.bind('inproc://polltest2')

gevent.spawn(sender)

# Create poller and register both reciever sockets
poller = zmq.Poller()
poller.register(receiver1, zmq.POLLIN)
poller.register(receiver2, zmq.POLLIN)

# Read 10 messages from both reciever sockets
msgcnt = 0
while msgcnt < 10:
	socks = dict(poller.poll())
	if receiver1 in socks and socks[receiver1] == zmq.POLLIN:
		print "Message from receiver1: %s" % receiver1.recv()
		msgcnt += 1

	if receiver2 in socks and socks[receiver2] == zmq.POLLIN:
		print "Message from receiver2: %s" % receiver2.recv()
		msgcnt += 1

print "%d messages received" % msgcnt



########NEW FILE########
__FILENAME__ = reqrep
"""
Complex example which is a combination of the rr* examples from the zguide.
"""
from gevent import spawn
from gevent_zeromq import zmq

# server
context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://localhost:5560")

def serve(socket):
    while True:
        message = socket.recv()
        print "Received request: ", message
        socket.send("World")
server = spawn(serve, socket)


# client
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5559")

#  Do 10 requests, waiting each time for a response
def client():
    for request in range(1,10):
        socket.send("Hello")
        message = socket.recv()
        print "Received reply ", request, "[", message, "]"


# broker
frontend = context.socket(zmq.XREP)
backend  = context.socket(zmq.XREQ);
frontend.bind("tcp://*:5559")
backend.bind("tcp://*:5560")

def proxy(socket_from, socket_to):
    while True:
        m = socket_from.recv_multipart()
        socket_to.send_multipart(m)

a = spawn(proxy, frontend, backend)
b = spawn(proxy, backend, frontend)

spawn(client).join()

########NEW FILE########
__FILENAME__ = simple
from gevent import spawn, spawn_later
from gevent_zeromq import zmq

# server
ctx = zmq.Context()
sock = ctx.socket(zmq.PUSH)
sock.bind('ipc:///tmp/zmqtest')

spawn(sock.send_pyobj, ('this', 'is', 'a', 'python', 'tuple'))
spawn_later(1, sock.send_pyobj, {'hi': 1234})
spawn_later(2, sock.send_pyobj, ({'this': ['is a more complicated object', ':)']}, 42, 42, 42))
spawn_later(3, sock.send_pyobj, 'foobar')
spawn_later(4, sock.send_pyobj, 'quit')


# client
ctx = zmq.Context() # create a new context to kick the wheels
sock = ctx.socket(zmq.PULL)
sock.connect('ipc:///tmp/zmqtest')

def get_objs(sock):
    while True:
        o = sock.recv_pyobj()
        print 'received python object:', o
        if o == 'quit':
            print 'exiting.'
            break

def print_every(s, t=None):
    print s
    if t:
        spawn_later(t, print_every, s, t)

print_every('printing every half second', 0.5)
spawn(get_objs, sock).join()


########NEW FILE########
__FILENAME__ = core
"""This module wraps the :class:`Socket` and :class:`Context` found in :mod:`pyzmq <zmq>` to be non blocking
"""
import zmq
from zmq import *
from zmq import devices
__all__ = zmq.__all__

import gevent
from gevent import select
from gevent.event import AsyncResult
from gevent.hub import get_hub


class GreenSocket(Socket):
    """Green version of :class:`zmq.core.socket.Socket`

    The following methods are overridden:

        * send
        * send_multipart
        * recv
        * recv_multipart

    To ensure that the ``zmq.NOBLOCK`` flag is set and that sending or recieving
    is deferred to the hub if a ``zmq.EAGAIN`` (retry) error is raised.
    
    The `__state_changed` method is triggered when the zmq.FD for the socket is
    marked as readable and triggers the necessary read and write events (which
    are waited for in the recv and send methods).

    Some double underscore prefixes are used to minimize pollution of
    :class:`zmq.core.socket.Socket`'s namespace.
    """

    def __init__(self, context, socket_type):
        self.__in_send_multipart = False
        self.__in_recv_multipart = False
        self.__setup_events()

    def __del__(self):
        self.close()

    def close(self, linger=None):
        super(GreenSocket, self).close(linger)
        self.__cleanup_events()

    def __cleanup_events(self):
        # close the _state_event event, keeps the number of active file descriptors down
        if getattr(self, '_state_event', None):
            try:
                self._state_event.stop()
            except AttributeError, e:
                # gevent<1.0 compat
                self._state_event.cancel()

        # if the socket has entered a close state resume any waiting greenlets
        if hasattr(self, '__writable'):
            self.__writable.set()
            self.__readable.set()

    def __setup_events(self):
        self.__readable = AsyncResult()
        self.__writable = AsyncResult()
        try:
            self._state_event = get_hub().loop.io(self.getsockopt(FD), 1) # read state watcher
            self._state_event.start(self.__state_changed)
        except AttributeError:
            # for gevent<1.0 compatibility
            from gevent.core import read_event
            self._state_event = read_event(self.getsockopt(FD), self.__state_changed, persist=True)

    def __state_changed(self, event=None, _evtype=None):
        if self.closed:
            self.__cleanup_events()
            return
        try:
            events = super(GreenSocket, self).getsockopt(zmq.EVENTS)
        except ZMQError, exc:
            self.__writable.set_exception(exc)
            self.__readable.set_exception(exc)
        else:
            if events & zmq.POLLOUT:
                self.__writable.set()
            if events & zmq.POLLIN:
                self.__readable.set()

    def _wait_write(self):
        self.__writable = AsyncResult()
        try:
            self.__writable.get(timeout=1)
        except gevent.Timeout:
            self.__writable.set()

    def _wait_read(self):
        self.__readable = AsyncResult()
        try:
            self.__readable.get(timeout=1)
        except gevent.Timeout:
            self.__readable.set()

    def send(self, data, flags=0, copy=True, track=False):
        # if we're given the NOBLOCK flag act as normal and let the EAGAIN get raised
        if flags & zmq.NOBLOCK:
            try:
                msg = super(GreenSocket, self).send(data, flags, copy, track)
            finally:
                if not self.__in_send_multipart:
                    self.__state_changed()
            return msg

        # ensure the zmq.NOBLOCK flag is part of flags
        flags |= zmq.NOBLOCK
        while True: # Attempt to complete this operation indefinitely, blocking the current greenlet
            try:
                # attempt the actual call
                return super(GreenSocket, self).send(data, flags, copy, track)
            except zmq.ZMQError, e:
                # if the raised ZMQError is not EAGAIN, reraise
                if e.errno != zmq.EAGAIN:
                    raise
            # defer to the event loop until we're notified the socket is writable
            self._wait_write()

    def recv(self, flags=0, copy=True, track=False):
        if flags & zmq.NOBLOCK:
            try:
                msg = super(GreenSocket, self).recv(flags, copy, track)
            finally:
                if not self.__in_recv_multipart:
                    self.__state_changed()
            return msg

        flags |= zmq.NOBLOCK
        while True:
            try:
                return super(GreenSocket, self).recv(flags, copy, track)
            except zmq.ZMQError, e:
                if e.errno != zmq.EAGAIN:
                    if not self.__in_recv_multipart:
                        self.__state_changed()
                    raise
            else:
                if not self.__in_recv_multipart:
                    self.__state_changed()
                return msg
            self._wait_read()

    def send_multipart(self, *args, **kwargs):
        """wrap send_multipart to prevent state_changed on each partial send"""
        self.__in_send_multipart = True
        try:
            msg = super(GreenSocket, self).send_multipart(*args, **kwargs)
        finally:
            self.__in_send_multipart = False
            self.__state_changed()
        return msg

    def recv_multipart(self, *args, **kwargs):
        """wrap recv_multipart to prevent state_changed on each partial recv"""
        self.__in_recv_multipart = True
        try:
            msg = super(GreenSocket, self).recv_multipart(*args, **kwargs)
        finally:
            self.__in_recv_multipart = False
            self.__state_changed()
        return msg


class GreenContext(Context):
    """Replacement for :class:`zmq.core.context.Context`

    Ensures that the greened Socket above is used in calls to `socket`.
    """
    _socket_class = GreenSocket


########NEW FILE########
__FILENAME__ = poll
import zmq
from zmq import Poller
import gevent
from gevent import select


class GreenPoller(Poller):
    """Replacement for :class:`zmq.core.Poller`

    Ensures that the greened Poller below is used in calls to
    :meth:`zmq.core.Poller.poll`.
    """

    def _get_descriptors(self):
        """Returns three elements tuple with socket descriptors ready
        for gevent.select.select
        """
        rlist = []
        wlist = []
        xlist = []

        for socket, flags in self.sockets.items():
            if isinstance(socket, zmq.Socket):
                rlist.append(socket.getsockopt(zmq.FD))
                continue
            elif isinstance(socket, int):
                fd = socket
            elif hasattr(socket, 'fileno'):
                try:
                    fd = int(socket.fileno())
                except:
                    raise ValueError('fileno() must return an valid integer fd')
            else:
                raise TypeError('Socket must be a 0MQ socket, an integer fd '
                                'or have a fileno() method: %r' % socket)

            if flags & zmq.POLLIN:
                rlist.append(fd)
            if flags & zmq.POLLOUT:
                wlist.append(fd)
            if flags & zmq.POLLERR:
                xlist.append(fd)

        return (rlist, wlist, xlist)

    def poll(self, timeout=-1):
        """Overridden method to ensure that the green version of
        Poller is used.

        Behaves the same as :meth:`zmq.core.Poller.poll`
        """

        if timeout is None:
            timeout = -1

        if timeout < 0:
            timeout = -1

        rlist = None
        wlist = None
        xlist = None

        if timeout > 0:
            tout = gevent.Timeout.start_new(timeout/1000.0)

        try:
            # Loop until timeout or events available
            rlist, wlist, xlist = self._get_descriptors()
            while True:
                events = super(GreenPoller, self).poll(0)
                if events or timeout == 0:
                    return events

                # wait for activity on sockets in a green way
                select.select(rlist, wlist, xlist)

        except gevent.Timeout, t:
            if t is not tout:
                raise
            return []
        finally:
           if timeout > 0:
               tout.cancel()

########NEW FILE########
__FILENAME__ = tests
import gevent
from gevent_zeromq import zmq

try:
    from gevent_utils import BlockingDetector
    gevent.spawn(BlockingDetector(25))
except ImportError:
    print 'If you encounter hangs consider installing gevent_utils'


########NEW FILE########
