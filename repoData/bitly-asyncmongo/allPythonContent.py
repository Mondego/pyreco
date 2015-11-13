__FILENAME__ = asyncjobs
#!/bin/env python
#
# Copyright 2013 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Tools for creating `messages
<http://www.mongodb.org/display/DOCS/Mongo+Wire+Protocol>`_ to be sent to
MongoDB.

.. note:: This module is for internal use and is generally not needed by
   application developers.
"""

import logging
import random
from bson import SON

import message
import helpers
from errors import AuthenticationError, RSConnectionError, InterfaceError


class AsyncMessage(object):
    def __init__(self, connection, message, callback):
        super(AsyncMessage, self).__init__()
        self.connection = connection
        self.message = message
        self.callback = callback

    def process(self, *args, **kwargs):
        try:
            self.connection._send_message(self.message, self.callback)
        except Exception, e:
            if self.callback is None:
                logging.error("Error occurred in safe update mode: %s", e)
            else:
                self.callback(None, e)


class AsyncJob(object):
    def __init__(self, connection, state, err_callback):
        super(AsyncJob, self).__init__()
        self.connection = connection
        self._err_callback = err_callback
        self._state = state

    def _error(self, e):
        self.connection.close()
        if self._err_callback:
            self._err_callback(e)

    def update_err_callback(self, err_callback):
        self._err_callback = err_callback

    def __repr__(self):
        return "%s at 0x%X, state = %r" % (self.__class__.__name__, id(self), self._state)


class AuthorizeJob(AsyncJob):
    def __init__(self, connection, dbuser, dbpass, pool, err_callback):
        super(AuthorizeJob, self).__init__(connection, "start", err_callback)
        self.dbuser = dbuser
        self.dbpass = dbpass
        self.pool = pool

    def process(self, response=None, error=None):
        if error:
            logging.debug("Error during authentication: %r", error)
            self._error(AuthenticationError(error))
            return

        if self._state == "start":
            self._state = "nonce"
            logging.debug("Sending nonce")
            msg = message.query(
                0,
                "%s.$cmd" % self.pool._dbname,
                0,
                1,
                SON({'getnonce': 1}),
                SON({})
            )
            self.connection._send_message(msg, self.process)
        elif self._state == "nonce":
            # this is the nonce response
            self._state = "finish"
            try:
                nonce = response['data'][0]['nonce']
                logging.debug("Nonce received: %r", nonce)
                key = helpers._auth_key(nonce, self.dbuser, self.dbpass)
            except Exception, e:
                self._error(AuthenticationError(e))
                return

            msg = message.query(
                0,
                "%s.$cmd" % self.pool._dbname,
                0,
                1,
                SON([('authenticate', 1),
                     ('user', self.dbuser),
                     ('nonce', nonce),
                     ('key', key)]),
                SON({})
            )
            self.connection._send_message(msg, self.process)
        elif self._state == "finish":
            self._state = "done"
            try:
                assert response['number_returned'] == 1
                response = response['data'][0]
            except Exception, e:
                self._error(AuthenticationError(e))
                return

            if response.get("ok") != 1:
                logging.debug("Failed authentication %s", response.get("errmsg"))
                self._error(AuthenticationError(response.get("errmsg")))
                return
            self.connection._next_job()
        else:
            self._error(ValueError("Unexpected state: %s" % self._state))


class ConnectRSJob(AsyncJob):
    def __init__(self, connection, seed, rs, secondary_only, err_callback):
        super(ConnectRSJob, self).__init__(connection, "seed", err_callback)
        self.known_hosts = set(seed)
        self.rs = rs
        self._blacklisted = set()
        self._primary = None
        self._sec_only = secondary_only

    def process(self, response=None, error=None):
        if error:
            logging.debug("Problem connecting: %s", error)

            if self._state == "ismaster":
                self._state = "seed"

        if self._state == "seed":
            if self._sec_only and self._primary:
                # Add primary host to blacklisted to avoid connecting to it
                self._blacklisted.add(self._primary)

            fresh = self.known_hosts ^ self._blacklisted
            logging.debug("Working through the rest of the host list: %r", fresh)

            while fresh:
                if self._primary and self._primary not in self._blacklisted:
                    # Try primary first
                    h = self._primary
                else:
                    h = random.choice(list(fresh))

                if h in fresh:
                    fresh.remove(h)

                # Add tried host to blacklisted
                self._blacklisted.add(h)

                logging.debug("Connecting to %s:%s", *h)
                self.connection._host, self.connection._port = h
                try:
                    self.connection._socket_connect()
                    logging.debug("Connected to %s", h)
                except InterfaceError, e:
                    logging.error("Failed to connect to the host: %s", e)
                else:
                    break

            else:
                self._error(RSConnectionError("No more hosts to try, tried: %s" % self.known_hosts))
                return

            self._state = "ismaster"
            msg = message.query(
                options=0,
                collection_name="admin.$cmd",
                num_to_skip=0,
                num_to_return=-1,
                query=SON([("ismaster", 1)])
            )
            self.connection._send_message(msg, self.process)

        elif self._state == "ismaster":
            logging.debug("ismaster response: %r", response)

            try:
                assert len(response["data"]) == 1
                res = response["data"][0]
            except Exception, e:
                self._error(RSConnectionError("Invalid response data: %r" % response.get("data")))
                return

            rs_name = res.get("setName")
            if rs_name and rs_name != self.rs:
                self._error(RSConnectionError("Wrong replica set: %s, expected: %s" % (rs_name, self.rs)))
                return

            hosts = res.get("hosts")
            if hosts:
                self.known_hosts.update(helpers._parse_host(h) for h in hosts)

            ismaster = res.get("ismaster")
            hidden = res.get("hidden")
            try:
                if ismaster and not self._sec_only:  # master and required to connect to primary
                    assert not hidden, "Primary cannot be hidden"
                    logging.debug("Connected to master (%s)", res.get("me", "unknown"))
                    self._state = "done"
                    self.connection._next_job()
                elif not ismaster and self._sec_only and not hidden:  # not master and required to connect to secondary
                    assert res.get("secondary"), "Secondary must self-report as secondary"
                    logging.debug("Connected to secondary (%s)", res.get("me", "unknown"))
                    self._state = "done"
                    self.connection._next_job()
                else:  # either not master and primary connection required or master and secondary required
                    primary = res.get("primary")
                    if primary:
                        self._primary = helpers._parse_host(primary)
                    self._state = "seed"
                    self.process()
            except Exception, e:
                self._error(RSConnectionError(e))
                return


########NEW FILE########
__FILENAME__ = glib2_backend
#!/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import glib

class Glib2Stream(object):
    def __init__(self, socket, **kwargs):
        self.__socket = socket
        self.__close_id = None
        self.__read_id = None
        self.__read_queue = []

    def write(self, data):
        self.__socket.send(data)
    
    def read(self, size, callback):
        self.__read_queue.append((size, callback))

        if not self.__read_id:
            self.set_waiting()

    def set_waiting(self):
        if self.__read_id:
            glib.source_remove(self.__read_id)

        self.__read_id = glib.io_add_watch(
            self.__socket,
            glib.IO_IN,
            self.__on_read_callback)

    def set_idle(self):
        if self.__read_id:
            glib.source_remove(self.__read_id)

    def __on_read_callback(self, source, condition):
        if not self.__read_queue:
            self.set_idle()
            return False

        size, callback = self.__read_queue.pop(0)
        data = self.__socket.recv(size)
        callback(data)
        return True

    def set_close_callback(self, callback):
        if self.__close_id:
            glib.source_remove(self.__close_id)

        self.__close_callback = callback
        self.__close_id = glib.io_add_watch(self.__socket,
                                           glib.IO_HUP|glib.IO_ERR,
                                            self.__on_close_callback)

    def __on_close_callback(self, source, cb_condition, *args, **kwargs):
        self.__close_callback()

    def close(self):
        if self.__close_id:
            glib.source_remove(self.__close_id)

        self.__socket.close()

class AsyncBackend(object):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AsyncBackend, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance

    def register_stream(self, socket, **kwargs):
        return Glib2Stream(socket, **kwargs)

########NEW FILE########
__FILENAME__ = glib3_backend
#!/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from gi.repository import GObject

class Glib3Stream(object):
    def __init__(self, socket, **kwargs):
        self.__socket = socket
        self.__close_id = None
        self.__read_id = None
        self.__read_queue = []

    def write(self, data):
        self.__socket.send(data)
    
    def read(self, size, callback):
        self.__read_queue.append((size, callback))

        if not self.__read_id:
            self.set_waiting()

    def set_waiting(self):
        if self.__read_id:
            GObject.source_remove(self.__read_id)

        self.__read_id = GObject.io_add_watch(
            self.__socket,
            GObject.IO_IN,
            self.__on_read_callback)

    def set_idle(self):
        if self.__read_id:
            GObject.source_remove(self.__read_id)

    def __on_read_callback(self, source, condition):
        if not self.__read_queue:
            self.set_idle()
            return False

        size, callback = self.__read_queue.pop(0)
        data = self.__socket.recv(size)
        callback(data)
        return True

    def set_close_callback(self, callback):
        if self.__close_id:
            GObject.source_remove(self.__close_id)

        self.__close_callback = callback
        self.__close_id = GObject.io_add_watch(self.__socket,
                                               GObject.IO_HUP|GObject.IO_ERR,
                                               self.__on_close_callback)

    def __on_close_callback(self, source, cb_condition, *args, **kwargs):
        self.__close_callback()

    def close(self):
        if self.__close_id:
            GObject.source_remove(self.__close_id)

        self.__socket.close()

class AsyncBackend(object):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AsyncBackend, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance

    def register_stream(self, socket, **kwargs):
        return Glib3Stream(socket, **kwargs)

########NEW FILE########
__FILENAME__ = tornado_backend
#!/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.iostream

class TornadoStream(object):
    def __init__(self, socket, **kwargs):
        """
        :Parameters:
          - `socket`: TCP socket
          - `**kwargs`: passed to `tornado.iostream.IOStream`
            - `io_loop` (optional): Tornado IOLoop instance.
            - `max_buffer_size` (optional):
            - `read_chunk_size` (optional):
        """
        self.__stream = tornado.iostream.IOStream(socket, **kwargs)

    def write(self, data):
        self.__stream.write(data)
    
    def read(self, size, callback):
        self.__stream.read_bytes(size, callback=callback)

    def set_close_callback(self, callback):
        self.__stream.set_close_callback(callback)

    def close(self):
        self.__stream._close_callback = None
        self.__stream.close()

class AsyncBackend(object):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AsyncBackend, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance

    def register_stream(self, socket, **kwargs):
        """
        :Parameters:
          - `socket`: TCP socket
          - `**kwargs`: passed to `tornado.iostream.IOStream`
            - `io_loop` (optional): Tornado IOLoop instance.
            - `max_buffer_size` (optional):
            - `read_chunk_size` (optional):
        """
        return TornadoStream(socket, **kwargs)

########NEW FILE########
__FILENAME__ = client
#!/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from errors import DataError
from pool import ConnectionPools
from cursor import Cursor
from bson.son import SON
from functools import partial

class Client(object):
    """
    Client connection to represent a remote database.
    
    Internally Client maintains a pool of connections that will live beyond the life of this object.
    
    :Parameters:
      - `pool_id`: unique id for this connection pool
      - `**kwargs`: passed to `pool.ConnectionPool`
          - `mincached` (optional): minimum connections to open on instantiation. 0 to open connections on first use
          - `maxcached` (optional): maximum inactive cached connections for this pool. 0 for unlimited
          - `maxconnections` (optional): maximum open connections for this pool. 0 for unlimited
          - `maxusage` (optional): number of requests allowed on a connection before it is closed. 0 for unlimited
          - `dbname`: mongo database name
          - `backend': async loop backend, default = tornado
      - `**kwargs`: passed to `connection.Connection`
          - `host`: hostname or ip of mongo host
          - `port`: port to connect to
          - `slave_okay` (optional): is it okay to connect directly to and perform queries on a slave instance
          - `autoreconnect` (optional): auto reconnect on interface errors
    
    @returns a `Client` instance that wraps a `pool.ConnectionPool`
    
    Usage:
        >>> db = asyncmongo.Client(pool_id, host=host, port=port, dbname=dbname)
        >>> db.collectionname.find({...}, callback=...)
        
    """
    def __init__(self, pool_id=None, **kwargs):
        self._pool = ConnectionPools.get_connection_pool(pool_id, **kwargs)
    
    def __getattr__(self, name):
        """Get a collection by name.

        :Parameters:
          - `name`: the name of the collection
        """
        return self.connection(name)

    def __getitem__(self, name):
        """Get a collection by name.
        :Parameters:
          - `name`: the name of the collection to get
        """
        return self.connection(name)
    
    def connection(self, collectionname, dbname=None):
        """Get a cursor to a collection by name.

        raises `DataError` on names with unallowable characters.

        :Parameters:
          - `collectionname`: the name of the collection
          - `dbname`: (optional) overide the default db for a connection
          
        """
        if not collectionname or ".." in collectionname:
            raise DataError("collection names cannot be empty")
        if "$" in collectionname and not (collectionname.startswith("oplog.$main") or
                                collectionname.startswith("$cmd")):
            raise DataError("collection names must not "
                              "contain '$': %r" % collectionname)
        if collectionname.startswith(".") or collectionname.endswith("."):
            raise DataError("collecion names must not start "
                            "or end with '.': %r" % collectionname)
        if "\x00" in collectionname:
            raise DataError("collection names must not contain the "
                              "null character")
        return Cursor(dbname or self._pool._dbname, collectionname, self._pool)

    def collection_names(self, callback):
        """Get a list of all the collection names in selected database"""
        callback = partial(self._collection_names_result, callback)
        self["system.namespaces"].find(_must_use_master=True, callback=callback)

    def _collection_names_result(self, callback, results, error=None):
        """callback to for collection names query, filters out collection names"""
        names = [r['name'] for r in results if r['name'].count('.') == 1]
        assert error == None, repr(error)
        strip = len(self._pool._dbname) + 1
        callback([name[strip:] for name in names])

    def command(self, command, value=1, callback=None,
                check=True, allowable_errors=[], **kwargs):
        """Issue a MongoDB command.

        Send command `command` to the database and return the
        response. If `command` is an instance of :class:`basestring`
        then the command {`command`: `value`} will be sent. Otherwise,
        `command` must be an instance of :class:`dict` and will be
        sent as is.

        Any additional keyword arguments will be added to the final
        command document before it is sent.

        For example, a command like ``{buildinfo: 1}`` can be sent
        using:

        >>> db.command("buildinfo")

        For a command where the value matters, like ``{collstats:
        collection_name}`` we can do:

        >>> db.command("collstats", collection_name)

        For commands that take additional arguments we can use
        kwargs. So ``{filemd5: object_id, root: file_root}`` becomes:

        >>> db.command("filemd5", object_id, root=file_root)

        :Parameters:
          - `command`: document representing the command to be issued,
            or the name of the command (for simple commands only).

            .. note:: the order of keys in the `command` document is
               significant (the "verb" must come first), so commands
               which require multiple keys (e.g. `findandmodify`)
               should use an instance of :class:`~bson.son.SON` or
               a string and kwargs instead of a Python `dict`.

          - `value` (optional): value to use for the command verb when
            `command` is passed as a string
          - `**kwargs` (optional): additional keyword arguments will
            be added to the command document before it is sent

        .. mongodoc:: commands
        """

        if isinstance(command, basestring):
            command = SON([(command, value)])

        command.update(kwargs)

        self.connection("$cmd").find_one(command,callback=callback,
                                       _must_use_master=True,
                                       _is_command=True)

########NEW FILE########
__FILENAME__ = connection
#!/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import socket
import struct
import logging
from types import NoneType
import functools

from errors import ProgrammingError, IntegrityError, InterfaceError
import helpers
import asyncjobs


class Connection(object):
    """
    :Parameters:
      - `host`: hostname or ip of mongo host (not allowed when replica sets are used)
      - `port`: port to connect to (not allowed when replica sets are used)
      - `dbuser`: db user to connect with
      - `dbpass`: db password
      - `autoreconnect` (optional): auto reconnect on interface errors
      - `rs`: replica set name (required when replica sets are used)
      - `seed`: seed list to connect to a replica set (required when replica sets are used)
      - `secondary_only`: (optional, only useful for replica set connections)
         if true, connect to a secondary member only
      - `**kwargs`: passed to `backends.AsyncBackend.register_stream`

    """
    def __init__(self,
                 host=None,
                 port=None,
                 dbuser=None,
                 dbpass=None,
                 autoreconnect=True,
                 pool=None,
                 backend="tornado",
                 rs=None,
                 seed=None,
                 secondary_only=False,
                 **kwargs):
        assert isinstance(autoreconnect, bool)
        assert isinstance(dbuser, (str, unicode, NoneType))
        assert isinstance(dbpass, (str, unicode, NoneType))
        assert isinstance(rs, (str, NoneType))
        assert pool
        assert isinstance(secondary_only, bool)
        
        if rs:
            assert host is None
            assert port is None
            assert isinstance(seed, (set, list))
        else:
            assert isinstance(host, (str, unicode))
            assert isinstance(port, int)
            assert seed is None
        
        self._host = host
        self._port = port
        self.__rs = rs
        self.__seed = seed
        self.__secondary_only = secondary_only
        self.__dbuser = dbuser
        self.__dbpass = dbpass
        self.__stream = None
        self.__callback = None
        self.__alive = False
        self.__autoreconnect = autoreconnect
        self.__pool = pool
        self.__kwargs = kwargs
        self.__backend = self.__load_backend(backend)
        self.__job_queue = []
        self.usage_count = 0

        self.__connect(self.connection_error)

    def connection_error(self, error):
        raise error

    def __load_backend(self, name):
        __import__('asyncmongo.backends.%s_backend' % name)
        mod = sys.modules['asyncmongo.backends.%s_backend' % name]
        return mod.AsyncBackend()
    
    def __connect(self, err_callback):
        # The callback is only called in case of exception by async jobs
        if self.__dbuser and self.__dbpass:
            self._put_job(asyncjobs.AuthorizeJob(self, self.__dbuser, self.__dbpass, self.__pool, err_callback))

        if self.__rs:
            self._put_job(asyncjobs.ConnectRSJob(self, self.__seed, self.__rs, self.__secondary_only, err_callback))
            # Mark the connection as alive, even though it's not alive yet to prevent double-connecting
            self.__alive = True
        else:
            self._socket_connect()

    def _socket_connect(self):
        """create a socket, connect, register a stream with the async backend"""
        self.usage_count = 0
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            s.connect((self._host, self._port))
            self.__stream = self.__backend.register_stream(s, **self.__kwargs)
            self.__stream.set_close_callback(self._socket_close)
            self.__alive = True
        except socket.error, error:
            raise InterfaceError(error)
    
    def _socket_close(self):
        """cleanup after the socket is closed by the other end"""
        callback = self.__callback
        self.__callback = None
        try:
            if callback:
                callback(None, InterfaceError('connection closed'))
        finally:
            # Flush the job queue, don't call the callbacks associated with the remaining jobs
            # since they have already been called as error callback on connection closing
            self.__job_queue = []
            self.__alive = False
            self.__pool.cache(self)
    
    def _close(self):
        """close the socket and cleanup"""
        callback = self.__callback
        self.__callback = None
        try:
            if callback:
                callback(None, InterfaceError('connection closed'))
        finally:
            # Flush the job queue, don't call the callbacks associated with the remaining jobs
            # since they have already been called as error callback on connection closing
            self.__job_queue = []
            self.__alive = False
            self.__stream.close()

    def close(self):
        """close this connection; re-cache this connection object"""
        try:
            self._close()
        finally:
            self.__pool.cache(self)

    def send_message(self, message, callback):
        """ send a message over the wire; callback=None indicates a safe=False call where we write and forget about it"""
        
        if self.__callback is not None:
            raise ProgrammingError('connection already in use')

        if callback:
            err_callback = functools.partial(callback, None)
        else:
            err_callback = None

        # Go and update err_callback for async jobs in queue if any
        for job in self.__job_queue:
            # this is a dirty hack and I hate it, but there is no way of setting the correct
            # err_callback during the connection time
            if isinstance(job, asyncjobs.AsyncJob):
                job.update_err_callback(err_callback)

        if not self.__alive:
            if self.__autoreconnect:
                self.__connect(err_callback)
            else:
                raise InterfaceError('connection invalid. autoreconnect=False')
        
        # Put the current message on the bottom of the queue
        self._put_job(asyncjobs.AsyncMessage(self, message, callback), 0)
        self._next_job()
        
    def _put_job(self, job, pos=None):
        if pos is None:
            pos = len(self.__job_queue)
        self.__job_queue.insert(pos, job)

    def _next_job(self):
        """execute the next job from the top of the queue"""
        if self.__job_queue:
            # Produce message from the top of the queue
            job = self.__job_queue.pop()
            # logging.debug("queue = %s, popped %r", self.__job_queue, job)
            job.process()
    
    def _send_message(self, message, callback):
        # logging.debug("_send_message, msg = %r: queue = %r, self.__callback = %r, callback = %r", 
        #               message, self.__job_queue, self.__callback, callback)

        self.__callback = callback
        self.usage_count +=1
        # __request_id used by get_more()
        (self.__request_id, data) = message
        try:
            self.__stream.write(data)
            if self.__callback:
                self.__stream.read(16, callback=self._parse_header)
            else:
                self.__request_id = None
                self.__pool.cache(self)
        
        except IOError:
            self.__alive = False
            raise
        # return self.__request_id 
    
    def _parse_header(self, header):
        # return self.__receive_data_on_socket(length - 16, sock)
        length = int(struct.unpack("<i", header[:4])[0])
        request_id = struct.unpack("<i", header[8:12])[0]
        assert request_id == self.__request_id, \
            "ids don't match %r %r" % (self.__request_id,
                                       request_id)
        operation = 1 # who knows why
        assert operation == struct.unpack("<i", header[12:])[0]
        try:
            self.__stream.read(length - 16, callback=self._parse_response)
        except IOError:
            self.__alive = False
            raise
    
    def _parse_response(self, response):
        callback = self.__callback
        request_id = self.__request_id
        self.__request_id = None
        self.__callback = None
        if not self.__job_queue:
            # skip adding to the cache because there is something else
            # that needs to be called on this connection for this request
            # (ie: we authenticated, but still have to send the real req)
            self.__pool.cache(self)

        try:
            response = helpers._unpack_response(response, request_id) # TODO: pass tz_awar
        except Exception, e:
            logging.debug('error %s' % e)
            callback(None, e)
            return
        
        if response and response['data'] and response['data'][0].get('err') and response['data'][0].get('code'):
            callback(response, IntegrityError(response['data'][0]['err'], code=response['data'][0]['code']))
            return
        callback(response)

########NEW FILE########
__FILENAME__ = cursor
#!/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

from bson.son import SON

import helpers
import message
import functools

_QUERY_OPTIONS = {
    "tailable_cursor": 2,
    "slave_okay": 4,
    "oplog_replay": 8,
    "no_timeout": 16}

class Cursor(object):
    """ Cursor is a class used to call oeprations on a given db/collection using a specific connection pool.
        it will transparently release connections back to the pool after they receive responses
    """
    def __init__(self, dbname, collection, pool):
        assert isinstance(dbname, (str, unicode))
        assert isinstance(collection, (str, unicode))
        assert isinstance(pool, object)
        
        self.__dbname = dbname
        self.__collection = collection
        self.__pool = pool
        self.__slave_okay = False
    
    @property
    def full_collection_name(self):
        return u'%s.%s' % (self.__dbname, self.__collection)
    
    def drop(self, *args, **kwargs):
        raise NotImplemented("patches accepted")

    def save(self, doc, **kwargs):
        assert isinstance(doc, dict)
        self.insert(doc, **kwargs)

    def insert(self, doc_or_docs,
               manipulate=True, safe=True, check_keys=True, callback=None, **kwargs):
        """Insert a document(s) into this collection.
        
        If `manipulate` is set, the document(s) are manipulated using
        any :class:`~pymongo.son_manipulator.SONManipulator` instances
        that have been added to this
        :class:`~pymongo.database.Database`. Returns the ``"_id"`` of
        the inserted document or a list of ``"_id"`` values of the
        inserted documents.  If the document(s) does not already
        contain an ``"_id"`` one will be added.
        
        If `safe` is ``True`` then the insert will be checked for
        errors, raising :class:`~pymongo.errors.OperationFailure` if
        one occurred. Safe inserts wait for a response from the
        database, while normal inserts do not.
        
        Any additional keyword arguments imply ``safe=True``, and
        will be used as options for the resultant `getLastError`
        command. For example, to wait for replication to 3 nodes, pass
        ``w=3``.
        
        :Parameters:
          - `doc_or_docs`: a document or list of documents to be
            inserted
          - `manipulate` (optional): manipulate the documents before
            inserting?
          - `safe` (optional): check that the insert succeeded?
          - `check_keys` (optional): check if keys start with '$' or
            contain '.', raising :class:`~pymongo.errors.InvalidName`
            in either case
          - `**kwargs` (optional): any additional arguments imply
            ``safe=True``, and will be used as options for the
            `getLastError` command
        
        .. mongodoc:: insert
        """
        if not isinstance(safe, bool):
            raise TypeError("safe must be an instance of bool")
        
        docs = doc_or_docs
        # return_one = False
        if isinstance(docs, dict):
            # return_one = True
            docs = [docs]
        
        # if manipulate:
        #     docs = [self.__database._fix_incoming(doc, self) for doc in docs]
        
        self.__limit = None
        if kwargs:
            safe = True
        
        if safe and not callable(callback):
            raise TypeError("callback must be callable")
        if not safe and callback is not None:
            raise TypeError("callback can not be used with safe=False")
        
        if callback:
            callback = functools.partial(self._handle_response, orig_callback=callback)

        connection = self.__pool.connection()
        try:
            connection.send_message(
                message.insert(self.full_collection_name, docs,
                    check_keys, safe, kwargs), callback=callback)
        except:
            connection.close()
            raise
    
    def remove(self, spec_or_id=None, safe=True, callback=None, **kwargs):
        if not isinstance(safe, bool):
            raise TypeError("safe must be an instance of bool")
        
        if spec_or_id is None:
            spec_or_id = {}
        if not isinstance(spec_or_id, dict):
            spec_or_id = {"_id": spec_or_id}
        
        self.__limit = None
        if kwargs:
            safe = True
        
        if safe and not callable(callback):
            raise TypeError("callback must be callable")
        if not safe and callback is not None:
            raise TypeError("callback can not be used with safe=False")
        
        if callback:
            callback = functools.partial(self._handle_response, orig_callback=callback)

        connection = self.__pool.connection()
        try:
            connection.send_message(
                message.delete(self.full_collection_name, spec_or_id, safe, kwargs),
                    callback=callback)
        except:
            connection.close()
            raise

    
    def update(self, spec, document, upsert=False, manipulate=False,
               safe=True, multi=False, callback=None, **kwargs):
        """Update a document(s) in this collection.
        
        Raises :class:`TypeError` if either `spec` or `document` is
        not an instance of ``dict`` or `upsert` is not an instance of
        ``bool``. If `safe` is ``True`` then the update will be
        checked for errors, raising
        :class:`~pymongo.errors.OperationFailure` if one
        occurred. Safe updates require a response from the database,
        while normal updates do not - thus, setting `safe` to ``True``
        will negatively impact performance.
        
        There are many useful `update modifiers`_ which can be used
        when performing updates. For example, here we use the
        ``"$set"`` modifier to modify some fields in a matching
        document:
        
        .. doctest::
          
          >>> db.test.insert({"x": "y", "a": "b"})
          ObjectId('...')
          >>> list(db.test.find())
          [{u'a': u'b', u'x': u'y', u'_id': ObjectId('...')}]
          >>> db.test.update({"x": "y"}, {"$set": {"a": "c"}})
          >>> list(db.test.find())
          [{u'a': u'c', u'x': u'y', u'_id': ObjectId('...')}]
        
        If `safe` is ``True`` returns the response to the *lastError*
        command. Otherwise, returns ``None``.
        
        # Any additional keyword arguments imply ``safe=True``, and will
        # be used as options for the resultant `getLastError`
        # command. For example, to wait for replication to 3 nodes, pass
        # ``w=3``.
        
        :Parameters:
          - `spec`: a ``dict`` or :class:`~bson.son.SON` instance
            specifying elements which must be present for a document
            to be updated
          - `document`: a ``dict`` or :class:`~bson.son.SON`
            instance specifying the document to be used for the update
            or (in the case of an upsert) insert - see docs on MongoDB
            `update modifiers`_
          - `upsert` (optional): perform an upsert if ``True``
          - `manipulate` (optional): manipulate the document before
            updating? If ``True`` all instances of
            :mod:`~pymongo.son_manipulator.SONManipulator` added to
            this :class:`~pymongo.database.Database` will be applied
            to the document before performing the update.
          - `safe` (optional): check that the update succeeded?
          - `multi` (optional): update all documents that match
            `spec`, rather than just the first matching document. The
            default value for `multi` is currently ``False``, but this
            might eventually change to ``True``. It is recommended
            that you specify this argument explicitly for all update
            operations in order to prepare your code for that change.
          - `**kwargs` (optional): any additional arguments imply
            ``safe=True``, and will be used as options for the
            `getLastError` command
        
        .. _update modifiers: http://www.mongodb.org/display/DOCS/Updating
        
        .. mongodoc:: update
        """
        if not isinstance(spec, dict):
            raise TypeError("spec must be an instance of dict")
        if not isinstance(document, dict):
            raise TypeError("document must be an instance of dict")
        if not isinstance(upsert, bool):
            raise TypeError("upsert must be an instance of bool")
        if not isinstance(safe, bool):
            raise TypeError("safe must be an instance of bool")
        # TODO: apply SON manipulators
        # if upsert and manipulate:
        #     document = self.__database._fix_incoming(document, self)
        
        if kwargs:
            safe = True
        
        if safe and not callable(callback):
            raise TypeError("callback must be callable")
        if not safe and callback is not None:
            raise TypeError("callback can not be used with safe=False")
        
        if callback:
            callback = functools.partial(self._handle_response, orig_callback=callback)

        self.__limit = None
        connection = self.__pool.connection()
        try:
            connection.send_message(
                message.update(self.full_collection_name, upsert, multi,
                    spec, document, safe, kwargs), callback=callback)
        except:
            connection.close()
            raise

    
    def find_one(self, spec_or_id, **kwargs):
        """Get a single document from the database.
        
        All arguments to :meth:`find` are also valid arguments for
        :meth:`find_one`, although any `limit` argument will be
        ignored. Returns a single document, or ``None`` if no matching
        document is found.
        """
        if spec_or_id is not None and not isinstance(spec_or_id, dict):
            spec_or_id = {"_id": spec_or_id}
        kwargs['limit'] = -1
        self.find(spec_or_id, **kwargs)
    
    def find(self, spec=None, fields=None, skip=0, limit=0,
                 timeout=True, snapshot=False, tailable=False, sort=None,
                 max_scan=None, slave_okay=False,
                 _must_use_master=False, _is_command=False, hint=None, debug=False,
                 comment=None, callback=None):
        """Query the database.
        
        The `spec` argument is a prototype document that all results
        must match. For example:
        
        >>> db.test.find({"hello": "world"}, callback=...)
        
        only matches documents that have a key "hello" with value
        "world".  Matches can have other keys *in addition* to
        "hello". The `fields` argument is used to specify a subset of
        fields that should be included in the result documents. By
        limiting results to a certain subset of fields you can cut
        down on network traffic and decoding time.
        
        Raises :class:`TypeError` if any of the arguments are of
        improper type.
        
        :Parameters:
          - `spec` (optional): a SON object specifying elements which
            must be present for a document to be included in the
            result set
          - `fields` (optional): a list of field names that should be
            returned in the result set ("_id" will always be
            included), or a dict specifying the fields to return
          - `skip` (optional): the number of documents to omit (from
            the start of the result set) when returning the results
          - `limit` (optional): the maximum number of results to
            return
          - `timeout` (optional): if True, any returned cursor will be
            subject to the normal timeout behavior of the mongod
            process. Otherwise, the returned cursor will never timeout
            at the server. Care should be taken to ensure that cursors
            with timeout turned off are properly closed.
          - `snapshot` (optional): if True, snapshot mode will be used
            for this query. Snapshot mode assures no duplicates are
            returned, or objects missed, which were present at both
            the start and end of the query's execution. For details,
            see the `snapshot documentation
            <http://dochub.mongodb.org/core/snapshot>`_.
          - `tailable` (optional): the result of this find call will
            be a tailable cursor - tailable cursors aren't closed when
            the last data is retrieved but are kept open and the
            cursors location marks the final document's position. if
            more data is received iteration of the cursor will
            continue from the last document received. For details, see
            the `tailable cursor documentation
            <http://www.mongodb.org/display/DOCS/Tailable+Cursors>`_.
          - `sort` (optional): a list of (key, direction) pairs
            specifying the sort order for this query. See
            :meth:`~pymongo.cursor.Cursor.sort` for details.
          - `max_scan` (optional): limit the number of documents
            examined when performing the query
          - `slave_okay` (optional): is it okay to connect directly
            to and perform queries on a slave instance
        
        .. mongodoc:: find
        """
        
        if spec is None:
            spec = {}
        
        if limit is None:
            limit = 0

        if not isinstance(spec, dict):
            raise TypeError("spec must be an instance of dict")
        if not isinstance(skip, int):
            raise TypeError("skip must be an instance of int")
        if not isinstance(limit, int):
            raise TypeError("limit must be an instance of int or None")
        if not isinstance(timeout, bool):
            raise TypeError("timeout must be an instance of bool")
        if not isinstance(snapshot, bool):
            raise TypeError("snapshot must be an instance of bool")
        if not isinstance(tailable, bool):
            raise TypeError("tailable must be an instance of bool")
        if not callable(callback):
            raise TypeError("callback must be callable")
        
        if fields is not None:
            if not fields:
                fields = {"_id": 1}
            if not isinstance(fields, dict):
                fields = helpers._fields_list_to_dict(fields)
        
        self.__spec = spec
        self.__fields = fields
        self.__skip = skip
        self.__limit = limit
        self.__batch_size = 0
        
        self.__timeout = timeout
        self.__tailable = tailable
        self.__snapshot = snapshot
        self.__ordering = sort and helpers._index_document(sort) or None
        self.__max_scan = max_scan
        self.__slave_okay = slave_okay
        self.__explain = False
        self.__hint = hint
        self.__comment = comment
        self.__debug = debug
        # self.__as_class = as_class
        self.__tz_aware = False #collection.database.connection.tz_aware
        self.__must_use_master = _must_use_master
        self.__is_command = _is_command
        
        connection = self.__pool.connection()
        try:
            if self.__debug:
                logging.debug('QUERY_SPEC: %r' % self.__query_spec())

            connection.send_message(
                message.query(self.__query_options(),
                              self.full_collection_name,
                              self.__skip, 
                              self.__limit,
                              self.__query_spec(),
                              self.__fields), 
                callback=functools.partial(self._handle_response, orig_callback=callback))
        except Exception, e:
            logging.debug('Error sending query %s' % e)
            connection.close()
            raise
    
    def _handle_response(self, result, error=None, orig_callback=None):
        if result and result.get('cursor_id'):
            connection = self.__pool.connection()
            try:
                connection.send_message(
                    message.kill_cursors([result['cursor_id']]),
                    callback=None)
            except Exception, e:
                logging.debug('Error killing cursor %s: %s' % (result['cursor_id'], e))
                connection.close()
                raise
        
        if error:
            logging.debug('%s %s' % (self.full_collection_name , error))
            orig_callback(None, error=error)
        else:
            if self.__limit == -1 and len(result['data']) == 1:
                # handle the find_one() call
                orig_callback(result['data'][0], error=None)
            else:
                orig_callback(result['data'], error=None)

    
    def __query_options(self):
        """Get the query options string to use for this query."""
        options = 0
        if self.__tailable:
            options |= _QUERY_OPTIONS["tailable_cursor"]
        if self.__slave_okay or self.__pool._slave_okay:
            options |= _QUERY_OPTIONS["slave_okay"]
        if not self.__timeout:
            options |= _QUERY_OPTIONS["no_timeout"]
        return options
    
    def __query_spec(self):
        """Get the spec to use for a query."""
        spec = self.__spec
        if not self.__is_command and "$query" not in self.__spec:
            spec = SON({"$query": self.__spec})
        if self.__ordering:
            spec["$orderby"] = self.__ordering
        if self.__explain:
            spec["$explain"] = True
        if self.__hint:
            spec["$hint"] = self.__hint
        if self.__comment:
            spec["$comment"] = self.__comment
        if self.__snapshot:
            spec["$snapshot"] = True
        if self.__max_scan:
            spec["$maxScan"] = self.__max_scan
        return spec
    
    

########NEW FILE########
__FILENAME__ = errors
#!/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# StandardError
#       |__Error
#          |__InterfaceError
#          |__DatabaseError
#             |__DataError
#             |__IntegrityError
#             |__ProgrammingError
#             |__NotSupportedError

class Error(StandardError):
    pass

class InterfaceError(Error):
    pass

class RSConnectionError(InterfaceError):
    pass

class DatabaseError(Error):
    pass

class DataError(DatabaseError):
    pass

class IntegrityError(DatabaseError):
    def __init__(self, msg, code=None):
        self.code = code
        self.msg = msg
    
    def __unicode__(self):
        return u'IntegrityError: %s code:%s' % (self.msg, self.code or '')
    
    def __str__(self):
        return str(self.__unicode__())

class ProgrammingError(DatabaseError):
    pass

class NotSupportedError(DatabaseError):
    pass

class TooManyConnections(Error):
    pass

class AuthenticationError(Error):
    pass

########NEW FILE########
__FILENAME__ = helpers
import hashlib

import bson
from bson.son import SON
import struct
from asyncmongo import ASCENDING, DESCENDING, GEO2D
from asyncmongo.errors import (DatabaseError, InterfaceError)


def _parse_host(h):
    try:
        host, port = h.split(":", 1)
        port = int(port)
    except ValueError:
        raise ValueError("Wrong host:port value: %s" % h)

    return host, port

def _unpack_response(response, cursor_id=None, as_class=dict, tz_aware=False):
    """Unpack a response from the database.

    Check the response for errors and unpack, returning a dictionary
    containing the response data.

    :Parameters:
      - `response`: byte string as returned from the database
      - `cursor_id` (optional): cursor_id we sent to get this response -
        used for raising an informative exception when we get cursor id not
        valid at server response
      - `as_class` (optional): class to use for resulting documents
    """
    response_flag = struct.unpack("<i", response[:4])[0]
    if response_flag & 1:
        # Shouldn't get this response if we aren't doing a getMore
        assert cursor_id is not None

        raise InterfaceError("cursor id '%s' not valid at server" %
                               cursor_id)
    elif response_flag & 2:
        error_object = bson.BSON(response[20:]).decode()
        if error_object["$err"] == "not master":
            raise DatabaseError("master has changed")
        raise DatabaseError("database error: %s" %
                               error_object["$err"])

    result = {}
    result["cursor_id"] = struct.unpack("<q", response[4:12])[0]
    result["starting_from"] = struct.unpack("<i", response[12:16])[0]
    result["number_returned"] = struct.unpack("<i", response[16:20])[0]
    result["data"] = bson.decode_all(response[20:], as_class, tz_aware)
    assert len(result["data"]) == result["number_returned"]
    return result

def _fields_list_to_dict(fields):
    """Takes a list of field names and returns a matching dictionary.

    ["a", "b"] becomes {"a": 1, "b": 1}

    and

    ["a.b.c", "d", "a.c"] becomes {"a.b.c": 1, "d": 1, "a.c": 1}
    """
    for key in fields:
        assert isinstance(key, (str,unicode))
    return dict([[key, 1] for key in fields])

def _index_document(index_list):
    """Helper to generate an index specifying document.

    Takes a list of (key, direction) pairs.
    """
    if isinstance(index_list, dict):
        raise TypeError("passing a dict to sort/create_index/hint is not "
                        "allowed - use a list of tuples instead. did you "
                        "mean %r?" % list(index_list.iteritems()))
    elif not isinstance(index_list, list):
        raise TypeError("must use a list of (key, direction) pairs, "
                        "not: " + repr(index_list))
    if not len(index_list):
        raise ValueError("key_or_list must not be the empty list")

    index = SON()
    for (key, value) in index_list:
        if not isinstance(key, basestring):
            raise TypeError("first item in each key pair must be a string")
        if value not in [ASCENDING, DESCENDING, GEO2D]:
            raise TypeError("second item in each key pair must be ASCENDING, "
                            "DESCENDING, or GEO2D")
        index[key] = value
    return index

def _password_digest(username, password):
    """Get a password digest to use for authentication.
    """
    if not isinstance(password, basestring):
        raise TypeError("password must be an instance of basestring")
    if not isinstance(username, basestring):
        raise TypeError("username must be an instance of basestring")

    md5hash = hashlib.md5()
    md5hash.update("%s:mongo:%s" % (username.encode('utf-8'),
                                    password.encode('utf-8')))
    return unicode(md5hash.hexdigest())

def _auth_key(nonce, username, password):
    """Get an auth key to use for authentication.
    """
    digest = _password_digest(username, password)
    md5hash = hashlib.md5()
    md5hash.update("%s%s%s" % (nonce, unicode(username), digest))
    return unicode(md5hash.hexdigest())

########NEW FILE########
__FILENAME__ = message
# Copyright 2009-2010 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for creating `messages
<http://www.mongodb.org/display/DOCS/Mongo+Wire+Protocol>`_ to be sent to
MongoDB.

.. note:: This module is for internal use and is generally not needed by
   application developers.
"""

import random
import struct

import bson
from bson.son import SON
try:
    from pymongo import _cbson
    _use_c = True
except ImportError:
    _use_c = False
from pymongo.errors import InvalidOperation


__ZERO = "\x00\x00\x00\x00"


def __last_error(args):
    """Data to send to do a lastError.
    """
    cmd = SON([("getlasterror", 1)])
    cmd.update(args)
    return query(0, "admin.$cmd", 0, -1, cmd)


def __pack_message(operation, data):
    """Takes message data and adds a message header based on the operation.

    Returns the resultant message string.
    """
    request_id = random.randint(-2 ** 31 - 1, 2 ** 31)
    message = struct.pack("<i", 16 + len(data))
    message += struct.pack("<i", request_id)
    message += __ZERO  # responseTo
    message += struct.pack("<i", operation)
    return (request_id, message + data)


def insert(collection_name, docs, check_keys, safe, last_error_args):
    """Get an **insert** message.
    """
    data = __ZERO
    data += bson._make_c_string(collection_name)
    bson_data = "".join([bson.BSON.encode(doc, check_keys) for doc in docs])
    if not bson_data:
        raise InvalidOperation("cannot do an empty bulk insert")
    data += bson_data
    if safe:
        (_, insert_message) = __pack_message(2002, data)
        (request_id, error_message) = __last_error(last_error_args)
        return (request_id, insert_message + error_message)
    else:
        return __pack_message(2002, data)
if _use_c:
    insert = _cbson._insert_message


def update(collection_name, upsert, multi, spec, doc, safe, last_error_args):
    """Get an **update** message.
    """
    options = 0
    if upsert:
        options += 1
    if multi:
        options += 2

    data = __ZERO
    data += bson._make_c_string(collection_name)
    data += struct.pack("<i", options)
    data += bson.BSON.encode(spec)
    data += bson.BSON.encode(doc)
    if safe:
        (_, update_message) = __pack_message(2001, data)
        (request_id, error_message) = __last_error(last_error_args)
        return (request_id, update_message + error_message)
    else:
        return __pack_message(2001, data)
if _use_c:
    update = _cbson._update_message


def query(options, collection_name,
          num_to_skip, num_to_return, query, field_selector=None):
    """Get a **query** message.
    """
    data = struct.pack("<I", options)
    data += bson._make_c_string(collection_name)
    data += struct.pack("<i", num_to_skip)
    data += struct.pack("<i", num_to_return)
    data += bson.BSON.encode(query)
    if field_selector is not None:
        data += bson.BSON.encode(field_selector)
    return __pack_message(2004, data)
if _use_c:
    query = _cbson._query_message


def get_more(collection_name, num_to_return, cursor_id):
    """Get a **getMore** message.
    """
    data = __ZERO
    data += bson._make_c_string(collection_name)
    data += struct.pack("<i", num_to_return)
    data += struct.pack("<q", cursor_id)
    return __pack_message(2005, data)
if _use_c:
    get_more = _cbson._get_more_message


def delete(collection_name, spec, safe, last_error_args):
    """Get a **delete** message.
    """
    data = __ZERO
    data += bson._make_c_string(collection_name)
    data += __ZERO
    data += bson.BSON.encode(spec)
    if safe:
        (_, remove_message) = __pack_message(2006, data)
        (request_id, error_message) = __last_error(last_error_args)
        return (request_id, remove_message + error_message)
    else:
        return __pack_message(2006, data)


def kill_cursors(cursor_ids):
    """Get a **killCursors** message.
    """
    data = __ZERO
    data += struct.pack("<i", len(cursor_ids))
    for cursor_id in cursor_ids:
        data += struct.pack("<q", cursor_id)
    return __pack_message(2007, data)

########NEW FILE########
__FILENAME__ = pool
#!/bin/env python
# 
# Copyright 2010 bit.ly
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from threading import Condition
import logging
from errors import TooManyConnections, ProgrammingError
from connection import Connection


class ConnectionPools(object):
    """ singleton to keep track of named connection pools """
    @classmethod
    def get_connection_pool(self, pool_id, *args, **kwargs):
        """get a connection pool, transparently creating it if it doesn't already exist

        :Parameters:
            - `pool_id`: unique id for a connection pool
        """
        assert isinstance(pool_id, (str, unicode))
        if not hasattr(self, '_pools'):
            self._pools = {}
        if pool_id not in self._pools:
            self._pools[pool_id] = ConnectionPool(*args, **kwargs)
        # logging.debug("%s: _connections = %d", pool_id, self._pools[pool_id]._connections)
        return self._pools[pool_id]
    
    @classmethod
    def close_idle_connections(self, pool_id=None):
        """close idle connections to mongo"""
        if not hasattr(self, '_pools'):
            return

        if pool_id:
            if pool_id not in self._pools:
                raise ProgrammingError("pool %r does not exist" % pool_id)
            else:
                pool = self._pools[pool_id]
                pool.close()
        else:
            for pool_id, pool in self._pools.items():
                pool.close()

class ConnectionPool(object):
    """Connection Pool to a single mongo instance.
    
    :Parameters:
      - `mincached` (optional): minimum connections to open on instantiation. 0 to open connections on first use
      - `maxcached` (optional): maximum inactive cached connections for this pool. 0 for unlimited
      - `maxconnections` (optional): maximum open connections for this pool. 0 for unlimited
      - `maxusage` (optional): number of requests allowed on a connection before it is closed. 0 for unlimited
      - `dbname`: mongo database name
      - `slave_okay` (optional): is it okay to connect directly to and perform queries on a slave instance
      - `**kwargs`: passed to `connection.Connection`
    
    """
    def __init__(self, 
                mincached=0, 
                maxcached=0, 
                maxconnections=0, 
                maxusage=0, 
                dbname=None, 
                slave_okay=False, 
                *args, **kwargs):
        assert isinstance(mincached, int)
        assert isinstance(maxcached, int)
        assert isinstance(maxconnections, int)
        assert isinstance(maxusage, int)
        assert isinstance(dbname, (str, unicode, None.__class__))
        assert isinstance(slave_okay, bool)
        if mincached and maxcached:
            assert mincached <= maxcached
        if maxconnections:
            assert maxconnections >= maxcached
            assert maxconnections >= mincached
        self._args, self._kwargs = args, kwargs
        self._maxusage = maxusage
        self._mincached = mincached
        self._maxcached = maxcached
        self._maxconnections = maxconnections
        self._idle_cache = [] # the actual connections that can be used
        self._condition = Condition()
        self._dbname = dbname
        self._slave_okay = slave_okay
        self._connections = 0

        
        # Establish an initial number of idle database connections:
        idle = [self.connection() for i in range(mincached)]
        while idle:
            self.cache(idle.pop())
    
    def new_connection(self):
        kwargs = self._kwargs
        kwargs['pool'] = self
        return Connection(*self._args, **kwargs)
    
    def connection(self):
        """ get a cached connection from the pool """
        
        self._condition.acquire()
        try:
            if (self._maxconnections and self._connections >= self._maxconnections):
                raise TooManyConnections("%d connections are already equal to the max: %d" % (self._connections, self._maxconnections))
            # connection limit not reached, get a dedicated connection
            try: # first try to get it from the idle cache
                con = self._idle_cache.pop(0)
            except IndexError: # else get a fresh connection
                con = self.new_connection()
            self._connections += 1
        finally:
            self._condition.release()
        return con

    def cache(self, con):
        """Put a dedicated connection back into the idle cache."""
        if self._maxusage and con.usage_count > self._maxusage:
            self._connections -=1
            logging.debug('dropping connection %s uses past max usage %s' % (con.usage_count, self._maxusage))
            con._close()
            return
        self._condition.acquire()
        if con in self._idle_cache:
            # called via socket close on a connection in the idle cache
            self._condition.release()
            return
        try:
            if not self._maxcached or len(self._idle_cache) < self._maxcached:
                # the idle cache is not full, so put it there
                self._idle_cache.append(con)
            else: # if the idle cache is already full,
                logging.debug('dropping connection. connection pool (%s) is full. maxcached %s' % (len(self._idle_cache), self._maxcached))
                con._close() # then close the connection
            self._condition.notify()
        finally:
            self._connections -= 1
            self._condition.release()
    
    def close(self):
        """Close all connections in the pool."""
        self._condition.acquire()
        try:
            while self._idle_cache: # close all idle connections
                con = self._idle_cache.pop(0)
                try:
                    con._close()
                except Exception:
                    pass
                self._connections -=1
            self._condition.notifyAll()
        finally:
            self._condition.release()
    


########NEW FILE########
__FILENAME__ = sample_app
#!/usr/bin/env python

import os
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.options
import logging
import simplejson as json
import asyncmongo
import pymongo.json_util
import base64
import settings


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        if not hasattr(self, "_db"):
            self._db = asyncmongo.Client(pool_id='test_pool', **settings.get('mongo_database'))
        return self._db
    
    def api_response(self, data):
        """return an api response in the proper output format with status_code == 200"""
        self.set_header("Content-Type", "application/javascript; charset=UTF-8")
        data = json.dumps(data, default=pymongo.json_util.default)
        self.finish(data)


class Put(BaseHandler):
    @tornado.web.asynchronous
    def get(self):
        rand = base64.b64encode(os.urandom(32))
        try:
            self.db.test.insert({ 'blah': rand }, callback=self.async_callback(self.finish_save))
        except Exception, e:
            logging.error(e)
            return self.api_response({'status':'ERROR', 'status_string': '%s' % e})
    
    def finish_save(self, response, error):
        if error or response[0].get('ok') != 1:
            logging.error(error)
            raise tornado.web.HTTPError(500, 'QUERY_ERROR')
        
        self.api_response({'status':'OK', 'status_string': 'record(%s) saved' % response})


class Application(tornado.web.Application):
    def __init__(self):
        debug = tornado.options.options.environment == "dev"
        app_settings = { 'debug':debug }
        
        handlers = [
            (r"/put", Put)
        ]
        
        tornado.web.Application.__init__(self, handlers, **app_settings)


if __name__ == "__main__":
    tornado.options.define("port", type=int, default=5150, help="Listen port")
    tornado.options.parse_command_line()
    
    logging.info("starting webserver on 0.0.0.0:%d" % tornado.options.options.port)
    http_server = tornado.httpserver.HTTPServer(request_callback=Application())
    http_server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = sample_app2
#!/usr/bin/env python

#   mkdir /tmp/asyncmongo_sample_app2
#   mongod --port 27017 --oplogSize 10 --dbpath /tmp/asyncmongo_sample_app2

#   $mongo
#   >>>use test;
#   db.addUser("testuser", "testpass");

#   ab  -n 1000 -c 16 http://127.0.0.1:8888/ 

import sys
import logging
import os
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if app_dir not in sys.path:
    logging.debug('adding %r to sys.path' % app_dir)
    sys.path.insert(0, app_dir)

import asyncmongo
# make sure we get the local asyncmongo
assert asyncmongo.__file__.startswith(app_dir)

import tornado.ioloop
import tornado.web
import tornado.options

class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        db.users.find_one({"user_id" : 1}, callback=self._on_response)

    def _on_response(self, response, error):
        assert not error
        self.write(str(response))
        self.finish()
        

if __name__ == "__main__":
    tornado.options.parse_command_line()
    application = tornado.web.Application([
            (r"/?", MainHandler)
            ])
    application.listen(8888)
    db = asyncmongo.Client(pool_id="test",
                           host='127.0.0.1',
                           port=27017,
                           mincached=5,
                           maxcached=15,
                           maxconnections=30,
                           dbname='test', 
                           dbuser='testuser',
                           dbpass='testpass')
    tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = settings
import tornado.options
import random
tornado.options.define("environment", default="dev", help="environment")

def randomize(values):
    """ this is a wrapper that returns a function which when called returns a random value"""
    def picker():
        return random.choice(values)
    return picker

options = {
    'dev' : {
        'mongo_database' : {'host' : '127.0.0.1', 'port' : 27017, 'dbname' : 'testdb', 'maxconnections':5}
    }
}

default = {}

def get(key):
    env = tornado.options.options.environment
    if env not in options:
        raise Exception("Invalid Environment (%s)" % env)
    v = options.get(env).get(key) or default.get(key)
    if callable(v):
        return v()
    return v

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

import os
import base64
import pygtk
pygtk.require('2.0')
import gtk
import asyncmongo

database= {'host' : '127.0.0.1', 'port' : 27018, 'dbname' : 'testdb', 'maxconnections':5}

class TestApp(object):
    def __init__(self):
        self.__win = gtk.Window()
        self.__win.set_title("AsyncMongo test")
        box = gtk.VBox()
        self.__win.add(box)
        
        self.message = gtk.Label('')
        box.pack_start(self.message)

        btn = gtk.Button(label="Test Insert")
        box.pack_start(btn)
        btn.connect('clicked', self._on_insert_clicked)
        
        btn = gtk.Button(label="Test Query")
        box.pack_start(btn)
        btn.connect('clicked', self._on_query_clicked)
        
        self._db = asyncmongo.Client(pool_id='test_pool', backend="glib2", **database)
    
    def _on_query_clicked(self, obj):
        self._db.test.find({}, callback=self._on_query_response)

    def _on_query_response(self, data, error):
        if error:
            self.message.set_text(error)
        
        self.message.set_text('Query OK, %d objects found' % len(data))
            
    def _on_insert_clicked(self, obj):
        rand = base64.b64encode(os.urandom(32))
        try:
            self._db.test.insert({ 'blah': rand }, callback=self._on_insertion)
        except Exception, e:
            print e
            
    def _on_insertion(self, data, error):
        if error:
            self.message.set_text(error)
        
        self.message.set_text("Insert OK")
        
    def show(self):
        self.__win.show_all()

if __name__ == "__main__":
    app = TestApp()
    app.show()
    gtk.main()

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

import os
import base64
import asyncmongo
from gi.repository import Gtk

database= {'host' : '127.0.0.1', 'port' : 27018, 'dbname' : 'testdb', 'maxconnections':5}

class TestApp(object):
    def __init__(self):
        self.__win = Gtk.Window()
        self.__win.set_title("AsyncMongo test")
        box = Gtk.VBox()
        self.__win.add(box)
        
        self.message = Gtk.Label('')
        box.pack_start(self.message, 0, 1, 1)

        btn = Gtk.Button(label="Test Insert")
        box.pack_start(btn, 0, 1, 1)
        btn.connect('clicked', self._on_insert_clicked)
        
        btn = Gtk.Button(label="Test Query")
        box.pack_start(btn, 0, 1, 1)
        btn.connect('clicked', self._on_query_clicked)
        
        self._db = asyncmongo.Client(pool_id='test_pool', backend="glib3", **database)
    
    def _on_query_clicked(self, obj):
        self._db.test.find({}, callback=self._on_query_response)

    def _on_query_response(self, data, error):
        if error:
            self.message.set_text(error)
        
        self.message.set_text('Query OK, %d objects found' % len(data))
            
    def _on_insert_clicked(self, obj):
        rand = base64.b64encode(os.urandom(32))
        try:
            self._db.test.insert({ 'blah': rand }, callback=self._on_insertion)
        except Exception, e:
            print e
            
    def _on_insertion(self, data, error):
        if error:
            self.message.set_text(error)
        
        self.message.set_text("Insert OK")
        
    def show(self):
        self.__win.show_all()

if __name__ == "__main__":
    app = TestApp()
    app.show()
    Gtk.main()

########NEW FILE########
__FILENAME__ = test_authentication
import tornado.ioloop
import time
import logging
import subprocess

import test_shunt
import asyncmongo

TEST_TIMESTAMP = int(time.time())

class AuthenticationTest(test_shunt.MongoTest):
    def setUp(self):
        super(AuthenticationTest, self).setUp()
        logging.info('creating user')
        pipe = subprocess.Popen('''echo -e 'use test;\n db.addUser("testuser", "testpass");\n exit;' | mongo --port 27018 --host 127.0.0.1''', shell=True)
        pipe.wait()
        
    def test_authentication(self):
        try:
            test_shunt.setup()
            db = asyncmongo.Client(pool_id='testauth', host='127.0.0.1', port=27018, dbname='test', dbuser='testuser',
                                   dbpass='testpass', maxconnections=2)
        
            def update_callback(response, error):
                logging.info("UPDATE:")
                tornado.ioloop.IOLoop.instance().stop()
                logging.info(response)
                assert len(response) == 1
                test_shunt.register_called('update')

            db.test_stats.update({"_id" : TEST_TIMESTAMP}, {'$inc' : {'test_count' : 1}}, upsert=True,
                                 callback=update_callback)

            tornado.ioloop.IOLoop.instance().start()
            test_shunt.assert_called('update')

            def query_callback(response, error):
                tornado.ioloop.IOLoop.instance().stop()
                logging.info(response)
                logging.info(error)
                assert error is None
                assert isinstance(response, dict)
                assert response['_id'] == TEST_TIMESTAMP
                assert response['test_count'] == 1
                test_shunt.register_called('retrieved')

            db.test_stats.find_one({"_id" : TEST_TIMESTAMP}, callback=query_callback)
            tornado.ioloop.IOLoop.instance().start()
            test_shunt.assert_called('retrieved')
        except:
            tornado.ioloop.IOLoop.instance().stop()
            raise

    def test_failed_auth(self):
        try:
            test_shunt.setup()
            db = asyncmongo.Client(pool_id='testauth_f', host='127.0.0.1', port=27018, dbname='test', dbuser='testuser',
                                   dbpass='wrong', maxconnections=2)

            def query_callback(response, error):
                tornado.ioloop.IOLoop.instance().stop()
                logging.info(response)
                logging.info(error)
                assert isinstance(error, asyncmongo.AuthenticationError)
                assert response is None
                test_shunt.register_called('auth_failed')

            db.test_stats.find_one({"_id" : TEST_TIMESTAMP}, callback=query_callback)
            tornado.ioloop.IOLoop.instance().start()
            test_shunt.assert_called('auth_failed')
        except:
            tornado.ioloop.IOLoop.instance().stop()
            raise

########NEW FILE########
__FILENAME__ = test_command
import tornado.ioloop

import test_shunt
import asyncmongo


class CommandTest(
    test_shunt.MongoTest,
    test_shunt.SynchronousMongoTest,
):
    mongod_options = [('--port', '27018')]

    def setUp(self):
        super(CommandTest, self).setUp()
        self.pymongo_conn.test.foo.insert({'_id': 1})

    def test_find_and_modify(self):
        db = asyncmongo.Client(pool_id='test_query', host='127.0.0.1', port=int(self.mongod_options[0][1]), dbname='test', mincached=3)

        results = []

        def callback(response, error):
            tornado.ioloop.IOLoop.instance().stop()
            self.assert_(error is None)
            results.append(response['value'])

        before = self.get_open_cursors()

        # First findAndModify creates doc with i: 2 and s: 'a'
        db.command('findAndModify', 'foo',
            callback=callback,
            query={'_id': 2},
            update={'$set': {'s': 'a'}},
            upsert=True,
            new=True,
        )

        tornado.ioloop.IOLoop.instance().start()
        self.assertEqual(
            {'_id': 2, 's': 'a'},
            results[0]
        )

        # Second findAndModify updates doc with i: 2, sets s to 'b'
        db.command('findAndModify', 'foo',
            callback=callback,
            query={'_id': 2},
            update={'$set': {'s': 'b'}},
            upsert=True,
            new=True,
        )

        tornado.ioloop.IOLoop.instance().start()
        self.assertEqual(
            {'_id': 2, 's': 'b'},
            results[1]
        )

        # check cursors
        after = self.get_open_cursors()
        assert before == after, "%d cursors left open (should be 0)" % (after - before)

if __name__ == '__main__':
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_connection
import tornado.ioloop
import logging
import time

import test_shunt
import asyncmongo
from asyncmongo.errors import DataError

TEST_TIMESTAMP = int(time.time())

class ConnectionTest(test_shunt.MongoTest):
    def test_getitem(self):
        db = asyncmongo.Client(pool_id='test_query', host='127.0.0.1', port=27018, dbname='test', mincached=3)
        self.assert_(
            repr(db['foo']) == repr(db.foo),
            "dict-style access of a collection should be same as property access"
        )

    def test_connection(self):
        db = asyncmongo.Client(pool_id='test_query', host='127.0.0.1', port=27018, dbname='test', mincached=3)
        for connection_name in [
            '.',
            '..',
            '.foo',
            'foo.',
            '.foo.',
            'foo\x00'
            '\x00foo'
        ]:
            self.assertRaises(
                DataError,
                lambda: db.connection(connection_name)
            )

    def test_query(self):
        logging.info('in test_query')
        test_shunt.setup()
        db = asyncmongo.Client(pool_id='test_query', host='127.0.0.1', port=27018, dbname='test', mincached=3)
        
        def insert_callback(response, error):
            tornado.ioloop.IOLoop.instance().stop()
            logging.info(response)
            assert len(response) == 1
            test_shunt.register_called('inserted')

        db.test_users.insert({"_id" : "test_connection.%d" % TEST_TIMESTAMP}, safe=True, callback=insert_callback)
        
        tornado.ioloop.IOLoop.instance().start()
        test_shunt.assert_called('inserted')
        
        def callback(response, error):
            tornado.ioloop.IOLoop.instance().stop()
            assert len(response) == 1
            test_shunt.register_called('got_record')

        db.test_users.find({}, limit=1, callback=callback)
        
        tornado.ioloop.IOLoop.instance().start()
        test_shunt.assert_called("got_record")

########NEW FILE########
__FILENAME__ = test_duplicate_insert
import tornado.ioloop
import time
import logging

import test_shunt
import asyncmongo

TEST_TIMESTAMP = int(time.time())

class DuplicateInsertTest(test_shunt.MongoTest):
    def test_duplicate_insert(self):
        test_shunt.setup()
        db = asyncmongo.Client(pool_id='dup_insert', host='127.0.0.1', port=27018, dbname='test')
        
        def insert_callback(response, error):
            tornado.ioloop.IOLoop.instance().stop()
            logging.info(response)
            assert len(response) == 1
            test_shunt.register_called('inserted')

        db.test_users.insert({"_id" : "duplicate_insert.%d" % TEST_TIMESTAMP}, callback=insert_callback)
        
        tornado.ioloop.IOLoop.instance().start()
        test_shunt.assert_called('inserted')
        
        def duplicate_callback(response, error):
            tornado.ioloop.IOLoop.instance().stop()
            logging.info(response)
            if error:
                test_shunt.register_called('dupe')

        db.test_users.insert({"_id" : "duplicate_insert.%d" % TEST_TIMESTAMP}, callback=duplicate_callback)
        
        tornado.ioloop.IOLoop.instance().start()
        test_shunt.assert_called('dupe')


########NEW FILE########
__FILENAME__ = test_insert_delete
import tornado.ioloop
import time
import logging

import test_shunt
import asyncmongo

TEST_TIMESTAMP = int(time.time())

class InsertDeleteTest(test_shunt.MongoTest):
    def test_insert(self):
        test_shunt.setup()
        db = asyncmongo.Client(pool_id='testinsert', host='127.0.0.1', port=27018, dbname='test')
        
        def insert_callback(response, error):
            tornado.ioloop.IOLoop.instance().stop()
            logging.info(response)
            assert len(response) == 1
            test_shunt.register_called('inserted')

        db.test_users.insert({"_id" : "insert.%d" % TEST_TIMESTAMP}, callback=insert_callback)
        
        tornado.ioloop.IOLoop.instance().start()
        test_shunt.assert_called('inserted')
        
        def query_callback(response, error):
            tornado.ioloop.IOLoop.instance().stop()
            logging.info(response)
            assert len(response) == 1
            test_shunt.register_called('retrieved')

        db.test_users.find_one({"_id" : "insert.%d" % TEST_TIMESTAMP}, callback=query_callback)
        tornado.ioloop.IOLoop.instance().start()
        test_shunt.assert_called('retrieved')

        
        def delete_callback(response, error):
            tornado.ioloop.IOLoop.instance().stop()
            logging.info(response)
            assert len(response) == 1
            test_shunt.register_called('deleted')

        db.test_users.remove({"_id" : "insert.%d" % TEST_TIMESTAMP}, callback=delete_callback)
        tornado.ioloop.IOLoop.instance().start()
        test_shunt.assert_called('deleted')


########NEW FILE########
__FILENAME__ = test_pooled_db
import tornado.ioloop
import logging
import time
from asyncmongo.errors import TooManyConnections

import test_shunt
import asyncmongo
TEST_TIMESTAMP = int(time.time())

class PooledDBTest(test_shunt.MongoTest):
    def test_pooled_db(self):
        """
        This tests simply verifies that we can grab two different connections from the pool
        and use them independantly.
        """
        print asyncmongo.__file__
        test_shunt.setup()
        client = asyncmongo.Client('id1', maxconnections=5, host='127.0.0.1', port=27018, dbname='test')
        test_users_collection = client.connection('test_users')
        
        def insert_callback(response, error):
            tornado.ioloop.IOLoop.instance().stop()
            logging.info(response)
            assert len(response) == 1
            test_shunt.register_called('inserted')

        test_users_collection.insert({"_id" : "record_test.%d" % TEST_TIMESTAMP}, safe=True, callback=insert_callback)
        
        tornado.ioloop.IOLoop.instance().start()
        test_shunt.assert_called('inserted')
        
        def pool_callback(response, error):
            if test_shunt.is_called('pool2'):
                tornado.ioloop.IOLoop.instance().stop()
            assert len(response) == 1
            test_shunt.register_called('pool1')

        def pool_callback2(response, error):
            if test_shunt.is_called('pool1'):
                # don't expect 2 finishes second
                tornado.ioloop.IOLoop.instance().stop()
            assert len(response) == 1
            test_shunt.register_called('pool2')

        test_users_collection.find({}, limit=1, callback=pool_callback)
        test_users_collection.find({}, limit=1, callback=pool_callback2)
        
        tornado.ioloop.IOLoop.instance().start()
        test_shunt.assert_called('pool1')
        test_shunt.assert_called('pool2')

    def too_many_connections(self):
        clients = [
            asyncmongo.Client('id2', maxconnections=2, host='127.0.0.1', port=27018, dbname='test')
            for i in range(3)
        ]

        def callback(response, error):
            pass

        for client in clients[:2]:
            client.connection('foo').find({}, callback=callback)

        self.assertRaises(
            TooManyConnections,
            lambda: clients[2].connection('foo').find({}, callback=callback)
        )


########NEW FILE########
__FILENAME__ = test_query
import tornado.ioloop
import logging
import time

import test_shunt
import asyncmongo


class QueryTest(test_shunt.MongoTest, test_shunt.SynchronousMongoTest):
    mongod_options = [('--port', '27018')]

    def setUp(self):
        super(QueryTest, self).setUp()
        self.pymongo_conn.test.foo.insert([{'i': i} for i in xrange(200)])

    def test_query(self):
        db = asyncmongo.Client(pool_id='test_query', host='127.0.0.1', port=int(self.mongod_options[0][1]), dbname='test', mincached=3)

        def noop_callback(response, error):
            logging.info(response)
            loop = tornado.ioloop.IOLoop.instance()
            # delay the stop so kill cursor has time on the ioloop to get pushed through to mongo
            loop.add_timeout(time.time() + .1, loop.stop)

        before = self.get_open_cursors()

        # run 2 queries
        db.foo.find({}, callback=noop_callback)
        tornado.ioloop.IOLoop.instance().start()
        db.foo.find({}, callback=noop_callback)
        tornado.ioloop.IOLoop.instance().start()
        
        # check cursors
        after = self.get_open_cursors()
        assert before == after, "%d cursors left open (should be 0)" % (after - before)

if __name__ == '__main__':
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = test_replica_set
import tornado.ioloop
import time
import logging
import subprocess

import test_shunt
import asyncmongo
import asyncmongo.connection

TEST_TIMESTAMP = int(time.time())

class ReplicaSetTest(test_shunt.MongoTest):
    mongod_options = [
        ('--port', '27018', '--replSet', 'rs0'),
        ('--port', '27019', '--replSet', 'rs0'),
        ('--port', '27020', '--replSet', 'rs0'),
    ]

    def mongo_cmd(self, cmd, port=27018, res='"ok" : 1'):
        logging.info("mongo_cmd: %s", cmd)
        pipe = subprocess.Popen("mongo --port %d" % port, shell=True,
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        reply = pipe.communicate(cmd)[0]
        assert reply.find(res) > 0
        return reply

    def wait_master(self, port):
        while True:
            if self.mongo_cmd("db.isMaster();", port).find('"ismaster" : true') > 0:
                logging.info("%d is a master", port)
                break
            else:
                logging.info("Waiting for %d to become master", port)
                time.sleep(5)

    def wait_secondary(self, port):
        while True:
            if self.mongo_cmd("db.isMaster();", port).find('"secondary" : true') > 0:
                logging.info("%d is a secondary", port)
                break
            else:
                logging.info("Waiting for %d to become secondary", port)
                time.sleep(5)

    def setUp(self):
        super(ReplicaSetTest, self).setUp()
        logging.info("configuring a replica set at 127.0.0.1")
        cfg = """
        {
            "_id" : "rs0",
            "members" : [
                {
                    "_id" : 0,
                    "host" : "127.0.0.1:27018"
                },
                {
                    "_id" : 1,
                    "host" : "127.0.0.1:27019",
                    "priority" : 2
                },
                {
                    "_id" : 2,
                    "host" : "127.0.0.1:27020",
                    "priority" : 0,
                    "hidden": true
                }
            ]
        }
        """
        self.mongo_cmd("rs.initiate(%s);" % cfg, 27019)
        logging.info("waiting for replica set to finish configuring")
        self.wait_master(27019)
        self.wait_secondary(27018)

    def test_connection(self):
        class Pool(object):
            def __init__(self):
                super(Pool, self).__init__()
                self._cache = []

            def cache(self, c):
                self._cache.append(c)

        class AsyncClose(object):
            def process(self, *args, **kwargs):
                tornado.ioloop.IOLoop.instance().stop()

        try:
            for i in xrange(10):
                conn = asyncmongo.connection.Connection(pool=Pool(),
                                                        seed=[('127.0.0.1', 27018), ('127.0.0.1', 27020)],
                                                        rs="rs0")

                conn._put_job(AsyncClose(), 0)
                conn._next_job()
                tornado.ioloop.IOLoop.instance().start()

                assert conn._host == '127.0.0.1'
                assert conn._port == 27019

            for i in xrange(10):
                conn = asyncmongo.connection.Connection(pool=Pool(),
                                                        seed=[('127.0.0.1', 27018), ('127.0.0.1', 27020)],
                                                        rs="rs0", secondary_only=True)

                conn._put_job(AsyncClose(), 0)
                conn._next_job()
                tornado.ioloop.IOLoop.instance().start()

                assert conn._host == '127.0.0.1'
                assert conn._port == 27018

        except:
            tornado.ioloop.IOLoop.instance().stop()
            raise

    def test_update(self):
        try:
            test_shunt.setup()

            db = asyncmongo.Client(pool_id='testrs_f', rs="wrong_rs", seed=[("127.0.0.1", 27020)], dbname='test', maxconnections=2)

            # Try to update with a wrong replica set name
            def update_callback(response, error):
                tornado.ioloop.IOLoop.instance().stop()
                logging.info(response)
                logging.info(error)
                assert isinstance(error, asyncmongo.RSConnectionError)
                test_shunt.register_called('update_f')

            db.test_stats.update({"_id" : TEST_TIMESTAMP}, {'$inc' : {'test_count' : 1}}, callback=update_callback)

            tornado.ioloop.IOLoop.instance().start()
            test_shunt.assert_called('update_f')

            db = asyncmongo.Client(pool_id='testrs', rs="rs0", seed=[("127.0.0.1", 27020)], dbname='test', maxconnections=2)

            # Update
            def update_callback(response, error):
                logging.info("UPDATE:")
                tornado.ioloop.IOLoop.instance().stop()
                logging.info(response)
                assert len(response) == 1
                test_shunt.register_called('update')

            db.test_stats.update({"_id" : TEST_TIMESTAMP}, {'$inc' : {'test_count' : 1}}, upsert=True, callback=update_callback)

            tornado.ioloop.IOLoop.instance().start()
            test_shunt.assert_called('update')

            # Retrieve the updated value
            def query_callback(response, error):
                tornado.ioloop.IOLoop.instance().stop()
                logging.info(response)
                logging.info(error)
                assert error is None
                assert isinstance(response, dict)
                assert response['_id'] == TEST_TIMESTAMP
                assert response['test_count'] == 1
                test_shunt.register_called('retrieved')

            db.test_stats.find_one({"_id" : TEST_TIMESTAMP}, callback=query_callback)
            tornado.ioloop.IOLoop.instance().start()
            test_shunt.assert_called('retrieved')

            # Switch the master
            self.mongo_cmd(
                "cfg = rs.conf(); cfg.members[1].priority = 1; cfg.members[0].priority = 2; rs.reconfig(cfg);",
                27019, "reconnected to server")
            self.wait_master(27018)

            # Expect the connection to be closed
            def query_err_callback(response, error):
                tornado.ioloop.IOLoop.instance().stop()
                logging.info(response)
                logging.info(error)
                assert isinstance(error, Exception)

            db.test_stats.find_one({"_id" : TEST_TIMESTAMP}, callback=query_err_callback)
            tornado.ioloop.IOLoop.instance().start()

            # Retrieve the updated value again, from the new master
            def query_again_callback(response, error):
                tornado.ioloop.IOLoop.instance().stop()
                logging.info(response)
                logging.info(error)
                assert error is None
                assert isinstance(response, dict)
                assert response['_id'] == TEST_TIMESTAMP
                assert response['test_count'] == 1
                test_shunt.register_called('retrieved_again')

            db.test_stats.find_one({"_id" : TEST_TIMESTAMP}, callback=query_again_callback)
            tornado.ioloop.IOLoop.instance().start()
            test_shunt.assert_called('retrieved_again')
        except:
            tornado.ioloop.IOLoop.instance().stop()
            raise

########NEW FILE########
__FILENAME__ = test_safe_updates
import tornado.ioloop
import time
import logging

import test_shunt
import asyncmongo

TEST_TIMESTAMP = int(time.time())

class SafeUpdatesTest(test_shunt.MongoTest):
    def test_update_safe(self):
        test_shunt.setup()
        db = asyncmongo.Client(pool_id='testinsert', host='127.0.0.1', port=27018, dbname='test', maxconnections=2)
        
        def update_callback(response, error):
            tornado.ioloop.IOLoop.instance().stop()
            logging.info(response)
            assert len(response) == 1
            test_shunt.register_called('update')

        # all of these should be called, but only one should have a callback
        # we also are checking that connections in the pool never increases >1 with max_connections=2
        # this is because connections for safe=False calls get put back in the pool immediated
        db.test_stats.update({"_id" : TEST_TIMESTAMP}, {'$inc' : {'test_count' : 1}}, safe=False, upsert=True)
        db.test_stats.update({"_id" : TEST_TIMESTAMP}, {'$inc' : {'test_count' : 1}}, safe=False, upsert=True)
        db.test_stats.update({"_id" : TEST_TIMESTAMP}, {'$inc' : {'test_count' : 1}}, safe=False, upsert=True)
        db.test_stats.update({"_id" : TEST_TIMESTAMP}, {'$inc' : {'test_count' : 1}}, safe=False, upsert=True)
        db.test_stats.update({"_id" : TEST_TIMESTAMP}, {'$inc' : {'test_count' : 1}}, upsert=True, callback=update_callback)
        
        tornado.ioloop.IOLoop.instance().start()
        test_shunt.assert_called('update')
        
        def query_callback(response, error):
            tornado.ioloop.IOLoop.instance().stop()
            logging.info(response)
            assert isinstance(response, dict)
            assert response['_id'] == TEST_TIMESTAMP
            assert response['test_count'] == 5
            test_shunt.register_called('retrieved')

        db.test_stats.find_one({"_id" : TEST_TIMESTAMP}, callback=query_callback)
        tornado.ioloop.IOLoop.instance().start()
        test_shunt.assert_called('retrieved')

########NEW FILE########
__FILENAME__ = test_shunt
import logging
import sys
import os
import unittest
import subprocess
import signal
import time

import tornado.ioloop
import pymongo

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
   format='%(asctime)s %(process)d %(filename)s %(lineno)d %(levelname)s #| %(message)s',
   datefmt='%H:%M:%S')

# add the path to the local asyncmongo
# there is probably a better way to do this that doesn't require magic
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if app_dir not in sys.path:
    logging.debug('adding %r to sys.path' % app_dir)
    sys.path.insert(0, app_dir)

import asyncmongo
import asyncmongo.pool
# make sure we get the local asyncmongo
assert asyncmongo.__file__.startswith(app_dir)

class PuritanicalIOLoop(tornado.ioloop.IOLoop):
    """
    A loop that quits when it encounters an Exception -- makes errors in
    callbacks easier to debug and prevents them from hanging the unittest
    suite.
    """
    def handle_callback_exception(self, callback):
        exc_type, exc_value, tb = sys.exc_info()
        raise exc_value

class MongoTest(unittest.TestCase):
    """
    Starts and stops a mongod
    """
    mongod_options = [('--port', str(27018))]
    def setUp(self):
        """setup method that starts up mongod instances using `self.mongo_options`"""
        # So any function that calls IOLoop.instance() gets the
        # PuritanicalIOLoop instead of a default loop.
        if not tornado.ioloop.IOLoop.initialized():
            self.loop = PuritanicalIOLoop()
            tornado.ioloop.IOLoop._instance = self.loop
        else:
            self.loop = tornado.ioloop.IOLoop.instance()
            self.assert_(
                isinstance(self.loop, PuritanicalIOLoop),
                "Couldn't install IOLoop"
            )
            
        self.temp_dirs = []
        self.mongods = []
        for options in self.mongod_options:
            dirname = os.tempnam()
            os.makedirs(dirname)
            self.temp_dirs.append(dirname)
            
            options = ['mongod', '--oplogSize', '2', '--dbpath', dirname,
                       '--smallfiles', '-v', '--nojournal', '--bind_ip', '0.0.0.0'] + list(options)
            logging.debug(options)
            pipe = subprocess.Popen(options)
            self.mongods.append(pipe)
            logging.debug('started mongod %s' % pipe.pid)
        sleep_time = 1 + (len(self.mongods) * 2)
        logging.info('waiting for mongod to start (sleeping %d seconds)' % sleep_time)
        time.sleep(sleep_time)

    def tearDown(self):
        """teardown method that cleans up child mongod instances, and removes their temporary data files"""
        logging.debug('teardown')
        asyncmongo.pool.ConnectionPools.close_idle_connections()
        for mongod in self.mongods:
            logging.debug('killing mongod %s' % mongod.pid)
            os.kill(mongod.pid, signal.SIGKILL)
            mongod.wait()
        for dirname in self.temp_dirs:
            logging.debug('cleaning up %s' % dirname)
            pipe = subprocess.Popen(['rm', '-rf', dirname])
            pipe.wait()


class SynchronousMongoTest(unittest.TestCase):
    """
    Convenience class: a test case that can make synchronous calls to the
    official pymongo to ease setup code, via the pymongo_conn property.
    """
    mongod_options = [('--port', str(27018))]
    @property
    def pymongo_conn(self):
        if not hasattr(self, '_pymongo_conn'):
            self._pymongo_conn = pymongo.Connection(port=int(self.mongod_options[0][1]))
        return self._pymongo_conn

    def get_open_cursors(self):
        output = self.pymongo_conn.admin.command('serverStatus')
        return output.get('cursors', {}).get('totalOpen')

results = {}

def setup():
    global results
    results = {}

def register_called(key, data=None):
    assert key not in results
    results[key] = data

def assert_called(key, data=None):
    assert key in results
    assert results[key] == data

def is_called(key):
    return key in results

########NEW FILE########
__FILENAME__ = test_slave_only
import tornado.ioloop
import time
import logging

import test_shunt
import asyncmongo

TEST_TIMESTAMP = int(time.time())

class SlaveOnlyTest(test_shunt.MongoTest):
    mongod_options = [
        ('--port', '27018', '--master'),
        ('--port', '27019', '--slave', '--source', '127.0.0.1:27018'), 
    ]
    def test_query_slave(self):
        try:
            test_shunt.setup()
            masterdb = asyncmongo.Client(pool_id='testquerymaster', host='127.0.0.1', port=27018, dbname='test', maxconnections=2)
            slavedb = asyncmongo.Client(pool_id='testqueryslave', host='127.0.0.1', port=27019, dbname='test', maxconnections=2, slave_okay=True)
            logging.debug('waiting for replication to start (sleeping 4 seconds)')
            time.sleep(4)
        
            def update_callback(response, error):
                tornado.ioloop.IOLoop.instance().stop()
                logging.info(response)
                assert len(response) == 1
                test_shunt.register_called('update')

            masterdb.test_stats.update({"_id" : TEST_TIMESTAMP}, {'$inc' : {'test_count' : 1}}, upsert=True, callback=update_callback)
        
            tornado.ioloop.IOLoop.instance().start()
            test_shunt.assert_called('update')

            # wait for the insert to get to the slave
            time.sleep(2.5)
        
            def query_callback(response, error):
                tornado.ioloop.IOLoop.instance().stop()
                logging.info(response)
                logging.info(error)
                assert error is None
                assert isinstance(response, dict)
                assert response['_id'] == TEST_TIMESTAMP
                assert response['test_count'] == 1
                test_shunt.register_called('retrieved')

            slavedb.test_stats.find_one({"_id" : TEST_TIMESTAMP}, callback=query_callback)
            tornado.ioloop.IOLoop.instance().start()
            test_shunt.assert_called('retrieved')
        except:
            tornado.ioloop.IOLoop.instance().stop()
            raise

########NEW FILE########
