__FILENAME__ = bluelet
"""Extremely simple pure-Python implementation of coroutine-style
asynchronous socket I/O. Inspired by, but inferior to, Eventlet.
Bluelet can also be thought of as a less-terrible replacement for
asyncore.

Bluelet: easy concurrency without all the messy parallelism.
"""
import socket
import select
import sys
import types
import errno
import traceback
import time
import collections


# A little bit of "six" (Python 2/3 compatibility): cope with PEP 3109 syntax
# changes.

PY3 = sys.version_info[0] == 3
if PY3:
    def _reraise(typ, exc, tb):
        raise exc.with_traceback(tb)
else:
    exec("""
def _reraise(typ, exc, tb):
    raise typ, exc, tb
""")


# Basic events used for thread scheduling.

class Event(object):
    """Just a base class identifying Bluelet events. An event is an
    object yielded from a Bluelet thread coroutine to suspend operation
    and communicate with the scheduler.
    """
    pass

class WaitableEvent(Event):
    """A waitable event is one encapsulating an action that can be
    waited for using a select() call. That is, it's an event with an
    associated file descriptor.
    """
    def waitables(self):
        """Return "waitable" objects to pass to select(). Should return
        three iterables for input readiness, output readiness, and
        exceptional conditions (i.e., the three lists passed to
        select()).
        """
        return (), (), ()

    def fire(self):
        """Called when an associated file descriptor becomes ready
        (i.e., is returned from a select() call).
        """
        pass

class ValueEvent(Event):
    """An event that does nothing but return a fixed value."""
    def __init__(self, value):
        self.value = value

class ExceptionEvent(Event):
    """Raise an exception at the yield point. Used internally."""
    def __init__(self, exc_info):
        self.exc_info = exc_info

class SpawnEvent(Event):
    """Add a new coroutine thread to the scheduler."""
    def __init__(self, coro):
        self.spawned = coro

class JoinEvent(Event):
    """Suspend the thread until the specified child thread has
    completed.
    """
    def __init__(self, child):
        self.child = child

class KillEvent(Event):
    """Unschedule a child thread."""
    def __init__(self, child):
        self.child = child

class DelegationEvent(Event):
    """Suspend execution of the current thread, start a new thread and,
    once the child thread finished, return control to the parent
    thread.
    """
    def __init__(self, coro):
        self.spawned = coro

class ReturnEvent(Event):
    """Return a value the current thread's delegator at the point of
    delegation. Ends the current (delegate) thread.
    """
    def __init__(self, value):
        self.value = value

class SleepEvent(WaitableEvent):
    """Suspend the thread for a given duration.
    """
    def __init__(self, duration):
        self.wakeup_time = time.time() + duration

    def time_left(self):
        return max(self.wakeup_time - time.time(), 0.0)

class ReadEvent(WaitableEvent):
    """Reads from a file-like object."""
    def __init__(self, fd, bufsize):
        self.fd = fd
        self.bufsize = bufsize

    def waitables(self):
        return (self.fd,), (), ()

    def fire(self):
        return self.fd.read(self.bufsize)

class WriteEvent(WaitableEvent):
    """Writes to a file-like object."""
    def __init__(self, fd, data):
        self.fd = fd
        self.data = data

    def waitable(self):
        return (), (self.fd,), ()

    def fire(self):
        self.fd.write(self.data)


# Core logic for executing and scheduling threads.

def _event_select(events):
    """Perform a select() over all the Events provided, returning the
    ones ready to be fired. Only WaitableEvents (including SleepEvents)
    matter here; all other events are ignored (and thus postponed).
    """
    # Gather waitables and wakeup times.
    waitable_to_event = {}
    rlist, wlist, xlist = [], [], []
    earliest_wakeup = None
    for event in events:
        if isinstance(event, SleepEvent):
            if not earliest_wakeup:
                earliest_wakeup = event.wakeup_time
            else:
                earliest_wakeup = min(earliest_wakeup, event.wakeup_time)
        elif isinstance(event, WaitableEvent):
            r, w, x = event.waitables()
            rlist += r
            wlist += w
            xlist += x
            for waitable in r:
                waitable_to_event[('r', waitable)] = event
            for waitable in w:
                waitable_to_event[('w', waitable)] = event
            for waitable in x:
                waitable_to_event[('x', waitable)] = event

    # If we have a any sleeping threads, determine how long to sleep.
    if earliest_wakeup:
        timeout = max(earliest_wakeup - time.time(), 0.0)
    else:
        timeout = None

    # Perform select() if we have any waitables.
    if rlist or wlist or xlist:
        rready, wready, xready = select.select(rlist, wlist, xlist, timeout)
    else:
        rready, wready, xready = (), (), ()
        if timeout:
            time.sleep(timeout)

    # Gather ready events corresponding to the ready waitables.
    ready_events = set()
    for ready in rready:
        ready_events.add(waitable_to_event[('r', ready)])
    for ready in wready:
        ready_events.add(waitable_to_event[('w', ready)])
    for ready in xready:
        ready_events.add(waitable_to_event[('x', ready)])

    # Gather any finished sleeps.
    for event in events:
        if isinstance(event, SleepEvent) and event.time_left() == 0.0:
            ready_events.add(event)

    return ready_events

class ThreadException(Exception):
    def __init__(self, coro, exc_info):
        self.coro = coro
        self.exc_info = exc_info
    def reraise(self):
        _reraise(self.exc_info[0], self.exc_info[1], self.exc_info[2])

SUSPENDED = Event()  # Special sentinel placeholder for suspended threads.

class Delegated(Event):
    """Placeholder indicating that a thread has delegated execution to a
    different thread.
    """
    def __init__(self, child):
        self.child = child

def run(root_coro):
    """Schedules a coroutine, running it to completion. This
    encapsulates the Bluelet scheduler, which the root coroutine can
    add to by spawning new coroutines.
    """
    # The "threads" dictionary keeps track of all the currently-
    # executing and suspended coroutines. It maps coroutines to their
    # currently "blocking" event. The event value may be SUSPENDED if
    # the coroutine is waiting on some other condition: namely, a
    # delegated coroutine or a joined coroutine. In this case, the
    # coroutine should *also* appear as a value in one of the below
    # dictionaries `delegators` or `joiners`.
    threads = {root_coro: ValueEvent(None)}

    # Maps child coroutines to delegating parents.
    delegators = {}

    # Maps child coroutines to joining (exit-waiting) parents.
    joiners = collections.defaultdict(list)

    def complete_thread(coro, return_value):
        """Remove a coroutine from the scheduling pool, awaking
        delegators and joiners as necessary and returning the specified
        value to any delegating parent.
        """
        del threads[coro]

        # Resume delegator.
        if coro in delegators:
            threads[delegators[coro]] = ValueEvent(return_value)
            del delegators[coro]

        # Resume joiners.
        if coro in joiners:
            for parent in joiners[coro]:
                threads[parent] = ValueEvent(None)
            del joiners[coro]

    def advance_thread(coro, value, is_exc=False):
        """After an event is fired, run a given coroutine associated with
        it in the threads dict until it yields again. If the coroutine
        exits, then the thread is removed from the pool. If the coroutine
        raises an exception, it is reraised in a ThreadException. If
        is_exc is True, then the value must be an exc_info tuple and the
        exception is thrown into the coroutine.
        """
        try:
            if is_exc:
                next_event = coro.throw(*value)
            else:
                next_event = coro.send(value)
        except StopIteration:
            # Thread is done.
            complete_thread(coro, None)
        except:
            # Thread raised some other exception.
            del threads[coro]
            raise ThreadException(coro, sys.exc_info())
        else:
            if isinstance(next_event, types.GeneratorType):
                # Automatically invoke sub-coroutines. (Shorthand for
                # explicit bluelet.call().)
                next_event = DelegationEvent(next_event)
            threads[coro] = next_event

    def kill_thread(coro):
        """Unschedule this thread and its (recursive) delegates.
        """
        # Collect all coroutines in the delegation stack.
        coros = [coro]
        while isinstance(threads[coro], Delegated):
            coro = threads[coro].child
            coros.append(coro)

        # Complete each coroutine from the top to the bottom of the
        # stack.
        for coro in reversed(coros):
            complete_thread(coro, None)

    # Continue advancing threads until root thread exits.
    exit_te = None
    while threads:
        try:
            # Look for events that can be run immediately. Continue
            # running immediate events until nothing is ready.
            while True:
                have_ready = False
                for coro, event in list(threads.items()):
                    if isinstance(event, SpawnEvent):
                        threads[event.spawned] = ValueEvent(None)  # Spawn.
                        advance_thread(coro, None)
                        have_ready = True
                    elif isinstance(event, ValueEvent):
                        advance_thread(coro, event.value)
                        have_ready = True
                    elif isinstance(event, ExceptionEvent):
                        advance_thread(coro, event.exc_info, True)
                        have_ready = True
                    elif isinstance(event, DelegationEvent):
                        threads[coro] = Delegated(event.spawned)  # Suspend.
                        threads[event.spawned] = ValueEvent(None)  # Spawn.
                        delegators[event.spawned] = coro
                        have_ready = True
                    elif isinstance(event, ReturnEvent):
                        # Thread is done.
                        complete_thread(coro, event.value)
                        have_ready = True
                    elif isinstance(event, JoinEvent):
                        threads[coro] = SUSPENDED  # Suspend.
                        joiners[event.child].append(coro)
                        have_ready = True
                    elif isinstance(event, KillEvent):
                        threads[coro] = ValueEvent(None)
                        kill_thread(event.child)
                        have_ready = True

                # Only start the select when nothing else is ready.
                if not have_ready:
                    break

            # Wait and fire.
            event2coro = dict((v,k) for k,v in threads.items())
            for event in _event_select(threads.values()):
                # Run the IO operation, but catch socket errors.
                try:
                    value = event.fire()
                except socket.error as exc:
                    if isinstance(exc.args, tuple) and \
                            exc.args[0] == errno.EPIPE:
                        # Broken pipe. Remote host disconnected.
                        pass
                    else:
                        traceback.print_exc()
                    # Abort the coroutine.
                    threads[event2coro[event]] = ReturnEvent(None)
                else:
                    advance_thread(event2coro[event], value)

        except ThreadException as te:
            # Exception raised from inside a thread.
            event = ExceptionEvent(te.exc_info)
            if te.coro in delegators:
                # The thread is a delegate. Raise exception in its
                # delegator.
                threads[delegators[te.coro]] = event
                del delegators[te.coro]
            else:
                # The thread is root-level. Raise in client code.
                exit_te = te
                break

        except:
            # For instance, KeyboardInterrupt during select(). Raise
            # into root thread and terminate others.
            threads = {root_coro: ExceptionEvent(sys.exc_info())}

    # If any threads still remain, kill them.
    for coro in threads:
        coro.close()

    # If we're exiting with an exception, raise it in the client.
    if exit_te:
        exit_te.reraise()


# Sockets and their associated events.

class SocketClosedError(Exception):
    pass

class Listener(object):
    """A socket wrapper object for listening sockets.
    """
    def __init__(self, host, port):
        """Create a listening socket on the given hostname and port.
        """
        self._closed = False
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(5)

    def accept(self):
        """An event that waits for a connection on the listening socket.
        When a connection is made, the event returns a Connection
        object.
        """
        if self._closed:
            raise SocketClosedError()
        return AcceptEvent(self)

    def close(self):
        """Immediately close the listening socket. (Not an event.)
        """
        self._closed = True
        self.sock.close()

class Connection(object):
    """A socket wrapper object for connected sockets.
    """
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self._buf = b''
        self._closed = False

    def close(self):
        """Close the connection."""
        self._closed = True
        self.sock.close()

    def recv(self, size):
        """Read at most size bytes of data from the socket."""
        if self._closed:
            raise SocketClosedError()

        if self._buf:
            # We already have data read previously.
            out = self._buf[:size]
            self._buf = self._buf[size:]
            return ValueEvent(out)
        else:
            return ReceiveEvent(self, size)

    def send(self, data):
        """Sends data on the socket, returning the number of bytes
        successfully sent.
        """
        if self._closed:
            raise SocketClosedError()
        return SendEvent(self, data)

    def sendall(self, data):
        """Send all of data on the socket."""
        if self._closed:
            raise SocketClosedError()
        return SendEvent(self, data, True)

    def readline(self, terminator=b"\n", bufsize=1024):
        """Reads a line (delimited by terminator) from the socket."""
        if self._closed:
            raise SocketClosedError()

        while True:
            if terminator in self._buf:
                line, self._buf = self._buf.split(terminator, 1)
                line += terminator
                yield ReturnEvent(line)
                break
            data = yield ReceiveEvent(self, bufsize)
            if data:
                self._buf += data
            else:
                line = self._buf
                self._buf = b''
                yield ReturnEvent(line)
                break

class AcceptEvent(WaitableEvent):
    """An event for Listener objects (listening sockets) that suspends
    execution until the socket gets a connection.
    """
    def __init__(self, listener):
        self.listener = listener

    def waitables(self):
        return (self.listener.sock,), (), ()

    def fire(self):
        sock, addr = self.listener.sock.accept()
        return Connection(sock, addr)

class ReceiveEvent(WaitableEvent):
    """An event for Connection objects (connected sockets) for
    asynchronously reading data.
    """
    def __init__(self, conn, bufsize):
        self.conn = conn
        self.bufsize = bufsize

    def waitables(self):
        return (self.conn.sock,), (), ()

    def fire(self):
        return self.conn.sock.recv(self.bufsize)

class SendEvent(WaitableEvent):
    """An event for Connection objects (connected sockets) for
    asynchronously writing data.
    """
    def __init__(self, conn, data, sendall=False):
        self.conn = conn
        self.data = data
        self.sendall = sendall

    def waitables(self):
        return (), (self.conn.sock,), ()

    def fire(self):
        if self.sendall:
            return self.conn.sock.sendall(self.data)
        else:
            return self.conn.sock.send(self.data)


# Public interface for threads; each returns an event object that
# can immediately be "yield"ed.

def null():
    """Event: yield to the scheduler without doing anything special.
    """
    return ValueEvent(None)

def spawn(coro):
    """Event: add another coroutine to the scheduler. Both the parent
    and child coroutines run concurrently.
    """
    if not isinstance(coro, types.GeneratorType):
        raise ValueError('%s is not a coroutine' % str(coro))
    return SpawnEvent(coro)

def call(coro):
    """Event: delegate to another coroutine. The current coroutine
    is resumed once the sub-coroutine finishes. If the sub-coroutine
    returns a value using end(), then this event returns that value.
    """
    if not isinstance(coro, types.GeneratorType):
        raise ValueError('%s is not a coroutine' % str(coro))
    return DelegationEvent(coro)

def end(value=None):
    """Event: ends the coroutine and returns a value to its
    delegator.
    """
    return ReturnEvent(value)

def read(fd, bufsize=None):
    """Event: read from a file descriptor asynchronously."""
    if bufsize is None:
        # Read all.
        def reader():
            buf = []
            while True:
                data = yield read(fd, 1024)
                if not data:
                    break
                buf.append(data)
            yield ReturnEvent(''.join(buf))
        return DelegationEvent(reader())

    else:
        return ReadEvent(fd, bufsize)

def write(fd, data):
    """Event: write to a file descriptor asynchronously."""
    return WriteEvent(fd, data)

def connect(host, port):
    """Event: connect to a network address and return a Connection
    object for communicating on the socket.
    """
    addr = (host, port)
    sock = socket.create_connection(addr)
    return ValueEvent(Connection(sock, addr))

def sleep(duration):
    """Event: suspend the thread for ``duration`` seconds.
    """
    return SleepEvent(duration)

def join(coro):
    """Suspend the thread until another, previously `spawn`ed thread
    completes.
    """
    return JoinEvent(coro)

def kill(coro):
    """Halt the execution of a different `spawn`ed thread.
    """
    return KillEvent(coro)


# Convenience function for running socket servers.

def server(host, port, func):
    """A coroutine that runs a network server. Host and port specify the
    listening address. func should be a coroutine that takes a single
    parameter, a Connection object. The coroutine is invoked for every
    incoming connection on the listening socket.
    """
    def handler(conn):
        try:
            yield func(conn)
        finally:
            conn.close()

    listener = Listener(host, port)
    try:
        while True:
            conn = yield listener.accept()
            yield spawn(handler(conn))
    except KeyboardInterrupt:
        pass
    finally:
        listener.close()

########NEW FILE########
__FILENAME__ = crawler
"""Demonstrates various ways of writing an application that makes
many URL requests.

Unfortunately, because the Python standard library only includes
blocking HTTP libraries, taking advantage of asynchronous I/O currently
entails writing a custom HTTP client. This example includes a very
simple, GET-only HTTP requester.
"""
from __future__ import print_function
import sys
import json
import threading
import multiprocessing
import time
sys.path.insert(0, '..')
import bluelet

# Python 2/3 compatibility.

PY3 = sys.version_info[0] == 3
if PY3:
    from urllib.parse import urlparse
    from urllib.request import urlopen
else:
    from urlparse import urlparse
    from urllib import urlopen


URL = 'http://api.twitter.com/1/statuses/user_timeline.json' \
      '?screen_name=%s&count=1'
USERNAMES = ('samps', 'b33ts', 'twitter', 'twitterapi', 'Support')

class AsyncHTTPClient(object):
    """A basic Bluelet-based asynchronous HTTP client. Only supports
    very simple GET queries.
    """
    def __init__(self, host, port, path):
        self.host = host
        self.port = port
        self.path = path

    def headers(self):
        """Returns the HTTP headers for this request."""
        heads = [
            "GET %s HTTP/1.1" % self.path,
            "Host: %s" % self.host,
            "User-Agent: bluelet-example",
        ]
        return "\r\n".join(heads).encode('utf8') + b"\r\n\r\n"


    # Convenience methods.

    @classmethod
    def from_url(cls, url):
        """Construct a request for the specified URL."""
        res = urlparse(url)
        path = res.path
        if res.query:
            path += '?' + res.query
        return cls(res.hostname, res.port or 80, path)

    @classmethod
    def fetch(cls, url):
        """Fetch content from an HTTP URL. This is a coroutine suitable
        for yielding to bluelet.
        """
        client = cls.from_url(url)
        yield client._connect()
        yield client._request()
        status, headers, body = yield client._read()
        yield bluelet.end(body)
    

    # Internal coroutines.

    def _connect(self):
        self.conn = yield bluelet.connect(self.host, self.port)

    def _request(self):
        yield self.conn.sendall(self.headers())

    def _read(self):
        buf = []
        while True:
            data = yield self.conn.recv(4096)
            if not data:
                break
            buf.append(data)
        response = ''.join(buf)

        # Parse response.
        headers, body = response.split("\r\n\r\n", 1)
        headers = headers.split("\r\n")
        status = headers.pop(0)
        version, code, message = status.split(' ', 2)
        headervals = {}
        for header in headers:
            key, value = header.split(": ")
            headervals[key] = value

        yield bluelet.end((int(code), headers, body))


# Various ways of writing the crawler.

def run_bluelet():
    # No lock is required guarding the shared variable because only
    # one thread is actually running at a time.
    tweets = {}

    def fetch(username):
        url = URL % username
        data = yield AsyncHTTPClient.fetch(url)
        tweets[username] = json.loads(data)[0]['text']

    def crawl():
        for username in USERNAMES:
            yield bluelet.spawn(fetch(username))

    bluelet.run(crawl())
    return tweets

def run_sequential():
    tweets = {}

    for username in USERNAMES:
        url = URL % username
        f = urlopen(url)
        data = f.read().decode('utf8')
        tweets[username] = json.loads(data)[0]['text']

    return tweets

def run_threaded():
    # We need a lock to avoid conflicting updates to the tweet
    # dictionary.
    lock = threading.Lock()
    tweets = {}

    class Fetch(threading.Thread):
        def __init__(self, username):
            threading.Thread.__init__(self)
            self.username = username
        def run(self):
            url = URL % self.username
            f = urlopen(url)
            data = f.read().decode('utf8')
            tweet = json.loads(data)[0]['text']
            with lock:
                tweets[self.username] = tweet

    # Start every thread and then wait for them all to finish.
    threads = [Fetch(name) for name in USERNAMES]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return tweets

def _process_fetch(username):
    # Mapped functions in multiprocessing can't be closures, so this
    # has to be at the module-global scope.
    url = URL % username
    f = urlopen(url)
    data = f.read().decode('utf8')
    tweet = json.loads(data)[0]['text']
    return (username, tweet)
def run_processes():
    pool = multiprocessing.Pool(len(USERNAMES))
    tweet_pairs = pool.map(_process_fetch, USERNAMES)
    return dict(tweet_pairs)


# Main driver.

if __name__ == '__main__':
    strategies = {
        'bluelet': run_bluelet,
        'sequential': run_sequential,
        'threading': run_threaded,
        'multiprocessing': run_processes,
    }
    for name, func in strategies.items():
        start = time.time()
        tweets = func()
        end = time.time()
        print('%s: %.2f seconds' % (name, (end - start)))

    # Show the tweets, just for fun.
    print()
    for username, tweet in tweets.items():
        print('%s: %s' % (username, tweet))

########NEW FILE########
__FILENAME__ = delegation
"""A demonstration of Bluelet's approach to invoking (delegating to)
sub-coroutines and spawning child coroutines.
"""
import sys
sys.path.insert(0, '..')
import bluelet

def child():
    print 'Child started.'
    yield bluelet.null()
    print 'Child resumed.'
    yield bluelet.null()
    print 'Child ending.'
    yield bluelet.end(42)
def parent():
    print 'Parent started.'
    yield bluelet.null()
    print 'Parent resumed.'
    result = yield child()
    print 'Child returned:', repr(result)
    print 'Parent ending.'

def exc_child():
    yield bluelet.null()
    raise Exception()
def exc_parent():
    try:
        yield exc_child()
    except Exception, exc:
        print 'Parent caught:', repr(exc)
def exc_grandparent():
    yield bluelet.spawn(exc_parent())

if __name__ == '__main__':
    bluelet.run(parent())
    bluelet.run(exc_grandparent())

########NEW FILE########
__FILENAME__ = echo
from __future__ import print_function
import sys
sys.path.insert(0, '..')
import bluelet

def echoer(conn):
    print('Connected: %s' % conn.addr[0])
    try:
        while True:
            data = yield conn.recv(1024)
            if not data:
                break
            print('Read from %s: %s' % (conn.addr[0], repr(data)))
            yield conn.sendall(data)
    finally:
        print('Disconnected: %s' % conn.addr[0])
        conn.close()
        
def echoserver():
    listener = bluelet.Listener('', 4915)
    try:
        while True:
            conn = yield listener.accept()
            yield bluelet.spawn(echoer(conn))
    except KeyboardInterrupt:
        print()
    finally:
        print('Exiting.')
        listener.close()

if __name__ == '__main__':
    bluelet.run(echoserver())

########NEW FILE########
__FILENAME__ = echo_asyncore
import asyncore
import socket
class Echoer(asyncore.dispatcher_with_send):
    def handle_read(self):
        data = self.recv(1024)
        self.send(data)
class EchoServer(asyncore.dispatcher):
    def __init__(self):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(('', 4915))
        self.listen(1)
    def handle_accept(self):
        sock, addr = self.accept()
        handler = Echoer(sock)
server = EchoServer()
asyncore.loop()

########NEW FILE########
__FILENAME__ = echo_plain
import socket
listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.bind(('', 4915))
listener.listen(1)
while True:
    sock, addr = listener.accept()
    while True:
        data = sock.recv(1024)
        if not data:
            break
        sock.sendall(data)

########NEW FILE########
__FILENAME__ = echo_simple
import sys
sys.path.insert(0, '..')
import bluelet

def echoer(conn):
    while True:
        data = yield conn.recv(1024)
        if not data:
            break
        yield conn.sendall(data)

if __name__ == '__main__':
    bluelet.run(bluelet.server('', 4915, echoer))

########NEW FILE########
__FILENAME__ = httpd
"""A simple Web server built with Bluelet to support concurrent requests
in a single OS thread.
"""
from __future__ import print_function
import sys
import os
import mimetypes
sys.path.insert(0, '..')
import bluelet

ROOT = '.'
INDEX_FILENAME = 'index.html'

def parse_request(lines):
    """Parse an HTTP request."""
    method, path, version = lines.pop(0).split(None, 2)
    headers = {}
    for line in lines:
        if not line:
            continue
        key, value = line.split(b': ', 1)
        headers[key] = value
    return method, path, headers

def mime_type(filename):
    """Return a reasonable MIME type for the file or text/plain as a
    fallback.
    """
    mt, _ = mimetypes.guess_type(filename)
    if mt:
        return mt
    else:
        return 'text/plain'

def respond(method, path, headers):
    """Generate an HTTP response for a parsed request."""
    # Remove query string, if any.
    if b'?' in path:
        path, query = path.split(b'?', 1)
    path = path.decode('utf8')

    # Strip leading / and add prefix.
    if path.startswith('/') and len(path) > 0:
        filename = path[1:]
    else:
        filename = path
    filename = os.path.join(ROOT, filename)

    # Expand to index file if possible.
    index_fn = os.path.join(filename, INDEX_FILENAME)
    if os.path.isdir(filename) and os.path.exists(index_fn):
        filename = index_fn

    if os.path.isdir(filename):
        # Directory listing.
        files = []
        for name in os.listdir(filename):
            files.append('<li><a href="%s">%s</a></li>' % (name, name))
        html = "<html><head><title>%s</title></head><body>" \
               "<h1>%s</h1><ul>%s</ul></body></html>""" % \
               (path, path, ''.join(files))
        return '200 OK', {'Content-Type': 'text/html'}, html

    elif os.path.exists(filename):
        # Send file contents.
        with open(filename) as f:
            return '200 OK', {'Content-Type': mime_type(filename)}, f.read()

    else:
        # Not found.
        print('Not found.')
        return '404 Not Found', {'Content-Type': 'text/html'}, \
               '<html><head><title>404 Not Found</title></head>' \
               '<body><h1>Not found.</h1></body></html>'

def webrequest(conn):
    """A Bluelet coroutine implementing an HTTP server."""
    # Get the HTTP request.
    request = []
    while True:
        line = (yield conn.readline(b'\r\n')).strip()
        if not line:
            # End of headers.
            break
        request.append(line)

    # Make sure a request was sent.
    if not request:
        return

    # Parse and log the request and get the response values.
    method, path, headers = parse_request(request)
    print('%s %s' % (method, path))
    status, headers, content = respond(method, path, headers)

    # Send response.
    yield conn.sendall(("HTTP/1.1 %s\r\n" % status).encode('utf8'))
    for key, value in headers.items():
        yield conn.sendall(("%s: %s\r\n" % (key, value)).encode('utf8'))
    yield conn.sendall(b"\r\n")
    yield conn.sendall(content)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        ROOT = os.path.expanduser(sys.argv[1])
    print('http://127.0.0.1:8000/')
    bluelet.run(bluelet.server('', 8000, webrequest))

########NEW FILE########
__FILENAME__ = ipc
from __future__ import print_function
import sys
sys.path.insert(0, '..')
import bluelet
import multiprocessing
import pickle
import uuid

def server(ep):
    while True:
        message = yield ep.get()
        if message == 'stop':
            break
        yield ep.put(message ** 2)

def client(ep):
    for i in range(10):
        yield ep.put(i)
        squared = yield ep.get()
        print(squared)
    yield ep.put('stop')

class BlueletProc(multiprocessing.Process):
    def __init__(self, coro):
        super(BlueletProc, self).__init__()
        self.coro = coro

    def run(self):
        bluelet.run(self.coro)

class Endpoint(object):
    def __init__(self, conn, sentinel):
        self.conn = conn
        self.sentinel = sentinel

    def put(self, obj):
        yield self.conn.sendall(pickle.dumps(obj) + self.sentinel)

    def get(self):
        data = yield self.conn.readline(self.sentinel)
        data = data[:-len(self.sentinel)]
        yield bluelet.end(pickle.loads(data))

def channel(port=4915):
    # Create a pair of connected sockets.
    connections = [None, None]
    listener = bluelet.Listener('127.0.0.1', port)

    def listen():
        connections[0] = yield listener.accept()  # Avoiding nonlocal.
    listen_thread = listen()
    yield bluelet.spawn(listen_thread)

    connections[1] = yield bluelet.connect('127.0.0.1', port)

    yield bluelet.join(listen_thread)

    # Wrap sockets in Endpoints.
    sentinel = uuid.uuid4().bytes  # Somewhat hacky...
    yield bluelet.end((Endpoint(connections[0], sentinel),
                       Endpoint(connections[1], sentinel)))

def main():
    ep1, ep2 = yield channel()
    if False:
        # Run in bluelet (i.e., no parallelism).
        yield bluelet.spawn(server(ep1))
        yield bluelet.spawn(client(ep2))
    else:
        # Run in separate processes.
        ta = BlueletProc(server(ep1))
        tb = BlueletProc(client(ep2))
        ta.start()
        tb.start()
        ta.join()
        tb.join()

if __name__ == '__main__':
    bluelet.run(main())

########NEW FILE########
__FILENAME__ = sleepy
from __future__ import print_function
import sys
sys.path.insert(0, '..')
import bluelet

def sleeper(duration):
    print('Going to sleep for %i seconds...' % duration)
    yield bluelet.sleep(duration)
    print('...woke up after %i seconds.' % duration)
        
def sleepy():
    for i in (0, 1, 3, 5):
        yield bluelet.spawn(sleeper(i))

if __name__ == '__main__':
    bluelet.run(sleepy())

########NEW FILE########
