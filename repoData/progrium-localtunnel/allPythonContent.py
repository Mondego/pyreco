__FILENAME__ = client
import argparse
import uuid
import sys
import socket

import eventlet
import eventlet.event
import eventlet.greenpool

from localtunnel import util
from localtunnel import protocol
from localtunnel import __version__

def open_proxy_backend(backend, target, name, client, use_ssl=False, ssl_opts=None):
    proxy = eventlet.connect(backend)
    if use_ssl:
        ssl_opts = ssl_opts or {}
        proxy = eventlet.wrap_ssl(proxy, server_side=False, **ssl_opts)
    proxy.sendall(protocol.version)
    protocol.send_message(proxy,
        protocol.proxy_request(
            name=name,
            client=client,
    ))
    reply = protocol.recv_message(proxy)
    if reply and 'proxy' in reply:
        try:
            local = eventlet.connect(target)
            util.join_sockets(proxy, local)
        except IOError:
            proxy.close()
    elif reply and 'error' in reply:
        print "  ERROR: {0}".format(reply['error'])
        return
    else:
        pass

def start_client(**kwargs):
    host = kwargs['host']
    backend_port = kwargs.get('backend_port')
    use_ssl = kwargs.get('use_ssl', False)
    ssl_opts = kwargs.get('ssl_opts', {})

    if not backend_port:
        try:
            backend_port = util.discover_backend_port(host)
        except:
            print "  ERROR: Unable to connect to service."
            sys.exit(0)

    frontend_ip = socket.gethostbyname(host.split(':')[0])
    frontend_address, frontend_hostname = util.parse_address(host,
            default_ip=frontend_ip)
    backend = (frontend_address[0], backend_port)

    name = kwargs['name']

    client = util.client_name()
    target = util.parse_address(kwargs['target'])[0]
    try:
        control = eventlet.connect(backend)
        if use_ssl:
            control = eventlet.wrap_ssl(control, server_side=False, **ssl_opts)
        control.sendall(protocol.version)
        protocol.send_message(control,
            protocol.control_request(
                name=name,
                client=client,
        ))
        reply = protocol.recv_message(control)
        if reply and 'control' in reply:
            reply = reply['control']

            def maintain_proxy_backend_pool():
                pool = eventlet.greenpool.GreenPool(reply['concurrency'])
                while True:
                    pool.spawn_n(open_proxy_backend,
                            backend, target, name, client, use_ssl, ssl_opts)
            proxying = eventlet.spawn(maintain_proxy_backend_pool)

            print "  {0}".format(reply['banner'])
            print "  Port {0} is now accessible from http://{1} ...\n".format(
                    target[1], reply['host'])

            try:
                while True:
                    message = protocol.recv_message(control)
                    assert message == protocol.control_ping()
                    protocol.send_message(control, protocol.control_pong())
            except (IOError, AssertionError):
                proxying.kill()

        elif reply and 'error' in reply:
            print "  ERROR: {0}".format(reply['message'])
        else:
            print "  ERROR: Unexpected server reply."
            print "         Make sure you have the latest version of the client."
    except KeyboardInterrupt:
        pass

def run():
    parser = argparse.ArgumentParser(
                description='Open a public HTTP tunnel to a local server')
    parser.add_argument('-s', dest='host', metavar='address',
                default='v2.localtunnel.com',
                help='localtunnel server address (default: v2.localtunnel.com)')
    parser.add_argument('--version', action='store_true',
                help='show version information for client and server')
    parser.add_argument('-m', action='store_true',
                help='show server metrics and exit')


    if '--version' in sys.argv:
        args = parser.parse_args()
        print "client: {}".format(__version__)
        try:
            server_version = util.lookup_server_version(args.host)
        except:
            server_version = '??'
        print "server: {} ({})".format(server_version, args.host)
        sys.exit(0)
    elif '-m' in sys.argv:
        args = parser.parse_args()
        util.print_server_metrics(args.host)
        sys.exit(0)

    parser.add_argument('-n', dest='name', metavar='name',
                default=str(uuid.uuid4()).split('-')[-1],
                help='name of the tunnel (default: randomly generate)')
    parser.add_argument('-c', dest='concurrency', type=int,
                metavar='concurrency', default=3,
                help='number of concurrent backend connections')
    parser.add_argument('target', metavar='target', type=str,
                help='local target port or address of server to tunnel to')
    args = parser.parse_args()


    start_client(**vars(args))


if __name__ == '__main__':
	run()


########NEW FILE########
__FILENAME__ = meta
import json
import os
# Some environments require these extra imports due to
# eventlet's monkey patching code.
import SocketServer
import httplib
import ftplib
import urllib
import BaseHTTPServer

from eventlet.wsgi import Server

from localtunnel import __version__
from localtunnel.server.tunnel import Tunnel
from localtunnel.server import metrics

def root(environ, start_response):
    if environ['PATH_INFO'].startswith('/meta'):
        return meta(environ, start_response)
    else:
        start_response('200 OK', {})
        return [""]

def meta(environ, start_response):
    path = environ['PATH_INFO']
    start_response('200 OK', {})
    if path.startswith('/meta/version'):
        return [str(__version__)]
    elif path.startswith('/meta/backend'):
        return [str(os.environ.get('DOTCLOUD_SERVER_BACKEND_PORT', 
            Tunnel.backend_port))]
    elif path.startswith('/meta/metrics'):
        return [json.dumps(metrics.dump_metrics(),
            sort_keys=True, indent=2, separators=(',', ': '))]



server = Server(None, None, root)

########NEW FILE########
__FILENAME__ = protocol
import struct
import json

version = 'LTP/0.2'
errors = {
    'unavailable': "This tunnel name is unavailable",
    'expired': "This tunnel has expired",
}

# Initial protocol assertion

def assert_protocol(socket):
    protocol = socket.recv(len(version))
    assert protocol == version

# Message IO

def recv_message(socket):
    try:
        header = socket.recv(4)
        length = struct.unpack(">I", header)[0]
        data = socket.recv(length)
        message = json.loads(data)
        return message
    except:
        return

def send_message(socket, message):
    data = json.dumps(message)
    header = struct.pack(">I", len(data))
    socket.sendall(''.join([header, data]))

# Message types

def control_request(name, client, protect=None, domain=None):
    request = dict(name=name, client=client)
    if protect:
        request['protect'] = protect
    if domain:
        request['domain'] = domain
    return {'control': request}

def control_reply(host, concurrency, banner=None):
    reply = dict(host=host, concurrency=concurrency)
    if banner:
        reply['banner'] = banner
    return {'control': reply}

def control_ping():
    return {'control': 'ping'}

def control_pong():
    return {'control': 'pong'}

def proxy_request(name, client):
    return {'proxy': dict(name=name, client=client)}

def proxy_reply():
    return {'proxy': True}

def error_reply(error):
    if isinstance(error, BaseException):
        return dict(error='exception', message=str(error))
    else:
        assert error in errors
        return dict(error=error, message=errors[error])


########NEW FILE########
__FILENAME__ = backend
import json
import logging
import re

import eventlet
from eventlet.timeout import Timeout

from localtunnel.server.tunnel import Tunnel
from localtunnel import util
from localtunnel import protocol
from localtunnel import __version__
from localtunnel.server import metrics

HOST_TEMPLATE = "{0}.{1}"
BANNER = """Thanks for trying localtunnel v2 beta!
  Source code: https://github.com/progrium/localtunnel
  Donate: http://j.mp/donate-localtunnel
"""
HEARTBEAT_INTERVAL = 5

@metrics.meter_calls(name='backend_conn')
def connection_handler(socket, address):
    """ simple dispatcher for backend connections """
    try:
        protocol.assert_protocol(socket)
        message = protocol.recv_message(socket)
        if message and 'control' in message:
            handle_control_request(socket, message['control'])
        elif message and 'proxy' in message:
            handle_proxy_request(socket, message['proxy'])
        else:
            logging.debug("!backend: no request message, closing")
    except AssertionError:
        logging.debug("!backend: invalid protocol, closing")

@metrics.time_calls(name='control_conn')
def handle_control_request(socket, request):
    try:
        tunnel = Tunnel.get_by_control_request(request)
    except RuntimeError, e:
        protocol.send_message(socket, protocol.error_reply('notavailable'))
        socket.close()
        return
    protocol.send_message(socket, protocol.control_reply(
        host=HOST_TEMPLATE.format(tunnel.name, Tunnel.domain_suffix),
        banner=BANNER,
        concurrency=Tunnel.max_pool_size,
    ))
    logging.info("created tunnel:\"{0}\" by client:\"{1}\"".format(
            tunnel.name, tunnel.client))

    try:
        while True:
            eventlet.sleep(HEARTBEAT_INTERVAL)
            protocol.send_message(socket, protocol.control_ping())
            with Timeout(HEARTBEAT_INTERVAL):
                message = protocol.recv_message(socket)
                assert message == protocol.control_pong()
    except (IOError, AssertionError, Timeout):
        logging.debug("expiring tunnel:\"{0}\"".format(tunnel.name))
        tunnel.destroy()

@metrics.time_calls(name='proxy_conn')
def handle_proxy_request(socket, request):
    try:
        tunnel = Tunnel.get_by_proxy_request(request)
    except RuntimeError, e:
        protocol.send_message(socket, protocol.error_reply('notavailable'))
        socket.close()
        return
    if not tunnel:
        protocol.send_message(socket, protocol.error_reply('expired'))
        socket.close()
        return
    try:
        proxy_used = tunnel.add_proxy_conn(socket)
        logging.debug("added connection:\"{0}\" by client:\"{1}\"".format(
            tunnel.name, tunnel.client))
        pool = proxy_used.wait()
        pool.waitall()
    except ValueError, e:
        protocol.send_message(socket, protocol.error_reply(e))
        socket.close()
        logging.debug(str(e))

########NEW FILE########
__FILENAME__ = cli
import argparse
import logging
import os

import eventlet
import eventlet.debug
import eventlet.greenpool

from localtunnel.server.tunnel import Tunnel
from localtunnel import util
from localtunnel.server import backend
from localtunnel.server import frontend
from localtunnel.server import metrics

def run():
    eventlet.debug.hub_prevent_multiple_readers(False)
    eventlet.monkey_patch(socket=True)

    logging.basicConfig(
        format="%(asctime)s %(levelname) 7s %(module)s: %(message)s",
        level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Localtunnel server daemon')
    parser.add_argument('frontend', metavar='frontend_listener', type=str,
        help='hostname to run frontend on (default: vcap.me:8000)', 
        default='vcap.me:8000')
    parser.add_argument('backend', metavar='backend_listener', type=str,
        help='port or address to run backend server on (default: 8001)',
        default='8001')
    args = parser.parse_args()
    
    frontend_address, frontend_hostname = util.parse_address(args.frontend)
    backend_address, backend_hostname = util.parse_address(args.backend)

    logging.info("starting frontend on {0} for {1}...".format(
        frontend_address, frontend_hostname))
    logging.info("starting backend on {0}...".format(backend_address))
    
    Tunnel.backend_port = backend_address[1]
    if frontend_address[1] == 80:
        Tunnel.domain_suffix = frontend_hostname
    else:
        Tunnel.domain_suffix = ":".join(
            [frontend_hostname, str(frontend_address[1])])
    
    stats_key = os.environ.get('STATHAT_EZKEY', None)
    if stats_key:
        metrics.run_reporter(stats_key)
    
    frontend_listener = eventlet.listen(frontend_address)
    backend_listener = eventlet.listen(backend_address)
    
    try:
        Tunnel.schedule_idle_scan()
        pool = eventlet.greenpool.GreenPool(size=2)
        pool.spawn_n(eventlet.serve, frontend_listener,
                frontend.connection_handler)
        pool.spawn_n(eventlet.serve, backend_listener,
                backend.connection_handler)
        pool.waitall()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
	run()


########NEW FILE########
__FILENAME__ = frontend
import json
import logging
import re
import os
from socket import MSG_PEEK

from localtunnel.server.tunnel import Tunnel
from localtunnel import util
from localtunnel import meta
from localtunnel import protocol
from localtunnel.server import metrics


def peek_http_host(socket):
    hostheader = re.compile('(^|\r\n)host: ([^\(\);,<>]+?)\r\n', re.I)
    # Peek up to 2048 bytes into data for the Host header
    for n in [128, 256, 512, 1024, 2048, 4096, 8192, 16384]:
        bytes = socket.recv(n, MSG_PEEK)
        if not bytes:
            break
        match = hostheader.search(bytes)
        if match:
            return match.group(2)


def send_http_error(socket, content, status=None):
    status = status or '500 Internal Error'
    data =  """HTTP/1.1 {0}\r\nContent-Length: {1}\r\nConnection: close\r\n\r\n{2}
            """.format(status, len(str(content)), content).strip()
    socket.sendall(data)
    socket.close()
    logging.debug("!{0}".format(content.lower()))


@metrics.time_calls(name='frontend_conn')
def connection_handler(socket, address):
    hostname = peek_http_host(socket)
    if not hostname:
        send_http_error(socket, 'No hostname', '400 Bad Request')
        return

    if hostname == Tunnel.domain_suffix:
        meta.server.process_request((socket, address))
        return

    tunnel = Tunnel.get_by_hostname(hostname)
    if not tunnel:
        send_http_error(socket, 'No tunnel for {0}'.format(hostname), '410 Gone')
        return

    conn, proxy_used = tunnel.pop_proxy_conn(timeout=2)
    if not conn:
        send_http_error(socket, 'No proxy connections', '502 Bad Gateway')
        return

    protocol.send_message(conn, protocol.proxy_reply())
    pool = util.join_sockets(conn, socket)
    proxy_used.send(pool)
    logging.debug("popped connection:\"{0}\" for frontend:\"{1}\"".format(
                tunnel.name, hostname))
    pool.waitall()

########NEW FILE########
__FILENAME__ = metrics
import logging

import requests
import eventlet

from yunomi import dump_metrics
from yunomi import counter
from yunomi import *

requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

report_interval = 30
monitored_metrics = """
total_tunnel_count
collect:darwin_count
collect:linux_count
collect:windows_count
idle_tunnel_count
control_conn_avg
frontend_conn_5m_rate
""".split("\n")[1:-1]

class StatHat(object):
    """The StatHat API wrapper."""
    STATHAT_URL = 'http://api.stathat.com'

    def __init__(self, key=None, prefix=None):
        self.key = key
        self.prefix = prefix or ''
        # Enable keep-alive and connection-pooling.
        self.session = requests.session()

    def _http_post(self, path, data):
        url = self.STATHAT_URL + path
        r = self.session.post(url, data=data, prefetch=True)
        return r

    def value(self, name, value):
        r = self._http_post('/ez', {
            'ezkey': self.key, 
            'stat': ''.join([self.prefix, name]), 
            'value': value})
        return r.ok

    def count(self, name, count):
        r = self._http_post('/ez', {
            'ezkey': self.key, 
            'stat': ''.join([self.prefix, name]), 
            'count': count})
        return r.ok

def run_reporter(stats_key):
    stats = StatHat(stats_key, 'localtunnel.')
    logging.info("starting metrics reporter with {0}".format(stats_key))
    def _report_stats():
        dump = {}
        for m in dump_metrics():
            dump[m['name']] = m['value']
        for metric in monitored_metrics:
            value = dump.get(metric)
            if value:
                if metric.startswith('collect:'):
                    # metrics starting with "collect:" are
                    # counters that will be reset once reported
                    stats.count(metric.split(':')[-1], value)
                    metric_name = metric.split('_count')[0]
                    counter(metric_name).clear()
                else:
                    stats.value(metric, value)
        logging.debug("metrics reported")
        eventlet.spawn_after(report_interval, _report_stats)
    eventlet.spawn_after(report_interval, _report_stats)



########NEW FILE########
__FILENAME__ = tunnel
import json
import re
import time
import logging

import eventlet
import eventlet.event
import eventlet.timeout
import eventlet.semaphore

from localtunnel.server import metrics

class Tunnel(object):
    max_pool_size = 3
    domain_suffix = None
    backend_port = None
    active_timeout = 5 * 60
    create_callback = None
    destroy_callback = None

    _tunnels = {}

    def __init__(self, name, client, protect=None, domain=None):
        self.name = name
        self.client = client
        if protect:
            user, passwd = protect.split(':')
            self.protect_user = user
            self.protect_passwd = passwd
            self.protect = True
        else:
            self.protect = False
        self.domain = domain
        self.created = time.time()
        self.updated = time.time()
        self.idle = False
        self.proxy_pool = []
        self.pool_semaphore = eventlet.semaphore.Semaphore(0)

        metrics.counter('total_tunnel').inc()
        platform = self.client.split(';', 1)[-1].lower()
        metrics.counter('collect:{0}'.format(platform)).inc()

    def add_proxy_conn(self, socket):
        pool_size = len(self.proxy_pool)
        if pool_size < Tunnel.max_pool_size:
            used = eventlet.event.Event()
            self.proxy_pool.append((socket, used))
            self.pool_semaphore.release()
            self.updated = time.time()
            self.idle = False
            return used
        else:
            raise ValueError("backend:\"{0}\" pool is full".format(
                    self.name))

    def pop_proxy_conn(self, timeout=None):
        with eventlet.timeout.Timeout(timeout, False):
            self.pool_semaphore.acquire()
        if not len(self.proxy_pool):
            return None, None
        return self.proxy_pool.pop()

    def destroy(self):
        cls = self.__class__
        for conn, _ in self.proxy_pool:
            conn.close()
        if self == cls._tunnels[self.name]:
            cls._tunnels.pop(self.name, None)
        metrics.counter('total_tunnel').dec()

        if cls.destroy_callback:
            cls.destroy_callback(self)


    @classmethod
    def create(cls, obj):
        tunnel = cls(**obj)
        cls._tunnels[tunnel.name] = tunnel

        if cls.create_callback:
            cls.create_callback(tunnel)

        return tunnel

    @classmethod
    def get_by_hostname(cls, hostname):
        if not hostname.endswith(Tunnel.domain_suffix):
            return
        match = re.match('(.+?\.|)(\w+)\.$', hostname[:-len(Tunnel.domain_suffix)])
        if match:
            return cls._tunnels.get(match.group(2))

    @classmethod
    def get_by_control_request(cls, request):
        if request['name'] in cls._tunnels:
            tunnel = cls._tunnels[request['name']]
            if tunnel.client != request['client']:
                raise RuntimeError("Tunnel name '{0}' is being used".format(
                        tunnel.name))
            else:
                tunnel.destroy()
        return cls.create(request)

    @classmethod
    def get_by_proxy_request(cls, request):
        if request['name'] in cls._tunnels:
            tunnel = cls._tunnels[request['name']]
            if tunnel.client != request['client']:
                raise RuntimeError("Tunnel name '{0}' is being used".format(
                        tunnel.name))
            return tunnel

    @classmethod
    def schedule_idle_scan(cls):
        def _scan_idle():
            counter = metrics.counter('idle_tunnel')
            counter.clear()
            for name, tunnel in cls._tunnels.iteritems():
                if time.time() - tunnel.updated > cls.active_timeout:
                    tunnel.idle = True
                    counter.inc()
            if counter.get_count():
                logging.debug("scan: {0} of {1} tunnels are idle".format(
                    counter.get_value(), len(cls._tunnels)))
            cls.schedule_idle_scan()
        eventlet.spawn_after(cls.active_timeout, _scan_idle)


########NEW FILE########
__FILENAME__ = util
import json
import getpass
import socket
import urllib2
import urlparse
import platform

import eventlet
import eventlet.greenpool

import requests

def join_sockets(a, b):
    """ socket joining implementation """
    def _pipe(from_, to):
        while True:
            try:
                data = from_.recv(64 * 1024)
                if not data:
                    break
                try:
                    to.sendall(data)
                except:
                    from_.close()
                    break
            except:
                break
        try:
            to.close()
        except: 
            pass
    pool = eventlet.greenpool.GreenPool(size=2)
    pool.spawn_n(_pipe, a, b)
    pool.spawn_n(_pipe, b, a)
    return pool

def client_name():
    """ semi-unique client identifier string """
    return "{0}@{1};{2}".format(
        getpass.getuser(), 
        socket.gethostname(),
        platform.system())

def parse_address(address, default_port=None, default_ip=None):
    """ 
    returns address (ip, port) and hostname from anything like:
      localhost:8000
      8000
      :8000
      myhost:80
      0.0.0.0:8000
    """
    default_ip = default_ip or '0.0.0.0'
    try:
        # this is if address is simply a port number
        return (default_ip, int(address)), None
    except ValueError:
        parsed = urlparse.urlparse("tcp://{0}".format(address))
        try:
            if socket.gethostbyname(parsed.hostname) == parsed.hostname:
                # hostname is an IP
                return (parsed.hostname, parsed.port or default_port), None
        except socket.error:
            # likely, hostname is a domain name that can't be resolved
            pass
        # hostname is a domain name
        return (default_ip, parsed.port or default_port), parsed.hostname


def discover_backend_port(hostname, frontend_port=80):
    resp = requests.get('http://{0}/meta/backend'.format(hostname))
    if resp.status_code == 200:
        return int(resp.text)
    else:
        raise RuntimeError("Frontend failed to provide backend port")

def lookup_server_version(hostname):
    resp = requests.get('http://{0}/meta/version'.format(hostname))
    if resp.status_code == 200:
        return resp.text
    else:
        raise RuntimeError("Server failed to provide version")

def print_server_metrics(hostname):
    resp = requests.get('http://{0}/meta/metrics'.format(hostname))
    if resp.status_code == 200:
        for metric in resp.json:
            print "%(name) -40s %(value)s" % metric
    else:
        raise RuntimeError("Server failed to provide metrics")


########NEW FILE########
__FILENAME__ = test_frontend
import unittest
from localtunnel.server.frontend import peek_http_host


class Socket(object):
    def __init__(self, message):
        self.message = message

    def recv(self, length, flags):
        return self.message[0:length]


class TestFrontendPeek(unittest.TestCase):
    def _test(self, header, expected):
        actual = peek_http_host(Socket(header))
        self.assertEqual(actual, expected)

    def test_simple(self):
        self._test("Host: ABC\r\n", "ABC")
        self._test("Other: XX\r\nHost: ABC\r\n", "ABC")
        self._test("Other: XX\r\nHost: ABC\r\nMore: XX\r\n", "ABC")

    def test_without_newline(self):
        self._test("Host: ABC", None)

    def test_port(self):
        self._test("Host: ABC:8000\r\n", "ABC:8000")

    def test_peeking(self):
        # Make sure the first peek of 128 chars contains just `Host: A`
        header = "%s\r\nHost: ABC\r\n" % (" " * 119)
        self._test(header, "ABC")

        # Make sure the second peek of 256 chars contains just `Host: A`
        header = "%s\r\nHost: ABC\r\n" % (" " * 247)
        self._test(header, "ABC")

        # Make sure the third peek of 512 chars contains just `Host: A`
        header = "%s\r\nHost: ABC\r\n" % (" " * 503)
        self._test(header, "ABC")

########NEW FILE########
__FILENAME__ = test_tunnel
import unittest
from localtunnel.server.tunnel import Tunnel


class TestTunnel(unittest.TestCase):
    def test_get_by_hostname(self):
        Tunnel.domain_suffix = 'bar'
        tunnel = Tunnel.create(dict(name='foo', client='Test-Client'))
        self.assertTrue(Tunnel.get_by_hostname('foo.bar'))
        self.assertTrue(Tunnel.get_by_hostname('xxx.foo.bar'))
        self.assertFalse(Tunnel.get_by_hostname('foo.bar.bar'))
        tunnel.destroy()

        Tunnel.domain_suffix = 'foo.bar'
        tunnel = Tunnel.create(dict(name='hello', client='Test-Client'))
        self.assertTrue(Tunnel.get_by_hostname('hello.foo.bar'))
        self.assertTrue(Tunnel.get_by_hostname('world.hello.foo.bar'))
        self.assertFalse(Tunnel.get_by_hostname('foo.bar'))
        self.assertFalse(Tunnel.get_by_hostname('bar'))
        self.assertFalse(Tunnel.get_by_hostname('hello.world.foo.bar'))
        tunnel.destroy()

        Tunnel.domain_suffix = None

    def test_tunnel_callbacks(self):
        Tunnel.domain_suffix = 'bar'
        self.create_called = False
        self.destroy_called = False

        def create_callback(tunnel):
            self.assertEquals(tunnel.name, "foo")
            self.create_called = True

        def destroy_callback(tunnel):
            self.assertEquals(tunnel.name, "foo")
            self.destroy_called = True

        Tunnel.create_callback = create_callback
        Tunnel.destroy_callback = destroy_callback

        tunnel = Tunnel.create(dict(name='foo', client='Test-Client'))
        tunnel.destroy()

        self.assertTrue(self.create_called)
        self.assertTrue(self.destroy_called)

########NEW FILE########
