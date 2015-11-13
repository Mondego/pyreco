__FILENAME__ = backend
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import os
import json

import gruvi

from bluepass import platform, util, logging
from bluepass.factory import singleton
from bluepass.component import Component
from bluepass.crypto import CryptoProvider
from bluepass.database import Database
from bluepass.model import Model
from bluepass.passwords import PasswordGenerator
from bluepass.locator import Locator, ZeroconfLocationSource
from bluepass.socketapi import SocketAPIServer
from bluepass.syncapi import SyncAPIServer, SyncAPIPublisher, init_syncapi_ssl
from bluepass.syncer import Syncer


def get_listen_address(options):
    """Return the default listen address."""
    if hasattr(os, 'fork'):
        addr = os.path.join(options.data_dir, 'backend.sock')
        util.try_unlink(addr)
    else:
        addr = 'localhost:0'
    return addr


class Backend(Component):
    """The Bluepass backend."""

    def __init__(self, options):
        """The *options* argument must be the parsed command-line arguments."""
        super(Backend, self).__init__(options)
        self._log = logging.get_logger(self)
        self._stop_event = gruvi.Signal()
        self._process = None

    @classmethod
    def add_options(self, parser):
        """Add command-line options to *parser*."""
        group = parser.add_argument_group('Options for backend')
        group.add_argument('-l', '--listen', metavar='ADDRSPEC',
                           help='The JSON-RPC listen address (HOST:PORT or PATH)')
        group.add_argument('--trace', action='store_true',
                           help='Trace JSON-RPC messages')

    @classmethod
    def check_options(cls, options):
        """Check parsed command-line options."""
        if not options.listen:
            options.listen = get_listen_address(options)
        return True

    def run(self):
        """Initialize the backend and run its main loop."""
        self._log.debug('initializing backend components')

        self._log.debug('initializing cryto provider')
        crypto = singleton(CryptoProvider)
        pwgen = singleton(PasswordGenerator)
        init_syncapi_ssl(self.options.data_dir)

        self._log.debug('initializing database')
        fname = os.path.join(self.options.data_dir, 'bluepass.db')
        database = singleton(Database, fname)
        database.lock()

        self._log.debug('initializing model')
        model = singleton(Model, database)

        self._log.debug('initializing locator')
        locator = singleton(Locator)
        for ls in platform.get_location_sources():
            self._log.debug('adding location source: {}', ls.name)
            locator.add_source(ls())

        self._log.debug('initializing sync API')
        syncapi = singleton(SyncAPIServer)
        syncapi.listen(('0.0.0.0', 0))

        self._log.debug('initializing sync API publisher')
        publisher = singleton(SyncAPIPublisher, syncapi)
        publisher.start()

        if locator.sources:
            self._log.debug('initializing background sync worker')
            syncer = singleton(Syncer)
            syncer.start()
        else:
            self._log.warning('no location sources available')
            self._log.warning('network synchronization is disabled')

        self._log.debug('initializing control API')
        socketapi = singleton(SocketAPIServer)
        if self.options.trace:
            tracename = os.path.join(self.options.data_dir, 'backend.trace')
            tracefile = open(tracename, 'w')
            socketapi._set_tracefile(tracefile)
        addr = gruvi.util.paddr(self.options.listen)
        socketapi.listen(addr)

        fname = os.path.join(self.options.data_dir, 'backend.run')
        addr = gruvi.util.getsockname(socketapi.transport)
        runinfo = { 'listen': gruvi.util.saddr(addr), 'pid': os.getpid() }
        util.write_atomic(fname, json.dumps(runinfo))

        # This is where the backend runs (until stop_event is raised or CTRL-C
        # is pressed).
        try:
            self._stop_event.wait(timeout=None, interrupt=True)
        except KeyboardInterrupt:
            self._log.info('CTRL-C pressed, exiting')

        self._log.debug('backend event loop terminated')

        self._log.debug('shutting down control API')
        socketapi.close()

        self._log.debug('shutting down database')
        database.close()

        self._log.debug('stopped all backend components')

        return 0

    def stop(self):
        """Stop the backend."""
        self._stop_event.emit()

########NEW FILE########
__FILENAME__ = base64
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import base64
import binascii
from gruvi import compat

Error = binascii.Error


# Types are as follows:
#
# Encode: bytes -> str
# Decode: str -> bytes
#
# Note this is different from the stdlib where base64 always works on bytes,
# and returns bytes. The types below make more sense to us because we always
# store the result of a base64 encoding in a dict that will be converted to
# JSON, which is unicode based.

def encode(b):
    """Encode a string into base-64 encoding."""
    if not isinstance(b, compat.binary_type):
        raise TypeError('expecting bytes')
    return base64.b64encode(b).decode('ascii')

def decode(s):
    """Decode a base-64 encoded string."""
    if not isinstance(s, compat.string_types):
        raise TypeError('expecting string')
    return base64.b64decode(s)

def check(s):
    """Check that `s' is a properly encoded base64 string."""
    if not isinstance(s, compat.string_types):
        raise TypeError('expecting string')
    try:
        base64.b64decode(s)
    except binascii.Error:
        return False
    return True

def try_decode(s):
    """Decode a base64 string and return None if there was an error."""
    try:
        return decode(s)
    except binascii.Error:
        pass

########NEW FILE########
__FILENAME__ = component
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.


class Component(object):
    """Base class for Bluepass components (frontend/backend)."""

    name = None
    description = None

    def __init__(self, options):
        """The *options* argument must be the parsed command-line options."""
        self._options = options

    @property
    def options(self):
        """The parsed command-line options."""
        return self._options

    @classmethod
    def add_options(cls, parser):
        """Initialize command-line options."""

    @classmethod
    def check_options(cls, options):
        """Check parsed command-line options."""
        return True

    def run(self):
        """Run the component.

        The return value is an exit status that should be passed to
        :meth:`sys.exit`.
        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = crypto
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import os
import hmac
import time
import math
import hashlib
import logging
import uuid
import textwrap
import binascii

from bluepass.ext import openssl
from bluepass.logging import *

CryptoError = openssl.Error

# Some useful commonly used DH parameters.
dhparams = \
{
    'skip2048': textwrap.dedent("""\
    MIIBCAKCAQEA9kJXtwh/CBdyorrWqULzBej5UxE5T7bxbrlLOCDaAadWoxTpj0BV
    89AHxstDqZSt90xkhkn4DIO9ZekX1KHTUPj1WV/cdlJPPT2N286Z4VeSWc39uK50
    T8X8dryDxUcwYc58yWb/Ffm7/ZFexwGq01uejaClcjrUGvC/RgBYK+X0iP1YTknb
    zSC0neSRBzZrM2w4DUUdD3yIsxx8Wy2O9vPJI8BD8KVbGI2Ou1WMuF040zT9fBdX
    Q6MdGGzeMyEstSr/POGxKUAYEY18hKcKctaGxAMZyAcpesqVDNmWn6vQClCbAkbT
    CD1mpF1Bn5x8vYlLIhkmuquiXsNV6TILOwIBAg==
    """),
    'ietf768': textwrap.dedent("""\
    MGYCYQD//////////8kP2qIhaMI0xMZii4DcHNEpAk4IimfMdAILvqY7E5siUUoIeY40BN3vlRmz
    zTpDGzArCm3yXxQ3T+E1bW1RwkXkhbV2Yl5+xvRMQummOjYg//////////8CAQI=
    """),
    'ietf1024': textwrap.dedent("""\
    MIGHAoGBAP//////////yQ/aoiFowjTExmKLgNwc0SkCTgiKZ8x0Agu+pjsTmyJRSgh5jjQE3e+V
    GbPNOkMbMCsKbfJfFDdP4TVtbVHCReSFtXZiXn7G9ExC6aY37WsL/1y29Aa37e44a/taiZ+lrp8k
    EXxLH+ZJKGZR7OZTgf//////////AgEC
    """)
}


class CryptoProvider(object):
    """Crypto provider.

    This class exposes the cryptographic primitives that are required by
    Bluepass. Currently the only available engine is OpenSSL, but at some
    point this could use a native platform crypto provider.
    """

    _pbkdf2_speed = {}

    def __init__(self, engine=None):
        """Create a new crypto provider."""
        self.engine = engine or openssl
        self._log = get_logger(self)

    def rsa_genkey(self, bits):
        """Generate an RSA key pair of `bits' bits. The result is a 2-tuple
        containing the private and public keys. The keys themselves as ASN.1
        encoded bitstrings.
        """
        return self.engine.rsa_genkey(bits)

    def rsa_checkkey(self, privkey):
        """Check that `privkey' is a valid RSA private key."""
        return self.engine.rsa_checkkey(privkey)

    def rsa_size(self, pubkey):
        """Return the size in bits of an RSA public key."""
        return self.engine.rsa_size(pubkey)

    def rsa_encrypt(self, s, pubkey, padding='oaep'):
        """RSA Encrypt a string `s' with public key `pubkey'. This uses direct
        encryption with OAEP padding.
        """
        return self.engine.rsa_encrypt(s, pubkey, padding)

    def rsa_decrypt(self, s, privkey, padding='oaep'):
        """RSA Decrypt a string `s' using the private key `privkey'."""
        return self.engine.rsa_decrypt(s, privkey, padding)

    def rsa_sign(self, s, privkey, padding='pss-sha256'):
        """Create a detached RSA signature of `s' using private key
        `privkey'."""
        return self.engine.rsa_sign(s, privkey, padding)

    def rsa_verify(self, s, sig, pubkey, padding='pss-sha256'):
        """Verify a detached RSA signature `sig' over `s' using the public key
        `pubkey'."""
        return self.engine.rsa_verify(s, sig, pubkey, padding)

    def dh_genparams(self, bits, generator):
        """Generate Diffie-Hellman parameters. The prime will be `bits'
        bits in size and `generator' will be the generator."""
        return self.engine.dh_genparams(bits)

    def dh_checkparams(self, params):
        """Check Diffie-Hellman parameters."""
        return self.engine.dh_checkparams(params)

    def dh_size(self, params):
        """Return the size in bits of the DH parameters `params'."""
        return self.engine.dh_size(params)

    def dh_genkey(self, params):
        """Generate a Diffie-Hellman key pair. The return value is a tuple
        (privkey, pubkey)."""
        return self.engine.dh_genkey(params)

    def dh_checkkey(self, params, pubkey):
        """Check a Diffie-Hellman public key."""
        return self.engine.dh_checkkey(params, pubkey)

    def dh_compute(self, params, privkey, pubkey):
        """Perform a Diffie-Hellman key exchange. The `privkey' parameter is
        our private key, `pubkey' is our peer's public key."""
        return self.engine.dh_compute(params, privkey, pubkey)

    def aes_encrypt(self, s, key, iv, mode='cbc-pkcs7'):
        """AES encrypt a string `s' with key `key'."""
        return self.engine.aes_encrypt(s, key, iv, mode)

    def aes_decrypt(self, s, key, iv, mode='cbc-pkcs7'):
        """AES decrypt a string `s' with key `key'."""
        return self.engine.aes_decrypt(s, key, iv, mode)

    def pbkdf2(self, password, salt, count, length, prf='hmac-sha1'):
        """PBKDF2 key derivation function from PKCS#5."""
        return self.engine.pbkdf2(password, salt, count, length, prf)

    def _measure_pbkdf2_speed(self, prf='hmac-sha1'):
        """Measure the speed of PBKDF2 on this system."""
        salt = password = '0123456789abcdef'
        length = 1; count = 1000
        self._log.debug('starting PBKDF2 speed measurement')
        start = time.time()
        while True:
            startrun = time.time()
            self.pbkdf2(password, salt, count, length, prf)
            endrun = time.time()
            if endrun - startrun > 0.4:
                break
            count = int(count * math.e)
        end = time.time()
        speed = int(count / (endrun - startrun))
        self._log.debug('PBKDF2 speed is {} iterations / second', speed)
        self._log.debug('PBKDF2 speed measurement took {:2f}', (end - start))
        # Store the speed in the class so that it can be re-used by
        # other instances.
        self._pbkdf2_speed[prf] = speed

    def pbkdf2_speed(self, prf='hmac-sha1'):
        """Return the speed in rounds/second for generating a key
        with PBKDF2 of up to the hash length size of `prf`."""
        if prf not in self._pbkdf2_speed:
            self._measure_pbkdf2_speed(prf)
        return self._pbkdf2_speed[prf]

    def pbkdf2_prf_available(self, prf):
        """Test if a given PRF is available for PBKDF2."""
        try:
            dummy = self.pbkdf2('test', 'test', 1, 1, prf)
        except CryptoError:
            return False
        return True

    def random(self, count, alphabet=None, separator=None):
        """Create a random string.
        
        The random string will be the concatenation of `count` elements
        randomly chosen from `alphabet`. The alphabet parameter can be a
        string, unicode string, a sequence of strings, or a sequence of unicode
        strings. If no alphabet is provided, a default alphabet is used
        containing all possible single byte values (0 through to 255).

        The type of the return value is the same as the elements in the
        alphabet (string or unicode).
        """
        return self.engine.random(count, alphabet, separator)

    def randint(self, bits):
        """Return a random integer with `bits' bits."""
        nbytes = (bits + 7) // 8
        mask = (1<<bits)-1
        return int(binascii.hexlify(self.random(nbytes)), 16) & mask

    def randuuid(self):
        """Return a type-4 random UUID."""
        return str(uuid.uuid4())

    def _get_hash(self, name):
        """INTERNAL: return a hash contructor from its name."""
        if not hasattr(hashlib, name):
            raise ValueError('no such hash function: %s' % name)
        return getattr(hashlib, name)

    def hmac(self, key, message, hash='sha256'):
        """Return the HMAC of `message' under `key', using the hash function
        `hash' (default: sha256)."""
        md = self._get_hash(hash)
        return hmac.new(key, message, md).digest()

    def hkdf(self, password, salt, info, length, hash='sha256'):
        """HKDF key derivation function."""
        md = self._get_hash(hash)
        md_size = md().digest_size
        if length > 255*md_size:
            raise ValueError('can only generate keys up to 255*md_size bytes')
        if not isinstance(password, bytes):
            password = password.encode('ascii')
        if salt is None:
            salt = b'\x00' * md_size
        elif not isinstance(salt, bytes):
            salt = salt.encode('ascii')
        if not isinstance(info, bytes):
            info = info.encode('ascii')
        prk = hmac.new(salt, password, md).digest()
        blocks = [b'']
        nblocks = (length + md_size - 1) // md_size
        for i in range(nblocks):
            blocks.append(hmac.new(prk, blocks[i] + info +
                                    chr(i+1).encode('ascii'), md).digest())
        return b''.join(blocks)[:length]

########NEW FILE########
__FILENAME__ = database
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import os
import re
import sys
import json
import sqlite3
import logging
from datetime import datetime

from bluepass.error import StructuredError
from bluepass import platform


def _get_json_value(obj, path):
    """Get a value from a JSON object."""
    for key in path[1:].split('$'):
        child = obj.get(key)
        if child is None:
            return
        obj = child
    return obj

def get_json_value(doc, path):
    """Get a value from a JSON document."""
    obj = json.loads(doc)
    return _get_json_value(obj, path)


class DatabaseError(StructuredError):
    """Database error."""


class Database(object):
    """Our central data store.

    This is a SQLite database that stores JSON documents. Some document
    database like functionality is provided.
    """

    sqlite_args = { 'timeout': 2 }

    def __init__(self, fname=None, **sqlite_args):
        """Constructor."""
        self.filename = None
        self._lock = None
        self.sqlite_args = self.sqlite_args  # move from class to instance
        self.sqlite_args.update(sqlite_args)
        if fname is not None:
            self.open(fname)

    def open(self, fname):
        """Open the database if it is not opened yet."""
        if self.filename is not None:
            raise DatabaseError('ProgrammingError', 'Database already opened.')
        self.connection = sqlite3.connect(fname, **self.sqlite_args)
        self.connection.create_function('get_json_value', 2, get_json_value)
        self.filename = fname
        self._load_schema()

    def _cursor(self):
        """Return a new cursor."""
        return self.connection.cursor()

    def _commit(self, cursor):
        """Commit and close a cursor."""
        if cursor.connection is not self.connection:
            raise DatabaseError('ProgrammingError', 'cursor does not belong to this store')
        self.connection.commit()
        cursor.close()

    def _load_schema(self):
        """INTERNAL: load information on indices and tables."""
        cursor = self._cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        tables = [ row[0] for row in cursor.fetchall() ]
        indices = {}
        for table in tables:
            cursor.execute("PRAGMA index_list('%s')" % table)
            indices[table] = [ row[1][2+len(table):] for row in cursor.fetchall() ]
        self._commit(cursor)
        self.tables = tables
        self.indices = indices

    def create_table(self, table):
        """INTERNAL: create a table."""
        cursor = self._cursor()
        cursor.execute('CREATE TABLE %s (doc TEXT)' % table)
        self.tables.append(table)
        self.indices[table] = []
        self._commit(cursor)

    def create_index(self, table, path, typ, unique):
        cursor = self._cursor()
        """Create a new index."""
        cursor.execute('ALTER TABLE %s ADD COLUMN _%s %s' % (table, path, typ))
        unique = 'UNIQUE' if unique else ''
        cursor.execute('CREATE %s INDEX _%s_%s ON %s(_%s)' % (unique, table, path, table, path))
        cursor.execute("UPDATE %s SET _%s = get_json_value(doc, '%s')" % (table, path, path))
        self.indices[table].append(path)
        self._commit(cursor)

    def lock(self):
        """Lock the database."""
        # I would have loved to use SQLite based locking but it seems
        # impossible to have a cross-connection and cross-transaction write
        # lock while still allowing reads from other connections (for e.g.
        # backups and getting lock information).
        lockname = '%s-lock' % self.filename
        try:
            self._lock = platform.lock_file(lockname)
        except platform.LockError as e:
            msg = 'Database is locked by process %d (%s)' % (e.lock_pid, e.lock_cmd)
            raise DatabaseError('Locked', msg)
        except Exception as e:
            raise DatabaseError('PlatformError', str(e))

    def unlock(self):
        """Unlock the database."""
        if not self._lock:
            return
        platform.unlock_file(self._lock)
        self._lock = None

    def close(self):
        """Close the connection to the document store. This also unlocks the database."""
        if self.connection is None:
            return
        self.connection.close()
        self.connection = None
        self.unlock()
        self.filename = None

    _pathref = re.compile(r'(?:\$[a-z_][a-z0-9_]*)+', re.I)

    def _update_references(self, query, table):
        """INTERNAL: Update $path references in `query'. This replaces the
        references with either an index, if it exists, or a call to the
        get_json_value() stored procedure."""
        offset = 0
        for match in self._pathref.finditer(query):
            ref = match.group(0)
            if ref in self.indices[table]:
                repl = '_%s' % ref
            else:
                repl = "get_json_value(doc, '%s')" % ref
            query = query[:match.start(0)+offset] + repl + query[match.end(0)+offset:]
            offset += len(repl) - len(ref)
        return query

    def execute(self, table, query, args=()):
        """Execute a direct SQL query on the database."""
        cursor = self._cursor()
        query = self._update_references(query, table)
        cursor.execute(query, args)
        result = cursor.fetchall()
        self._commit(cursor)
        return result

    def findall(self, table, where=None, args=(), sort=None):
        """Find a set of documents in a collection."""
        cursor = self._cursor()
        query = 'SELECT doc FROM %s' % table
        if where is not None:
            query += ' WHERE %s' % where
        if sort is not None:
            query += ' ORDER BY %s' % sort
        query = self._update_references(query, table)
        result = cursor.execute(query, args)
        result = [ json.loads(row[0]) for row in result ]
        self._commit(cursor)
        return result

    def findone(self, table, where=None, args=(), sort=None):
        """Like findall() but only return the first result. In case there were
        no results, this returns None."""
        result = self.findall(table, where, args, sort)
        if result:
            return result[0]

    def insert(self, table, document):
        """Insert a document into a table."""
        cursor = self._cursor()
        cursor.execute('INSERT INTO %s (doc) VALUES (?)' % table, (json.dumps(document),))
        if self.indices[table]:
            cols = [ "_%s = get_json_value(doc, '%s')" % (ix, ix) for ix in self.indices[table] ]
            query = 'UPDATE %s SET %s WHERE _rowid_ = ?' % (table, ', '.join(cols))
            cursor.execute(query, (cursor.lastrowid,))
        self._commit(cursor)

    def insert_many(self, table, documents):
        """Insert many documents."""
        cursor = self._cursor()
        for doc in documents:
            cursor.execute('INSERT INTO %s (doc) VALUES (?)' % table, (json.dumps(doc),))
            if not self.indices[table]:
                continue
            cols = [ "_%s = get_json_value(doc, '%s')" % (ix, ix) for ix in self.indices[table] ]
            query = 'UPDATE %s SET %s WHERE _rowid_ = ?' % (table, ', '.join(cols))
            cursor.execute(query, (cursor.lastrowid,))
        self._commit(cursor)

    def delete(self, table, where, args):
        """INTERNAL: delete a document."""
        cursor = self._cursor()
        query = 'DELETE FROM %s' % table
        query += ' WHERE %s' % where
        query = self._update_references(query, table)
        cursor.execute(query, args)
        self._commit(cursor)

    def update(self, table, where, args, document):
        """Update an existing document."""
        cursor = self._cursor()
        query = 'SELECT _rowid_ FROM %s WHERE %s' % (table, where)
        query = self._update_references(query, table)
        result = cursor.execute(query, args)
        for res in result:
            query = 'UPDATE %s SET doc = ? WHERE _rowid_ = ?' % table
            args = (json.dumps(document), res[0])
            cursor.execute(query, args)
            if not self.indices[table]:
                continue
            cols = [ "_%s = get_json_value(doc, '%s')" % (ix, ix) for ix in self.indices[table] ]
            query = 'UPDATE %s SET %s WHERE _rowid_ = ?' % (table, ', '.join(cols))
            cursor.execute(query, (res[0],))
        self._commit(cursor)

########NEW FILE########
__FILENAME__ = error
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import sys
import logging
import traceback


class Error(Exception):
    """Base class of all exceptions."""


class StructuredError(Error):
    """Structured error.

    Structured errors are used when there may be a need to transport an
    error remotely over one of our APIs (socket API or sync API).

    A structured error has 3 attribute:

     - error_name: a unique string identifying this error
     - error_message: a short phrase describing error_name
     - error_detail: extra dteails

    The error_name attribute is a string that uniquely identifies the error
    and may be used by code to interpret the error. The error_message and
    error_details are human readable strings, may be localized, and should
    never be interpreted.
    """

    # A single table of all error_name's. If a subclass needs a new error, it
    # needs to be added here.

    error_table = \
    {
        'OK': 'No error',
        'Exists': 'Object already exists',
        'NotFound': 'Object not found',
        'Locked': 'Object is locked',
        'InvalidCall': 'Wrong signature for callable object',
        'InvalidArgument': 'Invalid argument',
        'WrongPassword': 'Wrong password',
        'ConsistencyError': 'Internal data inconsistency error',
        'PlatformError': 'Generic platform or operating system error',
        'RemoteError': 'Communications error with a remote peer',
        'UncaughtException': 'An uncaught exception occurred',
        'ProgrammingError': 'Programming error'
    }

    def __init__(self, error_name, error_detail=''):
        """Create a new structured error."""
        self.error_name = error_name
        self.error_message = self._get_error_message(error_name)
        self.error_detail = error_detail
        super(StructuredError, self). \
                __init__(error_name, self.error_message, self.error_detail)

    def _get_error_message(self, name):
        """Return the error message for error `name`."""
        try:
            return self.error_table[name]
        except KeyError:
            pass
        logger = logging.getLogger('bluepass')
        logger.debug('error "%s" unknown, please add it to ' \
                     'StructuredError.error_table', name)
        message = 'Unknown error'
        return message

    def __str__(self):
        """Format this error to a human readable error message."""
        if self.error_detail:
            return '%s: %s' % (self.error_message, self.error_detail)
        else:
            return self.error_message

    def asdict(self):
        """Return the error as a dictionary."""
        d = { 'code': self.error_name,
              'message': self.error_message,
              'data': self.error_detail }
        return d

    @classmethod
    def uncaught_exception(cls):
        """Return an UncaughtException."""
        detail = traceback.format_exception(*sys.exc_info())
        detail = ''.join(detail)
        return cls('UncaughtException', detail)

########NEW FILE########
__FILENAME__ = factory
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.


def instance(typ):
    """Return the singleton instance of a type."""
    if not hasattr(typ, 'instance'):
        typ.instance = typ()
    return typ.instance


def singleton(cls, *args, **kwargs):
    """Create a singleton class instance."""
    factory = kwargs.pop('factory', None)
    if factory:
        obj = factory(*args, **kwargs)
    else:
        obj = cls(*args, **kwargs)
    cls.instance = obj
    return obj

########NEW FILE########
__FILENAME__ = application
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import sys

from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QApplication, QIcon, QPixmap

from bluepass.util import asset
from bluepass.factory import singleton, instance

from .socketapi import QtSocketApiClient
from .mainwindow import MainWindow
from .vaultmanager import VaultManager


class Bluepass(QApplication):
    """Qt application object."""

    def __init__(self, args):
        super(Bluepass, self).__init__(args)
        self._config = None
        icon = QIcon(QPixmap(asset('png', 'bluepass-logo-144.png')))
        self.setWindowIcon(icon)

    def exec_(self):
        mainwindow = singleton(MainWindow)
        mainwindow.show()
        return super(Bluepass, self).exec_()

    def mainWindow(self):
        return instance(MainWindow)

    def backend(self):
        return instance(QtSocketApiClient)

    def config(self):
        if self._config is None:
            self._config = self.backend().get_config()
        return self._config

    def update_config(self, config):
        self._config = config
        self.backend().update_config(config)

    def copyToClipboard(self, text, timeout=None):
        clipboard = self.clipboard()
        clipboard.setText(text)
        if timeout is None:
            return
        def clearClipboard():
            # There is a small race condition here where we could clear
            # somebody else's contents but there's nothing we can do about it.
            if not clipboard.ownsClipboard() or clipboard.text != text:
                return
            clipboard.clear()
        QTimer.singleShot(timeout*1000, clearClipboard)

########NEW FILE########
__FILENAME__ = dialogs
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

from PyQt4.QtCore import Slot, Qt
from PyQt4.QtGui import (QDialog, QLineEdit, QTextEdit, QComboBox, QLabel,
        QPushButton, QHBoxLayout, QVBoxLayout, QGridLayout, QApplication,
        QIcon, QPixmap)

from bluepass.util import asset
from .util import SortedList
from .socketapi import QtSocketApiError
from .passwordbutton import GeneratePasswordButton, RandomPasswordConfiguration


class EditPasswordDialog(QDialog):
    """Add password dialog.

    This dialog allows the user to edit a password.
    """

    stylesheet = """
        QLineEdit { background-color: white; }
    """
    
    def __init__(self, parent=None):
        super(EditPasswordDialog, self).__init__(parent)
        self.vault = None
        self.version = {}
        self.fields = {}
        self.groups = {}
        self.addWidgets()
        self.setStyleSheet(self.stylesheet)
        self.resize(500, 350)

    @Slot(str, str)
    def addGroup(self, vault, name):
        if vault not in self.groups:
            self.groups[vault] = SortedList()
        group = self.groups[vault]
        pos = group.find(name)
        if pos == -1:
            group.insert(name)

    @Slot(str, str)
    def removeGroup(self, vault, name):
        if vault not in self.groups:
            return
        group = self.groups[vault]
        pos = group.find(name)
        if pos != -1:
            group.remove(name)

    def setGroup(self, group):
        pos = self.combobox.findText(group)
        if pos == -1:
            pos = 0
        self.combobox.setCurrentIndex(pos)

    def addWidgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        grid = QGridLayout()
        layout.addLayout(grid)
        grid.setColumnMinimumWidth(1, 20)
        grid.setColumnStretch(2, 100)
        grid.setRowStretch(6, 100)
        label = QLabel('Group', self)
        grid.addWidget(label, 0, 0)
        combobox = QComboBox(self)
        combobox.setEditable(True)
        combobox.setInsertPolicy(QComboBox.InsertAtTop)
        grid.addWidget(combobox, 0, 2)
        self.combobox = combobox
        self.fields['group'] = (combobox.currentText, None)
        label = QLabel('Name', self)
        grid.addWidget(label, 1, 0)
        nameedt = QLineEdit(self)
        nameedt.textChanged.connect(self.fieldUpdated)
        grid.addWidget(nameedt, 1, 2)
        self.nameedt = nameedt
        self.fields['name'] = (nameedt.text, nameedt.setText)
        label = QLabel('Username', self)
        grid.addWidget(label, 2, 0)
        editor = QLineEdit(self)
        grid.addWidget(editor, 2, 2)
        self.fields['username'] = (editor.text, editor.setText)
        label = QLabel('Password', self)
        grid.addWidget(label, 3, 0)
        passwdedt = QLineEdit(self)
        passwdedt.setEchoMode(QLineEdit.Password)
        passwdedt.textChanged.connect(self.fieldUpdated)
        grid.addWidget(passwdedt, 3, 2)
        self.fields['password'] = (passwdedt.text, passwdedt.setText)
        self.passwdedt = passwdedt
        config = RandomPasswordConfiguration()
        icon = QIcon(QPixmap(asset('png', 'eye.png')))
        showbtn = QPushButton(icon, '', self)
        showbtn.setCheckable(True)
        showbtn.toggled.connect(self.setShowPassword)
        showbtn.setFixedHeight(passwdedt.sizeHint().height())
        grid.addWidget(showbtn, 3, 3)
        self.showbtn = showbtn
        passwdbtn = GeneratePasswordButton('Generate', config, self)
        passwdbtn.setFixedWidth(passwdbtn.sizeHint().width())
        grid.addWidget(passwdbtn, 3, 4)
        passwdbtn.passwordGenerated.connect(passwdedt.setText)
        label = QLabel('Website')
        grid.addWidget(label, 5, 0)
        editor = QLineEdit(self)
        grid.addWidget(editor, 5, 2, 1, 3)
        self.fields['url'] = (editor.text, editor.setText)
        label = QLabel('Comment')
        grid.addWidget(label, 6, 0)
        editor = QTextEdit(self)
        editor.setAcceptRichText(False)
        grid.addWidget(editor, 6, 2, 1, 3)
        self.fields['comment'] = (editor.toPlainText, editor.setPlainText)
        layout.addStretch(100)
        hbox = QHBoxLayout()
        layout.addLayout(hbox)
        cancelbtn = QPushButton('Cancel')
        cancelbtn.clicked.connect(self.hide)
        hbox.addWidget(cancelbtn)
        savebtn = QPushButton('Save')
        savebtn.setDefault(True)
        savebtn.setEnabled(False)
        savebtn.clicked.connect(self.savePassword)
        hbox.addWidget(savebtn)
        self.savebtn = savebtn
        hbox.addStretch(100)

    @Slot()
    def fieldUpdated(self):
        name = self.nameedt.text()
        password = self.passwdedt.text()
        enabled = name != ''
        self.savebtn.setEnabled(enabled)

    @Slot(bool)
    def setShowPassword(self, show):
        if show:
            self.passwdedt.setEchoMode(QLineEdit.Normal)
        else:
            self.passwdedt.setEchoMode(QLineEdit.Password)

    @Slot(str, dict)
    def editPassword(self, vault, version):
        self.combobox.clear()
        group = version.get('group', '')
        for name in self.groups.get(vault, []):
            self.combobox.addItem(name)
        self.setGroup(group)
        for field in self.fields:
            getvalue, setvalue = self.fields[field]
            if setvalue:
                setvalue(version.get(field, ''))
        if version.get('id'):
            self.setWindowTitle('Edit Password')
            self.savebtn.setText('Save')
        else:
            self.setWindowTitle('Add Password')
            self.nameedt.setFocus()
            self.savebtn.setText('Add')
        self.vault = vault
        self.version = version
        self.show()

    @Slot()
    def savePassword(self):
        version = self.version.copy()
        for field in self.fields:
            getvalue, setvalue = self.fields[field]
            version[field] = getvalue()
        qapp = QApplication.instance()
        backend = qapp.backend()
        mainwindow = qapp.mainWindow()
        if version.get('id'):
            try:
                backend.update_version(self.vault, version)
            except QtSocketApiError as e:
                mainwindow.showMessage('Could not update password: %s' % str(e))
            else:
                mainwindow.showMessage('Password updated successfully')
        else:
            try:
                backend.add_version(self.vault, version)
            except QtSocketApiError as e:
                mainwindow.showMessage('Could not add password: %s' % str(e))
            else:
                mainwindow.showMessage('Password added successfully')
        self.hide()


class PairingApprovalDialog(QDialog):

    stylesheet = """
        QLineEdit#pinedt { font-size: 22pt; font-family: monospace; }
    """

    def __init__(self, parent=None):
        super(PairingApprovalDialog, self).__init__(parent)
        self.addWidgets()
        self.setStyleSheet(self.stylesheet)
        self.resize(400, 300)
        backend = QApplication.instance().backend()
        backend.PairingComplete.connect(self.pairingComplete)

    def addWidgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        preamble = QLabel(self)
        preamble.setWordWrap(True)
        layout.addWidget(preamble)
        self.preamble = preamble
        grid = QGridLayout()
        grid.setColumnMinimumWidth(1, 10)
        layout.addLayout(grid)
        namelbl = QLabel('Name', self)
        grid.addWidget(namelbl, 0, 0)
        self.namelbl = namelbl
        nameedt = QLineEdit(self)
        nameedt.setFocusPolicy(Qt.NoFocus)
        grid.addWidget(nameedt, 0, 2)
        self.nameedt = nameedt
        vaultlbl = QLabel('Vault', self)
        grid.addWidget(vaultlbl, 1, 0)
        self.vaultlbl = vaultlbl
        vaultedt = QLineEdit(self)
        vaultedt.setFocusPolicy(Qt.NoFocus)
        grid.addWidget(vaultedt, 1, 2)
        self.vaultedt = vaultedt
        hbox = QHBoxLayout(self)
        layout.addLayout(hbox)
        hbox.addStretch(100)
        pinedt = QLineEdit(self)
        pinedt.setObjectName('pinedt')
        pinedt.setFocusPolicy(Qt.NoFocus)
        hbox.addWidget(pinedt)
        self.pinedt = pinedt
        hbox.addStretch(100)
        layout.addStretch(100)
        hbox = QHBoxLayout(self)
        layout.addLayout(hbox)
        hbox.addStretch(100)
        cancelbtn = QPushButton('Deny', self)
        cancelbtn.clicked.connect(self.denyApproval)
        hbox.addWidget(cancelbtn)
        self.cancelbtn = cancelbtn
        approvebtn = QPushButton('Allow', self)
        approvebtn.clicked.connect(self.grantApproval)
        hbox.addWidget(approvebtn)
        self.approvebtn = approvebtn
        hbox.addStretch(100)

    def reset(self):
        preamble = '<p>A remote node wants to connect to one of ' \
                   'your vaults. Do you want to proceed?</p>'
        self.preamble.setText(preamble)
        self.namelbl.show()
        self.nameedt.show()
        self.vaultlbl.show()
        self.vaultedt.show()
        self.pinedt.hide()

    def getApproval(self, name, vault, pin, kxid, send_response):
        backend = QApplication.instance().backend()
        vault = backend.get_vault(vault)
        if vault is None:
            send_response(False)
            return
        self.nameedt.setText(name)
        self.vaultedt.setText(vault['name'])
        self.pinedt.setText('%s-%s' % (pin[:3], pin[3:]))
        self.kxid = kxid
        self.send_response = send_response
        self.show()

    @Slot()
    def denyApproval(self):
        self.send_response(False)
        mainwindow = QApplication.instance().mainWindow()
        mainwindow.showMessage('Denied connection request')
        self.hide()

    @Slot()
    def grantApproval(self):
        self.send_response(True)
        preamble = '<p>Enter the PIN code below in the remote device.</p>'
        self.preamble.setText(preamble)
        self.namelbl.hide()
        self.nameedt.hide()
        self.vaultlbl.hide()
        self.vaultedt.hide()
        self.pinedt.show()

    @Slot(str)
    def pairingComplete(self, kxid):
        if kxid == self.kxid:
            self.hide()

########NEW FILE########
__FILENAME__ = frontend
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import sys

from bluepass import util
from bluepass.factory import singleton
from bluepass.component import Component

from .application import Bluepass
from .socketapi import QtSocketApiClient


class QtFrontend(Component):
    """Qt frontend for Bluepass."""

    name = 'qt'
    description = 'GUI frontend based on Qt and PyQt4'

    @classmethod
    def add_options(cls, parser):
        """Add command-line arguments."""
        group = parser.add_argument_group('Options for Qt frontend')
        group.add_argument('--qt-options', metavar='OPTIONS', default='',
                           help='Comma-separated list of Qt internal options')

    def run(self):
        """Start up the application."""
        args = [sys.argv[0]]
        qt_options = self.options.qt_options
        args += map(lambda o: '-{0}'.format(o.strip()), qt_options.split(','))
        app = singleton(Bluepass, args)

        addr = util.paddr(self.options.connect)
        socketapi = singleton(QtSocketApiClient)
        socketapi.connect(addr)

        return app.exec_()

########NEW FILE########
__FILENAME__ = mainwindow
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

from PyQt4.QtCore import QPoint, Qt, Slot, Signal
from PyQt4.QtGui import (QLabel, QLineEdit, QIcon, QPixmap, QPushButton,
        QAction, QMenu, QStatusBar, QKeySequence, QWidget, QFrame,
        QHBoxLayout, QVBoxLayout, QApplication, QMessageBox)

from bluepass.util import asset
from .dialogs import PairingApprovalDialog
from .passwordview import VaultView
from .vaultmanager import VaultManager
from .socketapi import QtSocketApiError


class ClearButton(QLabel):

    def __init__(self, *args, **kwargs):
        super(ClearButton, self).__init__(*args, **kwargs)
        pixmap = QPixmap(asset('png', 'clear.png'))
        self.setPixmap(pixmap)
        self.resize(pixmap.size())
        self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        self.parent().clear()


class SearchEditor(QLineEdit):

    def __init__(self, *args, **kwargs):
        super(SearchEditor, self).__init__(*args, **kwargs)
        self.setPlaceholderText('Enter a search term')
        icon = QLabel(self)
        pixmap = QPixmap(asset('png', 'search.png'))
        icon.setPixmap(pixmap)
        icon.resize(pixmap.size())
        self.searchicn = icon
        self.clearbtn = ClearButton(self)
        self.setTextMargins(30, 0, 30, 0)
        self.setFocusPolicy(Qt.NoFocus)
        self.current_vault = None
        self.queries = {}

    def resizeEvent(self, event):
        searchicn = self.searchicn
        searchicn.move(6, 1 + (self.height() - searchicn.height())//2)
        clearbtn = self.clearbtn
        clearbtn.move(self.width() - clearbtn.width() - 7,
                      1 + (self.height() - clearbtn.height())//2)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.parent().sink.setFocus()
            self.clear()
        else:
            super(SearchEditor, self).keyPressEvent(event)

    @Slot(str)
    def currentVaultChanged(self, uuid):
        self.queries[self.current_vault] = self.text()
        text = self.queries.get(uuid, '')
        self.setText(text)
        self.current_vault = uuid

    @Slot(int)
    def currentVaultItemCountChanged(self, count):
        if count > 0:
            self.setFocusPolicy(Qt.StrongFocus)
        else:
            self.setText('')
            self.setFocusPolicy(Qt.NoFocus)


class MenuButton(QPushButton):

    def __init__(self, parent=None):
        super(MenuButton, self).__init__(parent)
        self.setObjectName('menu')
        self.setIcon(QIcon(QPixmap(asset('png', 'bluepass-logo-48.png'))))
        self.setFocusPolicy(Qt.TabFocus)
        self.setFlat(True)
        self.buildMenu()

    def buildMenu(self):
        menu = QMenu(self)
        lockvault = menu.addAction('Lock Vault')
        lockvault.triggered.connect(self.lockVault)
        self.lockvault = lockvault
        managevaults = menu.addAction('Manage Vaults')
        managevaults.triggered.connect(self.showVaultManager)
        self.managevaults = managevaults
        visiblecb = menu.addAction('Be Visible for 60 seconds')
        visiblecb.setCheckable(True)
        visiblecb.toggled.connect(self.setAllowPairing)
        backend = QApplication.instance().backend()
        backend.AllowPairingStarted.connect(self.allowPairingStarted)
        backend.AllowPairingEnded.connect(self.allowPairingEnded)
        self.visiblecb = visiblecb
        menu.addSeparator()
        additem = menu.addAction('Add Password')
        additem.triggered.connect(self.addPassword)
        self.additem = additem
        copyuser = QAction('Copy Username', menu)
        copyuser.setShortcut(QKeySequence('CTRL+U'))
        copyuser.triggered.connect(self.copyUsername)
        menu.addAction(copyuser)
        self.copyuser = copyuser
        copypass = QAction('Copy Password', menu)
        copypass.setShortcut(QKeySequence('CTRL+C'))
        copypass.triggered.connect(self.copyPassword)
        menu.addAction(copypass)
        self.copypass = copypass
        menu.addSeparator()
        about = menu.addAction('About')
        about.triggered.connect(self.showAbout)
        self.about = about
        menu.addSeparator()
        quit = QAction('Exit', menu)
        quit.setShortcut(QKeySequence('CTRL+Q'))
        qapp = QApplication.instance()
        quit.triggered.connect(qapp.quit)
        menu.addAction(quit)
        self.setMenu(menu)

    @Slot()
    def copyUsername(self):
        qapp = QApplication.instance()
        version = qapp.mainWindow().passwordView().selectedVersion()
        username = version.get('username', '')
        qapp.copyToClipboard(username)

    @Slot()
    def copyPassword(self):
        qapp = QApplication.instance()
        version = qapp.mainWindow().passwordView().selectedVersion()
        password = version.get('password', '')
        qapp.copyToClipboard(password, 60)

    @Slot()
    def lockVault(self):
        qapp = QApplication.instance()
        mainwindow = qapp.mainWindow()
        pwview = mainwindow.passwordView()
        vault = pwview.currentVault()
        if not vault:
            return
        backend = qapp.backend()
        try:
            backend.lock_vault(vault)
        except QtSocketApiError as e:
            mainwindow.showMessage('Could not lock vault: %s' % str(e))
        else:
            mainwindow.showMessage('Vault was locked succesfully')

    @Slot()
    def addPassword(self):
        pwview = QApplication.instance().mainWindow().passwordView()
        pwview.newPassword()

    @Slot()
    def showVaultManager(self):
        mainwindow = QApplication.instance().mainWindow()
        mainwindow.showVaultManager()

    @Slot(bool)
    def setAllowPairing(self, checked):
        backend = QApplication.instance().backend()
        backend.set_allow_pairing(60 if checked else 0)
  
    @Slot(int)
    def allowPairingStarted(self, timeout):
        mainwindow = QApplication.instance().mainWindow()
        mainwindow.showMessage('Vaults will be visible for %d seconds' % timeout)

    @Slot()
    def allowPairingEnded(self):
        self.visiblecb.setChecked(False)
        mainwindow = QApplication.instance().mainWindow()
        mainwindow.showMessage('Vaults are no longer visible')

    @Slot()
    def showAbout(self):
        mainwindow = QApplication.instance().mainWindow()
        mainwindow.showAbout()

    def enableEntries(self):
        qapp = QApplication.instance()
        backend = qapp.backend()
        locatorAvailable = backend.locator_is_available()
        self.visiblecb.setEnabled(locatorAvailable)
        pwview = qapp.mainWindow().passwordView()
        versionSelected = bool(pwview.selectedVersion())
        self.copyuser.setEnabled(versionSelected)
        self.copypass.setEnabled(versionSelected)
        unlocked = not pwview.isCurrentVaultLocked()
        self.lockvault.setEnabled(unlocked)
        self.additem.setEnabled(unlocked)

    def enterEvent(self, event):
        self.setFlat(False)
        
    def leaveEvent(self, event):
        self.setFlat(True)

    def mousePressEvent(self, event):
        self.enableEntries()
        super(MenuButton, self).mousePressEvent(event)


class AddButton(QPushButton):

    def __init__(self, *args, **kwargs):
        super(AddButton, self).__init__(*args, **kwargs)
        icon = QIcon(QPixmap(asset('png', 'add.png')))
        self.setIcon(icon)
        self.clicked.connect(self.newPassword)
        self.setFlat(True)
        self.setFixedSize(30, 28)
        self.setFocusPolicy(Qt.TabFocus)
        self.setEnabled(False)

    @Slot(str)
    def currentVaultChanged(self, uuid):
        pwview = QApplication.instance().mainWindow().passwordView()
        enabled = pwview.hasCurrentVault() and not pwview.isCurrentVaultLocked()
        self.setEnabled(enabled)

    @Slot()
    def newPassword(self):
        pwview = QApplication.instance().mainWindow().passwordView()
        pwview.newPassword()

    def enterEvent(self, event):
        if self.isEnabled():
            self.setFlat(False)

    def leaveEvent(self, event):
        self.setFlat(True)


class MainWindow(QWidget):

    stylesheet = """
        QStatusBar { border: 0; }
        SearchEditor { height: 22px; background-color: white; }
        MenuButton { height: 22px; }
        MenuButton::menu-indicator { width: 0; }
        QLineEdit { height: 22px; }
    """

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setObjectName('top')
        self.setWindowTitle('Bluepass')
        self.addWidgets()
        self.resize(300, 400)
        self.first = True
        self.setStyleSheet(self.stylesheet)
        self.vaultmgr = VaultManager(self)
        self.pairdlg = PairingApprovalDialog(self)

    def addWidgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        hbox = QHBoxLayout()
        hbox.setSpacing(4)
        hbox.setContentsMargins(8, 8, 8, 2)
        searchbox = SearchEditor()
        hbox.addWidget(searchbox)
        self.searchbox = searchbox
        menu = MenuButton(self)
        hbox.addWidget(menu)
        layout.addLayout(hbox)
        pwview = VaultView(self)
        searchbox.textChanged.connect(pwview.setSearchQuery)
        pwview.currentVaultChanged.connect(searchbox.currentVaultChanged)
        pwview.currentVaultItemCountChanged.connect(searchbox.currentVaultItemCountChanged)
        layout.addWidget(pwview)
        self.pwview = pwview
        hbox = QHBoxLayout()
        addbutton = AddButton()
        pwview.currentVaultChanged.connect(addbutton.currentVaultChanged)
        hbox.addWidget(addbutton)
        frame = QFrame()
        frame.setFrameStyle(QFrame.VLine|QFrame.Raised)
        frame.setLineWidth(1)
        frame.setFixedHeight(26)
        hbox.addWidget(frame)
        statusbar = QStatusBar()
        hbox.addWidget(statusbar)
        self.statusbar = statusbar
        self.sink = QWidget()
        self.sink.setFocusPolicy(Qt.ClickFocus)
        self.sink.resize(0, 0)
        hbox.addWidget(self.sink)
        layout.addLayout(hbox)

    @Slot()
    def connectVault(self):
        vaultmgr = QApplication.instance().mainWindow().vaultManager()
        vaultmgr.setEnableNavigation(False)
        vaultmgr.showPage('ConnectVault')

    @Slot()
    def loseFocus(self):
        self.sink.setFocus()

    def showEvent(self, event):
        if not self.first:
            return
        self.loseFocus()
        self.pwview.loadVaults()
        self.first = False

    def showMessage(self, message):
        self.statusbar.showMessage(message, 10000)

    def passwordView(self):
        return self.pwview

    def vaultManager(self):
        return self.vaultmgr

    def showAbout(self):
        backend = QApplication.instance().backend()
        version_info = backend.get_version_info()
        text = '<p><b>Bluepass password manager, version %s</b></p>' \
               '<p>Bluepass is copyright (c) 2012-2013 Geert Jansen. ' \
               'Bluepass is free software available under the GNU General ' \
               'Public License, version 3. For more  information, see ' \
               '<a href="http://bluepass.org/">http://bluepass.org/</a>.</p>' \
               % version_info['version']
        QMessageBox.about(self, 'Bluepass', text)

    def showVaultManager(self, page='ManageVaults'):
        self.vaultmgr.reset()
        self.vaultmgr.showPage(page)

    def showPairingApprovalDialog(self, name, vault, pin, kxid, send_response):
        self.pairdlg.reset()
        self.pairdlg.getApproval(name, vault, pin, kxid, send_response)

########NEW FILE########
__FILENAME__ = passwordbutton
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

from PyQt4.QtCore import QTimer, Signal, Slot, Property, Qt, QPoint
from PyQt4.QtGui import (QPushButton, QStylePainter, QStyleOptionButton,
        QStyle, QGridLayout, QWidget, QLabel, QSpinBox, QLineEdit, QFrame,
        QApplication, QCheckBox, QFontMetrics)


class NoSelectSpinbox(QSpinBox):
    """This is a SpinBox that:

     * Will not select the displayed text when the value changes.
     * Does not accept keyboard input.
    """

    def __init__(self, parent=None):
        super(NoSelectSpinbox, self).__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)

    def stepBy(self, amount):
        super(NoSelectSpinbox, self).stepBy(amount)
        self.lineEdit().deselect()


class StrengthIndicator(QLabel):
    """A password strength indicator.

    This is a label that gives feedback on the strength of a password.
    """

    Poor, Good, Excellent = range(3)

    stylesheet = """
        StrengthIndicator { border: 1px solid black; }
        StrengthIndicator[strength="0"] { background-color: #ff2929; }
        StrengthIndicator[strength="1"] { background-color: #4dd133; }
        StrengthIndicator[strength="2"] { background-color: #4dd133; }
    """

    def __init__(self, parent=None):
        super(StrengthIndicator, self).__init__(parent)
        self._strength = 0
        self.setStyleSheet(self.stylesheet)

    def getStrength(self):
        return self._strength
    
    def setStrength(self, strength):
        self._strength = strength
        if strength == self.Poor:
            self.setText('Poor')
        elif strength == self.Good:
            self.setText('Good')
        elif strength == self.Excellent:
            self.setText('Excellent')
        self.setStyleSheet(self.stylesheet)

    strength = Property(int, getStrength, setStrength)


class PasswordConfiguration(QFrame):
    """Base class for password configuration popups.

    A password popup is installed in a GeneratePasswordButton, and allows
    the user to customize the parameters of password generation.
    """

    def __init__(self, method, parent=None):
        super(PasswordConfiguration, self).__init__(parent)
        self.method = method
        self.parameters = []

    parametersChanged = Signal(str, list)


class DicewarePasswordConfiguration(PasswordConfiguration):
    """Configuration for Diceware password generation."""

    stylesheet = """
        PasswordConfiguration { border: 1px solid grey; }
    """

    def __init__(self, parent=None):
        super(DicewarePasswordConfiguration, self).__init__('diceware', parent)
        self.parameters = [5]
        self.addWidgets()
        self.setFixedSize(self.sizeHint())
        self.setStyleSheet(self.stylesheet)

    def addWidgets(self):
        grid = QGridLayout()
        self.setLayout(grid)
        grid.setColumnMinimumWidth(1, 10)
        label = QLabel('Length', self)
        grid.addWidget(label, 0, 0)
        spinbox = NoSelectSpinbox(self)
        spinbox.setSuffix(' words')
        spinbox.setMinimum(4)
        spinbox.setMaximum(8)
        grid.addWidget(spinbox, 0, 2)
        label = QLabel('Security', self)
        grid.addWidget(label, 1, 0)
        strength = StrengthIndicator(self)
        grid.addWidget(strength, 1, 2)
        self.strength = strength
        spinbox.valueChanged.connect(self.setParameters)
        spinbox.setValue(self.parameters[0])

    @Slot(int)
    def setParameters(self, words):
        self.parameters[0] = words
        self.updateStrength()

    @Slot()
    def updateStrength(self):
        backend = QApplication.instance().backend()
        strength = backend.password_strength(self.method, *self.parameters)
        # We use Diceware only for locking our vaults. Because we know we
        # do proper salting and key stretching, we add 20 extra bits.
        strength += 20
        if strength < 70:
            strength = StrengthIndicator.Poor
        elif strength < 94:
            strength = StrengthIndicator.Good
        else:
            strength = StrengthIndicator.Excellent
        self.strength.setStrength(strength)


class RandomPasswordConfiguration(PasswordConfiguration):
    """Configuration for random password generation."""

    stylesheet = """
        PasswordConfiguration { border: 1px solid grey; }
    """

    def __init__(self, parent=None):
        super(RandomPasswordConfiguration, self).__init__('random', parent)
        self.parameters = [12, '[a-z][A-Z][0-9]']
        self.addWidgets()
        self.setFixedSize(self.sizeHint())
        self.setStyleSheet(self.stylesheet)

    def addWidgets(self):
        grid = QGridLayout()
        self.setLayout(grid)
        grid.setColumnMinimumWidth(1, 10)
        label = QLabel('Length', self)
        grid.addWidget(label, 0, 0)
        spinbox = NoSelectSpinbox(self)
        spinbox.setSuffix(' characters')
        spinbox.setMinimum(6)
        spinbox.setMaximum(20)
        grid.addWidget(spinbox, 0, 2, 1, 2)
        label = QLabel('Characters')
        grid.addWidget(label, 1, 0)
        def updateInclude(s):
            def stateChanged(state):
                self.updateInclude(state, s)
            return stateChanged
        lower = QCheckBox('Lower')
        grid.addWidget(lower, 1, 2)
        lower.stateChanged.connect(updateInclude('[a-z]'))
        upper = QCheckBox('Upper')
        grid.addWidget(upper, 1, 3)
        upper.stateChanged.connect(updateInclude('[A-Z]'))
        digits = QCheckBox('Digits')
        grid.addWidget(digits, 2, 2)
        digits.stateChanged.connect(updateInclude('[0-9]'))
        special = QCheckBox('Special')
        grid.addWidget(special, 2, 3)
        special.stateChanged.connect(updateInclude('[!-/]'))
        label = QLabel('Security', self)
        grid.addWidget(label, 3, 0)
        strength = StrengthIndicator(self)
        grid.addWidget(strength, 3, 2)
        self.strength = strength
        spinbox.valueChanged.connect(self.setLength)
        spinbox.setValue(self.parameters[0])
        lower.setChecked('[a-z]' in self.parameters[1])
        upper.setChecked('[A-Z]' in self.parameters[1])
        digits.setChecked('[0-9]' in self.parameters[1])
        special.setChecked('[!-/]' in self.parameters[1])

    @Slot(int)
    def setLength(self, length):
        self.parameters[0] = length
        self.parametersChanged.emit(self.method, self.parameters)
        self.updateStrength()

    @Slot()
    def updateInclude(self, enable, s):
        if enable and s not in self.parameters[1]:
            self.parameters[1] += s
        elif not enable:
            self.parameters[1] = self.parameters[1].replace(s, '')
        self.parametersChanged.emit(self.method, self.parameters)
        self.updateStrength()

    @Slot()
    def updateStrength(self):
        backend = QApplication.instance().backend()
        strength = backend.password_strength(self.method, *self.parameters)
        # We do not know if the remote site does key stretching or salting.
        # So we only give a Good rating if the entropy takes the password
        # out of reach of the largest Rainbow tables.
        if strength < 60:
            strength = StrengthIndicator.Poor
        elif strength < 84:
            strength = StrengthIndicator.Good
        else:
            strength = StrengthIndicator.Excellent
        self.strength.setStrength(strength)


class PopupButton(QPushButton):
    """A button with a popup.

    The popup will be displayed just below the button after the user
    keeps the button pressed for 500 msecs.
    """

    def __init__(self, text, parent=None):
        super(PopupButton, self).__init__(text, parent)
        timer = QTimer()
        timer.setSingleShot(True)
        timer.setInterval(500)
        timer.timeout.connect(self.showPopup)
        self.timer = timer
        self.popup = None

    # I would have preferred to implement the menu indicator by overriding
    # initStyleOption(), and nothing else, but it doesn't work. The C++
    # ::paintEvent() and ::sizeHint() are not able to call into it. So we need
    # to provide our own paintEvent() and sizeHint() too.

    def initStyleOption(self, option):
        super(PopupButton, self).initStyleOption(option)
        option.features |= option.HasMenu

    def paintEvent(self, event):
        p = QStylePainter(self)
        opts = QStyleOptionButton()
        self.initStyleOption(opts)
        p.drawControl(QStyle.CE_PushButton, opts)

    def sizeHint(self):
        size = super(PopupButton, self).sizeHint()
        fm = QFontMetrics(QApplication.instance().font())
        width = fm.width(self.text())
        opts = QStyleOptionButton()
        self.initStyleOption(opts)
        style = self.style()
        dw = style.pixelMetric(QStyle.PM_MenuButtonIndicator, opts, self)
        size.setWidth(width + dw + 10)
        return size

    def mousePressEvent(self, event):
        self.timer.start()
        super(PopupButton, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.timer.stop()
        super(PopupButton, self).mouseReleaseEvent(event)

    def setPopup(self, popup):
        popup.setParent(None)
        popup.setWindowFlags(Qt.Popup)
        popup.hide()
        # Install a closeEvent() on the popup that raises the button.
        def closeEvent(*args):
            self.setDown(False)
        popup.closeEvent = closeEvent
        self.popup = popup

    @Slot()
    def showPopup(self):
        if not self.popup:
            return
        pos = QPoint(self.width(), self.height())
        pos = self.mapToGlobal(pos)
        size = self.popup.size()
        self.popup.move(pos.x() - size.width(), pos.y())
        self.popup.show()


class GeneratePasswordButton(PopupButton):
    """A password generation button.

    A password is generated each time the user clicks the button.
    """

    def __init__(self, text, popup, parent=None):
        super(GeneratePasswordButton, self).__init__(text, parent)
        self.method = popup.method
        self.parameters = popup.parameters
        self.setPopup(popup)
        popup.parametersChanged.connect(self.parametersChanged)
        self.clicked.connect(self.generate)

    @Slot(str, list)
    def parametersChanged(self, method, parameters):
        self.method = method
        self.parameters = parameters
        self.generate()

    @Slot()
    def generate(self):
        backend = QApplication.instance().backend()
        password = backend.generate_password(self.method, *self.parameters)
        self.passwordGenerated.emit(password)

    passwordGenerated = Signal(str)

########NEW FILE########
__FILENAME__ = passwordview
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import math
import logging
from string import Template

from PyQt4.QtCore import Slot, Signal, Property, Qt
from PyQt4.QtGui import (QScrollArea, QWidget, QLabel, QVBoxLayout, QPixmap,
        QHBoxLayout, QVBoxLayout, QPushButton, QLineEdit, QFrame, QIcon,
        QApplication, QTabBar, QSizePolicy, QCheckBox, QStackedWidget,
        QGridLayout, QMenu, QKeySequence)

from bluepass.util import asset
from .util import SortedList
from .socketapi import QtSocketApiError
from .dialogs import EditPasswordDialog


def sortkey(version):
    """Return a key that established the order of items as they
    appear in our VaultView."""
    key = '%s\x00%s' % (version.get('group', ''),
                        version.get('name', ''))
    return key


def searchkey(version):
    """Return a single string that is used for matching items with
    the query entered in the search box."""
    key = '%s\000%s\000%s\000%s' % \
            (version.get('name', ''), version.get('comment', ''),
             version.get('url', ''), version.get('username', ''))
    return key.lower()


class NoVaultWidget(QFrame):
    """No Vault widget.

    This widget is shown in the VaultView when there are no vaults yet.
    It offers a brief explanation, and buttons to create a new vault or
    connect to an existing one.
    """

    def __init__(self, parent=None):
        super(NoVaultWidget, self).__init__(parent)
        self.addWidgets()

    def addWidgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addSpacing(10)
        label = QLabel(self)
        label.setTextFormat(Qt.RichText)
        label.setText('<p>There are currently no vaults.</p>'
                      '<p>To store passwords in Bluepass, '
                      'you need to create a vault first.</p>')
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addSpacing(10)
        hbox = QHBoxLayout()
        layout.addLayout(hbox)
        newbtn = QPushButton('Create New Vault', self)
        newbtn.clicked.connect(self.newVault)
        hbox.addStretch(100);
        hbox.addWidget(newbtn)
        hbox.addStretch(100)
        hbox = QHBoxLayout()
        layout.addLayout(hbox)
        connectbtn = QPushButton('Connect to Existing Vault', self)
        connectbtn.clicked.connect(self.connectVault)
        hbox.addStretch(100)
        hbox.addWidget(connectbtn)
        hbox.addStretch(100)
        width = max(newbtn.sizeHint().width(),
                    connectbtn.sizeHint().width()) + 40
        newbtn.setFixedWidth(width)
        connectbtn.setFixedWidth(width)
        layout.addStretch(100)

    @Slot()
    def newVault(self):
        """Show the vault manager to create a new vault."""
        vaultmgr = QApplication.instance().mainWindow().vaultManager()
        page = vaultmgr.page('NewVaultSimplified')
        page.reset()
        page.setName('My Passwords')
        vaultmgr.showPage(page)

    @Slot()
    def connectVault(self):
        """Show the vault manager to connect to an existing vault."""
        vaultmgr = QApplication.instance().mainWindow().vaultManager()
        page = vaultmgr.page('ShowNeighborsSimplified')
        page.reset()
        vaultmgr.showPage(page)


class UnlockVaultWidget(QFrame):
    """Unlock widget.
    
    This widget is displayed in the VaultView when a vault is locked.
    It allows the user to enter a password to unlock the vault.
    """

    def __init__(self, vault, parent=None):
        super(UnlockVaultWidget, self).__init__(parent)
        self.vault = vault
        self.addWidgets()
        self.loadConfig()

    def addWidgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addSpacing(10)
        preamble = QLabel('This vault is locked.', self)
        layout.addWidget(preamble)
        passwdedt = QLineEdit(self)
        passwdedt.setPlaceholderText('Type password to unlock')
        passwdedt.setEchoMode(QLineEdit.Password)
        passwdedt.textChanged.connect(self.passwordChanged)
        passwdedt.returnPressed.connect(self.unlockVault)
        layout.addSpacing(10)
        layout.addWidget(passwdedt)
        self.passwdedt = passwdedt
        unlockcb = QCheckBox('Try unlock other vaults too', self)
        unlockcb.stateChanged.connect(self.saveConfig)
        unlockcb.setVisible(False)
        layout.addWidget(unlockcb)
        self.unlockcb = unlockcb
        status = QLabel('', self)
        status.setVisible(False)
        status.setContentsMargins(0, 10, 0, 0)
        layout.addWidget(status)
        self.status = status
        hbox = QHBoxLayout()
        unlockbtn = QPushButton('Unlock', self)
        unlockbtn.setFixedSize(unlockbtn.sizeHint())
        unlockbtn.clicked.connect(self.unlockVault)
        unlockbtn.setEnabled(False)
        hbox.addWidget(unlockbtn)
        self.unlockbtn = unlockbtn
        hbox.addStretch(100)
        layout.addSpacing(10)
        layout.addLayout(hbox)
        layout.addStretch(100)

    def loadConfig(self):
        config = QApplication.instance().config()
        checked = config.get('Frontend', {}).get('Qt', {}). \
                get('UnlockVaultWidget', {}).get('unlock_others', 0)
        self.unlockcb.setChecked(checked)

    @Slot()
    def saveConfig(self):
        qapp = QApplication.instance()
        config = qapp.config()
        section = config.setdefault('Frontend', {}).setdefault('Qt', {}). \
                setdefault('UnlockVaultWidget', {})
        unlock_others = self.unlockcb.isChecked()
        section['unlock_others'] = unlock_others
        qapp.update_config(config)

    @Slot(str)
    def passwordChanged(self, password):
        self.unlockbtn.setEnabled(password != '')

    @Slot(int)
    def vaultCountChanged(self, count):
        pwview = QApplication.instance().mainWindow().passwordView()
        locked = len(pwview.lockedVaults())
        self.unlockcb.setVisible(locked > 1)

    @Slot(str)
    def setStatus(self, status):
        self.status.setText(status)
        self.status.setVisible(bool(status))

    @Slot()
    def unlockVault(self):
        qapp = QApplication.instance()
        backend = qapp.backend()
        mainwindow = qapp.mainWindow()
        password = self.passwdedt.text()
        unlock_others = self.unlockcb.isChecked()
        try:
            success = backend.unlock_vault(self.vault, password)
        except QtSocketApiError as e:
            status = '<i>Could not unlock vault: %s</i>' % e.error_message
            self.setStatus(status)
            return
        self.setStatus('')
        if not unlock_others:
            mainwindow.showMessage('Vault was unlocked successfully')
            return
        count = 1
        vaults = backend.get_vaults()
        for vault in vaults:
            uuid = vault['id']
            if uuid == self.vault:
                continue
            if not backend.vault_is_locked(uuid):
                continue
            try:
                backend.unlock_vault(uuid, password)
            except QtSocketApiError:
                pass
            else:
                count += 1
        mainwindow.showMessage('%d vaults were unlocked successfully' % count)

    @Slot()
    def reset(self):
        self.passwdedt.clear()
        qapp = QApplication.instance()
        qapp.mainWindow().loseFocus()


class NoItemWidget(QFrame):
    """No item widget.

    This widget is shown in the VaultView when a vault has no items yet.
    It shows a small description and a button to create the first item.
    """

    def __init__(self, vault, parent=None):
        super(NoItemWidget, self).__init__(parent)
        self.vault = vault
        self.addWidgets()

    def addWidgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addSpacing(10)
        label = QLabel('<p>There are no passwords in this vault.</p>' \
                       '<p>Use the "+" button at the bottom of this window ' \
                       'to add a password.</p>', self)
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch(100)


class GroupItem(QLabel):
    """A group heading in a list of items."""

    def __init__(self, vault, name, parent=None):
        super(GroupItem, self).__init__(parent)
        self.vault = vault
        self.name = name
        self.displayName = name or 'No Group'
        self.opened = True
        self.addWidgets()
        self.setText(self.displayName)

    def addWidgets(self):
        opener = QLabel(self)
        self.pixmap_open = QPixmap(asset('png', 'triangle-open.png'))
        self.pixmap_closed = QPixmap(asset('png', 'triangle-closed.png'))
        opener.setPixmap(self.pixmap_open)
        opener.resize(opener.pixmap().size())
        self.opener = opener
        self.setIndent(opener.width() + 12)
        self.setMargin(2)

    openStateChanged = Signal(str, str, bool)

    @Slot(int)
    def setMatchCount(self, nmatches):
        if nmatches == -1:
            self.setText(self.displayName)
        else:
            self.setText('%s (%d)' % (self.displayName, nmatches))

    def resizeEvent(self, event):
        size = self.height()
        x = (size - self.opener.width()) // 2
        y = (size - self.opener.height()) // 2 + 1
        self.opener.move(x, y)

    def mousePressEvent(self, event):
        if not self.opener.geometry().contains(event.pos()):
            return
        if self.opened:
            self.opener.setPixmap(self.pixmap_closed)
            self.opened = False
        else:
            self.opener.setPixmap(self.pixmap_open)
            self.opened = True
        self.openStateChanged.emit(self.vault, self.name, self.opened)


class PasswordItem(QLabel):

    stylesheet = """
        PasswordItem[selected="false"]
                { color: palette(window-text); background-color: white; }
        PasswordItem[selected="true"]
                { color: palette(highlighted-text); background-color: palette(highlight); }
        QLabel { height: 18px; }
    """

    def __init__(self, vault, version, parent=None):
        super(PasswordItem, self).__init__(parent)
        self.vault = vault
        self._selected = False
        self.updateData(version)

    def getSelected(self):
        return self._selected

    def setSelected(self, selected):
        self._selected = selected
        # Re-calculate style
        self.setStyleSheet(self.stylesheet)

    selected = Property(bool, getSelected, setSelected)

    clicked = Signal(str, str)

    @Slot(dict)
    def updateData(self, version):
        self.version = version
        self.setText(version.get('name', ''))

    @Slot()
    def copyUsernameToClipboard(self):
        username = self.version.get('username', '')
        QApplication.instance().copyToClipboard(username)

    @Slot()
    def copyPasswordToClipboard(self):
        password = self.version.get('password', '')
        QApplication.instance().copyToClipboard(password, 60)

    @Slot()
    def editPassword(self):
        pwview = QApplication.instance().mainWindow().passwordView()
        pwview.editPassword(self.vault, self.version)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.vault, self.version['id'])
        elif event.button() == Qt.RightButton:
            self.showContextMenu(event.pos())

    def mouseDoubleClickEvent(self, event):
        self.editPassword()

    def showContextMenu(self, pos):
        menu = QMenu(self)
        action = menu.addAction('Copy Username')
        action.setShortcut(QKeySequence('CTRL-U'))
        action.triggered.connect(self.copyUsernameToClipboard)
        action = menu.addAction('Copy Password')
        action.setShortcut(QKeySequence('CTRL-C'))
        action.triggered.connect(self.copyPasswordToClipboard)
        menu.addSeparator()
        action = menu.addAction('Edit')
        action.triggered.connect(self.editPassword)
        action = menu.addAction('Delete')
        action.triggered.connect(self.deleteItem)
        menu.popup(self.mapToGlobal(pos))

    @Slot()
    def deleteItem(self):
        backend = QApplication.instance().backend()
        version = { 'id': self.version['id'], 'name': self.version['name'],
                    '_type': self.version['_type'] }
        backend.delete_version(self.vault, version)


class VersionList(QScrollArea):
    """A container for passwords and group."""

    def __init__(self, parent=None):
        super(VersionList, self).__init__(parent)
        contents = QFrame(self)
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(100)
        contents.setLayout(layout)
        self.setWidget(contents)
        self.contents = contents

    def insertItem(self, pos, item):
        item.setParent(self.contents)
        self.contents.layout().insertWidget(pos, item)

    def removeItem(self, item):
        self.contents.layout().removeWidget(item)

    def resizeEvent(self, event):
        width = self.viewport().width()
        height = max(self.viewport().height(),
                     self.widget().sizeHint().height())
        self.widget().resize(width, height)

    def items(self):
        layout = self.contents.layout()
        items = [ layout.itemAt(pos).widget()
                  for pos in range(layout.count()-1) ]
        return items


class VaultView(QWidget):
    """The main "vault view" widget.

    This widget shows a tabbar and a set of ScrollArea's that show the
    contents of each vault.

    This is an "active" component in the sense that VaultView makes
    modifications to the model directly based on the user input. It
    accesses the model via the singleton BackendProxy instance at
    QAplication.instance().backend().
    """

    stylesheet = """
        NoVaultWidget, UnlockVaultWidget, NoItemWidget { background-color: white; border: 1px solid grey; }
        VersionList > QWidget > QFrame { background-color: white; border: 1px solid grey; }
        QTabBar { font: normal ${smaller}pt; }
        GroupItem { margin: 0; padding: 0; border: 0; background:
                qlineargradient(x1:0, y1:0, x2:0, y2:1, stop: 0 #ddd, stop: 1 #aaa) }
    """


    def __init__(self, parent=None):
        """Create a new password view."""
        super(VaultView, self).__init__(parent)
        self.vaults = {}
        self.vault_order = SortedList()
        self.current_vault = None
        self.versions = {}
        self.version_order = {}
        self.current_item = {}
        self.logger = logging.getLogger(__name__)
        self.addWidgets()
        self.setStyleSheet(self.stylesheet)
        editpwdlg = EditPasswordDialog()
        self.groupAdded.connect(editpwdlg.addGroup)
        self.groupRemoved.connect(editpwdlg.removeGroup)
        self.editpwdlg = editpwdlg
        backend = QApplication.instance().backend()
        backend.VaultAdded.connect(self.updateVault)
        backend.VaultRemoved.connect(self.updateVault)
        backend.VaultLocked.connect(self.vaultLocked)
        backend.VaultUnlocked.connect(self.vaultUnlocked)
        backend.VersionsAdded.connect(self.updateVaultItems)

    def addWidgets(self):
        """Create main layout."""
        logger = self.logger
        logger.debug('adding widgets')
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        tabbar = QTabBar(self)
        tabbar.setFocusPolicy(Qt.NoFocus)
        tabbar.setVisible(False)
        tabbar.currentChanged.connect(self.changeVault)
        layout.addWidget(tabbar)
        self.tabbar = tabbar
        stack = QStackedWidget(self)
        layout.addWidget(stack)
        novault = NoVaultWidget(stack)
        stack.addWidget(novault)
        self.stack = stack

    def setStyleSheet(self, stylesheet):
        """Set our style sheet. Reimplemented from QWidget.setStyleSheet()
        to perform substitutions."""
        subst = {}
        qapp = QApplication.instance()
        subst['smaller'] = int(math.ceil(0.8 * qapp.font().pointSize()))
        stylesheet = Template(stylesheet).substitute(subst)
        super(VaultView, self).setStyleSheet(stylesheet)

    def loadVaults(self):
        """Load all vaults."""
        backend = QApplication.instance().backend()
        vaults = backend.get_vaults()
        for vault in vaults:
            self.updateVault(vault)
        if self.vault_order:
            self.tabbar.setCurrentIndex(0)

    def updateVault(self, vault):
        """Update a vault, which may or may not exist already."""
        logger = self.logger
        uuid = vault['id']
        name = vault.get('name', '')
        logger.debug('updateVault() for %s (name: "%s")', uuid, name)
        deleted = vault.get('deleted', False)
        if not deleted and (uuid not in self.vaults or
                    uuid in self.vaults and
                    self.vaults[uuid].get('deleted', False)):
            logger.debug('this is a new vault')
            self.vaults[uuid] = vault
            unlocker = UnlockVaultWidget(uuid, self.stack)
            self.vaultCountChanged.connect(unlocker.vaultCountChanged)
            self.stack.addWidget(unlocker)
            noitems = NoItemWidget(uuid, self.stack)
            self.stack.addWidget(noitems)
            items = VersionList(self.stack)
            self.stack.addWidget(items)
            widgets = (unlocker, noitems, items)
            pos = self.vault_order.insert(name, uuid, widgets)
            backend = QApplication.instance().backend()
            if not backend.vault_is_locked(uuid):
                logger.debug('new vault is unlocked')
                self.versions[uuid] = {}
                self.version_order[uuid] = SortedList()
                self.current_item[uuid] = None
                versions = backend.get_versions(vault['id'])
                self.updateVaultItems(uuid, versions)
            self.tabbar.insertTab(pos, name)
        elif not deleted and uuid in self.vaults and \
                self.vaults[uuid].get('name', '') != name:
            logger.debug('this vault was renamed')
            curname = self.vaults[uuid].get('name', '')
            curpos = self.vault_order.find(curname, uuid)
            assert curpos != -1
            self.vaults[uuid] = vault
            widgets = self.vault_order.dataat(curpos)
            self.vault_order.removeat(curpos)
            pos = self.vault_order.insert(name, uuid, widgets)
            self.tabbar.removeTab(curpos)
            self.tabbar.insertTab(pos, name)
        elif deleted and uuid in self.vaults and \
                not self.vaults[uuid].get('deleted', False):
            logger.debug('this vault was deleted')
            curname = self.vaults[uuid].get('name', '')
            pos = self.vault_order.find(curname, uuid)
            assert pos != -1
            self.vaults[uuid] = vault
            widgets = self.vault_order.dataat(pos)
            self.vault_order.removeat(pos)
            self.tabbar.removeTab(pos)
            for widget in widgets:
                self.stack.removeWidget(widget)
        else:
            self.vaults[uuid] = vault
        self.tabbar.setVisible(len(self.vault_order) > 1)
        self.vaultCountChanged.emit(len(self.vault_order))

    @Slot(str, list)
    def updateVaultItems(self, uuid, versions):
        """Load the versions of a vault."""
        logger = self.logger
        logger.debug('updating %d versions for vault %s', len(versions), uuid)
        assert uuid in self.vaults
        vault = self.vaults[uuid]
        name = vault.get('name', '')
        pos = self.vault_order.find(name, uuid)
        assert pos != -1
        unlocker, noitems, items = self.vault_order.dataat(pos)
        modifications = []
        current_versions = self.versions[uuid]
        current_order = self.version_order[uuid]
        # Create a list of all operations that we need to execute on the
        # layout. We sort this list on the sortkey of the item. This makes
        # the logic easier, and it will also be slightly faster (as we don't
        # need to insert items in the middle).
        for version in versions:
            vuuid = version['id']
            key = sortkey(version)
            present = not version['_envelope'].get('deleted', False)
            cur_present = vuuid in current_versions
            cur_deleted = current_versions.get('vuuid', {}) \
                    .get('_envelope', {}).get('deleted', False)
            if present:
                if not cur_present:
                    modifications.append((key, 'new', version))
                elif cur_present and not cur_deleted:
                    modifications.append((key, 'update', version))
                elif cur_deleted:
                    modifications.append((key, 'undelete', version))
            else:
                if cur_present and not cur_deleted:
                    modifications.append((key, 'delete', version))
        modifications.sort()
        # Now execute the operations on the layout in the order the items
        # will appear on the screen.
        for key,mod,version in modifications:
            vuuid = version['id']
            curversion = current_versions.get(vuuid)
            if mod in ('new', 'update'):
                # Need to insert a new group?
                group = version.get('group', '')
                grouppos = current_order.find(group)
                if grouppos == -1:
                    item = GroupItem(uuid, group)
                    item.openStateChanged.connect(self.setGroupOpenState)
                    pos = current_order.insert(group, None, (item, None))
                    items.insertItem(pos, item)
                    self.groupAdded.emit(uuid, group)
            if mod == 'new':
                assert curversion is None
                pos = current_order.find(key)
                assert pos == -1
                item = PasswordItem(uuid, version)
                item.clicked.connect(self.changeCurrentItem)
                search = searchkey(version)
                pos = current_order.insert(key, vuuid, (item, search))
                items.insertItem(pos, item)
            elif mod == 'update':
                assert curversion is not None
                curkey = sortkey(curversion)
                curpos = current_order.find(curkey, vuuid)
                assert curpos != -1
                item, search = current_order.dataat(curpos)
                item.updateData(version)
                if key != curkey:
                    current_order.removeat(curpos)
                    newpos = current_order.insert(key, vuuid, (item, search))
                    items.removeItem(item)
                    items.insertItem(newpos, item)
            elif mod == 'delete':
                assert curversion is not None
                curkey = sortkey(current_versions[vuuid])
                curpos = current_order.find(curkey, vuuid)
                assert curpos != -1
                item, search = current_order.dataat(curpos)
                current_order.removeat(curpos)
                items.removeItem(item)
                item.hide(); item.destroy()
                if self.current_item[uuid] == vuuid:
                    self.current_item[uuid] = None
            if mod in ('update', 'delete'):
                # Was this the last element in a group?
                curgroup = curversion.get('group', '')
                curpos = current_order.find(curgroup)
                assert curpos != -1
                prefix = '%s\x00' % curgroup
                if curpos == len(current_order)-1 or \
                        not current_order.keyat(curpos+1).startswith(prefix):
                    item, search = current_order.dataat(curpos)
                    current_order.removeat(curpos)
                    items.removeItem(item)
                    item.hide(); item.destroy()
                    self.groupRemoved.emit(uuid, group)
        # We can now update the version cache
        for version in versions:
            current_versions[version['id']] = version
        if uuid != self.current_vault:
            return
        # Do we need to switch from the noitems -> items widget?
        if len(current_order) > 0:
            self.stack.setCurrentWidget(items)
        else:
            self.stack.setCurrentWidget(items)
            self.stack.setCurrentWidget(noitems)
        self.currentVaultItemCountChanged.emit(len(current_order))

    vaultCountChanged = Signal(int)
    currentVaultChanged = Signal(str)
    currentVaultItemCountChanged = Signal(int)
    groupAdded = Signal(str, str)
    groupRemoved = Signal(str, str)

    @Slot(int)
    def changeVault(self, current):
        """Change the current vault."""
        if not self.vaults:
            return  # ignore early trigger when the slot gets connected
        if current == -1:
            self.stack.setCurrentIndex(0)
            uuid = None
        else:
            uuid = self.vault_order.valueat(current)
            unlocker, noitems, items = self.vault_order.dataat(current)
            if self.versions.get(uuid):
                self.stack.setCurrentWidget(items)
            elif uuid in self.versions:
                self.stack.setCurrentWidget(noitems)
            else:
                self.stack.setCurrentWidget(unlocker)
        self.current_vault = uuid
        self.currentVaultChanged.emit(uuid)
        nitems = len(self.version_order[uuid]) if uuid in self.versions else 0
        self.currentVaultItemCountChanged.emit(nitems)
        QApplication.instance().mainWindow().loseFocus()

    def currentVault(self):
        """Return the current vault."""
        return self.current_vault

    def lockedVaults(self):
        """Return a list of all locked vaults."""
        return [ self.vaults[uuid] for uuid in self.vault_order.itervalues()
                 if uuid not in self.versions ]

    def unlockedVaults(self):
        """Return a list of all unlocked vaults."""
        return [ self.vaults[uuid] for uuid in self.vault_order.itervalues()
                 if uuid in self.versions ]

    def selectedVersion(self):
        """Return the selected version in the current vault, if any."""
        uuid = self.currentVault()
        if uuid not in self.vaults:
            return
        if uuid not in self.versions:
            return  # locked
        assert uuid in self.current_item
        vuuid = self.current_item[uuid]
        if not vuuid:
            return
        item = self.versions[uuid][vuuid]
        return item

    @Slot(dict)
    def vaultLocked(self, vault):
        """Called when a vault was locked."""
        uuid = vault['id']
        if uuid not in self.vaults:
            return
        name = vault.get('name', '')
        pos = self.vault_order.find(name, uuid)
        if pos == -1:
            return
        if uuid not in self.versions:
            return  # already locked
        unlocker, noitems, items = self.vault_order.dataat(pos)
        self.stack.setCurrentWidget(unlocker)
        del self.versions[uuid]
        del self.version_order[uuid]
        del self.current_item[uuid]
        for item in items.items():
            items.removeItem(item)
            item.hide(); item.destroy()
        self.currentVaultChanged.emit(uuid)

    @Slot(dict)
    def vaultUnlocked(self, vault):
        """Called when a vault was unlocked."""
        uuid = vault['id']
        if uuid not in self.vaults:
            return
        name = vault.get('name', '')
        pos = self.vault_order.find(name, uuid)
        if pos == -1:
            return
        if uuid in self.versions:
            return  # already unlocked
        unlocker, noitems, items = self.vault_order.dataat(pos)
        self.versions[uuid] = {}
        self.version_order[uuid] = SortedList()
        self.current_item[uuid] = None
        backend = QApplication.instance().backend()
        versions = backend.get_versions(uuid)
        self.updateVaultItems(uuid, versions)
        unlocker.reset()
        if self.current_vault and self.current_vault != uuid:
            return
        if versions:
            self.stack.setCurrentWidget(items)
            items.resizeEvent(None)
        else:
            self.stack.setCurrentWidget(noitems)
        self.parent().loseFocus()
        self.currentVaultChanged.emit(uuid)

    @Slot(str, bool)
    def setGroupOpenState(self, uuid, group, visible):
        """Open or close a group."""
        if uuid not in self.vaults:
            return
        if uuid not in self.versions:
            return  # locked
        assert uuid in self.version_order
        vault = self.vaults[uuid]
        name = vault.get('name', '')
        pos = self.vault_order.find(name, uuid)
        if pos == -1:
            return
        items = self.vault_order.dataat(pos)[2]
        current_order = self.version_order[uuid]
        vpos = current_order.find(group)
        if vpos == -1:
            return
        vpos += 1
        prefix = '%s\x00' % group
        while vpos < len(current_order) and \
                current_order.keyat(vpos).startswith(prefix):
            item = current_order.dataat(vpos)[0]
            item.setVisible(visible)
            vpos += 1
        items.resizeEvent(None)

    @Slot(str, str)
    def changeCurrentItem(self, uuid, vuuid):
        """Change the selected item."""
        if uuid not in self.vaults:
            return
        if uuid not in self.versions:
            return  # locked
        assert uuid in self.current_item
        curuuid = self.current_item[uuid]
        if vuuid == curuuid:
            return
        current_versions = self.versions[uuid]
        current_order = self.version_order[uuid]
        if curuuid is not None:
            version = current_versions[curuuid]
            key = sortkey(version)
            pos = current_order.find(key, curuuid)
            assert pos != -1
            current = current_order.dataat(pos)[0]
            current.setSelected(False)
        if vuuid is not None:
            version = current_versions[vuuid]
            key = sortkey(version)
            pos = current_order.find(key, vuuid)
            assert pos != -1
            selected = current_order.dataat(pos)[0]
            selected.setSelected(True)
        self.current_item[uuid] = vuuid

    @Slot(str)
    def setSearchQuery(self, query):
        """Set a search query. This shows the subset of items that match
        the query."""
        if self.current_vault is None:
            return
        uuid = self.current_vault
        assert uuid in self.vaults
        if uuid not in self.versions:
            return  # locked
        if query:
            query = query.lower()
        else:
            query = None
        current_order = self.version_order[uuid]
        group = None
        for pos,key in enumerate(current_order):
            widget, searchkey = current_order.dataat(pos)
            if '\x00' not in key:
                if group is not None:
                    group.setMatchCount(-1 if query is None else nmatches)
                group = widget
                nmatches = 0
            else:
                assert group is not None
                found = not query or searchkey.find(query) != -1
                widget.setVisible(found)
                nmatches += int(found)
        if group is not None:
            group.setMatchCount(-1 if query is None else nmatches)

    def keyPressEvent(self, event):
        """Key press event handler."""
        if event.key() == Qt.Key_Escape:
            vault = self.currentVault()
            self.changeCurrentItem(vault, None)
            self.parent().loseFocus()
        else:
            super(VaultView, self).keyPressEvent(event)

    def hasCurrentVault(self):
        """Return whether there is a current vault."""
        return self.current_vault is not None

    def isCurrentVaultLocked(self):
        """Return whether the current vault is locked."""
        return self.current_vault not in self.versions

    @Slot()
    def newPassword(self):
        """Show a dialog to add a password."""
        vault = self.currentVault()
        current = self.selectedVersion()
        group = current.get('group') if current else ''
        version = { '_type': 'Password', 'group': group }
        self.editpwdlg.editPassword(vault, version)

    @Slot(str, dict)
    def editPassword(self, vault, version):
        """Show a dialog to edit a password."""
        self.editpwdlg.editPassword(vault, version)

########NEW FILE########
__FILENAME__ = qjsonrpc
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import json
import errno
import socket
import logging
import collections
import fnmatch

from PyQt4.QtCore import (QEvent, QObject, QSocketNotifier, QTimer, QEventLoop,
                          QCoreApplication)

from gruvi import jsonrpc
from bluepass import platform, util


__all__ = ['QJsonRpcError', 'QJsonRpcClient', 'QJsonRpcHandler', 'request',
           'notification']

# re-export these to our consumers as module-level objects
from gruvi.jsonrpc import (create_request, create_response, create_error,
                           create_notification)


class _Dispatch(QEvent):
    """Event used by QJsonRpcClient to start dispatching messages."""

    _evtype = QEvent.Type(QEvent.registerEventType())

    def __init__(self):
        super(_Dispatch, self).__init__(self._evtype)


class QJsonRpcError(Exception):
    pass


class QJsonRpcClient(QObject):
    """A JSON-RPC client integrated with the Qt event loop."""

    default_timeout = 5

    def __init__(self, message_handler=None, timeout=-1, parent=None):
        """Create a new message bus connection.

        The *handler* specifies an optional message handler.
        """
        super(QJsonRpcClient, self).__init__(parent)
        self._message_handler = message_handler
        self._timeout = timeout if timeout != -1 else self.default_timeout
        self._socket = None
        self._method_calls = {}
        self._outbuf = b''
        self._incoming = collections.deque()
        self._outgoing = collections.deque()
        self._parser = jsonrpc.JsonRpcParser()
        self._read_notifier = None
        self._write_notifier = None
        self._log = logging.getLogger('bluepass.qjsonrpc')

    @property
    def timeout(self):
        return self._timeout

    def connect(self, address):
        """Connect to a JSON-RPC server at *address*."""
        sock = util.create_connection(address, self._timeout)
        sock.settimeout(0)
        self._read_notifier = QSocketNotifier(sock.fileno(), QSocketNotifier.Read, self)
        self._read_notifier.activated.connect(self._do_read)
        self._read_notifier.setEnabled(True)
        self._write_notifier = QSocketNotifier(sock.fileno(), QSocketNotifier.Write, self)
        self._write_notifier.activated.connect(self._do_write)
        self._write_notifier.setEnabled(False)
        self._socket = sock

    def _do_read(self):
        # Read messages from the socket and put them into the incoming queue
        # until nothing more can be read.
        while True:
            try:
                buf = self._socket.recv(4096)
            except socket.error as e:
                if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                    break
                self._log.error('recv() error {0}'.format(e.errno))
                self.close()
                break
            if buf == b'':
                self._log.error('peer closed connection')
                self.close()
                break
            nbytes = self._parser.feed(buf)
            if nbytes != len(buf):
                self._log.error('parse error {0}'.format(self._parser.error))
                self.close()
                break
            while True:
                message = self._parser.pop_message()
                if not message:
                    break
                self._incoming.append(message)
        # Schedule a dispatch if there are incoming messages
        if self._incoming:
            QCoreApplication.instance().postEvent(self, _Dispatch())

    def _do_write(self):
        # Drain message from the outgoing queue until we would block or until
        # the queue is empty.
        while True:
            if not self._outbuf:
                if not self._outgoing:
                    break
                message = self._outgoing.popleft()
                self._outbuf = json.dumps(message).encode('utf8')
            try:
                nbytes = self._socket.send(self._outbuf)
            except socket.error as e:
                if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                    break
                self.logger.error('send() error {0}'.format(e.errno))
                self.close()
                break
            self._outbuf = self._outbuf[nbytes:]
        if not self._outbuf:
            self._write_notifier.setEnabled(False)

    def close(self):
        """Close the connection."""
        if self._socket is None:
            return
        self._read_notifier.setEnabled(False)
        self._write_notifier.setEnabled(False)
        try:
            self._socket.close()
        except socket.error:
            pass
        self._log.debug('connection closed')
        self._socket = None

    def send_message(self, message):
        """Send a raw JSON-RPC message."""
        if self._socket is None:
            raise RuntimeError('not connected')
        if not jsonrpc.check_message(message):
            raise ValueError('invalid JSON-RPC message')
        self._outgoing.append(message)
        if not self._write_notifier.isEnabled():
            self._write_notifier.setEnabled(True)

    def send_notification(self, method, *args):
        """Send a JSON-RPC notification."""
        message = jsonrpc.create_notification(method, args)
        self.send_message(message)

    def event(self, event):
        # Process the DispatchMessages event
        if isinstance(event, _Dispatch):
            self._dispatch()
            event.accept()
            return True
        else:
            event.ignore()
            return False

    def _dispatch(self):
        # Dispatch message from the connection.
        while self._incoming:
            message = self._incoming.popleft()
            if 'result' in message or 'error' in message:
                # response
                key = message['id']
                callback = self._method_calls.get(key, None)
                if callback:
                    callback(message, self)
            elif self._message_handler:
                self._message_handler(message, self)
            else:
                self._log.info('no handler, cannot handle incoming message')

    def call_method(self, method, *args, **kwargs):
        """Call a method."""
        if self._method_calls:
            raise RuntimeError('recursive call_method() detected')
        message = jsonrpc.create_request(method, args)
        self.send_message(message)
        replies = []
        def method_response(message, client):
            replies.append(message)
        def method_timeout():
            reply = jsonrpc.create_error(message, jsonrpc.errno.SERVER_ERROR,
                                        'Method call timed out')
            replies.append(reply)
        timeout = kwargs.pop('timeout', self.timeout)
        if timeout:
            timer = QTimer(self)
            timer.setInterval(timeout*1000)
            timer.setSingleShot(True)
            timer.timeout.connect(method_timeout)
            timer.start()
        # Run an embedded event loop to process network events until we get a
        # response. We allow only one concurrent call so that we don't run the
        # risk of overflowing the stack.
        self._method_calls[message['id']] = method_response
        loop = QEventLoop()
        mask = QEventLoop.ExcludeUserInputEvents | QEventLoop.WaitForMoreEvents
        while True:
            loop.processEvents(mask)
            if replies:
                break
        if timeout:
            timer.stop()
        reply = replies[0]
        del self._method_calls[message['id']]
        if reply.get('error'):
            raise QJsonRpcError(reply['error'])
        self.message = reply
        return reply.get('result')


def request(name=None):
    """Return a decorator that marks a function as a request handler."""
    def decorate(handler):
        handler.request = True
        handler.name = name or handler.__name__
        return handler
    return decorate

def notification(name=None):
    """Return a decorator that marks a function as a notification handler."""
    def decorate(handler):
        handler.notification = True
        handler.name = name or handler.__name__
        return handler
    return decorate


class QJsonRpcHandler(object):
    """An object based message handler.

    Methods on instances can be decorated with :func:`request` or
    :func:`notification` to mark them as request and notificaiton handlers
    respectively.
    """

    def __init__(self):
        self._request_handlers = []
        self._notification_handlers = []
        self._init_handlers()

    def _init_handlers(self):
        for sym in dir(self):
            handler = getattr(self, sym)
            if getattr(handler, 'request', False):
                self._request_handlers.append(handler)
            elif getattr(handler, 'notification', False):
                self._notification_handlers.append(handler)

    def __call__(self, message, client):
        method = message.get('method')
        if not method:
            return
        is_request = (message.get('id') is not None)
        if is_request:
            handlers = self._request_handlers
        else:
            handlers = self._notification_handlers
        handlers_found = 0
        for handler in handlers:
            if not fnmatch.fnmatch(method, handler.name):
                continue
            handlers_found += 1
            args = message.get('params', ())
            self.message = message
            self.client = client
            self.send_response = True
            result = exc = None
            try:
                result = handler(*args)
            except Exception as e:
                client._log.exception('uncaught exception in handler')
                exc = e
            self.message = None
            self.client = None
            if not is_request:
                continue
            if exc:
                response = jsonrpc.create_error(message, jsonrpc.errno.INTERNAL_ERROR)
            elif self.send_response:
                response = jsonrpc.create_response(message, result)
            else:
                response = None
            if response:
                client.send_message(response)
            break
        if is_request and handlers_found == 0:
            error = jsonrpc.create_error(message, jsonrpc.errno.METHOD_NOT_FOUND)
            client.send_message(error)

########NEW FILE########
__FILENAME__ = socketapi
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

from PyQt4.QtCore import Signal
from PyQt4.QtGui import QApplication

from . import qjsonrpc
from .qjsonrpc import *

__all__ = ['QtSocketApiError', 'QtSocketApiClient']


QtSocketApiError = QJsonRpcError


class QtSocketApiHandler(QJsonRpcHandler):
    """JSON-RPC message handler used by :class:`QtSocketApiClient`."""

    def __init__(self, notification_handler):
        super(QtSocketApiHandler, self).__init__()
        self._notification_handler = notification_handler

    @notification('*')
    def catch_all_notifications(self, *ignored):
        self._notification_handler(self.message)

    @request()
    def get_pairing_approval(self, name, vault, pin, kxid):
        message = self.message
        client = self.client
        mainwindow = QApplication.instance().mainWindow()
        def send_response(approved):
            reply = qjsonrpc.create_response(message, approved)
            client.send_message(reply)
        self.send_response = False
        mainwindow.showPairingApprovalDialog(name, vault, pin, kxid, send_response)


class QtSocketApiClient(QJsonRpcClient):
    """Qt frontend client for the Bluepass socket API."""

    def __init__(self, parent=None):
        handler = QtSocketApiHandler(self._notification_handler)
        super(QtSocketApiClient, self).__init__(handler, parent=parent)

    def _notification_handler(self, message):
        """Forward notifications to corresponding Qt signals."""
        assert message.get('id') is None
        method = message.get('method')
        assert method is not None
        signal = getattr(self, method, None)
        if signal and hasattr(signal, 'emit'):
            signal.emit(*message.get('params', ()))

    VaultAdded = Signal(dict)
    VaultRemoved = Signal(dict)
    VaultCreationComplete = Signal(str, str, dict)
    VaultLocked = Signal(dict)
    VaultUnlocked = Signal(dict)
    VersionsAdded = Signal(str, list)
    NeighborDiscovered = Signal(dict)
    NeighborUpdated = Signal(dict)
    NeighborDisappeared = Signal(dict)
    AllowPairingStarted = Signal(int)
    AllowPairingEnded = Signal()
    PairNeighborStep1Completed = Signal(str, str, dict)
    PairNeighborStep2Completed = Signal(str, str, dict)
    PairingComplete = Signal(str)

    def get_version_info(self):
        return self.call_method('get_version_info')

    def get_config(self):
        return self.call_method('get_config')

    def update_config(self, config):
        return self.call_method('update_config', config)

    def create_vault(self, name, password, async=False):
        return self.call_method('create_vault', name, password, async)

    def get_vault(self, uuid):
        return self.call_method('get_vault', uuid)

    def get_vaults(self):
        return self.call_method('get_vaults')

    def update_vault(self, vault):
        return self.call_method('update_vault', vault)

    def delete_vault(self, vault):
        return self.call_method('delete_vault', vault)

    def get_vault_statistics(self, uuid):
        return self.call_method('get_vault_statistics', uuid)

    def unlock_vault(self, uuid, password):
        return self.call_method('unlock_vault', uuid, password)

    def lock_vault(self, uuid):
        return self.call_method('lock_vault', uuid)

    def vault_is_locked(self, uuid):
        return self.call_method('vault_is_locked', uuid)

    def get_version(self, vault, uuid):
        return self.call_method('get_version', vault, uuid)

    def get_versions(self, vault):
        return self.call_method('get_versions', vault)

    def add_version(self, vault, version):
        return self.call_method('add_version', vault, version)

    def update_version(self, vault, version):
        return self.call_method('update_version', vault, version)

    def delete_version(self, vault, version):
        return self.call_method('delete_version', vault, version)
    
    def get_version_history(self, vault, uuid):
        return self.call_method('get_version_history', vault, uuid)

    def generate_password(self, method, *args):
        return self.call_method('generate_password', method, *args)

    def password_strength(self, method, *args):
        return self.call_method('password_strength', method, *args)

    def get_neighbors(self):
        return self.call_method('get_neighbors')

    def locator_is_available(self):
        return self.call_method('locator_is_available')

    def set_allow_pairing(self, timeout):
        return self.call_method('set_allow_pairing', timeout)

    def pair_neighbor_step1(self, node, source):
        return self.call_method('pair_neighbor_step1', node, source)

    def pair_neighbor_step2(self, cookie, pin, name, password):
        return self.call_method('pair_neighbor_step2', cookie, pin, name, password)

########NEW FILE########
__FILENAME__ = util
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import bisect
import os.path


## The "blist" package provides a list with better asymptotic insert()
## and remove() behavior for operations not at the end of the list.
#try:
#    from blist import blist as list
#except ImportError:
#    pass


class SortedList(object):
    """A SortedList is collection of keys/value pairs, where the keys have an
    ordering and where the pairs are stored in the list in that ordering.

    Keys do not need to be unique.
    """

    def __init__(self):
        self._keys = list()
        self._values = list()
        self._data = list()

    def find(self, key, value=None):
        """Find the pair with `key` and optionally `value` and return its
        index, or -1 if the pair was not found."""
        pos = bisect.bisect_left(self._keys, key)
        if value is not None:
            while pos < len(self._keys) and self._keys[pos] == key and \
                        self._values[pos] != value:
                pos += 1
            if pos == len(self._keys):
                return -1
        if pos == len(self._keys) or self._keys[pos] != key:
            return -1
        return pos

    def insert(self, key, value=None, data=None):
        """Insert the key/value pair. Return the position where the pair was
        inserted."""
        pos = bisect.bisect_right(self._keys, key)
        self._keys.insert(pos, key)
        self._values.insert(pos, value)
        self._data.insert(pos, data)
        return pos

    def remove(self, key, value=None):
        """Remove a key/value pair. Return the position where the pair was
        deleted, or -1 if the pair was not found."""
        pos = bisect.bisect_left(self._keys, key)
        if value is not None:
            while pos < len(self._keys) and self._keys[pos] == key and \
                        self._values[pos] != value:
                pos += 1
            if pos == len(self._keys):
                return -1
        if self._keys[pos] != key:
            return -1
        del self._keys[pos]
        del self._values[pos]
        del self._data[pos]

    def removeat(self, pos):
        """Remove the entry at `pos`."""
        del self._keys[pos]
        del self._values[pos]
        del self._data[pos]

    def keyat(self, pos):
        """Return the key at position `pos`."""
        return self._keys[pos]

    def valueat(self, pos):
        """Return the value at position `pos`."""
        return self._values[pos]

    def dataat(self, pos):
        """Return the extra data element at position `pos`."""
        return self._data[pos]

    def __len__(self):
        return len(self._keys)

    def __iter__(self):
        return iter(self._keys)

    iterkeys = __iter__

    def itervalues(self):
        return iter(self._values)

    def iterdata(self):
        return iter(self._data)

########NEW FILE########
__FILENAME__ = vaultmanager
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import time
import logging

from PyQt4.QtCore import Slot, Qt, QTimer, QPoint, QSize, QTimer, QEventLoop
from PyQt4.QtGui import (QWidget, QDialog, QPushButton, QHBoxLayout,
        QVBoxLayout, QStackedWidget, QTableWidget, QTableWidgetItem,
        QFrame, QHeaderView, QApplication, QGridLayout, QLineEdit,
        QLabel, QCheckBox, QMessageBox, QComboBox, QMenu, QFont,
        QFontMetrics)

Item = QTableWidgetItem

from .passwordbutton import (GeneratePasswordButton,
        DicewarePasswordConfiguration)


class Overlay(QFrame):

    stylesheet = """
        Overlay { background-color: palette(window); border: 1px solid grey; }
    """

    def __init__(self, parent=None):
        super(Overlay, self).__init__(parent)
        self.setStyleSheet(self.stylesheet)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        self.setLayout(layout)
        message = QLabel(self)
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignTop)
        layout.addWidget(message)
        self.message = message
        self.setStyleSheet(self.stylesheet)
        self.setWindowFlags(Qt.SplashScreen|Qt.WindowStaysOnTopHint)

    def setMessage(self, message):
        self.message.setText(message)

    def show(self):
        super(Overlay, self).show()
        self.raise_()

    def showEvent(self, event):
        parent = self.parent()
        pos = QPoint((parent.width() - self.width()) / 2,
                     (parent.height() - self.height()) / 3)
        pos = parent.mapToGlobal(pos)
        self.move(pos)
        size = self.sizeHint()
        self.resize(size.width(), max(80, size.height()))


class Page(QFrame):
    """A page in the VaultManager dialog."""

    name = 'Page'
    title = 'Description'

    def __init__(self, vaultmgr):
        super(Page, self).__init__()
        self.vaultmgr = vaultmgr
        self.defaultbtn = None
        self.oncomplete = 'hide'
        self.addPopup()

    def addPopup(self):
        popup = Overlay(self)
        popup.setFixedWidth(300)
        popup.hide()
        self.popup = popup
        autohide_timer = QTimer(self)
        autohide_timer.timeout.connect(self.hidePopup)
        self.autohide_timer = autohide_timer
        progress_timer = QTimer(self)
        progress_timer.timeout.connect(self.showProgress)
        self.progress_timer = progress_timer
        self.popup_minimum_show = 0

    def reset(self):
        """Reset the page."""
        self.hidePopup()

    def setDefaultButton(self, button):
        """Set `button` as the default button for this page."""
        self.defaultbtn = button

    def showEvent(self, event):
        # There can only be done default button in a dialog. Because we
        # multplex multiple pages with each a default button in in the
        # same dialog via a QStackedWidget, we set the right default button
        # just before the widget is shown. That will clear the other default
        # buttons and make the per-page default button the real default.
        if self.defaultbtn:
            self.defaultbtn.setDefault(True)

    def setOnCompleteAction(self, action):
        """Set what needs to happen when the vault is created.
        Possible values are "hide" and "back". """
        self.oncomplete = action

    def done(self):
        """This page is done. Execute the OnComplete action."""
        self.hidePopup()
        vaultmgr = QApplication.instance().mainWindow().vaultManager()
        if self.oncomplete == 'back':
            vaultmgr.back()
        else:
            vaultmgr.hide()

    def showPopup(self, message, minimum_show=None, autohide=None,
                  progress=None, nomove=False):
        self.message = message
        self.popup.setMessage(message)
        self.popup.show()
        if minimum_show:
            self.popup_minimum_show = time.time() + minimum_show / 1000.0
        if autohide:
            self.autohide_timer.start(autohide)
        else:
            self.autohide_timer.stop()
        if progress:
            self.progress_timer.start(progress)
        else:
            self.progress_timer.stop()

    def showProgress(self):
        self.message += '.'
        self.popup.setMessage(self.message)

    def waitPopup(self):
        if not self.popup_minimum_show:
            return
        qapp = QApplication.instance()
        while True:
            if time.time() > self.popup_minimum_show:
                break
            qapp.processEvents(QEventLoop.WaitForMoreEvents)
        self.autohide_timer.stop()
        self.progress_timer.stop()

    def hidePopup(self):
        self.waitPopup()
        self.popup.hide()

    def updatePopupPosition(self):
        if self.popup.isVisible():
            self.popup.showEvent(None)


class ManageVaults(Page):

    name = 'ManageVaults'
    title = 'Manage Vaults'

    def __init__(self, vaultmgr):
        super(ManageVaults, self).__init__(vaultmgr)
        self.addWidgets()
        self.loadVaults()

    def addWidgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        preamble = QLabel(self)
        layout.addWidget(preamble)
        self.preamble = preamble
        layout.addSpacing(10)
        table = QTableWidget(self)
        layout.addWidget(table)
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setMinimumWidth(400)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setColumnCount(4)
        table.hideColumn(0)
        table.setHorizontalHeaderLabels(['ID', 'Vault', '# of Items', '# of Peers'])
        table.setFocusPolicy(Qt.NoFocus)
        table.itemSelectionChanged.connect(self.rowSelected)
        hhead = table.horizontalHeader()
        hhead.setResizeMode(QHeaderView.Stretch)
        hhead.setHighlightSections(False)
        vhead = table.verticalHeader()
        vhead.hide()
        self.table = table
        hbox = QHBoxLayout()
        layout.addLayout(hbox)
        button = QPushButton('Create Vault', self)
        button.clicked.connect(self.createVault)
        hbox.addWidget(button)
        button = QPushButton('Connect to Vault', self)
        backend = QApplication.instance().backend()
        available = backend.locator_is_available()
        if available:
            button.clicked.connect(self.connectVault)
        else:
            button.setEnabled(False)
        hbox.addWidget(button)
        removebtn = QPushButton('Remove Vault', self)
        removebtn.setEnabled(False)
        removebtn.clicked.connect(self.removeVault)
        self.removebtn = removebtn
        hbox.addWidget(removebtn)

    def loadVaults(self):
        backend = QApplication.instance().backend()
        vaults = backend.get_vaults()
        for vault in vaults:
            self.vaultAdded(vault)
        backend.VaultAdded.connect(self.vaultAdded)
        backend.VaultRemoved.connect(self.vaultRemoved)

    def reset(self):
        preamble = 'The following vaults are present:'
        self.preamble.setText(preamble)
        self.table.clearSelection()

    @Slot()
    def rowSelected(self):
        items = self.table.selectedItems()
        self.removebtn.setEnabled(len(items) > 0)

    @Slot(dict)
    def vaultAdded(self, vault):
        table = self.table
        row = table.rowCount(); table.setRowCount(row+1)
        table.setItem(row, 0, Item(vault['id']))
        table.setItem(row, 1, Item(vault['name']))
        backend = QApplication.instance().backend()
        stats = backend.get_vault_statistics(vault['id'])
        table.setItem(row, 2, Item(str(stats['current_versions'])))
        table.setItem(row, 3, Item(str(stats['trusted_nodes'])))
        table.sortItems(1)

    @Slot(dict)
    def vaultRemoved(self, vault):
        rows = self.table.rowCount()
        for row in range(rows):
            uuid = self.table.item(row, 0).text()
            if vault['id'] == uuid:
                self.table.removeRow(row)
                break

    @Slot()
    def createVault(self):
        vaultmgr = QApplication.instance().mainWindow().vaultManager()
        page = vaultmgr.page('NewVault')
        page.reset()
        vaultmgr.showPage(page)

    @Slot()
    def connectVault(self):
        vaultmgr = QApplication.instance().mainWindow().vaultManager()
        page = vaultmgr.page('ShowNeighbors')
        page.reset()
        vaultmgr.showPage(page)

    @Slot()
    def removeVault(self):
        row = self.table.selectedIndexes()[0].row()
        uuid = self.table.item(row, 0).text()
        text = 'Removing a vault removes all its entries.   \n' \
               'This operation cannot be undone.\n' \
               'Are you sure you want to continue?'
        result = QMessageBox.warning(self, 'Remove Vault', text,
                        QMessageBox.Ok|QMessageBox.Cancel,
                        QMessageBox.Cancel)
        if result != QMessageBox.Ok:
            return
        backend = QApplication.instance().backend()
        vault = backend.get_vault(uuid)
        backend.delete_vault(vault)


class PinEditor(QLineEdit):
    """A QLineEdit with an input mask to edit a PIN code in the
    format of 123-456.

    This could use setInputMask() but i don't like how that works
    (it works in "replace" mode and not "insert" mode).
    """

    def __init__(self, parent=None):
        super(PinEditor, self).__init__(parent)
        self.textChanged.connect(self.hyphenate)
        self.cursorPositionChanged.connect(self.updateCursor)
        self.prevtext = ''
        self.prevpos = 0
        self.nested = False

    def updateCursor(self, old, new):
        if self.nested:
            return
        self.prevpos = new

    def setTextNoSignal(self, text):
        self.nested = True
        self.setText(text)
        self.nested = False

    def hyphenate(self, text):
        if self.nested:
            return
        digits = text.replace('-', '')
        if digits and not digits.isdigit() or len(digits) > 6:
            self.setTextNoSignal(self.prevtext)
            self.setCursorPosition(self.prevpos)
            return
        pos = self.cursorPosition()
        prevpos = self.prevpos
        if len(digits) > 3:
            text = '%s-%s' % (digits[:3], digits[3:])
        else:
            text = digits
        if len(digits) == 3:
            # fully stuff with a hyphen at the end
            if pos == 3 and prevpos == 2:
                text += '-'
                pos += 1
            elif pos == 4 and prevpos >= 4:
                pos -= 1
        elif prevpos == 3 and pos == 4:
            # character inserted before '-', move over it
            pos += 1
        self.setTextNoSignal(text)
        self.setCursorPosition(pos)
        self.prevtext = text
        self.prevpos = pos

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        width = fm.width('999-999') + 10
        height = fm.height() + 8
        return QSize(width, height)


class CreateVault(Page):
    """Create vault page.

    This is a multifunctional page that supports 3 related modes:

     - NewVault: create a new vault
     - NewVaultSimplified: create a new vault, simplified
     - ConnectVault: connect to an existing vault.

    """

    title = 'Create New Vault'
    stylesheet = """
        PinEditor { font-size: 22pt; font-family: monospace; }
    """

    def __init__(self, vaultmgr, name):
        super(CreateVault, self).__init__(vaultmgr)
        self.name = name
        self.method = 0
        self.uuid = None
        self.cookie = None
        self.logger = logging.getLogger(__name__)
        self.addWidgets()
        self.setStyleSheet(self.stylesheet)
        backend = QApplication.instance().backend()
        backend.VaultCreationComplete.connect(self.vaultCreationComplete)
        backend.PairNeighborStep2Completed.connect(self.pairNeighborStep2Completed)

    def addWidgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        preamble = QLabel()
        preamble.setWordWrap(True)
        layout.addSpacing(10)
        layout.addWidget(preamble)
        layout.addSpacing(10)
        self.preamble = preamble
        grid = QGridLayout()
        layout.addLayout(grid)
        grid.setColumnMinimumWidth(1, 20)
        grid.setColumnStretch(2, 100)
        pinlbl = QLabel('PIN', self)
        grid.addWidget(pinlbl, 0, 0)
        self.pinlbl = pinlbl
        pinedt = PinEditor(self)
        pinedt.textChanged.connect(self.fieldUpdated)
        grid.addWidget(pinedt, 0, 2)
        self.pinedt = pinedt
        namelbl = QLabel('Name', self)
        grid.addWidget(namelbl, 1, 0)
        self.namelbl = namelbl
        nameedt = QLineEdit(self)
        nameedt.textChanged.connect(self.fieldUpdated)
        grid.addWidget(nameedt, 1, 2)
        self.nameedt = nameedt
        label = QLabel('Protect with', self)
        grid.addWidget(label, 2, 0)
        methodbox = QComboBox(self)
        methodbox.addItem('Generate a secure passphrase')
        methodbox.addItem('I will enter my own passphrase')
        methodbox.addItem('Do not use a passphrase')
        grid.addWidget(methodbox, 2, 2)
        methodbox.activated.connect(self.methodUpdated)
        config = DicewarePasswordConfiguration()
        passwdbtn = GeneratePasswordButton('Generate', config, self)
        passwdbtn.setFocusPolicy(Qt.ClickFocus)
        grid.addWidget(passwdbtn, 2, 3)
        self.passwdbtn = passwdbtn
        label = QLabel('Passphrase', self)
        grid.addWidget(label, 3, 0)
        passwdedt = QLineEdit(self)
        passwdbtn.passwordGenerated.connect(passwdedt.setText)
        passwdedt.textChanged.connect(self.fieldUpdated)
        grid.addWidget(passwdedt, 3, 2, 1, 2)
        self.passwdedt = passwdedt
        repeatlbl = QLabel('Repeat', self)
        grid.addWidget(repeatlbl, 4, 0)
        self.repeatlbl = repeatlbl
        repeatedt = QLineEdit(self)
        repeatedt.setEchoMode(QLineEdit.Password)
        repeatedt.textChanged.connect(self.fieldUpdated)
        grid.addWidget(repeatedt, 4, 2, 1, 2)
        self.repeatedt = repeatedt
        unlockcb = QCheckBox('Automatically unlock when you log in', self)
        grid.addWidget(unlockcb, 5, 2, 1, 2)
        self.unlockcb = unlockcb
        status = QLabel(self)
        layout.addSpacing(10)
        layout.addWidget(status)
        self.status = status
        layout.addStretch(100)
        hbox = QHBoxLayout()
        layout.addLayout(hbox)
        cancelbtn = QPushButton('Cancel', self)
        cancelbtn.clicked.connect(self.vaultmgr.hide)
        hbox.addWidget(cancelbtn)
        self.cancelbtn = cancelbtn
        createbtn = QPushButton('Create', self)
        self.setDefaultButton(createbtn)
        createbtn.setEnabled(False)
        createbtn.clicked.connect(self.createVault)
        hbox.addWidget(createbtn)
        hbox.addStretch(100)
        self.createbtn = createbtn

    def configureMode(self, mode):
        """Configure the mode."""
        if mode == 'NewVault':
            self.title = 'Create a New Vault'
            preamble = '<p>Please enter the vault details below.</p>'
            self.pinlbl.hide()
            self.pinedt.hide()
            self.preamble.setText(preamble)
            self.nameedt.setFocus()
            self.passwdbtn.generate()
            self.setOnCompleteAction('back')
            self.cancelbtn.hide()
        elif mode == 'NewVaultSimplified':
            self.title = 'Create a New Vault'
            preamble = '<p>You are strongly recommended to protect your ' \
                       'vault with a passphrase.</p>' \
                       '<p><span style="font-weight: bold">NOTE:</span> ' \
                       'There is no way to recover a lost passphrase. ' \
                       'You may want to write down your passphrase now, ' \
                       'but you should discard of the note in a secure way ' \
                       'as soon as you have memorized it.</p>'
            self.preamble.setText(preamble)
            self.pinlbl.hide()
            self.pinedt.hide()
            self.namelbl.hide()
            self.nameedt.hide()
            self.unlockcb.hide()
            self.passwdbtn.generate()
            self.createbtn.setFocus()
            self.setOnCompleteAction('hide')
            self.cancelbtn.show()
        elif mode == 'ConnectVault':
            self.title = 'Connect to Vault'
            preamble = '<p>Please enter the PIN code that is currently ' \
                       'displayed by Bluepass on the device that you are ' \
                       'connecting to.</p>'
            self.preamble.setText(preamble)
            self.createbtn.setText('Connect')
            self.pinedt.setFocus()
            self.passwdbtn.generate()
            self.setOnCompleteAction('back')
            self.cancelbtn.hide()

    def setName(self, name):
        """Set the value for the value name."""
        self.nameedt.setText(name)

    def reset(self):
        """Reset the dialog."""
        super(CreateVault, self).reset()
        self.uuid = None
        self.cookie = None
        self.status.setText('')
        self.nameedt.setText('')
        self.pinedt.setText('')
        self.passwdedt.setText('')
        self.repeatedt.setText('')
        self.methodUpdated(0)
        self.configureMode(self.name)

    @Slot(int)
    def methodUpdated(self, method):
        """Called when the method combo box has canged value."""
        if method == 0:
            self.passwdedt.setEnabled(True)
            self.passwdedt.setEchoMode(QLineEdit.Normal)
            self.repeatlbl.hide()
            self.repeatedt.hide()
            self.passwdbtn.setEnabled(True)
            self.passwdbtn.generate()
        elif method == 1:
            self.passwdedt.setEnabled(True)
            self.passwdedt.setEchoMode(QLineEdit.Password)
            self.passwdedt.clear()
            self.passwdedt.setFocus()
            self.repeatlbl.show()
            self.repeatedt.clear()
            self.repeatedt.show()
            self.passwdbtn.setEnabled(False)
        elif method == 2:
            self.passwdedt.clear()
            self.passwdedt.setEnabled(False)
            self.passwdbtn.setEnabled(False)
            self.repeatlbl.hide()
            self.repeatedt.hide()
        self.method = method
        self.fieldUpdated()

    @Slot()
    def fieldUpdated(self):
        """Called when one of the text editors has changed content."""
        pin = self.pinedt.text()
        name = self.nameedt.text()
        password = self.passwdedt.text()
        repeat = self.repeatedt.text()
        enabled = name != ''
        if self.name == 'ConnectVault':
            enabled = enabled and len(pin) == 7
        if self.method == 0:
            enabled = enabled and password != ''
        elif self.method == 1:
            if password and repeat and repeat != password:
                self.status.setText('<i>The passphrases do not match.</i>')
            else:
                self.status.setText('')
            enabled = enabled and password != '' and password == repeat
        self.createbtn.setEnabled(enabled)

    @Slot()
    def createVault(self):
        """Create the vault in the Backend."""
        backend = QApplication.instance().backend()
        pin = self.pinedt.text().replace('-', '')
        name = self.nameedt.text()
        password = self.passwdedt.text()
        self.createbtn.setEnabled(False)
        if self.name == 'ConnectVault':
            self.showPopup('<i>Creating connection with vault </i>',
                           minimum_show=2000, progress=100)
            backend.pair_neighbor_step2(self.cookie, pin, name, password)
        else:
            self.showPopup('<i>Creating vault. This may take a few seconds.</i>',
                           minimum_show=2000, progress=100)
            self.uuid = backend.create_vault(name, password, async=True)

    @Slot(str, str, dict)
    def vaultCreationComplete(self, uuid, status, detail):
        """Signal that arrives when the asynchronous vault creation
        has completed."""
        if uuid != self.uuid:
            return
        if status == 'OK':
            if self.name == 'NewVaultSimplified':
                mainwindow = QApplication.instance().mainWindow()
                mainwindow.showMessage('The vault was successfully created.')
                self.hidePopup()
                self.vaultmgr.hide()
            else:
                self.waitPopup()
                self.hidePopup()
                page = self.vaultmgr.page('ManageVaults')
                page.showPopup('The vault was succesfully created.', autohide=2000)
                self.vaultmgr.showPage(page)
        else:
            status = '<i>Could not create vault: %s</i>' % detail.get('error_message')
            self.status.setText(status)
            self.logger.error('%s\n%s' % (detail.get('message'), detail.get('data')))
        self.createbtn.setEnabled(True)
        self.uuid = None

    @Slot(str, str, dict)
    def pairNeighborStep2Completed(self, cookie, status, detail):
        if cookie != self.cookie:
            return
        if status == 'OK':
            self.done()
        else:
            self.showPopup('<i>Error: %s</i>' % detail['data'],
                           minimum_show=2000, autohide=2000)
        self.createbtn.setEnabled(True)
        self.cookie = None


class ShowNeighbors(Page):

    name = 'ShowNeighbors'
    title = 'Connect to Existing Vault'

    def __init__(self, vaultmgr, name):
        super(ShowNeighbors, self).__init__(vaultmgr)
        self.name = name
        self.addWidgets()
        self.loadNeighbors()
        self.cookie = None
        backend = QApplication.instance().backend()
        backend.PairNeighborStep1Completed.connect(self.pairNeighborStep1Completed)

    def addWidgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        preamble = QLabel(self)
        preamble.setWordWrap(True)
        layout.addWidget(preamble)
        self.preamble = preamble
        layout.addSpacing(10)
        table = QTableWidget(self)
        layout.addWidget(table)
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setMinimumWidth(400)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setColumnCount(4)
        table.hideColumn(0)
        table.setHorizontalHeaderLabels(['ID', 'Vault', 'Source', 'On Node'])
        table.setFocusPolicy(Qt.NoFocus)
        table.itemSelectionChanged.connect(self.rowSelected)
        hhead = table.horizontalHeader()
        hhead.setResizeMode(QHeaderView.Stretch)
        hhead.setHighlightSections(False)
        vhead = table.verticalHeader(); vhead.hide()
        self.table = table
        hbox = QHBoxLayout()
        layout.addLayout(hbox)
        cancelbtn = QPushButton('Cancel', self)
        cancelbtn.clicked.connect(self.vaultmgr.hide)
        hbox.addWidget(cancelbtn)
        self.cancelbtn = cancelbtn
        connectbtn = QPushButton('Connect', self)
        connectbtn.setEnabled(False)
        connectbtn.clicked.connect(self.connectVault)
        hbox.addWidget(connectbtn)
        self.connectbtn = connectbtn
        hbox.addStretch(100)

    def configureMode(self, mode):
        if mode == 'ShowNeighbors':
            preamble = '<p>The following vault are currently available on ' \
                       'the network.</p>'
            self.preamble.setText(preamble)
            self.cancelbtn.hide()
        elif mode == 'ShowNeighborsSimplified':
            preamble = '<p>The following vaults are currently available on ' \
                       'the network.</p>' \
                       '<p><span style="font-weight: bold">NOTE:</span> ' \
                       'You must select the menu option "Be visible for ' \
                       '60 seconds" on the remove device for it to show ' \
                       'up here.</p>'
            self.preamble.setText(preamble)
            self.cancelbtn.show()

    def reset(self):
        self.cookie = None
        self.configureMode(self.name)

    def loadNeighbors(self):
        self.vaults = {}
        self.neighbors = {}
        backend = QApplication.instance().backend()
        backend.VaultAdded.connect(self.vaultAdded)
        backend.VaultRemoved.connect(self.vaultRemoved)
        vaults = backend.get_vaults()
        for vault in vaults:
            self.vaultAdded(vault)
        backend.NeighborDiscovered.connect(self.neighborUpdated)
        backend.NeighborUpdated.connect(self.neighborUpdated)
        backend.NeighborDisappeared.connect(self.neighborRemoved)
        neighbors = backend.get_neighbors()
        for neighbor in neighbors:
            self.neighborUpdated(neighbor)

    @Slot(dict)
    def vaultAdded(self, vault):
        assert vault['id'] not in self.vaults
        self.vaults[vault['id']] = vault
        for node in self.neighbors:
            neighbor = self.neighbors[node]
            # The added vault should hide any neighbor offering that vault
            if neighbor['vault'] == vault['id']:
                self.removeNeighbor(neighbor)

    @Slot(dict)
    def vaultRemoved(self, vault):
        assert vault['id'] in self.vaults
        del self.vaults[vault['id']]
        for node in self.neighbors:
            neighbor = self.neighbors[node]
            # The removed vault should show any neighbor offering that vault,
            # if that neighbor would have been visible without the vault.
            if neighbor['vault'] == vault['id'] \
                    and len(neighbor['addresses']) > 0 \
                    and neighbor['properties'].get('visible') == 'true':
                self.updateNeighbor(neighbor)

    @Slot(dict)
    def neighborUpdated(self, neighbor):
        self.neighbors[neighbor['node']] = neighbor
        if len(neighbor['addresses']) > 0 \
                and neighbor['properties'].get('visible') == 'true' \
                and neighbor['vault'] not in self.vaults:
            self.updateNeighbor(neighbor)
        else:
            self.removeNeighbor(neighbor)

    @Slot(dict)
    def neighborRemoved(self, neighbor):
        assert neighbor['node'] in self.neighbors
        del self.neighbors[neighbor['node']]
        self.removeNeighbor(neighbor)

    def updateNeighbor(self, neighbor):
        table = self.table
        for row in range(table.rowCount()):
            node = table.item(row, 0).text()
            source = table.item(row, 2).text()
            if neighbor['node'] == node and neighbor['source'] == source:
                table.setItem(row, 1, Item(neighbor['vaultname']))
                table.setItem(row, 3, Item(neighbor['nodename']))
                break
        else:
            row = table.rowCount()
            table.setRowCount(row+1)
            table.setItem(row, 0, Item(neighbor['node']))
            table.setItem(row, 1, Item(neighbor['vaultname']))
            table.setItem(row, 2, Item(neighbor['source']))
            table.setItem(row, 3, Item(neighbor['nodename']))
            table.sortItems(1)

    def removeNeighbor(self, neighbor):
        table = self.table
        for row in range(table.rowCount()):
            node = table.item(row, 0).text()
            source = table.item(row, 2).text()
            if neighbor['node'] == node and neighbor['source'] == source:
                table.removeRow(row)
                break

    @Slot()
    def rowSelected(self):
        items = self.table.selectedItems()
        self.connectbtn.setEnabled(len(items) > 0)

    @Slot()
    def connectVault(self):
        backend = QApplication.instance().backend()
        self.showPopup('<i>Requesting approval to connnect</i><br>',
                       progress=500)
        self.connectbtn.setEnabled(False)
        items = self.table.selectedIndexes()
        row = items[0].row()
        node = self.table.item(row, 0).text()
        vault = self.table.item(row, 1).text()
        source = self.table.item(row, 2).text()
        self.cookie = backend.pair_neighbor_step1(node, source)
        self.vault = vault

    @Slot(str, str, dict)
    def pairNeighborStep1Completed(self, cookie, status, detail):
        if cookie != self.cookie:
            return
        if status == 'OK':
            self.hidePopup()
            vaultmgr = QApplication.instance().mainWindow().vaultManager()
            page = vaultmgr.page('ConnectVault')
            page.reset()
            page.setName(self.vault)
            page.cookie = cookie
            vaultmgr.showPage(page)
        else:
            self.showPopup('<i>Error: %s</i>' % detail['data'],
                           minimum_show=2000, autohide=2000)
            self.hidePopup()
        self.connectbtn.setEnabled(True)


class VaultManager(QDialog):
    """The Vault Manager.

    This is a modeless top-level dialog that is used to manage vaults.

    It is an active component that makes changes to the model directly.
    """

    stylesheet = """
        QFrame#header { min-height: 30px; max-height: 30px; }
        QFrame#header QPushButton { min-height: 20px; max-height: 20px; }
        QStackedWidget > QFrame { background-color: white; border: 1px solid grey; }
    """

    def __init__(self, parent=None):
        super(VaultManager, self).__init__(parent)
        self.addWidgets()
        self.setStyleSheet(self.stylesheet)
        flags = Qt.Window|Qt.CustomizeWindowHint|Qt.WindowCloseButtonHint
        self.setWindowFlags(flags)
        self.pages = {}
        self.backlinks = {}
        self.current_page = None
        self.addPage(ManageVaults(self))
        self.addPage(CreateVault(self, 'NewVault'), back='ManageVaults')
        self.addPage(ShowNeighbors(self, 'ShowNeighbors'), back='ManageVaults')
        self.addPage(ShowNeighbors(self, 'ShowNeighborsSimplified'))
        self.addPage(CreateVault(self, 'ConnectVault'), back='ShowNeighbors')
        self.addPage(CreateVault(self, 'NewVaultSimplified'))
        self.resize(500, 400)

    def addWidgets(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        self.setLayout(layout)
        header = QFrame(self)
        header.setObjectName('header')
        hbox = QHBoxLayout()
        hbox.addSpacing(10)
        hbox.setContentsMargins(0, 0, 0, 0)
        header.setLayout(hbox)
        backbutton = QPushButton('< Back', header)
        backbutton.clicked.connect(self.back)
        hbox.addWidget(backbutton)
        hbox.addStretch(100)
        self.backbutton = backbutton
        layout.addWidget(header)
        layout.addSpacing(5)
        self.header = header
        stack = QStackedWidget(self)
        layout.addWidget(stack)
        self.stack = stack

    def addPage(self, page, back=None):
        """Add a page."""
        index = self.stack.addWidget(page)
        self.pages[page.name] = (index, page)
        if back is not None:
            self.backlinks[page.name] = back

    def showPage(self, name):
        """Show a page."""
        if isinstance(name, Page):
            name = name.name
        if name not in self.pages:
            raise ValueError('Unknown page: %s' % name)
        index, page = self.pages[name]
        self.current_page = name
        self.stack.setCurrentIndex(index)
        self.setWindowTitle(page.title)
        self.backbutton.setVisible(name in self.backlinks)
        self.show()

    def currentPage(self):
        """Return the current page."""
        if self.current_page:
            return self.pages[self.current_page][1]

    def page(self, name):
        """Return a page."""
        if name in self.pages:
            return self.pages[name][1]

    def reset(self):
        for name in self.pages:
            self.pages[name][1].reset()
        self.showPage('ManageVaults')

    @Slot()
    def back(self):
        back = self.backlinks.get(self.current_page)
        if back is None:
            return
        self.showPage(back)

    def moveEvent(self, event):
        page = self.currentPage()
        if page:
            page.updatePopupPosition()

########NEW FILE########
__FILENAME__ = json
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

from json import *
import itertools
from gruvi import compat


def dumps_c14n(obj):
    """Serialize an object as canonicalized JSON."""
    return dumps(obj, sort_keys=True, indent=None, separators=(',',':'))

def dumps_pretty(obj):
    """Pretty-print a JSON message."""
    return dumps(obj, sort_keys=True, indent=2)


def try_loads(s, cls=None):
    """Load the JSON object in `s` or return None in case there is an error."""
    try:
        obj = loads(s)
    except Exception as e:
        print(repr(s))
        raise
        return
    if cls is not None and not isinstance(obj, cls):
        return
    return obj


class UnpackError(Exception):
    """Validation error."""


def unpack(obj, fmt, names=()):
    """Unpack an object `obj` according to the format string `fmt`.  The
    `names` argument specifies the keys of dictionary entries in the format
    string. The return value is a single, flat tuple with all the unpacked
    values. An UnpackError is raised in case the object cannot be unpacked
    with the provided format string."""
    unpacker = Unpacker(fmt)
    return unpacker.unpack(obj, names)


def check_unpack(obj, fmt, *names):
    """Like unpack() but returns True if the object could be unpacked, and
    False otherwise."""
    try:
        unpack(obj, fmt, *names)
    except UnpackError:
        return False
    return True


class Unpacker(object):
    """A parser and validator for our "unpack" string format.

    The EBNF representation of the grammar is:

      top : value
      value : object | array | type
      object : '{' ('s' ['?'] type)* ['!' | '*'] '}'
      array : '[' value* ['!' | '*'] ']'
      type : 'n' | 'b' | 'i' | 'u' | 's' | 'f' | 'o'

    The tokens ':' and ',' are removed from the input stream, so the more
    natural { s:s, s:s } format can be used instead of {ssss}. Boths forms
    are equivalent.

    The format is very similar to the format uses for Jansson's json_unpack()
    function. That format is documented here:

      http://www.digip.org/jansson/doc/2.3/apiref.html
    """

    def __init__(self, format):
        """Create a new unpacker for format string `format`."""
        self.format = format

    def _tokenize(self):
        """INTERNAL: Return a tokenizer for the format string."""
        for ch in self.format:
            if ch not in ' \t:,':
                yield  ch

    def _accept(self, tokens):
        """INTERNAL: return the next token if it is in `tokens`, or None."""
        if self.current is None or self.current not in tokens:
            return ''
        old = self.current
        self.current = next(self._tokeniter)
        return old

    def _expect(self, tokens):
        """INTERNAL: return the next token if it is in `tokens`, or raise an error."""
        if self.current is None or self.current not in tokens:
            raise ValueError('expecting token: %s (got: %s)' % (tokens, self.current))
        old = self.current
        self.current = next(self._tokeniter)
        return old

    def unpack(self, obj, names=()):
        """Unpack an object according to the format string provided in the
        constructor. The `names` argument specifies the names of dictionary
        entries. The return value is a single, flat tuple with all the
        unpackged values."""
        self._tokeniter = itertools.chain(self._tokenize(), (None,))
        self.current = next(self._tokeniter)
        self._nameiter = itertools.chain(names, (None,))
        self.values = []
        names = iter(names)
        self.p_value(obj)
        if self.current is not None:
            raise ValueError('extra input present')
        return tuple(self.values)

    def p_value(self, ctx):
        """value : object | array | type"""
        for production in self.p_object, self.p_array, self.p_type:
            try:
                production(ctx)
            except ValueError:
                pass
            else:
                return
        raise ValueError('expecting list, object or type')

    def p_object(self, ctx):
        """object : '{' ('s' ['?'] type)* ['!' | '*'] '}'"""
        self._expect('{')
        keys = set()
        while True:
            ch = self._accept('*!}')
            if ch:
                if ch == '!':
                    if ctx and set(ctx) > keys:
                        extra = ', '.join(set(ctx) - keys)
                        raise UnpackError('extra keys in input: %s' % extra)
                if ch != '}':
                    self._expect('}')
                break
            self._expect('s')
            opt = self._accept('?')
            name = next(self._nameiter)
            if name is None:
                raise UnpackError('not enough name arguments provided')
            keys.add(name)
            if ctx is None:
                self.p_value(None)
            elif name not in ctx and not opt:
                raise UnpackError('mandatory key not provided: %s' % name)
            else:
                self.p_value(ctx.get(name))

    def p_array(self, ctx):
        """array : '[' value* ['!' | '*'] ']'"""
        self._expect('[')
        i = 0
        while True:
            ch = self._accept('*!]')
            if ch:
                if ch == '!':
                    if ctx and i != len(ctx):
                        raise UnpackError('more items in input list than expected')
                if ch != ']':
                    self._expect(']')
                break
            if ctx is None:
                self.p_value(None)
            elif i >= len(ctx):
                raise UnpackError('mandatory list item not provided')
            else:
                self.p_value(ctx[i])
                i += 1

    def p_type(self, ctx):
        """type : 'n' | 'b' | 'i' | 'u' | 's' | 'f' | 'o'"""
        typ = self._expect('nbiusfo')
        if ctx is None:
            self.values.append(None)
            return
        if typ == 'n' and ctx is not None:
            raise UnpackError('expecting None')
        elif typ == 'b' and not isinstance(ctx, bool):
            raise UnpackError('expecting boolean')
        elif typ == 'i' and not isinstance(ctx, int):
            raise UnpackError('expecting integer')
        elif typ == 'u' and not (isinstance(ctx, int) and ctx >= 0):
            raise UnpackError('expecting unsigned integer')
        elif typ == 's' and not isinstance(ctx, compat.string_types):
            raise UnpackError('expecting string')
        elif typ == 'f' and not isinstance(ctx, float):
            raise UnpackError('expecting float')
        self.values.append(ctx)

########NEW FILE########
__FILENAME__ = keyring
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from bluepass.error import Error


class KeyringError(Error):
    """Keyring error."""


class Keyring(object):
    """Interface to an OS or Desktop Environment's keyring functionality."""

    def isavailable(self):
        """Return whether the keyring is available."""
        raise NotImplementedError

    def store(self, key, password):
        """Store a password."""
        raise NotImplementedError

    def retrieve(self, key):
        """Retrieve a password."""
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = locator
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from bluepass import logging
from bluepass.error import Error


class LocationError(Error):
    pass


class LocationSource(object):
    """A location source."""

    name = None

    def isavailable(self):
        raise NotImplementedError

    def register(self, node, nodename, vault, vaultname, address):
        raise NotImplementedError

    def set_property(self, node, name, value):
        raise NotImplementedError

    def unregister(self, node):
        raise NotImplementedError

    def add_callback(self, callback):
        raise NotImplementedError


class ZeroconfLocationSource(LocationSource):

    service = '_bluepass._tcp'
    domain = 'local'


class Locator(object):
    """Locator object.

    The locator keeps track of a list of current neighbors across multiple
    location sources.

    A neighbor is uniquely identified by the source identifier and its node ID.
    A node may have multiple addresses even within once location source. Each
    of these addresses are stored in the "addresses" property of a neighbor.

    The method get_neighbors() returns list of all currently known neighbors.
    Each neighbor is represented by a dictionary. An example is given below:

      {
          'source': 'LAN',
          'node': 'uuid',
          'nodename': 'Node Name',
          'vault': 'uuid',
          'vaultname': 'Vault Name',
          'addresses': [ { 'family': 2, 'addr': ['1.2.3.4', 100] } ],
          'properties': { 'visible': True }
      }

    The locator raises the events "NeighborDiscovered" "NeighborUpdated" and
    "NeighborDisappeared" to that users can be notified asynchronously of
    changes to the list of current neighbors.
    """

    def __init__(self):
        """Create a new locator object."""
        self.sources = []
        self.callbacks = []
        self.neighbors = {}
        self.addresses = {}
        self.vaults = set()
        self._log = logging.get_logger(self)

    def raise_event(self, event, *args):
        """Run all registered callbacks."""
        for callback in self.callbacks:
            callback(event, *args)

    def add_callback(self, callback):
        """Add a callback that gets notified when nodes come and go."""
        self.callbacks.append(callback)

    def _source_event(self, event, *args):
        """Callback for source events."""
        neighbor = args[0]
        node = neighbor['node']
        vault = neighbor['vault']
        source = neighbor['source']
        if event == 'NeighborDiscovered':
            if source not in self.neighbors:
                self.neighbors[source] = {}
            if node in self.neighbors[source]:
                self._log.error('NeighborDiscovered event for known neighbor')
                return
            self.neighbors[source][node] = neighbor
        elif event == 'NeighborUpdated':
            if source not in self.neighbors or node not in self.neighbors[source]:
                self._log.error('NeighborUpdated event for unknown neighbor')
                return
            self.neighbors[source][node] = neighbor
        elif event == 'NeighborDisappeared':
            if source not in self.neighbors or node not in self.neighbors[source]:
                self._log.error('NeighborDisappeared event for unknown neighbor')
                return
            del self.neighbors[source][node]
            if not self.neighbors[source]:
                del self.neighbors[source]
        self.raise_event(event, *args)

    def add_source(self, source):
        """Add a new location source."""
        self.sources.append(source)
        source.add_callback(self._source_event)

    def register(self, node, nodename, vault, vaultname, address,
                 properties=None):
        """Register a ourselves with all sources."""
        for source in self.sources:
            source.register(node, nodename, vault, vaultname, address,
                            properties)

    def set_property(self, node, name, value):
        """Set a property on a vault in each location source."""
        for source in self.sources:
            source.set_property(node, name, value)

    def unregister(self, node):
        """Unregister a vault with each location source."""
        for source in self.sources:
            source.unregister(node)

    def get_neighbor(self, node, source):
        """Resolve a single neighbor."""
        return self.neighbors.get(source, {}).get(node)

    def get_neighbors(self):
        """Return the list of neighbors."""
        neighbors = []
        for source in self.neighbors:
            neighbors += self.neighbors[source].values()
        return neighbors

########NEW FILE########
__FILENAME__ = logging
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import os
import sys
import logging

import gruvi.logging

__all__ = ['get_logger', 'setup_logging']

_default_name = 'bluepass'


def get_logger(context='', name=None):
    """Return a logger for *context*."""
    if name is None:
        name = _default_name
    return gruvi.logging.get_logger(context, name)


def set_default_logger(name):
    global _default_name
    _default_name = name


def setup_logging(options):
    """Configure logging destination."""
    logger = logging.getLogger()
    if sys.stdout.isatty() or options.log_stdout:
        handler = logging.StreamHandler(sys.stdout)
        logfmt = '%(name)s %(levelname)s %(message)s'
        handler.setFormatter(logging.Formatter(logfmt))
        logger.addHandler(handler)
    if not options.log_stdout:
        logfile = os.path.join(options.data_dir, 'bluepass.log')
        handler = logging.FileHandler(logfile, 'w')
        logfmt = '%(asctime)s %(name)s %(levelname)s %(message)s'
        handler.setFormatter(logging.Formatter(logfmt))
        logger.addHandler(handler)
    level = logging.DEBUG if options.debug else \
                logging.INFO if options.verbose else logging.WARNING
    logger.setLevel(level)

########NEW FILE########
__FILENAME__ = main
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import os
import sys
import time
import json
import errno
import socket
import argparse
import subprocess
import binascii

import bluepass
from bluepass import platform, util, logging
from bluepass.factory import singleton
from bluepass.backend import Backend

log = None


def create_parser():
    """Build the command-line parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Show debugging information.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Be verbose.')
    parser.add_argument('-V', '--version', action='store_true',
                        help='Show version information and exit.')
    parser.add_argument('-f', '--frontend', help='Select frontend to use.')
    parser.add_argument('-c', '--connect', metavar='ADDRSPEC',
                        help='Connect to existing backend (HOST:PORT or PATH)')
    parser.add_argument('--log-stdout', action='store_true',
                        help='Log to stdout even if not on a tty')
    parser.add_argument('--data-dir', metavar='DIRECTORY',
                        help='Specify data directory')
    parser.add_argument('--auth-token', metavar='TOKEN',
                        help='Backend authentication token')
    parser.add_argument('--daemon', action='store_true',
                        help='Do not kill backend on exit')
    parser.add_argument('--list-frontends', action='store_true',
                        help='List available frontends and exit.')
    parser.add_argument('--run-backend', action='store_true', help='Run the backend')
    parser.add_argument('--timeout', type=int, help='Backend timeout', default=2)
    return parser


def start_backend(options):
    args = [sys.executable, '-mbluepass.main', '--run-backend'] + sys.argv[1:]
    process = subprocess.Popen(args)
    log.debug('started backend with pid {}', process.pid)
    return process

def stop_backend(options, process, sock):
    # Try to stop our child. First nicely, then progressively less nice.
    start_time = time.time()
    elapsed = 0
    while elapsed < 3*options.timeout:
        if sock:
            log.debug('sending "stop" command to backend')
            request = { 'id': 'main.1', 'method': 'stop', 'jsonrpc': '2.0' }
            sock.send(json.dumps(request).encode('ascii'))
            sock.close()
            sock = None
        elif elapsed > options.timeout:
            log.debug('calling terminate() on backend')
            process.terminate()
        elif elapsed > 2*options.timeout:
            log.debug('calling kill() on backend')
            process.kill()
        if process.poll() is not None:
            break
        time.sleep(0.1)
        elapsed = time.time() - start_time
    exitstatus = process.returncode
    if exitstatus is None:
        log.error('could not stop backend after {} seconds', elapsed)
        return False
    elif exitstatus:
        log.error('backend exited with status {}', exitstatus)
    else:
        log.debug('backend exited after {} seconds', elapsed)
    return True

def connect_backend(options):
    runfile = os.path.join(options.data_dir, 'backend.run')
    sock = None
    start_time = time.time()
    elapsed = 0
    while elapsed < options.timeout:
        st = util.try_stat(runfile)
        if st is None:
            continue
        with open(runfile) as fin:
            buf = fin.read()
        runinfo = json.loads(buf)
        if not isinstance(runinfo, dict):
            break
        addr = util.paddr(runinfo['listen'])
        try:
            sock = util.create_connection(addr, timeout=0.2)
        except (OSError, IOError) as e:
            if e.errno and e.errno not in (errno.ENOENT, errno.ECONNREFUSED):
                raise
        else:
            break
        time.sleep(0.1)
        elapsed = time.time() - start_time
    log.debug('backed started up in {} seconds', elapsed)
    return sock, runinfo


def create_auth_token():
    """Return a new auth token."""
    return binascii.hexlify(os.urandom(32)).decode('ascii')


def main():
    """Main entry point."""

    # First get the --frontend parameter so that we can its command-line
    # options.

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-f', '--frontend', nargs='?')
    options, _ = parser.parse_known_args()

    for fe in platform.get_frontends():
        if fe.name == options.frontend or options.frontend is None:
            Frontend = fe
            break
    else:
        print('Error: no such frontend: {0}'.format(options.frontend), file=sys.stderr)
        print('Use --list-frontends to list available frontends', file=sys.stderr)
        return 1

    # Now build the real parser and parse arguments

    parser = create_parser()
    Frontend.add_options(parser)
    Backend.add_options(parser)
    options = parser.parse_args()

    # Early exits?

    if options.version:
        print('Bluepass version {0}'.format(bluepass.__version__))
        return 0

    if options.list_frontends:
        print('Available frontends:')
        for fe in platform.get_frontends():
            print('* {0:10}: {1}'.format(fe.name, fe.description))
        return 0

    # Check options and fill in defaults

    if options.data_dir is None:
        options.data_dir = platform.get_appdir('bluepass')
    if options.auth_token is None:
        options.auth_token = os.environ.get('BLUEPASS_AUTH_TOKEN')

    if not Frontend.check_options(options):
        return 1
    if not Backend.check_options(options):
        return 1

    if options.connect and options.run_backend:
        print('Error: specify either --connect or --run-backend but not both', file=sys.stderr)
        return 1

    # Unless we are spawning the backend and can create our own auth token,
    # we need the user to specify it.

    startbe = not (options.connect or options.run_backend)
    if options.auth_token is None:
        if not startbe:
            print('Error: --auth-token or $BLUEPASS_AUTH_TOKEN is required',
                        file=sys.stderr)
            return 1
        options.auth_token = create_auth_token()
        os.environ['BLUEPASS_AUTH_TOKEN'] = options.auth_token

    global log
    logging.setup_logging(options)
    log = logging.get_logger(name='main')

    # Need to start up the backend?

    if startbe:
        process = start_backend(options)
        sock, runinfo = connect_backend(options)
        options.connect = runinfo['listen']

    # Run either the front-end or the backend

    if options.run_backend:
        logging.set_default_logger('backend')
        backend = singleton(Backend, options)
        ret = backend.run()
    else:
        logging.set_default_logger('frontend.{0}'.format(fe.name))
        frontend = singleton(Frontend, options)
        ret = frontend.run()

    # Back from frontend or backend.

    if startbe and not options.daemon:
        stop_backend(options, process, sock)

    return ret


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = model
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import time
import math
import itertools
import socket
import uuid

from bluepass import base64, json, uuid4, logging
from bluepass.error import StructuredError
from bluepass.crypto import CryptoProvider, CryptoError
from bluepass import platform

import hashlib

import gruvi
from gruvi import compat

__all__ = ('Model', 'ModelError')


class ModelError(StructuredError):
    """Model error."""


class Model(object):
    """This class implements our vault/item model on top of our database."""

    def __init__(self, database):
        """Create a new model on top of `database`."""
        self.database = database
        self.crypto = CryptoProvider()
        self.vaults = {}
        self._log = logging.get_logger(self)
        self._next_seqnr = {}
        self._private_keys = {}
        self._trusted_certs = {}
        self._version_cache = {}
        self._linear_history = {}
        self._full_history = {}
        self.callbacks = []
        self._update_schema()
        self._load_vaults()

    def _update_schema(self):
        """Create or update the database schema."""
        db = self.database
        if 'config' not in db.tables:
            db.create_table('config')
        if 'vaults' not in db.tables:
            db.create_table('vaults')
            db.create_index('vaults', '$id', 'TEXT', True)
        if 'items' not in db.tables:
            db.create_table('items')
            db.create_index('items', '$id', 'TEXT', True)
            db.create_index('items', '$vault', 'TEXT', False)
            db.create_index('items', '$origin$node', 'TEXT', False)
            db.create_index('items', '$origin$seqnr', 'INT', False)
            db.create_index('items', '$payload$_type', 'TEXT', False)

    def check_vault(self, vault):
        """Check a vault for consistency."""
        try:
            u = json.unpack(vault, '{s:s,s:s,s:s,s:' \
                            '{s:{s:s,s:s,s:s,s:{s:s,s:s,s:s,s:s,s:u,s:u},' \
                            '    s:{s:s,s:s,s:s}},'
                            ' s:{s:s,s:s,s:s,s:{s:s,s:s,s:s,s:s,s:u,s:u},' \
                            '    s:{s:s,s:s,s:s}},'
                            ' s:{s:s,s:s,s:s,s:{s:s}}}}',
                            ('id', 'name', 'node', 'keys',
                             'sign', 'keytype', 'private', 'public', 'encinfo',
                                'algo', 'iv', 'kdf', 'salt', 'count', 'length',
                                'pwcheck', 'algo', 'random', 'verifier',
                             'encrypt', 'keytype', 'private', 'public', 'encinfo',
                                'algo', 'iv', 'kdf', 'salt', 'count', 'length',
                                'pwcheck', 'algo', 'random', 'verifier',
                             'auth', 'keytype', 'private', 'public', 'encinfo',
                                'algo'))
        except json.UnpackError as e:
            return False, str(e)
        if not uuid4.check(u[0]):
            return False, 'Illegal UUID "%s"' % u[0]
        if len(u[1]) == 0:
            return False, 'Vault name cannot be empty'
        elif len(u[1]) > 100:
            return False, 'Vault name too long (max = 100 characters)'
        if not uuid4.check(u[2]):
            return False, 'Illegal node UUID "%s"' % u[2]
        if u[3] != 'rsa':
            return False, 'Unknown key type "%s" for sign key' % u[3]
        if not base64.check(u[4]):
            return False, 'Invalid base64 for private sign key'
        if not base64.check(u[5]):
            return False, 'Invalid base64 for public sign key'
        if u[6] != 'aes-cbc-pkcs7':
            return False, 'Unkown algo "%s" for sign key' % u[6]
        if not base64.check(u[7]):
            return False, 'Invalid base64 for encinfo/IV for sign key' % u[7]
        if u[8] not in ('pbkdf2-hmac-sha1', 'pbkdf2-hmac-sha256'):
            return False, 'Unknown encinfo/kdf "%s" for sign key' % u[8]
        if not base64.check(u[9]):
            return False, 'Invalid base64 for encinfo/salt for sign key' % u[9]
        if u[12] != 'hmac-random-sha256':
            return False, 'Unknown pwcheck/algo "%s" for sign key' % u[12]
        if not base64.check(u[13]):
            return False, 'Invalid base64 in pwcheck/random for sign key' % u[13]
        if not base64.check(u[14]):
            return False, 'Invalid base64 in pwcheck/verifier for sign key' % u[14]
        if u[15] != 'rsa':
            return False, 'Unknown key type "%s" for encrypt key' % u[15]
        if not base64.check(u[16]):
            return False, 'Invalid base64 for private encrypt key'
        if not base64.check(u[17]):
            return False, 'Invalid base64 for public encrypt key'
        if u[18] != 'aes-cbc-pkcs7':
            return False, 'Unkown algo "%s" for encrypt key' % u[18]
        if not base64.check(u[19]):
            return False, 'Invalid base64 for encinfo/IV for encrypt key' % u[19]
        if u[20] not in ('pbkdf2-hmac-sha1', 'pbkdf2-hmac-sha256'):
            return False, 'Unknown encinfo/kdf "%s" for encrypt key' % u[20]
        if not base64.check(u[21]):
            return False, 'Invalid base64 for encinfo/salt for encrypt key' % u[21]
        if u[24] != 'hmac-random-sha256':
            return False, 'Unknown pwcheck/algo "%s" for encrypt key' % u[24]
        if not base64.check(u[25]):
            return False, 'Invalid base64 in pwcheck/random for encrypt key' % u[25]
        if not base64.check(u[26]):
            return False, 'Invalid base64 in pwcheck/verifier for encrypt key' % u[26]
        if u[27] != 'rsa':
            return False, 'Unknown key type "%s" for auth key' % u[27]
        if not base64.check(u[28]):
            return False, 'Invalid base64 for private auth key'
        if not base64.check(u[29]):
            return False, 'Invalid base64 for public auth key'
        if u[30] != 'plain':
            return False, 'Unexpected algo "%s" for encrypt key' % u[30]
        return True, 'All checks passed'

    def check_item(self, item):
        """Check the envelope of an item."""
        try:
            u = json.unpack(item, '{s:s,s:s,s:s,s:{s:s,s:u!},' \
                            's:{s:s*},s:{s:s,s:s!}!}',
                            ('id', '_type', 'vault', 'origin', 'node', 'seqnr',
                             'payload', '_type', 'signature', 'algo', 'blob'))
        except json.UnpackError as e:
            return False, str(e)
        if not uuid4.check(u[0]):
            return False, 'Illegal UUID'
        if u[1] != 'Item':
            return False, 'Expecting type "Item" (got: "%s")' % u[1]
        if not uuid4.check(u[2]):
            return False, 'Illegal vault UUID'
        if not uuid4.check(u[3]):
            return False, 'Illegal origin node UUID'
        if u[5] not in ('Certificate', 'EncryptedItem'):
            return False, 'Unknown payload type "%s"' % u[5]
        if u[6] != 'rsa-pss-sha256':
            return False, 'Unkown signature algo "%s"' % u[6]
        if not base64.check(u[7]):
            return False, 'Illegal base64 for signature'
        return True, 'All checks passed'

    def check_certificate(self, item):
        """Check the format of a certificiate.

        NOTE: This only does format checks , no signatures are verified!
        """
        try:
            u = json.unpack(item, '{s:s,s:{s:s,s:s,s:s,s:s,s:{s?:{s:s,s:s!},' \
                            's?:{s:s,s:s!},s:{s:s,s:s!}!},s?:{s?:b!}!}}',
                            ('id', 'payload', 'id', '_type', 'node', 'name',
                             'keys', 'sign', 'key', 'keytype',
                             'encrypt', 'key', 'keytype', 'auth', 'key',
                             'keytype', 'restrictions', 'synconly'))
        except json.UnpackError as e:
            return False, str(e)
        assert uuid4.check(u[0])
        if not uuid4.check(u[1]):
            return False, 'Invalid UUID'
        if u[2] != 'Certificate':
            return False, 'Expecting type "Certificate" (got: "%s")' % u[3]
        if not uuid4.check(u[3]):
            return False, 'Invalid node UUID'
        if not u[4]:
            return False, 'Name cannot be empty'
        elif len(u[4]) > 100:
            return False, 'Name too long (max = 100 characters)'
        if not base64.check(u[5]):
            return False, 'Invalid base64 for sign key'
        if u[6] != 'rsa':
            return False, 'Unknown key type "%s" for sign key' % u[6]
        if not base64.check(u[7]):
            return False, 'Invalid base64 for encrypt key'
        if u[8] != 'rsa':
            return False, 'Unkown key type "%s" for encrypt key' % u[8]
        if not base64.check(u[9]):
            return False, 'Invalid base64 for auth key'
        if u[10] != 'rsa':
            return False, 'Unkown key type "%s" for auth key' % u[10]
        return True, 'All checks passed'

    def check_encrypted_item(self, item):
        """Check the format of an encrypted item."""
        try:
            u = json.unpack(item, '{s:s,s:{s:s,s:s,s:s,s:s,s:s,s:o!}}',
                            ('id', 'payload', '_type', 'algo', 'iv',
                             'blob', 'keyalgo', 'keys'))
        except json.UnpackError as e:
            return False, str(e)
        assert uuid4.check(u[0])
        assert u[1] == 'EncryptedItem'
        if u[2] != 'aes-cbc-pkcs7':
            return False, 'Unknown algo "%s"' % u[2]
        if not base64.check(u[3]):
            return False, 'Invalid base64 for IV'
        if not base64.check(u[4]):
            return False, 'Invalid base64 for blob'
        if u[5] != 'rsa-oaep':
            return False, 'Unknown keyalgo "%s"' % u[5]
        if not isinstance(u[6], dict):
            return False, 'Invalid keys dict'
        for key,value in u[6].items():
            if not uuid4.check(key):
                return False, 'Illegal key UUID "%s" in keys dict' % key
            if not base64.check(value):
                return False, 'Invalid base64 for key "%s" in keys dict' % key
        return True, 'All checks passed'

    def _check_items(self, vault):
        """Check all items in a vault."""
        total = errors = 0
        items = self.database.findall('items', '$vault = ?', (vault,))
        self._log.debug('Checking all items in vault "{}"', vault)
        for item in items:
            uuid = item.get('id', '<no id>')
            status, detail = self.check_item(item)
            if not status:
                self._log.error('Invalid item "{}": {}', uuid, detail)
                errors += 1
                continue
            typ = item['payload']['_type']
            if typ == 'Certificate':
                status, detail = self.check_certificate(item)
                if not status:
                    self._log.error('Invalid certificate "{}": {}', uuid, detail)
                    errors += 1
                    continue
            elif typ == 'EncryptedItem':
                status, detail = self.check_encrypted_item(item)
                if not status:
                    self._log.error('Invalid encrypted item "{}": {}', uuid, detail)
                    errors += 1
                    continue
            else:
                self_log.error('Unknown payload type "{}" in item "{}"', typ, item['id'])
                continue
            total += 1
        self._log.debug('Vault "{}" contains {} items and {} errors', vault, total, errors)
        return errors == 0

    def _load_vault(self, vault):
        """Check and load a single vault."""
        uuid = vault.get('id', '<no id>')
        status, detail = self.check_vault(vault)
        if not status:
            self._log.error('Vault "{}" has errors (skipping): {}', uuid, detail)
            return False
        uuid = vault['id']
        if not self._check_items(vault['id']):
            self._log.error('Vault {} has items with errors, skipping', uuid)
            return False
        self.vaults[uuid] = vault
        self._private_keys[uuid] = []
        self._version_cache[uuid] = {}
        self._linear_history[uuid] = {}
        self._full_history[uuid] = {}
        seqnr = self.database.execute('items', """
                SELECT MAX($origin$seqnr)
                FROM items
                WHERE $origin$node = ? AND $vault = ?
                """, (vault['node'], vault['id']))
        if seqnr:
            self._next_seqnr[uuid] = seqnr[0][0] + 1
        else:
            self._next_seqnr[uuid] = 0
        self._log.debug('Succesfully loaded vault "{}" ({})', uuid, vault['name'])
        return True

    def _load_vaults(self):
        """Check and load all vaults."""
        total = errors = 0
        filename = self.database.filename
        self._log.debug('loading all vaults from database {}', filename)
        vaults = self.database.findall('vaults')
        for vault in vaults:
            total += 1
            if not self._load_vault(vault):
                errors += 1
                continue
            self._calculate_trust(vault['id'])
        self._log.debug('successfully loaded {} vaults, {} vaults had errors',
                        total-errors, errors)

    def _verify_signature(self, item, pubkey):
        """Verify the signature on an item."""
        assert self.check_item(item)[0]
        signature = item.pop('signature')
        if signature['algo'] != 'rsa-pss-sha256':
            self._log.error('unknown signature algo "{}" for item "{}"', algo, item['id'])
            return False
        message = json.dumps_c14n(item).encode('utf8')
        blob = base64.decode(signature['blob'])
        try:
            status = self.crypto.rsa_verify(message, blob, pubkey, 'pss-sha256')
        except CryptoError:
            log.error('garbage in signature for item "%s"', item['id'])
            return False
        if not status:
            log.error('invalid signature for item "%s"', item['id'])
            return False
        item['signature'] = signature
        return True

    def __collect_certs(self, node, nodekey, certs, result, depth):
        """Collect valid certificates."""
        if node not in certs:
            return
        result[node] = []
        for cert in certs[node]:
            if not self._verify_signature(cert, nodekey):
                continue
            synconly = cert['payload'].get('restrictions', {}).get('synconly', False)
            subject = cert['payload']['node']
            subjkey = base64.decode(cert['payload']['keys']['sign']['key'])
            if node == subject:
                # self-signed certificate
                result[node].append((depth+1+synconly*100, cert))
            else:
                result[node].append((depth+2+synconly*100, cert))
            if subject in result:
                # There are loops in the "signed by" graph because during
                # pairing nodes sign each other's key.
                continue
            if synconly:
                # Synconly certs are not allowed to sign items
                continue
            self.__collect_certs(subject, subjkey, certs, result, depth+2)

    def _calculate_trust(self, vault):
        """Calculate a list of trusted certificates."""
        assert vault in self.vaults
        # Create mapping of certificates by their signer
        certs = {}
        query = "$vault = ? AND $payload$_type = 'Certificate'"
        result = self.database.findall('items', query, (vault,))
        for cert in result:
            assert self.check_item(cert)[0]
            signer = cert['origin']['node']
            try:
                certs[signer].append(cert)
            except KeyError:
                certs[signer] = [cert]
        # Collect valid certs: a valid cert is one that is signed by a trusted
        # signing key. A trusted signing key is our own key, or a key that has
        # a valid certificate that does not have the "synconly" option.
        node = self.vaults[vault]['node']
        nodekey = base64.decode(self.vaults[vault]['keys']['sign']['public'])
        result = {}
        self.__collect_certs(node, nodekey, certs, result, 0)
        trusted_certs = {}
        for signer in result:
            for cert in result[signer]:
                subject = cert[1]['payload']['node']
                try:
                    trusted_certs[subject].append(cert)
                except KeyError:
                    trusted_certs[subject] = [cert]
        for subject in trusted_certs:
            certs = trusted_certs[subject]
            certs.sort()
            trusted_certs[subject] = [ cert[1] for cert in certs ]
        ncerts = sum([len(certs) for certs in trusted_certs.items()])
        self._log.debug('there are {} trusted certs for vault "{}"', ncerts, vault)
        self._trusted_certs[vault] = trusted_certs

    def check_decrypted_item(self, item):
        """Check a decrypted item."""
        try:
            u = json.unpack(item, '{s:s,s:{s:s,s:s}}',
                            ('id', 'payload', 'id', '_type'))
        except json.UnpackError as e:
            return False, str(e)
        if not uuid4.check(u[1]):
            return False, 'Invalid UUID "%s"' % u[1]
        if u[2] != 'Version':
            return False, 'Unknown type "%s"' % u[2]
        return True, 'All checks passed'

    def check_version(self, item):
        """Check a decrypted item and ensure it is a valid version."""
        try:
            u = json.unpack(item, '{s:s,s:{s:s,s:s,s?:s,s?:b,s:u,s{s:s}}}',
                            ('id', 'payload', 'id', '_type', 'parent', 'deleted',
                             'created_at', 'version', 'id'))
        except json.UnpackError as e:
            return str(e)
        assert uuid4.check(u[0])
        if not uuid4.check(u[1]):
            return False, 'Invalid version UUID "%s"' % u[1]
        if u[2] != 'Version':
            return False, 'Expecting type "Version" (got: "%s")' % u[2]
        if u[3] and not uuid4.check(u[3]):
            return False, 'Invalid parent UUID "%s"' % u[3]
        if not uuid4.check(u[6]):
            return False, 'Invalid version data UUID "%s"' % u[6]
        return True, 'All checks passed'

    def _update_version_cache(self, items, notify=True, local=True):
        """Update the version cache for `items'. If `notify` is True,
        callbacks will be run."""
        grouped = {}
        for item in items:
            uuid = item['payload']['version']['id']
            try:
                grouped[uuid].append(item)
            except KeyError:
                grouped[uuid] = [item]
        changes = {}
        for uuid,versions in grouped.items():
            vault = versions[0]['vault']
            try:
                self._full_history[vault][uuid] += versions
            except KeyError:
                self._full_history[vault][uuid] = versions
            linear = self._sort_history(uuid, self._full_history[vault][uuid])
            self._linear_history[vault][uuid] = linear
            current = self._version_cache[vault].get(uuid)
            if not current and not linear[0]['payload'].get('deleted'):
                self._version_cache[vault][uuid] = linear[0]
            elif current and linear[0]['payload'].get('deleted'):
                del self._version_cache[vault][uuid]
            elif current and linear[0]['payload']['id'] != current['payload']['id']:
                self._version_cache[vault][uuid] = linear[0]
            else:
                continue
            if not notify:
                continue
            if vault not in changes:
                changes[vault] = []
            changes[vault].append(self._get_version(linear[0]))
        for vault in changes:
            self.raise_event('VersionsAdded', vault, changes[vault])

    def _clear_version_cache(self, vault):
        """Wipe and reset the version cache. Used when locking a vault."""
        if vault not in self._version_cache:
            return
        assert vault in self._linear_history
        assert vault in self._full_history
        self._version_cache[vault].clear()
        self._linear_history[vault].clear()
        self._full_history[vault].clear()

    def _sort_history(self, uuid, items):
        """Create a linear history for a set of versions. This is
        where our conflict resolution algorithm is implemented."""
        # Create a tree mapping parents to their children
        if not items:
            return []
        tree = {}
        parents = {}
        for item in items:
            parent = item['payload'].get('parent')
            try:
                tree[parent].append(item)
            except KeyError:
                tree[parent] = [item]
            parents[item['payload']['id']] = item
        # Our conflict resulution works like this: we find the leaf in the
        # tree with the highest created_at time. That is the current version.
        # The linear history of the current version are its ancestors.
        #
        # This algorithm protects us from nodes in the vault that have a wrong
        # clock. However, if two updates happen close enough that the entire
        # tree has not yet replicated, then the item with the highest created_at
        # will win, whether or not that is the version that was created last
        # according to a universal clock.
        leaves = []
        for item in items:
            if item['payload']['id'] in tree:
                continue  # not leaf
            leaves.append(item)
        assert len(leaves) > 0
        leaves.sort(key=lambda x: x['payload']['created_at'], reverse=True)
        history = [leaves[0]]
        parent = item['payload'].get('parent')
        while parent is not None and parent in parents:
            item = parents[parent]
            history.append(item)
            parent = item['payload'].get('parent')
        return history
 
    def _load_versions(self, vault):
        """Load all current versions and their history."""
        versions = []
        query = "$vault = ? AND $payload$_type = 'EncryptedItem'"
        items = self.database.findall('items', query, (vault,))
        for item in items:
            if not self._verify_item(vault, item) or \
                    not self._decrypt_item(vault, item) or \
                    not self.check_decrypted_item(item)[0] or \
                    not self.check_version(item)[0]:
                continue
            versions.append(item)
        self._update_version_cache(versions, notify=False)
        cursize = len(self._version_cache[vault])
        linsize = sum((len(h) for h in self._linear_history[vault].items()))
        fullsize = sum((len(h) for h in self._full_history[vault].items()))
        self._log.debug('loaded {} versions from vault {}', cursize, vault)
        self._log.debug('linear history contains {} versions', linsize)
        self._log.debug('full history contains {} versions', fullsize)

    def _sign_item(self, vault, item):
        """Add a signature to an item."""
        assert vault in self.vaults
        assert vault in self._private_keys
        signature = {}
        signature['algo'] = 'rsa-pss-sha256'
        message = json.dumps_c14n(item).encode('utf8')
        signkey = self._private_keys[vault][0]
        blob = self.crypto.rsa_sign(message, signkey, padding='pss-sha256')
        signature['blob'] = base64.encode(blob)
        item['signature'] = signature

    def _verify_item(self, vault, item):
        """Verify that an item has a correct signature and that it
        the signature was created by a trusted node."""
        signer = item['origin']['node']
        if signer not in self._trusted_certs[vault]:
            self._log.error('item {} was signed by unknown/untrusted node {}',
                            item['id'], signer)
            return False
        cert = self._trusted_certs[vault][signer][0]['payload']
        synconly = cert.get('restrictions', {}).get('synconly')
        if synconly:
            return False  # synconly certs may not sign items
        pubkey = base64.decode(cert['keys']['sign']['key'])
        return self._verify_signature(item, pubkey)

    def _encrypt_item(self, vault, item):
        """INTERNAL: Encrypt an item."""
        assert vault in self.vaults
        assert vault in self._private_keys
        crypto = self.crypto
        clear = item.pop('payload')
        item['payload'] = payload = {}
        payload['_type'] = 'EncryptedItem'
        payload['algo'] = 'aes-cbc-pkcs7'
        iv = crypto.random(16)
        payload['iv'] = base64.encode(iv)
        symkey = crypto.random(16)
        message = json.dumps(clear).encode('utf8')
        blob = crypto.aes_encrypt(message, symkey, iv, mode='cbc-pkcs7')
        payload['blob'] = base64.encode(blob)
        payload['keyalgo'] = 'rsa-oaep'
        payload['keys'] = keys = {}
        # encrypt the symmetric key to all nodes in the vault including ourselves
        for node in self._trusted_certs[vault]:
            cert = self._trusted_certs[vault][node][0]['payload']
            synconly = cert.get('restrictions', {}).get('synconly')
            if synconly:
                # do not encrypt items to "synconly" nodes
                continue
            pubkey = base64.decode(cert['keys']['encrypt']['key'])
            enckey = crypto.rsa_encrypt(symkey, pubkey, padding='oaep')
            keys[node] = base64.encode(enckey)

    def _decrypt_item(self, vault, item):
        """INTERNAL: decrypt an encrypted item."""
        assert vault in self.vaults
        assert vault in self._private_keys
        crypto = self.crypto
        algo = item['payload']['algo']
        keyalgo = item['payload']['keyalgo']
        if algo != 'aes-cbc-pkcs7':
            self._log.error('unknow algo in encrypted payload in item {}: {}', item['id'], algo)
            return False
        if keyalgo != 'rsa-oaep':
            self._log.error('unknow keyalgo in encrypted payload in item {}: {}', item['id'], algo)
            return False
        node = self.vaults[vault]['node']
        keys = item['payload']['keys']
        if node not in keys:
            self._log.info('item {} was not encrypted to us, skipping', item['id'])
            return False
        try:
            enckey = base64.decode(keys[node])
            privkey = self._private_keys[vault][1]
            symkey = crypto.rsa_decrypt(enckey, privkey, padding='oaep')
            blob = base64.decode(item['payload']['blob'])
            iv = base64.decode(item['payload']['iv'])
            clear = crypto.aes_decrypt(blob, symkey, iv, mode='cbc-pkcs7')
        except CryptoError as e:
            self._log.error('could not decrypt encrypted payload in item {}: {}' % (item['id'], str(e)))
            return False
        payload = json.try_loads(clear.decode('utf8'))
        if payload is None:
            self._log.error('illegal JSON in decrypted payload in item {}', item['id'])
            return False
        item['payload'] = payload
        return True

    def _add_origin(self, vault, item):
        """Add the origin section to an item."""
        item['origin'] = origin = {}
        origin['node'] = self.vaults[vault]['node']
        origin['seqnr'] = self._next_seqnr[vault]
        self._next_seqnr[vault] += 1
        
    def _new_item(self, vault, ptype, **kwargs):
        """Create a new empty item."""
        item = {}
        item['id'] = self.crypto.randuuid()
        item['_type'] = 'Item'
        item['vault'] = vault
        item['payload'] = payload = {}
        payload['_type'] = ptype
        payload.update(kwargs)
        return item

    def _new_certificate(self, vault, **kwargs):
        """Create anew certificate."""
        item = self._new_item(vault, 'Certificate', **kwargs)
        item['payload']['id'] = self.crypto.randuuid()
        return item

    def _new_version(self, vault, parent=None, **version):
        """Create a new empty version."""
        item = self._new_item(vault, 'Version')
        payload = item['payload']
        payload['id'] = self.crypto.randuuid()
        payload['created_at'] = int(time.time())
        if parent is not None:
            payload['parent'] = parent
        payload['version'] = version.copy()
        return item

    def _get_version(self, item):
        """Return the version inside an item, with envelope."""
        payload = item['payload'].copy()
        version = payload['version'].copy()
        del payload['version']
        version['_envelope'] = payload
        return version

    def _create_vault_key(self, password):
        """Create a new vault key. Return a tuple (private, public,
        keyinfo). The keyinfo structure contains the encrypted keys."""
        crypto = self.crypto
        keyinfo = {}
        private, public = crypto.rsa_genkey(3072)
        keyinfo['keytype'] = 'rsa'
        keyinfo['public'] = base64.encode(public)
        keyinfo['encinfo'] = encinfo = {}
        if not password:
            encinfo['algo'] = 'plain'
            keyinfo['private'] = base64.encode(private)
            return private, public, keyinfo
        encinfo['algo'] = 'aes-cbc-pkcs7'
        iv = crypto.random(16)
        encinfo['iv'] = base64.encode(iv)
        prf = 'hmac-sha256' if self.crypto.pbkdf2_prf_available('hmac-sha256') \
                    else 'hmac-sha1'
        encinfo['kdf'] = 'pbkdf2-%s' % prf
        # Tune pbkdf2 so that it takes about 0.2 seconds (but always at
        # least 4096 iterations).
        count = max(4096, int(0.2 * crypto.pbkdf2_speed(prf)))
        self._log.debug('using {} iterations for PBKDF2', count)
        encinfo['count'] = count
        encinfo['length'] = 16
        salt = crypto.random(16)
        encinfo['salt'] = base64.encode(salt)
        symkey = crypto.pbkdf2(password, salt, encinfo['count'],
                               encinfo['length'], prf=prf)
        enckey = crypto.aes_encrypt(private, symkey, iv, mode='cbc-pkcs7')
        keyinfo['private'] = base64.encode(enckey)
        keyinfo['pwcheck'] = pwcheck = {}
        pwcheck['algo'] = 'hmac-random-sha256'
        random = crypto.random(16)
        pwcheck['random'] = base64.encode(random)
        verifier = crypto.hmac(symkey, random, 'sha256')
        pwcheck['verifier'] = base64.encode(verifier)
        return private, public, keyinfo

    def _create_vault_keys(self, password):
        """Create all 3 vault keys (sign, encrypt and auth)."""
        # Generate keys in the CPU thread pool.
        prf = 'hmac-sha256' if self.crypto.pbkdf2_prf_available('hmac-sha256') \
                    else 'hmac-sha1'
        dummy = self.crypto.pbkdf2_speed(prf)
        pool = gruvi.ThreadPool.get_cpu_pool()
        fsign = pool.submit(self._create_vault_key, password)
        fencrypt = pool.submit(self._create_vault_key, password)
        fauth = pool.submit(self._create_vault_key, '')
        keys = { 'sign': fsign.result(), 'encrypt': fencrypt.result(),
                 'auth': fauth.result() }
        return keys
  
    # Events / callbacks

    def add_callback(self, callback):
        """Register a callback that that gets notified when one or more
        versions have changed."""
        self.callbacks.append(callback)

    def raise_event(self, event, *args):
        """Raise an event o all callbacks."""
        for callback in self.callbacks:
            try:
                callback(event, *args)
            except Exception as e:
                self._log.error('callback raised exception: {}' % str(e))

    # API for a typical GUI consumer

    def get_config(self):
        """Return the configuration document."""
        config = self.database.findone('config')
        if config is None:
            config = { 'id': self.crypto.randuuid() }
            self.database.insert('config', config)
        return config

    def update_config(self, config):
        """Update the configuration document."""
        if not isinstance(config, dict):
            raise ModelError('InvalidArgument', '"config" must be a dict')
        uuid = config.get('id')
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Invalid config uuid')
        self.database.update('config', '$id = ?', (uuid,), config)

    def create_vault(self, name, password, uuid=None, notify=True):
        """Create a new vault.
        
        The `name` argument specifies the name of the vault to create. The
        private keys for this vault are encrypted with `password'. If the
        `uuid` argument is given, a vault with this UUID is created. The
        default is to generate an new UUID for this vault. The `notify`
        arguments determines wether or not callbacks must be called when this
        vault is created.
        """
        if not isinstance(name, compat.string_types):
            raise ModelError('InvalidArgument', '"name" must be str/unicode')
        if not isinstance(password, compat.string_types):
            raise ModelError('InvalidArgument', '"password" must be str/unicode')
        if uuid is not None:
            if not uuid4.check(uuid):
                raise ModelError('InvalidArgument', 'Illegal vault uuid')
            if uuid in self.vaults:
                raise ModelError('Exists', 'A vault with this UUID already exists')
        if isinstance(password, compat.text_type):
            password = password.encode('utf8')
        vault = {}
        if uuid is None:
            uuid = self.crypto.randuuid()
        vault['id'] = uuid
        vault['_type'] = 'Vault'
        vault['name'] = name
        vault['node'] = self.crypto.randuuid()
        keys = self._create_vault_keys(password)
        vault['keys'] = dict(((key, keys[key][2]) for key in keys))
        self.database.insert('vaults', vault)
        if notify:
            self.raise_event('VaultAdded', vault)
        self.vaults[uuid] = vault
        # Start unlocked by default
        self._private_keys[uuid] = (keys['sign'][0], keys['encrypt'][0])
        self._version_cache[uuid] = {}
        self._linear_history[uuid] = {}
        self._full_history[uuid] = {}
        self._next_seqnr[uuid] = 0
        # Add a self-signed certificate
        certinfo = { 'node': vault['node'], 'name': socket.gethostname() }
        keys = certinfo['keys'] = {}
        for key in vault['keys']:
            keys[key] = { 'key': vault['keys'][key]['public'],
                          'keytype': vault['keys'][key]['keytype'] }
        certinfo['restrictions'] = {}
        item = self._new_certificate(uuid, **certinfo)
        self._add_origin(uuid, item)
        self._sign_item(uuid, item)
        self.import_item(uuid, item, notify=notify)
        return vault

    def get_vault(self, uuid):
        """Return the vault with `uuid` or None if there is no such vault."""
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        return self.database.findone('vaults', '$id = ?', (uuid,))

    def get_vaults(self):
        """Return a list of all vaults."""
        return self.database.findall('vaults')

    def update_vault(self, vault):
        """Update a vault."""
        status, detail = self.check_vault(vault)
        if not status:
            raise ModelError('InvalidArgument', 'Invalid vault: %s' % detail)
        self.database.update('vaults', '$id = ?', (vault['id'],), vault)
        self.raise_event('VaultUpdated', vault)

    def delete_vault(self, vault):
        """Delete a vault and all its items."""
        if not isinstance(vault, dict):
            raise ModelError('InvalidArgument', '"vault" must be a dict')
        uuid = vault.get('id')
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Invalid vault UUID')
        if uuid not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        self.database.delete('vaults', '$id = ?', (uuid,))
        self.database.delete('items', '$vault = ?', (uuid,))
        # The VACUUM command here ensures that the data we just deleted is
        # removed from the sqlite database file. However, quite likely the
        # data is still on the disk, at least for some time. So this is not
        # a secure delete.
        self.database.execute('vaults', 'VACUUM')
        del self.vaults[uuid]
        del self._private_keys[uuid]
        del self._version_cache[uuid]
        del self._linear_history[uuid]
        del self._full_history[uuid]
        del self._next_seqnr[uuid]
        vault['deleted'] = True
        self.raise_event('VaultRemoved', vault)

    def get_vault_statistics(self, uuid):
        """Return some statistics for a vault."""
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if uuid not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        stats = {}
        stats['current_versions'] = len(self._version_cache[uuid])
        stats['total_versions'] = len(self._linear_history[uuid])
        linsize = sum((len(h) for h in self._linear_history[uuid].items()))
        stats['linear_history_size'] = linsize
        fullsize = sum((len(h) for h in self._full_history[uuid].items()))
        stats['full_history_size'] = fullsize
        result = self.database.execute('items', """
                    SELECT COUNT(*) FROM items WHERE $vault = ?
                    """, (uuid,))
        stats['total_items'] = result[0]
        result = self.database.execute('items', """
                    SELECT COUNT(*) FROM items WHERE $vault = ?
                    AND $payload$_type = 'Certificate'
                    """, (uuid,))
        stats['total_certificates'] = result[0]
        result = self.database.execute('items', """
                    SELECT COUNT(*) FROM
                    (SELECT DISTINCT $payload$node FROM items
                     WHERE $vault = ? AND $payload$_type = 'Certificate')
                    """, (uuid,))
        stats['total_nodes'] = result[0]
        stats['trusted_nodes'] = len(self._trusted_certs[uuid])
        return stats

    def unlock_vault(self, uuid, password):
        """Unlock a vault.
        
        The vault `uuid` is unlocked using `password`. This decrypts the
        private keys that are stored in the database and stored them in
        memory. It is not an error to unlock a vault that is already unlocked.
        """
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if not isinstance(password, compat.string_types):
            raise ModelError('InvalidArgument', 'Illegal password')
        if uuid not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        assert uuid in self._private_keys
        if len(self._private_keys[uuid]) > 0:
            return
        if isinstance(password, compat.text_type):
            password = password.encode('utf8')
        crypto = self.crypto
        for key in ('sign', 'encrypt'):
            keyinfo = self.vaults[uuid]['keys'][key]
            pubkey = base64.decode(keyinfo['public'])
            privkey = base64.decode(keyinfo['private'])
            encinfo = keyinfo['encinfo']
            pwcheck = keyinfo['pwcheck']
            # These are enforced by check_vault()
            assert encinfo['algo'] == 'aes-cbc-pkcs7'
            assert encinfo['kdf'] in ('pbkdf2-hmac-sha1', 'pbkdf2-hmac-sha256')
            assert pwcheck['algo'] == 'hmac-random-sha256'
            salt = base64.decode(encinfo['salt'])
            iv = base64.decode(encinfo['iv'])
            prf = encinfo['kdf'][7:]
            symkey = crypto.pbkdf2(password, salt, encinfo['count'],
                                   encinfo['length'], prf=prf)
            random = base64.decode(pwcheck['random'])
            verifier = base64.decode(pwcheck['verifier'])
            check = crypto.hmac(symkey, random, 'sha256')
            if check != verifier:
                raise ModelError('WrongPassword')
            private = crypto.aes_decrypt(privkey, symkey, iv, 'cbc-pkcs7')
            self._private_keys[uuid].append(private)
        self._load_versions(uuid)
        self._log.debug('unlocked vault "{}" ({})', uuid, self.vaults[uuid]['name'])
        self.raise_event('VaultUnlocked', self.vaults[uuid])

    def lock_vault(self, uuid):
        """Lock a vault.
        
        This destroys the decrypted private keys and any decrypted items that
        are cached. It is not an error to lock a vault that is already locked.
        """
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if uuid not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        assert uuid in self._private_keys
        if len(self._private_keys[uuid]) == 0:
            return
        self._private_keys[uuid] = []
        self._clear_version_cache(uuid)
        self._log.debug('locked vault "{}" ({})', uuid, self.vaults[uuid]['name'])
        self.raise_event('VaultLocked', self.vaults[uuid])

    def vault_is_locked(self, uuid):
        """Return whether a vault is locked."""
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if uuid not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        assert uuid in self._private_keys
        return len(self._private_keys[uuid]) == 0

    def get_version(self, vault, uuid):
        """Get a single current version."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Illegal version uuid')
        if vault not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        if self.vault_is_locked(vault):
            raise ModelError('Locked', 'Vault is locked')
        assert vault in self._version_cache
        item = self._version_cache[vault].get(uuid)
        version = self._get_version(item) if item else None
        return version

    def get_versions(self, vault):
        """Return a list of all current versions."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if vault not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        if self.vault_is_locked(vault):
            raise ModelError('Locked', 'Vault is locked')
        assert vault in self._version_cache
        versions = []
        for item in self._version_cache[vault].values():
            version = self._get_version(item)
            versions.append(version)
        return versions

    def add_version(self, vault, version):
        """Add a new version."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if not isinstance(version, dict):
            raise ModelError('InvalidArgument', '"version" must be a dict')
        if vault not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        if vault not in self._private_keys:
            raise ModelError('Locked', 'Vault is locked')
        version['id'] = self.crypto.randuuid()
        item = self._new_version(vault, **version)
        self._encrypt_item(vault, item)
        self._add_origin(vault, item)
        self._sign_item(vault, item)
        self.import_item(vault, item)
        version = self._get_version(item)
        return version

    def update_version(self, vault, version):
        """Update an existing version."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if not isinstance(version, dict):
            raise ModelError('InvalidArgument', '"version" must be a dict')
        uuid = version.get('id')
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Invalid version uuid')
        if vault not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        if vault not in self._private_keys:
            raise ModelError('Locked', 'Vault is locked')
        assert vault in self._version_cache
        if uuid not in self._version_cache[vault]:
            raise ModelError('NotFound', 'Version to update not found')
        parent = self._version_cache[vault][uuid]['payload']['id']
        item = self._new_version(vault, parent=parent, **version)
        self._encrypt_item(vault, item)
        self._add_origin(vault, item)
        self._sign_item(vault, item)
        self.import_item(vault, item)
        version = self._get_version(item)
        return version

    def delete_version(self, vault, version):
        """Delete a version."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if not isinstance(version, dict):
            raise ModelError('InvalidArgument', '"version" must be a dict')
        uuid = version.get('id')
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Invalid version uuid')
        if vault not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        if vault not in self._private_keys:
            raise ModelError('Locked', 'Vault is locked')
        assert vault in self._version_cache
        if uuid not in self._version_cache[vault]:
            raise ModelError('NotFound', 'Version to delete not found')
        parent = self._version_cache[vault][uuid]['payload']['id']
        item = self._new_version(vault, parent=parent, **version)
        item['payload']['deleted'] = True
        self._encrypt_item(vault, item)
        self._add_origin(vault, item)
        self._sign_item(vault, item)
        self.import_item(vault, item)
        version = self._get_version(item)
        return version

    def get_version_history(self, vault, uuid):
        """Return the history for version `uuid`."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Illegal version uuid')
        if vault not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        if self.vault_is_locked(vault):
            raise ModelError('Locked', 'Vault is locked')
        assert vault in self._linear_history
        if uuid not in self._linear_history[vault]:
            raise ModelError('NotFound', 'Version not found')
        history = [ self._get_version(item)
                    for item in self._linear_history[vault][uuid] ]
        return history

    def get_version_item(self, vault, uuid):
        """Get the most recent item for a version (including
        deleted versions)."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if not uuid4.check(uuid):
            raise ModelError('InvalidArgument', 'Illegal version uuid')
        if vault not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        if self.vault_is_locked(vault):
            raise ModelError('Locked', 'Vault is locked')
        assert vault in self._version_cache
        version = self._linear_history[vault].get(uuid)
        if version:
            version = version[0].copy()
        return version

    # Pairing

    def get_certificate(self, vault, node):
        """Return a certificate for `node` in `vault`, if there is one."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if not uuid4.check(node):
            raise ModelError('InvalidArgument', 'Illegal node uuid')
        if vault not in self.vaults or node not in self._trusted_certs[vault]:
            return
        return self._trusted_certs[vault][node][0]

    def get_auth_key(self, vault):
        """Return the private authentication key for `vault`."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if vault not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        vault = self.vaults[vault]
        key = base64.decode(vault['keys']['auth']['private'])
        return key

    def check_certinfo(self, certinfo):
        """Check a certificate info structure."""
        try:
            u = json.unpack(certinfo, '{s:s,s:s,s:{s:{s:s,s:s!},' \
                            's:{s:s,s:s!},s:{s:s,s:s!}!},s?:{s?:b!}!}',
                            ('node', 'name', 'keys', 'sign', 'key', 'keytype',
                             'encrypt', 'key', 'keytype', 'auth', 'key',
                             'keytype', 'restrictions', 'synconly'))
        except json.UnpackError as e:
            return False, str(e)
        if not uuid4.check(u[0]):
            return False, 'Illegal node UUID'
        if not u[1]:
            return False, 'Name must be > 0 characters'
        if len(u[1]) > 100:
            return False, 'Name too long (max = 100 characters)'
        if not base64.check(u[2]):
            return False, 'Illegal base64 in sign key'
        if u[3] != 'rsa':
            return False, 'Unknown sign key type: %s' % u[3]
        if not base64.check(u[4]):
            return False, 'Illegal base64 in encrypt key'
        if u[5] != 'rsa':
            return False, 'Unknown encrypt key type: %s' % u[5]
        if not base64.check(u[6]):
            return False, 'Illegal base64 in auth key'
        if u[7] != 'rsa':
            return False, 'Unknown auth key type: %s' % u[5]
        return True, 'All checks passed'

    def add_certificate(self, vault, certinfo):
        """Add a certificate to a vault.

        Adding a certificate to a vault establishes a trust relationship
        between this node and the node that we are generating the certifcate
        for. If the certificate is "synconly", then only synchronization with
        us is allowed. If the certificate is not synconly, in addition,
        existing versions will be re-encrypted to the newly added node, and new
        versions will be encrypted to it automatically. The new node may also
        introduce other new nodes into the vault. 
        """
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault UUID')
        if vault not in self.vaults:
            raise ModelError('NotFound', 'Vault not found')
        if self.vault_is_locked(vault):
            raise ModelError('Locked', 'Vault is locked')
        status, detail = self.check_certinfo(certinfo)
        if not status:
            raise ModelError('InvalidArgument', detail)
        item = self._new_certificate(vault, **certinfo)
        self._add_origin(vault, item)
        self._sign_item(vault, item)
        self.import_item(vault, item)
        synconly = certinfo.get('restrictions', {}).get('synconly')
        if not synconly:
            for version in self.get_versions(vault):
                if not version.get('deleted'):
                    self.update_version(vault, version)
        return item

    # Synchronization

    def get_vector(self, vault):
        """Return a vector containing the latest versions for each node that
        we know of."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if vault not in self.vaults:
            raise ModelError('NotFound', 'No such vault')
        vector = self.database.execute('items', """
                    SELECT $origin$node,MAX($origin$seqnr)
                    FROM items
                    WHERE $vault = ?
                    GROUP BY $origin$node""", (vault,))
        return vector

    def get_items(self, vault, vector=None):
        """Return the items in `vault` that are newer than `vector`."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if vector is not None:
            if not isinstance(vector, (tuple, list)):
                raise ModelError('InvalidArgument', 'Illegal vector')
            for elem in vector:
                if not isinstance(elem, (tuple, list)) or len(elem) != 2 or \
                        not uuid4.check(elem[0]) or \
                        not isinstance(elem[1], compat.integer_types):
                    raise ModelError('InvalidArgument', 'Illegal vector')
        if vault not in self.vaults:
            raise ModelError('NotFound', 'no such vault')
        query = '$vault = ?'
        args = [vault]
        if vector is not None:
            nodes = self.database.execute('items',
                            'SELECT DISTINCT $origin$node FROM items')
            terms = []
            vector = dict(vector)
            for node, in nodes:
                if node in vector:
                    terms.append('($origin$node = ? AND $origin$seqnr > ?)')
                    args.append(node); args.append(vector[node])
                else:
                    terms.append('$origin$node = ?')
                    args.append(node)
            query += ' AND (%s)' % ' OR '.join(terms)
        return self.database.findall('items', query, args)

    def import_item(self, vault, item, notify=True):
        """Import a single item."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault UUID')
        status, detail = self.check_item(item)
        if not status:
            raise ModelError('InvalidArgument', 'Invalid item: %s' % detail)
        if item['payload']['_type'] == 'Certificate':
            status, detail = self.check_certificate(item)
            if not status:
                raise ModelError('InvalidArgument', 'Invalid cert: %s' % detail)
            self.database.insert('items', item)
            self._log.debug('imported certificate, re-calculating trust')
            self._calculate_trust(item['vault'])
            # Find items that are signed by this certificate
            query = "$vault = ? AND $payload$_type = 'EncryptedItem'" \
                    " AND $origin$node = ?"
            args = (vault, item['payload']['node'])
            items = self.database.findall('items', query, args)
        elif item['payload']['_type'] == 'EncryptedItem':
            status, detail = self.check_encrypted_item(item)
            if not status:
                raise ModelError('InvalidArgument',
                                 'Invalid encrypted item: %s' % detail)
            self.database.insert('items', item)
            items = [item]
        else:
            raise ModelError('InvalidArgument', 'Unknown payload type')
        if self.vault_is_locked(vault):
            return
        # See if the wider set of certificates exposed some versions
        versions = []
        for item in items:
            if not self._verify_item(vault, item) or \
                    not self._decrypt_item(vault, item) or \
                    not self.check_decrypted_item(item)[0] or \
                    not self.check_version(item)[0]:
                continue
            versions.append(item)
        self._log.debug('updating version cache for {} versions', len(versions))
        self._update_version_cache(versions, notify=notify)

    def import_items(self, vault, items, notify=True):
        """Import multiple items. This is more efficient than calling
        import_item() multiple times. Items with errors are silently skipped
        and do not prevent good items to be imported."""
        if not uuid4.check(vault):
            raise ModelError('InvalidArgument', 'Illegal vault uuid')
        if vault not in self.vaults:
            raise ModelError('NotFound')
        self._log.debug('importing {} items', len(items))
        items = [ item for item in items if self.check_item(item)[0] ]
        self._log.debug('{} items are well formed', len(items))
        # Weed out items we already have.
        vector = dict(self.get_vector(vault))
        items = [ item for item in items
                  if item['origin']['seqnr']
                        > vector.get(item['origin']['node'], -1) ]
        self._log.debug('{} items are new', len(items))
        # If we are adding certs we need to add them first and re-calculate
        # trust before adding the other items.
        certs = [ item for item in items
                  if item['payload']['_type'] == 'Certificate'
                        and self.check_certificate(item)[0] ]
        if certs:
            # It is safe to import any certificate. Certificates require
            # a trusted signature before they are considered trusted.
            self.database.insert_many('items', certs)
            self._calculate_trust(vault)
            self._log.debug('imported {} certificates and recalculated trust', len(certs))
            # Some items may have become exposed by the certs. Find items
            # that were signed by the certs we just added.
            query = "$vault = ? AND $payload$_type = 'EncryptedItem'"
            query += ' AND (%s)' % ' OR '.join([ '$origin$node = ?' ] * len(certs))
            args = [ vault ]
            args += [ cert['payload']['node'] for cert in certs ]
            certitems = self.database.findall('items', query, args)
            self._log.debug('{} items are possibly touched by these certs', len(certitems))
        else:
            certitems = []
        # Now see which items are valid under the possibly wider set of
        # certificates and add them
        encitems = [ item for item in items
                     if item['payload']['_type'] == 'EncryptedItem'
                            and self.check_encrypted_item(item)[0] ]
        self.database.insert_many('items', encitems)
        self._log.debug('imported {} encrypted items', len(encitems))
        # Update version and history caches (if the vault is unlocked)
        if not self.vault_is_locked(vault):
            versions = []
            for item in itertools.chain(encitems, certitems):
                if not self._verify_item(vault, item) or \
                        not self._decrypt_item(vault, item) or \
                        not self.check_decrypted_item(item)[0] or \
                        not self.check_version(item)[0]:
                    continue
                versions.append(item)
            self._update_version_cache(versions, notify=notify)
        return len(certs) + len(encitems)

########NEW FILE########
__FILENAME__ = passwords
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import math
import os.path

from bluepass import util
from bluepass.crypto import CryptoProvider
from bluepass.factory import instance

__all__ = ('PasswordGenerator',)


class PasswordGenerator(object):
    """Password generator.
    
    This generator supports two password formats:

      * "random"

        The password is generated as a fixed number of characters randomly
        taken from a set of characters. The set of characters can be specified
        using regular expression style character ranges e.g. "[a-z0-9_]".

        This is the method used by default for generating individual passwords.

     * "diceware"

        The password is generated according to the "Diceware(tm)" method. See:
        http://world.std.com/~reinhold/diceware.html for more information.
        Diceware passphrases provide rememberable and extremely good
        passphrases.
        
        This method is used by default for vault passwords.
    """

    def __init__(self):
        """Create a new PasswordGenerator."""
        self.crypto = instance(CryptoProvider)
        self._load_wordlist()

    def _expand_alphabet(self, alphabet):
        """Expand all regular expression style character ranges
        (e.g. "[a-z0-9]") in the string `alphabet`."""
        s_start, s_set, s_try_start_range, s_end_range = range(4)
        result = []
        startchar = endchar = None
        state = s_start
        for ch in alphabet:
            if state == s_start:
                if ch == '[':
                    state = s_set
                else:
                    result.append(ch)
            elif state == s_set:
                if ch == ']':
                    state = s_start
                else:
                    startchar = ch
                    state = s_try_start_range
            elif state == s_try_start_range:
                if ch == '-':
                    state = s_end_range
                elif ch == ']':
                    result.append(startchar)
                    state = s_start
                else:
                    state = s_set
                    result.append(startchar)
            elif state == s_end_range:
                if ch == ']':
                    result.append(startchar)
                    result.append('-')
                    state = s_start
                else:
                    endchar = ch
                    for nr in range(ord(startchar), ord(endchar)+1):
                        result.append(chr(nr))
                    state = s_set
        if state != s_start:
            raise ValueError('Illegal alphabet specification')
        return result

    def _load_wordlist(self):
        """Load the Diceware wordlist."""
        fin = open(util.asset('diceware', 'wordlist.asc'))
        wordlist = []
        for line in fin:
            if line[:5].isdigit() and line[5:6] == '\t':
                key, value = line.split()
                wordlist.append(value)
        fin.close()
        self.wordlist = wordlist

    def generate_random(self, size, alphabet=None):
        """Generate a random password, consisting of `size` characters
        from the alphabet `alphabet`.
        """
        if alphabet:
            alphabet = self._expand_alphabet(alphabet)
        password = self.crypto.random(size, alphabet)
        return password

    def strength_random(self, size, alphabet=None):
        """Return the strength of a random password."""
        if alphabet:
            alphabet = self._expand_alphabet(alphabet)
            nchars = len(alphabet)
        else:
            nchars = 255
        strength = int(math.log(nchars ** size, 2))
        return strength

    def generate_diceware(self, words):
        """Generate a Diceware passwords of `words` words."""
        password = self.crypto.random(words, self.wordlist, ' ')
        return password

    def strength_diceware(self, words):
        """Return the strength of a Diceware password."""
        strength = int(math.log(6.0 ** (5*words), 2))
        return strength

    def generate(self, method, *args, **kwargs):
        """Generate a password."""
        if method == 'random':
            return self.generate_random(*args, **kwargs)
        elif method == 'diceware':
            return self.generate_diceware(*args, **kwargs)
        else:
            raise ValueError('Unknown method: %s' % method)

    def strength(self, method, *args, **kwargs):
        if method == 'random':
            return self.strength_random(*args, **kwargs)
        elif method == 'diceware':
            return self.strength_diceware(*args, **kwargs)
        else:
            raise ValueError('Unknown method: %s' % method)

########NEW FILE########
__FILENAME__ = misc
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import os
from subprocess import Popen, PIPE


def get_machine_info():
    """Return a tuple (hostname, os, arch, cores, cpu_speed, memory)."""
    osname, hostname, dummy, dummy, arch = os.uname()
    cores = 0
    process = Popen(['sysctl', 'hw.availcpu'], stdout=PIPE)
    stdout, stderr = process.communicate()
    status = process.poll()
    if status:
        cores = 1
    else:
        cores = int(stdout.split()[-1])
    process = Popen(['sysctl', 'hw.cpufrequency_max'], stdout=PIPE)
    stdout, stderr = process.communicate()
    status = process.poll()
    if status:
        cpu_speed = 0
    else:
        cpu_speed = int(stdout.split()[-1]) / 1000000
    process = Popen(['sysctl', 'hw.memsize'], stdout=PIPE)
    stdout, stderr = process.communicate()
    status = process.poll()
    if status:
        memory = 0
    else:
        memory = int(stdout.split()[-1]) / 1000000
    return (hostname, osname, arch, cores, cpu_speed, memory)

########NEW FILE########
__FILENAME__ = keyring
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from bluepass.keyring import Keyring


class DummyKeyring(Keyring):
    """A dummy key ring for platforms where we don't have native keyring integration."""

    def isavailable(self):
        return False

########NEW FILE########
__FILENAME__ = zeroconf
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from bluepass.zeroconf import Zeroconf

class DummyZeroconf(Zeroconf):
    """A dummy Zeroconf provider for platforms where we don't have a
    Zeroconf stack available. Note that on such platforms LAN sync will
    not work."""

    def isavailable(self):
        return False

########NEW FILE########
__FILENAME__ = avahi
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import socket
import logging

import gruvi
from gruvi import txdbus, compat
from gruvi.dbus import DBusClient, DBusError
from bluepass.locator import ZeroconfLocationSource, LocationError

# We do not import "avahi" because it depends on python-dbus which is
# a dependency I do not want to introduce. So redefine these here:

DBUS_NAME = 'org.freedesktop.Avahi'
PATH_SERVER = '/'
IFACE_SERVER = 'org.freedesktop.Avahi.Server'
IFACE_SERVICE_BROWSER = 'org.freedesktop.Avahi.ServiceBrowser'
IFACE_SERVICE_RESOLVER = 'org.freedesktop.Avahi.ServiceResolver'
IFACE_ENTRY_GROUP = 'org.freedesktop.Avahi.EntryGroup'

IFACE_UNSPEC = -1
PROTO_INET = 0
PROTO_INET6 = 1
SERVER_RUNNING = 2


def encode_txt(txt):
    """Encode dictionary of TXT records to the format expected by Avahi."""
    result = []
    for name,value in txt.items():
        item = '{}={}'.format(name, value)
        item = list(bytearray(item.encode('utf8')))
        result.append(item)
    return result

def decode_txt(txt):
    """Decode a list of TXT records that we get from Avahi into a dict."""
    result = {}
    for item in txt:
        item = bytearray(item).decode('utf8')
        name, value = item.split('=')
        result[name] = value
    return result


def signal_handler(interface=None):
    """Annotate a method as a D_BUS signal handler."""
    def _decorate(func):
        func.signal_handler = True
        func.member = func.__name__
        func.interface = interface
        return func
    return _decorate


class DBusHandler(object):
    """DBus message handler."""

    def __init__(self):
        self.signal_handlers = []
        self.local = gruvi.local()
        self._init_handlers()

    def _init_handlers(self):
        for name in vars(self.__class__):
            handler = getattr(self, name)
            if getattr(handler, 'signal_handler', False):
                self.signal_handlers.append(handler)

    @property
    def protocol(self):
        return self.local.protocol

    def __call__(self, message, protocol, transport):
        if not isinstance(message, txdbus.SignalMessage):
            return
        for handler in self.signal_handlers:
            if handler.member != message.member:
                continue
            if handler.interface and message.interface != handler.interface:
                continue
            break
        else:
            return
        self.local.protocol = protocol
        try:
            handler(*message.body)
        finally:
            del self.local.protocol


class AvahiHandler(DBusHandler):
    """DBusHandler that responds to Avahi signals."""

    def __init__(self, callback):
        """Constructor. The callback is notified for all events."""
        super(AvahiHandler, self).__init__()
        self._resolvers = {}
        self._callback = callback
        self.logger = logging.getLogger(__name__)

    def _call_avahi(self, path, method, interface, signature=None, args=None):
        """Call into Avahi."""
        try:
            reply = self.protocol.call_method(DBUS_NAME, path, interface, method,
                                              signature=signature, args=args)
        except DBusError as e:
            self.logger.error('D-BUS error for method %s: %s', method, str(e))
        else:
            return reply

    @signal_handler(interface=IFACE_SERVICE_BROWSER)
    def ItemNew(self, *args):
        resolver = self._call_avahi(PATH_SERVER, 'ServiceResolverNew', IFACE_SERVER,
                                   'iisssiu', args[:5] + (PROTO_INET, 0))
        if not resolver:
            return
        key = '.'.join(map(str, args[:5]))
        self._resolvers[key] = resolver

    @signal_handler(interface=IFACE_SERVICE_BROWSER)
    def ItemRemove(self, *args):
        key = '.'.join(map(str, args[:5]))
        if key not in self._resolvers:
            self.logger.error('ItemRemove signal for unknown service: %s', key)
            return
        resolver = self._resolvers.pop(key)
        self._call_avahi(resolver, 'Free', IFACE_SERVICE_RESOLVER)
        self._callback('ItemRemove', *args)

    @signal_handler(interface=IFACE_SERVICE_RESOLVER)
    def Found(self, *args):
        self._callback('Found', *args)


class AvahiLocationSource(ZeroconfLocationSource):
    """Avahi Zeroconf location source.
    
    This location source provides loation services for a local network
    using DNS-SD. This source is for freedesktop like platforms and uses
    Avahi via its D-BUS interface.

    DNS-SD is used in the following way for vault discovery:

    1. The Bluepass service is registered as a PTR record under:

        _bluepass._tcp.local

    2. The previous PTR record will resolve to a list of SRV and TXT records.
       Instead of using the vault UUID as the service name, this uses the
       vault's node UUID because a vault can be replicated over many Bluepass
       instances and is therefore not unique.

        <node_uuid>._bluepass._tcp.local

       The TXT records specify a set of properteis, with at least a
       "vault" property containing the UUID of the vault. A "visible" property
       may also be set, indicating whether this node currently accepts pairing
       requests.
    """

    name = 'avahi-zeroconf'

    def __init__(self):
        """Constructor."""
        super(AvahiLocationSource, self).__init__()
        handler = AvahiHandler(self._avahi_event)
        self.client = DBusClient(handler)
        self.client.connect('system')
        self.logger = logging.getLogger(__name__)
        self.callbacks = []
        self.neighbors = {}
        self.addresses = {}
        self._browser = None
        self._entry_groups = {}

    def _call_avahi(self, path, method, interface, signature=None, args=None):
        """INTERNAL: call into Avahi."""
        try:
            reply = self.client.call_method(DBUS_NAME, path, interface, method,
                                            signature=signature, args=args)
        except DBusError as e:
            msg = 'Encounted a D-BUS error for method %s: %s'
            self.logger.error(msg, method, str(e))
            raise LocationError(msg % (method, str(e)))
        return reply

    def _run_callbacks(self, event, *args):
        """Run all registered callbacks."""
        for callback in self.callbacks:
            callback(event, *args)

    def _proto_to_family(self, proto):
        """Convert an Avahi protocol ID to an address family."""
        if proto == PROTO_INET:
            family = socket.AF_INET
        elif proto == PROTO_INET6:
            family = socket.AF_INET6
        else:
            family = -1
        return family

    def _avahi_event(self, event, *args):
        """Single unified callback for AvahiHandler."""
        logger = self.logger
        if event == 'Found':
            node = args[2]
            neighbor = { 'node': node, 'source': 'LAN' }
            txt = decode_txt(args[9])
            properties = neighbor['properties'] = {}
            for name,value in txt.items():
                if name in ('nodename', 'vault', 'vaultname'):
                    neighbor[name] = value
                else:
                    properties[name] = value
            for name in ('nodename', 'vault', 'vaultname'):
                if not neighbor.get(name):
                    logger.error('node %s lacks TXT field "%s"', node, name)
                    return
            event = 'NeighborUpdated' if node in self.neighbors else 'NeighborDiscovered'
            family = self._proto_to_family(args[6])
            if family != socket.AF_INET:
                return
            addr = { 'family': family, 'host': args[5], 'addr': (args[7], args[8]) }
            addr['id'] = '%s:%s:%s' % (family, args[7], args[8])
            # There can be multiple addresses per node for different
            # interfaces and/or address families. We keep track of this
            # so we distinghuish address changes from new addresses that
            # become available.
            key = '%d:%d' % (args[0], args[1])
            if node not in self.addresses:
                self.addresses[node] = {}
            self.addresses[node][key] = addr
            neighbor['addresses'] = list(self.addresses[node].values())
            self.neighbors[node] = neighbor
            self._run_callbacks(event, neighbor)
        elif event == 'ItemRemove':
            node = args[2]
            key = '%d:%d' % (args[0], args[1])
            if node not in self.neighbors or key not in self.addresses[node]:
                logger.error('ItemRemove event for unknown node "%s"', node)
                return
            del self.addresses[node][key]
            neighbor = self.neighbors[node]
            neighbor['addresses'] = list(self.addresses[node].values())
            if not neighbor['addresses']:
                del self.addresses[node]
                del self.neighbors[node]
            event = 'NeighbordUpdated' if node in self.neighbors else 'NeighborDisappeared'
            self._run_callbacks(event, neighbor)

    def isavailable(self):
        """Return wheter Avahi is available or not."""
        try:
            version = self._call_avahi(PATH_SERVER, 'GetVersionString', IFACE_SERVER)
        except LocationError:
            return False
        self.logger.info('Found Avahi version %s', version)
        state = self._call_avahi(PATH_SERVER, 'GetState', IFACE_SERVER)
        if state != SERVER_RUNNING:
            self.logger.error('Avahi not in the RUNNING state (instead: %s)', state)
            return False
        return True

    def add_callback(self, callback):
        """Add a callback for this location source. When the first callback is
        added, we start browsing the zeroconf domain."""
        self.callbacks.append(callback)
        if self._browser is not None:
            return
        args = (IFACE_UNSPEC, PROTO_INET, self.service, self.domain, 0)
        self._browser = self._call_avahi(PATH_SERVER, 'ServiceBrowserNew',
                                 IFACE_SERVER, 'iissu', args)

    def register(self, node, nodename, vault, vaultname, address, properties=None):
        """Register a service instance."""
        group = self._call_avahi(PATH_SERVER, 'EntryGroupNew', IFACE_SERVER)
        host = self._call_avahi(PATH_SERVER, 'GetHostNameFqdn', IFACE_SERVER)
        port = address[1]
        properties = properties.copy() if properties else {}
        properties['nodename'] = nodename
        properties['vault'] = vault
        properties['vaultname'] = vaultname
        args = (IFACE_UNSPEC, PROTO_INET, 0, node, self.service, self.domain,
                host, port, encode_txt(properties))
        self._call_avahi(group, 'AddService', IFACE_ENTRY_GROUP, 'iiussssqaay', args)
        self._call_avahi(group, 'Commit', IFACE_ENTRY_GROUP)
        self._entry_groups[node] = (group, properties)

    def set_property(self, node, name, value):
        """Update a property."""
        if node not in self._entry_groups:
            raise RuntimeError('Node is not registered yet')
        group, properties = self._entry_groups[node]
        properties[name] = value
        args = (IFACE_UNSPEC, PROTO_INET, 0, node, self.service, self.domain,
                encode_txt(properties))
        self._call_avahi(group, 'UpdateServiceTxt', IFACE_ENTRY_GROUP, 'iiusssaay', args)

    def unregister(self, node):
        """Release our registration."""
        if node not in self._entry_groups:
            raise RuntimeError('Node is not registered yet')
        group, properties = self._entry_groups[node]
        self._call_avahi(group, 'Free', IFACE_ENTRY_GROUP)
        del self._entry_groups[node]

########NEW FILE########
__FILENAME__ = secrets
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import time
import tdbus
import logging

from bluepass.keyring import Keyring, KeyringError
from bluepass.crypto import CryptoProvider, CryptoError, dhparams


CONN_SERVICE = 'org.freedesktop.secrets'
PATH_SERVICE = '/org/freedesktop/secrets'
PATH_LOGIN_COLLECTION = '/org/freedesktop/secrets/collection/login'
IFACE_SERVICE = 'org.freedesktop.Secret.Service'
IFACE_COLLECTION = 'org.freedesktop.Secret.Collection'
IFACE_ITEM = 'org.freedesktop.Secret.Item'
IFACE_SESSION = 'org.freedesktop.Secret.Session'
IFACE_PROPS = 'org.freedesktop.DBus.Properties'


class SecretsKeyring(Keyring):
    """A Keyring interface into the freedesktop "secrets" service.

    This interface is available on Freedesktop platforms (GNOME, KDE).
    """

    def __init__(self, connection):
        """Create a new keyring. Requires a python-tdbus dispatcher as an argument."""
        self.connection = connection
        self.logger = logging.getLogger('bluepass.platform.freedesktop.keyring')
        self.crypto = CryptoProvider()

    def _call_svc(self, path, method, interface, format=None, args=None):
        """INTERNAL: call into the secrets service."""
        try:
            result = self.connection.call_method(path, method, interface=interface,
                            format=format, args=args, destination=CONN_SERVICE)
        except tdbus.Error as e:
            raise KeyringError('D-BUS error for method "%s": %s' % (method, str(e)))
        return result

    def isavailable(self):
        """Return whether or not we can store a key. This requires the secrets
        service to be available and the login keyring to be unlocked."""
        try:
            reply = self._call_svc(PATH_LOGIN_COLLECTION, 'Get', IFACE_PROPS,
                                   'ss', (IFACE_COLLECTION, 'Locked'))
        except KeyringError:
            self.logger.debug('could not access secrets service')
            return False
        value = reply.get_args()[0]
        if value[0] != 'b':
            raise KeyringError('expecting type "b" for "Locked" property')
        self.logger.debug('login keyring is locked: %s', value[1])
        return not value[1]

    def _open_session(self):
        """INTERNAL: open a session."""
        algo = 'dh-ietf1024-sha256-aes128-cbc-pkcs7'
        params = dhparams['ietf1024']
        keypair = self.crypto.dh_genkey(params)
        reply = self._call_svc(PATH_SERVICE, 'OpenSession', IFACE_SERVICE,
                               'sv', (algo, ('ay', keypair[1])))
        if reply.get_signature() != 'vo':
            raise KeyringError('expecting "vo" reply signature for "OpenSession"')
        output, path = reply.get_args()
        if output[0] != 'ay':
            raise KeyringError('expecting "ay" type for output argument of "OpenSession"')
        pubkey = output[1]
        if not self.crypto.dh_checkkey(params, pubkey):
            raise KeyringError('insecure public key returned by "OpenSession"')
        secret = self.crypto.dh_compute(params, keypair[0], pubkey)
        symkey = self.crypto.hkdf(secret, None, '', 16, 'sha256')
        return path, symkey

    def store(self, key, value):
        """Store a secret in the keyring."""
        session, symkey = self._open_session()
        try:
            attrib = { 'application': 'bluepass', 'bluepass-key-id': key }
            props = { 'org.freedesktop.Secret.Item.Label': ('s', 'Bluepass Key: %s' % key),
                      'org.freedesktop.Secret.Item.Attributes': ('a{ss}', attrib) }
            iv = self.crypto.random(16)
            encrypted = self.crypto.aes_encrypt(value, symkey, iv, 'cbc-pkcs7')
            secret = (session, iv, encrypted, 'text/plain')
            reply = self._call_svc(PATH_LOGIN_COLLECTION, 'CreateItem', IFACE_COLLECTION,
                                   'a{sv}(oayays)b', (props, secret, True))
            item, prompt = reply.get_args()
            if item == '/':
                raise KeyringError('not expecting a prompt for "CreateItem"')
            return item
        finally:
            self._call_svc(session, 'Close', IFACE_SESSION)

    def retrieve(self, key):
        """Retrieve a secret from the keyring."""
        session, symkey = self._open_session()
        try:
            attrib = { 'application': 'bluepass', 'bluepass-key-id': key }
            reply = self._call_svc(PATH_LOGIN_COLLECTION, 'SearchItems', IFACE_COLLECTION,
                                   'a{ss}', (attrib,))
            paths = reply.get_args()[0]
            if len(paths) > 1:
                self.logger.error('SearchItems returned %d entries for key "%s"' % (len(paths), key))
                return
            elif len(paths) == 0:
                return
            item = paths[0]
            reply = self._call_svc(item, 'GetSecret', IFACE_ITEM, 'o', (session,))
            secret = reply.get_args()[0]
            decrypted = self.crypto.aes_decrypt(secret[2], symkey, secret[1], 'cbc-pkcs7')
            return decrypted
        finally:
            self._call_svc(session, 'Close', IFACE_SESSION)

########NEW FILE########
__FILENAME__ = misc
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import os

def get_machine_info():
    """Return a tuple (hostname, os, arch, cores, cpu_speed, memory)."""
    osname, hostname, dummy, dummy, arch = os.uname()
    cores = 0
    fin = file('/proc/cpuinfo')
    for line in fin:
        line = line.strip()
        if not line:
            continue
        label, value = line.split(':')
        label = label.strip(); value = value.strip()
        if label == 'processor':
            cores += 1
    fin.close()
    try:
        fin = file('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq')
        cpu_speed = int(fin.readline().strip()) / 1000
        fin.close()
    except IOError:
        cpu_speed = 0
    memory = 0
    fin = file('/proc/meminfo')
    for line in fin:
        line = line.strip()
        if not line:
            continue
        label, value = line.split(':')
        label = label.strip(); value = value.strip()
        if label == 'MemTotal':
            value = value.rstrip('kB')
            memory = int(value) / 1000
            break
    return (hostname, osname, arch, cores, cpu_speed, memory)

########NEW FILE########
__FILENAME__ = misc
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import os
import sys
import os.path
import stat
import pwd
import fcntl
import errno

__all__ = ['get_username', 'get_homedir', 'get_appdir', 'get_sockdir', 
           'LockError', 'lock_file', 'unlock_file']


def get_username(uid=None):
    """Return the current user's name."""
    if uid is None:
        try:
            return os.environ['USER']
        except KeyError:
            uid = os.getuid()
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)

def get_homedir(uid=None):
    """Return the user's home directory."""
    if uid is None:
        try:
            return os.environ['HOME']
        except KeyError:
            uid = os.getuid()
    try:
        return pwd.getpwuid(uid).pw_dir
    except KeyError:
        return None

def _try_stat(fname):
    """Stat a file name but return None in case of error."""
    try:
        return os.stat(fname)
    except OSError:
        pass

def get_appdir(appname):
    """Return a directory under $HOME to store application data."""
    candidates = []
    home = get_homedir()
    xdgdata = os.path.join(home, '.local', 'share')
    st = _try_stat(xdgdata)
    if st is not None and stat.S_ISDIR(st.st_mode):
        candidates.append(os.path.join(xdgdata, appname))
    candidates.append(os.path.join(home, '.%s' % appname))
    # See if it already exists
    for appdir in candidates:
        st = _try_stat(appdir)
        if st is not None and stat.S_ISDIR(st.st_mode):
            return appdir
    # If not create it. Just fail if someone created a non-directory
    # file system object at our desired location.
    appdir = candidates[0]
    os.mkdir(appdir)
    return appdir


def get_sockdir():
    """Return the per-user socket directory."""
    sockdir = '/var/run/user/{0}'.format(os.getuid())
    try:
        st = os.stat(sockdir)
    except OSError:
        st = None
    if st and stat.S_ISDIR(st.st_mode):
        return sockdir
    return get_appdir('bluepass')


class LockError(Exception):
    pass

def lock_file(lockname):
    """Create a lock file `lockname`."""
    try:
        fd = os.open(lockname, os.O_RDWR|os.O_CREAT, 0o644)
        try:
            fcntl.lockf(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except IOError as e:
            if e.errno not in (errno.EACCES, errno.EAGAIN):
                raise
            msg = 'lockf() failed to lock %s: %s' % (lockname, os.strerror(e.errno))
            err = LockError(msg)
            line = os.read(fd, 4096).decode('ascii')
            lockinfo = line.rstrip().split(':')
            if len(lockinfo) == 3:
                err.lock_pid = int(lockinfo[0])
                err.lock_uid = int(lockinfo[1])
                err.lock_cmd = lockinfo[2]
            raise err
        os.ftruncate(fd, 0)
        cmd = os.path.basename(sys.argv[0])
        os.write(fd, ('%d:%d:%s\n' % (os.getpid(), os.getuid(), cmd)).encode('ascii'))
    except (OSError, IOError) as e:
        raise LockError('%s: %s' % (lockname, os.strerror(e.errno)))
    lock = (fd, lockname)
    return lock

def unlock_file(lock):
    """Unlock a file."""
    fd, lockname = lock
    try:
        fcntl.lockf(fd, fcntl.LOCK_UN)
        os.close(fd)
        os.unlink(lockname)
    except (OSError, IOError):
        pass

########NEW FILE########
__FILENAME__ = socket
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import errno
import socket


def socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
    """Emulate the Unix socketpair() function on Windows."""
    # We create a connected TCP socket. Note the trick with setblocking(0)
    # that prevents us from having to create a thread.
    lsock = socket.socket(family, type, proto)
    lsock.bind(('localhost', 0))
    lsock.listen(1)
    addr, port = lsock.getsockname()
    csock = socket.socket(family, type, proto)
    csock.setblocking(0)
    try:
        csock.connect((addr, port))
    except socket.error, e:
        if e.errno != errno.WSAEWOULDBLOCK:
            raise
    ssock, addr = lsock.accept()
    csock.setblocking(1)
    lsock.close()
    return (ssock, csock)

def is_interrupt(e):
    """Return whether the exception `e' is an EINTR error."""
    return e.errno == errno.EINTR

def is_woudblock(e):
    """Return whether the exception `e' is an EAGAIN error."""
    return e.errno == errno.WSAWOULDBLOCK

def is_eof(e):
    """Return whether the exception `e' is an EPIPE error."""
    return e.errno in (errno.EPIPE, errno.ECONNRESET)

########NEW FILE########
__FILENAME__ = socketapi
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import binascii

from bluepass import _version, util, json
from bluepass.factory import instance
from bluepass.error import StructuredError
from bluepass.crypto import CryptoProvider
from bluepass.model import Model
from bluepass.passwords import PasswordGenerator
from bluepass.locator import Locator
from bluepass.syncapi import SyncAPIPublisher, SyncAPIClient, SyncAPIError

import gruvi
from gruvi import jsonrpc
from gruvi.jsonrpc import *


class PairingError(StructuredError):
    """Pairing error."""


def method():
    """Decorate a method."""
    def decorate(method):
        method.method = True
        return method
    return decorate


class JsonRpcHandler(object):
    """JSON-RPC procotol handler."""

    def __init__(self):
        self.local = gruvi.local()

    @property
    def message(self):
        return self.local.message

    @property
    def protocol(self):
        return self.local.protocol

    @property
    def transport(self):
        return self.local.transport

    def send_response(self, result):
        response = jsonrpc.create_response(self.message, result)
        self.protocol.send_message(self.transport, response)
        self.local.response_sent = True

    def send_notification(self, name, *args):
        message = jsonrpc.create_notification(name, args)
        self.protocol.send_message(self.transport, message)

    def __call__(self, message, protocol, transport):
        method = message.get('method')
        if method is None:
            return
        handler = getattr(self, method, None)
        if handler is None or not getattr(handler, 'method', False):
            return
        args = message.get('params', ())
        self.local.message = message
        self.local.protocol = protocol
        self.local.transport = transport
        self.local.response_sent = False
        response = None
        try:
            result = handler(*args)
        except StructuredError as e:
            if not self.local.response_sent:
                response = jsonrpc.create_error(message, error=e.asdict())
        else:
            if not self.local.response_sent:
                response = jsonrpc.create_response(message, result)
        return response


class SocketAPIHandler(JsonRpcHandler):
    """A message bus handler that implements our socket API."""

    # NOTE: all methods run in separate fibers!

    def __init__(self):
        super(SocketAPIHandler, self).__init__()
        self.crypto = instance(CryptoProvider)
        self.pairdata = {}

    @method()
    def stop(self):
        from .backend import Backend
        instance(Backend).stop()

    # Version

    @method()
    def get_version_info(self):
        """Get version information.

        Returns a dictionary containing at least the key "version".
        """
        version_info = {'version': _version.__version__}
        return version_info

    # Model methods

    @method()
    def get_config(self):
        """Return the configuration object.

        The configuration object is a dictionary that can be used by frontends
        to store configuration data.
        """
        return instance(Model).get_config()

    @method()
    def update_config(self, config):
        """Update the configuration object."""
        return instance(Model).update_config(config)

    @method()
    def create_vault(self, name, password, async=False):
        """Create a new vault.

        The vault will have the name *name*. The vault's private keys will be
        encrypted with *password*.

        The *async* parameter specifies if the vault creation needs to be
        asynchronous. If it is set to False, then the vault is created
        synchronously and it is returned as a dictionary. If async is set to
        True, then this will return the UUID of the vault as a stirng. Once the
        vault has been created, the ``VaultCreationComplete`` signal will be
        raised. The signal has three arguments: the UUID, a status code, and a
        detailed message.

        Creating a vault requires the backend to generate 3 RSA keys. This can
        be a time consuming process. Therefore it is recommended to use
        asynchronous vault creation in user interfaces.
        """
        # Vault creation is time consuming because 3 RSA keys have
        # to be generated. Therefore an async variant is provided.
        model = instance(Model)
        if not async:
            return model.create_vault(name, password)
        uuid = self.crypto.randuuid()
        self.send_response(uuid)
        try:
            vault = model.create_vault(name, password, uuid)
        except StructuredError as e:
            status = e[0]
            detail = e.asdict()
        except Exception:
            e = StructuredError.uncaught_exception()
            status = e[0]
            detail = e.asdict()
        else:
            status = 'OK'
            detail = vault
        self.send_notification('VaultCreationComplete', uuid, status, detail)

    @method()
    def get_vault(self, uuid):
        """Return the vault with UUID *uuid*.

        The result value is a dictionary containing the vault metadata, or
        ``None`` if the vault was not found.
        """
        return instance(Model).get_vault(uuid)

    @method()
    def get_vaults(self):
        """Return a list of all vaults.

        The result value is a list if dictionaries containing vault metadata.
        """
        return instance(Model).get_vaults()

    @method()
    def update_vault(self, vault):
        """Update a vault's metadata.

        The *vault* parameter must be a dictionary. The recommended way to use
        this function is to use :meth:`get_vault` to retrieve the metadata,
        make updates, make updates to it, and the use this method to save the
        updates.

        On success, nothing is returned. On error, an exception is raised.
        """
        return instance(Model).update_vault(uuid, vault)

    @method()
    def delete_vault(self, vault):
        """Delete a vault and all its items.

        The *vault* parameter must be a vault metadata dictionary returned by
        :meth:`get_vault`.
        """
        return instance(Model).delete_vault(vault)

    @method()
    def get_vault_statistics(self, uuid):
        """Return statistics about a vault.

        The return value is a dictionary.
        """
        return instance(Model).get_vault_statistics(uuid)

    @method()
    def unlock_vault(self, uuid, password):
        """Unlock a vault.

        The vault *uuid* is unlocked using *password*. This decrypts the
        private keys that are stored in the database and stored them in
        memory.

        On error, an exception is raised. It is not an error to unlock a vault
        that is already unlocked.
        """
        return instance(Model).unlock_vault(uuid, password)

    @method()
    def lock_vault(self, uuid):
        """Lock a vault.

        This destroys the decrypted private keys and any other decrypted items
        that are cached.

        It is not an error to lock a vault that is already locked.
        """
        return instance(Model).lock_vault(uuid)

    @method()
    def vault_is_locked(self, uuid):
        """Return whether or not the vault *uuid* is locked."""
        return instance(Model).vault_is_locked(uuid)

    @method()
    def get_version(self, vault, uuid):
        """Return a version from a vault.

        The latest version identified by *uuid* is returned from *vault*.  The
        version is returned as a dictionary. If the version does not exist,
        ``None`` is returned.
        
        In Bluepass, vaults contain versions. Think of a version as an
        arbitrary object that is versioned and encrypted. A version has at
        least "id" and "_type" keys. The "id" will stay constant over the
        entire lifetime of the version. Newer versions supersede older
        versions. This method call returns the newest instance of the version.

        Versions are the unit of synchronization in our peer to peer
        replication protocol. They are also the unit of encryption. Both
        passwords are groups are stored as versions.
        """
        return instance(Model).get_version(vault, uuid)

    @method()
    def get_versions(self, vault):
        """Return the newest instances for all versions in a vault.

        The return value is a list of dictionaries.
        """
        return instance(Model).get_versions(vault)

    @method()
    def add_version(self, vault, version):
        """Add a new version to a vault.

        The *version* parameter must be a dictionary. The version is a new
        version and should not contain and "id" key yet.
        """
        return instance(Model).add_version(vault, version)

    @method()
    def update_version(self, vault, version):
        """Update an existing version.

        The *version* parameter should be a dictionary. It must have an "id"
        of a version that already exists. The version will become the latest
        version of the specific id.
        """
        return instance(Model).update_version(vault, version)

    @method()
    def delete_version(self, vault, version):
        """Delete a version from a vault.

        This create a special updated version of the record with a "deleted"
        flag set. By default, deleted versions do not show up in the output of
        :meth:`get_versions`.
        """
        return instance(Model).delete_version(vault, version)

    @method()
    def get_version_history(self, vault, uuid):
        """Get the history of a version.

        This returns a ordered list with the linear history all the way from
        the current newest instance of the version, back to the first version.
        """
        return instance(Model).get_version_history(vault, uuid)

    # Password methods

    @method()
    def generate_password(self, method, *args):
        """Generate a password.

        The *method* specifies the method. It can currently be "diceware" or
        "random". The "diceware" method takes one argument: an integer with the
        number of words to generate. The "random" method takes two arguments:
        th size in character, and an alphabest in the form of a regular
        expression character set (e.g. [a-zA-Z0-9]).
        """
        return instance(PasswordGenerator).generate(method, *args)

    @method()
    def password_strength(self, method, *args):
        """Return the strength of a password that was generated by
        :meth:`generate_password`.

        The return value is an integer indicating the entropy of the password
        in bits.
        """
        return instance(PasswordGenerator).strength(method, *args)

    # Locator methods

    @method()
    def locator_is_available(self):
        """Return whether or not the locator is available.

        There are platforms where we don't have a locator at the moment.
        """
        locator = instance(Locator)
        return len(locator.sources) > 0

    @method()
    def get_neighbors(self):
        """Return current neighbords on the network.

        The return value is a list of dictionaries.
        """
        return instance(Locator).get_neighbors()

    # Pairing methods

    @method()
    def set_allow_pairing(self, timeout):
        """Be visible on the network for *timeout* seconds.

        When visible, other instances of Bluepass will be able to find us, and
        initiate a pairing request. The pairing request will still have to be
        approved, and PIN codes needs to be exchanged.
        """
        publisher = instance(SyncAPIPublisher)
        publisher.set_allow_pairing(timeout)

    @method()
    def pair_neighbor_step1(self, node, source):
        """Start a new pairing process.

        A pairing process is started with node *node* residing in source
        *source*.

        The return value is a string containing a random cookie that identifies
        the current request.
        """
        locator = instance(Locator)
        neighbor = locator.get_neighbor(node, source)
        if neighbor is None:
            raise PairingError('NotFound', 'No such neighbor')
        visible = neighbor['properties'].get('visible')
        if not visible:
            raise PairingError('NotFound', 'Node not visible')
        vault = neighbor['vault']
        model = instance(Model)
        if model.get_vault(vault):
            raise PairingError('Exists', 'Vault already exists')
        # Don't keep the GUI blocked while we wait for remote approval.
        cookie = binascii.hexlify(self.crypto.random(16)).decode('ascii')
        self.send_response(cookie)
        name = util.gethostname()
        for addr in neighbor['addresses']:
            client = SyncAPIClient()
            addr = addr['addr']
            try:
                client.connect(addr)
            except SyncAPIError as e:
                continue  # try next address
            try:
                kxid = client.pair_step1(vault, name)
            except SyncAPIError as e:
                status = e.args[0]
                detail = e.asdict()
            else:
                status = 'OK'
                detail = {}
                self.pairdata[cookie] = (kxid, neighbor, addr)
            self.send_notification('PairNeighborStep1Completed', cookie, status, detail)
            client.close()
            break

    @method()
    def pair_neighbor_step2(self, cookie, pin, name, password):
        """Complete a pairing process.

        The *cookie* argument are returned by :meth:`pair_neighbor_step1`. The
        *pin* argument is the PIN code that the remote Bluepass instance showed
        to its user. The *name* and *password* arguments specify the name and
        password of the paired vault that is created in the local instance.

        Paired vaults will automatically be kept up to date. Changes made in a
        paired vault in once Bluepass instance will automatically be synced to
        other instances by the Bluepass backend.

        To get notified of new versions that were added, listen for the
        ``VersionsAdded`` signal.
        """
        if cookie not in self.pairdata:
            raise PairingError('NotFound', 'No such key exchange ID')
        kxid, neighbor, addr = self.pairdata.pop(cookie)
        # Again don't keep the GUI blocked while we pair and do a full sync
        self.send_response(None)
        model = instance(Model)
        vault = model.create_vault(name, password, neighbor['vault'],
                                   notify=False)
        certinfo = { 'node': vault['node'], 'name': util.gethostname() }
        keys = certinfo['keys'] = {}
        for key in vault['keys']:
            keys[key] = { 'key': vault['keys'][key]['public'],
                          'keytype': vault['keys'][key]['keytype'] }
        client = SyncAPIClient()
        client.connect(addr)
        try:
            peercert = client.pair_step2(vault['id'], kxid, pin, certinfo)
        except SyncAPIError as e:
            status = e.args[0]
            detail = e.asdict()
            model.delete_vault(vault)
        else:
            status = 'OK'
            detail = {}
            model.add_certificate(vault['id'], peercert)
            client.sync(vault['id'], model, notify=False)
            model.raise_event('VaultAdded', vault)
        self.send_notification('PairNeighborStep2Completed', cookie, status,
                               detail)
        client.close()


def jsonrpc_type(obj):
    """Return a string identify a JSON-RPC message."""
    if obj.get('method') and obj.get('id'):
        return 'request'
    elif obj.get('method'):
        return 'notification'
    elif obj.get('error'):
        return 'error'
    elif obj.get('result'):
        return 'response'
    else:
        return 'unknown'


class SocketAPIServer(JsonRpcServer):

    def __init__(self):
        super(SocketAPIServer, self).__init__(SocketAPIHandler())
        self._tracefile = None
        instance(Model).add_callback(self._forward_events)
        instance(Locator).add_callback(self._forward_events)
        instance(SyncAPIPublisher).add_callback(self._forward_events)

    def _forward_events(self, event, *args):
        # Forward the event over the message bus.
        for client in self.clients:
            message = jsonrpc.create_notification(event, args)
            self.send_message(client, message)

    def _set_tracefile(self, tracefile):
        self._tracefile = tracefile

    def _log_request(self, message):
        if not self._tracefile:
            return
        self._tracefile.write('/* <= incoming {0}, version {1} */\n'.format
                        (jsonrpc_type(message), message.get('jsonrpc', '1.0')))
        self._tracefile.write(json.dumps_pretty(message))
        self._tracefile.write('\n\n')

    def _log_response(self, message):
        if not self._tracefile:
            return
        self._tracefile.write('/* => outgoing {0}, version {1} */\n'.format
                        (jsonrpc_type(message), message.get('jsonrpc', '1.0')))
        self._tracefile.write(json.dumps_pretty(message))
        self._tracefile.write('\n\n')

########NEW FILE########
__FILENAME__ = ssl
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import ssl
import socket

from bluepass.ext import _sslex


class SSLSocket(ssl.SSLSocket):
    """An extended version of SSLSocket.
    
    This backports two features from Python 3.x to 2.x that we depend on:

    * Retrieving the channel bindings (get_channel_bindings()).
    * Setting the Diffie-Hellman group parameters (via the "dhparams"
       and dh_single_use keyword arguments to the constructor).

    This whole thing is a horrible hack. Luckly we don't need it on Python 3.
    """

    def __init__(self, *args, **kwargs):
        """Constructor."""
        # Below an even more disgusting hack.. Python's _ssl.sslwrap() requires
        # keyfile and certfile to be set for server sockets. However in case we
        # use anonymous Diffie-Hellman, we don't need these. The "solution" is
        # to force the socket to be a client socket for the purpose of the
        # constructor, and then later patch it to be a server socket
        # (_sslex._set_accept_state()). Fortunately this is solved in Python
        # 3.x.
        self._sslex_dhparams = kwargs.pop('dhparams', '')
        self._sslex_dh_single_use = kwargs.pop('dh_single_use', False)
        self._sslex_server_side = kwargs.pop('server_side', False)
        self._sslex_ciphers = kwargs.pop('ciphers', None)
        super(SSLSocket, self).__init__(*args, **kwargs)

    def do_handshake(self):
        """Set DH parameters prior to handshake."""
        if self._sslex_dhparams:
            _sslex.set_dh_params(self._sslobj, self._sslex_dhparams,
                                 self._sslex_dh_single_use)
            self._sslex_dhparms = None
        if self._sslex_ciphers:
            _sslex.set_ciphers(self._sslobj, self._sslex_ciphers)
            self._sslex_ciphers = None
        # Now make it a server socket again if we need to..
        if self._sslex_server_side:
            _sslex._set_accept_state(self._sslobj)
            self._sslex_server_side = None
        super(SSLSocket, self).do_handshake()

    def get_channel_binding(self, typ='tls-unique'):
        """Return the channel binding for this SSL socket."""
        if typ != 'tls-unique':
            raise ValueError('Unsupported channel binding: %s' % typ)
        if self._sslobj is None:
            return
        return _sslex.get_channel_binding(self._sslobj)


def patch_ssl_wrap_socket():
    """Monkey patch ssl.wrap_socket to use our extended SSL socket."""
    from gruvi import compat
    if compat.PY3:
        return
    import ssl
    def wrap_socket(sock, **kwargs):
        return SSLSocket(sock, **kwargs)
    ssl.wrap_socket = wrap_socket

########NEW FILE########
__FILENAME__ = syncapi
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import os
import re
import sys
import time
import logging
import binascii
import socket
import ssl

try:
    import httplib as http
    from urlparse import parse_qs
except ImportError:
    from http import client as http
    from urllib.parse import parse_qs

import gruvi
from gruvi import Fiber, compat
from gruvi.http import HttpServer, HttpClient

from bluepass import _version, json, base64, uuid4, util, logging
from bluepass.error import StructuredError
from bluepass.factory import instance, singleton
from bluepass.crypto import CryptoProvider, CryptoError, dhparams
from bluepass.model import Model
from bluepass.locator import Locator

__all__ = ('SyncAPIError', 'SyncAPIClient', 'SyncAPIApplication', 'SyncAPIServer')


def init_syncapi_ssl(pemdir):
    """Perform once-off SSL initialization for the syncapi."""
    init_pem_directory(pemdir)
    SyncAPIClient.pem_directory = pemdir
    SyncAPIServer.pem_directory = pemdir
    from bluepass.ssl import patch_ssl_wrap_socket
    patch_ssl_wrap_socket()

def init_pem_directory(pemdir):
    fname = os.path.join(pemdir, 'dhparams.pem')
    st = util.try_stat(fname)
    if st is not None:
        return
    with open(fname, 'w') as fout:
        fout.write('-----BEGIN DH PARAMETERS-----\n')
        fout.write(dhparams['skip2048'])
        fout.write('-----END DH PARAMETERS-----\n')


class SyncAPIError(StructuredError):
    """Sync API error."""


def adjust_pin(pin, n):
    """Increment the numerical string `pin` by `n`, wrapping it if needed."""
    mask = int('9' * len(pin)) + 1
    numpin = int(pin) + n
    numpin = numpin % mask
    fmt = '%%0%dd' % len(pin)
    strpin = fmt % numpin
    return strpin


_re_optval = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*' \
                        r'=\s*([^"]*|"([^\\"]|\\.)*")$')

def parse_option_header(header, sep1=' ', sep2=' '):
    """Parse an option header."""
    options = {}
    p1 = header.find(sep1)
    if p1 == -1:
        return header, options
    head = header[:p1].strip()
    optvals = header[p1+1:].split(sep2)
    for optval in optvals:
        optval = optval.strip()
        mobj = _re_optval.match(optval)
        if mobj is None:
            raise ValueError('Illegal option string')
        key = mobj.group(1)
        value = mobj.group(2)
        if value.startswith('"'):
            value = value[1:-1]
        options[key] = value
    return head, options

def create_option_header(value, sep1=' ', sep2=' ', **kwargs):
    """Create an option header."""
    result = [value]
    for key,value in kwargs.items():
        result.append(sep1)
        result.append(' ' if sep1 != ' ' else '')
        result.append(key)
        result.append('="')
        value = str(value)
        value = value.replace('\\', '\\\\').replace('"', '\\"')
        result.append(value)
        result.append('"')
        sep1 = sep2
    return ''.join(result)


def parse_vector(vector):
    """Parse an up-to-date vector."""
    result = []
    parts = vector.split(',')
    for part in parts:
        uuid, seqno = part.split(':')
        if not uuid4.check(uuid):
            raise ValueError('Illegal UUID')
        seqno = int(seqno)
        result.append((uuid, seqno))
    return result

def dump_vector(vector):
    """Dump an up-to-date vector."""
    vec = ','.join(['%s:%s' % (uuid, seqno) for (uuid, seqno) in vector])
    #if isinstance(vec, unicode):
    #    vec = vec.encode('iso-8859-1')  # XXX: investiage
    return vec


class SyncAPIClient(object):
    """
    SyncAPI client.

    This classs implements a client to the Bluepass HTTP based synchronization
    API. The two main functions are pairing (pair_step1() and pair_step2())
    and synchronization (sync()).
    """

    pem_directory = None

    def __init__(self):
        """Create a new client for the syncapi API at `address`."""
        self.address = None
        self.connection = None
        self._log = logging.get_logger(self)
        self.crypto = CryptoProvider()
        if self.pem_directory is None and compat.PY3:
            self.pem_directory = tempfile.mkdtemp()
            init_pem_directory(self.pem_directory)

    def _make_request(self, method, url, headers=None, body=None):
        """Make an HTTP request to the API.
        
        This returns the HTTPResponse object on success, or None on failure.
        """
        headers = [] if headers is None else headers[:]
        headers.append(('User-Agent', 'Bluepass/%s' % _version.__version__))
        headers.append(('Accept', 'text/json'))
        if body is None:
            body = b''
        else:
            body = json.dumps(body).encode('utf8')
            headers.append(('Content-Type', 'text/json'))
        connection = self.connection
        assert connection is not None
        try:
            self._log.debug('client request: {} {}', method, url)
            connection.request(method, url, headers, body)
            response = connection.getresponse()
            body = response.read()
        except gruvi.Error as e:
            self._log.error('error when making HTTP request: {}', str(e))
            return
        ctype = response.get_header('Content-Type')
        if ctype == 'text/json':
            parsed = json.try_loads(body.decode('utf8'))
            if parsed is None:
                self._log.error('response body contains invalid JSON')
                return
            response.entity = parsed
            self._log.debug('parsed "{}" request body ({} bytes)', ctype, len(body))
        else:
            response.entity = None
        return response

    def connect(self, address):
        """Connect to the remote syncapi."""
        if compat.PY3:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            context.set_ciphers('ADH+AES')
            context.load_dh_params(os.path.join(self.pem_directory, 'dhparams.pem'))
            sslargs = {'context': context}
        else:
            sslargs = {'dhparams': base64.decode(dhparams['skip2048']),
                       'ciphers': 'ADH+AES'}
        connection = HttpClient()
        try:
            connection.connect(address, ssl=True, **sslargs)
        except gruvi.Error as e:
            self._log.error('could not connect to {}:{}' % address)
            raise SyncAPIError('RemoteError', 'Could not connect')
        self.address = address
        self.connection = connection

    def close(self):
        """Close the connection."""
        if self.connection is not None:
            try:
                conection.close()
            except Exception:
                pass
        self.connection = None

    def _get_hmac_cb_auth(self, kxid, pin):
        """Return the headers for a client to server HMAC_CB auth."""
        cb = self.connection.transport.ssl.get_channel_binding('tls-unique')
        signature = self.crypto.hmac(adjust_pin(pin, +1).encode('ascii'), cb, 'sha1')
        signature = base64.encode(signature)
        auth = create_option_header('HMAC_CB', kxid=kxid, signature=signature)
        headers = [('Authorization', auth)]
        return headers

    def _check_hmac_cb_auth(self, response, pin):
        """Check a server to client HMAC_CB auth."""
        authinfo = response.get_header('Authentication-Info', '')
        try:
            method, options = parse_option_header(authinfo)
        except ValueError:
            self._log.error('illegal Authentication-Info header: {}', authinfo)
            return False
        if 'signature' not in options or not base64.check(options['signature']):
            self._log.error('illegal Authentication-Info header: {}', authinfo)
            return False
        signature = base64.decode(options['signature'])
        cb = self.connection.transport.ssl.get_channel_binding('tls-unique')
        check = self.crypto.hmac(adjust_pin(pin, -1).encode('ascii'), cb, 'sha1')
        if check != signature:
            self._log.error('HMAC_CB signature did not match')
            return False
        return True

    def pair_step1(self, uuid, name):
        """Perform step 1 in a pairing exchange.
        
        If succesful, this returns a key exchange ID. On error, a SyncAPIError
        exception is raised.
        """
        if self.connection is None:
            raise SyncAPIError('ProgrammingError', 'Not connected')
        url = '/api/vaults/%s/pair' % uuid
        headers = [('Authorization', 'HMAC_CB name=%s' % name)]
        response = self._make_request('POST', url, headers)
        if response is None:
            raise SyncAPIError('RemoteError', 'Could not make HTTP request')
        status = response.status
        if status != 401:
            self_log.error('expecting HTTP status 401 (got: {})', status)
            raise SyncAPIError('RemoteError', 'HTTP {0}'.format(response.status))
        wwwauth = response.get_header('WWW-Authenticate', '')
        try:
            method, options = parse_option_header(wwwauth)
        except ValueError:
            raise SyncAPIError('RemoteError', 'Illegal response')
        if method != 'HMAC_CB' or 'kxid' not in options:
            self._log.error('illegal WWW-Authenticate header: {}', wwwauth)
            raise SyncAPIError('RemoteError', 'Illegal response')
        return options['kxid']

    def pair_step2(self, uuid, kxid, pin, certinfo):
        """Perform step 2 in pairing exchange.
        
        If successfull, this returns the peer certificate. On error, a
        SyncAPIError is raised.
        """
        if self.connection is None:
            raise SyncAPIError('ProgrammingError', 'Not connected')
        url = '/api/vaults/%s/pair' % uuid
        headers = self._get_hmac_cb_auth(kxid, pin)
        response = self._make_request('POST', url, headers, certinfo)
        if response is None:
            raise SyncAPIError('RemoteError', 'Could not make syncapi request')
        status = response.status
        if status != 200:
            self._log.error('expecting HTTP status 200 (got: {})', status)
            raise SyncAPIError('RemoteError', 'HTTP status {0}'.format(response.status))
        if not self._check_hmac_cb_auth(response, pin):
            raise SyncAPIError('RemoteError', 'Illegal syncapi response')
        peercert = response.entity
        if peercert is None or not isinstance(peercert, dict):
            raise SyncAPIError('RemoteError', 'Illegal syncapi response')
        return peercert

    def _get_rsa_cb_auth(self, uuid, model):
        """Return the headers for RSA_CB authentication."""
        cb = self.connection.transport.ssl.get_channel_binding('tls-unique')
        privkey = model.get_auth_key(uuid)
        assert privkey is not None
        signature = self.crypto.rsa_sign(cb, privkey, 'pss-sha1')
        signature = base64.encode(signature)
        vault = model.get_vault(uuid)
        auth = create_option_header('RSA_CB', node=vault['node'], signature=signature)
        headers = [('Authorization', auth)]
        return headers

    def _check_rsa_cb_auth(self, uuid, response, model):
        """Verify RSA_CB authentication."""
        authinfo = response.get_header('Authentication-Info', '')
        try:
            method, options = parse_option_header(authinfo)
        except ValueError:
            self._log.error('illegal Authentication-Info header')
            return False
        if 'signature' not in options or 'node' not in options \
                or not base64.check(options['signature']) \
                or not uuid4.check(options['node']):
            self._log.error('illegal Authentication-Info header')
            return False
        cb = self.connection.transport.ssl.get_channel_binding('tls-unique')
        signature = base64.decode(options['signature'])
        cert = model.get_certificate(uuid, options['node'])
        if cert is None:
            self_log.error('unknown node {} in RSA_CB authentication', node)
            return False
        pubkey = base64.decode(cert['payload']['keys']['auth']['key'])
        try:
            status = self.crypto.rsa_verify(cb, signature, pubkey, 'pss-sha1')
        except CryptoError:
            self._log.error('corrupt RSA_CB signature')
            return False
        if not status:
            self._log.error('RSA_CB signature did not match')
        return status

    def sync(self, uuid, model, notify=True):
        """Synchronize vault `uuid` with the remote peer."""
        if self.connection is None:
            raise SyncAPIError('ProgrammingError', 'Not connected')
        vault = model.get_vault(uuid)
        if vault is None:
            raise SyncAPIError('NotFound', 'Vault not found')
        vector = model.get_vector(uuid)
        vector = dump_vector(vector)
        url = '/api/vaults/%s/items?vector=%s' % (vault['id'], vector)
        headers = self._get_rsa_cb_auth(uuid, model)
        response = self._make_request('GET', url, headers)
        if not response:
            raise SyncAPIError('RemoteError', 'Could not make HTTP request')
        status = response.status
        if status != 200:
            self._log.error('expecting HTTP status 200 (got: {})', status)
            raise SyncAPIError('RemoteError', 'Illegal syncapi response')
        if not self._check_rsa_cb_auth(uuid, response, model):
            raise SyncAPIError('RemoteError', 'Illegal syncapi response')
        initems = response.entity
        if initems is None or not isinstance(initems, list):
            raise SyncAPIError('RemoteError', 'Illegal syncapi response')
        nitems = model.import_items(uuid, initems, notify=notify)
        self._log.debug('imported {} items into model', nitems)
        vector = response.get_header('X-Vector', '')
        try:
            vector = parse_vector(vector)
        except ValueError as e:
            self._log.error('illegal X-Vector header: {} ({})', vector, str(e))
            raise SyncAPIError('RemoteError', 'Invalid response')
        outitems = model.get_items(uuid, vector)
        url = '/api/vaults/%s/items' % uuid
        response = self._make_request('POST', url, headers, outitems)
        if not response:
            raise SyncAPIError('RemoteError', 'Illegal syncapi response')
        if status != 200:
            self._log.error('expecting HTTP status 200 (got: {})', status)
            raise SyncAPIError('RemoteError', 'Illegal syncapi response')
        if not self._check_rsa_cb_auth(uuid, response, model):
            raise SyncAPIError('RemoteError', 'Illegal syncapi response')
        self._log.debug('succesfully retrieved {} items from peer', len(initems))
        self._log.debug('succesfully pushed {} items to peer', len(outitems))
        return len(initems) + len(outitems)


def expose(path, **kwargs):
    """Decorator to expose a method via a Rails like route."""
    def _f(func):
        func.path = path
        func.kwargs = kwargs
        func.kwargs['handler'] = func.__name__
        return func
    return _f


class HTTPReturn(Exception):
    """When raised, this exception will issue a HTTP return."""

    def __init__(self, status, headers=None):
        self.status = status
        self.headers = headers or []


class WSGIApplication(object):
    """A higher-level handler interface on top of WSGI.
    
    This class implements Rails-like routing and JSON marshaling/
    demarshaling.
    """

    _re_var = re.compile(':([a-z-A-Z_][a-z-A-Z0-9_]*)')

    def __init__(self):
        self._log = logging.get_logger(self)
        self.routes = []
        self._init_mapper()
        self.local = gruvi.local()

    def _init_mapper(self):
        """Add all routes that were configured with the @expose() decorator."""
        for name in vars(self.__class__):
            method = getattr(self, name)
            if callable(method) and hasattr(method, 'path'):
                pattern = self._re_var.sub('(?P<\\1>[^/]+)', method.path)
                regex = re.compile(pattern)
                self.routes.append((regex, method.kwargs))

    def _match_routes(self, env):
        """Match a request against the set of routes."""
        url = env['PATH_INFO']
        method = env['REQUEST_METHOD']
        matchvars = { 'method': method }
        for regex,kwargs in self.routes:
            mobj = regex.match(url)
            if mobj is None:
                continue
            nomatch = [ var for var in matchvars
                        if var in kwargs and matchvars[var] != kwargs[var] ]
            if nomatch:
                continue
            match = mobj.groupdict().copy()
            match.update(kwargs)
            return match

    def _get_environ(self):
        return self.local.environ

    environ = property(_get_environ)

    def _get_headers(self):
        return self.local.headers

    headers = property(_get_headers)

    def __call__(self, env, start_response):
        """WSGI entry point."""
        self.local.environ = env
        self.local.headers = []
        self.local.start_response = start_response
        self._log.debug('server request: {} {}', env['REQUEST_METHOD'], env['PATH_INFO'])
        match = self._match_routes(env)
        if not match:
            return self._simple_response(http.NOT_FOUND)
        for key in match:
            env['mapper.%s' % key] = match[key]
        ctype = env.get('CONTENT_TYPE')
        if ctype:
            if ctype != 'text/json':
                return self._simple_response(http.UNSUPPORTED_MEDIA_TYPE)
            body = env['wsgi.input'].read()
            entity = json.try_loads(body.decode('utf8'))
            if entity is None:
                return self._simple_response(http.BAD_REQUEST)
            self.entity = entity
        else:
            self.entity = None
        handler = getattr(self,  match['handler'])
        try:
            result = handler(env)
        except HTTPReturn as e:
            return self._simple_response(e.status, e.headers)
        except Exception:
            self._log.exception('uncaught exception in handler')
            return self._simple_response(http.INTERNAL_SERVER_ERROR)
        if result is not None:
            result = json.dumps(result).encode('utf8')
            self.headers.append(('Content-Type', 'text/json'))
        else:
            result = ''
        start_response('200 OK', self.headers)
        return [result]

    def _simple_response(self, status, headers=[]):
        """Return a simple text/plain response."""
        if isinstance(status, int):
            status = '%s %s' % (status, http.responses[status])
        headers.append(('Content-Type', 'text/plain'))
        headers.append(('Content-Length', str(len(status))))
        self.local.start_response(status, headers)
        return [status]


class SyncAPIApplication(WSGIApplication):
    """A WSGI application that implements our SyncAPI."""

    def __init__(self):
        super(SyncAPIApplication, self).__init__()
        self.crypto = CryptoProvider()
        self.allow_pairing = False
        self.key_exchanges = {}

    def _do_auth_hmac_cb(self, uuid):
        """Perform mutual HMAC_CB authentication."""
        wwwauth = create_option_header('HMAC_CB', realm=uuid)
        headers = [('WWW-Authenticate', wwwauth)]
        auth = self.environ.get('HTTP_AUTHORIZATION')
        if auth is None:
            raise HTTPReturn(http.UNAUTHORIZED, headers)
        try:
            method, options = parse_option_header(auth)
        except ValueError:
            raise HTTPReturn(http.UNAUTHORIZED, headers)
        if method != 'HMAC_CB':
            raise HTTPReturn(http.UNAUTHORIZED, headers)
        if 'name' in options:
            # pair step 1 - ask user for permission to pair
            name = options['name']
            if not self.allow_pairing:
                raise HTTPReturn('403 Pairing Disabled')
            from bluepass.socketapi import SocketAPIServer
            bus = instance(SocketAPIServer)
            kxid = binascii.hexlify(self.crypto.random(16)).decode('ascii')
            pin = '%06d' % (self.crypto.randint(bits=31) % 1000000)
            for client in bus.clients:
                approved = bus.call_method(client, 'get_pairing_approval',
                                           name, uuid, pin, kxid)
                break
            if not approved:
                raise HTTPReturn('403 Approval Denied')
            restrictions = {}
            self.key_exchanges[kxid] = (time.time(), restrictions, pin)
            wwwauth = create_option_header('HMAC_CB', kxid=kxid)
            headers = [('WWW-Authenticate', wwwauth)]
            raise HTTPReturn(http.UNAUTHORIZED, headers)
        elif 'kxid' in options:
            # pair step 2 - check auth and do the actual pairing
            kxid = options['kxid']
            if kxid not in self.key_exchanges:
                raise HTTPReturn(http.FORBIDDEN)
            starttime, restrictions, pin = self.key_exchanges.pop(kxid)
            signature = base64.try_decode(options.get('signature', ''))
            if not signature:
                raise HTTPReturn(http.FORBIDDEN)
            now = time.time()
            if now - starttime > 60:
                raise HTTPReturn('403 Request Timeout')
            cb = self.environ['SSL_CHANNEL_BINDING_TLS_UNIQUE']
            check = self.crypto.hmac(adjust_pin(pin, +1).encode('ascii'), cb, 'sha1')
            if check != signature:
                raise HTTPReturn('403 Invalid PIN')
            from bluepass.socketapi import SocketAPIServer
            bus = instance(SocketAPIServer)
            for client in bus.clients:
                bus.send_notification(client, 'PairingComplete', kxid)
            # Prove to the other side we also know the PIN
            signature = self.crypto.hmac(adjust_pin(pin, -1).encode('ascii'), cb, 'sha1')
            signature = base64.encode(signature)
            authinfo = create_option_header('HMAC_CB', kxid=kxid, signature=signature)
            self.headers.append(('Authentication-Info', authinfo))
        else:
            raise HTTPReturn(http.UNAUTHORIZED, headers)
 
    def _do_auth_rsa_cb(self, uuid):
        """Perform mutual RSA_CB authentication."""
        wwwauth = create_option_header('RSA_CB', realm=uuid)
        headers = [('WWW-Authenticate', wwwauth)]
        auth = self.environ.get('HTTP_AUTHORIZATION')
        if auth  is None:
            raise HTTPReturn(http.UNAUTHORIZED, headers)
        try:
            method, opts = parse_option_header(auth)
        except ValueError:
            raise HTTPReturn(http.UNAUTHORIZED, headers)
        if method != 'RSA_CB':
            raise HTTPReturn(http.UNAUTHORIZED, headers)
        if 'node' not in opts or not uuid4.check(opts['node']):
            raise HTTPReturn(http.UNAUTHORIZED, headers)
        if 'signature' not in opts or not base64.check(opts['signature']):
            raise HTTPReturn(http.UNAUTHORIZED, headers)
        model = instance(Model)
        cert = model.get_certificate(uuid, opts['node'])
        if cert is None:
            raise HTTPReturn(http.UNAUTHORIZED, headers)
        signature = base64.decode(opts['signature'])
        pubkey = base64.decode(cert['payload']['keys']['auth']['key'])
        cb = self.environ['SSL_CHANNEL_BINDING_TLS_UNIQUE']
        if not self.crypto.rsa_verify(cb, signature, pubkey, 'pss-sha1'):
            raise HTTPReturn(http.UNAUTHORIZED, headers)
        # The peer was authenticated. Authenticate ourselves as well.
        privkey = model.get_auth_key(uuid)
        vault = model.get_vault(uuid)
        node = vault['node']
        signature = self.crypto.rsa_sign(cb, privkey, 'pss-sha1')
        signature = base64.encode(signature)
        auth = create_option_header('RSA_CB', node=node, signature=signature)
        self.headers.append(('Authentication-Info', auth))

    @expose('/api/vaults/:vault/pair', method='POST')
    def pair(self, env):
        uuid = env['mapper.vault']
        if not uuid4.check(uuid):
            raise HTTPReturn(http.NOT_FOUND)
        model = instance(Model)
        vault = model.get_vault(uuid)
        if not vault:
            raise HTTPReturn(http.NOT_FOUND)
        self._do_auth_hmac_cb(uuid)
        # Sign the certificate request that was sent to tus
        certinfo = self.entity
        if not certinfo or not isinstance(certinfo, dict):
            raise HTTPReturn(http.BAD_REQUEST)
        model.add_certificate(uuid, certinfo)
        # And send our own certificate request in return
        certinfo = { 'node': vault['node'], 'name': socket.gethostname() }
        certkeys = certinfo['keys'] = {}
        for key in vault['keys']:
            certkeys[key] = { 'key': vault['keys'][key]['public'],
                              'keytype': vault['keys'][key]['keytype'] }
        return certinfo

    @expose('/api/vaults/:vault/items', method='GET')
    def sync_outbound(self, env):
        uuid = env['mapper.vault']
        if not uuid4.check(uuid):
            raise HTTPReturn(http.NOT_FOUND)
        model = instance(Model)
        vault = model.get_vault(uuid)
        if vault is None:
            raise HTTPReturn(http.NOT_FOUND)
        self._do_auth_rsa_cb(uuid)
        args = parse_qs(env.get('QUERY_STRING', ''))
        vector = args.get('vector', [''])[0]
        if vector:
            try:
                vector = parse_vector(vector)
            except ValueError:
                raise HTTPReturn(http.BAD_REQUEST)
        items = model.get_items(uuid, vector)
        myvector = model.get_vector(uuid)
        self.headers.append(('X-Vector', dump_vector(myvector)))
        return items

    @expose('/api/vaults/:vault/items', method='POST')
    def sync_inbound(self, env):
        uuid = env['mapper.vault']
        if not uuid4.check(uuid):
            raise HTTPReturn(http.NOT_FOUND)
        model = instance(Model)
        vault = model.get_vault(uuid)
        if vault is None:
            raise HTTPReturn(http.NOT_FOUND)
        self._do_auth_rsa_cb(uuid)
        items = self.entity
        if items is None or not isinstance(items, list):
            raise HTTPReturn(http.BAD_REQUEST)
        model.import_items(uuid, items)


class SyncAPIServer(HttpServer):
    """The WSGI server that runs the syncapi."""

    pem_directory = None

    def __init__(self):
        handler = singleton(SyncAPIApplication)
        super(SyncAPIServer, self).__init__(handler)
        if self.pem_directory is None and compat.PY3:
            self.pem_directory = tempfile.mkdtemp()
            init_pem_directory(self.pem_directory)

    def _get_environ(self, transport, message):
        env = super(SyncAPIServer, self)._get_environ(transport, message)
        env['SSL_CIPHER'] = transport.ssl.cipher()
        cb = transport.ssl.get_channel_binding('tls-unique')
        env['SSL_CHANNEL_BINDING_TLS_UNIQUE'] = cb
        return env

    def listen(self, address):
        if compat.PY3:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            context.set_ciphers('ADH+AES')
            context.load_dh_params(os.path.join(self.pem_directory, 'dhparams.pem'))
            sslargs = {'context': context}
        else:
            sslargs = {'dhparams': base64.decode(dhparams['skip2048']),
                       'ciphers': 'ADH+AES'}
        super(SyncAPIServer, self).listen(address, ssl=True, **sslargs)


class SyncAPIPublisher(Fiber):
    """Sync API publisher.

    The Publisher is responsible for publising the location of our syncapi
    via the Locator, and keeping these published locations up to date.

    The publisher needs to make calls to the locator which might block,
    and therefore runs in its own fiber.
    """

    def __init__(self, server):
        super(SyncAPIPublisher, self).__init__(target=self._run)
        self.server = server
        self.queue = gruvi.Queue()
        self.published_nodes = set()
        self.allow_pairing = False
        self.allow_pairing_until = None
        self.callbacks = []

    def add_callback(self, callback):
        """Add a callback that gets notified of events."""
        self.callbacks.append(callback)

    def raise_event(self, event, *args):
        """Raise an event to all registered callbacks."""
        for callback in self.callbacks:
            callback(event, *args)

    def set_allow_pairing(self, timeout):
        """Allow pairing for up to `timeout` seconds. Use a timeout
        of zero to disable pairing."""
        self.queue.put(('allow_pairing', (timeout,)))

    def stop(self):
        """Stop the publisher."""
        self.queue.put(('stop', None))

    def _event_callback(self, event, *args):
        self.queue.put((event, args))

    def _get_hostname(self):
        name = socket.gethostname()
        pos = name.find('.')
        if pos != -1:
            name = name[:pos]
        return name

    def _run(self):
        """Main execution loop, runs in its own fiber."""
        log = logging.get_logger(self)
        locator = instance(Locator)
        self.locator = locator
        model = instance(Model)
        model.add_callback(self._event_callback)
        nodename = self._get_hostname()
        vaults = model.get_vaults()
        for vault in vaults:
            addr = gruvi.getsockname(self.server.transport)
            locator.register(vault['node'], nodename, vault['id'], vault['name'], addr)
            log.debug('published node {}', vault['node'])
            self.published_nodes.add(vault['node'])
        stopped = False
        while not stopped:
            timeout = self.allow_pairing_until - time.time() \
                        if self.allow_pairing else None
            entry = self.queue.get(timeout)
            if entry:
                event, args = entry
                log.debug('processing event: {}', event)
                if event == 'allow_pairing':
                    timeout = args[0]
                    if timeout > 0:
                        self.allow_pairing = True
                        self.allow_pairing_until = time.time() + timeout
                        for node in self.published_nodes:
                            locator.set_property(node, 'visible', 'true')
                            log.debug('make node {} visible', node)
                        instance(SyncAPIApplication).allow_pairing = True
                        self.raise_event('AllowPairingStarted', timeout)
                    else:
                        self.allow_pairing = False
                        self.allow_pairing_until = None
                        for node in self.published_nodes:
                            locator.set_property(node, 'visible', 'false')
                            log.debug('make node {} invisible (user)', node)
                        instance(SyncAPIApplication).allow_pairing = False
                        self.raise_event('AllowPairingEnded')
                elif event == 'VaultAdded':
                    vault = args[0]
                    node = vault['node']
                    if node in self.published_nodes:
                        log.error('got VaultAdded signal for published node')
                        continue
                    properties = {}
                    if self.allow_pairing:
                        properties['visible'] = 'true'
                    addr = gruvi.getsockname(self.server.transport)
                    locator.register(node, nodename, vault['id'], vault['name'],
                                     addr, properties)
                    self.published_nodes.add(node)
                    log.debug('published node {}', node)
                elif event == 'VaultRemoved':
                    vault = args[0]
                    node = vault['node']
                    if node not in self.published_nodes:
                        log.error('got VaultRemoved signal for unpublished node')
                        continue
                    locator.unregister(node)
                    self.published_nodes.remove(node)
                    log.debug('unpublished node {}', node)
                elif event == 'stop':
                    stopped = True
            now = time.time()
            if self.allow_pairing and now >= self.allow_pairing_until:
                for node in self.published_nodes:
                    self.locator.set_property(node, 'visible', 'false')
                    log.debug('make node {} invisible (timeout)', node)
                self.allow_pairing = False
                self.allow_pairing_until = None
                instance(SyncAPIApplication).allow_pairing = False
                self.raise_event('AllowPairingEnded')
            log.debug('done processing event')
        log.debug('shutting down publisher')

########NEW FILE########
__FILENAME__ = syncer
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import time
import logging

import gruvi
from gruvi import Fiber

from bluepass import logging
from bluepass.factory import instance
from bluepass.model import Model
from bluepass.locator import Locator
from bluepass.syncapi import SyncAPIClient, SyncAPIError


class Syncer(Fiber):
    """Syncer.
    
    The syncer is an component that is responsible for inbound/outbound
    synchronization. The sync jobs are run either periodically, or based on
    certain system events, like a neighbor becoming visible on the network or
    an entry being added.
    """

    interval = 300

    def __init__(self):
        """Constructor."""
        super(Syncer, self).__init__(target=self._run)
        self._log = logging.get_logger(self)
        self.queue = gruvi.Queue()
        self.neighbors = {}
        self.last_sync = {}

    def _event_callback(self, event, *args):
        """Store events and wake up the main loop."""
        self.queue.put((event, args))

    def set_last_sync(self, node, time):
        """Set the last_sync time for `node` to `time`."""
        self.last_sync[node] = time

    def _run(self):
        """This runs the synchronization loop."""
        model = instance(Model)
        model.add_callback(self._event_callback)
        locator = instance(Locator)
        locator.add_callback(self._event_callback)
        neighbors = locator.get_neighbors()
        mynodes = set((v['node'] for v in model.get_vaults()))
        myvaults = set((v['id'] for v in model.get_vaults()))
        while True:
            # Determine how long we need to wait
            now = time.time()
            timeout = self.interval
            for neighbor in neighbors:
                node = neighbor['node']
                vault = neighbor['vault']
                if node in mynodes or vault not in myvaults \
                            or not model.get_certificate(vault, node):
                    continue
                last_sync = self.last_sync.get(node, 0)
                timeout = min(timeout, max(0, last_sync + self.interval - now))
            # Now wait for a timeout, or an event.
            entry = self.queue.get(timeout)
            # Build a list of nodes that we need to sync with.
            #
            # We sync to nodes that are are not ours, whose vault we also
            # have, and where there is a certificate. In addition, at least
            # one of the following three needs to be true:
            #
            # 1. The last sync to this node is > interval seconds ago.
            # 2. A version was added locally to the node's vault
            # 3. The node resides at an address that we are already syncing
            #    with.
            #
            # Regarding #3, we organize the nodes by network address, and try
            # to sync all nodes over a single connection. So the nodes in #3
            # are almost "free" to do so that's they are included.
            now = time.time()
            neighbors = locator.get_neighbors()
            mynodes = set((v['node'] for v in model.get_vaults()))
            myvaults = set((v['id'] for v in model.get_vaults()))
            byaddress = {}
            sync_nodes = set()
            sync_vaults = set()
            # First process events.
            if entry:
                event, args = entry
                if event == 'NeighborDiscovered':
                    neighbor = args[0]
                    # As an optimization do not sync with new neighbors that
                    # are discovered while we are running, because we known
                    # that when they are started up they will sync with us.
                    self.last_sync[neighbor['node']] = now
                elif event == 'VersionsAdded':
                    vault, versions = args
                    # As an optimization, only push out a list of added
                    # versions in case it is generated locally, because we know
                    # the originator will push the update to everybody else.
                    for version in versions:
                        item = model.get_version_item(vault, version['id'])
                        if item['origin']['node'] not in mynodes:
                            continue
                        self._log.debug('local update, syncing to all nodes for vault {}', vault)
                        sync_vaults.add(vault)
                        break
            # Now build a list of nodes including a "byaddress" list.
            for neighbor in neighbors:
                node = neighbor['node']
                vault = neighbor['vault']
                if node in mynodes or vault not in myvaults \
                            or not model.get_certificate(vault, node):
                    # Never sync with these nodes...
                    continue
                last_sync = self.last_sync.get(node, 0)
                timeout = last_sync + self.interval < now
                if timeout or vault in sync_vaults:
                    for addr in neighbor['addresses']:
                        key = addr['id']
                        if key not in byaddress:
                            byaddress[key] = (addr['family'], addr, [])
                        byaddress[key][2].append(neighbor)
                    sync_nodes.add(node)
                    continue
                # See if we are already syncing with an address, and if so,
                # include /that address only/ in the sync job.
                for addr in neighbor['addresses']:
                    key = addr['id']
                    if key in byaddress:
                        byaddress[key][2].append(neighbor)
                        sync_nodes.add(node)
            if not sync_nodes:
                # Nothing to do...
                continue
            self._log.debug('total nodes to sync: {}', len(sync_nodes))
            # Now sync to the nodes. Try to reuse the network connection for
            # multiple nodes. We sort the addresses on location source so that
            # we will be able to give different priorites to different sources
            # later.
            nnodes = nconnections = 0
            addresses = sorted(byaddress.values(), key=lambda x: x[0])
            for source,addr,neighbors in addresses:
                client = None
                for neighbor in neighbors:
                    node = neighbor['node']
                    if node not in sync_nodes:
                        continue  # already synced
                    self._log.debug('syncing with node {}', node)
                    if client is None:
                        client = SyncAPIClient()
                        try:
                            client.connect(addr['addr'])
                        except SyncAPIError as e:
                            self._log.error('could not connect to {}: {}', addr, str(e))
                            client.close()
                            break
                        self._log.debug('connected to {}', addr)
                        nconnections += 1
                    vault = neighbor['vault']
                    starttime = time.time()
                    try:
                        client.sync(vault, model)
                    except SyncAPIError:
                        self._log.error('failed to sync vault {} at {}', vault, addr)
                        client.close()
                        client = None
                    else:
                        self._log.debug('succesfully synced vault {} at {}', vault, addr)
                        nnodes += 1
                        sync_nodes.remove(node)
                        self.last_sync[node] = starttime
                if client:
                    client.close()
                if not sync_nodes:
                    break  # we are done
            self._log.debug('synced to {} nodes using {} network connections', nnodes, nconnections)
            if sync_nodes:
                self._log.debug('failed to sync with {} nodes', len(sync_nodes))
        self._log.debug('syncer loop terminated')

########NEW FILE########
__FILENAME__ = util
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import os
import stat
import errno
import socket

from gruvi import compat
import gruvi.util


def asset(*path):
    """Return the path of an asset specified by *path*."""
    dname, _ = os.path.split(__file__)
    base = os.path.join(dname, 'assets')
    st = try_stat(base)
    if st is None or not stat.S_ISDIR(st.st_mode):
        # developer install? Try top of source dir.
        dname, _ = os.path.split(dname)
        base = os.path.join(dname, 'assets')
        st = try_stat(base)
        if st is None or not stat.S_ISDIR(st.st_mode):
            raise RuntimeError('Runtime assets not found')
    asset = os.path.join(base, *path)
    st = try_stat(asset)
    if st is None or not stat.S_ISREG(st.st_mode):
        raise RuntimeError('asset {} not found'.format('/'.join(path)))
    return asset


def gethostname():
    """Return the host name."""
    hostname = socket.gethostname()
    pos = hostname.find('.')
    if pos != -1:
        hostname = hostname[:pos]
    return hostname


def paddr(s):
    """Parse a string form of a socket address."""
    return gruvi.util.paddr(s)

def saddr(address):
    """Convert a socket address into a string form."""
    return gruvi.util.saddr(address)

def create_connection(address, timeout=None):
    """Create a connection to *address* and return the socket."""
    if isinstance(address, tuple) and ':' in address[0]:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)
    elif isinstance(address, tuple) and '.' in address[0]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    elif isinstance(address, compat.string_types):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
    else:
        raise ValueError('expecting IPv4/IPv6 tuple, or path')
    sock.settimeout(timeout)
    sock.connect(address)
    return sock


def try_stat(fname):
    """Try to stat a path. Do not raise an error if the file does not exist."""
    try:
        st = os.stat(fname)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
        st = None
    return st

def try_unlink(fname):
    """Try to stat a path. Do not raise an error if the file does not exist."""
    try:
        st = os.unlink(fname)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
        st = None
    return st


def replace(src, dst):
    """Replace *src* with *dst*. Atomic if the Platform or Python version
    supports it."""
    if hasattr(os, 'replace'):
        os.replace(src, dst)
    elif hasattr(os, 'fork'):
        # posix has atomic rename()
        os.rename(src, dst)
    else:
        # not atomic Python <= 3.2 on Windows
        try_unlink(dst)
        os.rename(src, dst)


def write_atomic(fname, contents):
    """Atomically write *contents* to *fname* by creating a temporarily file
    and renaming it in place."""
    tmpname = '{0}-{1}.tmp'.format(fname, os.getpid())
    with open(tmpname, 'w') as fout:
        fout.write(contents)
    replace(tmpname, fname)

########NEW FILE########
__FILENAME__ = uuid4
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import re
from gruvi import compat

_re_uuid = re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-'
                      '[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)

def check(s):
    return isinstance(s, compat.string_types) and bool(_re_uuid.match(s))

########NEW FILE########
__FILENAME__ = test_lock
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import os
import sys

from ..unit import UnitTest, assert_raises
from bluepass.platform import lock_file, unlock_file, LockError


class TestLock(UnitTest):

    def test_lock_unlock(self):
        fname = self.tempfile()
        lock = lock_file(fname)
        unlock_file(lock)

    def test_lock_multiple(self):
        fname = self.tempfile()
        lock = lock_file(fname)
        # The tests below would require flock() on Posix which does per-fd
        # locking instead of lockf() which is per process. However flock() is
        # not safe on NFS on all platforms. So disable these tests.
        #err = assert_raises(LockError, lock_file, fname)
        #assert hasattr(err, 'lock_pid')
        #assert err.lock_pid == os.getpid()
        #assert hasattr(err, 'lock_uid')
        #assert err.lock_uid == os.getuid()
        #assert hasattr(err, 'lock_cmd')
        #assert sys.argv[0].endswith(err.lock_cmd)
        unlock_file(lock)
        lock = lock_file(fname)
        unlock_file(lock)

########NEW FILE########
__FILENAME__ = test_backend
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import os
import time
import socket
import signal

from gevent import core
from .unit import UnitTest, assert_raises

from bluepass.factory import create
from bluepass.database import DatabaseError
from bluepass.backend import Backend, BackendController
from bluepass.messagebus import MessageBusConnection, MessageBusError
from bluepass.util import misc as util


class TestBackend(UnitTest):

    def setup(self):
        os.environ['HOME'] = self.tempdir()
        authtok = os.urandom(16).encode('hex')
        self.config = { 'debug': True, 'log_stdout': False,
                        'auth_token': authtok }
        # XXX: Create a Posix/Windows controller? For now just os.spawnve()
        # and a timeout.
        ctrl = BackendController(self.config)
        cmd, args, env = ctrl.startup_info()
        self.backend_pid = os.spawnve(os.P_NOWAIT, cmd, args, env)
        time.sleep(1)
        addrspec = ctrl.backend_address()
        addr = util.parse_address(addrspec)
        csock = util.create_connection(addr)
        self.connection = MessageBusConnection(csock, authtok)

    def teardown(self):
        self.connection.close()
        time.sleep(0.5)
        os.kill(self.backend_pid, signal.SIGTERM)
        time.sleep(0.5)

    def test_db_created(self):
        dbname = os.path.join(os.environ['HOME'], '.bluepass', 'bluepass.db')
        assert os.access(dbname, os.R_OK)
        lockname = os.path.join(os.environ['HOME'], '.bluepass', 'bluepass.db-lock')
        assert os.access(dbname, os.R_OK)

    def test_multiple_startup(self):
        backend = Backend(self.config)
        exc = assert_raises(DatabaseError, backend.run)
        assert exc.error_name == 'Locked'

    def test_config(self):
        conn = self.connection
        config = conn.call_method('get_config')
        config['foo'] = 'bar'
        conn.call_method('update_config', config)
        config = conn.call_method('get_config')
        assert config['foo'] == 'bar'

    def test_lock_unlock_vault(self):
        conn = self.connection
        vault = conn.call_method('create_vault', 'My Vault', 'Passw0rd')
        version = conn.call_method('add_version', vault['id'], {'foo': 'bar'})
        assert isinstance(version, dict)
        assert 'id' in version
        conn.call_method('lock_vault', vault['id'])
        assert conn.call_method('vault_is_locked', vault['id'])
        err = assert_raises(MessageBusError, conn.call_method, 'get_version', vault['id'], version['id'])
        assert err.error_name == 'Locked'
        err = assert_raises(MessageBusError, conn.call_method, 'unlock_vault', vault['id'], 'Passw!rd')
        assert err.error_name == 'WrongPassword'
        conn.call_method('unlock_vault', vault['id'], 'Passw0rd')
        assert not conn.call_method('vault_is_locked', vault['id'])
        version2 = conn.call_method('get_version', vault['id'], version['id'])
        assert isinstance(version2, dict)
        assert version2['id'] == version['id']
        assert version2['foo'] == version['foo']

    def test_speed(self):
        conn = self.connection
        start = time.time()
        ncalls = 1000
        for i in range(ncalls):
            conn.call_method('get_config')
        end = time.time()
        print('speed: %.2f calls/sec' % (1.0 * ncalls / (end - start)))

    def test_generate_password(self):
        conn = self.connection
        pw = conn.call_method('generate_password', 'random', 20, '[0-9]')
        assert isinstance(pw, (str, unicode))
        assert len(pw) == 20
        assert pw.isdigit()
        pw = conn.call_method('generate_password', 'diceware', 6)
        assert isinstance(pw, (str, unicode))
        assert len(pw) >= 11
        assert pw.count(' ') == 5

########NEW FILE########
__FILENAME__ = test_crypto
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import os
import sys
import binascii
from subprocess import Popen, PIPE

from .unit import UnitTest, assert_raises, SkipTest
from bluepass.crypto import CryptoProvider, CryptoError, dhparams

from gruvi import compat


class CryptoTest(UnitTest):

    @classmethod
    def setup_class(cls):
        super(CryptoTest, cls).setup_class()
        cls.provider = CryptoProvider()

    def load_vectors(self, relname, start):
        dname = os.path.split(__file__)[0]
        fname = os.path.join(dname, relname)
        fin = open(fname)
        vectors = []
        while True:
            line = fin.readline()
            if not line:
                break
            line = line.rstrip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('%s=' % start):
                vectors.append({})
            if '=' not in line or not vectors:
                raise RuntimeError('Illegal test vector format: %s' % fname)
            key, value = line.split('=')
            value = binascii.unhexlify(value)
            vectors[-1][key] = value
        return vectors


class TestCrypto(CryptoTest):

    @classmethod
    def setup_class(cls):
        super(TestCrypto, cls).setup_class()
        cls.rsakeys = [ (sz, cls.provider.rsa_genkey(sz))
                     for sz in (2048, 3072) ]

    def test_rsa_encrypt(self):
        cp = self.provider
        for keysize,key in self.rsakeys:
            for size in range(keysize//8 - 41):
                pt = os.urandom(size)
                ct = cp.rsa_encrypt(pt, key[1])
                assert len(ct) == keysize//8
                pt2 = cp.rsa_decrypt(ct, key[0])
                assert pt == pt2

    def test_rsa_sign(self):
        cp = self.provider
        for keysize,key in self.rsakeys:
            for size in range(0, 10000, 100):
                msg = os.urandom(size)
                sig = cp.rsa_sign(msg, key[0])
                assert cp.rsa_verify(msg, sig, key[1])

    def test_rsa_encrypt_vectors(self):
        cp = self.provider
        if not hasattr(cp.engine, '_insert_random_bytes'):
            raise SkipTest('RSA-OAEP tests require -DTEST_BUILD')
        vectors = self.load_vectors('vectors/rsa-oaep.txt', start='PT')
        for vector in vectors:
            cp.engine._insert_random_bytes(vector['SEED'])
            ct = cp.rsa_encrypt(vector['PT'], vector['PUBKEY'], 'oaep')
            assert vector['CT'] == ct
            pt = cp.rsa_decrypt(vector['CT'], vector['PRIVKEY'], 'oaep')
            assert pt == vector['PT']

    def test_rsa_sign_vectors(self):
        cp = self.provider
        if not hasattr(cp.engine, '_insert_random_bytes'):
            raise SkipTest('RSA-PSS tests require -DTEST_BUILD')
        vectors = self.load_vectors('vectors/rsa-pss.txt', start='MSG')
        for vector in vectors:
            cp.engine._insert_random_bytes(vector['SALT'])
            sig = cp.rsa_sign(vector['MSG'], vector['PRIVKEY'], 'pss-sha1')
            assert sig == vector['SIG']
            assert cp.rsa_verify(vector['MSG'], vector['SIG'],
                                 vector['PUBKEY'], 'pss-sha1')

    def test_dh_exchange(self):
        cp = self.provider
        params = dhparams['skip2048']
        kp1 = cp.dh_genkey(params)
        kp2 = cp.dh_genkey(params)
        secret1 = cp.dh_compute(params, kp1[0], kp2[1])
        secret2 = cp.dh_compute(params, kp2[0], kp1[1])
        assert secret1 == secret2

    def test_aes_encrypt(self):
        cp = self.provider
        for size in range(100):
            for keysize in (16, 24, 32):
                key = os.urandom(keysize)
                iv = os.urandom(16)
                cleartext = os.urandom(size)
                ciphertext = cp.aes_encrypt(cleartext, key, iv)
                padlen = (16 - len(cleartext)%16)
                assert len(ciphertext) == len(cleartext) + padlen
                clear2 = cp.aes_decrypt(ciphertext, key, iv)
                assert cleartext == clear2

    def test_aes_vectors(self):
        cp = self.provider
        vectors = self.load_vectors('vectors/aes-cbc-pkcs7.txt', start='PT')
        for vector in vectors:
            ct = cp.aes_encrypt(vector['PT'], vector['KEY'], vector['IV'])
            assert ct == vector['CT']
            pt = cp.aes_decrypt(vector['CT'], vector['KEY'], vector['IV'])
            assert pt == vector['PT']

    def test_pbkdf2_vectors(self):
        cp = self.provider
        vectors = self.load_vectors('vectors/pbkdf2.txt', start='PASSWORD')
        for vector in vectors:
            key = cp.pbkdf2(vector['PASSWORD'], vector['SALT'],
                            int(vector['ITER']), int(vector['KEYLEN']),
                            'hmac-sha1')
            assert key == vector['KEY']

    def test_pbkdf2_size(self):
        cp = self.provider
        for sz in range(100):
            key = cp.pbkdf2('password', 'salt', 1, sz)
            assert len(key) == sz

    def test_pbkdf2_error_empty_password(self):
        cp = self.provider
        assert_raises(CryptoError, cp.pbkdf2, '', 'salt', 1, 1)

    def test_pbkdf2_error_empty_salt(self):
        cp = self.provider
        assert_raises(CryptoError, cp.pbkdf2, 'password', '', 1, 1)

    def test_pbkdf2_error_zero_iter(self):
        cp = self.provider
        assert_raises(CryptoError, cp.pbkdf2, 'password', 'salt', 0, 1)

    def test_pbkdf2_speed(self):
        cp = self.provider
        speed = cp.pbkdf2_speed()

    def test_hkdf_vectors(self):
        cp = self.provider
        vectors = self.load_vectors('vectors/hkdf.txt', start='PASSWORD')
        for vector in vectors:
            key = cp.hkdf(vector['PASSWORD'], vector['SALT'], vector['INFO'],
                              int(vector['KEYLEN']), vector['HASH'].decode('ascii'))
            assert key == vector['KEY']

    def test_random_bytes(self):
        cp = self.provider
        rnd = cp.random(10)
        assert isinstance(rnd, bytes)
        assert len(rnd) == 10

    def test_random_with_alphabet(self):
        cp = self.provider
        rnd = cp.random(10, '0123456789')
        assert isinstance(rnd, str)
        assert len(rnd) == 10
        assert rnd.isdigit()
        rnd = cp.random(10, u'0123456789')
        assert isinstance(rnd, compat.text_type)
        assert len(rnd) == 10
        assert rnd.isdigit()
        rnd = cp.random(5, ['01', '23', '45', '67', '89'])
        assert isinstance(rnd, str)
        assert len(rnd) == 10
        assert rnd.isdigit()
        rnd = cp.random(5, ['01', '23', '45', '67', '89'], '0')
        assert isinstance(rnd, str)
        assert len(rnd) == 14
        assert rnd.isdigit()
        rnd = cp.random(5, [u'01', u'23', u'45', u'67', u'89'], u'0')
        assert isinstance(rnd, compat.text_type)
        assert len(rnd) == 14
        assert rnd.isdigit()

########NEW FILE########
__FILENAME__ = test_database
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

from .unit import UnitTest
from bluepass.database import Database


class TestDatabase(UnitTest):
    """Unit test suite for Database."""

    def setup(self):
        self.filename = self.tempfile()
        self.database = Database(self.filename)
        self.database.create_table('items')

    def teardown(self):
        self.database.close()

    def test_open_close(self):
        db = self.database
        d1 = { 'id': 1, 'foo': 'bar' }
        db.insert('items', d1)
        docs = db.findall('items')
        assert d1 in docs
        assert len(docs) == 1
        db.close()
        db.open(self.filename)
        docs = db.findall('items')
        assert d1 in docs
        assert len(docs) == 1

    def test_find_str(self):
        db = self.database
        db.insert('items', {'foo': 'bar'})
        db.insert('items', {'foo': 'baz'})
        docs = db.findall('items', '$foo=?', ('bar',))
        assert len(docs) == 1
        assert docs[0]['foo'] == 'bar'

    def test_find_int(self):
        db = self.database
        db.insert('items', {'foo': 1})
        db.insert('items', {'foo': 2})
        docs = db.findall('items', '$foo=?', (1,))
        assert len(docs) == 1
        assert docs[0]['foo'] == 1

    def test_find_int_gt(self):
        db = self.database
        db.insert('items', {'foo': 1})
        db.insert('items', {'foo': 2})
        docs = db.findall('items', '$foo>?', (1,))
        assert len(docs) == 1
        assert docs[0]['foo'] == 2

    def test_find_or(self):
        db = self.database
        db.insert('items', {'foo': 1})
        db.insert('items', {'foo': 2})
        docs = db.findall('items', '$foo=? OR $foo=?', (1,2))
        assert len(docs) == 2
        assert docs[0]['foo'] in (1, 2)
        assert docs[1]['foo'] in (1, 2)

    def test_find_and(self):
        db = self.database
        db.insert('items', {'foo': 1, 'bar': 1})
        db.insert('items', {'foo': 2, 'bar': 1})
        docs = db.findall('items', '$foo=? AND $bar=?', (1,1))
        assert len(docs) == 1
        assert docs[0]['foo'] == 1
        assert docs[0]['bar'] == 1

    def test_find_nested(self):
        db = self.database
        db.insert('items', {'foo': {'bar': 1}})
        db.insert('items', {'foo': {'bar': 2}})
        docs = db.findall('items', '$foo$bar=?', (1,))
        assert len(docs) == 1
        assert docs[0]['foo']['bar'] == 1

    def test_find_with_index(self):
        db = self.database
        db.create_index('items', '$foo', 'INTEGER', True)
        db.insert('items',{'foo': 1})
        db.insert('items',{'foo': 2})
        docs = db.findall('items','$foo==?', (1,))
        assert len(docs) == 1
        assert docs[0]['foo'] == 1

    def test_open_close_with_index(self):
        db = self.database
        db.create_index('items', '$foo', 'INTEGER', True)
        db.insert('items', {'foo': 1})
        db.insert('items', {'foo': 2})
        db.close()
        db.open(self.filename)
        docs = db.findall('items', '$foo==?', (1,))
        assert len(docs) == 1
        assert docs[0]['foo'] == 1

    def test_findone(self):
        db = self.database
        db.insert('items', {'foo': 1, 'bar': 1})
        db.insert('items', {'foo': 2, 'bar': 1})
        doc = db.findone('items', '$foo = 1')
        assert doc['foo'] == 1
        doc = db.findone('items', '$bar = 1')
        assert doc['bar'] == 1
        doc = db.findone('items', '$bar = 2')
        assert doc is None

    def test_insert_many(self):
        db = self.database
        db.insert_many('items', [{'foo': 1}, {'foo': 2}])
        docs = db.findall('items')
        assert len(docs) == 2

    def test_update(self):
        db = self.database
        db.insert('items', {'foo': 1, 'bar': 1})
        db.insert('items', {'foo': 2, 'bar': 2})
        docs = db.findall('items', '$bar=2')
        assert len(docs) == 1
        assert docs[0] == {'foo': 2, 'bar': 2 }
        doc = docs[0]
        doc['bar'] = 3
        db.update('items', '$foo = ?', (2,), doc)
        docs = db.findall('items')
        assert len(docs) == 2
        doc = db.findone('items', '$bar=3')
        assert doc == {'foo': 2, 'bar': 3}

    def test_update_with_index(self):
        db = self.database
        db.create_index('items', '$foo', 'INTEGER', True)
        db.create_index('items', '$bar', 'INTEGER', True)
        db.insert('items', {'foo': 1, 'bar': 1})
        db.insert('items', {'foo': 2, 'bar': 2})
        docs = db.findall('items', '$bar=2')
        assert len(docs) == 1
        assert docs[0] == {'foo': 2, 'bar': 2 }
        doc = docs[0]
        doc['bar'] = 3
        db.update('items', '$foo=?', (2,), doc)
        docs = db.findall('items')
        assert len(docs) == 2
        doc = db.findone('items', '$bar=3')
        assert doc == {'foo': 2, 'bar': 3}

    def test_delete(self):
        db = self.database
        db.insert('items', {'foo': 1, 'bar': 1})
        db.insert('items', {'foo': 2, 'bar': 2})
        docs = db.findall('items')
        assert len(docs) == 2
        doc = docs.pop()
        db.delete('items', '$foo = ?', (doc['foo'],))
        docs = db.findall('items')
        assert len(docs) == 1
        assert docs[0] != doc

########NEW FILE########
__FILENAME__ = test_keyring
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

import os

from .unit import UnitTest, SkipTest
from bluepass.factory import create
from bluepass.keyring import Keyring, KeyringError


class TestKeyring(UnitTest):

    @classmethod
    def setup_class(cls):
        super(TestKeyring, cls).setup_class()
        keyring = create(Keyring)
        if keyring is None or not keyring.isavailable():
            raise SkipTest('This test requires a Keyring to be avaialble')
        cls.keyring = keyring

    def test_roundtrip(self):
        key = os.urandom(8).encode('hex')
        secret = os.urandom(32)
        self.keyring.store(key, secret)
        value = self.keyring.retrieve(key)
        assert value == secret

    def test_overwrite(self):
        key = os.urandom(8).encode('hex')
        for i in range(10):
            secret = os.urandom(i)
            self.keyring.store(key, secret)
            value = self.keyring.retrieve(key)
            assert value == secret

########NEW FILE########
__FILENAME__ = test_locator
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import time
import gevent
import socket

from .unit import UnitTest, SkipTest
from bluepass import platform
from bluepass.crypto import CryptoProvider
from bluepass.locator import *
from bluepass.factory import singleton


class TestLocator(UnitTest):

    @classmethod
    def setup_class(cls):
        super(TestLocator, cls).setup_class()
        sources = platform.get_location_sources()
        if not sources:
            raise SkipTest('No location sources avaialble')
        cls.locator = Locator()
        cls.locator.add_source(sources[0]())
        cls.crypto = CryptoProvider()

    def test_register(self):
        locator = self.locator
        node = self.crypto.randuuid()
        nodename = 'My Node'
        vault = self.crypto.randuuid()
        vaultname = 'My Vault'
        address = ('1.2.3.4', 100)
        locator.register(node, nodename, vault, vaultname, address)
        gevent.sleep(5)
        result = locator.get_neighbors()
        assert isinstance(result, list)
        assert len(result) > 0
        result = result[0]
        assert isinstance(result, dict)
        assert 'node' in result
        assert result['node'] == node
        assert 'nodename' in result
        assert result['nodename'] == nodename
        assert 'vault' in result
        assert result['vault'] == vault
        assert 'vaultname' in result
        assert result['vaultname'] == vaultname
        assert 'source' in result
        assert result['source'] == 'LAN'
        assert 'properties' in result
        assert isinstance(result['properties'], dict)
        assert len(result['properties']) == 0
        assert 'addresses' in result
        assert isinstance(result['addresses'], list)
        assert len(result['addresses']) >= 1
        for addr in result['addresses']:
            assert isinstance(addr, dict)
            assert 'family' in addr
            assert isinstance(addr['family'], int)
            assert addr['family'] in (socket.AF_INET, socket.AF_INET6)
            assert 'addr' in addr
            assert isinstance(addr['addr'], tuple)
            assert isinstance(addr['addr'][0], (str, unicode))
            assert isinstance(addr['addr'][1], int)
            assert addr['addr'][1] == address[1]
        locator.unregister(node)
        gevent.sleep(5)
        result = locator.get_neighbors()
        assert isinstance(result, list)
        #assert len(result) == 0

    def test_set_property(self):
        locator = self.locator
        node = self.crypto.randuuid()
        nodename = 'My Node'
        vault = self.crypto.randuuid()
        vaultname = 'My Vault'
        address = ('1.2.3.4', 100)
        locator.register(node, nodename, vault, vaultname, address)
        gevent.sleep(5)
        locator.set_property(node, 'foo', 'bar')
        gevent.sleep(5)
        result = locator.get_neighbors()
        assert isinstance(result, list)
        assert len(result) > 0
        result = result[0]
        assert 'properties' in result
        assert isinstance(result['properties'], dict)
        assert len(result['properties']) == 1
        assert 'foo' in result['properties']
        assert result['properties']['foo'] == 'bar'
        locator.set_property(node, 'baz', 'qux')
        gevent.sleep(5)
        result = locator.get_neighbors()
        gevent.sleep(5)
        assert isinstance(result, list)
        assert len(result) > 0
        result = result[0]
        assert 'properties' in result
        assert isinstance(result['properties'], dict)
        assert len(result['properties']) == 2
        assert 'foo' in result['properties']
        assert result['properties']['foo'] == 'bar'
        assert 'baz' in result['properties']
        assert result['properties']['baz'] == 'qux'
        locator.unregister(node)

########NEW FILE########
__FILENAME__ = test_model
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import time
import socket
import logging

from .unit import UnitTest, assert_raises
from bluepass.database import *
from bluepass.model import *


class TestModel(UnitTest):

    def setup(self):
        self.filename = self.tempfile()
        self.database = Database(self.filename)
        self.model = Model(self.database)

    def teardown(self):
        self.database.close()

    def test_config(self):
        model = self.model
        config = model.get_config()
        assert isinstance(config, dict)
        assert 'id' in config
        config['foo'] = 'bar'
        config['baz'] = { 'qux': 'quux' }
        model.update_config(config)
        config2 = model.get_config()
        assert config == config2

    def test_create_vault(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        assert vault['name'] == 'My Vault'
        assert 'id' in vault
        assert 'node' in vault
        assert 'keys' in vault

    def test_get_vaults(self):
        model = self.model
        uuid = model.create_vault('My Vault', 'Passw0rd')
        uuid2 = model.create_vault('His Vault', 'Passw0rd')
        vaults = model.get_vaults()
        assert len(vaults) == 2
        assert vaults[0]['name'] in ('My Vault', 'His Vault')
        assert vaults[1]['name'] in ('My Vault', 'His Vault')
        assert vaults[0]['name'] != vaults[1]['name']

    def test_update_vault(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        assert vault['name'] == 'My Vault'
        vault['name'] = 'His Vault'
        model.update_vault(vault)
        vault2 = model.get_vault(vault['id'])
        assert vault2['name'] == 'His Vault'

    def test_delete_vault(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        assert vault['name'] == 'My Vault'
        model.delete_vault(vault)
        vault = model.get_vault(vault['id'])
        assert vault is None

    def test_lock_vault(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        assert not model.vault_is_locked(vault['id'])
        model.lock_vault(vault['id'])
        assert model.vault_is_locked(vault['id'])

    def test_unlock_vault(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        assert not model.vault_is_locked(vault['id'])
        model.lock_vault(vault['id'])
        assert model.vault_is_locked(vault['id'])
        model.unlock_vault(vault['id'], 'Passw0rd')
        assert not model.vault_is_locked(vault['id'])

    def test_vault_open_close(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        version = model.add_version(vault['id'], {'foo': 'bar'})
        assert version['foo'] == 'bar'
        self.database.close()
        model2 = Model(Database(self.filename))
        model2.unlock_vault(vault['id'], 'Passw0rd')
        version2 = model2.get_version(vault['id'], version['id'])
        assert version2 is not None
        assert version2['foo'] == 'bar'

    def test_vault_password(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        version = model.add_version(vault['id'], {'foo': 'bar'})
        assert version['foo'] == 'bar'
        model.lock_vault(vault['id'])
        err = assert_raises(ModelError, model.get_version, vault['id'], version['id'])
        assert err.error_name == 'Locked'
        err = assert_raises(ModelError, model.unlock_vault, vault['id'], 'Passw!rd')
        assert err.error_name == 'WrongPassword'
        assert model.vault_is_locked(vault['id'])
        err = assert_raises(ModelError, model.get_version, vault['id'], version['id'])
        assert err.error_name == 'Locked'
        model.unlock_vault(vault['id'], 'Passw0rd')
        assert not model.vault_is_locked(vault['id'])
        version = model.get_version(vault['id'], version['id'])
        assert version is not None
        assert version['foo'] == 'bar'

    def test_add_version(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        version = model.add_version(vault['id'], {'foo': 'bar'})
        assert isinstance(version, dict)
        assert 'id' in version
        assert version['foo'] == 'bar'

    def test_update_version(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        version = model.add_version(vault['id'], {'foo': 'bar'})
        assert isinstance(version, dict)
        assert version['foo'] == 'bar'
        version['foo'] = 'baz'
        model.update_version(vault['id'], version)
        version2 = model.get_version(vault['id'], version['id'])
        assert version2['foo'] == 'baz'

    def test_delete_version(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        version = model.add_version(vault['id'], {'foo': 'bar'})
        version['deleted'] = True
        model.delete_version(vault['id'], version)
        history = model.get_version_history(vault['id'], version['id'])
        assert len(history) == 2
        assert 'id' in history[0]
        assert history[0]['id'] == history[1]['id']
        assert history[0]['deleted']
        version2 = model.get_version(vault['id'], version['id'])
        assert version2 is None

    def test_get_version_history(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        version = model.add_version(vault['id'], {'foo': 'bar'})
        assert version['foo'] == 'bar'
        version['foo'] = 'baz'
        model.update_version(vault['id'], version)
        version = model.get_version(vault['id'], version['id'])
        assert version['foo'] == 'baz'
        history = model.get_version_history(vault['id'], version['id'])
        assert len(history) == 2
        assert history[0]['foo'] == 'baz'
        assert history[1]['foo'] == 'bar'

    def test_concurrent_updates(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        version = model.add_version(vault['id'], {'foo': 'bar'})
        # Need to access some internals here to fake a concurrent update.
        vid = model._version_cache[vault['id']][version['id']]['payload']['id']
        def update_vid(vid, **kwargs):
            item = model._new_version(vault['id'], parent=vid, **kwargs)
            model._encrypt_item(vault['id'], item)
            model._add_origin(vault['id'], item)
            model._sign_item(vault['id'], item)
            model.import_item(vault['id'], item)
        update_vid(vid, id=version['id'], foo='baz')
        time.sleep(1)  # created_at has a resolution of 1 sec
        update_vid(vid, id=version['id'], foo='qux')
        history = model.get_version_history(vault['id'], version['id'])
        assert len(history) == 2
        assert history[0]['foo'] == 'qux'
        assert history[1]['foo'] == 'bar'

    def test_callbacks(self):
        model = self.model
        vault = model.create_vault('My Vault', 'Passw0rd')
        events = []
        def callback(event, *args):
            events.append((event, args))
        model.add_callback(callback)
        version = model.add_version(vault['id'], {'foo': 'bar'})
        assert len(events) == 1
        assert events[0] == ('VersionsAdded', (vault['id'], [version]))
        del version['foo']
        version['deleted'] = True
        version = model.delete_version(vault['id'], version)
        assert len(events) == 2
        assert events[1] == ('VersionsAdded', (vault['id'], [version]))

    def test_add_certificate(self):
        model1 = Model(Database(self.tempfile()))
        model2 = Model(Database(self.tempfile()))
        # Two vaults, with the same UUID, for pairng
        vault1 = model1.create_vault('My Vault', 'Passw0rd')
        vault2 = model2.create_vault('My Vault', 'Passw0rd', uuid=vault1['id'])
        assert vault1['id'] == vault2['id']
        version2 = model2.add_version(vault2['id'], {'foo': 'bar'})
        # Add certificate for node1 to node2. This will re-encrypt
        # the version for node1.
        certinfo = { 'node': vault1['node'], 'name': 'node1' }
        keys = certinfo['keys'] = {}
        for key in vault1['keys']:
            keys[key] = { 'key': vault1['keys'][key]['public'],
                          'keytype': vault1['keys'][key]['keytype'] }
        model2.add_certificate(vault2['id'], certinfo)
        history = model2.get_version_history(vault2['id'], version2['id'])
        assert len(history) == 2
        # Import items from model2 into model1. However, there is no cert
        # yet for node2, so the version should not become visible.
        items = model2.get_items(vault2['id'])
        model1.import_items(vault1['id'], items)
        version1 = model1.get_version(vault1['id'], version2['id'])
        assert version1 is None
        cert = model1.get_certificate(vault1['id'], vault2['node'])
        assert cert is None
        # Add a "synconly" certificate. This should not expose the version
        certinfo = { 'node': vault2['node'], 'name': 'node2' }
        keys = certinfo['keys'] = {}
        for key in vault1['keys']:
            keys[key] = { 'key': vault2['keys'][key]['public'],
                          'keytype': vault2['keys'][key]['keytype'] }
        certinfo['restrictions'] = { 'synconly': True }
        model1.add_certificate(vault1['id'], certinfo)
        cert = model1.get_certificate(vault1['id'], vault2['node'])
        assert cert is not None
        assert cert['payload']['node'] == vault2['node']
        assert cert['payload']['restrictions']['synconly']
        version1 = model1.get_version(vault1['id'], version2['id'])
        assert version1 is None
        # Now add a real certificate. the version should become visible now.
        certinfo = { 'node': vault2['node'], 'name': 'node2' }
        keys = certinfo['keys'] = {}
        for key in vault1['keys']:
            keys[key] = { 'key': vault2['keys'][key]['public'],
                          'keytype': vault2['keys'][key]['keytype'] }
        certinfo['restrictions'] = {}
        model1.add_certificate(vault1['id'], certinfo)
        cert = model1.get_certificate(vault1['id'], vault2['node'])
        assert cert is not None
        assert cert['payload']['node'] == vault2['node']
        assert not cert['payload'].get('restrictions', {}).get('synconly')
        version1 = model1.get_version(vault1['id'], version2['id'])
        assert version1 is not None
        assert version1['foo'] == 'bar'

########NEW FILE########
__FILENAME__ = test_passwords
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

from .unit import UnitTest
from bluepass.passwords import *


class TestPasswordGenerator(UnitTest):

    @classmethod
    def setup_class(cls):
        super(TestPasswordGenerator, cls).setup_class()
        cls.generator = PasswordGenerator()

    def test_generate_random(self):
        gen = self.generator
        pw = gen.generate('random', 20)
        assert isinstance(pw, bytes)
        assert len(pw) == 20
        pw = gen.generate('random', 20, 'ab')
        assert isinstance(pw, str)
        assert len(pw) == 20
        assert 'a' in pw
        assert 'b' in pw
        pw = gen.generate('random', 20, '[0-9]')
        assert isinstance(pw, str)
        assert len(pw) == 20
        assert pw.isdigit()
        pw = gen.generate('random', 20, '[0-]')
        assert isinstance(pw, str)
        assert len(pw) == 20
        assert '-' in pw
        pw = gen.generate('random', 20, '][[]')
        assert isinstance(pw, str)
        assert len(pw) == 20
        assert '[' in pw
        assert ']' in pw

    def test_generate_diceware(self):
        gen = self.generator
        pw = gen.generate('diceware', 6)
        assert isinstance(pw, str)
        assert len(pw) >= 11
        print(pw)
        assert pw.count(' ') == 5

########NEW FILE########
__FILENAME__ = test_qjsonrpc
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

from PyQt4.QtCore import QCoreApplication
from gruvi import jsonrpc

from unit import *
from bluepass.frontends.qt import qjsonrpc
from bluepass.frontends.qt.qjsonrpc import *


try:
    from socket import socketpair
except ImportError:
    from gruvi.socketpair import socketpair


def echo_app(message, client):
    if not message.get('id'):
        return
    method = message.get('method')
    if not method or method != 'echo':
        return
    args = message.get('params', ())
    response = qjsonrpc.create_response(message, args)
    client.send_message(response)

def blackhole_app(message, client):
    pass

_notifications = []

def notify_app(message, client):
    method = message.get('method')
    if not method:
        return
    if not message.get('id'):
        _notifications.append((method, message.get('params', ())))
    elif method == 'get':
        response = qjsonrpc.create_response(message, _notifications)
        client.send_message(response)


class TestQJsonRpc(UnitTest):

    @classmethod
    def setUpClass(cls):
        super(TestQJsonRpc, cls).setUpClass()
        qapp = QCoreApplication.instance()
        if qapp is None:
            qapp = QCoreApplication([])
        cls.qapp = qapp

    def test_request(self):
        csock, ssock = socketpair()
        client = QJsonRpcClient()
        client.connect(csock)
        server = QJsonRpcClient(echo_app)
        server.connect(ssock)
        result = client.call_method('echo', 'foo')
        self.assertEqual(result, ['foo'])

    def test_request_timeout(self):
        csock, ssock = socketpair()
        client = QJsonRpcClient(timeout=0.1)
        self.assertEqual(client.timeout, 0.1)
        client.connect(csock)
        server = QJsonRpcClient(blackhole_app)
        server.connect(ssock)
        self.assertRaises(QJsonRpcError, client.call_method, 'echo', 'foo')

    def test_notification(self):
        csock, ssock = socketpair()
        client = QJsonRpcClient()
        client.connect(csock)
        server = QJsonRpcClient(notify_app)
        server.connect(ssock)
        client.send_notification('notify')
        client.send_notification('notify', 'foo')
        client.send_notification('notify', 'bar', 'baz')
        notifications = client.call_method('get')
        self.assertEquals(notifications, [['notify', []], ['notify', ['foo']],
                                          ['notify', ['bar', 'baz']]])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_syncapi
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import time

from gevent import socket
from gevent.event import Event

from .unit import UnitTest
from bluepass.factory import create, instance
from bluepass.database import Database
from bluepass.model import Model
from bluepass.syncapi import *
from bluepass.messagebus import *


class MBTestHandler(MessageBusHandler):

    @method()
    def get_pairing_approval(self, name, uuid, pin, kxid):
        self.name = name
        self.pin = pin
        return True, {}


class TestSyncAPI(UnitTest):

    def test_pair_and_sync(self):
        # Create two databases and two models
        database1 = Database(self.tempfile())
        model1 = create(Model, database1)
        assert instance(Model) is model1
        vault1 = model1.create_vault('Vault1', 'Passw0rd')
        database2 = Database(self.tempfile())
        model2 = Model(database2)
        vault2 = model2.create_vault('Vault2', 'Passw0rd', uuid=vault1['id'])
        # Start a message bus server and client connection
        lsock = socket.socket()
        lsock.bind(('localhost', 0))
        lsock.listen(2)
        mbserver = create(MessageBusServer, lsock, 'S3cret', None)
        #mbserver.set_trace('/tmp/server.txt')
        mbserver.start()
        csock = socket.socket()
        csock.connect(lsock.getsockname())
        mbhandler = MBTestHandler()
        mbclient = MessageBusConnection(csock, 'S3cret', mbhandler)
        #mbclient.set_trace('/tmp/client.txt')
        # Start the syncapi
        lsock = socket.socket()
        lsock.bind(('localhost', 0))
        lsock.listen(2)
        address = lsock.getsockname()
        syncapp = SyncAPIApplication()
        syncapp.allow_pairing = True
        server = SyncAPIServer(lsock, syncapp)
        server.start()
        # Pair with vault1
        client = SyncAPIClient(lsock.getsockname())
        client.connect()
        kxid = client.pair_step1(vault1['id'], 'foo')
        assert kxid is not None
        assert mbhandler.name == 'foo'
        certinfo = { 'name': 'node2', 'node': vault2['node'] }
        keys = certinfo['keys'] = {}
        for key in vault2['keys']:
            keys[key] = { 'key': vault2['keys'][key]['public'],
                          'keytype': vault2['keys'][key]['keytype'] }
        peercert = client.pair_step2(vault1['id'], kxid, mbhandler.pin, certinfo)
        assert isinstance(peercert, dict)
        assert model1.check_certinfo(peercert)[0]
        model2.add_certificate(vault2['id'], peercert)
        # Sync
        version1 = model1.add_version(vault1['id'], {'foo': 'bar'})
        client.sync(vault1['id'], model2)
        version2 = model2.get_version(vault1['id'], version1['id'])
        assert version2 is not None
        assert version2['foo'] == 'bar'

########NEW FILE########
__FILENAME__ = unit
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import os
import sys
import shutil
import tempfile
import unittest

if sys.version_info[:2] >= (2,7):
    import unittest
else:
    import unittest2 as unittest

SkipTest = unittest.SkipTest

__all__ = ['UnitTest', 'SkipTest', 'unittest']


def assert_raises(exc, func, *args):
    """Like nose.tools.assert_raises but returns the exception."""
    try:
        func(*args)
    except Exception as e:
        if isinstance(e, exc):
            return e
        raise
    raise AssertionError('%s not raised' % exc.__name__)


class UnitTest(unittest.TestCase):
    """Base class for unit tests."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.prevdir = os.getcwd()
        os.chdir(cls.tmpdir)
        cls.tmpdirs = []

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.prevdir)
        shutil.rmtree(cls.tmpdir)
        for tmpdir in cls.tmpdirs:
            shutil.rmtree(tmpdir)

    def tempfile(self):
        return tempfile.mkstemp(dir=self.tmpdir)[1]

    def tempdir(self):
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        return tmpdir

    def write_file(self, fname, contents):
        fout = file(fname, 'w')
        fout.write(contents)
        fout.close()

    def assertRaises(self, exc, func, *args, **kwargs):
        # Like unittest.assertRaises, but returns the exception.
        try:
            func(*args, **kwargs)
        except exc as e:
            exc = e
        except Exception as e:
            self.fail('Wrong exception raised: {0!s}'.format(e))
        else:
            self.fail('Exception not raised: {0!s}'.format(exc))
        return exc

########NEW FILE########
__FILENAME__ = test_json
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

from ..unit import UnitTest, assert_raises
from bluepass.util.json import *


class TestJSON(object):

    def test_unpack_simple(self):
        values = unpack(True, 'b')
        assert values == (True,)
        values = unpack(10, 'i')
        assert values == (10,)
        values = unpack('test', 's')
        assert values == ('test',)
        values = unpack(1.618, 'f')
        assert values == (1.618,)
        values = unpack({'foo':'bar'}, 'o')
        assert values == ({'foo':'bar'},)

    def test_unsigned_int(self):
        values = unpack(0, 'u')
        assert values == (0,)
        values = unpack(1, 'u')
        assert values == (1,)
        assert_raises(UnpackError, unpack, -1, 'u')

    def test_unpack_object(self):
        doc = {'foo': 'bar', 'baz': 'qux'}
        values = unpack(doc, '{s:s,s:s}', ('foo', 'baz'))
        assert values == ('bar', 'qux')

    def test_unpack_nested_object(self):
        doc = {'foo': {'bar': 'baz'}}
        values = unpack(doc, '{s:{s:s}}', ('foo', 'bar'))
        assert values == ('baz',)

    def test_unpack_critical_object(self):
        doc = {'foo': 'bar', 'baz': 'qux'}
        values = unpack(doc, '{s:s,s:s!}', ('foo', 'baz'))
        assert values == ('bar', 'qux')
        assert_raises(UnpackError, unpack, doc, '{s:s!}', ('foo',))
        values = unpack(doc, '{s:s*}', ('foo',))
        assert values == ('bar',)
        values = unpack(doc, '{s:s}', ('foo',))
        assert values == ('bar',)

    def test_unpack_object_with_optional_keys(self):
        doc = {'foo': 'bar'}
        values = unpack(doc, '{s:s,s?:s}', ('foo', 'baz'))
        assert values == ('bar', None)

    def test_unpack_list(self):
        doc = ['foo', 'bar']
        values = unpack(doc, '[ss]')
        assert values == ('foo', 'bar')

    def test_unpack_nested_list(self):
        doc = ['foo', ['bar', 'baz']]
        values = unpack(doc, '[s[ss]]')
        assert values == ('foo', 'bar', 'baz')

    def test_unpack_critical_list(self):
        doc = ['foo', 'bar']
        values = unpack(doc, '[ss!]')
        assert values == ('foo', 'bar')
        assert_raises(UnpackError, unpack, doc, '[s!]')
        values = unpack(doc, '[s*]')
        assert values == ('foo',)
        values = unpack(doc, '[s]')
        assert values == ('foo',)

########NEW FILE########
__FILENAME__ = test_ssl
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.

from __future__ import absolute_import, print_function

import os
import gevent
from gevent import socket
import subprocess
from subprocess import PIPE

from ..unit import UnitTest
from bluepass import crypto
from bluepass.util.ssl import SSLSocket


class TestSSL(UnitTest):

    def _create_certificate(self, fname, subject):
        ret = subprocess.call(['openssl', 'req', '-new', '-newkey',
                'rsa:1024', '-x509', '-subj', subject, '-days', '365',
                '-nodes', '-out', fname, '-keyout', fname],
                stdout=PIPE, stderr=PIPE)
        if ret != 0:
            raise RuntimeError('Failed to generated certificate')
        return fname

    def test_channel_binding(self):
        self._create_certificate('server.pem', '/CN=foo/')
        cb = []; data = []
        def server(sock):
            conn, addr = sock.accept()
            sslsock = SSLSocket(conn, server_side=True,
                             keyfile='server.pem', certfile='server.pem')
            cb.append(sslsock.get_channel_binding())
            buf = sslsock.read()
            data.append(buf)
            conn = sslsock.unwrap()
            conn.close()
        def client(sock, addr):
            sock.connect(addr)
            sslsock = SSLSocket(sock)
            cb.append(sslsock.get_channel_binding())
            sslsock.write('foo')
            data.append('foo')
            sslsock.unwrap()
        s1 = socket.socket()
        s1.bind(('localhost', 0))
        s1.listen(2)
        s2 = socket.socket()
        g1 = gevent.spawn(server, s1)
        g2 = gevent.spawn(client, s2, s1.getsockname())
        gevent.joinall([g1, g2])
        s1.close(); s2.close()
        assert len(cb) == 2
        assert len(cb[0]) in (12, 36)
        assert cb[0] == cb[1]
        assert len(data) == 2
        assert data[0] == data[1]

    def test_anon_dh(self):
        dhparams = crypto.dhparams['skip2048']
        data = []; ciphers = []; cb = []
        def server(sock):
            conn, addr = sock.accept()
            sslsock = SSLSocket(conn, server_side=True,
                                  dhparams=dhparams, ciphers='ADH+AES')
            buf = sslsock.read()
            data.append(buf)
            ciphers.append(sslsock.cipher())
            cb.append(sslsock.get_channel_binding())
            conn = sslsock.unwrap()
            conn.close()
        def client(sock, addr):
            sock.connect(addr)
            sslsock = SSLSocket(sock, ciphers='ADH+AES')
            sslsock.write('foo')
            data.append('foo')
            ciphers.append(sslsock.cipher())
            cb.append(sslsock.get_channel_binding())
            sslsock.unwrap()
        s1 = socket.socket()
        s1.bind(('localhost', 0))
        s1.listen(2)
        s2 = socket.socket()
        g1 = gevent.spawn(server, s1)
        g2 = gevent.spawn(client, s2, s1.getsockname())
        gevent.joinall([g1, g2])
        s1.close(); s2.close()
        assert len(data) == 2
        assert len(data[0]) > 0
        assert data[0] == data[1]
        assert len(ciphers) == 2
        assert len(ciphers[0]) > 0
        assert ciphers[0] == ciphers[1]
        assert 'ADH' in ciphers[0][0]
        assert len(cb) == 2
        assert len(cb[0]) in (12, 36)
        assert cb[0] == cb[1]

########NEW FILE########
__FILENAME__ = aesvect
#!/usr/bin/env python
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.
#
# This script generates AES test vectors of different lengths. The
# test vectors are created by encrypting random input via "openssl"
# command line utility to encrypt random input.

import os
import sys
import time
from subprocess import Popen, PIPE

sys.stdout.write('# Generated by: %s on %s\n' % (sys.argv[0], time.ctime()))

for keysize in (16, 24, 32):
    for ptlen in (0, 8, 14, 15, 16, 23, 31, 32, 42, 48, 64):
        key = os.urandom(keysize)
        iv = os.urandom(16)
        pt = os.urandom(ptlen)
        algo = '-aes-%d-cbc' % (keysize*8)
        cmd = Popen(['openssl', 'enc', '-e', algo, '-K', key.encode('hex'),
                    '-iv', iv.encode('hex')], stdin=PIPE, stdout=PIPE)
        ct, stderr = cmd.communicate(pt)
        sys.stdout.write('\n')
        sys.stdout.write('PT=%s\n' % pt.encode('hex'))
        sys.stdout.write('KEY=%s\n' % key.encode('hex'))
        sys.stdout.write('IV=%s\n' % iv.encode('hex'))
        sys.stdout.write('CT=%s\n' % ct.encode('hex'))

########NEW FILE########
__FILENAME__ = oakley
#!/usr/bin/env python
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.
#
# This script outputs the first and second "Oakley" groups from RFC2409
# in base64 encoded PKCS#3 "DHParameter" format. These groups are used in
# the Freedestop secrets service.
#
# The keys can be found in section 6.1 and 6.2 in the RFC here:
# http://www.ietf.org/rfc/rfc2409.txt

from pyasn1.codec.der import encoder
from pyasn1.type.univ import Sequence, Integer
from pyasn1.type.namedtype import NamedTypes, NamedType


oakley1 = """
         FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1
         29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD
         EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245
         E485B576 625E7EC6 F44C42E9 A63A3620 FFFFFFFF FFFFFFFF
        """
oakley2 = """
         FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1
         29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD
         EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245
         E485B576 625E7EC6 F44C42E9 A637ED6B 0BFF5CB6 F406B7ED
         EE386BFB 5A899FA5 AE9F2411 7C4B1FE6 49286651 ECE65381
         FFFFFFFF FFFFFFFF
        """

class DHParameter(Sequence):
    componentType = NamedTypes(
        NamedType('prime', Integer()),
        NamedType('base', Integer()))

def format_asn1(hexfmt):
    s = hexfmt.replace(' ', '').replace('\n', '')
    i = int(s, 16)
    params = DHParameter()
    params.setComponentByName('prime', i)
    params.setComponentByName('base', 2)
    return encoder.encode(params).encode('base64').rstrip()

print 'Oakley #1:'
print format_asn1(oakley1)
print

print 'Oakley #2:'
print format_asn1(oakley2)
print

########NEW FILE########
__FILENAME__ = pkcs1vect
#!/usr/bin/env python
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.
#
# This script reads the PKCS1 v2.1 test vectors as input and formats
# them in a way that is understood by our tests. The script understands
# test vectors for both encryption with OAEP and signatures with PSS.
#
# The input file that is needed for this program can be downloaded here:
# ftp://ftp.rsasecurity.com/pub/pkcs/pkcs-1/pkcs-1v2-1-vec.zip

import sys
import time

from pyasn1.codec.der import encoder
from pyasn1.type.univ import Sequence, Integer
from pyasn1.type.namedtype import NamedTypes, NamedType

if len(sys.argv) != 2:
    sys.stderr.write('Usage: %s <file>\n' % sys.argv[0])
    sys.exit(1)
fname = sys.argv[1]

tagmap = {
    'Message to be encrypted': 'PT', 'Seed': 'SEED', 'Encryption': 'CT',
    'Message to be signed': 'MSG', 'Salt': 'SALT', 'Signature': 'SIG'
}

s_sync, s_read_tag, s_read_value = range(3)
state = s_sync
records = []
for line in file(fname):
    line = line.rstrip()
    if state == s_sync:
        if not line:
            state = s_read_tag
    elif state == s_read_tag:
        if not line:
            continue
        if not line.startswith('#') or not line.endswith(':'):
            state = s_sync
            continue
        tag = line[2:-1]
        if tag in tagmap:
            tag = tagmap[tag]
        else:
            tag = tag.split()[-1]
        value = ''
        state = s_read_value
    elif state == s_read_value:
        if not line:
            records.append((tag, value))
            state = s_read_tag
            continue
        value += line.replace(' ', '')


vectors = []
for tag,value in records:
    if tag == 'n':
        key = {}
    if tag == 'PT':
        vector = key.copy()
    if tag in ('n', 'e', 'd', 'p', 'q', 'dP', 'dQ', 'qInv'):
        key[tag] = value
    else:
        vector[tag] = value
    if tag in ('CT', 'SIG'):
        vectors.append(vector)


class RSAPublicKey(Sequence):
    componentType = NamedTypes(
        NamedType('n', Integer()),
        NamedType('e', Integer()))

class RSAPrivateKey(Sequence):
    componentType = NamedTypes(
        NamedType('version', Integer()),
        NamedType('n', Integer()),
        NamedType('e', Integer()),
        NamedType('d', Integer()),
        NamedType('p', Integer()),
        NamedType('q', Integer()),
        NamedType('dP', Integer()),
        NamedType('dQ', Integer()),
        NamedType('qInv', Integer()))


for vector in vectors:
    pubkey = RSAPublicKey()
    for comp in ('n', 'e'):
        pubkey.setComponentByName(comp, int(vector[comp], 16))
    vector['PUBKEY'] = encoder.encode(pubkey).encode('hex')
    privkey = RSAPrivateKey()
    privkey.setComponentByName('version', 0)
    for comp in ('n', 'e', 'd', 'p', 'q', 'dP', 'dQ', 'qInv'):
        privkey.setComponentByName(comp, int(vector[comp], 16))
    vector['PRIVKEY'] = encoder.encode(privkey).encode('hex')


sys.stdout.write('# Generated by %s from %s on %s\n' % 
                 (sys.argv[0], sys.argv[1], time.ctime()))
for vector in vectors:
    sys.stdout.write('\n')
    for tag in ('PT', 'MSG', 'PUBKEY', 'PRIVKEY', 'SEED', 'CT', 'SALT', 'SIG'):
        if tag in vector:
            sys.stdout.write('%s=%s\n' % (tag, vector[tag]))

########NEW FILE########
__FILENAME__ = strength
#!/usr/bin/env python
#
# This file is part of Bluepass. Bluepass is Copyright (c) 2012-2013
# Geert Jansen.
#
# Bluepass is free software available under the GNU General Public License,
# version 3. See the file LICENSE distributed with this file for the exact
# licensing terms.
#
# This script calculates the strength of the Diceware(r) passphrases we
# generate under our PBKDF2 key derivation algorithm for various adversaries.
# The model takes into account Moore's law and contains a few tunable knobs.

import sys
import math

# Keys per year for one core. Assume only 10 keys per second due
# to the key stretching that is employed.
a = 10*86400*365
# Moore's law exponent: the 18-month variant
b = math.log(2) / 1.5
# Our adversaries with the # of cores they have available
adversaries = [(10, 'Home User'), (10000, 'Organized Crime'),
               (10000000, 'Govt Agency')]

def format_years(y):
    if y < 1.0/365/24/60:
        return '%.2f seconds' % (1.0 * y * 365 * 24 * 60 * 60)
    elif y < 1.0/365/24:
        return '%.2f minutes' % (1.0 * y * 365 * 24 * 60)
    elif y < 1.0/365:
        return '%.2f hours' % (1.0 * y * 365 * 24)
    elif y < 1.0:
        return '%.2f days' % (1.0 * y * 365)
    elif y < 10.0:
        return '%.2f years' % y
    elif y < 100.0:
        return '%.1f years' % y
    else:
        return '%.0f years' % y

rows = [['Words', 'Bits'] + [adv[1] for adv in adversaries]]

for keysize in range(1,7):
    keys = 6 ** (5 * keysize)
    bits = math.log(keys, 2)
    line = [str(keysize), str('%.2f' % bits)]
    for adv in adversaries:
        nkeys = 0
        for yr in range(1,1000):
            speed = adv[0] * a * math.exp(b*yr)
            nkeys += speed
            if nkeys > keys/2:
                tdesc = format_years(1.0 * yr * keys / 2 / nkeys)
                break
        else:
            tdesc = '> 1.000 years'
        line.append(tdesc)
    rows.append(line)

ncols = 2 + len(adversaries)
colsize = [0] * ncols
for row in rows:
    for ix in range(ncols):
        colsize[ix] = max(colsize[ix], len(row[ix]))
fmt = [ '%%-%ds' % sz for sz in colsize ]

print '  '.join(fmt[i] % rows[0][i] for i in range(ncols))
print '  '.join('-' * colsize[i] for i in range(ncols))
for row in rows[1:]:
    print '  '.join(fmt[i] % row[i] for i in range(ncols))

########NEW FILE########
