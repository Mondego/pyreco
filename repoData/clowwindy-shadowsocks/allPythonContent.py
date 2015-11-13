__FILENAME__ = encrypt
#!/usr/bin/env python

# Copyright (c) 2014 clowwindy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import hashlib
import string
import struct
import logging
import encrypt_salsa20


def random_string(length):
    try:
        import M2Crypto.Rand
        return M2Crypto.Rand.rand_bytes(length)
    except ImportError:
        # TODO really strong enough on Linux?
        return os.urandom(length)


cached_tables = {}
cached_keys = {}


def get_table(key):
    m = hashlib.md5()
    m.update(key)
    s = m.digest()
    (a, b) = struct.unpack('<QQ', s)
    table = [c for c in string.maketrans('', '')]
    for i in xrange(1, 1024):
        table.sort(lambda x, y: int(a % (ord(x) + i) - a % (ord(y) + i)))
    return table


def init_table(key, method=None):
    if method is not None and method == 'table':
        method = None
    if method:
        try:
            __import__('M2Crypto')
        except ImportError:
            logging.error('M2Crypto is required to use encryption other than '
                          'default method')
            sys.exit(1)
    if not method:
        if key in cached_tables:
            return cached_tables[key]
        encrypt_table = ''.join(get_table(key))
        decrypt_table = string.maketrans(encrypt_table,
                                         string.maketrans('', ''))
        cached_tables[key] = [encrypt_table, decrypt_table]
    else:
        try:
            Encryptor(key, method)  # test if the settings if OK
        except Exception as e:
            logging.error(e)
            sys.exit(1)


def EVP_BytesToKey(password, key_len, iv_len):
    # equivalent to OpenSSL's EVP_BytesToKey() with count 1
    # so that we make the same key and iv as nodejs version
    password = str(password)
    r = cached_keys.get(password, None)
    if r:
        return r
    m = []
    i = 0
    while len(''.join(m)) < (key_len + iv_len):
        md5 = hashlib.md5()
        data = password
        if i > 0:
            data = m[i - 1] + password
        md5.update(data)
        m.append(md5.digest())
        i += 1
    ms = ''.join(m)
    key = ms[:key_len]
    iv = ms[key_len:key_len + iv_len]
    cached_keys[password] = (key, iv)
    return (key, iv)


method_supported = {
    'aes-128-cfb': (16, 16),
    'aes-192-cfb': (24, 16),
    'aes-256-cfb': (32, 16),
    'bf-cfb': (16, 8),
    'camellia-128-cfb': (16, 16),
    'camellia-192-cfb': (24, 16),
    'camellia-256-cfb': (32, 16),
    'cast5-cfb': (16, 8),
    'des-cfb': (8, 8),
    'idea-cfb': (16, 8),
    'rc2-cfb': (16, 8),
    'rc4': (16, 0),
    'seed-cfb': (16, 16),
    'salsa20-ctr': (32, 8),
}


class Encryptor(object):
    def __init__(self, key, method=None):
        if method == 'table':
            method = None
        self.key = key
        self.method = method
        self.iv = None
        self.iv_sent = False
        self.cipher_iv = ''
        self.decipher = None
        if method:
            self.cipher = self.get_cipher(key, method, 1, iv=random_string(32))
        else:
            self.encrypt_table, self.decrypt_table = init_table(key)
            self.cipher = None

    def get_cipher_len(self, method):
        method = method.lower()
        m = method_supported.get(method, None)
        return m

    def iv_len(self):
        return len(self.cipher_iv)

    def get_cipher(self, password, method, op, iv=None):
        password = password.encode('utf-8')
        method = method.lower()
        m = self.get_cipher_len(method)
        if m:
            key, iv_ = EVP_BytesToKey(password, m[0], m[1])
            if iv is None:
                iv = iv_
            iv = iv[:m[1]]
            if op == 1:
                self.cipher_iv = iv[:m[1]]  # this iv is for cipher not decipher
            if method != 'salsa20-ctr':
                import M2Crypto.EVP
                return M2Crypto.EVP.Cipher(method.replace('-', '_'), key, iv, op,
                                       key_as_bytes=0, d='md5', salt=None, i=1,
                                       padding=1)
            else:
                return encrypt_salsa20.Salsa20Cipher(method, key, iv, op)

        logging.error('method %s not supported' % method)
        sys.exit(1)

    def encrypt(self, buf):
        if len(buf) == 0:
            return buf
        if not self.method:
            return string.translate(buf, self.encrypt_table)
        else:
            if self.iv_sent:
                return self.cipher.update(buf)
            else:
                self.iv_sent = True
                return self.cipher_iv + self.cipher.update(buf)

    def decrypt(self, buf):
        if len(buf) == 0:
            return buf
        if not self.method:
            return string.translate(buf, self.decrypt_table)
        else:
            if self.decipher is None:
                decipher_iv_len = self.get_cipher_len(self.method)[1]
                decipher_iv = buf[:decipher_iv_len]
                self.decipher = self.get_cipher(self.key, self.method, 0,
                                                iv=decipher_iv)
                buf = buf[decipher_iv_len:]
                if len(buf) == 0:
                    return buf
            return self.decipher.update(buf)


def encrypt_all(password, method, op, data):
    if method is not None and method.lower() == 'table':
        method = None
    if not method:
        [encrypt_table, decrypt_table] = init_table(password)
        if op:
            return string.translate(encrypt_table, data)
        else:
            return string.translate(decrypt_table, data)
    else:
        import M2Crypto.EVP
        result = []
        method = method.lower()
        (key_len, iv_len) = method_supported[method]
        (key, _) = EVP_BytesToKey(password, key_len, iv_len)
        if op:
            iv = random_string(iv_len)
            result.append(iv)
        else:
            iv = data[:iv_len]
            data = data[iv_len:]
        cipher = M2Crypto.EVP.Cipher(method.replace('-', '_'), key, iv, op,
                                     key_as_bytes=0, d='md5', salt=None, i=1,
                                     padding=1)
        result.append(cipher.update(data))
        f = cipher.final()
        if f:
            result.append(f)
        return ''.join(result)

########NEW FILE########
__FILENAME__ = encrypt_salsa20
#!/usr/bin/python

import time
import struct
import logging
import sys

slow_xor = False
imported = False

BLOCK_SIZE = 16384


def run_imports():
    global imported, slow_xor, salsa20, numpy
    if not imported:
        imported = True
        try:
            import numpy
        except ImportError:
            logging.error('can not import numpy, using SLOW XOR')
            logging.error('please install numpy if you use salsa20')
            slow_xor = True
        try:
            import salsa20
        except ImportError:
            logging.error('you have to install salsa20 before you use salsa20')
            sys.exit(1)


def numpy_xor(a, b):
    if slow_xor:
        return py_xor_str(a, b)
    dtype = numpy.byte
    if len(a) % 4 == 0:
        dtype = numpy.uint32
    elif len(a) % 2 == 0:
        dtype = numpy.uint16

    ab = numpy.frombuffer(a, dtype=dtype)
    bb = numpy.frombuffer(b, dtype=dtype)
    c = numpy.bitwise_xor(ab, bb)
    r = c.tostring()
    return r


def py_xor_str(a, b):
    c = []
    for i in xrange(0, len(a)):
        c.append(chr(ord(a[i]) ^ ord(b[i])))
    return ''.join(c)


class Salsa20Cipher(object):
    """a salsa20 CTR implemetation, provides m2crypto like cipher API"""

    def __init__(self, alg, key, iv, op, key_as_bytes=0, d=None, salt=None,
                 i=1, padding=1):
        run_imports()
        if alg != 'salsa20-ctr':
            raise Exception('unknown algorithm')
        self._key = key
        self._nonce = struct.unpack('<Q', iv)[0]
        self._pos = 0
        self._next_stream()

    def _next_stream(self):
        self._nonce &= 0xFFFFFFFFFFFFFFFF
        self._stream = salsa20.Salsa20_keystream(BLOCK_SIZE,
                                                 struct.pack('<Q', self._nonce),
                                                 self._key)
        self._nonce += 1

    def update(self, data):
        results = []
        while True:
            remain = BLOCK_SIZE - self._pos
            cur_data = data[:remain]
            cur_data_len = len(cur_data)
            cur_stream = self._stream[self._pos:self._pos + cur_data_len]
            self._pos = self._pos + cur_data_len
            data = data[remain:]

            results.append(numpy_xor(cur_data, cur_stream))

            if self._pos >= BLOCK_SIZE:
                self._next_stream()
                self._pos = 0
            if not data:
                break
        return ''.join(results)


def test():
    from os import urandom
    import random

    rounds = 1 * 1024
    plain = urandom(BLOCK_SIZE * rounds)
    import M2Crypto.EVP
    # cipher = M2Crypto.EVP.Cipher('aes_128_cfb', 'k' * 32, 'i' * 16, 1,
    #                key_as_bytes=0, d='md5', salt=None, i=1,
    #                padding=1)
    # decipher = M2Crypto.EVP.Cipher('aes_128_cfb', 'k' * 32, 'i' * 16, 0,
    #                key_as_bytes=0, d='md5', salt=None, i=1,
    #                padding=1)

    cipher = Salsa20Cipher('salsa20-ctr', 'k' * 32, 'i' * 8, 1)
    decipher = Salsa20Cipher('salsa20-ctr', 'k' * 32, 'i' * 8, 1)
    results = []
    pos = 0
    print 'start'
    start = time.time()
    while pos < len(plain):
        l = random.randint(100, 32768)
        c = cipher.update(plain[pos:pos + l])
        results.append(c)
        pos += l
    pos = 0
    c = ''.join(results)
    results = []
    while pos < len(plain):
        l = random.randint(100, 32768)
        results.append(decipher.update(c[pos:pos + l]))
        pos += l
    end = time.time()
    print BLOCK_SIZE * rounds / (end - start)
    assert ''.join(results) == plain


if __name__ == '__main__':
    test()
########NEW FILE########
__FILENAME__ = eventloop
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 clowwindy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# from ssloop
# https://github.com/clowwindy/ssloop


import select
from collections import defaultdict


__all__ = ['EventLoop', 'POLL_NULL', 'POLL_IN', 'POLL_OUT', 'POLL_ERR',
           'POLL_HUP', 'POLL_NVAL']

POLL_NULL = 0x00
POLL_IN = 0x01
POLL_OUT = 0x04
POLL_ERR = 0x08
POLL_HUP = 0x10
POLL_NVAL = 0x20


class EpollLoop(object):

    def __init__(self):
        self._epoll = select.epoll()

    def poll(self, timeout):
        return self._epoll.poll(timeout)

    def add_fd(self, fd, mode):
        self._epoll.register(fd, mode)

    def remove_fd(self, fd):
        self._epoll.unregister(fd)

    def modify_fd(self, fd, mode):
        self._epoll.modify(fd, mode)


class KqueueLoop(object):

    MAX_EVENTS = 1024

    def __init__(self):
        self._kqueue = select.kqueue()
        self._fds = {}

    def _control(self, fd, mode, flags):
        events = []
        if mode & POLL_IN:
            events.append(select.kevent(fd, select.KQ_FILTER_READ, flags))
        if mode & POLL_OUT:
            events.append(select.kevent(fd, select.KQ_FILTER_WRITE, flags))
        for e in events:
            self._kqueue.control([e], 0)

    def poll(self, timeout):
        if timeout < 0:
            timeout = None  # kqueue behaviour
        events = self._kqueue.control(None, KqueueLoop.MAX_EVENTS, timeout)
        results = defaultdict(lambda: POLL_NULL)
        for e in events:
            fd = e.ident
            if e.filter == select.KQ_FILTER_READ:
                results[fd] |= POLL_IN
            elif e.filter == select.KQ_FILTER_WRITE:
                results[fd] |= POLL_OUT
        return results.iteritems()

    def add_fd(self, fd, mode):
        self._fds[fd] = mode
        self._control(fd, mode, select.KQ_EV_ADD)

    def remove_fd(self, fd):
        self._control(fd, self._fds[fd], select.KQ_EV_DELETE)
        del self._fds[fd]

    def modify_fd(self, fd, mode):
        self.remove_fd(fd)
        self.add_fd(fd, mode)


class SelectLoop(object):

    def __init__(self):
        self._r_list = set()
        self._w_list = set()
        self._x_list = set()

    def poll(self, timeout):
        r, w, x = select.select(self._r_list, self._w_list, self._x_list,
                                timeout)
        results = defaultdict(lambda: POLL_NULL)
        for p in [(r, POLL_IN), (w, POLL_OUT), (x, POLL_ERR)]:
            for fd in p[0]:
                results[fd] |= p[1]
        return results.items()

    def add_fd(self, fd, mode):
        if mode & POLL_IN:
            self._r_list.add(fd)
        if mode & POLL_OUT:
            self._w_list.add(fd)
        if mode & POLL_ERR:
            self._x_list.add(fd)

    def remove_fd(self, fd):
        if fd in self._r_list:
            self._r_list.remove(fd)
        if fd in self._w_list:
            self._w_list.remove(fd)
        if fd in self._x_list:
            self._x_list.remove(fd)

    def modify_fd(self, fd, mode):
        self.remove_fd(fd)
        self.add_fd(fd, mode)


class EventLoop(object):
    def __init__(self):
        if hasattr(select, 'epoll'):
            self._impl = EpollLoop()
        elif hasattr(select, 'kqueue'):
            self._impl = KqueueLoop()
        elif hasattr(select, 'select'):
            self._impl = SelectLoop()
        else:
            raise Exception('can not find any available functions in select '
                            'package')
        self._fd_to_f = {}

    def poll(self, timeout=None):
        events = self._impl.poll(timeout)
        return ((self._fd_to_f[fd], event) for fd, event in events)

    def add(self, f, mode):
        fd = f.fileno()
        self._fd_to_f[fd] = f
        self._impl.add_fd(fd, mode)

    def remove(self, f):
        fd = f.fileno()
        self._fd_to_f[fd] = None
        self._impl.remove_fd(fd)

    def modify(self, f, mode):
        fd = f.fileno()
        self._impl.modify_fd(fd, mode)


# from tornado
def errno_from_exception(e):
    """Provides the errno from an Exception object.

    There are cases that the errno attribute was not set so we pull
    the errno out of the args but if someone instatiates an Exception
    without any args you will get a tuple error. So this function
    abstracts all that behavior to give you a safe way to get the
    errno.
    """

    if hasattr(e, 'errno'):
        return e.errno
    elif e.args:
        return e.args[0]
    else:
        return None

########NEW FILE########
__FILENAME__ = local
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 clowwindy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import with_statement
import sys
if sys.version_info < (2, 6):
    import simplejson as json
else:
    import json

try:
    import gevent
    import gevent.monkey
    gevent.monkey.patch_all(dns=gevent.version_info[0] >= 1)
except ImportError:
    gevent = None
    print >>sys.stderr, 'warning: gevent not found, using threading instead'

import socket
import eventloop
import errno
import select
import SocketServer
import struct
import os
import random
import re
import logging
import getopt
import encrypt
import utils
import udprelay


MSG_FASTOPEN = 0x20000000


def send_all(sock, data):
    bytes_sent = 0
    while True:
        r = sock.send(data[bytes_sent:])
        if r < 0:
            return r
        bytes_sent += r
        if bytes_sent == len(data):
            return bytes_sent


class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True

    def get_request(self):
        connection = self.socket.accept()
        connection[0].settimeout(config_timeout)
        return connection


class Socks5Server(SocketServer.StreamRequestHandler):
    @staticmethod
    def get_server():
        a_port = config_server_port
        a_server = config_server
        if isinstance(config_server_port, list):
            # support config like "server_port": [8081, 8082]
            a_port = random.choice(config_server_port)
        if isinstance(config_server, list):
            # support config like "server": ["123.123.123.1", "123.123.123.2"]
            a_server = random.choice(config_server)

        r = re.match(r'^(.*):(\d+)$', a_server)
        if r:
            # support config like "server": "123.123.123.1:8381"
            # or "server": ["123.123.123.1:8381", "123.123.123.2:8381"]
            a_server = r.group(1)
            a_port = int(r.group(2))
        return a_server, a_port

    @staticmethod
    def handle_tcp(sock, remote, encryptor, pending_data=None,
                   server=None, port=None):
        connected = False
        try:
            if config_fast_open:
                fdset = [sock]
            else:
                fdset = [sock, remote]
            while True:
                should_break = False
                r, w, e = select.select(fdset, [], [], config_timeout)
                if not r:
                    logging.warn('read time out')
                    break
                if sock in r:
                    if not connected and config_fast_open:
                        data = sock.recv(4096)
                        data = encryptor.encrypt(pending_data + data)
                        pending_data = None
                        logging.info('fast open %s:%d' % (server, port))
                        try:
                            remote.sendto(data, MSG_FASTOPEN, (server, port))
                        except (OSError, IOError) as e:
                            if eventloop.errno_from_exception(e) == errno.EINPROGRESS:
                                pass
                            else:
                                raise e
                        connected = True
                        fdset = [sock, remote]
                    else:
                        data = sock.recv(4096)
                        if pending_data:
                            data = pending_data + data
                            pending_data = None
                        data = encryptor.encrypt(data)
                        if len(data) <= 0:
                            should_break = True
                        else:
                            result = send_all(remote, data)
                            if result < len(data):
                                raise Exception('failed to send all data')

                if remote in r:
                    data = encryptor.decrypt(remote.recv(4096))
                    if len(data) <= 0:
                        should_break = True
                    else:
                        result = send_all(sock, data)
                        if result < len(data):
                            raise Exception('failed to send all data')
                if should_break:
                    # make sure all data are read before we close the sockets
                    # TODO: we haven't read ALL the data, actually
                    # http://cs.ecs.baylor.edu/~donahoo/practical/CSockets/TCPRST.pdf
                    break
        finally:
            sock.close()
            remote.close()

    def handle(self):
        try:
            encryptor = encrypt.Encryptor(config_password, config_method)
            sock = self.connection
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            data = sock.recv(262)
            if not data:
                sock.close()
                return
            if len(data) < 3:
                return
            method = ord(data[2])
            if method == 2:
                logging.warn('client tries to use username/password auth, prete'
                             'nding the password is OK')
                sock.send('\x05\x02')
                try:
                    ver_ulen = sock.recv(2)
                    ulen = ord(ver_ulen[1])
                    if ulen:
                        username = sock.recv(ulen)
                        assert(ulen == len(username))
                    plen = ord(sock.recv(1))
                    if plen:
                        _password = sock.recv(plen)
                        assert(plen == len(_password))
                    sock.send('\x01\x00')
                except Exception as e:
                    logging.error(e)
                    return
            elif method == 0:
                sock.send("\x05\x00")
            else:
                logging.error('unsupported method %d' % method)
                return
            data = self.rfile.read(4) or '\x00' * 4
            mode = ord(data[1])
            if mode == 1:
                pass
            elif mode == 3:
                # UDP
                logging.debug('UDP assc request')
                if sock.family == socket.AF_INET6:
                    header = '\x05\x00\x00\x04'
                else:
                    header = '\x05\x00\x00\x01'
                addr, port = sock.getsockname()
                addr_to_send = socket.inet_pton(sock.family, addr)
                port_to_send = struct.pack('>H', port)
                sock.send(header + addr_to_send + port_to_send)
                while True:
                    data = sock.recv(4096)
                    if not data:
                        break
                return
            else:
                logging.warn('unknown mode %d' % mode)
                return
            addrtype = ord(data[3])
            addr_to_send = data[3]
            if addrtype == 1:
                addr_ip = self.rfile.read(4)
                addr = socket.inet_ntoa(addr_ip)
                addr_to_send += addr_ip
            elif addrtype == 3:
                addr_len = self.rfile.read(1)
                addr = self.rfile.read(ord(addr_len))
                addr_to_send += addr_len + addr
            elif addrtype == 4:
                addr_ip = self.rfile.read(16)
                addr = socket.inet_ntop(socket.AF_INET6, addr_ip)
                addr_to_send += addr_ip
            else:
                logging.warn('addr_type not supported')
                # not supported
                return
            addr_port = self.rfile.read(2)
            addr_to_send += addr_port
            port = struct.unpack('>H', addr_port)
            try:
                reply = "\x05\x00\x00\x01"
                reply += socket.inet_aton('0.0.0.0') + struct.pack(">H", 2222)
                self.wfile.write(reply)
                # reply immediately
                a_server, a_port = Socks5Server.get_server()
                addrs = socket.getaddrinfo(a_server, a_port)
                if addrs:
                    af, socktype, proto, canonname, sa = addrs[0]
                    if config_fast_open:
                        remote = socket.socket(af, socktype, proto)
                        remote.setsockopt(socket.IPPROTO_TCP,
                                          socket.TCP_NODELAY, 1)
                        Socks5Server.handle_tcp(sock, remote, encryptor,
                                                addr_to_send, a_server, a_port)
                    else:
                        logging.info('connecting %s:%d' % (addr, port[0]))
                        remote = socket.create_connection((a_server, a_port),
                                                        timeout=config_timeout)
                        remote.settimeout(config_timeout)
                        remote.setsockopt(socket.IPPROTO_TCP,
                                          socket.TCP_NODELAY, 1)
                        Socks5Server.handle_tcp(sock, remote, encryptor,
                                                addr_to_send)
            except (OSError, IOError) as e:
                logging.warn(e)
                return
        except (OSError, IOError) as e:
            raise e
            logging.warn(e)


def main():
    global config_server, config_server_port, config_password, config_method,\
        config_fast_open, config_timeout

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S', filemode='a+')

    # fix py2exe
    if hasattr(sys, "frozen") and sys.frozen in \
            ("windows_exe", "console_exe"):
        p = os.path.dirname(os.path.abspath(sys.executable))
        os.chdir(p)
    version = ''
    try:
        import pkg_resources
        version = pkg_resources.get_distribution('shadowsocks').version
    except:
        pass
    print 'shadowsocks %s' % version

    config_password = None
    config_method = None

    config_path = utils.find_config()
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 's:b:p:k:l:m:c:t:',
                                      ['fast-open'])
        for key, value in optlist:
            if key == '-c':
                config_path = value

        if config_path:
            logging.info('loading config from %s' % config_path)
            with open(config_path, 'rb') as f:
                try:
                    config = json.load(f)
                except ValueError as e:
                    logging.error('found an error in config.json: %s',
                                  e.message)
                    sys.exit(1)
        else:
            config = {}

        optlist, args = getopt.getopt(sys.argv[1:], 's:b:p:k:l:m:c:t:',
                                      ['fast-open'])
        for key, value in optlist:
            if key == '-p':
                config['server_port'] = int(value)
            elif key == '-k':
                config['password'] = value
            elif key == '-l':
                config['local_port'] = int(value)
            elif key == '-s':
                config['server'] = value
            elif key == '-m':
                config['method'] = value
            elif key == '-b':
                config['local_address'] = value
            elif key == '--fast-open':
                config['fast_open'] = True
    except getopt.GetoptError as e:
        logging.error(e)
        utils.print_local_help()
        sys.exit(2)

    config_server = config['server']
    config_server_port = config['server_port']
    config_local_port = config['local_port']
    config_password = config['password']
    config_method = config.get('method', None)
    config_local_address = config.get('local_address', '127.0.0.1')
    config_timeout = int(config.get('timeout', 300))
    config_fast_open = config.get('fast_open', False)

    if not config_password and not config_path:
        sys.exit('config not specified, please read '
                 'https://github.com/clowwindy/shadowsocks')

    utils.check_config(config)

    encrypt.init_table(config_password, config_method)

    addrs = socket.getaddrinfo(config_local_address, config_local_port)
    if not addrs:
        logging.error('cant resolve listen address')
        sys.exit(1)
    ThreadingTCPServer.address_family = addrs[0][0]
    try:
        udprelay.UDPRelay(config_local_address, int(config_local_port),
                          config_server, config_server_port, config_password,
                          config_method, int(config_timeout), True).start()
        server = ThreadingTCPServer((config_local_address, config_local_port),
                                    Socks5Server)
        server.timeout = int(config_timeout)
        logging.info("starting local at %s:%d" %
                     tuple(server.server_address[:2]))
        server.serve_forever()
    except socket.error, e:
        logging.error(e)
    except KeyboardInterrupt:
        server.shutdown()
        sys.exit(0)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = lru_cache
#!/usr/bin/python
# -*- coding: utf-8 -*-

import collections
import logging
import heapq
import time


class LRUCache(collections.MutableMapping):
    """This class is not thread safe"""

    def __init__(self, timeout=60, close_callback=None, *args, **kwargs):
        self.timeout = timeout
        self.close_callback = close_callback
        self.store = {}
        self.time_to_keys = collections.defaultdict(list)
        self.last_visits = []
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        "O(logm)"
        t = time.time()
        self.time_to_keys[t].append(key)
        heapq.heappush(self.last_visits, t)
        return self.store[key]

    def __setitem__(self, key, value):
        "O(logm)"
        t = time.time()
        self.store[key] = value
        self.time_to_keys[t].append(key)
        heapq.heappush(self.last_visits, t)

    def __delitem__(self, key):
        "O(1)"
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def sweep(self):
        "O(m)"
        now = time.time()
        c = 0
        while len(self.last_visits) > 0:
            least = self.last_visits[0]
            if now - least <= self.timeout:
                break
            for key in self.time_to_keys[least]:
                heapq.heappop(self.last_visits)
                if self.store.__contains__(key):
                    value = self.store[key]
                    if self.close_callback is not None:
                        self.close_callback(value)

                    del self.store[key]
                    c += 1
            del self.time_to_keys[least]
        if c:
            logging.debug('%d keys swept' % c)

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 clowwindy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import with_statement
import sys
if sys.version_info < (2, 6):
    import simplejson as json
else:
    import json


# TODO remove gevent
try:
    import gevent
    import gevent.monkey
    gevent.monkey.patch_all(dns=gevent.version_info[0] >= 1)
except ImportError:
    gevent = None
    print >>sys.stderr, 'warning: gevent not found, using threading instead'


import socket
import select
import threading
import SocketServer
import struct
import logging
import getopt
import encrypt
import os
import utils
import udprelay


def send_all(sock, data):
    bytes_sent = 0
    while True:
        r = sock.send(data[bytes_sent:])
        if r < 0:
            return r
        bytes_sent += r
        if bytes_sent == len(data):
            return bytes_sent


class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True

    def server_activate(self):
        if config_fast_open:
            try:
                self.socket.setsockopt(socket.SOL_TCP, 23, 5)
            except socket.error:
                logging.error('warning: fast open is not available')
        self.socket.listen(self.request_queue_size)

    def get_request(self):
        connection = self.socket.accept()
        connection[0].settimeout(config_timeout)
        return connection


class Socks5Server(SocketServer.StreamRequestHandler):
    def handle_tcp(self, sock, remote):
        try:
            fdset = [sock, remote]
            while True:
                should_break = False
                r, w, e = select.select(fdset, [], [], config_timeout)
                if not r:
                    logging.warn('read time out')
                    break
                if sock in r:
                    data = self.decrypt(sock.recv(4096))
                    if len(data) <= 0:
                        should_break = True
                    else:
                        result = send_all(remote, data)
                        if result < len(data):
                            raise Exception('failed to send all data')
                if remote in r:
                    data = self.encrypt(remote.recv(4096))
                    if len(data) <= 0:
                        should_break = True
                    else:
                        result = send_all(sock, data)
                        if result < len(data):
                            raise Exception('failed to send all data')
                if should_break:
                    # make sure all data are read before we close the sockets
                    # TODO: we haven't read ALL the data, actually
                    # http://cs.ecs.baylor.edu/~donahoo/practical/CSockets/TCPRST.pdf
                    break

        finally:
            sock.close()
            remote.close()

    def encrypt(self, data):
        return self.encryptor.encrypt(data)

    def decrypt(self, data):
        return self.encryptor.decrypt(data)

    def handle(self):
        try:
            self.encryptor = encrypt.Encryptor(self.server.key,
                                               self.server.method)
            sock = self.connection
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            iv_len = self.encryptor.iv_len()
            data = sock.recv(iv_len)
            if iv_len > 0 and not data:
                sock.close()
                return
            if iv_len:
                self.decrypt(data)
            data = sock.recv(1)
            if not data:
                sock.close()
                return
            addrtype = ord(self.decrypt(data))
            if addrtype == 1:
                addr = socket.inet_ntoa(self.decrypt(self.rfile.read(4)))
            elif addrtype == 3:
                addr = self.decrypt(
                    self.rfile.read(ord(self.decrypt(sock.recv(1)))))
            elif addrtype == 4:
                addr = socket.inet_ntop(socket.AF_INET6,
                                        self.decrypt(self.rfile.read(16)))
            else:
                # not supported
                logging.warn('addr_type not supported, maybe wrong password')
                return
            port = struct.unpack('>H', self.decrypt(self.rfile.read(2)))
            try:
                logging.info('connecting %s:%d' % (addr, port[0]))
                remote = socket.create_connection((addr, port[0]),
                                                  timeout=config_timeout)
                remote.settimeout(config_timeout)
                remote.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except socket.error, e:
                # Connection refused
                logging.warn(e)
                return
            self.handle_tcp(sock, remote)
        except socket.error, e:
            logging.warn(e)


def main():
    global config_server, config_server_port, config_method, config_fast_open, \
        config_timeout

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S', filemode='a+')


    version = ''
    try:
        import pkg_resources
        version = pkg_resources.get_distribution('shadowsocks').version
    except:
        pass
    print 'shadowsocks %s' % version

    config_path = utils.find_config()
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 's:p:k:m:c:t:',
                                      ['fast-open', 'workers:'])
        for key, value in optlist:
            if key == '-c':
                config_path = value

        if config_path:
            logging.info('loading config from %s' % config_path)
            with open(config_path, 'rb') as f:
                try:
                    config = json.load(f)
                except ValueError as e:
                    logging.error('found an error in config.json: %s',
                                  e.message)
                    sys.exit(1)
        else:
            config = {}

        optlist, args = getopt.getopt(sys.argv[1:], 's:p:k:m:c:t:',
                                      ['fast-open', 'workers='])
        for key, value in optlist:
            if key == '-p':
                config['server_port'] = int(value)
            elif key == '-k':
                config['password'] = value
            elif key == '-s':
                config['server'] = value
            elif key == '-m':
                config['method'] = value
            elif key == '-t':
                config['timeout'] = value
            elif key == '--fast-open':
                config['fast_open'] = True
            elif key == '--workers':
                config['workers'] = value
    except getopt.GetoptError:
        utils.print_server_help()
        sys.exit(2)

    config_server = config['server']
    config_server_port = config['server_port']
    config_key = config['password']
    config_method = config.get('method', None)
    config_port_password = config.get('port_password', None)
    config_timeout = int(config.get('timeout', 300))
    config_fast_open = config.get('fast_open', False)
    config_workers = config.get('workers', 1)

    if not config_key and not config_path:
        sys.exit('config not specified, please read '
                 'https://github.com/clowwindy/shadowsocks')

    utils.check_config(config)

    if config_port_password:
        if config_server_port or config_key:
            logging.warn('warning: port_password should not be used with '
                         'server_port and password. server_port and password '
                         'will be ignored')
    else:
        config_port_password = {}
        config_port_password[str(config_server_port)] = config_key

    encrypt.init_table(config_key, config_method)
    addrs = socket.getaddrinfo(config_server, int(8387))
    if not addrs:
        logging.error('cant resolve listen address')
        sys.exit(1)
    ThreadingTCPServer.address_family = addrs[0][0]
    tcp_servers = []
    udp_servers = []
    for port, key in config_port_password.items():
        tcp_server = ThreadingTCPServer((config_server, int(port)),
                                        Socks5Server)
        tcp_server.key = key
        tcp_server.method = config_method
        tcp_server.timeout = int(config_timeout)
        logging.info("starting server at %s:%d" %
                     tuple(tcp_server.server_address[:2]))
        tcp_servers.append(tcp_server)
        udp_server = udprelay.UDPRelay(config_server, int(port), None, None,
                                       key, config_method, int(config_timeout),
                                       False)
        udp_servers.append(udp_server)

    def run_server():
        for tcp_server in tcp_servers:
            threading.Thread(target=tcp_server.serve_forever).start()
        for udp_server in udp_servers:
            udp_server.start()

    if int(config_workers) > 1:
        if os.name == 'posix':
            children = []
            is_child = False
            for i in xrange(0, int(config_workers)):
                r = os.fork()
                if r == 0:
                    logging.info('worker started')
                    is_child = True
                    run_server()
                    break
                else:
                    children.append(r)
            if not is_child:
                def handler(signum, frame):
                    for pid in children:
                        os.kill(pid, signum)
                        os.waitpid(pid, 0)
                    sys.exit()
                import signal
                signal.signal(signal.SIGTERM, handler)

                # master
                for tcp_server in tcp_servers:
                    tcp_server.server_close()
                for udp_server in udp_servers:
                    udp_server.close()

                for child in children:
                    os.waitpid(child, 0)
        else:
            logging.warn('worker is only available on Unix/Linux')
            run_server()
    else:
        run_server()


if __name__ == '__main__':
    try:
        main()
    except socket.error, e:
        logging.error(e)

########NEW FILE########
__FILENAME__ = udprelay
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 clowwindy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# SOCKS5 UDP Request
# +----+------+------+----------+----------+----------+
# |RSV | FRAG | ATYP | DST.ADDR | DST.PORT |   DATA   |
# +----+------+------+----------+----------+----------+
# | 2  |  1   |  1   | Variable |    2     | Variable |
# +----+------+------+----------+----------+----------+

# SOCKS5 UDP Response
# +----+------+------+----------+----------+----------+
# |RSV | FRAG | ATYP | DST.ADDR | DST.PORT |   DATA   |
# +----+------+------+----------+----------+----------+
# | 2  |  1   |  1   | Variable |    2     | Variable |
# +----+------+------+----------+----------+----------+

# shadowsocks UDP Request (before encrypted)
# +------+----------+----------+----------+
# | ATYP | DST.ADDR | DST.PORT |   DATA   |
# +------+----------+----------+----------+
# |  1   | Variable |    2     | Variable |
# +------+----------+----------+----------+

# shadowsocks UDP Response (before encrypted)
# +------+----------+----------+----------+
# | ATYP | DST.ADDR | DST.PORT |   DATA   |
# +------+----------+----------+----------+
# |  1   | Variable |    2     | Variable |
# +------+----------+----------+----------+

# shadowsocks UDP Request and Response (after encrypted)
# +-------+--------------+
# |   IV  |    PAYLOAD   |
# +-------+--------------+
# | Fixed |   Variable   |
# +-------+--------------+

# HOW TO NAME THINGS
# ------------------
# `dest`    means destination server, which is from DST fields in the SOCKS5
#           request
# `local`   means local server of shadowsocks
# `remote`  means remote server of shadowsocks
# `client`  means UDP clients that connects to other servers
# `server`  means the UDP server that handles user requests


import time
import threading
import socket
import logging
import struct
import encrypt
import eventloop
import lru_cache
import errno


BUF_SIZE = 65536


def parse_header(data):
    addrtype = ord(data[0])
    dest_addr = None
    dest_port = None
    header_length = 0
    if addrtype == 1:
        if len(data) >= 7:
            dest_addr = socket.inet_ntoa(data[1:5])
            dest_port = struct.unpack('>H', data[5:7])[0]
            header_length = 7
        else:
            logging.warn('[udp] header is too short')
    elif addrtype == 3:
        if len(data) > 2:
            addrlen = ord(data[1])
            if len(data) >= 2 + addrlen:
                dest_addr = data[2:2 + addrlen]
                dest_port = struct.unpack('>H', data[2 + addrlen:4 +
                                          addrlen])[0]
                header_length = 4 + addrlen
            else:
                logging.warn('[udp] header is too short')
        else:
            logging.warn('[udp] header is too short')
    elif addrtype == 4:
        if len(data) >= 19:
            dest_addr = socket.inet_ntop(socket.AF_INET6, data[1:17])
            dest_port = struct.unpack('>H', data[17:19])[0]
            header_length = 19
        else:
            logging.warn('[udp] header is too short')
    else:
        logging.warn('unsupported addrtype %d' % addrtype)
    if dest_addr is None:
        return None
    return (addrtype, dest_addr, dest_port, header_length)


def client_key(a, b, c, d):
    return '%s:%s:%s:%s' % (a, b, c, d)


class UDPRelay(object):
    def __init__(self, listen_addr='127.0.0.1', listen_port=1080,
                 remote_addr='127.0.0.1', remote_port=8387, password=None,
                 method='table', timeout=300, is_local=True):
        self._listen_addr = listen_addr
        self._listen_port = listen_port
        self._remote_addr = remote_addr
        self._remote_port = remote_port
        self._password = password
        self._method = method
        self._timeout = timeout
        self._is_local = is_local
        self._cache = lru_cache.LRUCache(timeout=timeout,
                                         close_callback=self._close_client)
        self._client_fd_to_server_addr = lru_cache.LRUCache(timeout=timeout)
        self._closed = False

        addrs = socket.getaddrinfo(self._listen_addr, self._listen_port, 0,
                                   socket.SOCK_DGRAM, socket.SOL_UDP)
        if len(addrs) == 0:
            raise Exception("can't get addrinfo for %s:%d" %
                            (self._listen_addr, self._listen_port))
        af, socktype, proto, canonname, sa = addrs[0]
        server_socket = socket.socket(af, socktype, proto)
        server_socket.bind((self._listen_addr, self._listen_port))
        server_socket.setblocking(False)
        self._server_socket = server_socket

    def _close_client(self, client):
        if hasattr(client, 'close'):
            self._eventloop.remove(client)
            client.close()
        else:
            # just an address
            pass

    def _handle_server(self):
        server = self._server_socket
        data, r_addr = server.recvfrom(BUF_SIZE)
        if self._is_local:
            frag = ord(data[2])
            if frag != 0:
                logging.warn('drop a message since frag is not 0')
                return
            else:
                data = data[3:]
        else:
            # decrypt data
            data = encrypt.encrypt_all(self._password, self._method, 0, data)
            if not data:
                return
        header_result = parse_header(data)
        if header_result is None:
            return
        addrtype, dest_addr, dest_port, header_length = header_result

        if self._is_local:
            server_addr, server_port = self._remote_addr, self._remote_port
        else:
            server_addr, server_port = dest_addr, dest_port

        key = client_key(r_addr[0], r_addr[1], dest_addr, dest_port)
        client = self._cache.get(key, None)
        if not client:
            # TODO async getaddrinfo
            addrs = socket.getaddrinfo(server_addr, server_port, 0,
                                       socket.SOCK_DGRAM, socket.SOL_UDP)
            if addrs:
                af, socktype, proto, canonname, sa = addrs[0]
                client = socket.socket(af, socktype, proto)
                client.setblocking(False)
                self._cache[key] = client
                self._client_fd_to_server_addr[client.fileno()] = r_addr
            else:
                # drop
                return
            self._eventloop.add(client, eventloop.POLL_IN)

        data = data[header_length:]
        if not data:
            return
        if self._is_local:
            data = encrypt.encrypt_all(self._password, self._method, 1, data)
            if not data:
                return
        try:
            client.sendto(data, (server_addr, server_port))
        except IOError as e:
            err = eventloop.errno_from_exception(e)
            if err in (errno.EINPROGRESS, errno.EAGAIN):
                pass
            else:
                logging.error(e)

    def _handle_client(self, sock):
        data, r_addr = sock.recvfrom(BUF_SIZE)
        if not self._is_local:
            addrlen = len(r_addr[0])
            if addrlen > 255:
                # drop
                return
            data = '\x03' + chr(addrlen) + r_addr[0] + \
                   struct.pack('>H', r_addr[1]) + data
            response = encrypt.encrypt_all(self._password, self._method, 1,
                                           data)
            if not response:
                return
        else:
            data = encrypt.encrypt_all(self._password, self._method, 0,
                                       data)
            if not data:
                return
            header_result = parse_header(data)
            if header_result is None:
                return
            # addrtype, dest_addr, dest_port, header_length = header_result
            response = '\x00\x00\x00' + data
        client_addr = self._client_fd_to_server_addr.get(sock.fileno(), None)
        if client_addr:
            self._server_socket.sendto(response, client_addr)
        else:
            # this packet is from somewhere else we know
            # simply drop that packet
            pass

    def _run(self):
        server_socket = self._server_socket
        self._eventloop = eventloop.EventLoop()
        self._eventloop.add(server_socket, eventloop.POLL_IN)
        last_time = time.time()
        while not self._closed:
            try:
                events = self._eventloop.poll(10)
            except (OSError, IOError) as e:
                if eventloop.errno_from_exception(e) == errno.EPIPE:
                    # Happens when the client closes the connection
                    continue
                else:
                    logging.error(e)
                    continue
            for sock, event in events:
                if sock == self._server_socket:
                    self._handle_server()
                else:
                    self._handle_client(sock)
            now = time.time()
            if now - last_time > 3.5:
                self._cache.sweep()
            if now - last_time > 7:
                self._client_fd_to_server_addr.sweep()
                last_time = now

    def start(self):
        if self._closed:
            raise Exception('closed')
        t = threading.Thread(target=self._run)
        t.setName('UDPThread')
        t.setDaemon(False)
        t.start()
        self._thread = t

    def close(self):
        self._closed = True
        self._server_socket.close()

    def thread(self):
        return self._thread

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 clowwindy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import socket
import logging


def inet_ntop(family, ipstr):
    if family == socket.AF_INET:
        return socket.inet_ntoa(ipstr)
    elif family == socket.AF_INET6:
        v6addr = ':'.join(('%02X%02X' % (ord(i), ord(j)))
                          for i, j in zip(ipstr[::2], ipstr[1::2]))
        return v6addr


def inet_pton(family, addr):
    if family == socket.AF_INET:
        return socket.inet_aton(addr)
    elif family == socket.AF_INET6:
        if '.' in addr:  # a v4 addr
            v4addr = addr[addr.rindex(':') + 1:]
            v4addr = socket.inet_aton(v4addr)
            v4addr = map(lambda x: ('%02X' % ord(x)), v4addr)
            v4addr.insert(2, ':')
            newaddr = addr[:addr.rindex(':') + 1] + ''.join(v4addr)
            return inet_pton(family, newaddr)
        dbyts = [0] * 8  # 8 groups
        grps = addr.split(':')
        for i, v in enumerate(grps):
            if v:
                dbyts[i] = int(v, 16)
            else:
                for j, w in enumerate(grps[::-1]):
                    if w:
                        dbyts[7 - j] = int(w, 16)
                    else:
                        break
                break
        return ''.join((chr(i // 256) + chr(i % 256)) for i in dbyts)
    else:
        raise RuntimeError("What family?")


if not hasattr(socket, 'inet_pton'):
    socket.inet_pton = inet_pton

if not hasattr(socket, 'inet_ntop'):
    socket.inet_ntop = inet_ntop

def find_config():
    config_path = 'config.json'
    if os.path.exists(config_path):
        return config_path
    config_path = os.path.join(os.path.dirname(__file__), '../', 'config.json')
    if os.path.exists(config_path):
        return config_path
    return None


def check_config(config):
    if config.get('local_address', '') in ['0.0.0.0']:
        logging.warn('warning: local set to listen 0.0.0.0, which is not safe')
    if config.get('server', '') in ['127.0.0.1', 'localhost']:
        logging.warn('warning: server set to listen %s:%s, are you sure?' %
                     (config['server'], config['server_port']))
    if (config.get('method', '') or '').lower() == 'rc4':
        logging.warn('warning: RC4 is not safe; please use a safer cipher, '
                     'like AES-256-CFB')
    if (int(config.get('timeout', 300)) or 300) < 100:
        logging.warn('warning: your timeout %d seems too short' %
                     int(config.get('timeout')))
    if (int(config.get('timeout', 300)) or 300) > 600:
        logging.warn('warning: your timeout %d seems too long' %
                     int(config.get('timeout')))


def print_local_help():
    print '''usage: sslocal [-h] -s SERVER_ADDR -p SERVER_PORT [-b LOCAL_ADDR]
                -l LOCAL_PORT -k PASSWORD -m METHOD [-t TIMEOUT] [-c CONFIG]
                [--fast-open]

optional arguments:
  -h, --help            show this help message and exit
  -s SERVER_ADDR        server address
  -p SERVER_PORT        server port
  -b LOCAL_ADDR         local binding address, default is 127.0.0.1
  -l LOCAL_PORT         local port
  -k PASSWORD           password
  -m METHOD             encryption method, for example, aes-256-cfb
  -t TIMEOUT            timeout in seconds
  -c CONFIG             path to config file
  --fast-open           use TCP_FASTOPEN, requires Linux 3.7+
'''


def print_server_help():
    print '''usage: ssserver [-h] -s SERVER_ADDR -p SERVER_PORT -k PASSWORD
                -m METHOD [-t TIMEOUT] [-c CONFIG] [--fast-open]

optional arguments:
  -h, --help            show this help message and exit
  -s SERVER_ADDR        server address
  -p SERVER_PORT        server port
  -k PASSWORD           password
  -m METHOD             encryption method, for example, aes-256-cfb
  -t TIMEOUT            timeout in seconds
  -c CONFIG             path to config file
  --fast-open           use TCP_FASTOPEN, requires Linux 3.7+
  --workers WORKERS     number of workers, available on Unix/Linux
'''
########NEW FILE########
__FILENAME__ = test
#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import signal
import sys
import select
import struct
import hashlib
import string
import time
from subprocess import Popen, PIPE

target1 = [
    [60, 53, 84, 138, 217, 94, 88, 23, 39, 242, 219, 35, 12, 157, 165, 181, 255, 143, 83, 247, 162, 16, 31, 209, 190,
     171, 115, 65, 38, 41, 21, 245, 236, 46, 121, 62, 166, 233, 44, 154, 153, 145, 230, 49, 128, 216, 173, 29, 241, 119,
     64, 229, 194, 103, 131, 110, 26, 197, 218, 59, 204, 56, 27, 34, 141, 221, 149, 239, 192, 195, 24, 155, 170, 183, 11
        , 254, 213, 37, 137, 226, 75, 203, 55, 19, 72, 248, 22, 129, 33, 175, 178, 10, 198, 71, 77, 36, 113, 167, 48, 2,
     117, 140, 142, 66, 199, 232, 243, 32, 123, 54, 51, 82, 57, 177, 87, 251, 150, 196, 133, 5, 253, 130, 8, 184, 14,
     152, 231, 3, 186, 159, 76, 89, 228, 205, 156, 96, 163, 146, 18, 91, 132, 85, 80, 109, 172, 176, 105, 13, 50, 235,
     127, 0, 189, 95, 98, 136, 250, 200, 108, 179, 211, 214, 106, 168, 78, 79, 74, 210, 30, 73, 201, 151, 208, 114, 101,
     174, 92, 52, 120, 240, 15, 169, 220, 182, 81, 224, 43, 185, 40, 99, 180, 17, 212, 158, 42, 90, 9, 191, 45, 6, 25, 4
        , 222, 67, 126, 1, 116, 124, 206, 69, 61, 7, 68, 97, 202, 63, 244, 20, 28, 58, 93, 134, 104, 144, 227, 147, 102,
     118, 135, 148, 47, 238, 86, 112, 122, 70, 107, 215, 100, 139, 223, 225, 164, 237, 111, 125, 207, 160, 187, 246, 234
        , 161, 188, 193, 249, 252],
    [151, 205, 99, 127, 201, 119, 199, 211, 122, 196, 91, 74, 12, 147, 124, 180, 21, 191, 138, 83, 217, 30, 86, 7, 70,
     200, 56, 62, 218, 47, 168, 22, 107, 88, 63, 11, 95, 77, 28, 8, 188, 29, 194, 186, 38, 198, 33, 230, 98, 43, 148,
     110, 177, 1, 109, 82, 61, 112, 219, 59, 0, 210, 35, 215, 50, 27, 103, 203, 212, 209, 235, 93, 84, 169, 166, 80, 130
        , 94, 164, 165, 142, 184, 111, 18, 2, 141, 232, 114, 6, 131, 195, 139, 176, 220, 5, 153, 135, 213, 154, 189, 238
        , 174, 226, 53, 222, 146, 162, 236, 158, 143, 55, 244, 233, 96, 173, 26, 206, 100, 227, 49, 178, 34, 234, 108,
     207, 245, 204, 150, 44, 87, 121, 54, 140, 118, 221, 228, 155, 78, 3, 239, 101, 64, 102, 17, 223, 41, 137, 225, 229,
     66, 116, 171, 125, 40, 39, 71, 134, 13, 193, 129, 247, 251, 20, 136, 242, 14, 36, 97, 163, 181, 72, 25, 144, 46,
     175, 89, 145, 113, 90, 159, 190, 15, 183, 73, 123, 187, 128, 248, 252, 152, 24, 197, 68, 253, 52, 69, 117, 57, 92,
     104, 157, 170, 214, 81, 60, 133, 208, 246, 172, 23, 167, 160, 192, 76, 161, 237, 45, 4, 58, 10, 182, 65, 202, 240,
     185, 241, 79, 224, 132, 51, 42, 126, 105, 37, 250, 149, 32, 243, 231, 67, 179, 48, 9, 106, 216, 31, 249, 19, 85,
     254, 156, 115, 255, 120, 75, 16]]

target2 = [
    [124, 30, 170, 247, 27, 127, 224, 59, 13, 22, 196, 76, 72, 154, 32, 209, 4, 2, 131, 62, 101, 51, 230, 9, 166, 11, 99
        , 80, 208, 112, 36, 248, 81, 102, 130, 88, 218, 38, 168, 15, 241, 228, 167, 117, 158, 41, 10, 180, 194, 50, 204,
     243, 246, 251, 29, 198, 219, 210, 195, 21, 54, 91, 203, 221, 70, 57, 183, 17, 147, 49, 133, 65, 77, 55, 202, 122,
     162, 169, 188, 200, 190, 125, 63, 244, 96, 31, 107, 106, 74, 143, 116, 148, 78, 46, 1, 137, 150, 110, 181, 56, 95,
     139, 58, 3, 231, 66, 165, 142, 242, 43, 192, 157, 89, 175, 109, 220, 128, 0, 178, 42, 255, 20, 214, 185, 83, 160,
     253, 7, 23, 92, 111, 153, 26, 226, 33, 176, 144, 18, 216, 212, 28, 151, 71, 206, 222, 182, 8, 174, 205, 201, 152,
     240, 155, 108, 223, 104, 239, 98, 164, 211, 184, 34, 193, 14, 114, 187, 40, 254, 12, 67, 93, 217, 6, 94, 16, 19, 82
        , 86, 245, 24, 197, 134, 132, 138, 229, 121, 5, 235, 238, 85, 47, 103, 113, 179, 69, 250, 45, 135, 156, 25, 61,
     75, 44, 146, 189, 84, 207, 172, 119, 53, 123, 186, 120, 171, 68, 227, 145, 136, 100, 90, 48, 79, 159, 149, 39, 213,
     236, 126, 52, 60, 225, 199, 105, 73, 233, 252, 118, 215, 35, 115, 64, 37, 97, 129, 161, 177, 87, 237, 141, 173, 191
        , 163, 140, 234, 232, 249],
    [117, 94, 17, 103, 16, 186, 172, 127, 146, 23, 46, 25, 168, 8, 163, 39, 174, 67, 137, 175, 121, 59, 9, 128, 179, 199
        , 132, 4, 140, 54, 1, 85, 14, 134, 161, 238, 30, 241, 37, 224, 166, 45, 119, 109, 202, 196, 93, 190, 220, 69, 49
        , 21, 228, 209, 60, 73, 99, 65, 102, 7, 229, 200, 19, 82, 240, 71, 105, 169, 214, 194, 64, 142, 12, 233, 88, 201
        , 11, 72, 92, 221, 27, 32, 176, 124, 205, 189, 177, 246, 35, 112, 219, 61, 129, 170, 173, 100, 84, 242, 157, 26,
     218, 20, 33, 191, 155, 232, 87, 86, 153, 114, 97, 130, 29, 192, 164, 239, 90, 43, 236, 208, 212, 185, 75, 210, 0,
     81, 227, 5, 116, 243, 34, 18, 182, 70, 181, 197, 217, 95, 183, 101, 252, 248, 107, 89, 136, 216, 203, 68, 91, 223,
     96, 141, 150, 131, 13, 152, 198, 111, 44, 222, 125, 244, 76, 251, 158, 106, 24, 42, 38, 77, 2, 213, 207, 249, 147,
     113, 135, 245, 118, 193, 47, 98, 145, 66, 160, 123, 211, 165, 78, 204, 80, 250, 110, 162, 48, 58, 10, 180, 55, 231,
     79, 149, 74, 62, 50, 148, 143, 206, 28, 15, 57, 159, 139, 225, 122, 237, 138, 171, 36, 56, 115, 63, 144, 154, 6,
     230, 133, 215, 41, 184, 22, 104, 254, 234, 253, 187, 226, 247, 188, 156, 151, 40, 108, 51, 83, 178, 52, 3, 31, 255,
     195, 53, 235, 126, 167, 120]]


def get_table(key):
    m = hashlib.md5()
    m.update(key)
    s = m.digest()
    (a, b) = struct.unpack('<QQ', s)
    table = [c for c in string.maketrans('', '')]
    for i in xrange(1, 1024):
        table.sort(lambda x, y: int(a % (ord(x) + i) - a % (ord(y) + i)))
    return table

encrypt_table = ''.join(get_table('foobar!'))
decrypt_table = string.maketrans(encrypt_table, string.maketrans('', ''))

for i in range(0, 256):
    assert(target1[0][i] == ord(encrypt_table[i]))
    assert(target1[1][i] == ord(decrypt_table[i]))

encrypt_table = ''.join(get_table('barfoo!'))
decrypt_table = string.maketrans(encrypt_table, string.maketrans('', ''))

for i in range(0, 256):
    assert(target2[0][i] == ord(encrypt_table[i]))
    assert(target2[1][i] == ord(decrypt_table[i]))
p1 = Popen(['python', 'shadowsocks/server.py', '-c', sys.argv[-1]], shell=False, bufsize=0, stdin=PIPE, 
    stdout=PIPE, stderr=PIPE, close_fds=True)
p2 = Popen(['python', 'shadowsocks/local.py', '-c', sys.argv[-1]], shell=False, bufsize=0, stdin=PIPE,
    stdout=PIPE, stderr=PIPE, close_fds=True)
p3 = None

print 'encryption test passed'

try:
    local_ready = False
    server_ready = False
    fdset = [p1.stdout, p2.stdout, p1.stderr, p2.stderr]
    while True:
        r, w, e = select.select(fdset, [], fdset)
        if e:
            break
            
        for fd in r:
            line = fd.readline()
            sys.stdout.write(line)
            if line.find('starting local') >= 0:
                local_ready = True
            if line.find('starting server') >= 0:
                server_ready = True

        if local_ready and server_ready and p3 is None:
            time.sleep(1)
            p3 = Popen(['curl', 'http://www.example.com/', '-v', '-L',
                        '--socks5-hostname', '127.0.0.1:1080'], shell=False,
                        bufsize=0,  close_fds=True)
            break
            
    if p3 is not None:
        r = p3.wait()
        if r == 0:
            print 'test passed'
        sys.exit(r)
    
finally:
    for p in [p1, p2]:
        try:
            os.kill(p.pid, signal.SIGTERM)
        except OSError:
            pass
   
sys.exit(-1)

########NEW FILE########
__FILENAME__ = test_latency
#!/usr/bin/python

import sys
import time


before = time.time()

for line in sys.stdin:
    if 'HTTP/1.1 ' in line:
        diff = time.time() - before
        print 'headline %dms' % (diff * 1000)


########NEW FILE########
