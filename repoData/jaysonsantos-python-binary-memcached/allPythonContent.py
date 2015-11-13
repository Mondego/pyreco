__FILENAME__ = client
import logging
from bmemcached.protocol import Protocol

try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps


class Client(object):
    """
    This is intended to be a client class which implement standard cache interface that common libs do.
    """
    def __init__(self, servers=['127.0.0.1:11211'], username=None,
                 password=None, compression=None):
        """
        :param servers: A list of servers with ip[:port] or unix socket.
        :type servers: list
        :param username: If your server have auth activated, provide it's username.
        :type username: basestring
        :param password: If your server have auth activated, provide it's password.
        :type password: basestring
        """
        self.username = username
        self.password = password
        self.compression = compression
        self.set_servers(servers)


    @property
    def servers(self):
        for server in self._servers:
            yield server

    def set_servers(self, servers):
        """
        Iter to a list of servers and instantiate Protocol class.

        :param servers: A list of servers
        :type servers: list
        :return: Returns nothing
        :rtype: None
        """
        if isinstance(servers, basestring):
            servers = [servers]

        assert servers, "No memcached servers supplied"
        self._servers = [Protocol(server, self.username, self.password,
                                  self.compression) for server in servers]

    def _set_retry_delay(self, value):
        for server in self._servers:
            server.set_retry_delay(value)

    def enable_retry_delay(self, enable):
        """
        Enable or disable delaying between reconnection attempts.

        The first reconnection attempt will always happen immediately, so intermittent network
        errors don't cause caching to turn off.  The retry delay takes effect after the first
        reconnection fails.

        The reconnection delay is enabled by default for TCP connections, and disabled by
        default for Unix socket connections.
        """
        # The public API only allows enabling or disabling the delay, so it'll be easier to
        # add exponential falloff in the future.  _set_retry_delay is exposed for tests.
        self._set_retry_delay(5 if enable else 0)

    def get(self, key, get_cas=False):
        """
        Get a key from server.

        :param key: Key's name
        :type key: basestring
        :param get_cas: If true, return (value, cas), where cas is the new CAS value.
        :type get_cas: boolean
        :return: Returns a key data from server.
        :rtype: object
        """
        for server in self.servers:
            value, cas = server.get(key)
            if value is not None:
                if get_cas:
                    return value, cas
                else:
                    return value

    def gets(self, key):
        """
        Get a key from server, returning the value and its CAS key.

        This method is for API compatibility with other implementations.

        :param key: Key's name
        :type key: basestring
        :return: Returns (key data, value), or (None, None) if the value is not in cache.
        :rtype: object
        """
        for server in self.servers:
            value, cas = server.get(key)
            if value is not None:
                return value, cas
        return None, None

    def get_multi(self, keys, get_cas=False):
        """
        Get multiple keys from server.

        :param keys: A list of keys to from server.
        :type keys: list
        :param get_cas: If get_cas is true, each value is (data, cas), with each result's CAS value.
        :type get_cas: boolean
        :return: A dict with all requested keys.
        :rtype: dict
        """
        d = {}
        if keys:
            for server in self.servers:
                results = server.get_multi(keys)
                if not get_cas:
                    for key, (value, cas) in results.items():
                        results[key] = value
                d.update(results)
                keys = [_ for _ in keys if not _ in d]
                if not keys:
                    break
        return d

    def set(self, key, value, time=0):
        """
        Set a value for a key on server.

        :param key: Key's name
        :type key: basestring
        :param value: A value to be stored on server.
        :type value: object
        :param time: Time in seconds that your key will expire.
        :type time: int
        :return: True in case of success and False in case of failure
        :rtype: bool
        """
        returns = []
        for server in self.servers:
            returns.append(server.set(key, value, time))

        return any(returns)

    def cas(self, key, value, cas, time=0):
        """
        Set a value for a key on server if its CAS value matches cas.

        :param key: Key's name
        :type key: basestring
        :param value: A value to be stored on server.
        :type value: object
        :param time: Time in seconds that your key will expire.
        :type time: int
        :return: True in case of success and False in case of failure
        :rtype: bool
        """
        returns = []
        for server in self.servers:
            returns.append(server.cas(key, value, cas, time))

        return any(returns)

    def set_multi(self, mappings, time=0):
        """
        Set multiple keys with it's values on server.

        :param mappings: A dict with keys/values
        :type mappings: dict
        :param time: Time in seconds that your key will expire.
        :type time: int
        :return: True in case of success and False in case of failure
        :rtype: bool
        """
        returns = []
        if mappings:
            for server in self.servers:
                returns.append(server.set_multi(mappings, time))

        return all(returns)

    def add(self, key, value, time=0):
        """
        Add a key/value to server ony if it does not exist.

        :param key: Key's name
        :type key: basestring
        :param value: A value to be stored on server.
        :type value: object
        :param time: Time in seconds that your key will expire.
        :type time: int
        :return: True if key is added False if key already exists
        :rtype: bool
        """
        returns = []
        for server in self.servers:
            returns.append(server.add(key, value, time))

        return any(returns)

    def replace(self, key, value, time=0):
        """
        Replace a key/value to server ony if it does exist.

        :param key: Key's name
        :type key: basestring
        :param value: A value to be stored on server.
        :type value: object
        :param time: Time in seconds that your key will expire.
        :type time: int
        :return: True if key is replace False if key does not exists
        :rtype: bool
        """
        returns = []
        for server in self.servers:
            returns.append(server.replace(key, value, time))

        return any(returns)

    def delete(self, key, cas=0):
        """
        Delete a key/value from server. If key does not exist, it returns True.

        :param key: Key's name to be deleted
        :type key: basestring
        :return: True in case o success and False in case of failure.
        :rtype: bool
        """
        returns = []
        for server in self.servers:
            returns.append(server.delete(key, cas))

        return any(returns)

    def incr(self, key, value):
        """
        Increment a key, if it exists, returns it's actual value, if it don't, return 0.

        :param key: Key's name
        :type key: basestring
        :param value: Number to be incremented
        :type value: int
        :return: Actual value of the key on server
        :rtype: int
        """
        returns = []
        for server in self.servers:
            returns.append(server.incr(key, value))

        return returns[0]

    def decr(self, key, value):
        """
        Decrement a key, if it exists, returns it's actual value, if it don't, return 0.
        Minimum value of decrement return is 0.

        :param key: Key's name
        :type key: basestring
        :param value: Number to be decremented
        :type value: int
        :return: Actual value of the key on server
        :rtype: int
        """
        returns = []
        for server in self.servers:
            returns.append(server.decr(key, value))

        return returns[0]

    def flush_all(self, time=0):
        """
        Send a command to server flush|delete all keys.

        :param time: Time to wait until flush in seconds.
        :type time: int
        :return: True in case of success, False in case of failure
        :rtype: bool
        """
        returns = []
        for server in self.servers:
            returns.append(server.flush_all(time))

        return any(returns)

    def stats(self, key=None):
        """
        Return server stats.

        :param key: Optional if you want status from a key.
        :type key: basestring
        :return: A dict with server stats
        :rtype: dict
        """
        # TODO: Stats with key is not working.

        returns = {}
        for server in self.servers:
            returns[server.server] = server.stats(key)

        return returns

    def disconnect_all(self):
        """
        Disconnect all servers.

        :return: Nothing
        :rtype: None
        """
        for server in self.servers:
            server.disconnect()

########NEW FILE########
__FILENAME__ = exceptions
class MemcachedException(Exception):
    pass


class AuthenticationNotSupported(MemcachedException):
    pass


class InvalidCredentials(MemcachedException):
    pass

########NEW FILE########
__FILENAME__ = protocol
try:
    from cPickle import dumps, loads
except ImportError:
    from pickle import dumps, loads

from datetime import datetime, timedelta
import logging
import re
import socket
import struct
import threading
from urllib import splitport
import zlib

from bmemcached.exceptions import AuthenticationNotSupported, InvalidCredentials, MemcachedException


logger = logging.getLogger(__name__)


class Protocol(threading.local):
    """
    This class is used by Client class to communicate with server.
    """
    HEADER_STRUCT = '!BBHBBHLLQ'
    HEADER_SIZE = 24

    MAGIC = {
        'request': 0x80,
        'response': 0x81
    }

    # All structures will be appended to HEADER_STRUCT
    COMMANDS = {
        'get': {'command': 0x00, 'struct': '%ds'},
        'getk': {'command': 0x0C, 'struct': '%ds'},
        'getkq': {'command': 0x0D, 'struct': '%ds'},
        'set': {'command': 0x01, 'struct': 'LL%ds%ds'},
        'setq': {'command': 0x11, 'struct': 'LL%ds%ds'},
        'add': {'command': 0x02, 'struct': 'LL%ds%ds'},
        'addq': {'command': 0x12, 'struct': 'LL%ds%ds'},
        'replace': {'command': 0x03, 'struct': 'LL%ds%ds'},
        'delete': {'command': 0x04, 'struct': '%ds'},
        'incr': {'command': 0x05, 'struct': 'QQL%ds'},
        'decr': {'command': 0x06, 'struct': 'QQL%ds'},
        'flush': {'command': 0x08, 'struct': 'I'},
        'noop': {'command': 0x0a, 'struct': ''},
        'stat': {'command': 0x10},
        'auth_negotiation': {'command': 0x20},
        'auth_request': {'command': 0x21, 'struct': '%ds%ds'},
    }

    STATUS = {
        'success': 0x00,
        'key_not_found': 0x01,
        'key_exists': 0x02,
        'auth_error': 0x08,
        'unknown_command': 0x81,

        # This is used internally, and is never returned by the server.  (The server returns a 16-bit
        # value, so it's not capable of returning this value.)
        'server_disconnected': 0xFFFFFFFF,
    }

    FLAGS = {
        'pickle': 1 << 0,
        'integer': 1 << 1,
        'long': 1 << 2,
        'compressed': 1 << 3
    }

    COMPRESSION_THRESHOLD = 128

    def __init__(self, server, username=None, password=None, compression=None):
        self.server = server
        self._username = username
        self._password = password

        self.compression = zlib if compression is None else compression
        self.connection = None
        self.authenticated = False

        self.reconnects_deferred_until = None

        if not server.startswith('/'):
            self.host, self.port = self.split_host_port(self.server)
            self.set_retry_delay(5)
        else:
            self.host = self.port = None
            self.set_retry_delay(0)

    @property
    def server_uses_unix_socket(self):
        return self.host is None

    def set_retry_delay(self, value):
        self.retry_delay = value

    def _open_connection(self):
        if self.connection:
            return

        self.authenticated = False

        # If we're deferring a reconnection attempt, wait.
        if self.reconnects_deferred_until and self.reconnects_deferred_until > datetime.now():
            return

        try:
            if self.host:
                self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connection.connect((self.host, self.port))
            else:
                self.connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.connection.connect(self.server)

            self._send_authentication()
        except socket.error:
            # If the connection attempt fails, start delaying retries.
            self.reconnects_deferred_until = datetime.now() + timedelta(seconds=self.retry_delay)
            raise

    def _connection_error(self, exception):
        # On error, clear our dead connection.
        self.disconnect()

    @classmethod
    def split_host_port(cls, server):
        """
        Return (host, port) from server.

        Port defaults to 11211.

        >>> split_host_port('127.0.0.1:11211')
        ('127.0.0.1', 11211)
        >>> split_host_port('127.0.0.1')
        ('127.0.0.1', 11211)
        """
        host, port = splitport(server)
        if port is None:
            port = 11211
        port = int(port)
        if re.search(':.*$', host):
            host = re.sub(':.*$', '', host)
        return host, port

    def _read_socket(self, size):
        """
        Reads data from socket.

        :param size: Size in bytes to be read.
        :type size: int
        :return: Data from socket
        :rtype: basestring
        """
        value = ''
        while len(value) < size:
            data = self.connection.recv(size - len(value))
            if not data:
                break
            value += data

        # If we got less data than we requested, the server disconnected.
        if len(value) < size:
            raise socket.error()

        return value

    def _get_response(self):
        """
        Get memcached response from socket.

        :return: A tuple with binary values from memcached.
        :rtype: tuple
        """
        try:
            self._open_connection()
            if self.connection is None:
                # The connection wasn't opened, which means we're deferring a reconnection attempt.
                # Raise a socket.error, so we'll return the same server_disconnected message as we
                # do below.
                raise socket.error('Delaying reconnection attempt')

            header = self._read_socket(self.HEADER_SIZE)
            (magic, opcode, keylen, extlen, datatype, status, bodylen, opaque,
             cas) = struct.unpack(self.HEADER_STRUCT, header)

            assert magic == self.MAGIC['response']

            extra_content = None
            if bodylen:
                extra_content = self._read_socket(bodylen)

            return (magic, opcode, keylen, extlen, datatype, status, bodylen,
                    opaque, cas, extra_content)
        except socket.error as e:
            self._connection_error(e)

            # (magic, opcode, keylen, extlen, datatype, status, bodylen, opaque, cas, extra_content)
            message = str(e)
            return (self.MAGIC['response'], -1, 0, 0, 0, self.STATUS['server_disconnected'], 0, 0, 0, message)

    def _send(self, data):
        try:
            self._open_connection()
            if self.connection is None:
                return

            self.connection.sendall(data)
        except socket.error as e:
            self._connection_error(e)

    def authenticate(self, username, password):
        """
        Authenticate user on server.

        :param username: Username used to be authenticated.
        :type username: basestring
        :param password: Password used to be authenticated.
        :type password: basestring
        :return: True if successful.
        :raises: InvalidCredentials, AuthenticationNotSupported, MemcachedException
        :rtype: bool
        """
        self._username = username
        self._password = password

        # Reopen the connection with the new credentials.
        self.disconnect()
        self._open_connection()
        return self.authenticated

    def _send_authentication(self):
        if not self._username or not self._password:
            return False

        logger.info('Authenticating as %s' % self._username)
        self._send(struct.pack(self.HEADER_STRUCT,
                                         self.MAGIC['request'],
                                         self.COMMANDS['auth_negotiation']['command'],
                                         0, 0, 0, 0, 0, 0, 0))

        (magic, opcode, keylen, extlen, datatype, status, bodylen, opaque,
         cas, extra_content) = self._get_response()

        if status == self.STATUS['server_disconnected']:
            return False

        if status == self.STATUS['unknown_command']:
            logger.debug('Server does not requires authentication.')
            self.authenticated = True
            return True

        methods = extra_content

        if not 'PLAIN' in methods:
            raise AuthenticationNotSupported('This module only supports '
                                             'PLAIN auth for now.')

        method = 'PLAIN'
        auth = '\x00%s\x00%s' % (self._username, self._password)
        self._send(struct.pack(self.HEADER_STRUCT +
                                         self.COMMANDS['auth_request']['struct'] % (len(method), len(auth)),
                                         self.MAGIC['request'], self.COMMANDS['auth_request']['command'],
                                         len(method), 0, 0, 0, len(method) + len(auth), 0, 0, method, auth))

        (magic, opcode, keylen, extlen, datatype, status, bodylen, opaque,
         cas, extra_content) = self._get_response()

        if status == self.STATUS['server_disconnected']:
            return False

        if status == self.STATUS['auth_error']:
            raise InvalidCredentials("Incorrect username or password")

        if status != self.STATUS['success']:
            raise MemcachedException('Code: %d Message: %s' % (status, extra_content))

        logger.debug('Auth OK. Code: %d Message: %s' % (status, extra_content))

        self.authenticated = True
        return True

    def serialize(self, value):
        """
        Serializes a value based on it's type.

        :param value: Something to be serialized
        :type value: basestring, int, long, object
        :return: Serialized type
        :rtype: str
        """
        flags = 0
        if isinstance(value, str):
            pass
        elif isinstance(value, int) and isinstance(value, bool) is False:
            flags |= self.FLAGS['integer']
            value = str(value)
        elif isinstance(value, long):
            flags |= self.FLAGS['long']
            value = str(value)
        else:
            flags |= self.FLAGS['pickle']
            value = dumps(value)

        if len(value) > self.COMPRESSION_THRESHOLD:
            value = self.compression.compress(value)
            flags |= self.FLAGS['compressed']

        return flags, value

    def deserialize(self, value, flags):
        """
        Deserialized values based on flags or just return it if it is not serialized.

        :param value: Serialized or not value.
        :type value: basestring, int
        :param flags: Value flags
        :type flags: int
        :return: Deserialized value
        :rtype: basestring|int
        """
        if flags & self.FLAGS['compressed']:  # pragma: no branch
            value = self.compression.decompress(value)

        if flags & self.FLAGS['integer']:
            return int(value)
        elif flags & self.FLAGS['long']:
            return long(value)
        elif flags & self.FLAGS['pickle']:
            return loads(value)

        return value

    def get(self, key):
        """
        Get a key and its CAS value from server.  If the value isn't cached, return
        (None, None).

        :param key: Key's name
        :type key: basestring
        :return: Returns (value, cas).
        :rtype: object
        """
        logger.info('Getting key %s' % key)
        data = struct.pack(self.HEADER_STRUCT +
                                         self.COMMANDS['get']['struct'] % (len(key)),
                                         self.MAGIC['request'],
                                         self.COMMANDS['get']['command'],
                                         len(key), 0, 0, 0, len(key), 0, 0, key)
        self._send(data)

        (magic, opcode, keylen, extlen, datatype, status, bodylen, opaque,
         cas, extra_content) = self._get_response()

        logger.debug('Value Length: %d. Body length: %d. Data type: %d' % (
            extlen, bodylen, datatype))

        if status != self.STATUS['success']:
            if status == self.STATUS['key_not_found']:
                logger.debug('Key not found. Message: %s'
                             % extra_content)
                return None, None

            if status == self.STATUS['server_disconnected']:
                return None, None

            raise MemcachedException('Code: %d Message: %s' % (status, extra_content))

        flags, value = struct.unpack('!L%ds' % (bodylen - 4, ), extra_content)

        return self.deserialize(value, flags), cas

    def get_multi(self, keys):
        """
        Get multiple keys from server.

        :param keys: A list of keys to from server.
        :type keys: list
        :return: A dict with all requested keys.
        :rtype: dict
        """
        # pipeline N-1 getkq requests, followed by a regular getk to uncork the
        # server
        keys, last = keys[:-1], keys[-1]
        msg = ''.join([
            struct.pack(self.HEADER_STRUCT +
                        self.COMMANDS['getkq']['struct'] % (len(key)),
                        self.MAGIC['request'],
                        self.COMMANDS['getkq']['command'],
                        len(key), 0, 0, 0, len(key), 0, 0, key)
            for key in keys])
        msg += struct.pack(self.HEADER_STRUCT +
                           self.COMMANDS['getk']['struct'] % (len(last)),
                           self.MAGIC['request'],
                           self.COMMANDS['getk']['command'],
                           len(last), 0, 0, 0, len(last), 0, 0, last)

        self._send(msg)

        d = {}
        opcode = -1
        while opcode != self.COMMANDS['getk']['command']:
            (magic, opcode, keylen, extlen, datatype, status, bodylen, opaque,
             cas, extra_content) = self._get_response()

            if status == self.STATUS['success']:
                flags, key, value = struct.unpack('!L%ds%ds' %
                                                  (keylen, bodylen - keylen - 4),
                                                  extra_content)
                d[key] = self.deserialize(value, flags), cas
            elif status == self.STATUS['server_disconnected']:
                break
            elif status != self.STATUS['key_not_found']:
                raise MemcachedException('Code: %d Message: %s' % (status, extra_content))

        return d

    def _set_add_replace(self, command, key, value, time, cas=0):
        """
        Function to set/add/replace commands.

        :param key: Key's name
        :type key: basestring
        :param value: A value to be stored on server.
        :type value: object
        :param time: Time in seconds that your key will expire.
        :type time: int
        :param cas: The CAS value that must be matched for this operation to complete, or 0 for no CAS.
        :type cas: int
        :return: True in case of success and False in case of failure
        :rtype: bool
        """
        logger.info('Setting/adding/replacing key %s.' % key)
        flags, value = self.serialize(value)
        logger.info('Value bytes %d.' % len(value))

        self._send(struct.pack(self.HEADER_STRUCT +
                                         self.COMMANDS[command]['struct'] % (len(key), len(value)),
                                         self.MAGIC['request'],
                                         self.COMMANDS[command]['command'],
                                         len(key),
                                         8, 0, 0, len(key) + len(value) + 8, 0, cas, flags,
                                         time, key, value))

        (magic, opcode, keylen, extlen, datatype, status, bodylen, opaque,
         cas, extra_content) = self._get_response()

        if status != self.STATUS['success']:
            if status == self.STATUS['key_exists']:
                return False
            elif status == self.STATUS['key_not_found']:
                return False
            elif status == self.STATUS['server_disconnected']:
                return False
            raise MemcachedException('Code: %d Message: %s' % (status, extra_content))

        return True

    def set(self, key, value, time):
        """
        Set a value for a key on server.

        :param key: Key's name
        :type key: basestring
        :param value: A value to be stored on server.
        :type value: object
        :param time: Time in seconds that your key will expire.
        :type time: int
        :return: True in case of success and False in case of failure
        :rtype: bool
        """
        return self._set_add_replace('set', key, value, time)

    def cas(self, key, value, cas, time):
        """
        Add a key/value to server ony if it does not exist.

        :param key: Key's name
        :type key: basestring
        :param value: A value to be stored on server.
        :type value: object
        :param time: Time in seconds that your key will expire.
        :type time: int
        :return: True if key is added False if key already exists and has a different CAS
        :rtype: bool
        """
        # The protocol CAS value 0 means "no cas".  Calling cas() with that value is
        # probably unintentional.  Don't allow it, since it would overwrite the value
        # without performing CAS at all.
        assert cas != 0, '0 is an invalid CAS value'

        # If we get a cas of None, interpret that as "compare against nonexistant and set",
        # which is simply Add.
        if cas is None:
            return self._set_add_replace('add', key, value, time)
        else:
            return self._set_add_replace('set', key, value, time, cas=cas)

    def add(self, key, value, time):
        """
        Add a key/value to server ony if it does not exist.

        :param key: Key's name
        :type key: basestring
        :param value: A value to be stored on server.
        :type value: object
        :param time: Time in seconds that your key will expire.
        :type time: int
        :return: True if key is added False if key already exists
        :rtype: bool
        """
        return self._set_add_replace('add', key, value, time)

    def replace(self, key, value, time):
        """
        Replace a key/value to server ony if it does exist.

        :param key: Key's name
        :type key: basestring
        :param value: A value to be stored on server.
        :type value: object
        :param time: Time in seconds that your key will expire.
        :type time: int
        :return: True if key is replace False if key does not exists
        :rtype: bool
        """
        return self._set_add_replace('replace', key, value, time)

    def set_multi(self, mappings, time=100):
        """
        Set multiple keys with its values on server.

        If a key is a (key, cas) tuple, insert as if cas(key, value, cas) had
        been called.

        :param mappings: A dict with keys/values
        :type mappings: dict
        :param time: Time in seconds that your key will expire.
        :type time: int
        :return: True
        :rtype: bool
        """
        mappings = mappings.items()
        msg = []

        for key, value in mappings:
            if isinstance(key, tuple):
                key, cas = key
            else:
                cas = None

            final = False
            if cas == 0:
                # Like cas(), if the cas value is 0, treat it as compare-and-set against not
                # existing.
                command = 'addq'
            else:
                command = 'setq'

            flags, value = self.serialize(value)
            m = struct.pack(self.HEADER_STRUCT +
                            self.COMMANDS[command]['struct'] % (len(key), len(value)),
                            self.MAGIC['request'],
                            self.COMMANDS[command]['command'],
                            len(key),
                            8, 0, 0, len(key) + len(value) + 8, 0, cas or 0,
                            flags, time, key, value)
            msg.append(m)

        m = struct.pack(self.HEADER_STRUCT +
                        self.COMMANDS['noop']['struct'],
                        self.MAGIC['request'],
                        self.COMMANDS['noop']['command'],
                        0, 0, 0, 0, 0, 0, 0)
        msg.append(m)

        msg = ''.join(msg)

        self._send(msg)

        opcode = -1
        retval = True
        while opcode != self.COMMANDS['noop']['command']:
            (magic, opcode, keylen, extlen, datatype, status, bodylen, opaque,
             cas, extra_content) = self._get_response()
            if status != self.STATUS['success']:
                retval = False
            if status == self.STATUS['server_disconnected']:
                break

        return retval

    def _incr_decr(self, command, key, value, default, time):
        """
        Function which increments and decrements.

        :param key: Key's name
        :type key: basestring
        :param value: Number to be (de|in)cremented
        :type value: int
        :param default: Default value if key does not exist.
        :type default: int
        :param time: Time in seconds to expire key.
        :type time: int
        :return: Actual value of the key on server
        :rtype: int
        """
        self._send(struct.pack(self.HEADER_STRUCT +
                                         self.COMMANDS[command]['struct'] % len(key),
                                         self.MAGIC['request'],
                                         self.COMMANDS[command]['command'],
                                         len(key),
                                         20, 0, 0, len(key) + 20, 0, 0, value,
                                         default, time, key))

        (magic, opcode, keylen, extlen, datatype, status, bodylen, opaque,
         cas, extra_content) = self._get_response()

        if status not in (self.STATUS['success'], self.STATUS['server_disconnected']):
            raise MemcachedException('Code: %d Message: %s' % (status, extra_content))
        if status == self.STATUS['server_disconnected']:
            return 0

        return struct.unpack('!Q', extra_content)[0]

    def incr(self, key, value, default=0, time=1000000):
        """
        Increment a key, if it exists, returns it's actual value, if it don't, return 0.

        :param key: Key's name
        :type key: basestring
        :param value: Number to be incremented
        :type value: int
        :param default: Default value if key does not exist.
        :type default: int
        :param time: Time in seconds to expire key.
        :type time: int
        :return: Actual value of the key on server
        :rtype: int
        """
        return self._incr_decr('incr', key, value, default, time)

    def decr(self, key, value, default=0, time=100):
        """
        Decrement a key, if it exists, returns it's actual value, if it don't, return 0.
        Minimum value of decrement return is 0.

        :param key: Key's name
        :type key: basestring
        :param value: Number to be decremented
        :type value: int
        :param default: Default value if key does not exist.
        :type default: int
        :param time: Time in seconds to expire key.
        :type time: int
        :return: Actual value of the key on server
        :rtype: int
        """
        return self._incr_decr('decr', key, value, default, time)

    def delete(self, key, cas=0):
        """
        Delete a key/value from server. If key existed and was deleted, it returns True.

        :param key: Key's name to be deleted
        :type key: basestring
        :param cas: If set, only delete the key if its CAS value matches.
        :type cas: int
        :return: True in case o success and False in case of failure.
        :rtype: bool
        """
        logger.info('Deleting key %s' % key)
        self._send(struct.pack(self.HEADER_STRUCT +
                                         self.COMMANDS['delete']['struct'] % len(key),
                                         self.MAGIC['request'],
                                         self.COMMANDS['delete']['command'],
                                         len(key), 0, 0, 0, len(key), 0, cas, key))

        (magic, opcode, keylen, extlen, datatype, status, bodylen, opaque,
         cas, extra_content) = self._get_response()

        if status == self.STATUS['server_disconnected']:
            return False
        if status != self.STATUS['success'] and status not in (self.STATUS['key_not_found'], self.STATUS['key_exists']):
            raise MemcachedException('Code: %d message: %s' % (status, extra_content))

        logger.debug('Key deleted %s' % key)
        return status != self.STATUS['key_exists']

    def flush_all(self, time):
        """
        Send a command to server flush|delete all keys.

        :param time: Time to wait until flush in seconds.
        :type time: int
        :return: True in case of success, False in case of failure
        :rtype: bool
        """
        logger.info('Flushing memcached')
        self._send(struct.pack(self.HEADER_STRUCT +
                                         self.COMMANDS['flush']['struct'],
                                         self.MAGIC['request'],
                                         self.COMMANDS['flush']['command'],
                                         0, 4, 0, 0, 4, 0, 0, time))

        (magic, opcode, keylen, extlen, datatype, status, bodylen, opaque,
         cas, extra_content) = self._get_response()

        if status not in (self.STATUS['success'], self.STATUS['server_disconnected']):
            raise MemcachedException('Code: %d message: %s' % (status, extra_content))

        logger.debug('Memcached flushed')
        return True

    def stats(self, key=None):
        """
        Return server stats.

        :param key: Optional if you want status from a key.
        :type key: basestring
        :return: A dict with server stats
        :rtype: dict
        """
        # TODO: Stats with key is not working.
        if key is not None:
            keylen = len(key)
            packed = struct.pack(
                self.HEADER_STRUCT + '%ds' % keylen,
                self.MAGIC['request'],
                self.COMMANDS['stat']['command'],
                keylen, 0, 0, 0, keylen, 0, 0, key)
        else:
            packed = struct.pack(
                self.HEADER_STRUCT,
                self.MAGIC['request'],
                self.COMMANDS['stat']['command'],
                0, 0, 0, 0, 0, 0, 0)

        self._send(packed)

        value = {}

        while True:
            response = self._get_response()

            status = response[5]
            if status == self.STATUS['server_disconnected']:
                break

            keylen = response[2]
            bodylen = response[6]

            if keylen == 0 and bodylen == 0:
                break

            extra_content = response[-1]
            key = extra_content[:keylen]
            body = extra_content[keylen:bodylen]
            value[key] = body

        return value

    def disconnect(self):
        """
        Disconnects from server.  A new connection will be established the next time a request is made.

        :return: Nothing
        :rtype: None
        """
        if self.connection:
            self.connection.close()
            self.connection = None


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Python Binary Memcached (bmemached) documentation build configuration file, created by
# sphinx-quickstart on Mon Apr 15 12:02:27 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Python Binary Memcached (bmemached)'
copyright = u'2013, Jayson Reis'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.17'
# The full version, including alpha/beta/rc tags.
release = '0.17'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'PythonBinaryMemcachedbmemacheddoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'PythonBinaryMemcachedbmemached.tex', u'Python Binary Memcached (bmemached) Documentation',
   u'Jayson Reis', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'pythonbinarymemcachedbmemached', u'Python Binary Memcached (bmemached) Documentation',
     [u'Jayson Reis'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'PythonBinaryMemcachedbmemached', u'Python Binary Memcached (bmemached) Documentation',
   u'Jayson Reis', 'PythonBinaryMemcachedbmemached', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = test_auth
import mock
import unittest
import bmemcached
from bmemcached.exceptions import AuthenticationNotSupported, InvalidCredentials, MemcachedException


class TestServerAuth(unittest.TestCase):
    @mock.patch.object(bmemcached.client.Protocol, '_get_response')
    def testServerDoesntNeedAuth(self, mocked_response):
        """
        If 0x81 ('unkown_command') comes back in the status field when
        authenticating, it isn't needed.
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 0)
        server = bmemcached.client.Protocol('127.0.0.1')
        # can pass anything and it'll work
        self.assertTrue(server.authenticate('user', 'badpassword'))

    @mock.patch.object(bmemcached.client.Protocol, '_get_response')
    def testNotUsingPlainAuth(self, mocked_response):
        """
        Raise AuthenticationNotSupported unless we're using PLAIN auth.
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0, 0, 0, 0, [])
        server = bmemcached.client.Protocol('127.0.0.1')
        self.assertRaises(AuthenticationNotSupported,
                          server.authenticate, 'user', 'password')

    @mock.patch.object(bmemcached.client.Protocol, '_get_response')
    def testAuthNotSuccessful(self, mocked_response):
        """
        Raise MemcachedException for anything unsuccessful.
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0x01, 0, 0, 0, ['PLAIN'])
        server = bmemcached.client.Protocol('127.0.0.1')
        self.assertRaises(MemcachedException,
                          server.authenticate, 'user', 'password')

    @mock.patch.object(bmemcached.client.Protocol, '_get_response')
    def testAuthSuccessful(self, mocked_response):
        """
        Valid logins return True.
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0, 0, 0, 0, ['PLAIN'])
        server = bmemcached.client.Protocol('127.0.0.1')
        self.assertTrue(server.authenticate('user', 'password'))

    @mock.patch.object(bmemcached.client.Protocol, '_get_response')
    def testAuthUnsuccessful(self, mocked_response):
        """
        Invalid logins raise InvalidCredentials
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0x08, 0, 0, 0, ['PLAIN'])
        server = bmemcached.client.Protocol('127.0.0.1')
        self.assertRaises(InvalidCredentials, server.authenticate,
                          'user', 'password2')

########NEW FILE########
__FILENAME__ = test_compression
import unittest
import bmemcached
import bz2

class MemcachedTests(unittest.TestCase):
    def setUp(self):
        self.server = '127.0.0.1:11211'
        self.client = bmemcached.Client(self.server, 'user', 'password')
        self.bzclient = bmemcached.Client(self.server, 'user', 'password', bz2)
        self.data = b'this is test data. ' * 32

    def tearDown(self):
        self.client.delete(b'test_key')
        self.client.delete(b'test_key2')
        self.client.disconnect_all()
        self.bzclient.disconnect_all()

    def testCompressedData(self):
        self.client.set(b'test_key', self.data)
        self.assertEqual(self.data, self.client.get(b'test_key'))

    def testBZ2CompressedData(self):
        self.bzclient.set(b'test_key', self.data)
        self.assertEqual(self.data, self.bzclient.get(b'test_key'))

    def testCompressionMissmatch(self):
        self.client.set(b'test_key', self.data)
        self.bzclient.set(b'test_key2', self.data)
        self.assertEqual(self.client.get(b'test_key'),
                self.bzclient.get(b'test_key2'))
        self.assertRaises(IOError, self.bzclient.get, b'test_key')


########NEW FILE########
__FILENAME__ = test_errors
import unittest
import mock
import bmemcached
from bmemcached.exceptions import MemcachedException


class TestMemcachedErrors(unittest.TestCase):
    def testGet(self):
        """
        Raise MemcachedException if request wasn't successful and
        wasn't a 'key not found' error.
        """
        client = bmemcached.Client('127.0.0.1:11211', 'user', 'password')
        with mock.patch.object(bmemcached.client.Protocol, '_get_response') as mocked_response:
            mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 0)
            self.assertRaises(MemcachedException, client.get, 'foo')

    def testSet(self):
        """
        Raise MemcachedException if request wasn't successful and
        wasn't a 'key not found' or 'key exists' error.
        """
        client = bmemcached.Client('127.0.0.1:11211', 'user', 'password')
        with mock.patch.object(bmemcached.client.Protocol, '_get_response') as mocked_response:
            mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 0)
            self.assertRaises(MemcachedException, client.set, 'foo', 'bar', 300)

    def testIncrDecr(self):
        """
        Incr/Decr raise MemcachedException unless the request wasn't
        successful.
        """
        client = bmemcached.Client('127.0.0.1:11211', 'user', 'password')
        client.set('foo', 1)
        with mock.patch.object(bmemcached.client.Protocol, '_get_response') as mocked_response:
            mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 2)
            self.assertRaises(MemcachedException, client.incr, 'foo', 1)
            self.assertRaises(MemcachedException, client.decr, 'foo', 1)

    def testDelete(self):
        """
        Raise MemcachedException if the delete request isn't successful.
        """
        client = bmemcached.Client('127.0.0.1:11211', 'user', 'password')
        client.flush_all()
        with mock.patch.object(bmemcached.client.Protocol, '_get_response') as mocked_response:
            mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 0)
            self.assertRaises(MemcachedException, client.delete, 'foo')

    def testFlushAll(self):
        """
        Raise MemcachedException if the flush wasn't successful.
        """
        client = bmemcached.Client('127.0.0.1:11211', 'user', 'password')
        with mock.patch.object(bmemcached.client.Protocol, '_get_response') as mocked_response:
            mocked_response.return_value = (0, 0, 0, 0, 0, 0x81, 0, 0, 0, 0)
            self.assertRaises(MemcachedException, client.flush_all)


########NEW FILE########
__FILENAME__ = test_error_handling
import multiprocessing, select, socket, threading, time, unittest
import bmemcached
from bmemcached.protocol import Protocol


class _CacheProxy(multiprocessing.Process):
    def __init__(self, server, pipe, listen_port=None):
        super(_CacheProxy, self).__init__()
        self._listen_port = listen_port
        self.server = server
        self.pipe = pipe

    def run(self):
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_sock.setblocking(False)
        listen_sock.bind(('127.0.0.1', self._listen_port or 0))
        listen_sock.listen(1)

        # Tell our caller the (host, port) that we're listening on.
        self.pipe.send(listen_sock.getsockname())

        # Open a connection to the real memcache server.
        if not self.server.startswith('/'):
            host, port = Protocol.split_host_port(self.server)
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.connect((host, port))
        else:
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.connect(self.server)

        # The connection to this server above is blocking, but reads and writes below are nonblocking.
        server_sock.setblocking(False)

        # listen_sock is the socket we're listening for connections on.  We only handle
        # a single connection at a time.
        # client_sock is the connection we've accepted from listen_sock.
        # server_sock is the connection to the actual server.
        client_sock = None

        # Data waiting to be sent to client_sock:
        data_for_client = ''

        # Data waiting to be sent to server_sock:
        data_for_server = ''

        while True:
            read_sockets = [listen_sock]
            write_sockets = []

            sockets = [listen_sock]
            if client_sock:
                # Only add client_sock to read_sockets if we don't already have data
                # from it waiting to be sent to the real server.
                if not data_for_server:
                    read_sockets.append(client_sock)

                # Only add client_sock to write_sockets if we have data to send.
                if data_for_client:
                    write_sockets.append(client_sock)

            if not data_for_client:
                read_sockets.append(server_sock)
            if data_for_server:
                write_sockets.append(server_sock)

            r, w, _ = select.select(read_sockets, write_sockets, [])
            if listen_sock in r:
                if client_sock:
                    client_sock.close()
                client_sock, client_addr = listen_sock.accept()
                client_sock.setblocking(False)

            if server_sock in r:
                data_for_client += server_sock.recv(1024)

            if client_sock in r:
                data_for_server += client_sock.recv(1024)

            if server_sock in w:
                bytes_written = server_sock.send(data_for_server)
                data_for_server = data_for_server[bytes_written:]

            if client_sock in w:
                bytes_written = client_sock.send(data_for_client)
                data_for_client = data_for_client[bytes_written:]

class MemcachedTests(unittest.TestCase):
    def setUp(self):
        self._proxy_port = None

        # Start a helper to proxy requests to the actual memcache server.  This uses a
        # process instead of a thread, so we can simply kill the process between tests.
        self._start_proxy()
        self._stop_proxy()
        self._start_proxy()

        self.client = bmemcached.Client(self.server)

        # Disable retry delays, so we can disconnect and reconnect from the
        # server without needing to put delays in most of the tests.
        self.client.enable_retry_delay(False)

        # Clean up from any previous tests.
        self.client.delete('test_key')
        self.client.delete('test_key2')

    def _server_host(self):
        return '127.0.0.1:11211'

    def _start_proxy(self):
        # Start the proxy.  If this isn't the first time we've started the proxy,
        # use the same port we got the first time around.
        parent_pipe, child_pipe = multiprocessing.Pipe()
        self._proxy_thread = _CacheProxy(self._server_host(), child_pipe, self._proxy_port)
        self._proxy_thread.start()

        # Read the port the server is actually listening on.  If we supplied a port, it
        # will always be the same.  This also guarantees that the process is listening on
        # the port before we continue and try to connect to it.
        sockname = parent_pipe.recv()
        self._proxy_port = sockname[1]
        self.server = '%s:%i' % sockname

    def _stop_proxy(self):
        if not self._proxy_thread:
            return

        # Kill the proxy, which causes communication to the server to fail.
        self._proxy_thread.terminate()
        self._proxy_thread.join()
        self._proxy_thread = None

    def tearDown(self):
        self.client.disconnect_all()
        self._stop_proxy()

    def testSet(self):
        self.assertTrue(self.client.set('test_key', 'test'))
        self._stop_proxy()
        self.assertFalse(self.client.set('test_key', 'test'))

    def testSetMulti(self):
        self.assertTrue(self.client.set_multi({
            'test_key': 'value',
            'test_key2': 'value2'}))

        self._stop_proxy()

        self.assertFalse(self.client.set_multi({
            'test_key': 'value',
            'test_key2': 'value2'}))

    def testGet(self):
        self.client.set('test_key', 'test')
        self.assertEqual('test', self.client.get('test_key'))

        # If the server is offline, get always returns None.
        self._stop_proxy()
        self.assertTrue(self.client.get('test_key') is None)

        # After the server comes back online, gets will resume.
        self._start_proxy()
        self.assertEqual('test', self.client.get('test_key'))

    def testRetryDelay(self):
        # Test delaying retries.  We only enable retry delays for this test, since we
        # need to pause to test it, which slows down the test.
        self.client._set_retry_delay(0.25)

        self.client.set('test_key', 'test')
        self.assertEqual('test', self.client.get('test_key'))

        # If the server is offline, get always returns None.  This request will cause
        # the client to notice that the connection is offline, but not to retry the
        # request.
        self._stop_proxy()
        self.assertTrue(self.client.get('test_key') is None)

        # If we start the proxy again now, it'll reconnect immediately without any delay.
        self._start_proxy()
        self.assertEqual('test', self.client.get('test_key'))

        # Stop the proxy again, and make another request to cause the client to notice the
        # disconnection.
        self._stop_proxy()
        self.assertTrue(self.client.get('test_key') is None)

        # Make another request.  As above, the client will attempt a reconnection here, but
        # the server is still offline so it'll fail.  This will cause the retry delay to
        # kick in.
        # After the server comes back online, gets will continue to return None for 0.25
        # second, since delays are still deferred.
        self.assertTrue(self.client.get('test_key') is None)

        # Start the server.  This time, attempting to read from the server won't cause a
        # connection attempt, because we're still delaying.
        self._start_proxy()
        self.assertTrue(self.client.get('test_key') is None)

        # Sleep until the retry delay has elapsed, and verify that we connect to the server
        # this time.
        time.sleep(0.3)
        self.assertEqual('test', self.client.get('test_key'))

    def testGetMulti(self):
        self.assertTrue(self.client.set_multi({
            'test_key': 'value',
            'test_key2': 'value2'
        }))
        self.assertEqual({'test_key': 'value', 'test_key2': 'value2'},
                         self.client.get_multi(['test_key', 'test_key2']))

        self._stop_proxy()

        self.assertEqual({}, self.client.get_multi(['test_key', 'test_key2']))

        self._start_proxy()

        self.assertEqual({'test_key': 'value', 'test_key2': 'value2'},
                         self.client.get_multi(['test_key', 'test_key2']))

    def testDelete(self):
        self._stop_proxy()
        self.assertFalse(self.client.delete('test_key'))

    def testAdd(self):
        self._stop_proxy()
        self.assertFalse(self.client.add('test_key', 'test'))

    def testReplace(self):
        self._stop_proxy()
        self.assertFalse(self.client.replace('test_key', 'value2'))

    def testIncrement(self):
        self._stop_proxy()
        self.assertEqual(0, self.client.incr('test_key', 1))
        self.assertEqual(0, self.client.incr('test_key', 1))

    def testDecrement(self):
        self._stop_proxy()
        self.assertEqual(0, self.client.decr('test_key', 1))

    def testFlush(self):
        self._stop_proxy()
        self.assertTrue(self.client.flush_all())

    def testStats(self):
        self._stop_proxy()
        stats = self.client.stats()[self.server]
        self.assertEqual(stats, {})

class SocketMemcachedTests(MemcachedTests):
    """
    Same tests as above, just make sure it works with sockets.
    """
    def _server_host(self):
        return '/tmp/memcached.sock'


########NEW FILE########
__FILENAME__ = test_server_parsing
import mock
import unittest
import bmemcached


class TestServerParsing(unittest.TestCase):
    def testAcceptStringServer(self):
        client = bmemcached.Client('127.0.0.1:11211')
        self.assertEqual(len(list(client.servers)), 1)

    def testAcceptIterableServer(self):
        client = bmemcached.Client(['127.0.0.1:11211', '127.0.0.1:11211'])
        self.assertEqual(len(list(client.servers)), 2)

    def testNoPortGiven(self):
        server = bmemcached.client.Protocol('127.0.0.1')
        self.assertEqual(server.host, '127.0.0.1')
        self.assertEqual(server.port, 11211)

    def testInvalidPort(self):
        server = bmemcached.client.Protocol('127.0.0.1:blah')
        self.assertEqual(server.host, '127.0.0.1')
        self.assertEqual(server.port, 11211)

    def testNonStandardPort(self):
        server = bmemcached.client.Protocol('127.0.0.1:5000')
        self.assertEqual(server.host, '127.0.0.1')
        self.assertEqual(server.port, 5000)

    def testAcceptUnixSocket(self):
        client = bmemcached.Client('/tmp/memcached.sock')
        self.assertEqual(len(list(client.servers)), 1)

    @mock.patch.object(bmemcached.client.Protocol, '_get_response')
    def testPassCredentials(self, mocked_response):
        """
        If username/password passed to Client, auto-authenticate.
        """
        mocked_response.return_value = (0, 0, 0, 0, 0, 0, 0, 0, 0, ['PLAIN'])
        client = bmemcached.Client('127.0.0.1:11211', username='user',
                                   password='password')
        server = list(client.servers)[0]

        # Force a connection.  Normally this is only done when we make a request to the
        # server.
        server._send_authentication()

        self.assertTrue(server.authenticated)

    @mock.patch.object(bmemcached.client.Protocol, '_get_response')
    def testNoCredentialsNoAuth(self, mocked_response):
        mocked_response.return_value = (0, 0, 0, 0, 0, 0x01, 0, 0, 0, ['PLAIN'])
        client = bmemcached.Client('127.0.0.1:11211')
        server = list(client.servers)[0]

        # Force a connection.  Normally this is only done when we make a request to the
        # server.
        server._send_authentication()

        self.assertFalse(server.authenticated)

    def testNoServersSupplied(self):
        """
        Raise assertion if the server list is empty.
        """
        self.assertRaises(AssertionError, bmemcached.Client, [])

########NEW FILE########
__FILENAME__ = test_simple_functions
import unittest
import bmemcached
from bmemcached.protocol import Protocol


class MemcachedTests(unittest.TestCase):
    def setUp(self):
        self.server = '127.0.0.1:11211'
        self.server = '/tmp/memcached.sock'
        self.client = bmemcached.Client(self.server) #, 'user', 'password')

    def tearDown(self):
        self.reset()
        self.client.disconnect_all()
        
    def reset(self):
        self.client.delete('test_key')
        self.client.delete('test_key2')

    def testSet(self):
        self.assertTrue(self.client.set('test_key', 'test'))

    def testSetMulti(self):
        self.assertTrue(self.client.set_multi({
            'test_key': 'value',
            'test_key2': 'value2'}))

    def testSetMultiBigData(self):
        self.client.set_multi(dict(
                (unicode(k).encode(), b'value') for k in range(32767)))

    def testGet(self):
        self.client.set('test_key', 'test')
        self.assertEqual('test', self.client.get('test_key'))

    def testCas(self):
        value, cas = self.client.gets('nonexistant')
        self.assertTrue(value is None)
        self.assertTrue(cas is None)

        # cas() with a cas value of None is equivalent to add.
        self.assertTrue(self.client.cas('test_key', 'test', cas))
        self.assertFalse(self.client.cas('test_key', 'testX', cas))

        # Load the CAS key.
        value, cas = self.client.gets('test_key')
        self.assertEqual('test', value)
        self.assertTrue(cas is not None)

        # Overwrite test_key only if it hasn't changed since we read it.
        self.assertTrue(self.client.cas('test_key', 'test2', cas))
        self.assertEqual(self.client.get('test_key'), 'test2')

        # This call won't overwrite the value, since the CAS key is out of date.
        self.assertFalse(self.client.cas('test_key', 'test3', cas))
        self.assertEqual(self.client.get('test_key'), 'test2')

    def testCasDelete(self):
        self.assertTrue(self.client.set('test_key', 'test'))
        value, cas = self.client.gets('test_key')

        # If a different CAS value is supplied, the key is not deleted.
        self.assertFalse(self.client.delete('test_key', cas=cas+1))
        self.assertEqual('test', self.client.get('test_key'))

        # If the correct CAS value is supplied, the key is deleted.
        self.assertTrue(self.client.delete('test_key', cas=cas))
        self.assertEqual(None, self.client.get('test_key'))

    def testMultiCas(self):
        # Set multiple values, some using CAS and some not.  True is returned, because
        # both values were stored.
        self.assertTrue(self.client.set_multi({
            ('test_key', 0): 'value1',
            'test_key2': 'value2',
        }))

        self.assertEqual(self.client.get('test_key'), 'value1')
        self.assertEqual(self.client.get('test_key2'), 'value2')

        # A CAS value of 0 means add.  The value already exists, so this won't overwrite it.
        # False is returned, because not all items were stored, but test_key2 is still stored.
        self.assertFalse(self.client.set_multi({
            ('test_key', 0): 'value3',
            'test_key2': 'value3',
        }))

        self.assertEqual(self.client.get('test_key'), 'value1')
        self.assertEqual(self.client.get('test_key2'), 'value3')

        # Update with the correct CAS value.
        value, cas = self.client.gets('test_key')
        self.assertTrue(self.client.set_multi({
            ('test_key', cas): 'value4',
        }))
        self.assertEqual(self.client.get('test_key'), 'value4')

    def testGetMultiCas(self):
        self.client.set('test_key', 'value1')
        self.client.set('test_key2', 'value2')

        value1, cas1 = self.client.gets('test_key')
        value2, cas2 = self.client.gets('test_key2')

        # Batch retrieve items and their CAS values, and verify that they match
        # the values we got by looking them up individually.
        values = self.client.get_multi(['test_key', 'test_key2'], get_cas=True)
        self.assertEqual(values.get('test_key')[0], 'value1')
        self.assertEqual(values.get('test_key2')[0], 'value2')

    def testGetEmptyString(self):
        self.client.set('test_key', '')
        self.assertEqual('', self.client.get('test_key'))

    def testGetMulti(self):
        self.assertTrue(self.client.set_multi({
            'test_key': 'value',
            'test_key2': 'value2'
        }))
        self.assertEqual({'test_key': 'value', 'test_key2': 'value2'},
                         self.client.get_multi(['test_key', 'test_key2']))
        self.assertEqual({'test_key': 'value', 'test_key2': 'value2'},
                         self.client.get_multi(['test_key', 'test_key2', 'nothere']))

    def testGetLong(self):
        self.client.set('test_key', 1L)
        value = self.client.get('test_key')
        self.assertEqual(1L, value)
        self.assertTrue(isinstance(value, long))

    def testGetInteger(self):
        self.client.set('test_key', 1)
        value = self.client.get('test_key')
        self.assertEqual(1, value)
        self.assertTrue(isinstance(value, int))

    def testGetBoolean(self):
        self.client.set('test_key', True)
        self.assertTrue(self.client.get('test_key') is True)

    def testGetObject(self):
        self.client.set('test_key', {'a': 1})
        value = self.client.get('test_key')
        self.assertTrue(isinstance(value, dict))
        self.assertTrue('a' in value)
        self.assertEqual(1, value['a'])

    def testDelete(self):
        self.client.set('test_key', 'test')
        self.assertTrue(self.client.delete('test_key'))
        self.assertEqual(None, self.client.get('test_key'))

    def testDeleteUnknownKey(self):
        self.assertTrue(self.client.delete('test_key'))

    def testAddPass(self):
        self.assertTrue(self.client.add('test_key', 'test'))

    def testAddFail(self):
        self.client.add('test_key', 'value')
        self.assertFalse(self.client.add('test_key', 'test'))

    def testReplacePass(self):
        self.client.add('test_key', 'value')
        self.assertTrue(self.client.replace('test_key', 'value2'))
        self.assertEqual('value2', self.client.get('test_key'))

    def testReplaceFail(self):
        self.assertFalse(self.client.replace('test_key', 'value'))

    def testIncrement(self):
        self.assertEqual(0, self.client.incr('test_key', 1))
        self.assertEqual(1, self.client.incr('test_key', 1))

    def testDecrement(self):
        self.assertEqual(0, self.client.decr('test_key', 1))
        self.assertEqual(0, self.client.decr('test_key', 1))

    def testFlush(self):
        self.client.set('test_key', 'test')
        self.assertTrue(self.client.flush_all())
        self.assertEqual(None, self.client.get('test_key'))

    def testStats(self):
        stats = self.client.stats()[self.server]
        self.assertTrue('pid' in stats)

        stats = self.client.stats('settings')[self.server]
        self.assertTrue('verbosity' in stats)

        stats = self.client.stats('slabs')[self.server]
        self.assertTrue('1:get_hits' in stats)

    def testReconnect(self):
        self.client.set('test_key', 'test')
        self.client.disconnect_all()
        self.assertEqual('test', self.client.get('test_key'))

########NEW FILE########
__FILENAME__ = test_socket
import bmemcached
import test_simple_functions


class SocketMemcachedTests(test_simple_functions.MemcachedTests):
    """
    Same tests as above, just make sure it works with sockets.
    """
    def setUp(self):
        self.server = '/tmp/memcached.sock'
        self.client = bmemcached.Client(self.server, 'user', 'password')

########NEW FILE########
__FILENAME__ = threading-processing-safe
import logging
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

import concurrent.futures

import bmemcached

c = bmemcached.Client('127.0.0.1:11211')


def get(key):
    return c.get(key)

with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
    f = [executor.submit(get, '12345690') for i in xrange(20)]

    for future in concurrent.futures.as_completed(f):
        print future.result()

########NEW FILE########
