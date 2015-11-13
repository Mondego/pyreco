__FILENAME__ = benchmark
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import optparse
import time

from zenqueue.client import QueueClient
from zenqueue import log


option_parser = optparse.OptionParser(
    usage='python -m zenqueue.client.benchmark [options]', version='0.2')

option_parser.add_option('-a', '--address', metavar='ADDR',
    default='127.0.0.1:3000',
    help='Contact server on address ADDR [default %default]')

option_parser.add_option('-l', '--log-level', metavar='LEVEL', default='SILENT',
    help='Set logging level to LEVEL [default %default]')

option_parser.add_option('-n', '--num-messages', metavar='COUNT',
    default=1000000, type='int',
    help='Send/receive COUNT messages in total [default %default]')

option_parser.add_option('-u', '--unit-size', metavar='SIZE', default=10000,
    type='int',
    help='Send/receive messages in batches of SIZE [default %default]')

option_parser.add_option('-m', '--message', metavar='MESSAGE', default='a',
    help='Send/receive message MSG [default "%default"]')

option_parser.add_option('-s', '--synchronous', action='store_true',
    default=False,
    help='Use synchronous transfer mode [default asynchronous]')

option_parser.add_option('-t', '--http', action='store_true',
    default=False,
    help='Use HTTP instead of native client [default native]')


def main():
    options, args = option_parser.parse_args()

    # Set logging level
    if options.log_level.upper() == 'SILENT':
        log.silence()
    else:
        log.set_level(options.log_level.upper())

    # Build address
    split_addr = options.address.split(':')
    if len(split_addr) == 1:
        host, port = split_addr[0], 3000
    elif len(split_addr) == 2:
        host, port = split_addr[0], int(split_addr[1])
    else:
        print 'Invalid address specified; defaulting to 127.0.0.1:3000'
        host, port = '127.0.0.1', 3000
    
    # Build message unit
    message = options.message.decode('utf-8')
    unit = [message] * options.unit_size
    message_count = options.num_messages
    
    # Configure mode (sync/async).
    mode = 'async'
    if options.synchronous:
        mode = 'sync'
    
    # Configure method (native/http)
    method = 'native'
    if options.http:
        method = 'http'
    
    client = QueueClient(mode=mode, method=method, host=host, port=port)
    
    start_time = time.time()
    
    while message_count > 0:
        client.push_many(*unit)
        assert (client.pull_many(options.unit_size, timeout=0) == unit)
        message_count -= options.unit_size
    
    end_time = time.time()
    
    if method == 'native':
        client.close()
    
    time_taken = end_time - start_time
    
    print '%d messages transferred in chunks of %s' % (options.num_messages,
                                                       options.unit_size)
    print 'Time taken: %0.4f seconds' % (time_taken,)
    print 'Average speed: %0.4f messages/second' % (
        options.num_messages / time_taken,)


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-

from zenqueue import json
from zenqueue import log


class AbstractQueueClient(object):
    
    class QueueClientError(Exception): pass
    class ActionError(QueueClientError): pass
    class ClosedClientError(QueueClientError): pass
    class RequestError(QueueClientError): pass
    class Timeout(QueueClientError): pass
    class UnknownError(QueueClientError): pass
    
    actions = ['push', 'push_many', 'pull', 'pull_many']
    log_name = 'zenq.client'
    
    def __init__(self):
        self.log = log.get_logger(self.log_name + ':%x' % (id(self),))
    
    def send(self, data):
        raise NotImplementedError
    
    def action(self, action, args, kwargs):
        raise NotImplementedError
    
    def handle_response(self, data):
        try:
            status, result = json.loads(data)
        except ValueError, exc:
            self.log.error('Invalid response returned: %r', data)
            raise
        
        # This handles the various response statuses the server can return.
        if status == 'success':
            self.log.debug('Request successful')
            return result
        elif status == 'error:action':
            self.log.error('Action error occurred')
            raise self.ActionError(result)
        elif status == 'error:request':
            self.log.error('Request error occurred')
            raise self.RequestError(result)
        elif status == 'error:timeout':
            self.log.debug('Request timed out')
            raise self.Timeout
        elif status == 'error:unknown':
            self.log.error('Unknown error occurred')
            raise self.UnknownError(result)
    
    def __getattr__(self, attribute):
        if attribute in self.actions:
            def wrapper(*args, **kwargs):
                return self.action(attribute, args, kwargs)
            return wrapper
        raise AttributeError(attribute)

########NEW FILE########
__FILENAME__ = async
# -*- coding: utf-8 -*-

from eventlet import httpc

from zenqueue.client.http.common import HTTPQueueClient


class QueueClient(HTTPQueueClient):
    
    def send(self, url, data=''):
        # Catch non-successful HTTP requests and treat them as if they were.
        try:
            result = httpc.post(url, data=data,
                content_type='application/json; charset=utf-8')
        except httpc.ConnectionError, exc:
            result = exc.params.response_body
        
        return result
########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-

import urllib

from urlobject import URLObject

from zenqueue import json
from zenqueue.client.common import AbstractQueueClient


class HTTPQueueClient(AbstractQueueClient):
    
    log_name = 'zenq.client.http'
    
    def __init__(self, host='127.0.0.1', port=3080):
        super(HTTPQueueClient, self).__init__() # Initializes logging.
        
        self.host = host
        self.port = port
    
    def send(self, url, data=''):
        raise NotImplementedError
    
    def action(self, action, args, kwargs):
        # It's really pathetic, but it's still debugging output.
        self.log.debug('Action %r called with %d args', action,
            len(args) + len(kwargs))
        
        path = '/' + urllib.quote(action) + '/'        
        url = URLObject(host=self.host).with_port(self.port).with_path(path)
        received_data = self.send(url, data=json.dumps([args, kwargs]))
        
        return self.handle_response(received_data)
########NEW FILE########
__FILENAME__ = sync
# -*- coding: utf-8 -*-

import urllib2

from zenqueue.client.http.common import HTTPQueueClient


class QueueClient(HTTPQueueClient):
    
    def send(self, url, data=''):
        request = urllib2.Request(url, data=data)
        request.add_header('Content-Type', 'application/json; charset=utf-8')
        
        # Catch non-successful HTTP requests and treat them as if they were.
        try:
            conn = urllib2.urlopen(request)
        except urllib2.HTTPError, exc:
            conn = exc
        
        # Both `urllib2.HTTPError` and normal response objects have the same
        # methods and behavior.
        try:
            result = conn.read()
        finally:
            conn.close()
        
        return result
########NEW FILE########
__FILENAME__ = async
# -*- coding: utf-8 -*-

from eventlet import api

from zenqueue.client.native.common import NativeQueueClient
from zenqueue.utils.async import Lock


class QueueClient(NativeQueueClient):
    
    lock_class = Lock
    
    def connect_tcp(self, address):
        self.log.info('Connecting to server at address %r', address)
        return api.connect_tcp(address)

########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-

from collections import deque
import errno
import socket

from zenqueue import json
from zenqueue import log
from zenqueue.client.common import AbstractQueueClient


CLOSE_SIGNAL = object() # A sort of singleton, which you can test with `is`.


class NativeQueueClient(AbstractQueueClient):
    
    log_name = 'zenq.client.native'
    lock_class = NotImplemented
    
    def __init__(self, host='127.0.0.1', port=3000):
        super(NativeQueueClient, self).__init__() # Initializes the log.
        
        self.socket = self.connect_tcp((host, port))
        self.__reader = None
        self.__writer = None
        self.__closed = False
        
        self.lock = self.lock_class()
    
    def connect_tcp(self, address):
        # This is an abstract supermethod.
        raise NotImplementedError
    
    # Magic methods for use with the 'with' statement (context management).
    # Although ZenQueue runs really slowly on Python 2.6 and I don't know why.
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()
        return False
    
    def close(self):
        # The following closes the connection by first sending the 'quit'
        # message and then closing the socket via the forced _close() method.
        self.lock.acquire()
        try:
            self.writer.write(json.dumps(['quit']) + '\r\n')
            self._close()
        except Exception, exc:
            self.log.error('Error %r occurred while closing connection', exc)
            raise
        finally:
            self.lock.release()
    
    def _close(self):
        self.lock.cancel_all()
        
        # If it's already been closed, no need to close it.
        if not self.socket:
            return
        
        # Close the connection with the server.
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except socket.error, exc:
            # If 'broken pipe' or 'bad file descriptor' exceptions are raised
            # then it basically means the server has already been closed.
            if exc[0] not in [errno.EBADF, errno.EPIPE, errno.ENOTCONN]:
                raise
        
        self.socket.close()
        
        self.socket = None
        self.__writer = None
        self.__reader = None
        self.__closed = True
    
    def send(self, data):
        
        # Acquire the socket lock.
        self.log.debug('Acquiring socket lock')
        self.lock.acquire()
        self.log.debug('Socket lock acquired')
        
        if not self.socket:
            raise self.ClosedClientError
        
        try:
            # Send the request data. It should be a single line,
            # terminated by CR/LF characters, but we won't try to
            # enforce this because we assume the client knows what
            # he/she/it is doing.
            self.log.debug('Sending request data')
            self.writer.write(data)
            # Necessary to ensure the data is sent.
            self.writer.flush()
            
            self.log.debug('Reading line from server')
            # This could block, in which case no other thread would be able to
            # use this client object until it were finished.
            result = self.reader.readline().rstrip('\r\n')
            self.log.debug('Line read from server')
        except Exception, exc:
            self.log.error('Error %r occurred', exc)
            raise
        finally:
            self.log.debug('Releasing socket lock')
            self.lock.release()
        
        return result
    
    def action(self, action, args, kwargs):
        # It's really pathetic, but it's still debugging output.
        self.log.debug('Action %r called with %d args', action,
            len(args) + len(kwargs))
        
        # This method is responsible for the JSON encoding/decoding, not send().
        # This was deliberate because it keeps most of the protocol details
        # separate from the lower-level socket code.
        received_data = self.send(json.dumps([action, args, kwargs]) + '\r\n')
        return self.handle_response(received_data)
    
    @property
    def reader(self):
        # Caches reader attribute. This wraps the socket, making it work like
        # a file handle (with read() and readline() methods, etc.).
        if (not self.__reader) and self.socket:
            self.__reader = self.socket.makefile('r')
        return self.__reader
    
    @property
    def writer(self):
        # Caches writer attribute. See the comments on the reader property for
        # more information.
        if (not self.__writer) and self.socket:
            self.__writer = self.socket.makefile('w')
        return self.__writer
    
    @property
    def closed(self):
        return self.__closed

########NEW FILE########
__FILENAME__ = sync
# -*- coding: utf-8 -*-

import socket
import threading

from zenqueue.client.native.common import NativeQueueClient
from zenqueue.utils.sync import Lock


class QueueClient(NativeQueueClient):
    
    lock_class = Lock
    
    def connect_tcp(self, address):
        self.log.info('Connecting to server at address %r', address)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(address)
        return sock

########NEW FILE########
__FILENAME__ = log
# -*- coding: utf-8 -*-

# This module contains some defaults for the logging system.

import logging
import sys


LOG_FORMATTER = logging.Formatter(
    "%(asctime)s :: %(name)s :: %(levelname)-7s :: %(message)s",
    datefmt='%a, %d %b %Y %H:%M:%S')

CONSOLE_HANDLER = logging.StreamHandler(sys.stdout)
CONSOLE_HANDLER.setLevel(logging.DEBUG)
CONSOLE_HANDLER.setFormatter(LOG_FORMATTER)

ROOT_LOGGER = logging.getLogger('')
ROOT_LOGGER.setLevel(logging.DEBUG) # Default logging level for library work.
ROOT_LOGGER.addHandler(CONSOLE_HANDLER)

LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL', 'CRITICAL']
for level in LOG_LEVELS:
    vars()[level] = getattr(logging, level)

global get_logger
get_logger = logging.getLogger

def set_level(level):
    ROOT_LOGGER.setLevel(getattr(logging, level))

def silence():
    global get_logger
    get_logger = lambda name: NullLogger()
    ROOT_LOGGER.setLevel(float('inf'))


class NullLogger(object):
    def __getattr__(self, attr):
        if attr.upper() in LOG_LEVELS:
            return lambda *args, **kwargs: None

########NEW FILE########
__FILENAME__ = async
# -*- coding: utf-8 -*-

from zenqueue.queue.common import AbstractQueue
from zenqueue.utils.async import Semaphore


Queue = AbstractQueue.with_semaphore_class(Semaphore)
########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-

from collections import deque


class AbstractQueue(object):
    
    semaphore_class = None
    
    class Timeout(Exception):
        pass
    
    def __init__(self, initial=None):
        self.queue = deque(initial or [])
        self.semaphore = self.semaphore_class(initial=0)
    
    def pull(self, timeout=None):
        try:
            self.semaphore.acquire(timeout=timeout)
        except self.semaphore.Timeout:
            raise self.Timeout
        return self.queue.pop()
    
    def pull_many(self, n, timeout=None):
        
        # Shortcut for null consumers.
        if n is None and timeout is None:
            while True:
                self.pull()
        
        # If n is None, iterate indefinitely, otherwise n times.
        if n is None:
            gen = eternal(True)
        else:
            gen = xrange(n)
        
        # Pull either n or infinity items from the queue until timeout.
        results = []
        
        for i in gen:
            try:
                results.append(self.pull(timeout=timeout))
            except self.Timeout:
                if not results:
                    raise
        
        return results
    
    def push(self, value):
        # Add it to the inner queue. appendleft() is used because pop() removes
        # from the right.
        self.queue.appendleft(value)
        
        # If coroutines are waiting for items to be available, then this will
        # notify the first of these that there is at least one item on the
        # queue.
        self.semaphore.release()
    
    def push_many(self, *values):
        for value in values:
            self.push(value)
    
    @classmethod
    def with_semaphore_class(cls, semaphore_class):
        return type('Queue', (cls,), {'semaphore_class': semaphore_class})


def eternal(item):
    while True:
        yield item
########NEW FILE########
__FILENAME__ = sync
# -*- coding: utf-8 -*-

from zenqueue.queue.common import AbstractQueue
from zenqueue.utils.sync import Semaphore


Queue = AbstractQueue.with_semaphore_class(Semaphore)
########NEW FILE########
__FILENAME__ = http
# -*- coding: utf-8 -*-

import optparse
import random
import re

from eventlet import api
from eventlet import wsgi

from werkzeug import Request, Response
from werkzeug import exceptions
from werkzeug.routing import Map, Rule

from zenqueue import json
from zenqueue import log
from zenqueue.queue import Queue
import zenqueue


DEFAULT_MAX_CONC_REQUESTS = 1024


# Option parser setup (for command-line usage)

USAGE = 'Usage: %prog [-i IFACE] [-p PORT] [-c NUM] [-l LEVEL]'
OPTION_PARSER = optparse.OptionParser(prog='python -m zenqueue.server.http',
    usage=USAGE, version=zenqueue.__version__)
OPTION_PARSER.add_option('-i', '--interface', default='0.0.0.0',
    help='Bind to interface IFACE [default %default]', metavar='IFACE')
OPTION_PARSER.add_option('-p', '--port', type='int', default=3080,
    help='Run on port PORT [default %default]', metavar='PORT')
OPTION_PARSER.add_option('-c', '--max-connections', type='int', dest='max_size',
    help='Allow maximum NUM concurrent requests [default %default]',
    metavar='NUM', default=DEFAULT_MAX_CONC_REQUESTS)
OPTION_PARSER.add_option('-l', '--log-level', dest='log_level', default='INFO',
    help='Use log level LEVEL [default %default] (use SILENT for no logging)',
    metavar='LEVEL')

# End option parser setup


URL_MAP = Map([
    Rule('/push/', endpoint='push'),
    Rule('/pull/', endpoint='pull'),
    Rule('/push_many/', endpoint='push_many'),
    Rule('/pull_many/', endpoint='pull_many'),
])


class JSONResponse(Response):
    
    def __new__(cls, obj, status=200):
        return Response(response=json.dumps(obj), mimetype='application/json',
            status=status)


class HTTPQueueServer(object):
    
    def __init__(self, queue=None):
        self.log = log.get_logger('zenq.server.http:%x' % (id(self),))
        self.queue = queue or Queue()
    
    def unpack_args(self, data):
        self.log.debug('Data received: %r', data)
        
        args, kwargs = (), {}
        if data:
            parsed = json.loads(data)
            if len(parsed) > 0:
                args = parsed[0]
            if len(parsed) > 1:
                kwargs = parsed[1]
        
        # Convert unicode strings to byte strings.
        for key in kwargs.keys():
            kwargs[str(key)] = kwargs.pop(key)
        
        return args, kwargs
    
    def __call__(self, request):
        
        adapter = URL_MAP.bind_to_environ(request.environ)
        client_id = '%0.6x' % (random.randint(1, 16777215),)
        
        try:
            endpoint, values = adapter.match()
            action = 'do_' + endpoint
            
            # Parse arguments and keyword arguments from request data.
            try:
                args, kwargs = self.unpack_args(request.data)
            except ValueError:
                self.log.error('Received malformed request from client %s',
                    client_id)
                return JSONResponse(['error:request', 'malformed request'],
                    status=400) # Bad Request
        
            # Find the method corresponding to the requested action.
            try:
                method = getattr(self, action)
            except AttributeError:
                self.log.error('Missing action requested by client %s',
                    client_id)
                return JSONResponse(['error:request', 'action not found'],
                    status=404) # Not Found
            
            # Run the method, dealing with exceptions or success.
            try:
                self.log.debug('Action %r requested by client %s',
                    action, client_id)
                output = method(*args, **kwargs)
            except self.queue.Timeout:
                # The client will pick this up. It's not so much a
                # serious error, which is why we don't log it: timeouts
                # are more often than not specified for very useful
                # reasons.
                return JSONResponse(['error:timeout', None])
            except Exception, exc:
                self.log.error(
                    'Action %r raised error %r for client %s',
                    action, exc, client_id)
                return JSONResponse(['error:action', repr(exc)], status=500)
            else:
                # I guess debug is overkill.
                self.log.debug('Action %r successful for client %s',
                    action, client_id)
                return JSONResponse(['success', output])
        except Exception, exc:
            self.log.error('Unknown error occurred for client %s: %r',
                client_id, exc)
            # If we really don't know what happened, return a generic 500.
            return JSONResponse(['error:unknown', repr(exc)], status=500)
        except exceptions.HTTPException, exc:
            return exc
    
    def serve(self, interface='0.0.0.0', port=3080,
        max_size=DEFAULT_MAX_CONC_REQUESTS):
        
        self.log.info('ZenQueue HTTP Server v%s', zenqueue.__version__)
        if interface == '0.0.0.0':
            self.log.info('Serving on %s:%d (all interfaces)', interface, port)
        else:
            self.log.info('Serving on %s:%d', interface, port)
        
        self.sock = api.tcp_listener((interface, port))
        
        try:
            # Wrap `self` with `Request.application` so that we get a request as
            # an argument instead of the usual `environ, start_response`.
            wsgi.server(self.sock, Request.application(self), max_size=max_size)
        finally:
            self.sock = None
    
    def do_push(self, value):
        self.queue.push(value)
    
    def do_pull(self, timeout=None):
        return self.queue.pull(timeout=timeout)
    
    def do_push_many(self, *values):
        self.queue.push_many(*values)
    
    def do_pull_many(self, n, timeout=None):
        return self.queue.pull_many(n, timeout=timeout)


def _main():
    options, args = OPTION_PARSER.parse_args()
    
    # Handle log level.
    log_level = options.log_level
    if log_level.upper() == 'SILENT':
        # Completely disables logging output.
        log.silence()
    elif log_level.upper() not in log.LOG_LEVELS:
        log.ROOT_LOGGER.warning(
            'Invalid log level supplied, defaulting to INFO')
        log.ROOT_LOGGER.setLevel(log.INFO)
    else:
        log.ROOT_LOGGER.setLevel(getattr(log, log_level.upper()))
    
    # Instantiate and start server.
    server = HTTPQueueServer()
    server.serve(interface=options.interface, port=options.port,
                 max_size=options.max_size)


if __name__ == '__main__':
    _main()
########NEW FILE########
__FILENAME__ = native
# -*- coding: utf-8 -*-

import errno
import optparse
import socket
import sys

from eventlet import api
from eventlet import coros

from zenqueue import json
from zenqueue import log
from zenqueue.queue import Queue
import zenqueue


DEFAULT_MAX_CONC_REQUESTS = 1024


# Option parser setup (for command-line usage)

USAGE = 'Usage: %prog [-i IFACE] [-p PORT] [-c NUM] [-l LEVEL]'
OPTION_PARSER = optparse.OptionParser(prog='python -m zenqueue.server.native',
    usage=USAGE, version=zenqueue.__version__)
OPTION_PARSER.add_option('-i', '--interface', default='0.0.0.0',
    help='Bind to interface IFACE [default %default]', metavar='IFACE')
OPTION_PARSER.add_option('-p', '--port', type='int', default=3000,
    help='Run on port PORT [default %default]', metavar='PORT')
OPTION_PARSER.add_option('-c', '--max-connections', type='int', dest='max_size',
    help='Allow maximum NUM concurrent requests [default %default]',
    metavar='NUM', default=DEFAULT_MAX_CONC_REQUESTS)
OPTION_PARSER.add_option('-l', '--log-level', dest='log_level', default='INFO',
    help='Use log level LEVEL [default %default] (use SILENT for no logging)',
    metavar='LEVEL')

# End option parser setup


# These exception definitions, while empty, allow code higher up the call chain
# to identify the nature of an error. Break, for example, is more of a signal
# than an error.
class ActionError(Exception): pass
class Break(Exception): pass


class NativeQueueServer(object):
    
    def __init__(self, queue=None, max_size=DEFAULT_MAX_CONC_REQUESTS):
        
        self.log = log.get_logger('zenq.server.native:%x' % (id(self),))
        
        # An initial queue may be provided; this might help with durable queues
        # (i.e. those that save their state to disk and can restore it on load).
        self.queue = queue or Queue()
        
        # The client pool is a pool of coroutines which doesn't allow more than
        # max_size coroutines to be running 'at the same time' (although
        # strictly speaking they never do anyway). In this case it represents
        # the maximum number of clients that may be connected at once.
        self.client_pool = coros.CoroutinePool(max_size=max_size)
        
        self.socket = None
    
    def serve(self, interface='0.0.0.0', port=3000):
        
        self.log.info('ZenQueue Native Server v%s', zenqueue.__version__)
        if interface == '0.0.0.0':
            self.log.info('Serving on %s:%d (all interfaces)', interface, port)
        else:
            self.log.info('Serving on %s:%d', interface, port)
        
        self.socket = api.tcp_listener((interface, port))
        
        # A lot of the code below was copied or adapted from eventlet's
        # implementation of an asynchronous WSGI server.
        try:
            while True:
                try:
                    try:
                        client_socket, client_addr = self.socket.accept()
                    except socket.error, exc:
                        # EPIPE (Broken Pipe) and EBADF (Bad File Descriptor)
                        # errors are common for clients that suddenly quit. We
                        # shouldn't worry so much about them.
                        if exc[0] not in [errno.EPIPE, errno.EBADF]:
                            raise
                    # Throughout the logging output, we use the client's ID in
                    # hexadecimal to identify a particular client in the logs.
                    self.log.info('Client %x connected: %r',
                        id(client_socket), client_addr)
                    # Handle this client on the pool, sleeping for 0 time to
                    # allow the handler (or other coroutines) to run.
                    self.client_pool.execute_async(self.handle, client_socket)
                    api.sleep(0)
                
                except KeyboardInterrupt:
                    # It's a fatal error because it kills the program.
                    self.log.fatal('Received keyboard interrupt.')
                    # This removes the socket from the current hub's list of
                    # sockets to check for clients (i.e. the select() call).
                    # select() is a key component of asynchronous networking.
                    api.get_hub().remove_descriptor(self.socket.fileno())
                    break
        finally:
            try:
                self.log.info('Shutting down server.')
                self.socket.close()
            except socket.error, exc:
                # See above for why we shouldn't worry about Broken Pipe or Bad
                # File Descriptor errors.
                if exc[0] not in [errno.EPIPE, errno.EBADF]:
                    raise
            finally:
                self.socket = None
    
    @staticmethod
    def parse_command(line):
        command = json.loads(line)
        
        # The specification for commands is really simple. Essentially they
        # consist of lists:
        #     ['action_name', ['arg1', 'arg2'], {'key': 'value'}]
        # The protocol is surprisingly close to Remote Procedure Call (RPC).
        action, args, kwargs = command[0], (), {}
        if len(command) > 1:
            args = command[1]
        if len(command) > 2:
            kwargs = command[2]
        
        # Convert unicode strings to byte strings.
        for key in kwargs.keys():
            kwargs[str(key)] = kwargs.pop(key)
        
        return action, args, kwargs
    
    def handle(self, client):
        reader, writer = client.makefile('r'), client.makefile('w')
        
        try:
            while True:
                try:
                    # If the client sends an empty line, ignore it.
                    line = reader.readline()
                    stripped_line = line.rstrip('\r\n')
                    if not line:
                        break
                    elif not stripped_line:
                        api.sleep(0)
                        continue
                
                    # Try to parse the request, failing if it is invalid.
                    try:
                        action, args, kwargs = self.parse_command(stripped_line)
                    except ValueError:
                        # Request was malformed. ValueError is raised by
                        # simplejson when the passed string is not valid JSON.
                        self.log.error('Received malformed request from client %x',
                            id(client))
                        write_json(writer, ['error:request', 'malformed request'])
                        continue
                
                    # Find the method corresponding to the requested action.
                    try:
                        method = getattr(self, 'do_' + action)
                    except AttributeError:
                        self.log.error('Missing action requested by client %x',
                            id(client))
                        write_json(writer, ['error:request', 'action not found'])
                        continue
                
                    # Run the method, dealing with exceptions or success.
                    try:
                        self.log.debug('Action %r requested by client %x',
                            action, id(client))
                        # All actions get the client socket as an additional
                        # argument. This means they can do cool things with the
                        # client object that might not be possible otherwise.
                        output = method(client, *args, **kwargs)
                    except Break:
                        # The Break error propagates up the call chain and
                        # causes the server to disconnect the client.
                        break
                    except self.queue.Timeout:
                        # The client will pick this up. It's not so much a
                        # serious error, which is why we don't log it: timeouts
                        # are more often than not specified for very useful
                        # reasons.
                        write_json(writer, ['error:timeout', None])
                    except Exception, exc:
                        self.log.error(
                            'Action %r raised error %r for client %x',
                            action, exc, id(client))
                        write_json(writer, ['error:action', repr(exc)])
                        # Chances are that if an error occurred, we'll need to
                        # raise it properly. This will trigger the closing of
                        # the client socket via the finally clause below.
                        raise ActionError(exc)
                    else:
                        # I guess debug is overkill.
                        self.log.debug('Action %r successful for client %x',
                            action, id(client))
                        write_json(writer, ['success', output])
                except ActionError, exc:
                    # Raise the inner action error. This will prevent the
                    # catch-all except statement below from logging action
                    # errors as 'unknown' errors. The exception has already been
                    # written to the client.
                    raise ActionError.args[0]
                except Exception, exc:
                    self.log.error('Unknown error occurred for client %x: %r',
                        id(client), exc)
                    # If we really don't know what happened, then
                    write_json(writer, ['error:unknown', repr(exc)])
                    raise # Raises the last exception, in this case exc.
        except:
            # If any exception has been raised at this point, it will show up as
            # an error in the logging output.
            self.log.error('Forcing disconnection of client %x', id(client))
        finally:
            # If code reaches this point simply by non-error means (i.e. an
            # actual call to the quit, exit or shutdown actions), then it will
            # not include an error-level logging event.
            self.log.info('Client %x disconnected', id(client))
            client.close()
    
    # Most of these methods are pure wrappers around the underlying queue
    # object.
    
    def do_push(self, client, value):
        self.queue.push(value)
    
    def do_pull(self, client, timeout=None):
        # Timeouts will propagate upwards to the client loop and be handled
        # accordingly.
        return self.queue.pull(timeout=timeout)
    
    def do_push_many(self, client, *values):
        self.queue.push_many(*values)
    
    def do_pull_many(self, client, n, timeout=None):
        # Timeouts will propagate upwards to the client loop and be handled
        # accordingly.
        return self.queue.pull_many(n, timeout=timeout)
    
    def do_quit(self, client):
        client.shutdown(socket.SHUT_RDWR)
        # This will be caught and cause the client loop to break, essentially
        # closing the client's connection.
        raise Break
    # exit and shutdown are synonyms for quit.
    do_exit = do_shutdown = do_quit


def write_json(writer, object):
    # A simple utility method.
    writer.write(json.dumps(object) + '\r\n')


def _main():
    options, args = OPTION_PARSER.parse_args()
    
    # Handle log level.
    log_level = options.log_level
    if log_level.upper() == 'SILENT':
        # Completely disables logging output.
        log.silence()
    elif log_level.upper() not in log.LOG_LEVELS:
        log.ROOT_LOGGER.warning(
            'Invalid log level supplied, defaulting to INFO')
        log.ROOT_LOGGER.setLevel(log.INFO)
    else:
        log.ROOT_LOGGER.setLevel(getattr(log, log_level.upper()))
    
    # Instantiate and start server.
    server = NativeQueueServer(max_size=options.max_size)
    server.serve(interface=options.interface, port=options.port)


if __name__ == '__main__':
    _main()
########NEW FILE########
__FILENAME__ = async
# -*- coding: utf-8 -*-

from collections import deque

from eventlet import api
from eventlet import coros


class DummyTimer(object):
    def cancel(self):
        pass


class Semaphore(object):
    
    """
    A direct translation of the semaphore to coroutine-based programming.
    
    The Semaphore is a synchronization technique that can be used by a number
    of coroutines at once. The mechanism of its function is that it holds a
    count in memory which is set to an initial value. Every time a coroutine
    acquire()s the semaphore, this count is decreased by one, and every
    release() increases the count. If a coroutine attempts to acquire() a
    semaphore with a count of zero, the coroutine will yield until another
    coroutine release()s it.
    """
    
    class WaitCancelled(Exception): pass
    class Timeout(Exception): pass
    
    def __init__(self, initial=0):
        self.coro_queue = deque()
        self.__count = initial
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, *exc_info):
        self.release()
        return False
    
    def acquire(self, timeout=None):
        
        if self.__count <= 0:
            ready_event = coros.event()
            self.coro_queue.appendleft(ready_event)
            
            timer = DummyTimer()
            if timeout is not None:
                timer = api.exc_after(timeout, self.Timeout)
            
            try:
                result = ready_event.wait()
            except self.Timeout:
                if ready_event in self.coro_queue:
                    self.coro_queue.remove(ready_event)
                raise
            else:
                timer.cancel()
                
            if not result:
                raise self.WaitCancelled
        
        self.__count -= 1
    
    def release(self):
        self.__count += 1
    
        if self.coro_queue:
            ready_event = self.coro_queue.pop()
            ready_event.send(True)
            api.sleep(0)
    
    def cancel_all(self):
        while self.coro_queue:
            ready_event = self.coro_queue.pop()
            ready_event.send(False)
        api.sleep(0)
    
    @property
    def count(self):
        return self.__count


class Lock(Semaphore):
    
    def __init__(self):
        super(Lock, self).__init__(initial=1)
    
    @property
    def in_use(self):
        return (self.count == 0)


def callcc(function):
    def continuation_generator():
        val = yield
        yield
        yield val
    continuation = continuation_generator()
    continuation.next()
    def callback(value):
        continuation.send(value)
    function(callback)
    return continuation.next()
########NEW FILE########
__FILENAME__ = sync
# -*- coding: utf-8 -*-

from collections import deque
from functools import wraps

import threading


def with_lock(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        self._lock.acquire()
        try:
            return method(self, *args, **kwargs)
        finally:
            self._lock.release()
    return wrapper


class Event(object):
    
    """An event which allows values to be sent."""
    
    class WaitCancelled(Exception): pass
    class Timeout(Exception): pass
    
    def __init__(self):
        self._lock = threading.Lock()
        self._waiters = {}
        self._result = None
    
    @with_lock
    def send(self, value=True):
        self._result = value
        
        for waiter in self._waiters.keys():
            self._waiters[waiter][1] = True
            self._waiters[waiter][0].set()
    
    @with_lock
    def cancel_all(self):
        for waiter in self._waiters.keys():
            self.cancel(waiter)
    
    @with_lock
    def cancel(self, thread):
        if thread in self._waiters:
            self._waiters[thread][1] = False
            self._waiters[thread][0].set()
    
    def wait(self, timeout=None):
        event = threading.Event()
        self._waiters[threading.currentThread()] = [event, None]
        
        # A timeout of None implies eternal blocking.
        if timeout is not None:
            event.wait(timeout)
        else:
            event.wait()
        
        status = self._waiters.pop(threading.currentThread())[1]
        
        if not event.isSet():
            raise self.Timeout
        
        if status:
            return self._result
        raise self.WaitCancelled


class Semaphore(object):
    
    """A semaphore with queueing which records the threads which acquire it."""
    
    class WaitCancelled(Exception): pass
    class Timeout(Exception): pass
    
    def __init__(self, initial=0):
        self.evt_queue = deque()
        self._lock = threading.Lock()
        self.__count = initial
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, *exc_info):
        self.release()
        return False
    
    def acquire(self, timeout=None):
        
        if self.__count <= 0:
            ready_event = Event()
            self.evt_queue.appendleft(ready_event)
            
            try:
                result = ready_event.wait(timeout=timeout)
            except ready_event.Timeout:
                if ready_event in self.evt_queue:
                    self.evt_queue.remove(ready_event)
                raise self.Timeout
            except ready_event.WaitCancelled:
                if ready_event in self.evt_queue:
                    self.evt_queue.remove(ready_event)
                raise self.WaitCancelled
        
        self.__count -= 1
    
    def release(self):
        self.__count += 1
    
        if self.evt_queue:
            ready_event = self.evt_queue.pop()
            ready_event.send(True)
    
    @with_lock
    def cancel_all(self):
        while self.evt_queue:
            ready_event = self.evt_queue.pop()
            ready_event.cancel_all()
    
    @property
    def count(self):
        return self.__count


class Lock(Semaphore):
    
    def __init__(self):
        super(Lock, self).__init__(initial=1)
    
    @property
    def in_use(self):
        return (self.count == 0)
########NEW FILE########
