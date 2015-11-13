__FILENAME__ = bench_elevator
import uuid
import hurdles

from hurdles.tools import extra_setup

from pyelevator import Elevator, WriteBatch


class BenchElevator(hurdles.BenchCase):
    def setUp(self):
        self.client = Elevator(timeout=10)
        self._bootstrap_db()

    def tearDown(self):
        pass

    def _bootstrap_db(self):
        with WriteBatch(timeout=10000) as batch:
            for x in xrange(100000):
                batch.Put(str(x), uuid.uuid4().hex)

    @extra_setup("import uuid\n"
                 "from pyelevator import WriteBatch\n"
                 "batch = WriteBatch(timeout=1000)\n"
                 "for x in xrange(100000):\n"
                 "    batch.Put(str(x), uuid.uuid4().hex)")
    def bench_write_batch(self, *args, **kwargs):
        kwargs['batch'].Write()

    @extra_setup("import random\n"
                 "keys = [str(random.randint(1, 9999)) for x in xrange(9999)]")
    def bench_mget_on_random_keys(self, *args, **kwargs):
        self.client.MGet(kwargs['keys'])

    @extra_setup("import random\n"
                 "keys = [str(random.randint(1, 9999)) for x in xrange(9999)]")
    def bench_mget_on_random_keys_with_compression(self, *args, **kwargs):
        self.client.MGet(kwargs['keys'], compression=True)

    @extra_setup("keys = [str(x) for x in xrange(9999)]")
    def bench_mget_on_serial_keys(self, *args, **kwargs):
        self.client.MGet(kwargs['keys'])

    @extra_setup("keys = [str(x) for x in xrange(9999)]")
    def bench_mget_on_serial_keys_with_compression(self, *args, **kwargs):
        self.client.MGet(kwargs['keys'], compression=True)

    def bench_range(self, *args, **kwargs):
        self.client.Range('1', '999998')

    def bench_range_with_compression(self, *args, **kwargs):
        self.client.Range('1', '999998', compression=True)

    def bench_slice(self, *args, **kwargs):
        self.client.Slice('1', 999998)

    def bench_slice_with_compression(self, *args, **kwargs):
        self.client.Slice('1', 999998, compression=True)

    @extra_setup("import random\n"
                 "keys = [str(random.randint(1, 10)) for x in xrange(10)]")
    def bench_random_get(self, *args, **kwargs):
        for key in kwargs['keys']:
            self.client.Get(key)

    def bench_serial_get(self, *args, **kwargs):
        pos = 1
        limit = 10

        while pos <= limit:
            self.client.Get(str(pos))
            pos += 1

########NEW FILE########
__FILENAME__ = api
../../../../share/pyshared/elevator/api.py
########NEW FILE########
__FILENAME__ = backend
../../../../share/pyshared/elevator/backend.py
########NEW FILE########
__FILENAME__ = conf
../../../../share/pyshared/elevator/conf.py
########NEW FILE########
__FILENAME__ = constants
../../../../share/pyshared/elevator/constants.py
########NEW FILE########
__FILENAME__ = db
../../../../share/pyshared/elevator/db.py
########NEW FILE########
__FILENAME__ = env
../../../../share/pyshared/elevator/env.py
########NEW FILE########
__FILENAME__ = frontend
../../../../share/pyshared/elevator/frontend.py
########NEW FILE########
__FILENAME__ = internals
../../../../../share/pyshared/elevator/helpers/internals.py
########NEW FILE########
__FILENAME__ = message
../../../../share/pyshared/elevator/message.py
########NEW FILE########
__FILENAME__ = server
../../../../share/pyshared/elevator/server.py
########NEW FILE########
__FILENAME__ = daemon
../../../../../share/pyshared/elevator/utils/daemon.py
########NEW FILE########
__FILENAME__ = decorators
../../../../../share/pyshared/elevator/utils/decorators.py
########NEW FILE########
__FILENAME__ = patterns
../../../../../share/pyshared/elevator/utils/patterns.py
########NEW FILE########
__FILENAME__ = snippets
../../../../../share/pyshared/elevator/utils/snippets.py
########NEW FILE########
__FILENAME__ = api
../../../../share/pyshared/elevator/api.py
########NEW FILE########
__FILENAME__ = backend
../../../../share/pyshared/elevator/backend.py
########NEW FILE########
__FILENAME__ = conf
../../../../share/pyshared/elevator/conf.py
########NEW FILE########
__FILENAME__ = constants
../../../../share/pyshared/elevator/constants.py
########NEW FILE########
__FILENAME__ = db
../../../../share/pyshared/elevator/db.py
########NEW FILE########
__FILENAME__ = env
../../../../share/pyshared/elevator/env.py
########NEW FILE########
__FILENAME__ = frontend
../../../../share/pyshared/elevator/frontend.py
########NEW FILE########
__FILENAME__ = internals
../../../../../share/pyshared/elevator/helpers/internals.py
########NEW FILE########
__FILENAME__ = message
../../../../share/pyshared/elevator/message.py
########NEW FILE########
__FILENAME__ = server
../../../../share/pyshared/elevator/server.py
########NEW FILE########
__FILENAME__ = daemon
../../../../../share/pyshared/elevator/utils/daemon.py
########NEW FILE########
__FILENAME__ = decorators
../../../../../share/pyshared/elevator/utils/decorators.py
########NEW FILE########
__FILENAME__ = patterns
../../../../../share/pyshared/elevator/utils/patterns.py
########NEW FILE########
__FILENAME__ = snippets
../../../../../share/pyshared/elevator/utils/snippets.py
########NEW FILE########
__FILENAME__ = api
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import leveldb
import logging

from .db import DatabaseOptions
from .message import ResponseContent, ResponseHeader
from .constants import KEY_ERROR, TYPE_ERROR, DATABASE_ERROR,\
                       VALUE_ERROR, RUNTIME_ERROR, SIGNAL_ERROR,\
                       SUCCESS_STATUS, FAILURE_STATUS, WARNING_STATUS,\
                       SIGNAL_BATCH_PUT, SIGNAL_BATCH_DELETE
from .utils.patterns import destructurate
from .helpers.internals import failure, success


errors_logger = logging.getLogger('errors_logger')


class Handler(object):
    """
    Class that handles commands server side.
    Translates, messages commands to it's methods calls.
    """
    def __init__(self, databases):
        self.databases = databases
        self.handlers = {
            'GET': self.Get,
            'PUT': self.Put,
            'DELETE': self.Delete,
            'RANGE': self.Range,
            'SLICE': self.Slice,
            'BATCH': self.Batch,
            'MGET': self.MGet,
            'DBCONNECT': self.DBConnect,
            'DBMOUNT': self.DBMount,
            'DBUMOUNT': self.DBUmount,
            'DBCREATE': self.DBCreate,
            'DBDROP': self.DBDrop,
            'DBLIST': self.DBList,
            'DBREPAIR': self.DBRepair,
        }
        self.context = {}

    def Get(self, db, key, *args, **kwargs):
        """
        Handles GET message command.
        Executes a Get operation over the leveldb backend.

        db      =>      LevelDB object
        *args   =>      (key) to fetch
        """
        try:
            return success(db.Get(key))
        except KeyError:
            error_msg = "Key %r does not exist" % key
            errors_logger.exception(error_msg)
            return failure(KEY_ERROR, error_msg)

    def MGet(self, db, keys, *args, **kwargs):
        def get_or_none(key, context):
            try:
                res = db.Get(key)
            except KeyError:
                warning_msg = "Key {0} does not exist".format(key)
                context['status'] = WARNING_STATUS
                errors_logger.warning(warning_msg)
                res = None
            return res

        context = {'status': SUCCESS_STATUS}
        value = [get_or_none(key, context) for key in keys]
        status = context['status']

        return status, value

    def Put(self, db, key, value, *args, **kwargs):
        """
        Handles Put message command.
        Executes a Put operation over the leveldb backend.

        db      =>      LevelDB object
        *args   =>      (key, value) to update

        """
        try:
            return success(db.Put(key, value))
        except TypeError:
            error_msg = "Unsupported value type : %s" % type(value)
            errors_logger.exception(error_msg)
            return failure(TYPE_ERROR, error_msg)

    def Delete(self, db, key, *args, **kwargs):
        """
        Handles Delete message command
        Executes a Delete operation over the leveldb backend.

        db      =>      LevelDB object
        *args   =>      (key) to delete from backend

        """
        return success(db.Delete(key))

    def Range(self, db, key_from, key_to, *args, **kwargs):
        """Returns the Range of key/value between
        `key_from and `key_to`"""
        # Operate over a snapshot in order to return
        # a consistent state of the db
        db_snapshot = db.CreateSnapshot()
        value = list(db_snapshot.RangeIter(key_from, key_to))

        return success(value)

    def Slice(self, db, key_from, offset, *args, **kwargs):
        """Returns a slice of the db. `offset` keys,
        starting a `key_from`"""
        # Operates over a snapshot in order to return
        # a consistent state of the db
        db_snapshot = db.CreateSnapshot()
        it = db_snapshot.RangeIter(key_from)
        value = []
        pos = 0

        while pos < offset:
            try:
                value.append(it.next())
            except StopIteration:
                break
            pos += 1

        return success(value)

    def Batch(self, db, collection, *args, **kwargs):
        batch = leveldb.WriteBatch()
        batch_actions = {
            SIGNAL_BATCH_PUT: batch.Put,
            SIGNAL_BATCH_DELETE: batch.Delete,
        }

        try:
            for command in collection:
                signal, args = destructurate(command)
                batch_actions[signal](*args)
        except KeyError:  # Unrecognized signal
            return (FAILURE_STATUS,
                    [SIGNAL_ERROR, "Unrecognized signal received : %r" % signal])
        except ValueError:
            return (FAILURE_STATUS,
                    [VALUE_ERROR, "Batch only accepts sequences (list, tuples,...)"])
        except TypeError:
            return (FAILURE_STATUS,
                    [TYPE_ERROR, "Invalid type supplied"])
        db.Write(batch)

        return success()

    def DBConnect(self, *args, **kwargs):
        db_name = args[0]

        if (not db_name or
            not self.databases.exists(db_name)):
            error_msg = "Database %s doesn't exist" % db_name
            errors_logger.error(error_msg)
            return failure(DATABASE_ERROR, error_msg)

        db_uid = self.databases.index['name_to_uid'][db_name]
        if self.databases[db_uid]['status'] == self.databases.STATUSES.UNMOUNTED:
            self.databases.mount(db_name)

        return success(db_uid)

    def DBMount(self, db_name, *args, **kwargs):
        return self.databases.mount(db_name)

    def DBUmount(self, db_name, *args, **kwargs):
        return self.databases.umount(db_name)

    def DBCreate(self, db, db_name, db_options=None, *args, **kwargs):
        db_options = DatabaseOptions(**db_options) if db_options else DatabaseOptions()

        if db_name in self.databases.index['name_to_uid']:
            error_msg = "Database %s already exists" % db_name
            errors_logger.error(error_msg)
            return failure(DATABASE_ERROR, error_msg)

        return self.databases.add(db_name, db_options)

    def DBDrop(self, db, db_name, *args, **kwargs):
        if not self.databases.exists(db_name):
            error_msg = "Database %s does not exist" % db_name
            errors_logger.error(error_msg)
            return failure(DATABASE_ERROR, error_msg)

        status, content = self.databases.drop(db_name)
        return status, content

    def DBList(self, db, *args, **kwargs):
        return success(self.databases.list())

    def DBRepair(self, db, db_uid, *args, **kwargs):
        db_path = self.databases['paths_index'][db_uid]

        leveldb.RepairDB(db_path)

        return success()

    def _gen_response(self, request, cmd_status, cmd_value):
        if cmd_status == FAILURE_STATUS:
            header = ResponseHeader(status=cmd_status, err_code=cmd_value[0], err_msg=cmd_value[1])
            content = ResponseContent(datas=None)
        else:
            if 'compression' in request.meta:
                compression = request.meta['compression']
            else:
                compression = False

            header = ResponseHeader(status=cmd_status, compression=compression)
            content = ResponseContent(datas=cmd_value, compression=compression)

        return header, content

    def command(self, message, *args, **kwargs):
        status = SUCCESS_STATUS
        err_code, err_msg = None, None

        # DB does not exist
        if message.db_uid and (not message.db_uid in self.databases):
            error_msg = "Database %s doesn't exist" % message.db_uid
            errors_logger.error(error_msg)
            status, value = failure(RUNTIME_ERROR, error_msg)
        # Command not recognized
        elif not message.command in self.handlers:
            error_msg = "Command %s not handled" % message.command
            errors_logger.error(error_msg)
            status, value = failure(KEY_ERROR, error_msg)
        # Valid request
        else:
            if not message.db_uid:
                status, value = self.handlers[message.command](*message.data, **kwargs)
            else:
                database = self.databases[message.db_uid]['connector']
                status, value = self.handlers[message.command](database, *message.data, **kwargs)

        # Will output a valid ResponseHeader and ResponseContent objects
        return self._gen_response(message, status, value)

########NEW FILE########
__FILENAME__ = backend
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import zmq
import logging
import threading

from .constants import FAILURE_STATUS, REQUEST_ERROR, WORKER_HALT
from .env import Environment
from .api import Handler
from .message import Request, MessageFormatError, ResponseContent, ResponseHeader
from .db import DatabasesHandler
from .utils.patterns import enum

activity_logger = logging.getLogger("activity_logger")
errors_logger = logging.getLogger("errors_logger")


class HaltException(Exception):
    pass


class Worker(threading.Thread):
    def __init__(self, zmq_context, databases, *args, **kwargs):
        threading.Thread.__init__(self)
        self.STATES = enum('RUNNING', 'IDLE', 'STOPPED')
        self.zmq_context = zmq_context
        self.state = self.STATES.RUNNING
        self.databases = databases
        self.env = Environment()
        self.socket = self.zmq_context.socket(zmq.XREQ)
        self.handler = Handler(databases)
        self.processing = False

    def run(self):
        self.socket.connect('inproc://elevator')
        msg = None

        while (self.state == self.STATES.RUNNING):
            try:
                sender_id, msg = self.socket.recv_multipart(copy=False)
                # If worker pool sends a WORKER_HALT, then close
                # and return to stop execution
                if sender_id.bytes == WORKER_HALT:  # copy=False -> zmq.Frame
                    raise HaltException("Gracefully stopping worker %r" % self.ident)
            except zmq.ZMQError as e:
                self.state = self.STATES.STOPPED
                errors_logger.warning('Worker %r encountered and error,'
                                      ' and was forced to stop' % self.ident)
                return
            except HaltException as e:
                activity_logger.info(e)
                return self.close()

            self.processing = True

            try:
                message = Request(msg)
            except MessageFormatError as e:
                errors_logger.exception(e.value)
                header = ResponseHeader(status=FAILURE_STATUS,
                                        err_code=REQUEST_ERROR,
                                        err_msg=e.value)
                content = ResponseContent(datas={})
                self.socket.send_multipart([sender_id, header, content], copy=False)
                continue

            # Handle message, and execute the requested
            # command in leveldb
            header, response = self.handler.command(message)

            self.socket.send_multipart([sender_id, header, response], flags=zmq.NOBLOCK, copy=False)
            self.processing = False

    def close(self):
        self.state = self.STATES.STOPPED

        if not self.socket.closed:
            self.socket.close()


class WorkersPool():
    def __init__(self, workers_count=4, **kwargs):
        env = Environment()
        database_store = env['global']['database_store']
        databases_storage = env['global']['databases_storage_path']
        self.databases = DatabasesHandler(database_store, databases_storage)
        self.pool = []

        self.zmq_context = zmq.Context()
        self.socket = self.zmq_context.socket(zmq.XREQ)
        self.socket.bind('inproc://elevator')
        self.init_workers(workers_count)

    def __del__(self):
        while any(worker.isAlive() for worker in self.pool):
            self.socket.send_multipart([WORKER_HALT, ""])

        for worker in self.pool:
            worker.join()

        self.socket.close()

    def init_workers(self, count):
        pos = 0

        while pos < count:
            worker = Worker(self.zmq_context, self.databases)
            worker.start()
            self.pool.append(worker)
            pos += 1

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import argparse


DEFAULT_CONFIG_FILE = '/etc/elevatord.conf'


def init_parser():
    parser = argparse.ArgumentParser(
        description="Elevator command line manager"
    )
    parser.add_argument('-d', '--daemon', action='store_true', default=False)
    parser.add_argument('-c', '--config', action='store', type=str,
                        default=DEFAULT_CONFIG_FILE)
    # tcp or ipc
    parser.add_argument('-t', '--transport', action='store', type=str,
                        default='tcp')
    parser.add_argument('-b', '--bind', action='store', type=str,
                        default='127.0.0.1')
    parser.add_argument('-p', '--port', action='store', type=str, default='4141')
    parser.add_argument('-w', '--workers', action='store', type=int, default=4)
    parser.add_argument('-P', '--paranoid', action='store_true', default=False)
    parser.add_argument('-v', '--log-level', action='store', type=str, default='INFO')

    return parser

########NEW FILE########
__FILENAME__ = constants
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

## Internals
WORKER_HALT = "-1"

## Protocol

# Status codes
SUCCESS_STATUS = 1
FAILURE_STATUS = -1
WARNING_STATUS = -2

# Error codes
TYPE_ERROR = 0
KEY_ERROR = 1
VALUE_ERROR = 2
INDEX_ERROR = 3
RUNTIME_ERROR = 4
OS_ERROR = 5
DATABASE_ERROR = 6
SIGNAL_ERROR = 7
REQUEST_ERROR = 8

# Signals
SIGNAL_BATCH_PUT = 1
SIGNAL_BATCH_DELETE = 0

########NEW FILE########
__FILENAME__ = db
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import os
import uuid
import logging
import leveldb
import ujson as json

from shutil import rmtree
from threading import Thread, Event
from leveldb import LevelDBError

from .env import Environment
from .constants import OS_ERROR, DATABASE_ERROR
from .utils.snippets import from_bytes_to_mo
from .utils.patterns import enum
from .helpers.internals import failure, success


activity_logger = logging.getLogger("activity_logger")
errors_logger = logging.getLogger("errors_logger")


class Ocd(Thread):
    """Sometimes, you just want your program to have some
    obsessive compulsive disorder

    Source : http://pastebin.com/xNV7hx8h"""
    def __init__(self, interval, function, iterations=0, args=[], kwargs={}):
        Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.iterations = iterations
        self.args = args
        self.kwargs = kwargs
        self.finished = Event()

    def run(self):
        count = 0
        while not self.finished.is_set() and (self.iterations <= 0 or count < self.iterations):
            self.finished.wait(self.interval)
            if not self.finished.is_set():
                self.function(*self.args, **self.kwargs)
                count += 1

    def cancel(self):
        self.finished.set()


class DatabaseOptions(dict):
    def __init__(self, *args, **kwargs):
        self['create_if_missing'] = True
        self['error_if_exists'] = False
        self['paranoid_checks'] = False
        self['block_cache_size'] = 8 * (2 << 20)
        self['write_buffer_size'] = 2 * (2 << 20)
        self['block_size'] = 4096
        self['max_open_files'] = 1000

        for key, value in kwargs.iteritems():
            if key in self:
                self[key] = value


class DatabasesHandler(dict):
    STATUSES = enum('MOUNTED', 'UNMOUNTED')

    def __init__(self, store, dest, *args, **kwargs):
        self.env = Environment()
        self.index = dict().fromkeys('name_to_uid')

        self.index['name_to_uid'] = {}
        self['reverse_name_index'] = {}
        self['paths_index'] = {}
        self.dest = dest
        self.store = store

        self._global_cache_size = None

        self.load()
        self.mount('default')  # Always mount default

    @property
    def global_cache_size(self):
        store_datas = self.extract_store_datas()
        max_caches = [int(db["options"]["block_cache_size"]) for db
                      in store_datas.itervalues()]

        return sum([from_bytes_to_mo(x) for x in max_caches])

    def _disposable_cache(self, new_cache_size):
        next_cache_size = self.global_cache_size + from_bytes_to_mo(new_cache_size)
        ratio = int(self.env["global"]["max_cache_size"]) - next_cache_size

        # Both values are in
        if ratio < 0:
            return (False, ratio)
        return (True, ratio)

    def _get_db_connector(self, path, *args, **kwargs):
        connector = None

        try:
            connector = leveldb.LevelDB(path, *args, **kwargs)
        except LevelDBError as e:
            errors_logger.exception(e.message)

        return connector

    def extract_store_datas(self):
        """Retrieves database store from file

        If file doesn't exist, or is invalid json,
        and empty store is returned.

        Return
        ------
        store_datas, dict
        """
        try:
            store_datas = json.load(open(self.store, 'r'))
        except (IOError, ValueError):
            store_datas = {}

        return store_datas

    def load(self):
        """Loads databases from store file"""
        store_datas = self.extract_store_datas()

        for db_name, db_desc in store_datas.iteritems():
            self.index['name_to_uid'].update({db_name: db_desc['uid']})
            self.update({
                db_desc['uid']: {
                    'connector': None,
                    'name': db_name,
                    'path': db_desc['path'],
                    'status': self.STATUSES.UNMOUNTED,
                    'ref_count': 0,
                }
            })

        # Always bootstrap 'default'
        if 'default' not in self.index['name_to_uid']:
            self.add('default')

    def store_update(self, db_name, db_desc):
        """Updates the database store file db_name
        key, with db_desc value"""
        store_datas = self.extract_store_datas()

        store_datas.update({db_name: db_desc})
        json.dump(store_datas, open(self.store, 'w'))

    def store_remove(self, db_name):
        """Removes a database from store file"""
        store_datas = self.extract_store_datas()
        store_datas.pop(db_name)
        json.dump(store_datas, open(self.store, 'w'))

    def mount(self, db_name):
        db_uid = self.index['name_to_uid'][db_name] if db_name in self.index['name_to_uid'] else None

        if self[db_uid]['status'] == self.STATUSES.UNMOUNTED:
            db_path = self[db_uid]['path']
            connector = self._get_db_connector(db_path)

            if connector is None:
                return failure(DATABASE_ERROR, "Database %s could not be mounted" % db_path)

            self[db_uid]['status'] = self.STATUSES.MOUNTED
            self[db_uid]['connector'] = leveldb.LevelDB(db_path)
        else:
            return failure(DATABASE_ERROR, "Database %r already mounted" % db_name)

        return success()

    def umount(self, db_name):
        db_uid = self.index['name_to_uid'][db_name] if db_name in self.index['name_to_uid'] else None

        if self[db_uid]['status'] == self.STATUSES.MOUNTED:
            self[db_uid]['status'] = self.STATUSES.UNMOUNTED
            del self[db_uid]['connector']
            self[db_uid]['connector'] = None
        else:
            return failure(DATABASE_ERROR, "Database %r already unmounted" % db_name)

        return success()

    def add(self, db_name, db_options=None):
        """Adds a db to the DatabasesHandler object, and sync it
        to the store file"""
        db_options = db_options or DatabaseOptions()
        cache_status, ratio = self._disposable_cache(db_options["block_cache_size"])
        if not cache_status:
            return failure(DATABASE_ERROR,
                           "Not enough disposable cache memory "
                           "%d Mo missing" % ratio)

        db_name_is_path = db_name.startswith('.') or ('/' in db_name)
        is_abspath = lambda: not db_name.startswith('.') and ('/' in db_name)

        # Handle case when a db is a path
        if db_name_is_path:
            if not is_abspath():
                return failure(DATABASE_ERROR, "Canno't create database from relative path")
            try:
                new_db_path = db_name
                if not os.path.exists(new_db_path):
                    os.mkdir(new_db_path)
            except OSError as e:
                return failure(OS_ERROR, e.strerror)
        else:
            new_db_path = os.path.join(self.dest, db_name)

        path = new_db_path
        connector = self._get_db_connector(path)

        if connector is None:
            return (DATABASE_ERROR, "Database %s could not be created" % path)

        # Adding db to store, and updating handler
        uid = str(uuid.uuid4())
        options = db_options
        self.store_update(db_name, {
            'path': path,
            'uid': uid,
            'options': options,
        })

        self.index['name_to_uid'].update({db_name: uid})
        self.update({
            uid: {
                'connector': connector,
                'name': db_name,
                'path': path,
                'status': self.STATUSES.MOUNTED,
                'ref_count': 0,
            },
        })

        return success()

    def drop(self, db_name):
        """Drops a db from the DatabasesHandler, and sync it
        to store file"""
        db_uid = self.index['name_to_uid'].pop(db_name)
        db_path = self[db_uid]['path']

        self.pop(db_uid)
        self.store_remove(db_name)

        try:
            rmtree(db_path)
        except OSError:
            return failure(DATABASE_ERROR, "Cannot drop db : %s, files not found")

        return success()

    def exists(self, db_name):
        """Checks if a database exists on disk"""
        db_uid = self.index['name_to_uid'][db_name] if db_name in self.index['name_to_uid'] else None

        if db_uid:
            if os.path.exists(self[db_uid]['path']):
                return True
            else:
                self.drop(db_name)

        return False

    def list(self):
        """Lists all the DatabasesHandler known databases"""
        return [db_name for db_name
                in [key for key
                    in self.index['name_to_uid'].iterkeys()]
                if self.exists(db_name)]

########NEW FILE########
__FILENAME__ = env
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

from ConfigParser import ConfigParser

from utils.patterns import Singleton
from utils.snippets import items_to_dict


class Environment(dict):
    """
    Unix shells like environment class. Implements add,
    get, load, flush methods. Handles lists of values too.
    Basically Acts like a basic key/value store.
    """
    __metaclass__ = Singleton

    def __init__(self, env_file='', *args, **kwargs):
        if env_file:
            self.load_from_file(env_file=env_file)  # Has to be called last!

        self.update(kwargs)
        dict.__init__(self, *args, **kwargs)

    def load_from_file(self, env_file):
        """
        Updates the environment using an ini file containing
        key/value descriptions.
        """
        config = ConfigParser()

        with open(env_file, 'r') as f:
            config.readfp(f)

            for section in config.sections():
                self.update({section: items_to_dict(config.items(section))})

    def reload_from_file(self, env_file=''):
        self.flush(env_file)
        self.load(env_file)

    def load_from_args(self, section, args):
        """Loads argparse kwargs into environment, as `section`"""
        if not section in self:
            self[section] = {}

        for (arg, value) in args:
            self[section][arg] = value

    def flush(self):
        """
        Flushes the environment from it's manually
        set attributes.
        """
        for attr in self.attributes:
            delattr(self, attr)

########NEW FILE########
__FILENAME__ = frontend
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import zmq
import logging

from .env import Environment

errors_logger = logging.getLogger("errors_logger")


class Proxy():
    def __init__(self, transport, endpoint):
        self.env = Environment()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.XREP)
        self.host = self._gen_bind_adress(transport, endpoint)
        self.socket.bind(self.host)

    def __del__(self):
        self.socket.close()
        self.context.term()

    def _gen_bind_adress(self, transport, endpoint):
        if transport == 'ipc':
            if not 'unixsocket' in self.env['global']:
                err_msg = "Ipc transport layer was selected, but no unixsocket "\
                          "path could be found in conf file"
                errors_logger.exception(err_msg)
                raise KeyError(err_msg)
            return '{0}://{1}'.format(transport, self.env['global']['unixsocket'])

        else:  # consider it's tcp
            return '{0}://{1}'.format(transport, endpoint)

########NEW FILE########
__FILENAME__ = internals
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

from __future__ import absolute_import

from ..constants import FAILURE_STATUS, SUCCESS_STATUS, WARNING_STATUS


def failure(err_code, err_msg):
    """Returns a formatted error status and content"""
    return (FAILURE_STATUS, [err_code, err_msg])


def success(content=None):
    """Returns a formatted success status and content"""
    return (SUCCESS_STATUS, content)


def warning(error_code, error_msg, content):
    """Returns a formatted warning status and content"""
    return (WARNING_STATUS, [error_code, error_msg, content])

########NEW FILE########
__FILENAME__ = message
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

from __future__ import absolute_import

import msgpack
import logging
import lz4

from .constants import FAILURE_STATUS

activity_logger = logging.getLogger("activity_logger")
errors_logger = logging.getLogger("errors_logger")


class MessageFormatError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Request(object):
    """Handler objects for client requests messages

    Format :
    {
        'meta': {...},
        'cmd': 'GET',
        'uid': 'mysuperduperdbuid',
        'args': [...],
    }
    """
    def __init__(self, raw_message):
        self.message = msgpack.unpackb(raw_message)
        self.meta = self.message.get('meta', {})
        activity_logger.debug('<Request ' + str(self.message) + '>')

        try:
            self.db_uid = self.message.get('uid')  # In some case db_uid should be None
            self.command = self.message['cmd']
            self.data = self.message['args']  # __getitem__ will raise if !key
        except KeyError:
            errors_logger.exception("Invalid request message : %s" % self.message)
            raise MessageFormatError("Invalid request message : %r" % self.message)


class ResponseContent(tuple):
    """Handler objects for responses messages

    Format:
    {
        'meta': {
            'status': 1|0|-1,
            'err_code': null|0|1|[...],
            'err_msg': '',
        },
        'datas': [...],
    }
    """
    def __new__(cls, *args, **kwargs):
        response = {
            'datas': cls._format_datas(kwargs['datas']),
        }
        activity_logger.debug('<Response ' + str(response['datas']) + '>')
        msg = msgpack.packb(response)

        if kwargs.pop('compression', False) is True:
            msg = lz4.dumps(msg)

        return msg

    @classmethod
    def _format_datas(cls, datas):
        if datas and not isinstance(datas, (tuple, list)):
            datas = [datas]
        return datas


class ResponseHeader(dict):
    def __new__(cls, *args, **kwargs):
        header = {
            'status': kwargs.pop('status'),
            'err_code': kwargs.pop('err_code', None),
            'err_msg': kwargs.pop('err_msg', None),
            'compression': kwargs.pop('compression', False)
        }
        activity_logger.debug('<ResponseHeader ' + str(header) + '>')

        for key, value in kwargs.iteritems():
            header.update({key: value})

        return msgpack.packb(header)

########NEW FILE########
__FILENAME__ = server
# -*- coding:utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import sys
import traceback
import zmq
import logging
import procname

from elevator import conf
from elevator.env import Environment
from elevator.backend import WorkersPool
from elevator.frontend import Proxy
from elevator.utils.daemon import Daemon


ARGS = conf.init_parser().parse_args(sys.argv[1:])


def setup_process_name(env):
    args = env['args']
    endpoint = ' {0}://{1}:{2} '.format(args['transport'],
                                        args['bind'],
                                        args['port'])
    config = ' --config {0} '.format(args['config'])
    process_name = 'elevator' + endpoint + config

    procname.setprocname(process_name)


def setup_loggers(env):
    activity_log_file = env['global']['activity_log']
    errors_log_file = env['global']['errors_log']

    # Setup up activity logger
    numeric_level = getattr(logging, env['args']['log_level'].upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % env['args']['log_level'].upper())

    # Set up activity logger on file and stderr
    activity_formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(funcName)s : %(message)s")
    file_stream = logging.FileHandler(activity_log_file)
    stderr_stream = logging.StreamHandler(sys.stdout)
    file_stream.setFormatter(activity_formatter)
    stderr_stream.setFormatter(activity_formatter)

    activity_logger = logging.getLogger("activity_logger")
    activity_logger.setLevel(numeric_level)
    activity_logger.addHandler(file_stream)
    activity_logger.addHandler(stderr_stream)

    # Setup up activity logger
    errors_logger = logging.getLogger("errors_logger")
    errors_logger.setLevel(logging.WARNING)
    errors_stream = logging.FileHandler(errors_log_file)
    errors_formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(funcName)s : %(message)s")
    errors_stream.setFormatter(errors_formatter)
    errors_logger.addHandler(errors_stream)


def log_uncaught_exceptions(e, paranoid=False):
    errors_logger = logging.getLogger("errors_logger")
    tb = traceback.format_exc()

    # Log into errors log
    errors_logger.critical(''.join(tb))
    errors_logger.critical('{0}: {1}'.format(type(e), e.message))

    # Log into stderr
    logging.critical(''.join(tb))
    logging.critical('{0}: {1}'.format(type(e), e.message))

    if paranoid:
        sys.exit(1)


def runserver(env):
    args = env['args']

    setup_loggers(env)
    activity_logger = logging.getLogger("activity_logger")

    workers_pool = WorkersPool(args['workers'])
    proxy = Proxy(args['transport'], ':'.join([args['bind'], args['port']]))

    poll = zmq.Poller()
    poll.register(workers_pool.socket, zmq.POLLIN)
    poll.register(proxy.socket, zmq.POLLIN)

    activity_logger.info('Elevator server started on %s' % proxy.host)

    while True:
        try:
            sockets = dict(poll.poll())
            if proxy.socket in sockets:
                if sockets[proxy.socket] == zmq.POLLIN:
                    msg = proxy.socket.recv_multipart(copy=False)
                    workers_pool.socket.send_multipart(msg, copy=False)

            if workers_pool.socket in sockets:
                if sockets[workers_pool.socket] == zmq.POLLIN:
                    msg = workers_pool.socket.recv_multipart(copy=False)
                    proxy.socket.send_multipart(msg, copy=False)
        except KeyboardInterrupt:
            activity_logger.info('Gracefully shuthing down workers')
            del workers_pool
            activity_logger.info('Stopping proxy')
            del proxy
            activity_logger.info('Done')
            sys.exit(0)
        except Exception as e:
            log_uncaught_exceptions(e, paranoid=args['paranoid'])


class ServerDaemon(Daemon):
    def run(self):
        env = Environment()  # Already bootstraped singleton obj
        while True:
            runserver(env)


def main():
    # As Environment object is a singleton
    # every further instanciation of the object
    # will point on this one, and conf will be
    # present in it yet.
    env = Environment(ARGS.config)
    env.load_from_args('args', ARGS._get_kwargs())
    setup_process_name(env)

    if env['args']['daemon'] is True:
        server_daemon = ServerDaemon('/tmp/elevator.pid')
        server_daemon.start()
    else:
        runserver(env)

########NEW FILE########
__FILENAME__ = daemon
"""
    ***
    Modified generic daemon class
    ***

    Author:     http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
                www.boxedice.com

    License:    http://creativecommons.org/licenses/by-sa/3.0/

    Changes:    23rd Jan 2009 (David Mytton <david@boxedice.com>)
                - Replaced hard coded '/dev/null in __init__ with os.devnull
                - Added OS check to conditionally remove code that doesn't work on OS X
                - Added output to console on completion
                - Tidied up formatting
                11th Mar 2009 (David Mytton <david@boxedice.com>)
                - Fixed problem with daemon exiting on Python 2.4 (before SystemExit was part of the Exception base)
                13th Aug 2010 (David Mytton <david@boxedice.com>
                - Fixed unhandled exception if PID file is empty
"""

# Core modules
import atexit
import os
import sys
import time
import signal


class Daemon(object):
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull, home_dir='.', umask=022, verbose=1):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.home_dir = home_dir
        self.verbose = verbose
        self.umask = umask
        self.daemon_alive = True

    def daemonize(self):
        """
        Do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # Exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # Decouple from parent environment
        os.chdir(self.home_dir)
        os.setsid()
        os.umask(self.umask)

        # Do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # Exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        if sys.platform != 'darwin':  # This block breaks on OS X
            # Redirect standard file descriptors
            sys.stdout.flush()
            sys.stderr.flush()
            si = file(self.stdin, 'r')
            so = file(self.stdout, 'a+')
            if self.stderr:
                se = file(self.stderr, 'a+', 0)
                os.dup2(se.fileno(), sys.stderr.fileno())
            else:
                se = sys.stderr
            os.dup2(si.fileno(), sys.stdin.fileno())
            os.dup2(so.fileno(), sys.stdout.fileno())

        def sigtermhandler(signum, frame):
            self.daemon_alive = False
        signal.signal(signal.SIGTERM, sigtermhandler)
        signal.signal(signal.SIGINT, sigtermhandler)

        if self.verbose >= 1:
            print "Started"

        # Write pidfile
        atexit.register(self.delpid)  # Make sure pid file is removed if we quit
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def start(self, *args, **kwargs):
        """
        Start the daemon
        """

        if self.verbose >= 1:
            print "Starting..."

        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        except SystemExit:
            pid = None

        if pid:
            message = "pidfile %s already exists. Is it already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run(*args, **kwargs)

    def stop(self):
        """
        Stop the daemon
        """

        if self.verbose >= 1:
            print "Stopping..."

        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        except ValueError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Not running?\n"
            sys.stderr.write(message % self.pidfile)

            # Just to be sure. A ValueError might occur if the PID file is empty but does actually exist
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)

            return  # Not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

        if self.verbose >= 1:
            print "Stopped"

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """

########NEW FILE########
__FILENAME__ = decorators
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import collections
import functools
import time

from itertools import ifilterfalse


class Counter(dict):
    'Mapping where default values are zero'
    def __missing__(self, key):
        return 0


def lru_cache(maxsize=100):
    '''Least-recently-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    '''
    maxqueue = maxsize * 10

    def decorating_function(user_function,
            len=len, iter=iter, tuple=tuple, sorted=sorted, KeyError=KeyError):
        cache = {}                   # mapping of args to results
        queue = collections.deque()  # order that keys have been used
        refcount = Counter()         # times each key is in the queue
        sentinel = object()          # marker for looping around the queue
        kwd_mark = object()          # separate positional and keyword args

        # lookup optimizations (ugly but fast)
        queue_append, queue_popleft = queue.append, queue.popleft
        queue_appendleft, queue_pop = queue.appendleft, queue.pop

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            # cache key records both positional and keyword args
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))

            # record recent use of this key
            queue_append(key)
            refcount[key] += 1

            # get cache entry or compute if not found
            try:
                result = cache[key]
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                cache[key] = result
                wrapper.misses += 1

                # purge least recently used cache entry
                if len(cache) > maxsize:
                    key = queue_popleft()
                    refcount[key] -= 1
                    while refcount[key]:
                        key = queue_popleft()
                        refcount[key] -= 1
                    try:
                        del cache[key], refcount[key]
                    except KeyError:
                        pass

            # periodically compact the queue by eliminating duplicate keys
            # while preserving order of most recent access
            if len(queue) > maxqueue:
                refcount.clear()
                queue_appendleft(sentinel)
                for key in ifilterfalse(refcount.__contains__,
                                        iter(queue_pop, sentinel)):
                    queue_appendleft(key)
                    refcount[key] = 1

            return result

        def clear():
            cache.clear()
            queue.clear()
            refcount.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper
    return decorating_function


# @Report
# Number of times to indent output
# A list is used to force access by reference
__report_indent = [0]


def time_it(function):
    """
    Decorator whichs times a function execution.
    """
    def wrap(*args, **kwargs):
        start = time.time()
        r = function(*args, **kwargs)
        end = time.time()
        print "%s (%0.3f ms)" % (function.func_name, (end - start) * 1000)
        return r
    return wrap


def report(fn):
    """Decorator to print information about a function
    call for use while debugging.
    Prints function name, arguments, and call number
    when the function is called. Prints this information
    again along with the return value when the function
    returns.
    """

    def wrap(*params, **kwargs):
        call = wrap.callcount = wrap.callcount + 1

        indent = ' ' * __report_indent[0]
        fc = "%s(%s)" % (fn.__name__, ', '.join(
            [a.__repr__() for a in params] +
            ["%s = %s" % (a, repr(b)) for a, b in kwargs.items()]
        ))

        print "%s%s called [#%s]" % (indent, fc, call)
        __report_indent[0] += 1
        ret = fn(*params, **kwargs)
        __report_indent[0] -= 1
        print "%s%s returned %s [#%s]" % (indent, fc, repr(ret), call)

        return ret
    wrap.callcount = 0
    return wrap


def memoize(func, cache, num_args):
    """
    Wrap a function so that results for any argument tuple are stored in
    'cache'. Note that the args to the function must be usable as dictionary
    keys.

    Only the first num_args are considered when creating the key.
    """
    @functools.wraps(func)
    def wrapper(*args):
        mem_args = args[:num_args]
        if mem_args in cache:
            return cache[mem_args]
        result = func(*args)
        cache[mem_args] = result
        return result
    return wrapper


###   Cached Property   ###


class _Missing(object):
    """cached_property decorator dependency"""
    def __repr__(self):
        return 'no value'

    def __reduce__(self):
        return '_missing'


_missing = _Missing()


class cached_property(object):
    """A decorator that converts a function into a lazy property.  The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

        class Foo(object):

            @cached_property
            def foo(self):
                # calculate something important here
                return 42

    The class has to have a `__dict__` in order for this property to
    work.

    .. versionchanged:: 0.6
       the `writeable` attribute and parameter was deprecated.  If a
       cached property is writeable or not has to be documented now.
       For performance reasons the implementation does not honor the
       writeable setting and will always make the property writeable.
    """
    # implementation detail: this property is implemented as non-data
    # descriptor.  non-data descriptors are only invoked if there is
    # no entry with the same name in the instance's __dict__.
    # this allows us to completely get rid of the access function call
    # overhead.  If one choses to invoke __get__ by hand the property
    # will still work as expected because the lookup logic is replicated
    # in __get__ for manual invocation.

    def __init__(self, func, name=None, doc=None, writeable=False):
        if writeable:
            from warnings import warn
            warn(DeprecationWarning('the writeable argument to the '
                                    'cached property is a noop since 0.6 '
                                    'because the property is writeable '
                                    'by default for performance reasons'))

        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

########NEW FILE########
__FILENAME__ = patterns
from collections import Sequence

# Enums beautiful python implementation
# Used like this :
# Numbers = enum('ZERO', 'ONE', 'TWO')
# >>> Numbers.ZERO
# 0
# >>> Numbers.ONE
# 1
# Found here: http://stackoverflow.com/questions/36932/whats-the-best-way-to-implement-an-enum-in-python
def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)


class Singleton(type):
    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(name, bases, dict)
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance

    def __del__(cls, *args, **kw):
        cls.instance is None


class DestructurationError(Exception):
    pass


def destructurate(container):
    try:
        return container[0], container[1:]
    except (KeyError, AttributeError):
        raise DestructurationError("Can't destructurate a non-sequence container")

########NEW FILE########
__FILENAME__ = snippets
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Checks if a str is a word(unique),
# or an expression (more than one word).
is_expression = lambda s: ' ' in s.strip()


# Lambda function which tranforms a ConfigParser items
# list of tuples object into a dictionnary,
# doesn't use dict comprehension in order to keep 2.6
# backward compatibility.
def items_to_dict(items):
    res = {}

    for k, v in items:
        res[k] = v
    return res

# Iterates through a sequence of size `clen`
chunks = lambda seq, clen: [seq[i:(i + clen)] for i in xrange(0, len(seq), clen)]

# Decodes a list content from a given charset
ldecode = lambda list, charset: [string.decode(charset) for string in charset]

# Encodes a list content from a given charset
lencode = lambda list, charset: [string.encode(charset) for string in charset]

# Checks if a sequence is ascendently sorted
asc_sorted = lambda seq: all(seq[i] <= seq[i + 1] for i in xrange(len(seq) - 1))

# idem descending
desc_sorted = lambda seq: all(seq[i] >= seq[i + 1] for i in xrange(len(seq) - 1))

# Convert bytes to Mo
from_bytes_to_mo = lambda bytes: bytes / 1048576

#Convert Mo to bytes
from_mo_to_bytes = lambda mo: mo * 1048576

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Elevator documentation build configuration file, created by
# sphinx-quickstart on Fri Oct 19 14:34:58 2012.
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
#sys.path.insert(0, os.path.abspath('.'))

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
project = u'Elevator'
copyright = u'2012, Oleiade'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.4'
# The full version, including alpha/beta/rc tags.
release = '0.4'

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
exclude_patterns = []

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
htmlhelp_basename = 'Elevatordoc'


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
  ('index', 'Elevator.tex', u'Elevator Documentation',
   u'Oleiade', 'manual'),
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
    ('index', 'elevator', u'Elevator Documentation',
     [u'Oleiade'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Elevator', u'Elevator Documentation',
   u'Oleiade', 'Elevator', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'Elevator'
epub_author = u'Oleiade'
epub_publisher = u'Oleiade'
epub_copyright = u'2012, Oleiade'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}


# Flask theme
sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'flask'

########NEW FILE########
__FILENAME__ = api
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import plyvel
import logging
import time

from .db import DatabaseOptions
from .message import ResponseContent, ResponseHeader
from .constants import KEY_ERROR, TYPE_ERROR, DATABASE_ERROR,\
                       VALUE_ERROR, RUNTIME_ERROR, SIGNAL_ERROR,\
                       SUCCESS_STATUS, FAILURE_STATUS, WARNING_STATUS,\
                       SIGNAL_BATCH_PUT, SIGNAL_BATCH_DELETE
from .utils.patterns import destructurate
from .helpers.internals import failure, success


activity_logger = logging.getLogger('activity_logger')
errors_logger = logging.getLogger('errors_logger')


class Handler(object):
    """
    Class that handles commands server side.
    Translates, messages commands to it's methods calls.
    """
    def __init__(self, databases):
        self.databases = databases
        self.handlers = {
            'GET': self.Get,
            'PUT': self.Put,
            'DELETE': self.Delete,
            'EXISTS': self.Exists,
            'RANGE': self.Range,
            'SLICE': self.Slice,
            'BATCH': self.Batch,
            'MGET': self.MGet,
            'PING': self.Ping,
            'DBCONNECT': self.DBConnect,
            'DBMOUNT': self.DBMount,
            'DBUMOUNT': self.DBUmount,
            'DBCREATE': self.DBCreate,
            'DBDROP': self.DBDrop,
            'DBLIST': self.DBList,
            'DBREPAIR': self.DBRepair,
        }
        self.context = {}

    def Get(self, db, key, *args, **kwargs):
        """
        Handles GET message command.
        Executes a Get operation over the plyvel backend.

        db      =>      LevelDB object
        *args   =>      (key) to fetch
        """
        value = db.get(key)

        if not value:
            error_msg = "Key %r does not exist" % key
            errors_logger.exception(error_msg)
            return failure(KEY_ERROR, error_msg)
        else:
            return success(value)

    def MGet(self, db, keys, *args, **kwargs):
        status = SUCCESS_STATUS
        db_snapshot = db.snapshot()

        values = [None] * len(keys)
        min_key, max_key = min(keys), max(keys)
        keys_index = {k: index for index, k in enumerate(keys)}
        bound_range = db_snapshot.iterator(start=min_key, stop=max_key, include_stop=True)

        for key, value in bound_range:
            if key in keys_index:
                values[keys_index[key]] = value

        status = WARNING_STATUS if any(v is None for v in values) else status

        return status, values

    def Put(self, db, key, value, *args, **kwargs):
        """
        Handles Put message command.
        Executes a Put operation over the plyvel backend.

        db      =>      LevelDB object
        *args   =>      (key, value) to update

        """
        try:
            return success(db.put(key, value))
        except TypeError:
            error_msg = "Unsupported value type : %s" % type(value)
            errors_logger.exception(error_msg)
            return failure(TYPE_ERROR, error_msg)

    def Delete(self, db, key, *args, **kwargs):
        """
        Handles Delete message command
        Executes a Delete operation over the plyvel backend.

        db      =>      LevelDB object
        *args   =>      (key) to delete from backend

        """
        return success(db.delete(key))

    def Exists(self, db, key, *args, **kwargs):
        """
        Return whether or not the given key is present
        in the database.

        db      =>      LevelDB object
        *args   =>      (key) to check

        """

        # We should be able to check if the key without getting the value
        # by creating an iterator, seeking to the key and check if the
        # iterator is valid.
        # However, it doesn't work with Plyvel 0.8.
        # cf https://github.com/wbolster/plyvel/issues/32
        return success(db.get(key) is not None)

    def Range(self, db, key_from, key_to,
              include_key=True, include_value=True, prefix=None):
        """Returns the Range of key/value between
        `key_from and `key_to`"""
        # Operate over a snapshot in order to return
        # a consistent state of the db
        db_snapshot = db.snapshot()
        it = db_snapshot.iterator(start=key_from, stop=key_to,
                                  include_key=include_key,
                                  include_value=include_value,
                                  prefix=prefix,
                                  include_stop=True)
        value = list(it)
        del db_snapshot

        return success(value)

    def Slice(self, db, key_from, offset,
              include_key=True, include_value=True):
        """Returns a slice of the db. `offset` keys,
        starting a `key_from`"""
        # Operates over a snapshot in order to return
        # a consistent state of the db
        db_snapshot = db.snapshot()
        it = db_snapshot.iterator(start=key_from,
                                  include_key=include_key,
                                  include_value=include_value,
                                  include_stop=True)
        value = []
        pos = 0

        while pos < offset:
            try:
                value.append(it.next())
            except StopIteration:
                break
            pos += 1

        return success(value)

    def Batch(self, db, collection, *args, **kwargs):
        batch = db.write_batch()
        batch_actions = {
            SIGNAL_BATCH_PUT: batch.put,
            SIGNAL_BATCH_DELETE: batch.delete,
        }

        try:
            for command in collection:
                signal, args = destructurate(command)
                batch_actions[signal](*args)
        except KeyError:  # Unrecognized signal
            return failure(SIGNAL_ERROR, "Unrecognized signal received : %r" % signal)
        except ValueError:
            return failure(VALUE_ERROR, "Batch only accepts sequences (list, tuples,...)")
        except TypeError:
            return failure(TYPE_ERROR, "Invalid type supplied")
        batch.write()

        return success()

    def Ping(self, *args, **kwargs):
        return success("PONG")

    def DBConnect(self, *args, **kwargs):
        db_name = args[0]

        if (not db_name or
            not self.databases.exists(db_name)):
            error_msg = "Database %s doesn't exist" % db_name
            errors_logger.error(error_msg)
            return failure(DATABASE_ERROR, error_msg)

        db_uid = self.databases.index['name_to_uid'][db_name]
        if self.databases[db_uid].status == self.databases.STATUSES.UNMOUNTED:
            self.databases.mount(db_name)

        return success(db_uid)

    def DBMount(self, db_name, *args, **kwargs):
        return self.databases.mount(db_name)

    def DBUmount(self, db_name, *args, **kwargs):
        return self.databases.umount(db_name)

    def DBCreate(self, db, db_name, db_options=None, *args, **kwargs):
        db_options = DatabaseOptions(**db_options) if db_options else DatabaseOptions()

        if db_name in self.databases.index['name_to_uid']:
            error_msg = "Database %s already exists" % db_name
            errors_logger.error(error_msg)
            return failure(DATABASE_ERROR, error_msg)

        return self.databases.add(db_name, db_options)

    def DBDrop(self, db, db_name, *args, **kwargs):
        if not self.databases.exists(db_name):
            error_msg = "Database %s does not exist" % db_name
            errors_logger.error(error_msg)
            return failure(DATABASE_ERROR, error_msg)

        status, content = self.databases.drop(db_name)
        return status, content

    def DBList(self, db, *args, **kwargs):
        return success(self.databases.list())

    def DBRepair(self, db, db_uid, *args, **kwargs):
        db_path = self.databases['paths_index'][db_uid]

        plyvel.RepairDB(db_path)

        return success()

    def _gen_response(self, request, cmd_status, cmd_value):
        if cmd_status == FAILURE_STATUS:
            header = ResponseHeader(status=cmd_status, err_code=cmd_value[0], err_msg=cmd_value[1])
            content = ResponseContent(datas=None)
        else:
            if 'compression' in request.meta:
                compression = request.meta['compression']
            else:
                compression = False

            header = ResponseHeader(status=cmd_status, compression=compression)
            content = ResponseContent(datas=cmd_value, compression=compression)

        return header, content

    def command(self, message, *args, **kwargs):
        status = SUCCESS_STATUS
        err_code, err_msg = None, None

        # DB does not exist
        if message.db_uid and (not message.db_uid in self.databases):
            error_msg = "Database %s doesn't exist" % message.db_uid
            errors_logger.error(error_msg)
            status, value = failure(RUNTIME_ERROR, error_msg)
        # Command not recognized
        elif not message.command in self.handlers:
            error_msg = "Command %s not handled" % message.command
            errors_logger.error(error_msg)
            status, value = failure(KEY_ERROR, error_msg)
        # Valid request
        else:
            if not message.db_uid:
                status, value = self.handlers[message.command](*message.data, **kwargs)
            else:
                database = self.databases[message.db_uid]
                if self.databases.status(database.name) == self.databases.STATUSES.UNMOUNTED:
                    activity_logger.debug("Re-mount %s")
                    self.databases.mount(database.name)

                # Tick last access time
                self.databases[message.db_uid].last_access = time.time()
                status, value = self.handlers[message.command](database.connector, *message.data, **kwargs)

        # Will output a valid ResponseHeader and ResponseContent objects
        return self._gen_response(message, status, value)

########NEW FILE########
__FILENAME__ = args
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import argparse


DEFAULT_CONFIG_FILE = '/etc/elevator/elevator.conf'


def init_parser():
    parser = argparse.ArgumentParser(
        description="Elevator command line manager"
    )
    parser.add_argument('-d', '--daemon', action='store_true', default=False)
    parser.add_argument('-c', '--config', action='store', type=str,
                        default=DEFAULT_CONFIG_FILE)
    # tcp or ipc
    parser.add_argument('-t', '--transport', action='store', type=str)
    parser.add_argument('-b', '--bind', action='store', type=str)
    parser.add_argument('-p', '--port', action='store', type=str)
    parser.add_argument('-w', '--workers', action='store', type=int, default=4)
    parser.add_argument('-v', '--log-level', action='store', type=str, default='INFO')

    return parser

########NEW FILE########
__FILENAME__ = atm
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import threading
import logging
import time


activity_logger = logging.getLogger("activity_logger")


class Majordome(threading.Thread):
    """Ticks every `interval` minutes and unmounts unused databases
    since last tick.

    Inspired of : http://pastebin.com/xNV7hx8h"""
    def __init__(self, supervisor, db_handler, interval, iterations=0):
        threading.Thread.__init__(self)
        self.interval = interval * 60  # Turn it's value in minutes
        self.last_tick = time.time()
        self.iterations = iterations
        self.supervisor = supervisor
        self.db_handler = db_handler
        self.function = self.unmount_unused_db
        self.finished = threading.Event()

    def unmount_unused_db(self):
        """Automatically unmount unused databases on tick"""
        db_last_access = self.db_handler.last_access

        for db, access in db_last_access.iteritems():
            if (access < self.last_tick):
                db_status = self.db_handler[db]['status']
                if db_status == self.db_handler.STATUSES.MOUNTED:
                    self.db_handler.umount(self.db_handler[db]['name'])
                    activity_logger.debug("No activity on {db}, unmouting...".format(db=db))

    def run(self):
        count = 0

        while (not self.finished.is_set() and
               (self.iterations <= 0 or count < self.iterations)):
            self.finished.wait(self.interval)
            if not self.finished.is_set():
                self.function()
                self.last_tick = time.time()
                count += 1

    def cancel(self):
        self.finished.set()

########NEW FILE########
__FILENAME__ = protocol
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import msgpack


## Internal workers supervisor signals
WORKER_STATUS = "STATUS"
WORKER_HALT = "STOP"
WORKER_LAST_ACTION = "LAST_ACTION"


class ServiceMessage(object):
    @staticmethod
    def dumps(data):
        if not isinstance(data, (tuple, list)):
            data = (data, )

        return msgpack.packb(data)

    @staticmethod
    def loads(msg):
        return msgpack.unpackb(msg)

########NEW FILE########
__FILENAME__ = supervisor
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import zmq
import logging

from collections import defaultdict

from elevator.utils.snippets import sec_to_ms

from elevator.backend.worker import Worker
from elevator.backend.protocol import ServiceMessage
from elevator.backend.protocol import WORKER_HALT, WORKER_STATUS,\
                                      WORKER_LAST_ACTION


activity_logger = logging.getLogger("activity_logger")
errors_logger = logging.getLogger("errors_logger")


class Supervisor(object):
    """A remote control to lead them all

    Exposes an internal api to talk to database workers and
    give them orders.
    """
    def __init__(self, zmq_context, databases_store, timeout=3):
        self.databases_store = databases_store
        self.workers = defaultdict(dict)
        self.timeout = sec_to_ms(timeout)

        self.zmq_context = zmq_context
        self.socket = zmq_context.socket(zmq.ROUTER)
        self.socket.setsockopt(zmq.RCVTIMEO, self.timeout)
        self.socket.bind('inproc://supervisor')

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def command(self, instruction,
                workers_ids=None, max_retries=3,
                timeout=None):
        """Command an action to workers.

        An optional list of workers ids can be provided
        as an argument, in order to restrain the command
        to specific workers.
        """
        workers_ids = workers_ids or self.workers.iterkeys()
        timeout = timeout or self.timeout
        responses = []

        for worker_id in workers_ids:
            if worker_id in self.workers:
                worker_socket = self.workers[worker_id]['socket']
                request = ServiceMessage.dumps(instruction)
                self.socket.send_multipart([worker_socket, request], flags=zmq.NOBLOCK)

                retried = 0
                while retried <= max_retries:
                    sockets = dict(self.poller.poll(self.timeout))

                    if sockets and sockets.get(self.socket) == zmq.POLLIN:
                        serialized_response = self.socket.recv_multipart(flags=zmq.NOBLOCK)[1]
                        responses.append(ServiceMessage.loads(serialized_response))
                        break
                    else:
                        retried += 1

                if retried == max_retries:
                    err_msg = "Instruction %s sent to %s failed. Retried %d times"
                    errors_logger.error(err_msg % (instruction, worker_id, retried))

        return responses

    def status(self, worker_id):
        """Fetches a worker status"""
        return self.command(WORKER_STATUS, [worker_id])

    def statuses(self):
        """Fetch workers statuses"""
        return self.command(WORKER_STATUS)

    def stop(self, worker_id):
        """Stop a specific worker"""
        self.command(WORKER_HALT, [worker_id])
        self.workers[worker_id]['thread'].join()
        self.workers.pop(worker_id)

    def stop_all(self):
        """Stop every supervised workers"""
        self.command(WORKER_HALT)

        for worker in self.workers.itervalues():
            worker['thread'].join()

        for _id in self.workers.keys():
            self.workers.pop(_id)

    def last_activity(self, worker_id):
        """Asks a specific worker information about it's
        last activity

        Returns a tuple containing it's latest activity timestamp
        first, and the database affected by it in second
        """
        return self.command(WORKER_LAST_ACTION, [worker_id])

    def last_activity_all(self):
        """Asks every supervised workers informations about it's
        last activity

        Returns a list of tuples containing it's latest activity timestamp
        first, and the database affected by it in second
        """
        return self.command(WORKER_LAST_ACTION)

    def init_workers(self, count):
        """Starts `count` workers.

        Awaits for their id to be received (blocking), and
        registers their socket id and thread reference
        """
        pos = 0

        while pos < count:
            # Start a worker
            worker = Worker(self.zmq_context, self.databases_store)
            worker.start()

            socket_id, response = self.socket.recv_multipart()
            worker_id = ServiceMessage.loads(response)[0]

            self.workers[worker_id]['socket'] = socket_id
            self.workers[worker_id]['thread'] = worker
            pos += 1

########NEW FILE########
__FILENAME__ = worker
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import zmq
import uuid
import time
import logging
import threading

from elevator.api import Handler
from elevator.message import Request, ResponseHeader,\
                             ResponseContent, MessageFormatError
from elevator.utils.patterns import enum
from elevator.constants import SUCCESS_STATUS, FAILURE_STATUS,\
                               REQUEST_ERROR

from elevator.backend.protocol import ServiceMessage
from elevator.backend.protocol import WORKER_STATUS, WORKER_HALT,\
                                      WORKER_LAST_ACTION

activity_logger = logging.getLogger("activity_logger")
errors_logger = logging.getLogger("errors_logger")


class HaltException(Exception):
    pass


class Worker(threading.Thread):
    STATES = enum('PROCESSING', 'IDLE', 'STOPPED')

    def __init__(self, zmq_context, databases, *args, **kwargs):
        threading.Thread.__init__(self)
        self.instructions = {
            WORKER_STATUS: self._status_inst,
            WORKER_HALT: self._stop_inst,
            WORKER_LAST_ACTION: self._last_activity_inst,
        }
        self.uid = uuid.uuid4().hex
        self.zmq_context = zmq_context

        self.state = self.STATES.IDLE

        # Wire backend and remote control sockets
        self.backend_socket = self.zmq_context.socket(zmq.DEALER)
        self.remote_control_socket = self.zmq_context.socket(zmq.DEALER)

        self.databases = databases
        self.handler = Handler(databases)

        self.running = False
        self.last_operation = (None, None)

    def wire_sockets(self):
        """Connects the worker sockets to their endpoints, and sends
        alive signal to the supervisor"""
        self.backend_socket.connect('inproc://backend')
        self.remote_control_socket.connect('inproc://supervisor')
        self.remote_control_socket.send_multipart([ServiceMessage.dumps(self.uid)])

    def _status_inst(self):
        return str(self.state)

    def _stop_inst(self):
        return self.stop()

    def _last_activity_inst(self):
        return self.last_operation

    def handle_service_message(self):
        """Handles incoming service messages from supervisor socket"""
        try:
            serialized_request = self.remote_control_socket.recv_multipart(flags=zmq.NOBLOCK)[0]
        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                return

        instruction = ServiceMessage.loads(serialized_request)[0]

        try:
            response = self.instructions[instruction]()
        except KeyError:
            errors_logger.exception("%s instruction not recognized by worker" % instruction)
            return

        self.remote_control_socket.send_multipart([ServiceMessage.dumps(response)],
                                                  flags=zmq.NOBLOCK)

        # If halt instruction succedded, raise HaltException
        # so the worker event loop knows it has to stop
        if instruction == WORKER_HALT and int(response) == SUCCESS_STATUS:
            raise HaltException()
        return

    def handle_command(self):
        """Handles incoming command messages from backend socket

        Receives incoming messages in a non blocking way,
        sets it's set accordingly to IDLE or PROCESSING,
        and sends the responses in a non-blocking way.
        """
        msg = None
        try:
            sender_id, msg = self.backend_socket.recv_multipart(copy=False, flags=zmq.NOBLOCK)
        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                return
        self.state = self.STATES.PROCESSING

        try:
            message = Request(msg)
        except MessageFormatError as e:
            errors_logger.exception(e.value)
            header = ResponseHeader(status=FAILURE_STATUS,
                                    err_code=REQUEST_ERROR,
                                    err_msg=e.value)
            content = ResponseContent(datas={})
            self.backend_socket.send_multipart([sender_id, header, content], copy=False)
            return

        # Handle message, and execute the requested
        # command in leveldb
        header, response = self.handler.command(message)
        self.last_operation = (time.time(), message.db_uid)

        self.backend_socket.send_multipart([sender_id, header, response], flags=zmq.NOBLOCK, copy=False)
        self.state = self.STATES.IDLE

        return

    def run(self):
        """Non blocking event loop which polls for supervisor
        or backend events"""
        poller = zmq.Poller()
        poller.register(self.backend_socket, zmq.POLLIN)
        poller.register(self.remote_control_socket, zmq.POLLIN)

        # Connect sockets, and send the supervisor
        # alive signals
        self.wire_sockets()

        while (self.state != self.STATES.STOPPED):
            sockets = dict(poller.poll())
            if sockets:
                if sockets.get(self.remote_control_socket) == zmq.POLLIN:
                    try:
                        self.handle_service_message()
                    except HaltException:
                        break

                if sockets.get(self.backend_socket) == zmq.POLLIN:
                    self.handle_command()  # Might change state

    def stop(self):
        """Stops the worker

        Changes it's state to STOPPED.
        Closes it's backend socket.
        Returns SUCCESS_STATUS.
        """
        self.state = self.STATES.STOPPED

        if not self.backend_socket.closed:
            self.backend_socket.close()

        activity_logger.info("Gracefully stopping worker %s" % self.uid)
        return str(SUCCESS_STATUS)

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

from ConfigParser import ConfigParser

from utils.snippets import items_to_dict


class Config(dict):
    """
    Unix shells like environment class. Implements add,
    get, load, flush methods. Handles lists of values too.
    Basically Acts like a basic key/value store.
    """
    def __init__(self, f=None, *args, **kwargs):
        if f:
            self.update_with_file(f)  # Has to be called last!

        self.update(kwargs)
        dict.__init__(self, *args, **kwargs)

    def update_with_file(self, f):
        """
        Updates the environment using an ini file containing
        key/value descriptions.
        """
        config = ConfigParser()

        with open(f, 'r') as f:
            config.readfp(f)

            for section in config.sections():
                self.update(items_to_dict(config.items(section)))

    def reload_from_file(self, f=''):
        self.flush(f)
        self.load(f)

    def update_with_args(self, args):
        """Loads argparse kwargs into environment, as `section`"""
        for (arg, value) in args:
            if value is not None:
                self[arg] = value

    def flush(self):
        """
        Flushes the environment from it's manually
        set attributes.
        """
        for attr in self.attributes:
            delattr(self, attr)

########NEW FILE########
__FILENAME__ = constants
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

## Protocol

# Status codes
SUCCESS_STATUS = 1
FAILURE_STATUS = -1
WARNING_STATUS = -2

# Error codes
TYPE_ERROR = 0
KEY_ERROR = 1
VALUE_ERROR = 2
INDEX_ERROR = 3
RUNTIME_ERROR = 4
OS_ERROR = 5
DATABASE_ERROR = 6
SIGNAL_ERROR = 7
REQUEST_ERROR = 8

# Signals
SIGNAL_BATCH_PUT = 1
SIGNAL_BATCH_DELETE = 0

########NEW FILE########
__FILENAME__ = db
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import os
import uuid
import logging
import plyvel
import ujson as json

from shutil import rmtree
from plyvel import CorruptionError

from .constants import OS_ERROR, DATABASE_ERROR
from .utils.patterns import enum
from .helpers.internals import failure, success


activity_logger = logging.getLogger("activity_logger")
errors_logger = logging.getLogger("errors_logger")


class DatabaseOptions(dict):
    def __init__(self, *args, **kwargs):
        self['create_if_missing'] = True
        self['error_if_exists'] = False
        self['bloom_filter_bits'] = 10  # Value recommended by leveldb doc
        self['paranoid_checks'] = False
        self['lru_cache_size'] = 512 * (1 << 20)  # 512 Mo
        self['write_buffer_size'] = 4 * (1 << 20)  # 4 Mo
        self['block_size'] = 4096
        self['max_open_files'] = 1000

        for key, value in kwargs.iteritems():
            if key in self:
                self[key] = value


class Database(object):
    STATUS = enum('MOUNTED', 'UNMOUNTED')

    def __init__(self, name, path, options,
                 status=STATUS.UNMOUNTED, init_connector=False):
        self.name = name
        self.path = path
        self.status = status
        self.last_access = 0.0
        self._connector = None
        self.options = options

        if init_connector:
            self.set_connector(self.path, **self.options)

    def __del__(self):
        del self._connector

    @property
    def connector(self):
        return self._connector

    @connector.setter
    def connector(self, value):
        if isinstance(value, plyvel.DB) or value is None:
            self._connector = value
        else:
            raise TypeError("Connector whether should be"
                            "a plyvel object or None")

    @connector.deleter
    def connector(self):
        del self._connector

    def set_connector(self, path, *args, **kwargs):
        kwargs.update({'create_if_missing': True})

        try:
            self._connector = plyvel.DB(path, *args, **kwargs)
        except CorruptionError as e:
            errors_logger.exception(e.message)

    def mount(self):
        if self.status is self.STATUS.UNMOUNTED:
            self.set_connector(self.path)

            if self.connector is None:
                return failure(DATABASE_ERROR, "Database %s could not be mounted" % self.path)

            self.status = self.STATUS.MOUNTED
        else:
            return failure(DATABASE_ERROR, "Database %r already mounted" % self.path)

        return success()

    def umount(self):
        if self.status is self.STATUS.MOUNTED:
            self.status = self.STATUS.UNMOUNTED
            del self._connector
            self._connector = None
        else:
            return failure(DATABASE_ERROR, "Database %r already unmounted" % self.name)

        return success()


class DatabaseStore(dict):
    STATUSES = enum('MOUNTED', 'UNMOUNTED')

    def __init__(self, config, *args, **kwargs):
        self.index = dict().fromkeys('name_to_uid')

        self.index['name_to_uid'] = {}
        self['reverse_name_index'] = {}
        self['paths_index'] = {}
        self.store_file = config['database_store']
        self.storage_path = config['databases_storage_path']

        self._global_cache_size = None

        self.load()
        self.mount('default')  # Always mount default

    def __del__(self):
        """
        Explictly shutsdown the internal leveldb connectors
        """
        for uid in self.keys():
            del self[uid]

    @property
    def last_access(self):
        result = {}

        for uid, data in self.iteritems():
            if hasattr(data, 'last_access'):
                result[uid] = data.last_access

        return result

    def extract_store_datas(self):
        """Retrieves database store from file

        If file doesn't exist, or is invalid json,
        and empty store is returned.

        Return
        ------
        store_datas, dict
        """
        try:
            store_datas = json.load(open(self.store_file, 'r'))
        except (IOError, ValueError):
            store_datas = {}

        return store_datas

    def load(self):
        """Loads databases from store file"""
        store_datas = self.extract_store_datas()

        for db_name, db_desc in store_datas.iteritems():
            self.index['name_to_uid'].update({db_name: db_desc['uid']})
            self.update({
                db_desc['uid']: Database(db_name, db_desc['path'], db_desc['options'])
            })

        # Always bootstrap 'default'
        if 'default' not in self.index['name_to_uid']:
            self.add('default')

    def store_update(self, db_name, db_desc):
        """Updates the database store file db_name
        key, with db_desc value"""
        store_datas = self.extract_store_datas()

        store_datas.update({db_name: db_desc})
        json.dump(store_datas, open(self.store_file, 'w'))

    def store_remove(self, db_name):
        """Removes a database from store file"""
        store_datas = self.extract_store_datas()
        store_datas.pop(db_name)
        json.dump(store_datas, open(self.store_file, 'w'))

    def status(self, db_name):
        """Returns the mounted/unmounted database status"""

        db_uid = self.index['name_to_uid'][db_name] if db_name in self.index['name_to_uid'] else None
        return self[db_uid].status

    def mount(self, db_name):
        db_uid = self.index['name_to_uid'][db_name] if db_name in self.index['name_to_uid'] else None
        return self[db_uid].mount()

    def umount(self, db_name):
        db_uid = self.index['name_to_uid'][db_name] if db_name in self.index['name_to_uid'] else None
        return self[db_uid].umount()

    def add(self, db_name, db_options=None):
        """Adds a db to the DatabasesStore object, and sync it
        to the store file"""
        db_options = db_options or DatabaseOptions()
        db_name_is_path = db_name.startswith('.') or ('/' in db_name)
        is_abspath = lambda: not db_name.startswith('.') and ('/' in db_name)

        # Handle case when a db is a path
        if db_name_is_path:
            if not is_abspath():
                return failure(DATABASE_ERROR, "Canno't create database from relative path")
            try:
                new_db_path = db_name
                if not os.path.exists(new_db_path):
                    os.mkdir(new_db_path)
            except OSError as e:
                return failure(OS_ERROR, e.strerror)
        else:
            new_db_path = os.path.join(self.storage_path, db_name)

        path = new_db_path
        database = Database(db_name,
                            path,
                            db_options,
                            status=Database.STATUS.MOUNTED,
                            init_connector=True)

        # Adding db to store, and updating handler
        uid = str(uuid.uuid4())
        self.index['name_to_uid'].update({db_name: uid})
        self.store_update(db_name, {
            'path': path,
            'uid': uid,
            'options': db_options,
        })
        self.update({uid: database})

        return success()

    def drop(self, db_name):
        """Drops a db from the DatabasesHandler, and sync it
        to store file"""
        db_uid = self.index['name_to_uid'].pop(db_name)
        db_path = self[db_uid].path

        self.pop(db_uid)
        self.store_remove(db_name)

        try:
            rmtree(db_path)
        except OSError:
            return failure(DATABASE_ERROR, "Cannot drop db : %s, files not found")

        return success()

    def exists(self, db_name):
        """Checks if a database exists on disk"""
        db_uid = self.index['name_to_uid'][db_name] if db_name in self.index['name_to_uid'] else None

        if db_uid:
            if os.path.exists(self[db_uid].path):
                return True
            else:
                self.drop(db_name)

        return False

    def list(self):
        """Lists all the DatabasesHandler known databases"""
        return [db_name for db_name
                in [key for key
                    in self.index['name_to_uid'].iterkeys()]
                if self.exists(db_name)]

########NEW FILE########
__FILENAME__ = frontend
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import zmq
import logging

errors_logger = logging.getLogger("errors_logger")


class Frontend():
    def __init__(self, config):
        self.config = config
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)

        endpoint = ':'.join([self.config['bind'], self.config['port']])
        self.host = self._gen_bind_adress(self.config['transport'], endpoint)
        self.socket.bind(self.host)

    def __del__(self):
        self.socket.close()
        self.context.term()

    def _gen_bind_adress(self, transport, endpoint):
        if transport == 'ipc':
            if not 'unixsocket' in self.config:
                err_msg = "Ipc transport layer was selected, but no unixsocket "\
                          "path could be found in conf file"
                errors_logger.exception(err_msg)
                raise KeyError(err_msg)
            return '{0}://{1}'.format(transport, self.config['unixsocket'])

        else:  # consider it's tcp
            return '{0}://{1}'.format(transport, endpoint)

########NEW FILE########
__FILENAME__ = internals
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

from __future__ import absolute_import

from ..constants import FAILURE_STATUS, SUCCESS_STATUS, WARNING_STATUS


def failure(err_code, err_msg):
    """Returns a formatted error status and content"""
    return (FAILURE_STATUS, [err_code, err_msg])


def success(content=None):
    """Returns a formatted success status and content"""
    return (SUCCESS_STATUS, content)


def warning(error_code, error_msg, content):
    """Returns a formatted warning status and content"""
    return (WARNING_STATUS, [error_code, error_msg, content])

########NEW FILE########
__FILENAME__ = log
# -*- coding:utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import sys
import logging
import traceback


def loglevel_from_str(log_level_str):
    log_level_str = log_level_str.upper()
    numeric_level = getattr(logging, log_level_str, None)

    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level_str)

    return numeric_level


def setup_loggers(config):
    activity_log_file = config['activity_log']
    errors_log_file = config['errors_log']

    # Compute numeric log level value from string
    # ex: "DEBUG"
    log_level = loglevel_from_str(config['log_level'])

    # Set up logging format and formatter instance
    log_format = "[%(asctime)s] %(levelname)s %(funcName)s : %(message)s"
    formatter = logging.Formatter(log_format)

    # Set up logging streams
    stdout_stream = logging.StreamHandler(sys.stdout)
    stdout_stream.setFormatter(formatter)
    activity_file_stream = logging.FileHandler(activity_log_file)
    activity_file_stream.setFormatter(formatter)
    errors_file_stream = logging.FileHandler(errors_log_file)
    errors_file_stream.setFormatter(formatter)

    # Set up activity logger
    activity_logger = logging.getLogger("activity_logger")
    activity_logger.setLevel(log_level)
    activity_logger.addHandler(activity_file_stream)
    activity_logger.addHandler(stdout_stream)

    # Setup up errors logger
    errors_logger = logging.getLogger("errors_logger")
    errors_logger.setLevel(logging.WARNING)
    errors_logger.addHandler(errors_file_stream)

    return activity_logger, errors_logger


def log_critical(e):
    errors_logger = logging.getLogger("errors_logger")
    tb = traceback.format_exc()

    # Log into errors log
    errors_logger.critical(''.join(tb))
    errors_logger.critical('{0}: {1}'.format(type(e), e.message))

    # Log into stderr
    logging.critical(''.join(tb))
    logging.critical('{0}: {1}'.format(type(e), e.message))

########NEW FILE########
__FILENAME__ = message
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

from __future__ import absolute_import

import msgpack
import logging
import lz4

from .constants import FAILURE_STATUS

activity_logger = logging.getLogger("activity_logger")
errors_logger = logging.getLogger("errors_logger")


class MessageFormatError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Request(object):
    """Handler objects for client requests messages

    Format :
    {
        'meta': {...},
        'cmd': 'GET',
        'uid': 'mysuperduperdbuid',
        'args': [...],
    }
    """
    def __init__(self, raw_message):
        self.message = msgpack.unpackb(raw_message)
        self.meta = self.message.get('meta', {})
        activity_logger.debug('<Request ' + str(self.message) + '>')

        try:
            self.db_uid = self.message.get('uid')  # In some case db_uid should be None
            self.command = self.message['cmd']
            self.data = self.message['args']  # __getitem__ will raise if !key
        except KeyError:
            errors_logger.exception("Invalid request message : %s" % self.message)
            raise MessageFormatError("Invalid request message : %r" % self.message)


class ResponseContent(tuple):
    """Handler objects for responses messages

    Format:
    {
        'meta': {
            'status': 1|0|-1,
            'err_code': null|0|1|[...],
            'err_msg': '',
        },
        'datas': [...],
    }
    """
    def __new__(cls, *args, **kwargs):
        response = {
            'datas': cls._format_datas(kwargs['datas']),
        }
        activity_logger.debug('<Response ' + str(response['datas']) + '>')
        msg = msgpack.packb(response)

        if kwargs.pop('compression', False) is True:
            msg = lz4.dumps(msg)

        return msg

    @classmethod
    def _format_datas(cls, datas):
        if datas and not isinstance(datas, (tuple, list)):
            datas = [datas]
        return datas


class ResponseHeader(dict):
    def __new__(cls, *args, **kwargs):
        header = {
            'status': kwargs.pop('status'),
            'err_code': kwargs.pop('err_code', None),
            'err_msg': kwargs.pop('err_msg', None),
            'compression': kwargs.pop('compression', False)
        }
        activity_logger.debug('<ResponseHeader ' + str(header) + '>')

        for key, value in kwargs.iteritems():
            header.update({key: value})

        return msgpack.packb(header)

########NEW FILE########
__FILENAME__ = server
# -*- coding:utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import sys
import zmq
import logging
import procname

from lockfile.linklockfile import LinkLockFile

from elevator import args
from elevator.db import DatabaseStore
from elevator.config import Config
from elevator.log import setup_loggers, log_critical
from elevator.backend import Backend
from elevator.frontend import Frontend
from elevator.utils.daemon import daemon


def setup_process_name(config_file):
    config = ' -c {0} '.format(config_file)
    process_name = 'elevator' + config

    procname.setprocname(process_name)


def runserver(config):
    setup_loggers(config)
    activity_logger = logging.getLogger("activity_logger")

    databases = DatabaseStore(config)
    backend = Backend(databases, config)
    frontend = Frontend(config)

    poller = zmq.Poller()
    poller.register(backend.socket, zmq.POLLIN)
    poller.register(frontend.socket, zmq.POLLIN)

    activity_logger.info('Elevator server started on %s' % frontend.host)

    while True:
        try:
            sockets = dict(poller.poll())
            if frontend.socket in sockets:
                if sockets[frontend.socket] == zmq.POLLIN:
                    msg = frontend.socket.recv_multipart(copy=False)
                    backend.socket.send_multipart(msg, copy=False)

            if backend.socket in sockets:
                if sockets[backend.socket] == zmq.POLLIN:
                    msg = backend.socket.recv_multipart(copy=False)
                    frontend.socket.send_multipart(msg, copy=False)
        except KeyboardInterrupt:
            activity_logger.info('Gracefully shuthing down workers')
            del backend
            activity_logger.info('Stopping frontend')
            del frontend
            activity_logger.info('Done')
            return
        except Exception as e:
            log_critical(e)
            del backend
            del frontend
            return

def main():
    cmdline = args.init_parser().parse_args(sys.argv[1:])
    config = Config(cmdline.config)

    config.update_with_args(cmdline._get_kwargs())
    setup_process_name(cmdline.config)

    if config['daemon'] is True:
        daemon_context = daemon(pidfile=config['pidfile'])

        with daemon_context:
            runserver(config)
    else:
        runserver(config)

########NEW FILE########
__FILENAME__ = daemon
# Copyright 2013 by Eric Suh
# Copyright (c) 2013 Theo Crevon
# This code is freely licensed under the MIT license found at
# <http://opensource.org/licenses/MIT>

import sys
import os
import errno
import atexit
import signal
import time
import subprocess

from contextlib import contextmanager


class PIDFileError(Exception):
    pass


@contextmanager
def pidfile(path, pid):
    make_pidfile(path, pid)
    yield
    remove_pidfile(path)


def readpid(path):
    with open(path) as f:
        pid = f.read().strip()
    if not pid.isdigit():
        raise PIDFileError('Malformed PID file at path {}'.format(path))
    return pid


def pidfile_is_stale(path):
    '''Checks if a PID file already exists there, and if it is, whether it
    is stale. Returns True if a PID file exists containing a PID for a
    process that does not exist any longer.'''
    try:
        pid = readpid(path)
    except IOError as e:
        if e.errno == errno.ENOENT:
            return False # nonexistant file isn't stale
        raise e
    if pid == '' or not pid.isdigit():
        raise PIDFileError('Malformed PID file at path {}'.format(path))
    return not is_pid_running(pid)


def _ps():
    raw = subprocess.check_output(['ps', '-eo', 'pid'])
    return [line.strip() for line in raw.split('\n')[1:] if line != '']


def is_pid_running(pid):
    try:
        procs = os.listdir('/proc')
    except OSError as e:
        if e.errno == errno.ENOENT:
            return str(pid) in _ps()
        raise e
    return str(pid) in [proc for proc in procs if proc.isdigit()]


def make_pidfile(path, pid):
    '''Create a PID file. '''
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except OSError as e:
        if e.errno == errno.EEXIST:
            if pidfile_is_stale(path):
                remove_pidfile(path)
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            else:
                raise PIDFileError(
                    'Non-stale PID file already exists at {}'.format(path))

    pidf = os.fdopen(fd, 'w')
    pidf.write(str(pid))
    pidf.flush()
    pidf.close()


def remove_pidfile(path):
    try:
        os.remove(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


class daemon(object):
    'Context manager for POSIX daemon processes'

    def __init__(self,
                 pidfile=None,
                 workingdir='/',
                 umask=0,
                 stdin=None,
                 stdout=None,
                 stderr=None,
                ):
        self.pidfile = pidfile
        self.workingdir = workingdir
        self.umask = umask

        devnull = os.open(os.devnull, os.O_RDWR)
        self.stdin = stdin.fileno() if stdin is not None else devnull
        self.stdout = stdout.fileno() if stdout is not None else devnull
        self.stderr = stderr.fileno() if stderr is not None else self.stdout

    def __enter__(self):
        self.daemonize()
        return

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.stop()
        return

    def daemonize(self):
        '''Set up a daemon.

        There are a few major steps:
        1. Changing to a working directory that won't go away
        2. Changing user permissions mask
        3. Forking twice to detach from terminal and become new process leader
        4. Redirecting standard input/output
        5. Creating a PID file'''

        # Set up process conditions
        os.chdir(self.workingdir)
        os.umask(self.umask)

        # Double fork to daemonize
        _getchildfork(1)
        os.setsid()
        _getchildfork(2)

        # Redirect standard input/output files
        sys.stdin.flush()
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(self.stdin, sys.stdin.fileno())
        os.dup2(self.stdout, sys.stdout.fileno())
        os.dup2(self.stderr, sys.stderr.fileno())

        # Create PID file
        if self.pidfile is not None:
            pid = str(os.getpid())
            try:
                make_pidfile(self.pidfile, pid)
            except PIDFileError as e:
                sys.stederr.write('Creating PID file failed. ({})'.format(e))
                os._exit(os.EX_OSERR)
        atexit.register(self.stop)

    def stop(self):
        if self.pidfile is not None:
            pid = readpid(self.pidfile)
            try:
                while True:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.1)
            except OSError as e:
                if e.errno == errno.ESRCH:
                    remove_pidfile(self.pidfile)
                else:
                    raise

def _getchildfork(n):
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(os.EX_OK) # Exit in parent
    except OSError as e:
        sys.stederr.write('Fork #{} failed: {} ({})\n'.format(
            n, e.errno, e.strerror))
        os._exit(os.EX_OSERR)

########NEW FILE########
__FILENAME__ = decorators
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import collections
import functools
import time

from itertools import ifilterfalse


class Counter(dict):
    'Mapping where default values are zero'
    def __missing__(self, key):
        return 0


def lru_cache(maxsize=100):
    '''Least-recently-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    '''
    maxqueue = maxsize * 10

    def decorating_function(user_function,
            len=len, iter=iter, tuple=tuple, sorted=sorted, KeyError=KeyError):
        cache = {}                   # mapping of args to results
        queue = collections.deque()  # order that keys have been used
        refcount = Counter()         # times each key is in the queue
        sentinel = object()          # marker for looping around the queue
        kwd_mark = object()          # separate positional and keyword args

        # lookup optimizations (ugly but fast)
        queue_append, queue_popleft = queue.append, queue.popleft
        queue_appendleft, queue_pop = queue.appendleft, queue.pop

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            # cache key records both positional and keyword args
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))

            # record recent use of this key
            queue_append(key)
            refcount[key] += 1

            # get cache entry or compute if not found
            try:
                result = cache[key]
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                cache[key] = result
                wrapper.misses += 1

                # purge least recently used cache entry
                if len(cache) > maxsize:
                    key = queue_popleft()
                    refcount[key] -= 1
                    while refcount[key]:
                        key = queue_popleft()
                        refcount[key] -= 1
                    try:
                        del cache[key], refcount[key]
                    except KeyError:
                        pass

            # periodically compact the queue by eliminating duplicate keys
            # while preserving order of most recent access
            if len(queue) > maxqueue:
                refcount.clear()
                queue_appendleft(sentinel)
                for key in ifilterfalse(refcount.__contains__,
                                        iter(queue_pop, sentinel)):
                    queue_appendleft(key)
                    refcount[key] = 1

            return result

        def clear():
            cache.clear()
            queue.clear()
            refcount.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper
    return decorating_function


# @Report
# Number of times to indent output
# A list is used to force access by reference
__report_indent = [0]


def time_it(function):
    """
    Decorator whichs times a function execution.
    """
    def wrap(*args, **kwargs):
        start = time.time()
        r = function(*args, **kwargs)
        end = time.time()
        print "%s (%0.3f ms)" % (function.func_name, (end - start) * 1000)
        return r
    return wrap


def report(fn):
    """Decorator to print information about a function
    call for use while debugging.
    Prints function name, arguments, and call number
    when the function is called. Prints this information
    again along with the return value when the function
    returns.
    """

    def wrap(*params, **kwargs):
        call = wrap.callcount = wrap.callcount + 1

        indent = ' ' * __report_indent[0]
        fc = "%s(%s)" % (fn.__name__, ', '.join(
            [a.__repr__() for a in params] +
            ["%s = %s" % (a, repr(b)) for a, b in kwargs.items()]
        ))

        print "%s%s called [#%s]" % (indent, fc, call)
        __report_indent[0] += 1
        ret = fn(*params, **kwargs)
        __report_indent[0] -= 1
        print "%s%s returned %s [#%s]" % (indent, fc, repr(ret), call)

        return ret
    wrap.callcount = 0
    return wrap


def memoize(func, cache, num_args):
    """
    Wrap a function so that results for any argument tuple are stored in
    'cache'. Note that the args to the function must be usable as dictionary
    keys.

    Only the first num_args are considered when creating the key.
    """
    @functools.wraps(func)
    def wrapper(*args):
        mem_args = args[:num_args]
        if mem_args in cache:
            return cache[mem_args]
        result = func(*args)
        cache[mem_args] = result
        return result
    return wrapper


###   Cached Property   ###


class _Missing(object):
    """cached_property decorator dependency"""
    def __repr__(self):
        return 'no value'

    def __reduce__(self):
        return '_missing'


_missing = _Missing()


class cached_property(object):
    """A decorator that converts a function into a lazy property.  The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

        class Foo(object):

            @cached_property
            def foo(self):
                # calculate something important here
                return 42

    The class has to have a `__dict__` in order for this property to
    work.

    .. versionchanged:: 0.6
       the `writeable` attribute and parameter was deprecated.  If a
       cached property is writeable or not has to be documented now.
       For performance reasons the implementation does not honor the
       writeable setting and will always make the property writeable.
    """
    # implementation detail: this property is implemented as non-data
    # descriptor.  non-data descriptors are only invoked if there is
    # no entry with the same name in the instance's __dict__.
    # this allows us to completely get rid of the access function call
    # overhead.  If one choses to invoke __get__ by hand the property
    # will still work as expected because the lookup logic is replicated
    # in __get__ for manual invocation.

    def __init__(self, func, name=None, doc=None, writeable=False):
        if writeable:
            from warnings import warn
            warn(DeprecationWarning('the writeable argument to the '
                                    'cached property is a noop since 0.6 '
                                    'because the property is writeable '
                                    'by default for performance reasons'))

        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

########NEW FILE########
__FILENAME__ = patterns
from collections import Sequence

# Enums beautiful python implementation
# Used like this :
# Numbers = enum('ZERO', 'ONE', 'TWO')
# >>> Numbers.ZERO
# 0
# >>> Numbers.ONE
# 1
# Found here: http://stackoverflow.com/questions/36932/whats-the-best-way-to-implement-an-enum-in-python
def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)


class Singleton(type):
    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(name, bases, dict)
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
        return cls.instance

    def __del__(cls, *args, **kw):
        cls.instance is None


class DestructurationError(Exception):
    pass


def destructurate(container):
    try:
        return container[0], container[1:]
    except (KeyError, AttributeError):
        raise DestructurationError("Can't destructurate a non-sequence container")

########NEW FILE########
__FILENAME__ = snippets
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Checks if a str is a word(unique),
# or an expression (more than one word).
is_expression = lambda s: ' ' in s.strip()


# Lambda function which tranforms a ConfigParser items
# list of tuples object into a dictionnary,
# doesn't use dict comprehension in order to keep 2.6
# backward compatibility.
def items_to_dict(items):
    res = {}

    for k, v in items:
        res[k] = v
    return res

# Iterates through a sequence of size `clen`
chunks = lambda seq, clen: [seq[i:(i + clen)] for i in xrange(0, len(seq), clen)]

# Decodes a list content from a given charset
ldecode = lambda list, charset: [string.decode(charset) for string in charset]

# Encodes a list content from a given charset
lencode = lambda list, charset: [string.encode(charset) for string in charset]

# Checks if a sequence is ascendently sorted
asc_sorted = lambda seq: all(seq[i] <= seq[i + 1] for i in xrange(len(seq) - 1))

# idem descending
desc_sorted = lambda seq: all(seq[i] >= seq[i + 1] for i in xrange(len(seq) - 1))

# Convert bytes to Mo
from_bytes_to_mo = lambda bytes: bytes / 1048576

#Convert Mo to bytes
from_mo_to_bytes = lambda mo: mo * 1048576

# Convert seconds to milliseconds
sec_to_ms = lambda s: s * 1000

########NEW FILE########
__FILENAME__ = args
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import argparse

DEFAULT_CONFIG_FILE = '/etc/elevatord.conf'


def init_parser():
    parser = argparse.ArgumentParser(description="Elevator command line client")
    parser.add_argument('-c', '--config', action='store', type=str,
                        default=DEFAULT_CONFIG_FILE)
    # tcp or ipc
    parser.add_argument('-t', '--protocol', action='store', type=str,
                        default='tcp')
    parser.add_argument('-b', '--endpoint', action='store', type=str,
                        default='127.0.0.1:4141')

    return parser

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

from __future__ import absolute_import

import zmq

from elevator.constants import *

from .io import output_result
from .errors import *
from .helpers import success, fail
from .message import Request, ResponseHeader, Response


class Client(object):
    def __init__(self, *args, **kwargs):
        self.protocol = kwargs.pop('protocol', 'tcp')
        self.endpoint = kwargs.pop('endpoint', '127.0.0.1:4141')
        self.host = "%s://%s" % (self.protocol, self.endpoint)

        self.context = None
        self.socket = None
        self.timeout = kwargs.pop('timeout', 10000)

        self.db_uid = None
        self.db_name = None

        self.setup_socket()

        if self.ping():
            self.connect()
        else:
            failure_msg = 'No elevator server hanging on {0}://{1}'.format(self.protocol, self.endpoint)
            output_result(FAILURE_STATUS, failure_msg)

    def __del__(self):
        self.socket.close()
        self.context.term()

    def ping(self, *args, **kwargs):
        pings = True
        timeout = kwargs.pop('timeout', 1000)
        orig_timeout = self.timeout
        self.socket.setsockopt(zmq.RCVTIMEO, timeout)

        request = Request(db_uid=None, command="PING", args=[])
        self.socket.send_multipart([request])

        try:
            self.socket.recv_multipart()
        except zmq.core.error.ZMQError:
            pings = False

        # Restore original timeout
        self.timeout = orig_timeout
        self.socket.setsockopt(zmq.RCVTIMEO, self.timeout)

        return pings

    def connect(self, db_name=None, *args, **kwargs):
        db_name = 'default' if db_name is None else db_name
        status, datas = self.send_cmd(None, 'DBCONNECT', [db_name], *args, **kwargs)

        if status == FAILURE_STATUS:
            return status, datas
        else:
            self.db_uid = datas
            self.db_name = db_name

    def setup_socket(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.XREQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.RCVTIMEO, self.timeout)
        self.socket.connect(self.host)

    def teardown_socket(self):
        self.socket.close()
        self.context.term()

    def _process_request(self, command, arguments):
        if command in ["MGET"] and arguments:
            return command, [arguments]
        return command, arguments

    def _process_response(self, req_cmd, res_datas):
        if req_cmd in ["GET", "DBCONNECT", "PING"] and res_datas:
            return res_datas[0]
        return res_datas

    def send_cmd(self, db_uid, command, arguments, *args, **kwargs):
        command, arguments = self._process_request(command, arguments)
        self.socket.send_multipart([Request(db_uid=db_uid,
                                                             command=command,
                                                             args=arguments,
                                                             meta={})],)

        try:
            raw_header, raw_response = self.socket.recv_multipart()
            header = ResponseHeader(raw_header)
            response = Response(raw_response)

            if header.status == FAILURE_STATUS:
                return fail(ELEVATOR_ERROR[header.err_code], header.err_msg)
        except zmq.core.error.ZMQError:
            return fail("TimeoutError", "Server did not respond in time")

        return success(self._process_response(command, response.datas))

########NEW FILE########
__FILENAME__ = errors
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

from __future__ import absolute_import

from elevator.constants import *


ELEVATOR_ERROR = {
    TYPE_ERROR: 'TypeError',
    KEY_ERROR: 'KeyError',
    VALUE_ERROR: 'ValueError',
    INDEX_ERROR: 'IndexError',
    RUNTIME_ERROR: 'RuntimeError',
    OS_ERROR: 'OSError',
    DATABASE_ERROR: 'DatabaseError',
    SIGNAL_ERROR: 'SignalError',
}

########NEW FILE########
__FILENAME__ = helpers
# -*- coding:utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

from elevator.constants import SUCCESS_STATUS, FAILURE_STATUS


def fail(type, msg):
    return FAILURE_STATUS, "Error : " + ', '.join([type.upper(), msg])


def success(datas):
    return SUCCESS_STATUS, datas

########NEW FILE########
__FILENAME__ = io
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import shlex

from clint.textui import puts, colored

from elevator.utils.patterns import destructurate

from .helpers import FAILURE_STATUS


def prompt(*args, **kwargs):
    current_db = kwargs.pop('current_db', 'default')

    if current_db:
        pattern = '@ Elevator.{db} => '.format(db=current_db)
    else:
        pattern = '! Offline => '
    input_str = raw_input(pattern)

    return input_str


def parse_input(input_str, *args, **kwargs):
    input_str = shlex.split(input_str.strip())
    command, args = destructurate(input_str)
    return command.upper(), args


def output_result(status, result, *args, **kwargs):
    if result:
        if status == FAILURE_STATUS:
            puts(colored.red(str(result)))
        else:
            puts(str(result))

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

from __future__ import absolute_import

import sys

from .io import prompt, parse_input, output_result
from .client import Client
from .args import init_parser


def main():
    args = init_parser().parse_args(sys.argv[1:])
    client = Client(protocol=args.protocol,
                         endpoint=args.endpoint)

    try:
        while True:
            input_str = prompt(current_db=client.db_name)

            if input_str:
                command, args = parse_input(input_str)

                if not command == "DBCONNECT":
                    status, result = client.send_cmd(client.db_uid, command, args)
                    output_result(status, result)
                else:
                    client.connect(*args)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = message
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import msgpack
import logging


errors_logger = logging.getLogger("errors_logger")


class MessageFormatError(Exception):
    pass


class Request(object):
    """Handler objects for frontend->backend objects messages"""
    def __new__(cls, *args, **kwargs):
        try:
            content = {
                'meta': kwargs.pop('meta', {}),
                'uid': kwargs.get('db_uid'),  # uid can eventually be None
                'cmd': kwargs.pop('command'),
                'args': kwargs.pop('args'),
            }
        except KeyError:
            raise MessageFormatError("Invalid request format : %s" % str(kwargs))

        return msgpack.packb(content)


class Response(object):
    def __init__(self, raw_message, *args, **kwargs):
        message = msgpack.unpackb(raw_message)

        try:
            self.datas = message['datas']
        except KeyError:
            errors_logger.exception("Invalid response message : %s" %
                                    message)
            raise MessageFormatError("Invalid response message")


class ResponseHeader(object):
    def __init__(self, raw_header):
        header = msgpack.unpackb(raw_header)

        try:
            self.status = header.pop('status')
            self.err_code = header.pop('err_code')
            self.err_msg = header.pop('err_msg')
        except KeyError:
            errors_logger.exception("Invalid response header : %s" %
                                    header)
            raise MessageFormatError("Invalid response header")

        for key, value in header.iteritems():
            setattr(self, key, value)

########NEW FILE########
__FILENAME__ = install
#!/usr/bin/env python
# -*- coding: utf-8 -*-


from fabric.api import *
from fabric.context_managers import quiet


#
# DEPENDENCIES BUILD
#
@task
def leveldb():
    """Locally builds and install leveldb system-wide"""
    with lcd('/tmp'):
        with quiet():
            local('mkdir leveldb_install')

        with lcd('leveldb_install'):
            local('svn checkout http://snappy.googlecode.com/svn/trunk/ snappy-read-only')

            with lcd('snappy-read-only'):
                local('./autogen.sh && ./configure --enable-shared=no --enable-static=yes')
                local("make clean && make CXXFLAGS='-g -O2 -fPIC'")

            local('git clone https://code.google.com/p/leveldb/ || (cd leveldb; git pull)')

            with lcd('leveldb'):
                local('make clean')
                local("make LDFLAGS='-L../snappy-read-only/.libs/ -Bstatic -lsnappy -shared' "
                            "OPT='-fPIC -O2 -DNDEBUG -DSNAPPY -I../snappy-read-only' "
                            "SNAPPY_CFLAGS='' ")

    sudo('cp -rf /tmp/leveldb_install/leveldb/libleveldb.so* /usr/local/lib')
    sudo('cp -rf /tmp/leveldb_install/leveldb/include/leveldb /usr/local/include')
    local('rm -rf /tmp/leveldb_install')


@task
def zmq():
    """Locally builds and install zeromq-3.2 system wide"""
    with lcd('/tmp'):
        local('wget http://download.zeromq.org/zeromq-3.2.0-rc1.tar.gz;'
              'tar xf zeromq-3.2.0-rc1.tar.gz')
        with lcd('zeromq-3.2.0'):
            local('chmod -R 777 .')
            local('./autogen.sh ; ./configure')
            local('make ; sudo make install')

    local('rm -rf /tmp/zeromq-3.2.0-rc1.tar.gz')


@task
def all():
    build_zmq()
    build_leveldb()

########NEW FILE########
__FILENAME__ = client_tests

########NEW FILE########
__FILENAME__ = io_tests

########NEW FILE########
__FILENAME__ = api_tests
import unittest2
import shutil
import msgpack
import os
import plyvel

from nose.tools import *

from elevator.api import Handler
from elevator.db import DatabaseStore
from elevator.constants import *
from elevator.message import Request

from .fakers import gen_test_config


class ApiTests(unittest2.TestCase):
    def _bootstrap_db(self, db):
        for val in xrange(9):
            db.put(str(val), str(val + 10))

    def setUp(self):
        self.store = '/tmp/store.json'
        self.dest = '/tmp/dbs'
        self.config = gen_test_config()
        if not os.path.exists(self.dest):
            os.mkdir(self.dest)

        self.databases = DatabaseStore(self.config)
        self.default_db_uid = self.databases.index['name_to_uid']['default']
        self._bootstrap_db(self.databases[self.default_db_uid].connector)
        self.handler = Handler(self.databases)

    def tearDown(self):
        self.databases.__del__()
        del self.handler
        os.remove(self.store)
        shutil.rmtree(self.dest)

    def request_message(self, command, args, db_uid=None):
        db_uid = db_uid or self.default_db_uid
        return Request(msgpack.packb({
            'uid': db_uid,
            'cmd': command,
            'args': args,
        }))

    def test_command_with_existing_command(self):
        message = self.request_message('GET', ['1'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertNotEqual(plain_content['datas'], None)

    def test_command_with_non_existing_command(self):
        message = self.request_message('COTCOT', ['testarg'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        self.assertEqual(plain_header['status'], FAILURE_STATUS)
        self.assertEqual(plain_header['err_code'], KEY_ERROR)

    def test_command_with_invalid_db_uid(self):
        message = self.request_message('PUT', ['1', '1'], db_uid='failinguid')
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        self.assertEqual(plain_header['status'], FAILURE_STATUS)
        self.assertEqual(plain_header['err_code'], RUNTIME_ERROR)

    def test_get_of_existing_key(self):
        message = self.request_message('GET', ['1'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(plain_content['datas'], ('11',))

    def test_get_of_non_existing_key(self):
        message = self.request_message('GET', ['abc123'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        self.assertEqual(plain_header['status'], FAILURE_STATUS)
        self.assertEqual(plain_header['err_code'], KEY_ERROR)

    def test_mget_of_existing_keys(self):
        message = self.request_message('MGET', [['1', '2', '3']])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(plain_content['datas'], ('11', '12', '13'))

    def test_mget_of_not_fully_existing_keys(self):
        message = self.request_message('MGET', [['1', '2', 'touptoupidou']])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], WARNING_STATUS)
        self.assertEqual(len(plain_content['datas']), 3)
        self.assertEqual(plain_content['datas'], ('11', '12', None))

    def test_put_of_valid_key(self):
        message = self.request_message('PUT', ['a', '1'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(plain_content['datas'], None)

    def test_put_of_invalid_value(self):
        message = self.request_message('PUT', ['a', 1])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        self.assertEqual(plain_header['status'], FAILURE_STATUS)
        self.assertEqual(plain_header['err_code'], TYPE_ERROR)

    def test_delete(self):
        message = self.request_message('DELETE', ['9'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(plain_content['datas'], None)

    def test_exists_of_existing_key(self):
        message = self.request_message('EXISTS', ['1'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(plain_content['datas'], True)

    def test_exists_of_non_existing_key_1(self):
        message = self.request_message('EXISTS', ['0'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(plain_content['datas'], False)

    def test_exists_of_non_existing_key_2(self):
        message = self.request_message('EXISTS', ['non_existing'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(plain_content['datas'], False)

    def test_range(self):
        message = self.request_message('RANGE', ['1', '2'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertIsInstance(plain_content['datas'], tuple)
        self.assertEqual(plain_content['datas'][0], ('1', '11'))
        self.assertEqual(plain_content['datas'][1], ('2', '12'))

    def test_range_with_keys_only(self):
        message = self.request_message('RANGE', ['1', '2', True, False])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertIsInstance(plain_content['datas'], tuple)

        self.assertEqual(len(plain_content['datas'][0]), 1)
        self.assertEqual(len(plain_content['datas'][1]), 1)

        self.assertEqual(plain_content['datas'][0], ('1'))
        self.assertEqual(plain_content['datas'][1], ('2'))

    def test_range_of_len_one(self):
        """Should still return a tuple of tuple"""
        message = self.request_message('RANGE', ['1', '1'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertIsInstance(plain_content['datas'], tuple)
        self.assertEqual(len(plain_content), 1)
        self.assertEqual(plain_content['datas'], (('1', '11'),))

    def test_slice_with_limit(self):
        message = self.request_message('SLICE', ['1', 3])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertIsInstance(plain_content['datas'], tuple)
        self.assertEqual(len(plain_content['datas']), 3)
        self.assertEqual(plain_content['datas'][0], ('1', '11'))
        self.assertEqual(plain_content['datas'][1], ('2', '12'))
        self.assertEqual(plain_content['datas'][2], ('3', '13'))

    def test_slice_with_limit_value_of_one(self):
        message = self.request_message('SLICE', ['1', 1])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertIsInstance(plain_content['datas'], tuple)
        self.assertEqual(len(plain_content), 1)
        self.assertEqual(plain_content['datas'], (('1', '11'),))

    def test_batch_with_valid_collection(self):
        message = self.request_message('BATCH', args=[
            [(SIGNAL_BATCH_PUT, 'a', 'a'),
             (SIGNAL_BATCH_PUT, 'b', 'b'),
             (SIGNAL_BATCH_PUT, 'c', 'c')],
        ])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(plain_content['datas'], None)

    def test_batch_with_invalid_signals(self):
        message = self.request_message('BATCH', [
            [(-5, 'a', 'a'),
             (-5, 'b', 'b'),
             (-5, 'c', 'c')],
        ])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        self.assertEqual(plain_header['status'], FAILURE_STATUS)
        self.assertEqual(plain_header['err_code'], SIGNAL_ERROR)

    def test_batch_with_invalid_collection_datas_type(self):
        message = self.request_message('BATCH', [
            [(SIGNAL_BATCH_PUT, 'a', 1),
             (SIGNAL_BATCH_PUT, 'b', 2),
             (SIGNAL_BATCH_PUT, 'c', 3)],
        ])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        self.assertEqual(plain_header['status'], FAILURE_STATUS)
        self.assertEqual(plain_header['err_code'], TYPE_ERROR)

    def test_connect_to_valid_database(self):
        message = Request(msgpack.packb({
            'uid': None,
            'cmd': 'DBCONNECT',
            'args': ['default'],
        }))
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertIsNotNone(plain_content)

    def test_connect_to_invalid_database(self):
        message = Request(msgpack.packb({
                'uid': None,
                'cmd': 'DBCONNECT',
                'args': ['dadaislikeadad']
        }))
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        self.assertEqual(plain_header['status'], FAILURE_STATUS)
        self.assertEqual(plain_header['err_code'], DATABASE_ERROR)

    def test_connect_automatically_mounts_and_unmounted_db(self):
        # Unmount by hand the database
        db_uid = self.handler.databases.index['name_to_uid']['default']
        self.handler.databases[db_uid].status = self.handler.databases.STATUSES.UNMOUNTED
        self.handler.databases[db_uid].connector = None

        message = Request(msgpack.packb({
                'db_uid': None,
                'cmd': 'DBCONNECT',
                'args': ['default']
        }))
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(self.handler.databases[db_uid].status, self.handler.databases.STATUSES.MOUNTED)
        self.assertIsInstance(self.handler.databases[db_uid].connector, plyvel.DB)

    def test_create_valid_db(self):
        message = self.request_message('DBCREATE', ['testdb'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(plain_content['datas'], None)

    def test_create_already_existing_db(self):
        message = self.request_message('DBCREATE', ['default'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        self.assertEqual(plain_header['status'], FAILURE_STATUS)
        self.assertEqual(plain_header['err_code'], DATABASE_ERROR)

    def test_drop_valid_db(self):
        message = self.request_message('DBDROP', ['default'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(plain_content['datas'], None)

        # Please teardown with something to destroy
        # MOUAHAHAHAH... Hum sorry.
        os.mkdir('/tmp/default')

    def test_drop_non_existing_db(self):
        message = self.request_message('DBDROP', ['testdb'])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        self.assertEqual(plain_header['status'], FAILURE_STATUS)
        self.assertEqual(plain_header['err_code'], DATABASE_ERROR)

    def test_list_db(self):
        message = self.request_message('DBLIST', [])
        header, content = self.handler.command(message)

        plain_header = msgpack.unpackb(header)
        plain_content = msgpack.unpackb(content)

        self.assertEqual(plain_header['status'], SUCCESS_STATUS)
        self.assertEqual(len(plain_content), 1)
        self.assertEqual(plain_content['datas'], ('default',))

########NEW FILE########
__FILENAME__ = test_atm
import os
import zmq
import shutil
import unittest2

from elevator.db import DatabaseStore
from elevator.backend.atm import Majordome
from elevator.backend.supervisor import Supervisor

from ..fakers import gen_test_config


class MajordomeTest(unittest2.TestCase):
    def setUp(self):
        zmq_context = zmq.Context()
        config = gen_test_config()

        self.database_store = config['database_store']
        self.databases_storage_path = config['databases_storage_path']

        if not os.path.exists(self.databases_storage_path):
            os.mkdir(self.databases_storage_path)

        self.db_handler = DatabaseStore(config)

        # Let's fake a backend for workers to talk to
        self.socket = zmq_context.socket(zmq.DEALER)
        self.socket.bind('inproc://backend')

        self.supervisor = Supervisor(zmq_context, self.db_handler)

    def tearDown(self):
        self.supervisor.stop_all()

        if hasattr(self, 'majordome'):
            self.majordome.cancel()

        os.remove(self.database_store)
        shutil.rmtree(self.databases_storage_path)

    def test_unmount_existing_mounted_database(self):
        default_db_uid = self.db_handler.index['name_to_uid']['default']
        db_to_watch = self.db_handler[default_db_uid]
        self.assertEqual(db_to_watch.status, DatabaseStore.STATUSES.MOUNTED)

        # Use 1/60 interval in order to set it as 1sec
        self.majordome = Majordome(self.supervisor,
                                   self.db_handler,
                                   1 / 60)
        self.assertEqual(db_to_watch.status, DatabaseStore.STATUSES.MOUNTED)

    def test_unmount_existing_unmounted_database(self):
        default_db_uid = self.db_handler.index['name_to_uid']['default']
        db_to_watch = self.db_handler[default_db_uid]

        self.assertEqual(db_to_watch.status, DatabaseStore.STATUSES.MOUNTED)
        self.db_handler.umount('default')
        self.assertEqual(db_to_watch.status, DatabaseStore.STATUSES.UNMOUNTED)

        # Use 1/60 interval in order to set it as 1sec
        self.majordome = Majordome(self.supervisor,
                                   self.db_handler,
                                   1 / 60)
        self.assertEqual(db_to_watch.status, DatabaseStore.STATUSES.UNMOUNTED)

########NEW FILE########
__FILENAME__ = test_supervisor
import os
import zmq
import time
import shutil
import threading
import unittest2

from elevator.db import DatabaseStore
from elevator.backend.supervisor import Supervisor
from elevator.backend.worker import Worker
from elevator.backend.protocol import WORKER_STATUS

from ..fakers import gen_test_config


class SupervisorTest(unittest2.TestCase):
    def setUp(self):
        zmq_context = zmq.Context()
        config = gen_test_config()

        self.database_store = config['database_store']
        self.databases_storage_path = config['databases_storage_path']
        if not os.path.exists(self.databases_storage_path):
            os.mkdir(self.databases_storage_path)
        self.db_handler = DatabaseStore(config)

        # Let's fake a backend for workers to talk to
        self.socket = zmq_context.socket(zmq.DEALER)
        self.socket.bind('inproc://backend')

        self.supervisor = Supervisor(zmq_context, self.db_handler)

    def tearDown(self):
        self.supervisor.stop_all()
        os.remove(self.database_store)
        shutil.rmtree(self.databases_storage_path)

    def test_init_workers_with_positive_count(self):
        start_thread_count = len(threading.enumerate())
        workers_count = 4

        self.supervisor.init_workers(workers_count)
        time.sleep(1)  # Wait for workers to start

        self.assertEqual(len(threading.enumerate()),
                         start_thread_count + workers_count)
        self.assertEqual(len(self.supervisor.workers), workers_count)

        for _id, worker in self.supervisor.workers.iteritems():
            self.assertIn('thread', worker)
            self.assertIsInstance(worker['thread'], threading.Thread)
            self.assertTrue(worker['thread'].isAlive())

            self.assertIn('socket', worker)

    def test_stop_specific_worker(self):
        start_thread_count = len(threading.enumerate())
        workers_count = 4
        self.supervisor.init_workers(workers_count)
        time.sleep(1)  # Wait for the workers to start
        worker_to_stop = self.supervisor.workers.keys()[0]

        self.assertEqual(len(threading.enumerate()),
                         start_thread_count + workers_count)

        self.supervisor.stop(worker_to_stop)

        self.assertEqual(len(threading.enumerate()),
                         (start_thread_count + workers_count) - 1)
        self.assertNotIn(worker_to_stop, self.supervisor.workers)

    def test_stop_all(self):
        start_thread_count = len(threading.enumerate())
        workers_count = 4
        self.supervisor.init_workers(workers_count)
        time.sleep(1)  # Wait for the workers to start

        self.assertEqual(len(threading.enumerate()),
                         start_thread_count + workers_count)

        self.supervisor.stop_all()

        self.assertEqual(len(threading.enumerate()),
                         start_thread_count)
        self.assertEqual(len(self.supervisor.workers), 0)

    def test_specific_worker_status(self):
        workers_count = 4
        self.supervisor.init_workers(workers_count)
        worker_to_ask = self.supervisor.workers.keys()[0]

        status = self.supervisor.status(worker_to_ask)
        self.assertIsInstance(status, list)
        self.assertEqual(len(status), 1)
        self.assertEqual(status[0], (str(Worker.STATES.IDLE),))

    def test_workers_status(self):
        workers_count = 4
        self.supervisor.init_workers(workers_count)

        status = self.supervisor.statuses()
        self.assertIsInstance(status, list)
        self.assertEqual(len(status), 4)
        self.assertEqual(status, [(str(Worker.STATES.IDLE),)] * 4)

    def test_inactive_worker_last_activity(self):
        workers_count = 2
        self.supervisor.init_workers(workers_count)
        worker_to_ask = self.supervisor.workers.keys()[0]

        status = self.supervisor.last_activity(worker_to_ask)
        self.assertIsInstance(status, list)
        self.assertEqual(len(status), 1)
        self.assertEqual(status[0], (None, None))

    def test_inactive_workers_last_activities(self):
        workers_count = 2
        self.supervisor.init_workers(workers_count)

        status = self.supervisor.last_activity_all()
        self.assertIsInstance(status, list)
        self.assertEqual(len(status), 2)
        self.assertEqual(status[0], (None, None))
        self.assertEqual(status[1], (None, None))

    def test_valid_working_command_with_workers(self):
        workers_count = 4
        self.supervisor.init_workers(workers_count)

        responses = self.supervisor.command(WORKER_STATUS,
                                            max_retries=1,
                                            timeout=100)

        self.assertIsInstance(responses, list)
        self.assertGreaterEqual(len(responses), 4)

    def test_valid_working_command_without_workers(self):
        responses = self.supervisor.command(WORKER_STATUS,
                                            max_retries=1,
                                            timeout=100)

        self.assertIsInstance(responses, list)
        self.assertEqual(responses, [])

    def test_invalid_command_with_workers(self):
        workers_count = 2
        self.supervisor.init_workers(workers_count)

        responses = self.supervisor.command("NONEXISTINGCOMMAND",
                                            max_retries=1,
                                            timeout=100)

        self.assertIsInstance(responses, list)
        self.assertEqual(responses, [])


########NEW FILE########
__FILENAME__ = test_worker
import unittest2


class WorkerTest(unittest2.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

########NEW FILE########
__FILENAME__ = db_tests
from __future__ import absolute_import

import unittest2
import os
import json
import shutil
import tempfile
import plyvel

from elevator.utils.snippets import from_mo_to_bytes
from elevator.constants import SUCCESS_STATUS, FAILURE_STATUS,\
                               KEY_ERROR, RUNTIME_ERROR, DATABASE_ERROR
from elevator.db import Database, DatabaseStore, DatabaseOptions

from .fakers import gen_test_config
from .utils import rm_from_pattern


class DatabaseOptionsTest(unittest2.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


class DatabasesTest(unittest2.TestCase):
    def setUp(self):
        self.store = '/tmp/store.json'
        self.dest = '/tmp/dbs'
        self.config = gen_test_config()
        if not os.path.exists(self.dest):
            os.mkdir(self.dest)
        self.handler = DatabaseStore(self.config)

    def tearDown(self):
        self.handler.__del__()
        os.remove('/tmp/store.json')
        shutil.rmtree('/tmp/dbs')

    def test_init(self):
        self.assertIn('default', self.handler.index['name_to_uid'])
        default_db_uid = self.handler.index['name_to_uid']['default']

        self.assertEqual(self.handler[default_db_uid].name, 'default')
        self.assertEqual(self.handler[default_db_uid].path, '/tmp/dbs/default')

    def test_load(self):
        db_name = 'testdb'
        self.handler.add(db_name)

        self.assertIn(db_name, self.handler.index['name_to_uid'])
        db_uid = self.handler.index['name_to_uid'][db_name]

        self.assertIn(db_uid, self.handler)
        self.assertEqual(self.handler[db_uid].name, db_name)
        self.assertIn('default', self.handler.index['name_to_uid'])

    def test_store_update(self):
        db_name = 'test_db'
        db_desc = {
            'path': '/tmp/test_path',
            'uid': 'testuid',
            'options': {},
        }
        self.handler.store_update(db_name, db_desc)

        store_datas = json.load(open(self.handler.store_file, 'r'))
        self.assertIn(db_name, store_datas)
        self.assertEqual(store_datas[db_name], db_desc)

    def test_store_remove(self):
        db_name = 'test_db'
        db_desc = {
            'path': '/tmp/test_path',
            'uid': 'testuid',
            'options': {},
        }
        self.handler.store_update(db_name, db_desc)
        self.handler.store_remove(db_name)
        store_datas = json.load(open(self.handler.store_file, 'r'))

        self.assertNotIn(db_name, store_datas)

    def test_drop_existing_db(self):
        db_name = 'default'  # Automatically created on startup
        status, content = self.handler.drop(db_name)

        self.assertEqual(status, SUCCESS_STATUS)
        self.assertEqual(content, None)

        store_datas = json.load(open(self.handler.store_file, 'r'))
        self.assertNotIn(db_name, store_datas)

    def test_remove_existing_db_which_files_were_erased(self):
        db_name = 'testdb'  # Automatically created on startup
        db_path = '/tmp/dbs/testdb'
        status, content = self.handler.add(db_name)
        shutil.rmtree(db_path)
        status, content = self.handler.drop(db_name)

        self.assertEqual(status, FAILURE_STATUS)
        self.assertIsInstance(content, list)
        self.assertEqual(len(content), 2)
        self.assertEqual(content[0], DATABASE_ERROR)

        store_datas = json.load(open(self.handler.store_file, 'r'))
        self.assertNotIn(db_name, store_datas)

    def test_add_from_db_name_without_options_passed(self):
        db_name = 'testdb'
        default_db_options = DatabaseOptions()
        status, content = self.handler.add(db_name)

        self.assertEqual(status, SUCCESS_STATUS)
        self.assertEqual(content, None)

        store_datas = json.load(open(self.handler.store_file, 'r'))
        self.assertIn(db_name, store_datas)
        self.assertEqual(store_datas[db_name]["path"],
                         os.path.join(self.dest, db_name))

        self.assertIsNotNone(store_datas[db_name]["uid"])

        stored_db_options = store_datas[db_name]["options"]
        self.assertIsNotNone(stored_db_options)
        self.assertIsInstance(stored_db_options, dict)

        for option_name, option_value in default_db_options.iteritems():
            self.assertIn(option_name, stored_db_options)
            self.assertEqual(option_value, stored_db_options[option_name])

    def test_add_from_db_name_with_options_passed(self):
        db_name = 'testdb'
        db_options = DatabaseOptions(paranoid_checks=True)
        status, content = self.handler.add(db_name, db_options)

        self.assertEqual(status, SUCCESS_STATUS)
        self.assertEqual(content, None)

        store_datas = json.load(open(self.handler.store_file, 'r'))
        self.assertIn(db_name, store_datas)
        self.assertEqual(store_datas[db_name]["path"],
                         os.path.join(self.dest, db_name))

        self.assertIsNotNone(store_datas[db_name]["uid"])

        stored_db_options = store_datas[db_name]["options"]
        self.assertIsNotNone(stored_db_options)
        self.assertIsInstance(stored_db_options, dict)

        for option_name, option_value in db_options.iteritems():
            if option_name == "paranoid_check":
                self.assertEqual(option_value, False)
                continue
            self.assertIn(option_name, stored_db_options)
            self.assertEqual(option_value, stored_db_options[option_name])

    def test_add_from_db_abspath(self):
        db_path = '/tmp/dbs/testdb'  # Could be anywhere on fs
        default_db_options = DatabaseOptions()
        status, content = self.handler.add(db_path)

        self.assertEqual(status, SUCCESS_STATUS)
        self.assertEqual(content, None)

        store_datas = json.load(open(self.handler.store_file, 'r'))
        self.assertIn(db_path, store_datas)
        self.assertEqual(store_datas[db_path]["path"],
                         os.path.join(self.dest, db_path))

        self.assertIsNotNone(store_datas[db_path]["uid"])

        stored_db_options = store_datas[db_path]["options"]
        self.assertIsNotNone(stored_db_options)
        self.assertIsInstance(stored_db_options, dict)

        for option_name, option_value in default_db_options.iteritems():
            self.assertIn(option_name, stored_db_options)
            self.assertEqual(option_value, stored_db_options[option_name])

    def test_add_from_db_relpath(self):
        db_path = './testdb'  # Could be anywhere on fs
        status, content = self.handler.add(db_path)

        self.assertEqual(status, FAILURE_STATUS)
        self.assertIsInstance(content, list)
        self.assertEqual(len(content), 2)
        self.assertEqual(content[0], DATABASE_ERROR)

        store_datas = json.load(open(self.handler.store_file, 'r'))
        self.assertNotIn(db_path, store_datas)

    def test_add_db_mounts_it_automatically(self):
        db_name = 'testdb'  # Automatically created on startup
        status, content = self.handler.add(db_name)
        db_uid = self.handler.index['name_to_uid'][db_name]

        self.assertEqual(self.handler[db_uid].status, Database.STATUS.MOUNTED)
        self.assertIsNotNone(self.handler[db_uid].connector)
        self.assertIsInstance(self.handler[db_uid].connector, plyvel.DB)

    def test_mount_unmounted_db(self):
        db_name = 'testdb'  # Automatically created on startup
        status, content = self.handler.add(db_name)
        db_uid = self.handler.index['name_to_uid'][db_name]
        # Unmount the db by hand
        self.handler[db_uid].status = self.handler.STATUSES.UNMOUNTED
        self.handler[db_uid].connector = None

        # Re-mount it and assert everything went fine
        status, content = self.handler.mount(db_name)

        self.assertEqual(status, SUCCESS_STATUS)
        self.assertEqual(self.handler[db_uid].status, self.handler.STATUSES.MOUNTED)
        self.assertIsNotNone(self.handler[db_uid].connector)
        self.assertIsInstance(self.handler[db_uid].connector, plyvel.DB)

    def test_mount_already_mounted_db(self):
        db_name = 'testdb'  # Automatically created on startup
        status, content = self.handler.add(db_name)

        status, content = self.handler.mount(db_name)
        self.assertEqual(status, FAILURE_STATUS)
        self.assertEqual(len(content), 2)
        self.assertEqual(content[0], DATABASE_ERROR)

    def test_mount_corrupted_db(self):
        db_name = 'testdb'
        status, content = self.handler.add(db_name)
        db_uid = self.handler.index['name_to_uid'][db_name]

        # Intetionaly rm db MANIFEST in order for a corruption
        # to appear.
        rm_from_pattern(self.handler[db_uid].path, 'MANIFEST*')

        status, content = self.handler.mount(db_name)
        self.assertEqual(status, FAILURE_STATUS)
        self.assertEqual(len(content), 2)
        self.assertEqual(content[0], DATABASE_ERROR)

    def test_unmount_mounted_db(self):
        db_name = 'testdb'  # Automatically created on startup
        status, content = self.handler.add(db_name)
        db_uid = self.handler.index['name_to_uid'][db_name]

        # Re-mount it and assert everything went fine
        status, content = self.handler.umount(db_name)

        self.assertEqual(status, SUCCESS_STATUS)
        self.assertEqual(self.handler[db_uid].status, self.handler.STATUSES.UNMOUNTED)
        self.assertIsNone(self.handler[db_uid].connector)

    def test_umount_already_unmounted_db(self):
        db_name = 'testdb'  # Automatically created on startup
        status, content = self.handler.add(db_name)
        db_uid = self.handler.index['name_to_uid'][db_name]

        # Unmount the db by hand
        self.handler[db_uid].status = self.handler.STATUSES.UNMOUNTED
        self.handler[db_uid].connector = None

        status, content = self.handler.umount(db_name)
        self.assertEqual(status, FAILURE_STATUS)
        self.assertEqual(len(content), 2)
        self.assertEqual(content[0], DATABASE_ERROR)

########NEW FILE########
__FILENAME__ = fakers
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import os
import shutil
import subprocess
import tempfile
import ConfigParser
import random

from elevator.config import Config

mkdtemp = lambda _dir: tempfile.mkdtemp(suffix='-test',
                                        prefix='elevator-',
                                        dir=_dir)
mkstemp = lambda suffix, _dir: tempfile.mkstemp(suffix="-test" + suffix,
                                                prefix='elevator-',
                                                dir=_dir)[1]


def gen_test_config():
    tmp = mkdtemp('/tmp')
    return Config(**{
        'daemonize': 'no',
        'pidfile': os.path.join(tmp, 'elevator_test.pid'),
        'databases_storage_path': os.path.join(tmp, 'elevator_test'),
        'database_store': os.path.join(tmp, 'elevator_test/store.json'),
        'default_db': 'default',
        'port': 4141,
        'bind': '127.0.0.1',
        'activity_log': os.path.join(tmp, 'elevator_test.log'),
        'errors_log': os.path.join(tmp, 'elevator_errors.log'),
        'max_cache_size': 1024,
    })


def gen_test_conf():
    """Generates a ConfigParser object built with test options values"""
    global_config_options = {
        "pidfile": mkstemp('.pid', '/tmp'),
        "databases_storage_path": mkdtemp('/tmp'),  # Will be randomly set later
        "database_store": mkstemp('.json', '/tmp'),
        "port": str(random.randint(4142, 60000)),
        "activity_log": mkstemp('.log', '/tmp'),
        "errors_log": mkstemp('_errors.log', '/tmp'),
    }
    config = ConfigParser.ConfigParser()
    config.add_section('global')

    for key, value in global_config_options.iteritems():
        config.set('global', key, value)

    return config


class TestDaemon(object):
    def __init__(self):
        self.bootstrap_conf()
        self.process = None

        self.port = self.config.get('global', 'port')

    def __del__(self):
        for key, value in self.config.items('global'):
            if not isinstance(value, (int, float)) and os.path.exists(value):
                if os.path.isfile(value):
                    os.remove(value)
                elif os.path.isdir(value):
                    shutil.rmtree(value)

        os.remove(self.conf_file_path)

    def bootstrap_conf(self):
        self.conf_file_path = mkstemp('.conf', '/tmp')
        self.config = gen_test_conf()

        with open(self.conf_file_path) as f:
            self.config.write(f)

    def start(self):
        self.process = subprocess.Popen(['elevator',
                                         '--config', self.conf_file_path,
                                         '--port', self.port])

    def stop(self):
        self.process.kill()

########NEW FILE########
__FILENAME__ = message_tests
from __future__ import absolute_import

import unittest2
import msgpack

from nose.tools import raises

from elevator.message import Request, ResponseContent,\
                             ResponseHeader, MessageFormatError
from elevator.constants import *


class RequestTest(unittest2.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @raises(MessageFormatError)
    def test_request_with_missing_mandatory_arguments(self):
        request = msgpack.packb({
            'uid': '123-456-789',
            'cmd': 'GET',
        })

        request = Request(request)

    def test_valid_request_without_meta(self):
        request = msgpack.packb({
            'uid': '123-456-789',
            'cmd': 'PUT',
            'args': ['key', 'value']
        })

        request = Request(request)
        self.assertIsNotNone(request)

        self.assertTrue(hasattr(request, 'meta'))
        self.assertTrue(hasattr(request, 'db_uid'))
        self.assertTrue(hasattr(request, 'command'))
        self.assertTrue(hasattr(request, 'data'))

        self.assertEqual(request.db_uid, '123-456-789')
        self.assertEqual(request.command, 'PUT')
        self.assertEqual(request.data, ('key', 'value'))

    def test_valid_request_with_meta(self):
        request = msgpack.packb({
            'meta': {
                'test': 'test',
            },
            'uid': '123-456-789',
            'cmd': 'PUT',
            'args': ['key', 'value']
        })

        request = Request(request)
        self.assertIsNotNone(request)

        self.assertTrue(hasattr(request, 'meta'))
        self.assertTrue(hasattr(request, 'db_uid'))
        self.assertTrue(hasattr(request, 'command'))
        self.assertTrue(hasattr(request, 'data'))

        self.assertEqual(request.meta, {'test': 'test'})
        self.assertEqual(request.db_uid, '123-456-789')
        self.assertEqual(request.command, 'PUT')
        self.assertEqual(request.data, ('key', 'value'))


class ResponseContentTest(unittest2.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_success_response_with_values(self):
        response = ResponseContent(datas=['thisistheres'])
        unpacked_response = msgpack.unpackb(response)
        self.assertIsInstance(unpacked_response, dict)
        self.assertIn('datas', unpacked_response)
        self.assertEqual(unpacked_response['datas'], ('thisistheres',))

    @raises
    def test_success_response_without_values(self):
        ResponseContent()


class ResponseHeaderTest(unittest2.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_success_header(self):
        header = ResponseHeader(status=SUCCESS_STATUS)
        unpacked_header = msgpack.unpackb(header)

        self.assertIsInstance(unpacked_header, dict)
        self.assertIn('status', unpacked_header)
        self.assertIn('err_code', unpacked_header)
        self.assertIn('err_msg', unpacked_header)
        self.assertEqual(unpacked_header['status'], SUCCESS_STATUS)
        self.assertIsNone(unpacked_header['err_code'], None)
        self.assertIsNone(unpacked_header['err_msg'], None)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

# Copyright (c) 2012 theo crevon
#
# See the file LICENSE for copying permission.

import os
import re


def rm_from_pattern(dir, pattern):
    """Removes directory files matching with a provided
    pattern"""
    for f in os.listdir(dir):
        if re.search(pattern, f):
                os.remove(os.path.join(dir, f))

########NEW FILE########
