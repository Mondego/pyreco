__FILENAME__ = record
# -*- coding: utf-8 -*-
#
# Lazyboy examples
#
# © 2009 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#
# This example assumes the following schema:
#
# <Keyspaces>
#     <Keyspace Name="UserData">
#         <ColumnFamily CompareWith="BytesType" Name="Users"/>
#     </Keyspace>
# </Keyspaces>
#


from lazyboy import *
from lazyboy.key import Key


# Define your cluster(s)
connection.add_pool('UserData', ['localhost:9160'])

# This can be used for convenience, rather than repeating the Keyspace
# and CF.
class UserKey(Key):
    """This is a key class which defaults to storage in the Users CF
    in the UserData Keyspace."""
    def __init__(self, key=None):
        Key.__init__(self, "UserData", "Users", key)



# Subclass Record to create an object of the correct type.
class User(record.Record):
    """A class representing a user in Cassandra."""

    # Anything in here _must_ be set before the object is saved
    _required = ('username',)

    def __init__(self, *args, **kwargs):
        """Initialize the record, along with a new key."""
        record.Record.__init__(self, *args, **kwargs)
        self.key = UserKey()


# Create an empty object
u = User()

# Set the key. A UUID will be generated for you
print u.key
# -> {'keyspace': 'UserData', 'column_family': 'Users',
#     'key': 'da6c8e19174f40cfa6d0b65a08eef62f',
#      'super_column': None}

# If you want to store records in a SuperColumn, set key.super_column:
superkey = u.key.clone(super_column="scol_a")

data = {'username': 'ieure', 'email': 'ian@digg.com'}

# The object is a dict. All these are equivalent.
u.update(data)
u.update(data.items())
u.update(**data)
for k in data:
    u[k] = data[k]

# Arguments to __init__ are passed to update()
u_ = User(data)
print u_           # -> {'username': 'ieure', 'email': 'ian@digg.com'}

# You can see if it's been modified.
print u.is_modified()           # -> True

# Save to Cassandra
u.save()           # -> {'username': 'ieure', 'email': 'ian@digg.com'}

print u.is_modified()           # -> False

# Load it in a new instance.
#u_ = User().load(key)
u_ = User().load(u.key.clone())    # PATCH

print u_           # -> {'username': 'ieure', 'email': 'ian@digg.com'}

print u.is_modified()           # -> False
del u['username']
print u.valid()                 # -> False
print u.missing()               # -> ('username',)
try:
    u.save()        # -> ('Missing required field(s):', ('username',))
except Exception, e:
    print e

# Discard modifications
u.revert()
print u.is_modified()           # -> False
print u.valid()                 # -> True

########NEW FILE########
__FILENAME__ = view
# -*- coding: utf-8 -*-
#
# © 2009 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#
# This example assumes the following schema:
#
# <Keyspaces>
#     <Keyspace Name="UserData">
#         <ColumnFamily CompareWith="BytesType" Name="Users"/>
#         <ColumnFamily CompareWith="BytesType" Name="UserViews"/>
#     </Keyspace>
# </Keyspaces>
#

from pprint import pprint

from lazyboy import *
from lazyboy.key import Key
from record import UserKey, User

connection.add_pool('UserData', ['localhost:9160'])

class AllUsersViewKey(Key):
    """This is a key class which defaults to storage in the UserViews CF
    in the UserData Keyspace."""
    def __init__(self, key=None):
        Key.__init__(self, "UserData", "UserViews", key)


# You should subclass View to provide defaults for your view.
class AllUsersView(View):
    def __init__(self):
        View.__init__(self)
        # This is the key to the CF holding the view
        self.key = AllUsersViewKey(key='row_a')
        # Records referenced in the view will be instances of this class.
        self.record_class = User
        # This is the key for the record.
        self.record_key = UserKey()


# Instantiate the view
auv = AllUsersView()

_users = ({'username': 'jsmith', 'email': 'jsmith@example.com'},
          {'username': 'jdoe', 'email': 'jdoe@example.com'},
          {'username': 'jxdoe', 'email': 'jxdoe@example.com'})

# Add records to the view
for _user in _users:
    auv.append(User(_user).save())

# When the view is iterated, the records referenced in it's keys are
# returned.
pprint(tuple(auv))
# -> ({'username': 'jxdoe', 'email': 'jxdoe@example.com'}
#     {'username': 'jdoe', 'email': 'jdoe@example.com'},
#     {'username': 'jsmith', 'email': 'jsmith@example.com'})

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
#
# © 2009, 2010 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#

"""Lazyboy: Base class for access to Cassandra."""

from cassandra.ttypes import ConsistencyLevel

from lazyboy.exceptions import ErrorIncompleteKey
import lazyboy.connection as connection


class CassandraBase(object):

    """The base class for all Cassandra-accessing objects."""

    consistency = ConsistencyLevel.ONE

    def __init__(self):
        self._clients = {}

    def _get_cas(self, keyspace=None):
        """Return the cassandra client."""
        if not keyspace and (not hasattr(self, 'key') or not self.key):
            raise ErrorIncompleteKey("Instance has no key.")

        keyspace = keyspace or self.key.keyspace
        if keyspace not in self._clients:
            self._clients[keyspace] = connection.get_pool(keyspace)

        return self._clients[keyspace]

########NEW FILE########
__FILENAME__ = column_crud
# -*- coding: utf-8 -*-
#
# © 2009 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#

"""Column-level operations."""

from cassandra import ttypes as cas_types

from lazyboy.connection import get_pool
from lazyboy.iterators import unpack


def get_column(key, column_name, consistency=None):
    """Get a column."""
    consistency = consistency or cas_types.ConsistencyLevel.ONE
    return unpack(
        [get_pool(key.keyspace).get(
            key.keyspace, key.key,
            key.get_path(column=column_name), consistency)]).next()


def set_column(key, column, consistency=None):
    """Set a column."""
    assert isinstance(column, cas_types.Column)
    consistency = consistency or cas_types.ConsistencyLevel.ONE
    return set(key, column.name, column.value, column.timestamp, consistency)


def get(key, column, consistency=None):
    """Get the value of a column."""
    return get_column(key, column, consistency).value


def set(key, name, value, timestamp=None, consistency=None):
    """Set a column's value."""
    consistency = consistency or cas_types.ConsistencyLevel.ONE
    get_pool(key.keyspace).insert(
        key.keyspace, key.key, key.get_path(column=name), value, timestamp,
        consistency)


def remove(key, column, timestamp=None, consistency=None):
    """Remove a column."""
    consistency = consistency or cas_types.ConsistencyLevel.ONE
    get_pool(key.keyspace).remove(key.keyspace, key.key,
                                  key.get_path(column=column), timestamp,
                                  consistency)

########NEW FILE########
__FILENAME__ = connection
# -*- coding: utf-8 -*-
#
# © 2009, 2010 Digg, Inc. All rights reserved.
# Author: Chris Goffinet <goffinet@digg.com>
# Author: Ian Eure <ian@digg.com>
#

"""Lazyboy: Connections."""
from __future__ import with_statement
from functools import update_wrapper
import logging
import random
import os
import threading
import socket
import errno
import time

from cassandra import Cassandra
import cassandra.ttypes as cas_types
from thrift import Thrift
from thrift.transport import TTransport, TSocket
from thrift.protocol import TBinaryProtocol
import thrift

import lazyboy.exceptions as exc
from contextlib import contextmanager

_SERVERS = {}
_CLIENTS = {}
RETRY_ATTEMPTS = 5

def _retry_default_callback(attempt, exc_):
    """Retry an attempt five times, then give up."""
    return attempt < RETRY_ATTEMPTS


def retry(callback=None):
    """Retry an operation."""

    callback = callback or _retry_default_callback
    assert callable(callback)

    def __closure__(func):

        def __inner__(*args, **kwargs):
            attempt = 1
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception, ex:
                    if not callback(attempt, ex):
                        raise ex
                    attempt += 1
        return __inner__
    return __closure__


def add_pool(name, servers, timeout=None, recycle=None, **kwargs):
    """Add a connection."""
    _SERVERS[name] = dict(servers=servers, timeout=timeout, recycle=recycle,
                          **kwargs)


def get_pool(name):
    """Return a client for the given pool name."""
    key = str(os.getpid()) + threading.currentThread().getName() + name
    if key in _CLIENTS:
        return _CLIENTS[key]

    try:
        _CLIENTS[key] = Client(**_SERVERS[name])
        return _CLIENTS[key]
    except Exception:
        raise exc.ErrorCassandraClientNotFound(
            "Pool `%s' is not defined." % name)


class _DebugTraceFactory(type):

    """A factory for making debug-tracing clients."""

    def __new__(mcs, name, bases, dct):
        """Create a new tracing client class."""
        assert len(bases) == 1, "Sorry, we don't do multiple inheritance."
        new_class = type(name, bases, dct)

        base_class = bases[0]
        for attrname in dir(base_class):
            attr = getattr(base_class, attrname)

            if (attrname.startswith('__') or attrname.startswith('send_')
                or attrname.startswith('recv_') or not callable(attr)):
                continue

            def wrap(func):
                """Returns a new wrapper for a function."""

                def __wrapper__(self, *args, **kwargs):
                    """A funcall wrapper."""
                    start_time = time.time()
                    try:
                        out = func(self, *args, **kwargs)
                    except Exception, ex:
                        self.log.error(
                            "Caught %s while calling: %s:%s -> %s(%s, %s)",
                            ex.__class__.__name__, self.host, self.port,
                            func.__name__, args, kwargs)
                        raise

                    end_time = time.time()

                    elapsed = (end_time - start_time) * 1000
                    log_func = (self.log.warn if elapsed >= self._slow_thresh
                                else self.log.debug)

                    log_func("%dms: %s:%s -> %s(%s, %s)",
                             elapsed, self.host, self.port,
                             func.__name__, args, kwargs)

                    return out

                update_wrapper(__wrapper__, func)
                return __wrapper__

            setattr(new_class, attrname, wrap(attr))

        return new_class


class DebugTraceClient(Cassandra.Client):

    """A client with debug tracing and slow query logging."""

    __metaclass__ = _DebugTraceFactory

    def __init__(self, *args, **kwargs):
        """Initialize"""
        slow_thresh = kwargs.get('slow_thresh', 100)
        log = kwargs.get('log', logging.getLogger(self.__class__.__name__))
        if 'slow_thresh' in kwargs:
            del kwargs['slow_thresh']
        if 'log' in kwargs:
            del kwargs['log']
        Cassandra.Client.__init__(self, *args, **kwargs)
        self._slow_thresh = slow_thresh
        self.log = log


class Client(object):

    """A wrapper around the Cassandra client which load-balances."""

    def __init__(self, servers, timeout=None, recycle=None, debug=False,
                 **conn_args):
        """Initialize the client."""
        self._servers = servers
        self._recycle = recycle
        self._timeout = timeout

        class_ = DebugTraceClient if debug else Cassandra.Client
        self._clients = [s for s in
                         [self._build_server(class_, *server.split(":"),
                                             **conn_args)
                          for server in servers] if s]
        self._current_server = random.randint(0, len(self._clients))

    def _build_server(self, class_, host, port, **conn_args):
        """Return a client for the given host and port."""
        try:
            socket_ = TSocket.TSocket(host, int(port))
            if self._timeout:
                socket_.setTimeout(self._timeout)
            transport = TTransport.TBufferedTransport(socket_)
            protocol = TBinaryProtocol.TBinaryProtocolAccelerated(transport)
            client = class_(protocol, **conn_args)
            client.transport = transport
            setattr(client, 'host', host)
            setattr(client, 'port', port)
            return client
        except (Thrift.TException, cas_types.InvalidRequestException,
                cas_types.UnavailableException):
            return None

    def _get_server(self):
        """Return the next server (round-robin) from the list."""
        if self._clients is None or len(self._clients) == 0:
            raise exc.ErrorCassandraNoServersConfigured()

        self._current_server = self._current_server % len(self._clients)
        return self._clients[self._current_server]

    def list_servers(self):
        """Return all servers we know about."""
        return self._clients

    def _connect(self):
        """Connect to Cassandra if not connected."""

        client = self._get_server()

        if client.transport.isOpen() and self._recycle:
            if (client.connect_time + self._recycle) > time.time():
                return client
            else:
                client.transport.close()

        elif client.transport.isOpen():
            return client

        try:
            client.transport.open()
            client.connect_time = time.time()
        except thrift.transport.TTransport.TTransportException, ex:
            client.transport.close()
            raise exc.ErrorThriftMessage(
                ex.message, self._servers[self._current_server])

        return client

    @contextmanager
    def get_client(self):
        """Yield a Cassandra client connection."""
        client = None
        try:
            client = self._connect()
            yield client
        except socket.error, ex:
            if client:
                client.transport.close()

            args = (errno.errorcode[ex.args[0]], ex.args[1],
                    self._servers[self._current_server])
            raise exc.ErrorThriftMessage(*args)
        except Thrift.TException, ex:
            message = ex.message or "Transport error, reconnect"
            if client:
                client.transport.close()
            raise exc.ErrorThriftMessage(message,
                                         self._servers[self._current_server])
        except (cas_types.NotFoundException, cas_types.UnavailableException,
                cas_types.InvalidRequestException), ex:
            ex.args += (self._servers[self._current_server],
                        "on %s" % self._servers[self._current_server])
            raise ex

    @retry()
    def get(self, *args, **kwargs):
        """
        Parameters:
        - keyspace
        - key
        - column_path
        - consistency_level
        """
        with self.get_client() as client:
            return client.get(*args, **kwargs)

    @retry()
    def get_slice(self, *args, **kwargs):
        """
        Parameters:
        - keyspace
        - key
        - column_parent
        - predicate
        - consistency_level
        """
        with self.get_client() as client:
            return client.get_slice(*args, **kwargs)

    @retry()
    def get_range_slice(self, *args, **kwargs):
        """
        returns a subset of columns for a range of keys.

        Parameters:
        - keyspace
        - column_parent
        - predicate
        - start_key
        - finish_key
        - row_count
        - consistency_level
        """
        with self.get_client() as client:
            return client.get_range_slice(*args, **kwargs)

    @retry()
    def multiget(self, *args, **kwargs):
        """
        Parameters:
        - keyspace
        - keys
        - column_path
        - consistency_level
        """
        with self.get_client() as client:
            return client.multiget(*args, **kwargs)

    @retry()
    def multiget_slice(self, *args, **kwargs):
        """
        Parameters:
        - keyspace
        - keys
        - column_parent
        - predicate
        - consistency_level
        """
        with self.get_client() as client:
            return client.multiget_slice(*args, **kwargs)

    @retry()
    def get_count(self, *args, **kwargs):
        """
        Parameters:
        - keyspace
        - key
        - column_parent
        - consistency_level
        """
        with self.get_client() as client:
            return client.get_count(*args, **kwargs)

    @retry()
    def get_key_range(self, *args, **kwargs):
        """
        Parameters:
        - keyspace
        - column_family
        - start
        - finish
        - count
        - consistency_level
        """
        with self.get_client() as client:
            return client.get_key_range(*args, **kwargs)

    @retry()
    def remove(self, *args, **kwargs):
        """
        Parameters:
        - keyspace
        - key
        - column_path
        - timestamp
        - consistency_level
        """
        with self.get_client() as client:
            return client.remove(*args, **kwargs)

    @retry()
    def get_string_property(self, *args, **kwargs):
        """
        Parameters:
        - property
        """
        with self.get_client() as client:
            return client.get_string_property(*args, **kwargs)

    @retry()
    def get_string_list_property(self, *args, **kwargs):
        """
        Parameters:
        - property
        """
        with self.get_client() as client:
            return client.get_string_list_property(*args, **kwargs)

    @retry()
    def describe_keyspace(self, *args, **kwargs):
        """
        Parameters:
        - keyspace
        """
        with self.get_client() as client:
            return client.describe_keyspace(*args, **kwargs)

    @retry()
    def batch_insert(self, *args, **kwargs):
        """
        Parameters:
        - keyspace
        - key
        - cfmap
        - consistency_level
        """
        with self.get_client() as client:
            return client.batch_insert(*args, **kwargs)

    @retry()
    def batch_mutate(self, *args, **kwargs):
        """
        Parameters:
        - keyspace
        - mutation_map
        - consistency_level
        """
        with self.get_client() as client:
            return client.batch_mutate(*args, **kwargs)

    @retry()
    def insert(self, *args, **kwargs):
        """
        Parameters:
        - keyspace
        - key
        - column_path
        - value
        - timestamp
        - consistency_level
        """
        with self.get_client() as client:
            return client.insert(*args, **kwargs)

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
#
# © 2009 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#

"""Lazyboy: Exceptions."""


class LazyboyException(Exception):
    """Base exception class which all Lazyboy exceptions extend."""
    pass


class ErrorNotSupported(LazyboyException):
    """Raised when the operation is unsupported."""
    pass


class ErrorMissingField(LazyboyException):
    """Raised in Record.save when a record is incomplete."""
    pass


class ErrorInvalidValue(LazyboyException):
    """Raised when a Record's item is set to None."""
    pass


class ErrorMissingKey(LazyboyException):
    """Raised when a key is needed, but not available."""
    pass


class ErrorIncompleteKey(LazyboyException):
    """Raised when there isn't enough information to create a key."""
    pass


class ErrorNoSuchRecord(LazyboyException):
    """Raised when a nonexistent record is requested."""
    pass


class ErrorCassandraClientNotFound(LazyboyException):
    """Raised when there is no client for a requested keyspace."""
    pass


class ErrorThriftMessage(LazyboyException):
    """Raised when there is a Thrift transport error."""
    pass


class ErrorCassandraNoServersConfigured(LazyboyException):
    """Raised when Client has no servers, but was asked for one."""
    pass


class ErrorImmutable(LazyboyException):
    """Raised on an attempt to modify an immutable object."""
    pass

########NEW FILE########
__FILENAME__ = iterators
# -*- coding: utf-8 -*-
#
# © 2009, 2010 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#

"""Iterator-based Cassandra tools."""

import itertools as it
from operator import attrgetter, itemgetter
from collections import defaultdict

from lazyboy.connection import get_pool
import lazyboy.exceptions as exc

from cassandra.ttypes import SlicePredicate, SliceRange, ConsistencyLevel, \
    ColumnOrSuperColumn, Column, ColumnParent


GET_KEYSPACE = attrgetter("keyspace")
GET_COLFAM = attrgetter("column_family")
GET_KEY = attrgetter("key")
GET_SUPERCOL = attrgetter("super_column")


def groupsort(iterable, keyfunc):
    """Return a generator which sort and groups a list."""
    return it.groupby(sorted(iterable, key=keyfunc), keyfunc)


def slice_iterator(key, consistency, **predicate_args):
    """Return an iterator over a row."""

    predicate = SlicePredicate()
    if 'columns' in predicate_args:
        predicate.column_names = predicate_args['columns']
    else:
        args = {'start': "", 'finish': "",
                  'count': 100000, 'reversed': False}
        args.update(predicate_args)
        predicate.slice_range=SliceRange(**args)

    consistency = consistency or ConsistencyLevel.ONE

    client = get_pool(key.keyspace)
    res = client.get_slice(
        key.keyspace, key.key, key, predicate, consistency)

    if not res:
        raise exc.ErrorNoSuchRecord("No record matching key %s" % key)

    return unpack(res)


def multigetterator(keys, consistency, **range_args):
    """Return a dictionary of data from Cassandra.

    This fetches data with the minumum number of network requests. It
    DOES NOT preserve order.

    If you depend on ordering, use list_multigetterator. This may
    require more requests.
    """
    kwargs = {'start': "", 'finish': "",
              'count': 100000, 'reversed': False}
    kwargs.update(range_args)
    predicate = SlicePredicate(slice_range=SliceRange(**kwargs))
    consistency = consistency or ConsistencyLevel.ONE

    out = {}
    for (keyspace, ks_keys) in groupsort(keys, GET_KEYSPACE):
        client = get_pool(keyspace)
        out[keyspace] = {}
        for (colfam, cf_keys) in groupsort(ks_keys, GET_COLFAM):

            if colfam not in keyspace:
                out[keyspace][colfam] = defaultdict(dict)

            for (supercol, sc_keys) in groupsort(cf_keys, GET_SUPERCOL):
                records = client.multiget_slice(
                    keyspace, map(GET_KEY, sc_keys),
                    ColumnParent(colfam, supercol), predicate, consistency)

                for (row_key, cols) in records.iteritems():
                    cols = unpack(cols)
                    if supercol is None:
                        out[keyspace][colfam][row_key] = cols
                    else:
                        out[keyspace][colfam][row_key][supercol] = cols

    return out


def sparse_get(key, columns):
    """Return an iterator over a specific set of columns."""

    client = get_pool(key.keyspace)
    res = client.get_slice(
        key.keyspace, key.key, key, SlicePredicate(column_names=columns),
        ConsistencyLevel.ONE)

    return unpack(res)


def sparse_multiget(keys, columns):
    """Return an iterator over a specific set of columns."""

    first_key = iter(keys).next()
    client = get_pool(first_key.keyspace)
    row_keys = [key.key for key in keys]
    res = client.multiget_slice(
        first_key.keyspace, row_keys, first_key,
        SlicePredicate(column_names=columns), ConsistencyLevel.ONE)

    out = {}
    for (row_key, cols) in res.iteritems():
        out[row_key] = [corsc.column or corsc.super_column for corsc in cols]
    return out


def key_range(key, start="", finish="", count=100):
    """Return an iterator over a range of keys."""
    cas = get_pool(key.keyspace)
    return cas.get_key_range(key.keyspace, key.column_family, start,
                                  finish, count, ConsistencyLevel.ONE)


def key_range_iterator(key, start="", finish="", count=100):
    """Return an iterator which produces Key instances for a key range."""
    return (key.clone(key=k) for k in key_range(key, start, finish, count))


def pack(objects):
    """Return a generator which packs objects into ColumnOrSuperColumns."""
    for object_ in objects:
        key = 'column' if isinstance(object_, Column) else 'super_column'
        yield ColumnOrSuperColumn(**{key: object_})


def unpack(records):
    """Return a generator which unpacks objects from ColumnOrSuperColumns."""
    return (corsc.column or corsc.super_column for corsc in records)


def repeat_seq(seq, num=1):
    """Return a seq of seqs with elements of seq repeated n times.


    repeat_seq([0, 1, 2, 3, 4], 2) -> [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4]]
    """
    return (it.repeat(x, num) for x in seq)


def repeat(seq, num):
    """Retuan seq with each element repeated n times.

    repeat([0, 1, 2, 3, 4], 2) -> [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
    """
    return chain_iterable(repeat_seq(seq, num))


def chain_iterable(iterables):
    """Yield values from a seq of seqs."""
    # from_iterable(['ABC', 'DEF']) --> A B C D E F
    for seq in iterables:
        for element in seq:
            yield element


def chunk_seq(seq, size):
    """Return a sequence in chunks.

    First, we use repeat() to create an infinitely repeating sequence
    of numbers, repeated 3 times:
    (0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, … n, n)

    Then we zip this with the elements of the input seq:
    ((0, a), (0, b), (0, c), (1, d), (1, e), (1, f), … (13, z))

    This is passed into groupby, where the zipped seq is grouped by
    the first item, producing (len(seq)/size) groups of elements:
    ((0, group-0), (1, group-1), … (n, group-n))

    This is then fed to imap, which extracts the group-n iterator and
    materializes it to:
    ((a, b, c), (d, e, f), (g, h, i), …)
    """
    return it.imap(lambda elt: tuple(it.imap(itemgetter(1), elt[1])),
                   it.groupby(it.izip(repeat(it.count(), size), seq),
                              itemgetter(0)))

########NEW FILE########
__FILENAME__ = key
# -*- coding: utf-8 -*-
#
# © 2009 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#
"""Lazyboy: Key."""

import uuid

from cassandra.ttypes import ColumnPath, ColumnParent

from lazyboy.base import CassandraBase
from lazyboy.exceptions import ErrorIncompleteKey


class Key(ColumnParent, CassandraBase):

    """A key which determines how to reach a record."""

    def __init__(self, keyspace=None, column_family=None, key=None,
                 super_column=None):
        if not keyspace or not column_family:
            raise ErrorIncompleteKey("A required attribute was not set.")
        key = key or self._gen_uuid()

        self.keyspace, self.key = keyspace, key
        ColumnParent.__init__(self, column_family, super_column)
        CassandraBase.__init__(self)

    def _gen_uuid(self):
        """Generate a UUID for this object"""
        return uuid.uuid4().hex

    def is_super(self):
        """Return a boolean indicating if this is a key to a supercolumn."""
        return bool(self.super_column)

    def _attrs(self):
        """Get attributes of this key."""
        return dict((attr, getattr(self, attr)) for attr in
                    ('keyspace', 'column_family', 'key', 'super_column'))

    def __repr__(self):
        """Return a printable representation of this key."""
        return str(self._attrs())

    def __unicode__(self):
        """Return a unicode string of this key."""
        return unicode(str(self))

    def get_path(self, **kwargs):
        """Return a new ColumnPath for this key."""
        new = self._attrs()
        del new['keyspace'], new['key']
        new.update(kwargs)
        return ColumnPath(**new)

    def clone(self, **kwargs):
        """Return a clone of this key with keyword args changed"""
        return DecoratedKey(self, **kwargs)


class DecoratedKey(Key):

    """A key which decorates another.

    Any properties set in this key override properties in the parent
    key. Non-overriden properties changed in the parent key are
    changed in the child key.
    """

    def __init__(self, parent_key, **kwargs):
        self.parent_key = parent_key
        for (key, val) in kwargs.items():
            setattr(self, key, val)

    def __getattr__(self, attr):
        if hasattr(self.parent_key, attr):
            return getattr(self.parent_key, attr)

        raise AttributeError("`%s' object has no attribute `%s'" % \
                                 (self.__class__.__name__, attr))

########NEW FILE########
__FILENAME__ = record
# -*- coding: utf-8 -*-
#
# © 2009, 2010 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#
"""Lazyboy: Record."""

import time
import copy
from itertools import ifilterfalse as filternot

from cassandra.ttypes import Column, SuperColumn

from lazyboy.connection import get_pool
from lazyboy.base import CassandraBase
from lazyboy.key import Key
import lazyboy.iterators as iterators
import lazyboy.exceptions as exc


class Record(CassandraBase, dict):

    """An object backed by a record in Cassandra."""

    # A tuple of items which must be present for the object to be valid
    _required = ()

    # The keyspace this record should be saved in
    _keyspace = None

    # The column family this record should be saved in
    _column_family = None

    # Indexes which this record should be added to on save
    _indexes = []

    # Denormalized copies of this record
    _mirrors = []

    def __init__(self, *args, **kwargs):
        dict.__init__(self)
        CassandraBase.__init__(self)

        self._clean()

        if args or kwargs:
            self.update(*args, **kwargs)

    def make_key(self, key=None, super_column=None, **kwargs):
        """Return a new key."""
        args = {'keyspace': self._keyspace,
                'column_family': self._column_family,
                'key': key,
                'super_column': super_column}
        args.update(**kwargs)
        return Key(**args)

    def default_key(self):
        """Return a default key for this record."""
        raise exc.ErrorMissingKey("There is no key set for this record.")

    def set_key(self, key, super_column=None):
        """Set the key for this record."""
        self.key = self.make_key(key=key, super_column=super_column)
        return self

    def get_indexes(self):
        """Return indexes this record should be stored in."""
        return [index() if isinstance(index, type) else index
                for index in self._indexes]

    def get_mirrors(self):
        """Return mirrors this record should be stored in."""
        return [mirror if isinstance(mirror, type) else mirror
                for mirror in self._mirrors]

    def valid(self):
        """Return a boolean indicating whether the record is valid."""
        return len(self.missing()) == 0

    def missing(self):
        """Return a tuple of required items which are missing."""
        return tuple(filternot(self.get, self._required))

    def is_modified(self):
        """Return True if the record has been modified since it was loaded."""
        return bool(len(self._modified) + len(self._deleted))

    def _clean(self):
        """Remove every item from the object"""
        map(self.__delitem__, self.keys())
        self._original, self._columns = {}, {}
        self._modified, self._deleted = {}, {}
        self.key = None

    def update(self, arg=None, **kwargs):
        """Update the object as with dict.update. Returns None."""
        if arg:
            if hasattr(arg, 'keys'):
                for key in arg:
                    self[key] = arg[key]
            else:
                for (key, val) in arg:
                    self[key] = val

        if kwargs:
            for key in kwargs:
                self[key] = kwargs[key]
        return self

    def sanitize(self, value):
        """Return a value appropriate for sending to Cassandra."""
        if value.__class__ is unicode:
            value = value.encode('utf-8')
        return str(value)

    def __repr__(self):
        """Return a printable representation of this record."""
        return "%s: %s" % (self.__class__.__name__, dict.__repr__(self))

    @staticmethod
    def timestamp():
        """Return a GMT UNIX timestamp."""
        return int(time.time())

    def __setitem__(self, item, value):
        """Set an item, storing it into the _columns backing store."""
        if value is None:
            raise exc.ErrorInvalidValue("You may not set an item to None.")

        value = self.sanitize(value)

        # If this doesn't change anything, don't record it
        _orig = self._original.get(item)
        if _orig and _orig.value == value:
            return

        dict.__setitem__(self, item, value)

        if item not in self._columns:
            self._columns[item] = Column(name=item)

        col = self._columns[item]

        if item in self._deleted:
            del self._deleted[item]

        self._modified[item] = True
        col.value, col.timestamp = value, self.timestamp()

    def __delitem__(self, item):
        dict.__delitem__(self, item)
        # Don't record this as a deletion if it wouldn't require a remove()
        self._deleted[item] = item in self._original
        if item in self._modified:
            del self._modified[item]
        del self._columns[item]

    def _inject(self, key, columns):
        """Inject columns into the record after they have been fetched.."""
        self.key = key
        if not isinstance(columns, dict):
            columns = dict((col.name, col) for col in iter(columns))

        self._original = columns
        self.revert()
        return self

    def _marshal(self):
        """Marshal deleted and changed columns."""
        return {'deleted': tuple(self.key.get_path(column=col)
                                 for col in self._deleted.keys()),
                'changed': tuple(self._columns[key]
                                 for key in self._modified.keys())}

    def load(self, key, consistency=None):
        """Load this record from primary key"""
        if not isinstance(key, Key):
            key = self.make_key(key)

        self._clean()
        consistency = consistency or self.consistency

        columns = iterators.slice_iterator(key, consistency)

        self._inject(key, dict([(column.name, column) for column in columns]))
        return self

    def save(self, consistency=None):
        """Save the record, returns self."""
        if not self.valid():
            raise exc.ErrorMissingField("Missing required field(s):",
                                        self.missing())

        if not hasattr(self, 'key') or not self.key:
            self.key = self.default_key()

        assert isinstance(self.key, Key), "Bad record key in save()"

        # Marshal and save changes
        changes = self._marshal()
        self._save_internal(self.key, changes, consistency)

        try:
            try:
                # Save mirrors
                for mirror in self.get_mirrors():
                    self._save_internal(mirror.mirror_key(self), changes,
                                        consistency)
            finally:
                # Update indexes
                for index in self.get_indexes():
                    index.append(self)
        finally:
            # Clean up internal state
            if changes['changed']:
                self._modified.clear()
            self._original = copy.deepcopy(self._columns)

        return self

    def _save_internal(self, key, changes, consistency=None):
        """Internal save method."""

        consistency = consistency or self.consistency
        client = self._get_cas(key.keyspace)
        # Delete items
        for path in changes['deleted']:
            client.remove(key.keyspace, key.key, path,
                          self.timestamp(), consistency)
        self._deleted.clear()

        # Update items
        if changes['changed']:
            client.batch_insert(*self._get_batch_args(
                    key, changes['changed'], consistency))

    def _get_batch_args(self, key, columns, consistency=None):
        """Return a BatchMutation for the given key and columns."""
        consistency = consistency or self.consistency

        if key.is_super():
            columns = [SuperColumn(name=key.super_column, columns=columns)]

        return (key.keyspace, key.key,
                {key.column_family: tuple(iterators.pack(columns))},
                consistency)

    @classmethod
    def remove_key(cls, key, consistency=None):
        """Remove a row based on a key."""
        consistency = consistency or cls.consistency
        get_pool(key.keyspace).remove(key.keyspace, key.key,
                                      key.get_path(), cls.timestamp(),
                               consistency)

    def remove(self, consistency=None):
        """Remove this record from Cassandra."""
        consistency = consistency or self.consistency
        self._get_cas().remove(self.key.keyspace, self.key.key,
                               self.key.get_path(), self.timestamp(),
                               consistency)
        self._clean()
        return self

    def revert(self):
        """Revert changes, restoring to the state we were in when loaded."""
        for col in self._original.values():
            dict.__setitem__(self, col.name, col.value)
            self._columns[col.name] = copy.copy(col)

        self._modified, self._deleted = {}, {}


class MirroredRecord(Record):

    """A mirrored (denormalized) record."""

    def mirror_key(self, parent_record):
        """Return the key this mirror should be saved into."""
        assert isinstance(parent_record, Record)
        raise exc.ErrorMissingKey("Please implement a mirror_key method.")

    def save(self, consistency=None):
        """Refuse to save this record."""
        raise exc.ErrorImmutable("Mirrored records are immutable.")

########NEW FILE########
__FILENAME__ = recordset
# -*- coding: utf-8 -*-
#
# © 2009 Digg, Inc All rights reserved.
# Author: Ian Eure <ian@digg.com>
#
"""Efficiently handle sets of Records."""

from itertools import ifilter

from lazyboy.key import Key
import lazyboy.iterators as itr
from lazyboy.record import Record
from lazyboy.base import CassandraBase
from lazyboy.exceptions import ErrorMissingField


def valid(records):
    """Returns True if all records in the set are valid."""
    return all(record.valid() for record in records)


def missing(records):
    """Returns a tuple indicating any fields missing from the records
    in the set."""
    return dict((r.key.key, r.missing()) for r in records if not r.valid())


def modified(records):
    """Returns a tuple of modifiedrecords in the set."""
    return tuple(ifilter(lambda r: r.is_modified(), records))


class RecordSet(CassandraBase, dict):

    """A set of Lazyboy records."""

    def __init__(self, records=None):
        """Initialize the RecordSet. Returns None."""
        CassandraBase.__init__(self)
        records = self._transform(records) if records else {}
        dict.__init__(self, records)

    def _transform(self, records):
        """Return a dict keyed by record key for sequence of Records."""
        if not records:
            return {}

        assert hasattr(records, '__iter__')

        return dict((record.key.key, record) for record in records)

    def append(self, record):
        """Append a new record to the set."""
        return self.__setitem__(record.key.key, record)

    def save(self, consistency=None):
        """Save all records.

        FIXME: This is really pretty terrible, but until we have batch
        delete and row-spanning mutations, this is as good as it can
        be. Except for SuperColumns."""

        consistency = consistency or self.consistency
        records = modified(self.itervalues())
        if not valid(records):
            raise ErrorMissingField("Missing required field(s):",
                                    missing(records))

        for record in records:
            record.save(consistency)
        return self


class KeyRecordSet(RecordSet):
    """A set of Records defined by record key. Records are batch loaded."""

    def __init__(self, keys=None, record_class=None, consistency=None):
        """Initialize the set."""
        record_class = record_class or Record
        records = (self._batch_load(record_class, keys, consistency)
                   if keys else None)
        RecordSet.__init__(self, records)

    def _batch_load(self, record_class, keys, consistency=None):
        """Return an iterator of records for the given keys."""
        consistency = consistency or self.consistency
        data = itr.multigetterator(keys, consistency)
        for (keyspace, col_fams) in data.iteritems():
            for (col_fam, rows) in col_fams.iteritems():
                for (row_key, cols) in rows.iteritems():
                    yield record_class()._inject(
                        Key(keyspace=keyspace, column_family=col_fam,
                            key=row_key), cols)

########NEW FILE########
__FILENAME__ = test_base
# -*- coding: utf-8 -*-
#
# © 2009 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#
"""Unit tests for Lazyboy's CassandraBase."""

import unittest
from lazyboy.base import CassandraBase
import lazyboy.connection
from lazyboy.key import Key
from lazyboy.exceptions import ErrorIncompleteKey


class CassandraBaseTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(CassandraBaseTest, self).__init__(*args, **kwargs)
        self.class_ = CassandraBase

    def _get_object(self, *args, **kwargs):
        return self.class_(*args, **kwargs)

    def setUp(self):
        self.__get_pool = lazyboy.connection.get_pool
        lazyboy.connection.get_pool = lambda keyspace: "Test"
        self.object = self._get_object()

    def tearDown(self):
        lazyboy.connection.get_pool = self.__get_pool
        del self.object

    def test_init(self):
        self.assert_(self.object._clients == {})

    def test_get_cas(self):
        self.assertRaises(ErrorIncompleteKey, self.object._get_cas)

        # Get with explicit tale
        self.assert_(self.object._get_cas('foo') == "Test")

        # Implicit based on pk
        self.object.pk = Key(keyspace='eggs', column_family="bacon",
                             key='sausage')
        self.assert_(self.object._get_cas('foo') == "Test")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_column_crud
# -*- coding: utf-8 -*-
#
# © 2009 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#

"""Unit tests for Lazyboy CRUD."""

import unittest
import cassandra.ttypes as cas_types

from lazyboy import column_crud as crud
from lazyboy import Key


class CrudTest(unittest.TestCase):

    """Test suite for Lazyboy CRUD."""

    class FakeClient(object):

        def __init__(self):
            self._column = None
            self._inserts = []

        def _set_column(self, column):
            self._column = column

        def get(self, *args, **kwargs):
            return cas_types.ColumnOrSuperColumn(column=self._column)

        def insert(self, *args):
            self._inserts.append(args)

        def __getattr__(self, attr):

            def __inner__(self, *args, **kwargs):
                return None
            return __inner__

    def setUp(self):
        self.client = self.FakeClient()
        crud.get_pool = lambda pool: self.client

    def test_get_column(self):
        col = cas_types.Column("eggs", "bacon", 123)
        self.client._set_column(col)
        self.assert_(crud.get_column(Key("cleese", "palin", "chapman"),
                                     "eggs", None) is col)

    def test_set_column(self):
        key = Key("cleese", "palin", "chapman")
        args = (key, "eggs", "bacon", 456, None)
        crud.set(*args)
        self.assert_(len(self.client._inserts) == 1)

    def test_get(self):
        col = cas_types.Column("eggs", "bacon", 123)
        self.client._set_column(col)
        self.assert_(crud.get(Key("cleese", "palin", "chapman"),
                                     "eggs", None) == "bacon")

    def test_set(self):
        key = Key("cleese", "palin", "chapman")
        args = (key, cas_types.Column("eggs", "bacon", 456), None)
        crud.set_column(*args)
        self.assert_(len(self.client._inserts) == 1)

    def test_remove(self):
        key = Key("cleese", "palin", "chapman")
        args = (key, "eggs", 456, None)
        crud.remove(*args)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_connection
# -*- coding: utf-8 -*-
#
# © 2009, 2010 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
# Author: Chris Goffinet <goffinet@digg.com>
#
"""Connection unit tests."""

from __future__ import with_statement
import unittest
import time
import types
import logging
import socket
from contextlib import contextmanager

from cassandra import Cassandra
from cassandra.ttypes import *
from thrift.transport.TTransport import TTransportException
from thrift import Thrift
from thrift.transport import TSocket

import lazyboy.connection as conn
from lazyboy.exceptions import *
from test_record import MockClient
from lazyboy.util import save, raises


class Generic(object):
    pass


class _MockTransport(object):

    def __init__(self, *args, **kwargs):
        self.calls = {'open': 0, 'close': 0}

    def open(self):
        self.calls['open'] += 1

    def close(self):
        self.calls['close'] += 1


class ConnectionTest(unittest.TestCase):

    def setUp(self):
        self.pool = 'testing'
        self._client = conn.Client
        conn.Client = MockClient
        conn._CLIENTS = {}
        conn._SERVERS = {self.pool: dict(servers=['localhost:1234'])}

    def tearDown(self):
        conn.Client = self._client


class TestPools(ConnectionTest):

    def test_add_pool(self):
        servers = ['localhost:1234', 'localhost:5678']
        conn.add_pool(__name__, servers)
        self.assert_(conn._SERVERS[__name__]["servers"] == servers)

    def test_get_pool(self):
        client = conn.get_pool(self.pool)
        self.assert_(type(client) is conn.Client)

        # Again, to cover the short-circuit conditional
        client = conn.get_pool(self.pool)
        self.assert_(type(client) is conn.Client)

        self.assertRaises(TypeError, conn.Client)

        self.assertRaises(ErrorCassandraClientNotFound,
                          conn.get_pool, (__name__))


class TestClient(ConnectionTest):

    def setUp(self):
        super(TestClient, self).setUp()
        self.client = MockClient(['localhost:1234', 'localhost:5678'])

    def test_init(self):
        pass

    def test_build_server(self):

        exc_classes = (InvalidRequestException, UnavailableException,
                       Thrift.TException)

        cls = Cassandra.Client
        srv = self.client._build_server(cls, 'localhost', 1234)
        self.assert_(isinstance(srv, Cassandra.Client))

        self.client._timeout = 250
        srv = self.client._build_server(cls, 'localhost', 1234)
        self.assert_(srv._iprot.trans._TBufferedTransport__trans._timeout ==
                     self.client._timeout * .001)
        self.assert_(isinstance(srv, Cassandra.Client))

        with save(conn.TSocket, ('TSocket',)):
            for exc_class in exc_classes:
                conn.TSocket.TSocket = raises(exc_class)
                self.assert_(self.client._build_server(cls, 'localhost', 1234)
                             is None)

    def test_get_server(self):
        # Zero clients
        real = self.client._clients
        bad = (None, [])
        for clts in bad:
            self.client._clients = clts
            self.assertRaises(ErrorCassandraNoServersConfigured,
                         self.client._get_server)

        # Round-robin
        fake = ['eggs', 'bacon', 'spam']
        self.client._clients = fake
        self.client._current_server = 0
        for exp in range(2 * len(fake)):
            srv = self.client._get_server()
            self.assert_(srv in fake)

    def test_list_servers(self):
        servers = self.client.list_servers()
        self.assert_(servers.__class__ == list)
        self.assert_(self.client._clients == servers)

    def test_connect(self):
        client = self.client._get_server()
        self.client._get_server = lambda: client

        # Already connected
        client.transport = _MockTransport()
        client.transport.isOpen = lambda: True
        self.assert_(self.client._connect())

        # Not connected, no error
        nopens = client.transport.calls['open']
        with save(client.transport, ('isOpen',)):
            client.transport.isOpen = lambda: False
            self.assert_(self.client._connect())
            self.assert_(client.transport.calls['open'] == nopens + 1)

        # Thrift Exception on connect - trapped
        ncloses = client.transport.calls['close']
        with save(client.transport, ('isOpen', 'open')):
            client.transport.isOpen = lambda: False
            client.transport.open = raises(TTransportException)
            self.assertRaises(ErrorThriftMessage, self.client._connect)
            self.assert_(client.transport.calls['close'] == ncloses +1)

        # Other exception on connect should be ignored
        with save(client.transport, ('isOpen', 'open')):
            client.transport.isOpen = lambda: False
            client.transport.open = raises(Exception)
            ncloses = client.transport.calls['close']
            self.assertRaises(Exception, self.client._connect)

        # Connection recycling - reuse same connection
        nopens = client.transport.calls['open']
        ncloses = client.transport.calls['close']
        conn = self.client._connect()
        self.client._recycle = 60
        client.connect_time = time.time()
        self.assert_(conn is self.client._connect())
        self.assert_(client.transport.calls['open'] == nopens)
        self.assert_(client.transport.calls['open'] == ncloses)

        # Recycling - reconnect
        nopens = client.transport.calls['open']
        ncloses = client.transport.calls['close']
        conn = self.client._connect()
        self.client._recycle = 60
        client.connect_time = 0
        self.assert_(conn is self.client._connect())
        self.assert_(client.transport.calls['open'] == nopens + 1)
        self.assert_(client.transport.calls['close'] == ncloses + 1)


    def test_methods(self):
        """Test the various client methods."""

        methods = filter(lambda m: m[0] != '_', dir(Cassandra.Iface))

        real_client = Generic()

        @contextmanager
        def get_client():
            yield real_client

        client = self._client(['127.0.0.1:9160'])
        client.get_client = get_client
        dummy = lambda *args, **kwargs: (True, args, kwargs)

        for method in methods:
            self.assert_(hasattr(client, method),
                         "Lazyboy client lacks interface method %s" % method)
            self.assert_(callable(getattr(client, method)))
            setattr(real_client, method, dummy)
            res = getattr(client, method)('cleese', gilliam="Terry")
            self.assert_(isinstance(res, tuple),
                         "%s method failed: %s" % (method, res))
            self.assert_(res[0] is True)
            self.assert_(res[1] == ('cleese',))
            self.assert_(res[2] == {'gilliam': "Terry"})

    def test_get_client(self):
        """Test get_client."""
        cass_client = Generic()
        raw_server = Generic()
        self.client._get_server = lambda: raw_server
        self.client._connect = lambda: raw_server
        self.client._servers = [raw_server]
        self.client._current_server = 0

        transport = _MockTransport()
        raw_server.transport = transport

        with self.client.get_client() as clt:
            self.assert_(clt is raw_server)

        # Socket error handling
        ncloses = transport.calls['close']
        try:
            with self.client.get_client() as clt:
                raise socket.error(7, "Test error")
            self.fail_("Exception not raised.")
        except ErrorThriftMessage, exc:
            self.assert_(transport.calls['close'] == ncloses + 1)
            self.assert_(exc.args[1] == "Test error")

        closed = []
        try:
            raw_server.transport = Generic()
            raw_server.transport.close = lambda: closed.append(True)
            with self.client.get_client() as clt:
                raise Thrift.TException("Cleese")
        except ErrorThriftMessage, exc:
            self.assert_(len(closed) == 1)
            self.assert_(exc.args[0] == "Cleese")

        closed = []
        try:
            raw_server.transport = Generic()
            raw_server.transport.close = lambda: closed.append(True)
            with self.client.get_client() as clt:
                raise Thrift.TException()
        except Exception, exc:
            self.assert_(len(closed) == 1)
            self.assert_(exc.args[0] != "")

        # Cassandra exceptions - no open/close, added info
        excs = ((NotFoundException, UnavailableException,
                 InvalidRequestException))
        for exc_ in excs:
            try:
                with self.client.get_client() as clt:
                    raise exc_("John Cleese")
                self.fail_("Exception gobbled.")
            except (exc_), ex:
                self.assert_(len(ex.args) > 1)
                server = self.client._servers[self.client._current_server]
                self.assert_(repr(server) in ex.args[-1])


class TestRetry(unittest.TestCase):

    """Test retry logic."""

    def test_retry_default_callback(self):
        """Make sure retry_default_callback works."""
        for x in range(conn.RETRY_ATTEMPTS):
            self.assert_(conn._retry_default_callback(x, None))

        self.assert_(not conn._retry_default_callback(x + 1, None))

    def test_retry(self):
        """Test retry."""
        retries = []
        def bad_func():
            retries.append(True)
            raise Exception("Whoops.")

        retry_func = conn.retry()(bad_func)
        self.assertRaises(Exception, retry_func)
        self.assert_(len(retries) == conn.RETRY_ATTEMPTS)


class DebugTraceClientTest(unittest.TestCase):

    """Test the DebugTraceClient."""

    def test_init(self):
        with save(conn.DebugTraceClient, ('__metaclass__',)):
            del conn.DebugTraceClient.__metaclass__
            logger = logging.getLogger("TestCase")
            client = conn.DebugTraceClient(None, slow_thresh=150,
                                           log=logger)
            self.assert_(isinstance(client, Cassandra.Client))
            self.assert_(hasattr(client, 'log'))
            self.assert_(isinstance(client.log, logging.Logger))
            self.assert_(client.log is logger)
            self.assert_(hasattr(client, '_slow_thresh'))
            self.assert_(client._slow_thresh == 150)


class DebugTraceFactoryTest(unittest.TestCase):

    """Test DebugTraceFactory."""

    def setUp(self):
        Cassandra.Iface.raises = raises(Exception)

    def tearDown(self):
        del Cassandra.Iface.raises

    def test_multiple_inherit_exception(self):
        """Make sure we get an exception in multi-inherit cases."""
        TypeA = type('TypeA', (), {})
        TypeB = type('TypeB', (), {})

        mcs = conn._DebugTraceFactory
        self.assertRaises(AssertionError, mcs.__new__,
                          mcs, 'TypeC', (TypeA, TypeB), {})

    def test_trace_factory(self):
        """Make sure the trace factory works as advertised."""

        class Tracer(Cassandra.Iface):
            """Dummy class for testing the tracer."""

            __metaclass__ = conn._DebugTraceFactory


        for name in dir(Tracer):
            if name.startswith('__'):
                continue

            self.assert_(getattr(Tracer, name) != getattr(Cassandra.Iface, name),
                         "Child class shares attr %s" % name)


        error, warn, debug = [], [], []

        fake_log = type('FakeLog', (logging.Logger, object),
                        {'__init__': lambda self: None,
                         'warn': lambda self, *args: warn.append(args),
                         'debug': lambda self, *args: debug.append(args),
                         'error': lambda self, *args: error.append(args)})

        tr = Tracer()
        tr._slow_thresh = 0
        tr.log = fake_log()
        tr.host, tr.port = '127.0.0.1', 1337

        tr.get_string_property("Foo")
        self.assert_(len(warn) == 1)

        tr._slow_thresh = 100
        tr.get_string_property("Foo")
        self.assert_(len(warn) == 1)
        self.assert_(len(debug) == 1)

        self.assertRaises(Exception, tr.raises)
        self.assert_(len(error) == 1)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_iterators
# -*- coding: utf-8 -*-
#
# © 2009, 2010 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#

"""Unit tests for lazyboy.iterators."""

import unittest
import types
import itertools as it

from lazyboy.key import Key
import lazyboy.exceptions as exc
import lazyboy.iterators as iterators
import cassandra.ttypes as ttypes
from test_record import MockClient

from cassandra.ttypes import ConsistencyLevel, Column, SuperColumn


class SliceIteratorTest(unittest.TestCase):

    """Test suite for lazyboy.iterators.slice_iterator."""

    def setUp(self):
        """Prepare the test fixture."""
        self.__get_pool = iterators.get_pool
        self.client = MockClient(['127.0.0.1:9160'])
        iterators.get_pool = lambda pool: self.client

    def tearDown(self):
        """Tear down the test fixture."""
        iterators.get_pool = self.__get_pool

    def test_slice_iterator(self):
        """Test slice_iterator."""

        key = Key(keyspace="eggs", column_family="bacon", key="tomato")
        slice_iterator = iterators.slice_iterator(key, ConsistencyLevel.ONE)
        self.assert_(isinstance(slice_iterator, types.GeneratorType))
        for col in slice_iterator:
            self.assert_(isinstance(col, ttypes.Column))

    def test_slice_iterator_error(self):

        class Client(object):

            def get_slice(*args, **kwargs):
                return None

        key = Key(keyspace="eggs", column_family="bacon", key="tomato")
        real_get_pool = iterators.get_pool
        try:
            iterators.get_pool = lambda pool: Client()
            self.assertRaises(exc.ErrorNoSuchRecord,
                              iterators.slice_iterator,
                              key, ConsistencyLevel.ONE)
        finally:
            iterators.get_pool = real_get_pool

    def test_slice_iterator_supercolumns(self):
        """Test slice_iterator with supercolumns."""
        key = Key(keyspace="eggs", column_family="bacon", key="tomato",
                  super_column="spam")

        cols = [bla.column for bla in self.client.get_slice()]
        scol = ttypes.SuperColumn(name="spam", columns=cols)
        corsc = ttypes.ColumnOrSuperColumn(super_column=scol)

        self.client.get_slice = lambda *args: [corsc]

        slice_iterator = iterators.slice_iterator(key, ConsistencyLevel.ONE)
        self.assert_(isinstance(slice_iterator, types.GeneratorType))
        for col in slice_iterator:
            self.assert_(isinstance(col, ttypes.SuperColumn))

    def test_multigetterator(self):
        """Test multigetterator."""
        keys = [Key("eggs", "bacon", "cleese"),
                Key("eggs", "bacon", "gilliam"),
                Key("eggs", "spam", "jones"),
                Key("eggs", "spam", "idle"),
                Key("tomato", "sausage", "chapman"),
                Key("tomato", "sausage", "palin")]

        def pack(cols):
            return list(iterators.pack(cols))

        data = {'eggs': # Keyspace
                {'bacon': # Column Family
                 {'cleese': pack([Column(name="john", value="cleese")]),
                  'gilliam': pack([Column(name="terry", value="gilliam")])},
                 'spam': # Column Family
                     {'jones': pack([Column(name="terry", value="jones")]),
                      'idle': pack([Column(name="eric", value="idle")])}},
                'tomato': # Keyspace
                {'sausage': # Column Family
                 {'chapman':
                      pack([SuperColumn(name="chap_scol", columns=[])]),
                  'palin':
                      pack([SuperColumn(name="pal_scol", columns=[])])}}}

        def multiget_slice(keyspace, keys, column_parent, predicate,
                           consistencylevel):
            return data[keyspace][column_parent.column_family]
        self.client.multiget_slice = multiget_slice

        res = iterators.multigetterator(keys, ConsistencyLevel.ONE)
        self.assert_(isinstance(res, dict))
        for (keyspace, col_fams) in res.iteritems():
            self.assert_(keyspace in res)
            self.assert_(isinstance(col_fams, dict))
            for (col_fam, rows) in col_fams.iteritems():
                self.assert_(col_fam in data[keyspace])
                self.assert_(isinstance(rows, dict))
                for (row_key, columns) in rows.iteritems():
                    self.assert_(row_key in data[keyspace][col_fam])
                    for column in columns:
                        if keyspace == 'tomato':
                            self.assert_(isinstance(column, SuperColumn))
                        else:
                            self.assert_(isinstance(column, Column))

    def test_sparse_get(self):
        """Test sparse_get."""
        key = Key(keyspace="eggs", column_family="bacon", key="tomato")

        getter = iterators.sparse_get(key, ['eggs', 'bacon'])
        self.assert_(isinstance(getter, types.GeneratorType))
        for col in getter:
            self.assert_(isinstance(col, ttypes.Column))

    def test_sparse_multiget(self):
        """Test sparse_multiget."""
        key = Key(keyspace="eggs", column_family="bacon", key="tomato")

        row_keys = ['cleese', 'jones', 'gilliam', 'chapman', 'idle', 'palin']

        keys = (key.clone(key=row_key) for row_key in row_keys)


        cols = self.client.get_slice()
        res = dict((row_key, cols) for row_key in row_keys)

        self.client.multiget_slice = lambda *args: res
        getter = iterators.sparse_multiget(keys, ['eggs', 'bacon'])
        for (row_key, cols) in getter.iteritems():
            self.assert_(isinstance(row_key, str))
            self.assert_(row_key in row_keys)
            self.assert_(isinstance(cols, list))
            for col in cols:
                self.assert_(isinstance(col, ttypes.Column))

    def test_key_range(self):
        """Test key_range."""
        key = Key(keyspace="eggs", column_family="bacon", key="tomato")
        keys = ['spam', 'eggs', 'sausage', 'tomato', 'spam']
        self.client.get_key_range = lambda *args: keys
        self.assert_(iterators.key_range(key) == keys)

    def test_key_range_iterator(self):
        """Test key_range_iterator."""
        key = Key(keyspace="eggs", column_family="bacon", key="tomato")
        keys = ['spam', 'eggs', 'sausage', 'tomato', 'spam']

        real_key_range = iterators.key_range
        iterators.key_range = lambda *args: keys
        try:
            key_iter = iterators.key_range_iterator(key)
            self.assert_(isinstance(key_iter, types.GeneratorType))
            for key in key_iter:
                self.assert_(isinstance(key, Key))
        finally:
            iterators.key_range = real_key_range

    def test_pack(self):
        """Test pack."""
        columns = self.client.get_slice()
        packed = iterators.pack(columns)
        self.assert_(isinstance(packed, types.GeneratorType))
        for obj in packed:
            self.assert_(isinstance(obj, ttypes.ColumnOrSuperColumn))

    def test_unpack(self):
        """Test unpack."""
        columns = self.client.get_slice()
        unpacked = iterators.unpack(columns)
        self.assert_(isinstance(unpacked, types.GeneratorType))

        for obj in unpacked:
            self.assert_(isinstance(obj, ttypes.Column))


class UtilTest(unittest.TestCase):

    """Test suite for iterator utilities."""

    def test_repeat_seq(self):
        """Test repeat_seq."""
        repeated = tuple(iterators.repeat_seq(range(10), 2))
        self.assert_(len(repeated) == 10)
        for (idx, elt) in enumerate(repeated):
            elt = tuple(elt)
            self.assert_(len(elt) == 2)
            for x in elt:
                self.assert_(x == idx)

    def test_repeat(self):
        """Test repeat."""
        repeated = tuple(iterators.repeat(range(10), 2))
        self.assert_(len(repeated) == 20)

        start = 0
        for x in range(10):
            self.assert_(repeated[start:start + 2] == (x, x))
            start += 2

    def test_chain_iterable(self):
        """Test chain_iterable."""
        chain = tuple(iterators.chain_iterable(
                (it.repeat(x, 10) for x in range(10))))
        self.assert_(len(chain) == 100)

        for x in range(10):
            self.assert_(chain[x * 10:x * 10 + 10] == tuple(it.repeat(x, 10)))

    def test_chunk_seq(self):
        """Test chunk_seq."""
        chunks = tuple(iterators.chunk_seq("abcdefghijklmnopqrstuvwxyz", 3))
        self.assert_(len(chunks) == 9)
        for chunk in chunks:
            self.assert_(len(chunk) >= 1 and len(chunk) <= 3)
            for elt in chunk:
                self.assert_(isinstance(elt, str))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_key
# -*- coding: utf-8 -*-
#
# Lazyboy: PrimaryKey unit tests
#
# © 2009 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#

import unittest

from cassandra.ttypes import ColumnPath

from lazyboy.key import Key
from lazyboy.exceptions import ErrorIncompleteKey


class KeyTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(KeyTest, self).__init__(*args, **kwargs)
        self.allowed = ({'keyspace': 'egg', 'column_family': 'sausage',
                         'key': 'bacon'},
                        {'keyspace': 'egg', 'column_family': 'sausage',
                         'key': 'bacon', 'super_column': 'tomato'})
        self.denied = ({'keyspace': 'egg', 'key': 'bacon'},
                       {'keyspace': 'egg', 'key': 'bacon',
                        'super_column': 'sausage'})

    def test_init(self):
        for args in self.allowed:
            pk = Key(**args)
            for k in args:
                self.assert_(getattr(pk, k) == args[k],
                             "Expected `%s', for key `%s', got `%s'" % \
                                 (args[k], k, getattr(pk, k)))

        for args in self.denied:
            self.assertRaises(ErrorIncompleteKey, Key, **args)

    def test_gen_uuid(self):
        key = Key(keyspace="eggs", column_family="bacon")
        self.assert_(type(key._gen_uuid()) == str)
        self.assert_(key._gen_uuid() != key._gen_uuid(),
                     "Unique IDs aren't very unique.")

    def test_super(self):
        self.assert_(not Key(keyspace='eggs', column_family='bacon',
                             key='sausage').is_super())
        self.assert_(Key(keyspace='eggs', column_family='bacon',
                             key='sausage', super_column='tomato').is_super())

    def test_str(self):
        x = Key(keyspace='eggs', key='spam', column_family='bacon').__str__()
        self.assert_(type(x) is str)

    def test_unicode(self):
        pk = Key(keyspace='eggs', key='spam', column_family='bacon')
        x = pk.__unicode__()
        self.assert_(type(x) is unicode)
        self.assert_(str(x) == str(pk))

    def test_repr(self):
        pk = Key(keyspace='eggs', key='spam', column_family='bacon')
        self.assert_(unicode(pk) == repr(pk))

    def test_get_path(self):
        base_key = dict(keyspace='eggs', key='spam', column_family='bacon')
        key = Key(**base_key)
        path = key.get_path()
        self.assert_(isinstance(path, ColumnPath))
        self.assert_(path.column_family == key.column_family)
        self.assert_(base_key['keyspace'] == key.keyspace)

        keey = key.clone()
        path2 = keey.get_path()
        self.assert_(path2 == path)

        path = key.get_path(column="foo")
        self.assert_(path.column == "foo")

    def test_clone(self):
        pk = Key(keyspace='eggs', key='spam', column_family='bacon')
        ppkk = pk.clone()
        self.assert_(isinstance(ppkk, Key))
        self.assert_(repr(pk) == repr(ppkk))
        for k in ('keyspace', 'key', 'column_family'):
            self.assert_(getattr(pk, k) == getattr(ppkk, k))

        # Changes override base keys, but don't change them.
        _pk = pk.clone(key='sausage')
        self.assert_(hasattr(_pk, 'keyspace'))
        self.assert_(hasattr(_pk, 'column_family'))
        self.assert_(hasattr(_pk, 'key'))

        self.assert_(_pk.key == 'sausage')
        self.assert_(pk.key == 'spam')
        _pk = pk.clone(super_column='tomato')
        self.assert_(_pk.super_column == 'tomato')
        self.assertRaises(AttributeError, _pk.__getattr__, 'sopdfj')
        self.assert_(hasattr(pk, 'key'))

        # Changes to the base propagate to cloned PKs.
        pk.keyspace = 'beans'
        self.assert_(_pk.keyspace == 'beans')

        __pk = _pk.clone()
        self.assert_(__pk.keyspace == 'beans')
        pk.keyspace = 'tomato'
        self.assert_(__pk.keyspace == 'tomato')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_record
# -*- coding: utf-8 -*-
#
# © 2009, 2010 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#
"""Record unit tests."""

from __future__ import with_statement
import time
import math
import uuid
import random
import types
import unittest

from cassandra.ttypes import Column, SuperColumn, ColumnOrSuperColumn, \
    ColumnParent

import lazyboy.record
from lazyboy.view import View
from lazyboy.connection import Client
from lazyboy.key import Key
from lazyboy.util import save
import lazyboy.exceptions as exc

Record = lazyboy.record.Record
MirroredRecord = lazyboy.record.MirroredRecord

from test_base import CassandraBaseTest


_last_cols = []
_inserts = []


class MockClient(Client):

    """A mock Cassandra client which returns canned responses"""

    def get_slice(self, *args, **kwargs):
        [_last_cols.pop() for i in range(len(_last_cols))]
        cols = []
        for i in range(random.randrange(1, 15)):
            cols.append(ColumnOrSuperColumn(
                    column=Column(name=uuid.uuid4().hex,
                                  value=uuid.uuid4().hex,
                                  timestamp=time.time())))
        _last_cols.extend(cols)
        return cols

    def batch_insert(self, keyspace, key, cfmap, consistency_level):
        _inserts.append(cfmap)
        return True

    def remove(self, keyspace, key, column_path, timestamp, consistency_level):
        return


class RecordTest(CassandraBaseTest):

    class Record(Record):
        _keyspace = 'sausage'
        _column_family = 'bacon'
        _required = ('eggs',)

    def __init__(self, *args, **kwargs):
        super(RecordTest, self).__init__(*args, **kwargs)
        self.class_ = self.Record

    def test_init(self):
        self.object = self._get_object({'id': 'eggs', 'title': 'bacon'})
        self.assert_(self.object['id'] == 'eggs')
        self.assert_(self.object['title'] == 'bacon')

    def test_make_key(self):
        """Test make_key."""
        key = self.object.make_key("eggs")
        self.assert_(isinstance(key, Key))
        self.assert_(key.key == "eggs")
        self.assert_(key.keyspace == self.object._keyspace)
        self.assert_(key.column_family == self.object._column_family)

    def test_default_key(self):
        self.assertRaises(exc.ErrorMissingKey, self.object.default_key)

    def test_set_key(self):
        self.object._keyspace = "spam"
        self.object._column_family = "bacon"
        self.object.set_key("eggs", "tomato")
        self.assert_(hasattr(self.object, 'key'))
        self.assert_(isinstance(self.object.key, Key))
        self.assert_(self.object.key.keyspace == "spam")
        self.assert_(self.object.key.column_family == "bacon")
        self.assert_(self.object.key.key == "eggs")
        self.assert_(self.object.key.super_column == "tomato")

    def test_get_indexes(self):
        self.object._indexes = ({}, {})
        self.assert_(tuple(self.object.get_indexes()) == ({}, {}))

    def test_valid(self):
        self.assert_(not self.object.valid())
        self.object['eggs'] = 'sausage'
        self.assert_(self.object.valid())

    def test_missing(self):
        self.object._clean()
        self.assert_(self.object.missing() == self.object._required)
        self.object['eggs'] = 'sausage'
        self.assert_(self.object.missing() == ())

    def test_clean(self):
        data = {'id': 'eggs', 'title': 'bacon'}
        self.object = self._get_object(data)
        for k in data:
            self.assert_(k in self.object, "Key %s was not set?!" % (k,))
            self.assert_(self.object[k] == data[k])

        self.object._clean()
        for k in data:
            self.assert_(not k in self.object)

    def test_sanitize(self):
        self.assert_(isinstance(self.object.sanitize(u'ÜNICÖDE'), str))

    def test_repr(self):
        self.assert_(isinstance(repr(self.object), str))

    def test_update(self):
        data = {'id': 'eggs', 'title': 'bacon'}
        self.object.update(data)
        for k in data:
            self.assert_(self.object[k] == data[k])

        self.object._clean()
        self.object.update(data.items())
        for k in data:
            self.assert_(self.object[k] == data[k])

        self.object._clean()
        self.object.update(**data)
        for k in data:
            self.assert_(self.object[k] == data[k])

    def test_setitem_getitem(self):
        data = {'id': 'eggs', 'title': 'bacon'}
        self.assertRaises(exc.ErrorInvalidValue, self.object.__setitem__,
                          "eggs", None)
        for k in data:
            self.object[k] = data[k]
            self.assert_(self.object[k] == data[k],
                         "Data not set in Record")
            self.assert_(k in self.object._columns,
                         "Data not set in Record.columns")
            self.assert_(self.object._columns[k].__class__ is Column,
                         "Record._columns[%s] is %s, not Column" % \
                             (type(self.object._columns[k]), k))
            self.assert_(self.object._columns[k].value == data[k],
                         "Value mismatch in Column, got `%s', expected `%s'" \
                             % (self.object._columns[k].value, data[k]))
            now = self.object.timestamp()
            self.assert_(self.object._columns[k].timestamp <= now,
                         "Expected timestamp <= %s, got %s" \
                             % (now, self.object._columns[k].timestamp))

            self.assert_(k not in self.object._deleted,
                         "Key was marked as deleted.")
            self.assert_(k in self.object._modified,
                         "Key not in modified list")

            del self.object[k]
            self.object[k] = data[k]
            self.assert_(k not in self.object._deleted)

        # Make sure setting an identical original value doesn't change
        self.object._inject(
            self.object.key,
            {"eggs": Column(name="eggs", value="bacon", timestamp=0)})
        self.assert_(self.object["eggs"] == "bacon")
        self.assert_(self.object._original["eggs"].timestamp == 0)
        self.object["eggs"] = "bacon"
        self.assert_(self.object._original["eggs"].timestamp == 0)

    def test_delitem(self):
        data = {'id': 'eggs', 'title': 'bacon'}
        for k in data:
            self.object[k] = data[k]
            self.assert_(self.object[k] == data[k],
                         "Data not set in Record")
            self.assert_(k not in self.object._deleted,
                         "Key was marked as deleted.")
            self.assert_(k in self.object._modified,
                         "Key not in modified list")
            del self.object[k]
            self.assert_(k not in self.object, "Key was not deleted.")
            self.assert_(k in self.object._deleted,
                         "Key was not marked as deleted.")
            self.assert_(k not in self.object._modified,
                         "Deleted key in modified list")
            self.assert_(k not in self.object._columns,
                         "Column was not deleted.")

    def get_mock_cassandra(self, keyspace=None):
        """Return a mock cassandra instance"""
        mock = None
        if not mock:
            mock = MockClient(['localhost:1234'])
        return mock

    def test_load(self):
        test_data = (Column(name="eggs", value="1"),
                     Column(name="bacon", value="2"),
                     Column(name="spam", value="3"))

        real_slice = lazyboy.record.iterators.slice_iterator
        try:
            lazyboy.record.iterators.slice_iterator = lambda *args: test_data

            key = Key(keyspace='eggs', column_family='bacon', key='tomato')
            self.object.make_key = lambda *args, **kwargs: key
            self.object.load('tomato')
            self.assert_(self.object.key is key)

            key = Key(keyspace='eggs', column_family='bacon', key='tomato')
            self.object.load(key)

        finally:
            lazyboy.record.iterators.slice_iterator = real_slice

        self.assert_(self.object.key is key)
        cols = dict([[column.name, column] for column in test_data])
        self.assert_(self.object._original == cols)

        for col in cols.values():
            self.assert_(self.object[col.name] == col.value)
            self.assert_(self.object._columns[col.name] == col)

    def test_get_batch_args(self):
        columns = (Column(name="eggs", value="1"),
                   Column(name="bacon", value="2"),
                   Column(name="sausage", value="3"))
        column_names = [col.name for col in columns]

        data = {'eggs': "1", 'bacon': "2", 'sausage': "3"}
        key = Key(keyspace='eggs', column_family='bacon', key='tomato')

        args = self.object._get_batch_args(key, columns)

        # Make sure the key is correct
        self.assert_(args[0] is key.keyspace)
        self.assert_(args[1] is key.key)
        self.assert_(isinstance(args[2], dict))
        keys = args[2].keys()
        self.assert_(len(keys) == 1)
        self.assert_(keys[0] == key.column_family)
        self.assert_(not isinstance(args[2][key.column_family],
                                    types.GeneratorType))
        for val in args[2][key.column_family]:
            self.assert_(isinstance(val, ColumnOrSuperColumn))
            self.assert_(val.column in columns)
            self.assert_(val.super_column is None)

        key.super_column = "spam"
        args = self.object._get_batch_args(key, columns)
        self.assert_(args[0] is key.keyspace)
        self.assert_(args[1] is key.key)
        self.assert_(isinstance(args[2], dict))

        keys = args[2].keys()
        self.assert_(len(keys) == 1)
        self.assert_(keys[0] == key.column_family)
        self.assert_(not isinstance(args[2][key.column_family],
                                    types.GeneratorType))
        for val in args[2][key.column_family]:
            self.assert_(isinstance(val, ColumnOrSuperColumn))
            self.assert_(val.column is None)
            self.assert_(isinstance(val.super_column, SuperColumn))
            self.assert_(val.super_column.name is key.super_column)
            self.assert_(hasattr(val.super_column.columns, '__iter__'))
            for col in val.super_column.columns:
                self.assert_(col.name in data.keys())
                self.assert_(col.value == data[col.name])

    def test_remove(self):
        data = {'eggs': "1", 'bacon': "2", 'sausage': "3"}
        self.object.update(data)
        self.object.key = Key("eggs", "bacon", "tomato")
        self.object._get_cas = self.get_mock_cassandra
        self.assert_(self.object.remove() is self.object)
        self.assert_(not self.object.is_modified())
        for (key, val) in data.iteritems():
            self.assert_(key not in self.object)

    def test_save(self):
        self.assertRaises(exc.ErrorMissingField, self.object.save)
        data = {'eggs': "1", 'bacon': "2", 'sausage': "3"}
        self.object.update(data)

        self.assertRaises(exc.ErrorMissingKey, self.object.save)

        key = Key(keyspace='eggs', column_family='bacon', key='tomato')
        self.object.key = key
        self.object._get_cas = self.get_mock_cassandra
        del self.object['bacon']
        # FIXME – This doesn't really work, in the sense that
        # self.fail() is never called, but it still triggers an error
        # which makes the test fail, due to incorrect arity in the
        # arguments to the lambda.
        MockClient.remove = lambda self, a, b, c, d, e: None
        self.object.load = lambda self: None

        res = self.object.save()
        self.assert_(res == self.object,
                     "Self not returned from Record.save")
        cfmap = _inserts[-1]
        self.assert_(isinstance(cfmap, dict))

        self.assert_(self.object.key.column_family in cfmap,
                     "PK family %s not in cfmap" %
                     (self.object.key.column_family,))

        for corsc in cfmap[self.object.key.column_family]:
            self.assert_(corsc.__class__ == ColumnOrSuperColumn)
            self.assert_(corsc.column and not corsc.super_column)
            col = corsc.column

            self.assert_(col.name in data,
                         "Column %s wasn't set from update()" % \
                             (col.name))
            self.assert_(data[col.name] == col.value,
                         "Value of column %s is wrong, %s ≠ %s" % \
                             (col.name, data[col.name], col.value))
            self.assert_(col == self.object._columns[col.name],
                         "Column from cf._columns wasn't used in mutation_t")

            self.assert_(
                self.object._original['eggs']
                is not self.object._columns['eggs'],
                "Internal state corrupted on save.")

    def test_save_index(self):

        class FakeView(object):

            def __init__(self):
                self.records = []

            def append(self, record):
                self.records.append(record)

        views = [FakeView(), FakeView()]
        saves = []
        self.object.get_indexes = lambda: views
        self.object._save_internal = lambda *args: saves.append(True)

        data = {'eggs': "1", 'bacon': "2", 'sausage': "3"}
        self.object.update(data)
        self.object._keyspace = "cleese"
        self.object._column_family = "gilliam"
        self.object.set_key("blah")
        self.object.save()
        for view in views:
            self.assert_(self.object in view.records)

    def test_save_mirror(self):

        class FakeMirror(object):

            def __init__(self):
                self.records = []

            def mirror_key(self, parent_record):
                self.records.append(parent_record)
                return parent_record.key.clone(column_family="mirror")

        mirrors = [FakeMirror(), FakeMirror()]
        saves = []
        self.object.get_mirrors = lambda: mirrors
        self.object._save_internal = lambda *args: saves.append(True)

        data = {'eggs': "1", 'bacon': "2", 'sausage': "3"}
        self.object.update(data)
        self.object._keyspace = "cleese"
        self.object._column_family = "gilliam"
        self.object.set_key("blah")
        self.object.save()
        for mirror in mirrors:
            self.assert_(self.object in mirror.records)

    def test_save_mirror_failure(self):
        data = {'eggs': "1", 'bacon': "2", 'sausage': "3"}
        saves = []
        self.object._save_internal = lambda *args: saves.append(True)
        self.object._keyspace = "cleese"
        self.object._column_family = "gilliam"
        self.object.set_key("blah")

        class BrokenMirror(object):

            def mirror_key(self, parent_record):
                raise Exception("Testing")

        class BrokenView(object):

            def mirror_key(self, parent_record):
                raise Exception("Testing")

        class FakeView(object):

            def __init__(self):
                self.records = []

            def append(self, record):
                self.records.append(record)

        # Make sure a broken mirror doesn't break the record or views.
        mirrors = [BrokenMirror(), BrokenMirror()]
        self.object.get_mirrors = lambda: mirrors

        self.assert_(not self.object.is_modified())
        self.object.update(data)
        self.assert_(self.object.is_modified())

        views = [FakeView()]
        self.object.get_indexes = lambda: views
        self.assertRaises(Exception, self.object.save)
        for view in views:
            self.assert_(self.object in view.records)

        self.assertRaises(Exception, self.object.save)

        not self.assert_(not self.object.is_modified())

        self.object.update(data)
        views = [FakeView()]
        self.object.get_indexes = lambda: views
        self.assertRaises(Exception, self.object.save)
        self.assert_(not self.object.is_modified())
        for view in views:
            self.assert_(self.object in view.records)

        views = [BrokenView()]
        self.object.get_indexes = lambda: views
        self.object.update(data)
        self.assertRaises(Exception, self.object.save)
        self.assert_(not self.object.is_modified())

    def test_revert(self):
        data = {'id': 'eggs', 'title': 'bacon'}
        for k in data:
            self.object._original[k] = Column(name=k, value=data[k])

        self.object.revert()

        for k in data:
            self.assert_(self.object[k] == data[k])

    def test_is_modified(self):
        data = {'id': 'eggs', 'title': 'bacon'}

        self.assert_(not self.object.is_modified(),
                     "Untouched instance is marked modified.")

        self.object.update(data)
        self.assert_(self.object.is_modified(),
                     "Altered instance is not modified.")

    def test_timestamp(self):
        """Test Record.timestamp."""
        tstamp = self.object.timestamp()
        self.assert_(isinstance(tstamp, int))
        tstamp_2 = self.object.timestamp()
        self.assert_(tstamp_2 >= tstamp)

        self.assert_(abs(self.object.timestamp() - time.time()) <= 2)

    def test_remove_key(self):
        """Test remove_key."""
        client = MockClient(['localhost:1234'])
        key = Key("123", "456")
        with save(lazyboy.record, ('get_pool',)):
            lazyboy.record.get_pool = lambda keyspace: client
            Record.remove_key(key)

    def test_modified_reference(self):
        """Make sure original column values don't change."""
        rec = Record()._inject(Key('foo', 'bar', 'baz'),
                               (Column("username", "whaddup"),))
        orig = rec['username']
        rec['username'] = "jcleese"
        self.assert_(rec._original['username'].value == orig)


class MirroredRecordTest(unittest.TestCase):

    """Tests for MirroredRecord"""

    def setUp(self):
        self.object = MirroredRecord()

    def test_mirror_key(self):
        self.assertRaises(exc.ErrorMissingKey, self.object.mirror_key,
                          self.object)

    def test_save(self):
        self.assertRaises(exc.ErrorImmutable, self.object.save)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_recordset
# -*- coding: utf-8 -*-
#
# © 2009 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#
"""Unit tests for Lazyboy recordset module."""

import unittest
import uuid
from random import randrange, sample
from operator import attrgetter
from functools import partial

from test_base import CassandraBaseTest
from test_record import MockClient, _last_cols, _inserts

from cassandra.ttypes import ColumnOrSuperColumn

from lazyboy.key import Key
from lazyboy.record import Record
import lazyboy.recordset as sets
#import valid, missing, modified, RecordSet, KeyRecordSet
from lazyboy.exceptions import ErrorMissingKey, ErrorMissingField


def rand_set(records):
    return sample(records, randrange(1, len(records)))


class TestFunctions(unittest.TestCase):

    """Unit tests for record utility functions."""

    def setUp(self):
        """Prepare the test environment."""
        num_records = 15
        keys = [Key(keyspace='spam', column_family='bacon')
                for x in range(num_records)]

        records = []
        for key in keys:
            r = Record()
            r.key = key
            records.append(r)

        self.records = records

    def test_valid(self):
        """Test lazyboy.recordset.valid."""
        self.assert_(sets.valid(self.records))
        invalid = rand_set(self.records)
        for record in invalid:
            record.valid = lambda: False

        self.assert_(not sets.valid(invalid))
        self.assert_(not sets.valid(self.records))

    def test_missing(self):
        """Test lazyboy.recordset.missing."""
        self.assert_(not sets.missing(self.records))
        records = rand_set(self.records)
        for record in records:
            record.missing = lambda: ('eggs', 'bacon')

        self.assert_(sets.missing(records))
        self.assert_(sets.missing(self.records))

    def test_modified(self):
        """Test lazyboy.recordset.modified."""
        self.assert_(not sets.modified(self.records))
        records = rand_set(self.records)
        for record in records:
            record.is_modified = lambda: True

        self.assert_(sets.modified(records))
        self.assert_(tuple(sets.modified(records)) == tuple(records))
        self.assert_(sets.modified(self.records))


class TestRecordSet(unittest.TestCase):
    """Unit tests for lazyboy.recordset.RecordSet."""

    def setUp(self):
        """Prepare the test object."""
        self.object = sets.RecordSet()

    def _get_records(self, count, **kwargs):
        """Return records for testing."""
        records = []
        for n in range(count):
            record = Record()

            if kwargs:
                record.key = Key(**kwargs)
            records.append(record)

        return records

    def test_transform(self):
        """Make sure RecordSet._transoform() works correctly."""
        self.assert_(self.object._transform([]) == {})
        records = self._get_records(5, keyspace="eggs", column_family="bacon")
        out = self.object._transform(records)
        self.assert_(len(out) == len(records))
        for record in records:
            self.assert_(record.key.key in out)
            self.assert_(out[record.key.key] is record)

        for key in out:
            self.assert_(key == out[key].key.key)

    def test_init(self):
        """Make sure the object can be constructed."""
        records = self._get_records(5, keyspace="eggs", column_family="bacon")
        rs = sets.RecordSet(records)

    def test_basic(self):
        """Make sure basic functionality works."""
        records = self._get_records(5, keyspace="eggs", column_family="bacon")
        rs = sets.RecordSet(records)
        self.assert_(len(rs) == len(records))
        self.assert_(rs.values() == records)
        self.assert_(set(rs.keys()) == set(record.key.key
                                           for record in records))

    def test_append(self):
        """Make sure RecordSet.append() works."""
        records = self._get_records(5, keyspace="eggs", column_family="bacon")
        for record in records:
            self.object.append(record)
            self.assert_(record.key.key in self.object)
            self.assert_(self.object[record.key.key] is record)

        self.assert_(self.object.values() == records)

    def test_save_failures(self):
        """Make sure RecordSet.save() aborts if there are invalid records."""

        records = self._get_records(5, keyspace="eggs", column_family="bacon")

        for record in records:
            record.is_modified = lambda: True
            record.valid = lambda: False
            self.object.append(record)

        self.assertRaises(ErrorMissingField, self.object.save)

    def test_save(self):
        """Make sure RecordSet.save() works."""

        class FakeRecord(object):

            class Key(object):
                pass

            def __init__(self):
                self.saved = False
                self.key = self.Key()
                self.key.key = str(uuid.uuid4())

            def save(self, consistency=None):
                self.saved = True
                return self

            def is_modified(self):
                return True

            def valid(self):
                return True


        records = [FakeRecord() for x in range(10)]
        map(self.object.append, records)
        self.object.save()
        for record in records:
            self.assert_(record.saved)
            self.assert_(self.object[record.key.key] is record)


class KeyRecordSetTest(unittest.TestCase):

    def setUp(self):
        self.object = sets.KeyRecordSet()

    def test_batch_load(self):
        records, keys = [], []
        for x in range(10):
            record = Record()
            record.key = Key('eggs', 'bacon')
            record['number'] = x
            record['square'] = x * x
            records.append(record)
            keys.append(record.key)

        backing = {}
        for record in records:
            backing[record.key.key] = [ColumnOrSuperColumn(col)
                                       for col in record._columns.values()]

        mock_client = MockClient([])
        mock_client.multiget_slice = \
            lambda ks, keys, parent, pred, clvl: backing
        sets.itr.get_pool = lambda ks: mock_client

        out_records = self.object._batch_load(Record, keys)
        for record in out_records:
            self.assert_(isinstance(record, Record))
            self.assert_(record.key in keys)
            orig = records[records.index(record)]
            self.assert_(orig['number'] == record['number'])
            self.assert_(orig['square'] == record['square'])

    def test_init(self):
        """Make sure KeyRecordSet.__init__ works as expected"""
        fake_key = partial(Key, "Eggs", "Bacon")
        keys = [fake_key(str(uuid.uuid1())) for x in range(10)]
        rs = sets.KeyRecordSet(keys, Record)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_view
# -*- coding: utf-8 -*-
#
# © 2009, 2010 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#
"""Unit tests for Lazyboy views."""

import unittest
import uuid
import types
from itertools import islice

from cassandra.ttypes import Column, ColumnOrSuperColumn

import lazyboy.view as view
from lazyboy.key import Key
from lazyboy.iterators import pack, unpack
from lazyboy.record import Record
from test_record import MockClient


class IterTimeTest(unittest.TestCase):

    """Test lazyboy.view time iteration functions."""

    def test_iter_time(self):
        """Test _iter_time."""
        iterator = view._iter_time(days=1)
        first = 0
        for x in range(10):
            val = iterator.next()
            self.assert_(val > first)

    def test_test_iter_days(self):
        """Test _iter_days."""
        iterator = view._iter_days()
        first = "19000101"
        for x in range(10):
            val = iterator.next()
            self.assert_(val > first)


class ViewTest(unittest.TestCase):
    """Unit tests for Lazyboy views."""

    def setUp(self):
        """Prepare the text fixture."""
        obj = view.View()
        obj.key = Key(keyspace='eggs', column_family='bacon',
                      key='dummy_view')
        obj.record_key = Key(keyspace='spam', column_family='tomato')
        self.client = MockClient(['localhost:1234'])
        obj._get_cas = lambda: self.client
        self.object = obj

    def test_repr(self):
        """Test view.__repr__."""
        self.assert_(isinstance(repr(self.object), str))

    def test_len(self):
        """Test View.__len__."""
        self.client.get_count = lambda *args: 99
        self.object.key = Key("Eggs", "Bacon")
        self.assert_(len(self.object) == 99)

    def test_keys_types(self):
        """Ensure that View._keys() returns the correct type & keys."""
        view = self.object
        keys = view._keys()
        self.assert_(hasattr(keys, '__iter__'))
        for key in tuple(keys):
            self.assert_(isinstance(key, Key))
            self.assert_(key.keyspace == view.record_key.keyspace)
            self.assert_(key.column_family == view.record_key.column_family)

        view._keys("foo", "bar")

    def __base_view_test(self, view, ncols, chunk_size):
        """Base test for View._keys iteration."""
        cols = map(ColumnOrSuperColumn,
                   [Column(name=x, value=x)
                    for x in range(ncols)])

        def get_slice(instance, keyspace, key, parent, predicate, level):
            try:
                start = int(predicate.slice_range.start)
            except ValueError:
                start = 0
            count = int(predicate.slice_range.count)
            return cols[start:start + count]

        view.chunk_size = chunk_size
        MockClient.get_slice = get_slice
        keys = tuple(view._keys())
        self.assert_(len(keys) == len(cols),
                     "Got %s keys instead of of %s" %
                     (len(keys), len(cols)))

        self.assert_(len(set(keys)) == len(keys),
                     "Duplicates present in output")

    def test_empty_view(self):
        """Make sure empty views work correctly."""
        self.__base_view_test(self.object, 0, 10)

    def test_view_even(self):
        """Make sure iteration works across boundaries ending on the
        chunk size."""
        self.__base_view_test(self.object, 100, 10)
        self.__base_view_test(self.object, 100, 100)
        self.__base_view_test(self.object, 10, 9)
        self.__base_view_test(self.object, 9, 10)

    def test_view_odd(self):
        """Make sure iteration works with an odd chunk_size resulting
        in a remainder."""
        self.__base_view_test(self.object, 100, 7)

    def test_iter(self):
        """Test View.__iter__()"""

        class FakeKey(Key):
            pass

        class FakeRecord(Record):

            def load(self, key):
                assert isinstance(key, FakeKey)
                self.key = key
                return self


        view_ = self.object
        view_.record_class = FakeRecord
        keys = [FakeKey(keyspace="eggs", column_family="bacon", key=x)
                              for x in range(10)]
        view_._keys = lambda: keys

        for record in view_:
            self.assert_(isinstance(record, FakeRecord))
            self.assert_(isinstance(record.key, FakeKey))
            self.assert_(record.key in keys)

    def test_append(self):
        view = self.object
        MockClient.insert = \
            lambda conn, keyspace, key, path, value, time, x: True
        rec = Record()
        rec.key = Key(keyspace="eggs", column_family="bacon", key="tomato")
        self.object.append(rec)


class FaultTolerantViewTest(unittest.TestCase):

    """Test suite for lazyboy.view.FaultTolerantView."""

    def test_iter(self):
        """Make sure FaultTolerantView.__iter__ ignores load errors."""

        class IntermittentFailureRecord(object):

            def load(self, key):
                if key % 2 == 0:
                    raise Exception("Failed to load")
                self.key = key
                return self

        ftv = view.FaultTolerantView()

        client = MockClient(['localhost:1234'])
        client.get_count = lambda *args: 99
        ftv._get_cas = lambda: client

        ftv.record_class = IntermittentFailureRecord
        ftv._keys = lambda: range(10)
        res = tuple(ftv)
        self.assert_(len(res) == 5)
        for record in res:
            self.assert_(record.key % 2 != 0)


class BatchLoadingViewTest(unittest.TestCase):

    """Test lazyboy.view.BatchLoadingView."""

    def test_init(self):
        self.object = view.BatchLoadingView()
        self.assert_(hasattr(self.object, 'chunk_size'))
        self.assert_(isinstance(self.object.chunk_size, int))

    def test_iter(self):
        mg = view.multigetterator

        self.object = view.BatchLoadingView(None, Key("Eggs", "Bacon"))
        # self.object._keys = lambda: [Key("Eggs", "Bacon", x)
        #                              for x in range(25)]
        self.object._cols = lambda start=None, end=None: \
            [Column("name:%s" % x, "val:%s" % x) for x in range(25)]

        columns = [Column(x, x * x) for x in range(10)]
        data = {'Digg': {'Users': {}}}
        for key in self.object._keys():
            data['Digg']['Users'][key] = iter(columns)

        try:
            view.multigetterator = lambda *args, **kwargs: data
            self.assert_(isinstance(self.object.__iter__(),
                                    types.GeneratorType))

            for record in self.object:
                self.assert_(isinstance(record, Record))
                self.assert_(hasattr(record, 'key'))
                self.assert_(record.key.keyspace == "Digg")
                self.assert_(record.key.column_family == "Users")
                self.assert_(record.key.key in self.object.keys())
                for x in range(10):
                    self.assert_(x in record)
                    self.assert_(record[x] == x * x)

        finally:
            view.multigetterator = mg


class PartitionedViewTest(unittest.TestCase):

    """Test lazyboy.view.PartitionedView."""

    view_class = view.PartitionedView

    def setUp(self):
        """Prepare the text fixture."""
        obj = view.PartitionedView()
        obj.view_key = Key(keyspace='eggs', column_family='bacon',
                      key='dummy_view')
        obj.view_class = view.View
        self.object = obj

    def test_partition_keys(self):
        """Test PartitionedView.partition_keys."""
        keys = self.object.partition_keys()
        self.assert_(isinstance(keys, list) or
                     isinstance(keys, tuple) or
                     isinstance(keys, types.GeneratorType))

    def test_get_view(self):
        """Test PartitionedView._get_view."""
        partition = self.object._get_view(self.object.view_key)
        self.assert_(isinstance(partition, self.object.view_class))

    def test_iter(self):
        """Test PartitionedView.__iter__."""
        keys = ['eggs', 'bacon', 'tomato', 'sausage', 'spam']
        self.object.partition_keys = lambda: keys
        self.object._get_view = lambda key: [key]
        gen = self.object.__iter__()
        for record in gen:
            self.assert_(record in keys)

    def test_append_view(self):
        """Test PartitionedView._append_view."""
        record = Record()
        self.object._get_view = lambda key: key
        data = (('one', 'two'),
                ['one', 'two'],
                iter(('one', 'two')))

        for data_set in data:
            self.object.partition_keys = lambda: data_set
            self.assert_(self.object._append_view(record) == "one")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
#
# © 2009, 2010 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#

"""Utility functions."""

from __future__ import with_statement
from contextlib import contextmanager
import logging


def raise_(exc=None, *args, **kwargs):
    """Raise an exception."""
    raise (exc or Exception)(*args, **kwargs)


def raises(exc=None, *args, **kwargs):
    """Return a function which raises an exception when called."""

    def __inner__(*func_args, **func_kwargs):
        """Raise the exception."""
        raise_(exc, *args, **kwargs)
    return __inner__


@contextmanager
def save(obj, attrs=None):
    """Save attributes of an object, then restore them."""
    orig_attrs = {}
    for attr in attrs:
        orig_attrs[attr] = getattr(obj, attr)

    try:
        yield
    finally:
        for attr in attrs:
            try:
                setattr(obj, attr, orig_attrs[attr])
            except Exception:
                pass


def returns(value):
    """Return a function which returns a value, ignoring arguments."""

    def __return_inner(*args, **kwargs):
        """Return value."""
        return value

    return __return_inner


@contextmanager
def suppress(*args):
    """Run code while suppressing exceptions in args."""
    try:
        yield
    except args, exc:
        logging.warn("Suppressing: %s %s", type(exc), exc)

########NEW FILE########
__FILENAME__ = view
# -*- coding: utf-8 -*-
#
# © 2009, 2010 Digg, Inc. All rights reserved.
# Author: Ian Eure <ian@digg.com>
#
"""Lazyboy: Views."""

import datetime
import uuid
import traceback
from itertools import islice

from cassandra.ttypes import SlicePredicate, SliceRange, Column

from lazyboy.key import Key
from lazyboy.base import CassandraBase
from lazyboy.iterators import multigetterator, unpack, chunk_seq
from lazyboy.record import Record
from lazyboy.connection import Client


def _iter_time(start=None, **kwargs):
    """Return a sequence which iterates time."""
    day = start or datetime.datetime.today()
    intv = datetime.timedelta(**kwargs)
    while day.year >= 1900:
        yield day.strftime('%Y%m%d')
        day = day - intv


def _iter_days(start=None):
    """Return a sequence which iterates over time one day at a time."""
    return _iter_time(start, days=1)


class View(CassandraBase):

    """A regular view."""

    def __init__(self, view_key=None, record_key=None, record_class=None,
                 start_col=None, exclusive=False):
        assert not view_key or isinstance(view_key, Key)
        assert not record_key or isinstance(record_key, Key)
        assert not record_class or isinstance(record_class, type)

        CassandraBase.__init__(self)

        self.chunk_size = 100
        self.key = view_key
        self.record_key = record_key
        self.record_class = record_class or Record
        self.reversed = False
        self.last_col = None
        self.start_col = start_col
        self.exclusive = exclusive

    def __repr__(self):
        return "%s: %s" % (self.__class__.__name__, self.key)

    def __len__(self):
        """Return the number of records in this view."""
        return self._get_cas().get_count(
            self.key.keyspace, self.key.key, self.key, self.consistency)

    def _cols(self, start_col=None, end_col=None):
        """Yield columns in the view."""
        client = self._get_cas()
        assert isinstance(client, Client), \
            "Incorrect client instance: %s" % client.__class__
        last_col = start_col or self.start_col or ""
        end_col = end_col or ""
        chunk_size = self.chunk_size
        passes = 0
        while True:
            # When you give Cassandra a start key, it's included in the
            # results. We want it in the first pass, but subsequent iterations
            # need to the count adjusted and the first record dropped.
            fudge = 1 if self.exclusive else int(passes > 0)

            cols = client.get_slice(
                self.key.keyspace, self.key.key, self.key,
                SlicePredicate(slice_range=SliceRange(
                        last_col, end_col, self.reversed, chunk_size + fudge)),
                self.consistency)

            if len(cols) == 0:
                raise StopIteration()

            for col in unpack(cols[fudge:]):
                yield col
                last_col = col.name

            passes += 1

            if len(cols) < self.chunk_size:
                raise StopIteration()

    def _keys(self, start_col=None, end_col=None):
        """Yield keys in this view"""
        return (self.make_key(col) for col in self._cols(start_col, end_col))

    def make_key(self, column):
        """Make a record key for a column."""
        assert isinstance(column, Column)
        return self.record_key.clone(key=column.value)

    def __iter__(self):
        """Iterate over all objects in this view."""
        for (key, col) in ((self.make_key(col), col) for col in self._cols()):
            self.last_col = col
            yield self.record_class().load(key)

    def _record_key(self, record=None):
        """Return the column name for a given record."""
        return record.key.key if record else str(uuid.uuid1())

    def append(self, record):
        """Append a record to a view"""
        assert isinstance(record, Record), \
            "Can't append non-record type %s to view %s" % \
            (record.__class__, self.__class__)
        self._get_cas().insert(
            self.key.keyspace, self.key.key,
            self.key.get_path(column=self._record_key(record)),
            record.key.key, record.timestamp(), self.consistency)

    def remove(self, record):
        """Remove a record from a view"""
        assert isinstance(record, Record), \
            "Can't remove non-record type %s to view %s" % \
            (record.__class__, self.__class__)
        self._get_cas().remove(
            self.key.keyspace, self.key.key,
            self.key.get_path(column=self._record_key(record)),
            record.timestamp(), self.consistency)


class FaultTolerantView(View):

    """A view which ignores missing keys."""

    def __iter__(self):
        """Iterate over all objects in this view, ignoring bad keys."""
        for key in self._keys():
            try:
                yield self.record_class().load(key)
            except GeneratorExit:
                raise
            except Exception:
                pass


class BatchLoadingView(View):

    """A view which loads records in bulk."""

    def __init__(self, view_key=None, record_key=None, record_class=None,
                 start_col=None, exclusive=False):
        """Initialize the view, setting the chunk_size to a large value."""
        View.__init__(self, view_key, record_key, record_class, start_col,
                      exclusive)
        self.chunk_size = 5000

    def __iter__(self):
        """Batch load and iterate over all objects in this view."""
        all_cols = self._cols()

        cols = [True]
        fetched = 0
        while len(cols) > 0:
            cols = tuple(islice(all_cols, self.chunk_size))
            fetched += len(cols)
            keys = tuple(self.make_key(col) for col in cols)
            recs = multigetterator(keys, self.consistency)

            if (self.record_key.keyspace not in recs
                or self.record_key.column_family not in
                recs[self.record_key.keyspace]):
                raise StopIteration()

            data = recs[self.record_key.keyspace][self.record_key.column_family]

            for (index, k) in enumerate(keys):
                record_data = data[k.key]
                if k.is_super():
                    record_data = record_data[k.super_column]

                self.last_col = cols[index]
                yield (self.record_class()._inject(
                        self.record_key.clone(key=k.key), record_data))


class PartitionedView(object):

    """A Lazyboy view which is partitioned across rows."""

    def __init__(self, view_key=None, view_class=None):
        self.view_key = view_key
        self.view_class = view_class

    def partition_keys(self):
        """Return a sequence of row keys for the view partitions."""
        return ()

    def _get_view(self, key):
        """Return an instance of a view for a partition key."""
        return self.view_class(self.view_key.clone(key=key))

    def __iter__(self):
        """Iterate over records in the view."""
        for view in (self._get_view(key) for key in self.partition_keys()):
            for record in view:
                yield record

    def _append_view(self, record):
        """Return the view which this record should be appended to.

        This defaults to the first view from partition_keys, but you
        can partition by anything, e.g. first letter of some field in
        the record.
        """
        key = iter(self.partition_keys()).next()
        return self._get_view(key)

    def append(self, record):
        """Append a record to the view."""
        return self._append_view(record).append(record)

########NEW FILE########
