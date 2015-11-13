__FILENAME__ = compat
from ctypes import string_at, create_string_buffer

from MySQLdb import libmysql


def string_literal(obj):
    obj = str(obj)
    buf = create_string_buffer(len(obj) * 2)
    length = libmysql.c.mysql_escape_string(buf, obj, len(obj))
    return "'%s'" % string_at(buf, length)
########NEW FILE########
__FILENAME__ = connection
import contextlib
from ctypes import (addressof, cast, create_string_buffer, string_at, c_char,
    c_uint, POINTER)

from MySQLdb import cursors, libmysql, converters
from MySQLdb.constants import error_codes


class Connection(object):
    # This alias is for use in stuff called via __del__, which needs to be sure
    # it has a hard ref, so it isn't None'd out.
    _mysql_close = libmysql.c.mysql_close

    MYSQL_ERROR_MAP = {
        error_codes.PARSE_ERROR: "ProgrammingError",
        error_codes.NO_SUCH_TABLE: "ProgrammingError",

        error_codes.DATA_TOO_LONG: "DataError",

        error_codes.DUP_ENTRY: "IntegrityError",
        error_codes.ROW_IS_REFERENCED_2: "IntegrityError",
    }

    from MySQLdb.exceptions import (Warning, Error, InterfaceError,
        DataError, DatabaseError, OperationalError, IntegrityError,
        InternalError, ProgrammingError, NotSupportedError)

    def __init__(self, host=None, user=None, passwd=None, db=None, port=0,
        client_flag=0, charset=None, init_command=None, connect_timeout=None,
        sql_mode=None, encoders=None, decoders=None, use_unicode=True):

        self._db = libmysql.c.mysql_init(None)

        if connect_timeout is not None:
            connect_timeout = c_uint(connect_timeout)
            res = libmysql.c.mysql_options(self._db,
                libmysql.MYSQL_OPT_CONNECT_TIMEOUT,
                cast(addressof(connect_timeout), POINTER(c_char))
            )
            if res:
                self._exception()
        if init_command is not None:
            res = libmysql.c.mysql_options(self._db,
                libmysql.MYSQL_INIT_COMMAND, init_command
            )
            if res:
                self._exception()

        res = libmysql.c.mysql_real_connect(self._db, host, user, passwd, db, port, None, client_flag)
        if not res:
            self._exception()

        if encoders is None:
            encoders = converters.DEFAULT_ENCODERS
        if decoders is None:
            decoders = converters.DEFAULT_DECODERS
        self.encoders = encoders
        self.decoders = decoders

        if charset is not None:
            res = libmysql.c.mysql_set_character_set(self._db, charset)
            if res:
                self._exception()

        if sql_mode is not None:
            with contextlib.closing(self.cursor()) as cursor:
                cursor.execute("SET SESSION sql_mode=%s", (sql_mode,))

        self.autocommit(False)

    def __del__(self):
        if not self.closed:
            self.close()

    def _check_closed(self):
        if self.closed:
            raise self.InterfaceError(0, "")

    def _has_error(self):
        return libmysql.c.mysql_errno(self._db) != 0

    def _exception(self):
        err = libmysql.c.mysql_errno(self._db)
        if not err:
            err_cls = self.InterfaceError
        else:
            if err in self.MYSQL_ERROR_MAP:
                err_cls = getattr(self, self.MYSQL_ERROR_MAP[err])
            elif err < 1000:
                err_cls = self.InternalError
            else:
                err_cls = self.OperationalError
        raise err_cls(err, libmysql.c.mysql_error(self._db))

    @property
    def closed(self):
        return self._db is None

    def close(self):
        self._check_closed()
        self._mysql_close(self._db)
        self._db = None

    def autocommit(self, flag):
        self._check_closed()
        res = libmysql.c.mysql_autocommit(self._db, chr(flag))
        if ord(res):
            self._exception()

    def commit(self):
        self._check_closed()
        res = libmysql.c.mysql_commit(self._db, "COMMIT")
        if ord(res):
            self._exception()

    def rollback(self):
        self._check_closed()
        res = libmysql.c.mysql_rollback(self._db)
        if ord(res):
            self._exception()

    def cursor(self, cursor_class=None, encoders=None, decoders=None):
        if cursor_class is None:
            cursor_class = cursors.Cursor
        if encoders is None:
            encoders = self.encoders[:]
        if decoders is None:
            decoders = self.decoders[:]
        return cursor_class(self, encoders=encoders, decoders=decoders)

    def string_literal(self, obj):
        self._check_closed()
        obj = str(obj)
        buf = create_string_buffer(len(obj) * 2)
        length = libmysql.c.mysql_real_escape_string(self._db, buf, obj, len(obj))
        return "'%s'" % string_at(buf, length)

    def character_set_name(self):
        self._check_closed()
        return libmysql.c.mysql_character_set_name(self._db)

    def get_server_info(self):
        self._check_closed()
        return libmysql.c.mysql_get_server_info(self._db)

def connect(*args, **kwargs):
    return Connection(*args, **kwargs)
########NEW FILE########
__FILENAME__ = CLIENT
# File is named this way because that's how it is in MySQLdb, and SQLAlchemy
# looks for it.

FOUND_ROWS = 2
########NEW FILE########
__FILENAME__ = error_codes
DUP_ENTRY = 1062
PARSE_ERROR = 1064
NO_SUCH_TABLE = 1146
DATA_TOO_LONG = 1406
ROW_IS_REFERENCED_2 = 1451
########NEW FILE########
__FILENAME__ = field_types
DECIMAL = 0
TINY = 1
SHORT = 2
LONG = 3
FLOAT = 4
DOUBLE = 5
NULL = 6
TIMESTAMP = 7
LONGLONG = 8
INT24 = 9
DATE = 10
TIME = 11
DATETIME = 12
YEAR = 13
NEWDATE = 14
VARCHAR = 15
BIT = 16
NEWDECIMAL = 246
ENUM = 247
SET = 248
TINY_BLOB = 249
MEDIUM_BLOB = 250
LONG_BLOB = 251
BLOB = 252
VAR_STRING = 253
STRING = 254
GEOMETRY = 255

CHAR = TINY
INTERVAL = ENUM
########NEW FILE########
__FILENAME__ = converters
import math
from datetime import datetime, date, time, timedelta
from decimal import Decimal

from MySQLdb.constants import field_types


def literal(value):
    return lambda conn, obj: value

def unicode_to_quoted_sql(connection, obj):
    return connection.string_literal(obj.encode(connection.character_set_name()))

def object_to_quoted_sql(connection, obj):
    if hasattr(obj, "__unicode__"):
        return unicode_to_quoted_sql(connection, unicode(obj))
    return connection.string_literal(str(obj))

def fallback_encoder(obj):
    return object_to_quoted_sql

def literal_encoder(connection, obj):
    return str(obj)

def datetime_encoder(connection, obj):
    return connection.string_literal(obj.strftime("%Y-%m-%d %H:%M:%S"))

_simple_field_encoders = {
    type(None): lambda connection, obj: "NULL",
    int: literal_encoder,
    bool: lambda connection, obj: str(int(obj)),
    unicode: unicode_to_quoted_sql,
    datetime: datetime_encoder,
}

def simple_encoder(obj):
    return _simple_field_encoders.get(type(obj))

DEFAULT_ENCODERS = [
    simple_encoder,
    fallback_encoder,
]


def datetime_decoder(value):
    date_part, time_part = value.split(" ", 1)
    return datetime.combine(
        date_decoder(date_part),
        time(*[int(part) for part in time_part.split(":")])
    )

def date_decoder(value):
    return date(*[int(part) for part in value.split("-")])

def time_decoder(value):
    # MySQLdb returns a timedelta here, immitate this nonsense.
    hours, minutes, seconds = value.split(":")
    td = timedelta(
        hours = int(hours),
        minutes = int(minutes),
        seconds = int(seconds),
        microseconds = int(math.modf(float(seconds))[0]*1000000),
    )
    if hours < 0:
        td = -td
    return td

def timestamp_decoder(value):
    if " " in value:
        return datetime_decoder(value)
    raise NotImplementedError

_simple_field_decoders = {
    field_types.TINY: int,
    field_types.SHORT: int,
    field_types.LONG: int,
    field_types.LONGLONG: int,
    field_types.YEAR: int,

    field_types.FLOAT: float,
    field_types.DOUBLE: float,

    field_types.DECIMAL: Decimal,
    field_types.NEWDECIMAL: Decimal,

    field_types.BLOB: str,
    field_types.VAR_STRING: str,
    field_types.STRING: str,

    field_types.DATETIME: datetime_decoder,
    field_types.DATE: date_decoder,
    field_types.TIME: time_decoder,
    field_types.TIMESTAMP: timestamp_decoder,
}

def fallback_decoder(connection, field):
    return _simple_field_decoders.get(field[1])

DEFAULT_DECODERS = [
    fallback_decoder,
]
########NEW FILE########
__FILENAME__ = cursors
import collections
import ctypes
import itertools
import re
import warnings
import weakref

from MySQLdb import libmysql


INSERT_VALUES = re.compile(
    r"(?P<start>.+values\s*)"
    r"(?P<values>\(((?<!\\)'[^\)]*?\)[^\)]*(?<!\\)?'|[^\(\)]|(?:\([^\)]*\)))+\))"
    r"(?P<end>.*)",
    re.I
)



class Cursor(object):
    def __init__(self, connection, encoders, decoders):
        self.connection = weakref.proxy(connection)
        self.arraysize = 1
        self.encoders = encoders
        self.decoders = decoders

        self._result = None
        self._executed = None
        self.rowcount = -1

    def __del__(self):
        self.close()

    def _check_closed(self):
        if not self.connection or not self.connection._db:
            raise self.connection.InterfaceError(0, "")

    def _check_executed(self):
        if not self._executed:
            raise self.connection.ProgrammingError("execute() first")

    def _clear(self):
        if self._result is not None:
            self._result.close()
            self._result = None
        self.rowcount = -1

    def _query(self, query):
        self._executed = query
        self.connection._check_closed()
        r = libmysql.c.mysql_real_query(self.connection._db, ctypes.c_char_p(query), len(query))
        if r:
            self.connection._exception()
        self._result = Result(self)

    def _get_encoder(self, val):
        for encoder in self.encoders:
            res = encoder(val)
            if res:
                return res

    def _get_decoder(self, val):
        for decoder in self.decoders:
            res = decoder(self.connection, val)
            if res:
                return res

    def _escape_data(self, args):
        self._check_closed()
        # MySQLdb's argument escaping rules are completely at odds with the
        # DB-API spec, unfortunately the project this codebase was originally
        # written for uses those features, so we emulate them.
        if isinstance(args, collections.Sequence) and not isinstance(args, basestring):
            return tuple([
                self._get_encoder(arg)(self.connection, arg)
                for arg in args
            ])
        elif isinstance(args, collections.Mapping):
            return dict([
                (key, self._get_encoder(value)(self.connection, value))
                for key, value in args.iteritems()
            ])
        else:
            return self._get_encoder(args)(self.connection, args)

    @property
    def description(self):
        if self._result is not None:
            return self._result.description
        return None

    def __iter__(self):
        return iter(self.fetchone, None)

    def close(self):
        self.connection = None
        if self._result is not None:
            self._result.close()
            self._result = None

    def execute(self, query, args=None):
        self._check_closed()
        self._clear()

        if isinstance(query, unicode):
            query = query.encode(self.connection.character_set_name())
        if args is not None:
            query %= self._escape_data(args)
        self._query(query)

    def executemany(self, query, args):
        self._check_closed()
        self._clear()
        if not args:
            return

        if isinstance(query, unicode):
            query = query.encode(self.connection.character_set_name())
        matched = INSERT_VALUES.match(query)
        if not matched:
            rowcount = 0
            for arg in args:
                self.execute(query, arg)
                rowcount += self.rowcount
            self.rowcount = rowcount
        else:
            start, values, end = matched.group("start", "values", "end")
            sql_params = [
                values % self._escape_data(arg)
                for arg in args
            ]
            multirow_query = start + ",\n".join(sql_params) + end
            self._query(multirow_query)
        return self.rowcount

    def callproc(self, procname, args=()):
        self._check_closed()
        self._clear()

        query = "SELECT %s(%s)" % (procname, ",".join(["%s"] * len(args)))
        if isinstance(query, unicode):
            query = query.encode(self.connection.character_set_name())
        query %= self._escape_data(args)
        self._query(query)
        return args


    def fetchall(self):
        self._check_executed()
        if not self._result:
            return []
        return self._result.fetchall()

    def fetchmany(self, size=None):
        self._check_executed()
        if not self._result:
            return []
        if size is None:
            size = self.arraysize
        return self._result.fetchmany(size)

    def fetchone(self):
        self._check_executed()
        if not self._result:
            return None
        return self._result.fetchone()

    def setinputsizes(self, *args):
        pass

    def setoutputsize(self, *args):
        pass

class DictCursor(Cursor):
    def _make_row(self, row):
        return dict(
            (description[0], value)
            for description, value in itertools.izip(self._result.description, row)
        )

    def fetchall(self):
        rows = super(DictCursor, self).fetchall()
        return [self._make_row(row) for row in rows]

    def fetchmany(self, size=None):
        rows = super(DictCursor, self).fetchmany(size)
        return [self._make_row(row) for row in rows]

    def fetchone(self):
        row = super(DictCursor, self).fetchone()
        if row is not None:
            row = self._make_row(row)
        return row

_Description = collections.namedtuple("Description", [
    "name", "type_code", "display_size", "internal_size", "precision", "scale", "null_ok"
])
class Description(_Description):
    def __new__(cls, *args, **kwargs):
        charsetnr = kwargs.pop("charsetnr")
        self = super(Description, cls).__new__(cls, *args, **kwargs)
        self.charsetnr = charsetnr
        return self

class Result(object):
    def __init__(self, cursor):
        self.cursor = cursor
        self._result = libmysql.c.mysql_store_result(self.cursor.connection._db)
        self.description = None
        self.rows = None
        self.row_index = 0
        # TOOD: this is a hack, find a better way.
        if self.cursor._executed.upper().startswith("CREATE"):
            cursor.rowcount = -1
        else:
            cursor.rowcount = libmysql.c.mysql_affected_rows(cursor.connection._db)
        if not self._result:
            cursor.lastrowid = libmysql.c.mysql_insert_id(cursor.connection._db)
            return


        self.description = self._describe()
        self.row_decoders = [
            self.cursor._get_decoder(field)
            for field in self.description
        ]

        self.rows = []

    def _get_row(self):
        row = libmysql.c.mysql_fetch_row(self._result)
        if not row:
            if self.cursor.connection._has_error():
                self.cursor.connection.exception()
            return
        n = libmysql.c.mysql_num_fields(self._result)
        lengths = libmysql.c.mysql_fetch_lengths(self._result)
        r = [None] * n
        for i, decoder in enumerate(self.row_decoders):
            if not row[i]:
                r[i] = None
            else:
                val = ctypes.string_at(row[i], lengths[i])
                if decoder is None:
                    raise self.cursor.connection.InternalError("No decoder for"
                        " type %s, value: %s" % (self.description[i][1], val)
                    )
                r[i] = decoder(val)

        return tuple(r)

    def _describe(self):
        n = libmysql.c.mysql_num_fields(self._result)
        fields = libmysql.c.mysql_fetch_fields(self._result)
        d = [None] * n
        for i in xrange(n):
            f = fields[i]
            d[i] = Description(
                ctypes.string_at(f.name, f.name_length),
                f.type,
                f.max_length,
                f.length,
                f.length,
                f.decimals,
                None,
                charsetnr=f.charsetnr
            )
        return tuple(d)

    def _check_rows(self, meth):
        if self.rows is None:
            raise self.cursor.connection.ProgrammingError("Can't %s from a "
                "query with no result rows" % meth)

    def close(self):
        if self._result:
            libmysql.c.mysql_free_result(self._result)
        self._result = None

    def flush(self):
        if self._result:
            while True:
                row = self._get_row()
                if row is None:
                    break
                self.rows.append(row)

    def fetchall(self):
        self._check_rows("fetchall")
        if self._result:
            self.flush()
        rows = self.rows[self.row_index:]
        self.row_index = len(self.rows)
        return rows

    def fetchmany(self, size):
        self._check_rows("fetchmany")
        if self._result:
            for i in xrange(size - (len(self.rows) - self.row_index)):
                row = self._get_row()
                if row is None:
                    break
                self.rows.append(row)
        if self.row_index >= len(self.rows):
            return []
        row_end = self.row_index + size
        if row_end >= len(self.rows):
            row_end = len(self.rows)
        rows = self.rows[self.row_index:row_end]
        self.row_index = row_end
        return rows

    def fetchone(self):
        self._check_rows("fetchone")

        if self.row_index >= len(self.rows):
            row = self._get_row()
            if row is None:
                return
            self.rows.append(row)
        row = self.rows[self.row_index]
        self.row_index += 1
        return row

########NEW FILE########
__FILENAME__ = exceptions
class Warning(StandardError):
    pass

class Error(StandardError):
    pass
class InterfaceError(Error):
    pass
class DatabaseError(Error):
    pass
class DataError(DatabaseError):
    pass
class OperationalError(DatabaseError):
    pass
class IntegrityError(DatabaseError):
    pass
class InternalError(DatabaseError):
    pass
class ProgrammingError(DatabaseError):
    pass
class NotSupportedError(DatabaseError):
    pass

########NEW FILE########
__FILENAME__ = libmysql
import ctypes


class MYSQL(ctypes.Structure):
    _fields_ = []
MYSQL_P = ctypes.POINTER(MYSQL)

class MYSQL_RES(ctypes.Structure):
    _fields_ = []
MYSQL_RES_P = ctypes.POINTER(MYSQL_RES)

MYSQL_ROW = ctypes.POINTER(ctypes.POINTER(ctypes.c_char))

class MYSQL_FIELD(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.POINTER(ctypes.c_char)),
        ("org_name", ctypes.POINTER(ctypes.c_char)),
        ("table", ctypes.POINTER(ctypes.c_char)),
        ("org_table", ctypes.POINTER(ctypes.c_char)),
        ("db", ctypes.POINTER(ctypes.c_char)),
        ("catalog", ctypes.POINTER(ctypes.c_char)),
        ("def", ctypes.POINTER(ctypes.c_char)),
        ("length", ctypes.c_ulong),
        ("max_length", ctypes.c_ulong),
        ("name_length", ctypes.c_uint),
        ("org_name_length", ctypes.c_uint),
        ("table_length", ctypes.c_uint),
        ("org_table_length", ctypes.c_uint),
        ("db_length", ctypes.c_uint),
        ("catalog_length", ctypes.c_uint),
        ("def_length", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("decimals", ctypes.c_uint),
        ("charsetnr", ctypes.c_uint),
        ("type", ctypes.c_uint),
        ("extension", ctypes.c_void_p),
    ]
MYSQL_FIELD_P = ctypes.POINTER(MYSQL_FIELD)

# Hardcoded based on the values I found on two different Linux systems, bad: no
# cookies
MYSQL_OPT_CONNECT_TIMEOUT = 0
MYSQL_INIT_COMMAND = 3

c = None
# Prefer the higher version, obscure.
for lib in ["libmysqlclient.so.16", "libmysqlclient.so.15", "mysqlclient", "libmysqlclient.18.dylib"]:
    try:
        c = ctypes.CDLL(lib)
    except OSError:
        pass
    else:
        break
if c is None:
    raise ImportError("Can't find a libmysqlclient")

c.mysql_init.argtypes = [MYSQL_P]
c.mysql_init.restype = MYSQL_P

c.mysql_real_connect.argtypes = [
    MYSQL_P,            # connection
    ctypes.c_char_p,    # host
    ctypes.c_char_p,    # user
    ctypes.c_char_p,    # password
    ctypes.c_char_p,    # database
    ctypes.c_int,       # port
    ctypes.c_char_p,    # unix socket
    ctypes.c_ulong      # client_flag
]
c.mysql_real_connect.restype = MYSQL_P

c.mysql_error.argtypes = [MYSQL_P]
c.mysql_error.restype = ctypes.c_char_p

c.mysql_errno.argtypes = [MYSQL_P]
c.mysql_errno.restype = ctypes.c_uint

c.mysql_real_query.argtypes = [MYSQL_P, ctypes.c_char_p, ctypes.c_ulong]
c.mysql_real_query.restype = ctypes.c_int

c.mysql_query.argtypes = [MYSQL_P, ctypes.c_char_p]
c.mysql_query.restype = ctypes.c_int

c.mysql_store_result.argtypes = [MYSQL_P]
c.mysql_store_result.restype = MYSQL_RES_P

c.mysql_num_fields.argtypes = [MYSQL_RES_P]
c.mysql_num_fields.restype = ctypes.c_uint

c.mysql_fetch_row.argtypes = [MYSQL_RES_P]
c.mysql_fetch_row.restype = MYSQL_ROW

c.mysql_fetch_lengths.argtypes = [MYSQL_RES_P]
c.mysql_fetch_lengths.restype = ctypes.POINTER(ctypes.c_ulong)

c.mysql_fetch_fields.argtypes = [MYSQL_RES_P]
c.mysql_fetch_fields.restype = MYSQL_FIELD_P

c.mysql_escape_string.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong]
c.mysql_escape_string.restype = ctypes.c_ulong

c.mysql_real_escape_string.argtypes = [MYSQL_P, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong]
c.mysql_real_escape_string.restype = ctypes.c_ulong

c.mysql_affected_rows.argtypes = [MYSQL_P]
c.mysql_affected_rows.restype = ctypes.c_ulonglong

c.mysql_get_server_info.argtypes = [MYSQL_P]
c.mysql_get_server_info.restype = ctypes.c_char_p

c.mysql_insert_id.argtypes = [MYSQL_P]
c.mysql_insert_id.restype = ctypes.c_ulonglong

c.mysql_autocommit.argtypes = [MYSQL_P, ctypes.c_char]
c.mysql_autocommit.restype = ctypes.c_char

c.mysql_commit.argtypes = [MYSQL_P]
c.mysql_commit.restype = ctypes.c_char

c.mysql_rollback.argtypes = [MYSQL_P]
c.mysql_rollback.restype = ctypes.c_char

c.mysql_set_character_set.argtypes = [MYSQL_P, ctypes.c_char_p]
c.mysql_set_character_set.restype = ctypes.c_int

c.mysql_close.argtypes = [MYSQL_P]
c.mysql_close.restype = None

c.mysql_free_result.argtypes = [MYSQL_RES_P]
c.mysql_free_result.restype = None

c.mysql_character_set_name.argtypes = [MYSQL_P]
c.mysql_character_set_name.restype = ctypes.c_char_p

# Second thing is an enum, it looks to be a long on Linux systems.
c.mysql_options.argtypes = [MYSQL_P, ctypes.c_long, ctypes.c_char_p]
c.mysql_options.restype = ctypes.c_int

########NEW FILE########
__FILENAME__ = types
from MySQLdb.constants import field_types


class FieldType(object):
    def __init__(self, *args):
        self.values = frozenset(args)

    def __eq__(self, other):
        if isinstance(other, FieldType):
            return self.values.issuperset(other.values)
        return other in self.values


BINARY = FieldType(
    field_types.BLOB, field_types.LONG_BLOB, field_types.MEDIUM_BLOB,
    field_types.TINY_BLOB
)
DATETIME = FieldType()
NUMBER = FieldType()
ROWID = FieldType()
STRING = FieldType(field_types.VAR_STRING, field_types.STRING)
########NEW FILE########
__FILENAME__ = base
import contextlib


class BaseMySQLTests(object):
    @contextlib.contextmanager
    def create_table(self, connection, table_name, **fields):
        pk = fields.pop("primary_key", None)
        with contextlib.closing(connection.cursor()) as cursor:
            # TODO: this could return data unexpectadly because the fields are
            # in arbitrary order, you have been warned.
            fields = ", ".join(
                "%s %s" % (name, field_type)
                for name, field_type in fields.iteritems()
            )
            if pk is not None:
                fields += ", PRIMARY KEY (%s)" % pk
            cursor.execute("CREATE TABLE %s (%s) ENGINE=InnoDB" % (table_name, fields))
        try:
            yield
        finally:
            with contextlib.closing(connection.cursor()) as cursor:
                cursor.execute("DROP TABLE %s" % table_name)
########NEW FILE########
__FILENAME__ = conftest
import MySQLdb


def pytest_addoption(parser):
    group = parser.getgroup("MySQL package options")
    group.addoption(
        "--mysql-host",
        default = "localhost",
        dest = "mysql_host",
    )
    group.addoption(
        "--mysql-user",
        default = "root",
        dest = "mysql_user",
    )
    group.addoption(
        "--mysql-password",
        default = None,
        dest = "mysql_passwd",
    )
    group.addoption(
        "--mysql-database",
        default = "test_mysqldb",
        dest = "mysql_database",
    )

def pytest_funcarg__connection(request):
    option = request.config.option
    extra_kwargs = {}
    if hasattr(request.function, "connect_opts"):
        extra_kwargs = request.function.connect_opts.kwargs.copy()
    conn = MySQLdb.connect(
        host=option.mysql_host, user=option.mysql_user,
        passwd=option.mysql_passwd, db=option.mysql_database, **extra_kwargs
    )

    def close_conn():
        if not conn.closed:
            conn.close()

    request.addfinalizer(close_conn)
    return conn
########NEW FILE########
__FILENAME__ = dbapi20
#!/usr/bin/env python
''' Python DB API 2.0 driver compliance unit test suite. 
    
    This software is Public Domain and may be used without restrictions.

 "Now we have booze and barflies entering the discussion, plus rumours of
  DBAs on drugs... and I won't tell you what flashes through my mind each
  time I read the subject line with 'Anal Compliance' in it.  All around
  this is turning out to be a thoroughly unwholesome unit test."

    -- Ian Bicking
'''

__rcs_id__  = '$Id: dbapi20.py,v 1.11 2005/01/02 02:41:01 zenzen Exp $'
__version__ = '$Revision: 1.12 $'[11:-2]
__author__ = 'Stuart Bishop <stuart@stuartbishop.net>'

import unittest
import time
import sys


# Revision 1.12  2009/02/06 03:35:11  kf7xm
# Tested okay with Python 3.0, includes last minute patches from Mark H.
#
# Revision 1.1.1.1.2.1  2008/09/20 19:54:59  rupole
# Include latest changes from main branch
# Updates for py3k
#
# Revision 1.11  2005/01/02 02:41:01  zenzen
# Update author email address
#
# Revision 1.10  2003/10/09 03:14:14  zenzen
# Add test for DB API 2.0 optional extension, where database exceptions
# are exposed as attributes on the Connection object.
#
# Revision 1.9  2003/08/13 01:16:36  zenzen
# Minor tweak from Stefan Fleiter
#
# Revision 1.8  2003/04/10 00:13:25  zenzen
# Changes, as per suggestions by M.-A. Lemburg
# - Add a table prefix, to ensure namespace collisions can always be avoided
#
# Revision 1.7  2003/02/26 23:33:37  zenzen
# Break out DDL into helper functions, as per request by David Rushby
#
# Revision 1.6  2003/02/21 03:04:33  zenzen
# Stuff from Henrik Ekelund:
#     added test_None
#     added test_nextset & hooks
#
# Revision 1.5  2003/02/17 22:08:43  zenzen
# Implement suggestions and code from Henrik Eklund - test that cursor.arraysize
# defaults to 1 & generic cursor.callproc test added
#
# Revision 1.4  2003/02/15 00:16:33  zenzen
# Changes, as per suggestions and bug reports by M.-A. Lemburg,
# Matthew T. Kromer, Federico Di Gregorio and Daniel Dittmar
# - Class renamed
# - Now a subclass of TestCase, to avoid requiring the driver stub
#   to use multiple inheritance
# - Reversed the polarity of buggy test in test_description
# - Test exception heirarchy correctly
# - self.populate is now self._populate(), so if a driver stub
#   overrides self.ddl1 this change propogates
# - VARCHAR columns now have a width, which will hopefully make the
#   DDL even more portible (this will be reversed if it causes more problems)
# - cursor.rowcount being checked after various execute and fetchXXX methods
# - Check for fetchall and fetchmany returning empty lists after results
#   are exhausted (already checking for empty lists if select retrieved
#   nothing
# - Fix bugs in test_setoutputsize_basic and test_setinputsizes
#
def str2bytes(sval):
    if sys.version_info < (3,0) and isinstance(sval, str):
        sval = sval.decode("latin1")
    return sval.encode("latin1")

class DatabaseAPI20Test(unittest.TestCase):
    ''' Test a database self.driver for DB API 2.0 compatibility.
        This implementation tests Gadfly, but the TestCase
        is structured so that other self.drivers can subclass this 
        test case to ensure compiliance with the DB-API. It is 
        expected that this TestCase may be expanded in the future
        if ambiguities or edge conditions are discovered.

        The 'Optional Extensions' are not yet being tested.

        self.drivers should subclass this test, overriding setUp, tearDown,
        self.driver, connect_args and connect_kw_args. Class specification
        should be as follows:

        import dbapi20 
        class mytest(dbapi20.DatabaseAPI20Test):
           [...] 

        Don't 'import DatabaseAPI20Test from dbapi20', or you will
        confuse the unit tester - just 'import dbapi20'.
    '''

    # The self.driver module. This should be the module where the 'connect'
    # method is to be found
    driver = None
    connect_args = () # List of arguments to pass to connect
    connect_kw_args = {} # Keyword arguments for connect
    table_prefix = 'dbapi20test_' # If you need to specify a prefix for tables

    ddl1 = 'create table %sbooze (name varchar(20))' % table_prefix
    ddl2 = 'create table %sbarflys (name varchar(20))' % table_prefix
    xddl1 = 'drop table %sbooze' % table_prefix
    xddl2 = 'drop table %sbarflys' % table_prefix

    lowerfunc = 'lower' # Name of stored procedure to convert string->lowercase
        
    # Some drivers may need to override these helpers, for example adding
    # a 'commit' after the execute.
    def executeDDL1(self,cursor):
        cursor.execute(self.ddl1)

    def executeDDL2(self,cursor):
        cursor.execute(self.ddl2)

    def setUp(self):
        ''' self.drivers should override this method to perform required setup
            if any is necessary, such as creating the database.
        '''
        pass

    def tearDown(self):
        ''' self.drivers should override this method to perform required cleanup
            if any is necessary, such as deleting the test database.
            The default drops the tables that may be created.
        '''
        con = self._connect()
        try:
            cur = con.cursor()
            for ddl in (self.xddl1,self.xddl2):
                try: 
                    cur.execute(ddl)
                    con.commit()
                except self.driver.Error, e: 
                    if not self.is_table_does_not_exist(e):
                        raise
        finally:
            con.close()

    def _connect(self):
        try:
            return self.driver.connect(
                *self.connect_args,**self.connect_kw_args
                )
        except AttributeError:
            self.fail("No connect method found in self.driver module")

    def test_connect(self):
        con = self._connect()
        con.close()

    def test_apilevel(self):
        try:
            # Must exist
            apilevel = self.driver.apilevel
            # Must equal 2.0
            self.assertEqual(apilevel,'2.0')
        except AttributeError:
            self.fail("Driver doesn't define apilevel")

    def test_threadsafety(self):
        try:
            # Must exist
            threadsafety = self.driver.threadsafety
            # Must be a valid value
            self.failUnless(threadsafety in (0,1,2,3))
        except AttributeError:
            self.fail("Driver doesn't define threadsafety")

    def test_paramstyle(self):
        try:
            # Must exist
            paramstyle = self.driver.paramstyle
            # Must be a valid value
            self.failUnless(paramstyle in (
                'qmark','numeric','named','format','pyformat'
                ))
        except AttributeError:
            self.fail("Driver doesn't define paramstyle")

    def test_Exceptions(self):
        # Make sure required exceptions exist, and are in the
        # defined heirarchy.
        if sys.version[0] == '3': #under Python 3 StardardError no longer exists
            self.failUnless(issubclass(self.driver.Warning,Exception))
            self.failUnless(issubclass(self.driver.Error,Exception))
        else:
            self.failUnless(issubclass(self.driver.Warning,StandardError))
            self.failUnless(issubclass(self.driver.Error,StandardError))

        self.failUnless(
            issubclass(self.driver.InterfaceError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.DatabaseError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.OperationalError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.IntegrityError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.InternalError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.ProgrammingError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.NotSupportedError,self.driver.Error)
            )

    def test_ExceptionsAsConnectionAttributes(self):
        # OPTIONAL EXTENSION
        # Test for the optional DB API 2.0 extension, where the exceptions
        # are exposed as attributes on the Connection object
        # I figure this optional extension will be implemented by any
        # driver author who is using this test suite, so it is enabled
        # by default.
        con = self._connect()
        drv = self.driver
        self.failUnless(con.Warning is drv.Warning)
        self.failUnless(con.Error is drv.Error)
        self.failUnless(con.InterfaceError is drv.InterfaceError)
        self.failUnless(con.DatabaseError is drv.DatabaseError)
        self.failUnless(con.OperationalError is drv.OperationalError)
        self.failUnless(con.IntegrityError is drv.IntegrityError)
        self.failUnless(con.InternalError is drv.InternalError)
        self.failUnless(con.ProgrammingError is drv.ProgrammingError)
        self.failUnless(con.NotSupportedError is drv.NotSupportedError)


    def test_commit(self):
        con = self._connect()
        try:
            # Commit must work, even if it doesn't do anything
            con.commit()
        finally:
            con.close()

    def test_rollback(self):
        con = self._connect()
        # If rollback is defined, it should either work or throw
        # the documented exception
        if hasattr(con,'rollback'):
            try:
                con.rollback()
            except self.driver.NotSupportedError:
                pass
    
    def test_cursor(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

    def test_cursor_isolation(self):
        con = self._connect()
        try:
            # Make sure cursors created from the same connection have
            # the documented transaction isolation level
            cur1 = con.cursor()
            cur2 = con.cursor()
            self.executeDDL1(cur1)
            cur1.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            cur2.execute("select name from %sbooze" % self.table_prefix)
            booze = cur2.fetchall()
            self.assertEqual(len(booze),1)
            self.assertEqual(len(booze[0]),1)
            self.assertEqual(booze[0][0],'Victoria Bitter')
        finally:
            con.close()

    def test_description(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(cur.description,None,
                'cursor.description should be none after executing a '
                'statement that can return no rows (such as DDL)'
                )
            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(len(cur.description),1,
                'cursor.description describes too many columns'
                )
            self.assertEqual(len(cur.description[0]),7,
                'cursor.description[x] tuples must have 7 elements'
                )
            self.assertEqual(cur.description[0][0].lower(),'name',
                'cursor.description[x][0] must return column name'
                )
            self.assertEqual(cur.description[0][1],self.driver.STRING,
                'cursor.description[x][1] must return column type. Got %r'
                    % cur.description[0][1]
                )

            # Make sure self.description gets reset
            self.executeDDL2(cur)
            self.assertEqual(cur.description,None,
                'cursor.description not being set to None when executing '
                'no-result statements (eg. DDL)'
                )
        finally:
            con.close()

    def test_rowcount(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(cur.rowcount,-1,
                'cursor.rowcount should be -1 after executing no-result '
                'statements'
                )
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            self.failUnless(cur.rowcount in (-1,1),
                'cursor.rowcount should == number or rows inserted, or '
                'set to -1 after executing an insert statement'
                )
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.failUnless(cur.rowcount in (-1,1),
                'cursor.rowcount should == number of rows returned, or '
                'set to -1 after executing a select statement'
                )
            self.executeDDL2(cur)
            self.assertEqual(cur.rowcount,-1,
                'cursor.rowcount not being reset to -1 after executing '
                'no-result statements'
                )
        finally:
            con.close()

    lower_func = 'lower'
    def test_callproc(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if self.lower_func and hasattr(cur,'callproc'):
                r = cur.callproc(self.lower_func,('FOO',))
                self.assertEqual(len(r),1)
                self.assertEqual(r[0],'FOO')
                r = cur.fetchall()
                self.assertEqual(len(r),1,'callproc produced no result set')
                self.assertEqual(len(r[0]),1,
                    'callproc produced invalid result set'
                    )
                self.assertEqual(r[0][0],'foo',
                    'callproc produced invalid results'
                    )
        finally:
            con.close()

    def test_close(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

        # cursor.execute should raise an Error if called after connection
        # closed
        self.assertRaises(self.driver.Error,self.executeDDL1,cur)

        # connection.commit should raise an Error if called after connection'
        # closed.'
        self.assertRaises(self.driver.Error,con.commit)

        # connection.close should raise an Error if called more than once
        self.assertRaises(self.driver.Error,con.close)

    def test_execute(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self._paraminsert(cur)
        finally:
            con.close()

    def _paraminsert(self,cur):
        self.executeDDL1(cur)
        cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
            self.table_prefix
            ))
        self.failUnless(cur.rowcount in (-1,1))

        if self.driver.paramstyle == 'qmark':
            cur.execute(
                'insert into %sbooze values (?)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'numeric':
            cur.execute(
                'insert into %sbooze values (:1)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'named':
            cur.execute(
                'insert into %sbooze values (:beer)' % self.table_prefix, 
                {'beer':"Cooper's"}
                )
        elif self.driver.paramstyle == 'format':
            cur.execute(
                'insert into %sbooze values (%%s)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'pyformat':
            cur.execute(
                'insert into %sbooze values (%%(beer)s)' % self.table_prefix,
                {'beer':"Cooper's"}
                )
        else:
            self.fail('Invalid paramstyle')
        self.failUnless(cur.rowcount in (-1,1))

        cur.execute('select name from %sbooze' % self.table_prefix)
        res = cur.fetchall()
        self.assertEqual(len(res),2,'cursor.fetchall returned too few rows')
        beers = [res[0][0],res[1][0]]
        beers.sort()
        self.assertEqual(beers[0],"Cooper's",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly'
            )
        self.assertEqual(beers[1],"Victoria Bitter",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly'
            )

    def test_executemany(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            largs = [ ("Cooper's",) , ("Boag's",) ]
            margs = [ {'beer': "Cooper's"}, {'beer': "Boag's"} ]
            if self.driver.paramstyle == 'qmark':
                cur.executemany(
                    'insert into %sbooze values (?)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'numeric':
                cur.executemany(
                    'insert into %sbooze values (:1)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'named':
                cur.executemany(
                    'insert into %sbooze values (:beer)' % self.table_prefix,
                    margs
                    )
            elif self.driver.paramstyle == 'format':
                cur.executemany(
                    'insert into %sbooze values (%%s)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'pyformat':
                cur.executemany(
                    'insert into %sbooze values (%%(beer)s)' % (
                        self.table_prefix
                        ),
                    margs
                    )
            else:
                self.fail('Unknown paramstyle')
            self.failUnless(cur.rowcount in (-1,2),
                'insert using cursor.executemany set cursor.rowcount to '
                'incorrect value %r' % cur.rowcount
                )
            cur.execute('select name from %sbooze' % self.table_prefix)
            res = cur.fetchall()
            self.assertEqual(len(res),2,
                'cursor.fetchall retrieved incorrect number of rows'
                )
            beers = [res[0][0],res[1][0]]
            beers.sort()
            self.assertEqual(beers[0],"Boag's",'incorrect data retrieved')
            self.assertEqual(beers[1],"Cooper's",'incorrect data retrieved')
        finally:
            con.close()

    def test_fetchone(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchone should raise an Error if called before
            # executing a select-type query
            self.assertRaises(self.driver.Error,cur.fetchone)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            self.executeDDL1(cur)
            self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if a query retrieves '
                'no rows'
                )
            self.failUnless(cur.rowcount in (-1,0))

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchone()
            self.assertEqual(len(r),1,
                'cursor.fetchone should have retrieved a single row'
                )
            self.assertEqual(r[0],'Victoria Bitter',
                'cursor.fetchone retrieved incorrect data'
                )
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if no more rows available'
                )
            self.failUnless(cur.rowcount in (-1,1))
        finally:
            con.close()

    samples = [
        'Carlton Cold',
        'Carlton Draft',
        'Mountain Goat',
        'Redback',
        'Victoria Bitter',
        'XXXX'
        ]

    def _populate(self):
        ''' Return a list of sql commands to setup the DB for the fetch
            tests.
        '''
        populate = [
            "insert into %sbooze values ('%s')" % (self.table_prefix,s) 
                for s in self.samples
            ]
        return populate

    def test_fetchmany(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchmany should raise an Error if called without
            #issuing a query
            self.assertRaises(self.driver.Error,cur.fetchmany,4)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany()
            self.assertEqual(len(r),1,
                'cursor.fetchmany retrieved incorrect number of rows, '
                'default of arraysize is one.'
                )
            cur.arraysize=10
            r = cur.fetchmany(3) # Should get 3 rows
            self.assertEqual(len(r),3,
                'cursor.fetchmany retrieved incorrect number of rows'
                )
            r = cur.fetchmany(4) # Should get 2 more
            self.assertEqual(len(r),2,
                'cursor.fetchmany retrieved incorrect number of rows'
                )
            r = cur.fetchmany(4) # Should be an empty sequence
            self.assertEqual(len(r),0,
                'cursor.fetchmany should return an empty sequence after '
                'results are exhausted'
            )
            self.failUnless(cur.rowcount in (-1,6))

            # Same as above, using cursor.arraysize
            cur.arraysize=4
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany() # Should get 4 rows
            self.assertEqual(len(r),4,
                'cursor.arraysize not being honoured by fetchmany'
                )
            r = cur.fetchmany() # Should get 2 more
            self.assertEqual(len(r),2)
            r = cur.fetchmany() # Should be an empty sequence
            self.assertEqual(len(r),0)
            self.failUnless(cur.rowcount in (-1,6))

            cur.arraysize=6
            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchmany() # Should get all rows
            self.failUnless(cur.rowcount in (-1,6))
            self.assertEqual(len(rows),6)
            self.assertEqual(len(rows),6)
            rows = [r[0] for r in rows]
            rows.sort()
          
            # Make sure we get the right data back out
            for i in range(0,6):
                self.assertEqual(rows[i],self.samples[i],
                    'incorrect data retrieved by cursor.fetchmany'
                    )

            rows = cur.fetchmany() # Should return an empty list
            self.assertEqual(len(rows),0,
                'cursor.fetchmany should return an empty sequence if '
                'called after the whole result set has been fetched'
                )
            self.failUnless(cur.rowcount in (-1,6))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            r = cur.fetchmany() # Should get empty sequence
            self.assertEqual(len(r),0,
                'cursor.fetchmany should return an empty sequence if '
                'query retrieved no rows'
                )
            self.failUnless(cur.rowcount in (-1,0))

        finally:
            con.close()

    def test_fetchall(self):
        con = self._connect()
        try:
            cur = con.cursor()
            # cursor.fetchall should raise an Error if called
            # without executing a query that may return rows (such
            # as a select)
            self.assertRaises(self.driver.Error, cur.fetchall)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            # cursor.fetchall should raise an Error if called
            # after executing a a statement that cannot return rows
            self.assertRaises(self.driver.Error,cur.fetchall)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,len(self.samples)))
            self.assertEqual(len(rows),len(self.samples),
                'cursor.fetchall did not retrieve all rows'
                )
            rows = [r[0] for r in rows]
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                'cursor.fetchall retrieved incorrect rows'
                )
            rows = cur.fetchall()
            self.assertEqual(
                len(rows),0,
                'cursor.fetchall should return an empty list if called '
                'after the whole result set has been fetched'
                )
            self.failUnless(cur.rowcount in (-1,len(self.samples)))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            rows = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,0))
            self.assertEqual(len(rows),0,
                'cursor.fetchall should return an empty list if '
                'a select query returns no rows'
                )
            
        finally:
            con.close()
    
    def test_mixedfetch(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows1  = cur.fetchone()
            rows23 = cur.fetchmany(2)
            rows4  = cur.fetchone()
            rows56 = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,6))
            self.assertEqual(len(rows23),2,
                'fetchmany returned incorrect number of rows'
                )
            self.assertEqual(len(rows56),2,
                'fetchall returned incorrect number of rows'
                )

            rows = [rows1[0]]
            rows.extend([rows23[0][0],rows23[1][0]])
            rows.append(rows4[0])
            rows.extend([rows56[0][0],rows56[1][0]])
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                    'incorrect data retrieved or inserted'
                    )
        finally:
            con.close()

    def help_nextset_setUp(self,cur):
        ''' Should create a procedure called deleteme
            that returns two result sets, first the 
	    number of rows in booze then "name from booze"
        '''
        raise NotImplementedError('Helper not implemented')
        #sql="""
        #    create procedure deleteme as
        #    begin
        #        select count(*) from booze
        #        select name from booze
        #    end
        #"""
        #cur.execute(sql)

    def help_nextset_tearDown(self,cur):
        'If cleaning up is needed after nextSetTest'
        raise NotImplementedError('Helper not implemented')
        #cur.execute("drop procedure deleteme")

    def test_nextset(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if not hasattr(cur,'nextset'):
                return

            try:
                self.executeDDL1(cur)
                sql=self._populate()
                for sql in self._populate():
                    cur.execute(sql)

                self.help_nextset_setUp(cur)

                cur.callproc('deleteme')
                numberofrows=cur.fetchone()
                assert numberofrows[0]== len(self.samples)
                assert cur.nextset()
                names=cur.fetchall()
                assert len(names) == len(self.samples)
                s=cur.nextset()
                assert s == None,'No more return sets, should return None'
            finally:
                self.help_nextset_tearDown(cur)

        finally:
            con.close()

    def test_nextset(self):
        raise NotImplementedError('Drivers need to override this test')

    def test_arraysize(self):
        # Not much here - rest of the tests for this are in test_fetchmany
        con = self._connect()
        try:
            cur = con.cursor()
            self.failUnless(hasattr(cur,'arraysize'),
                'cursor.arraysize must be defined'
                )
        finally:
            con.close()

    def test_setinputsizes(self):
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setinputsizes( (25,) )
            self._paraminsert(cur) # Make sure cursor still works
        finally:
            con.close()

    def test_setoutputsize_basic(self):
        # Basic test is to make sure setoutputsize doesn't blow up
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setoutputsize(1000)
            cur.setoutputsize(2000,0)
            self._paraminsert(cur) # Make sure the cursor still works
        finally:
            con.close()

    def test_setoutputsize(self):
        # Real test for setoutputsize is driver dependant
        raise NotImplementedError('Driver needed to override this test')

    def test_None(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            cur.execute('insert into %sbooze values (NULL)' % self.table_prefix)
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchall()
            self.assertEqual(len(r),1)
            self.assertEqual(len(r[0]),1)
            self.assertEqual(r[0][0],None,'NULL value not returned as None')
        finally:
            con.close()

    def test_Date(self):
        d1 = self.driver.Date(2002,12,25)
        d2 = self.driver.DateFromTicks(time.mktime((2002,12,25,0,0,0,0,0,0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(d1),str(d2))

    def test_Time(self):
        t1 = self.driver.Time(13,45,30)
        t2 = self.driver.TimeFromTicks(time.mktime((2001,1,1,13,45,30,0,0,0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Timestamp(self):
        t1 = self.driver.Timestamp(2002,12,25,13,45,30)
        t2 = self.driver.TimestampFromTicks(
            time.mktime((2002,12,25,13,45,30,0,0,0))
            )
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Binary(self):
        b = self.driver.Binary(str2bytes('Something'))
        b = self.driver.Binary(str2bytes(''))

    def test_STRING(self):
        self.failUnless(hasattr(self.driver,'STRING'),
            'module.STRING must be defined'
            )

    def test_BINARY(self):
        self.failUnless(hasattr(self.driver,'BINARY'),
            'module.BINARY must be defined.'
            )

    def test_NUMBER(self):
        self.failUnless(hasattr(self.driver,'NUMBER'),
            'module.NUMBER must be defined.'
            )

    def test_DATETIME(self):
        self.failUnless(hasattr(self.driver,'DATETIME'),
            'module.DATETIME must be defined.'
            )

    def test_ROWID(self):
        self.failUnless(hasattr(self.driver,'ROWID'),
            'module.ROWID must be defined.'
            )


########NEW FILE########
__FILENAME__ = test_connection
import contextlib

import py

from MySQLdb.cursors import DictCursor

from .base import BaseMySQLTests


class TestConnection(BaseMySQLTests):
    def test_custom_cursor_class(self, connection):
        with contextlib.closing(connection.cursor(DictCursor)) as cur:
            assert type(cur) is DictCursor

    def test_closed_rollback(self, connection):
        connection.close()
        with py.test.raises(connection.InterfaceError):
            connection.rollback()

    def test_closed_property(self, connection):
        assert not connection.closed
        connection.close()
        assert connection.closed

    def test_string_literal(self, connection):
        assert connection.string_literal(3) == "'3'"

    @py.test.mark.connect_opts(sql_mode="ANSI")
    def test_sql_mode(self, connection):
        with self.create_table(connection, "people", age="INT"):
            with contextlib.closing(connection.cursor()) as cursor:
                cursor.execute('SELECT "people"."age" FROM "people"')
                rows = cursor.fetchall()
                assert rows == []

    def test_closed_error(self, connection):
        connection.close()
        with py.test.raises(connection.InterfaceError) as exc:
            connection.rollback()
        assert str(exc.value) == "(0, '')"

########NEW FILE########
__FILENAME__ = test_cursor
# -*- coding: utf-8 -*-

import contextlib
import datetime
import warnings

import py

from MySQLdb.cursors import DictCursor
from MySQLdb.constants import CLIENT

from .base import BaseMySQLTests


class TestCursor(BaseMySQLTests):
    def assert_roundtrips(self, connection, obj, check_type=True):
        with contextlib.closing(connection.cursor()) as cur:
            cur.execute("SELECT %s", (obj,))
            row, = cur.fetchall()
            val, = row
            if check_type:
                assert type(val) is type(obj)
            assert val == obj

    def test_basic_execute(self, connection):
        with self.create_table(connection, "things", name="VARCHAR(20)"):
            with contextlib.closing(connection.cursor()) as cur:
                cur.execute("INSERT INTO things (name) VALUES ('website')")
                cur.execute("SELECT name FROM things")
                results = cur.fetchall()
                assert results == [("website",)]

    def test_fetchmany_insert(self, connection):
        with self.create_table(connection, "things", name="VARCHAR(20)"):
            with contextlib.closing(connection.cursor()) as cur:
                cur.execute("INSERT INTO things (name) VALUES ('website')")
                with py.test.raises(connection.ProgrammingError):
                    cur.fetchmany()

    def test_iterable(self, connection):
        with self.create_table(connection, "users", uid="INT"):
            with contextlib.closing(connection.cursor()) as cur:
                cur.executemany("INSERT INTO users (uid) VALUES (%s)", [(i,) for i in xrange(5)])
                cur.execute("SELECT * FROM users")
                x = iter(cur)
                row = cur.fetchone()
                assert row == (0,)
                row = x.next()
                assert row == (1,)
                rows = cur.fetchall()
                assert rows == [(2,), (3,), (4,)]
                with py.test.raises(StopIteration):
                    x.next()

    def test_lastrowid(self, connection):
        with self.create_table(connection, "users", uid="INT NOT NULL AUTO_INCREMENT", primary_key="uid"):
            with contextlib.closing(connection.cursor()) as cur:
                cur.execute("INSERT INTO users () VALUES ()")
                assert cur.lastrowid

    def test_autocommit(self, connection):
        with self.create_table(connection, "users", uid="INT"):
            with contextlib.closing(connection.cursor()) as cur:
                cur.executemany("INSERT INTO users (uid) VALUES (%s)", [(i,) for i in xrange(5)])
                connection.rollback()
                cur.execute("SELECT COUNT(*) FROM users")
                c, = cur.fetchall()
                assert c == (0,)

    def test_none(self, connection):
        with contextlib.closing(connection.cursor()) as cur:
            cur.execute("SELECT %s", (None,))
            row, = cur.fetchall()
            assert row == (None,)

    def test_bool(self, connection):
        self.assert_roundtrips(connection, True, check_type=False)
        self.assert_roundtrips(connection, False, check_type=False)

    def test_longlong(self, connection):
        with contextlib.closing(connection.cursor()) as cur:
            cur.execute("SHOW COLLATION")
            cur.fetchone()

    def test_datetime(self, connection):
        with self.create_table(connection, "events", dt="TIMESTAMP"):
            with contextlib.closing(connection.cursor()) as cur:
                t = datetime.datetime.combine(datetime.datetime.today(), datetime.time(12, 20, 2))
                cur.execute("INSERT INTO events (dt) VALUES (%s)", (t,))
                cur.execute("SELECT dt FROM events")
                r, = cur.fetchall()
                assert r == (t,)

    def test_date(self, connection):
        with contextlib.closing(connection.cursor()) as cur:
            cur.execute("SELECT CURDATE()")
            row, = cur.fetchall()
            assert row == (datetime.date.today(),)

    def test_time(self, connection):
        with self.create_table(connection, "events", t="TIME"):
            with contextlib.closing(connection.cursor()) as cur:
                t = datetime.time(12, 20, 2)
                cur.execute("INSERT INTO events (t) VALUES (%s)", (t,))
                cur.execute("SELECT t FROM events")
                r, = cur.fetchall()
                # Against all rationality, MySQLdb returns a timedelta here
                # immitate this idiotic behavior.
                assert r == (datetime.timedelta(hours=12, minutes=20, seconds=2),)

    def test_binary(self, connection):
        self.assert_roundtrips(connection, "".join(chr(x) for x in xrange(255)))
        self.assert_roundtrips(connection, 'm\xf2\r\n')

    def test_blob(self, connection):
        with self.create_table(connection, "people", name="BLOB"):
            with contextlib.closing(connection.cursor()) as cur:
                cur.execute("INSERT INTO people (name) VALUES (%s)", ("".join(chr(x) for x in xrange(255)),))
                cur.execute("SELECT * FROM people")
                row, = cur.fetchall()
                val, = row
                assert val == "".join(chr(x) for x in xrange(255))
                assert type(val) is str

    def test_nonexistant_table(self, connection):
        with contextlib.closing(connection.cursor()) as cur:
            with py.test.raises(connection.ProgrammingError) as cm:
                cur.execute("DESCRIBE t")
            assert cm.value.args[0] == 1146

    def test_rowcount(self, connection):
        with self.create_table(connection, "people", age="INT"):
            with contextlib.closing(connection.cursor()) as cur:
                cur.execute("DESCRIBE people")
                assert cur.rowcount == 1

                cur.execute("DELETE FROM people WHERE age = %s", (10,))
                assert cur.rowcount == 0

                cur.executemany("INSERT INTO people (age) VALUES (%s)", [(i,) for i in xrange(5)])
                cur.execute("DELETE FROM people WHERE age < %s", (3,))
                assert cur.rowcount == 3

    def test_limit(self, connection):
        with self.create_table(connection, "people", age="INT"):
            with contextlib.closing(connection.cursor()) as cur:
                cur.executemany("INSERT INTO people (age) VALUES (%s)", [(10,), (11,)])
                cur.execute("SELECT * FROM people ORDER BY age LIMIT %s", (1,))
                rows = cur.fetchall()
                assert rows == [(10,)]

    @py.test.mark.connect_opts(client_flag=CLIENT.FOUND_ROWS)
    def test_found_rows_client_flag(self, connection):
        with self.create_table(connection, "people", age="INT"):
            with contextlib.closing(connection.cursor()) as cur:
                cur.execute("INSERT INTO people (age) VALUES (20)")
                cur.execute("UPDATE people SET age = 20 WHERE age = 20")
                assert cur.rowcount == 1

    def test_broken_execute(self, connection):
        with contextlib.closing(connection.cursor()) as cursor:
            cursor.execute("SELECT %s", "hello")
            row, = cursor.fetchall()
            assert row == ("hello",)

            cursor.execute("SELECT %s, %s", ["Hello", "World"])
            row, = cursor.fetchall()
            assert row == ("Hello", "World")

    def test_integrity_error(self, connection):
        with self.create_table(connection, "people", uid="INT", primary_key="uid"):
            with contextlib.closing(connection.cursor()) as cursor:
                cursor.execute("INSERT INTO people (uid) VALUES (1)")
                with py.test.raises(connection.IntegrityError):
                    cursor.execute("INSERT INTO people (uid) VALUES (1)")

    def test_description(self, connection):
        with self.create_table(connection, "people", uid="INT"):
            with contextlib.closing(connection.cursor()) as cursor:
                cursor.execute("DELETE FROM people WHERE uid = %s", (1,))
                assert cursor.description is None

                cursor.execute("SELECT uid FROM people")
                assert len(cursor.description) == 1
                assert cursor.description[0][0] == "uid"

    def test_executemany_return(self, connection):
        with self.create_table(connection, "people", uid="INT"):
            with contextlib.closing(connection.cursor()) as cursor:
                r = cursor.executemany("INSERT INTO people (uid) VALUES (%s)", [(1,), (2,)])
                assert r == 2

    def test_unicode(self, connection):
        with self.create_table(connection, "snippets", content="TEXT"):
            with contextlib.closing(connection.cursor()) as cursor:
                unicodedata = (u"Alors vous imaginez ma surprise, au lever du "
                    u"jour, quand une drôle de petite voix m’a réveillé. Elle "
                    u"disait: « S’il vous plaît… dessine-moi un mouton! »")
                cursor.executemany("INSERT INTO snippets (content) VALUES (%s)", [
                    (unicodedata.encode("utf-8"),),
                    (unicodedata.encode("utf-8"),),
                ])
                cursor.execute("SELECT content FROM snippets LIMIT 1")
                r, = cursor.fetchall()
                v, = r
                v = v.decode("utf-8")
                assert isinstance(v, unicode)
                assert v == unicodedata


class TestDictCursor(BaseMySQLTests):
    def test_fetchall(self, connection):
        with self.create_table(connection, "people", name="VARCHAR(20)", age="INT"):
            with contextlib.closing(connection.cursor(DictCursor)) as cur:
                cur.execute("INSERT INTO people (name, age) VALUES ('guido', 50)")
                cur.execute("SELECT * FROM people")
                rows = cur.fetchall()
                assert rows == [{"name": "guido", "age": 50}]

    def test_fetchmany(self, connection):
        with self.create_table(connection, "users", uid="INT"):
            with contextlib.closing(connection.cursor(DictCursor)) as cur:
                cur.executemany("INSERT INTO users (uid) VALUES (%s)", [(i,) for i in xrange(10)])
                cur.execute("SELECT * FROM users")
                rows = cur.fetchmany()
                assert rows == [{"uid": 0}]
                rows = cur.fetchmany(2)
                assert rows == [{"uid": 1}, {"uid": 2}]

    def test_fetchone(self, connection):
        with self.create_table(connection, "salads", country="VARCHAR(20)"):
            with contextlib.closing(connection.cursor(DictCursor)) as cur:
                cur.execute("INSERT INTO salads (country) VALUES ('Italy')")
                cur.execute("SELECT * FROM salads")
                row = cur.fetchone()
                assert row == {"country": "Italy"}
                row = cur.fetchone()
                assert row is None
########NEW FILE########
__FILENAME__ = test_dbapi20
import py

import MySQLdb

from . import dbapi20


class MySQLDBAPI20Tests(dbapi20.DatabaseAPI20Test):
    driver = MySQLdb

    def setUp(self):
        from pytest import config

        option = config.option
        self.connect_kw_args = {
            "host": option.mysql_host,
            "user": option.mysql_user,
            "passwd": option.mysql_passwd,
            "db": option.mysql_database,
        }

    def is_table_does_not_exist(self, exc):
        return exc.args[0] == 1051

    def test_nextset(self):
        py.test.skip("No idea what this is, skipping for now")

    def test_setoutputsize(self):
        py.test.skip("No idea what this is, skipping for now")
########NEW FILE########
__FILENAME__ = test_mod
import MySQLdb


class TestModule(object):
    def test_string_literal(self):
        assert MySQLdb.string_literal(2) == "'2'"

########NEW FILE########
