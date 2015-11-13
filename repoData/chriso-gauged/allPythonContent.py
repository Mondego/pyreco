__FILENAME__ = benchmark
'''
Gauged - https://github.com/chriso/gauged
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from gauged import Gauged
from random import random
from math import floor, ceil
from time import time
from calendar import timegm
from datetime import datetime, timedelta
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

def abbreviate(suffixes, cutoff):
    def abbreviate_(number, decimals=1):
        position = 0
        while position < len(suffixes) and abs(number) >= cutoff:
            number = round(number / cutoff, decimals)
            position += 1
        if floor(number) == ceil(number):
            number = int(number)
        return str(number) + suffixes[position]
    return abbreviate_

abbreviate_number = abbreviate([ '', 'K', 'M', 'B' ], 1000)
abbreviate_bytes = abbreviate([ 'B', 'KB', 'MB', 'GB', 'TB' ], 1024)

# Parse CLI options
benchmark = ArgumentParser(usage='%(prog)s [OPTIONS]',
    formatter_class=ArgumentDefaultsHelpFormatter)
benchmark.add_argument('-n', '--number', type=int, default=1000000,
    help='How many measurements to store')
benchmark.add_argument('-t', '--days', type=int, default=365,
    help='How many days to spread the measurements over')
benchmark.add_argument('-d', '--driver', default='sqlite://',
    help='Where to store the data (defaults to SQLite in-memory)')
benchmark.add_argument('-b', '--block-size', type=int, default=Gauged.DAY,
    help='The block size to use')
benchmark.add_argument('-r', '--resolution', type=int, default=Gauged.SECOND,
    help='The resolution to use')
options = vars(benchmark.parse_args())

# Setup the Gauged instance
gauged = Gauged(options['driver'], block_size=options['block_size'],
    resolution=options['resolution'], key_overflow=Gauged.IGNORE,
    gauge_nan=Gauged.IGNORE)
gauged.sync()

print 'Writing to %s (block_size=%s, resolution=%s)' % (options['driver'],
    options['block_size'], options['resolution'])

# Get the start and end timestamp
end = datetime.now()
start = end - timedelta(days=options['days'])
start_timestamp = timegm(start.timetuple())
end_timestamp = timegm(end.timetuple())

number = abbreviate_number(options['number'])

print 'Spreading %s measurements to key "foobar" over %s days' % (number, options['days'])

# Benchmark writes
measurements = options['number']
span = end_timestamp - start_timestamp
start = time()
with gauged.writer as writer:
    data = [ 'foobar', 0 ]
    gauges = [ data ]
    add = writer.add
    for timestamp in xrange(start_timestamp, end_timestamp, span // measurements):
        data[1] = random()
        add(gauges, timestamp=timestamp*1000)
elapsed = time() - start

print 'Wrote %s measurements in %s seconds (%s/s)' % (number, round(elapsed, 3),
    abbreviate_number(measurements / elapsed))

statistics = gauged.statistics()
byte_count = statistics.byte_count
print 'Gauge data uses %s (%s per measurement)' % (abbreviate_bytes(byte_count),
    abbreviate_bytes(byte_count / float(measurements)))

# Read benchmarks
for aggregate in ( 'min', 'max', 'sum', 'count', 'mean', 'stddev', 'median' ):
    start = time()
    gauged.aggregate('foobar', aggregate)
    elapsed = time() - start
    print '%s() in %ss (read %s measurements/s)' % (aggregate,
        round(elapsed, 3), abbreviate_number(measurements / elapsed))

########NEW FILE########
__FILENAME__ = aggregates
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

class Aggregate(object):

    SUM = 'sum'
    MIN = 'min'
    MAX = 'max'
    MEAN = 'mean'
    STDDEV = 'stddev'
    PERCENTILE = 'percentile'
    MEDIAN = 'median'
    COUNT = 'count'

    ALL = set(( SUM, MIN, MAX, MEAN, STDDEV, PERCENTILE, MEDIAN, COUNT ))

    ASSOCIATIVE = set(( SUM, MIN, MAX, COUNT ))

########NEW FILE########
__FILENAME__ = bridge
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

import os, glob, sys
from ctypes import POINTER, Structure, CDLL, cdll
from ctypes import c_int, c_size_t, c_uint32, c_char_p, c_bool, c_float

class SharedLibrary(object):
    '''A shared library wrapper'''

    def __init__(self, name, prefix):
        self.prefix = prefix
        path = os.path.dirname(os.path.realpath(os.path.join(__file__, '..')))
        version = sys.version.split(' ')[0][0:3]
        shared_lib = os.path.join(path, 'build', 'lib*-' + version, name + '*.*')
        lib = glob.glob(shared_lib)[0]
        try:
            self.library = cdll.LoadLibrary(lib)
        except OSError as err:
            raise OSError('Failed to load the C extension: ' + str(err))

    def prototype(self, name, argtypes, restype=None):
        '''Define argument / return types for the specified C function'''
        function = self.function(name)
        function.argtypes = argtypes
        if restype:
            function.restype = restype

    def function(self, name):
        '''Get a function by name'''
        return getattr(self.library, '%s_%s' % (self.prefix, name))

    def __getattr__(self, name):
        fn = self.function(name)
        setattr(self, name, fn)
        return fn

class Array(Structure):
    '''A wrapper for the C type gauged_array_t'''
    _fields_ = [('buffer', POINTER(c_float)), ('size', c_size_t),
                ('length', c_size_t)]

class Map(Structure):
    '''A wrapper for the C type gauged_map_t'''
    _fields_ = [('buffer', POINTER(c_uint32)), ('size', c_size_t),
                ('length', c_size_t)]

class WriterHashNode(Structure):
    '''A wrapper for the C type gauged_writer_hash_node_t'''

WriterHashNode._fields_ = [('key', c_char_p), ('map', POINTER(Map)),
    ('array', POINTER(Array)), ('namespace', c_uint32),
    ('seed', c_uint32), ('next', POINTER(WriterHashNode))]

class WriterHash(Structure):
    '''A wrapper for the C type gauged_writer_hash_t'''
    _fields_ = [('nodes', POINTER(POINTER(WriterHashNode))),
                ('size', c_size_t), ('count', c_size_t),
                ('head', POINTER(WriterHashNode))]

class Writer(Structure):
    '''A wrapper for the C type gauged_writer_t'''
    _fields_ = [('pending', POINTER(WriterHash)),
                ('max_key', c_size_t), ('copy', c_char_p),
                ('buffer', POINTER(c_char_p)),
                ('buffer_size', c_size_t)]

# Define pointer types
ArrayPtr = POINTER(Array)
MapPtr = POINTER(Map)
WriterPtr = POINTER(Writer)
SizetPtr = POINTER(c_size_t)
Uint32Ptr = POINTER(c_uint32)
FloatPtr = POINTER(c_float)

# Load the shared library
Gauged = SharedLibrary('_gauged', 'gauged')

# Define argument & return types
Gauged.prototype('array_new', [], ArrayPtr)
Gauged.prototype('array_free', [ArrayPtr])
Gauged.prototype('array_length', [ArrayPtr], c_size_t)
Gauged.prototype('array_export', [ArrayPtr], FloatPtr)
Gauged.prototype('array_import', [FloatPtr, c_size_t], ArrayPtr)
Gauged.prototype('array_append', [ArrayPtr, c_float], c_int)
Gauged.prototype('map_new', [], MapPtr)
Gauged.prototype('map_free', [MapPtr])
Gauged.prototype('map_export', [MapPtr], Uint32Ptr)
Gauged.prototype('map_length', [MapPtr], c_size_t)
Gauged.prototype('map_import', [Uint32Ptr, c_size_t], MapPtr)
Gauged.prototype('map_append', [MapPtr, c_uint32, ArrayPtr], c_int)
Gauged.prototype('map_advance', [Uint32Ptr, SizetPtr, Uint32Ptr, SizetPtr,
    POINTER(FloatPtr)], Uint32Ptr)
Gauged.prototype('map_concat', [MapPtr, MapPtr, c_uint32, c_uint32,
    c_uint32], c_int)
Gauged.prototype('map_first', [MapPtr], c_float)
Gauged.prototype('map_last', [MapPtr], c_float)
Gauged.prototype('map_sum', [MapPtr], c_float)
Gauged.prototype('map_min', [MapPtr], c_float)
Gauged.prototype('map_max', [MapPtr], c_float)
Gauged.prototype('map_mean', [MapPtr], c_float)
Gauged.prototype('map_stddev', [MapPtr], c_float)
Gauged.prototype('map_sum_of_squares', [MapPtr, c_float], c_float)
Gauged.prototype('map_count', [MapPtr], c_float)
Gauged.prototype('map_percentile', [MapPtr, c_float, FloatPtr], c_int)
Gauged.prototype('writer_new', [c_size_t], WriterPtr)
Gauged.prototype('writer_free', [WriterPtr])
Gauged.prototype('writer_flush_arrays', [WriterPtr, c_uint32], c_int)
Gauged.prototype('writer_flush_maps', [WriterPtr, c_bool], c_int)

########NEW FILE########
__FILENAME__ = config
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from .writer import Writer
from .utilities import to_bytes, Time

DEFAULTS = {
    'namespace': 0,
    'block_size': Time.DAY,
    'resolution': Time.SECOND,
    'writer_name': 'default',
    'overwrite_blocks': False,
    'key_overflow': Writer.ERROR,
    'key_whitelist': None,
    'flush_seconds': 0,
    'append_only_violation': Writer.ERROR,
    'gauge_nan': Writer.ERROR,
    'key_cache_size': 64 * 1024,
    'max_interval_steps': 31 * 24,
    'min_cache_interval': Time.HOUR,
    'max_look_behind': Time.WEEK,
    'defaults': {
        'namespace': None,
        'limit': 10,
        'offset': None,
        'prefix': None,
        'start': None,
        'end': None,
        'interval': Time.DAY,
        'cache': True,
        'key': None,
        'aggregate': None,
        'percentile': 50
    }
}

class Config(object):

    def __init__(self, **kwargs):
        self.block_arrays = None
        self.defaults = None
        self.key_whitelist = None
        self.block_size = None
        self.resolution = None
        self.update(**kwargs)

    def update(self, **kwargs):
        for key in kwargs.iterkeys():
            if key not in DEFAULTS:
                raise ValueError('Unknown configuration key: ' + key)
        for key, default in DEFAULTS.iteritems():
            if key == 'defaults':
                defaults = DEFAULTS['defaults'].copy()
                if 'defaults' in kwargs:
                    for key, value in kwargs['defaults'].iteritems():
                        if key not in defaults:
                            raise ValueError('Unknown default key: ' + key)
                        defaults[key] = value
                self.defaults = defaults
            else:
                setattr(self, key, kwargs.get(key, default))
        if self.block_size % self.resolution != 0:
            raise ValueError('`block_size` must be a multiple of `resolution`')
        self.block_arrays = self.block_size // self.resolution
        if self.key_whitelist is not None:
            self.key_whitelist = set(( to_bytes(key) for key in self.key_whitelist ))

########NEW FILE########
__FILENAME__ = context
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from hashlib import sha1
from calendar import timegm
from datetime import date
from time import time
from math import sqrt
from .structures import SparseMap
from .aggregates import Aggregate
from .utilities import to_bytes
from .results import Statistics, TimeSeries
from .errors import GaugedDateRangeError, GaugedIntervalSizeError

class Context(object):

    def __init__(self, driver, config, **context):
        self.driver = driver
        self.config = config
        self.namespace = context.pop('namespace')
        if self.namespace is None:
            self.namespace = config.namespace
        self.context = config.defaults.copy()
        first, last = self.driver.block_offset_bounds(self.namespace)
        self.no_data = last is None
        context['min_block'] = long(first or 0)
        context['max_block'] = long(last or 0)
        for key, value in context.iteritems():
            if value is not None:
                self.context[key] = value
        self.check_timestamps()
        self.suppress_interval_size_error = False

    def keys(self):
        context = self.context
        return self.driver.keys(self.namespace, prefix=context['prefix'],
            limit=context['limit'], offset=context['offset'])

    def statistics(self):
        context = self.context
        start, end = context['start'], context['end']
        block_size = self.config.block_size
        start_block = start // block_size
        end_block, end_array = end // block_size, end % block_size
        if not end_array:
            end_block -= 1
        start = start_block * block_size
        end = (end_block + 1) * block_size
        namespace = self.namespace
        stats = self.driver.get_namespace_statistics(namespace,
            start_block, end_block)
        return Statistics(namespace, start, end, stats[0], stats[1])

    def value(self, timestamp=None, key=None):
        key = self.translated_key if key is None else key
        if key is None:
            return None
        context, config = self.context, self.config
        block_size = config.block_size
        look_behind = config.max_look_behind // block_size
        timestamp = context['end'] if timestamp is None else timestamp
        end_block, offset = timestamp // block_size, timestamp % block_size
        offset = offset // config.resolution
        get_block = self.get_block
        result = block = None
        try:
            while end_block >= 0:
                block = get_block(key, end_block)
                if block is not None:
                    if offset is not None:
                        tmp = block.slice(end=offset+1)
                        block.free()
                        block = tmp
                    if block.byte_length():
                        result = block.last()
                        block.free()
                        block = None
                        break
                    block.free()
                    block = None
                if not look_behind:
                    break
                offset = None
                look_behind -= 1
                end_block -= 1
        finally:
            if block is not None:
                block.free()
        return result

    def aggregate(self, start=None, end=None, aggregate=None, key=None):
        key = self.translated_key if key is None else key
        if key is None:
            return None
        context = self.context
        aggregate = context['aggregate'] if aggregate is None else aggregate
        start = context['start'] if start is None else start
        end = context['end'] if end is None else end
        result = block = None
        if aggregate not in Aggregate.ALL:
            raise ValueError('Unknown aggregate: %s' % aggregate)
        block_size = self.config.block_size
        start_block, start_array = start // block_size, start % block_size
        end_block = end // block_size
        if start_array:
            start_block += 1
        # Can we break the operation up into smaller chunks that utilise the
        # aggregate_series() cache and then combine the results?
        if start_block + 1 < end_block and aggregate in Aggregate.ASSOCIATIVE:
            block_boundary_start = start_block * block_size
            block_boundary_end = end_block * block_size
            values = []
            if start < block_boundary_start:
                values.append(self.aggregate(start, block_boundary_start, aggregate, key))
            self.suppress_interval_size_error = True
            values.extend(self.aggregate_series(block_boundary_start, block_boundary_end,
                aggregate, key, block_size).values)
            if end > block_boundary_end:
                values.append(self.aggregate(block_boundary_end, end, aggregate, key))
            values = [ value for value in values if value is not None ]
            if aggregate == Aggregate.SUM:
                result = sum(values) if len(values) else None
            elif aggregate == Aggregate.MIN:
                result = min(values) if len(values) else None
            elif aggregate == Aggregate.MAX:
                result = max(values) if len(values) else None
            else: # Aggregate.COUNT
                result = sum(values) if len(values) else 0
            return result
        try:
            if aggregate == Aggregate.SUM:
                for block in self.block_iterator(key, start, end):
                    if result is None:
                        result = 0
                    result += block.sum()
                    block.free()
                    block = None
            elif aggregate == Aggregate.COUNT:
                result = 0
                for block in self.block_iterator(key, start, end):
                    result += block.count()
                    block.free()
                    block = None
            elif aggregate == Aggregate.MIN:
                for block in self.block_iterator(key, start, end):
                    comparison = block.min()
                    if result is None or result > comparison:
                        result = comparison
                    block.free()
                    block = None
            elif aggregate == Aggregate.MAX:
                for block in self.block_iterator(key, start, end):
                    comparison = block.max()
                    if result is None or result < comparison:
                        result = comparison
                    block.free()
                    block = None
            elif aggregate == Aggregate.MEAN:
                count = 0
                for block in self.block_iterator(key, start, end):
                    block_count = block.count()
                    if block_count:
                        count += block_count
                        if result is None:
                            result = 0
                        result += block.sum()
                    block.free()
                    block = None
                if result is not None:
                    result = result / count if count else 0
            elif aggregate == Aggregate.STDDEV:
                count = self.aggregate(start, end, Aggregate.COUNT, key)
                if count:
                    block_sum = self.aggregate(start, end, Aggregate.SUM, key)
                    mean = block_sum / count
                    sum_of_squares = 0
                    for block in self.block_iterator(key, start, end):
                        sum_of_squares += block.sum_of_squares(mean)
                        block.free()
                        block = None
                    result = sqrt(sum_of_squares / count)
            else: # percentile & median
                block = self.query(key, start, end)
                if block is not None:
                    if aggregate == Aggregate.PERCENTILE:
                        result = block.percentile(context['percentile'])
                    else:
                        result = block.median()
        finally:
            if block is not None:
                block.free()
        return result if result == result else None

    def value_series(self):
        key = self.translated_key
        if key is None or self.no_data:
            return TimeSeries([])
        context = self.context
        start = context['start']
        end = context['end']
        namespace = self.namespace
        interval = self.interval
        cache = self.cache
        if cache:
            cache_key = sha1(str(dict(key=key,
                look_behind=self.config.max_look_behind))).digest()
            driver = self.driver
            cached = dict(driver.get_cache(namespace, cache_key, interval, start, end))
        else:
            cached = {}
        values = []
        value_fn = self.value
        while start < end:
            group_end = min(end, start + interval)
            value = cached[start] if start in cached else value_fn(start, key)
            values.append(( start, group_end, value ))
            start += interval
        if cache:
            to_cache = []
            cache_until_timestamp = self.cache_until * self.config.block_size
            for start, end, value in values:
                if cache_until_timestamp >= end and start not in cached:
                    to_cache.append(( start, value ))
            if len(to_cache):
                driver.add_cache(namespace, cache_key, interval, to_cache)
        return TimeSeries(( (start, value) for start, _, value in values \
            if value is not None ))

    def aggregate_series(self, start=None, end=None, aggregate=None,
            key=None, interval=None):
        key = self.translated_key if key is None else key
        if key is None or self.no_data:
            return TimeSeries([])
        context = self.context
        start = context['start'] if start is None else start
        end = context['end'] if end is None else end
        aggregate = context['aggregate'] if aggregate is None else aggregate
        namespace = self.namespace
        interval = self.interval if interval is None else interval
        cache = self.cache
        if cache:
            cache_key = sha1(str(dict(key=key, aggregate=aggregate))).digest()
            driver = self.driver
            cached = dict(driver.get_cache(namespace, cache_key, interval, start, end))
        else:
            cached = {}
        values = []
        aggregate_fn = self.aggregate
        while start < end:
            group_end = min(end, start + interval)
            if start in cached:
                result = cached[start]
            else:
                result = aggregate_fn(start, group_end, aggregate)
            values.append(( start, group_end, result ))
            start += interval
        if cache:
            to_cache = []
            cache_until_timestamp = self.cache_until * self.config.block_size
            for start, end, result in values:
                if cache_until_timestamp >= end and start not in cached:
                    to_cache.append(( start, result ))
            if len(to_cache):
                driver.add_cache(namespace, cache_key, interval, to_cache)
        return TimeSeries(( (start, value) for start, _, value in values ))

    def block_iterator(self, key, start, end, yield_if_empty=False):
        config = self.config
        block_size, resolution = config.block_size, config.resolution
        start_block, start_array = start // block_size, start % block_size
        end_block, end_array = end // block_size, end % block_size
        start_array, end_array = start_array // resolution, end_array // resolution
        if not end_array:
            end_block -= 1
        get_block = self.get_block
        block = None
        try:
            while start_block <= end_block:
                block = get_block(key, start_block)
                if block is not None:
                    if start_block != end_block:
                        if start_array:
                            sliced = block.slice(start=start_array)
                            block.free()
                            block = sliced
                    elif start_array or end_array:
                        sliced = block.slice(start=start_array, end=end_array)
                        block.free()
                        block = sliced
                    yield block
                    block = None
                elif yield_if_empty:
                    yield None
                start_array = 0
                start_block += 1
        finally:
            if block is not None:
                block.free()

    def query(self, key, start, end):
        context = self.context
        start = context['start'] if start is None else start
        end = context['end'] if end is None else end
        blocks = self.block_iterator(key, start, end, yield_if_empty=True)
        block_arrays = self.config.block_arrays
        offset = 0
        result = SparseMap()
        block = None
        try:
            for block in blocks:
                if block is not None:
                    result.concat(block, offset=offset)
                    block.free()
                    block = None
                offset += block_arrays
        except: # pragma: no cover
            result.free()
            raise
        finally:
            if block is not None:
                block.free()
        return result

    def get_block(self, key, block):
        # Note: the second item is a flags column for future extensions, e.g.
        # to signal that the block needs decompressing
        buf, _ = self.driver.get_block(self.namespace, block, key)
        return SparseMap(buf, len(buf)) if buf is not None else None

    def check_timestamps(self):
        context = self.context
        start, end = context['start'], context['end']
        if start is None:
            start = 0
        elif isinstance(start, date):
            start = long(timegm(start.timetuple()) * 1000)
        block_size = self.config.block_size
        if end is None:
            end = context['max_block'] * block_size + block_size
        elif isinstance(end, date):
            end = long(timegm(end.timetuple()) * 1000)
        start = long(start)
        end = long(end)
        if start < 0 or end < 0:
            now = long(time() * 1000)
            if start < 0:
                start += now
            if end < 0:
                end += now
            if start < 0 or end < 0:
                raise GaugedDateRangeError('Invalid date range')
        start = max(context['min_block'] * block_size, start)
        end = min(context['max_block'] * block_size + block_size, end)
        if start > end:
            # Don't error if exactly one timestamp was specified. We might
            # have truncated the other without them knowing..
            has_start_timestamp = context.get('start') is not None
            has_end_timestamp = context.get('end') is not None
            if has_start_timestamp ^ has_end_timestamp:
                start = end
        if start > end:
            raise GaugedDateRangeError('Invalid date range')
        context['start'] = start
        context['end'] = end

    @property
    def translated_key(self):
        namespace_key = (self.namespace, to_bytes(self.context['key']))
        ids = self.driver.lookup_ids((namespace_key,))
        return ids.get(namespace_key)

    @property
    def cache(self):
        if not self.context['cache']:
            return False
        return self.context['interval'] >= self.config.min_cache_interval

    @property
    def cache_until(self):
        return self.context['max_block'] if self.cache else 0

    @property
    def interval(self):
        context = self.context
        interval = long(context['interval'])
        if interval <= 0:
            raise GaugedIntervalSizeError
        interval_steps = (context['end'] - context['start']) // interval
        if interval_steps > self.config.max_interval_steps \
                and not self.suppress_interval_size_error:
            raise GaugedIntervalSizeError
        return interval

########NEW FILE########
__FILENAME__ = interface
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

class DriverInterface(object):

    MAX_KEY = 1024

    def create_schema(self):
        raise NotImplementedError

    def clear_schema(self):
        raise NotImplementedError

    def drop_schema(self):
        raise NotImplementedError

    def keys(self, namespace, prefix=None, limit=None, offset=None):
        raise NotImplementedError

    def lookup_ids(self, keys):
        raise NotImplementedError

    def get_block(self, namespace, offset, key):
        raise NotImplementedError

    def insert_keys(self, keys):
        raise NotImplementedError

    def replace_blocks(self, blocks):
        raise NotImplementedError

    def insert_or_append_blocks(self, blocks):
        raise NotImplementedError

    def commit(self):
        raise NotImplementedError

    def block_offset_bounds(self, namespace):
        raise NotImplementedError

    def set_metadata(self, metadata, replace=True):
        raise NotImplementedError

    def get_metadata(self, key):
        raise NotImplementedError

    def set_writer_position(self, name, timestamp):
        raise NotImplementedError

    def get_writer_position(self, name):
        raise NotImplementedError

    def get_namespaces(self):
        raise NotImplementedError

    def remove_namespace(self, namespace):
        raise NotImplementedError

    def clear_from(self, offset, timestamp):
        raise NotImplementedError

    def get_cache(self, namespace, query_hash, length, start, end):
        pass

    def add_cache(self, namespace, query_hash, length, cache):
        pass

    def remove_cache(self, namespace):
        pass

    def add_namespace_statistics(self, namespace, offset,
            data_points, byte_count):
        raise NotImplementedError

    def get_namespace_statistics(self, namespace, start_offset, end_offset):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = mysql
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from warnings import filterwarnings
from .interface import DriverInterface

class MySQLDriver(DriverInterface):
    '''A mysql driver for gauged'''

    MAX_KEY = 255

    def __init__(self, bulk_insert=1000, **kwargs):
        try:
            mysql = __import__('MySQLdb')
            filterwarnings('ignore', category=mysql.Warning)
            self.to_buffer = lambda buf: buf
        except ImportError:
            try:
                mysql = __import__('pymysql')
                self.to_buffer = str
            except ImportError:
                raise ImportError('The mysql-python or pymysql library is required')
        self.db = mysql.connect(**kwargs)
        self.bulk_insert = bulk_insert
        self.cursor = self.db.cursor()

    def keys(self, namespace, prefix=None, limit=None, offset=None):
        '''Get keys from a namespace'''
        params = [ namespace ]
        query = '''SELECT `key` FROM gauged_keys
            WHERE namespace = %s'''
        if prefix is not None:
            query += ' AND `key` LIKE %s'
            params.append(prefix + '%')
        if limit is not None:
            query += ' LIMIT '
            if offset is not None:
                query += '%s, '
                params.append(offset)
            query += '%s'
            params.append(limit)
        cursor = self.cursor
        cursor.execute(query, params)
        return [ key for key, in cursor ]

    def lookup_ids(self, keys):
        '''Lookup the integer ID associated with each (namespace, key) in the
        keys list'''
        keys_len = len(keys)
        ids = { namespace_key: None for namespace_key in keys }
        start = 0
        bulk_insert = self.bulk_insert
        query = 'SELECT namespace, `key`, id FROM gauged_keys WHERE '
        check = '(namespace = %s AND `key` = %s) '
        cursor = self.cursor
        execute = cursor.execute
        while start < keys_len:
            rows = keys[start:start+bulk_insert]
            params = [ param for params in rows for param in params ]
            id_query = query + (check + ' OR ') * (len(rows) - 1) + check
            execute(id_query, params)
            for namespace, key, id_ in cursor:
                ids[( namespace, key )] = id_
            start += bulk_insert
        return ids

    def get_block(self, namespace, offset, key):
        '''Get the block identified by namespace, offset and key'''
        cursor = self.cursor
        cursor.execute('''SELECT data, flags FROM gauged_data
            WHERE namespace = %s AND offset = %s AND `key` = %s''',
            ( namespace, offset, key ))
        row = cursor.fetchone()
        return ( None, None ) if row is None else row

    def insert_keys(self, keys):
        '''Insert keys into a table which assigns an ID'''
        start = 0
        bulk_insert = self.bulk_insert
        keys_len = len(keys)
        query = 'INSERT IGNORE INTO gauged_keys (namespace, `key`) VALUES '
        execute = self.cursor.execute
        while start < keys_len:
            rows = keys[start:start+bulk_insert]
            params = [ param for params in rows for param in params ]
            insert = '(%s,%s),' * (len(rows) - 1) + '(%s,%s)'
            execute(query + insert, params)
            start += bulk_insert

    def replace_blocks(self, blocks):
        '''Replace multiple blocks. blocks must be a list of tuples where
        each tuple consists of (namespace, offset, key, data)'''
        start = 0
        bulk_insert = self.bulk_insert
        blocks_len = len(blocks)
        row = '(%s,%s,%s,%s,%s)'
        query = 'REPLACE INTO gauged_data (namespace, offset, `key`, data, flags) VALUES '
        execute = self.cursor.execute
        to_buffer = self.to_buffer
        while start < blocks_len:
            rows = blocks[start:start+bulk_insert]
            params = []
            for namespace, offset, key, data, flags in rows:
                params.extend(( namespace, offset, key, to_buffer(data), flags ))
            insert = (row + ',') * (len(rows) - 1) + row
            execute(query + insert, params)
            start += bulk_insert

    def insert_or_append_blocks(self, blocks):
        '''Insert multiple blocks. If a block already exists, the data is
        appended. blocks must be a list of tuples where each tuple consists
        of (namespace, offset, key, data)'''
        start = 0
        bulk_insert = self.bulk_insert
        blocks_len = len(blocks)
        row = '(%s,%s,%s,%s,%s)'
        query = 'INSERT INTO gauged_data (namespace, offset, `key`, data, flags) VALUES '
        post = ''' ON DUPLICATE KEY UPDATE data = CONCAT(data, VALUES(data)),
            flags = VALUES(flags)'''
        execute = self.cursor.execute
        to_buffer = self.to_buffer
        while start < blocks_len:
            rows = blocks[start:start+bulk_insert]
            params = []
            for namespace, offset, key, data, flags in rows:
                params.extend(( namespace, offset, key, to_buffer(data), flags ))
            insert = (row + ',') * (len(rows) - 1) + row
            execute(query + insert + post, params)
            start += bulk_insert

    def block_offset_bounds(self, namespace):
        '''Get the minimum and maximum block offset for the specified namespace'''
        cursor = self.cursor
        cursor.execute('''SELECT CONVERT(MIN(offset), UNSIGNED),
            CONVERT(MAX(offset), UNSIGNED)
            FROM gauged_statistics WHERE namespace = %s''', (namespace,))
        return cursor.fetchone()

    def set_metadata(self, metadata, replace=True):
        params = [ param for params in metadata.iteritems() for param in params ]
        query = 'REPLACE' if replace else 'INSERT IGNORE'
        query += ' INTO gauged_metadata VALUES (%s,%s)'
        query += ',(%s,%s)' * (len(metadata) - 1)
        self.cursor.execute(query, params)
        self.db.commit()

    def get_metadata(self, key):
        cursor = self.cursor
        cursor.execute('SELECT value FROM gauged_metadata WHERE `key` = %s', (key,))
        result = cursor.fetchone()
        return result[0] if result else None

    def all_metadata(self):
        cursor = self.cursor
        cursor.execute('SELECT * FROM gauged_metadata')
        return dict(( row for row in cursor ))

    def set_writer_position(self, name, timestamp):
        '''Insert a timestamp to keep track of the current writer position'''
        self.cursor.execute('''REPLACE INTO gauged_writer_history (id, timestamp)
            VALUES (%s, %s)''', (name, timestamp))

    def get_writer_position(self, name):
        '''Get the current writer position'''
        cursor = self.cursor
        cursor.execute('''SELECT timestamp FROM gauged_writer_history
            WHERE id = %s''', (name,))
        result = cursor.fetchone()
        return result[0] if result else 0

    def get_namespaces(self):
        '''Get a list of namespaces'''
        cursor = self.cursor
        cursor.execute('''SELECT DISTINCT namespace FROM gauged_statistics''')
        return [ namespace for namespace, in cursor ]

    def remove_namespace(self, namespace):
        '''Remove all data associated with the current namespace'''
        params = (namespace, )
        execute = self.cursor.execute
        execute('DELETE FROM gauged_data WHERE namespace = %s', params)
        execute('DELETE FROM gauged_statistics WHERE namespace = %s', params)
        execute('DELETE FROM gauged_keys WHERE namespace = %s', params)
        self.remove_cache(namespace)

    def clear_from(self, offset, timestamp):
        params = (offset, )
        execute = self.cursor.execute
        execute('''DELETE FROM gauged_data WHERE offset >= %s''', params)
        execute('''DELETE FROM gauged_statistics WHERE offset >= %s ''', params)
        execute('''DELETE FROM gauged_cache WHERE start + length >= %s''',
            (timestamp,))
        execute('''UPDATE gauged_writer_history SET timestamp = %s
            WHERE timestamp > %s''', (timestamp, timestamp))

    def get_cache(self, namespace, query_hash, length, start, end):
        '''Get a cached value for the specified date range and query'''
        cursor = self.cursor
        cursor.execute('''SELECT start, value FROM gauged_cache WHERE namespace = %s
            AND hash = %s AND length = %s AND start BETWEEN %s AND %s''',
            (namespace, query_hash, length, start, end))
        return cursor.fetchall()

    def add_cache(self, namespace, query_hash, length, cache):
        '''Add cached values for the specified date range and query'''
        start = 0
        bulk_insert = self.bulk_insert
        cache_len = len(cache)
        row = '(%s,%s,%s,%s,%s)'
        query = '''INSERT IGNORE INTO gauged_cache
            (namespace, hash, length, start, value) VALUES '''
        execute = self.cursor.execute
        while start < cache_len:
            rows = cache[start:start+bulk_insert]
            params = []
            for timestamp, value in rows:
                params.extend(( namespace, query_hash, length, timestamp, value ))
            insert = (row + ',') * (len(rows) - 1) + row
            execute(query + insert, params)
            start += bulk_insert
        self.db.commit()

    def remove_cache(self, namespace):
        '''Remove all cached values for the specified namespace'''
        self.cursor.execute('DELETE FROM gauged_cache WHERE namespace = %s', (namespace,))

    def commit(self):
        '''Commit the current transaction'''
        self.db.commit()

    def create_schema(self):
        '''Create all necessary tables'''
        cursor = self.cursor
        execute = cursor.execute
        execute('SHOW TABLES')
        tables = set(( table for table, in cursor ))
        if 'gauged_data' not in tables:
            execute('''CREATE TABLE gauged_data (
                namespace INT(11) UNSIGNED NOT NULL,
                offset INT(11) UNSIGNED NOT NULL,
                `key` BIGINT(15) UNSIGNED NOT NULL,
                data MEDIUMBLOB NOT NULL,
                flags INT(11) UNSIGNED NOT NULL,
                PRIMARY KEY (offset, namespace, `key`))''')
        if 'gauged_keys' not in tables:
            execute('''CREATE TABLE gauged_keys (
                id BIGINT(15) UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
                namespace INT(11) UNSIGNED NOT NULL,
                `key` VARCHAR(255) BINARY NOT NULL,
                UNIQUE KEY (namespace, `key`))''')
        if 'gauged_writer_history' not in tables:
            execute('''CREATE TABLE gauged_writer_history (
                id VARCHAR(255) NOT NULL PRIMARY KEY,
                timestamp BIGINT(15) UNSIGNED NOT NULL)''')
        if 'gauged_cache' not in tables:
            execute('''CREATE TABLE gauged_cache (
                namespace INT(11) UNSIGNED NOT NULL,
                hash BINARY(20) NOT NULL,
                length BIGINT(15) UNSIGNED NOT NULL,
                start BIGINT(15) UNSIGNED NOT NULL,
                value FLOAT(11),
                PRIMARY KEY (namespace, hash, length, start))''')
        if 'gauged_statistics' not in tables:
            execute('''CREATE TABLE gauged_statistics (
                namespace INT(11) UNSIGNED NOT NULL,
                offset INT(11) UNSIGNED NOT NULL,
                data_points INT(11) UNSIGNED NOT NULL,
                byte_count INT(11) UNSIGNED NOT NULL,
                PRIMARY KEY (namespace, offset))''')
        if 'gauged_metadata' not in tables:
            execute('''CREATE TABLE gauged_metadata (
                `key` VARCHAR(255) NOT NULL PRIMARY KEY,
                value VARCHAR(255) NOT NULL)''')
        self.db.commit()

    def clear_schema(self):
        '''Clear all gauged data'''
        execute = self.cursor.execute
        execute('TRUNCATE TABLE gauged_data')
        execute('TRUNCATE TABLE gauged_keys')
        execute('TRUNCATE TABLE gauged_writer_history')
        execute('TRUNCATE TABLE gauged_cache')
        execute('TRUNCATE TABLE gauged_statistics')
        self.db.commit()

    def drop_schema(self):
        '''Drop all gauged tables'''
        execute = self.cursor.execute
        execute('DROP TABLE IF EXISTS gauged_data')
        execute('DROP TABLE IF EXISTS gauged_keys')
        execute('DROP TABLE IF EXISTS gauged_writer_history')
        execute('DROP TABLE IF EXISTS gauged_cache')
        execute('DROP TABLE IF EXISTS gauged_statistics')
        execute('DROP TABLE IF EXISTS gauged_metadata')
        self.db.commit()

    def add_namespace_statistics(self, namespace, offset, data_points, byte_count):
        '''Update namespace statistics for the period identified by
        offset'''
        self.cursor.execute('''INSERT INTO gauged_statistics VALUES (%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE data_points = data_points + VALUES(data_points),
            byte_count = byte_count + VALUES(byte_count)''',
            ( namespace, offset, data_points, byte_count ))

    def get_namespace_statistics(self, namespace, start_offset, end_offset):
        '''Get namespace statistics for the period between start_offset and
        end_offset (inclusive)'''
        cursor = self.cursor
        cursor.execute('''SELECT SUM(data_points), SUM(byte_count)
            FROM gauged_statistics WHERE namespace = %s AND offset
            BETWEEN %s AND %s''', (namespace, start_offset, end_offset))
        return [ long(count or 0) for count in cursor.fetchone() ]

########NEW FILE########
__FILENAME__ = postgresql
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from .interface import DriverInterface

class PostgreSQLDriver(DriverInterface):
    '''A PostgreSQL driver for gauged'''

    MAX_KEY = 255

    def __init__(self, **kwargs):
        try:
            self.psycopg2 = __import__('psycopg2')
        except ImportError:
            raise ImportError('The psycopg2 library is required')
        self.db = self.psycopg2.connect(**kwargs)
        self.cursor = self.db.cursor()
        self.bulk_insert = 1000

    def keys(self, namespace, prefix=None, limit=None, offset=None):
        '''Get keys from a namespace'''
        params = [ namespace ]
        query = '''SELECT key FROM gauged_keys
            WHERE namespace = %s'''
        if prefix is not None:
            query += ' AND key LIKE %s'
            params.append(prefix + '%')
        if limit is not None:
            query += ' LIMIT %s'
            params.append(limit)
        if offset is not None:
            query += ' OFFSET %s'
            params.append(offset)
        cursor = self.cursor
        cursor.execute(query, params)
        return [ key for key, in cursor ]

    def lookup_ids(self, keys):
        '''Lookup the integer ID associated with each (namespace, key) in the
        keys list'''
        keys_len = len(keys)
        ids = { namespace_key: None for namespace_key in keys }
        start = 0
        bulk_insert = self.bulk_insert
        query = 'SELECT namespace, key, id FROM gauged_keys WHERE '
        check = '(namespace = %s AND key = %s) '
        cursor = self.cursor
        execute = cursor.execute
        while start < keys_len:
            rows = keys[start:start+bulk_insert]
            params = [ param for params in rows for param in params ]
            id_query = query + (check + ' OR ') * (len(rows) - 1) + check
            execute(id_query, params)
            for namespace, key, id_ in cursor:
                ids[( namespace, key )] = id_
            start += bulk_insert
        return ids

    def get_block(self, namespace, offset, key):
        '''Get the block identified by namespace, offset, key and
        value'''
        cursor = self.cursor
        cursor.execute('''SELECT data, flags FROM gauged_data
            WHERE namespace = %s AND "offset" = %s AND key = %s''',
            ( namespace, offset, key ))
        row = cursor.fetchone()
        return ( None, None ) if row is None else row

    def insert_keys(self, keys):
        '''Insert keys into a table which assigns an ID'''
        start = 0
        bulk_insert = self.bulk_insert
        keys_len = len(keys)
        query = 'INSERT INTO gauged_keys (namespace, key) VALUES '
        execute = self.cursor.execute
        while start < keys_len:
            rows = keys[start:start+bulk_insert]
            params = [ param for params in rows for param in params ]
            insert = '(%s,%s),' * (len(rows) - 1) + '(%s,%s)'
            execute(query + insert, params)
            start += bulk_insert

    def replace_blocks(self, blocks):
        '''Replace multiple blocks. blocks must be a list of tuples where
        each tuple consists of (namespace, offset, key, data)'''
        start = 0
        execute = self.cursor.execute
        query = '''DELETE FROM gauged_data WHERE namespace = %s AND
            "offset" = %s AND key = %s'''
        for namespace, offset, key, _, _ in blocks:
            execute(query, (namespace, offset, key))
        bulk_insert = self.bulk_insert
        blocks_len = len(blocks)
        row = '(%s,%s,%s,%s,%s)'
        query = '''INSERT INTO gauged_data
            (namespace, "offset", key, data, flags) VALUES '''
        binary = self.psycopg2.Binary
        while start < blocks_len:
            rows = blocks[start:start+bulk_insert]
            params = []
            for namespace, offset, key, data, flags in rows:
                params.extend(( namespace, offset, key, binary(data), flags ))
            insert = (row + ',') * (len(rows) - 1) + row
            execute(query + insert, params)
            start += bulk_insert

    def insert_or_append_blocks(self, blocks):
        '''Insert multiple blocks. If a block already exists, the data is
        appended. blocks must be a list of tuples where each tuple consists
        of (namespace, offset, key, data)'''
        binary = self.psycopg2.Binary
        execute = self.cursor.execute
        query = '''UPDATE gauged_data SET data = data || %s, flags = %s
            WHERE namespace = %s AND "offset" = %s AND key = %s;
            INSERT INTO gauged_data (data, flags, namespace, "offset", key)
            SELECT %s, %s, %s, %s, %s WHERE NOT EXISTS (
            SELECT 1 FROM gauged_data WHERE namespace = %s AND "offset" = %s
            AND key = %s)'''
        for namespace, offset, key, data, flags in blocks:
            data = binary(data)
            execute(query, (data, flags, namespace, offset, key, data, flags,
                namespace, offset, key, namespace, offset, key))

    def block_offset_bounds(self, namespace):
        '''Get the minimum and maximum block offset for the specified namespace'''
        cursor = self.cursor
        cursor.execute('''SELECT MIN("offset"), MAX("offset")
            FROM gauged_statistics WHERE namespace = %s''', (namespace,))
        return cursor.fetchone()

    def set_metadata(self, metadata, replace=True):
        execute = self.cursor.execute
        if replace:
            query = 'DELETE FROM gauged_metadata WHERE key IN (%s'
            query += ',%s' * (len(metadata) - 1) + ')'
            execute(query, metadata.keys())
        params = [ param for params in metadata.iteritems() for param in params ]
        query = 'INSERT INTO gauged_metadata VALUES (%s,%s)'
        query += ',(%s,%s)' * (len(metadata) - 1)
        execute(query, params)
        self.db.commit()

    def get_metadata(self, key):
        cursor = self.cursor
        cursor.execute('SELECT value FROM gauged_metadata WHERE key = %s', (key,))
        result = cursor.fetchone()
        return result[0] if result else None

    def all_metadata(self):
        cursor = self.cursor
        cursor.execute('SELECT * FROM gauged_metadata')
        return dict(( row for row in cursor ))

    def set_writer_position(self, name, timestamp):
        '''Insert a timestamp to keep track of the current writer position'''
        execute = self.cursor.execute
        execute('DELETE FROM gauged_writer_history WHERE id = %s', (name,))
        execute('''INSERT INTO gauged_writer_history (id, timestamp)
            VALUES (%s, %s)''', (name, timestamp,))

    def get_writer_position(self, name):
        '''Get the current writer position'''
        cursor = self.cursor
        cursor.execute('''SELECT timestamp FROM gauged_writer_history
            WHERE id = %s''', (name,))
        result = cursor.fetchone()
        return result[0] if result else 0

    def get_namespaces(self):
        '''Get a list of namespaces'''
        cursor = self.cursor
        cursor.execute('''SELECT DISTINCT namespace FROM gauged_statistics''')
        return [ namespace for namespace, in cursor ]

    def remove_namespace(self, namespace):
        '''Remove all data associated with the current namespace'''
        params = (namespace, )
        execute = self.cursor.execute
        execute('DELETE FROM gauged_data WHERE namespace = %s', params)
        execute('DELETE FROM gauged_statistics WHERE namespace = %s', params)
        execute('DELETE FROM gauged_keys WHERE namespace = %s', params)
        self.remove_cache(namespace)

    def clear_from(self, offset, timestamp):
        params = (offset, )
        execute = self.cursor.execute
        execute('DELETE FROM gauged_data WHERE "offset" >= %s', params)
        execute('DELETE FROM gauged_statistics WHERE "offset" >= %s', params)
        execute('DELETE FROM gauged_cache WHERE start + length >= %s',
            (timestamp,))
        execute('''UPDATE gauged_writer_history SET timestamp = %s
            WHERE timestamp > %s''', (timestamp, timestamp))

    def get_cache(self, namespace, query_hash, length, start, end):
        '''Get a cached value for the specified date range and query'''
        query_hash = self.psycopg2.Binary(query_hash)
        cursor = self.cursor
        cursor.execute('''SELECT start, value FROM gauged_cache WHERE namespace = %s
            AND "hash" = %s AND length = %s AND start BETWEEN %s AND %s''',
            (namespace, query_hash, length, start, end))
        return cursor.fetchall()

    def add_cache(self, namespace, query_hash, length, cache):
        '''Add cached values for the specified date range and query'''
        start = 0
        bulk_insert = self.bulk_insert
        cache_len = len(cache)
        row = '(%s,%s,%s,%s,%s)'
        query = '''INSERT INTO gauged_cache
            (namespace, "hash", length, start, value) VALUES '''
        execute = self.cursor.execute
        query_hash = self.psycopg2.Binary(query_hash)
        while start < cache_len:
            rows = cache[start:start+bulk_insert]
            params = []
            for timestamp, value in rows:
                params.extend(( namespace, query_hash, length, timestamp, value ))
            insert = (row + ',') * (len(rows) - 1) + row
            execute(query + insert, params)
            start += bulk_insert
        self.db.commit()

    def remove_cache(self, namespace):
        '''Remove all cached values for the specified namespace'''
        self.cursor.execute('DELETE FROM gauged_cache WHERE namespace = %s', (namespace,))

    def commit(self):
        '''Commit the current transaction'''
        self.db.commit()

    def create_schema(self):
        '''Create all necessary tables'''
        execute = self.cursor.execute
        try:
            return execute('SELECT 1 FROM gauged_statistics')
        except self.psycopg2.ProgrammingError:
            pass
        self.db.rollback()
        execute('''CREATE TABLE IF NOT EXISTS gauged_data (
                namespace integer NOT NULL,
                "offset" integer NOT NULL,
                key bigint NOT NULL,
                data bytea NOT NULL,
                flags integer NOT NULL,
                PRIMARY KEY ("offset", namespace, key));
            CREATE TABLE IF NOT EXISTS gauged_keys (
                id serial PRIMARY KEY,
                namespace integer NOT NULL,
                key varchar NOT NULL);
            CREATE UNIQUE INDEX ON gauged_keys (
                namespace, key);
            CREATE OR REPLACE RULE gauged_ignore_duplicate_keys
                AS ON INSERT TO gauged_keys WHERE EXISTS (
                SELECT 1 FROM gauged_keys WHERE key = NEW.key
                    AND namespace = NEW.namespace)
                DO INSTEAD NOTHING;
            CREATE TABLE IF NOT EXISTS gauged_writer_history (
                id varchar PRIMARY KEY,
                timestamp bigint NOT NULL);
            CREATE TABLE IF NOT EXISTS gauged_cache (
                namespace integer NOT NULL,
                "hash" bytea NOT NULL,
                length bigint NOT NULL,
                start bigint NOT NULL,
                value real,
                PRIMARY KEY(namespace, hash, length, start));
            CREATE OR REPLACE RULE gauged_ignore_duplicate_cache
                AS ON INSERT TO gauged_cache WHERE EXISTS (
                SELECT 1 FROM gauged_cache WHERE namespace = NEW.namespace AND
                "hash" = NEW.hash AND length = NEW.length AND start = NEW.start)
                DO INSTEAD NOTHING;
            CREATE TABLE IF NOT EXISTS gauged_statistics (
                namespace integer NOT NULL,
                "offset" integer NOT NULL,
                data_points integer NOT NULL,
                byte_count integer NOT NULL,
                PRIMARY KEY (namespace, "offset"));
            CREATE TABLE IF NOT EXISTS gauged_metadata (
                key varchar PRIMARY KEY,
                value varchar NOT NULL);
            CREATE OR REPLACE RULE gauged_ignore_duplicate_metadata
                AS ON INSERT TO gauged_metadata WHERE EXISTS (
                SELECT 1 FROM gauged_metadata WHERE key = NEW.key)
                DO INSTEAD NOTHING''')
        self.db.commit()

    def clear_schema(self):
        '''Clear all gauged data'''
        execute = self.cursor.execute
        execute('''TRUNCATE gauged_data;
            TRUNCATE gauged_keys RESTART IDENTITY;
            TRUNCATE gauged_writer_history;
            TRUNCATE gauged_cache;
            TRUNCATE gauged_statistics''')
        self.db.commit()

    def drop_schema(self):
        '''Drop all gauged tables'''
        try:
            self.cursor.execute('''
                DROP TABLE IF EXISTS gauged_data;
                DROP TABLE IF EXISTS gauged_keys;
                DROP TABLE IF EXISTS gauged_writer_history;
                DROP TABLE IF EXISTS gauged_cache;
                DROP TABLE IF EXISTS gauged_statistics;
                DROP TABLE IF EXISTS gauged_metadata''')
            self.db.commit()
        except self.psycopg2.InternalError: # pragma: no cover
            self.db.rollback()

    def add_namespace_statistics(self, namespace, offset, data_points, byte_count):
        '''Update namespace statistics for the period identified by
        offset'''
        query = '''UPDATE gauged_statistics SET data_points = data_points + %s,
            byte_count = byte_count + %s WHERE namespace = %s AND "offset" = %s;
            INSERT INTO gauged_statistics SELECT %s, %s, %s, %s WHERE NOT EXISTS (
            SELECT 1 FROM gauged_statistics WHERE namespace = %s AND "offset" = %s)'''
        self.cursor.execute(query, (data_points, byte_count, namespace,
            offset, namespace, offset, data_points, byte_count, namespace, offset))

    def get_namespace_statistics(self, namespace, start_offset, end_offset):
        '''Get namespace statistics for the period between start_offset and
        end_offset (inclusive)'''
        cursor = self.cursor
        cursor.execute('''SELECT SUM(data_points), SUM(byte_count)
            FROM gauged_statistics WHERE namespace = %s AND "offset"
            BETWEEN %s AND %s''', (namespace, start_offset, end_offset))
        return [ long(count or 0) for count in cursor.fetchone() ]

########NEW FILE########
__FILENAME__ = sqlite
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from .interface import DriverInterface

class SQLiteDriver(DriverInterface):


    MAX_KEY = 255

    MEMORY = 'sqlite://'

    def __init__(self, database, bulk_insert=125):
        try:
            sqlite = __import__('sqlite3')
        except ImportError:
            raise ImportError('The sqlite3 library is required')
        self.db = sqlite.connect(database, check_same_thread=False)
        self.db.text_factory = str
        self.bulk_insert = bulk_insert
        self.cursor = self.db.cursor()

    def keys(self, namespace, prefix=None, limit=None, offset=None):
        '''Get keys from a namespace'''
        params = [ namespace ]
        query = '''SELECT `key` FROM gauged_keys
            WHERE namespace = ?'''
        if prefix is not None:
            query += ' AND `key` LIKE ?'
            params.append(prefix + '%')
        if limit is not None:
            query += ' LIMIT '
            if offset is not None:
                query += '?, '
                params.append(offset)
            query += '?'
            params.append(limit)
        cursor = self.cursor
        cursor.execute(query, params)
        return [ key for key, in cursor ]

    def lookup_ids(self, keys):
        '''Lookup the integer ID associated with each (namespace, key) in the
        keys list'''
        keys_len = len(keys)
        ids = { namespace_key: None for namespace_key in keys }
        start = 0
        bulk_insert = self.bulk_insert
        query = 'SELECT namespace, `key`, id FROM gauged_keys WHERE '
        check = '(namespace = ? AND `key` = ?) '
        cursor = self.cursor
        execute = cursor.execute
        while start < keys_len:
            rows = keys[start:start+bulk_insert]
            params = [ param for params in rows for param in params ]
            id_query = query + (check + ' OR ') * (len(rows) - 1) + check
            execute(id_query, params)
            for namespace, key, id_ in cursor:
                ids[( namespace, key )] = id_
            start += bulk_insert
        return ids

    def get_block(self, namespace, offset, key):
        '''Get the block identified by namespace, offset and key'''
        cursor = self.cursor
        cursor.execute('''SELECT data, flags FROM gauged_data
            WHERE namespace = ? AND offset = ? AND `key` = ?''',
            ( namespace, offset, key ))
        row = cursor.fetchone()
        return ( None, None ) if row is None else row

    def insert_keys(self, keys):
        '''Insert keys into a table which assigns an ID'''
        start = 0
        bulk_insert = self.bulk_insert
        keys_len = len(keys)
        select = 'SELECT ?,?'
        query = 'INSERT OR IGNORE INTO gauged_keys (namespace, `key`) '
        execute = self.cursor.execute
        while start < keys_len:
            rows = keys[start:start+bulk_insert]
            params = [ param for params in rows for param in params ]
            insert = (select + ' UNION ') * (len(rows) - 1) + select
            execute(query + insert, params)
            start += bulk_insert

    def replace_blocks(self, blocks):
        '''Replace multiple blocks. blocks must be a list of tuples where
        each tuple consists of (namespace, offset, key, data, flags)'''
        start = 0
        bulk_insert = self.bulk_insert
        blocks_len = len(blocks)
        select = 'SELECT ?,?,?,?,?'
        query = 'REPLACE INTO gauged_data (namespace, offset, `key`, data, flags) '
        execute = self.cursor.execute
        while start < blocks_len:
            rows = blocks[start:start+bulk_insert]
            params = [ param for params in rows for param in params ]
            insert = (select + ' UNION ') * (len(rows) - 1) + select
            execute(query + insert, params)
            start += bulk_insert

    def insert_or_append_blocks(self, blocks):
        '''Insert multiple blocks. If a block already exists, the data is
        appended. blocks must be a list of tuples where each tuple consists
        of (namespace, offset, key, data)'''
        start = 0
        bulk_insert = self.bulk_insert
        blocks_len = len(blocks)
        select = 'SELECT ?,?,?,"",0'
        query = 'INSERT OR IGNORE INTO gauged_data (namespace, offset, `key`, data, flags) '
        execute = self.cursor.execute
        while start < blocks_len:
            rows = blocks[start:start+bulk_insert]
            params = []
            for namespace, offset, key, _, _ in rows:
                params.extend(( namespace, offset, key ))
            insert = (select + ' UNION ') * (len(rows) - 1) + select
            execute(query + insert, params)
            start += bulk_insert
        for namespace, offset, key, data, flags in blocks:
            execute('''UPDATE gauged_data SET data = CAST(data || ? AS BLOB)
                , flags = ? WHERE namespace = ? AND offset = ? AND
                `key` = ?''', ( data, flags, namespace, offset, key ))

    def block_offset_bounds(self, namespace):
        '''Get the minimum and maximum block offset for the specified namespace'''
        cursor = self.cursor
        cursor.execute('''SELECT MIN(offset), MAX(offset) FROM gauged_statistics
            WHERE namespace = ?''', (namespace,))
        return cursor.fetchone()

    def set_metadata(self, metadata, replace=True):
        params = [ param for params in metadata.iteritems() for param in params ]
        query = 'REPLACE' if replace else 'INSERT OR IGNORE'
        query += ' INTO gauged_metadata SELECT ?,?'
        query += ' UNION SELECT ?,?' * (len(metadata) - 1)
        self.cursor.execute(query, params)
        self.db.commit()

    def get_metadata(self, key):
        cursor = self.cursor
        cursor.execute('SELECT value FROM gauged_metadata WHERE `key` = ?', (key,))
        result = cursor.fetchone()
        return result[0] if result else None

    def all_metadata(self):
        cursor = self.cursor
        cursor.execute('SELECT * FROM gauged_metadata')
        return dict(( row for row in cursor ))

    def set_writer_position(self, name, timestamp):
        '''Insert a timestamp to keep track of the current writer position'''
        self.cursor.execute('''REPLACE INTO gauged_writer_history (id, timestamp)
            VALUES (?, ?)''', (name, timestamp))

    def get_writer_position(self, name):
        '''Get the current writer position'''
        cursor = self.cursor
        cursor.execute('''SELECT timestamp FROM gauged_writer_history
            WHERE id = ?''', (name,))
        result = cursor.fetchone()
        return result[0] if result else 0

    def get_namespaces(self):
        '''Get a list of namespaces'''
        cursor = self.cursor
        cursor.execute('''SELECT DISTINCT namespace FROM gauged_statistics''')
        return [ namespace for namespace, in cursor ]

    def remove_namespace(self, namespace):
        '''Remove all data associated with the current namespace'''
        params = (namespace, )
        execute = self.cursor.execute
        execute('DELETE FROM gauged_data WHERE namespace = ?', params)
        execute('DELETE FROM gauged_statistics WHERE namespace = ?', params)
        execute('DELETE FROM gauged_keys WHERE namespace = ?', params)
        self.remove_cache(namespace)

    def clear_from(self, offset, timestamp):
        params = (offset, )
        execute = self.cursor.execute
        execute('''DELETE FROM gauged_data WHERE offset >= ?''', params)
        execute('''DELETE FROM gauged_statistics WHERE offset >= ? ''', params)
        execute('''DELETE FROM gauged_cache WHERE start + length >= ?''', (timestamp,))
        execute('''UPDATE gauged_writer_history SET timestamp = ?
            WHERE timestamp > ?''', (timestamp, timestamp))

    def get_cache(self, namespace, query_hash, length, start, end):
        '''Get a cached value for the specified date range and query'''
        query = '''SELECT start, value FROM gauged_cache WHERE namespace = ?
            AND hash = ? AND length = ? AND start BETWEEN ? AND ?'''
        cursor = self.cursor
        cursor.execute(query, (namespace, query_hash, length, start, end))
        return tuple(cursor.fetchall())

    def add_cache(self, namespace, query_hash, length, cache):
        '''Add cached values for the specified date range and query'''
        start = 0
        bulk_insert = self.bulk_insert
        cache_len = len(cache)
        select = 'SELECT ?, ?, ?, ?, ?'
        query = '''INSERT OR IGNORE INTO gauged_cache
            (namespace, hash, length, start, value) '''
        execute = self.cursor.execute
        while start < cache_len:
            rows = cache[start:start+bulk_insert]
            params = []
            for timestamp, value in rows:
                params.extend(( namespace, query_hash, length, timestamp, value ))
            insert = (select + ' UNION ') * (len(rows) - 1) + select
            execute(query + insert, params)
            start += bulk_insert
        self.db.commit()

    def remove_cache(self, namespace):
        '''Remove all cached values for the specified namespace'''
        self.cursor.execute('DELETE FROM gauged_cache WHERE namespace = ?', (namespace,))

    def commit(self):
        '''Commit the current transaction'''
        self.db.commit()

    def create_schema(self):
        '''Create all necessary tables'''
        self.cursor.executescript('''
            CREATE TABLE IF NOT EXISTS gauged_data (
                namespace UNSIGNED INT NOT NULL,
                offset UNSIGNED INT NOT NULL,
                `key` INTEGER NOT NULL,
                data BLOB,
                flags UNSIGNED INT NOT NULL,
                PRIMARY KEY (offset, namespace, `key`));
            CREATE TABLE IF NOT EXISTS gauged_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                namespace UNSIGNED INT NOT NULL,
                `key` VARCHAR NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS gauged_namespace_key ON gauged_keys
                (namespace, `key`);
            CREATE TABLE IF NOT EXISTS gauged_writer_history (
                id VARCHAR NOT NULL PRIMARY KEY,
                timestamp UNSIGNED BIGINT NOT NULL);
            CREATE TABLE IF NOT EXISTS gauged_cache (
                namespace UNSIGNED INT NOT NULL,
                hash CHAR(20) NOT NULL,
                length UNSIGNED BIGINT NOT NULL,
                start UNSIGNED BIGINT NOT NULL,
                value FLOAT,
                PRIMARY KEY (namespace, hash, length, start));
            CREATE TABLE IF NOT EXISTS gauged_statistics (
                namespace UNSIGNED INT NOT NULL,
                offset UNSIGNED INT NOT NULL,
                data_points UNSIGNED INT NOT NULL,
                byte_count INUNSIGNED INT NOT NULL,
                PRIMARY KEY (namespace, offset));
            CREATE TABLE IF NOT EXISTS gauged_metadata (
                `key` VARCHAR NOT NULL PRIMARY KEY,
                value VARCHAR NOT NULL)''')
        self.db.commit()

    def clear_schema(self):
        '''Clear all gauged data'''
        self.cursor.executescript('''
            DELETE FROM gauged_data;
            DELETE FROM gauged_keys;
            DELETE FROM gauged_writer_history;
            DELETE FROM gauged_cache;
            DELETE FROM gauged_statistics;
            DELETE FROM sqlite_sequence WHERE name = "gauged_keys"''')
        self.db.commit()

    def drop_schema(self):
        '''Drop all gauged tables'''
        self.cursor.executescript('''
            DROP TABLE IF EXISTS gauged_data;
            DROP TABLE IF EXISTS gauged_keys;
            DROP TABLE IF EXISTS gauged_writer_history;
            DROP TABLE IF EXISTS gauged_cache;
            DROP TABLE IF EXISTS gauged_statistics;
            DROP TABLE IF EXISTS gauged_metadata''')
        self.db.commit()

    def add_namespace_statistics(self, namespace, offset, data_points, byte_count):
        '''Update namespace statistics for the period identified by
        offset'''
        execute = self.cursor.execute
        execute('''INSERT OR IGNORE INTO gauged_statistics
            VALUES (?, ?, 0, 0)''', ( namespace, offset ))
        execute('''UPDATE gauged_statistics SET data_points = data_points + ?,
            byte_count = byte_count + ? WHERE namespace = ? AND offset = ?''',
            ( data_points, byte_count, namespace, offset ))

    def get_namespace_statistics(self, namespace, start_offset, end_offset):
        '''Get namespace statistics for the period between start_offset and
        end_offset (inclusive)'''
        cursor = self.cursor
        cursor.execute('''SELECT SUM(data_points), SUM(byte_count)
            FROM gauged_statistics WHERE namespace = ? AND offset
            BETWEEN ? AND ?''', (namespace, start_offset, end_offset))
        return [ long(count or 0) for count in cursor.fetchone() ]

########NEW FILE########
__FILENAME__ = gauged
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from types import StringType
from time import time
from warnings import warn
from .writer import Writer
from .context import Context
from .drivers import get_driver, SQLiteDriver
from .utilities import Time
from .aggregates import Aggregate
from .config import Config
from .errors import (GaugedVersionMismatchError, GaugedBlockSizeMismatch,
    GaugedSchemaError)
from .version import __version__

class Gauged(object):
    '''Read and write gauge data'''

    VERSION = __version__

    SECOND = Time.SECOND
    MINUTE = Time.MINUTE
    HOUR = Time.HOUR
    DAY = Time.DAY
    WEEK = Time.WEEK
    NOW = Time()

    ERROR = Writer.ERROR
    IGNORE = Writer.IGNORE
    REWRITE = Writer.REWRITE

    AGGREGATES = Aggregate.ALL
    MIN = Aggregate.MIN
    MAX = Aggregate.MAX
    SUM = Aggregate.SUM
    MEAN = Aggregate.MEAN
    STDDEV = Aggregate.STDDEV
    PERCENTILE = Aggregate.PERCENTILE
    MEDIAN = Aggregate.MEDIAN
    COUNT = Aggregate.COUNT

    def __init__(self, driver=None, config=None, **kwargs):
        in_memory = driver is None
        if in_memory:
            driver = SQLiteDriver.MEMORY
        if type(driver) == StringType:
            driver = get_driver(driver)
        if config is None:
            config = Config()
        if len(kwargs):
            config.update(**kwargs)
        self.driver = driver
        self.config = config
        self.valid_schema = False
        if in_memory:
            self.sync()

    @property
    def writer(self):
        '''Create a new writer instance'''
        self.check_schema()
        return Writer(self.driver, self.config)

    def value(self, key, timestamp=None, namespace=None):
        '''Get the value of a gauge at the specified time'''
        return self.make_context(key=key, end=timestamp,
            namespace=namespace).value()

    def aggregate(self, key, aggregate, start=None, end=None,
            namespace=None, percentile=None):
        '''Get an aggregate of all gauge data stored in the specified date range'''
        return self.make_context(key=key, aggregate=aggregate, start=start,
            end=end, namespace=namespace,
            percentile=percentile).aggregate()

    def value_series(self, key, start=None, end=None, interval=None,
            namespace=None, cache=None):
        '''Get a time series of gauge values'''
        return self.make_context(key=key, start=start, end=end,
            interval=interval, namespace=namespace, cache=cache).value_series()

    def aggregate_series(self, key, aggregate, start=None, end=None,
            interval=None, namespace=None, cache=None, percentile=None):
        '''Get a time series of gauge aggregates'''
        return self.make_context(key=key, aggregate=aggregate, start=start,
            end=end, interval=interval, namespace=namespace, cache=cache,
            percentile=percentile).aggregate_series()

    def keys(self, prefix=None, limit=None, offset=None, namespace=None):
        '''Get gauge keys'''
        return self.make_context(prefix=prefix, limit=limit, offset=offset,
            namespace=namespace).keys()

    def namespaces(self):
        '''Get a list of namespaces'''
        return self.driver.get_namespaces()

    def statistics(self, start=None, end=None, namespace=None):
        '''Get write statistics for the specified namespace and date range'''
        return self.make_context(start=start, end=end,
            namespace=namespace).statistics()

    def sync(self):
        '''Create the necessary schema'''
        self.driver.create_schema()
        self.driver.set_metadata({
            'current_version': Gauged.VERSION,
            'initial_version': Gauged.VERSION,
            'block_size': self.config.block_size,
            'resolution': self.config.resolution,
            'created_at': long(time() * 1000)
        }, replace=False)

    def metadata(self):
        '''Get gauged metadata'''
        try:
            metadata = self.driver.all_metadata()
        except: # pylint: disable=W0702
            metadata = {}
        return metadata

    def migrate(self):
        '''Migrate an old Gauged schema to the current version. This is
        just a placeholder for now'''
        self.driver.set_metadata({ 'current_version': Gauged.VERSION })

    def make_context(self, **kwargs):
        '''Create a new context for reading data'''
        self.check_schema()
        return Context(self.driver, self.config, **kwargs)

    def check_schema(self):
        '''Check the schema exists and matches configuration'''
        if self.valid_schema:
            return
        config = self.config
        metadata = self.metadata()
        if 'current_version' not in metadata:
            raise GaugedSchemaError('Gauged schema not found, try a gauged.sync()')
        if metadata['current_version'] != Gauged.VERSION:
            msg = 'The schema is version %s while this Gauged is version %s. '
            msg += 'Try upgrading Gauged and/or running gauged.migrate()'
            msg = msg % (metadata['current_version'], Gauged.VERSION)
            raise GaugedVersionMismatchError(msg)
        expected_block_size = '%s/%s' % (config.block_size, config.resolution)
        block_size = '%s/%s' % (metadata['block_size'], metadata['resolution'])
        if block_size != expected_block_size:
            msg = 'Expected %s and got %s' % (expected_block_size, block_size)
            warn(msg, GaugedBlockSizeMismatch)
        self.valid_schema = True

########NEW FILE########
__FILENAME__ = lru
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

class LRU(object):
    '''A least recently used cache'''

    def __init__(self, maximum):
        self.maximum = maximum
        self.data = {}
        self.head = None
        self.tail = None

    def clear(self):
        while self.head is not None:
            del self[self.head.key]

    def __contains__(self, key):
        return key in self.data

    def __getitem__(self, key):
        value = self.data[key].value
        self[key] = value
        return value

    def __setitem__(self, key, value):
        if key in self.data:
            del self[key]
        obj = LRUNode(self.tail, key, value)
        if not self.head:
            self.head = obj
        if self.tail:
            self.tail.next = obj
        self.tail = obj
        self.data[key] = obj
        if len(self.data) > self.maximum:
            head = self.head
            head.next.prev = None
            self.head = head.next
            head.next = None
            del self.data[head.key]
            del head

    def __delitem__(self, key):
        obj = self.data[key]
        if obj.prev:
            obj.prev.next = obj.next
        else:
            self.head = obj.next
        if obj.next:
            obj.next.prev = obj.prev
        else:
            self.tail = obj.prev
        del self.data[key]

class LRUNode(object):
    '''A node in the LRU cache'''

    __slots__ = ['prev', 'next', 'key', 'value']

    def __init__(self, prev, key, value):
        self.prev = prev
        self.key = key
        self.value = value
        self.next = None

########NEW FILE########
__FILENAME__ = statistics
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

class Statistics(object):
    '''A wrapper for the result of a statistics() operation'''

    __slots__ = [ 'namespace', 'start', 'end', 'data_points', 'byte_count' ]

    def __init__(self, namespace=0, start=0, end=0, data_points=0, byte_count=0):
        self.namespace = namespace
        self.start = start
        self.end = end
        self.data_points = data_points
        self.byte_count = byte_count

    def __repr__(self):
        instance = 'Statistics(namespace=%s, start=%s, end=%s, '
        instance += 'data_points=%s, byte_count=%s)'
        return instance % (self.namespace, self.start, self.end,
            self.data_points, self.byte_count)

########NEW FILE########
__FILENAME__ = time_series
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from types import DictType
from ..utilities import table_repr, to_datetime

class TimeSeries(object):
    '''A representation of a time series with a fixed interval'''

    def __init__(self, points):
        '''Initialise the time series. `points` is expected to be either a list of
        tuples where each tuple represents a point (timestamp, value), or a dict where
        the keys are timestamps. Timestamps are expected to be in milliseconds'''
        if type(points) == DictType:
            points = points.items()
        self.points = sorted(points)

    @property
    def timestamps(self):
        '''Get all timestamps from the series'''
        return [ point[0] for point in self.points ]

    @property
    def dates(self):
        '''Get all dates from the time series as `datetime` instances'''
        return [ to_datetime(timestamp) for timestamp, _ in self.points ]

    @property
    def values(self):
        '''Get all values from the time series'''
        return [ point[1] for point in self.points ]

    @property
    def interval(self):
        if len(self.points) <= 1:
            return None
        return self.points[1][0] - self.points[0][0]

    def map(self, fn):
        '''Run a map function across all y points in the series'''
        return TimeSeries([ (x, fn(y)) for x, y in self.points ])

    def __abs__(self):
        return TimeSeries([ (x, abs(y)) for x, y in self.points ])

    def __round__(self, n=0):
        return TimeSeries([ (x, round(y, n)) for x, y in self.points ])

    def round(self, n=0):
        # Manual delegation for v2.x
        return self.__round__(n)

    def __add__(self, operand):
        if not isinstance(operand, TimeSeries):
            return TimeSeries([ ( x, y + operand ) for x, y in self.points ])
        lookup = dict(operand.points)
        return TimeSeries([ ( x, y + lookup[x] ) for x, y in self.points if x in lookup ])

    def __iadd__(self, operand):
        if not isinstance(operand, TimeSeries):
            self.points = [ ( x, y + operand ) for x, y in self.points ]
        else:
            lookup = dict(operand.points)
            self.points = [ ( x, y + lookup[x] ) for x, y in self.points if x in lookup ]
        return self

    def __sub__(self, operand):
        if not isinstance(operand, TimeSeries):
            return TimeSeries([ ( x, y - operand ) for x, y in self.points ])
        lookup = dict(operand.points)
        return TimeSeries([ ( x, y - lookup[x] ) for x, y in self.points if x in lookup ])

    def __isub__(self, operand):
        if not isinstance(operand, TimeSeries):
            self.points = [ ( x, y - operand ) for x, y in self.points ]
        else:
            lookup = dict(operand.points)
            self.points = [ ( x, y - lookup[x] ) for x, y in self.points if x in lookup ]
        return self

    def __mul__(self, operand):
        if not isinstance(operand, TimeSeries):
            return TimeSeries([ ( x, y * operand ) for x, y in self.points ])
        lookup = dict(operand.points)
        return TimeSeries([ ( x, y * lookup[x] ) for x, y in self.points if x in lookup ])

    def __imul__(self, operand):
        if not isinstance(operand, TimeSeries):
            self.points = [ ( x, y * operand ) for x, y in self.points ]
        else:
            lookup = dict(operand.points)
            self.points = [ ( x, y * lookup[x] ) for x, y in self.points if x in lookup ]
        return self

    def __div__(self, operand):
        if not isinstance(operand, TimeSeries):
            return TimeSeries([ ( x, float(y) / operand ) for x, y in self.points ])
        lookup = dict(operand.points)
        return TimeSeries([ ( x, float(y) / lookup[x] ) for x, y in self.points if x in lookup ])

    def __idiv__(self, operand):
        if not isinstance(operand, TimeSeries):
            self.points = [ ( x, float(y) / operand ) for x, y in self.points ]
        else:
            lookup = dict(operand.points)
            self.points = [ ( x, float(y) / lookup[x] ) for x, y in self.points if x in lookup ]
        return self

    def __pow__(self, operand):
        if not isinstance(operand, TimeSeries):
            return TimeSeries([ ( x, y ** operand ) for x, y in self.points ])
        lookup = dict(operand.points)
        return TimeSeries([ ( x, y ** lookup[x] ) for x, y in self.points if x in lookup ])

    def __ipow__(self, operand):
        if not isinstance(operand, TimeSeries):
            self.points = [ ( x, y ** operand ) for x, y in self.points ]
        else:
            lookup = dict(operand.points)
            self.points = [ ( x, y ** lookup[x] ) for x, y in self.points if x in lookup ]
        return self

    def __getitem__(self, x):
        return dict(self.points)[x]

    def __iter__(self):
        return iter(self.points)

    def __len__(self):
        return len(self.points)

    def __repr__(self):
        if not len(self.points):
            return 'TimeSeries([])'
        data = {}
        columns = [ 'Value' ]
        rows = []
        for date, value in self.points:
            date = to_datetime(date).isoformat(' ')
            rows.append(date)
            data[date] = { 'Value': value }
        return table_repr(columns, rows, data)

########NEW FILE########
__FILENAME__ = float_array
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from types import ListType, BufferType
from ctypes import (create_string_buffer, c_void_p, pythonapi, py_object, byref,
    cast, addressof, c_char, c_size_t)
from ..bridge import Gauged, FloatPtr
from ..errors import GaugedUseAfterFreeError
from ..utilities import IS_PYPY

class FloatArray(object):
    '''An array of C floats'''

    ALLOCATIONS = 0

    __slots__ = [ '_ptr' ]

    def __init__(self, buf=None, length=0):
        '''Create a new array. The constructor accepts a buffer + byte_length or a
        python list of floats'''
        if type(buf) == ListType:
            items = buf
            buf = None
        else:
            items = None
        if buf is not None:
            if IS_PYPY:
                buf = create_string_buffer(str(buf))
            if type(buf) == BufferType:
                address = c_void_p()
                buf_length = c_size_t()
                pythonapi.PyObject_AsReadBuffer(py_object(buf),
                    byref(address), byref(buf_length))
                buf_length = buf_length.value
                buf = address
            buf = cast(buf, FloatPtr)
        self._ptr = Gauged.array_import(buf, length)
        FloatArray.ALLOCATIONS += 1
        if self._ptr is None:
            raise MemoryError
        if items is not None:
            for item in items:
                self.append(item)

    @property
    def ptr(self):
        '''Get the array's C pointer'''
        if self._ptr is None:
            raise GaugedUseAfterFreeError
        return self._ptr

    def free(self):
        '''Free the underlying C array'''
        if self._ptr is None:
            return
        Gauged.array_free(self.ptr)
        FloatArray.ALLOCATIONS -= 1
        self._ptr = None

    def values(self):
        '''Get all floats in the array as a list'''
        return list(self)

    def append(self, member):
        '''Append a float to the array'''
        if not Gauged.array_append(self.ptr, member):
            raise MemoryError

    def byte_length(self):
        '''Get the byte length of the array'''
        return self.ptr.contents.length * 4

    def buffer(self, byte_offset=0):
        '''Get a copy of the array buffer'''
        contents = self.ptr.contents
        ptr = addressof(contents.buffer.contents) + byte_offset
        length = contents.length * 4 - byte_offset
        return buffer((c_char * length).from_address(ptr).raw) if length else None

    def clear(self):
        '''Clear the array'''
        self.ptr.contents.length = 0

    def __getitem__(self, offset):
        '''Get the member at the specified offset'''
        contents = self.ptr.contents
        if offset >= contents.length:
            raise IndexError
        return contents.buffer[offset]

    def __len__(self):
        '''Get the number of floats in the array'''
        return self.ptr.contents.length

    def __repr__(self):
        return '[' + ', '.join(( str(value) for value in self )) + ']'

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        self.free()

########NEW FILE########
__FILENAME__ = sparse_map
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from types import DictType, BufferType
from ctypes import (create_string_buffer, c_void_p, pythonapi, py_object, byref,
    cast, c_uint32, addressof, c_char, c_size_t, c_float)
from ..bridge import Gauged, MapPtr, Uint32Ptr, FloatPtr
from ..utilities import IS_PYPY
from ..errors import GaugedUseAfterFreeError

class SparseMap(object):
    '''A structure which adds another dimension to FloatArray. The
    Map encodes a FloatArray + offset contiguously to improve cache
    locality'''

    ALLOCATIONS = 0

    __slots__ = [ '_ptr' ]

    def __init__(self, buf=None, length=0):
        '''Create a new SparseMap. The constructor accepts a buffer and
        byte_length, a python dict containing { offset: array, ... }, or a
        pointer to a C structure'''
        if type(buf) == DictType:
            items = buf
            buf = None
        else:
            items = None
        if type(buf) == MapPtr:
            self._ptr = buf
        else:
            if buf is not None:
                if IS_PYPY:
                    buf = create_string_buffer(str(buf))
                if type(buf) == BufferType:
                    address = c_void_p()
                    buf_length = c_size_t()
                    pythonapi.PyObject_AsReadBuffer(py_object(buf),
                        byref(address), byref(buf_length))
                    buf_length = buf_length.value
                    buf = address
                buf = cast(buf, Uint32Ptr)
            self._ptr = Gauged.map_import(buf, length)
        if self._ptr is None:
            raise MemoryError
        SparseMap.ALLOCATIONS += 1
        if items is not None:
            for position in sorted(items.keys()):
                self.append(position, items[position])

    @property
    def ptr(self):
        '''Get the map's C pointer'''
        if self._ptr is None:
            raise GaugedUseAfterFreeError
        return self._ptr

    def free(self):
        '''Free the map'''
        if self._ptr is None:
            return
        Gauged.map_free(self.ptr)
        SparseMap.ALLOCATIONS -= 1
        self._ptr = None

    def append(self, position, array):
        '''Append an array to the end of the map. The position
        must be greater than any positions in the map'''
        if not Gauged.map_append(self.ptr, position, array.ptr):
            raise MemoryError

    def slice(self, start=0, end=0):
        '''Slice the map from [start, end)'''
        tmp = Gauged.map_new()
        if tmp is None:
            raise MemoryError
        if not Gauged.map_concat(tmp, self.ptr, start, end, 0):
            Gauged.map_free(tmp) # pragma: no cover
            raise MemoryError
        return SparseMap(tmp)

    def concat(self, operand, start=0, end=0, offset=0):
        '''Concat a map. You can also optionally slice the operand map
        and apply an offset to each position before concatting'''
        if not Gauged.map_concat(self.ptr, operand.ptr, start, end, offset):
            raise MemoryError

    def byte_length(self):
        '''Get the byte length of the map'''
        return self.ptr.contents.length * 4

    def buffer(self, byte_offset=0):
        '''Get a copy of the map buffer'''
        contents = self.ptr.contents
        ptr = addressof(contents.buffer.contents) + byte_offset
        length = contents.length * 4 - byte_offset
        return buffer((c_char * length).from_address(ptr).raw) if length else None

    def clear(self):
        '''Clear the map'''
        self.ptr.contents.length = 0

    def first(self):
        '''Get the first float in the map'''
        return Gauged.map_first(self.ptr)

    def last(self):
        '''Get the last float in the map'''
        return Gauged.map_last(self.ptr)

    def sum(self):
        '''Get the sum of all floats in the map'''
        return Gauged.map_sum(self.ptr)

    def min(self):
        '''Get the minimum of all floats in the map'''
        return Gauged.map_min(self.ptr)

    def max(self):
        '''Get the maximum of all floats in the map'''
        return Gauged.map_max(self.ptr)

    def mean(self):
        '''Get the maximum of all floats in the map'''
        return Gauged.map_mean(self.ptr)

    def stddev(self):
        '''Get the maximum of all floats in the map'''
        return Gauged.map_stddev(self.ptr)

    def count(self):
        '''Get the maximum of all floats in the map'''
        return Gauged.map_count(self.ptr)

    def sum_of_squares(self, mean):
        '''Get the sum of squared differences compared to the specified
        mean'''
        return Gauged.map_sum_of_squares(self.ptr, c_float(mean))

    def percentile(self, percentile):
        '''Get a percentile of all floats in the map. Since the sorting is
        done in-place, the map is no longer safe to use after calling this
        or median()'''
        percentile = float(percentile)
        if percentile != percentile or percentile < 0 or percentile > 100:
            raise ValueError('Expected a 0 <= percentile <= 100')
        result = c_float()
        if not Gauged.map_percentile(self.ptr, percentile, byref(result)):
            raise MemoryError
        return result.value

    def median(self):
        '''Get the median of all floats in the map'''
        return self.percentile(50)

    def items(self):
        '''Get a dict representing map items => { offset: array, ... }'''
        return dict(self.iteritems())

    def iteritems(self):
        '''Get a generator which yields (offset, array)'''
        current_buf = self.ptr.contents.buffer
        length = self.ptr.contents.length
        seen_length = 0
        header = c_size_t()
        position = c_uint32()
        arraylength = c_size_t()
        arrayptr = FloatPtr()
        header_ = byref(header)
        position_ = byref(position)
        arraylength_ = byref(arraylength)
        arrayptr_ = byref(arrayptr)
        advance = Gauged.map_advance
        while seen_length < length:
            current_buf = advance(current_buf, header_, position_,
                arraylength_, arrayptr_)
            seen_length += header.value + arraylength.value
            address = addressof(arrayptr.contents)
            arr = (c_float * arraylength.value).from_address(address)
            yield position.value, list(arr)

    def __repr__(self):
        rows = []
        for position, values in self.iteritems():
            row = '[ %s ] = [%s]' % (position, ', '.join(( str(v) for v in values )))
            rows.append(row)
        return '\n'.join(rows)

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        self.free()

########NEW FILE########
__FILENAME__ = utilities
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from time import time
from datetime import datetime
from sys import builtin_module_names
from types import StringType, UnicodeType

IS_PYPY = '__pypy__' in builtin_module_names

def to_bytes(value):
    '''Get a byte array representing the value'''
    if type(value) == UnicodeType:
        return value.encode('utf8')
    elif type(value) != StringType:
        return str(value)
    return value

class Time(object):
    '''Common time constants in milliseconds'''

    SECOND = 1000
    MINUTE = 60 * SECOND
    HOUR = 60 * MINUTE
    DAY = 24 * HOUR
    WEEK = 7 * DAY

    def __get__(self, instance, owner):
        return long(time() * 1000)

def table_repr(columns, rows, data, padding=2):
    '''Generate a table for cli output'''
    padding = ' ' * padding
    column_lengths = [ len(column) for column in columns ]
    for row in rows:
        for i, column in enumerate(columns):
            item = str(data[row][column])
            column_lengths[i] = max(len(item), column_lengths[i])
    max_row_length = max(( len(row) for row in rows )) if len(rows) else 0
    table_row = ' ' * max_row_length
    for i, column in enumerate(columns):
        table_row += padding + column.rjust(column_lengths[i])
    table_rows = [ table_row ]
    for row in rows:
        table_row = row.rjust(max_row_length)
        for i, column in enumerate(columns):
            item = str(data[row][column])
            table_row += padding + item.rjust(column_lengths[i])
        table_rows.append(table_row)
    return '\n'.join(table_rows)

def to_datetime(milliseconds):
    '''Convert a timestamp in milliseconds to a datetime'''
    return datetime.fromtimestamp(milliseconds // 1000)

########NEW FILE########
__FILENAME__ = version
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

__version__ = '0.4.0'

__version_info__ = tuple([ int(v) for v in __version__.split('.') ])

########NEW FILE########
__FILENAME__ = writer
'''
Gauged
https://github.com/chriso/gauged (MIT Licensed)
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from time import time
from threading import Timer
from types import StringType, UnicodeType, DictType
from collections import defaultdict
from pprint import pprint
from ctypes import c_uint32, byref
from .structures import SparseMap
from .lru import LRU
from ctypes import c_float
from .errors import (GaugedAppendOnlyError, GaugedKeyOverflowError, GaugedNaNError,
    GaugedUseAfterFreeError)
from .bridge import Gauged
from .results import Statistics
from .utilities import to_bytes

class Writer(object):
    '''Handle queueing and writes to the specified data store'''

    ERROR = 0
    IGNORE = 1
    REWRITE = 2

    KEY_OVERFLOW = -1

    ALLOCATIONS = 0

    def __init__(self, driver, config):
        self.driver = driver
        self.config = config
        self.key_cache = LRU(config.key_cache_size)
        self.current_array = 0
        self.current_block = 0
        self.whitelist = None
        self.flush_now = False
        self.statistics = defaultdict(Statistics)
        if config.flush_seconds:
            self.start_flush_timer()
        self.flush_daemon = None
        self.writer = None
        self.allocate_writer()

    def add(self, data, value=None, timestamp=None, namespace=None, debug=False):
        '''Queue a gauge or gauges to be written'''
        if value is not None:
            return self.add(((data, value),), timestamp=timestamp,
                namespace=namespace, debug=debug)
        writer = self.writer
        if writer is None:
            raise GaugedUseAfterFreeError
        if timestamp is None:
            timestamp = long(time() * 1000)
        config = self.config
        block_size = config.block_size
        this_block = timestamp // block_size
        this_array = (timestamp % block_size) // config.resolution
        if namespace is None:
            namespace = config.namespace
        if this_block < self.current_block or \
                (this_block == self.current_block \
                    and this_array < self.current_array):
            if config.append_only_violation == Writer.ERROR:
                msg = 'Gauged is append-only; timestamps must be increasing'
                raise GaugedAppendOnlyError(msg)
            elif config.append_only_violation == Writer.REWRITE:
                this_block = self.current_block
                this_array = self.current_array
            else:
                return
        if type(data) == UnicodeType:
            data = data.encode('utf8')
        if debug:
            return self.debug(timestamp, namespace, data)
        if this_block > self.current_block:
            self.flush_blocks()
            self.current_block = this_block
            self.current_array = this_array
        elif this_array > self.current_array:
            if not Gauged.writer_flush_arrays(writer, self.current_array):
                raise MemoryError
            self.current_array = this_array
        data_points = 0
        namespace_statistics = self.statistics[namespace]
        whitelist = config.key_whitelist
        skip_long_keys = config.key_overflow == Writer.IGNORE
        skip_gauge_nan = config.gauge_nan == Writer.IGNORE
        if type(data) == StringType and skip_gauge_nan \
                and skip_long_keys and whitelist is None: # fast path
            data_points = c_uint32(0)
            if not Gauged.writer_emit_pairs(writer, namespace, data, \
                    byref(data_points)):
                raise MemoryError
            data_points = data_points.value
        else:
            if type(data) == DictType:
                data = data.iteritems()
            elif type(data) == StringType:
                data = self.parse_query(data)
            emit = Gauged.writer_emit
            for key, value in data:
                key = to_bytes(key)
                if whitelist is not None and key not in whitelist:
                    continue
                try:
                    value = float(value)
                except ValueError:
                    value = float('nan')
                if value != value: # NaN?
                    if skip_gauge_nan:
                        continue
                    raise GaugedNaNError
                success = emit(writer, namespace, key, c_float(value))
                if success != 1:
                    if not success:
                        raise MemoryError
                    elif success == Writer.KEY_OVERFLOW and not skip_long_keys:
                        msg = 'Key is larger than the driver allows '
                        msg += '(%s)' % key
                        raise GaugedKeyOverflowError(msg)
                data_points += 1
        namespace_statistics.data_points += data_points
        if self.flush_now:
            self.flush()

    def flush(self):
        '''Flush all pending gauges'''
        writer = self.writer
        if writer is None:
            raise GaugedUseAfterFreeError
        self.flush_writer_position()
        keys = self.translate_keys()
        blocks = []
        current_block = self.current_block
        statistics = self.statistics
        driver = self.driver
        flags = 0 # for future extensions, e.g. block compression
        for namespace, key, block in self.pending_blocks():
            length = block.byte_length()
            if not length:
                continue
            key_id = keys[( namespace, key )]
            statistics[namespace].byte_count += length
            blocks.append((namespace, current_block, key_id, block.buffer(), flags))
        if self.config.overwrite_blocks:
            driver.replace_blocks(blocks)
        else:
            driver.insert_or_append_blocks(blocks)
            if not Gauged.writer_flush_maps(writer, True):
                raise MemoryError
        update_namespace = driver.add_namespace_statistics
        for namespace, stats in statistics.iteritems():
            update_namespace(namespace, self.current_block,
                stats.data_points, stats.byte_count)
        statistics.clear()
        driver.commit()
        self.flush_now = False

    def resume_from(self):
        '''Get a timestamp representing the position just after the last
        written gauge'''
        position = self.driver.get_writer_position(self.config.writer_name)
        return position + self.config.resolution if position else 0

    def clear_from(self, timestamp):
        '''Clear all data from `timestamp` onwards. Note that the timestamp
        is rounded down to the nearest block boundary'''
        block_size = self.config.block_size
        offset, remainder = timestamp // block_size, timestamp % block_size
        if remainder:
            raise ValueError('Timestamp must be on a block boundary')
        self.driver.clear_from(offset, timestamp)

    def parse_query(self, query):
        '''Parse a query string and return an iterator which yields (key, value)'''
        writer = self.writer
        if writer is None:
            raise GaugedUseAfterFreeError
        Gauged.writer_parse_query(writer, query)
        position = 0
        writer_contents = writer.contents
        size = writer_contents.buffer_size
        pointers = writer_contents.buffer
        while position < size:
            yield pointers[position], pointers[position+1]
            position += 2

    def debug(self, timestamp, namespace, data): # pragma: no cover
        print 'Timestamp: %s, Namespace: %s' % (timestamp, namespace)
        if type(data) == StringType:
            data = self.parse_query(data)
        elif type(data) == DictType:
            data = data.iteritems()
        whitelist = self.config.key_whitelist
        if whitelist is not None:
            data = { key: value for key, value in data if key in whitelist }
        else:
            data = dict(data)
        pprint(data)
        print ''

    def flush_writer_position(self):
        config = self.config
        timestamp = long(self.current_block) * config.block_size \
            + long(self.current_array) * config.resolution
        if timestamp:
            self.driver.set_writer_position(config.writer_name, timestamp)

    def translate_keys(self):
        keys = list(self.pending_keys())
        if not len(keys):
            return {}
        key_cache = self.key_cache
        to_translate = [ key for key in keys if key not in key_cache ]
        self.driver.insert_keys(to_translate)
        ids = self.driver.lookup_ids(to_translate)
        for key in keys:
            if key in key_cache:
                ids[key] = key_cache[key]
        for key, id_ in ids.iteritems():
            key_cache[key] = id_
        return ids

    def flush_blocks(self):
        writer = self.writer
        if not Gauged.writer_flush_arrays(writer, self.current_array):
            raise MemoryError
        self.flush()
        if not Gauged.writer_flush_maps(writer, False):
            raise MemoryError

    def start_flush_timer(self):
        period = self.config.flush_seconds
        self.flush_daemon = Timer(period, self.flush_timer_tick)
        self.flush_daemon.setDaemon(True)
        self.flush_daemon.start()

    def flush_timer_tick(self):
        self.flush_now = True
        self.start_flush_timer()

    def pending_keys(self):
        pending = self.writer.contents.pending.contents
        head = pending.head
        while True:
            if not head:
                break
            node = head.contents
            yield node.namespace, node.key
            head = node.next

    def pending_blocks(self):
        block = SparseMap()
        initial_ptr = block._ptr
        pending = self.writer.contents.pending.contents
        head = pending.head
        while True:
            if not head:
                break
            node = head.contents
            block._ptr = node.map
            yield node.namespace, node.key, block
            head = node.next
        block._ptr = initial_ptr
        block.free()

    def allocate_writer(self):
        self.current_array = 0
        self.current_block = 0
        if self.writer is None:
            self.writer = Gauged.writer_new(self.driver.MAX_KEY or 0)
            Writer.ALLOCATIONS += 1
            if not self.writer:
                raise MemoryError

    def cleanup(self):
        if self.flush_daemon is not None:
            self.flush_daemon.cancel()
            self.flush_daemon = None
        self.flush_blocks()
        Gauged.writer_free(self.writer)
        Writer.ALLOCATIONS -= 1
        self.writer = None
        self.key_cache.clear()

    def __enter__(self):
        self.allocate_writer()
        return self

    def __exit__(self, type_, value, traceback):
        self.cleanup()

########NEW FILE########
__FILENAME__ = test_case
'''
Gauged - https://github.com/chriso/gauged
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

import unittest

class TestCase(unittest.TestCase):
    '''A base class for all Gauged tests'''

########NEW FILE########
__FILENAME__ = test_driver
'''
Gauged - https://github.com/chriso/gauged
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from hashlib import sha1
from .test_case import TestCase

class TestDriver(TestCase):
    '''Test each available driver'''

    # Override this with an instantiated driver
    driver = None

    def setUp(self):
        self.driver.clear_schema()

    def test_insert_keys(self):
        self.driver.insert_keys([ (1, 'foo') ])
        self.driver.insert_keys([ (1, 'bar') ])
        self.driver.insert_keys([ (2, 'foobar') ])
        self.driver.insert_keys([ (3, 'Foo') ])
        ids = self.driver.lookup_ids([ (1, 'foo'), (1, 'bar'), (1, 'foobar') ])
        self.assertEqual(ids[(1, 'foo')], 1)
        self.assertEqual(ids[(1, 'bar')], 2)
        self.assertEqual(ids[(1, 'foobar')], None)
        self.assertEqual(len(ids), 3)
        ids = self.driver.lookup_ids([ (2, 'foo'), (2, 'foobar') ])
        self.assertEqual(ids[(2, 'foo')], None)
        self.assertEqual(ids[(2, 'foobar')], 3)
        self.assertEqual(len(ids), 2)
        ids = self.driver.lookup_ids([ (3, 'Foo') ])
        self.assertEqual(ids[(3, 'Foo')], 4)
        self.assertEqual(len(ids), 1)

    def test_insert_blocks(self):
        blocks = [( 0,  1, 2, 'foo', 0x10 ),
                  ( 1,  2, 3, 'bar', 0x10 )]
        self.driver.replace_blocks(blocks)
        buf, flags = self.driver.get_block(0, 1, 2)
        self.assertEqual(str(buf), 'foo')
        self.assertEqual(flags, 0x10)
        self.assertEqual(str(self.driver.get_block(1, 2, 3)[0]), 'bar')
        self.driver.replace_blocks([( 0,  1, 2, '\xe4\x00\x12', 0x10 )])
        self.assertEqual(str(self.driver.get_block(0, 1, 2)[0]), '\xe4\x00\x12')
        self.driver.insert_or_append_blocks([( 0,  1, 2, '\xe4\x00\x12', 0x10 )])
        self.assertEqual(str(self.driver.get_block(0, 1, 2)[0]), '\xe4\x00\x12\xe4\x00\x12')

    def test_keys(self):
        self.driver.insert_keys([ (1, 'bar') ])
        self.driver.insert_keys([ (1, 'foobar') ])
        self.driver.insert_keys([ (1, 'fooqux') ])
        self.driver.insert_keys([ (2, 'foo') ])
        keys = self.driver.keys(1)
        self.assertListEqual(keys, [ 'bar', 'foobar', 'fooqux' ])
        keys = self.driver.keys(1, prefix='foo')
        self.assertListEqual(keys, [ 'foobar', 'fooqux' ])
        keys = self.driver.keys(1, prefix='foo', limit=1)
        self.assertListEqual(keys, [ 'foobar' ])
        keys = self.driver.keys(1, prefix='foo', limit=1, offset=1)
        self.assertListEqual(keys, [ 'fooqux' ])
        keys = self.driver.keys(2, prefix='foo')
        self.assertListEqual(keys, [ 'foo' ])
        keys = self.driver.keys(2, prefix='bar')
        self.assertListEqual(keys, [ ])

    def test_insert_or_append(self):
        blocks = [( 0,  1, 1, 'foo', 0x10 )]
        self.driver.replace_blocks(blocks)
        blocks = [( 0,  1, 1, 'bar', 0x10 )]
        self.driver.insert_or_append_blocks(blocks)
        buf, flags = self.driver.get_block(0, 1, 1)
        self.assertEqual(str(buf), 'foobar')
        self.assertEqual(flags, 0x10)

    def test_history(self):
        self.assertEqual(self.driver.get_writer_position('foo'), 0)
        self.driver.set_writer_position('foo', 100)
        self.assertEqual(self.driver.get_writer_position('bar'), 0)
        self.assertEqual(self.driver.get_writer_position('foo'), 100)
        self.driver.set_writer_position('foo', 10)
        self.assertEqual(self.driver.get_writer_position('foo'), 10)
        self.driver.set_writer_position('bar', 1000)
        self.assertEqual(self.driver.get_writer_position('bar'), 1000)

    def test_remove_namespace(self):
        self.driver.remove_namespace(1)
        blocks = [( 0,  1, 2, 'foo', 0x10 ),
                  ( 1,  2, 3, 'bar', 0x10 )]
        self.driver.replace_blocks(blocks)
        self.assertEqual(str(self.driver.get_block(0, 1, 2)[0]), 'foo')
        self.assertEqual(str(self.driver.get_block(1, 2, 3)[0]), 'bar')
        self.driver.remove_namespace(1)
        self.assertEqual(str(self.driver.get_block(0, 1, 2)[0]), 'foo')
        self.assertEqual(self.driver.get_block(1, 2, 3)[0], None)

    def test_cache(self):
        id_ = sha1('foobar').digest()
        self.assertSequenceEqual(self.driver.get_cache(0, id_, 2, 3, 4), ())
        self.driver.add_cache(0, id_, 2, [(3, 4), (4, 6)])
        self.assertSequenceEqual(self.driver.get_cache(0, id_, 2, 3, 4),
            ((3, 4), (4, 6)))
        self.driver.add_cache(1, id_, 2, [(3, 4)])
        self.assertSequenceEqual(self.driver.get_cache(1, id_, 2, 3, 4), ((3, 4),))
        self.driver.remove_cache(0)
        self.assertSequenceEqual(self.driver.get_cache(0, id_, 2, 3, 4), ())
        self.assertSequenceEqual(self.driver.get_cache(1, id_, 2, 3, 4), ((3, 4),))

    def test_namespace_statistics(self):
        min_block, max_block = self.driver.block_offset_bounds(0)
        self.assertEqual(min_block, None)
        self.assertEqual(max_block, None)
        statistics = self.driver.get_namespace_statistics(0, 0, 0)
        self.assertListEqual(statistics, [ 0, 0 ])
        self.driver.add_namespace_statistics(0, 0, 1, 2)
        self.driver.add_namespace_statistics(0, 0, 6, 7)
        self.driver.add_namespace_statistics(0, 1, 101, 102)
        statistics = self.driver.get_namespace_statistics(0, 0, 0)
        self.assertListEqual(statistics, [ 7, 9 ])
        statistics = self.driver.get_namespace_statistics(0, 0, 1)
        self.assertListEqual(statistics, [ 108, 111 ])
        min_block, max_block = self.driver.block_offset_bounds(0)
        self.assertEqual(min_block, 0)
        self.assertEqual(max_block, 1)
        self.driver.add_namespace_statistics(1, 2, 101, 102)
        min_block, max_block = self.driver.block_offset_bounds(1)
        self.assertEqual(min_block, 2)
        self.assertEqual(max_block, 2)
        min_block, max_block = self.driver.block_offset_bounds(0)
        self.assertEqual(min_block, 0)
        self.assertEqual(max_block, 1)
        self.assertItemsEqual(self.driver.get_namespaces(), [0, 1])

    def test_clear_from(self):
        self.driver.add_namespace_statistics(0, 0, 1, 2)
        self.driver.add_namespace_statistics(1, 1, 4, 5)
        self.driver.add_namespace_statistics(1, 2, 101, 102)
        blocks = [( 0,  1, 2, 'foo', 0x10 ),
                  ( 1,  2, 3, 'bar', 0x10 )]
        self.driver.replace_blocks(blocks)
        id_ = sha1('foobar').digest()
        self.driver.add_cache(0, id_, 5, [(13, 4), (15, 4), (18, 4), (23, 6)])
        self.driver.set_writer_position('foo', 18)
        self.driver.set_writer_position('bar', 22)
        self.driver.clear_from(2, 20)
        buf, flags = self.driver.get_block(0, 1, 2)
        self.assertEqual(str(buf), 'foo')
        self.assertEqual(flags, 0x10)
        self.assertEqual(self.driver.get_block(1, 2, 3)[0], None)
        self.assertEqual(self.driver.get_writer_position('foo'), 18)
        self.assertEqual(self.driver.get_writer_position('bar'), 20)
        self.assertSequenceEqual(self.driver.get_cache(0, id_, 5, 0, 100), [(13, 4)])
        self.assertListEqual(self.driver.get_namespace_statistics(1, 0, 3), [4, 5])

    def test_metadata(self):
        self.assertEqual(self.driver.get_metadata('foobaz'), None)
        self.driver.set_metadata({ 'foo': 'bar', 'bar': 'baz' })
        self.assertEqual(self.driver.get_metadata('foo'), 'bar')
        self.assertEqual(self.driver.get_metadata('bar'), 'baz')
        self.driver.set_metadata({ 'foo': 'qux' })
        self.assertEqual(self.driver.get_metadata('foo'), 'qux')
        self.driver.set_metadata({ 'foo': 'bar', 'qux': 'foobar' }, replace=False)
        self.assertEqual(self.driver.get_metadata('foo'), 'qux')
        self.assertEqual(self.driver.get_metadata('qux'), 'foobar')

########NEW FILE########
__FILENAME__ = test_dsn
'''
Gauged - https://github.com/chriso/gauged
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from gauged.drivers import parse_dsn, SQLiteDriver
from .test_case import TestCase

class TestDSN(TestCase):
    '''Test the driver functions'''

    def test_stripping_dialect_from_schema(self):
        driver = parse_dsn('sqlite+foobar://')[0]
        self.assertIs(driver, SQLiteDriver)

    def test_unknown_driver(self):
        with self.assertRaises(ValueError):
            parse_dsn('foobar://')

    def test_user_and_password(self):
        kwargs = parse_dsn('mysql://root:foo@localhost')[2]
        self.assertEqual(kwargs['user'], 'root')
        self.assertEqual(kwargs['passwd'], 'foo')
        kwargs = parse_dsn('postgresql://root:foo@localhost')[2]
        self.assertEqual(kwargs['user'], 'root')
        self.assertEqual(kwargs['password'], 'foo')

    def test_user_without_password(self):
        kwargs = parse_dsn('mysql://root@localhost')[2]
        self.assertEqual(kwargs['user'], 'root')
        self.assertNotIn('passwd', kwargs)
        kwargs = parse_dsn('postgresql://root@localhost')[2]
        self.assertEqual(kwargs['user'], 'root')
        self.assertNotIn('password', kwargs)

    def test_default_users(self):
        kwargs = parse_dsn('mysql://localhost')[2]
        self.assertEqual(kwargs['user'], 'root')
        kwargs = parse_dsn('postgresql://localhost')[2]
        self.assertEqual(kwargs['user'], 'postgres')

    def test_unix_socket(self):
        kwargs = parse_dsn('mysql:///?unix_socket=/tmp/mysql.sock')[2]
        self.assertEqual(kwargs['unix_socket'], '/tmp/mysql.sock')
        kwargs = parse_dsn('postgresql:///?unix_socket=/tmp/mysql.sock')[2]
        self.assertNotIn('unix_socket', kwargs)
        self.assertEqual(kwargs['host'], '/tmp/mysql.sock')

    def test_no_host_or_port(self):
        kwargs = parse_dsn('mysql://')[2]
        self.assertNotIn('host', kwargs)
        self.assertNotIn('port', kwargs)
        kwargs = parse_dsn('postgresql://')[2]
        self.assertNotIn('host', kwargs)
        self.assertNotIn('port', kwargs)

    def test_hort_without_port(self):
        kwargs = parse_dsn('mysql://localhost')[2]
        self.assertEqual(kwargs['host'], 'localhost')
        self.assertNotIn('port', kwargs)
        kwargs = parse_dsn('postgresql://localhost')[2]
        self.assertEqual(kwargs['host'], 'localhost')
        self.assertNotIn('port', kwargs)

    def test_hort_with_port(self):
        kwargs = parse_dsn('mysql://localhost:123')[2]
        self.assertEqual(kwargs['host'], 'localhost')
        self.assertEqual(kwargs['port'], 123)
        kwargs = parse_dsn('postgresql://localhost:123')[2]
        self.assertEqual(kwargs['host'], 'localhost')
        self.assertEqual(kwargs['port'], 123)

    def test_passing_kwargs(self):
        kwargs = parse_dsn('mysql://localhost?foo=bar')[2]
        self.assertEqual(kwargs['foo'], 'bar')
        kwargs = parse_dsn('postgresql://localhost?foo=bar')[2]
        self.assertEqual(kwargs['foo'], 'bar')

########NEW FILE########
__FILENAME__ = test_gauged
'''
Gauged - https://github.com/chriso/gauged
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

import datetime, random
from math import ceil, floor, sqrt
from time import time, sleep
from warnings import filterwarnings
from gauged import Gauged, Writer, Config
from gauged.errors import (GaugedKeyOverflowError, GaugedDateRangeError, GaugedAppendOnlyError,
    GaugedIntervalSizeError, GaugedNaNError, GaugedUseAfterFreeError,
    GaugedVersionMismatchError, GaugedBlockSizeMismatch, GaugedSchemaError)
from gauged.structures import SparseMap, FloatArray
from types import LongType, IntType
from .test_case import TestCase

filterwarnings('ignore', category=GaugedBlockSizeMismatch)

class TestGauged(TestCase):
    '''Test higher-level functionality in gauged.py'''

    # Override this with an instantiated driver
    driver = None

    def setUp(self):
        SparseMap.ALLOCATIONS = 0
        FloatArray.ALLOCATIONS = 0
        Writer.ALLOCATIONS = 0
        self.driver.clear_schema()

    def tearDown(self):
        self.assertEqual(SparseMap.ALLOCATIONS, 0)
        self.assertEqual(FloatArray.ALLOCATIONS, 0)
        self.assertEqual(Writer.ALLOCATIONS, 0)

    def test_keys(self):
        gauged = Gauged(self.driver)
        with gauged.writer as writer:
            writer.add('foobar', 1, timestamp=1000)
            writer.add('foobaz', 1, timestamp=1000)
            writer.add('bar', 1, timestamp=1000, namespace=1)
        self.assertListEqual(gauged.keys(), ['foobar', 'foobaz'])
        self.assertListEqual(gauged.keys(prefix='bar'), [])
        self.assertListEqual(gauged.keys(namespace=1), ['bar'])
        self.assertListEqual(gauged.keys(namespace=1, prefix='bar'), ['bar'])
        self.assertListEqual(gauged.keys(limit=1), ['foobar'])
        self.assertListEqual(gauged.keys(limit=1, offset=1), ['foobaz'])

    def test_memory_driver(self):
        gauged = Gauged()
        with gauged.writer as writer:
            writer.add('foo', 1, timestamp=1000)
        self.assertEqual(gauged.value('foo', timestamp=1000), 1)

    def test_add_with_whitelist(self):
        gauged = Gauged(self.driver, key_whitelist=['a'])
        with gauged.writer as writer:
            writer.add({ 'a': 123, 'b': 456 }, timestamp=2000)
        self.assertEqual(gauged.value('a', timestamp=2000), 123)
        self.assertEqual(gauged.value('b', timestamp=2000), None)

    def test_invalid_resolution(self):
        with self.assertRaises(ValueError):
            Gauged(self.driver, resolution=1000, block_size=1500)

    def test_statistics(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000)
        with gauged.writer as writer:
            writer.add('bar', 123, timestamp=10000)
            writer.add('bar', 123, timestamp=15000, namespace=1)
            writer.add({ 'foo': 123, 'bar': 456 }, timestamp=20000)
        stats = gauged.statistics()
        self.assertEqual(stats.data_points, 3)
        self.assertEqual(stats.byte_count, 24)
        stats = gauged.statistics(end=20000)
        # note: statistics() rounds to the nearest block boundary
        self.assertEqual(stats.data_points, 1)
        self.assertEqual(stats.byte_count, 8)
        stats = gauged.statistics(namespace=1)
        self.assertEqual(stats.data_points, 1)
        self.assertEqual(stats.byte_count, 8)

    def test_invalid_connection_string(self):
        with self.assertRaises(ValueError):
            Gauged('foobar://localhost')

    def test_parse_query(self):
        gauged = Gauged(self.driver)
        with gauged.writer as writer:
            result = writer.parse_query('foo=bar&baz=&foobar&%3Ckey%3E=value%3D%3')
            self.assertDictEqual(dict(result), {'<key>':'value=%3', 'foo':'bar', 'baz': ''})

    def test_constant_accessibility(self):
        gauged = Gauged(self.driver)
        self.assertTrue(type(Gauged.HOUR) == IntType)
        self.assertTrue(type(gauged.HOUR) == IntType)
        self.assertTrue(type(Gauged.NOW) == LongType)
        self.assertTrue(type(gauged.NOW) == LongType)

    def test_gauge(self):
        gauged = Gauged(self.driver, block_size=50000, gauge_nan=Gauged.IGNORE)
        self.assertEqual(gauged.value('foobar'), None)
        with gauged.writer as writer:
            writer.add('foobar', 200, timestamp=23000)
        self.assertEqual(gauged.value('foobar'), 200)
        self.assertEqual(gauged.value('foobar', timestamp=22000), None)
        with gauged.writer as writer:
            writer.add({ 'foobar': 300, 'invalid': 'nan' }, timestamp=50000)
        self.assertEqual(gauged.value('foobar'), 300)
        self.assertEqual(gauged.value('foobar', 30000), 200)
        timestamp = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=60)
        self.assertEqual(gauged.value('foobar', timestamp), 300)
        with gauged.writer as writer:
            writer.add({ 'foobar': 350 }, timestamp=90000)
            writer.add('foobar', 100, timestamp=120000)
            writer.add('bar', 150, timestamp=130000)
        self.assertItemsEqual(gauged.keys(), [ 'foobar', 'bar' ])
        self.assertEqual(gauged.value('foobar'), 100)
        with gauged.writer as writer:
            writer.add('foobar', 500, timestamp=150000)
        self.assertEqual(gauged.value('foobar'), 500)
        with gauged.writer as writer:
            writer.add('foobar', 1500, timestamp=10000, namespace=1)
        self.assertEqual(gauged.value('foobar', namespace=1), 1500)
        self.assertEqual(gauged.value('foobar'), 500)
        with gauged.writer as writer:
            writer.clear_from(100000)
        self.assertEqual(gauged.value('foobar'), 350)
        with self.assertRaises(GaugedDateRangeError):
            self.assertEqual(gauged.value('foobar', timestamp=-10000000000000), None)

    def test_gauge_nan(self):
        gauged = Gauged(self.driver, block_size=50000)
        with gauged.writer as writer:
            with self.assertRaises(GaugedNaNError):
                writer.add('foobar', 'baz')
        self.assertEqual(gauged.value('foobar'), None)
        gauged = Gauged(self.driver, block_size=50000, gauge_nan=Gauged.IGNORE)
        with gauged.writer as writer:
            writer.add('foobar', 'baz')
        self.assertEqual(gauged.value('foobar'), None)

    def test_gauge_long_key(self):
        gauged = Gauged(self.driver)
        long_key = ''
        for _ in xrange(self.driver.MAX_KEY + 1):
            long_key += 'a'
        with gauged.writer as writer:
            with self.assertRaises(GaugedKeyOverflowError):
                writer.add(long_key, 10)
        gauged = Gauged(self.driver, key_overflow=Gauged.IGNORE)
        with gauged.writer as writer:
            writer.add(long_key, 10)

    def test_aggregate(self):
        gauged = Gauged(self.driver, block_size=10000)
        self.assertEqual(gauged.aggregate('foobar', Gauged.SUM), None)
        with gauged.writer as writer:
            writer.add('foobar', 50, timestamp=10000)
            writer.add('foobar', 150, timestamp=15000)
            writer.add('foobar', 250, timestamp=20000)
            writer.add('foobar', 350, timestamp=40000)
            writer.add('foobar', 70, timestamp=60000)
        self.assertEqual(gauged.aggregate('foobar', Gauged.MIN, start=11000), 70)
        self.assertEqual(gauged.aggregate('foobar', Gauged.MIN, start=11000, end=55000), 150)
        self.assertEqual(gauged.aggregate('foobar', Gauged.SUM), 870)
        self.assertEqual(gauged.aggregate('foobar', Gauged.MIN), 50)
        self.assertEqual(gauged.aggregate('foobar', Gauged.MAX), 350)
        result = gauged.aggregate('foobar', Gauged.STDDEV)
        self.assertAlmostEqual(result, 112.7120224, places=5)
        result = gauged.aggregate('foobar', Gauged.PERCENTILE, percentile=50)
        self.assertEqual(result, 150)
        result = gauged.aggregate('foobar', Gauged.MEDIAN)
        self.assertEqual(result, 150)
        result = gauged.aggregate('foobar', Gauged.PERCENTILE, percentile=90)
        self.assertEqual(result, 310)
        result = gauged.aggregate('foobar', Gauged.COUNT)
        self.assertEqual(result, 5)
        start = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=10)
        end = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=20)
        self.assertEqual(gauged.aggregate('foobar', Gauged.MEAN, start=start, end=end), 100)
        with self.assertRaises(ValueError):
            gauged.aggregate('foobar', Gauged.PERCENTILE, percentile=-1)
        with self.assertRaises(ValueError):
            gauged.aggregate('foobar', Gauged.PERCENTILE, percentile=101)
        with self.assertRaises(ValueError):
            gauged.aggregate('foobar', Gauged.PERCENTILE, percentile=float('nan'))
        with self.assertRaises(ValueError):
            gauged.aggregate('foobar', 'unknown')

    def test_series(self):
        gauged = Gauged(self.driver, block_size=10000)
        self.assertEqual(len(gauged.value_series('foobar', start=0, end=10000).values), 0)
        with gauged.writer as writer:
            writer.add('foobar', 50, timestamp=10000)
            writer.add('foobar', 150, timestamp=15000)
            writer.add('foobar', 250, timestamp=20000)
            writer.add('foobar', 350, timestamp=40000)
            writer.add('foobar', 70, timestamp=60000)
        series = gauged.value_series('foobar', start=0, end=80000, interval=10000)
        self.assertListEqual(series.values, [ 50, 250, 250, 350, 350, 70 ])
        series = gauged.value_series('foobar', interval=10000)
        self.assertListEqual(series.values, [ 50, 250, 250, 350, 350, 70 ])
        series = gauged.value_series('foobar', start=0, end=80000, interval=10000, namespace=1)
        self.assertListEqual(series.values, [])
        with self.assertRaises(GaugedIntervalSizeError):
            gauged.value_series('foobar', interval=0)
        with self.assertRaises(GaugedDateRangeError):
            gauged.value_series('foobar', start=500, end=300)
        with self.assertRaises(GaugedDateRangeError):
            gauged.value_series('foobar', start=-100000000000000)
        with self.assertRaises(GaugedDateRangeError):
            gauged.value_series('foobar', end=-Gauged.NOW-10000)
        self.assertListEqual(gauged.value_series('foobar', start=100000).values, [])

    def test_series_caching(self):
        gauged = Gauged(self.driver, block_size=10000, min_cache_interval=1)
        with gauged.writer as writer:
            writer.add('foobar', 50, timestamp=10000)
            writer.add('foobar', 150, timestamp=15000)
            writer.add('foobar', 250, timestamp=20000)
            writer.add('foobar', 350, timestamp=40000)
            writer.add('foobar', 70, timestamp=60000)
            writer.add('bar', 70, timestamp=60000)
        series = gauged.value_series('foobar', start=0, end=60000, interval=10000)
        self.assertListEqual(series.values, [ 50, 250, 250, 350, 350 ])
        series = gauged.value_series('bar', start=0, end=60000, interval=10000)
        self.assertListEqual(series.values, [])
        gauged = Gauged(self.driver, block_size=10000, overwrite_blocks=True, min_cache_interval=1)
        with gauged.writer as writer:
            writer.add('foobar', 150, timestamp=10000)
            writer.add('foobar', 253, timestamp=15000)
            writer.add('foobar', 351, timestamp=20000)
            writer.add('foobar', 450, timestamp=40000)
            writer.add('foobar', 170, timestamp=60000)
        series = gauged.value_series('foobar', start=0, end=60000, interval=10000)
        self.assertListEqual(series.values, [ 50, 250, 250, 350, 350 ])
        series = gauged.value_series('bar', start=0, end=60000, interval=10000)
        self.assertListEqual(series.values, [])
        series = gauged.value_series('foobar', start=0, end=60000, interval=10000, cache=False)
        self.assertListEqual(series.values, [ 150, 351, 351, 450, 450 ])
        self.driver.remove_cache(0)
        series = gauged.value_series('foobar', start=0, end=60000, interval=10000)
        self.assertListEqual(series.values, [ 150, 351, 351, 450, 450 ])

    def test_series_aggregate(self):
        gauged = Gauged(self.driver, block_size=10000)
        self.assertEqual(len(gauged.aggregate_series('foobar', Gauged.SUM).values), 0)
        with gauged.writer as writer:
            writer.add('foobar', 50, timestamp=10000)
            writer.add('foobar', 150, timestamp=15000)
            writer.add('foobar', 120, timestamp=20000)
            writer.add('foobar', 30, timestamp=25000)
            writer.add('foobar', 40, timestamp=30000)
            writer.add('foobar', 10, timestamp=35000)
            writer.add('bar', 10, timestamp=40000)
        series = gauged.aggregate_series('foobar', Gauged.SUM,
            start=10000, end=40000, interval=10000)
        self.assertListEqual(series.values, [200, 150, 50])
        series = gauged.aggregate_series('foobar', Gauged.SUM,
            start=10000, end=40000, interval=10000, namespace=1)
        self.assertListEqual(series.values, [])
        series = gauged.aggregate_series('foobar', Gauged.SUM,
            start=10000, end=32000, interval=10000)
        self.assertListEqual(series.values, [200, 150, 40])
        series = gauged.aggregate_series('foobar', Gauged.COUNT,
            start=10000, end=50000, interval=10000)
        self.assertListEqual(series.values, [2, 2, 2, 0])
        series = gauged.aggregate_series('foobar', Gauged.MIN,
            start=12000, end=42000, interval=10000)
        self.assertListEqual(series.values, [120, 30, 10])
        series = gauged.aggregate_series('foobar', Gauged.MAX,
            start=12000, end=42000, interval=10000)
        self.assertListEqual(series.values, [150, 40, 10])

    def test_aggregate_series_caching(self):
        gauged = Gauged(self.driver, block_size=10000, min_cache_interval=1)
        series = gauged.aggregate_series('foobar', Gauged.MEAN,
            start=0, end=60000, interval=10000)
        self.assertListEqual(series.values, [])
        with gauged.writer as writer:
            writer.add('bar', 50, timestamp=0)
            writer.add('foobar', 50, timestamp=10000)
            writer.add('foobar', 150, timestamp=15000)
            writer.add('foobar', 250, timestamp=20000)
            writer.add('foobar', 350, timestamp=40000)
            writer.add('foobar', 70, timestamp=60000)
        series = gauged.aggregate_series('foobar', Gauged.MEAN,
            start=0, end=60000, interval=10000)
        self.assertListEqual(series.values, [ None, 100, 250, None, 350, None ])
        gauged = Gauged(self.driver, block_size=10000, overwrite_blocks=True, min_cache_interval=1)
        with gauged.writer as writer:
            writer.add('foobar', 150, timestamp=10000)
            writer.add('foobar', 253, timestamp=15000)
            writer.add('foobar', 351, timestamp=20000)
            writer.add('foobar', 450, timestamp=40000)
            writer.add('foobar', 170, timestamp=60000)
        series = gauged.aggregate_series('foobar', Gauged.MEAN,
            start=0, end=60000, interval=10000)
        self.assertListEqual(series.values, [ None, 100, 250, None, 350, None ])
        series = gauged.aggregate_series('foobar', Gauged.MEAN,
            start=0, end=60000, interval=10000, cache=False)
        self.assertListEqual(series.values, [ None, 201.5, 351, None, 450, None ])
        self.driver.remove_cache(0)
        series = gauged.aggregate_series('foobar', Gauged.MEAN,
            start=0, end=60000, interval=10000)
        self.assertListEqual(series.values, [ None, 201.5, 351, None, 450, None ])
        self.assertListEqual(series.timestamps, [ 0, 10000, 20000, 30000, 40000, 50000 ])

    def test_no_data(self):
        gauged = Gauged(self.driver)
        self.assertEqual(len(gauged.namespaces()), 0)
        self.assertEqual(len(gauged.value_series('foo')), 0)
        self.assertEqual(len(gauged.aggregate_series('foo', Gauged.SUM)), 0)
        self.assertEqual(gauged.value('foo'), None)
        self.assertEqual(gauged.aggregate('foo', Gauged.SUM), None)
        self.assertEqual(len(gauged.keys()), 0)
        stats = gauged.statistics()
        for attr in ['data_points', 'byte_count']:
            self.assertEqual(getattr(stats, attr), 0)

    def test_interval_size_error(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000)
        with gauged.writer as writer:
            writer.add('likes', 10)
        with self.assertRaises(GaugedIntervalSizeError):
            gauged.value_series('likes', interval=1)
        with self.assertRaises(GaugedIntervalSizeError):
            gauged.aggregate_series('likes', Gauged.SUM, interval=1)
        with self.assertRaises(GaugedIntervalSizeError):
            gauged.aggregate_series('likes', Gauged.MEAN, interval=1)

    def test_invalid_config_key(self):
        with self.assertRaises(ValueError):
            Gauged(self.driver, foobar=None)

    def test_invalid_context_key(self):
        with self.assertRaises(ValueError):
            Gauged(self.driver, defaults={'foobar':None})

    def test_metadata_on_create(self):
        gauged = Gauged(self.driver)
        metadata = gauged.driver.all_metadata()
        self.assertEqual(metadata['current_version'], Gauged.VERSION)
        self.assertEqual(metadata['initial_version'], Gauged.VERSION)
        self.assertIn('created_at', metadata)

    def test_version_mismatch(self):
        self.driver.set_metadata({ 'current_version': 'foo' })
        gauged = Gauged(self.driver)
        with self.assertRaises(GaugedVersionMismatchError):
            with gauged.writer:
                pass
        gauged.migrate()

    def test_accepting_data_as_string(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000,
            key_overflow=Gauged.IGNORE, gauge_nan=Gauged.IGNORE)
        with gauged.writer as writer:
            writer.add('foo=123.456&bar=-15.98&qux=0&invalid=foobar\n', timestamp=20000)
        self.assertAlmostEqual(123.456, gauged.value('foo', timestamp=20000), 5)
        self.assertAlmostEqual(-15.98, gauged.value('bar', timestamp=20000), 5)
        self.assertEqual(gauged.value('qux', timestamp=20000), 0)
        self.assertEqual(gauged.value('invalid', timestamp=20000), None)
        stats = gauged.statistics()
        self.assertEqual(stats.data_points, 3)
        self.assertEqual(stats.byte_count, 24)
        stats = gauged.statistics(end=25000)
        self.assertEqual(stats.data_points, 3)
        self.assertEqual(stats.byte_count, 24)
        gauged = Gauged(self.driver, resolution=1000, block_size=10000,
            key_overflow=Gauged.IGNORE)
        with self.assertRaises(GaugedNaNError):
            with gauged.writer as writer:
                writer.add(u'foo=123.456&bar=-15.98&qux=0&invalid=foobar\n', timestamp=20000)

    def test_context_defaults(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000)
        with gauged.writer as writer:
            writer.add('bar', 123, timestamp=10000)
            writer.add('foo', 456, timestamp=20000)
        self.assertListEqual(gauged.keys(), [ 'bar', 'foo' ])
        gauged = Gauged(self.driver, resolution=1000, block_size=10000, defaults={
            'limit': 1
        })
        self.assertListEqual(gauged.keys(), [ 'bar' ])

    def test_look_behind(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000, max_look_behind=10000)
        with gauged.writer as writer:
            writer.add('foo', 123, timestamp=10000)
            writer.add('bar', 123, timestamp=40000)
        self.assertEqual(gauged.value('foo', timestamp=10000), 123)
        self.assertEqual(gauged.value('foo', timestamp=20000), 123)
        self.assertEqual(gauged.value('foo', timestamp=30000), None)

    def test_block_slicing(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000)
        with gauged.writer as writer:
            writer.add('foo', 100, timestamp=11000)
            writer.add('foo', 200, timestamp=23000)
        self.assertEqual(gauged.aggregate('foo', Gauged.MEAN, start=10000, end=30000), 150)
        self.assertEqual(gauged.aggregate('foo', Gauged.MEAN, start=11000, end=24000), 150)
        self.assertEqual(gauged.aggregate('foo', Gauged.MEAN, start=11000, end=23000), 100)
        self.assertEqual(gauged.aggregate('foo', Gauged.STDDEV, start=11000, end=23000), 0)

    def test_coercing_non_string_keys(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000)
        with gauged.writer as writer:
            writer.add(1234, 100, timestamp=10000)
            writer.add(True, 100, timestamp=10000)
            writer.add(u'foo', 100, timestamp=10000)
        self.assertEqual(gauged.value('1234', timestamp=10000), 100)
        self.assertEqual(gauged.value('True', timestamp=10000), 100)
        self.assertEqual(gauged.value('foo', timestamp=10000), 100)

    def test_flush_flushes_last_complete_block(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000)
        with gauged.writer as writer:
            writer.add('foo', 1, timestamp=1000)
            writer.add('foo', 2, timestamp=2000)
            writer.add('foo', 3, timestamp=3000)
            self.assertEqual(gauged.value('foo', timestamp=3000), None)
            writer.flush()
            self.assertEqual(gauged.value('foo', timestamp=3000), 2)
        self.assertEqual(gauged.value('foo', timestamp=3000), 3)

    def test_auto_flush(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000, flush_seconds=0.001)
        with gauged.writer as writer:
            writer.add('foo', 1, timestamp=1000)
            self.assertEqual(gauged.value('foo', timestamp=2000), None)
            sleep(0.002)
            self.assertEqual(gauged.value('foo', timestamp=2000), None)
            # note: the next write triggers the flush() of all prior writes
            writer.add('foo', 2, timestamp=2000)
            sleep(0.002)
            self.assertEqual(gauged.value('foo', timestamp=2000), 1)
        self.assertEqual(gauged.value('foo', timestamp=2000), 2)

    def test_use_after_free_error(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000)
        with gauged.writer as writer:
            pass
        with self.assertRaises(GaugedUseAfterFreeError):
            writer.flush()
        with self.assertRaises(GaugedUseAfterFreeError):
            writer.add('foo', 123, timestamp=1000)
        with self.assertRaises(GaugedUseAfterFreeError):
            list(writer.parse_query('foo=bar'))

    def test_add_debug(self):
        context = dict(called=False)
        gauged = Gauged(self.driver)
        def mock_debug(*_):
            context['called'] = True
        with gauged.writer as writer:
            writer.debug = mock_debug
            writer.add('foo', 123, timestamp=10000, debug=True)
            writer.add('foo=123', timestamp=10000, debug=True)
        self.assertEqual(gauged.value('foo', timestamp=10000), None)
        self.assertTrue(context['called'])

    def test_append_only_violation(self):
        gauged = Gauged(self.driver)
        with gauged.writer as writer:
            writer.add('foo', 123, timestamp=2000)
            with self.assertRaises(GaugedAppendOnlyError):
                writer.add('foo', 456, timestamp=1000)
        self.assertEqual(gauged.value('foo', timestamp=1000), None)
        self.assertEqual(gauged.value('foo', timestamp=2000), 123)

    def test_ignore_append_only_violation(self):
        gauged = Gauged(self.driver, append_only_violation=Gauged.IGNORE)
        with gauged.writer as writer:
            writer.add('foo', 123, timestamp=2000)
            writer.add('foo', 456, timestamp=1000)
        self.assertEqual(gauged.value('foo', timestamp=1000), None)
        self.assertEqual(gauged.value('foo', timestamp=2000), 123)

    def test_rewrite_append_only_violation(self):
        gauged = Gauged(self.driver, append_only_violation=Gauged.REWRITE)
        with gauged.writer as writer:
            writer.add('foo', 123, timestamp=2000)
            writer.add('foo', 456, timestamp=1000)
        self.assertEqual(gauged.value('foo', timestamp=1000), None)
        self.assertEqual(gauged.value('foo', timestamp=2000), 456)

    def test_interim_flushing(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000)
        with gauged.writer as writer:
            writer.add('foo', 123, timestamp=1000)
            writer.flush()
            writer.add('bar', 456, timestamp=2000)
            writer.flush()
            writer.add('baz', 789, timestamp=10000)
        self.assertEqual(gauged.value('foo', timestamp=10000), 123)
        self.assertEqual(gauged.value('bar', timestamp=10000), 456)
        self.assertEqual(gauged.value('baz', timestamp=10000), 789)

    def test_resume_from(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000)
        with gauged.writer as writer:
            self.assertEqual(writer.resume_from(), 0)
            writer.add('foo', 123, timestamp=10000)
            writer.add('foo', 456, timestamp=15000)
            writer.add('foo', 789, timestamp=20000)
        with gauged.writer as writer:
            self.assertEqual(writer.resume_from(), 21000)
        with gauged.writer as writer:
            writer.add('foo', 123, timestamp=25000)
            writer.add('foo', 456, timestamp=30000)
            writer.add('foo', 789, timestamp=35000)
        with gauged.writer as writer:
            self.assertEqual(writer.resume_from(), 36000)
        gauged = Gauged(self.driver, resolution=1000, block_size=10000, writer_name='foobar')
        with gauged.writer as writer:
            self.assertEqual(writer.resume_from(), 0)
            writer.add('foo', 123, timestamp=10000)
        with gauged.writer as writer:
            self.assertEqual(writer.resume_from(), 11000)
        gauged = Gauged(self.driver, resolution=1000, block_size=10000)
        with gauged.writer as writer:
            self.assertEqual(writer.resume_from(), 36000)

    def test_clear_from(self):
        gauged = Gauged(self.driver, resolution=1000, block_size=10000)
        with gauged.writer as writer:
            writer.add('foo', 1, timestamp=10000)
            writer.add('foo', 2, timestamp=20000)
            writer.add('foo', 3, timestamp=30000)
            writer.add('foo', 4, timestamp=40000, namespace=1)
        with gauged.writer as writer:
            self.assertEqual(writer.resume_from(), 41000)
        self.assertEqual(gauged.value('foo', timestamp=40000), 3)
        self.assertEqual(gauged.value('foo', timestamp=40000, namespace=1), 4)
        with gauged.writer as writer:
            with self.assertRaises(ValueError):
                # note: must be cleared from nearest block boundary (20000)
                writer.clear_from(25000)
            writer.clear_from(20000)
        self.assertEqual(gauged.value('foo', timestamp=40000), 1)
        self.assertEqual(gauged.value('foo', timestamp=40000, namespace=1), None)
        with gauged.writer as writer:
            self.assertEqual(writer.resume_from(), 21000)
            writer.add('foo', 5, timestamp=30000)
            writer.add('foo', 6, timestamp=30000, namespace=1)
        self.assertEqual(gauged.value('foo', timestamp=40000), 5)
        self.assertEqual(gauged.value('foo', timestamp=40000, namespace=1), 6)

    def test_gauged_init_store(self):
        gauged = Gauged('sqlite+foo://')
        self.assertEqual(len(gauged.metadata()), 0)
        with self.assertRaises(GaugedSchemaError):
            gauged.keys()

    def test_config_instance(self):
        config = Config(append_only_violation=Gauged.REWRITE,
            resolution=1000, block_size=10000)
        gauged = Gauged(self.driver, config=config)
        with gauged.writer as writer:
            writer.add('foo', 1, timestamp=2000)
            writer.add('foo', 2, timestamp=1000)
        self.assertEqual(gauged.value('foo', timestamp=2000), 2)

    def test_relative_dates(self):
        now = long(time() * 1000)
        gauged = Gauged(self.driver, defaults={'start':-4*Gauged.DAY})
        with gauged.writer as writer:
            writer.add('foo', 1, timestamp=now-6*Gauged.DAY)
            writer.add('foo', 2, timestamp=now-5*Gauged.DAY)
            writer.add('foo', 3, timestamp=now-3*Gauged.DAY)
            writer.add('foo', 4, timestamp=now-2*Gauged.DAY)
            writer.add('foo', 5, timestamp=now-Gauged.DAY)
        self.assertEqual(gauged.value('foo'), 5)
        self.assertEqual(gauged.value('foo', timestamp=-1.5*Gauged.DAY), 4)

    def test_fuzzy(self, decimal_places=4, max_values=3):
        def random_values(n, minimum, maximum, decimals):
            return [ round(random.random() * (maximum - minimum) + minimum, decimals) \
                for _ in xrange(n) ]
        def percentile(values, percentile):
            if not len(values):
                return float('nan')
            values = sorted(values)
            rank = float(len(values) - 1) * percentile / 100
            nearest_rank = int(floor(rank))
            result = values[nearest_rank]
            if (ceil(rank) != nearest_rank):
                result += (rank - nearest_rank) * (values[nearest_rank + 1] - result)
            return result
        def stddev(values):
            total = len(values)
            mean = float(sum(values)) / total
            sum_of_squares = sum((elem - mean) ** 2 for elem in values)
            return sqrt(float(sum_of_squares) / total)
        for resolution in (100, 500, 1000):
            for n in xrange(1, max_values):
                for end in (1000, 10000):
                    gauged = Gauged(self.driver, block_size=1000, resolution=resolution)
                    gauged.driver.clear_schema()
                    values = random_values(n, -100, 100, 2)
                    with gauged.writer as writer:
                        timestamps = sorted(random_values(n, 0, end, 0))
                        for value, timestamp in zip(values, timestamps):
                            writer.add('foo', value, timestamp=int(timestamp))
                    self.assertAlmostEqual(sum(values), gauged.aggregate('foo', Gauged.SUM),
                        places=decimal_places)
                    self.assertAlmostEqual(min(values), gauged.aggregate('foo', Gauged.MIN),
                        places=decimal_places)
                    self.assertAlmostEqual(max(values), gauged.aggregate('foo', Gauged.MAX),
                        places=decimal_places)
                    self.assertAlmostEqual(len(values), gauged.aggregate('foo', Gauged.COUNT),
                        places=decimal_places)
                    mean = float(sum(values)) / len(values)
                    self.assertAlmostEqual(mean, gauged.aggregate('foo', Gauged.MEAN),
                        places=decimal_places)
                    self.assertAlmostEqual(stddev(values), gauged.aggregate('foo', Gauged.STDDEV),
                        places=decimal_places)
                    self.assertAlmostEqual(percentile(values, 50), gauged.aggregate('foo', Gauged.MEDIAN),
                        places=decimal_places)
                    self.assertAlmostEqual(percentile(values, 98), gauged.aggregate('foo',
                        Gauged.PERCENTILE, percentile=98), places=decimal_places)

########NEW FILE########
__FILENAME__ = test_lru
'''
Gauged - https://github.com/chriso/gauged
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from gauged import LRU
from .test_case import TestCase

class TestLRU(TestCase):
    '''Test the least recently used cache in lru.py'''

    def test_lru_eviction(self):
        lru = LRU(3)
        lru[1] = 'foo'
        lru[2] = 'bar'
        lru[3] = 'foobar'
        self.assertTrue(3 in lru)
        self.assertTrue(2 in lru)
        self.assertTrue(1 in lru)
        self.assertEqual(lru[3], 'foobar')
        self.assertEqual(lru[2], 'bar')
        self.assertEqual(lru[1], 'foo')
        lru[4] = 'bla'
        self.assertTrue(4 in lru)
        self.assertTrue(1 in lru)
        self.assertTrue(2 in lru)
        self.assertFalse(3 in lru)

    def test_len_1(self):
        lru = LRU(1)
        lru[1] = 'foo'
        self.assertEqual(lru[1], 'foo')
        self.assertTrue(1 in lru)
        lru[2] = 'bar'
        self.assertEqual(lru[2], 'bar')
        self.assertFalse(1 in lru)

########NEW FILE########
__FILENAME__ = test_result
'''
Gauged - https://github.com/chriso/gauged
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

import re
from datetime import datetime
from gauged.results import Statistics, TimeSeries
from .test_case import TestCase

class TestResult(TestCase):
    '''Test result wrappers'''

    def test_statistics_repr(self):
        stat = Statistics(1, 2, 3, 4, 5)
        self.assertEqual(str(stat), 'Statistics(namespace=1, start=2, end=3, ' \
            'data_points=4, byte_count=5)')

    def test_tuple_list_init(self):
        series = TimeSeries([ (1, 2), (3, 4), (5, 6) ])
        self.assertListEqual(series.timestamps, [1, 3, 5])
        self.assertListEqual(series.values, [2, 4, 6])
        self.assertEqual(len(series), 3)

    def test_dict_init(self):
        series = TimeSeries({ 1: 2, 3: 4, 5: 6 })
        self.assertListEqual(series.timestamps, [1, 3, 5])
        self.assertListEqual(series.values, [2, 4, 6])
        self.assertEqual(len(series), 3)

    def test_accessors(self):
        points = [ (1234000, 54), (5678000, 100) ]
        series = TimeSeries(points)
        dates = series.dates
        for date in dates:
            self.assertTrue(isinstance(date, datetime))
        self.assertListEqual(series.dates, [datetime.fromtimestamp(1234),
            datetime.fromtimestamp(5678)])
        self.assertListEqual(series.timestamps, [1234000, 5678000])
        self.assertListEqual(series.values, [54, 100])

    def test_initial_sort(self):
        points = [ (3, 54), (2, 100), (4, 32) ]
        series = TimeSeries(points)
        self.assertListEqual(series.timestamps, [2, 3, 4])
        self.assertListEqual(series.values, [100, 54, 32])

    def test_interval(self):
        series = TimeSeries([])
        self.assertEqual(series.interval, None)
        series = TimeSeries([ (1, 2) ])
        self.assertEqual(series.interval, None)
        series = TimeSeries([ (1, 2), (3, 4) ])
        self.assertEqual(series.interval, 2)

    def test_map(self):
        series = TimeSeries([ (1, 2), (3, 4), (5, 6) ])
        double = series.map(lambda y: y * 2)
        self.assertTrue(isinstance(double, TimeSeries))
        self.assertListEqual([ (1, 4), (3, 8), (5, 12) ], double.points)

    def test_indexing(self):
        series = TimeSeries([ (1, 3), (2, 3), (3, 3) ])
        self.assertEqual(series[1], 3)
        self.assertEqual(series[2], 3)
        with self.assertRaises(KeyError):
            series[4]

    def test_iteration(self):
        points = [ (1, 2), (3, 4), (5, 6) ]
        series = TimeSeries(points)
        self.assertListEqual([ s for s in series ], points)

    def test_map_return_type(self):
        series = TimeSeries([ (1, 2), (3, 4), (5, 6) ])
        double = series.map(lambda y: y * 2)
        self.assertTrue(isinstance(double, TimeSeries))
        self.assertListEqual([ (1, 4), (3, 8), (5, 12) ], double.points)

    def test_add(self):
        a = TimeSeries([ (1, 3), (2, 3), (3, 3) ])
        b = TimeSeries([ (0, 1), (1, 1), (2, 1), (3, 1), (4, 1) ])
        c = a + b
        self.assertTrue(isinstance(c, TimeSeries))
        self.assertListEqual(c.points, [ (1, 4), (2, 4), (3, 4) ])
        c = c + 5
        self.assertTrue(isinstance(c, TimeSeries))
        self.assertListEqual(c.points, [ (1, 9), (2, 9), (3, 9) ])

    def test_add_update(self):
        a = TimeSeries([ (1, 3), (2, 3), (3, 3) ])
        b = TimeSeries([ (0, 1), (1, 1), (2, 1), (3, 1), (4, 1) ])
        a += b
        self.assertListEqual(a.points, [ (1, 4), (2, 4), (3, 4) ])
        a += 5
        self.assertListEqual(a.points, [ (1, 9), (2, 9), (3, 9) ])

    def test_sub(self):
        a = TimeSeries([ (1, 3), (2, 3), (3, 3) ])
        b = TimeSeries([ (0, 1), (1, 1), (2, 1), (3, 1), (4, 1) ])
        c = a - b
        self.assertTrue(isinstance(c, TimeSeries))
        self.assertListEqual(c.points, [ (1, 2), (2, 2), (3, 2) ])
        c = c - 1
        self.assertTrue(isinstance(c, TimeSeries))
        self.assertListEqual(c.points, [ (1, 1), (2, 1), (3, 1) ])

    def test_sub_update(self):
        a = TimeSeries([ (1, 3), (2, 3), (3, 3) ])
        b = TimeSeries([ (0, 1), (1, 1), (2, 1), (3, 1), (4, 1) ])
        a -= b
        self.assertListEqual(a.points, [ (1, 2), (2, 2), (3, 2) ])
        a -= 1
        self.assertListEqual(a.points, [ (1, 1), (2, 1), (3, 1) ])

    def test_mul(self):
        a = TimeSeries([ (1, 3), (2, 3), (3, 3) ])
        b = TimeSeries([ (0, 2), (1, 3), (2, 2), (3, 2), (4, 1) ])
        c = a * b
        self.assertTrue(isinstance(c, TimeSeries))
        self.assertListEqual(c.points, [ (1, 9), (2, 6), (3, 6) ])
        c = c * 2
        self.assertTrue(isinstance(c, TimeSeries))
        self.assertListEqual(c.points, [ (1, 18), (2, 12), (3, 12) ])

    def test_mul_update(self):
        a = TimeSeries([ (1, 3), (2, 3), (3, 3) ])
        b = TimeSeries([ (0, 2), (1, 3), (2, 2), (3, 2), (4, 1) ])
        a *= b
        self.assertListEqual(a.points, [ (1, 9), (2, 6), (3, 6) ])
        a *= 2
        self.assertListEqual(a.points, [ (1, 18), (2, 12), (3, 12) ])

    def test_div(self):
        a = TimeSeries([ (1, 3), (2, 4), (3, 3) ])
        b = TimeSeries([ (0, 2), (1, 3), (2, 2), (3, 2), (4, 1) ])
        c = a / b
        self.assertTrue(isinstance(c, TimeSeries))
        self.assertListEqual(c.points, [ (1, 1), (2, 2), (3, 1.5) ])
        c = c / 2
        self.assertTrue(isinstance(c, TimeSeries))
        self.assertListEqual(c.points, [ (1, 0.5), (2, 1), (3, 0.75) ])

    def test_div_update(self):
        a = TimeSeries([ (1, 3), (2, 4), (3, 3) ])
        b = TimeSeries([ (0, 2), (1, 3), (2, 2), (3, 2), (4, 1) ])
        a /= b
        self.assertListEqual(a.points, [ (1, 1), (2, 2), (3, 1.5) ])
        a /= 0.5
        self.assertListEqual(a.points, [ (1, 2), (2, 4), (3, 3) ])

    def test_pow(self):
        a = TimeSeries([ (1, 3), (2, 3), (3, 3) ])
        b = TimeSeries([ (0, 2), (1, 3), (2, 2), (3, 1), (4, 1) ])
        c = a ** b
        self.assertTrue(isinstance(c, TimeSeries))
        self.assertListEqual(c.points, [ (1, 27), (2, 9), (3, 3) ])
        c = c ** 2
        self.assertTrue(isinstance(c, TimeSeries))
        self.assertListEqual(c.points, [ (1, 729), (2, 81), (3, 9) ])

    def test_abs(self):
        a = TimeSeries([ (1, -3), (2, 3.3), (3, -5) ])
        a = abs(a)
        self.assertTrue(isinstance(a, TimeSeries))
        self.assertListEqual(a.values, [ 3, 3.3, 5 ])

    def test_round(self):
        a = TimeSeries([ (1, -0.3), (2, 3.3), (3, 1.1) ])
        a = a.round()
        self.assertTrue(isinstance(a, TimeSeries))
        self.assertListEqual(a.values, [ 0, 3, 1 ])

    def test_pow_update(self):
        a = TimeSeries([ (1, 3), (2, 3), (3, 3) ])
        b = TimeSeries([ (0, 2), (1, 3), (2, 2), (3, 1), (4, 1) ])
        a **= b
        self.assertListEqual(a.points, [ (1, 27), (2, 9), (3, 3) ])
        a **= 2
        self.assertListEqual(a.points, [ (1, 729), (2, 81), (3, 9) ])

    def test_time_series_repr(self):
        a = TimeSeries([ (10000, 500), (20000, 1234), (30000, 12345678) ])
        lines = repr(a).split('\n')
        self.assertEqual(lines[0], '                        Value')
        self.assertTrue(re.match(r'^19(?:69|70)-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:10       500$', lines[1]))
        self.assertTrue(re.match(r'^19(?:69|70)-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:20      1234$', lines[2]))
        self.assertTrue(re.match(r'^19(?:69|70)-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:30  12345678$', lines[3]))
        self.assertEqual(str(TimeSeries([])), 'TimeSeries([])')

########NEW FILE########
__FILENAME__ = test_structures
'''
Gauged - https://github.com/chriso/gauged
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

from gauged.structures import FloatArray, SparseMap
from gauged.errors import GaugedUseAfterFreeError
from .test_case import TestCase

class TestStructures(TestCase):
    '''Test the FloatArray structure'''

    def setUp(self):
        SparseMap.ALLOCATIONS = 0
        FloatArray.ALLOCATIONS = 0

    def tearDown(self):
        self.assertEqual(SparseMap.ALLOCATIONS, 0)
        self.assertEqual(FloatArray.ALLOCATIONS, 0)

    def test_array_empty_array(self):
        s = FloatArray()
        self.assertEqual(s.byte_length(), 0)
        self.assertEqual(len(s), 0)
        self.assertListEqual(s.values(), [])
        s.free()

    def test_array_instantiation_from_list(self):
        s = FloatArray([1, 2, 3])
        self.assertEqual(s.byte_length(), 12)
        self.assertEqual(len(s), 3)
        self.assertListEqual(s.values(), [1, 2, 3])
        s.free()

    def test_array_append(self):
        s = FloatArray([1, 2, 3])
        s.append(4)
        s.append(10)
        self.assertEqual(s.byte_length(), 20)
        self.assertListEqual(s.values(), [1, 2, 3, 4, 10])
        s.free()

    def test_array_clear(self):
        s = FloatArray([1, 2, 3])
        self.assertEqual(s.byte_length(), 12)
        s.clear()
        self.assertEqual(s.byte_length(), 0)
        s.free()

    def test_array_getitem(self):
        s = FloatArray([1, 2, 3])
        self.assertEqual(s[0], 1)
        self.assertEqual(s[1], 2)
        self.assertEqual(s[2], 3)
        with self.assertRaises(IndexError):
            self.assertEqual(s[3], 0)
        s.free()

    def test_array_import_export(self):
        s = FloatArray([1, 2, 3])
        buf = str(s.buffer())
        s.free()
        self.assertEqual(len(buf), 12)
        copy = FloatArray(buf, 12)
        self.assertListEqual(copy.values(), [1, 2, 3])
        copy.free()
        s = FloatArray()
        self.assertEqual(s.buffer(), None)
        s.free()

    def test_array_import_export_using_buffer(self):
        s = FloatArray([1, 2, 3])
        buf = buffer(s.buffer())
        s.free()
        self.assertEqual(len(buf), 12)
        copy = FloatArray(buf, 12)
        self.assertListEqual(copy.values(), [1, 2, 3])
        copy.free()
        s = FloatArray()
        self.assertEqual(s.buffer(), None)
        s.free()

    def test_array_buffer_offset(self):
        s = FloatArray([1, 2, 3])
        buf = s.buffer(byte_offset=4)
        s.free()
        self.assertEqual(len(buf), 8)
        copy = FloatArray(buf, 8)
        self.assertListEqual(copy.values(), [2, 3])
        copy.free()

    def test_map_empty_map(self):
        v = SparseMap()
        self.assertDictEqual(dict(v.items()), { })
        self.assertEqual(v.byte_length(), 0)
        v.free()

    def test_map_map_from_dict(self):
        a = FloatArray([ 1, 2, 3, 4 ])
        b = FloatArray([ 2, 4, 6, 8 ])
        v = SparseMap({ 1: a, 3: b })
        self.assertDictEqual(dict(v.items()), { 1: [1, 2, 3, 4], 3: [2, 4, 6, 8] })
        v.free()
        a.free()
        b.free()

    def test_map_append(self):
        v = SparseMap()
        s = FloatArray([1, 2, 3])
        v.append(1, s)
        s.free()
        self.assertDictEqual(dict(v.items()), { 1: [1, 2, 3] })
        v.free()

    def test_map_import_export(self):
        a = FloatArray([ 1, 2, 3, 4 ])
        b = FloatArray([ 2, 4, 6, 8 ])
        v = SparseMap({ 1: a, 3: b })
        buf = v.buffer()
        a.free()
        b.free()
        v.free()
        self.assertEqual(len(buf), 40)
        copy = SparseMap(buf, len(buf))
        self.assertDictEqual(dict(copy.items()), { 1: [1, 2, 3, 4], 3: [2, 4, 6, 8] })
        copy.free()
        v = SparseMap()
        self.assertEqual(v.buffer(), None)
        v.free()

    def test_map_clear(self):
        a = FloatArray([ 1, 2, 3, 4 ])
        b = FloatArray([ 2, 4, 6, 8 ])
        v = SparseMap({ 1: a, 3: b })
        a.free()
        b.free()
        v.clear()
        self.assertEqual(v.byte_length(), 0)
        v.free()

    def test_map_buffer_offset(self):
        a = FloatArray([ 1 ])
        b = FloatArray([ 1, 2, 3 ])
        v = SparseMap({ 1: a, 3: b })
        buf = v.buffer(byte_offset=8)
        a.free()
        b.free()
        v.free()
        copy = SparseMap(buf, len(buf))
        self.assertDictEqual(dict(copy.items()), { 3: [1, 2, 3] })
        copy.free()

    def test_context_manager_free(self):
        outside = None
        with FloatArray() as structure:
            outside = structure
            self.assertIsNot(structure.ptr, None)
        self.assertIs(outside._ptr, None)
        with SparseMap() as structure:
            outside = structure
            self.assertIsNot(structure.ptr, None)
        self.assertIs(outside._ptr, None)

    def test_use_array_after_free_error(self):
        s = FloatArray()
        s.free()
        with self.assertRaises(GaugedUseAfterFreeError):
            len(s)
        with self.assertRaises(GaugedUseAfterFreeError):
            s.values()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.values()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.append(1)
        with self.assertRaises(GaugedUseAfterFreeError):
            s.byte_length()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.buffer()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.clear()

    def test_use_map_after_free_error(self):
        s = SparseMap()
        s.free()
        freed_array = FloatArray()
        freed_array.free()
        tmp_array = FloatArray()
        tmp = SparseMap()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.append(1, tmp_array)
        with self.assertRaises(GaugedUseAfterFreeError):
            tmp.append(1, freed_array)
        with self.assertRaises(GaugedUseAfterFreeError):
            s.slice()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.concat(tmp)
        with self.assertRaises(GaugedUseAfterFreeError):
            tmp.concat(s)
        with self.assertRaises(GaugedUseAfterFreeError):
            s.byte_length()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.buffer()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.clear()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.first()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.last()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.sum()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.min()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.max()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.mean()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.stddev()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.count()
        with self.assertRaises(GaugedUseAfterFreeError):
            s.percentile(50)
        with self.assertRaises(GaugedUseAfterFreeError):
            list(s.iteritems())
        tmp_array.free()
        tmp.free()

    def test_map_repr(self):
        map = SparseMap()
        self.assertEqual(str(map), '')
        a = FloatArray([1, 2, 3])
        map.append(1, a)
        b = FloatArray([4])
        map.append(2, b)
        self.assertEqual(str(map), '[ 1 ] = [1.0, 2.0, 3.0]\n[ 2 ] = [4.0]')
        a.free()
        b.free()
        map.free()

    def test_array_repr(self):
        s = FloatArray()
        self.assertEqual(str(s), '[]')
        s.free()
        s = FloatArray([1])
        self.assertEqual(str(s), '[1.0]')
        s.free()
        s = FloatArray([1, 2, 3])
        self.assertEqual(str(s), '[1.0, 2.0, 3.0]')
        s.free()

    def test_double_free(self):
        s = FloatArray()
        s.free()
        s.free()
        v = SparseMap()
        v.free()
        v.free()

########NEW FILE########
__FILENAME__ = test
'''
Gauged - https://github.com/chriso/gauged
Copyright 2014 (c) Chris O'Hara <cohara87@gmail.com>
'''

import gauged, unittest, sys, gc
from ConfigParser import ConfigParser
from test import (TestGauged, TestStructures, TestLRU, TestDriver,
    TestDSN, TestResult)

# Get the list of test drivers
config = ConfigParser()
config.read('test_drivers.cfg')
test_drivers = config.items('drivers')

# Parse command line options
argv = set(sys.argv)
quick_tests = '--quick' in argv    # Use only the first driver (in-memory SQLite)
raise_on_error = '--raise' in argv # Stop and dump a trace when a test driver fails
run_forever = '--forever' in argv  # Run the tests forever (to check for leaks)
drivers_only = '--drivers' in argv # Run driver tests only
verbose = '--verbose' in argv      # Increase test runner verbosity

if quick_tests:
    test_drivers = test_drivers[:1]

def run_tests():

    suite = unittest.TestSuite()

    test_class = driver = None

    # Test each driver in gauged/drivers. We need to dynamically subclass
    # the TestDriver class here - the unittest module doesn't allow us to
    # use __init__ to pass in driver arguments or a driver instance
    for driver, dsn in test_drivers:
        try:
            gauged_instance = gauged.Gauged(dsn)
            # Empty the data store
            gauged_instance.driver.drop_schema()
            gauged_instance.sync()
            gauged_instance.driver.create_schema()
            # Test the driver class
            test_class = type('Test%s' % driver, (TestDriver,), {})
            test_class.driver = gauged_instance.driver
            suite.addTest(unittest.makeSuite(test_class))
            # Test gauged/gauged.py using the driver
            if not drivers_only:
                test_class = type('TestGaugedWith%s' % driver, (TestGauged,), {})
                test_class.driver = gauged_instance.driver
                suite.addTest(unittest.makeSuite(test_class))
        except Exception as e:
            print 'Skipping %s tests (%s). Check test_driver.cfg' % (driver[:-6], str(e).rstrip())
            if raise_on_error:
                raise

    if test_class is None:
        msg = 'No drivers available for unit tests, check configuration in test_driver.cfg'
        raise RuntimeWarning(msg)

    # Test the remaining classes
    if not drivers_only:
        suite.addTest(unittest.makeSuite(TestStructures))
        suite.addTest(unittest.makeSuite(TestLRU))
        suite.addTest(unittest.makeSuite(TestDSN))
        suite.addTest(unittest.makeSuite(TestResult))

    # Setup the test runner
    verbosity = 2 if verbose else 1
    if run_forever:
        verbosity = 0
    test_runner = unittest.TextTestRunner(verbosity=verbosity)

    # Run the tests
    while True:
        result = test_runner.run(suite)
        if result.errors or result.failures:
            exit(1)
        if not run_forever:
            break
        gc.collect()

if __name__ == '__main__':
    run_tests()

########NEW FILE########
