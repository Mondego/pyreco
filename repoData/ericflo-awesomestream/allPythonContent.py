__FILENAME__ = backends
import collections
import datetime
import simplejson
import uuid

from awesomestream.utils import all_combinations, permutations
from awesomestream.utils import coerce_ts, coerce_dt

class BaseBackend(object):
    def __init__(self, keys=None):
        self.keys = keys or []
    
    def insert(self, data, date=None):
        raise NotImplementedError
    
    def keys_from_keydict(self, keydict):
        if not keydict:
            yield '_all'
            raise StopIteration
        idx_key_parts = sorted(keydict.keys())
        # Make sure all values are lists
        values = []
        for k in idx_key_parts:
            value = keydict[k]
            if not isinstance(value, (list, tuple)):
                value = [value]
            values.append([unicode(v).encode('utf-8') for v in value])
        for value_permutation in permutations(values):
            yield '-'.join(idx_key_parts + value_permutation)
    
    def indexes_from_data(self, data):
        # Maintain all of the other indices
        for key_list in all_combinations(self.keys):
            add_key, keydict = True, {}
            for k in key_list:
                value = data.get(k)
                if value is None:
                    add_key = False
                    break
                else:
                    keydict[k] = value
            if add_key:
                for k in self.keys_from_keydict(keydict):
                    yield k
    
    def serialize(self, data):
        if data is None:
            return None
        return simplejson.dumps(data)
    
    def deserialize(self, data):
        if data is None:
            return None
        return simplejson.loads(data)


class MemoryBackend(BaseBackend):
    def __init__(self, keys=None):
        super(MemoryBackend, self).__init__(keys=keys)
        self._items = {}
        self._indices = collections.defaultdict(lambda: [])
    
    def insert(self, data, date=None):
        key = str(uuid.uuid1())
        
        self._items[key] = self.serialize(data)
        
        t = coerce_ts(date)
        
        # Insert into the global index
        self._indices['_all'].insert(0, (t, key))
        
        # Maintain the other indices
        for idx_key in self.indexes_from_data(data):
            self._indices[idx_key].insert(0, (t, key))
        
        return key
    
    def _get_many(self, keys):
        return map(self.deserialize, map(self._items.get, keys))
    
    def items(self, start=0, end=20, **kwargs):
        # Get the list of keys to search
        idx_keys = list(self.keys_from_keydict(kwargs))
        # If there's only one key to look through, we're in luck and we can
        # just return it properly
        if len(idx_keys) == 1:
            keys = self._indices[idx_keys[0]][start:end]
            return self._get_many((k[1] for k in keys))
        # Otherwise, we need to pull in more data and do more work in-process
        else:
            keys = []
            seen = set()
            for key in idx_keys:
                for subkey in self._indices[key][0:end]:
                    # For every key in every index that we haven't seen yet,
                    # add it and note that we've seen it.
                    if subkey[1] not in seen:
                        keys.append(subkey)
                        seen.add(subkey[1])
            # Sort the full list of keys by the timestamp
            keys.sort(key=lambda x: x[0], reverse=True)
            # Take the slice of keys that we want (start:end) and get the
            # appropriate objects, discarding the timestamp
            return self._get_many((k[1] for k in keys[start:end]))


class RedisBackend(BaseBackend):
    def __init__(self, keys=None, host=None, port=None, db=9):
        super(RedisBackend, self).__init__(keys=keys)
        from redis import Redis
        self.client = Redis(host=host, port=port, db=db)
    
    def insert(self, data, date=None):
        key = str(uuid.uuid1())
        
        self.client.set(key, self.serialize(data))
        
        serialized_key = self.serialize((coerce_ts(date), key))
        
        # Insert into the global index
        self.client.push('_all', serialized_key, head=True)
        
        # Maintain the other indices
        for idx_key in self.indexes_from_data(data):
            self.client.push(idx_key, serialized_key, head=True)
    
    def _get_many(self, keys):
        return map(self.deserialize, self.client.mget(*keys))
    
    def items(self, start=0, end=20, **kwargs):
        # Get the list of keys to search
        idx_keys = list(self.keys_from_keydict(kwargs))
        # If there's only one key to look through, we're in luck and we can
        # just return it properly
        if len(idx_keys) == 1:
            keys = map(self.deserialize,
                self.client.lrange(idx_keys[0], start, end))
            return self._get_many((k[1] for k in keys))
        # Otherwise, we need to pull in more data and do more work in-process
        else:
            keys = []
            seen = set()
            for key in idx_keys:
                subkeys = map(self.deserialize, self.client.lrange(key, 0, end))
                for subkey in subkeys:
                    # For every key in every index that we haven't seen yet,
                    # add it and note that we've seen it.
                    if subkey[1] not in seen:
                        keys.append(subkey)
                        seen.add(subkey[1])
            # Sort the full list of keys by the timestamp
            keys.sort(key=lambda x: x[0], reverse=True)
            # Take the slice of keys that we want (start:end) and get the
            # appropriate objects, discarding the timestamp
            return self._get_many((k[1] for k in keys[start:end]))


class SQLBackend(BaseBackend):
    def __init__(self, dsn=None, keys=None, table_name='stream_items', **kwargs):
        super(SQLBackend, self).__init__(keys=keys)
        from sqlalchemy import create_engine
        self.table_name = table_name
        self.engine = create_engine(dsn, **kwargs)
        self.setup_table()
    
    def setup_table(self):
        from sqlalchemy import MetaData, Table, Column, String, Text, DateTime
        index_columns = []
        for k in self.keys:
            index_columns.append(Column(k, Text, index=True))
        self.metadata = MetaData()
        self.metadata.bind = self.engine
        self.table = Table(self.table_name, self.metadata,
            Column('key', String(length=36), primary_key=True),
            Column('data', Text, nullable=False),
            Column('date', DateTime, default=datetime.datetime.now, index=True,
                nullable=False),
            *index_columns
        )
        self.table.create(bind=self.engine, checkfirst=True)
    
    def insert(self, data, date=None):
        key = str(uuid.uuid1())
        dct = {
            'key': key,
            'data': self.serialize(data),
            'date': coerce_dt(date),
        }
        for k in self.keys:
            value = data.get(k)
            if value is not None:
                value = unicode(value).encode('utf-8')
            dct[k] = value
        self.table.insert().execute(**dct)
    
    def items(self, start=0, end=20, **kwargs):
        query = self.table.select()
        for key, value in kwargs.iteritems():
            if isinstance(value, list):
                values = [unicode(v).encode('utf-8') for v in value]
                query = query.where(getattr(self.table.c, key).in_(values))
            else:
                value = unicode(value).encode('utf-8')
                query = query.where(getattr(self.table.c, key)==value)
        query = query.offset(start).limit(end-start).order_by(
            self.table.c.date.desc())
        result = query.execute()
        return [self.deserialize(row['data']) for row in result]
########NEW FILE########
__FILENAME__ = jsonrpc
import sys
import traceback

from uuid import uuid1

from urlparse import urlparse
from httplib import HTTPConnection

from simplejson import dumps, loads

from werkzeug import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest

def create_app(backend):
    @Request.application
    def application(request):
        try:
            # Parse the JSON in the request
            try:
                data = loads(request.stream.read())
            except ValueError:
                raise BadRequest()
            # Grab the function to execute
            try:
                method = getattr(backend, data['method'])
            except (KeyError, IndexError):
                raise BadRequest()
            if method is None:
                raise NotFound()
            # Get the args and kwargs
            args = data.get('args', [])
            kwargs = data.get('kwargs', {})
            kwargs = dict(((k.encode('utf-8'), v) for k, v in kwargs.iteritems()))
            # Attempt to call the method with the params, or catch the
            # exception and pass that back to the client
            try:
                response = Response(dumps({
                    'id': data.get('id'),
                    'result': method(*args, **kwargs),
                    'error': None,
                }))
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, e:
                print e
                response = Response(dumps({
                    'id': data.get('id'),
                    'result': None,
                    'error': ''.join(traceback.format_exception(*sys.exc_info())),
                }))
            # Finish up and return the response
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Length'] = len(response.data)
            response.status_code = 200
            return response
        except HTTPException, e:
            # If an http exception is caught we can return it as response
            # because those exceptions render standard error messages when
            # called as wsgi application.
            return e
    return application

def run_server(app, port, numthreads=10):
    from cherrypy import wsgiserver
    server = wsgiserver.CherryPyWSGIServer(('0.0.0.0', port), app,
        numthreads=numthreads)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()

class Client(object):
    def __init__(self, server):
        self.server = server
        url_parts = urlparse(server)
        self.port = url_parts.port
        self.host, _, _ = url_parts.netloc.partition(':')
        self.headers = {'Content-Type': 'application/json'}

    def __getattr__(self, obj):
        return self._request(obj)

    def _request(self, method):
        def _inner(*args, **kwargs):
            data = dumps({
                'id': str(uuid1()),
                'method': method,
                'args': args,
                'kwargs': kwargs,
            })
            conn = HTTPConnection(self.host, self.port)
            conn.request('POST', '/', data, self.headers)
            response = conn.getresponse().read()
            decoded_response = loads(response)
            conn.close()
            error = decoded_response.get('error')
            if error is not None:
                raise ValueError(error)
            return decoded_response.get('result')
        return _inner
########NEW FILE########
__FILENAME__ = repl
import code
import sys

from awesomestream.jsonrpc import Client

def main():
    try:
        host = sys.argv[1]
    except IndexError:
        host = 'http://localhost:9997/'
    banner = """>>> from awesomestream.jsonrpc import Client
>>> c = Client('%s')""" % (host,)
    c = Client(host)
    code.interact(banner, local={'Client': Client, 'c': c})

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = utils
import time
import datetime

def coerce_ts(value=None):
    '''
    Given a variety of inputs, this function will return the proper
    timestamp (a float).  If None or no value is given, then it will
    return the current timestamp.
    '''
    if value is None:
        return time.time()
    if isinstance(value, int):
        value = float(value)
    if isinstance(value, datetime.timedelta):
        value = datetime.datetime.now() + value
    if isinstance(value, datetime.date):
        value = datetime.datetime(year=value.year, month=value.month,
            day=value.day)
    if isinstance(value, datetime.datetime):
        value = float(time.mktime(value.timetuple()) * 1e6)
    return value

def coerce_dt(value=None):
    '''
    Given a variety of inputs, this function will return the proper
    ``datetime.datetime`` instance.  If None or no value is given, then
    it will return ``datetime.datetime.now()``.
    '''
    if value is None:
        return datetime.datetime.now()
    if isinstance(value, int):
        value = float(value)
    if isinstance(value, float):
        return datetime.datetime.fromtimestamp(value)
    if isinstance(value, datetime.date):
        return datetime.datetime(year=value.year, month=value.month,
            day=value.day)
    if isinstance(value, datetime.timedelta):
        value = datetime.datetime.now() + value
    return value

# TODO: The following are not the proper function names. Should figure out
#       exactly what we want to call these so that it's less ambiguous to
#       someone new to the code.

def combinations(iterable, r):
    pool = tuple(iterable)
    n = len(pool)
    if r > n:
        return
    indices = range(r)
    yield tuple(pool[i] for i in indices)
    while True:
        for i in reversed(range(r)):
            if indices[i] != i + n - r:
                break
        else:
            return
        indices[i] += 1
        for j in range(i+1, r):
            indices[j] = indices[j-1] + 1
        yield tuple(pool[i] for i in indices)

def all_combinations(iterable):
    for r in range(1, len(iterable) + 1):
        for item in combinations(iterable, r):
            yield item

def permutations(lst):
    current = [-1] + ([0] * (len(lst) - 1))
    maxes = [len(item) - 1 for item in lst]
    while 1:
        for i, (c, m) in enumerate(zip(current, maxes)):
            if i > 0:
                current[i - 1] = 0
            if c < m:
                current[i] = c + 1
                break
        yield [lst[i][idx] for i, idx in enumerate(current)]
        if current == maxes:
            raise StopIteration
########NEW FILE########
__FILENAME__ = basic_client
import os
import sys

# Munge the path a bit to make this work from directly within the examples dir
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))

from awesomestream.jsonrpc import Client
from pprint import pprint

if __name__ == '__main__':
    c = Client('http://127.0.0.1:9997/')
    items = [
        {'kind': 'play', 'user': 1, 'game': 'bloons'},
        {'kind': 'play', 'user': 1, 'game': 'ryokan'},
        {'kind': 'high-score', 'user': 1, 'game': 'ryokan', 'score': 10},
        {'kind': 'high-score', 'user': 2, 'game': 'ryokan', 'score': 20},
    ]
    # First we insert some data
    for item in items:
        c.insert(item)
    # Now we query it back
    print ">>> c.items()"
    pprint(c.items())
    print ">>> c.items(kind='play')"
    pprint(c.items(kind='play'))
    print ">>> c.items(user=1)"
    pprint(c.items(user=1))
    print ">>> c.items(user=2)"
    pprint(c.items(user=2))
    print ">>> c.items(user=1, kind='play')"
    pprint(c.items(user=1, kind='play'))
    print ">>> c.items(user=1, kind='high-score')"
    pprint(c.items(user=1, kind='high-score'))
    print ">>> c.items(user=[1, 2], kind='high-score')"
    pprint(c.items(user=[1, 2], kind='high-score'))
    print ">>> c.items(user=[1, 2], kind=['high-score', 'play'])"
    pprint(c.items(user=[1, 2], kind=['high-score', 'play']))

########NEW FILE########
__FILENAME__ = memory_server
import os
import sys

# Munge the path a bit to make this work from directly within the examples dir
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))

from awesomestream.backends import MemoryBackend
from awesomestream.jsonrpc import create_app, run_server

if __name__ == '__main__':
    backend = MemoryBackend(keys=['kind', 'user', 'game'])
    app = create_app(backend)
    run_server(app, 9997)
########NEW FILE########
__FILENAME__ = redis_server
import os
import sys

# Munge the path a bit to make this work from directly within the examples dir
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))

from awesomestream.backends import RedisBackend
from awesomestream.jsonrpc import create_app, run_server

if __name__ == '__main__':
    backend = RedisBackend(
        keys=['kind', 'user', 'game'],
        host='127.0.0.1',
        port=6379
    )
    app = create_app(backend)
    run_server(app, 9997)
########NEW FILE########
__FILENAME__ = sqlite_server
import os
import sys

# Munge the path a bit to make this work from directly within the examples dir
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))

from awesomestream.backends import SQLBackend
from awesomestream.jsonrpc import create_app, run_server

if __name__ == '__main__':
    backend = SQLBackend(
        dsn='sqlite:////tmp/stream.db',
        keys=['kind', 'user', 'game'],
    )
    app = create_app(backend)
    run_server(app, 9997)
########NEW FILE########
__FILENAME__ = test_backend
import unittest

from awesomestream.backends import MemoryBackend

class MemoryBackendTest(unittest.TestCase):
    def setUp(self):
        self.backend = MemoryBackend(keys=['kind', 'user', 'game'])
    
    def test_basic(self):
        items = [
            {'kind': 'play', 'user': 1, 'game': 'bloons'},
            {'kind': 'play', 'user': 1, 'game': 'ryokan'},
            {'kind': 'high-score', 'user': 1, 'game': 'ryokan', 'score': 10},
            {'kind': 'high-score', 'user': 2, 'game': 'ryokan', 'score': 20},
        ]
        # First we insert some data
        for item in items:
            self.backend.insert(item)
        # Now we assert that it comes back properly in different queries
        self.assertEqual(self.backend.items(), list(reversed(items)))
        self.assertEqual(self.backend.items(kind='play'), [items[1], items[0]])
        self.assertEqual(self.backend.items(user=1),
            [items[2], items[1], items[0]])
        self.assertEqual(self.backend.items(user=2), [items[3]])
        self.assertEqual(self.backend.items(user=1, kind='play'),
            [items[1], items[0]])
        self.assertEqual(self.backend.items(user=1, kind='high-score'),
            [items[2]])
        self.assertEqual(self.backend.items(user=[1, 2]), list(reversed(items)))

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_utils
import unittest

from awesomestream.utils import permutations

class PermutationsTest(unittest.TestCase):
    def test_multiple_permutations(self):
        vals = [[1, 2, 3], [4, 5], [6, 7]]
        self.assertEqual(
            list(permutations(vals)),
            [
                [1, 4, 6],
                [2, 4, 6],
                [3, 4, 6],
                [1, 5, 6],
                [2, 5, 6],
                [3, 5, 6],
                [1, 4, 7],
                [2, 4, 7],
                [3, 4, 7],
                [1, 5, 7],
                [2, 5, 7],
                [3, 5, 7],
            ]
        )
    
    def test_single_permutation(self):
        vals = [['asdf']]
        self.assertEqual(list(permutations(vals)), [['asdf']])
    
    def test_double_permutation(self):
        vals = [['1', '2']]
        self.assertEqual(list(permutations(vals)), [['1'], ['2']])
########NEW FILE########
