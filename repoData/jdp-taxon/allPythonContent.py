__FILENAME__ = backend
class Backend(object):
    def __init__(self):
        pass

    def tag_items(self, tag, *items):
        raise NotImplementedError

    def untag_items(self, tag, *items):
        raise NotImplementedError

    def remove_items(self, *items):
        raise NotImplementedError

    def all_tags(self):
        raise NotImplementedError

    def all_items(self):
        raise NotImplementedError

    def query(self, q):
        raise NotImplementedError

    def empty(self):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = memory
import operator
try:
    from collections import Counter
except ImportError:
    from ._counter import Counter

from .backend import Backend
from ..query import Query


class MemoryBackend(Backend):
    def __init__(self):
        self.empty()

    def tag_items(self, tag, *items):
        if tag not in self.tags:
            self.tags[tag] = 0
            self.tagged[tag] = set()
        new_items = set(items) - self.tagged[tag]
        if len(new_items) == 0:
            return []
        self.tags[tag] += len(new_items)
        self.tagged[tag].update(set(new_items))
        self.items += Counter(new_items)
        return list(new_items)

    def untag_items(self, tag, *items):
        old_items = set(items) & self.tagged[tag]
        if len(old_items) == 0:
            return []
        self.tags[tag] -= len(old_items)
        self.tagged[tag] -= set(old_items)
        self.items -= Counter(old_items)
        return list(old_items)

    def remove_items(self, *items):
        removed = []
        for item in set(items):
            if item not in self.items:
                continue
            for tag in self.all_tags():
                if item not in self.tagged[tag]:
                    continue
                self.tagged[tag] -= set([item])
                self.tags[tag] -= 1
                self.items[item] -= 1
            removed.append(item)
        return removed

    def all_tags(self):
        return [tag[0] for tag in self.tags.items() if tag[1] > 0]

    def all_items(self):
        return [item[0] for item in self.items.items() if item[1] > 0]

    def query(self, q):
        if isinstance(q, Query):
            fn, args = q.freeze()
            return self._raw_query(fn, args)
        elif isinstance(q, tuple):
            fn, args = q
            return self._raw_query(fn, args)
        else:
            raise ValueError

    def _raw_query(self, fn, args):
        if fn == 'tag':
            if len(args) == 1:
                return None, self.tagged.get(args[0], [])
            else:
                groups = [self.tagged.get(tag, []) for tag in args]
                return None, reduce(operator.add, groups)
        elif fn == 'and':
            results = [set(items) for _, items in [self._raw_query(*a) for a in args]]
            return None, reduce(operator.__and__, results)
        elif fn == 'or':
            results = [set(items) for _, items in [self._raw_query(*a) for a in args]]
            return None, reduce(operator.__or__, results)
        elif fn == 'not':
            results = [set(items) for _, items in [self._raw_query(*a) for a in args]]
            results.insert(0, set(self.all_items()))
            return None, reduce(operator.sub, results)
        else:
            raise ValueError

    def empty(self):
        self.tagged = dict()
        self.items = Counter()
        self.tags = Counter()

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u"%s()" % (self.__class__.__name__)

########NEW FILE########
__FILENAME__ = redis
import hashlib
try:
    import cPickle as pickle
except:
    import pickle

from functools import partial
from itertools import imap

from .backend import Backend
from ..query import Query


class RedisBackend(Backend):
    def __init__(self, redis, name):
        self._r = redis
        self._name = name
        make_key = partial(lambda *parts: ':'.join(parts), self._name)
        self.tag_key = partial(make_key, 'tag')
        self.result_key = partial(make_key, 'result')
        self.items_key = make_key('items')
        self.tags_key = make_key('tags')
        self.cache_key = make_key('cache')

    @property
    def redis(self):
        return self._r

    @property
    def name(self):
        return self._name

    def encode(self, data):
        return pickle.dumps(data)

    def decode(self, data):
        return pickle.loads(data)

    def tag_items(self, tag, *items):
        items = list(set(self.encode(item) for item in items) - self._r.smembers(self.tag_key(tag)))
        if len(items) == 0:
            return []
        with self._r.pipeline() as pipe:
            pipe.zincrby(self.tags_key, tag, len(items))
            pipe.sadd(self.tag_key(tag), *items)
            for item in items:
                pipe.zincrby(self.items_key, item, 1)
            pipe.execute()
        return map(self.decode, items)

    def untag_items(self, tag, *items):
        items = list(set(self.encode(item) for item in items) & self._r.smembers(self.tag_key(tag)))
        if len(items) == 0:
            return []
        with self._r.pipeline() as pipe:
            pipe.zincrby(self.tags_key, tag, -len(items))
            pipe.srem(self.tag_key(tag), *items)
            for item in items:
                pipe.zincrby(self.items_key, item, -1)
            pipe.execute()
        self._clear_cache()
        return map(self.decode, items)

    def remove_items(self, *items):
        removed = []
        if not len(items):
            return removed
        for item in imap(self.encode, items):
            score = self._r.zscore(self.items_key, item)
            if not score:
                continue
            for tag in self.all_tags():
                srem_ok = self._r.srem(self.tag_key(tag), item)
                if not srem_ok:
                    continue
                with self._r.pipeline() as pipe:
                    pipe.zincrby(self.tags_key, tag, -1)
                    pipe.zincrby(self.items_key, item, -1)
                    pipe.execute()
            removed.append(self.decode(item))
        self._clear_cache()
        return removed

    def all_tags(self):
        return list(self._r.zrangebyscore(self.tags_key, 1, '+inf'))

    def all_items(self):
        return map(self.decode, self._r.zrangebyscore(self.items_key, 1, '+inf'))

    def query(self, q):
        if isinstance(q, Query):
            fn, args = q.freeze()
            return self._raw_query(fn, args)
        elif isinstance(q, tuple):
            fn, args = q
            return self._raw_query(fn, args)
        else:
            raise TypeError("%s is not a recognized Taxon query" % q)

    def _raw_query(self, fn, args):
        "Perform a raw query on the Taxon instance"
        h = hashlib.sha1(pickle.dumps((fn, args)))
        keyname = self.result_key(h.hexdigest())
        if self._r.exists(keyname):
            return (keyname, map(self.decode, self._r.smembers(keyname)))

        if fn == 'tag':
            if len(args) == 1:
                key = self.tag_key(args[0])
                return (key, map(self.decode, self._r.smembers(key)))
            else:
                keys = [self.tag_key(k) for k in args]
                self._r.sunionstore(keyname, *keys)
                self._r.sadd(self.cache_key, keyname)
                return (keyname, map(self.decode, self._r.smembers(keyname)))
        elif fn == 'and':
            interkeys = [key for key, _ in [self._raw_query(*a) for a in args]]
            self._r.sinterstore(keyname, *interkeys)
            self._r.sadd(self.cache_key, keyname)
            return (keyname, map(self.decode, self._r.smembers(keyname)))
        elif fn == 'or':
            interkeys = [key for key, _ in [self._raw_query(*a) for a in args]]
            self._r.sunionstore(keyname, *interkeys)
            self._r.sadd(self.cache_key, keyname)
            return (keyname, map(self.decode, self._r.smembers(keyname)))
        elif fn == 'not':
            interkeys = [key for key, _ in [self._raw_query(*a) for a in args]]
            tags = self.all_tags()
            scratchpad_key = self.result_key('_')
            self._r.sunionstore(scratchpad_key, *map(self.tag_key, tags))
            self._r.sdiffstore(keyname, scratchpad_key, *interkeys)
            self._r.sadd(self.cache_key, keyname)
            return (keyname, map(self.decode, self._r.smembers(keyname)))
        else:
            raise ValueError("Unkown Taxon operator '%s'" % fn)

    def _clear_cache(self):
        cached_keys = self._r.smembers(self.cache_key)
        if len(cached_keys) > 0:
            self._r.delete(*cached_keys)
        return True

    def empty(self):
        self._r.flushdb()

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u"%s(%r, %r)" % (self.__class__.__name__, self.redis, self.name)

########NEW FILE########
__FILENAME__ = _counter
## {{{ http://code.activestate.com/recipes/576611/ (r11)
from operator import itemgetter
from heapq import nlargest
from itertools import repeat, ifilter


class Counter(dict):
    '''Dict subclass for counting hashable objects.  Sometimes called a bag
    or multiset.  Elements are stored as dictionary keys and their counts
    are stored as dictionary values.

    >>> Counter('zyzygy')
    Counter({'y': 3, 'z': 2, 'g': 1})

    '''

    def __init__(self, iterable=None, **kwds):
        '''Create a new, empty Counter object.  And if given, count elements
        from an input iterable.  Or, initialize the count from another mapping
        of elements to their counts.

        >>> c = Counter()                           # a new, empty counter
        >>> c = Counter('gallahad')                 # a new counter from an iterable
        >>> c = Counter({'a': 4, 'b': 2})           # a new counter from a mapping
        >>> c = Counter(a=4, b=2)                   # a new counter from keyword args

        '''        
        self.update(iterable, **kwds)

    def __missing__(self, key):
        return 0

    def most_common(self, n=None):
        '''List the n most common elements and their counts from the most
        common to the least.  If n is None, then list all element counts.

        >>> Counter('abracadabra').most_common(3)
        [('a', 5), ('r', 2), ('b', 2)]

        '''        
        if n is None:
            return sorted(self.iteritems(), key=itemgetter(1), reverse=True)
        return nlargest(n, self.iteritems(), key=itemgetter(1))

    def elements(self):
        '''Iterator over elements repeating each as many times as its count.

        >>> c = Counter('ABCABC')
        >>> sorted(c.elements())
        ['A', 'A', 'B', 'B', 'C', 'C']

        If an element's count has been set to zero or is a negative number,
        elements() will ignore it.

        '''
        for elem, count in self.iteritems():
            for _ in repeat(None, count):
                yield elem

    # Override dict methods where the meaning changes for Counter objects.

    @classmethod
    def fromkeys(cls, iterable, v=None):
        raise NotImplementedError(
            'Counter.fromkeys() is undefined.  Use Counter(iterable) instead.')

    def update(self, iterable=None, **kwds):
        '''Like dict.update() but add counts instead of replacing them.

        Source can be an iterable, a dictionary, or another Counter instance.

        >>> c = Counter('which')
        >>> c.update('witch')           # add elements from another iterable
        >>> d = Counter('watch')
        >>> c.update(d)                 # add elements from another counter
        >>> c['h']                      # four 'h' in which, witch, and watch
        4

        '''        
        if iterable is not None:
            if hasattr(iterable, 'iteritems'):
                if self:
                    self_get = self.get
                    for elem, count in iterable.iteritems():
                        self[elem] = self_get(elem, 0) + count
                else:
                    dict.update(self, iterable) # fast path when counter is empty
            else:
                self_get = self.get
                for elem in iterable:
                    self[elem] = self_get(elem, 0) + 1
        if kwds:
            self.update(kwds)

    def copy(self):
        'Like dict.copy() but returns a Counter instance instead of a dict.'
        return Counter(self)

    def __delitem__(self, elem):
        'Like dict.__delitem__() but does not raise KeyError for missing values.'
        if elem in self:
            dict.__delitem__(self, elem)

    def __repr__(self):
        if not self:
            return '%s()' % self.__class__.__name__
        items = ', '.join(map('%r: %r'.__mod__, self.most_common()))
        return '%s({%s})' % (self.__class__.__name__, items)

    # Multiset-style mathematical operations discussed in:
    #       Knuth TAOCP Volume II section 4.6.3 exercise 19
    #       and at http://en.wikipedia.org/wiki/Multiset
    #
    # Outputs guaranteed to only include positive counts.
    #
    # To strip negative and zero counts, add-in an empty counter:
    #       c += Counter()

    def __add__(self, other):
        '''Add counts from two counters.

        >>> Counter('abbb') + Counter('bcc')
        Counter({'b': 4, 'c': 2, 'a': 1})


        '''
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for elem in set(self) | set(other):
            newcount = self[elem] + other[elem]
            if newcount > 0:
                result[elem] = newcount
        return result

    def __sub__(self, other):
        ''' Subtract count, but keep only results with positive counts.

        >>> Counter('abbbc') - Counter('bccd')
        Counter({'b': 2, 'a': 1})

        '''
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for elem in set(self) | set(other):
            newcount = self[elem] - other[elem]
            if newcount > 0:
                result[elem] = newcount
        return result

    def __or__(self, other):
        '''Union is the maximum of value in either of the input counters.

        >>> Counter('abbb') | Counter('bcc')
        Counter({'b': 3, 'c': 2, 'a': 1})

        '''
        if not isinstance(other, Counter):
            return NotImplemented
        _max = max
        result = Counter()
        for elem in set(self) | set(other):
            newcount = _max(self[elem], other[elem])
            if newcount > 0:
                result[elem] = newcount
        return result

    def __and__(self, other):
        ''' Intersection is the minimum of corresponding counts.

        >>> Counter('abbb') & Counter('bcc')
        Counter({'b': 1})

        '''
        if not isinstance(other, Counter):
            return NotImplemented
        _min = min
        result = Counter()
        if len(self) < len(other):
            self, other = other, self
        for elem in ifilter(self.__contains__, other):
            newcount = _min(self[elem], other[elem])
            if newcount > 0:
                result[elem] = newcount
        return result


if __name__ == '__main__':
    import doctest
    print doctest.testmod()
## end of http://code.activestate.com/recipes/576611/ }}}

########NEW FILE########
__FILENAME__ = core
from urlparse import urlparse

from .backends import Backend, MemoryBackend, RedisBackend
from .query import Query


class Taxon(object):
    """A Taxon instance provides methods to organize and query data by tag.
    """

    def __init__(self, backend):
        """Create a new instance to access the data stored in the backend.

        >>> Taxon(MemoryBackend())
        """
        if not isinstance(backend, Backend):
            raise ValueError("%r is not a valid backend" % backend)
        self._backend = backend

    @property
    def backend(self):
        """Return the the instance of the backend being used."""
        return self._backend

    def tag(self, tag, *items):
        """Add tag ``tag`` to each element in ``items``.

        >>> t = Taxon(MemoryBackend())
        >>> t.tag('closed', 'issue-91', 'issue-105', 'issue-4')
        """
        return self.backend.tag_items(tag, *items)

    def untag(self, tag, *items):
        """Remove tag ``tag`` from each element in ``items``.

        >>> t = Taxon(MemoryBackend())
        >>> t.untag('closed', 'issue-91')
        """
        return self.backend.untag_items(tag, *items)

    def remove(self, *items):
        """Remove each element in ``items`` from the store.

        >>> t = Taxon(MemoryBackend())
        >>> t.tag('functional', 'Haskell', 'Pure', 'ML', 'C')
        >>> t.remove('C')
        """
        return self.backend.remove_items(*items)

    def tags(self):
        """Return a list of all the tags known to the store.

        >>> t = Taxon(MemoryBackend())
        >>> t.tag('water', 'Squirtle')
        >>> t.tag('fire', 'Charmander')
        >>> t.tag('grass', 'Bulbasaur')
        >>> t.tags()
        ['water', 'fire', 'grass']
        """
        return self.backend.all_tags()

    def items(self):
        """Return a list of all the items in the store.

        >>> t = Taxon(MemoryBackend())
        >>> t.tag('water', 'Squirtle')
        >>> t.tag('fire', 'Charmander')
        >>> t.tag('grass', 'Bulbasaur')
        >>> t.items()
        ['Squirtle', 'Charmander', 'Bulbasaur']
        """
        return self.backend.all_items()

    def query(self, q):
        """Perform a query and return the results and metadata.

        The first element of the tuple contains the metadata, which can be any
        value and is specific to the backend being used. The second element is
        a list of the items matching the query.

        >>> t = Taxon(MemoryBackend())
        >>> t.tag('ice', 'Dewgong', 'Articuno')
        >>> t.tag('flying', 'Articuno', 'Pidgeotto')
        >>> t.query(Tag('ice') & Tag('flying'))
        (None, ['Articuno'])
        """
        if not isinstance(q, (tuple, Query)):
            raise ValueError("%r is not a valid query" % q)
        return self.backend.query(q)

    def find(self, q):
        """Return a set of the items matching the query, ignoring metadata.

        >>> t = Taxon(MemoryBackend())
        >>> t.tag('ice', 'Dewgong', 'Articuno')
        >>> t.tag('flying', 'Articuno', 'Pidgeotto')
        >>> t.find(Tag('ice') & Tag('flying'))
        ['Articuno']
        """
        _, items = self.query(q)
        return set(items)

    def empty(self):
        """Remove all tags and items from the store.

        >>> t = Taxon(MemoryBackend())
        >>> t.tag('foo', 'bar')
        >>> t.empty()
        >>> t.tags()
        []
        >>> t.items()
        []
        """
        return self.backend.empty()

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u"%s(%r)" % (self.__class__.__name__, self.backend)


class MemoryTaxon(Taxon):
    """A utility class to quickly create a memory-backed Taxon instance."""

    def __init__(self):
        """Create a new Taxon instance with a memory backend."""
        super(MemoryTaxon, self).__init__(MemoryBackend())

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u"%s()" % (self.__class__.__name__)


class RedisTaxon(Taxon):
    """A utility class to quickly create a Redis-backed Taxon instance."""

    def __init__(self, dsn='redis://localhost', name='txn'):
        """Create a new Taxon instance with a Redis backend.

        A DSN is used to specify the Redis server to connect to. The path part
        of the DSN can be used to specify which database to select.

        >>> t = RedisTaxon('redis://localhost:6379/10')

        The name of the instance is used as a namespacing mechanism, so that
        multiple Taxon instances can use the same Redis database without
        clobbering each others' data.

        >>> t = RedisTaxon(name='my-other-blog')
        """
        self._dsn = dsn
        r = self._redis_from_dsn(self._dsn)
        super(RedisTaxon, self).__init__(RedisBackend(r, name))

    def _redis_from_dsn(self, dsn):
        """Return a Redis instance from a string DSN."""
        import redis
        parts = urlparse(dsn)
        _, _, netloc = parts.netloc.partition('@')
        netloc = netloc.rsplit(':')
        host = netloc[0]
        try:
            port = int(netloc[1])
        except IndexError:
            port = 6379
        try:
            db = int(parts.path.strip('/'))
        except ValueError:
            db = 0
        return redis.Redis(host=host, port=port, db=db)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u"%s(%r, %r)" % (self.__class__.__name__, self._dsn, self.backend.name)

########NEW FILE########
__FILENAME__ = query
__all__ = ['Query', 'Tag', 'And', 'Or', 'Not']


class Query(object):
    """
    Taxon is queried by ``tuple`` objects that represent the syntax tree of the
    query. These tuple queries can become unwieldy quickly, so the query DSL is
    provided as the main way to query Taxon.

    All subclasses of ``Query`` implement a ``freeze`` method which builds the
    tuple representation of the query.
    """

    def __init__(self, expr):
        self.expr = expr
        self.children = []

    def __and__(self, other):
        return And(self, other)

    def __or__(self, other):
        return Or(self, other)

    def __invert__(self):
        return Not(self)

    @classmethod
    def coerce(self, expr):
        "Returns the ``Query`` representation of the expression."
        if isinstance(expr, Query):
            return expr
        elif isinstance(expr, basestring):
            return Tag(expr)
        else:
            raise TypeError("Expected %s or string, got %s" % (Query.__name__, expr))

    def freeze(self):
        "Returns a hashable representation of the query expression."
        return (self.op, tuple(c.freeze() for c in self.children))


class Tag(Query):
    "Returns the items with the specified tag."
    def freeze(self):
        return ("tag", [self.expr])


class And(Query):
    "Returns the items matched by all ``Query`` expressions."

    op = "and"

    def __init__(self, *exprs):
        self.children = [Query.coerce(e) for e in exprs]


class Or(Query):
    "Returns the items matched by any or all of the ``Query`` expressions."

    op = "or"

    def __init__(self, *exprs):
        self.children = [Query.coerce(e) for e in exprs]


class Not(Query):
    "Returns the items **not** matched by any of the ``Query`` expressions."

    def __init__(self, expr):
        self.expr = Query.coerce(expr)

    def freeze(self):
        return ("not", tuple([self.expr.freeze()]))

########NEW FILE########
__FILENAME__ = context
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

from nose.tools import make_decorator

import taxon


def benchmark():
    def decorate(func):
        def newfunc(*arg, **kw):
            import time
            start = time.time()
            ret = func(*arg, **kw)
            end = time.time()
            sys.stderr.write('%s took %2fs\n' % (func.__name__, end - start))
            return ret
        newfunc = make_decorator(func)(newfunc)
        return newfunc
    return decorate

########NEW FILE########
__FILENAME__ = test_basic
from functools import partial
from nose.tools import raises, eq_, ok_
from .context import taxon, benchmark
from taxon import MemoryTaxon, RedisTaxon
from taxon.query import *

TestRedisTaxon = partial(RedisTaxon, 'redis://localhost:6379/9', 'test')


class _TestBasics(object):
    def __init__(self, taxon_cls):
        self.taxon_cls = taxon_cls

    def setup(self):
        self.t = self.taxon_cls()

    def teardown(self):
        self.t.empty()

    def test_one_item_tag(self):
        tagged = self.t.tag('foo', 'a')
        eq_(tagged, ['a'])

    def test_many_item_tag(self):
        tagged = self.t.tag('foo', 'a', 'b', 'c')
        eq_(set(tagged), set(['a', 'b', 'c']))

    def test_existing_tag(self):
        tagged = self.t.tag('bar', 'x')
        eq_(tagged, ['x'])
        tagged = self.t.tag('bar', 'x', 'y')
        eq_(tagged, ['y'])
        tagged = self.t.tag('bar', 'x')
        eq_(tagged, [])

    def test_all_tags(self):
        self.t.tag('foo', 'x', 'y')
        self.t.tag('bar', 'y', 'z')
        eq_(set(self.t.tags()), set(['foo', 'bar']))

    def test_all_items(self):
        self.t.tag('foo', 'x', 'y')
        self.t.tag('bar', 'y', 'z')
        eq_(set(self.t.items()), set(['x', 'y', 'z']))

    def test_remove_tag(self):
        self.t.tag('bar', 'x', 'y')
        untagged = self.t.untag('bar', 'x')
        eq_(untagged, ['x'])
        untagged = self.t.untag('bar', 'x')
        eq_(untagged, [])

    def test_remove_item(self):
        self.t.tag('bar', 'x', 'y')
        self.t.tag('foo', 'x', 'z')
        removed = self.t.remove('x')
        eq_(removed, ['x'])
        removed = self.t.remove('y')
        eq_(removed, ['y'])
        removed = self.t.remove('w')
        eq_(removed, [])

    def test_item_tag_sync(self):
        self.t.tag('bar', 'x', 'y')
        self.t.tag('foo', 'x', 'z')
        removed = self.t.remove('x')
        eq_(removed, ['x'])
        removed = self.t.remove('y')
        eq_(removed, ['y'])
        removed = self.t.remove('w')
        eq_(removed, [])
        eq_(self.t.tags(), ['foo'])
        eq_(self.t.items(), ['z'])


class TestMemoryBasics(_TestBasics):
    def __init__(self):
        super(TestMemoryBasics, self).__init__(MemoryTaxon)


class TestRedisBasics(_TestBasics):
    def __init__(self):
        super(TestRedisBasics, self).__init__(TestRedisTaxon)

    def setup(self):
        super(TestRedisBasics, self).setup()
        if self.t.backend.redis.dbsize() > 0:
            raise RuntimeError("Redis database is not empty")

    def teardown(self):
        super(TestRedisBasics, self).teardown()
        self.t.backend.redis.flushdb()

########NEW FILE########
__FILENAME__ = test_query
from functools import partial
from os.path import dirname
from nose.tools import raises, eq_, ok_
from .context import taxon, benchmark
from taxon import MemoryTaxon, RedisTaxon
from taxon.query import *

TestRedisTaxon = partial(RedisTaxon, 'redis://localhost:6379/9', 'test')


class _TestBackend(object):
    def __init__(self, taxon_cls):
        self.taxon_cls = taxon_cls

    def setup(self):
        self.t = self.taxon_cls()
        for line in open(dirname(__file__) + '/fixtures/pokemon_types.csv'):
            line = line.strip()
            if not line:
                continue
            tokens = line.split()
            pokemon, types = tokens[0], tokens[1:]
            for t in types:
                self.t.tag(t, pokemon)

    def teardown(self):
        self.t.empty()

    def test_all_tags(self):
        tags = self.t.tags()
        ok_(len(tags) > 0)
        eq_(len(tags), 17)

    def test_all_items(self):
        items = self.t.items()
        ok_(len(items) > 0)
        eq_(len(items), 649)

    def test_find_tag(self):
        # Find all water-type pokemon
        water = self.t.find(Tag('water'))
        ok_(len(water) > 0)
        eq_(len(water), 111)

    def test_find_and(self):
        # Find all grass/poison dual types
        results = self.t.find(And('grass', 'poison'))
        ok_(len(results) > 0)
        eq_(len(results), 14)

    def test_find_or(self):
        # Find all that are either grass or poison (or both)
        results = self.t.find(Or('grass', 'poison'))
        ok_(len(results) > 0)
        eq_(len(results), 119)

    def test_find_not(self):
        # Find all that are not fire-type
        results = self.t.find(Not('fire'))
        ok_(len(results) > 0)
        eq_(len(results), 599)

    def test_find_complex(self):
        # Find all that are flying that are also fire or water type
        results = self.t.find(And('flying', Or('fire', 'water')))
        ok_(len(results) > 0)
        eq_(len(results), 11)

    def test_find_all(self):
        tags = self.t.tags()
        # Find all items by providing every tag
        results = self.t.find(Or(*tags))
        eq_(len(results), len(self.t.items()))
        eq_(set(results), set(self.t.items()))
        # Find all items through union of all tags
        results = self.t.find(reduce(Or, tags))
        eq_(len(results), len(self.t.items()))
        eq_(set(results), set(self.t.items()))

    @raises(TypeError)
    def test_find_invalid(self):
        self.t.find(Tag('water') & 5)


class TestMemoryBackend(_TestBackend):
    def __init__(self):
        super(TestMemoryBackend, self).__init__(MemoryTaxon)


class TestRedisBackend(_TestBackend):
    def __init__(self):
        super(TestRedisBackend, self).__init__(TestRedisTaxon)

    def setup(self):
        t = self.taxon_cls()
        if t.backend.redis.dbsize() > 0:
            raise RuntimeError("Redis database is not empty")
        super(TestRedisBackend, self).setup()

    def teardown(self):
        super(TestRedisBackend, self).teardown()
        self.t.backend.redis.flushdb()

########NEW FILE########
