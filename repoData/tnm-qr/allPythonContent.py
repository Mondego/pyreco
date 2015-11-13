__FILENAME__ = qr
"""
QR | Redis-Based Data Structures in Python
"""

__author__ = 'Ted Nyman'
__version__ = '0.6.0'
__license__ = 'MIT'

import redis
import logging

try:
    import json
except ImportError:
    import simplejson as json

# This is a complete nod to hotqueue -- this is one of the
# things that they did right. Natively pickling and unpiclking
# objects is pretty useful.
try:
    import cPickle as pickle
except ImportError:
    import pickle

class NullHandler(logging.Handler):
    """A logging handler that discards all logging records"""
    def emit(self, record):
        pass

# Clients can add handlers if they are interested.
log = logging.getLogger('qr')
log.addHandler(NullHandler())

# A dictionary of connection pools, based on the parameters used
# when connecting. This is so we don't have an unwieldy number of
# connections
connectionPools = {}

def getRedis(**kwargs):
    """
    Match up the provided kwargs with an existing connection pool.
    In cases where you may want a lot of queues, the redis library will
    by default open at least one connection for each. This uses redis'
    connection pool mechanism to keep the number of open file descriptors
    tractable.
    """
    key = ':'.join((repr(key) + '=>' + repr(value)) for key, value in kwargs.items())
    try:
        return redis.Redis(connection_pool=connectionPools[key])
    except KeyError:
        cp = redis.ConnectionPool(**kwargs)
        connectionPools[key] = cp
        return redis.Redis(connection_pool=cp)

class worker(object):
    def __init__(self, q, err=None, *args, **kwargs):
        self.q = q
        self.err = err
        self.args = args
        self.kwargs = kwargs
    
    def __call__(self, f):
        def wrapped():
            while True:
                # Blocking pop
                next = self.q.pop(block=True)
                if not next:
                    continue
                try:
                    # Try to execute the user's callback.
                    f(next, *self.args, **self.kwargs)
                except Exception as e:
                    try:
                        # Failing that, let's call the user's
                        # err-back, which we should keep from
                        # ever throwing an exception
                        self.err(e, *args, **kwargs)
                    except:
                        pass
        return wrapped
        
class BaseQueue(object):
    """Base functionality common to queues"""
    @staticmethod
    def all(t, pattern, **kwargs):
        r = getRedis(**kwargs)
        return [t(k, **kwargs) for k in r.keys(pattern)]
    
    def __init__(self, key, **kwargs):
        self.serializer = pickle
        self.redis = getRedis(**kwargs)
        self.key = key
    
    def __len__(self):
        """Return the length of the queue"""
        return self.redis.llen(self.key)
    
    def __getitem__(self, val):
        """Get a slice or a particular index."""
        try:
            return [self._unpack(i) for i in self.redis.lrange(self.key, val.start, val.stop - 1)]
        except AttributeError:
            return self._unpack(self.redis.lindex(self.key, val))
        except Exception as e:
            log.error('Get item failed ** %s' % repr(e))
            return None
    
    def _pack(self, val):
        """Prepares a message to go into Redis"""
        return self.serializer.dumps(val, 1)
    
    def _unpack(self, val):
        """Unpacks a message stored in Redis"""
        try:
            return self.serializer.loads(val)
        except TypeError:
            return None
    
    def dump(self, fobj):
        """Destructively dump the contents of the queue into fp"""
        next = self.redis.rpop(self.key)
        while next:
            fobj.write(next)
            next = self.redis.rpop(self.key)
    
    def load(self, fobj):
        """Load the contents of the provided fobj into the queue"""
        try:
            while True:
                self.redis.lpush(self.key, self._pack(self.serializer.load(fobj)))
        except:
            return
    
    def dumpfname(self, fname, truncate=False):
        """Destructively dump the contents of the queue into fname"""
        if truncate:
            with file(fname, 'w+') as f:
                self.dump(f)
        else:
            with file(fname, 'a+') as f:
                self.dump(f)
    
    def loadfname(self, fname):
        """Load the contents of the contents of fname into the queue"""
        with file(fname) as f:
            self.load(f)
    
    def extend(self, vals):
        """Extends the elements in the queue."""
        with self.redis.pipeline(transaction=False) as pipe:
            for val in vals:
                pipe.lpush(self.key, self._pack(val))
            pipe.execute()
    
    def peek(self):
        """Look at the next item in the queue"""
        return self[-1]

    def elements(self):
        """Return all elements as a Python list"""
        return [self._unpack(o) for o in self.redis.lrange(self.key, 0, -1)]
    
    def elements_as_json(self):
        """Return all elements as JSON object"""
        return json.dumps(self.elements)
    
    def clear(self):
        """Removes all the elements in the queue"""
        self.redis.delete(self.key)

class Deque(BaseQueue):
    """Implements a double-ended queue"""
    
    @staticmethod
    def all(pattern='*', **kwargs):
        return BaseQueue.all(Deque, pattern, **kwargs)

    def push_back(self, element):
        """Push an element to the back of the deque"""
        self.redis.lpush(self.key, self._pack(element))
        log.debug('Pushed ** %s ** for key ** %s **' % (element, self.key))
        
    def push_front(self, element):
        """Push an element to the front of the deque"""
        key = self.key
        push_it = self.redis.rpush(key, self._pack(element))
        log.debug('Pushed ** %s ** for key ** %s **' % (element, self.key))

    def pop_front(self):
        """Pop an element from the front of the deque"""
        popped = self.redis.rpop(self.key)
        log.debug('Popped ** %s ** from key ** %s **' % (popped, self.key))
        return self._unpack(popped )

    def pop_back(self):
        """Pop an element from the back of the deque"""
        popped = self.redis.lpop(self.key)
        log.debug('Popped ** %s ** from key ** %s **' % (popped, self.key))
        return self._unpack(popped)

class Queue(BaseQueue): 
    """Implements a FIFO queue"""

    @staticmethod
    def all(pattern='*', **kwargs):
        return BaseQueue.all(Queue, pattern, **kwargs)
    
    def push(self, element):
        """Push an element"""
        self.redis.lpush(self.key, self._pack(element))
        log.debug('Pushed ** %s ** for key ** %s **' % (element, self.key))

    def pop(self, block=False):
        """Pop an element"""
        if not block:
            popped = self.redis.rpop(self.key)
        else:
            queue, popped = self.redis.brpop(self.key)
        log.debug('Popped ** %s ** from key ** %s **' % (popped, self.key))
        return self._unpack(popped)
    
class PriorityQueue(BaseQueue):
    """A priority queue"""
    def __len__(self):
        """Return the length of the queue"""
        return self.redis.zcard(self.key)
    
    def __getitem__(self, val):
        """Get a slice or a particular index."""
        try:
            return [self._unpack(i) for i in self.redis.zrange(self.key, val.start, val.stop - 1)]
        except AttributeError:
            val = self.redis.zrange(self.key, val, val)
            if val:
                return self._unpack(val[0])
            return None
        except Exception as e:
            log.error('Get item failed ** %s' % repr(e))
            return None
    
    def dump(self, fobj):
        """Destructively dump the contents of the queue into fp"""
        next = self.pop()
        while next:
            self.serializer.dump(next[0], fobj)
            next = self.pop()
    
    def load(self, fobj):
        """Load the contents of the provided fobj into the queue"""
        try:
            while True:
                value, score = self.serializer.load(fobj)
                self.redis.zadd(self.key, value, score)
        except Exception as e:
            return
    
    def dumpfname(self, fname, truncate=False):
        """Destructively dump the contents of the queue into fname"""
        if truncate:
            with file(fname, 'w+') as f:
                self.dump(f)
        else:
            with file(fname, 'a+') as f:
                self.dump(f)
    
    def loadfname(self, fname):
        """Load the contents of the contents of fname into the queue"""
        with file(fname) as f:
            self.load(f)
    
    def extend(self, vals):
        """Extends the elements in the queue."""
        with self.redis.pipeline(transaction=False) as pipe:
            for val, score in vals:
                pipe.zadd(self.key, self._pack(val), score)
            return pipe.execute()

    def peek(self, withscores=False):
        """Look at the next item in the queue"""
        val = self.redis.zrange(self.key, 0, 0, withscores=True)
        if val:
            value, score = val[0]
            value = self._unpack(value)
            if withscores:
                return (value, score)
            return value
        elif withscores:
            return (None, 0.0)
        return None

    def elements(self):
        """Return all elements as a Python list"""
        return [self._unpack(o) for o in self.redis.zrange(self.key, 0, -1)]

    def pop(self, withscores=False):
        """Get the element with the lowest score, and pop it off"""
        with self.redis.pipeline() as pipe:
            o = pipe.zrange(self.key, 0, 0, withscores=True)
            o = pipe.zremrangebyrank(self.key, 0, 0)
            results, count = pipe.execute()
            if results:
                value, score = results[0]
                value = self._unpack(value)
                if withscores:
                    return (value, score)
                return value
            elif withscores:
                return (None, 0.0)
            return None
    
    def push(self, value, score):
        '''Add an element with a given score'''
        return self.redis.zadd(self.key, self._pack(value), score)

class CappedCollection(BaseQueue):
    """
    Implements a capped collection (the collection never
    gets larger than the specified size).
    """
    
    @staticmethod
    def all(pattern='*', **kwargs):
        return BaseQueue.all(CappedCollection, pattern, **kwargs)

    def __init__(self, key, size, **kwargs):
        BaseQueue.__init__(self, key, **kwargs)
        self.size = size

    def push(self, element):
        size = self.size
        with self.redis.pipeline() as pipe:
            # ltrim is zero-indexed 
            pipe = pipe.lpush(self.key, self._pack(element)).ltrim(self.key, 0, size-1)
            pipe.execute()

    def extend(self, vals):
        """Extends the elements in the queue."""
        with self.redis.pipeline() as pipe:
            for val in vals:
                pipe.lpush(self.key, self._pack(val))
            pipe.ltrim(self.key, 0, self.size-1)
            pipe.execute()

    def pop(self, block=False):
        if not block:
            popped = self.redis.rpop(self.key)
        else:
            queue, popped = self.redis.brpop(self.key)
        log.debug('Popped ** %s ** from key ** %s **' % (popped, self.key))
        return self._unpack(popped)

class Stack(BaseQueue):
    """Implements a LIFO stack""" 

    @staticmethod
    def all(pattern='*', **kwargs):
        return BaseQueue.all(Stack, pattern, **kwargs)
    
    def push(self, element):
        """Push an element"""
        self.redis.lpush(self.key, self._pack(element))
        log.debug('Pushed ** %s ** for key ** %s **' % (element, self.key))
         
    def pop(self, block=False):
        """Pop an element"""
        if not block:
            popped = self.redis.lpop(self.key)
        else:
            queue, popped = self.redis.blpop(self.key)
        log.debug('Popped ** %s ** from key ** %s **' % (popped, self.key))
        return self._unpack(popped)

########NEW FILE########
__FILENAME__ = tests
import os
import qr
import redis
import unittest

r = redis.Redis()

class Queue(unittest.TestCase):
    def setUp(self):
        r.delete('qrtestqueue')
        self.q = qr.Queue(key='qrtestqueue')
        self.assertEquals(len(self.q), 0)

    def test_roundtrip(self):
        q = self.q
        q.push('foo')
        self.assertEquals(len(q), 1)
        self.assertEquals(q.pop(), 'foo')
        self.assertEquals(len(q), 0)

    def test_order(self):
        q = self.q
        q.push('foo')
        q.push('bar')
        self.assertEquals(q.pop(), 'foo')
        self.assertEquals(q.pop(), 'bar')

    def test_order_mixed(self):
        q = self.q
        q.push('foo')
        self.assertEquals(q.pop(), 'foo')
        q.push('bar')
        self.assertEquals(q.pop(), 'bar')

    def test_len(self):
        count = 100
        for i in range(count):
            self.assertEquals(len(self.q), i)
            self.q.push(i)
        for i in range(count):
            self.assertEquals(len(self.q), count - i)
            self.q.pop()
        self.q.clear()

    def test_get_item(self):
        count = 100
        items = [i for i in range(count)]
        self.q.clear()
        self.q.extend(items)
        items.reverse()
        # Get single values
        for i in range(count):
            self.assertEquals(self.q[i], items[i])
        # Get small ranges
        for i in range(count-1):
            self.assertEquals(self.q[i:i+1], items[i:i+1])
        # Now get the whole range
        self.assertEquals(self.q[0:-1], items[0:-1])
        self.q.clear()
    
    def test_extend(self):
        '''Test extending a queue, including with a generator'''
        count = 100
        self.q.extend(i for i in range(count))
        self.assertEquals(len(self.q), count)
        self.q.clear()
        
        self.q.extend([i for i in range(count)])
        self.assertEquals(len(self.q), count)
        self.q.clear()
        
        self.q.extend(range(count))
        self.assertEquals(self.q.elements(), [count - i - 1 for i in range(count)])
        self.q.clear()
            
    def test_pack_unpack(self):
        '''Make sure that it behaves like python-object-in, python-object-out'''
        count = 100
        self.q.extend({'key': i} for i in range(count))
        next = self.q.pop()
        while next:
            self.assertTrue(isinstance(next, dict))
            next = self.q.pop()
    
    def test_dump_load(self):
        # Get a temporary file to dump a queue to that file
        count = 100
        self.q.extend(range(count))
        self.assertEquals(self.q.elements(), [count - i - 1for i in range(count)])
        with os.tmpfile() as f:
            self.q.dump(f)
            # Now, assert that it is empty
            self.assertEquals(len(self.q), 0)
            # Now, try to load it back in
            f.seek(0)
            self.q.load(f)
            self.assertEquals(len(self.q), count)
            self.assertEquals(self.q.elements(), [count - i - 1 for i in range(count)])
            # Now clean up after myself
            f.truncate()
            self.q.clear()
    
class CappedCollection(unittest.TestCase):
    def setUp(self):
        r.delete('qrtestcc')
        self.aq = qr.CappedCollection(key='qrtestcc', size=3)
        self.assertEquals(len(self.aq), 0)

    def test_roundtrip(self):
        aq = self.aq
        aq.push('foo')
        self.assertEquals(len(aq), 1)
        self.assertEquals(aq.pop(), 'foo')
        self.assertEquals(len(aq), 0)

    def test_order(self):
        aq = self.aq
        aq.push('foo')
        aq.push('bar')
        self.assertEquals(aq.pop(), 'foo')
        self.assertEquals(aq.pop(), 'bar')

    def test_order_mixed(self):
        aq = self.aq
        aq.push('foo')
        self.assertEquals(aq.pop(), 'foo')
        aq.push('bar')
        self.assertEquals(aq.pop(), 'bar')

    def test_limit(self):
        aq = self.aq
        aq.push('a')
        aq.push('b')
        aq.push('c')
        self.assertEquals(len(aq), 3)
        aq.push('d')
        aq.push('e')
        self.assertEquals(len(aq), 3)
        self.assertEquals(aq.pop(), 'c')
        self.assertEquals(aq.pop(), 'd')
        self.assertEquals(aq.pop(), 'e')
        self.assertEquals(len(aq), 0)

    def test_extend(self):
        '''Test extending a queue, including with a generator'''
        count = 100
        self.aq.extend(i for i in range(count))
        self.assertEquals(len(self.aq), self.aq.size)
        self.aq.clear()

class Stack(unittest.TestCase):
    def setUp(self):
        r.delete('qrteststack')
        self.stack = qr.Stack(key='qrteststack')

    def test_roundtrip(self):
        stack = self.stack
        stack.push('foo')
        self.assertEquals(len(stack), 1)
        self.assertEquals(stack.pop(), 'foo')
        self.assertEquals(len(stack), 0)

    def test_order(self):
        stack = self.stack
        stack.push('foo')
        stack.push('bar')
        self.assertEquals(stack.pop(), 'bar')
        self.assertEquals(stack.pop(), 'foo')

    def test_order_mixed(self):
        stack = self.stack
        stack.push('foo')
        self.assertEquals(stack.pop(), 'foo')
        stack.push('bar')
        self.assertEquals(stack.pop(), 'bar')

    def test_get_item(self):
        count = 100
        items = [i for i in range(count)]
        self.stack.extend(items)
        items.reverse()
        # Get single values
        for i in range(count):
            self.assertEquals(self.stack[i], items[i])
        # Get small ranges
        for i in range(count-1):
            self.assertEquals(self.stack[i:i+2], items[i:i+2])
        # Now get the whole range
        self.assertEquals(self.stack[0:-1], items[0:-1])
        self.stack.clear()

    def test_extend(self):
        '''Test extending a queue, including with a generator'''
        count = 100
        self.stack.extend(i for i in range(count))
        self.assertEquals(self.stack.elements(), [count - i - 1 for i in range(count)])
        
        # Also, make sure it's still a stack. It should be in reverse order
        last = self.stack.pop()
        while last != None:
            now = self.stack.pop()
            self.assertTrue(last > now)
            last = now
        self.stack.clear()

    def test_dump_load(self):
        # Get a temporary file to dump a queue to that file
        count = 100
        self.stack.extend(range(count))
        self.assertEquals(self.stack.elements(), [count - i - 1 for i in range(count)])
        with os.tmpfile() as f:
            self.stack.dump(f)
            # Now, assert that it is empty
            self.assertEquals(len(self.stack), 0)
            # Now, try to load it back in
            f.seek(0)
            self.stack.load(f)
            self.assertEquals(len(self.stack), count)
            self.assertEquals(self.stack.elements(), [count - i - 1 for i in range(count)])
            # Now clean up after myself
            f.truncate()
            self.stack.clear()

class PriorityQueue(unittest.TestCase):
    def setUp(self):
        r.delete('qrpriorityqueue')
        self.q = qr.PriorityQueue(key='qrpriorityqueue')

    def test_roundtrip(self):
        self.q.push('foo', 1)
        self.assertEquals(len(self.q), 1)
        self.assertEquals(self.q.pop(), 'foo')
        self.assertEquals(len(self.q), 0)

    def test_order(self):
        self.q.push('foo', 1)
        self.q.push('bar', 0)
        self.assertEquals(self.q.pop(), 'bar')
        self.assertEquals(self.q.pop(), 'foo')

    def test_get_item(self):
        count = 100
        items = [i for i in range(count)]
        self.q.extend(zip(items, items))
        # Get single values
        for i in range(count):
            self.assertEquals(self.q[i], items[i])
        # Get small ranges
        for i in range(count-1):
            self.assertEquals(self.q[i:i+2], items[i:i+2])
        # Now get the whole range
        self.assertEquals(self.q[0:-1], items[0:-1])
        self.q.clear()

    def test_extend(self):
        '''Test extending a queue, including with a generator'''
        count = 100
        items = [i for i in range(count)]
        self.q.extend(zip(items, items))
        self.assertEquals(self.q.elements(), items)
        self.q.clear()

    def test_pop(self):
        '''Test whether or not we can get real values with pop'''
        count = 100
        items = [i for i in range(count)]
        self.q.extend(zip(items, items))
        next = self.q.pop()
        while next:
            self.assertTrue(isinstance(next, int))
            next = self.q.pop()
        # Now we'll pop with getting the scores as well
        items = [i for i in range(count)]
        self.q.extend(zip(items, items))
        value, score = self.q.pop(withscores=True)
        while value:
            self.assertTrue(isinstance(value, int))
            self.assertTrue(isinstance(score, float))
            value, score = self.q.pop(withscores=True)
        
    def test_push(self):
        '''Test whether we can push well'''
        count = 100
        for i in range(count):
            self.q.push(i, count - i)
        value, score = self.q.pop(withscores=True)
        while value:
            self.assertEqual(value + score, count)
            value, score = self.q.pop(withscores=True)
        
    def test_uniqueness(self):
        count = 100
        # Push the same value on with different scores
        for i in range(count):
            self.q.push(1, i)
        self.assertEquals(len(self.q), 1)
        self.q.clear()
    
    def test_dump_load(self):
        # Get a temporary file to dump a queue to that file
        count = 100
        items = [i for i in range(count)]
        self.q.extend(zip(items, items))
        self.assertEquals(self.q.elements(), items)
        with os.tmpfile() as f:
            self.q.dump(f)
            # Now, assert that it is empty
            self.assertEquals(len(self.q), 0)
            # Now, try to load it back in
            f.seek(0)
            self.q.load(f)
            self.assertEquals(len(self.q), count)
            self.assertEquals(self.q.elements(), items)
            # Now clean up after myself
            f.truncate()
            self.q.clear()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
