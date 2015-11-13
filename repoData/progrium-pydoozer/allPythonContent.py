__FILENAME__ = client
import logging
import os
import random
import struct

import gevent
import gevent.event
import gevent.socket

from msg_pb2 import Response
from msg_pb2 import Request

REQUEST_TIMEOUT = 2.0

DEFAULT_RETRY_WAIT = 2.0
"""Default connection retry waiting time (seconds)"""

DEFAULT_URI = "doozer:?%s" % "&".join([
    "ca=127.0.0.1:8046",
    "ca=127.0.0.1:8041",
    "ca=127.0.0.1:8042",
    "ca=127.0.0.1:8043",
    ])

_spawner = gevent.spawn


class ConnectError(Exception): pass
class ResponseError(Exception):
    def __init__(self, response, request):
        self.code = response.err_code
        self.detail = response.err_detail
        self.response = response
        self.request = request

    def __str__(self):
        return str(pb_dict(self.request))

class TagInUse(ResponseError): pass
class UnknownVerb(ResponseError): pass
class Readonly(ResponseError): pass
class TooLate(ResponseError): pass
class RevMismatch(ResponseError): pass
class BadPath(ResponseError): pass
class MissingArg(ResponseError): pass
class Range(ResponseError): pass
class NotDirectory(ResponseError): pass
class IsDirectory(ResponseError): pass
class NoEntity(ResponseError): pass


def response_exception(response):
    """Takes a response, returns proper exception if it has an error code"""
    exceptions = {
        Response.TAG_IN_USE: TagInUse, Response.UNKNOWN_VERB: UnknownVerb,
        Response.READONLY: Readonly, Response.TOO_LATE: TooLate, 
        Response.REV_MISMATCH: RevMismatch, Response.BAD_PATH: BadPath,
        Response.MISSING_ARG: MissingArg, Response.RANGE: Range,
        Response.NOTDIR: NotDirectory, Response.ISDIR: IsDirectory,
        Response.NOENT: NoEntity, }
    if 'err_code' in [field.name for field, value in response.ListFields()]:
        return exceptions[response.err_code]
    else:
        return None


def pb_dict(message):
    """Create dict representation of a protobuf message"""
    return dict([(field.name, value) for field, value in message.ListFields()])


def parse_uri(uri):
    """Parse the doozerd URI scheme to get node addresses"""
    if uri.startswith("doozer:?"):
        before, params = uri.split("?", 1)
        addrs = []
        for param in params.split("&"):
            key, value = param.split("=", 1)
            if key == "ca":
                addrs.append(value)
        return addrs
    else:
        raise ValueError("invalid doozerd uri")


def connect(uri=None, timeout=None):
    """
    Start a Doozer client connection

    @param uri: str|None, Doozer URI
    @param timeout: float|None, connection timeout in seconds (per address)
    """

    uri = uri or os.environ.get("DOOZER_URI", DEFAULT_URI)
    addrs = parse_uri(uri)
    if not addrs:
        raise ValueError("there were no addrs supplied in the uri (%s)" % uri)
    return Client(addrs, timeout)


class Connection(object):
    def __init__(self, addrs=None, timeout=None):
        """
        @param timeout: float|None, connection timeout in seconds (per address)
        """
        self._logger = logging.getLogger('pydoozer.Connection')
        self._logger.debug('__init__(%s)', addrs)

        if addrs is None:
            addrs = []
        self.addrs = addrs
        self.addrs_index = 0
        """Next address to connect to in self.addrs"""

        self.pending = {}
        self.loop = None
        self.sock = None
        self.address = None
        self.timeout = timeout
        self.ready = gevent.event.Event()

        # Shuffle the addresses so all clients don't connect to the
        # same node in the cluster.
        random.shuffle(addrs)

    def connect(self):
        self.reconnect()

    def reconnect(self, kill_loop=True):
        """
        Reconnect to the cluster.

        @param kill_loop: bool, kill the current receive loop
        """

        self._logger.debug('reconnect()')

        self.disconnect(kill_loop)

        # Default to the socket timeout
        retry_wait = self.timeout or gevent.socket.getdefaulttimeout() or DEFAULT_RETRY_WAIT
        for retry in range(5):
            addrs_left = len(self.addrs)
            while addrs_left:
                try:
                    parts = self.addrs[self.addrs_index].split(':')
                    self.addrs_index = (self.addrs_index + 1) % len(self.addrs)
                    host = parts[0]
                    port = parts[1] if len(parts) > 1 else 8046
                    self.address = "%s:%s" % (host, port)
                    self._logger.debug('Connecting to %s...', self.address)
                    self.sock = gevent.socket.create_connection((host, int(port)),
                                                                timeout=self.timeout)
                    self._logger.debug('Connection successful')

                    # Reset the timeout on the connection so it
                    # doesn't make .recv() and .send() timeout.
                    self.sock.settimeout(None)
                    self.ready.set()

                    # Any commands that were in transit when the
                    # connection was lost is obviously not getting a
                    # reply. Retransmit them.
                    self._retransmit_pending()
                    self.loop = _spawner(self._recv_loop)
                    return

                except IOError, e:
                    self._logger.info('Failed to connect to %s (%s)', self.address, e)
                    pass
                addrs_left -= 1

            self._logger.debug('Waiting %d seconds to reconnect', retry_wait)
            gevent.sleep(retry_wait)
            retry_wait *= 2

        self._logger.error('Could not connect to any of the defined addresses')
        raise ConnectError("Can't connect to any of the addresses: %s" % self.addrs)

    def disconnect(self, kill_loop=True):
        """
        Disconnect current connection.

        @param kill_loop: bool, Kill the current receive loop
        """
        self._logger.debug('disconnect()')

        if kill_loop and self.loop:
            self._logger.debug('killing loop')
            self.loop.kill()
            self.loop = None
        if self.sock:
            self._logger.debug('closing connection')
            self.sock.close()
            self.sock = None

        self._logger.debug('clearing ready signal')
        self.ready.clear()
        self.address = None

    def send(self, request, retry=True):
        request.tag = 0
        while request.tag in self.pending:
            request.tag += 1
            request.tag %= 2**31

        # Create and send request
        data = request.SerializeToString()
        data_len = len(data)
        head = struct.pack(">I", data_len)
        packet = ''.join([head, data])
        entry = self.pending[request.tag] = {
            'event': gevent.event.AsyncResult(),
            'packet': packet,
        }
        self._logger.debug('Sending packet, tag: %d, len: %d', request.tag, data_len)
        try:
            self._send_pack(packet, retry)

            # Wait for response
            try:
                response = entry['event'].get(timeout=REQUEST_TIMEOUT)
            except gevent.timeout.Timeout:
                if retry:
                    # If we get a timeout (which is conservatively high),
                    # something is probably wrong with the
                    # connection/instance so reconnect to the
                    # cluster. This will trigger a retransmit of the
                    # packages in transit.
                    logging.debug('Got timeout on receive, triggering reconnect()')
                    self.reconnect()
                    response = entry['event'].get(timeout=REQUEST_TIMEOUT)

        except Exception:
            raise
        finally:
            # We want to ensure that we always clear the pending
            # request, since nothing is now waiting for the answer.
            del self.pending[request.tag]

        exception = response_exception(response)
        if exception:
            raise exception(response, request)
        return response

    def _send_pack(self, packet, retry=True):
        """
        Send the given packet to the currently connected node.

        @param packet: struct, packet to send
        @param retry: bool, retry the sending once
        """
        try:
            self.ready.wait(timeout=2)
            self.sock.send(packet)
        except IOError, e:
            self._logger.warning('Error sending packet (%s)', e)
            self.reconnect()
            if retry:
                self._logger.debug('Retrying sending packet')
                self.ready.wait()
                self.sock.send(packet)
            else:
                self._logger.warning('Failed retrying to send packet')
                raise e

    def _recv_loop(self):
        self._logger.debug('_recv_loop(%s)', self.address)

        while True:
            try:
                head = self.sock.recv(4)
                length = struct.unpack(">I", head)[0]
                data = self.sock.recv(length)
                response = Response()
                response.ParseFromString(data)
                self._logger.debug('Received packet, tag: %d, len: %d', response.tag, length)
                if response.tag in self.pending:
                    self.pending[response.tag]['event'].set(response)
            except struct.error, e:
                self._logger.warning('Got invalid packet from server (%s)', e)
                # If some extra bytes are sent, just reconnect. 
                # This is related to this bug: 
                # https://github.com/ha/doozerd/issues/5
                break
            except IOError, e:
                self._logger.warning('Lost connection? (%s)', e)
                break

        # Note: .reconnect() will spawn a new loop
        self.reconnect(kill_loop=False)

    def _retransmit_pending(self):
        """
        Retransmits all pending packets.
        """

        for i in xrange(0, len(self.pending)):
            self._logger.debug('Retransmitting packet')
            try:
                self._send_pack(self.pending[i]['packet'], retry=False)
            except Exception:
                # If we can't even retransmit the package, we give
                # up. The consumer will timeout.
                logging.warning('Got exception retransmitting package')


class Client(object):
    def __init__(self, addrs=None, timeout=None):
        """
        @param timeout: float|None, connection timeout in seconds (per address)
        """
        if addrs is None:
            addrs = []
        self.connection = Connection(addrs, timeout)
        self.connect()

    def rev(self):
        request = Request(verb=Request.REV)
        return self.connection.send(request)

    def set(self, path, value, rev):
        request = Request(path=path, value=value, rev=rev, verb=Request.SET)
        return self.connection.send(request, retry=False)

    def get(self, path, rev=None):
        request = Request(path=path, verb=Request.GET)
        if rev:
            request.rev = rev
        return self.connection.send(request)

    def delete(self, path, rev):
        request = Request(path=path, rev=rev, verb=Request.DEL)
        return self.connection.send(request, retry=False)

    def wait(self, path, rev):
        request = Request(path=path, rev=rev, verb=Request.WAIT)
        return self.connection.send(request)

    def stat(self, path, rev):
        request = Request(path=path, rev=rev, verb=Request.STAT)
        return self.connection.send(request)

    def access(self, secret):
        request = Request(value=secret, verb=Request.ACCESS)
        return self.connection.send(request)

    def _getdir(self, path, offset=0, rev=None):
        request = Request(path=path, offset=offset, verb=Request.GETDIR)
        if rev:
            request.rev = rev
        return self.connection.send(request)

    def _walk(self, path, offset=0, rev=None):
        request = Request(path=path, offset=offset, verb=Request.WALK)
        if rev:
            request.rev = rev
        return self.connection.send(request)

    def watch(self, path, rev):
        raise NotImplementedError()

    def _list(self, method, path, offset=None, rev=None):
        offset = offset or 0
        entities = []
        try:
            while True:
                response = getattr(self, method)(path, offset, rev)
                entities.append(response)
                offset += 1
        except ResponseError, e:
            if e.code == Response.RANGE:
                return entities
            else:
                raise e

    def walk(self, path, offset=None, rev=None):
        return self._list('_walk', path, offset, rev)

    def getdir(self, path, offset=None, rev=None):
        return self._list('_getdir', path, offset, rev)

    def disconnect(self):
        self.connection.disconnect()

    def connect(self):
        self.connection.connect()

########NEW FILE########
__FILENAME__ = msg_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)



DESCRIPTOR = descriptor.FileDescriptor(
  name='msg.proto',
  package='server',
  serialized_pb='\n\tmsg.proto\x12\x06server\"\xf2\x01\n\x07Request\x12\x0b\n\x03tag\x18\x01 \x01(\x05\x12\"\n\x04verb\x18\x02 \x01(\x0e\x32\x14.server.Request.Verb\x12\x0c\n\x04path\x18\x04 \x01(\t\x12\r\n\x05value\x18\x05 \x01(\x0c\x12\x11\n\tother_tag\x18\x06 \x01(\x05\x12\x0e\n\x06offset\x18\x07 \x01(\x05\x12\x0b\n\x03rev\x18\t \x01(\x03\"i\n\x04Verb\x12\x07\n\x03GET\x10\x01\x12\x07\n\x03SET\x10\x02\x12\x07\n\x03\x44\x45L\x10\x03\x12\x07\n\x03REV\x10\x05\x12\x08\n\x04WAIT\x10\x06\x12\x07\n\x03NOP\x10\x07\x12\x08\n\x04WALK\x10\t\x12\n\n\x06GETDIR\x10\x0e\x12\x08\n\x04STAT\x10\x10\x12\n\n\x06\x41\x43\x43\x45SS\x10\x63\"\xc8\x02\n\x08Response\x12\x0b\n\x03tag\x18\x01 \x01(\x05\x12\r\n\x05\x66lags\x18\x02 \x01(\x05\x12\x0b\n\x03rev\x18\x03 \x01(\x03\x12\x0c\n\x04path\x18\x05 \x01(\t\x12\r\n\x05value\x18\x06 \x01(\x0c\x12\x0b\n\x03len\x18\x08 \x01(\x05\x12&\n\x08\x65rr_code\x18\x64 \x01(\x0e\x32\x14.server.Response.Err\x12\x12\n\nerr_detail\x18\x65 \x01(\t\"\xac\x01\n\x03\x45rr\x12\t\n\x05OTHER\x10\x7f\x12\x0e\n\nTAG_IN_USE\x10\x01\x12\x10\n\x0cUNKNOWN_VERB\x10\x02\x12\x0c\n\x08READONLY\x10\x03\x12\x0c\n\x08TOO_LATE\x10\x04\x12\x10\n\x0cREV_MISMATCH\x10\x05\x12\x0c\n\x08\x42\x41\x44_PATH\x10\x06\x12\x0f\n\x0bMISSING_ARG\x10\x07\x12\t\n\x05RANGE\x10\x08\x12\n\n\x06NOTDIR\x10\x14\x12\t\n\x05ISDIR\x10\x15\x12\t\n\x05NOENT\x10\x16')



_REQUEST_VERB = descriptor.EnumDescriptor(
  name='Verb',
  full_name='server.Request.Verb',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='GET', index=0, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='SET', index=1, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='DEL', index=2, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='REV', index=3, number=5,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='WAIT', index=4, number=6,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='NOP', index=5, number=7,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='WALK', index=6, number=9,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='GETDIR', index=7, number=14,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='STAT', index=8, number=16,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ACCESS', index=9, number=99,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=159,
  serialized_end=264,
)

_RESPONSE_ERR = descriptor.EnumDescriptor(
  name='Err',
  full_name='server.Response.Err',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='OTHER', index=0, number=127,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='TAG_IN_USE', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='UNKNOWN_VERB', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='READONLY', index=3, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='TOO_LATE', index=4, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='REV_MISMATCH', index=5, number=5,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='BAD_PATH', index=6, number=6,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='MISSING_ARG', index=7, number=7,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='RANGE', index=8, number=8,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='NOTDIR', index=9, number=20,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ISDIR', index=10, number=21,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='NOENT', index=11, number=22,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=423,
  serialized_end=595,
)


_REQUEST = descriptor.Descriptor(
  name='Request',
  full_name='server.Request',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='tag', full_name='server.Request.tag', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='verb', full_name='server.Request.verb', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='path', full_name='server.Request.path', index=2,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='value', full_name='server.Request.value', index=3,
      number=5, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='other_tag', full_name='server.Request.other_tag', index=4,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='offset', full_name='server.Request.offset', index=5,
      number=7, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='rev', full_name='server.Request.rev', index=6,
      number=9, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _REQUEST_VERB,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=22,
  serialized_end=264,
)


_RESPONSE = descriptor.Descriptor(
  name='Response',
  full_name='server.Response',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='tag', full_name='server.Response.tag', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='flags', full_name='server.Response.flags', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='rev', full_name='server.Response.rev', index=2,
      number=3, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='path', full_name='server.Response.path', index=3,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='value', full_name='server.Response.value', index=4,
      number=6, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='len', full_name='server.Response.len', index=5,
      number=8, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='err_code', full_name='server.Response.err_code', index=6,
      number=100, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=127,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='err_detail', full_name='server.Response.err_detail', index=7,
      number=101, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _RESPONSE_ERR,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=267,
  serialized_end=595,
)

_REQUEST.fields_by_name['verb'].enum_type = _REQUEST_VERB
_REQUEST_VERB.containing_type = _REQUEST;
_RESPONSE.fields_by_name['err_code'].enum_type = _RESPONSE_ERR
_RESPONSE_ERR.containing_type = _RESPONSE;
DESCRIPTOR.message_types_by_name['Request'] = _REQUEST
DESCRIPTOR.message_types_by_name['Response'] = _RESPONSE

class Request(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REQUEST
  
  # @@protoc_insertion_point(class_scope:server.Request)

class Response(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESPONSE
  
  # @@protoc_insertion_point(class_scope:server.Response)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = client
#!/usr/bin/python
import os
import sys
sys.path.append(os.path.dirname(__file__) + "/..")

import doozer

client = doozer.connect()

rev = client.set("/foo", "test", 0).rev
print "Setting /foo to test with rev %s" % rev

foo = client.get("/foo")
print "Got /foo with %s" % foo.value

root = client.getdir("/")
print "Directly under / is %s" % ', '.join([file.path for file in root])

client.delete("/foo", rev)
print "Deleted /foo"

foo = client.get("/foo")
print repr(foo)

walk = client.walk("/**")
for file in walk:
    print ' '.join([file.path, str(file.rev), file.value])

client.disconnect()

########NEW FILE########
__FILENAME__ = doozerdata
#!/usr/bin/python
"""
created by stephan preeker. 2011-10
"""
import doozer
import gevent

from doozer.client import RevMismatch, TooLate, NoEntity, BadPath
from gevent import Timeout

class DoozerData():
    """
    class which stores data to doozerd backend

    locally we store the path -> revision numbers dict

    -all values need to be strings.
    -we watch changes to values.
        in case of a update we call the provided callback method with value.

    on initialization a path/folder can be specified where all keys
    will be stored.
    """

    def __init__(self, client, callback=None, path='/pydooz'):
        self.client = client
        self._folder = path
        self.revisions = {}
        #method called when external source changes value.
        self.callback = callback

        #load existing values.
        walk = client.walk('%s/**' % path)
        for file in walk:
            self.revisions[self.key_path(file.path)] = file.rev

        #start watching for changes.
        if self.callback:
            self.watch()

    def watch(self):
        """
        watch the directory path for changes.
        call callback on change.
        do NOT call callback if it is a change of our own,
        thus when the revision is the same as the rev we have
        stored in out revisions.
        """

        rev =  self.client.rev().rev

        def watchjob(rev):
            change = None

            while True:
                try:
                    change = self.client.wait("%s/**" % self._folder, rev)
                except Timeout:
                    rev = self.client.rev().rev
                    change = None

                if change:
                    self._handle_change(change)
                    rev = change.rev+1
                #print '.....', rev

        self.watchjob = gevent.spawn(watchjob, rev)

    def _handle_change(self, change):
        """
        A change has been watched. deal with it.
        """
        #get the last part of the path.
        key_path = self.key_path(change.path)

        print 'handle change', self.revisions.get(key_path, 0), change.rev

        if self._old_or_delete(key_path, change):
            return

        print change.path
        self.revisions[key_path] = change.rev
        #create or update route.
        if change.flags == 4:
            self.revisions[key_path] = change.rev
            self.callback(change.value)
            return

        print 'i could get here ...if i saw my own/old delete.'
        print change

    def _old_or_delete(self, key_path, change):
        """
        If the change is done by ourselves or already seen
        we don't have to do a thing.
        if change is a delete not from outselves call the callback.
        """
        if key_path in self.revisions:
            #check if we already have this change.
            if self.revisions[key_path] == change.rev:
                return True
            #check if it is an delete action.
            #if key_path is still in revisions it is not our
            #own or old delete action.
            if change.flags == 8:
                print 'got delete!!'
                self.revisions.pop(key_path)
                self.callback(change.value, path=key_path, destroy=True)
                return True

        return False

    def get(self, key_path):
        """
        get the latest data for path.

        get the local revision number
        if revision revnumber does not match??
           -SUCCEED and update rev number.
        return the doozer data
        """
        rev = 0
        if key_path in self.revisions:
            rev = self.revisions[key_path]
        try:
            return self.client.get(self.folder(key_path), rev).value
        except RevMismatch:
            print 'revision mismach..'
            item = self.client.get(self.folder(key_path))
            self.revisions[key_path] = item.rev
            return item.value

    def set(self, key_path, value):
        """
        set a value, BUT check if you have the latest revision.
        """
        if not isinstance(value, str):
            raise TypeError('Keywords for this object must be strings. You supplied %s' % type(value))

        rev = 0
        if key_path in self.revisions:
            rev = self.revisions[key_path]
        self._set(key_path, value, rev)

    def _set(self, key_path, value, rev):
        try:
            newrev = self.client.set(self.folder(key_path), value, rev)
            self.revisions[key_path] = newrev.rev
            print self.revisions[key_path]
            print 'setting %s with rev %s oldrev %s' % (key_path, newrev.rev, rev)
        except RevMismatch:
            print 'ERROR failed to set %s %s %s' % (key_path, rev, self.revisions[key_path])

    def key_path(self, path):
        return path.split('/')[-1]

    def folder(self, key_path):
        return "%s/%s" % (self._folder, key_path)

    def delete(self, key_path):
        """
        delete path. only with correct latest revision.
        """
        try:
            rev = self.revisions[key_path]
            self.revisions.pop(key_path)
            item = self.client.delete(self.folder(key_path), rev)
        except RevMismatch:
            print 'ERROR!! rev value changed meanwhile!!', item.path, item.value
        except BadPath:
            print 'ERROR!! path is bad.', self.folder(key_path)

    def delete_all(self):
        """ clear all data.
        """
        for path, rev, value in self.items():
            try:
                item = self.client.delete(self.folder(path), rev)
            except RevMismatch:
                item = self.client.delete(self.folder(path))
                print 'value changed meanwhile!!', item.path, item.value
            except TooLate:
                print 'too late..'
                rev = self.client.rev().rev
                item = self.client.delete(self.folder(path), rev)

    def items(self):
        """
        return all current items from doozer.
        update local rev numbers.
        """
        try:
            folder = self.client.getdir(self._folder)
        except NoEntity:
            print 'we are empty'
            folder = []

        for thing in folder:
            item = self.client.get(self.folder(thing.path))
            yield (thing.path, item.rev, item.value)


def print_change(change, path=None, destroy=True):
    print 'watched a change..'
    print  change, destroy, path

def change_value(d):

    gevent.sleep(1)
    d.set('test', '0')
    gevent.sleep(1)
    d.set('test2', '0')
    gevent.sleep(1)
    d.set('test', '1')

#make sure you start doozerd(s).
def test_doozerdata():

    client = doozer.connect()
    d = DoozerData(client, callback=print_change)
    d.set('foo1', 'bar1')
    d.set('foo2', 'bar2')
    d.set('foo3', 'bar3')
    #create a second client

    client2 = doozer.connect()
    d2 = DoozerData(client2, callback=print_change)
    d2.set('foo4', 'bar4')
    #let the second client change values to
    #those should be printed.
    cv = gevent.spawn(change_value, d2)

    for path, rev, value in d.items():
        print path,'->', value

    print d.get('foo1')
    print d.get('foo2')

    d.delete_all()

    #should be empty.
    for di in d.items():
        print di

    #the change value function added content over time..
    gevent.sleep(3)
    print 'data in d1'
    for di in d.items():
        print di
    print 'data in d2'
    for dii in d2.items():
        print dii
    # there is content. in both instances.
    # because the change_value job adds data later.
    cv.join(cv)
    #d.delete_all()

if __name__ == '__main__':
    test_doozerdata()


########NEW FILE########
__FILENAME__ = watch
#!/usr/bin/python
import os
import sys
sys.path.append(os.path.dirname(__file__) + "/..")

import gevent
import doozer

from gevent import Timeout

client = doozer.connect()
rev = client.rev().rev

def watch_test(rev):
    while True:
        try:
            change = client.wait("/watch", rev)
            print change.rev, change.value
            rev = change.rev+1
        except Timeout, t:
            print t
            rev = client.rev().rev
            change = None

watch_job = gevent.spawn(watch_test, rev+1)

for i in range(10):
    gevent.sleep(1)
    rev = client.set("/watch", "test4%d" % i, rev).rev
    print rev


foo = client.get("/watch")
print "Got /watch with %s" % foo.value

gevent.sleep(2)
client.delete("/watch", rev)
print "Deleted /watch"

foo = client.get("/watch")
print foo

client.disconnect()
watch_job.kill()

########NEW FILE########
__FILENAME__ = watch_glob
#!/usr/bin/python
import os
import sys
sys.path.append(os.path.dirname(__file__) + "/..")

import gevent
import doozer
import simplejson

from gevent import Timeout

client = doozer.connect()

#clean out the foo dir.
walk = client.walk("/foo/**")
for node in walk:
    client.delete(node.path, node.rev)

rev = client.set("/foo/bar", "test", 0).rev

def watch_test(rev):
    while True:
        try:
            change = client.wait("/foo/**", rev )
            print "saw change at %s with %s" % ( change.rev, change.value)
            rev = change.rev+1
        except Timeout, t:
            change = None
            print t
            rev = client.rev().rev
            #rev =+1

#spawn the process that watches the foo dir for changes.
watch_job = gevent.spawn(watch_test, rev+1)

#add new data in foo
for i in range(10):
    gevent.sleep(0.5)
    revk = client.set("/foo/bar%d" % i, simplejson.dumps({'data': i}), 0).rev

foo = client.getdir("/foo")

print "Directly under /foo is "
for f in foo:
    print f.path, f.rev,
    print client.get("/foo/"+f.path).value

    dir(f)

client.disconnect()
watch_job.kill()


########NEW FILE########
