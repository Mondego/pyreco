__FILENAME__ = client
import sys
from socket import socket, gethostbyname
import logging
from commands import getoutput
from subprocess import call, check_call
import atexit

from myvpn.tun import Tun
from myvpn.utils import populate_common_argument_parser, proxy, get_platform
from myvpn.consts import MAGIC_WORD

logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    populate_common_argument_parser(parser)
    parser.add_argument('--server', required=True)
    parser.add_argument('--ip', default='192.168.5.2')
    parser.add_argument('--peer-ip', default='192.168.5.1')
    parser.add_argument('--default-gateway', action='store_true',
                        help="use vpn as default gateway")
    parser.add_argument('--up',
                        help="script to run at connection")
    parser.add_argument('--down',
                        help="script to run at connection closed")


def main(args):
    tun = Tun(device=args.device, ip=args.ip, peer_ip=args.peer_ip)
    tun.open()

    sock = socket()
    server_ip = gethostbyname(args.server)
    logger.info("%s resolved to %s", args.server, server_ip)

    try:
        sock.connect((server_ip, args.port))
        logger.info("connected to %s:%i" % (server_ip, args.port))
        sock.send(MAGIC_WORD)
        data = sock.recv(len(MAGIC_WORD))
        if data != MAGIC_WORD:
            logger.warning("Handshake failed")
            sys.exit(2)

        logger.info("Connection with %s:%i established" % (server_ip, args.port))

        gateway = get_default_gateway()

        if args.down:
            atexit.register(on_down, args.down,
                            server_ip=server_ip,
                            restore_gateway=gateway if args.default_gateway else None)

        call(['route', 'delete', server_ip+'/32'])
        check_call(['route', 'add', server_ip+'/32', gateway])

        if args.default_gateway:
            logger.info("set default gateway")
            call(['route', 'delete', 'default'])
            check_call(['route', 'add', 'default', args.peer_ip])

        if args.up:
            logger.info("Run up script")
            check_call(args.up)

        proxy(tun.fd, sock)

    except KeyboardInterrupt:
        logger.warning("Stopped by user")


def get_default_gateway():
    platform = get_platform()
    if platform == 'darwin':
        output = getoutput("netstat -nr | grep default | head -n1 | awk '{ print $2 }'")
        gateway = output.strip()
    else:
        output = getoutput("netstat -nr | grep -e '^0.0.0.0' | head -n1 | awk '{ print $2 }'")
        gateway = output.strip()
    return gateway


def on_down(script, server_ip, restore_gateway=None):
    if restore_gateway:
        logger.info("restore gateway to %s", restore_gateway)
        call(['route', 'delete', 'default'])
        call(['route', 'add', 'default', restore_gateway])

    call(['route', 'delete', server_ip+'/32'])

    logger.info("Run down script")
    call([script])

########NEW FILE########
__FILENAME__ = consts
DEFAULT_PORT = 2504
MAGIC_WORD = "Wazaaaaaaaaaaahhhh !"

########NEW FILE########
__FILENAME__ = http
import os
import time
from zlib import compress, decompress
from struct import pack, unpack
from argparse import ArgumentTypeError
from subprocess import call, check_call
from SocketServer import TCPServer, ThreadingMixIn, StreamRequestHandler
import logging
import urlparse
import socket
import threading
import errno
import atexit

from .tun import Tun
from .utils import get_platform, add_route, get_default_gateway, \
        restore_gateway

FAKE_HEAD = b'ID3\x02\x00\x00\x00\x00'

logger = logging.getLogger(__name__)

def ip(s):
    try:
        segs = [int(x) for x in s.split('.')]
        if len(segs) != 4:
            raise ValueError
        if not all(0 <= seg <= 255 for seg in segs):
            raise ValueError
        return s
    except ValueError:
        raise ArgumentTypeError("%r is not a valid IP address" % s)


def populate_argument_parser(parser):
    parser.add_argument('--mode', choices=['server', 'client'],
                        default='client')
    platform = get_platform()
    default_device = '/dev/tun5' if platform == 'darwin' else '/dev/net/tun'
    parser.add_argument('--device', default=default_device, help="TUN device")
    parser.add_argument('--ip', type=ip)
    parser.add_argument('--peer-ip', type=ip)

    server_group = parser.add_argument_group('server mode only')
    server_group.add_argument('-b', '--bind', default='127.0.0.1:2504',
                              help="interface to listen")

    client_group = parser.add_argument_group('client mode only')
    client_group.add_argument('--url', help="server url")
    client_group.add_argument('--default-gateway', action='store_true',
                              help="use vpn as default gateway")
    client_group.add_argument('--up', help="script to run at connection")
    client_group.add_argument('--down', help="script to run at disconnection")


def main(args):
    tun = Tun(args.device, args.ip, args.peer_ip)
    tun.open()

    if args.mode == 'server':
        server_main(args, tun)
    else:
        client_main(args, tun)


def server_main(args, tun):
    netseg = '.'.join(args.ip.split('.')[:3] + ['0/24'])
    call(['iptables', '-t', 'nat', '-D', 'POSTROUTING', '-s', netseg, '-j', 'MASQUERADE'])
    check_call(['iptables', '-t', 'nat', '-A', 'POSTROUTING', '-s', netseg, '-j', 'MASQUERADE'])

    host, port = args.bind.split(':')
    port = int(port)

    class HTTPServer(ThreadingMixIn, TCPServer):
        allow_reuse_address = True
        daemon_threads = True

    class Handler(StreamRequestHandler):
        def handle(self):
            line = self.rfile.readline().strip()
            logger.info("%s: %s", self.client_address, line)
            try:
                method = line.split()[0]
                while self.rfile.readline().strip():
                    pass
                if method == 'GET':
                    self.wfile.write('HTTP/1.1 200 OK\r\n')
                    self.wfile.write('Server: python\r\n')
                    self.wfile.write('Content-Type: audio/mpeg\r\n')
                    self.wfile.write('\r\n')
                    for data in read_tun(tun):
                        logger.debug('> %dB', len(data))
                        self.wfile.write(data)
                        self.wfile.flush()

                elif method == 'POST':
                    for data in read_connection(self.rfile):
                        logger.debug('< %dB', len(data))
                        os.write(tun.fd, data)

            finally:
                logger.info("%s %s: disconnected", self.client_address, method)

    httpd = HTTPServer((host, port), Handler)
    logger.warning("Serving on %s:%d", host, port)
    httpd.serve_forever()


def client_main(args, tun):
    url = urlparse.urlparse(args.url)
    if ':' in url.netloc:
        host, port = url.netloc.split(':')
        port = int(port)
    else:
        host, port = url.netloc, 80

    host_ip = socket.gethostbyname(host)

    def get():
        sock = socket.socket()
        sock.connect((host, port))
        logger.info("GET %s", args.url)
        sock.sendall('GET %s HTTP/1.1\r\n' % url.path)
        sock.sendall('Host: %s\r\n' % url.netloc)
        sock.sendall('Accept: */*\r\n')
        sock.sendall('\r\n')

        f = sock.makefile('r', 0)
        while f.readline().strip():
            # read until blank line
            pass

        for data in read_connection(f):
            logger.debug('< %dB', len(data))
            os.write(tun.fd, data)

        logger.warning("quit get")

    def post():
        sock = socket.socket()
        sock.connect((host, port))
        logger.info("POST %s", args.url)
        sock.sendall('POST %s HTTP/1.1\r\n' % url.path)
        sock.sendall('Host: %s\r\n' % url.netloc)
        sock.sendall('Accept: */*\r\n')
        sock.sendall('\r\n')

        for data in read_tun(tun):
            logger.debug('> %dB', len(data))
            sock.sendall(data)

        logger.warning("quit post")


    t1 = threading.Thread(target=get)
    t1.setDaemon(True)
    t2 = threading.Thread(target=post)
    t2.setDaemon(True)
    t1.start()
    t2.start()

    gateway = get_default_gateway()

    if args.down:
        atexit.register(on_down, args.down)

    add_route(host_ip + '/32', gateway)

    if args.default_gateway:
        logger.info("set default gateway")
        call(['route', 'delete', 'default'])
        check_call(['route', 'add', 'default', args.peer_ip])
        atexit.register(restore_gateway)

    if args.up:
        logger.info("Run up script")
        check_call(args.up)

    try:
        while t1.is_alive() and t2.is_alive():
            time.sleep(5)
    except KeyboardInterrupt:
        pass

def encrypt(data):
    return compress(data)[::-1]

def decrypt(data):
    return decompress(data[::-1])

def read_connection(f):
    data = f.read(len(FAKE_HEAD))
    if data != FAKE_HEAD:
        logger.debug("read fake head: %r", data)
        return
    logger.debug("got fake head")

    while True:
        data_len = f.read(2)
        if not data_len:
            logger.debug("read data len: %dB", len(data))
            break

        data_len = unpack('H', data_len)[0]
        data = f.read(data_len)
        if len(data) < data_len:
            logger.debug("read data (expect %dB): %dB", data_len, len(data))
            break

        data = decrypt(data)
        yield data


def read_tun(tun):
    yield FAKE_HEAD
    while True:
        try:
            data = os.read(tun.fd, 1500)
        except OSError, e:
            if e.errno == errno.EAGAIN:
                time.sleep(1)
                continue
        data = encrypt(data)
        yield pack('H', len(data)) + data


def on_down(script):
    logger.info("Run down script")
    call([script], stdout=open('/dev/null', 'w'))

########NEW FILE########
__FILENAME__ = server
import logging
from SocketServer import TCPServer, BaseRequestHandler
from subprocess import check_call, call

from myvpn.tun import Tun
from myvpn.utils import populate_common_argument_parser, proxy
from myvpn.consts import MAGIC_WORD

logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    populate_common_argument_parser(parser)
    parser.add_argument('--ip', default='192.168.5.1')
    parser.add_argument('--peer-ip', default='192.168.5.2')

def main(args):
    tun = Tun(device=args.device, ip=args.ip, peer_ip=args.peer_ip)
    tun.open()

    netseg = '.'.join(args.ip.split('.')[:3] + ['0/24'])
    call(['iptables', '-t', 'nat', '-D', 'POSTROUTING', '-s', netseg, '-j', 'MASQUERADE'])
    check_call(['iptables', '-t', 'nat', '-A', 'POSTROUTING', '-s', netseg, '-j', 'MASQUERADE'])

    logger.info("listen at port %d", args.port)
    server = TCPServer(('0.0.0.0', args.port), MyHandlerFactory(tun))
    server.serve_forever()


def MyHandlerFactory(tun):
    class MyHandler(BaseRequestHandler):
        def handle(self):
            logger.info("client connected from %s:%i" % self.client_address)
            data = self.request.recv(len(MAGIC_WORD))
            if data != MAGIC_WORD:
                logger.warning("bad magic word for %s:%i" % self.client_address)
                return

            logger.info("handshaked")
            self.request.send(MAGIC_WORD)

            proxy(tun.fd, self.request)

    return MyHandler

########NEW FILE########
__FILENAME__ = ssh
import sys
from subprocess import check_call, Popen, call
import atexit
import logging
from socket import gethostbyname
from time import sleep

from .utils import add_route, get_default_gateway, restore_gateway

logger = logging.getLogger(__name__)

def populate_argument_parser(parser):
    server_mode = '--server' in sys.argv

    if not server_mode:
        parser.add_argument('host')
        parser.add_argument('--path', default='myvpn', help="path to myvpn on server")
        parser.add_argument('--default-gateway', action='store_true',
                            help="use vpn as default gateway")
        parser.add_argument('--up',
                            help="script to run at connection")
        parser.add_argument('--down',
                            help="script to run at connection closed")

    parser.add_argument('--server', action='store_true', help="server mode")
    parser.add_argument('-w', dest='tun')
    parser.add_argument('client_tun_ip', nargs='?', default='192.168.5.2')
    parser.add_argument('server_tun_ip', nargs='?', default='192.168.5.1')
    parser.add_argument('-l', '--login-name')
    parser.add_argument('-i', '--identify-file')


def main(args):
    if args.server:
        return server(args)

    host_ip = gethostbyname(args.host)
    local_tun, remote_tun = ['tun%s' % x for x in args.tun.split(':')]

    ssh_cmd = ['ssh', '-w', args.tun]
    if args.login_name:
        ssh_cmd += ['-l', args.login_name]
    if args.identify_file:
        ssh_cmd += ['-i', args.identify_file]
    ssh_cmd.append(args.host)
    remote_cmd = ['sudo', args.path, 'ssh', '--server', '-w', args.tun,
                  args.client_tun_ip, args.server_tun_ip]
    cmd = ssh_cmd + remote_cmd
    ssh_p = Popen(cmd)
    atexit.register(ssh_p.terminate)

    while True:
        retval = call(['ifconfig', local_tun, args.client_tun_ip,
                       args.server_tun_ip, 'up'],
                      stderr=None if args.verbose else open('/dev/null', 'w'))
        if retval == 0:
            break
        sleep(1)

    gateway = get_default_gateway()

    if args.down:
        atexit.register(on_down, args.down)

    add_route(host_ip + '/32', gateway)

    if args.default_gateway:
        logger.info("set default gateway")
        call(['route', 'delete', 'default'])
        check_call(['route', 'add', 'default', args.server_tun_ip])
        atexit.register(restore_gateway)

    if args.up:
        logger.info("Run up script")
        check_call(args.up)

    ssh_p.wait()


def server(args):
    local_tun, remote_tun = ['tun%s' % x for x in args.tun.split(':')]
    check_call(['ifconfig', remote_tun, args.server_tun_ip, 'pointopoint',
                args.client_tun_ip, 'up'])
    netseg = '.'.join(args.server_tun_ip.split('.')[:3] + ['0/24'])
    call(['iptables', '-t', 'nat', '-D', 'POSTROUTING', '-s', netseg, '-j',
          'MASQUERADE'])
    check_call(['iptables', '-t', 'nat', '-A', 'POSTROUTING', '-s', netseg,
                '-j', 'MASQUERADE'])


def on_down(script):
    logger.info("Run down script")
    call([script], stdout=open('/dev/null', 'w'))

########NEW FILE########
__FILENAME__ = tun
import os
from fcntl import ioctl
import struct
import logging
from subprocess import check_call

from .utils import get_platform

TUNSETIFF = 0x400454ca
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000

logger = logging.getLogger(__name__)
platform = get_platform()

class Tun(object):
    def __init__(self, device, ip, peer_ip):
        self.device = device
        self.ip = ip
        self.peer_ip = peer_ip

    def open(self):
        self.fd = os.open(self.device, os.O_RDWR)

        if platform == 'linux':
            iface = ioctl(self.fd, TUNSETIFF, struct.pack('16sH', 'tun%d', IFF_TUN|IFF_NO_PI))
            self.ifname = iface[:16].strip('\0')
            check_call(['ifconfig', self.ifname, self.ip, 'pointopoint',
                        self.peer_ip, 'up'])
        else:
            self.ifname = self.device.split('/')[-1]
            check_call(['ifconfig', self.ifname, self.ip, self.peer_ip,
                        'up'])

        logger.info("%s open", self.ifname)


    def close(self):
        os.close(self.fd)
        del self.fd

########NEW FILE########
__FILENAME__ = utils
import os
import logging
from threading import Thread
from subprocess import call, check_call, Popen, PIPE
import atexit

from myvpn.consts import DEFAULT_PORT

logger = logging.getLogger(__name__)

def get_platform():
    return os.uname()[0].lower()

def populate_common_argument_parser(parser):
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help="TCP port [default: %(default)s]")
    platform = get_platform()
    default_device = '/dev/tun5' if platform == 'darwin' else '/dev/net/tun'
    parser.add_argument('--device', default=default_device,
                        help="TUN device [default: %(default)s]")


def encrypt(data):
    return data[::-1]

def decrypt(data):
    return data[::-1]

def proxy(tun_fd, sock):
    t1 = Thread(target=copy_fd_to_socket, args=(tun_fd, sock))
    t1.setDaemon(True)
    t1.start()

    copy_socket_to_fd(sock, tun_fd)

    t1.join()

def copy_fd_to_socket(fd, sock):
    while 1:
        data = os.read(fd, 1500)
        data = encrypt(data)
        logger.debug("> %dB", len(data))
        sock.sendall('%04x' % len(data) + data)

def copy_socket_to_fd(sock, fd):
    while 1:
        data_len = int(sock.recv(4), 16)
        data = ''
        while len(data) < data_len:
            data += sock.recv(data_len - len(data))
        logger.debug("< %dB", data_len)
        data = decrypt(data)
        os.write(fd, data)


def add_route(net, gateway):
    call(['route', 'delete', net])
    check_call(['route', 'add', net, gateway])
    atexit.register(call, ['route', 'delete', net])


def get_default_gateway():
    p = Popen(['scutil'], stdin=PIPE, stdout=PIPE)
    output = p.communicate('open\nget State:/Network/Global/IPv4\nd.show\nquit\n')[0]
    for line in output.splitlines():
        if 'Router' in line:
            gateway = line.split('Router : ')[-1]
            break
    return gateway


def restore_gateway():
    gateway = get_default_gateway()
    logger.info("restore gateway to %s", gateway)
    call(['route', 'delete', 'default'])
    call(['route', 'add', 'default', gateway])

########NEW FILE########
__FILENAME__ = vpn
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import logging

def main():
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(title="commands")
    subcommands = [
        ('ssh', 'ssh', "Run in ssh tunnel"),
        ('http', 'http', "Run in http tunnel"),
    ]
    for command, module_name, help_text in subcommands:
        subparser = subparsers.add_parser(command, help=help_text,
                                          formatter_class=ArgumentDefaultsHelpFormatter)
        subparser.add_argument('-v', '--verbose', action='store_true',
                               help="enable additional output")
        module = __import__(module_name, globals(), locals(),
                            ['populate_argument_parser', 'main'], 1)
        module.populate_argument_parser(subparser)
        subparser.set_defaults(func=module.main)

    args = parser.parse_args()
    loglevel = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=loglevel)

    return args.func(args)

########NEW FILE########
