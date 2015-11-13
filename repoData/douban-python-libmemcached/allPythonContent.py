__FILENAME__ = benchmark
#!/usr/bin/env python

import time
import random
import sys


options = None
total_time = None

def run_test(func, name):
    sys.stdout.write(name + ': ')
    sys.stdout.flush()
    start_time = time.time()
    try:
        func()
    except:
        print "failed or not supported"
        global options
        if options.verbose:
            import traceback; traceback.print_exc()
    else:
        end_time = time.time()
        global total_time
        total_time += end_time - start_time
        print "%f seconds" % (end_time - start_time)


class BigObject(object):
    def __init__(self, letter='1', size=10000):
        self.object = letter * size

    def __eq__(self, other):
        return self.object == other.object


class Benchmark(object):
    def __init__(self, module, options):
        self.module = module
        self.options = options
        self.init_server()
        self.test_set()
        self.test_set_get()
        self.test_random_get()
        self.test_set_same()
        self.test_set_big_object()
        self.test_set_get_big_object()
        self.test_set_big_string()
        self.test_set_get_big_string()
        self.test_get()
        self.test_get_big_object()
        self.test_get_multi()
        self.test_get_list()

    def init_server(self):
        #self.mc = self.module.Client([self.options.server_address])
        self.mc = self.module.Client(["faramir:11217"])
        self.mc.set_behavior(self.module.BEHAVIOR_BINARY_PROTOCOL, 1)
        self.mc.set('bench_key', "E" * 50)

        num_tests = self.options.num_tests
        self.keys = ['key%d' % i for i in xrange(num_tests)]
        self.values = ['value%d' % i for i in xrange(num_tests)]
        self.random_keys = ['key%d' % random.randint(0, num_tests) for i in xrange(num_tests * 3)]

    def test_set(self):
        set_ = self.mc.set
        pairs = zip(self.keys, self.values)

        def test():
            for key, value in pairs:
                set_(key, value)
        def test_loop():
            for i in range(10):
                for key, value in pairs:
                    set_(key, value)
        run_test(test, 'test_set')

        for key, value in pairs:
            self.mc.delete(key)

    def test_set_get(self):
        set_ = self.mc.set
        get_ = self.mc.get
        pairs = zip(self.keys, self.values)

        def test():
            for key, value in pairs:
                set_(key, value)
                result = get_(key)
                assert result == value
        run_test(test, 'test_set_get')

        #for key, value in pairs:
        #    self.mc.delete(key)

    def test_random_get(self):
        get_ = self.mc.get
        set_ = self.mc.set

        value = "chenyin"

        def test():
            index = 0
            for key in self.random_keys:
                result = get_(key)
                index += 1
                if(index % 5 == 0):
                    set_(key, value)
        run_test(test, 'test_random_get')

    def test_set_same(self):
        set_ = self.mc.set

        def test():
            for i in xrange(self.options.num_tests):
                set_('key', 'value')
        def test_loop():
            for i in range(10):
                for i in xrange(self.options.num_tests):
                    set_('key', 'value')
        run_test(test, 'test_set_same')

        self.mc.delete('key')

    def test_set_big_object(self):
        set_ = self.mc.set
        # libmemcached is slow to store large object, so limit the
        # number of objects here to make tests not stall.
        pairs = [('key%d' % i, BigObject()) for i in xrange(100)]

        def test():
            for key, value in pairs:
                set_(key, value)

        run_test(test, 'test_set_big_object (100 objects)')

        for key, value in pairs:
            self.mc.delete(key)

    def test_set_get_big_object(self):
        set_ = self.mc.set
        get_ = self.mc.get
        # libmemcached is slow to store large object, so limit the
        # number of objects here to make tests not stall.
        pairs = [('key%d' % i, BigObject()) for i in xrange(100)]

        def test():
            for key, value in pairs:
                set_(key, value)
                result = get_(key)
                assert result == value

        run_test(test, 'test_set_get_big_object (100 objects)')

        #for key, value in pairs:
        #    self.mc.delete(key)

    def test_set_get_big_string(self):
        set_ = self.mc.set
        get_ = self.mc.get

        # libmemcached is slow to store large object, so limit the
        # number of objects here to make tests not stall.
        pairs = [('key%d' % i, 'x' * 10000) for i in xrange(100)]

        def test():
            for key, value in pairs:
                set_(key, value)
                result = get_(key)
                assert result == value
        run_test(test, 'test_set_get_big_string (100 objects)')


    def test_set_big_string(self):
        set_ = self.mc.set

        # libmemcached is slow to store large object, so limit the
        # number of objects here to make tests not stall.
        pairs = [('key%d' % i, 'x' * 10000) for i in xrange(100)]

        def test():
            for key, value in pairs:
                set_(key, value)
        run_test(test, 'test_set_big_string (100 objects)')

        for key, value in pairs:
            self.mc.delete(key)


    def test_get(self):
        pairs = zip(self.keys, self.values)
        for key, value in pairs:
            self.mc.set(key, value)

        get = self.mc.get

        def test():
            for key, value in pairs:
                result = get(key)
                assert result == value
        run_test(test, 'test_get')

        for key, value in pairs:
            self.mc.delete(key)

    def test_get_big_object(self):
        pairs = [('bkey%d' % i, BigObject('x')) for i in xrange(100)]
        for key, value in pairs:
            self.mc.set(key, value)

        get = self.mc.get
        expected_values = [BigObject('x') for i in xrange(100)]

        def test():
            for i in xrange(100):
                result = get('bkey%d' % i)
                assert result == expected_values[i]
        run_test(test, 'test_get_big_object (100 objects)')

        for key, value in pairs:
            self.mc.delete(key)

    def test_get_multi(self):
        pairs = zip(self.keys, self.values)
        for key, value in pairs:
            self.mc.set(key, value)

        keys = self.keys
        expected_result = dict(pairs)

        def test():
            result = self.mc.get_multi(keys)
            assert result == expected_result
        run_test(test, 'test_get_multi')

        for key, value in pairs:
            self.mc.delete(key)

    def test_get_list(self):
        pairs = zip(self.keys, self.values)
        for key, value in pairs:
            self.mc.set(key, value)

        keys = self.keys
        expected_result = self.values

        def test():
            result = self.mc.get_list(keys)
            assert result == expected_result
        run_test(test, 'test_get_list')

        for key in self.keys:
            self.mc.delete(key)


def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-a', '--server-address', dest='server_address',
            default='127.0.0.1:11211',
            help="address:port of memcached [default: 127.0.0.1:11211]")
    parser.add_option('-n', '--num-tests', dest='num_tests', type='int',
            default=1000,
            help="repeat counts of each test [default: 1000]")
    parser.add_option('-v', '--verbose', dest='verbose',
            action='store_true', default=False,
            help="show traceback infomation if a test fails")
    global options
    options, args = parser.parse_args()

    global total_time
    total_time = 0

    print "Benchmarking cmemcached..."
    import cmemcached
    Benchmark(cmemcached, options)


if __name__ == '__main__':
    main()
    global total_time
    print "total_time is %f" % total_time

########NEW FILE########
__FILENAME__ = cmemcached
import os
import sys
import traceback
from zlib import compress, decompress, error as zlib_error
from cmemcached_imp import *
import cmemcached_imp
import threading

_FLAG_PICKLE = 1 << 0
_FLAG_INTEGER = 1 << 1
_FLAG_LONG = 1 << 2
_FLAG_BOOL = 1 << 3
_FLAG_COMPRESS = 1 << 4
_FLAG_MARSHAL = 1 << 5

VERSION = "0.41-greenify"


def prepare(val, comp_threshold):
    val, flag = cmemcached_imp.prepare(val)
    if comp_threshold > 0 and val and len(val) > comp_threshold:
        val = compress(val)
        flag |= _FLAG_COMPRESS
    return val, flag


def restore(val, flag):
    if val is None:
        return val

    if flag & _FLAG_COMPRESS:
        try:
            val = decompress(val)
        except zlib_error:
            return None
        flag &= ~_FLAG_COMPRESS

    return cmemcached_imp.restore(val, flag)


class ThreadUnsafe(Exception):
    pass


class Client(cmemcached_imp.Client):

    "a wraper around cmemcached_imp"

    def __init__(self, servers, do_split=1, comp_threshold=0, behaviors={}, logger=None, cas_support=False, *a, **kw):
        cmemcached_imp.Client.__init__(self, logger)
        self.servers = servers
        self.do_split = do_split
        self.comp_threshold = comp_threshold
        self.behaviors = dict(behaviors.items())
        self.add_server(servers)

        self.set_behavior(BEHAVIOR_NO_BLOCK, 1)  # nonblock
        self.set_behavior(BEHAVIOR_TCP_NODELAY, 1)  # nonblock
        self.set_behavior(BEHAVIOR_TCP_KEEPALIVE, 1)
        self.set_behavior(BEHAVIOR_CACHE_LOOKUPS, 1)
        # self.set_behavior(BEHAVIOR_BUFFER_REQUESTS, 0) # no request buffer

        #self.set_behavior(BEHAVIOR_KETAMA, 1)
        self.set_behavior(BEHAVIOR_HASH, HASH_MD5)
        self.set_behavior(BEHAVIOR_KETAMA_HASH, HASH_MD5)
        self.set_behavior(BEHAVIOR_DISTRIBUTION, DIST_CONSISTENT_KETAMA)
        if cas_support:
            self.set_behavior(BEHAVIOR_SUPPORT_CAS, 1)

        for k, v in behaviors.items():
            self.set_behavior(k, v)

        self._thread_ident = None
        self._created_stack = traceback.extract_stack()

    def __reduce__(self):
        return (Client, (self.servers, self.do_split, self.comp_threshold, self.behaviors))

    def set_behavior(self, k, v):
        self.behaviors[k] = v
        return cmemcached_imp.Client.set_behavior(self, k, v)

    def set(self, key, val, time=0, compress=True):
        self._record_thread_ident()
        self._check_thread_ident()
        comp = compress and self.comp_threshold or 0
        val, flag = prepare(val, comp)
        if val is not None:
            return self.set_raw(key, val, time, flag)
        else:
            print >>sys.stderr, '[cmemcached]', 'serialize %s failed' % key

    def set_multi(self, values, time=0, compress=True, return_failure=False):
        self._record_thread_ident()
        self._check_thread_ident()
        comp = compress and self.comp_threshold or 0
        raw_values = dict((k, prepare(v, comp)) for k, v in values.iteritems())
        return self.set_multi_raw(raw_values, time, return_failure=return_failure)

    def get(self, key):
        self._record_thread_ident()
        val, flag = cmemcached_imp.Client.get_raw(self, key)
        return restore(val, flag)

    def get_multi(self, keys):
        self._record_thread_ident()
        result = cmemcached_imp.Client.get_multi_raw(self, keys)
        return dict((k, restore(v, flag))
                    for k, (v, flag) in result.iteritems())

    def gets(self, key):
        self._record_thread_ident()
        val, flag, cas = cmemcached_imp.Client.gets_raw(self, key)
        return restore(val, flag), cas

    def get_list(self, keys):
        self._record_thread_ident()
        result = self.get_multi(keys)
        return [result.get(key) for key in keys]

    def expire(self, key):
        self._record_thread_ident()
        return self.touch(key, -1)

    def reset(self):
        self.clear_thread_ident()

    def clear_thread_ident(self):
        self._thread_ident = None
        self._thread_ident_stack = None

    def _record_thread_ident(self):
        if self._thread_ident is None:
            self._thread_ident = self._get_current_thread_ident()

    def _check_thread_ident(self):
        if self._get_current_thread_ident() != self._thread_ident:
            raise ThreadUnsafe("mc client created in %s\n%s, called in %s" %
                               (self._thread_ident,
                                self._created_stack,
                                self._get_current_thread_ident()))

    def _get_current_thread_ident(self):
        return (os.getpid(), threading.current_thread().name)

########NEW FILE########
__FILENAME__ = benchmark
#!/usr/bin/env python

import time
import random
import string
import sys
import traceback


global total_time

def run_test(func, name):
    sys.stdout.write(name + ': ')
    sys.stdout.flush()
    start_time = time.time()
    try:
        func()
    except:
        print "failed or not supported"
        global options
        if options.verbose:
            traceback.print_exc()
    else:
        end_time = time.time() 
        global total_time
        total_time += end_time - start_time
        print "%f seconds" % (end_time - start_time)


class BigObject(object):
    def __init__(self, letter='1', size=10000):
        self.object = letter * size

    def __eq__(self, other):
        return self.object == other.object


class Benchmark(object):
    def __init__(self, module, options):
        self.module = module
        self.options = options
        self.init_server()
        self.test_set()
        self.test_set_get()
        self.test_random_get()
        self.test_set_same()
        self.test_set_big_object()
        self.test_set_get_big_object()
        self.test_set_big_string()
        self.test_set_get_big_string()
        self.test_get()
        self.test_get_big_object()
        self.test_get_multi()
        self.test_get_list()

    def init_server(self):
        #self.mc = self.module.Client([self.options.server_address])
        self.mc = self.module.Client(["127.0.0.1:11211","127.0.0.1:11212", "127.0.0.1:11213", "127.0.0.1:11214", "127.0.0.1:11215"])
        self.mc.set('bench_key', "E" * 50)

        num_tests = self.options.num_tests
        self.keys = ['key%d' % i for i in xrange(num_tests)]
        self.values = ['value%d' % i for i in xrange(num_tests)]
        import random
        self.random_keys = ['key%d' % random.randint(0, num_tests) for i in xrange(num_tests * 3)]

    def test_set(self):
        set_ = self.mc.set
        pairs = zip(self.keys, self.values)

        def test():
            for key, value in pairs:
                set_(key, value)
        def test_loop():
            for i in range(10):
                for key, value in pairs:
                    set_(key, value)
        run_test(test, 'test_set')

        for key, value in pairs:
            self.mc.delete(key)

    def test_set_get(self):
        set_ = self.mc.set
        get_ = self.mc.get
        pairs = zip(self.keys, self.values)

        def test():
            for key, value in pairs:
                set_(key, value)
                result = get_(key)
                assert result == value
        run_test(test, 'test_set_get')

        #for key, value in pairs:
        #    self.mc.delete(key)

    def test_random_get(self):
        get_ = self.mc.get
        set_ = self.mc.set

        value = "chenyin"

        def test():
            index = 0
            for key in self.random_keys:
                result = get_(key)
                index += 1
                if(index % 5 == 0):
                    set_(key, value)
        run_test(test, 'test_random_get')

    def test_set_same(self):
        set_ = self.mc.set

        def test():
            for i in xrange(self.options.num_tests):
                set_('key', 'value')
        def test_loop():
            for i in range(10):
                for i in xrange(self.options.num_tests):
                    set_('key', 'value')
        run_test(test, 'test_set_same')

        self.mc.delete('key')

    def test_set_big_object(self):
        set_ = self.mc.set
        # libmemcached is slow to store large object, so limit the
        # number of objects here to make tests not stall.
        pairs = [('key%d' % i, BigObject()) for i in xrange(100)]

        def test():
            for key, value in pairs:
                set_(key, value)

        run_test(test, 'test_set_big_object (100 objects)')

        for key, value in pairs:
            self.mc.delete(key)

    def test_set_get_big_object(self):
        set_ = self.mc.set
        get_ = self.mc.get
        # libmemcached is slow to store large object, so limit the
        # number of objects here to make tests not stall.
        pairs = [('key%d' % i, BigObject()) for i in xrange(100)]

        def test():
            for key, value in pairs:
                set_(key, value)
                result = get_(key)
                assert result == value

        run_test(test, 'test_set_get_big_object (100 objects)')

        #for key, value in pairs:
        #    self.mc.delete(key)

    def test_set_get_big_string(self):
        set_ = self.mc.set
        get_ = self.mc.get

        # libmemcached is slow to store large object, so limit the
        # number of objects here to make tests not stall.
        pairs = [('key%d' % i, 'x' * 10000) for i in xrange(100)]

        def test():
            for key, value in pairs:
                set_(key, value)
                result = get_(key)
                assert result == value
        run_test(test, 'test_set_get_big_string (100 objects)')


    def test_set_big_string(self):
        set_ = self.mc.set

        # libmemcached is slow to store large object, so limit the
        # number of objects here to make tests not stall.
        pairs = [('key%d' % i, 'x' * 10000) for i in xrange(100)]

        def test():
            for key, value in pairs:
                set_(key, value)
        run_test(test, 'test_set_big_string (100 objects)')

        for key, value in pairs:
            self.mc.delete(key)


    def test_get(self):
        pairs = zip(self.keys, self.values)
        for key, value in pairs:
            self.mc.set(key, value)

        get = self.mc.get

        def test():
            for key, value in pairs:
                result = get(key)
                assert result == value
        run_test(test, 'test_get')

        for key, value in pairs:
            self.mc.delete(key)
        
    def test_get_big_object(self):
        pairs = [('bkey%d' % i, BigObject('x')) for i in xrange(100)]
        for key, value in pairs:
            self.mc.set(key, value)

        get = self.mc.get
        expected_values = [BigObject('x') for i in xrange(100)]
        
        def test():
            for i in xrange(100):
                result = get('bkey%d' % i)
                assert result == expected_values[i]
        run_test(test, 'test_get_big_object (100 objects)')

        for key, value in pairs:
            self.mc.delete(key)

    def test_get_multi(self):
        pairs = zip(self.keys, self.values)
        for key, value in pairs:
            self.mc.set(key, value)

        keys = self.keys
        expected_result = dict(pairs)

        def test():
            result = self.mc.get_multi(keys)
            assert result == expected_result
        run_test(test, 'test_get_multi')

        for key, value in pairs:
            self.mc.delete(key)

    def test_get_list(self):
        pairs = zip(self.keys, self.values)
        for key, value in pairs:
            self.mc.set(key, value)

        keys = self.keys
        expected_result = self.values
        
        def test():
            result = self.mc.get_list(keys)
            assert result == expected_result
        run_test(test, 'test_get_list')
        
        for key in self.keys:
            self.mc.delete(key)


def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-a', '--server-address', dest='server_address',
            default='127.0.0.1:11211',
            help="address:port of memcached [default: 127.0.0.1:11211]")
    parser.add_option('-n', '--num-tests', dest='num_tests', type='int',
            default=1000,
            help="repeat counts of each test [default: 1000]")
    parser.add_option('-v', '--verbose', dest='verbose',
            action='store_true', default=False,
            help="show traceback infomation if a test fails")
    global options
    options, args = parser.parse_args()


    options.verbose=1
    print "verbose", options.verbose

    global total_time
    total_time = 0

    print "Benchmarking cmemcached..."
    import cmemcached
    Benchmark(cmemcached, options)


if __name__ == '__main__':
    main()
    global total_time
    print "total_time is %f" % total_time

########NEW FILE########
__FILENAME__ = node_failure_test
from cmemcached import *
import time
import cmemcached
print cmemcached

mc = Client([
#	'192.163.1.222:11211',
#	'192.163.1.2:11211',
#	'192.163.1.5:11211',
#    'localhost:7902'
    'theoden:11400',
	], do_split=0)
print mc.set_behavior(BEHAVIOR_NO_BLOCK, 0)
#print mc.set_behavior(BEHAVIOR_TCP_NODELAY, 1)
mc.set_behavior(BEHAVIOR_CONNECT_TIMEOUT, 50)
mc.set_behavior(BEHAVIOR_SND_TIMEOUT, 500*1000)
mc.set_behavior(BEHAVIOR_RCV_TIMEOUT, 500*1000)
mc.set_behavior(BEHAVIOR_POLL_TIMEOUT, 5000)
mc.set_behavior(BEHAVIOR_SERVER_FAILURE_LIMIT, 2)
mc.set_behavior(BEHAVIOR_RETRY_TIMEOUT, 10)

print mc.get_behavior(BEHAVIOR_NO_BLOCK)
print mc.get_behavior(BEHAVIOR_TCP_NODELAY)

for i in xrange(1):
    print time.time(), mc.set('test', 'test'*1024*1024)
#    print time.time(), len(mc.get('test') or '')

########NEW FILE########
__FILENAME__ = pickle_perf
from cPickle import dumps, loads
from timeit import Timer

num = 300
class BigObject(object):
    def __init__(self, letter='1', size=10000):
        self.object = letter * size

    def __eq__(self, other):
        return self.object == other.object

sillything = []

for i in (1000, 10000, 100000, 200000):
    value = [BigObject(str(j%10), i) for j in xrange(num)]
    sillything.append(value)


value_t = None

def test_pickle():
    for tset in sillything:
        for t in tset:
            value = dumps(t, -1)
            value_t = loads(value)
            #assert value_t == t

from time import time
t=time()
for i in xrange(10):
    test_pickle()
print time()-t
#t=Timer(setup='from __main__ import test_pickle', stmt='test_pickle()')
#print t.timeit()


########NEW FILE########
__FILENAME__ = set_get_pressure_test
import cmemcached
class BigObject(object):
    def __init__(self, letter='1', size=10000):
        self.object = letter * size

    def __eq__(self, other):
        return self.object == other.object

mc=cmemcached.Client(["127.0.0.1:11211","127.0.0.1:11212","127.0.0.1:11213", "127.0.0.1:11214"])

num=200
keyss = []
for i in xrange(4):
    k=i
    keyss.append(['key%d_%d' % (k,j) for j in xrange(num)])


valuess = []
for i in (1000, 10000, 100000, 200000):
    values = [BigObject(str(j%10), i) for j in xrange(num)]
    valuess.append(values)

def test_set_get(mc, pairs):
    counter = 0
    for key, value in pairs:
        mc.set(key, value)
        if(counter%4 == 0):
            #assert mc.get(key) == value
            pass
        counter+=1

from time import time
t=time()
for i in xrange(100):
    for k in xrange(4):
        pairs = zip(keyss[k],valuess[k])
        test_set_get(mc, pairs)
print time()-t

########NEW FILE########
__FILENAME__ = test_key_mapping
import cmemcached
import optparse

class BigObject(object):
    def __init__(self, letter='1', size=10000):
        self.object = letter * size

    def __eq__(self, other):
        return self.object == other.object

parameters = ['set', 'add_server', 'remove_server']
parameters_string = '|'.join(parameters)
p = optparse.OptionParser(usage=("%prog " + parameters_string))

options, arguments = p.parse_args()
if len(arguments) != 1 or arguments[0] not in parameters:
    p.error('Only one parameter(in %s) are supported!' % parameters_string)
print arguments[0]

if arguments[0] == 'remove_server':
    mc =  cmemcached.Client(["127.0.0.1:11211","127.0.0.1:11212","127.0.0.1:11213"])
else:
    mc =  cmemcached.Client(["127.0.0.1:11211","127.0.0.1:11212","127.0.0.1:11213", "127.0.0.1:11214"])

num_tests = 10000
count = 0
keys = ['helloworld%d' % i for i in xrange(num_tests)]
if arguments[0] == 'set':
    for key in keys:
        mc.set(key , 'aa')
    for key in keys:
        assert mc.get(key) == 'aa'

if arguments[0] == 'add_server':
    mc.add_server(["127.0.0.1:11215"])
    for key in keys:
        if mc.get(key) == 'aa':
            count += 1
    print "hit rate:", float(count)/num_tests

if arguments[0] == 'remove_server':
    for key in keys:
        if mc.get(key) == 'aa':
            count += 1
    print "hit rate:", float(count)/num_tests

########NEW FILE########
__FILENAME__ = test_prefix
#!/usr/local/bin/python2.7
#coding:utf-8

from cmemcached import Client as m2

prefix = 'dae|admin|'

c1=m2(['localhost:11211'], prefix=prefix)
c2=m2(['localhost:11211'])

c1.set('a', 1)
assert(c1.get('a')==1)
assert(c2.get(prefix+'a')==1)
assert(c2.get('a')==None)

c1.add('b', 2)
assert(c1.get('b')==2)
assert(c2.get(prefix+'b')==2)
assert(c2.get('b')==None)

c1.incr('b')
assert(c1.get('b')==3)
assert(c2.get(prefix+'b')==3)

c2.decr(prefix+'b')
assert(c1.get('b')==2)

c1.set_multi({'x':'a', 'y':'b'})
ret = c1.get_multi(['x', 'y'])
assert(ret.get('x') == 'a' and ret.get('y') == 'b')
assert(c1.delete_multi(['a', 'b', 'x', 'y']))

########NEW FILE########
__FILENAME__ = test_server_down
#!/usr/bin/env python
import cmemcached

mc=cmemcached.Client(["127.0.0.1:11211","127.0.0.1:11212","127.0.0.1:11213", "127.0.0.1:11214"])

num = 10000
keys = ["key%d" % k for k in xrange(num)]

success_counter = 0
failure_counter = 0

def print_counter():
    print "success_counter is ", success_counter
    print "failure_counter is ", failure_counter
    assert failure_counter+success_counter == num
    print "mis rate is ", float(failure_counter)/num


while True:
    for key in keys:
        mc.set(key, "aa")
    for key in keys:
        if mc.get(key) == "aa":
                success_counter += 1
        else:
                failure_counter += 1
    print_counter()
    success_counter = 0
    failure_counter = 0


########NEW FILE########
__FILENAME__ = test_cmemcached
# -*- encoding:utf-8 -*-

import cmemcached
import unittest
import cPickle as pickle
import marshal
import time
import os
import threading
import subprocess

TEST_SERVER = "localhost"
TEST_UNIX_SOCKET = "/tmp/memcached.sock"

memcached_process = None


def setup():
    global memcached_process
    memcached_process = subprocess.Popen(['memcached'])
    time.sleep(0.5)


def teardown():
    memcached_process.terminate()


class BigObject(object):

    def __init__(self, letter='1', size=2000000):
        self.object = letter * size

    def __eq__(self, other):
        return self.object == other.object


class NoPickle(object):

    def __getattr__(self, name):
        pass


class TestCmemcached(unittest.TestCase):

    def setUp(self):
        self.mc = cmemcached.Client([TEST_SERVER], comp_threshold=1024)

    def test_set_get(self):
        self.mc.set("key", "value")
        self.assertEqual(self.mc.get("key"), "value")

        self.mc.set("key_int", 1)
        self.assertEqual(self.mc.get("key_int"), 1)

        self.mc.set("key_long", 1234567890L)
        self.assertEqual(self.mc.get("key_long"), 1234567890L)

        self.mc.set("key_object", BigObject())
        self.assertEqual(self.mc.get("key_object"), BigObject())

        big_object = BigObject('x', 1000001)
        self.mc.set("key_big_object", big_object)
        self.assertEqual(self.mc.get("key_big_object"), big_object)

    def test_set_get_none(self):
        self.assertEqual(self.mc.set('key', None), True)
        self.assertEqual(self.mc.get('key'), None)

    def test_chinese_set_get(self):
        key = '豆瓣'
        value = '在炎热的夏天我们无法停止上豆瓣'
        self.assertEqual(self.mc.set(key, value), 1)

        self.assertEqual(self.mc.get(key), value)

    def test_unicode_set_get(self):
        key = "test_unicode_set_get"
        value = u"中文"
        self.assertEqual(self.mc.set(key, value), 1)
        self.assertEqual(self.mc.get(key), value)

    def test_special_key(self):
        key = 'keke a kid'
        value = 1024
        self.assertEqual(self.mc.set(key, value), 0)
        self.assertEqual(self.mc.get(key), None)
        key = 'u:keke a kid'
        self.assertEqual(self.mc.set(key, value), 0)
        self.assertEqual(self.mc.get(key), None)

    def test_unicode_key(self):
        key1 = u"answer"
        key2 = u"答案"
        bytes_key1 = "answer"
        bytes_key2 = "答案"
        value = 42

        self.assertEqual(self.mc.set(key1, value), 1)
        self.assertEqual(self.mc.get(key1), value)

        self.assertEqual(self.mc.set(key2, value), 1)
        self.assertEqual(self.mc.get(key2), value)

        self.assertEqual(self.mc.incr(key2), value + 1)
        self.assertEqual(self.mc.get(key2), value + 1)

        self.assertEqual(self.mc.delete(key1), 1)
        self.assertEqual(self.mc.get(key1), None)

        self.assertEqual(self.mc.add(key1, value), 1)
        self.assertEqual(self.mc.get(key1), value)
        self.assertEqual(self.mc.add(key1, value), False)
        self.assertEqual(self.mc.set(key1, value), 1)

        self.assertEqual(self.mc.get(bytes_key1), self.mc.get(key1))
        self.assertEqual(self.mc.get(bytes_key2), self.mc.get(key2))

    def test_add(self):
        key = 'test_add'
        self.mc.delete(key)
        self.assertEqual(self.mc.add(key, 'tt'), 1)
        self.assertEqual(self.mc.get(key), 'tt')
        self.assertEqual(self.mc.add(key, 'tt'), 0)
        self.mc.delete(key + '2')
        self.assertEqual(self.mc.add(key + '2', range(10)), 1)

    def test_replace(self):
        key = 'test_replace'
        self.mc.delete(key)
        self.assertEqual(self.mc.replace(key, ''), 0)
        self.assertEqual(self.mc.set(key, 'b'), 1)
        self.assertEqual(self.mc.replace(key, 'a'), 1)
        self.assertEqual(self.mc.get(key), 'a')

    def test_append(self):
        key = "test_append"
        value = "append\n"
        self.mc.delete(key)
        self.assertEqual(self.mc.append(key, value), 0)
        self.mc.set(key, "")
        self.assertEqual(self.mc.append(key, value), 1)
        self.assertEqual(self.mc.append(key, value), 1)
        self.assertEqual(self.mc.prepend(key, 'before\n'), 1)
        self.assertEqual(self.mc.get(key), 'before\n' + value * 2)

    def test_append_multi(self):
        N = 10
        K = "test_append_multi_%d"
        data = "after\n"
        for i in range(N):
            self.assertEqual(self.mc.set(K % i, "before\n"), 1)
        keys = [K % i for i in range(N)]
        # append
        self.assertEqual(self.mc.append_multi(keys, data), 1)
        self.assertEqual(self.mc.get_multi(keys),
                         dict(zip(keys, ["before\n" + data] * N)))
        # prepend
        self.assertEqual(self.mc.prepend_multi(keys, data), 1)
        self.assertEqual(self.mc.get_multi(keys),
                         dict(zip(keys, [data + "before\n" + data] * N)))
        # delete
        self.assertEqual(self.mc.delete_multi(keys), 1)
        self.assertEqual(self.mc.get_multi(keys), {})

    def test_append_multi_performance(self):
        N = 70000
        K = "test_append_multi_%d"
        data = "after\n"
        keys = [K % i for i in range(N)]
        t = time.time()
        self.mc.append_multi(keys, data)
        t = time.time() - t
        assert t < 1, 'should append 7w key in 1 secs %f' % t

    def test_set_multi(self):
        values = dict(('key%s' % k, ('value%s' % k) * 100)
                      for k in range(1000))
        values.update({' ': ''})
        self.assertEqual(self.mc.set_multi(values), 1)
        del values[' ']
        self.assertEqual(self.mc.get_multi(values.keys()), values)
        #mc=cmemcached.Client(["localhost:11999"], comp_threshold=1024)
        #self.assertEqual(mc.set_multi(values), 0)

    def test_append_large(self):
        k = 'test_append_large'
        self.mc.set(k, 'a' * 2048)
        self.mc.append(k, 'bbbb')
        assert 'bbbb' not in self.mc.get(k)
        self.mc.set(k, 'a' * 2048, compress=False)
        self.mc.append(k, 'bbbb')
        assert 'bbbb' in self.mc.get(k)

    def test_incr(self):
        key = "Not_Exist"
        self.assertEqual(self.mc.incr(key), None)
        # key="incr:key1"
        #self.mc.set(key, "not_numerical")
        #self.assertEqual(self.mc.incr(key), 0)
        key = "incr:key2"
        self.mc.set(key, 2007)
        self.assertEqual(self.mc.incr(key), 2008)

    def test_decr(self):
        key = "Not_Exist"
        self.assertEqual(self.mc.decr(key), None)
        # key="decr:key1"
        #self.mc.set(key, "not_numerical")
        # self.assertEqual(self.mc.decr(key),0)
        key = "decr:key2"
        self.mc.set(key, 2009)
        self.assertEqual(self.mc.decr(key), 2008)

    def test_get_multi(self):
        keys = ["hello1", "hello2", "hello3"]
        values = ["vhello1", "vhello2", "vhello3"]
        for x in xrange(3):
            self.mc.set(keys[x], values[x])
            self.assertEqual(self.mc.get(keys[x]), values[x])
        result = self.mc.get_multi(keys)
        for x in xrange(3):
            self.assertEqual(result[keys[x]], values[x])

    def test_get_multi_invalid(self):
        keys = ["hello1", "hello2", "hello3"]
        values = ["vhello1", "vhello2", "vhello3"]
        for x in xrange(3):
            self.mc.set(keys[x], values[x])
            self.assertEqual(self.mc.get(keys[x]), values[x])
        invalid_keys = keys + ['hoho\r\n']
        result = self.mc.get_multi(invalid_keys)
        for x in xrange(3):
            self.assertEqual(result[keys[x]], values[x])
        result_new = self.mc.get_multi(keys)
        for x in xrange(3):
            self.assertEqual(result_new[keys[x]], values[x])

    def test_get_multi_big(self):
        keys = ["hello1", "hello2", "hello3"]
        values = [BigObject(str(i), 1000001) for i in xrange(3)]
        for x in xrange(3):
            self.mc.set(keys[x], values[x])
            self.assertEqual(self.mc.get(keys[x]), values[x])
        result = self.mc.get_multi(keys)
        for x in xrange(3):
            self.assertEqual(result[keys[x]], values[x])

    def test_get_multi_with_empty_string(self):
        keys = ["hello1", "hello2", "hello3"]
        for k in keys:
            self.mc.set(k, '')
        self.assertEqual(self.mc.get_multi(keys), dict(zip(keys, [""] * 3)))

    def testBool(self):
        self.mc.set("bool", True)
        value = self.mc.get("bool")
        self.assertEqual(value, True)
        self.mc.set("bool_", False)
        value = self.mc.get("bool_")
        self.assertEqual(value, False)

    def testEmptyString(self):
        self.assertTrue(self.mc.set("str", ''))
        value = self.mc.get("str")
        self.assertEqual(value, '')

    def testGetHost(self):
        host = self.mc.get_host_by_key("str")
        self.assertEqual(host, TEST_SERVER)

    def test_get_list(self):
        self.mc.set("a", 'a')
        self.mc.delete('b')
        v = self.mc.get_list(['a', 'b'])
        self.assertEqual(v, ['a', None])

    def test_marshal(self):
        v = [{2: {"a": 337}}]
        self.mc.set("a", v)
        self.assertEqual(self.mc.get("a"), v)
        raw, flags = self.mc.get_raw("a")
        self.assertEqual(raw, marshal.dumps(v, 2))

    def test_pickle(self):
        v = [{"v": BigObject('a', 10)}]
        self.mc.set("a", v)
        self.assertEqual(self.mc.get("a"), v)
        raw, flags = self.mc.get_raw("a")
        self.assertEqual(raw, pickle.dumps(v, -1))

    def test_no_pickle(self):
        v = NoPickle()
        self.assertEqual(self.mc.set("nopickle", v), None)
        self.assertEqual(self.mc.get("nopickle"), None)

    def test_big_list(self):
        v = range(1024 * 1024)
        r = self.mc.set('big_list', v)

        self.assertEqual(r, True)
        self.assertEqual(self.mc.get('big_list'), v)

    def test_last_error(self):
        from cmemcached import RETURN_MEMCACHED_SUCCESS, RETURN_MEMCACHED_NOTFOUND
        self.assertEqual(self.mc.set('testkey', 'hh'), True)
        self.assertEqual(self.mc.get('testkey'), 'hh')
        self.assertEqual(self.mc.get_last_error(), RETURN_MEMCACHED_SUCCESS)
        self.assertEqual(self.mc.get('testkey1'), None)
        self.assertEqual(self.mc.get_last_error(), RETURN_MEMCACHED_SUCCESS)
        self.assertEqual(self.mc.get_multi(['testkey']), {'testkey': 'hh'})
        self.assertEqual(self.mc.get_last_error(), RETURN_MEMCACHED_SUCCESS)
        self.assertEqual(self.mc.get_multi(['testkey1']), {})
        self.assertEqual(self.mc.get_last_error(), RETURN_MEMCACHED_SUCCESS)

        self.mc = cmemcached.Client(["localhost:11999"], comp_threshold=1024)
        self.assertEqual(self.mc.set('testkey', 'hh'), False)
        self.assertEqual(self.mc.get('testkey'), None)
        self.assertNotEqual(self.mc.get_last_error(), RETURN_MEMCACHED_SUCCESS)
        self.assertEqual(self.mc.get_multi(['testkey']), {})
        self.assertNotEqual(self.mc.get_last_error(), RETURN_MEMCACHED_SUCCESS)

    def test_stats(self):
        s = self.mc.stats()
        self.assertEqual(TEST_SERVER in s, True)
        st = s[TEST_SERVER]
        st_keys = sorted([
            "pid",
            "uptime",
            "time",
            "version",
            "pointer_size",
            "rusage_user",
            "rusage_system",
            "curr_items",
            "total_items",
            "bytes",
            "curr_connections",
            "total_connections",
            "connection_structures",
            "cmd_get",
            "cmd_set",
            "get_hits",
            "get_misses",
            "evictions",
            "bytes_read",
            "bytes_written",
            "limit_maxbytes",
            "threads",
        ])
        self.assertEqual(sorted(st.keys()), st_keys)
        mc = cmemcached.Client(["localhost:11999", TEST_SERVER])
        s = mc.stats()
        self.assertEqual(len(s), 2)

    # def test_gets_multi(self):
    #    keys=["hello1", "hello2", "hello3"]
    #    values=["vhello1", "vhello2", "vhello3"]
    #    for x in xrange(3):
    #        self.mc.set(keys[x], values[x])
    #        self.assertEqual(self.mc.get(keys[x]) , values[x])
    #    result=self.mc.gets_multi(keys)
    #    for x in xrange(3):
    # print result[keys[x]][0],result[keys[x]][1]
    #        self.assertEqual(result[keys[x]][0] , values[x])

    # def test_cas(self):
    #    keys=["hello1", "hello2", "hello3"]
    #    values=["vhello1", "vhello2", "vhello3"]
    #    for x in xrange(3):
    #        self.mc.set(keys[x], values[x])
    #        self.assertEqual(self.mc.get(keys[x]) , values[x])
    #    result=self.mc.gets_multi(keys)
    #    for x in xrange(3):
    #        self.assertEqual(result[keys[x]][0] , values[x])
    #        self.assertEqual(self.mc.cas(keys[x],'cas',cas=result[keys[x]][1]) , 1)
    #        self.assertEqual(self.mc.cas(keys[x],'cas2',cas=result[keys[x]][1]) , 0)
    #        self.assertEqual(self.mc.get(keys[x]) , 'cas')

    def test_client_pickable(self):
        import pickle
        d = pickle.dumps(self.mc)
        self.mc = pickle.loads(d)
        self.test_stats()

    def test_touch(self):
        self.mc.set('test', 1)
        self.assertEqual(self.mc.get('test'), 1)
        self.assertEqual(self.mc.touch('test', -1), 1)
        self.assertEqual(self.mc.get('test'), None)

        self.mc.set('test', 1)
        self.assertEqual(self.mc.get('test'), 1)
        self.assertEqual(self.mc.touch('test', 1), 1)
        time.sleep(1)
        self.assertEqual(self.mc.get('test'), None)

    def test_ketama(self):
        mc = cmemcached.Client(
            ['localhost', 'myhost:11211', '127.0.0.1:11212', 'myhost:11213'])
        # for i in range(10):
        #    k = 'test:%d' % (i*10000)
        #    print """'%s': '%s',""" % (k, mc.get_host_by_key(k))
        rs = {
            'test:10000': 'localhost',
            'test:20000': '127.0.0.1:11212',
            'test:30000': '127.0.0.1:11212',
            'test:40000': '127.0.0.1:11212',
            'test:50000': '127.0.0.1:11212',
            'test:60000': 'myhost:11213',
            'test:70000': '127.0.0.1:11212',
            'test:80000': '127.0.0.1:11212',
            'test:90000': '127.0.0.1:11212',
        }
        for k in rs:
            self.assertEqual(mc.get_host_by_key(k), rs[k])

    def test_should_raise_exception_if_called_in_different_thread(self):
        catched = [False]

        def f():
            try:
                self.mc.set('key_thread', 1)
            except cmemcached.ThreadUnsafe:
                catched[0] = True

        # make connection in main thread
        self.mc.get('key_thread')

        # use it in another thread (should be forbidden)
        t = threading.Thread(target=f)
        t.start()
        t.join()
        self.assertEqual(catched, [True])


# class TestUnixSocketCmemcached(TestCmemcached):
#
#    def setUp(self):
#        os.system('memcached -d -s %s' % TEST_UNIX_SOCKET)
#        self.mc=cmemcached.Client([TEST_UNIX_SOCKET], comp_threshold=1024)
#
#    def testGetHost(self):
#        host = self.mc.get_host_by_key("str")
#        self.assertEqual(host, TEST_UNIX_SOCKET)
#
#    def test_stats(self):
#        "not need"

class TestBinaryCmemcached(TestCmemcached):

    def setUp(self):
        self.mc = cmemcached.Client([TEST_SERVER], comp_threshold=1024)
        self.mc.set_behavior(cmemcached.BEHAVIOR_BINARY_PROTOCOL, 1)

    def test_append_multi_performance(self):
        "binary is slow, bug ?"

    def test_stats(self):
        "not yet support"

    def test_touch(self):
        "not yet support"


class TestPrefix(TestCmemcached):

    def setUp(self):
        self.mc = cmemcached.Client([TEST_SERVER], comp_threshold=1024,
                                    prefix='/prefix')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_logger
from mock import Mock, patch
import cmemcached

INVALID_SERVER_ADDR = '127.0.0.1:12345'


def test_sys_stderr_should_have_no_output_when_no_logger_is_set():
    with patch('sys.stderr') as mock_stderr:
        client = cmemcached.Client([INVALID_SERVER_ADDR])
        client.get('test_key_with_no_logger')
        client.set('test_key_with_no_logger', 'test_value_with_no_logger')
        assert not mock_stderr.write.called


def test_logger_should_be_called_when_set():
    logger = Mock()
    client = cmemcached.Client([INVALID_SERVER_ADDR], logger=logger)
    client.get('test_key_with_logger')
    client.set('test_key_with_logger', 'test_value_with_logger')
    logger.assert_called_with("[cmemcached]memcached_get: server "
                              "127.0.0.1:12345 error: CONNECTION FAILURE\n")

########NEW FILE########
__FILENAME__ = test_multi_return_failure
from mock import Mock, patch
import cmemcached

INVALID_SERVER_ADDR = '127.0.0.1:12345'


def test_set_multi_return_failure():
    client = cmemcached.Client([INVALID_SERVER_ADDR])
    v = dict([(str(i), "vv%s" % i) for i in range(10)])
    r, failures = client.set_multi(v, return_failure=True)
    assert r == False
    assert failures == v.keys()


def test_delete_multi_return_failure():
    client = cmemcached.Client([INVALID_SERVER_ADDR])
    keys = [str(i) for i in range(10)]
    r, failures = client.delete_multi(keys, return_failure=True)
    assert r == False
    assert failures == keys



########NEW FILE########
__FILENAME__ = test_set_long
import cmemcached
import unittest
import subprocess
import time

TEST_SERVER = "localhost"
memcached_process = None

def setup():
    global memcached_process
    memcached_process = subprocess.Popen(['memcached'])
    time.sleep(0.5)


def teardown():
    memcached_process.terminate()


class TestCmemcached_for_long(unittest.TestCase):

    def setUp(self):
        self.mc = cmemcached.Client([TEST_SERVER], comp_threshold=1024)

    def test_set_get_long(self):
        self.mc.set("key_long_short", long(1L))
        v = self.mc.get("key_long_short")
        self.assertEqual(v, 1L)
        self.assertEqual(type(v), long)

        big = 1233345435353543L
        self.mc.set("key_long_big", big)
        v = self.mc.get("key_long_big")
        self.assertEqual(v, big)
        self.assertEqual(type(v), long)


########NEW FILE########
