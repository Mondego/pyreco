__FILENAME__ = client
# Copyright 2012 Pinterest.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A comprehensive, fast, pure-Python memcached client library.

Basic Usage:
------------

 from pymemcache.client import Client

 client = Client(('localhost', 11211))
 client.set('some_key', 'some_value')
 result = client.get('some_key')


Serialization:
--------------

 import json
 from pymemcache.client import Client

 def json_serializer(key, value):
     if type(value) == str:
         return value, 1
     return json.dumps(value), 2

 def json_deserializer(key, value, flags):
     if flags == 1:
         return value
     if flags == 2:
         return json.loads(value)
     raise Exception("Unknown serialization format")

 client = Client(('localhost', 11211), serializer=json_serializer,
                 deserializer=json_deserializer)
 client.set('key', {'a':'b', 'c':'d'})
 result = client.get('key')


Best Practices:
---------------

 - Always set the connect_timeout and timeout arguments in the constructor to
   avoid blocking your process when memcached is slow.
 - Use the "noreply" flag for a significant performance boost. The "noreply"
   flag is enabled by default for "set", "add", "replace", "append", "prepend",
   and "delete". It is disabled by default for "cas", "incr" and "decr". It
   obviously doesn't apply to any get calls.
 - Use get_many and gets_many whenever possible, as they result in less
   round trip times for fetching multiple keys.
 - Use the "ignore_exc" flag to treat memcache/network errors as cache misses
   on calls to the get* methods. This prevents failures in memcache, or network
   errors, from killing your web requests. Do not use this flag if you need to
   know about errors from memcache, and make sure you have some other way to
   detect memcache server failures.
"""

__author__ = "Charles Gordon"


import socket
import six


RECV_SIZE = 4096
VALID_STORE_RESULTS = {
    b'set':     (b'STORED',),
    b'add':     (b'STORED', b'NOT_STORED'),
    b'replace': (b'STORED', b'NOT_STORED'),
    b'append':  (b'STORED', b'NOT_STORED'),
    b'prepend': (b'STORED', b'NOT_STORED'),
    b'cas':     (b'STORED', b'EXISTS', b'NOT_FOUND'),
}


# Some of the values returned by the "stats" command
# need mapping into native Python types
STAT_TYPES = {
    # General stats
    b'version': six.binary_type,
    b'rusage_user': lambda value: float(value.replace(b':', b'.')),
    b'rusage_system': lambda value: float(value.replace(b':', b'.')),
    b'hash_is_expanding': lambda value: int(value) != 0,
    b'slab_reassign_running': lambda value: int(value) != 0,

    # Settings stats
    b'inter': six.binary_type,
    b'evictions': lambda value: value == b'on',
    b'growth_factor': float,
    b'stat_key_prefix': six.binary_type,
    b'umask': lambda value: int(value, 8),
    b'detail_enabled': lambda value: int(value) != 0,
    b'cas_enabled': lambda value: int(value) != 0,
    b'auth_enabled_sasl': lambda value: value == b'yes',
    b'maxconns_fast': lambda value: int(value) != 0,
    b'slab_reassign': lambda value: int(value) != 0,
    b'slab_automove': lambda value: int(value) != 0,
}


class MemcacheError(Exception):
    "Base exception class"
    pass


class MemcacheClientError(MemcacheError):
    """Raised when memcached fails to parse the arguments to a request, likely
    due to a malformed key and/or value, a bug in this library, or a version
    mismatch with memcached."""
    pass


class MemcacheUnknownCommandError(MemcacheClientError):
    """Raised when memcached fails to parse a request, likely due to a bug in
    this library or a version mismatch with memcached."""
    pass


class MemcacheIllegalInputError(MemcacheClientError):
    """Raised when a key or value is not legal for Memcache (see the class docs
    for Client for more details)."""
    pass


class MemcacheServerError(MemcacheError):
    """Raised when memcached reports a failure while processing a request,
    likely due to a bug or transient issue in memcached."""
    pass


class MemcacheUnknownError(MemcacheError):
    """Raised when this library receives a response from memcached that it
    cannot parse, likely due to a bug in this library or a version mismatch
    with memcached."""
    pass


class MemcacheUnexpectedCloseError(MemcacheServerError):
    "Raised when the connection with memcached closes unexpectedly."
    pass


class Client(object):
    """
    A client for a single memcached server.

    Keys and Values:
    ----------------

     Keys must have a __str__() method which should return a str with no more
     than 250 ASCII characters and no whitespace or control characters. Unicode
     strings must be encoded (as UTF-8, for example) unless they consist only
     of ASCII characters that are neither whitespace nor control characters.

     Values must have a __str__() method to convert themselves to a byte string.
     Unicode objects can be a problem since str() on a Unicode object will
     attempt to encode it as ASCII (which will fail if the value contains
     code points larger than U+127). You can fix this will a serializer or by
     just calling encode on the string (using UTF-8, for instance).

     If you intend to use anything but str as a value, it is a good idea to use
     a serializer and deserializer. The pymemcache.serde library has some
     already implemented serializers, including one that is compatible with
     the python-memcache library.

    Serialization and Deserialization:
    ----------------------------------

     The constructor takes two optional functions, one for "serialization" of
     values, and one for "deserialization". The serialization function takes
     two arguments, a key and a value, and returns a tuple of two elements, the
     serialized value, and an integer in the range 0-65535 (the "flags"). The
     deserialization function takes three parameters, a key, value and flags
     and returns the deserialized value.

     Here is an example using JSON for non-str values:

      def serialize_json(key, value):
          if type(value) == str:
              return value, 1
          return json.dumps(value), 2

      def deserialize_json(key, value, flags):
          if flags == 1:
              return value
          if flags == 2:
              return json.loads(value)
          raise Exception("Unknown flags for value: {1}".format(flags))

    Error Handling:
    ---------------

     All of the methods in this class that talk to memcached can throw one of
     the following exceptions:

      * MemcacheUnknownCommandError
      * MemcacheClientError
      * MemcacheServerError
      * MemcacheUnknownError
      * MemcacheUnexpectedCloseError
      * MemcacheIllegalInputError
      * socket.timeout
      * socket.error

     Instances of this class maintain a persistent connection to memcached
     which is terminated when any of these exceptions are raised. The next
     call to a method on the object will result in a new connection being made
     to memcached.
    """

    def __init__(self,
                 server,
                 serializer=None,
                 deserializer=None,
                 connect_timeout=None,
                 timeout=None,
                 no_delay=False,
                 ignore_exc=False,
                 socket_module=socket,
                 key_prefix=b''):
        """
        Constructor.

        Args:
          server: tuple(hostname, port)
          serializer: optional function, see notes in the class docs.
          deserializer: optional function, see notes in the class docs.
          connect_timeout: optional float, seconds to wait for a connection to
            the memcached server. Defaults to "forever" (uses the underlying
            default socket timeout, which can be very long).
          timeout: optional float, seconds to wait for send or recv calls on
            the socket connected to memcached. Defaults to "forever" (uses the
            underlying default socket timeout, which can be very long).
          no_delay: optional bool, set the TCP_NODELAY flag, which may help
            with performance in some cases. Defaults to False.
          ignore_exc: optional bool, True to cause the "get", "gets",
            "get_many" and "gets_many" calls to treat any errors as cache
            misses. Defaults to False.
          socket_module: socket module to use, e.g. gevent.socket. Defaults to
            the standard library's socket module.
          key_prefix: Prefix of key. You can use this as namespace. Defaults
            to b''.

        Notes:
          The constructor does not make a connection to memcached. The first
          call to a method on the object will do that.
        """
        self.server = server
        self.serializer = serializer
        self.deserializer = deserializer
        self.connect_timeout = connect_timeout
        self.timeout = timeout
        self.no_delay = no_delay
        self.ignore_exc = ignore_exc
        self.socket_module = socket_module
        self.sock = None
        self.buf = b''
        if isinstance(key_prefix, six.text_type):
            key_prefix = key_prefix.encode('ascii')
        if not isinstance(key_prefix, bytes):
            raise TypeError("key_prefix should be bytes.")
        self.key_prefix = key_prefix

    def check_key(self, key):
        """Checks key and add key_prefix."""
        if isinstance(key, six.text_type):
            try:
                key = key.encode('ascii')
            except UnicodeEncodeError as e:
                raise MemcacheIllegalInputError("No ascii key: %r" % (key,))
        key = self.key_prefix + key
        if b' ' in key:
            raise MemcacheIllegalInputError("Key contains spaces: %r" % (key,))
        if len(key) > 250:
            raise MemcacheIllegalInputError("Key is too long: %r" % (key,))
        return key

    def _connect(self):
        sock = self.socket_module.socket(self.socket_module.AF_INET,
                                         self.socket_module.SOCK_STREAM)
        sock.settimeout(self.connect_timeout)
        sock.connect(self.server)
        sock.settimeout(self.timeout)
        if self.no_delay:
            sock.setsockopt(self.socket_module.IPPROTO_TCP,
                            self.socket_module.TCP_NODELAY, 1)
        self.sock = sock

    def close(self):
        """Close the connection to memcached, if it is open. The next call to a
        method that requires a connection will re-open it."""
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None
        self.buf = b''

    def set(self, key, value, expire=0, noreply=True):
        """
        The memcached "set" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (the default).

        Returns:
          If no exception is raised, always returns True. If an exception is
          raised, the set may or may not have occurred. If noreply is True,
          then a successful return does not guarantee a successful set.
        """
        return self._store_cmd(b'set', key, expire, noreply, value)

    def set_many(self, values, expire=0, noreply=True):
        """
        A convenience function for setting multiple values.

        Args:
          values: dict(str, str), a dict of keys and values, see class docs
                  for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (the default).

        Returns:
          If no exception is raised, always returns True. Otherwise all, some
          or none of the keys have been successfully set. If noreply is True
          then a successful return does not guarantee that any keys were
          successfully set (just that the keys were successfully sent).
        """

        # TODO: make this more performant by sending all the values first, then
        # waiting for all the responses.
        for key, value in six.iteritems(values):
            self.set(key, value, expire, noreply)
        return True

    def add(self, key, value, expire=0, noreply=True):
        """
        The memcached "add" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (the default).

        Returns:
          If noreply is True, the return value is always True. Otherwise the
          return value is True if the value was stgored, and False if it was
          not (because the key already existed).
        """
        return self._store_cmd(b'add', key, expire, noreply, value)

    def replace(self, key, value, expire=0, noreply=True):
        """
        The memcached "replace" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (the default).

        Returns:
          If noreply is True, always returns True. Otherwise returns True if
          the value was stored and False if it wasn't (because the key didn't
          already exist).
        """
        return self._store_cmd(b'replace', key, expire, noreply, value)

    def append(self, key, value, expire=0, noreply=True):
        """
        The memcached "append" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (the default).

        Returns:
          True.
        """
        return self._store_cmd(b'append', key, expire, noreply, value)

    def prepend(self, key, value, expire=0, noreply=True):
        """
        The memcached "prepend" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (the default).

        Returns:
          True.
        """
        return self._store_cmd(b'prepend', key, expire, noreply, value)

    def cas(self, key, value, cas, expire=0, noreply=False):
        """
        The memcached "cas" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          cas: int or str that only contains the characters '0'-'9'.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, False to wait for the reply (the default).

        Returns:
          If noreply is True, always returns True. Otherwise returns None if
          the key didn't exist, False if it existed but had a different cas
          value and True if it existed and was changed.
        """
        return self._store_cmd(b'cas', key, expire, noreply, value, cas)

    def get(self, key):
        """
        The memcached "get" command, but only for one key, as a convenience.

        Args:
          key: str, see class docs for details.

        Returns:
          The value for the key, or None if the key wasn't found.
        """
        return self._fetch_cmd(b'get', [key], False).get(key, None)

    def get_many(self, keys):
        """
        The memcached "get" command.

        Args:
          keys: list(str), see class docs for details.

        Returns:
          A dict in which the keys are elements of the "keys" argument list
          and the values are values from the cache. The dict may contain all,
          some or none of the given keys.
        """
        if not keys:
            return {}

        return self._fetch_cmd(b'get', keys, False)

    def gets(self, key):
        """
        The memcached "gets" command for one key, as a convenience.

        Args:
          key: str, see class docs for details.

        Returns:
          A tuple of (key, cas), or (None, None) if the key was not found.
        """
        return self._fetch_cmd(b'gets', [key], True).get(key, (None, None))

    def gets_many(self, keys):
        """
        The memcached "gets" command.

        Args:
          keys: list(str), see class docs for details.

        Returns:
          A dict in which the keys are elements of the "keys" argument list and
          the values are tuples of (value, cas) from the cache. The dict may
          contain all, some or none of the given keys.
        """
        if not keys:
            return {}

        return self._fetch_cmd(b'gets', keys, True)

    def delete(self, key, noreply=True):
        """
        The memcached "delete" command.

        Args:
          key: str, see class docs for details.

        Returns:
          If noreply is True, always returns True. Otherwise returns True if
          the key was deleted, and False if it wasn't found.
        """
        cmd = b'delete ' + self.check_key(key)
        if noreply:
            cmd += b' noreply'
        cmd += b'\r\n'
        result = self._misc_cmd(cmd, b'delete', noreply)
        if noreply:
            return True
        return result == b'DELETED'

    def delete_many(self, keys, noreply=True):
        """
        A convenience function to delete multiple keys.

        Args:
          keys: list(str), the list of keys to delete.

        Returns:
          True. If an exception is raised then all, some or none of the keys
          may have been deleted. Otherwise all the keys have been sent to
          memcache for deletion and if noreply is False, they have been
          acknowledged by memcache.
        """
        if not keys:
            return True

        # TODO: make this more performant by sending all keys first, then
        # waiting for all values.
        for key in keys:
            self.delete(key, noreply)

        return True

    def incr(self, key, value, noreply=False):
        """
        The memcached "incr" command.

        Args:
          key: str, see class docs for details.
          value: int, the amount by which to increment the value.
          noreply: optional bool, False to wait for the reply (the default).

        Returns:
          If noreply is True, always returns None. Otherwise returns the new
          value of the key, or None if the key wasn't found.
        """
        key = self.check_key(key)
        cmd = b'incr ' + key + b' ' + six.text_type(value).encode('ascii')
        if noreply:
            cmd += b' noreply'
        cmd += b'\r\n'
        result = self._misc_cmd(cmd, b'incr', noreply)
        if noreply:
            return None
        if result == b'NOT_FOUND':
            return None
        return int(result)

    def decr(self, key, value, noreply=False):
        """
        The memcached "decr" command.

        Args:
          key: str, see class docs for details.
          value: int, the amount by which to increment the value.
          noreply: optional bool, False to wait for the reply (the default).

        Returns:
          If noreply is True, always returns None. Otherwise returns the new
          value of the key, or None if the key wasn't found.
        """
        key = self.check_key(key)
        cmd = b'decr ' + key + b' ' + six.text_type(value).encode('ascii')
        if noreply:
            cmd += b' noreply'
        cmd += b'\r\n'
        result = self._misc_cmd(cmd, b'decr', noreply)
        if noreply:
            return None
        if result == b'NOT_FOUND':
            return None
        return int(result)

    def touch(self, key, expire=0, noreply=True):
        """
        The memcached "touch" command.

        Args:
          key: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (the default).

        Returns:
          True if the expiration time was updated, False if the key wasn't
          found.
        """
        key = self.check_key(key)
        cmd = b'touch ' + key + b' ' + six.text_type(expire).encode('ascii')
        if noreply:
            cmd += b' noreply'
        cmd += b'\r\n'
        result = self._misc_cmd(cmd, b'touch', noreply)
        if noreply:
            return True
        return result == b'TOUCHED'

    def stats(self, *args):
        """
        The memcached "stats" command.

        The returned keys depend on what the "stats" command returns.
        A best effort is made to convert values to appropriate Python
        types, defaulting to strings when a conversion cannot be made.

        Args:
          *arg: extra string arguments to the "stats" command. See the
                memcached protocol documentation for more information.

        Returns:
          A dict of the returned stats.
        """
        result = self._fetch_cmd(b'stats', args, False)

        for key, value in six.iteritems(result):
            converter = STAT_TYPES.get(key, int)
            try:
                result[key] = converter(value)
            except Exception:
                pass

        return result

    def flush_all(self, delay=0, noreply=True):
        """
        The memcached "flush_all" command.

        Args:
          delay: optional int, the number of seconds to wait before flushing,
                 or zero to flush immediately (the default).
          noreply: optional bool, True to not wait for the response (the default).

        Returns:
          True.
        """
        cmd = b'flush_all ' + six.text_type(delay).encode('ascii')
        if noreply:
            cmd += b' noreply'
        cmd += b'\r\n'
        result = self._misc_cmd(cmd, b'flush_all', noreply)
        if noreply:
            return True
        return result == b'OK'

    def quit(self):
        """
        The memcached "quit" command.

        This will close the connection with memcached. Calling any other
        method on this object will re-open the connection, so this object can
        be re-used after quit.
        """
        cmd = b"quit\r\n"
        self._misc_cmd(cmd, b'quit', True)
        self.close()

    def _raise_errors(self, line, name):
        if line.startswith(b'ERROR'):
            raise MemcacheUnknownCommandError(name)

        if line.startswith(b'CLIENT_ERROR'):
            error = line[line.find(b' ') + 1:]
            raise MemcacheClientError(error)

        if line.startswith(b'SERVER_ERROR'):
            error = line[line.find(b' ') + 1:]
            raise MemcacheServerError(error)

    def _fetch_cmd(self, name, keys, expect_cas):
        if not self.sock:
            self._connect()

        checked_keys = dict((self.check_key(k), k) for k in keys)
        cmd = name + b' ' + b' '.join(checked_keys) + b'\r\n'

        try:
            self.sock.sendall(cmd)

            result = {}
            while True:
                self.buf, line = _readline(self.sock, self.buf)
                self._raise_errors(line, name)

                if line == b'END':
                    return result
                elif line.startswith(b'VALUE'):
                    if expect_cas:
                        _, key, flags, size, cas = line.split()
                    else:
                        try:
                            _, key, flags, size = line.split()
                        except Exception as e:
                            raise ValueError("Unable to parse line %s: %s"
                                             % (line, str(e)))

                    self.buf, value = _readvalue(self.sock,
                                                 self.buf,
                                                 int(size))
                    key = checked_keys[key]

                    if self.deserializer:
                        value = self.deserializer(key, value, int(flags))

                    if expect_cas:
                        result[key] = (value, cas)
                    else:
                        result[key] = value
                elif name == b'stats' and line.startswith(b'STAT'):
                    _, key, value = line.split()
                    result[key] = value
                else:
                    raise MemcacheUnknownError(line[:32])
        except Exception:
            self.close()
            if self.ignore_exc:
                return {}
            raise

    def _store_cmd(self, name, key, expire, noreply, data, cas=None):
        key = self.check_key(key)
        if not self.sock:
            self._connect()

        if self.serializer:
            data, flags = self.serializer(key, data)
        else:
            flags = 0

        if not isinstance(data, six.binary_type):
            try:
                data = six.text_type(data).encode('ascii')
            except UnicodeEncodeError as e:
                raise MemcacheIllegalInputError(str(e))

        extra = b''
        if cas is not None:
            extra += b' ' + cas
        if noreply:
            extra += b' noreply'

        cmd = (name + b' ' + key + b' ' + six.text_type(flags).encode('ascii')
               + b' ' + six.text_type(expire).encode('ascii')
               + b' ' + six.text_type(len(data)).encode('ascii') + extra
               + b'\r\n' + data + b'\r\n')

        try:
            self.sock.sendall(cmd)

            if noreply:
                return True

            self.buf, line = _readline(self.sock, self.buf)
            self._raise_errors(line, name)

            if line in VALID_STORE_RESULTS[name]:
                if line == b'STORED':
                    return True
                if line == b'NOT_STORED':
                    return False
                if line == b'NOT_FOUND':
                    return None
                if line == b'EXISTS':
                    return False
            else:
                raise MemcacheUnknownError(line[:32])
        except Exception:
            self.close()
            raise

    def _misc_cmd(self, cmd, cmd_name, noreply):
        if not self.sock:
            self._connect()

        try:
            self.sock.sendall(cmd)

            if noreply:
                return

            _, line = _readline(self.sock, b'')
            self._raise_errors(line, cmd_name)

            return line
        except Exception:
            self.close()
            raise

    def __setitem__(self, key, value):
        self.set(key, value, noreply=True)

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError
        return value

    def __delitem__(self, key):
        self.delete(key, noreply=True)


def _readline(sock, buf):
    """Read line of text from the socket.

    Read a line of text (delimited by "\r\n") from the socket, and
    return that line along with any trailing characters read from the
    socket.

    Args:
        sock: Socket object, should be connected.
        buf: String, zero or more characters, returned from an earlier
            call to _readline or _readvalue (pass an empty string on the
            first call).

    Returns:
      A tuple of (buf, line) where line is the full line read from the
      socket (minus the "\r\n" characters) and buf is any trailing
      characters read after the "\r\n" was found (which may be an empty
      string).

    """
    chunks = []
    last_char = b''

    while True:
        # We're reading in chunks, so "\r\n" could appear in one chunk,
        # or across the boundary of two chunks, so we check for both
        # cases.

        # This case must appear first, since the buffer could have
        # later \r\n characters in it and we want to get the first \r\n.
        if last_char == b'\r' and buf[0:1] == b'\n':
            # Strip the last character from the last chunk.
            chunks[-1] = chunks[-1][:-1]
            return buf[1:], b''.join(chunks)
        elif buf.find(b'\r\n') != -1:
            before, sep, after = buf.partition(b"\r\n")
            chunks.append(before)
            return after, b''.join(chunks)

        if buf:
            chunks.append(buf)
            last_char = buf[-1:]

        buf = sock.recv(RECV_SIZE)
        if not buf:
            raise MemcacheUnexpectedCloseError()


def _readvalue(sock, buf, size):
    """Read specified amount of bytes from the socket.

    Read size bytes, followed by the "\r\n" characters, from the socket,
    and return those bytes and any trailing bytes read after the "\r\n".

    Args:
        sock: Socket object, should be connected.
        buf: String, zero or more characters, returned from an earlier
            call to _readline or _readvalue (pass an empty string on the
            first call).
        size: Integer, number of bytes to read from the socket.

    Returns:
      A tuple of (buf, value) where value is the bytes read from the
      socket (there will be exactly size bytes) and buf is trailing
      characters read after the "\r\n" following the bytes (but not
      including the \r\n).

    """
    chunks = []
    rlen = size + 2
    while rlen - len(buf) > 0:
        if buf:
            rlen -= len(buf)
            chunks.append(buf)
        buf = sock.recv(RECV_SIZE)
        if not buf:
            raise MemcacheUnexpectedCloseError()

    # Now we need to remove the \r\n from the end. There are two cases we care
    # about: the \r\n is all in the last buffer, or only the \n is in the last
    # buffer, and we need to remove the \r from the penultimate buffer.

    if rlen == 1:
        # replace the last chunk with the same string minus the last character,
        # which is always '\r' in this case.
        chunks[-1] = chunks[-1][:-1]
    else:
        # Just remove the "\r\n" from the latest chunk
        chunks.append(buf[:rlen - 2])

    return buf[rlen:], b''.join(chunks)

########NEW FILE########
__FILENAME__ = fallback
# Copyright 2012 Pinterest.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A client for falling back to older memcached servers when performing reads.

It is sometimes necessary to deploy memcached on new servers, or with a
different configuration. In theses cases, it is undesirable to start up an
empty memcached server and point traffic to it, since the cache will be cold,
and the backing store will have a large increase in traffic.

This class attempts to solve that problem by providing an interface identical
to the Client interface, but which can fall back to older memcached servers
when reads to the primary server fail. The approach for upgrading memcached
servers or configuration then becomes:

 1. Deploy a new host (or fleet) with memcached, possibly with a new
    configuration.
 2. From your application servers, use FallbackClient to write and read from
    the new cluster, and to read from the old cluster when there is a miss in
    the new cluster.
 3. Wait until the new cache is warm enough to support the load.
 4. Switch from FallbackClient to a regular Client library for doing all
    reads and writes to the new cluster.
 5. Take down the old cluster.

Best Practices:
---------------
 - Make sure that the old client has "ignore_exc" set to True, so that it
   treats failures like cache misses. That will allow you to take down the
   old cluster before you switch away from FallbackClient.
"""

class FallbackClient(object):
    def __init__(self, caches):
        assert len(caches) > 0
        self.caches = caches

    def close(self):
        "Close each of the memcached clients"
        for cache in self.caches:
            cache.close()

    def set(self, key, value, expire=0, noreply=True):
        self.caches[0].set(key, value, expire, noreply)

    def add(self, key, value, expire=0, noreply=True):
        self.caches[0].add(key, value, expire, noreply)

    def replace(self, key, value, expire=0, noreply=True):
        self.caches[0].replace(key, value, expire, noreply)

    def append(self, key, value, expire=0, noreply=True):
        self.caches[0].append(key, value, expire, noreply)

    def prepend(self, key, value, expire=0, noreply=True):
        self.caches[0].prepend(key, value, expire, noreply)

    def cas(self, key, value, cas, expire=0, noreply=True):
        self.caches[0].cas(key, value, cas, expire, noreply)

    def get(self, key):
        for cache in self.caches:
            result = cache.get(key)
            if result is not None:
                return result
        return None

    def get_many(self, keys):
        for cache in self.caches:
            result = cache.get_many(keys)
            if result:
                return result
        return []

    def gets(self, key):
        for cache in self.caches:
            result = cache.gets(key)
            if result is not None:
                return result
        return None

    def gets_many(self, keys):
        for cache in self.caches:
            result = cache.gets_many(keys)
            if result:
                return result
        return []

    def delete(self, key, noreply=True):
        self.caches[0].delete(key, noreply)

    def incr(self, key, value, noreply=True):
        self.caches[0].incr(key, value, noreply)

    def decr(self, key, value, noreply=True):
        self.caches[0].decr(key, value, noreply)

    def touch(self, key, expire=0, noreply=True):
        self.caches[0].touch(key, expire, noreply)

    def stats(self):
        # TODO: ??
        pass

    def flush_all(self, delay=0, noreply=True):
        self.caches[0].flush_all(delay, noreply)

    def quit(self):
        # TODO: ??
        pass

########NEW FILE########
__FILENAME__ = serde
# Copyright 2012 Pinterest.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import pickle

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


FLAG_PICKLE  = 1<<0
FLAG_INTEGER = 1<<1
FLAG_LONG    = 1<<2


def python_memcache_serializer(key, value):
    flags = 0

    if isinstance(value, str):
        pass
    elif isinstance(value, int):
        flags |= FLAG_INTEGER
        value = "%d" % value
    elif isinstance(value, long):
        flags |= FLAG_LONG
        value = "%d" % value
    else:
        flags |= FLAG_PICKLE
        output = StringIO()
        pickler = pickle.Pickler(output, 0)
        pickler.dump(value)
        value = output.getvalue()

    return value, flags

def python_memcache_deserializer(key, value, flags):
    if flags == 0:
        return value

    if flags & FLAG_INTEGER:
        return int(value)

    if flags & FLAG_LONG:
        return long(value)

    if flags & FLAG_PICKLE:
        try:
            buf = StringIO(value)
            unpickler = pickle.Unpickler(buf)
            return unpickler.load()
        except Exception as e:
            logging.info('Pickle error', exc_info=True)
            return None

    return value

########NEW FILE########
__FILENAME__ = benchmark
# Copyright 2012 Pinterest.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import time


def test_client(name, client, size, count):
    client.flush_all()

    value = 'X' * size

    start = time.time()

    for i in range(count):
        client.set(str(i), value)

    for i in range(count):
        client.get(str(i))

    duration = time.time() - start
    print("{0}: {1}".format(name, duration))


def test_pylibmc(host, port, size, count):
    try:
        import pylibmc
    except Exception:
        print("Could not import pylibmc, skipping test...")
        return

    client = pylibmc.Client(['{0}:{1}'.format(host, port)])
    client.behaviors = {"tcp_nodelay": True}
    test_client('pylibmc', client, size, count)


def test_memcache(host, port, size, count):
    try:
        import memcache
    except Exception:
        print("Could not import pymemcache.client, skipping test...")
        return

    client = memcache.Client(['{0}:{1}'.format(host, port)])
    test_client('memcache', client, size, count)


def test_pymemcache(host, port, size, count):
    try:
        import pymemcache.client
    except Exception:
        print("Could not import pymemcache.client, skipping test...")
        return

    client = pymemcache.client.Client((host, port))
    test_client('pymemcache', client, size, count)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server',
                        metavar='HOST',
                        required=True)
    parser.add_argument('-p', '--port',
                        metavar='PORT',
                        type=int,
                        required=True)
    parser.add_argument('-z', '--size',
                        metavar='SIZE',
                        default=1024,
                        type=int)
    parser.add_argument('-c', '--count',
                        metavar='COUNT',
                        default=10000,
                        type=int)

    args = parser.parse_args()

    test_pylibmc(args.server, args.port, args.size, args.count)
    test_memcache(args.server, args.port, args.size, args.count)
    test_pymemcache(args.server, args.port, args.size, args.count)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = integration
# Copyright 2012 Pinterest.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import socket

import six

from pymemcache.client import (Client, MemcacheClientError,
                               MemcacheUnknownCommandError)
from pymemcache.client import MemcacheIllegalInputError
from nose import tools


def get_set_test(host, port, socket_module):
    client = Client((host, port), socket_module=socket_module)
    client.flush_all()

    result = client.get('key')
    tools.assert_equal(result, None)

    client.set(b'key', b'value', noreply=False)
    result = client.get(b'key')
    tools.assert_equal(result, b'value')

    client.set(b'key2', b'value2', noreply=True)
    result = client.get(b'key2')
    tools.assert_equal(result, b'value2')

    result = client.get_many([b'key', b'key2'])
    tools.assert_equal(result, {b'key': b'value', b'key2': b'value2'})

    result = client.get_many([])
    tools.assert_equal(result, {})


def add_replace_test(host, port, socket_module):
    client = Client((host, port), socket_module=socket_module)
    client.flush_all()

    result = client.add(b'key', b'value', noreply=False)
    tools.assert_equal(result, True)
    result = client.get(b'key')
    tools.assert_equal(result, b'value')

    result = client.add(b'key', b'value2', noreply=False)
    tools.assert_equal(result, False)
    result = client.get(b'key')
    tools.assert_equal(result, b'value')

    result = client.replace(b'key1', b'value1', noreply=False)
    tools.assert_equal(result, False)
    result = client.get(b'key1')
    tools.assert_equal(result, None)

    result = client.replace(b'key', b'value2', noreply=False)
    tools.assert_equal(result, True)
    result = client.get(b'key')
    tools.assert_equal(result, b'value2')


def append_prepend_test(host, port, socket_module):
    client = Client((host, port), socket_module=socket_module)
    client.flush_all()

    result = client.append(b'key', b'value', noreply=False)
    tools.assert_equal(result, False)
    result = client.get(b'key')
    tools.assert_equal(result, None)

    result = client.set(b'key', b'value', noreply=False)
    tools.assert_equal(result, True)
    result = client.append(b'key', b'after', noreply=False)
    tools.assert_equal(result, True)
    result = client.get(b'key')
    tools.assert_equal(result, b'valueafter')

    result = client.prepend(b'key1', b'value', noreply=False)
    tools.assert_equal(result, False)
    result = client.get(b'key1')
    tools.assert_equal(result, None)

    result = client.prepend(b'key', b'before', noreply=False)
    tools.assert_equal(result, True)
    result = client.get(b'key')
    tools.assert_equal(result, b'beforevalueafter')


def cas_test(host, port, socket_module):
    client = Client((host, port), socket_module=socket_module)
    client.flush_all()

    result = client.cas(b'key', b'value', b'1', noreply=False)
    tools.assert_equal(result, None)

    result = client.set(b'key', b'value', noreply=False)
    tools.assert_equal(result, True)

    result = client.cas(b'key', b'value', b'1', noreply=False)
    tools.assert_equal(result, False)

    result, cas = client.gets(b'key')
    tools.assert_equal(result, b'value')

    result = client.cas(b'key', b'value1', cas, noreply=False)
    tools.assert_equal(result, True)

    result = client.cas(b'key', b'value2', cas, noreply=False)
    tools.assert_equal(result, False)


def gets_test(host, port, socket_module):
    client = Client((host, port), socket_module=socket_module)
    client.flush_all()

    result = client.gets(b'key')
    tools.assert_equal(result, (None, None))

    result = client.set(b'key', b'value', noreply=False)
    tools.assert_equal(result, True)
    result = client.gets(b'key')
    tools.assert_equal(result[0], b'value')


def delete_test(host, port, socket_module):
    client = Client((host, port), socket_module=socket_module)
    client.flush_all()

    result = client.delete(b'key', noreply=False)
    tools.assert_equal(result, False)

    result = client.get(b'key')
    tools.assert_equal(result, None)
    result = client.set(b'key', b'value', noreply=False)
    tools.assert_equal(result, True)
    result = client.delete(b'key', noreply=False)
    tools.assert_equal(result, True)
    result = client.get(b'key')
    tools.assert_equal(result, None)


def incr_decr_test(host, port, socket_module):
    client = Client((host, port), socket_module=socket_module)
    client.flush_all()

    result = client.incr(b'key', 1, noreply=False)
    tools.assert_equal(result, None)

    result = client.set(b'key', b'0', noreply=False)
    tools.assert_equal(result, True)
    result = client.incr(b'key', 1, noreply=False)
    tools.assert_equal(result, 1)

    def _bad_int():
        client.incr(b'key', b'foobar')

    tools.assert_raises(MemcacheClientError, _bad_int)

    result = client.decr(b'key1', 1, noreply=False)
    tools.assert_equal(result, None)

    result = client.decr(b'key', 1, noreply=False)
    tools.assert_equal(result, 0)
    result = client.get(b'key')
    tools.assert_equal(result, b'0')


def misc_test(host, port, socket_module):
    client = Client((host, port), socket_module=socket_module)
    client.flush_all()


def test_serialization_deserialization(host, port, socket_module):
    def _ser(key, value):
        return json.dumps(value).encode('ascii'), 1

    def _des(key, value, flags):
        if flags == 1:
            return json.loads(value.decode('ascii'))
        return value

    client = Client((host, port), serializer=_ser, deserializer=_des,
                    socket_module=socket_module)
    client.flush_all()

    value = {'a': 'b', 'c': ['d']}
    client.set(b'key', value)
    result = client.get(b'key')
    tools.assert_equal(result, value)


def test_errors(host, port, socket_module):
    client = Client((host, port), socket_module=socket_module)
    client.flush_all()

    def _key_with_ws():
        client.set(b'key with spaces', b'value', noreply=False)

    tools.assert_raises(MemcacheIllegalInputError, _key_with_ws)

    def _key_too_long():
        client.set(b'x' * 1024, b'value', noreply=False)

    tools.assert_raises(MemcacheClientError, _key_too_long)

    def _unicode_key_in_set():
        client.set(six.u('\u0FFF'), b'value', noreply=False)

    tools.assert_raises(MemcacheClientError, _unicode_key_in_set)

    def _unicode_key_in_get():
        client.get(six.u('\u0FFF'))

    tools.assert_raises(MemcacheClientError, _unicode_key_in_get)

    def _unicode_value_in_set():
        client.set(b'key', six.u('\u0FFF'), noreply=False)

    tools.assert_raises(MemcacheClientError, _unicode_value_in_set)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server',
                        metavar='HOST',
                        required=True)
    parser.add_argument('-p', '--port',
                        metavar='PORT',
                        type=int,
                        required=True)

    args = parser.parse_args()

    socket_modules = [socket]
    try:
        from gevent import socket as gevent_socket
    except ImportError:
        print("Skipping gevent (not installed)")
    else:
        socket_modules.append(gevent_socket)

    for socket_module in socket_modules:
        print("Testing with socket module:", socket_module.__name__)

        print("Testing get and set...")
        get_set_test(args.server, args.port, socket_module)
        print("Testing add and replace...")
        add_replace_test(args.server, args.port, socket_module)
        print("Testing append and prepend...")
        append_prepend_test(args.server, args.port, socket_module)
        print("Testing cas...")
        cas_test(args.server, args.port, socket_module)
        print("Testing gets...")
        gets_test(args.server, args.port, socket_module)
        print("Testing delete...")
        delete_test(args.server, args.port, socket_module)
        print("Testing incr and decr...")
        incr_decr_test(args.server, args.port, socket_module)
        print("Testing flush_all...")
        misc_test(args.server, args.port, socket_module)
        print("Testing serialization and deserialization...")
        test_serialization_deserialization(args.server, args.port,
                                           socket_module)
        print("Testing error cases...")
        test_errors(args.server, args.port, socket_module)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_client
# Copyright 2012 Pinterest.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import json
import socket
import unittest

from nose import tools
from pymemcache.client import Client, MemcacheUnknownCommandError
from pymemcache.client import MemcacheClientError, MemcacheServerError
from pymemcache.client import MemcacheUnknownError, MemcacheIllegalInputError
from pymemcache.test.utils import MockMemcacheClient


class MockSocket(object):
    def __init__(self, recv_bufs):
        self.recv_bufs = collections.deque(recv_bufs)
        self.send_bufs = []
        self.closed = False
        self.timeouts = []
        self.connections = []
        self.socket_options = []

    def sendall(self, value):
        self.send_bufs.append(value)

    def close(self):
        self.closed = True

    def recv(self, size):
        value = self.recv_bufs.popleft()
        if isinstance(value, Exception):
            raise value
        return value

    def settimeout(self, timeout):
        self.timeouts.append(timeout)

    def connect(self, server):
        self.connections.append(server)

    def setsockopt(self, level, option, value):
        self.socket_options.append((level, option, value))


class MockSocketModule(object):
    def socket(self, family, type):
        return MockSocket([])

    def __getattr__(self, name):
        return getattr(socket, name)


class ClientTestMixin(object):
    def test_set_success(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set(b'key', b'value', noreply=False)
        tools.assert_equal(result, True)

    def test_set_unicode_key(self):
        client = self.Client(None)
        client.sock = MockSocket([b''])

        def _set():
            client.set(u'\u0FFF', b'value', noreply=False)

        tools.assert_raises(MemcacheIllegalInputError, _set)

    def test_set_unicode_value(self):
        client = self.Client(None)
        client.sock = MockSocket([b''])

        def _set():
            client.set(b'key', u'\u0FFF', noreply=False)

        tools.assert_raises(MemcacheIllegalInputError, _set)

    def test_set_noreply(self):
        client = self.Client(None)
        client.sock = MockSocket([])
        result = client.set(b'key', b'value', noreply=True)
        tools.assert_equal(result, True)

    def test_set_many_success(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set_many({b'key' : b'value'}, noreply=False)
        tools.assert_equal(result, True)

    def test_add_stored(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r', b'\n'])
        result = client.add(b'key', b'value', noreply=False)
        tools.assert_equal(result, True)

    def test_add_not_stored(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r', b'\n'])
        result = client.add(b'key', b'value', noreply=False)

        client.sock = MockSocket([b'NOT_', b'STOR', b'ED', b'\r\n'])
        result = client.add(b'key', b'value', noreply=False)
        tools.assert_equal(result, False)

    def test_get_not_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'END\r\n'])
        result = client.get(b'key')
        tools.assert_equal(result, None)

    def test_get_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set(b'key', b'value', noreply=False)

        client.sock = MockSocket([b'VALUE key 0 5\r\nvalue\r\nEND\r\n'])
        result = client.get(b'key')
        tools.assert_equal(result, b'value')

    def test_get_many_none_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'END\r\n'])
        result = client.get_many([b'key1', b'key2'])
        tools.assert_equal(result, {})

    def test_get_many_some_found(self):
        client = self.Client(None)

        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set(b'key1', b'value1', noreply=False)

        client.sock = MockSocket([b'VALUE key1 0 6\r\nvalue1\r\nEND\r\n'])
        result = client.get_many([b'key1', b'key2'])
        tools.assert_equal(result, {b'key1': b'value1'})

    def test_get_many_all_found(self):
        client = self.Client(None)

        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set(b'key1', b'value1', noreply=False)

        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set(b'key2', b'value2', noreply=False)

        client.sock = MockSocket([b'VALUE key1 0 6\r\nvalue1\r\n'
                                  b'VALUE key2 0 6\r\nvalue2\r\nEND\r\n'])
        result = client.get_many([b'key1', b'key2'])
        tools.assert_equal(result, {b'key1': b'value1', b'key2': b'value2'})

    def test_get_unicode_key(self):
        client = self.Client(None)
        client.sock = MockSocket([b''])

        def _get():
            client.get(u'\u0FFF')

        tools.assert_raises(MemcacheIllegalInputError, _get)

    def test_delete_not_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'NOT_FOUND\r\n'])
        result = client.delete(b'key', noreply=False)
        tools.assert_equal(result, False)

    def test_delete_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r', b'\n'])
        result = client.add(b'key', b'value', noreply=False)

        client.sock = MockSocket([b'DELETED\r\n'])
        result = client.delete(b'key', noreply=False)
        tools.assert_equal(result, True)

    def test_delete_noreply(self):
        client = self.Client(None)
        client.sock = MockSocket([])
        result = client.delete(b'key', noreply=True)
        tools.assert_equal(result, True)

    def test_incr_not_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'NOT_FOUND\r\n'])
        result = client.incr(b'key', 1, noreply=False)
        tools.assert_equal(result, None)

    def test_incr_found(self):
        client = self.Client(None)

        client.sock = MockSocket([b'STORED\r\n'])
        client.set(b'key', 0, noreply=False)

        client.sock = MockSocket([b'1\r\n'])
        result = client.incr(b'key', 1, noreply=False)
        tools.assert_equal(result, 1)

    def test_incr_noreply(self):
        client = self.Client(None)

        client.sock = MockSocket([b'STORED\r\n'])
        client.set(b'key', 0, noreply=False)

        client.sock = MockSocket([])
        result = client.incr(b'key', 1, noreply=True)
        tools.assert_equal(result, None)

    def test_decr_not_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'NOT_FOUND\r\n'])
        result = client.decr(b'key', 1, noreply=False)
        tools.assert_equal(result, None)

    def test_decr_found(self):
        client = self.Client(None)

        client.sock = MockSocket([b'STORED\r\n'])
        client.set(b'key', 2, noreply=False)

        client.sock = MockSocket([b'1\r\n'])
        result = client.decr(b'key', 1, noreply=False)
        tools.assert_equal(result, 1)


class TestClient(ClientTestMixin, unittest.TestCase):

    Client = Client

    def test_append_stored(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n'])
        result = client.append(b'key', b'value', noreply=False)
        tools.assert_equal(result, True)

    def test_prepend_stored(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n'])
        result = client.prepend(b'key', b'value', noreply=False)
        tools.assert_equal(result, True)

    def test_cas_stored(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n'])
        result = client.cas(b'key', b'value', b'cas', noreply=False)
        tools.assert_equal(result, True)

    def test_cas_exists(self):
        client = self.Client(None)
        client.sock = MockSocket([b'EXISTS\r\n'])
        result = client.cas(b'key', b'value', b'cas', noreply=False)
        tools.assert_equal(result, False)

    def test_cas_not_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'NOT_FOUND\r\n'])
        result = client.cas(b'key', b'value', b'cas', noreply=False)
        tools.assert_equal(result, None)

    def test_cr_nl_boundaries(self):
        client = self.Client(None)
        client.sock = MockSocket([b'VALUE key1 0 6\r',
                                  b'\nvalue1\r\n'
                                  b'VALUE key2 0 6\r\n',
                                  b'value2\r\n'
                                  b'END\r\n'])
        result = client.get_many([b'key1', b'key2'])
        tools.assert_equals(result, {b'key1': b'value1', b'key2': b'value2'})

        client.sock = MockSocket([b'VALUE key1 0 6\r\n',
                                  b'value1\r',
                                  b'\nVALUE key2 0 6\r\n',
                                  b'value2\r\n',
                                  b'END\r\n'])
        result = client.get_many([b'key1', b'key2'])
        tools.assert_equals(result, {b'key1': b'value1', b'key2': b'value2'})

        client.sock = MockSocket([b'VALUE key1 0 6\r\n',
                                  b'value1\r\n',
                                  b'VALUE key2 0 6\r',
                                  b'\nvalue2\r\n',
                                  b'END\r\n'])
        result = client.get_many([b'key1', b'key2'])
        tools.assert_equals(result, {b'key1': b'value1', b'key2': b'value2'})


        client.sock = MockSocket([b'VALUE key1 0 6\r\n',
                                  b'value1\r\n',
                                  b'VALUE key2 0 6\r\n',
                                  b'value2\r',
                                  b'\nEND\r\n'])
        result = client.get_many([b'key1', b'key2'])
        tools.assert_equals(result, {b'key1': b'value1', b'key2': b'value2'})

        client.sock = MockSocket([b'VALUE key1 0 6\r\n',
                                  b'value1\r\n',
                                  b'VALUE key2 0 6\r\n',
                                  b'value2\r\n',
                                  b'END\r',
                                  b'\n'])
        result = client.get_many([b'key1', b'key2'])
        tools.assert_equals(result, {b'key1': b'value1', b'key2': b'value2'})

        client.sock = MockSocket([b'VALUE key1 0 6\r',
                                  b'\nvalue1\r',
                                  b'\nVALUE key2 0 6\r',
                                  b'\nvalue2\r',
                                  b'\nEND\r',
                                  b'\n'])
        result = client.get_many([b'key1', b'key2'])
        tools.assert_equals(result, {b'key1': b'value1', b'key2': b'value2'})

    def test_delete_exception(self):
        client = self.Client(None)
        client.sock = MockSocket([Exception('fail')])

        def _delete():
            client.delete(b'key', noreply=False)

        tools.assert_raises(Exception, _delete)
        tools.assert_equal(client.sock, None)
        tools.assert_equal(client.buf, b'')

    def test_flush_all(self):
        client = self.Client(None)
        client.sock = MockSocket([b'OK\r\n'])
        result = client.flush_all(noreply=False)
        tools.assert_equal(result, True)

    def test_incr_exception(self):
        client = self.Client(None)
        client.sock = MockSocket([Exception('fail')])

        def _incr():
            client.incr(b'key', 1)

        tools.assert_raises(Exception, _incr)
        tools.assert_equal(client.sock, None)
        tools.assert_equal(client.buf, b'')

    def test_get_error(self):
        client = self.Client(None)
        client.sock = MockSocket([b'ERROR\r\n'])

        def _get():
            client.get(b'key')

        tools.assert_raises(MemcacheUnknownCommandError, _get)

    def test_get_recv_chunks(self):
        client = self.Client(None)
        client.sock = MockSocket([b'VALUE key', b' 0 5\r', b'\nvalue', b'\r\n',
                                  b'END', b'\r', b'\n'])
        result = client.get(b'key')
        tools.assert_equal(result, b'value')

    def test_get_unknown_error(self):
        client = self.Client(None)
        client.sock = MockSocket([b'foobarbaz\r\n'])

        def _get():
            client.get(b'key')

        tools.assert_raises(MemcacheUnknownError, _get)

    def test_gets_not_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'END\r\n'])
        result = client.gets(b'key')
        tools.assert_equal(result, (None, None))

    def test_gets_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'VALUE key 0 5 10\r\nvalue\r\nEND\r\n'])
        result = client.gets(b'key')
        tools.assert_equal(result, (b'value', b'10'))

    def test_gets_many_none_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'END\r\n'])
        result = client.gets_many([b'key1', b'key2'])
        tools.assert_equal(result, {})

    def test_gets_many_some_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'VALUE key1 0 6 11\r\nvalue1\r\nEND\r\n'])
        result = client.gets_many([b'key1', b'key2'])
        tools.assert_equal(result, {b'key1': (b'value1', b'11')})

    def test_touch_not_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'NOT_FOUND\r\n'])
        result = client.touch(b'key', noreply=False)
        tools.assert_equal(result, False)

    def test_touch_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'TOUCHED\r\n'])
        result = client.touch(b'key', noreply=False)
        tools.assert_equal(result, True)

    def test_quit(self):
        client = self.Client(None)
        client.sock = MockSocket([])
        result = client.quit()
        tools.assert_equal(result, None)
        tools.assert_equal(client.sock, None)
        tools.assert_equal(client.buf, b'')

    def test_replace_stored(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n'])
        result = client.replace(b'key', b'value', noreply=False)
        tools.assert_equal(result, True)

    def test_replace_not_stored(self):
        client = self.Client(None)
        client.sock = MockSocket([b'NOT_STORED\r\n'])
        result = client.replace(b'key', b'value', noreply=False)
        tools.assert_equal(result, False)

    def test_serialization(self):
        def _ser(key, value):
            return json.dumps(value), 0

        client = self.Client(None, serializer=_ser)
        client.sock = MockSocket([b'STORED\r\n'])
        client.set('key', {'c': 'd'})
        tools.assert_equal(client.sock.send_bufs, [
            b'set key 0 0 10 noreply\r\n{"c": "d"}\r\n'
        ])

    def test_set_socket_handling(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set(b'key', b'value', noreply=False)
        tools.assert_equal(result, True)
        tools.assert_equal(client.sock.closed, False)
        tools.assert_equal(len(client.sock.send_bufs), 1)

    def test_set_error(self):
        client = self.Client(None)
        client.sock = MockSocket([b'ERROR\r\n'])

        def _set():
            client.set(b'key', b'value', noreply=False)

        tools.assert_raises(MemcacheUnknownCommandError, _set)

    def test_set_exception(self):
        client = self.Client(None)
        client.sock = MockSocket([Exception('fail')])

        def _set():
            client.set(b'key', b'value', noreply=False)

        tools.assert_raises(Exception, _set)
        tools.assert_equal(client.sock, None)
        tools.assert_equal(client.buf, b'')

    def test_set_client_error(self):
        client = self.Client(None)
        client.sock = MockSocket([b'CLIENT_ERROR some message\r\n'])

        def _set():
            client.set('key', 'value', noreply=False)

        tools.assert_raises(MemcacheClientError, _set)

    def test_set_server_error(self):
        client = self.Client(None)
        client.sock = MockSocket([b'SERVER_ERROR some message\r\n'])

        def _set():
            client.set(b'key', b'value', noreply=False)

        tools.assert_raises(MemcacheServerError, _set)

    def test_set_unknown_error(self):
        client = self.Client(None)
        client.sock = MockSocket([b'foobarbaz\r\n'])

        def _set():
            client.set(b'key', b'value', noreply=False)

        tools.assert_raises(MemcacheUnknownError, _set)

    def test_set_many_socket_handling(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set_many({b'key': b'value'}, noreply=False)
        tools.assert_equal(result, True)
        tools.assert_equal(client.sock.closed, False)
        tools.assert_equal(len(client.sock.send_bufs), 1)

    def test_set_many_exception(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n', Exception('fail')])

        def _set():
            client.set_many({b'key': b'value', b'other': b'value'},
                            noreply=False)

        tools.assert_raises(Exception, _set)
        tools.assert_equal(client.sock, None)
        tools.assert_equal(client.buf, b'')

    def test_stats(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STAT fake_stats 1\r\n', b'END\r\n'])
        result = client.stats()
        tools.assert_equal(client.sock.send_bufs, [
            b'stats \r\n'
        ])
        tools.assert_equal(result, {b'fake_stats': 1})

    def test_stats_with_args(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STAT fake_stats 1\r\n', b'END\r\n'])
        result = client.stats('some_arg')
        tools.assert_equal(client.sock.send_bufs, [
            b'stats some_arg\r\n'
        ])
        tools.assert_equal(result, {b'fake_stats': 1})

    def test_stats_conversions(self):
        client = self.Client(None)
        client.sock = MockSocket([
            # Most stats are converted to int
            b'STAT cmd_get 2519\r\n',
            b'STAT cmd_set 3099\r\n',

            # Unless they can't be, they remain str
            b'STAT libevent 2.0.19-stable\r\n',

            # Some named stats are explicitly converted
            b'STAT hash_is_expanding 0\r\n',
            b'STAT rusage_user 0.609165\r\n',
            b'STAT rusage_system 0.852791\r\n',
            b'STAT slab_reassign_running 1\r\n',
            b'STAT version 1.4.14\r\n',
            b'END\r\n',
        ])
        result = client.stats()
        tools.assert_equal(client.sock.send_bufs, [
            b'stats \r\n'
        ])
        expected = {
            b'cmd_get': 2519,
            b'cmd_set': 3099,
            b'libevent': b'2.0.19-stable',
            b'hash_is_expanding': False,
            b'rusage_user': 0.609165,
            b'rusage_system': 0.852791,
            b'slab_reassign_running': True,
            b'version': b'1.4.14',
        }
        tools.assert_equal(result, expected)

    def test_socket_connect(self):
        server = ("example.com", 11211)

        client = Client(server, socket_module=MockSocketModule())
        client._connect()
        tools.assert_equal(client.sock.connections, [server])

        timeout = 2
        connect_timeout = 3
        client = Client(server, connect_timeout=connect_timeout, timeout=timeout,
                        socket_module=MockSocketModule())
        client._connect()
        tools.assert_equal(client.sock.timeouts, [connect_timeout, timeout])

        client = Client(server, socket_module=MockSocketModule())
        client._connect()
        tools.assert_equal(client.sock.socket_options, [])

        client = Client(server, socket_module=MockSocketModule(), no_delay=True)
        client._connect()
        tools.assert_equal(client.sock.socket_options, [(socket.IPPROTO_TCP,
                                                        socket.TCP_NODELAY, 1)])

    def test_python_dict_set_is_supported(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n'])
        client[b'key'] = b'value'

    def test_python_dict_get_is_supported(self):
        client = self.Client(None)
        client.sock = MockSocket([b'VALUE key 0 5\r\nvalue\r\nEND\r\n'])
        tools.assert_equal(client[b'key'], b'value')

    def test_python_dict_get_not_found_is_supported(self):
        client = self.Client(None)
        client.sock = MockSocket([b'END\r\n'])

        def _get():
            _ = client[b'key']

        tools.assert_raises(KeyError, _get)

    def test_python_dict_del_is_supported(self):
        client = self.Client(None)
        client.sock = MockSocket([b'DELETED\r\n'])
        del client[b'key']

    def test_too_long_key(self):
        client = self.Client(None)
        client.sock = MockSocket([b'END\r\n'])
        tools.assert_raises(MemcacheClientError, client.get, b'x' * 251)

    def test_key_contains_spae(self):
        client = self.Client(None)
        client.sock = MockSocket([b'END\r\n'])
        tools.assert_raises(MemcacheClientError, client.get, b'abc xyz')

    def test_key_contains_nonascii(self):
        client = self.Client(None)
        client.sock = MockSocket([b'END\r\n'])
        tools.assert_raises(MemcacheClientError, client.get, u'\u3053\u3093\u306b\u3061\u306f')


class TestMockClient(ClientTestMixin, unittest.TestCase):
    Client = MockMemcacheClient


class TestPrefixedClient(ClientTestMixin, unittest.TestCase):
    def Client(self, *args, **kwargs):
        return Client(*args, key_prefix=b'xyz:', **kwargs)

    def test_get_found(self):
        client = self.Client(None)
        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set(b'key', b'value', noreply=False)

        client.sock = MockSocket([b'VALUE xyz:key 0 5\r\nvalue\r\nEND\r\n'])
        result = client.get(b'key')
        tools.assert_equal(result, b'value')

    def test_get_many_some_found(self):
        client = self.Client(None)

        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set(b'key1', b'value1', noreply=False)

        client.sock = MockSocket([b'VALUE xyz:key1 0 6\r\nvalue1\r\nEND\r\n'])
        result = client.get_many([b'key1', b'key2'])
        tools.assert_equal(result, {b'key1': b'value1'})

    def test_get_many_all_found(self):
        client = self.Client(None)

        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set(b'key1', b'value1', noreply=False)

        client.sock = MockSocket([b'STORED\r\n'])
        result = client.set(b'key2', b'value2', noreply=False)

        client.sock = MockSocket([b'VALUE xyz:key1 0 6\r\nvalue1\r\n'
                                  b'VALUE xyz:key2 0 6\r\nvalue2\r\nEND\r\n'])
        result = client.get_many([b'key1', b'key2'])
        tools.assert_equal(result, {b'key1': b'value1', b'key2': b'value2'})

    def test_python_dict_get_is_supported(self):
        client = self.Client(None)
        client.sock = MockSocket([b'VALUE xyz:key 0 5\r\nvalue\r\nEND\r\n'])
        tools.assert_equal(client[b'key'], b'value')

########NEW FILE########
__FILENAME__ = test_utils
from nose import tools
import six

from pymemcache.test.utils import MockMemcacheClient


def test_get_set():
    client = MockMemcacheClient()
    tools.assert_equal(client.get(b"hello"), None)

    client.set(b"hello", 12)
    tools.assert_equal(client.get(b"hello"), 12)


def test_get_many_set_many():
    client = MockMemcacheClient()
    client.set(b"h", 1)

    tools.assert_equal(client.get_many([b"h", b"e", b"l", b"o"]),
                       {b"h": 1})

    # Convert keys into bytes
    d = dict((k.encode('ascii'), v)
             for k, v in six.iteritems(dict(h=1, e=2, l=3)))
    client.set_many(d)
    tools.assert_equal(client.get_many([b"h", b"e", b"l", b"o"]),
                       d)


def test_add():
    client = MockMemcacheClient()

    client.add(b"k", 2)
    tools.assert_equal(client.get(b"k"), 2)

    client.add(b"k", 25)
    tools.assert_equal(client.get(b"k"), 2)


def test_delete():
    client = MockMemcacheClient()

    client.add(b"k", 2)
    tools.assert_equal(client.get(b"k"), 2)

    client.delete(b"k")
    tools.assert_equal(client.get(b"k"), None)


def test_incr_decr():
    client = MockMemcacheClient()

    client.add(b"k", 2)

    client.incr(b"k", 4)
    tools.assert_equal(client.get(b"k"), 6)

    client.decr(b"k", 2)
    tools.assert_equal(client.get(b"k"), 4)

########NEW FILE########
__FILENAME__ = utils
"""
Useful testing utilities.

This module is considered public API.

"""

import time

import six

from pymemcache.client import MemcacheIllegalInputError


class MockMemcacheClient(object):
    """
    A (partial) in-memory mock for Clients.

    """

    def __init__(self,
                 server=None,
                 serializer=None,
                 deserializer=None,
                 connect_timeout=None,
                 timeout=None,
                 no_delay=False,
                 ignore_exc=False):

        self._contents = {}

        self.serializer = serializer
        self.deserializer = deserializer

        # Unused, but present for interface compatibility
        self.server = server
        self.connect_timeout = connect_timeout
        self.timeout = timeout
        self.no_delay = no_delay
        self.ignore_exc = ignore_exc

    def get(self, key):
        if isinstance(key, six.text_type):
            raise MemcacheIllegalInputError(key)

        if key not in self._contents:
            return None

        expire, value, was_serialized = self._contents[key]
        if expire and expire < time.time():
            del self._contents[key]
            return None

        if self.deserializer:
            return self.deserializer(key, value, 2 if was_serialized else 1)
        return value

    def get_many(self, keys):
        out = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                out[key] = value
        return out

    def set(self, key, value, expire=0, noreply=True):
        if isinstance(key, six.text_type):
            raise MemcacheIllegalInputError(key)
        if isinstance(value, six.text_type):
            raise MemcacheIllegalInputError(value)

        was_serialized = False
        if self.serializer:
            value = self.serializer(key, value)

        if expire:
            expire += time.time()

        self._contents[key] = expire, value, was_serialized
        return True

    def set_many(self, values, expire=None, noreply=True):
        for key, value in six.iteritems(values):
            self.set(key, value, expire, noreply)
        return True

    def incr(self, key, value, noreply=False):
        current = self.get(key)
        present = current is not None
        if present:
            self.set(key, current + value, noreply=noreply)
        return None if noreply or not present else current + value

    def decr(self, key, value, noreply=False):
        current = self.get(key)
        if current is None:
            return

        self.set(key, current - value, noreply=noreply)
        return current - value

    def add(self, key, value, expire=None, noreply=True):
        current = self.get(key)
        present = current is not None
        if not present:
            self.set(key, value, expire, noreply)
        return not present

    def delete(self, key, noreply=True):
        current = self._contents.pop(key, None)
        present = current is not None
        return noreply or present

    def stats(self):
        # I make no claim that these values make any sense, but the format
        # of the output is the same as for pymemcache.client.Client.stats()
        return {
            "version": "MockMemcacheClient",
            "rusage_user": 1.0,
            "rusage_system": 1.0,
            "hash_is_expanding": False,
            "slab_reassign_running": False,
            "inter": "in-memory",
            "evictions": False,
            "growth_factor": 1.0,
            "stat_key_prefix": "",
            "umask": 0o644,
            "detail_enabled": False,
            "cas_enabled": False,
            "auth_enabled_sasl": False,
            "maxconns_fast": False,
            "slab_reassign": False,
            "slab_automove": False,
        }

########NEW FILE########
