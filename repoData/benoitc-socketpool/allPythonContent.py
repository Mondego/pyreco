__FILENAME__ = test_eventlet
# -*- coding: utf-8 -
#
# This file is part of socketpool.
# See the NOTICE for more information.

import eventlet

from socketpool.pool import ConnectionPool
from socketpool.conn import TcpConnector


# this handler will be run for each incoming connection in a dedicated greenlet

class EchoServer(object):

    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.spool = eventlet.GreenPool()
        self.running = False
        self.server = None

    def start(self):
        eventlet.spawn(self.run)

    def run(self):
        self.server = eventlet.listen((self.host, self.port))
        self.running = True
        while self.running:
            try:
                sock, address = self.server.accept()
                print "accepted", address
                self.spool.spawn_n(self.handle, sock, address)
            except (SystemExit, KeyboardInterrupt):
                break


    def handle(self, sock, address):
        print ('New connection from %s:%s' % address)

        while True:
            data = sock.recv(1024)
            if not data:
                break
            sock.send(data)
            print ("echoed %r" % data)


    def stop(self):
        self.running = False


if __name__ == '__main__':
    import time

    options = {'host': 'localhost', 'port': 6000}
    pool = ConnectionPool(factory=TcpConnector, options=options,
            backend="eventlet")
    server = EchoServer('localhost', 6000)
    server.start()

    epool = eventlet.GreenPool()
    def runpool(data):
        print 'ok'
        with pool.connection() as conn:
            print 'sending'
            sent = conn.send(data)
            print 'send %d bytes' % sent
            echo_data = conn.recv(1024)
            print "got %s" % data
            assert data == echo_data

    start = time.time()
    _ = [epool.spawn(runpool, "blahblah") for _ in xrange(20)]

    epool.waitall()
    server.stop()
    delay = time.time() - start

########NEW FILE########
__FILENAME__ = test_gevent
# -*- coding: utf-8 -
#
# This file is part of socketpool.
# See the NOTICE for more information.

import gevent
from gevent.server import StreamServer

from socketpool.pool import ConnectionPool
from socketpool.conn import TcpConnector

# this handler will be run for each incoming connection in a dedicated greenlet
def echo(sock, address):
    print ('New connection from %s:%s' % address)

    while True:
        data = sock.recv(1024)
        if not data:
            break
        sock.send(data)
        print ("echoed %r" % data)



if __name__ == '__main__':
    import time

    options = {'host': 'localhost', 'port': 6000}
    pool = ConnectionPool(factory=TcpConnector, backend="gevent")
    server = StreamServer(('localhost', 6000), echo)
    gevent.spawn(server.serve_forever)


    def runpool(data):
        with pool.connection(**options) as conn:
            print ("conn: pool size: %s" % pool.size)

            sent = conn.send(data)
            echo_data = conn.recv(1024)
            assert data == echo_data

    start = time.time()
    jobs = [gevent.spawn(runpool, "blahblah") for _ in xrange(50)]

    gevent.joinall(jobs)
    delay = time.time() - start

    print ("final pool size: %s" % pool.size)

    with pool.connection(**options) as conn:
        print ("conn: pool size: %s" % pool.size)

        sent = conn.send("hello")
        echo_data = conn.recv(1024)
        assert "hello" == echo_data

    print ("final pool size: %s" % pool.size)

########NEW FILE########
__FILENAME__ = test_threaded
# -*- coding: utf-8 -
#
# This file is part of socketpool.
# See the NOTICE for more information.

import socket
import sys
import threading

try:
    from queue import *
except ImportError:
    from Queue import *

try:
    import SocketServer as socketserver
except ImportError:
    import socketserver

import time

from socketpool.pool import ConnectionPool
from socketpool.conn import TcpConnector

PY3 = sys.version_info[0] == 3

if sys.version_info[0] == 3:
    def s2b(s):
        return s.encode('latin1')
else:
    def s2b(s):
        return s

class EchoHandler(socketserver.BaseRequestHandler):

    def handle(self):
        while True:
            data = self.request.recv(1024)
            if not data:
                break
            self.request.send(data)
            print("echoed %r" % data)

class EchoServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


if __name__ == "__main__":
    # Port 0 means to select an arbitrary unused port
    HOST, PORT = "localhost", 0

    server = EchoServer((HOST, PORT), EchoHandler)
    ip, port = server.server_address

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever,
            kwargs={"poll_interval":0.5})
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()

    options = {'host': ip, 'port': port}
    pool = ConnectionPool(factory=TcpConnector, options=options)
    q = Queue()

    def runpool():
        while True:
            try:
                data = q.get(False)
            except Empty:
                break
            try:
                with pool.connection() as conn:
                    print("conn: pool size: %s" % pool.size)
                    sent = conn.send(data)
                    echo = conn.recv(1024)
                    print("got %s" % data)
                    assert data == echo
            finally:
                q.task_done()


    for i in range(20):
        q.put(s2b("Hello World %s" % i), False)

    for i in range(4):
        th = threading.Thread(target=runpool)
        th.daemnon = True
        th.start()

    q.join()

    print ("final pool size: %s" % pool.size)

    pool.release_all()
    server.shutdown()

########NEW FILE########
__FILENAME__ = backend_eventlet
# -*- coding: utf-8 -
#
# This file is part of socketpool.
# See the NOTICE for more information.

import eventlet
from eventlet.green import select
from eventlet.green import socket
from eventlet import queue

from socketpool.pool import ConnectionPool

sleep = eventlet.sleep
Socket = socket.socket
Select = select.select
Semaphore = eventlet.semaphore.BoundedSemaphore

class PriorityQueue(queue.PriorityQueue):

    def __iter__(self):
        return self

    def __next__(self):
        try:
            result = self.get(block=False)
        except queue.Empty:
            raise StopIteration
        return result
    next = __next__

class ConnectionReaper(object):

    running = False

    def __init__(self, pool, delay=150):
        self.pool = pool
        self.delay = delay

    def start(self):
        self.running = True
        g = eventlet.spawn(self._exec)
        g.link(self._exit)

    def _exit(self, g):
        try:
            g.wait()
        except:
            pass
        self.running = False

    def _exec(self):
        while True:
            eventlet.sleep(self.delay)
            self.pool.murder_connections()

    def ensure_started(self):
        if not self.running:
            self.start()

########NEW FILE########
__FILENAME__ = backend_gevent
# -*- coding: utf-8 -
#
# This file is part of socketpool.
# See the NOTICE for more information.

import gevent
from gevent import select
from gevent import socket
from gevent import queue

try:
    from gevent import lock
except ImportError:
    #gevent < 1.0b2
    from gevent import coros as lock


sleep = gevent.sleep
Semaphore = lock.BoundedSemaphore
Socket = socket.socket
Select = select.select

class PriorityQueue(queue.PriorityQueue):

    def __next__(self):
        try:
            result = self.get(block=False)
        except queue.Empty:
            raise StopIteration
        return result
    next = __next__

class ConnectionReaper(gevent.Greenlet):

    running = False

    def __init__(self, pool, delay=150):
        self.pool = pool
        self.delay = delay
        gevent.Greenlet.__init__(self)

    def _run(self):
        self.running = True
        while True:
            gevent.sleep(self.delay)
            self.pool.murder_connections()

    def ensure_started(self):
        if not self.running or self.ready():
            self.start()

########NEW FILE########
__FILENAME__ = backend_thread
# -*- coding: utf-8 -
#
# This file is part of socketpool.
# See the NOTICE for more information.

import select
import socket
import threading
import time
import weakref

try:
    import Queue as queue
except ImportError: # py3
    import queue

Select = select.select
Socket = socket.socket
sleep = time.sleep
Semaphore = threading.BoundedSemaphore


class PriorityQueue(queue.PriorityQueue):

    def __iter__(self):
        return self

    def __next__(self):
        try:
            result = self.get(block=False)
        except queue.Empty:
            raise StopIteration
        return result
    next = __next__

class ConnectionReaper(threading.Thread):
    """ connection reaper thread. Open a thread that will murder iddle
    connections after a delay """

    running = False
    forceStop = False

    def __init__(self, pool, delay=600):
        self.pool = weakref.ref(pool)
        self.delay = delay
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        self.running = True
        while True:
            time.sleep(self.delay)
            pool = self.pool()
            if pool is not None:
                pool.murder_connections()

            if self.forceStop:
                self.running = False
                break

    def ensure_started(self):
        if not self.running and not self.isAlive():
            self.start()

########NEW FILE########
__FILENAME__ = conn
# -*- coding: utf-8 -
#
# This file is part of socketpool.
# See the NOTICE for more information.

import select
import socket
import time
import random

from socketpool import util

class Connector(object):
    def matches(self, **match_options):
        raise NotImplementedError()

    def is_connected(self):
        raise NotImplementedError()

    def handle_exception(self, exception):
        raise NotImplementedError()

    def get_lifetime(self):
        raise NotImplementedError()

    def invalidate(self):
        raise NotImplementedError()


class TcpConnector(Connector):

    def __init__(self, host, port, backend_mod, pool=None):
        self._s = backend_mod.Socket(socket.AF_INET, socket.SOCK_STREAM)
        self._s.connect((host, port))
        self.host = host
        self.port = port
        self.backend_mod = backend_mod
        self._connected = True
        # use a 'jiggle' value to make sure there is some
        # randomization to expiry, to avoid many conns expiring very
        # closely together.
        self._life = time.time() - random.randint(0, 10)
        self._pool = pool

    def __del__(self):
        self.release()

    def matches(self, **match_options):
        target_host = match_options.get('host')
        target_port = match_options.get('port')
        return target_host == self.host and target_port == self.port

    def is_connected(self):
        if self._connected:
            return util.is_connected(self._s)
        return False

    def handle_exception(self, exception):
        print('got an exception')
        print(str(exception))

    def get_lifetime(self):
        return self._life

    def invalidate(self):
        self._s.close()
        self._connected = False
        self._life = -1

    def release(self):
        if self._pool is not None:
            if self._connected:
                self._pool.release_connection(self)
            else:
                self._pool = None

    def send(self, data):
        return self._s.send(data)

    def recv(self, size=1024):
        return self._s.recv(size)

########NEW FILE########
__FILENAME__ = pool
# -*- coding: utf-8 -
#
# This file is part of socketpool.
# See the NOTICE for more information.

import contextlib
import time

from socketpool.util import load_backend

class MaxTriesError(Exception):
    pass

class MaxConnectionsError(Exception):
    pass

class ConnectionPool(object):
    """Pool of connections

    This is the main object to maintain connection. Connections are
    created using the factory instance passed as an option.

    Options:
    --------

    :attr factory: Instance of socketpool.Connector. See
        socketpool.conn.TcpConnector for an example
    :attr retry_max: int, default 3. Numbr of times to retry a
        connection before raising the MaxTriesError exception.
    :attr max_lifetime: int, default 600. time in ms we keep a
        connection in the pool
    :attr max_size: int, default 10. Maximum number of connections we
        keep in the pool.
    :attr options: Options to pass to the factory
    :attr reap_connection: boolean, default is true. If true a process
        will be launched in background to kill idle connections.
    :attr backend: string, default is thread. The socket pool can use
        different backend to handle process and connections. For now
        the backends "thread", "gevent" and "eventlet" are supported. But
        you can add your own backend if you want. For an example of backend,
        look at the module socketpool.gevent_backend.
    """

    def __init__(self, factory,
                 retry_max=3, retry_delay=.1,
                 timeout=-1, max_lifetime=600.,
                 max_size=10, options=None,
                 reap_connections=True, reap_delay=1,
                 backend="thread"):

        if isinstance(backend, str):
            self.backend_mod = load_backend(backend)
            self.backend = backend
        else:
            self.backend_mod = backend
            self.backend = str(getattr(backend, '__name__', backend))
        self.max_size = max_size
        self.pool = getattr(self.backend_mod, 'PriorityQueue')()
        self._free_conns = 0
        self.factory = factory
        self.retry_max = retry_max
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.max_lifetime = max_lifetime
        if options is None:
            self.options = {"backend_mod": self.backend_mod}
        else:
            self.options = options
            self.options["backend_mod"] = self.backend_mod

        # bounded semaphore to make self._alive 'safe'
        self._sem = self.backend_mod.Semaphore(1)

        self._reaper = None
        if reap_connections:
            self.reap_delay = reap_delay
            self.start_reaper()

    def __del__(self):
        self.stop_reaper()

    def too_old(self, conn):
        return time.time() - conn.get_lifetime() > self.max_lifetime

    def murder_connections(self):
        current_pool_size = self.pool.qsize()
        if current_pool_size > 0:
            for priority, candidate in self.pool:
                current_pool_size -= 1
                if not self.too_old(candidate):
                    self.pool.put((priority, candidate))
                else:
                    self._reap_connection(candidate)
                if current_pool_size <= 0:
                    break

    def start_reaper(self):
        self._reaper = self.backend_mod.ConnectionReaper(self,
                delay=self.reap_delay)
        self._reaper.ensure_started()

    def stop_reaper(self):
        self._reaper.forceStop = True

    def _reap_connection(self, conn):
        if conn.is_connected():
            conn.invalidate()

    @property
    def size(self):
        return self.pool.qsize()

    def release_all(self):
        if self.pool.qsize():
            for priority, conn in self.pool:
                self._reap_connection(conn)

    def release_connection(self, conn):
        if self._reaper is not None:
            self._reaper.ensure_started()

        with self._sem:
            if self.pool.qsize() < self.max_size:
                connected = conn.is_connected()
                if connected and not self.too_old(conn):
                    self.pool.put((conn.get_lifetime(), conn))
                else:
                    self._reap_connection(conn)
            else:
                self._reap_connection(conn)

    def get(self, **options):
        options.update(self.options)
        # Do not set this in self.options so we don't keep a persistent
        # reference on the pool which would prevent garbage collection.
        options["pool"] = self

        found = None
        i = self.pool.qsize()
        tries = 0
        last_error = None

        unmatched = []

        while tries < self.retry_max:
            # first let's try to find a matching one from pool

            if self.pool.qsize():
                for priority, candidate in self.pool:
                    i -= 1
                    if self.too_old(candidate):
                        # let's drop it
                        self._reap_connection(candidate)
                        continue

                    matches = candidate.matches(**options)
                    if not matches:
                        # let's put it back
                        unmatched.append((priority, candidate))
                    else:
                        if candidate.is_connected():
                            found = candidate
                            break
                        else:
                            # conn is dead for some reason.
                            # reap it.
                            self._reap_connection(candidate)

                    if i <= 0:
                        break

            if unmatched:
                for candidate in unmatched:
                    self.pool.put(candidate)

            # we got one.. we use it
            if found is not None:
                return found

            try:
                new_item = self.factory(**options)
            except Exception as e:
                last_error = e
            else:
                # we should be connected now
                if new_item.is_connected():
                    with self._sem:
                        return new_item

            tries += 1
            self.backend_mod.sleep(self.retry_delay)

        if last_error is None:
            raise MaxTriesError()
        else:
            raise last_error

    @contextlib.contextmanager
    def connection(self, **options):
        conn = self.get(**options)
        try:
            yield conn
            # what to do in case of success
        except Exception as e:
            conn.handle_exception(e)
        finally:
            self.release_connection(conn)

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -
#
# This file is part of socketpool.
# See the NOTICE for more information.

import errno
import os
import platform
import select
import socket
import sys

try:
    from importlib import import_module
except ImportError:
    import sys

    def _resolve_name(name, package, level):
        """Return the absolute name of the module to be imported."""
        if not hasattr(package, 'rindex'):
            raise ValueError("'package' not set to a string")
        dot = len(package)
        for x in range(level, 1, -1):
            try:
                dot = package.rindex('.', 0, dot)
            except ValueError:
                raise ValueError("attempted relative import beyond top-level "
                                  "package")
        return "%s.%s" % (package[:dot], name)


    def import_module(name, package=None):
        """Import a module.

        The 'package' argument is required when performing a relative import. It
        specifies the package to use as the anchor point from which to resolve the
        relative import to an absolute import.

        """
        if name.startswith('.'):
            if not package:
                raise TypeError("relative imports require the 'package' argument")
            level = 0
            for character in name:
                if character != '.':
                    break
                level += 1
            name = _resolve_name(name[level:], package, level)
        __import__(name)
        return sys.modules[name]

def load_backend(backend_name):
    """ load pool backend. If this is an external module it should be
    passed as "somelib.backend_mod", for socketpool backend you can just
    pass the name.

    Supported backend are :
        - thread: connection are maintained in a threadsafe queue.
        - gevent: support gevent
        - eventlet: support eventlet

    """
    try:
        if len(backend_name.split(".")) > 1:
            mod = import_module(backend_name)
        else:
            mod = import_module("socketpool.backend_%s" % backend_name)
        return mod
    except ImportError:
        error_msg = "%s isn't a socketpool backend" % backend_name
        raise ImportError(error_msg)


def can_use_kqueue():
    # See Issue #15. kqueue doesn't work on OS X 10.6 and below.
    if not hasattr(select, "kqueue"):
        return False

    if platform.system() == 'Darwin' and platform.mac_ver()[0] < '10.7':
        return False

    return True

def is_connected(skt):
    try:
        fno = skt.fileno()
    except socket.error as e:
        if e[0] == errno.EBADF:
            return False
        raise

    try:
        if hasattr(select, "epoll"):
            ep = select.epoll()
            ep.register(fno, select.EPOLLOUT | select.EPOLLIN)
            events = ep.poll(0)
            for fd, ev in events:
                if fno == fd and \
                        (ev & select.EPOLLOUT or ev & select.EPOLLIN):
                    ep.unregister(fno)
                    return True
            ep.unregister(fno)
        elif hasattr(select, "poll"):
            p = select.poll()
            p.register(fno, select.POLLOUT | select.POLLIN)
            events = p.poll(0)
            for fd, ev in events:
                if fno == fd and \
                        (ev & select.POLLOUT or ev & select.POLLIN):
                    p.unregister(fno)
                    return True
            p.unregister(fno)
        elif can_use_kqueue():
            kq = select.kqueue()
            events = [
                select.kevent(fno, select.KQ_FILTER_READ, select.KQ_EV_ADD),
                select.kevent(fno, select.KQ_FILTER_WRITE, select.KQ_EV_ADD)
            ]
            kq.control(events, 0)
            kevents = kq.control(None, 4, 0)
            for ev in kevents:
                if ev.ident == fno:
                    if ev.flags & select.KQ_EV_ERROR:
                        return False
                    else:
                        return True

            # delete
            events = [
                select.kevent(fno, select.KQ_FILTER_READ, select.KQ_EV_DELETE),
                select.kevent(fno, select.KQ_FILTER_WRITE, select.KQ_EV_DELETE)
            ]
            kq.control(events, 0)
            kq.close()
            return True
        else:
            r, _, _ = select.select([fno], [], [], 0)
            if not r:
                return True

    except IOError:
        pass
    except (ValueError, select.error,) as e:
        pass

    return False

########NEW FILE########
__FILENAME__ = test_backend_finding
from socketpool.pool import ConnectionPool
from socketpool.conn import TcpConnector

def pytest_generate_tests(metafunc):
    if 'backend' in metafunc.fixturenames:
        metafunc.parametrize('backend', ['thread', 'gevent', 'eventlet'])

class Test_Backend(object):
    def make_and_check_backend(self, expected_name, **kw):
        pool = ConnectionPool(TcpConnector, **kw)
        assert pool.backend == expected_name
        return pool

    def test_default_backend(self):
        self.make_and_check_backend('thread')

    def test_backend(self, backend):
        self.make_and_check_backend(backend, backend=backend)

    def test_thread_backend_as_module(self):
        from socketpool import backend_thread
        self.make_and_check_backend('socketpool.backend_thread',
                                    backend=backend_thread)

########NEW FILE########
__FILENAME__ = test_pool_01
# -*- coding: utf-8 -
#
# This file is part of socketpool.
# See the NOTICE for more information.

import time

import pytest

from socketpool import ConnectionPool, Connector
from socketpool.pool import MaxTriesError

class MessyConnector(Connector):

    def __init__(self, **options):
        pass

    def is_connected(self):
        return False

    def invalidate(self):
        pass

class Test_Pool(object):
    def test_size_on_isconnected_failure(self):
        pool = ConnectionPool(MessyConnector)
        assert pool.size == 0
        pytest.raises(MaxTriesError, pool.get)

    def test_stop_reaper_thread(self):
        """Verify that calling stop_reaper will terminate the reaper thread.
        """
        pool = ConnectionPool(MessyConnector, backend='thread')
        assert pool._reaper.running
        pool.stop_reaper()

        for i in xrange(1000):
            if not pool._reaper.running:
                return
            time.sleep(0.01)

        assert False, 'Reaper thread not terminated in time.'

    def test_del(self):
        """Verify that garbage collection of the pool will release the reaper
        thread.
        """
        pool = ConnectionPool(MessyConnector, backend='thread')
        reaper = pool._reaper

        assert reaper.running

        # Remove reference.
        pool = None

        for i in xrange(1000):
            if not reaper.running:
                return
            time.sleep(0.01)

        assert False, 'Reaper thread not terminated in time.'

########NEW FILE########
