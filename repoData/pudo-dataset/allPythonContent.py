__FILENAME__ = app
import logging
import argparse

from sqlalchemy.exc import ProgrammingError
from dataset.util import FreezeException
from dataset.persistence.table import Table
from dataset.persistence.database import Database
from dataset.freeze.config import Configuration, Export
from dataset.freeze.format import get_serializer


log = logging.getLogger(__name__)

parser = argparse.ArgumentParser(
    description='Generate static JSON and CSV extracts from a SQL database.',
    epilog='For further information, please check the documentation.')
parser.add_argument('config', metavar='CONFIG', type=str,
                    help='freeze file cofiguration')
parser.add_argument('--db', default=None,
                    help='Override the freezefile database URI')


def freeze(result, format='csv', filename='freeze.csv', fileobj=None,
           prefix='.', meta={}, indent=2, mode='list', wrap=True,
           callback=None, **kw):
    """
    Perform a data export of a given result set. This is a very
    flexible exporter, allowing for various output formats, metadata
    assignment, and file name templating to dump each record (or a set
    of records) into individual files.

    ::

        result = db['person'].all()
        dataset.freeze(result, format='json', filename='all-persons.json')

    Instead of passing in the file name, you can also pass a file object::

        result = db['person'].all()
        fh = open('/dev/null', 'wb')
        dataset.freeze(result, format='json', fileobj=fh)

    Be aware that this will disable file name templating and store all
    results to the same file.

    If ``result`` is a table (rather than a result set), all records in
    the table are exported (as if ``result.all()`` had been called).


    freeze supports two values for ``mode``:

        *list* (default)
            The entire result set is dumped into a single file.

        *item*
            One file is created for each row in the result set.

    You should set a ``filename`` for the exported file(s). If ``mode``
    is set to *item* the function would generate one file per row. In
    that case you can  use values as placeholders in filenames::

            dataset.freeze(res, mode='item', format='json',
                           filename='item-{{id}}.json')

    The following output ``format`` s are supported:

        *csv*
            Comma-separated values, first line contains column names.

        *json*
            A JSON file containing a list of dictionaries for each row
            in the table. If a ``callback`` is given, JSON with padding
            (JSONP) will be generated.

        *tabson*
            Tabson is a smart combination of the space-efficiency of the
            CSV and the parsability and structure of JSON.

    """
    kw.update({
        'format': format,
        'filename': filename,
        'fileobj': fileobj,
        'prefix': prefix,
        'meta': meta,
        'indent': indent,
        'callback': callback,
        'mode': mode,
        'wrap': wrap
    })
    records = result.all() if isinstance(result, Table) else result
    return freeze_export(Export({}, kw), result=records)


def freeze_export(export, result=None):
    try:
        if result is None:
            database = Database(export.get('database'))
            query = database.query(export.get('query'))
        else:
            query = result
        serializer_cls = get_serializer(export)
        serializer = serializer_cls(export, query)
        serializer.serialize()
    except ProgrammingError as pe:
        raise FreezeException("Invalid query: %s" % pe)


def main():
    # Set up default logger.
    logging.basicConfig(level=logging.INFO)

    try:
        args = parser.parse_args()
        config = Configuration(args.config)
        for export in config.exports:
            if args.db is not None:
                export.data['database'] = args.db
            if export.skip:
                log.info("Skipping: %s", export.name)
                continue
            log.info("Running: %s", export.name)
            freeze_export(export)
    except FreezeException as fe:
        log.error(fe)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()

########NEW FILE########
__FILENAME__ = config
import json
import yaml

try:
    str = unicode
except NameError:
    pass

from dataset.util import FreezeException


TRUISH = ['true', 'yes', '1', 'on']

DECODER = {
    'json': json,
    'yaml': yaml
    }


def merge_overlay(data, overlay):
    out = overlay.copy()
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            v = merge_overlay(v, out.get(k))
        out[k] = v
    return out


class Configuration(object):

    def __init__(self, file_name):
        self.file_name = file_name
        extension = file_name.rsplit('.', 1)[-1]
        loader = DECODER.get(extension, json)
        try:
            fh = open(file_name, 'rb')
            try:
                self.data = loader.load(fh)
            except ValueError as ve:
                raise FreezeException("Invalid freeze file: %s" % ve)
            fh.close()
        except IOError as ioe:
            raise FreezeException(str(ioe))

    @property
    def exports(self):
        if not isinstance(self.data, dict):
            raise FreezeException("The root element of the freeze file needs to be a hash")
        if not isinstance(self.data.get('exports'), list):
            raise FreezeException("The freeze file needs to have a list of exports")
        common = self.data.get('common', {})
        for export in self.data.get('exports'):
            yield Export(common, export)


class Export(object):

    def __init__(self, common, data):
        self.data = merge_overlay(data, common)

    def get(self, name, default=None):
        return self.data.get(name, default)

    def get_normalized(self, name, default=None):
        value = self.get(name, default=default)
        if value not in [None, default]:
            value = str(value).lower().strip()
        return value

    def get_bool(self, name, default=False):
        value = self.get_normalized(name)
        if value is None:
            return default
        return value in TRUISH

    def get_int(self, name, default=None):
        value = self.get_normalized(name)
        if value is None:
            return default
        return int(value)

    @property
    def skip(self):
        return self.get_bool('skip')

    @property
    def name(self):
        return self.get('name', self.get('query'))

########NEW FILE########
__FILENAME__ = common
import os
import re
import sys
import locale

try:
    str = unicode
except NameError:
    pass

from dataset.util import FreezeException
from slugify import slugify


TMPL_KEY = re.compile("{{([^}]*)}}")

OPERATIONS = {
        'identity': lambda x: x,
        'lower': lambda x: str(x).lower(),
        'slug': slugify
        }


class Serializer(object):

    def __init__(self, export, query):
        self.export = export
        self.query = query
        self._paths = []
        self._get_basepath()

        if export.get('filename') == '-':
            export['fileobj'] = sys.stdout
        self.fileobj = export.get('fileobj')

    def _get_basepath(self):
        prefix = self.export.get('prefix', '')
        prefix = os.path.abspath(prefix)
        prefix = os.path.realpath(prefix)
        self._prefix = prefix
        filename = self.export.get('filename')
        if filename is None:
            raise FreezeException("No 'filename' is specified")
        self._basepath = os.path.join(prefix, filename)

    def _tmpl(self, data):
        def repl(m):
            op, key = 'identity', m.group(1)
            if ':' in key:
                op, key = key.split(':', 1)
            return str(OPERATIONS.get(op)(data.get(key, '')))
        path = TMPL_KEY.sub(repl, self._basepath)
        enc = locale.getpreferredencoding()
        return os.path.realpath(path.encode(enc, 'replace'))

    def file_name(self, row):
        # signal that there is a fileobj available:
        if self.fileobj is not None:
            return None

        path = self._tmpl(row)
        if path not in self._paths:
            if not path.startswith(self._prefix):
                raise FreezeException("Possible path escape detected.")
            dn = os.path.dirname(path)
            if not os.path.isdir(dn):
                os.makedirs(dn)
            self._paths.append(path)
        return path

    @property
    def mode(self):
        mode = self.export.get_normalized('mode', 'list')
        if mode not in ['list', 'item']:
            raise FreezeException("Invalid mode: %s" % mode)
        return mode

    @property
    def wrap(self):
        return self.export.get_bool('wrap', default=self.mode == 'list')

    def serialize(self):
        self.init()
        transforms = self.export.get('transform', {})
        for row in self.query:

            for field, operation in transforms.items():
                row[field] = OPERATIONS.get(operation)(row.get(field))

            self.write(self.file_name(row), row)

        self.close()

########NEW FILE########
__FILENAME__ = fcsv
import csv
from datetime import datetime

from dataset.freeze.format.common import Serializer


def value_to_str(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, 'encode'):
        return value.encode('utf-8')
    if value is None:
        return ''
    return value


class CSVSerializer(Serializer):

    def init(self):
        self.handles = {}

    def write(self, path, result):
        keys = list(result.keys())
        if path not in self.handles:

            # handle fileobj that has been passed in:
            if path is not None:
                fh = open(path, 'wb')
            else:
                fh = self.fileobj

            writer = csv.writer(fh)
            writer.writerow([k.encode('utf-8') for k in keys])
            self.handles[path] = (writer, fh)
        writer, fh = self.handles[path]
        values = [value_to_str(result.get(k)) for k in keys]
        writer.writerow(values)

    def close(self):
        for writer, fh in self.handles.values():
            fh.close()

########NEW FILE########
__FILENAME__ = fjson
import json
from datetime import datetime
from collections import defaultdict

from dataset.freeze.format.common import Serializer


class JSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()


class JSONSerializer(Serializer):

    def init(self):
        self.buckets = defaultdict(list)

    def write(self, path, result):
        self.buckets[path].append(result)

    def wrap(self, result):
        if self.mode == 'item':
            result = result[0]
        if self.wrap:
            result = {
                'count': self.query.count,
                'results': result
            }
            meta = self.export.get('meta', {})
            if meta is not None:
                result['meta'] = meta
        return result

    def close(self):
        for path, result in self.buckets.items():
            result = self.wrap(result)

            fh = open(path, 'wb') if self.fileobj is None else self.fileobj

            data = json.dumps(result,
                              cls=JSONEncoder,
                              indent=self.export.get_int('indent'))
            if self.export.get('callback'):
                data = "%s && %s(%s);" % (self.export.get('callback'),
                                          self.export.get('callback'),
                                          data)
            fh.write(data)
            fh.close()

########NEW FILE########
__FILENAME__ = ftabson
from dataset.freeze.format.fjson import JSONSerializer


class TabsonSerializer(JSONSerializer):

    def wrap(self, result):
        fields = []
        data = []
        if len(result):
            keys = list(result[0].keys())
            fields = [{'id': k} for k in keys]
            for row in result:
                d = [row.get(k) for k in keys]
                data.append(d)
        result = {
            'count': self.query.count,
            'fields': fields,
            'data': data
            }
        meta = self.export.get('meta', {})
        if meta is not None:
            result['meta'] = meta
        return result

########NEW FILE########
__FILENAME__ = database
import logging
import threading
import re

try:
    from urllib.parse import urlencode
    from urllib.parse import parse_qs
except ImportError:
    from urllib import urlencode
    from urlparse import parse_qs

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import MetaData, Column
from sqlalchemy.schema import Table as SQLATable
from sqlalchemy import Integer, String

from alembic.migration import MigrationContext
from alembic.operations import Operations

from dataset.persistence.table import Table
from dataset.persistence.util import ResultIter
from dataset.util import DatasetException

log = logging.getLogger(__name__)


class Database(object):

    def __init__(self, url, schema=None, reflectMetadata=True,
                 engine_kwargs=None):
        if engine_kwargs is None:
            engine_kwargs = {}

        if url.startswith('postgres'):
            engine_kwargs.setdefault('poolclass', NullPool)

        self.lock = threading.RLock()
        self.local = threading.local()
        if '?' in url:
            url, query = url.split('?', 1)
            query = parse_qs(query)
            if schema is None:
                # le pop
                schema_qs = query.pop('schema', query.pop('searchpath', []))
                if len(schema_qs):
                    schema = schema_qs.pop()
            if len(query):
                url = url + '?' + urlencode(query, doseq=True)
        self.schema = schema
        self.engine = create_engine(url, **engine_kwargs)
        self.url = url
        self.metadata = MetaData(schema=schema)
        self.metadata.bind = self.engine
        if reflectMetadata:
            self.metadata.reflect(self.engine)
        self._tables = {}

    @property
    def executable(self):
        """ The current connection or engine against which statements
        will be executed. """
        if hasattr(self.local, 'connection'):
            return self.local.connection
        return self.engine

    @property
    def op(self):
        ctx = MigrationContext.configure(self.engine)
        return Operations(ctx)

    def _acquire(self):
        self.lock.acquire()

    def _release(self):
        if not hasattr(self.local, 'tx'):
            self.lock.release()
            self.local.must_release = False
        else:
            self.local.must_release = True

    def _release_internal(self):
        if not hasattr(self.local, 'must_release') and self.local.must_release:
            self.lock.release()
            self.local.must_release = False

    def begin(self):
        """ Enter a transaction explicitly. No data will be written
        until the transaction has been committed.

        **NOTICE:** Schema modification operations, such as the creation
        of tables or columns will not be part of the transactional context."""
        if not hasattr(self.local, 'connection'):
            self.local.connection = self.engine.connect()
        if not hasattr(self.local, 'tx'):
            self.local.tx = self.local.connection.begin()

    def commit(self):
        """ Commit the current transaction, making all statements executed
        since the transaction was begun permanent. """
        self.local.tx.commit()
        del self.local.tx
        self._release_internal()

    def rollback(self):
        """ Roll back the current transaction, discarding all statements
        executed since the transaction was begun. """
        self.local.tx.rollback()
        del self.local.tx
        self._release_internal()

    @property
    def tables(self):
        """
        Get a listing of all tables that exist in the database.
        """
        return list(
            set(self.metadata.tables.keys()) | set(self._tables.keys())
        )

    def create_table(self, table_name, primary_id='id', primary_type='Integer'):
        """
        Creates a new table. The new table will automatically have an `id` column
        unless specified via optional parameter primary_id, which will be used
        as the primary key of the table. Automatic id is set to be an
        auto-incrementing integer, while the type of custom primary_id can be a
        String or an Integer as specified with primary_type flag. The default
        length of String is 255. The caller can specify the length.
        The caller will be responsible for the uniqueness of manual primary_id.

        This custom id feature is only available via direct create_table call.

        Returns a :py:class:`Table <dataset.Table>` instance.
        ::

            table = db.create_table('population')

            # custom id and type
            table2 = db.create_table('population2', 'age')
            table3 = db.create_table('population3', primary_id='race', primary_type='String')
            # custom length of String
            table4 = db.create_table('population4', primary_id='race', primary_type='String(50)')
        """
        self._acquire()
        try:
            log.debug("Creating table: %s on %r" % (table_name, self.engine))
            match = re.match(r'^(Integer)$|^(String)(\(\d+\))?$', primary_type)
            if match:
                if match.group(1) == 'Integer':
                    auto_flag = False
                    if primary_id == 'id':
                        auto_flag = True
                    col = Column(primary_id, Integer, primary_key=True, autoincrement=auto_flag)
                elif not match.group(3):
                    col = Column(primary_id, String(255), primary_key=True)
                else:
                    len_string = int(match.group(3)[1:-1])
                    len_string = min(len_string, 255)
                    col = Column(primary_id, String(len_string), primary_key=True)
            else:
                raise DatasetException(
                    "The primary_type has to be either 'Integer' or 'String'.")

            table = SQLATable(table_name, self.metadata)
            table.append_column(col)
            table.create(self.engine)
            self._tables[table_name] = table
            return Table(self, table)
        finally:
            self._release()

    def load_table(self, table_name):
        """
        Loads a table. This will fail if the tables does not already
        exist in the database. If the table exists, its columns will be
        reflected and are available on the :py:class:`Table <dataset.Table>`
        object.

        Returns a :py:class:`Table <dataset.Table>` instance.
        ::

            table = db.load_table('population')
        """
        self._acquire()
        try:
            log.debug("Loading table: %s on %r" % (table_name, self))
            table = SQLATable(table_name, self.metadata, autoload=True)
            self._tables[table_name] = table
            return Table(self, table)
        finally:
            self._release()

    def update_table(self, table_name):
        self.metadata = MetaData(schema=self.schema)
        self.metadata.bind = self.engine
        self.metadata.reflect(self.engine)
        self._tables[table_name] = SQLATable(table_name, self.metadata)
        return self._tables[table_name]

    def get_table(self, table_name, primary_id='id', primary_type='Integer'):
        """
        Smart wrapper around *load_table* and *create_table*. Either loads a table
        or creates it if it doesn't exist yet.
        For short-hand to create a table with custom id and type using [], where
        table_name, primary_id, and primary_type are specified as a tuple

        Returns a :py:class:`Table <dataset.Table>` instance.
        ::

            table = db.get_table('population')
            # you can also use the short-hand syntax:
            table = db['population']

        """
        if table_name in self._tables:
            return Table(self, self._tables[table_name])
        self._acquire()
        try:
            if self.engine.has_table(table_name, schema=self.schema):
                return self.load_table(table_name)
            else:
                return self.create_table(table_name, primary_id, primary_type)
        finally:
            self._release()

    def __getitem__(self, table_name):
        return self.get_table(table_name)

    def query(self, query, **kw):
        """
        Run a statement on the database directly, allowing for the
        execution of arbitrary read/write queries. A query can either be
        a plain text string, or a `SQLAlchemy expression <http://docs.sqlalchemy.org/ru/latest/core/tutorial.html#selecting>`_. The returned
        iterator will yield each result sequentially.

        Any keyword arguments will be passed into the query to perform
        parameter binding.
        ::

            res = db.query('SELECT user, COUNT(*) c FROM photos GROUP BY user')
            for row in res:
                print(row['user'], row['c'])
        """
        return ResultIter(self.executable.execute(query, **kw))

    def __repr__(self):
        return '<Database(%s)>' % self.url

########NEW FILE########
__FILENAME__ = table
import logging
from itertools import count

from sqlalchemy.sql import and_, expression
from sqlalchemy.schema import Column, Index
from sqlalchemy import alias
from dataset.persistence.util import guess_type
from dataset.persistence.util import ResultIter, convert_row
from dataset.util import DatasetException


log = logging.getLogger(__name__)


class Table(object):

    def __init__(self, database, table):
        self.indexes = dict((i.name, i) for i in table.indexes)
        self.database = database
        self.table = table
        self._is_dropped = False

    @property
    def columns(self):
        """
        Get a listing of all columns that exist in the table.
        """
        return list(self.table.columns.keys())

    def drop(self):
        """
        Drop the table from the database, deleting both the schema
        and all the contents within it.

        Note: the object will raise an Exception if you use it after
        dropping the table. If you want to re-create the table, make
        sure to get a fresh instance from the :py:class:`Database <dataset.Database>`.
        """
        self.database._acquire()
        self._is_dropped = True
        self.database._tables.pop(self.table.name, None)
        self.table.drop(self.database.engine)

    def _check_dropped(self):
        if self._is_dropped:
            raise DatasetException('the table has been dropped. this object should not be used again.')

    def insert(self, row, ensure=True, types={}):
        """
        Add a row (type: dict) by inserting it into the table.
        If ``ensure`` is set, any of the keys of the row are not
        table columns, they will be created automatically.

        During column creation, ``types`` will be checked for a key
        matching the name of a column to be created, and the given
        SQLAlchemy column type will be used. Otherwise, the type is
        guessed from the row value, defaulting to a simple unicode
        field.
        ::

            data = dict(title='I am a banana!')
            table.insert(data)
        """
        self._check_dropped()
        if ensure:
            self._ensure_columns(row, types=types)
        res = self.database.executable.execute(self.table.insert(row))
        if len(res.inserted_primary_key) > 0:
            return res.inserted_primary_key[0]

    def insert_many(self, rows, chunk_size=1000, ensure=True, types={}):
        """
        Add many rows at a time, which is significantly faster than adding
        them one by one. Per default the rows are processed in chunks of
        1000 per commit, unless you specify a different ``chunk_size``.

        See :py:meth:`insert() <dataset.Table.insert>` for details on
        the other parameters.
        ::

            rows = [dict(name='Dolly')] * 10000
            table.insert_many(rows)
        """
        def _process_chunk(chunk):
            if ensure:
                for row in chunk:
                    self._ensure_columns(row, types=types)
            self.table.insert().execute(chunk)
        self._check_dropped()

        chunk = []
        for i, row in enumerate(rows, start=1):
            chunk.append(row)
            if i % chunk_size == 0:
                _process_chunk(chunk)
                chunk = []

        if chunk:
            _process_chunk(chunk)

    def update(self, row, keys, ensure=True, types={}):
        """
        Update a row in the table. The update is managed via
        the set of column names stated in ``keys``: they will be
        used as filters for the data to be updated, using the values
        in ``row``.
        ::

            # update all entries with id matching 10, setting their title columns
            data = dict(id=10, title='I am a banana!')
            table.update(data, ['id'])

        If keys in ``row`` update columns not present in the table,
        they will be created based on the settings of ``ensure`` and
        ``types``, matching the behavior of :py:meth:`insert() <dataset.Table.insert>`.
        """
        # check whether keys arg is a string and format as a list
        if not isinstance(keys, (list, tuple)):
            keys = [keys]
        self._check_dropped()
        if not keys or len(keys) == len(row):
            return False
        clause = [(u, row.get(u)) for u in keys]

        if ensure:
            self._ensure_columns(row, types=types)

        # Don't update the key itself, so remove any keys from the row dict
        clean_row = row.copy()
        for key in keys:
            if key in clean_row.keys():
                del clean_row[key]

        try:
            filters = self._args_to_clause(dict(clause))
            stmt = self.table.update(filters, clean_row)
            rp = self.database.executable.execute(stmt)
            return rp.rowcount > 0
        except KeyError:
            return False

    def upsert(self, row, keys, ensure=True, types={}):
        """
        An UPSERT is a smart combination of insert and update. If rows with matching ``keys`` exist
        they will be updated, otherwise a new row is inserted in the table.
        ::

            data = dict(id=10, title='I am a banana!')
            table.upsert(data, ['id'])
        """
        # check whether keys arg is a string and format as a list
        if not isinstance(keys, (list, tuple)):
            keys = [keys]
        self._check_dropped()
        if ensure:
            self.create_index(keys)

        filters = {}
        for key in keys:
            filters[key] = row.get(key)

        if self.find_one(**filters) is not None:
            self.update(row, keys, ensure=ensure, types=types)
        else:
            self.insert(row, ensure=ensure, types=types)

    def delete(self, **_filter):
        """ Delete rows from the table. Keyword arguments can be used
        to add column-based filters. The filter criterion will always
        be equality:

        .. code-block:: python

            table.delete(place='Berlin')

        If no arguments are given, all records are deleted.
        """
        self._check_dropped()
        if _filter:
            q = self._args_to_clause(_filter)
            stmt = self.table.delete(q)
        else:
            stmt = self.table.delete()
        rows = self.database.executable.execute(stmt)
        return rows.rowcount > 0

    def _ensure_columns(self, row, types={}):
        # Keep order of inserted columns
        for column in row.keys():
            if column in self.table.columns.keys():
                continue
            if column in types:
                _type = types[column]
            else:
                _type = guess_type(row[column])
            log.debug("Creating column: %s (%s) on %r" % (column,
                                                          _type, self.table.name))
            self.create_column(column, _type)

    def _args_to_clause(self, args):
        self._ensure_columns(args)
        clauses = []
        for k, v in args.items():
            if isinstance(v, (list, tuple)):
                clauses.append(self.table.c[k].in_(v))
            else:
                clauses.append(self.table.c[k] == v)
        return and_(*clauses)

    def create_column(self, name, type):
        """
        Explicitely create a new column ``name`` of a specified type.
        ``type`` must be a `SQLAlchemy column type <http://docs.sqlalchemy.org/en/rel_0_8/core/types.html>`_.
        ::

            table.create_column('created_at', sqlalchemy.DateTime)
        """
        self._check_dropped()
        self.database._acquire()
        try:
            if name not in self.table.columns.keys():
                self.database.op.add_column(
                    self.table.name,
                    Column(name, type)
                )
                self.table = self.database.update_table(self.table.name)
        finally:
            self.database._release()

    def drop_column(self, name):
        """
        Drop the column ``name``
        ::

            table.drop_column('created_at')
        """
        self._check_dropped()
        self.database._acquire()
        try:
            if name in self.table.columns.keys():
                self.database.op.drop_column(
                    self.table.name,
                    name
                )
                self.table = self.database.update_table(self.table.name)
        finally:
            self.database._release()

    def create_index(self, columns, name=None):
        """
        Create an index to speed up queries on a table. If no ``name`` is given a random name is created.
        ::

            table.create_index(['name', 'country'])
        """
        self._check_dropped()
        if not name:
            sig = abs(hash('||'.join(columns)))
            name = 'ix_%s_%s' % (self.table.name, sig)
        if name in self.indexes:
            return self.indexes[name]
        try:
            self.database._acquire()
            columns = [self.table.c[c] for c in columns]
            idx = Index(name, *columns)
            idx.create(self.database.engine)
        except:
            idx = None
        finally:
            self.database._release()
        self.indexes[name] = idx
        return idx

    def find_one(self, **_filter):
        """
        Works just like :py:meth:`find() <dataset.Table.find>` but returns one result, or None.
        ::

            row = table.find_one(country='United States')
        """
        self._check_dropped()
        args = self._args_to_clause(_filter)
        query = self.table.select(whereclause=args, limit=1)
        rp = self.database.executable.execute(query)
        return convert_row(rp.fetchone())

    def _args_to_order_by(self, order_by):
        if order_by[0] == '-':
            return self.table.c[order_by[1:]].desc()
        else:
            return self.table.c[order_by].asc()

    def find(self, _limit=None, _offset=0, _step=5000,
             order_by='id', **_filter):
        """
        Performs a simple search on the table. Simply pass keyword arguments as ``filter``.
        ::

            results = table.find(country='France')
            results = table.find(country='France', year=1980)

        Using ``_limit``::

            # just return the first 10 rows
            results = table.find(country='France', _limit=10)

        You can sort the results by single or multiple columns. Append a minus sign
        to the column name for descending order::

            # sort results by a column 'year'
            results = table.find(country='France', order_by='year')
            # return all rows sorted by multiple columns (by year in descending order)
            results = table.find(order_by=['country', '-year'])

        By default :py:meth:`find() <dataset.Table.find>` will break the
        query into chunks of ``_step`` rows to prevent huge tables
        from being loaded into memory at once.

        For more complex queries, please use :py:meth:`db.query() <dataset.Database.query>`
        instead."""
        self._check_dropped()
        if not isinstance(order_by, (list, tuple)):
            order_by = [order_by]
        order_by = [o for o in order_by if (o.startswith('-') and o[1:] or o) in self.table.columns]
        order_by = [self._args_to_order_by(o) for o in order_by]

        args = self._args_to_clause(_filter)

        # query total number of rows first
        count_query = alias(self.table.select(whereclause=args, limit=_limit, offset=_offset), name='count_query_alias').count()
        rp = self.database.executable.execute(count_query)
        total_row_count = rp.fetchone()[0]

        if _limit is None:
            _limit = total_row_count

        if _step is None or _step is False or _step == 0:
            _step = total_row_count

        if total_row_count > _step and not order_by:
            _step = total_row_count
            log.warn("query cannot be broken into smaller sections because it is unordered")

        queries = []

        for i in count():
            qoffset = _offset + (_step * i)
            qlimit = min(_limit - (_step * i), _step)
            if qlimit <= 0:
                break
            queries.append(self.table.select(whereclause=args, limit=qlimit,
                                             offset=qoffset, order_by=order_by))
        return ResultIter((self.database.executable.execute(q) for q in queries))

    def __len__(self):
        """
        Returns the number of rows in the table.
        """
        d = next(self.database.query(self.table.count()))
        return list(d.values()).pop()

    def distinct(self, *columns, **_filter):
        """
        Returns all rows of a table, but removes rows in with duplicate values in ``columns``.
        Interally this creates a `DISTINCT statement <http://www.w3schools.com/sql/sql_distinct.asp>`_.
        ::

            # returns only one row per year, ignoring the rest
            table.distinct('year')
            # works with multiple columns, too
            table.distinct('year', 'country')
            # you can also combine this with a filter
            table.distinct('year', country='China')
        """
        self._check_dropped()
        qargs = []
        try:
            columns = [self.table.c[c] for c in columns]
            for col, val in _filter.items():
                qargs.append(self.table.c[col] == val)
        except KeyError:
            return []

        q = expression.select(columns, distinct=True,
                              whereclause=and_(*qargs),
                              order_by=[c.asc() for c in columns])
        return self.database.query(q)

    def all(self):
        """
        Returns all rows of the table as simple dictionaries. This is simply a shortcut
        to *find()* called with no arguments.
        ::

            rows = table.all()"""
        return self.find()

    def __iter__(self):
        """
        Allows for iterating over all rows in the table without explicetly
        calling :py:meth:`all() <dataset.Table.all>`.
        ::

            for row in table:
                print(row)
        """
        return self.all()

    def __repr__(self):
        return '<Table(%s)>' % self.table.name

########NEW FILE########
__FILENAME__ = util
from datetime import datetime, timedelta
from inspect import isgenerator

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from sqlalchemy import Integer, UnicodeText, Float, DateTime, Boolean, types, Table, event


def guess_type(sample):
    if isinstance(sample, bool):
        return Boolean
    elif isinstance(sample, int):
        return Integer
    elif isinstance(sample, float):
        return Float
    elif isinstance(sample, datetime):
        return DateTime
    return UnicodeText


def convert_row(row):
    if row is None:
        return None
    return OrderedDict(row.items())


class ResultIter(object):
    """ SQLAlchemy ResultProxies are not iterable to get a
    list of dictionaries. This is to wrap them. """

    def __init__(self, result_proxies):
        if not isgenerator(result_proxies):
            result_proxies = iter((result_proxies, ))
        self.result_proxies = result_proxies
        self.count = 0
        self.rp = None

    def _next_rp(self):
        try:
            self.rp = next(self.result_proxies)
            self.count += self.rp.rowcount
            self.keys = list(self.rp.keys())
            return True
        except StopIteration:
            return False

    def __next__(self):
        if self.rp is None:
            if not self._next_rp():
                raise StopIteration
        row = self.rp.fetchone()
        if row is None:
            if self._next_rp():
                return next(self)
            else:
                # stop here
                raise StopIteration
        return convert_row(row)

    next = __next__

    def __iter__(self):
        return self


def sqlite_datetime_fix():
    class SQLiteDateTimeType(types.TypeDecorator):
        impl = types.Integer
        epoch = datetime(1970, 1, 1, 0, 0, 0)

        def process_bind_param(self, value, dialect):
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            return (value / 1000 - self.epoch).total_seconds()

        def process_result_value(self, value, dialect):
            if value is None:
                return None
            if isinstance(value, int):
                return self.epoch + timedelta(seconds=value / 1000)
            return value

    def is_sqlite(inspector):
        return inspector.engine.dialect.name == "sqlite"

    def is_datetime(column_info):
        return isinstance(column_info['type'], types.DateTime)

    @event.listens_for(Table, "column_reflect")
    def setup_epoch(inspector, table, column_info):
        if is_sqlite(inspector) and is_datetime(column_info):
            column_info['type'] = SQLiteDateTimeType()

########NEW FILE########
__FILENAME__ = util
# coding: utf-8
import re

SLUG_REMOVE = re.compile(r'[,\s\.\(\)/\\;:]*')


class DatasetException(Exception):
    pass


class FreezeException(DatasetException):
    pass

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# dataset documentation build configuration file, created by
# sphinx-quickstart on Mon Apr  1 18:41:21 2013.
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
sys.path.insert(0, os.path.abspath('../'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'dataset'
copyright = u'2013, Friedrich Lindenberg, Gregor Aisch, Stefan Wehrmeyer'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5'
# The full version, including alpha/beta/rc tags.
release = '0.5'

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
html_theme = 'kr'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# html_theme_options = {
#     'stickysidebar': "true"
# }

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

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
html_sidebars = {
    'index': ['sidebarlogo.html', 'sourcelink.html', 'searchbox.html'],
    'api': ['sidebarlogo.html', 'autotoc.html', 'sourcelink.html', 'searchbox.html'],
    '**': ['sidebarlogo.html', 'localtoc.html', 'sourcelink.html', 'searchbox.html']
}

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
html_show_sourcelink = False

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
htmlhelp_basename = 'datasetdoc'


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
  ('index', 'dataset.tex', u'dataset Documentation',
   u'Friedrich Lindenberg, Gregor Aisch, Stefan Wehrmeyer', 'manual'),
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
    ('index', 'dataset', u'dataset Documentation',
     [u'Friedrich Lindenberg, Gregor Aisch, Stefan Wehrmeyer'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'dataset', u'dataset Documentation',
   u'Friedrich Lindenberg, Gregor Aisch, Stefan Wehrmeyer', 'dataset', 'One line description of project.',
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

########NEW FILE########
__FILENAME__ = flask_theme_support
# flasky extensions.  flasky pygments style based on tango style
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class FlaskyStyle(Style):
    background_color = "#f8f8f8"
    default_style = ""

    styles = {
        # No corresponding class for the following:
        #Text:                     "", # class:  ''
        Whitespace:                "underline #f8f8f8",      # class: 'w'
        Error:                     "#a40000 border:#ef2929", # class: 'err'
        Other:                     "#000000",                # class 'x'

        Comment:                   "italic #8f5902", # class: 'c'
        Comment.Preproc:           "noitalic",       # class: 'cp'

        Keyword:                   "bold #004461",   # class: 'k'
        Keyword.Constant:          "bold #004461",   # class: 'kc'
        Keyword.Declaration:       "bold #004461",   # class: 'kd'
        Keyword.Namespace:         "bold #004461",   # class: 'kn'
        Keyword.Pseudo:            "bold #004461",   # class: 'kp'
        Keyword.Reserved:          "bold #004461",   # class: 'kr'
        Keyword.Type:              "bold #004461",   # class: 'kt'

        Operator:                  "#582800",   # class: 'o'
        Operator.Word:             "bold #004461",   # class: 'ow' - like keywords

        Punctuation:               "bold #000000",   # class: 'p'

        # because special names such as Name.Class, Name.Function, etc.
        # are not recognized as such later in the parsing, we choose them
        # to look the same as ordinary variables.
        Name:                      "#000000",        # class: 'n'
        Name.Attribute:            "#c4a000",        # class: 'na' - to be revised
        Name.Builtin:              "#004461",        # class: 'nb'
        Name.Builtin.Pseudo:       "#3465a4",        # class: 'bp'
        Name.Class:                "#000000",        # class: 'nc' - to be revised
        Name.Constant:             "#000000",        # class: 'no' - to be revised
        Name.Decorator:            "#888",           # class: 'nd' - to be revised
        Name.Entity:               "#ce5c00",        # class: 'ni'
        Name.Exception:            "bold #cc0000",   # class: 'ne'
        Name.Function:             "#000000",        # class: 'nf'
        Name.Property:             "#000000",        # class: 'py'
        Name.Label:                "#f57900",        # class: 'nl'
        Name.Namespace:            "#000000",        # class: 'nn' - to be revised
        Name.Other:                "#000000",        # class: 'nx'
        Name.Tag:                  "bold #004461",   # class: 'nt' - like a keyword
        Name.Variable:             "#000000",        # class: 'nv' - to be revised
        Name.Variable.Class:       "#000000",        # class: 'vc' - to be revised
        Name.Variable.Global:      "#000000",        # class: 'vg' - to be revised
        Name.Variable.Instance:    "#000000",        # class: 'vi' - to be revised

        Number:                    "#990000",        # class: 'm'

        Literal:                   "#000000",        # class: 'l'
        Literal.Date:              "#000000",        # class: 'ld'

        String:                    "#4e9a06",        # class: 's'
        String.Backtick:           "#4e9a06",        # class: 'sb'
        String.Char:               "#4e9a06",        # class: 'sc'
        String.Doc:                "italic #8f5902", # class: 'sd' - like a comment
        String.Double:             "#4e9a06",        # class: 's2'
        String.Escape:             "#4e9a06",        # class: 'se'
        String.Heredoc:            "#4e9a06",        # class: 'sh'
        String.Interpol:           "#4e9a06",        # class: 'si'
        String.Other:              "#4e9a06",        # class: 'sx'
        String.Regex:              "#4e9a06",        # class: 'sr'
        String.Single:             "#4e9a06",        # class: 's1'
        String.Symbol:             "#4e9a06",        # class: 'ss'

        Generic:                   "#000000",        # class: 'g'
        Generic.Deleted:           "#a40000",        # class: 'gd'
        Generic.Emph:              "italic #000000", # class: 'ge'
        Generic.Error:             "#ef2929",        # class: 'gr'
        Generic.Heading:           "bold #000080",   # class: 'gh'
        Generic.Inserted:          "#00A000",        # class: 'gi'
        Generic.Output:            "#888",           # class: 'go'
        Generic.Prompt:            "#745334",        # class: 'gp'
        Generic.Strong:            "bold #000000",   # class: 'gs'
        Generic.Subheading:        "bold #800080",   # class: 'gu'
        Generic.Traceback:         "bold #a40000",   # class: 'gt'
    }

########NEW FILE########
__FILENAME__ = sample_data
# -*- encoding: utf-8 -*-
from datetime import datetime

TEST_CITY_1 = u'B€rkeley'
TEST_CITY_2 = u'G€lway'

TEST_DATA = [
    {
        'date': datetime(2011, 1, 1),
        'temperature': 1,
        'place': TEST_CITY_2
    },
    {
        'date': datetime(2011, 1, 2),
        'temperature': -1,
        'place': TEST_CITY_2
    },
    {
        'date': datetime(2011, 1, 3),
        'temperature': 0,
        'place': TEST_CITY_2
    },
    {
        'date': datetime(2011, 1, 1),
        'temperature': 6,
        'place': TEST_CITY_1
    },
    {
        'date': datetime(2011, 1, 2),
        'temperature': 8,
        'place': TEST_CITY_1
    },
    {
        'date': datetime(2011, 1, 3),
        'temperature': 5,
        'place': TEST_CITY_1
    }
]

########NEW FILE########
__FILENAME__ = test_persistence
import os
import unittest
from datetime import datetime

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict  # Python < 2.7 drop-in

from sqlalchemy.exc import IntegrityError

from dataset import connect
from dataset.util import DatasetException

from .sample_data import TEST_DATA, TEST_CITY_1


class DatabaseTestCase(unittest.TestCase):

    def setUp(self):
        os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
        self.db = connect(os.environ['DATABASE_URL'])
        self.tbl = self.db['weather']
        for row in TEST_DATA:
            self.tbl.insert(row)

    def tearDown(self):
        for table in self.db.tables:
            self.db[table].drop()

    def test_valid_database_url(self):
        assert self.db.url, os.environ['DATABASE_URL']

    def test_database_url_query_string(self):
        db = connect('sqlite:///:memory:/?cached_statements=1')
        assert 'cached_statements' in db.url, db.url

    def test_tables(self):
        assert self.db.tables == ['weather'], self.db.tables

    def test_create_table(self):
        table = self.db['foo']
        assert table.table.exists()
        assert len(table.table.columns) == 1, table.table.columns
        assert 'id' in table.table.c, table.table.c

    def test_create_table_custom_id1(self):
        pid = "string_id"
        table = self.db.create_table("foo2", pid, 'String')
        assert table.table.exists()
        assert len(table.table.columns) == 1, table.table.columns
        assert pid in table.table.c, table.table.c

        table.insert({
            'string_id': 'foobar'})
        assert table.find_one(string_id='foobar')['string_id'] == 'foobar'

    def test_create_table_custom_id2(self):
        pid = "string_id"
        table = self.db.create_table("foo3", pid, 'String(50)')
        assert table.table.exists()
        assert len(table.table.columns) == 1, table.table.columns
        assert pid in table.table.c, table.table.c

        table.insert({
            'string_id': 'foobar'})
        assert table.find_one(string_id='foobar')['string_id'] == 'foobar'

    def test_create_table_custom_id3(self):
        pid = "int_id"
        table = self.db.create_table("foo4", primary_id=pid)
        assert table.table.exists()
        assert len(table.table.columns) == 1, table.table.columns
        assert pid in table.table.c, table.table.c

        table.insert({'int_id': 123})
        table.insert({'int_id': 124})
        assert table.find_one(int_id=123)['int_id'] == 123
        assert table.find_one(int_id=124)['int_id'] == 124
        self.assertRaises(IntegrityError, lambda: table.insert({'int_id': 123}))

    def test_create_table_shorthand1(self):
        pid = "int_id"
        table = self.db.get_table('foo5', pid)
        assert table.table.exists
        assert len(table.table.columns) == 1, table.table.columns
        assert pid in table.table.c, table.table.c

        table.insert({'int_id': 123})
        table.insert({'int_id': 124})
        assert table.find_one(int_id=123)['int_id'] == 123
        assert table.find_one(int_id=124)['int_id'] == 124
        self.assertRaises(IntegrityError, lambda: table.insert({'int_id': 123}))

    def test_create_table_shorthand2(self):
        pid = "string_id"
        table = self.db.get_table('foo6', primary_id=pid, primary_type='String')
        assert table.table.exists
        assert len(table.table.columns) == 1, table.table.columns
        assert pid in table.table.c, table.table.c

        table.insert({
            'string_id': 'foobar'})
        assert table.find_one(string_id='foobar')['string_id'] == 'foobar'

    def test_create_table_shorthand3(self):
        pid = "string_id"
        table = self.db.get_table('foo7', primary_id=pid, primary_type='String(20)')
        assert table.table.exists
        assert len(table.table.columns) == 1, table.table.columns
        assert pid in table.table.c, table.table.c

        table.insert({
            'string_id': 'foobar'})
        assert table.find_one(string_id='foobar')['string_id'] == 'foobar'

    def test_load_table(self):
        tbl = self.db.load_table('weather')
        assert tbl.table == self.tbl.table

    def test_query(self):
        r = self.db.query('SELECT COUNT(*) AS num FROM weather').next()
        assert r['num'] == len(TEST_DATA), r

    def test_table_cache_updates(self):
        tbl1 = self.db.get_table('people')
        data = OrderedDict([('first_name', 'John'), ('last_name', 'Smith')])
        tbl1.insert(data)
        data['id'] = 1
        tbl2 = self.db.get_table('people')
        assert dict(tbl2.all().next()) == dict(data), (tbl2.all().next(), data)


class TableTestCase(unittest.TestCase):

    def setUp(self):
        self.db = connect('sqlite:///:memory:')
        self.tbl = self.db['weather']
        for row in TEST_DATA:
            self.tbl.insert(row)

    def test_insert(self):
        assert len(self.tbl) == len(TEST_DATA), len(self.tbl)
        last_id = self.tbl.insert({
            'date': datetime(2011, 1, 2),
            'temperature': -10,
            'place': 'Berlin'}
        )
        assert len(self.tbl) == len(TEST_DATA) + 1, len(self.tbl)
        assert self.tbl.find_one(id=last_id)['place'] == 'Berlin'

    def test_upsert(self):
        self.tbl.upsert({
            'date': datetime(2011, 1, 2),
            'temperature': -10,
            'place': 'Berlin'},
            ['place']
        )
        assert len(self.tbl) == len(TEST_DATA) + 1, len(self.tbl)
        self.tbl.upsert({
            'date': datetime(2011, 1, 2),
            'temperature': -10,
            'place': 'Berlin'},
            ['place']
        )
        assert len(self.tbl) == len(TEST_DATA) + 1, len(self.tbl)

    def test_upsert_all_key(self):
        for i in range(0, 2):
            self.tbl.upsert({
                'date': datetime(2011, 1, 2),
                'temperature': -10,
                'place': 'Berlin'},
                ['date', 'temperature', 'place']
            )

    def test_delete(self):
        self.tbl.insert({
            'date': datetime(2011, 1, 2),
            'temperature': -10,
            'place': 'Berlin'}
        )
        assert len(self.tbl) == len(TEST_DATA) + 1, len(self.tbl)
        assert self.tbl.delete(place='Berlin') is True, 'should return 1'
        assert len(self.tbl) == len(TEST_DATA), len(self.tbl)
        assert self.tbl.delete() is True, 'should return non zero'
        assert len(self.tbl) == 0, len(self.tbl)

    def test_repr(self):
        assert repr(self.tbl) == '<Table(weather)>', 'the representation should be <Table(weather)>'

    def test_delete_nonexist_entry(self):
        assert self.tbl.delete(place='Berlin') is False, 'entry not exist, should fail to delete'

    def test_find_one(self):
        self.tbl.insert({
            'date': datetime(2011, 1, 2),
            'temperature': -10,
            'place': 'Berlin'}
        )
        d = self.tbl.find_one(place='Berlin')
        assert d['temperature'] == -10, d
        d = self.tbl.find_one(place='Atlantis')
        assert d is None, d

    def test_find(self):
        ds = list(self.tbl.find(place=TEST_CITY_1))
        assert len(ds) == 3, ds
        ds = list(self.tbl.find(place=TEST_CITY_1, _limit=2))
        assert len(ds) == 2, ds
        ds = list(self.tbl.find(place=TEST_CITY_1, _limit=2, _step=1))
        assert len(ds) == 2, ds
        ds = list(self.tbl.find(place=TEST_CITY_1, _limit=1, _step=2))
        assert len(ds) == 1, ds
        ds = list(self.tbl.find(order_by=['temperature']))
        assert ds[0]['temperature'] == -1, ds
        ds = list(self.tbl.find(order_by=['-temperature']))
        assert ds[0]['temperature'] == 8, ds

    def test_offset(self):
        ds = list(self.tbl.find(place=TEST_CITY_1, _offset=1))
        assert len(ds) == 2, ds
        ds = list(self.tbl.find(place=TEST_CITY_1, _limit=2, _offset=2))
        assert len(ds) == 1, ds

    def test_distinct(self):
        x = list(self.tbl.distinct('place'))
        assert len(x) == 2, x
        x = list(self.tbl.distinct('place', 'date'))
        assert len(x) == 6, x

    def test_insert_many(self):
        data = TEST_DATA * 100
        self.tbl.insert_many(data, chunk_size=13)
        assert len(self.tbl) == len(data) + 6

    def test_drop_warning(self):
        assert self.tbl._is_dropped is False, 'table shouldn\'t be dropped yet'
        self.tbl.drop()
        assert self.tbl._is_dropped is True, 'table should be dropped now'
        try:
            list(self.tbl.all())
        except DatasetException:
            pass
        else:
            assert False, 'we should not reach else block, no exception raised!'

    def test_columns(self):
        cols = self.tbl.columns
        assert len(list(cols)) == 4, 'column count mismatch'
        assert 'date' in cols and 'temperature' in cols and 'place' in cols

    def test_iter(self):
        c = 0
        for row in self.tbl:
            c += 1
        assert c == len(self.tbl)

    def test_update(self):
        date = datetime(2011, 1, 2)
        res = self.tbl.update({
            'date': date,
            'temperature': -10,
            'place': TEST_CITY_1},
            ['place', 'date']
        )
        assert res, 'update should return True'
        m = self.tbl.find_one(place=TEST_CITY_1, date=date)
        assert m['temperature'] == -10, 'new temp. should be -10 but is %d' % m['temperature']

    def test_create_column(self):
        from sqlalchemy import FLOAT
        tbl = self.tbl
        tbl.create_column('foo', FLOAT)
        assert 'foo' in tbl.table.c, tbl.table.c
        assert isinstance(tbl.table.c['foo'].type, FLOAT), tbl.table.c['foo'].type
        assert 'foo' in tbl.columns, tbl.columns

    def test_key_order(self):
        res = self.db.query('SELECT temperature, place FROM weather LIMIT 1')
        keys = list(res.next().keys())
        assert keys[0] == 'temperature'
        assert keys[1] == 'place'

    def test_empty_query(self):
        m = self.tbl.find(place='not in data')
        l = list(m)  # exhaust iterator
        assert len(l) == 0

########NEW FILE########
