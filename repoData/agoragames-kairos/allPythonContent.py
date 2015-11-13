__FILENAME__ = cassandra_backend
'''
Copyright (c) 2012-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/kairos/blob/master/LICENSE.txt
'''
from .exceptions import *
from .timeseries import *

import cql

import time
from datetime import date, datetime
from datetime import time as time_type
from decimal import Decimal
from Queue import Queue, Empty, Full
import re
from urlparse import *

# Test python3 compatibility
try:
  x = long(1)
except NameError:
  long = int
try:
  x = unicode('foo')
except NameError:
  unicode = str

TYPE_MAP = {
  str         : 'ascii',
  'str'       : 'ascii',
  'string'    : 'ascii',

  unicode     : 'text',  # works for py3 too
  'unicode'   : 'text',

  float       : 'float',
  'float'     : 'float',

  'double'    : 'double',

  int         : 'int',
  'int'       : 'int',
  'integer'   : 'int',

  long        : 'varint', # works for py3 too
  'long'      : 'varint',
  'int64'     : 'bigint',

  'decimal'   : 'decimal',

  bool        : 'boolean',
  'bool'      : 'boolean',
  'boolean'   : 'boolean',

  'text'      : 'text',
  'clob'      : 'blob',
  'blob'      : 'blob',

  'inet'      : 'inet',
}

QUOTE_TYPES = set(['ascii','text','blob'])
QUOTE_MATCH = re.compile("^'.*'$")

def scoped_connection(func):
  '''
  Decorator that gives out connections.
  '''
  def _with(series, *args, **kwargs):
    connection = None
    try:
      connection = series._connection()
      return func(series, connection, *args, **kwargs)
    finally:
      series._return( connection )
  return _with

class CassandraBackend(Timeseries):

  def __new__(cls, *args, **kwargs):
    if cls==CassandraBackend:
      ttype = kwargs.pop('type', None)
      if ttype=='series':
        return CassandraSeries.__new__(CassandraSeries, *args, **kwargs)
      elif ttype=='histogram':
        return CassandraHistogram.__new__(CassandraHistogram, *args, **kwargs)
      elif ttype=='count':
        return CassandraCount.__new__(CassandraCount, *args, **kwargs)
      elif ttype=='gauge':
        return CassandraGauge.__new__(CassandraGauge, *args, **kwargs)
      elif ttype=='set':
        return CassandraSet.__new__(CassandraSet, *args, **kwargs)
      raise NotImplementedError("No implementation for %s types"%(ttype))
    return Timeseries.__new__(cls, *args, **kwargs)

  @classmethod
  def url_parse(self, url, **kwargs):
    location = urlparse(url)
    if location.scheme in ('cassandra','cql'):
      host = location.netloc or "localhost:9160"
      if re.search(":[0-9]+$", host):
        ip,port = host.split(':')
      else:
        ip = host
        port = 9160

      keyspace = location.path[1:] or kwargs.get('database', 'kairos')
      if '?' in keyspace:
        keyspace,params = keyspace.split('?')

      return cql.connect(ip, int(port), keyspace, cql_version='3.0.0', **kwargs)


  def __init__(self, client, **kwargs):
    '''
    Initialize the sql backend after timeseries has processed the configuration.
    '''
    # Only CQL3 is supported
    if client.cql_major_version != 3:
      raise TypeError("Only CQL3 is supported")

    vtype = kwargs.get('value_type', float)
    if vtype in TYPE_MAP:
      self._value_type = TYPE_MAP[vtype]
    else:
      raise TypeError("Unsupported type '%s'"%(vtype))

    self._table = kwargs.get('table_name', self._table)

    # copy internal variables of the connection for poor-mans pooling
    self._host = client.host
    self._port = client.port
    self._keyspace = client.keyspace
    self._cql_version = client.cql_version
    self._compression = client.compression
    self._consistency_level = client.consistency_level
    self._transport = client.transport
    self._credentials = client.credentials
    self._pool = Queue(kwargs.get('pool_size',0))
    self._pool.put( client )

    super(CassandraBackend,self).__init__(client, **kwargs)

  def _connection(self):
    '''
    Return a connection from the pool
    '''
    try:
      return self._pool.get(False)
    except Empty:
      args = [
        self._host, self._port, self._keyspace
      ]
      kwargs = {
        'user'              : None,
        'password'          : None,
        'cql_version'       : self._cql_version,
        'compression'       : self._compression,
        'consistency_level' : self._consistency_level,
        'transport'         : self._transport,
      }
      if self._credentials:
        kwargs['user'] = self._credentials['user']
        kwargs['password'] = self._credentials['password']
      return cql.connect(*args, **kwargs)

  def _return(self, connection):
    try:
      self._pool.put(connection, False)
    except Full:
      # do not return connection to the pool.
      pass

  def _insert(self, name, value, timestamp, intervals, **kwargs):
    '''
    Insert the new value.
    '''
    if self._value_type in QUOTE_TYPES and not QUOTE_MATCH.match(value):
      value = "'%s'"%(value)

    for interval,config in self._intervals.items():
      timestamps = self._normalize_timestamps(timestamp, intervals, config)
      for tstamp in timestamps:
        self._insert_data(name, value, tstamp, interval, config, **kwargs)

  @scoped_connection
  def _insert_data(self, connection, name, value, timestamp, interval, config):
    '''Helper to insert data into cql.'''
    cursor = connection.cursor()
    try:
      stmt = self._insert_stmt(name, value, timestamp, interval, config)
      if stmt:
        cursor.execute(stmt)
    finally:
      cursor.close()

  @scoped_connection
  def _get(self, connection, name, interval, config, timestamp, **kws):
    '''
    Get the interval.
    '''
    i_bucket = config['i_calc'].to_bucket(timestamp)
    fetch = kws.get('fetch')
    process_row = kws.get('process_row') or self._process_row

    rval = OrderedDict()
    if fetch:
      data = fetch( connection, self._table, name, interval, [i_bucket] )
    else:
      data = self._type_get(name, interval, i_bucket)

    if config['coarse']:
      if data:
        rval[ config['i_calc'].from_bucket(i_bucket) ] = process_row(data.values()[0][None])
      else:
        rval[ config['i_calc'].from_bucket(i_bucket) ] = self._type_no_value()
    else:
      for r_bucket,row_data in data.values()[0].items():
        rval[ config['r_calc'].from_bucket(r_bucket) ] = process_row(row_data)

    return rval

  @scoped_connection
  def _series(self, connection, name, interval, config, buckets, **kws):
    '''
    Fetch a series of buckets.
    '''
    fetch = kws.get('fetch')
    process_row = kws.get('process_row') or self._process_row

    rval = OrderedDict()

    if fetch:
      data = fetch( connection, self._table, name, interval, buckets )
    else:
      data = self._type_get(name, interval, buckets[0], buckets[-1])

    if config['coarse']:
      for i_bucket in buckets:
        i_key = config['i_calc'].from_bucket(i_bucket)
        i_data = data.get( i_bucket )
        if i_data:
          rval[ i_key ] = process_row( i_data[None] )
        else:
          rval[ i_key ] = self._type_no_value()
    else:
      if data:
        for i_bucket, i_data in data.items():
          i_key = config['i_calc'].from_bucket(i_bucket)
          rval[i_key] = OrderedDict()
          for r_bucket, r_data in i_data.items():
            r_key = config['r_calc'].from_bucket(r_bucket)
            if r_data:
              rval[i_key][r_key] = process_row(r_data)
            else:
              rval[i_key][r_key] = self._type_no_value()

    return rval

  @scoped_connection
  def delete(self, connection, name):
    cursor = connection.cursor()
    try:
      cursor.execute("DELETE FROM %s WHERE name='%s';"%(self._table,name))
    finally:
      cursor.close()

  @scoped_connection
  def delete_all(self, connection):
    cursor = connection.cursor()
    try:
      cursor.execute("TRUNCATE %s"%(self._table))
    finally:
      cursor.close()

  @scoped_connection
  def list(self, connection):
    cursor = connection.cursor()
    rval = set()

    try:
      cursor.execute('SELECT name FROM %s'%(self._table))
      for row in cursor:
        rval.add(row[0])
    finally:
      cursor.close()
    return list(rval)

  @scoped_connection
  def properties(self, connection, name):
    cursor = connection.cursor()
    rval = {}

    try:
      for interval,config in self._intervals.items():
        rval.setdefault(interval, {})

        cursor.execute('''SELECT i_time
          FROM %s
          WHERE name = '%s' AND interval = '%s'
          ORDER BY interval ASC, i_time ASC
          LIMIT 1'''%(self._table, name, interval))

        rval[interval]['first'] = config['i_calc'].from_bucket(
          cursor.fetchone()[0] )

        cursor.execute('''SELECT i_time
          FROM %s
          WHERE name = '%s' AND interval = '%s'
          ORDER BY interval DESC, i_time DESC
          LIMIT 1'''%(self._table, name, interval))
        rval[interval]['last'] = config['i_calc'].from_bucket(
          cursor.fetchone()[0] )
    finally:
      cursor.close()

    return rval

class CassandraSeries(CassandraBackend, Series):

  def __init__(self, *a, **kwargs):
    self._table = 'series'
    super(CassandraSeries,self).__init__(*a, **kwargs)

    cursor = self._client.cursor()
    # TODO: support other value types
    # TODO: use varint for [ir]_time?
    try:
      res = cursor.execute('''CREATE TABLE IF NOT EXISTS %s (
        name text,
        interval text,
        i_time bigint,
        r_time bigint,
        value list<%s>,
        PRIMARY KEY(name, interval, i_time, r_time)
      )'''%(self._table, self._value_type))
    except cql.ProgrammingError as pe:
      if 'existing' not in str(pe):
        raise
    finally:
      cursor.close()

  def _insert_stmt(self, name, value, timestamp, interval, config):
    '''Helper to generate the insert statement.'''
    # Calculate the TTL and abort if inserting into the past
    expire, ttl = config['expire'], config['ttl'](timestamp)
    if expire and not ttl:
      return None

    i_time = config['i_calc'].to_bucket(timestamp)
    if not config['coarse']:
      r_time = config['r_calc'].to_bucket(timestamp)
    else:
      r_time = -1

    # TODO: figure out escaping rules of CQL
    table_spec = self._table
    if ttl:
      table_spec += " USING TTL %s "%(ttl)
    stmt = '''UPDATE %s SET value = value + [%s]
      WHERE name = '%s'
      AND interval = '%s'
      AND i_time = %s
      AND r_time = %s'''%(table_spec, value, name, interval, i_time, r_time)
    return stmt

  @scoped_connection
  def _type_get(self, connection, name, interval, i_bucket, i_end=None):
    rval = OrderedDict()

    # TODO: more efficient creation of query string
    stmt = '''SELECT i_time, r_time, value
      FROM %s
      WHERE name = '%s' AND interval = '%s'
    '''%(self._table, name, interval)
    if i_end :
      stmt += ' AND i_time >= %s AND i_time <= %s'%(i_bucket, i_end)
    else:
      stmt += ' AND i_time = %s'%(i_bucket)
    stmt += ' ORDER BY interval, i_time, r_time'

    cursor = connection.cursor()
    try:
      cursor.execute(stmt)
      for row in cursor:
        i_time, r_time, value = row
        if r_time==-1:
          r_time = None
        rval.setdefault(i_time,OrderedDict())[r_time] = value
    finally:
      cursor.close()
    return rval

class CassandraHistogram(CassandraBackend, Histogram):

  def __init__(self, *a, **kwargs):
    self._table = 'histogram'
    super(CassandraHistogram,self).__init__(*a, **kwargs)

    # TODO: use varint for [ir]_time?
    # TODO: support other value types
    cursor = self._client.cursor()
    try:
      res = cursor.execute('''CREATE TABLE IF NOT EXISTS %s (
        name text,
        interval text,
        i_time bigint,
        r_time bigint,
        value %s,
        count counter,
        PRIMARY KEY(name, interval, i_time, r_time, value)
      )'''%(self._table, self._value_type))
    except cql.ProgrammingError as pe:
      if 'existing' not in str(pe):
        raise
    finally:
      cursor.close()

  def _insert_stmt(self, name, value, timestamp, interval, config):
    '''Helper to generate the insert statement.'''
    # Calculate the TTL and abort if inserting into the past
    expire, ttl = config['expire'], config['ttl'](timestamp)
    if expire and not ttl:
      return None

    i_time = config['i_calc'].to_bucket(timestamp)
    if not config['coarse']:
      r_time = config['r_calc'].to_bucket(timestamp)
    else:
      r_time = -1

    # TODO: figure out escaping rules of CQL
    table_spec = self._table
    if ttl:
      table_spec += " USING TTL %s "%(ttl)
    stmt = '''UPDATE %s SET count = count + 1
      WHERE name = '%s'
      AND interval = '%s'
      AND i_time = %s
      AND r_time = %s
      AND value = %s'''%(table_spec, name, interval, i_time, r_time, value)
    return stmt

  @scoped_connection
  def _type_get(self, connection, name, interval, i_bucket, i_end=None):
    rval = OrderedDict()

    # TODO: more efficient creation of query string
    stmt = '''SELECT i_time, r_time, value, count
      FROM %s
      WHERE name = '%s' AND interval = '%s'
    '''%(self._table, name, interval)
    if i_end :
      stmt += ' AND i_time >= %s AND i_time <= %s'%(i_bucket, i_end)
    else:
      stmt += ' AND i_time = %s'%(i_bucket)
    stmt += ' ORDER BY interval, i_time, r_time'

    cursor = connection.cursor()
    try:
      cursor.execute(stmt)
      for row in cursor:
        i_time, r_time, value, count = row
        if r_time==-1:
          r_time = None
        rval.setdefault(i_time,OrderedDict()).setdefault(r_time,{})[value] = count
    finally:
      cursor.close()
    return rval

class CassandraCount(CassandraBackend, Count):

  def __init__(self, *a, **kwargs):
    self._table = 'count'
    super(CassandraCount,self).__init__(*a, **kwargs)

    # TODO: use varint for [ir]_time?
    # TODO: support other value types
    cursor = self._client.cursor()
    try:
      res = cursor.execute('''CREATE TABLE IF NOT EXISTS %s (
        name text,
        interval text,
        i_time bigint,
        r_time bigint,
        count counter,
        PRIMARY KEY(name, interval, i_time, r_time)
      )'''%(self._table))
    except cql.ProgrammingError as pe:
      if 'existing' not in str(pe):
        raise
    finally:
      cursor.close()

  def _insert_stmt(self, name, value, timestamp, interval, config):
    '''Helper to generate the insert statement.'''
    # Calculate the TTL and abort if inserting into the past
    expire, ttl = config['expire'], config['ttl'](timestamp)
    if expire and not ttl:
      return None

    i_time = config['i_calc'].to_bucket(timestamp)
    if not config['coarse']:
      r_time = config['r_calc'].to_bucket(timestamp)
    else:
      r_time = -1

    # TODO: figure out escaping rules of CQL
    table_spec = self._table
    if ttl:
      table_spec += " USING TTL %s "%(ttl)
    stmt = '''UPDATE %s SET count = count + %s
      WHERE name = '%s'
      AND interval = '%s'
      AND i_time = %s
      AND r_time = %s'''%(table_spec, value, name, interval, i_time, r_time)
    return stmt

  @scoped_connection
  def _type_get(self, connection, name, interval, i_bucket, i_end=None):
    rval = OrderedDict()

    # TODO: more efficient creation of query string
    stmt = '''SELECT i_time, r_time, count
      FROM %s
      WHERE name = '%s' AND interval = '%s'
    '''%(self._table, name, interval)
    if i_end :
      stmt += ' AND i_time >= %s AND i_time <= %s'%(i_bucket, i_end)
    else:
      stmt += ' AND i_time = %s'%(i_bucket)
    stmt += ' ORDER BY interval, i_time, r_time'

    cursor = connection.cursor()
    try:
      cursor.execute(stmt)
      for row in cursor:
        i_time, r_time, count = row
        if r_time==-1:
          r_time = None
        rval.setdefault(i_time,OrderedDict())[r_time] = count
    finally:
      cursor.close()
    return rval

class CassandraGauge(CassandraBackend, Gauge):

  def __init__(self, *a, **kwargs):
    self._table = 'gauge'
    super(CassandraGauge,self).__init__(*a, **kwargs)

    # TODO: use varint for [ir]_time?
    # TODO: support other value types
    cursor = self._client.cursor()
    try:
      res = cursor.execute('''CREATE TABLE IF NOT EXISTS %s (
        name text,
        interval text,
        i_time bigint,
        r_time bigint,
        value %s,
        PRIMARY KEY(name, interval, i_time, r_time)
      )'''%(self._table, self._value_type))
    except cql.ProgrammingError as pe:
      if 'existing' not in str(pe):
        raise
    finally:
      cursor.close()

  def _insert_stmt(self, name, value, timestamp, interval, config):
    '''Helper to generate the insert statement.'''
    # Calculate the TTL and abort if inserting into the past
    expire, ttl = config['expire'], config['ttl'](timestamp)
    if expire and not ttl:
      return None

    i_time = config['i_calc'].to_bucket(timestamp)
    if not config['coarse']:
      r_time = config['r_calc'].to_bucket(timestamp)
    else:
      r_time = -1

    # TODO: figure out escaping rules of CQL
    table_spec = self._table
    if ttl:
      table_spec += " USING TTL %s "%(ttl)
    stmt = '''UPDATE %s SET value = %s
      WHERE name = '%s'
      AND interval = '%s'
      AND i_time = %s
      AND r_time = %s'''%(table_spec, value, name, interval, i_time, r_time)
    return stmt

  @scoped_connection
  def _type_get(self, connection, name, interval, i_bucket, i_end=None):
    rval = OrderedDict()

    # TODO: more efficient creation of query string
    stmt = '''SELECT i_time, r_time, value
      FROM %s
      WHERE name = '%s' AND interval = '%s'
    '''%(self._table, name, interval)
    if i_end :
      stmt += ' AND i_time >= %s AND i_time <= %s'%(i_bucket, i_end)
    else:
      stmt += ' AND i_time = %s'%(i_bucket)
    stmt += ' ORDER BY interval, i_time, r_time'

    cursor = connection.cursor()
    try:
      cursor.execute(stmt)
      for row in cursor:
        i_time, r_time, value = row
        if r_time==-1:
          r_time = None
        rval.setdefault(i_time,OrderedDict())[r_time] = value
    finally:
      cursor.close()
    return rval

class CassandraSet(CassandraBackend, Set):

  def __init__(self, *a, **kwargs):
    self._table = 'sets'
    super(CassandraSet,self).__init__(*a, **kwargs)

    # TODO: use varint for [ir]_time?
    # TODO: support other value types
    cursor = self._client.cursor()
    try:
      res = cursor.execute('''CREATE TABLE IF NOT EXISTS %s (
        name text,
        interval text,
        i_time bigint,
        r_time bigint,
        value %s,
        PRIMARY KEY(name, interval, i_time, r_time, value)
      )'''%(self._table, self._value_type))
    except cql.ProgrammingError as pe:
      if 'existing' not in str(pe):
        raise
    finally:
      cursor.close()

  def _insert_stmt(self, name, value, timestamp, interval, config):
    '''Helper to generate the insert statement.'''
    # Calculate the TTL and abort if inserting into the past
    expire, ttl = config['expire'], config['ttl'](timestamp)
    if expire and not ttl:
      return None

    i_time = config['i_calc'].to_bucket(timestamp)
    if not config['coarse']:
      r_time = config['r_calc'].to_bucket(timestamp)
    else:
      r_time = -1

    # TODO: figure out escaping rules of CQL
    stmt = '''INSERT INTO %s (name, interval, i_time, r_time, value)
      VALUES ('%s', '%s', %s, %s, %s)'''%(self._table, name, interval, i_time, r_time, value)
    expire = config['expire']
    if ttl:
      stmt += " USING TTL %s"%(ttl)
    return stmt

  @scoped_connection
  def _type_get(self, connection, name, interval, i_bucket, i_end=None):
    rval = OrderedDict()

    # TODO: more efficient creation of query string
    stmt = '''SELECT i_time, r_time, value
      FROM %s
      WHERE name = '%s' AND interval = '%s'
    '''%(self._table, name, interval)
    if i_end :
      stmt += ' AND i_time >= %s AND i_time <= %s'%(i_bucket, i_end)
    else:
      stmt += ' AND i_time = %s'%(i_bucket)
    stmt += ' ORDER BY interval, i_time, r_time'

    cursor = connection.cursor()
    try:
      cursor.execute(stmt)
      for row in cursor:
        i_time, r_time, value = row
        if r_time==-1:
          r_time = None
        rval.setdefault(i_time,OrderedDict()).setdefault(r_time,set()).add( value )
    finally:
      cursor.close()
    return rval

########NEW FILE########
__FILENAME__ = exceptions
'''
Copyright (c) 2012-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/kairos/blob/master/LICENSE.txt
'''

class KairosException(Exception):
  '''Base class for all kairos exceptions'''

class UnknownInterval(KairosException):
  '''The requested interval is not configured.'''

########NEW FILE########
__FILENAME__ = mongo_backend
'''
Copyright (c) 2012-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/kairos/blob/master/LICENSE.txt
'''
from .exceptions import *
from .timeseries import *

import operator
import sys
import time
import re
import pymongo
from pymongo import ASCENDING, DESCENDING
from datetime import datetime
from urlparse import *

class MongoBackend(Timeseries):
  '''
  Mongo implementation of timeseries support.
  '''

  def __new__(cls, *args, **kwargs):
    if cls==MongoBackend:
      ttype = kwargs.pop('type', None)
      if ttype=='series':
        return MongoSeries.__new__(MongoSeries, *args, **kwargs)
      elif ttype=='histogram':
        return MongoHistogram.__new__(MongoHistogram, *args, **kwargs)
      elif ttype=='count':
        return MongoCount.__new__(MongoCount, *args, **kwargs)
      elif ttype=='gauge':
        return MongoGauge.__new__(MongoGauge, *args, **kwargs)
      raise NotImplementedError("No implementation for %s types"%(ttype))
    return Timeseries.__new__(cls, *args, **kwargs)

  def __init__(self, client, **kwargs):
    '''
    Initialize the mongo backend after timeseries has processed the configuration.
    '''
    if isinstance(client, pymongo.MongoClient):
      client = client['kairos']
    elif not isinstance(client, pymongo.database.Database):
      raise TypeError('Mongo handle must be MongoClient or database instance')

    self._escape_character = kwargs.get('escape_character', u"\U0000FFFF")
    super(MongoBackend,self).__init__(client, **kwargs)

    # Define the indices for lookups and TTLs
    for interval,config in self._intervals.items():
      # TODO: the interval+(resolution+)name combination should be unique,
      # but should the index be defined as such? Consider performance vs.
      # correctness tradeoff. Also will need to determine if we need to
      # maintain this multikey index or if there's a better way to implement
      # all the features. Lastly, determine if it's better to add 'value'
      # to the index and spec the fields in get() and series() so that we
      # get covered indices. There are reasons why that might be a
      # configuration option (performance vs. memory tradeoff)
      if config['coarse']:
        self._client[interval].ensure_index(
          [('interval',ASCENDING),('name',ASCENDING)], background=True )
      else:
        self._client[interval].ensure_index(
          [('interval',ASCENDING),('resolution',ASCENDING),('name',ASCENDING)],
          background=True )
      if config['expire']:
        self._client[interval].ensure_index(
          [('expire_from',ASCENDING)], expireAfterSeconds=config['expire'], background=True )

  @classmethod
  def url_parse(self, url, **kwargs):
    location = urlparse(url)
    if location.scheme == 'mongodb':
      client = pymongo.MongoClient( url, **kwargs )

      # Stupid urlparse has a "does this scheme use queries" registrar,
      # so copy that work here. Then pull out the optional database name.
      path = location.path
      if '?' in path:
        path = path.split('?',1)[0]
      path = re.search('[/]*([\w]*)', path).groups()[0] or kwargs.get('database','kairos')

      return client[ path ]

  # A very ugly way to capture histogram updates
  @property
  def _single_value(self):
    return True

  def _unescape(self, value):
    '''
    Recursively unescape values. Though slower, this doesn't require the user to
    know anything about the escaping when writing their own custom fetch functions.
    '''
    if isinstance(value, (str,unicode)):
      return value.replace(self._escape_character, '.')
    elif isinstance(value, dict):
      return { self._unescape(k) : self._unescape(v) for k,v in value.items() }
    elif isinstance(value, list):
      return [ self._unescape(v) for v in value ]
    return value

  def list(self):
    rval = set()
    for interval,config in self._intervals.items():
      rval.update( self._client.command({'distinct':interval, 'key':'name'})['values'] )
    return list(rval)

  def properties(self, name):
    rval = {}
    for interval,config in self._intervals.items():
      rval.setdefault(interval, {})
      query = {'name':name}
      res = self._client[interval].find_one(query, sort=[('interval',ASCENDING)])
      rval[interval]['first'] = config['i_calc'].from_bucket(res['interval'])
      res = self._client[interval].find_one(query, sort=[('interval',DESCENDING)])
      rval[interval]['last'] = config['i_calc'].from_bucket(res['interval'])

    return rval

  def _batch_key(self, query):
    '''
    Get a unique id from a query.
    '''
    return ''.join( ['%s%s'%(k,v) for k,v in sorted(query.items())] )

  def _batch_insert(self, inserts, intervals, **kwargs):
    '''
    Batch insert implementation.
    '''
    updates = {}
    # TODO support flush interval
    for interval,config in self._intervals.items():
      for timestamp,names in inserts.iteritems():
        timestamps = self._normalize_timestamps(timestamp, intervals, config)
        for name,values in names.iteritems():
          for value in values:
            for tstamp in timestamps:
              query,insert = self._insert_data(
                name, value, tstamp, interval, config, dry_run=True)

              batch_key = self._batch_key(query)
              updates.setdefault(batch_key, {'query':query, 'interval':interval})
              new_insert = self._batch(insert, updates[batch_key].get('insert'))
              updates[batch_key]['insert'] = new_insert

    # now that we've collected a bunch of updates, flush them out
    for spec in updates.values():
      self._client[ spec['interval'] ].update( 
        spec['query'], spec['insert'], upsert=True, check_keys=False )

  def _insert(self, name, value, timestamp, intervals, **kwargs):
    '''
    Insert the new value.
    '''
    # TODO: confirm that this is in fact using the indices correctly.
    for interval,config in self._intervals.items():
      timestamps = self._normalize_timestamps(timestamp, intervals, config)
      for tstamp in timestamps:
        self._insert_data(name, value, tstamp, interval, config, **kwargs)

  def _insert_data(self, name, value, timestamp, interval, config, **kwargs):
    '''Helper to insert data into mongo.'''
    # Mongo does not allow mixing atomic modifiers and non-$set sets in the
    # same update, so the choice is to either run the first upsert on
    # {'_id':id} to ensure the record is in place followed by an atomic update
    # based on the series type, or use $set for all of the keys to be used in
    # creating the record, which then disallows setting our own _id because
    # that "can't be updated". So the tradeoffs are:
    #   * 2 updates for every insert, maybe a local cache of known _ids and the
    #     associated memory overhead
    #   * Query by the 2 or 3 key tuple for this interval and the associated
    #     overhead of that index match vs. the presumably-faster match on _id
    #   * Yet another index for the would-be _id of i_key or r_key, where each
    #     index has a notable impact on write performance.
    # For now, choosing to go with matching on the tuple until performance
    # testing can be done. Even then, there may be a variety of factors which
    # make the results situation-dependent.
    insert = {'name':name, 'interval':config['i_calc'].to_bucket(timestamp)}
    if not config['coarse']:
      insert['resolution'] = config['r_calc'].to_bucket(timestamp)
    # copy the query before expire_from as that is not indexed
    query = insert.copy()

    if config['expire']:
      insert['expire_from'] = datetime.utcfromtimestamp( timestamp )

    # switch to atomic updates
    insert = {'$set':insert.copy()}

    # need to hide the period of any values. best option seems to be to pick
    # a character that "no one" uses.
    if isinstance(value, (str,unicode)):
      value = value.replace('.', self._escape_character)
    elif isinstance(value, float):
      value = str(value).replace('.', self._escape_character)

    self._insert_type( insert, value )

    # TODO: use write preference settings if we have them
    if not kwargs.get('dry_run',False):
      self._client[interval].update( query, insert, upsert=True, check_keys=False )
    return query, insert

  def _get(self, name, interval, config, timestamp, **kws):
    '''
    Get the interval.
    '''
    i_bucket = config['i_calc'].to_bucket(timestamp)
    fetch = kws.get('fetch')
    process_row = kws.get('process_row') or self._process_row

    rval = OrderedDict()
    query = {'name':name, 'interval':i_bucket}
    if config['coarse']:
      if fetch:
        record = fetch( self._client[interval], spec=query, method='find_one' )
      else:
        record = self._client[interval].find_one( query )

      if record:
        data = process_row( self._unescape(record['value']) )
        rval[ config['i_calc'].from_bucket(i_bucket) ] = data
      else:
        rval[ config['i_calc'].from_bucket(i_bucket) ] = self._type_no_value()
    else:
      sort = [('interval', ASCENDING), ('resolution', ASCENDING) ]
      if fetch:
        cursor = fetch( self._client[interval], spec=query, sort=sort, method='find' )
      else:
        cursor = self._client[interval].find( spec=query, sort=sort )

      idx = 0
      for record in cursor:
        rval[ config['r_calc'].from_bucket(record['resolution']) ] = \
          process_row(record['value'])

    return rval

  def _series(self, name, interval, config, buckets, **kws):
    '''
    Fetch a series of buckets.
    '''
    # make a copy of the buckets because we're going to mutate it
    buckets = list(buckets)
    rval = OrderedDict()
    step = config['step']
    resolution = config.get('resolution',step)
    fetch = kws.get('fetch')
    process_row = kws.get('process_row', self._process_row)

    query = { 'name':name, 'interval':{'$gte':buckets[0], '$lte':buckets[-1]} }
    sort = [('interval', ASCENDING)]
    if not config['coarse']:
      sort.append( ('resolution', ASCENDING) )

    if fetch:
      cursor = fetch( self._client[interval], spec=query, sort=sort, method='find' )
    else:
      cursor = self._client[interval].find( spec=query, sort=sort )
    for record in cursor:
      while buckets and buckets[0] < record['interval']:
        rval[ config['i_calc'].from_bucket(buckets.pop(0)) ] = self._type_no_value()
      if buckets and buckets[0]==record['interval']:
        buckets.pop(0)

      i_key = config['i_calc'].from_bucket(record['interval'])
      data = process_row( record['value'] )
      if config['coarse']:
        rval[ i_key ] = data
      else:
        rval.setdefault( i_key, OrderedDict() )
        rval[ i_key ][ config['r_calc'].from_bucket(record['resolution']) ] = data

    # are there buckets at the end for which we received no data?
    while buckets:
      rval[ config['i_calc'].from_bucket(buckets.pop(0)) ] = self._type_no_value()

    return rval

  def delete(self, name):
    '''
    Delete time series by name across all intervals. Returns the number of
    records deleted.
    '''
    # TODO: confirm that this does not use the combo index and determine
    # performance implications.
    num_deleted = 0
    for interval,config in self._intervals.items():
      # TODO: use write preference settings if we have them
      num_deleted += self._client[interval].remove( {'name':name} )['n']
    return num_deleted

class MongoSeries(MongoBackend, Series):

  def _batch(self, insert, existing):
    if not existing:
      insert['$push'] = {'value':{'$each':[ insert['$push']['value'] ]}}
      return insert
      
    existing['$push']['value']['$each'].append( insert.pop('$push')['value'] )
    return existing

  def _insert_type(self, spec, value):
    spec['$push'] = {'value':value}

class MongoHistogram(MongoBackend, Histogram):
  
  def _batch(self, insert, existing):
    if not existing:
      return insert

    for value,incr in insert['$inc'].iteritems():
      existing['$inc'][value] = existing['$inc'].get(value,0)+incr
    return existing

  def _insert_type(self, spec, value):
    spec['$inc'] = {'value.%s'%(value): 1}

class MongoCount(MongoBackend, Count):
  
  def _batch(self, insert, existing):
    if not existing:
      return insert

    existing['$inc']['value'] += insert['$inc']['value']
    return existing

  def _insert_type(self, spec, value):
    spec['$inc'] = {'value':value}

class MongoGauge(MongoBackend, Gauge):

  def _batch(self, insert, existing):
    if not existing:
      return insert

    existing['$set']['value'] = insert['$set']['value']
    return existing

  def _insert_type(self, spec, value):
    spec['$set']['value'] = value

########NEW FILE########
__FILENAME__ = redis_backend
'''
Copyright (c) 2012-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/kairos/blob/master/LICENSE.txt
'''
from .exceptions import *
from .timeseries import *

import operator
import sys
import time
import re
from urlparse import *
from redis import Redis

class RedisBackend(Timeseries):
  '''
  Redis implementation of timeseries support.
  '''

  def __new__(cls, *args, **kwargs):
    if cls==RedisBackend:
      ttype = kwargs.pop('type', None)
      if ttype=='series':
        return RedisSeries.__new__(RedisSeries, *args, **kwargs)
      elif ttype=='histogram':
        return RedisHistogram.__new__(RedisHistogram, *args, **kwargs)
      elif ttype=='count':
        return RedisCount.__new__(RedisCount, *args, **kwargs)
      elif ttype=='gauge':
        return RedisGauge.__new__(RedisGauge, *args, **kwargs)
      elif ttype=='set':
        return RedisSet.__new__(RedisSet, *args, **kwargs)
      raise NotImplementedError("No implementation for %s types"%(ttype))
    return Timeseries.__new__(cls, *args, **kwargs)

  def __init__(self, client, **kwargs):
    # prefix is redis-only feature (TODO: yes or no?)
    self._prefix = kwargs.get('prefix', '')
    if len(self._prefix) and not self._prefix.endswith(':'):
      self._prefix += ':'

    super(RedisBackend,self).__init__( client, **kwargs )

  @classmethod
  def url_parse(self, url, **kwargs):
    location = urlparse(url)
    if location.scheme == 'redis':
      return Redis.from_url( url, **kwargs )

  def _calc_keys(self, config, name, timestamp):
    '''
    Calculate keys given a stat name and timestamp.
    '''
    i_bucket = config['i_calc'].to_bucket( timestamp )
    r_bucket = config['r_calc'].to_bucket( timestamp )

    i_key = '%s%s:%s:%s'%(self._prefix, name, config['interval'], i_bucket)
    r_key = '%s:%s'%(i_key, r_bucket)

    return i_bucket, r_bucket, i_key, r_key

  def list(self):
    keys = self._client.keys()
    rval = set()
    for key in keys:
      key = key[len(self._prefix):]
      rval.add( key.split(':')[0] )
    return list(rval)

  def properties(self, name):
    prefix = '%s%s:'%(self._prefix,name)
    keys = self._client.keys('%s*'%(prefix))
    rval = {}

    for key in keys:
      key = key[len(prefix):].split(':')
      rval.setdefault( key[0], {} )
      if 'first' in rval[key[0]]:
        rval[key[0]]['first'] = min(rval[key[0]]['first'], int(key[1]))
      else:
        rval[key[0]]['first'] = int(key[1])
      if 'last' in rval[key[0]]:
        rval[key[0]]['last'] = max(rval[key[0]]['last'], int(key[1]))
      else:
        rval[key[0]]['last'] = int(key[1])

    for interval, properties in rval.items():
      # It's possible that there is data stored for which an interval
      # is not defined.
      if interval in self._intervals:
        config = self._intervals[interval]
        properties['first'] = config['i_calc'].from_bucket( properties['first'] )
        properties['last'] = config['i_calc'].from_bucket( properties['last'] )
      else:
        rval.pop(interval)

    return rval

  def _batch_insert(self, inserts, intervals, **kwargs):
    '''
    Specialized batch insert
    '''
    if 'pipeline' in kwargs:
      pipe = kwargs.get('pipeline')
      own_pipe = False
    else:
      pipe = self._client.pipeline(transaction=False)
      kwargs['pipeline'] = pipe
      own_pipe = True

    for timestamp,names in inserts.iteritems():
      for name,values in names.iteritems():
        for value in values:
          # TODO: support config param to flush the pipe every X inserts
          self._insert( name, value, timestamp, intervals, **kwargs )

    if own_pipe:
      kwargs['pipeline'].execute()

  def _insert(self, name, value, timestamp, intervals, **kwargs):
    '''
    Insert the value.
    '''
    if 'pipeline' in kwargs:
      pipe = kwargs.get('pipeline')
    else:
      pipe = self._client.pipeline(transaction=False)

    for interval,config in self._intervals.iteritems():
      timestamps = self._normalize_timestamps(timestamp, intervals, config)
      for tstamp in timestamps:
        self._insert_data(name, value, tstamp, interval, config, pipe)

    if 'pipeline' not in kwargs:
      pipe.execute()

  def _insert_data(self, name, value, timestamp, interval, config, pipe):
    '''Helper to insert data into redis'''
    # Calculate the TTL and abort if inserting into the past
    expire, ttl = config['expire'], config['ttl'](timestamp)
    if expire and not ttl:
      return

    i_bucket, r_bucket, i_key, r_key = self._calc_keys(config, name, timestamp)

    if config['coarse']:
      self._type_insert(pipe, i_key, value)
    else:
      # Add the resolution bucket to the interval. This allows us to easily
      # discover the resolution intervals within the larger interval, and
      # if there is a cap on the number of steps, it will go out of scope
      # along with the rest of the data
      pipe.sadd(i_key, r_bucket)
      self._type_insert(pipe, r_key, value)

    if expire:
      pipe.expire(i_key, ttl)
      if not config['coarse']:
        pipe.expire(r_key, ttl)

  def delete(self, name):
    '''
    Delete all the data in a named timeseries.
    '''
    keys = self._client.keys('%s%s:*'%(self._prefix,name))

    pipe = self._client.pipeline(transaction=False)
    for key in keys:
      pipe.delete( key )
    pipe.execute()

    # Could be not technically the exact number of keys deleted, but is a close
    # enough approximation
    return len(keys)

  def _get(self, name, interval, config, timestamp, **kws):
    '''
    Fetch a single interval from redis.
    '''
    i_bucket, r_bucket, i_key, r_key = self._calc_keys(config, name, timestamp)
    fetch = kws.get('fetch') or self._type_get
    process_row = kws.get('process_row') or self._process_row

    rval = OrderedDict()
    if config['coarse']:
      data = process_row( fetch(self._client, i_key) )
      rval[ config['i_calc'].from_bucket(i_bucket) ] = data
    else:
      # First fetch all of the resolution buckets for this set.
      resolution_buckets = sorted(map(int,self._client.smembers(i_key)))

      # Create a pipe and go fetch all the data for each.
      # TODO: turn off transactions here?
      pipe = self._client.pipeline(transaction=False)
      for bucket in resolution_buckets:
        r_key = '%s:%s'%(i_key, bucket)   # TODO: make this the "resolution_bucket" closure?
        fetch(pipe, r_key)
      res = pipe.execute()

      for idx,data in enumerate(res):
        data = process_row(data)
        rval[ config['r_calc'].from_bucket(resolution_buckets[idx]) ] = data

    return rval

  def _series(self, name, interval, config, buckets, **kws):
    '''
    Fetch a series of buckets.
    '''
    pipe = self._client.pipeline(transaction=False)
    step = config['step']
    resolution = config.get('resolution',step)
    fetch = kws.get('fetch') or self._type_get
    process_row = kws.get('process_row') or self._process_row

    rval = OrderedDict()
    for interval_bucket in buckets:
      i_key = '%s%s:%s:%s'%(self._prefix, name, interval, interval_bucket)

      if config['coarse']:
        fetch(pipe, i_key)
      else:
        pipe.smembers(i_key)
    res = pipe.execute()

    # TODO: a memory efficient way to use a single pipeline for this.
    for idx,data in enumerate(res):
      # TODO: use closures on the config for generating this interval key
      interval_bucket = buckets[idx] #start_bucket + idx
      interval_key = '%s%s:%s:%s'%(self._prefix, name, interval, interval_bucket)

      if config['coarse']:
        data = process_row( data )
        rval[ config['i_calc'].from_bucket(interval_bucket) ] = data
      else:
        rval[ config['i_calc'].from_bucket(interval_bucket) ] = OrderedDict()
        pipe = self._client.pipeline(transaction=False)
        resolution_buckets = sorted(map(int,data))
        for bucket in resolution_buckets:
          # TODO: use closures on the config for generating this resolution key
          resolution_key = '%s:%s'%(interval_key, bucket)
          fetch(pipe, resolution_key)

        resolution_res = pipe.execute()
        for x,data in enumerate(resolution_res):
          i_t = config['i_calc'].from_bucket(interval_bucket)
          r_t = config['r_calc'].from_bucket(resolution_buckets[x])
          rval[ i_t ][ r_t ] = process_row(data)

    return rval

class RedisSeries(RedisBackend, Series):

  def _type_insert(self, handle, key, value):
    '''
    Insert the value into the series.
    '''
    handle.rpush(key, value)

  def _type_get(self, handle, key):
    '''
    Get for a series.
    '''
    return handle.lrange(key, 0, -1)

class RedisHistogram(RedisBackend, Histogram):

  def _type_insert(self, handle, key, value):
    '''
    Insert the value into the series.
    '''
    handle.hincrby(key, value, 1)

  def _type_get(self, handle, key):
    return handle.hgetall(key)

class RedisCount(RedisBackend, Count):

  def _type_insert(self, handle, key, value):
    '''
    Insert the value into the series.
    '''
    if value!=0:
      if isinstance(value,float):
        handle.incrbyfloat(key, value)
      else:
        handle.incr(key,value)

  def _type_get(self, handle, key):
    return handle.get(key)

class RedisGauge(RedisBackend, Gauge):

  def _type_insert(self, handle, key, value):
    '''
    Insert the value into the series.
    '''
    handle.set(key, value)

  def _type_get(self, handle, key):
    return handle.get(key)

class RedisSet(RedisBackend, Set):

  def _type_insert(self, handle, key, value):
    '''
    Insert the value into the series.
    '''
    handle.sadd(key, value)

  def _type_get(self, handle, key):
    return handle.smembers(key)

########NEW FILE########
__FILENAME__ = sql_backend
'''
Copyright (c) 2012-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/kairos/blob/master/LICENSE.txt
'''
from .exceptions import *
from .timeseries import *

from sqlalchemy.types import TypeEngine
from sqlalchemy import Table, Column, BigInteger, Integer, String, Unicode, Text, LargeBinary, Float, Boolean, Time, Date, DateTime, Numeric, MetaData, UniqueConstraint, create_engine
from sqlalchemy.sql import select, update, insert, distinct, asc, desc, and_, or_, not_

import time
from datetime import date, datetime
from datetime import time as time_type
from decimal import Decimal
from urlparse import *

# Test python3 compatibility
try:
  x = long(1)
except NameError:
  long = int
try:
  x = unicode('foo')
except NameError:
  unicode = str

TYPE_MAP = {
  str         : String,
  'str'       : String,
  'string'    : String,

  unicode     : Unicode,  # works for py3 too
  'unicode'   : Unicode,

  float       : Float,
  'float'     : Float,

  int         : Integer,
  'int'       : Integer,
  'integer'   : Integer,

  long        : BigInteger, # works for py3 too
  'long'      : BigInteger,
  'int64'     : BigInteger,

  bool        : Boolean,
  'bool'      : Boolean,
  'boolean'   : Boolean,

  date        : Date,
  'date'      : Date,
  datetime    : DateTime,
  'datetime'  : DateTime,
  time_type   : Time,
  'time'      : Time,

  Decimal     : Numeric,
  'decimal'   : Numeric,

  'text'      : Text,
  'clob'      : Text,
  'blob'      : LargeBinary,
}

class SqlBackend(Timeseries):

  def __new__(cls, *args, **kwargs):
    if cls==SqlBackend:
      ttype = kwargs.pop('type', None)
      if ttype=='series':
        return SqlSeries.__new__(SqlSeries, *args, **kwargs)
      elif ttype=='histogram':
        return SqlHistogram.__new__(SqlHistogram, *args, **kwargs)
      elif ttype=='count':
        return SqlCount.__new__(SqlCount, *args, **kwargs)
      elif ttype=='gauge':
        return SqlGauge.__new__(SqlGauge, *args, **kwargs)
      raise NotImplementedError("No implementation for %s types"%(ttype))
    return Timeseries.__new__(cls, *args, **kwargs)

  @classmethod
  def url_parse(self, url, **kwargs):
    location = urlparse(url)
    if 'sql' in location.scheme:
      return create_engine( url, **kwargs )

  def __init__(self, client, **kwargs):
    '''
    Initialize the sql backend after timeseries has processed the configuration.
    '''
    self._metadata = MetaData()
    self._str_length = kwargs.get('string_length',255)
    self._txt_length = kwargs.get('text_length', 32*1024)

    vtype = kwargs.get('value_type', float)
    if vtype in TYPE_MAP:
      self._value_type = TYPE_MAP[vtype]
      if self._value_type == String:
        self._value_type = String(self._str_length)
      elif self._value_type == Text:
        self._value_type = Text(self._txt_length)
      elif self._value_type == LargeBinary:
        self._value_type = LargeBinary(self._txt_length)

    elif issubclass(vtype, TypeEngine):
      if vtype == String:
        self._value_type = String(self._str_length)
      elif vtype == Text:
        self._value_type = Text(self._txt_length)
      elif vtype == LargeBinary:
        self._value_type = LargeBinary(self._txt_length)

    elif isinstance(vtype, TypeEngine):
      self._value_type = vtype

    else:
      raise ValueError("Unsupported type '%s'"%(vtype))

    self._table_name = kwargs.get('table_name', self._table_name)

    super(SqlBackend,self).__init__(client, **kwargs)

  def list(self):
    connection = self._client.connect()
    rval = set()
    stmt = select([distinct(self._table.c.name)])

    for row in connection.execute(stmt):
      rval.add(row['name'])
    return list(rval)

  def properties(self, name):
    connection = self._client.connect()
    rval = {}

    for interval,config in self._intervals.items():
      rval.setdefault(interval, {})

      stmt = select([self._table.c.i_time]).where(
        and_(
          self._table.c.name==name,
          self._table.c.interval==interval
        )
      ).order_by( asc(self._table.c.i_time) ).limit(1)
      rval[interval]['first'] = config['i_calc'].from_bucket(
        connection.execute(stmt).first()['i_time'] )

      stmt = select([self._table.c.i_time]).where(
        and_(
          self._table.c.name==name,
          self._table.c.interval==interval
        )
      ).order_by( desc(self._table.c.i_time) ).limit(1)
      rval[interval]['last'] = config['i_calc'].from_bucket(
        connection.execute(stmt).first()['i_time'] )

    return rval

  def expire(self, name):
    '''
    Expire all the data.
    '''
    for interval,config in self._intervals.items():
      if config['expire']:
        # Because we're storing the bucket time, expiry has the same
        # "skew" as whatever the buckets are.
        expire_from = config['i_calc'].to_bucket(time.time() - config['expire'])
        conn = self._client.connect()

        conn.execute( self._table.delete().where(
          and_(
            self._table.c.name==name,
            self._table.c.interval==interval,
            self._table.c.i_time<=expire_from
          )
        ))

  def _insert(self, name, value, timestamp, intervals, **kwargs):
    '''
    Insert the new value.
    '''
    for interval,config in self._intervals.items():
      timestamps = self._normalize_timestamps(timestamp, intervals, config)
      for tstamp in timestamps:
        self._insert_data(name, value, tstamp, interval, config, **kwargs)

  def _get(self, name, interval, config, timestamp, **kws):
    '''
    Get the interval.
    '''
    i_bucket = config['i_calc'].to_bucket(timestamp)
    fetch = kws.get('fetch')
    process_row = kws.get('process_row') or self._process_row

    rval = OrderedDict()
    if fetch:
      data = fetch( self._client.connect(), self._table, name, interval, i_bucket )
    else:
      data = self._type_get(name, interval, i_bucket)

    if config['coarse']:
      if data:
        rval[ config['i_calc'].from_bucket(i_bucket) ] = process_row(data.values()[0][None])
      else:
        rval[ config['i_calc'].from_bucket(i_bucket) ] = self._type_no_value()
    else:
      for r_bucket,row_data in data.values()[0].items():
        rval[ config['r_calc'].from_bucket(r_bucket) ] = process_row(row_data)

    return rval

  def _series(self, name, interval, config, buckets, **kws):
    '''
    Fetch a series of buckets.
    '''
    fetch = kws.get('fetch')
    process_row = kws.get('process_row') or self._process_row

    rval = OrderedDict()

    if fetch:
      data = fetch( self._client.connect(), self._table, name, interval, buckets[0], buckets[-1] )
    else:
      data = self._type_get(name, interval, buckets[0], buckets[-1])

    if config['coarse']:
      for i_bucket in buckets:
        i_key = config['i_calc'].from_bucket(i_bucket)
        i_data = data.get( i_bucket )
        if i_data:
          rval[ i_key ] = process_row( i_data[None] )
        else:
          rval[ i_key ] = self._type_no_value()
    else:
      if data:
        for i_bucket, i_data in data.items():
          i_key = config['i_calc'].from_bucket(i_bucket)
          rval[i_key] = OrderedDict()
          for r_bucket, r_data in i_data.items():
            r_key = config['r_calc'].from_bucket(r_bucket)
            if r_data:
              rval[i_key][r_key] = process_row(r_data)
            else:
              rval[i_key][r_key] = self._type_no_value()

    return rval

  def delete(self, name):
    '''
    Delete time series by name across all intervals. Returns the number of
    records deleted.
    '''
    conn = self._client.connect()
    conn.execute( self._table.delete().where(self._table.c.name==name) )

class SqlSeries(SqlBackend, Series):

  def __init__(self, *a, **kwargs):
    # TODO: define indices
    # TODO: optionally create separate tables for each interval, like mongo?
    self._table_name = 'series'
    super(SqlSeries,self).__init__(*a, **kwargs)
    self._table = Table(self._table_name, self._metadata,
      Column('name', String(self._str_length), nullable=False),      # stat name
      Column('interval', String(self._str_length), nullable=False),  # interval name
      Column('insert_time', Float, nullable=False),     # to preserve order
      Column('i_time', Integer, nullable=False),        # interval timestamp
      Column('r_time', Integer, nullable=True),         # resolution timestamp
      Column('value', self._value_type, nullable=False)            # datas
    )
    self._metadata.create_all(self._client)

  def _insert_data(self, name, value, timestamp, interval, config, **kwargs):
    '''Helper to insert data into sql.'''
    kwargs = {
      'name'        : name,
      'interval'    : interval,
      'insert_time' : time.time(),
      'i_time'      : config['i_calc'].to_bucket(timestamp),
      'value'       : value
    }
    if not config['coarse']:
      kwargs['r_time'] = config['r_calc'].to_bucket(timestamp)
    stmt = self._table.insert().values(**kwargs)
    conn = self._client.connect()
    result = conn.execute(stmt)

  def _type_get(self, name, interval, i_bucket, i_end=None):
    connection = self._client.connect()
    rval = OrderedDict()
    stmt = self._table.select()

    if i_end:
      stmt = stmt.where(
        and_(
          self._table.c.name==name,
          self._table.c.interval==interval,
          self._table.c.i_time>=i_bucket,
          self._table.c.i_time<=i_end,
        )
      )
    else:
      stmt = stmt.where(
        and_(
          self._table.c.name==name,
          self._table.c.interval==interval,
          self._table.c.i_time==i_bucket,
        )
      )
    stmt = stmt.order_by( self._table.c.r_time, self._table.c.insert_time )

    for row in connection.execute(stmt):
      rval.setdefault(row['i_time'],OrderedDict()).setdefault(row['r_time'],[]).append( row['value'] )
    return rval

class SqlHistogram(SqlBackend, Histogram):

  def __init__(self, *a, **kwargs):
    # TODO: define indices
    # TODO: optionally create separate tables for each interval, like mongo?
    self._table_name = 'histogram'
    super(SqlHistogram,self).__init__(*a, **kwargs)
    self._table = Table(self._table_name, self._metadata,
      Column('name', String(self._str_length), nullable=False),      # stat name
      Column('interval', String(self._str_length), nullable=False),  # interval name
      Column('i_time', Integer, nullable=False),        # interval timestamp
      Column('r_time', Integer, nullable=True),         # resolution timestamp
      Column('value', self._value_type, nullable=False),           # histogram keys
      Column('count', Integer, nullable=False),         # key counts

      # Use a constraint for transaction-less insert vs update
      UniqueConstraint('name', 'interval', 'i_time', 'r_time', 'value', name='unique_value')
    )
    self._metadata.create_all(self._client)

  def _insert_data(self, name, value, timestamp, interval, config, **kwargs):
    '''Helper to insert data into sql.'''
    conn = self._client.connect()
    if not self._update_data(name, value, timestamp, interval, config, conn):
      try:
        kwargs = {
          'name'        : name,
          'interval'    : interval,
          'i_time'      : config['i_calc'].to_bucket(timestamp),
          'value'       : value,
          'count'       : 1
        }
        if not config['coarse']:
          kwargs['r_time'] = config['r_calc'].to_bucket(timestamp)
        stmt = self._table.insert().values(**kwargs)
        result = conn.execute(stmt)
      except:
        # TODO: only catch IntegrityError
        if not self._update_data(name, value, timestamp, interval, config, conn):
          raise

  def _update_data(self, name, value, timestamp, interval, config, conn):
    '''Support function for insert. Should be called within a transaction'''
    i_time = config['i_calc'].to_bucket(timestamp)
    if not config['coarse']:
      r_time = config['r_calc'].to_bucket(timestamp)
    else:
      r_time = None
    stmt = self._table.update().where(
      and_(
        self._table.c.name==name,
        self._table.c.interval==interval,
        self._table.c.i_time==i_time,
        self._table.c.r_time==r_time,
        self._table.c.value==value)
    ).values({self._table.c.count: self._table.c.count + 1})
    rval = conn.execute( stmt )
    return rval.rowcount

  def _type_get(self, name, interval, i_bucket, i_end=None):
    connection = self._client.connect()
    rval = OrderedDict()
    stmt = self._table.select()

    if i_end:
      stmt = stmt.where(
        and_(
          self._table.c.name==name,
          self._table.c.interval==interval,
          self._table.c.i_time>=i_bucket,
          self._table.c.i_time<=i_end,
        )
      )
    else:
      stmt = stmt.where(
        and_(
          self._table.c.name==name,
          self._table.c.interval==interval,
          self._table.c.i_time==i_bucket,
        )
      )
    stmt = stmt.order_by( self._table.c.r_time )

    for row in connection.execute(stmt):
      rval.setdefault(row['i_time'],OrderedDict()).setdefault(row['r_time'],{})[row['value']] = row['count']
    return rval

class SqlCount(SqlBackend, Count):

  def __init__(self, *a, **kwargs):
    # TODO: define indices
    # TODO: optionally create separate tables for each interval, like mongo?
    self._table_name = 'count'
    super(SqlCount,self).__init__(*a, **kwargs)
    self._table = Table(self._table_name, self._metadata,
      Column('name', String(self._str_length), nullable=False),      # stat name
      Column('interval', String(self._str_length), nullable=False),  # interval name
      Column('i_time', Integer, nullable=False),        # interval timestamp
      Column('r_time', Integer, nullable=True),         # resolution timestamp
      Column('count', Integer, nullable=False),         # key counts

      # Use a constraint for transaction-less insert vs update
      UniqueConstraint('name', 'interval', 'i_time', 'r_time', name='unique_count')
    )
    self._metadata.create_all(self._client)

  def _insert_data(self, name, value, timestamp, interval, config, **kwargs):
    '''Helper to insert data into sql.'''
    conn = self._client.connect()
    if not self._update_data(name, value, timestamp, interval, config, conn):
      try:
        kwargs = {
          'name'        : name,
          'interval'    : interval,
          'i_time'      : config['i_calc'].to_bucket(timestamp),
          'count'       : value
        }
        if not config['coarse']:
          kwargs['r_time'] = config['r_calc'].to_bucket(timestamp)
        stmt = self._table.insert().values(**kwargs)
        result = conn.execute(stmt)
      except:
        # TODO: only catch IntegrityError
        if not self._update_data(name, value, timestamp, interval, config, conn):
          raise

  def _update_data(self, name, value, timestamp, interval, config, conn):
    '''Support function for insert. Should be called within a transaction'''
    i_time = config['i_calc'].to_bucket(timestamp)
    if not config['coarse']:
      r_time = config['r_calc'].to_bucket(timestamp)
    else:
      r_time = None
    stmt = self._table.update().where(
      and_(
        self._table.c.name==name,
        self._table.c.interval==interval,
        self._table.c.i_time==i_time,
        self._table.c.r_time==r_time)
    ).values({self._table.c.count: self._table.c.count + value})
    rval = conn.execute( stmt )
    return rval.rowcount

  def _type_get(self, name, interval, i_bucket, i_end=None):
    connection = self._client.connect()
    rval = OrderedDict()
    stmt = self._table.select()

    if i_end:
      stmt = stmt.where(
        and_(
          self._table.c.name==name,
          self._table.c.interval==interval,
          self._table.c.i_time>=i_bucket,
          self._table.c.i_time<=i_end,
        )
      )
    else:
      stmt = stmt.where(
        and_(
          self._table.c.name==name,
          self._table.c.interval==interval,
          self._table.c.i_time==i_bucket,
        )
      )
    stmt = stmt.order_by( self._table.c.r_time )

    for row in connection.execute(stmt):
      rval.setdefault(row['i_time'],OrderedDict())[row['r_time']] = row['count']
    return rval

class SqlGauge(SqlBackend, Gauge):

  def __init__(self, *a, **kwargs):
    # TODO: define indices
    # TODO: optionally create separate tables for each interval, like mongo?
    self._table_name = 'gauge'
    super(SqlGauge,self).__init__(*a, **kwargs)
    self._table = Table(self._table_name, self._metadata,
      Column('name', String(self._str_length), nullable=False),      # stat name
      Column('interval', String(self._str_length), nullable=False),  # interval name
      Column('i_time', Integer, nullable=False),        # interval timestamp
      Column('r_time', Integer, nullable=True),         # resolution timestamp
      Column('value', self._value_type, nullable=False),           # key counts

      # Use a constraint for transaction-less insert vs update
      UniqueConstraint('name', 'interval', 'i_time', 'r_time', name='unique_count')
    )
    self._metadata.create_all(self._client)

  def _insert_data(self, name, value, timestamp, interval, config, **kwargs):
    '''Helper to insert data into sql.'''
    conn = self._client.connect()
    if not self._update_data(name, value, timestamp, interval, config, conn):
      try:
        kwargs = {
          'name'        : name,
          'interval'    : interval,
          'i_time'      : config['i_calc'].to_bucket(timestamp),
          'value'       : value
        }
        if not config['coarse']:
          kwargs['r_time'] = config['r_calc'].to_bucket(timestamp)
        stmt = self._table.insert().values(**kwargs)
        result = conn.execute(stmt)
      except:
        # TODO: only catch IntegrityError
        if not self._update_data(name, value, timestamp, interval, config, conn):
          raise

  def _update_data(self, name, value, timestamp, interval, config, conn):
    '''Support function for insert. Should be called within a transaction'''
    i_time = config['i_calc'].to_bucket(timestamp)
    if not config['coarse']:
      r_time = config['r_calc'].to_bucket(timestamp)
    else:
      r_time = None
    stmt = self._table.update().where(
      and_(
        self._table.c.name==name,
        self._table.c.interval==interval,
        self._table.c.i_time==i_time,
        self._table.c.r_time==r_time)
    ).values({self._table.c.value: value})
    rval = conn.execute( stmt )
    return rval.rowcount

  def _type_get(self, name, interval, i_bucket, i_end=None):
    connection = self._client.connect()
    rval = OrderedDict()
    stmt = self._table.select()

    if i_end:
      stmt = stmt.where(
        and_(
          self._table.c.name==name,
          self._table.c.interval==interval,
          self._table.c.i_time>=i_bucket,
          self._table.c.i_time<=i_end,
        )
      )
    else:
      stmt = stmt.where(
        and_(
          self._table.c.name==name,
          self._table.c.interval==interval,
          self._table.c.i_time==i_bucket,
        )
      )
    stmt = stmt.order_by( self._table.c.r_time )

    for row in connection.execute(stmt):
      rval.setdefault(row['i_time'],OrderedDict())[row['r_time']] = row['value']
    return rval

########NEW FILE########
__FILENAME__ = timeseries
'''
Copyright (c) 2012-2014, Agora Games, LLC All rights reserved.

https://github.com/agoragames/kairos/blob/master/LICENSE.txt
'''
from .exceptions import *

from datetime import datetime, timedelta
import operator
import sys
import time
import re
import warnings
import functools

if sys.version_info[:2] > (2, 6):
    from collections import OrderedDict
else:
    from ordereddict import OrderedDict

from monthdelta import MonthDelta

BACKENDS = {}

NUMBER_TIME = re.compile('^[\d]+$')
SIMPLE_TIME = re.compile('^([\d]+)([hdwmy])$')

SIMPLE_TIMES = {
  'h' : 60*60,        # hour
  'd' : 60*60*24,     # day
  'w' : 60*60*24*7,   # week
  'm' : 60*60*24*30,  # month(-ish)
  'y' : 60*60*24*365, # year(-ish)
}

GREGORIAN_TIMES = set(['daily', 'weekly', 'monthly', 'yearly'])

# Test python3 compatibility
try:
  x = long(1)
except NameError:
  long = int

def _resolve_time(value):
  '''
  Resolve the time in seconds of a configuration value.
  '''
  if value is None or isinstance(value,(int,long)):
    return value

  if NUMBER_TIME.match(value):
    return long(value)

  simple = SIMPLE_TIME.match(value)
  if SIMPLE_TIME.match(value):
    multiplier = long( simple.groups()[0] )
    constant = SIMPLE_TIMES[ simple.groups()[1] ]
    return multiplier * constant

  if value in GREGORIAN_TIMES:
    return value

  raise ValueError('Unsupported time format %s'%value)

class RelativeTime(object):
  '''
  Functions associated with relative time intervals.
  '''

  def __init__(self, step=1):
    self._step = step

  def step_size(self, t0=None, t1=None):
    '''
    Return the time in seconds of a step. If a begin and end timestamp,
    return the time in seconds between them after adjusting for what buckets
    they alias to. If t1 and t0 resolve to the same bucket,
    '''
    if t0!=None and t1!=None:
      tb0 = self.to_bucket( t0 )
      tb1 = self.to_bucket( t1, steps=1 ) # NOTE: "end" of second bucket
      if tb0==tb1:
        return self._step
      return self.from_bucket( tb1 ) - self.from_bucket( tb0 )
    return self._step

  def to_bucket(self, timestamp, steps=0):
    '''
    Calculate the bucket from a timestamp, optionally including a step offset.
    '''
    return int( timestamp / self._step ) + steps

  def from_bucket(self, bucket):
    '''
    Calculate the timestamp given a bucket.
    '''
    return bucket * self._step

  def buckets(self, start, end):
    '''
    Calculate the buckets within a starting and ending timestamp.
    '''
    start_bucket = self.to_bucket(start)
    end_bucket = self.to_bucket(end)
    return range(start_bucket, end_bucket+1)

  def normalize(self, timestamp, steps=0):
    '''
    Normalize a timestamp according to the interval configuration. Can
    optionally determine an offset.
    '''
    return self.from_bucket( self.to_bucket(timestamp, steps) )

  def ttl(self, steps, relative_time=None):
    '''
    Return the ttl given the number of steps, None if steps is not defined
    or we're otherwise unable to calculate one. If relative_time is defined,
    then return a ttl that is the number of seconds from now that the 
    record should be expired.
    '''
    if steps:
      if relative_time:
        rtime = self.to_bucket(relative_time)
        ntime = self.to_bucket(time.time())
        # The relative time is beyond our TTL cutoff
        if (ntime - rtime) > steps:
          return 0
        # The relative time is in "recent" past or future
        else:
          return (steps + rtime - ntime) * self._step
      return steps * self._step

    return None

class GregorianTime(object):
  '''
  Functions associated with gregorian time intervals.
  '''
  # NOTE: strptime weekly has the following bug:
  # In [10]: datetime.strptime('197001', '%Y%U')
  # Out[10]: datetime.datetime(1970, 1, 1, 0, 0)
  # In [11]: datetime.strptime('197002', '%Y%U')
  # Out[11]: datetime.datetime(1970, 1, 1, 0, 0)

  FORMATS = {
    'daily'   : '%Y%m%d',
    'weekly'  : '%Y%U',
    'monthly' : '%Y%m',
    'yearly'  : '%Y'
  }

  def __init__(self, step='daily'):
    self._step = step

  def step_size(self, t0, t1=None):
    '''
    Return the time in seconds for each step. Requires that we know a time
    relative to which we should calculate to account for variable length
    intervals (e.g. February)
    '''
    tb0 = self.to_bucket( t0 )
    if t1:
      tb1 = self.to_bucket( t1, steps=1 ) # NOTE: "end" of second bucket
    else:
      tb1 = self.to_bucket( t0, steps=1 )

    # Calculate the difference in days, then multiply by simple scalar
    days = (self.from_bucket(tb1, native=True) - self.from_bucket(tb0, native=True)).days
    return days * SIMPLE_TIMES['d']

  def to_bucket(self, timestamp, steps=0):
    '''
    Calculate the bucket from a timestamp.
    '''
    dt = datetime.utcfromtimestamp( timestamp )

    if steps!=0:
      if self._step == 'daily':
        dt = dt + timedelta(days=steps)
      elif self._step == 'weekly':
        dt = dt + timedelta(weeks=steps)
      elif self._step == 'monthly':
        dt = dt + MonthDelta(steps)
      elif self._step == 'yearly':
        year = int(dt.strftime( self.FORMATS[self._step] ))
        year += steps
        dt = datetime(year=year, month=1, day=1)

    return int(dt.strftime( self.FORMATS[self._step] ))

  def from_bucket(self, bucket, native=False):
    '''
    Calculate the timestamp given a bucket.
    '''
    # NOTE: this is due to a bug somewhere in strptime that does not process
    # the week number of '%Y%U' correctly. That bug could be very specific to
    # the combination of python and ubuntu that I was testing.
    bucket = str(bucket)
    if self._step == 'weekly':
      year, week = bucket[:4], bucket[4:]
      normal = datetime(year=int(year), month=1, day=1) + timedelta(weeks=int(week))
    else:
      normal = datetime.strptime(bucket, self.FORMATS[self._step])
    if native:
      return normal
    return long(time.mktime( normal.timetuple() ))

  def buckets(self, start, end):
    '''
    Calculate the buckets within a starting and ending timestamp.
    '''
    rval = [ self.to_bucket(start) ]
    step = 1

    # In theory there's already been a check that end>start
    # TODO: Not a fan of an unbound while loop here
    while True:
      bucket = self.to_bucket(start, step)
      bucket_time = self.from_bucket( bucket )
      if bucket_time >= end:
        if bucket_time==end:
          rval.append( bucket )
        break
      rval.append( bucket )
      step += 1

    return rval

  def normalize(self, timestamp, steps=0):
    '''
    Normalize a timestamp according to the interval configuration. Optionally
    can be used to calculate the timestamp N steps away.
    '''
    # So far, the only commonality with RelativeTime
    return self.from_bucket( self.to_bucket(timestamp, steps) )

  def ttl(self, steps, relative_time=None):
    '''
    Return the ttl given the number of steps, None if steps is not defined
    or we're otherwise unable to calculate one. If relative_time is defined,
    then return a ttl that is the number of seconds from now that the 
    record should be expired.
    '''
    if steps:
      # Approximate the ttl based on number of seconds, since it's
      # "close enough"
      if relative_time:
        rtime = self.to_bucket(relative_time)
        ntime = self.to_bucket(time.time())

        # Convert to number of days
        day_diff = (self.from_bucket(ntime, native=True) - self.from_bucket(rtime, native=True)).days
        # Convert steps to number of days as well
        step_diff = (steps*SIMPLE_TIMES[self._step[0]]) / SIMPLE_TIMES['d']

        # The relative time is beyond our TTL cutoff
        if day_diff > step_diff:
          return 0
        # The relative time is in "recent" past or future
        else:
          return (step_diff - day_diff) * SIMPLE_TIMES['d']
      return steps * SIMPLE_TIMES[ self._step[0] ]

    return None

class TimeseriesMeta(type):
  '''
  Meta class for URL parsing
  '''
  def __call__(cls, client, **kwargs):
    if isinstance(client, (str,unicode)):
      for backend in BACKENDS.values():
        handle = backend.url_parse(client, **kwargs.pop('client_config',{}))
        if handle:
          client = handle
          break
    if isinstance(client, (str,unicode)):
      raise ImportError("Unsupported or unknown client type for %s", client)
    return type.__call__(cls, client, **kwargs)

class Timeseries(object):
  '''
  Base class of all time series. Also acts as a factory to return the correct
  subclass if "type=" keyword argument supplied.
  '''
  __metaclass__ = TimeseriesMeta

  def __new__(cls, client, **kwargs):
    if cls==Timeseries:
      # load a backend based on the name of the client module
      client_module = client.__module__.split('.')[0]
      backend = BACKENDS.get( client_module )
      if backend:
        return backend( client, **kwargs )

      raise ImportError("Unsupported or unknown client type %s", client_module)
    return object.__new__(cls, client, **kwargs)

  def __init__(self, client, **kwargs):
    '''
    Create a time series using a given redis client and keyword arguments
    defining the series configuration.

    Optionally provide a prefix for all keys. If prefix length>0 and it
    doesn't end with ":", it will be automatically appended. Redis only.

    The redis client must be API compatible with the Redis instance from
    the redis package http://pypi.python.org/pypi/redis


    The supported keyword arguments are:

    type
      One of (series, histogram, count). Optional, defaults to "series".

      series - each interval will append values to a list
      histogram - each interval will track count of unique values
      count - each interval will maintain a single counter

    prefix
      Optional, is a prefix for all keys in this histogram. If supplied
      and it doesn't end with ":", it will be automatically appended.
      Redis only.

    read_func
      Optional, is a function applied to all values read back from the
      database. Without it, values will be strings. Must accept a string
      value and can return anything.

    write_func
      Optional, is a function applied to all values when writing. Can be
      used for histogram resolution, converting an object into an id, etc.
      Must accept whatever can be inserted into a timeseries and return an
      object which can be cast to a string.

    intervals
      Required, a dictionary of interval configurations in the form of:

      {
        # interval name, used in redis keys and should conform to best practices
        # and not include ":"
        minute: {

          # Required. The number of seconds that the interval will cover
          step: 60,

          # Optional. The maximum number of intervals to maintain. If supplied,
          # will use redis expiration to delete old intervals, else intervals
          # exist in perpetuity.
          steps: 240,

          # Optional. Defines the resolution of the data, i.e. the number of
          # seconds in which data is assumed to have occurred "at the same time".
          # So if you're tracking a month long time series, you may only need
          # resolution down to the day, or resolution=86400. Defaults to same
          # value as "step".
          resolution: 60,
        }
      }
    '''
    # Process the configuration first so that the backends can use that to
    # complete their setup.
    # Prefix is determined by the backend implementation.
    self._client = client
    self._read_func = kwargs.get('read_func',None)
    self._write_func = kwargs.get('write_func',None)
    self._intervals = kwargs.get('intervals', {})

    # Preprocess the intervals
    for interval,config in self._intervals.items():
      # Copy the interval name into the configuration, needed for redis
      config['interval'] = interval
      step = config['step'] = _resolve_time( config['step'] ) # Required
      steps = config.get('steps',None)       # Optional
      resolution = config['resolution'] = _resolve_time(
        config.get('resolution',config['step']) ) # Optional

      if step in GREGORIAN_TIMES:
        interval_calc = GregorianTime(step)
      else:
        interval_calc = RelativeTime(step)

      if resolution in GREGORIAN_TIMES:
        resolution_calc = GregorianTime(resolution)
      else:
        resolution_calc = RelativeTime(resolution)

      config['i_calc'] = interval_calc
      config['r_calc'] = resolution_calc

      config['expire'] = interval_calc.ttl( steps )
      config['ttl'] = functools.partial( interval_calc.ttl, steps )
      config['coarse'] = (resolution==step)

  def list(self):
    '''
    List all of the stat names that are stored.
    '''
    raise NotImplementedError()

  def properties(self, name):
    '''
    Get the properties of a stat.
    '''
    raise NotImplementedError()

  def expire(self, name):
    '''
    Manually expire data for storage engines that do not support auto expiry.
    '''
    raise NotImplementedError()

  def bulk_insert(self, inserts, intervals=0, **kwargs):
    '''
    Perform a bulk insert. The format of the inserts must be:

    {
      timestamp : {
        name: [ values ],
        ...
      },
      ...
    }

    If the timestamp should be auto-generated, then "timestamp" should be None.

    Backends can implement this in any number of ways, the default being to
    perform a single insert for each value, with no specialized locking,
    transactions or batching.
    '''
    if None in inserts:
      inserts[ time.time() ] = inserts.pop(None)
    if self._write_func:
      for timestamp,names in inserts.iteritems():
        for name,values in names.iteritems():
          names[name] = [ self._write_func(v) for v in values ]
    self._batch_insert(inserts, intervals, **kwargs)

  def insert(self, name, value, timestamp=None, intervals=0, **kwargs):
    '''
    Insert a value for the timeseries "name". For each interval in the
    configuration, will insert the value into a bucket for the interval
    "timestamp". If time is not supplied, will default to time.time(), else it
    should be a floating point value.

    If "intervals" is less than 0, inserts the value into timestamps
    "abs(intervals)" preceeding "timestamp" (i.e. "-1" inserts one extra value).
    If "intervals" is greater than 0, inserts the value into that many more
    intervals after "timestamp". The default behavior is to insert for a single
    timestamp.

    This supports the public methods of the same name in the subclasses. The
    value is expected to already be converted.
    '''
    if not timestamp:
      timestamp = time.time()

    if isinstance(value, (list,tuple,set)):
      if self._write_func:
        value = [ self._write_func(v) for v in value ]
      return self._batch_insert({timestamp:{name:value}}, intervals, **kwargs)

    if self._write_func:
      value = self._write_func(value)

    # TODO: document acceptable names
    # TODO: document what types values are supported
    # TODO: document behavior when time is outside the bounds of TTLed config
    # TODO: document how the data is stored.
    # TODO: better abstraction for "intervals" processing rather than in each implementation

    self._insert( name, value, timestamp, intervals, **kwargs )

  def _batch_insert(self, inserts, intervals, **kwargs):
    '''
    Support for batch insert. Default implementation is non-optimized and
    is a simple loop over values.
    '''
    for timestamp,names in inserts.iteritems():
      for name,values in names.iteritems():
        for value in values:
          self._insert( name, value, timestamp, intervals, **kwargs )

  def _normalize_timestamps(self, timestamp, intervals, config):
    '''
    Helper for the subclasses to generate a list of timestamps.
    '''
    rval = [timestamp]
    if intervals<0:
      while intervals<0:
        rval.append( config['i_calc'].normalize(timestamp, intervals) )
        intervals += 1
    elif intervals>0:
      while intervals>0:
        rval.append( config['i_calc'].normalize(timestamp, intervals) )
        intervals -= 1
    return rval

  def _insert(self, name, value, timestamp, intervals, **kwargs):
    '''
    Support for the insert per type of series.
    '''
    raise NotImplementedError()

  def delete(self, name):
    '''
    Delete all data in a timeseries. Subclasses are responsible for
    implementing this.
    '''
    raise NotImplementedError()

  def delete_all(self):
    '''
    Deletes all data in every timeseries. Default implementation is to walk
    all of the names and call delete(stat), storage implementations are welcome
    to optimize this.
    '''
    for name in self.list():
      self.delete(name)

  def iterate(self, name, interval, **kwargs):
    '''
    Returns a generator that iterates over all the intervals and returns
    data for various timestamps, in the form:

      ( unix_timestamp, data )

    This will check for all timestamp buckets that might exist between
    the first and last timestamp in a series. Each timestamp bucket will
    be fetched separately to keep this memory efficient, at the cost of
    extra trips to the data store.

    Keyword arguments are the same as get().
    '''
    config = self._intervals.get(interval)
    if not config:
      raise UnknownInterval(interval)
    properties = self.properties(name)[interval]

    i_buckets = config['i_calc'].buckets(properties['first'], properties['last'])
    for i_bucket in i_buckets:
      data = self.get(name, interval,
        timestamp=config['i_calc'].from_bucket(i_bucket), **kwargs)
      for timestamp,row in data.items():
        yield (timestamp,row)

  def get(self, name, interval, **kwargs):
    '''
    Get the set of values for a named timeseries and interval. If timestamp
    supplied, will fetch data for the period of time in which that timestamp
    would have fallen, else returns data for "now". If the timeseries
    resolution was not defined, then returns a simple list of values for the
    interval, else returns an ordered dict where the keys define the resolution
    interval and the values are the time series data in that (sub)interval.
    This allows the user to interpolate sparse data sets.

    If transform is defined, will utilize one of `[mean, count, min, max, sum]`
    to process each row of data returned. If the transform is a callable, will
    pass an array of data to the function. Note that the transform will be run
    after the data is condensed. If the transform is a list, then each row will
    return a hash of the form { transform_name_or_func : transformed_data }.
    If the transform is a hash, then it should be of the form
    { transform_name : transform_func } and will return the same structure as
    a list argument.

    Raises UnknownInterval if `interval` is not one of the configured
    intervals.

    TODO: Fix this method doc
    '''
    config = self._intervals.get(interval)
    if not config:
      raise UnknownInterval(interval)

    timestamp = kwargs.get('timestamp', time.time())
    fetch = kwargs.get('fetch')
    process_row = kwargs.get('process_row') or self._process_row
    condense = kwargs.get('condense', False)
    join_rows = kwargs.get('join_rows') or self._join
    transform = kwargs.get('transform')

    # DEPRECATED handle the deprecated version of condense
    condense = kwargs.get('condensed',condense)

    # If name is a list, then join all of results. It is more efficient to
    # use a single data structure and join "in-line" but that requires a major
    # refactor of the backends, so trying this solution to start with. At a
    # minimum we'd have to rebuild the results anyway because of the potential
    # for sparse data points would result in an out-of-order result.
    if isinstance(name, (list,tuple,set)):
      results = [ self._get(x, interval, config, timestamp, fetch=fetch, process_row=process_row) for x in name ]
      # Even resolution data is "coarse" in that it's not nested
      rval = self._join_results( results, True, join_rows )
    else:
      rval = self._get( name, interval, config, timestamp, fetch=fetch, process_row=process_row )

    # If condensed, collapse the result into a single row. Adjust the step_size
    # calculation to match.
    if config['coarse']:
      step_size = config['i_calc'].step_size(timestamp)
    else:
      step_size = config['r_calc'].step_size(timestamp)
    if condense and not config['coarse']:
      condense = condense if callable(condense) else self._condense
      rval = { config['i_calc'].normalize(timestamp) : condense(rval) }
      step_size = config['i_calc'].step_size(timestamp)

    if transform:
      for k,v in rval.items():
        rval[k] = self._process_transform(v, transform, step_size)
    return rval

  def _get(self, name, interval, config, timestamp, fetch):
    '''
    Support for the insert per type of series.
    '''
    raise NotImplementedError()

  def series(self, name, interval, **kwargs):
    '''
    Return all the data in a named time series for a given interval. If steps
    not defined and there are none in the config, defaults to 1.

    Returns an ordered dict of interval timestamps to a single interval, which
    matches the return value in get().

    If transform is defined, will utilize one of `[mean, count, min, max, sum]`
    to process each row of data returned. If the transform is a callable, will
    pass an array of data to the function. Note that the transform will be run
    after the data is condensed.

    Raises UnknownInterval if `interval` not configured.
    '''
    config = self._intervals.get(interval)
    if not config:
      raise UnknownInterval(interval)

    start = kwargs.get('start')
    end = kwargs.get('end')
    steps = kwargs.get('steps') or config.get('steps',1)

    fetch = kwargs.get('fetch')
    process_row = kwargs.get('process_row') or self._process_row
    condense = kwargs.get('condense', False)
    join_rows = kwargs.get('join_rows') or self._join
    collapse = kwargs.get('collapse', False)
    transform = kwargs.get('transform')
    # DEPRECATED handle the deprecated version of condense
    condense = kwargs.get('condensed',condense)

    # If collapse, also condense
    if collapse: condense = condense or True

    # Fugly range determination, all to get ourselves a start and end
    # timestamp. Adjust steps argument to include the anchoring date.
    if end is None:
      if start is None:
        end = time.time()
        end_bucket = config['i_calc'].to_bucket( end )
        start_bucket = config['i_calc'].to_bucket( end, (-steps+1) )
      else:
        start_bucket = config['i_calc'].to_bucket( start )
        end_bucket = config['i_calc'].to_bucket( start, steps-1 )
    else:
      end_bucket = config['i_calc'].to_bucket( end )
      if start is None:
        start_bucket = config['i_calc'].to_bucket( end, (-steps+1) )
      else:
        start_bucket = config['i_calc'].to_bucket( start )

    # Now that we have start and end buckets, convert them back to normalized
    # time stamps and then back to buckets. :)
    start = config['i_calc'].from_bucket( start_bucket )
    end = config['i_calc'].from_bucket( end_bucket )
    if start > end: end = start

    interval_buckets = config['i_calc'].buckets(start, end)

    # If name is a list, then join all of results. It is more efficient to
    # use a single data structure and join "in-line" but that requires a major
    # refactor of the backends, so trying this solution to start with. At a
    # minimum we'd have to rebuild the results anyway because of the potential
    # for sparse data points would result in an out-of-order result.
    if isinstance(name, (list,tuple,set)):
      results = [ self._series(x, interval, config, interval_buckets, fetch=fetch, process_row=process_row) for x in name ]
      rval = self._join_results( results, config['coarse'], join_rows )
    else:
      rval = self._series(name, interval, config, interval_buckets, fetch=fetch, process_row=process_row)

    # If fine-grained, first do the condensed pass so that it's easier to do
    # the collapse afterwards. Be careful not to run the transform if there's
    # going to be another pass at condensing the data.
    if not config['coarse']:
      if condense:
        condense = condense if callable(condense) else self._condense
        for key in rval.iterkeys():
          data = condense( rval[key] )
          if transform and not collapse:
            data = self._process_transform(data, transform, config['i_calc'].step_size(key))
          rval[key] = data
      elif transform:
        for interval,resolutions in rval.items():
          for key in resolutions.iterkeys():
            resolutions[key] = self._process_transform(resolutions[key], transform, config['r_calc'].step_size(key))

    if config['coarse'] or collapse:
      if collapse:
        collapse = collapse if callable(collapse) else condense if callable(condense) else self._condense
        data = collapse(rval)
        if transform:
          rval = { rval.keys()[0] : self._process_transform(data, transform, config['i_calc'].step_size(rval.keys()[0], rval.keys()[-1])) }
        else:
          rval = { rval.keys()[0] : data }

      elif transform:
        for key,data in rval.items():
          rval[key] = self._process_transform(data, transform, config['i_calc'].step_size(key))

    return rval

  def _series(self, name, interval, config, buckets, **kws):
    '''
    Subclasses must implement fetching a series.
    '''
    raise NotImplementedError()

  def _join_results(self, results, coarse, join):
    '''
    Join a list of results. Supports both get and series.
    '''
    rval = OrderedDict()
    i_keys = set()
    for res in results:
      i_keys.update( res.keys() )
    for i_key in sorted(i_keys):
      if coarse:
        rval[i_key] = join( [res.get(i_key) for res in results] )
      else:
        rval[i_key] = OrderedDict()
        r_keys = set()
        for res in results:
          r_keys.update( res.get(i_key,{}).keys() )
        for r_key in sorted(r_keys):
          rval[i_key][r_key] = join( [res.get(i_key,{}).get(r_key) for res in results] )
    return rval

  def _process_transform(self, data, transform, step_size):
    '''
    Process transforms on the data.
    '''
    if isinstance(transform, (list,tuple,set)):
      return { t : self._transform(data,t,step_size) for t in transform }
    elif isinstance(transform, dict):
      return { tn : self._transform(data,tf,step_size) for tn,tf in transform.items() }
    return self._transform(data,transform,step_size)

  def _transform(self, data, transform, step_size):
    '''
    Transform the data. If the transform is not supported by this series,
    returns the data unaltered.
    '''
    raise NotImplementedError()

  def _insert(self, handle, key, value):
    '''
    Subclasses must implement inserting a value for a key.
    '''
    raise NotImplementedError()

  def _process_row(self, data):
    '''
    Subclasses should apply any read function to the data. Will only be called
    if there is one.
    '''
    raise NotImplementedError()

  def _condense(self, data):
    '''
    Condense a mapping of timestamps and associated data into a single
    object/value which will be mapped back to a timestamp that covers all
    of the data.
    '''
    raise NotImplementedError()

  def _join(self, rows):
    '''
    Join multiple rows worth of data into a single result.
    '''
    raise NotImplementedError()


class Series(Timeseries):
  '''
  Simple time series where all data is stored in a list for each interval.
  '''

  def _type_no_value(self):
    return []

  def _transform(self, data, transform, step_size):
    '''
    Transform the data. If the transform is not supported by this series,
    returns the data unaltered.
    '''
    if transform=='mean':
      total = sum( data )
      count = len( data )
      data = float(total)/float(count) if count>0 else 0
    elif transform=='count':
      data = len( data )
    elif transform=='min':
      data = min( data or [0])
    elif transform=='max':
      data = max( data or [0])
    elif transform=='sum':
      data = sum( data )
    elif transform=='rate':
      data = len( data ) / float(step_size)
    elif callable(transform):
      data = transform(data, step_size)
    return data

  def _process_row(self, data):
    if self._read_func:
      return map(self._read_func, data)
    return data

  def _condense(self, data):
    '''
    Condense by adding together all of the lists.
    '''
    if data:
      return reduce(operator.add, data.values())
    return []

  def _join(self, rows):
    '''
    Join multiple rows worth of data into a single result.
    '''
    rval = []
    for row in rows:
      if row: rval.extend( row )
    return rval

class Histogram(Timeseries):
  '''
  Data for each interval is stored in a hash, counting occurrances of the
  same value within an interval. It is up to the user to determine the precision
  and distribution of the data points within the histogram.
  '''

  def _type_no_value(self):
    return {}

  def _transform(self, data, transform, step_size):
    '''
    Transform the data. If the transform is not supported by this series,
    returns the data unaltered.
    '''
    if transform=='mean':
      total = sum( k*v for k,v in data.items() )
      count = sum( data.values() )
      data = float(total)/float(count) if count>0 else 0
    elif transform=='count':
      data = sum(data.values())
    elif transform=='min':
      data = min(data.keys() or [0])
    elif transform=='max':
      data = max(data.keys() or [0])
    elif transform=='sum':
      data = sum( k*v for k,v in data.items() )
    elif transform=='rate':
      data = { k:v/float(step_size) for k,v in data.items() }
    elif callable(transform):
      data = transform(data, step_size)
    return data

  def _process_row(self, data):
    rval = {}
    for value,count in data.items():
      if self._read_func: value = self._read_func(value)
      rval[ value ] = int(count)
    return rval

  def _condense(self, data):
    '''
    Condense by adding together all of the lists.
    '''
    rval = {}
    for resolution,histogram in data.items():
      for value,count in histogram.items():
        rval[ value ] = count + rval.get(value,0)
    return rval

  def _join(self, rows):
    '''
    Join multiple rows worth of data into a single result.
    '''
    rval = {}
    for row in rows:
      if row:
        for value,count in row.items():
          rval[ value ] = count + rval.get(value,0)
    return rval

class Count(Timeseries):
  '''
  Time series that simply increments within each interval.
  '''

  def _type_no_value(self):
    return 0

  def _transform(self, data, transform, step_size):
    '''
    Transform the data. If the transform is not supported by this series,
    returns the data unaltered.
    '''
    if transform=='rate':
      data = data / float(step_size)
    elif callable(transform):
      data = transform(data, step_size)
    return data

  def insert(self, name, value=1, timestamp=None, **kwargs):
    super(Count,self).insert(name, value, timestamp, **kwargs)

  def _process_row(self, data):
    return int(data) if data else 0

  def _condense(self, data):
    '''
    Condense by adding together all of the lists.
    '''
    if data:
      return sum(data.values())
    return 0

  def _join(self, rows):
    '''
    Join multiple rows worth of data into a single result.
    '''
    rval = 0
    for row in rows:
      if row: rval += row
    return rval

class Gauge(Timeseries):
  '''
  Time series that stores the last value.
  '''

  def _type_no_value(self):
    # TODO: resolve this disconnect with redis backend
    return 0

  def _transform(self, data, transform, step_size):
    '''
    Transform the data. If the transform is not supported by this series,
    returns the data unaltered.
    '''
    if callable(transform):
      data = transform(data, step_size)
    return data

  def _process_row(self, data):
    if self._read_func:
      return self._read_func(data or '')
    return data

  def _condense(self, data):
    '''
    Condense by returning the last real value of the gauge.
    '''
    if data:
      data = filter(None,data.values())
      if data:
        return data[-1]
    return None

  def _join(self, rows):
    '''
    Join multiple rows worth of data into a single result.
    '''
    rval = None
    for row in rows:
      if row: rval = row
    return rval

class Set(Timeseries):
  '''
  Time series that manages sets.
  '''

  def _type_no_value(self):
    return set()

  def _transform(self, data, transform, step_size):
    '''
    Transform the data. If the transform is not supported by this series,
    returns the data unaltered.
    '''
    if transform=='mean':
      total = sum( data )
      count = len( data )
      data = float(total)/float(count) if count>0 else 0
    elif transform=='count':
      data = len(data)
    elif transform=='min':
      data = min(data or [0])
    elif transform=='max':
      data = max(data or [0])
    elif transform=='sum':
      data = sum(data)
    elif transform=='rate':
      data = len(data) / float(step_size)
    elif callable(transform):
      data = transform(data)
    return data

  def _process_row(self, data):
    if self._read_func:
      return set( (self._read_func(d) for d in data) )
    return data

  def _condense(self, data):
    '''
    Condense by or-ing all of the sets.
    '''
    if data:
      return reduce(operator.ior, data.values())
    return set()

  def _join(self, rows):
    '''
    Join multiple rows worth of data into a single result.
    '''
    rval = set()
    for row in rows:
      if row: rval |= row
    return rval

# Load the backends after all the timeseries had been defined.
try:
  from .redis_backend import RedisBackend
  BACKENDS['redis'] = RedisBackend
except ImportError as e:
  warnings.warn('Redis backend not loaded, {}'.format(e))

try:
  from .mongo_backend import MongoBackend
  BACKENDS['pymongo'] = MongoBackend
except ImportError as e:
  warnings.warn('Mongo backend not loaded, {}'.format(e))

try:
  from .sql_backend import SqlBackend
  BACKENDS['sqlalchemy'] = SqlBackend
except ImportError as e:
  warnings.warn('SQL backend not loaded, {}'.format(e))

try:
  from .cassandra_backend import CassandraBackend
  BACKENDS['cql'] = CassandraBackend
except ImportError as e:
  warnings.warn('Cassandra backend not loaded, {}'.format(e))

########NEW FILE########
__FILENAME__ = api_helper
from helper_helper import *
from helper_helper import _time

@unittest.skipUnless( os.environ.get('TEST_API','true').lower()=='true', 'skipping api' )
class ApiHelper(Chai):

  def setUp(self):
    super(ApiHelper,self).setUp()

    self.series = Timeseries(self.client, type='series', prefix='kairos',
      read_func=int, #write_func=str, 
      intervals={
        'minute' : {
          'step' : 60,
          'steps' : 5,
        },
        'hour' : {
          'step' : 3600,
          'resolution' : 60,
        },
        'bulk-hour' : {
          'step' : 3600,
        }
      } )
    self.series.delete_all()

  def tearDown(self):
    self.series.delete_all()

  def test_list(self):
    self.series.insert( 'test', 32, timestamp=_time(0) )
    self.series.insert( 'test1', 32, timestamp=_time(0) )
    self.series.insert( 'test2', 32, timestamp=_time(0) )
    self.series.insert( 'test', 32, timestamp=_time(0) )

    res = sorted(self.series.list())
    assert_equals( ['test', 'test1', 'test2'], res )

    self.series.delete('test')
    self.series.delete('test1')
    self.series.delete('test2')

  def test_properties(self):
    self.series.insert( 'test', 32, timestamp=_time(0) )
    self.series.insert( 'test', 32, timestamp=_time(60) )
    self.series.insert( 'test', 32, timestamp=_time(600) )

    res = self.series.properties('test')
    assert_equals( _time(0), res['minute']['first'] )
    assert_equals( _time(600), res['minute']['last'] )
    assert_equals( _time(0), res['hour']['first'] )
    assert_equals( _time(0), res['hour']['last'] )

    self.series.delete('test')

  def test_iterate(self):
    self.series.insert( 'test', 32, timestamp=_time(0) )
    self.series.insert( 'test', 42, timestamp=_time(60) )
    self.series.insert( 'test', 52, timestamp=_time(600) )

    # There should be a result for every possible step between first and last
    res = list(self.series.iterate('test','minute'))
    assert_equals( 11, len(res) )
    assert_equals( (_time(0),[32]), res[0] )
    assert_equals( (_time(60),[42]), res[1] )
    assert_equals( (_time(120),[]), res[2] )
    assert_equals( (_time(600),[52]), res[-1] )

    # With resolutions, there should be a result only for where there's data      
    res = list(self.series.iterate('test','hour'))
    assert_equals( 3, len(res) )
    assert_equals( (_time(0),[32]), res[0] )
    assert_equals( (_time(60),[42]), res[1] )
    assert_equals( (_time(600),[52]), res[2] )

    # Without resolutions, there should be a single result
    res = list(self.series.iterate('test','bulk-hour'))
    assert_equals( 1, len(res) )
    assert_equals( (_time(0),[32,42,52]), res[0] )

    self.series.delete('test')

########NEW FILE########
__FILENAME__ = cassandra_timeseries_test
'''
Functional tests for cassandra timeseries
'''
import time
import datetime
import os

import cql

from . import helpers
from .helpers import unittest, os, Timeseries

@unittest.skipUnless( os.environ.get('TEST_CASSANDRA','true').lower()=='true', 'skipping cassandra' )
class CassandraApiTest(helpers.ApiHelper):

  def setUp(self):
    self.client = cql.connect('localhost', 9160, os.environ.get('CASSANDRA_KEYSPACE','kairos'), cql_version='3.0.0')
    super(CassandraApiTest,self).setUp()

  def test_url_parse(self):
    assert_equals( 'CassandraSeries', 
      Timeseries( 'cql://localhost', type='series' ).__class__.__name__ )

# Not running gregorian tests because they run in the "far future" where long
# TTLs are not supported.
#@unittest.skipUnless( os.environ.get('TEST_CASSANDRA','true').lower()=='true', 'skipping cassandra' )
#class CassandraGregorianTest(helpers.GregorianHelper):

  #def setUp(self):
    #self.client = cql.connect('localhost', 9160, os.environ.get('CASSANDRA_KEYSPACE','kairos'), cql_version='3.0.0')
    #super(CassandraGregorianTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_CASSANDRA','true').lower()=='true', 'skipping cassandra' )
class CassandraSeriesTest(helpers.SeriesHelper):

  def setUp(self):
    self.client = cql.connect('localhost', 9160, os.environ.get('CASSANDRA_KEYSPACE','kairos'), cql_version='3.0.0')
    super(CassandraSeriesTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_CASSANDRA','true').lower()=='true', 'skipping cassandra' )
class CassandraHistogramTest(helpers.HistogramHelper):

  def setUp(self):
    self.client = cql.connect('localhost', 9160, os.environ.get('CASSANDRA_KEYSPACE','kairos'), cql_version='3.0.0')
    super(CassandraHistogramTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_CASSANDRA','true').lower()=='true', 'skipping cassandra' )
class CassandraCountTest(helpers.CountHelper):

  def setUp(self):
    self.client = cql.connect('localhost', 9160, os.environ.get('CASSANDRA_KEYSPACE','kairos'), cql_version='3.0.0')
    super(CassandraCountTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_CASSANDRA','true').lower()=='true', 'skipping cassandra' )
class CassandraGaugeTest(helpers.GaugeHelper):

  def setUp(self):
    self.client = cql.connect('localhost', 9160, os.environ.get('CASSANDRA_KEYSPACE','kairos'), cql_version='3.0.0')
    super(CassandraGaugeTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_CASSANDRA','true').lower()=='true', 'skipping cassandra' )
class CassandraSetTest(helpers.SetHelper):

  def setUp(self):
    self.client = cql.connect('localhost', 9160, os.environ.get('CASSANDRA_KEYSPACE','kairos'), cql_version='3.0.0')
    super(CassandraSetTest,self).setUp()

########NEW FILE########
__FILENAME__ = count_helper
from helper_helper import *
from helper_helper import _time

from collections import OrderedDict

@unittest.skipUnless( os.environ.get('TEST_COUNT','true').lower()=='true', 'skipping counts' )
class CountHelper(Chai):

  def setUp(self):
    super(CountHelper,self).setUp()

    self.series = Timeseries(self.client, type='count', prefix='kairos',
      read_func=int,
      intervals={
        'minute' : {
          'step' : 60,
          'steps' : 5,
        },
        'hour' : {
          'step' : 3600,
          'resolution' : 60,
        }
      } )
    self.series.delete_all()

  def tearDown(self):
    self.series.delete_all()

  def test_bulk_insert(self):
    inserts = {
      None      : { 'test1':[1,2,3], 'test2':[4,5,6] },
      _time(0)  : { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] },
      _time(30) : { 'test1':[1,2,3], 'test2':[4,5,6] },
      _time(60) : { 'test1':[1,2,3], 'test3':[7,8,9] }
    }
    self.series.bulk_insert( inserts )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( 1+2+3+1+2+3, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( 4+5+6+4+5+6, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( 7+8+9, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(60))
    assert_equals( 1+2+3, t1_i2[_time(60)] )

  def test_bulk_insert_intervals_after(self):
    a,b,c,d,e,f = 10,11,12,13,14,15
    inserts = OrderedDict( (
      (None     , { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(0) , { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] } ),
      (_time(30), { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(60), { 'test1':[a,b,c], 'test3':[d,e,f] })
    ) )
    self.series.bulk_insert( inserts, intervals=3 )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( 1+2+3+1+2+3, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( 4+5+6+4+5+6, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( 7+8+9, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(60))
    assert_equals( 1+2+3+1+2+3+a+b+c, t1_i2[_time(60)] )

    t3_i3 = self.series.get('test3', 'minute', timestamp=_time(120))
    assert_equals( 7+8+9+d+e+f, t3_i3[_time(120)] )

    t3_i4 = self.series.get('test3', 'minute', timestamp=_time(180))
    assert_equals( 7+8+9+d+e+f, t3_i4[_time(180)] )

  def test_bulk_insert_intervals_before(self):
    a,b,c,d,e,f = 10,11,12,13,14,15
    inserts = OrderedDict( (
      (None     , { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(0) , { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] } ),
      (_time(30), { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(60), { 'test1':[a,b,c], 'test3':[d,e,f] })
    ) )
    self.series.bulk_insert( inserts, intervals=-3 )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( 1+2+3+1+2+3+a+b+c, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( 4+5+6+4+5+6, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( 7+8+9+d+e+f, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(-60))
    assert_equals( 1+2+3+1+2+3+a+b+c, t1_i2[_time(-60)] )

    t3_i3 = self.series.get('test3', 'minute', timestamp=_time(-120))
    assert_equals( 7+8+9+d+e+f, t3_i3[_time(-120)] )

    t3_i4 = self.series.get('test3', 'minute', timestamp=_time(-180))
    assert_equals( 7+8+9, t3_i4[_time(-180)] )
  
  def test_get(self):
    # 2 hours worth of data
    for t in xrange(1, 7200):
      self.series.insert( 'test', 1, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    # middle of an interval
    interval = self.series.get( 'test', 'minute', timestamp=_time(100) )
    assert_equals( map(_time, [60]), interval.keys() )
    assert_equals( 60, interval[_time(60)] )

    # no matching interval, returns no with empty value list
    interval = self.series.get( 'test', 'minute' )
    assert_equals( 1, len(interval) )
    assert_equals( 0, interval.values()[0] )
    
    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.get( 'test', 'hour', timestamp=_time(100) )
    assert_equals( 60, len(interval) )
    assert_equals( 60, interval[_time(60)] )
    
    interval = self.series.get( 'test', 'hour', timestamp=_time(100), transform='rate' )
    assert_equals( 1.0, interval[_time(60)] )

    interval = self.series.get( 'test', 'hour', timestamp=_time(100), condensed=True )
    assert_equals( 1, len(interval) )
    assert_equals( 3599, interval[_time(0)] )
    
    interval = self.series.get( 'test', 'hour', timestamp=_time(4000), condensed=True )
    assert_equals( 1, len(interval) )
    assert_equals( 3600, interval[_time(3600)] )

    interval = self.series.get( 'test', 'hour', timestamp=_time(4000), condensed=True, transform='rate' )
    assert_equals( 1, len(interval) )
    assert_equals( 1.0, interval[_time(3600)] )

  def test_get_joined(self):
    # put some data in the first minutes of each hour for test1, and then for
    # a few more minutes in test2
    for t in xrange(1, 120):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(3600, 3720):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(120, 240):
      self.series.insert( 'test1', t, timestamp=_time(t) )
    for t in xrange(3721, 3840):
      self.series.insert( 'test1', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    # interval with 2 series worth of data
    interval = self.series.get( ['test1','test2'], 'minute', timestamp=_time(100) )
    assert_equals( [_time(60)], interval.keys() )
    assert_equals( 2*sum(range(60,120)), interval[_time(60)] )

    interval = self.series.get( ['test1','test2'], 'minute', timestamp=_time(100), transform='rate' )
    assert_equals( (2*sum(range(60,120)))/60.0, interval[_time(60)] )

    # interval with 1 series worth of data
    interval = self.series.get( ['test1','test2'], 'minute', timestamp=_time(122) )
    assert_equals( [_time(120)], interval.keys() )
    assert_equals( sum(range(120,180)), interval[_time(120)] )
    interval = self.series.get( ['test1','test2'], 'minute', timestamp=_time(122), transform='rate' )
    assert_equals( (sum(range(120,180)))/60.0, interval[_time(120)] )

    # no matching interval, returns no with empty value list
    interval = self.series.get( ['test1','test2'], 'minute' )
    assert_equals( 1, len(interval) )
    assert_equals( 0, interval.values()[0] )
    interval = self.series.get( ['test1','test2'], 'minute', transform='rate' )

    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100) )
    assert_equals( map(_time,[0,60,120,180]), interval.keys() )
    assert_equals( 2*sum(range(1,60)), interval[_time(0)] )
    assert_equals( 2*sum(range(60,120)), interval[_time(60)] )
    assert_equals( sum(range(120,180)), interval[_time(120)] )
    assert_equals( sum(range(180,240)), interval[_time(180)] )

    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100), condensed=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( 2*sum(range(1,120)) + sum(range(120,240)), interval[_time(0)] )

    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100), condensed=True, transform='rate' )
    assert_equals( (2*sum(range(1,120)) + sum(range(120,240)))/3600.0, interval[_time(0)] )

  def test_series(self):
    # 2 hours worth of data
    for t in xrange(1, 7200):
      self.series.insert( 'test', 1, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    interval = self.series.series( 'test', 'minute', end=_time(250) )
    assert_equals( map(_time, [0,60,120,180,240]), interval.keys() )
    assert_equals( 59, interval[_time(0)] )
    assert_equals( 60, interval[_time(60)] )
    
    interval = self.series.series( 'test', 'minute', steps=2, end=_time(250) )
    assert_equals( map(_time, [180,240]), interval.keys() )
    assert_equals( 60, interval[_time(240)] )

    interval = self.series.series( 'test', 'minute', steps=2, end=_time(250), transform='rate' )
    assert_equals( 1.0, interval[_time(240)] )

    # with collapse
    interval = self.series.series( 'test', 'minute', end=_time(250), collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( 299, interval[_time(0)] )
    
    ###
    ### with resolution
    ###
    interval = self.series.series( 'test', 'hour', end=_time(250) )
    assert_equals( 1, len(interval) )
    assert_equals( 60, len(interval[_time(0)]) )
    assert_equals( 59, interval[_time(0)][_time(0)] )
    assert_equals( 60, interval[_time(0)][_time(60)] )

    # single step, last one    
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200) )
    assert_equals( 1, len(interval) )
    assert_equals( 3600, interval[_time(3600)] )
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), transform='rate' )
    assert_equals( 1.0, interval[_time(3600)] )

    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), steps=2 )
    assert_equals( map(_time, [0,3600]), interval.keys() )
    assert_equals( 3599, interval[_time(0)] )
    assert_equals( 3600, interval[_time(3600)] )

    # with collapse
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), steps=2, collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( 7199, interval[_time(0)] )

  def test_series_joined(self):
    # put some data in the first minutes of each hour for test1, and then for
    # a few more minutes in test2
    for t in xrange(1, 120):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(3600, 3720):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(120, 240):
      self.series.insert( 'test1', t, timestamp=_time(t) )
    for t in xrange(3720, 3840):
      self.series.insert( 'test1', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250) )
    assert_equals( map(_time,[0,60,120,180,240]), interval.keys() )
    assert_equals( 2*sum(range(1,60)), interval[_time(0)] )
    assert_equals( 2*sum(range(60,120)), interval[_time(60)] )
    assert_equals( sum(range(120,180)), interval[_time(120)] )
    assert_equals( sum(range(180,240)), interval[_time(180)] )
    assert_equals( 0, interval[_time(240)] )
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250), transform='rate' )
    assert_equals( sum(range(120,180))/60.0, interval[_time(120)] )

    # no matching interval, returns no with empty value list
    interval = self.series.series( ['test1','test2'], 'minute', start=time.time(), steps=2 )
    assert_equals( 2, len(interval) )
    assert_equals( 0, interval.values()[0] )

    # with collapsed
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250), collapse=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( 2*sum(range(1,120))+sum(range(120,240)), interval[_time(0)] )

    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.series( ['test1','test2'], 'hour', end=_time(250) )
    assert_equals( 1, len(interval) )
    assert_equals( map(_time,[0,60,120,180]), interval[_time(0)].keys() )
    assert_equals( 4, len(interval[_time(0)]) )
    assert_equals( 2*sum(range(1,60)), interval[_time(0)][_time(0)] )
    assert_equals( 2*sum(range(60,120)), interval[_time(0)][_time(60)] )
    assert_equals( sum(range(120,180)), interval[_time(0)][_time(120)] )
    assert_equals( sum(range(180,240)), interval[_time(0)][_time(180)] )

    interval = self.series.series( ['test1','test2'], 'hour', end=_time(250), transform='rate' )
    assert_equals( sum(range(180,240)) / 60.0, interval[_time(0)][_time(180)] )

    # condensed
    interval = self.series.series( ['test1','test2'], 'hour', end=_time(250), condensed=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( 2*sum(range(1,120))+sum(range(120,240)), interval[_time(0)] )

    # with collapsed
    interval = self.series.series( ['test1','test2'], 'hour', condensed=True, end=_time(4200), steps=2, collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals(
      2*sum(range(1,120))+sum(range(120,240))+2*sum(range(3600,3720))+sum(range(3720,3840)),
      interval[_time(0)] )

########NEW FILE########
__FILENAME__ = gauge_helper
from helper_helper import *
from helper_helper import _time

@unittest.skipUnless( os.environ.get('TEST_GAUGE','true').lower()=='true', 'skipping gauges' )
class GaugeHelper(Chai):

  def setUp(self):
    super(GaugeHelper,self).setUp()

    self.series = Timeseries(self.client, type='gauge', prefix='kairos',
      read_func=lambda v: int(v or 0),
      intervals={
        'minute' : {
          'step' : 60,
          'steps' : 5,
        },
        'hour' : {
          'step' : 3600,
          'resolution' : 60,
        }
      } )
    self.series.delete_all()

  def tearDown(self):
    self.series.delete_all()
  
  def test_bulk_insert(self):
    inserts = {
      None      : { 'test1':[1,2,3], 'test2':[4,5,6] },
      _time(0)  : { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] },
      _time(30) : { 'test1':[1,2,3], 'test2':[4,5,6] },
      _time(60) : { 'test1':[1,2,3], 'test3':[7,8,9] }
    }
    self.series.bulk_insert( inserts )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( 3, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( 6, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( 9, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(60))
    assert_equals( 3, t1_i2[_time(60)] )

  def test_bulk_insert_intervals_after(self):
    a,b,c,d,e,f = 10,11,12,13,14,15
    inserts = OrderedDict( (
      (None     , { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(0) , { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] } ),
      (_time(30), { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(60), { 'test1':[a,b,c], 'test3':[d,e,f] })
    ) )
    self.series.bulk_insert( inserts, intervals=3 )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( 3, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( 6, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( 9, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(60))
    assert_equals( c, t1_i2[_time(60)] )

    t3_i3 = self.series.get('test3', 'minute', timestamp=_time(120))
    assert_equals( f, t3_i3[_time(120)] )

    t3_i4 = self.series.get('test3', 'minute', timestamp=_time(180))
    assert_equals( f, t3_i4[_time(180)] )

  def test_bulk_insert_intervals_before(self):
    a,b,c,d,e,f = 10,11,12,13,14,15
    inserts = OrderedDict( (
      (None     , { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(0) , { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] } ),
      (_time(30), { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(60), { 'test1':[a,b,c], 'test3':[d,e,f] })
    ) )
    self.series.bulk_insert( inserts, intervals=-3 )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( c, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( 6, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( f, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(-60))
    assert_equals( c, t1_i2[_time(-60)] )

    t3_i3 = self.series.get('test3', 'minute', timestamp=_time(-120))
    assert_equals( f, t3_i3[_time(-120)] )

    t3_i4 = self.series.get('test3', 'minute', timestamp=_time(-180))
    assert_equals( 9, t3_i4[_time(-180)] )
  
  def test_get(self):
    # 2 hours worth of data
    for t in xrange(1, 7200):
      self.series.insert( 'test', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    # middle of an interval
    interval = self.series.get( 'test', 'minute', timestamp=_time(100) )
    assert_equals( map(_time, [60]), interval.keys() )
    assert_equals( 119, interval[_time(60)] )

    # no matching interval, returns no with empty value list
    interval = self.series.get( 'test', 'minute' )
    assert_equals( 1, len(interval) )
    assert_equals( 0, interval.values()[0] )
    
    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.get( 'test', 'hour', timestamp=_time(100) )
    assert_equals( 60, len(interval) )
    assert_equals( 119, interval[_time(60)] )
    
    interval = self.series.get( 'test', 'hour', timestamp=_time(100), condensed=True )
    assert_equals( 1, len(interval) )
    assert_equals( 3599, interval[_time(0)] )
    
    interval = self.series.get( 'test', 'hour', timestamp=_time(4000), condensed=True )
    assert_equals( 1, len(interval) )
    assert_equals( 7199, interval[_time(3600)] )

  def test_get_joined(self):
    # put some data in the first minutes of each hour for test1, and then for
    # a few more minutes in test2
    for t in xrange(1, 120):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(3600, 3720):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(120, 240):
      self.series.insert( 'test1', t, timestamp=_time(t) )
    for t in xrange(3721, 3840):
      self.series.insert( 'test1', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    # interval with 2 series worth of data
    interval = self.series.get( ['test1','test2'], 'minute', timestamp=_time(100) )
    assert_equals( [_time(60)], interval.keys() )
    assert_equals( 119, interval[_time(60)] )

    # interval with 1 series worth of data
    interval = self.series.get( ['test1','test2'], 'minute', timestamp=_time(122) )
    assert_equals( [_time(120)], interval.keys() )
    assert_equals( 179, interval[_time(120)] )

    # no matching interval, returns no with empty value list
    interval = self.series.get( ['test1','test2'], 'minute' )
    assert_equals( 1, len(interval) )
    assert_equals( None, interval.values()[0] )

    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100) )
    assert_equals( map(_time,[0,60,120,180]), interval.keys() )
    assert_equals( 59, interval[_time(0)] )
    assert_equals( 119, interval[_time(60)] )
    assert_equals( 179, interval[_time(120)] )
    assert_equals( 239, interval[_time(180)] )

    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100), condensed=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( 239, interval[_time(0)] )

  def test_series(self):
    # 2 hours worth of data
    for t in xrange(1, 7200):
      self.series.insert( 'test', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    interval = self.series.series( 'test', 'minute', end=_time(250) )
    assert_equals( map(_time, [0,60,120,180,240]), interval.keys() )
    assert_equals( 59, interval[_time(0)] )
    assert_equals( 119, interval[_time(60)] )
    
    interval = self.series.series( 'test', 'minute', steps=2, end=_time(250) )
    assert_equals( map(_time, [180,240]), interval.keys() )
    assert_equals( 299, interval[_time(240)] )
    
    # with collapse
    interval = self.series.series( 'test', 'minute', end=_time(250), collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( 299, interval[_time(0)] )

    ###
    ### with resolution
    ###
    interval = self.series.series( 'test', 'hour', end=_time(250) )
    assert_equals( 1, len(interval) )
    assert_equals( 60, len(interval[_time(0)]) )
    assert_equals( 59, interval[_time(0)][_time(0)] )
    assert_equals( 119, interval[_time(0)][_time(60)] )

    # single step, last one    
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200) )
    assert_equals( 1, len(interval) )
    assert_equals( 7199, interval[_time(3600)] )

    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), steps=2 )
    assert_equals( map(_time, [0,3600]), interval.keys() )
    assert_equals( 3599, interval[_time(0)] )
    assert_equals( 7199, interval[_time(3600)] )

    # with collapse
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), steps=2, collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( 7199, interval[_time(0)] )

  def test_series_joined(self):
    # put some data in the first minutes of each hour for test1, and then for
    # a few more minutes in test2
    for t in xrange(1, 120):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(3600, 3720):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(120, 240):
      self.series.insert( 'test1', t, timestamp=_time(t) )
    for t in xrange(3720, 3840):
      self.series.insert( 'test1', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250) )
    assert_equals( map(_time,[0,60,120,180,240]), interval.keys() )
    assert_equals( 59, interval[_time(0)] )
    assert_equals( 119, interval[_time(60)] )
    assert_equals( 179, interval[_time(120)] )
    assert_equals( 239, interval[_time(180)] )
    assert_equals( None, interval[_time(240)] )

    # no matching interval, returns no with empty value list
    interval = self.series.series( ['test1','test2'], 'minute', start=time.time(), steps=2 )
    assert_equals( 2, len(interval) )
    assert_equals( None, interval.values()[0] )

    # with collapsed
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250), collapse=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( 239, interval[_time(0)] )

    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.series( ['test1','test2'], 'hour', end=_time(250) )
    assert_equals( 1, len(interval) )
    assert_equals( map(_time,[0,60,120,180]), interval[_time(0)].keys() )
    assert_equals( 4, len(interval[_time(0)]) )
    assert_equals( 59, interval[_time(0)][_time(0)] )
    assert_equals( 119, interval[_time(0)][_time(60)] )
    assert_equals( 179, interval[_time(0)][_time(120)] )
    assert_equals( 239, interval[_time(0)][_time(180)] )

    # condensed
    interval = self.series.series( ['test1','test2'], 'hour', end=_time(250), condensed=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( 239, interval[_time(0)] )

    # with collapsed
    interval = self.series.series( ['test1','test2'], 'hour', condensed=True, end=_time(4200), steps=2, collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( 3839, interval[_time(0)] )

########NEW FILE########
__FILENAME__ = gregorian_helper
from helper_helper import *
from helper_helper import _time

@unittest.skipUnless( os.environ.get('TEST_GREGORIAN','true').lower()=='true', 'skipping gregorian' )
class GregorianHelper(Chai):
  '''Test that Gregorian data is working right.'''
  def setUp(self):
    super(GregorianHelper,self).setUp()

    self.series = Timeseries(self.client, type='series', prefix='kairos',
      read_func=int, #write_func=str, 
      intervals={
        'daily' : {
          'step' : 'daily',
          'steps' : 5,
        },
        'weekly' : {
          'step' : 'weekly',
          'resolution' : 60,
        },
        'monthly' : {
          'step' : 'monthly',
        },
        'yearly' : {
          'step' : 'yearly',
        }
      } )
    self.series.delete_all()

  def tearDown(self):
    self.series.delete_all()

  def test_insert_multiple_intervals_after(self):
    ts1 = _time(0)
    ts2 = self.series._intervals['weekly']['i_calc'].normalize(ts1, 1)
    ts3 = self.series._intervals['weekly']['i_calc'].normalize(ts1, 2)
    assert_not_equals( ts1, ts2 )

    self.series.insert( 'test', 32, timestamp=ts1, intervals=1 )

    interval_1 = self.series.get( 'test', 'weekly', timestamp=ts1 )
    assert_equals( [32], interval_1[ts1] )

    interval_2 = self.series.get( 'test', 'weekly', timestamp=ts2 )
    assert_equals( [32], interval_2[ts2] )

    self.series.insert( 'test', 42, timestamp=ts1, intervals=2 )

    interval_1 = self.series.get( 'test', 'weekly', timestamp=ts1 )
    assert_equals( [32,42], interval_1[ts1] )
    interval_2 = self.series.get( 'test', 'weekly', timestamp=ts2 )
    assert_equals( [32,42], interval_2[ts2] )
    interval_3 = self.series.get( 'test', 'weekly', timestamp=ts3 )
    assert_equals( [42], interval_3[ts3] )

  def test_insert_multiple_intervals_before(self):
    ts1 = _time(0)
    ts2 = self.series._intervals['weekly']['i_calc'].normalize(ts1, -1)
    ts3 = self.series._intervals['weekly']['i_calc'].normalize(ts1, -2)
    assert_not_equals( ts1, ts2 )

    self.series.insert( 'test', 32, timestamp=ts1, intervals=-1 )

    interval_1 = self.series.get( 'test', 'weekly', timestamp=ts1 )
    assert_equals( [32], interval_1[ts1] )

    interval_2 = self.series.get( 'test', 'weekly', timestamp=ts2 )
    assert_equals( [32], interval_2[ts2] )

    self.series.insert( 'test', 42, timestamp=ts1, intervals=-2 )

    interval_1 = self.series.get( 'test', 'weekly', timestamp=ts1 )
    assert_equals( [32,42], interval_1[ts1] )
    interval_2 = self.series.get( 'test', 'weekly', timestamp=ts2 )
    assert_equals( [32,42], interval_2[ts2] )
    interval_3 = self.series.get( 'test', 'weekly', timestamp=ts3 )
    assert_equals( [42], interval_3[ts3] )

  def test_get(self):
    for day in range(0,365):
      d = datetime(year=2038, month=1, day=1) + timedelta(days=day)
      t = time.mktime( d.timetuple() )
      self.series.insert( 'test', 1, t )
    feb1 = long( time.mktime( datetime(year=2038,month=2,day=1).timetuple() ) )

    data = self.series.get('test', 'daily', timestamp=feb1)
    assert_equals( [1], data[feb1] )

    data = self.series.get('test', 'weekly', timestamp=feb1)
    assert_equals( 7, len(data) )
    assert_equals( [1], data.values()[0] )

    data = self.series.get('test', 'weekly', timestamp=feb1, condensed=True)
    assert_equals( 1, len(data) )
    assert_equals( 7*[1], data.values()[0] )

    data = self.series.get('test', 'monthly', timestamp=feb1)
    assert_equals( 28, len(data[feb1]) )

    data = self.series.get('test', 'yearly', timestamp=feb1)
    assert_equals( 365, len(data.items()[0][1]) )

  def test_series(self):
    for day in range(0,2*365):
      d = datetime(year=2038, month=1, day=1) + timedelta(days=day)
      t = time.mktime( d.timetuple() )
      self.series.insert( 'test', 1, t )

    start = long( time.mktime( datetime(year=2038,month=1,day=1).timetuple() ) )
    end = long( time.mktime( datetime(year=2038,month=12,day=31).timetuple() ) )

    data = self.series.series('test', 'daily', start=start, end=end)
    assert_equals( 365, len(data) )
    assert_equals( [1], data.values()[0] )
    assert_equals( [1], data.values()[-1] )

    data = self.series.series('test', 'weekly', start=start, end=end)
    assert_equals( 53, len(data) )
    assert_equals( 2, len(data.values()[0]) )
    assert_equals( 7, len(data.values()[1]) )
    assert_equals( 6, len(data.values()[-1]) )
    assert_equals( [1], data.values()[0].values()[0] )
    assert_equals( [1], data.values()[-1].values()[0] )

    data = self.series.series('test', 'weekly', start=start, end=end, condensed=True)
    assert_equals( 53, len(data) )
    assert_equals( 2*[1], data.values()[0] )
    assert_equals( 7*[1], data.values()[1] )
    assert_equals( 6*[1], data.values()[-1] )
    
    data = self.series.series('test', 'monthly', start=start, end=end)
    assert_equals( 12, len(data) )
    assert_equals( 31, len(data.values()[0]) ) # jan
    assert_equals( 28, len(data.values()[1]) ) # feb
    assert_equals( 30, len(data.values()[3]) ) # april
    
    data = self.series.series('test', 'yearly', start=start, end=end)
    assert_equals( 1, len(data) )
    assert_equals( 365, len(data.values()[0]) )
    
    data = self.series.series('test', 'yearly', start=start, steps=2)
    assert_equals( 2, len(data) )
    assert_equals( 365, len(data.values()[0]) )
    
    data = self.series.series('test', 'yearly', end=end, steps=2)
    assert_equals( 2, len(data) )
    assert_equals( [], data.values()[0] )
    assert_equals( 365, len(data.values()[1]) )

########NEW FILE########
__FILENAME__ = helpers
'''
Implementation of functional tests independent of backend
'''

from .api_helper import ApiHelper
from .gregorian_helper import GregorianHelper
from .series_helper import SeriesHelper
from .histogram_helper import HistogramHelper
from .count_helper import CountHelper
from .set_helper import SetHelper
from .gauge_helper import GaugeHelper
from .helper_helper import *

########NEW FILE########
__FILENAME__ = helper_helper
import os
import time
import unittest
from datetime import *

from chai import Chai

from kairos.timeseries import *

# mongo expiry requires absolute time vs. redis ttls, so adjust it in whole hours
def _time(t):
  return (500000*3600)+t


########NEW FILE########
__FILENAME__ = histogram_helper
from helper_helper import *
from helper_helper import _time

from collections import OrderedDict

@unittest.skipUnless( os.environ.get('TEST_HISTOGRAM','true').lower()=='true', 'skipping histogram' )
class HistogramHelper(Chai):

  def setUp(self):
    super(HistogramHelper,self).setUp()

    self.series = Timeseries(self.client, type='histogram', prefix='kairos',
      read_func=int,
      intervals={
        'minute' : {
          'step' : 60,
          'steps' : 5,
        },
        'hour' : {
          'step' : 3600,
          'resolution' : 60,
        }
      } )
    self.series.delete_all()

  def tearDown(self):
    self.series.delete_all()
  
  def test_bulk_insert(self):
    inserts = {
      None      : { 'test1':[1,2,3], 'test2':[4,5,6] },
      _time(0)  : { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] },
      _time(30) : { 'test1':[1,2,3], 'test2':[4,5,6] },
      _time(60) : { 'test1':[1,2,3], 'test3':[7,8,9] }
    }
    self.series.bulk_insert( inserts )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( {1:2, 2:2, 3:2}, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( {4:2, 5:2, 6:2}, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( {7:1, 8:1, 9:1}, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(60))
    assert_equals( {1:1, 2:1, 3:1}, t1_i2[_time(60)] )

  def test_bulk_insert_intervals_after(self):
    a,b,c,d,e,f = 10,11,12,13,14,15
    inserts = OrderedDict( (
      (None     , { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(0) , { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] } ),
      (_time(30), { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(60), { 'test1':[a,b,c], 'test3':[d,e,f] })
    ) )
    self.series.bulk_insert( inserts, intervals=3 )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( {1:2, 2:2, 3:2}, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( {4:2, 5:2, 6:2}, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( {7:1, 8:1, 9:1}, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(60))
    assert_equals( {1:2, 2:2, 3:2, a:1, b:1, c:1}, t1_i2[_time(60)] )

    t3_i3 = self.series.get('test3', 'minute', timestamp=_time(120))
    assert_equals( {7:1, 8:1, 9:1, d:1, e:1, f:1}, t3_i3[_time(120)] )

    t3_i4 = self.series.get('test3', 'minute', timestamp=_time(180))
    assert_equals( {7:1, 8:1, 9:1, d:1, e:1, f:1}, t3_i4[_time(180)] )

  def test_bulk_insert_intervals_before(self):
    a,b,c,d,e,f = 10,11,12,13,14,15
    inserts = OrderedDict( (
      (None     , { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(0) , { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] } ),
      (_time(30), { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(60), { 'test1':[a,b,c], 'test3':[d,e,f] })
    ) )
    self.series.bulk_insert( inserts, intervals=-3 )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( {1:2, 2:2, 3:2, a:1, b:1, c:1}, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( {4:2, 5:2, 6:2}, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( {7:1, 8:1, 9:1, d:1, e:1, f:1}, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(-60))
    assert_equals( {1:2, 2:2, 3:2, a:1, b:1, c:1}, t1_i2[_time(-60)] )

    t3_i3 = self.series.get('test3', 'minute', timestamp=_time(-120))
    assert_equals( {7:1, 8:1, 9:1, d:1, e:1, f:1}, t3_i3[_time(-120)] )

    t3_i4 = self.series.get('test3', 'minute', timestamp=_time(-180))
    assert_equals( {7:1, 8:1, 9:1}, t3_i4[_time(-180)] )

  def test_get(self):
    # 2 hours worth of data, value is same asV timestamp
    for t in xrange(1, 7200):
      self.series.insert( 'test', t/2, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    # middle of an interval
    interval = self.series.get( 'test', 'minute', timestamp=_time(100) )
    assert_equals( [_time(60)], interval.keys() )
    keys = list(range(30,60))
    assert_equals( keys, interval[_time(60)].keys() )
    for k in keys:
      assert_equals( 2, interval[_time(60)][k] )

    # no matching interval, returns no with empty value list
    interval = self.series.get( 'test', 'minute' )
    assert_equals( 1, len(interval) )
    assert_equals( 0, len(interval.values()[0]) )
    
    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.get( 'test', 'hour', timestamp=_time(100) )
    keys = list(range(30,60))
    assert_equals( 60, len(interval) )
    assert_equals( keys, interval[_time(60)].keys() )
    
    interval = self.series.get( 'test', 'hour', timestamp=_time(100), condensed=True )
    assert_equals( 1, len(interval) )
    assert_equals( list(range(0,1800)), interval[_time(0)].keys() )

  def test_get_joined(self):
    # put some data in the first minutes of each hour for test1, and then for
    # a few more minutes in test2
    for t in xrange(1, 120):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(3600, 3720):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(120, 240):
      self.series.insert( 'test1', t, timestamp=_time(t) )
    for t in xrange(3721, 3840):
      self.series.insert( 'test1', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    # interval with 2 series worth of data
    interval = self.series.get( ['test1','test2'], 'minute', timestamp=_time(100) )
    assert_equals( [_time(60)], interval.keys() )
    assert_equals( dict.fromkeys(range(60,120),2), interval[_time(60)] )

    # interval with 1 series worth of data
    interval = self.series.get( ['test1','test2'], 'minute', timestamp=_time(122) )
    assert_equals( [_time(120)], interval.keys() )
    assert_equals( dict.fromkeys(range(120,180),1), interval[_time(120)] )

    # no matching interval, returns no with empty value list
    interval = self.series.get( ['test1','test2'], 'minute' )
    assert_equals( 1, len(interval) )
    assert_equals( 0, len(interval.values()[0]) )

    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100) )
    assert_equals( map(_time,[0,60,120,180]), interval.keys() )
    assert_equals( dict.fromkeys(range(1,60), 2), interval[_time(0)] )
    assert_equals( dict.fromkeys(range(60,120), 2), interval[_time(60)] )
    assert_equals( dict.fromkeys(range(120,180), 1), interval[_time(120)] )
    assert_equals( dict.fromkeys(range(180,240), 1), interval[_time(180)] )

    data = dict.fromkeys(range(1,120), 2)
    data.update( dict.fromkeys(range(120,240),1) )
    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100), condensed=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( data, interval[_time(0)] )

    # with transforms
    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100), transform='count' )
    assert_equals( 120, interval[_time(60)] )

    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100), transform=['min','max','count'], condensed=True )
    assert_equals( {'min':1, 'max':239, 'count':358}, interval[_time(0)] )

  def test_series(self):
    # 2 hours worth of data, value is same asV timestamp
    for t in xrange(1, 7200):
      self.series.insert( 'test', t/2, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    interval = self.series.series( 'test', 'minute', end=_time(250) )
    assert_equals( map(_time, [0,60,120,180,240]), interval.keys() )
    assert_equals( list(range(0,30)), sorted(interval[_time(0)].keys()) )
    assert_equals( 1, interval[_time(0)][0] )
    for k in xrange(1,30):
      assert_equals(2, interval[_time(0)][k])
    assert_equals( list(range(120,150)), sorted(interval[_time(240)].keys()) )
    for k in xrange(120,150):
      assert_equals(2, interval[_time(240)][k])
    
    interval = self.series.series( 'test', 'minute', steps=2, end=_time(250) )
    assert_equals( map(_time, [180,240]), interval.keys() )
    assert_equals( list(range(120,150)), sorted(interval[_time(240)].keys()) )

    # with collapsed
    interval = self.series.series( 'test', 'minute', end=_time(250), collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( list(range(0,150)), sorted(interval[_time(0)].keys()) )
    for k in xrange(1,150):
      assert_equals(2, interval[_time(0)][k])
    
    ###
    ### with resolution
    ###
    interval = self.series.series( 'test', 'hour', end=_time(250) )
    assert_equals( 1, len(interval) )
    assert_equals( 60, len(interval[_time(0)]) )
    assert_equals( list(range(0,30)), sorted(interval[_time(0)][_time(0)].keys()) )

    # single step, last one    
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200) )
    assert_equals( 1, len(interval) )
    assert_equals( 1800, len(interval[_time(3600)]) )
    assert_equals( list(range(1800,3600)), sorted(interval[_time(3600)].keys()) )

    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), steps=2 )
    assert_equals( map(_time, [0,3600]), interval.keys() )
    assert_equals( 1800, len(interval[_time(0)]) )
    assert_equals( 1800, len(interval[_time(3600)]) )
    assert_equals( list(range(1800,3600)), sorted(interval[_time(3600)].keys()) )

    # with collapsed
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), steps=2, collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( 3600, len(interval[_time(0)]) )
    assert_equals( list(range(0,3600)), sorted(interval[_time(0)].keys()) )

  def test_series_joined(self):
    # put some data in the first minutes of each hour for test1, and then for
    # a few more minutes in test2
    for t in xrange(1, 120):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(3600, 3720):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(120, 240):
      self.series.insert( 'test1', t, timestamp=_time(t) )
    for t in xrange(3720, 3840):
      self.series.insert( 'test1', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250) )
    assert_equals( map(_time,[0,60,120,180,240]), interval.keys() )
    assert_equals( dict.fromkeys(range(1,60), 2), interval[_time(0)] )
    assert_equals( dict.fromkeys(range(60,120), 2), interval[_time(60)] )
    assert_equals( dict.fromkeys(range(120,180), 1), interval[_time(120)] )
    assert_equals( dict.fromkeys(range(180,240), 1), interval[_time(180)] )
    assert_equals( {}, interval[_time(240)] )

    # no matching interval, returns no with empty value list
    interval = self.series.series( ['test1','test2'], 'minute', start=time.time(), steps=2 )
    assert_equals( 2, len(interval) )
    assert_equals( {}, interval.values()[0] )

    # with transforms
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250), transform=['min','count'] )
    assert_equals( map(_time,[0,60,120,180,240]), interval.keys() )
    assert_equals( {'min':1, 'count':118}, interval[_time(0)] )
    assert_equals( {'min':60, 'count':120}, interval[_time(60)] )
    assert_equals( {'min':120, 'count':60}, interval[_time(120)] )
    assert_equals( {'min':180, 'count':60}, interval[_time(180)] )
    assert_equals( {'min':0, 'count':0}, interval[_time(240)] )

    # with collapsed
    data = dict.fromkeys(range(1,120), 2)
    data.update( dict.fromkeys(range(120,240), 1) )
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250), collapse=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( data, interval[_time(0)] )

    # with tranforms and collapsed
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250), transform=['min','max', 'count'], collapse=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( {'min':1, 'max':239, 'count':358}, interval[_time(0)] )

    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.series( ['test1','test2'], 'hour', end=_time(250) )
    assert_equals( 1, len(interval) )
    assert_equals( map(_time,[0,60,120,180]), interval[_time(0)].keys() )
    assert_equals( 4, len(interval[_time(0)]) )
    assert_equals( dict.fromkeys(range(1,60), 2), interval[_time(0)][_time(0)] )
    assert_equals( dict.fromkeys(range(60,120), 2), interval[_time(0)][_time(60)] )
    assert_equals( dict.fromkeys(range(120,180), 1), interval[_time(0)][_time(120)] )
    assert_equals( dict.fromkeys(range(180,240), 1), interval[_time(0)][_time(180)] )

    # condensed
    data = dict.fromkeys(range(1,120), 2)
    data.update( dict.fromkeys(range(120,240), 1) )
    interval = self.series.series( ['test1','test2'], 'hour', end=_time(250), condensed=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( data, interval[_time(0)] )

    # with collapsed across multiple intervals
    data = dict.fromkeys(range(1,120), 2)
    data.update( dict.fromkeys(range(120,240), 1) )
    data.update( dict.fromkeys(range(3600,3720), 2) )
    data.update( dict.fromkeys(range(3720,3840), 1) )
    interval = self.series.series( ['test1','test2'], 'hour', condensed=True, end=_time(4200), steps=2, collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( data, interval[_time(0)] )

    # with transforms collapsed
    interval = self.series.series( ['test1','test2'], 'hour', condensed=True, end=_time(4200), steps=2, collapse=True, transform=['min','max','count'] )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( {'min':1,'max':3839,'count':718}, interval[_time(0)] )

########NEW FILE########
__FILENAME__ = mongo_timeseries_test
'''
Functional tests for mongo timeseries
'''
import time
import datetime

from pymongo import *
from chai import Chai

from . import helpers
from .helpers import unittest, os, Timeseries

@unittest.skipUnless( os.environ.get('TEST_MONGO','true').lower()=='true', 'skipping mongo' )
class MongoApiTest(helpers.ApiHelper):

  def setUp(self):
    self.client = MongoClient('localhost')
    super(MongoApiTest,self).setUp()

  def test_url_parse(self):
    assert_equals( 'MongoSeries', 
      Timeseries('mongodb://localhost/kairos', type='series').__class__.__name__ )

@unittest.skipUnless( os.environ.get('TEST_MONGO','true').lower()=='true', 'skipping mongo' )
class MongoGregorianTest(helpers.GregorianHelper):

  def setUp(self):
    self.client = MongoClient('localhost')
    super(MongoGregorianTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_MONGO','true').lower()=='true', 'skipping mongo' )
class MongoSeriesTest(helpers.SeriesHelper):

  def setUp(self):
    self.client = MongoClient('localhost')
    super(MongoSeriesTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_MONGO','true').lower()=='true', 'skipping mongo' )
class MongoHistogramTest(helpers.HistogramHelper):

  def setUp(self):
    self.client = MongoClient('localhost')
    super(MongoHistogramTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_MONGO','true').lower()=='true', 'skipping mongo' )
class MongoCountTest(helpers.CountHelper):

  def setUp(self):
    self.client = MongoClient('localhost')
    super(MongoCountTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_MONGO','true').lower()=='true', 'skipping mongo' )
class MongoGaugeTest(helpers.GaugeHelper):

  def setUp(self):
    self.client = MongoClient('localhost')
    super(MongoGaugeTest,self).setUp()

########NEW FILE########
__FILENAME__ = redis_timeseries_test
'''
Functional tests for redis timeseries
'''
import time
import datetime

import redis
from chai import Chai

from . import helpers
from .helpers import unittest, os, Timeseries

@unittest.skipUnless( os.environ.get('TEST_REDIS','true').lower()=='true', 'skipping redis' )
class RedisApiTest(helpers.ApiHelper):

  def setUp(self):
    self.client = redis.Redis('localhost')
    super(RedisApiTest,self).setUp()

  def test_url_parse(self):
    assert_equals( 'RedisSeries', 
      Timeseries('redis://', type='series').__class__.__name__ )

@unittest.skipUnless( os.environ.get('TEST_REDIS','true').lower()=='true', 'skipping redis' )
class RedisGregorianTest(helpers.GregorianHelper):

  def setUp(self):
    self.client = redis.Redis('localhost')
    super(RedisGregorianTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_REDIS','true').lower()=='true', 'skipping redis' )
class RedisSeriesTest(helpers.SeriesHelper):

  def setUp(self):
    self.client = redis.Redis('localhost')
    super(RedisSeriesTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_REDIS','true').lower()=='true', 'skipping redis' )
class RedisHistogramTest(helpers.HistogramHelper):

  def setUp(self):
    self.client = redis.Redis('localhost')
    super(RedisHistogramTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_REDIS','true').lower()=='true', 'skipping redis' )
class RedisCountTest(helpers.CountHelper):

  def setUp(self):
    self.client = redis.Redis('localhost')
    super(RedisCountTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_REDIS','true').lower()=='true', 'skipping redis' )
class RedisGaugeTest(helpers.GaugeHelper):

  def setUp(self):
    self.client = redis.Redis('localhost')
    super(RedisGaugeTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_REDIS','true').lower()=='true', 'skipping redis' )
class RedisSetTest(helpers.SetHelper):

  def setUp(self):
    self.client = redis.Redis('localhost')
    super(RedisSetTest,self).setUp()

########NEW FILE########
__FILENAME__ = series_helper
from helper_helper import *
from helper_helper import _time

from collections import OrderedDict

@unittest.skipUnless( os.environ.get('TEST_SERIES','true').lower()=='true', 'skipping series' )
class SeriesHelper(Chai):

  def setUp(self):
    super(SeriesHelper,self).setUp()

    self.series = Timeseries(self.client, type='series', prefix='kairos',
      read_func=int, #write_func=str, 
      intervals={
        'minute' : {
          'step' : 60,
          'steps' : 5,
        },
        'hour' : {
          'step' : 3600,
          'resolution' : 60,
        }
      } )
    self.series.delete_all()

  def tearDown(self):
    self.series.delete_all()

  def test_bulk_insert(self):
    inserts = {
      None      : { 'test1':[1,2,3], 'test2':[4,5,6] },
      _time(0)  : { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] },
      _time(30) : { 'test1':[1,2,3], 'test2':[4,5,6] },
      _time(60) : { 'test1':[1,2,3], 'test3':[7,8,9] }
    }
    self.series.bulk_insert( inserts )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( [1,2,3,1,2,3], t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( [4,5,6,4,5,6], t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( [7,8,9], t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(60))
    assert_equals( [1,2,3], t1_i2[_time(60)] )

  def test_bulk_insert_intervals_after(self):
    a,b,c,d,e,f = 10,11,12,13,14,15
    inserts = OrderedDict( (
      (None     , { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(0) , { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] } ),
      (_time(30), { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(60), { 'test1':[a,b,c], 'test3':[d,e,f] })
    ) )
    self.series.bulk_insert( inserts, intervals=3 )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( [1,2,3,1,2,3], t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( [4,5,6,4,5,6], t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( [7,8,9], t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(60))
    assert_equals( [1,2,3,1,2,3,a,b,c], t1_i2[_time(60)] )

    t3_i3 = self.series.get('test3', 'minute', timestamp=_time(120))
    assert_equals( [7,8,9,d,e,f], t3_i3[_time(120)] )

    t3_i4 = self.series.get('test3', 'minute', timestamp=_time(180))
    assert_equals( [7,8,9,d,e,f], t3_i4[_time(180)] )

  def test_bulk_insert_intervals_before(self):
    a,b,c,d,e,f = 10,11,12,13,14,15
    inserts = OrderedDict( (
      (None     , { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(0) , { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] } ),
      (_time(30), { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(60), { 'test1':[a,b,c], 'test3':[d,e,f] })
    ) )
    self.series.bulk_insert( inserts, intervals=-3 )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( [1,2,3,1,2,3,a,b,c], t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( [4,5,6,4,5,6], t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( [7,8,9,d,e,f], t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(-60))
    assert_equals( [1,2,3,1,2,3,a,b,c], t1_i2[_time(-60)] )

    t3_i3 = self.series.get('test3', 'minute', timestamp=_time(-120))
    assert_equals( [7,8,9,d,e,f], t3_i3[_time(-120)] )

    t3_i4 = self.series.get('test3', 'minute', timestamp=_time(-180))
    assert_equals( [7,8,9], t3_i4[_time(-180)] )

  def test_insert_multiple_intervals_after(self):
    ts1 = _time(0)
    ts2 = self.series._intervals['minute']['i_calc'].normalize(ts1, 1)
    ts3 = self.series._intervals['minute']['i_calc'].normalize(ts1, 2)
    assert_not_equals( ts1, ts2 )

    self.series.insert( 'test', 32, timestamp=ts1, intervals=1 )

    interval_1 = self.series.get( 'test', 'minute', timestamp=ts1 )
    assert_equals( [32], interval_1[ts1] )

    interval_2 = self.series.get( 'test', 'minute', timestamp=ts2 )
    assert_equals( [32], interval_2[ts2] )

    self.series.insert( 'test', 42, timestamp=ts1, intervals=2 )

    interval_1 = self.series.get( 'test', 'minute', timestamp=ts1 )
    assert_equals( [32,42], interval_1[ts1] )
    interval_2 = self.series.get( 'test', 'minute', timestamp=ts2 )
    assert_equals( [32,42], interval_2[ts2] )
    interval_3 = self.series.get( 'test', 'minute', timestamp=ts3 )
    assert_equals( [42], interval_3[ts3] )

  def test_insert_multiple_intervals_before(self):
    ts1 = _time(0)
    ts2 = self.series._intervals['minute']['i_calc'].normalize(ts1, -1)
    ts3 = self.series._intervals['minute']['i_calc'].normalize(ts1, -2)
    assert_not_equals( ts1, ts2 )

    self.series.insert( 'test', 32, timestamp=ts1, intervals=-1 )

    interval_1 = self.series.get( 'test', 'minute', timestamp=ts1 )
    assert_equals( [32], interval_1[ts1] )

    interval_2 = self.series.get( 'test', 'minute', timestamp=ts2 )
    assert_equals( [32], interval_2[ts2] )

    self.series.insert( 'test', 42, timestamp=ts1, intervals=-2 )

    interval_1 = self.series.get( 'test', 'minute', timestamp=ts1 )
    assert_equals( [32,42], interval_1[ts1] )
    interval_2 = self.series.get( 'test', 'minute', timestamp=ts2 )
    assert_equals( [32,42], interval_2[ts2] )
    interval_3 = self.series.get( 'test', 'minute', timestamp=ts3 )
    assert_equals( [42], interval_3[ts3] )

  def test_get(self):
    # 2 hours worth of data, value is same asV timestamp
    for t in xrange(1, 7200):
      self.series.insert( 'test', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    # middle of an interval
    interval = self.series.get( 'test', 'minute', timestamp=_time(100) )
    assert_equals( [_time(60)], interval.keys() )
    assert_equals( list(range(60,120)), interval[_time(60)] )

    # end of an interval
    interval = self.series.get( 'test', 'minute', timestamp=_time(59) )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( list(range(1,60)), interval[_time(0)] )
    
    # no matching interval, returns no with empty value list
    interval = self.series.get( 'test', 'minute' )
    assert_equals( 1, len(interval) )
    assert_equals( 0, len(interval.values()[0]) )

    # with transforms
    interval = self.series.get( 'test', 'minute', timestamp=_time(100), transform='count' )
    assert_equals( 60, interval[_time(60)] )
    
    interval = self.series.get( 'test', 'minute', timestamp=_time(100), transform=['min','max'] )
    assert_equals( {'min':60, 'max':119}, interval[_time(60)] )
    
    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.get( 'test', 'hour', timestamp=_time(100) )
    assert_equals( 60, len(interval) )
    assert_equals( list(range(60,120)), interval[_time(60)] )
    
    interval = self.series.get( 'test', 'hour', timestamp=_time(100), condensed=True )
    assert_equals( 1, len(interval) )
    assert_equals( list(range(1,3600)), interval[_time(0)] )

    # with transforms
    interval = self.series.get( 'test', 'hour', timestamp=_time(100), transform='count' )
    assert_equals( 60, interval[_time(60)] )
    
    interval = self.series.get( 'test', 'hour', timestamp=_time(100), transform=['min','max'], condensed=True )
    assert_equals( {'min':1, 'max':3599}, interval[_time(0)] )

  def test_get_joined(self):
    # put some data in the first minutes of each hour for test1, and then for
    # a few more minutes in test2
    self.series.delete('test1')
    self.series.delete('test2')
    for t in xrange(1, 120):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(3600, 3720):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(120, 240):
      self.series.insert( 'test1', t, timestamp=_time(t) )
    for t in xrange(3721, 3840):
      self.series.insert( 'test1', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    # interval with 2 series worth of data
    interval = self.series.get( ['test1','test2'], 'minute', timestamp=_time(100) )
    assert_equals( [_time(60)], interval.keys() )
    assert_equals( list(range(60,120))+list(range(60,120)), interval[_time(60)] )

    # interval with 1 series worth of data
    interval = self.series.get( ['test1','test2'], 'minute', timestamp=_time(122) )
    assert_equals( [_time(120)], interval.keys() )
    assert_equals( list(range(120,180)), interval[_time(120)] )

    # no matching interval, returns no with empty value list
    interval = self.series.get( ['test1','test2'], 'minute' )
    assert_equals( 1, len(interval) )
    assert_equals( 0, len(interval.values()[0]) )

    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100) )
    assert_equals( map(_time,[0,60,120,180]), interval.keys() )
    assert_equals( list(range(1,60))+list(range(1,60)), interval[_time(0)] )
    assert_equals( list(range(60,120))+list(range(60,120)), interval[_time(60)] )
    assert_equals( list(range(120,180)), interval[_time(120)] )
    assert_equals( list(range(180,240)), interval[_time(180)] )

    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100), condensed=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals(
      list(range(1,60))+list(range(1,60))+list(range(60,120))+list(range(60,120))+\
      list(range(120,180))+list(range(180,240)),
      interval[_time(0)] )

    # with transforms
    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100), transform='count' )
    assert_equals( 120, interval[_time(60)] )

    interval = self.series.get( ['test1','test2'], 'hour', timestamp=_time(100), transform=['min','max','count'], condensed=True )
    assert_equals( {'min':1, 'max':239, 'count':358}, interval[_time(0)] )

  def test_series(self):
    # 2 hours worth of data, value is same asV timestamp
    for t in xrange(1, 7200):
      self.series.insert( 'test', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    interval = self.series.series( 'test', 'minute', end=_time(250) )
    assert_equals( map(_time,[0,60,120,180,240]), interval.keys() )
    assert_equals( list(range(1,60)), interval[_time(0)] )
    assert_equals( list(range(240,300)), interval[_time(240)] )
    
    interval = self.series.series( 'test', 'minute', steps=2, end=_time(250) )
    assert_equals( map(_time,[180,240]), interval.keys() )
    assert_equals( list(range(240,300)), interval[_time(240)] )

    # with transforms
    interval = self.series.series( 'test', 'minute', end=_time(250), transform=['min','count'] )
    assert_equals( map(_time,[0,60,120,180,240]), interval.keys() )
    assert_equals( {'min':1, 'count':59}, interval[_time(0)] )
    assert_equals( {'min':240, 'count':60}, interval[_time(240)] )

    # with collapsed
    interval = self.series.series( 'test', 'minute', end=_time(250), collapse=True )
    assert_equals( map(_time,[0]), interval.keys() )
    assert_equals( list(range(1,300)), interval[_time(0)] )

    # with transforms and collapsed
    interval = self.series.series( 'test', 'minute', end=_time(250), transform=['min','count'], collapse=True )
    assert_equals( map(_time,[0]), interval.keys() )
    assert_equals( {'min':1, 'count':299}, interval[_time(0)] )
    
    ###
    ### with resolution
    ###
    interval = self.series.series( 'test', 'hour', end=_time(250) )
    assert_equals( 1, len(interval) )
    assert_equals( 60, len(interval[_time(0)]) )
    assert_equals( list(range(1,60)), interval[_time(0)][_time(0)] )

    interval = self.series.series( 'test', 'hour', end=_time(250), transform=['count','max'] )
    assert_equals( 1, len(interval) )
    assert_equals( 60, len(interval[_time(0)]) )
    assert_equals( {'max':59, 'count':59}, interval[_time(0)][_time(0)] )

    # single step, last one    
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200) )
    assert_equals( 1, len(interval) )
    assert_equals( 3600, len(interval[_time(3600)]) )
    assert_equals( list(range(3600,7200)), interval[_time(3600)] )

    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), steps=2 )
    assert_equals( map(_time, [0,3600]), interval.keys() )
    assert_equals( 3599, len(interval[_time(0)]) )
    assert_equals( 3600, len(interval[_time(3600)]) )
    assert_equals( list(range(3600,7200)), interval[_time(3600)] )
    
    # with transforms
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), transform=['min','max'] )
    assert_equals( 1, len(interval) )
    assert_equals( {'min':3600, 'max':7199}, interval[_time(3600)] )

    # with collapsed
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), steps=2, collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( 7199, len(interval[_time(0)]) )
    assert_equals( list(range(1,7200)), interval[_time(0)] )

    # with transforms and collapsed
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), steps=2, collapse=True, transform=['min','count','max'] )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( {'min':1, 'max':7199, 'count':7199}, interval[_time(0)] )

  def test_series_joined(self):
    # put some data in the first minutes of each hour for test1, and then for
    # a few more minutes in test2
    self.series.delete('test1')
    self.series.delete('test2')
    for t in xrange(1, 120):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(3600, 3720):
      self.series.insert( 'test1', t, timestamp=_time(t) )
      self.series.insert( 'test2', t, timestamp=_time(t) )
    for t in xrange(120, 240):
      self.series.insert( 'test1', t, timestamp=_time(t) )
    for t in xrange(3720, 3840):
      self.series.insert( 'test1', t, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250) )
    assert_equals( map(_time,[0,60,120,180,240]), interval.keys() )
    assert_equals( list(range(1,60))+list(range(1,60)), interval[_time(0)] )
    assert_equals( list(range(60,120))+list(range(60,120)), interval[_time(60)] )
    assert_equals( list(range(120,180)), interval[_time(120)] )
    assert_equals( list(range(180,240)), interval[_time(180)] )
    assert_equals( [], interval[_time(240)] )

    # no matching interval, returns no with empty value list
    interval = self.series.series( ['test1','test2'], 'minute', start=time.time(), steps=2 )
    assert_equals( 2, len(interval) )
    assert_equals( [], interval.values()[0] )

    # with transforms
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250), transform=['min','count'] )
    assert_equals( map(_time,[0,60,120,180,240]), interval.keys() )
    assert_equals( {'min':1, 'count':118}, interval[_time(0)] )
    assert_equals( {'min':60, 'count':120}, interval[_time(60)] )
    assert_equals( {'min':120, 'count':60}, interval[_time(120)] )
    assert_equals( {'min':180, 'count':60}, interval[_time(180)] )
    assert_equals( {'min':0, 'count':0}, interval[_time(240)] )

    # with collapsed
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250), collapse=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals(
      list(range(1,60))+list(range(1,60))+list(range(60,120))+list(range(60,120))+\
      list(range(120,180))+list(range(180,240)),
      interval[_time(0)] )

    # with tranforms and collapsed
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250), transform=['min','max', 'count'], collapse=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( {'min':1, 'max':239, 'count':358}, interval[_time(0)] )

    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.series( ['test1','test2'], 'hour', end=_time(250) )
    assert_equals( 1, len(interval) )
    assert_equals( map(_time,[0,60,120,180]), interval[_time(0)].keys() )
    assert_equals( 4, len(interval[_time(0)]) )
    assert_equals( list(range(1,60))+list(range(1,60)), interval[_time(0)][_time(0)] )
    assert_equals( list(range(60,120))+list(range(60,120)), interval[_time(0)][_time(60)] )
    assert_equals( list(range(120,180)), interval[_time(0)][_time(120)] )
    assert_equals( list(range(180,240)), interval[_time(0)][_time(180)] )

    # condensed
    interval = self.series.series( ['test1','test2'], 'hour', end=_time(250), condensed=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals(
      list(range(1,60))+list(range(1,60))+list(range(60,120))+list(range(60,120))+\
      list(range(120,180))+list(range(180,240)),
      interval[_time(0)] )

    # with collapsed
    interval = self.series.series( ['test1','test2'], 'hour', condensed=True, end=_time(4200), steps=2, collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals(
      list(range(1,60))+list(range(1,60))+list(range(60,120))+list(range(60,120))+\
      list(range(120,180))+list(range(180,240))+\
      list(range(3600,3660))+list(range(3600,3660))+list(range(3660,3720))+list(range(3660,3720))+\
      list(range(3720,3780))+list(range(3780,3840)),
      interval[_time(0)] )

    # with transforms collapsed
    interval = self.series.series( ['test1','test2'], 'hour', condensed=True, end=_time(4200), steps=2, collapse=True, transform=['min','max','count'] )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( {'min':1,'max':3839,'count':718}, interval[_time(0)] )

########NEW FILE########
__FILENAME__ = set_helper
from helper_helper import *
from helper_helper import _time

@unittest.skipUnless( os.environ.get('TEST_SET','true').lower()=='true', 'skipping sets' )
class SetHelper(Chai):

  def setUp(self):
    super(SetHelper,self).setUp()

    self.series = Timeseries(self.client, type='set', prefix='kairos',
      read_func=lambda v: int(v or 0),
      intervals={
        'minute' : {
          'step' : 60,
          'steps' : 5,
        },
        'hour' : {
          'step' : 3600,
          'resolution' : 60,
        }
      } )
    self.series.delete_all()

  def tearDown(self):
    self.series.delete_all()
  
  def test_bulk_insert(self):
    inserts = {
      None      : { 'test1':[1,2,3], 'test2':[4,5,6] },
      _time(0)  : { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] },
      _time(30) : { 'test1':[1,2,3], 'test2':[4,5,6] },
      _time(60) : { 'test1':[1,2,3], 'test3':[7,8,9] }
    }
    self.series.bulk_insert( inserts )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( {1,2,3}, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( {4,5,6}, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( {7,8,9}, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(60))
    assert_equals( {1,2,3}, t1_i2[_time(60)] )

  def test_bulk_insert_intervals_after(self):
    a,b,c,d,e,f = 10,11,12,13,14,15
    inserts = OrderedDict( (
      (None     , { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(0) , { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] } ),
      (_time(30), { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(60), { 'test1':[a,b,c], 'test3':[d,e,f] })
    ) )
    self.series.bulk_insert( inserts, intervals=3 )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( {1,2,3}, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( {4,5,6}, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( {7,8,9}, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(60))
    assert_equals( {1,2,3,a,b,c}, t1_i2[_time(60)] )

    t3_i3 = self.series.get('test3', 'minute', timestamp=_time(120))
    assert_equals( {7,8,9,d,e,f}, t3_i3[_time(120)] )

    t3_i4 = self.series.get('test3', 'minute', timestamp=_time(180))
    assert_equals( {7,8,9,d,e,f}, t3_i4[_time(180)] )

  def test_bulk_insert_intervals_before(self):
    a,b,c,d,e,f = 10,11,12,13,14,15
    inserts = OrderedDict( (
      (None     , { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(0) , { 'test1':[1,2,3], 'test2':[4,5,6], 'test3':[7,8,9] } ),
      (_time(30), { 'test1':[1,2,3], 'test2':[4,5,6] } ),
      (_time(60), { 'test1':[a,b,c], 'test3':[d,e,f] })
    ) )
    self.series.bulk_insert( inserts, intervals=-3 )

    t1_i1 = self.series.get('test1', 'minute', timestamp=_time(0))
    assert_equals( {1,2,3,a,b,c}, t1_i1[_time(0)] )

    t2_i1 = self.series.get('test2', 'minute', timestamp=_time(0))
    assert_equals( {4,5,6}, t2_i1[_time(0)] )
    
    t3_i1 = self.series.get('test3', 'minute', timestamp=_time(0))
    assert_equals( {7,8,9,d,e,f}, t3_i1[_time(0)] )

    t1_i2 = self.series.get('test1', 'minute', timestamp=_time(-60))
    assert_equals( {1,2,3,a,b,c}, t1_i2[_time(-60)] )

    t3_i3 = self.series.get('test3', 'minute', timestamp=_time(-120))
    assert_equals( {7,8,9,d,e,f}, t3_i3[_time(-120)] )

    t3_i4 = self.series.get('test3', 'minute', timestamp=_time(-180))
    assert_equals( {7,8,9}, t3_i4[_time(-180)] )

  def test_get(self):
    # 2 hours worth of data. Trim some bits from data resolution to assert
    # proper set behavior
    for t in xrange(1, 7200):
      self.series.insert( 'test', t/15, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    # middle of an interval
    interval = self.series.get( 'test', 'minute', timestamp=_time(100) )
    assert_equals( map(_time, [60]), interval.keys() )
    assert_equals( set([4,5,6,7]), interval[_time(60)] )

    # no matching interval, returns no with empty value list
    interval = self.series.get( 'test', 'minute' )
    assert_equals( 1, len(interval) )
    assert_equals( set(), interval.values()[0] )

    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.get( 'test', 'hour', timestamp=_time(100) )
    assert_equals( 60, len(interval) )
    assert_equals( set([4,5,6,7]), interval[_time(60)] )

    interval = self.series.get( 'test', 'hour', timestamp=_time(100), condensed=True )
    assert_equals( 1, len(interval) )
    assert_equals( set(range(0,240)), interval[_time(0)] )

    interval = self.series.get( 'test', 'hour', timestamp=_time(4000), condensed=True )
    assert_equals( 1, len(interval) )
    assert_equals( set(range(240,480)), interval[_time(3600)] )

  def test_series(self):
    # 2 hours worth of data. Trim some bits from data resolution to assert
    # proper set behavior
    for t in xrange(1, 7200):
      self.series.insert( 'test', t/15, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    interval = self.series.series( 'test', 'minute', end=_time(250) )
    assert_equals( map(_time, [0,60,120,180,240]), interval.keys() )
    assert_equals( set([0,1,2,3]), interval[_time(0)] )
    assert_equals( set([4,5,6,7]), interval[_time(60)] )

    interval = self.series.series( 'test', 'minute', steps=2, end=_time(250) )
    assert_equals( map(_time, [180,240]), interval.keys() )
    assert_equals( set([16,17,18,19]), interval[_time(240)] )

    # with collapse
    interval = self.series.series( 'test', 'minute', end=_time(250), collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( set(range(0,20)), interval[_time(0)] )

    ###
    ### with resolution
    ###
    interval = self.series.series( 'test', 'hour', end=_time(250) )
    assert_equals( 1, len(interval) )
    assert_equals( 60, len(interval[_time(0)]) )
    assert_equals( set([0,1,2,3]), interval[_time(0)][_time(0)] )
    assert_equals( set([4,5,6,7]), interval[_time(0)][_time(60)] )

    # single step, last one
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200) )
    assert_equals( 1, len(interval) )
    assert_equals( set(range(240,480)), interval[_time(3600)] )

    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), steps=2 )
    assert_equals( map(_time, [0,3600]), interval.keys() )
    assert_equals( set(range(0,240)), interval[_time(0)] )
    assert_equals( set(range(240,480)), interval[_time(3600)] )

    # with collapse
    interval = self.series.series( 'test', 'hour', condensed=True, end=_time(4200), steps=2, collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( set(range(0,480)), interval[_time(0)] )

  def test_series_joined(self):
    # put some data in the first minutes of each hour for test1, and then for
    # a few more minutes in test2
    for t in xrange(1, 120):
      self.series.insert( 'test1', t/15, timestamp=_time(t) )
      self.series.insert( 'test2', t/15, timestamp=_time(t) )
    for t in xrange(3600, 3720):
      self.series.insert( 'test1', t/15, timestamp=_time(t) )
      self.series.insert( 'test2', t/15, timestamp=_time(t) )
    for t in xrange(120, 240):
      self.series.insert( 'test1', t/15, timestamp=_time(t) )
    for t in xrange(3720, 3840):
      self.series.insert( 'test1', t/15, timestamp=_time(t) )

    ###
    ### no resolution, condensed has no impact
    ###
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250) )
    assert_equals( map(_time,[0,60,120,180,240]), interval.keys() )
    assert_equals( set([0,1,2,3]), interval[_time(0)] )
    assert_equals( set([4,5,6,7]), interval[_time(60)] )
    assert_equals( set([8,9,10,11]), interval[_time(120)] )
    assert_equals( set([12,13,14,15]), interval[_time(180)] )
    assert_equals( set(), interval[_time(240)] )

    # no matching interval, returns no with empty value list
    interval = self.series.series( ['test1','test2'], 'minute', start=time.time(), steps=2 )
    assert_equals( 2, len(interval) )
    assert_equals( set(), interval.values()[0] )

    # with collapsed
    interval = self.series.series( ['test1','test2'], 'minute', end=_time(250), collapse=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( set(range(0,16)), interval[_time(0)] )

    ###
    ### with resolution, optionally condensed
    ###
    interval = self.series.series( ['test1','test2'], 'hour', end=_time(250) )
    assert_equals( 1, len(interval) )
    assert_equals( map(_time,[0,60,120,180]), interval[_time(0)].keys() )
    assert_equals( 4, len(interval[_time(0)]) )
    assert_equals( set([0,1,2,3]), interval[_time(0)][_time(0)] )
    assert_equals( set([4,5,6,7]), interval[_time(0)][_time(60)] )
    assert_equals( set([8,9,10,11]), interval[_time(0)][_time(120)] )
    assert_equals( set([12,13,14,15]), interval[_time(0)][_time(180)] )

    # condensed
    interval = self.series.series( ['test1','test2'], 'hour', end=_time(250), condensed=True )
    assert_equals( [_time(0)], interval.keys() )
    assert_equals( set(range(0,16)), interval[_time(0)] )

    # with collapsed
    interval = self.series.series( ['test1','test2'], 'hour', condensed=True, end=_time(4200), steps=2, collapse=True )
    assert_equals( map(_time, [0]), interval.keys() )
    assert_equals( set(range(0,16)) | set(range(240,256)), interval[_time(0)] )

########NEW FILE########
__FILENAME__ = sql_timeseries_test
'''
Functional tests for sql timeseries
'''
import time
import datetime
import os

from sqlalchemy import create_engine

from . import helpers
from .helpers import unittest, os, Timeseries

SQL_HOST = os.environ.get('SQL_HOST', 'sqlite:///:memory:')

@unittest.skipUnless( os.environ.get('TEST_SQL','true').lower()=='true', 'skipping sql' )
class SqlApiTest(helpers.ApiHelper):

  def setUp(self):
    self.client = create_engine(SQL_HOST, echo=False)
    super(SqlApiTest,self).setUp()

  def test_url_parse(self):
    assert_equals( 'SqlSeries', 
      Timeseries('sqlite:///:memory:', type='series').__class__.__name__ )

  def test_expire(self):
    cur_time = time.time()
    self.series.insert( 'test', 1, timestamp=cur_time-600 )
    self.series.insert( 'test', 2, timestamp=cur_time-60 )
    self.series.insert( 'test', 3, timestamp=cur_time )

    kwargs = {
      'condense':True,
      'collapse':True,
      'start':cur_time-600,
      'end':cur_time
    }
    assert_equals( [1,2,3], self.series.series('test', 'minute', **kwargs).values()[0] )
    assert_equals( [1,2,3], self.series.series('test', 'hour', **kwargs).values()[0] )
    self.series.expire('test')
    assert_equals( [2,3], self.series.series('test', 'minute', **kwargs).values()[0] )
    assert_equals( [1,2,3], self.series.series('test', 'hour', **kwargs).values()[0] )

    self.series.delete('test')

@unittest.skipUnless( os.environ.get('TEST_SQL','true').lower()=='true', 'skipping sql' )
class SqlGregorianTest(helpers.GregorianHelper):

  def setUp(self):
    self.client = create_engine(SQL_HOST, echo=False)
    super(SqlGregorianTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_SQL','true').lower()=='true', 'skipping sql' )
class SqlSeriesTest(helpers.SeriesHelper):

  def setUp(self):
    self.client = create_engine(SQL_HOST, echo=False)
    super(SqlSeriesTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_SQL','true').lower()=='true', 'skipping sql' )
class SqlHistogramTest(helpers.HistogramHelper):

  def setUp(self):
    self.client = create_engine(SQL_HOST, echo=False)
    super(SqlHistogramTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_SQL','true').lower()=='true', 'skipping sql' )
class SqlCountTest(helpers.CountHelper):

  def setUp(self):
    self.client = create_engine(SQL_HOST, echo=False)
    super(SqlCountTest,self).setUp()

@unittest.skipUnless( os.environ.get('TEST_SQL','true').lower()=='true', 'skipping sql' )
class SqlGaugeTest(helpers.GaugeHelper):

  def setUp(self):
    self.client = create_engine(SQL_HOST, echo=False)
    super(SqlGaugeTest,self).setUp()

########NEW FILE########
__FILENAME__ = cassandra_timeseries_test
'''
Functional tests for cassandra timeseries
'''
from Queue import Queue, Empty, Full

import cql
from chai import Chai

from kairos.cassandra_backend import *

class CassandraTest(Chai):

  def setUp(self):
    super(CassandraTest,self).setUp()
    self.series = CassandraSeries.__new__(CassandraSeries, 'client')

  def test_init(self):
    client = mock()
    client.cql_major_version = 3

    attrs = ['host', 'port', 'keyspace', 'cql_version', 'compression',
      'consistency_level', 'transport', 'credentials']
    for attr in attrs:
      setattr(client, attr, attr.encode('hex'))
    
    # Trap the stuff about setting things up
    with expect( client.cursor ).returns(mock()) as c:
      expect( c.execute )
      expect( c.close )

    self.series.__init__(client)
    assert_equals( 'float', self.series._value_type )
    assert_equals( 'series', self.series._table )

    # connection pooling
    for attr in attrs:
      assert_equals( getattr(client,attr), getattr(self.series,'_'+attr) )
    assert_equals( 1, self.series._pool.qsize() )
    assert_equals( 0, self.series._pool.maxsize )
    assert_equals( client, self.series._pool.get() )

  def test_init_when_invalid_cql_version(self):
    client = mock()
    client.cql_major_version = 2
    with assert_raises( TypeError ):
      self.series.__init__(client)

  def test_init_handles_value_type(self):
    client = mock()
    client.cql_major_version = 3
    # Trap the stuff about setting things up
    with expect( client.cursor ).returns(mock()) as c:
      expect( c.execute )
      expect( c.close )
    
    self.series.__init__(client, value_type=bool)
    assert_equals( 'boolean', self.series._value_type )
    self.series.__init__(client, value_type='double')
    assert_equals( 'double', self.series._value_type )

    with assert_raises( TypeError ):
      self.series.__init__(client, value_type=object())

  def test_init_handles_table_name(self):
    client = mock()
    client.cql_major_version = 3
    # Trap the stuff about setting things up
    with expect( client.cursor ).returns(mock()) as c:
      expect( c.execute )
      expect( c.close )

    self.series.__init__(client, table_name='round')
    assert_equals( 'round', self.series._table )

  def test_init_sets_pool_size(self):
    client = mock()
    client.cql_major_version = 3
    # Trap the stuff about setting things up
    with expect( client.cursor ).returns(mock()) as c:
      expect( c.execute )
      expect( c.close )

    self.series.__init__(client, pool_size=20)
    assert_equals( 20, self.series._pool.maxsize )

  def test_connection_from_pool(self):
    self.series._pool = Queue()
    self.series._pool.put('conn')
    assert_equals( 'conn', self.series._connection() )
    assert_equals( 0, self.series._pool.qsize() )

  def test_connection_when_pool_is_empty(self):
    self.series._pool = Queue(2)
    self.series._host = 'dotcom'
    self.series._port = 'call'
    self.series._keyspace = 'gatekeeper'
    self.series._cql_version = '3.2.1'
    self.series._compression = 'smaller'
    self.series._consistency_level = 'most'
    self.series._transport = 'thrifty'
    self.series._credentials = {'user':'you', 'password':'knockknock'}

    expect( cql, 'connect' ).args( 'dotcom', 'call', 'gatekeeper',
      user='you', password='knockknock', cql_version='3.2.1',
      compression='smaller', consistency_level='most', 
      transport='thrifty' ).returns( 'conn' )

    assert_equals( 'conn', self.series._connection() )

  def test_return_when_pool_not_full(self):
    self.series._pool = Queue(1)
    assert_equals( 0, self.series._pool.qsize() )
    self.series._return( 'conn' )
    assert_equals( 1, self.series._pool.qsize() )

  def test_return_when_pool_full(self):
    self.series._pool = Queue(2)
    self.series._return( 'a' )
    self.series._return( 'b' )
    self.series._return( 'c' )
    assert_equals( 2, self.series._pool.qsize() )
    assert_equals( 'a', self.series._pool.get() )
    assert_equals( 'b', self.series._pool.get() )

########NEW FILE########
__FILENAME__ = timeseries_test
'''
Functional tests for timeseries core
'''
import time
from datetime import datetime

from kairos.timeseries import *
from chai import Chai

class UrlTest(Chai):
  def test_bad_url(self):
    with assert_raises(ImportError):
      Timeseries("noop://foo/bar")

class RelativeTimeTest(Chai):

  def test_step_size(self):
    DAY = 60*60*24
    rt = RelativeTime( DAY )
    assert_equals( DAY, rt.step_size() )
    assert_equals( DAY, rt.step_size(0, 0) )

    assert_equals( DAY, rt.step_size(0, 0) )
    assert_equals( DAY, rt.step_size(0, DAY/2) )
    assert_equals( DAY, rt.step_size(0, DAY-1) )
    assert_equals( 2*DAY, rt.step_size(0, DAY) )
    assert_equals( 2*DAY, rt.step_size(0, DAY+(60*60*1)) )
    assert_equals( 3*DAY, rt.step_size(0, 2*DAY+1) )
    assert_equals( 2*DAY, rt.step_size(DAY+1, 2*DAY) )

  def test_ttl(self):
    DAY = 60*60*24
    rt = RelativeTime( DAY )
    assert_equals( 3*DAY, rt.ttl( 3 ) )
    assert_equals( 3*DAY, rt.ttl( 3, relative_time=time.time() ) )
    assert_equals( 4*DAY, rt.ttl( 3, relative_time=time.time()+DAY ) )
    assert_equals( 8*DAY, rt.ttl( 3, relative_time=time.time()+(5*DAY) ) )
    assert_equals( 2*DAY, rt.ttl( 3, relative_time=time.time()-DAY ) )
    assert_equals( DAY, rt.ttl( 3, relative_time=time.time()-2*DAY ) )
    assert_equals( 0, rt.ttl( 3, relative_time=time.time()-3*DAY ) )

class GregorianTimeTest(Chai):

  def test_buckets(self):
    gt = GregorianTime( 'daily' )
    buckets = gt.buckets( 0, 60*60*24*42 )
    assert_equals( buckets[:3], [19700101, 19700102, 19700103] )
    assert_equals( buckets[-3:], [19700209, 19700210, 19700211] )

    gt = GregorianTime( 'weekly' )
    buckets = gt.buckets( 0, 60*60*24*25 )
    assert_equals( buckets, [197000, 197001, 197002, 197003] )

    gt = GregorianTime( 'monthly' )
    buckets = gt.buckets( 0, 60*60*24*70 )
    assert_equals( buckets, [197001, 197002, 197003] )

    gt = GregorianTime( 'yearly' )
    buckets = gt.buckets( 0, 60*60*24*800 )
    assert_equals( buckets, [1970, 1971, 1972] )

  def test_step_size(self):
    DAY = 60*60*24
    gtd = GregorianTime( 'daily' )
    gtm = GregorianTime( 'monthly' )
    gty = GregorianTime( 'yearly' )

    # leap year
    t0 = time.mktime( datetime(year=2012, month=1, day=1).timetuple() )
    t1 = time.mktime( datetime(year=2012, month=1, day=5).timetuple() )
    t2 = time.mktime( datetime(year=2012, month=2, day=13).timetuple() )
    t3 = time.mktime( datetime(year=2012, month=2, day=29).timetuple() )
    t4 = time.mktime( datetime(year=2012, month=3, day=5).timetuple() )

    assert_equals( DAY, gtd.step_size(t0) )
    assert_equals( 31*DAY, gtm.step_size(t0) )
    assert_equals( 366*DAY, gty.step_size(t0) )

    assert_equals( DAY, gtd.step_size(t2) )
    assert_equals( 31*DAY, gtm.step_size(t0, t1) )
    assert_equals( 60*DAY, gtm.step_size(t1, t2) )
    assert_equals( 29*DAY, gtm.step_size(t2, t3) )
    assert_equals( 91*DAY, gtm.step_size(t1, t4) )
    assert_equals( 60*DAY, gtm.step_size(t2, t4) )

    # not-leap year
    t0 = time.mktime( datetime(year=2013, month=1, day=1).timetuple() )
    t1 = time.mktime( datetime(year=2013, month=1, day=5).timetuple() )
    t2 = time.mktime( datetime(year=2013, month=2, day=13).timetuple() )
    t3 = time.mktime( datetime(year=2013, month=2, day=28).timetuple() )
    t4 = time.mktime( datetime(year=2013, month=3, day=5).timetuple() )

    assert_equals( DAY, gtd.step_size(t0) )
    assert_equals( 31*DAY, gtm.step_size(t0) )
    assert_equals( 365*DAY, gty.step_size(t0) )

    assert_equals( DAY, gtd.step_size(t2) )
    assert_equals( 31*DAY, gtm.step_size(t0, t1) )
    assert_equals( 59*DAY, gtm.step_size(t1, t2) )
    assert_equals( 28*DAY, gtm.step_size(t2, t3) )
    assert_equals( 90*DAY, gtm.step_size(t1, t4) )
    assert_equals( 59*DAY, gtm.step_size(t2, t4) )

  def test_ttl(self):
    DAY = 60*60*24
    gt = GregorianTime( 'daily' )
    assert_equals( 3*DAY, gt.ttl( 3 ) )
    assert_equals( 3*DAY, gt.ttl( 3, relative_time=time.time() ) )
    assert_equals( 4*DAY, gt.ttl( 3, relative_time=time.time()+DAY ) )
    assert_equals( 8*DAY, gt.ttl( 3, relative_time=time.time()+(5*DAY) ) )
    assert_equals( 2*DAY, gt.ttl( 3, relative_time=time.time()-DAY ) )
    assert_equals( DAY, gt.ttl( 3, relative_time=time.time()-2*DAY ) )
    assert_equals( 0, gt.ttl( 3, relative_time=time.time()-3*DAY ) )

########NEW FILE########
