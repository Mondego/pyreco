__FILENAME__ = callbacks
import calendar
import re
from decimal import Decimal
import sys
import struct
from rdbtools.parser import RdbCallback, RdbParser

ESCAPE = re.compile(ur'[\x00-\x1f\\"\b\f\n\r\t\u2028\u2029]')
ESCAPE_ASCII = re.compile(r'([\\"]|[^\ -~])')
HAS_UTF8 = re.compile(r'[\x80-\xff]')
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
    u'\u2028': '\\u2028',
    u'\u2029': '\\u2029',
}
for i in range(0x20):
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))

def _floatconstants():
    _BYTES = '7FF80000000000007FF0000000000000'.decode('hex')
    # The struct module in Python 2.4 would get frexp() out of range here
    # when an endian is specified in the format string. Fixed in Python 2.5+
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()

def _encode_basestring(s):
    """Return a JSON representation of a Python string"""
    if isinstance(s, str) and HAS_UTF8.search(s) is not None:
        s = s.decode('utf-8')
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return u'"' + ESCAPE.sub(replace, s) + u'"'

def _encode_basestring_ascii(s):
    """Return an ASCII-only JSON representation of a Python string

    """
    try :
        if isinstance(s, str) and HAS_UTF8.search(s) is not None:
            s = s.decode('utf-8')
    except:
        pass

    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            n = ord(s)
            if n < 0x10000:
                #return '\\u{0:04x}'.format(n)
                return '\\u%04x' % (n,)
            else:
                # surrogate pair
                n -= 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                s2 = 0xdc00 | (n & 0x3ff)
                return '\\u%04x\\u%04x' % (s1, s2)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'

def _encode(s, quote_numbers = True):
    if quote_numbers:
        qn = '"'
    else:
        qn = ''
    if isinstance(s, int) or isinstance(s, long):
        return qn + str(s) + qn
    elif isinstance(s, float):
        if s != s:
            return "NaN"
        elif s == PosInf:
            return "Infinity"
        elif s == NegInf:
            return "-Infinity"
        else:
            return qn + str(s) + qn
    else:
        return _encode_basestring_ascii(s)

def encode_key(s):
    return _encode(s, quote_numbers=True)

def encode_value(s):
    return _encode(s, quote_numbers=False)


class JSONCallback(RdbCallback):
    def __init__(self, out):
        self._out = out
        self._is_first_db = True
        self._has_databases = False
        self._is_first_key_in_db = True
        self._elements_in_key = 0 
        self._element_index = 0
        
    def start_rdb(self):
        self._out.write('[')
    
    def start_database(self, db_number):
        if not self._is_first_db:
            self._out.write('},')
        self._out.write('{')
        self._is_first_db = False
        self._has_databases = True
        self._is_first_key_in_db = True

    def end_database(self, db_number):
        pass
        
    def end_rdb(self):
        if self._has_databases:
            self._out.write('}')
        self._out.write(']')

    def _start_key(self, key, length):
        if not self._is_first_key_in_db:
            self._out.write(',')
        self._out.write('\r\n')
        self._is_first_key_in_db = False
        self._elements_in_key = length
        self._element_index = 0
    
    def _end_key(self, key):
        pass
    
    def _write_comma(self):
        if self._element_index > 0 and self._element_index < self._elements_in_key :
            self._out.write(',')
        self._element_index = self._element_index + 1
        
    def set(self, key, value, expiry, info):
        self._start_key(key, 0)
        self._out.write('%s:%s' % (encode_key(key), encode_value(value)))
    
    def start_hash(self, key, length, expiry, info):
        self._start_key(key, length)
        self._out.write('%s:{' % encode_key(key))
    
    def hset(self, key, field, value):
        self._write_comma()
        self._out.write('%s:%s' % (encode_key(field), encode_value(value)))
    
    def end_hash(self, key):
        self._end_key(key)
        self._out.write('}')
    
    def start_set(self, key, cardinality, expiry, info):
        self._start_key(key, cardinality)
        self._out.write('%s:[' % encode_key(key))

    def sadd(self, key, member):
        self._write_comma()
        self._out.write('%s' % encode_value(member))
    
    def end_set(self, key):
        self._end_key(key)
        self._out.write(']')
    
    def start_list(self, key, length, expiry, info):
        self._start_key(key, length)
        self._out.write('%s:[' % encode_key(key))
    
    def rpush(self, key, value) :
        self._write_comma()
        self._out.write('%s' % encode_value(value))
    
    def end_list(self, key):
        self._end_key(key)
        self._out.write(']')
    
    def start_sorted_set(self, key, length, expiry, info):
        self._start_key(key, length)
        self._out.write('%s:{' % encode_key(key))
    
    def zadd(self, key, score, member):
        self._write_comma()
        self._out.write('%s:%s' % (encode_key(member), encode_value(score)))
    
    def end_sorted_set(self, key):
        self._end_key(key)
        self._out.write('}')


class DiffCallback(RdbCallback):
    '''Prints the contents of RDB in a format that is unix sort friendly, 
        so that two rdb files can be diffed easily'''
    def __init__(self, out):
        self._out = out
        self._index = 0
        self._dbnum = 0
        
    def start_rdb(self):
        pass
    
    def start_database(self, db_number):
        self._dbnum = db_number

    def end_database(self, db_number):
        pass
        
    def end_rdb(self):
        pass
       
    def set(self, key, value, expiry, info):
        self._out.write('db=%d %s -> %s' % (self._dbnum, encode_key(key), encode_value(value)))
        self.newline()
    
    def start_hash(self, key, length, expiry, info):
        pass
    
    def hset(self, key, field, value):
        self._out.write('db=%d %s . %s -> %s' % (self._dbnum, encode_key(key), encode_key(field), encode_value(value)))
        self.newline()
    
    def end_hash(self, key):
        pass
    
    def start_set(self, key, cardinality, expiry, info):
        pass

    def sadd(self, key, member):
        self._out.write('db=%d %s { %s }' % (self._dbnum, encode_key(key), encode_value(member)))
        self.newline()
    
    def end_set(self, key):
        pass
    
    def start_list(self, key, length, expiry, info):
        self._index = 0
            
    def rpush(self, key, value) :
        self._out.write('db=%d %s[%d] -> %s' % (self._dbnum, encode_key(key), self._index, encode_value(value)))
        self.newline()
        self._index = self._index + 1
    
    def end_list(self, key):
        pass
    
    def start_sorted_set(self, key, length, expiry, info):
        self._index = 0
    
    def zadd(self, key, score, member):
        self._out.write('db=%d %s[%d] -> {%s, score=%s}' % (self._dbnum, encode_key(key), self._index, encode_key(member), encode_value(score)))
        self.newline()
        self._index = self._index + 1
    
    def end_sorted_set(self, key):
        pass

    def newline(self):
        self._out.write('\r\n')


def _unix_timestamp(dt):
     return calendar.timegm(dt.utctimetuple())


class ProtocolCallback(RdbCallback):
    def __init__(self, out):
        self._out = out
        self.reset()

    def reset(self):
        self._expires = {}

    def set_expiry(self, key, dt):
        self._expires[key] = dt

    def get_expiry_seconds(self, key):
        if key in self._expires:
            return _unix_timestamp(self._expires[key])
        return None

    def expires(self, key):
        return key in self._expires

    def pre_expiry(self, key, expiry):
        if expiry is not None:
            self.set_expiry(key, expiry)

    def post_expiry(self, key):
        if self.expires(key):
            self.expireat(key, self.get_expiry_seconds(key))

    def emit(self, *args):
        self._out.write(u"*" + unicode(len(args)) + u"\r\n")
        for arg in args:
            self._out.write(u"$" + unicode(len(unicode(arg))) + u"\r\n")
            self._out.write(unicode(arg) + u"\r\n")

    def start_database(self, db_number):
        self.reset()
        self.select(db_number)

    # String handling

    def set(self, key, value, expiry, info):
        self.pre_expiry(key, expiry)
        self.emit('SET', key, value)
        self.post_expiry(key)

    # Hash handling

    def start_hash(self, key, length, expiry, info):
        self.pre_expiry(key, expiry)

    def hset(self, key, field, value):
        self.emit('HSET', key, field, value)

    def end_hash(self, key):
        self.post_expiry(key)

    # Set handling

    def start_set(self, key, cardinality, expiry, info):
        self.pre_expiry(key, expiry)

    def sadd(self, key, member):
        self.emit('SADD', key, member)

    def end_set(self, key):
        self.post_expiry(key)

    # List handling

    def start_list(self, key, length, expiry, info):
        self.pre_expiry(key, expiry)

    def rpush(self, key, value):
        self.emit('RPUSH', key, value)

    def end_list(self, key):
        self.post_expiry(key)

    # Sorted set handling

    def start_sorted_set(self, key, length, expiry, info):
        self.pre_expiry(key, expiry)

    def zadd(self, key, score, member):
        self.emit('ZADD', key, score, member)

    def end_sorted_set(self, key):
        self.post_expiry(key)

    # Other misc commands

    def select(self, db_number):
        self.emit('SELECT', db_number)

    def expireat(self, key, timestamp):
        self.emit('EXPIREAT', key, timestamp)

########NEW FILE########
__FILENAME__ = rdb
#!/usr/bin/env python
import os
import sys
from optparse import OptionParser
from rdbtools import RdbParser, JSONCallback, DiffCallback, MemoryCallback, ProtocolCallback, PrintAllKeys

VALID_TYPES = ("hash", "set", "string", "list", "sortedset")
def main():
    usage = """usage: %prog [options] /path/to/dump.rdb

Example : %prog --command json -k "user.*" /var/redis/6379/dump.rdb"""

    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--command", dest="command",
                  help="Command to execute. Valid commands are json, diff, and protocol", metavar="FILE")
    parser.add_option("-f", "--file", dest="output",
                  help="Output file", metavar="FILE")
    parser.add_option("-n", "--db", dest="dbs", action="append",
                  help="Database Number. Multiple databases can be provided. If not specified, all databases will be included.")
    parser.add_option("-k", "--key", dest="keys", default=None,
                  help="Keys to export. This can be a regular expression")
    parser.add_option("-t", "--type", dest="types", action="append",
                  help="""Data types to include. Possible values are string, hash, set, sortedset, list. Multiple typees can be provided. 
                    If not specified, all data types will be returned""")
    
    (options, args) = parser.parse_args()
    
    if len(args) == 0:
        parser.error("Redis RDB file not specified")
    dump_file = args[0]
    
    filters = {}
    if options.dbs:
        filters['dbs'] = []
        for x in options.dbs:
            try:
                filters['dbs'].append(int(x))
            except ValueError:
                raise Exception('Invalid database number %s' %x)
    
    if options.keys:
        filters['keys'] = options.keys
    
    if options.types:
        filters['types'] = []
        for x in options.types:
            if not x in VALID_TYPES:
                raise Exception('Invalid type provided - %s. Expected one of %s' % (x, (", ".join(VALID_TYPES))))
            else:
                filters['types'].append(x)
    
    # TODO : Fix this ugly if-else code
    if options.output:
        with open(options.output, "wb") as f:
            if 'diff' == options.command:
                callback = DiffCallback(f)
            elif 'json' == options.command:
                callback = JSONCallback(f)
            elif 'memory' == options.command:
                reporter = PrintAllKeys(f)
                callback = MemoryCallback(reporter, 64)
            elif 'protocol' == options.command:
                callback = ProtocolCallback(f)
            else:
                raise Exception('Invalid Command %s' % options.command)
            parser = RdbParser(callback)
            parser.parse(dump_file)
    else:
        if 'diff' == options.command:
            callback = DiffCallback(sys.stdout)
        elif 'json' == options.command:
            callback = JSONCallback(sys.stdout)
        elif 'memory' == options.command:
            reporter = PrintAllKeys(sys.stdout)
            callback = MemoryCallback(reporter, 64)
        elif 'protocol' == options.command:
            callback = ProtocolCallback(sys.stdout)
        else:
            raise Exception('Invalid Command %s' % options.command)

        parser = RdbParser(callback, filters=filters)
        parser.parse(dump_file)
    
if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = redis_memory_for_key
#!/usr/bin/env python
import struct
import os
import sys

try :
    from StringIO import StringIO
except ImportError:
    from io import StringIO
    
from optparse import OptionParser
from rdbtools import RdbParser, JSONCallback, MemoryCallback
from rdbtools.callbacks import encode_key

from redis import StrictRedis
from redis.exceptions import ConnectionError, ResponseError

def main():
    usage = """usage: %prog [options] redis-key
Examples :
%prog user:13423
%prog -h localhost -p 6379 user:13423
"""

    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--server", dest="host", default="127.0.0.1", 
                  help="Redis Server hostname. Defaults to 127.0.0.1")
    parser.add_option("-p", "--port", dest="port", default=6379, type="int", 
                  help="Redis Server port. Defaults to 6379")
    parser.add_option("-a", "--password", dest="password", 
                  help="Password to use when connecting to the server")
    parser.add_option("-d", "--db", dest="db", default=0,
                  help="Database number, defaults to 0")
    
    (options, args) = parser.parse_args()
    
    if len(args) == 0:
        parser.error("Key not specified")
    redis_key = args[0]
    print_memory_for_key(redis_key, host=options.host, port=options.port, 
                    db=options.db, password=options.password)

def print_memory_for_key(key, host='localhost', port=6379, db=0, password=None):
    redis = connect_to_redis(host, port, db, password)
    reporter = PrintMemoryUsage()
    callback = MemoryCallback(reporter, 64)
    parser = RdbParser(callback, filters={})
    parser._key = key

    raw_dump = redis.execute_command('dump', key)
    if not raw_dump:
        sys.stderr.write('Key %s does not exist\n' % key)
        sys.exit(-1)
    
    stream = StringIO(raw_dump)
    data_type = read_unsigned_char(stream)
    parser.read_object(stream, data_type)

def connect_to_redis(host, port, db, password):
    try:
        redis = StrictRedis(host=host, port=port, db=db, password=password)
        if not check_redis_version(redis):
            sys.stderr.write('This script only works with Redis Server version 2.6.x or higher\n')
            sys.exit(-1)
    except ConnectionError as e:
        sys.stderr.write('Could not connect to Redis Server : %s\n' % e)
        sys.exit(-1)
    except ResponseError as e:
        sys.stderr.write('Could not connect to Redis Server : %s\n' % e)
        sys.exit(-1)
    return redis
    
def check_redis_version(redis):
    server_info = redis.info()
    version_str = server_info['redis_version']
    version = tuple(map(int, version_str.split('.')))
    
    if version[0] > 2 or (version[0] == 2 and version[1] >= 6) :
        return True
    else:
        return False

def read_unsigned_char(f) :
    return struct.unpack('B', f.read(1))[0]

class PrintMemoryUsage():
    def next_record(self, record) :
        print("%s\t\t\t\t%s" % ("Key", encode_key(record.key)))
        print("%s\t\t\t\t%s" % ("Bytes", record.bytes))
        print("%s\t\t\t\t%s" % ("Type", record.type))
        if record.type in ('set', 'list', 'sortedset', 'hash'):
            print("%s\t\t\t%s" % ("Encoding", record.encoding))
            print("%s\t\t%s" % ("Number of Elements", record.size))
            print("%s\t%s" % ("Length of Largest Element", record.len_largest_element))
        
        #print("%d,%s,%s,%d,%s,%d,%d\n" % (record.database, record.type, encode_key(record.key), 
        #                                         record.bytes, record.encoding, record.size, record.len_largest_element))

if __name__ == '__main__':
    #print_memory_for_key('x')
    main()



########NEW FILE########
__FILENAME__ = redis_profiler
#!/usr/bin/env python
import os
import sys
from string import Template
from optparse import OptionParser
from rdbtools import RdbParser, MemoryCallback, PrintAllKeys, StatsAggregator

def main(): 
    usage = """usage: %prog [options] /path/to/dump.rdb

Example 1 : %prog -k "user.*" -k "friends.*" -f memoryreport.html /var/redis/6379/dump.rdb
Example 2 : %prog /var/redis/6379/dump.rdb"""

    parser = OptionParser(usage=usage)

    parser.add_option("-f", "--file", dest="output",
                  help="Output file", metavar="FILE")
    parser.add_option("-k", "--key", dest="keys", action="append",
                  help="Keys that should be grouped together. Multiple regexes can be provided")
    
    (options, args) = parser.parse_args()
    
    if len(args) == 0:
        parser.error("Redis RDB file not specified")
    dump_file = args[0]
    
    if not options.output:
        output = "redis_memory_report.html"
    else:
        output = options.output

    stats = StatsAggregator()
    callback = MemoryCallback(stats, 64)
    parser = RdbParser(callback)
    parser.parse(dump_file)
    stats_as_json = stats.get_json()
    
    t = open(os.path.join(os.path.dirname(__file__),"report.html.template")).read()
    report_template = Template(t)
    html = report_template.substitute(REPORT_JSON = stats_as_json)
    print(html)
    
if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = memprofiler
from collections import namedtuple
import random
import json

from rdbtools.parser import RdbCallback
from rdbtools.callbacks import encode_key

ZSKIPLIST_MAXLEVEL=32
ZSKIPLIST_P=0.25
REDIS_SHARED_INTEGERS = 10000

MemoryRecord = namedtuple('MemoryRecord', ['database', 'type', 'key', 'bytes', 'encoding','size', 'len_largest_element'])

class StatsAggregator():
    def __init__(self, key_groupings = None):
        self.aggregates = {}
        self.scatters = {}
        self.histograms = {}

    def next_record(self, record):
        self.add_aggregate('database_memory', record.database, record.bytes)
        self.add_aggregate('type_memory', record.type, record.bytes)
        self.add_aggregate('encoding_memory', record.encoding, record.bytes)
        
        self.add_aggregate('type_count', record.type, 1)
        self.add_aggregate('encoding_count', record.encoding, 1)
    
        self.add_histogram(record.type + "_length", record.size)
        self.add_histogram(record.type + "_memory", (record.bytes/10) * 10)
        
        if record.type == 'list':
            self.add_scatter('list_memory_by_length', record.bytes, record.size)
        elif record.type == 'hash':
            self.add_scatter('hash_memory_by_length', record.bytes, record.size)
        elif record.type == 'set':
            self.add_scatter('set_memory_by_length', record.bytes, record.size)
        elif record.type == 'sortedset':
            self.add_scatter('sortedset_memory_by_length', record.bytes, record.size)
        elif record.type == 'string':
            self.add_scatter('string_memory_by_length', record.bytes, record.size)
        else:
            raise Exception('Invalid data type %s' % record.type)

    def add_aggregate(self, heading, subheading, metric):
        if not heading in self.aggregates :
            self.aggregates[heading] = {}
        
        if not subheading in self.aggregates[heading]:
            self.aggregates[heading][subheading] = 0
            
        self.aggregates[heading][subheading] += metric
    
    def add_histogram(self, heading, metric):
        if not heading in self.histograms:
            self.histograms[heading] = {}

        if not metric in self.histograms[heading]:
            self.histograms[heading][metric] = 1
        else :
            self.histograms[heading][metric] += 1
    
    def add_scatter(self, heading, x, y):
        if not heading in self.scatters:
            self.scatters[heading] = []
        self.scatters[heading].append([x, y])
  
    def get_json(self):
        return json.dumps({"aggregates":self.aggregates, "scatters":self.scatters, "histograms":self.histograms})
        
class PrintAllKeys():
    def __init__(self, out):
        self._out = out
        self._out.write("%s,%s,%s,%s,%s,%s,%s\n" % ("database", "type", "key", 
                                                 "size_in_bytes", "encoding", "num_elements", "len_largest_element"))
    
    def next_record(self, record) :
        self._out.write("%d,%s,%s,%d,%s,%d,%d\n" % (record.database, record.type, encode_key(record.key), 
                                                 record.bytes, record.encoding, record.size, record.len_largest_element))
    
class MemoryCallback(RdbCallback):
    '''Calculates the memory used if this rdb file were loaded into RAM
        The memory usage is approximate, and based on heuristics.
    '''
    def __init__(self, stream, architecture):
        self._stream = stream
        self._dbnum = 0
        self._current_size = 0
        self._current_encoding = None
        self._current_length = 0
        self._len_largest_element = 0
        
        if architecture == 64 or architecture == '64':
            self._pointer_size = 8
        elif architecture == 32 or architecture == '32':
            self._pointer_size = 4
        
    def start_rdb(self):
        pass

    def start_database(self, db_number):
        self._dbnum = db_number

    def end_database(self, db_number):
        pass
        
    def end_rdb(self):
        pass
       
    def set(self, key, value, expiry, info):
        self._current_encoding = info['encoding']
        size = self.sizeof_string(key) + self.sizeof_string(value) + self.top_level_object_overhead()
        size += 2*self.robj_overhead()
        size += self.key_expiry_overhead(expiry)
        
        length = element_length(value)
        record = MemoryRecord(self._dbnum, "string", key, size, self._current_encoding, length, length)
        self._stream.next_record(record)
        self.end_key()
    
    def start_hash(self, key, length, expiry, info):
        self._current_encoding = info['encoding']
        self._current_length = length        
        size = self.sizeof_string(key)
        size += 2*self.robj_overhead()
        size += self.top_level_object_overhead()
        size += self.key_expiry_overhead(expiry)
        
        if 'sizeof_value' in info:
            size += info['sizeof_value']
        elif 'encoding' in info and info['encoding'] == 'hashtable':
            size += self.hashtable_overhead(length)
        else:
            raise Exception('start_hash', 'Could not find encoding or sizeof_value in info object %s' % info)
        self._current_size = size
    
    def hset(self, key, field, value):
        if(element_length(field) > self._len_largest_element) :
            self._len_largest_element = element_length(field)
        if(element_length(value) > self._len_largest_element) :
            self._len_largest_element = element_length(value)
        
        if self._current_encoding == 'hashtable':
            self._current_size += self.sizeof_string(field)
            self._current_size += self.sizeof_string(value)
            self._current_size += self.hashtable_entry_overhead()
            self._current_size += 2*self.robj_overhead()
    
    def end_hash(self, key):
        record = MemoryRecord(self._dbnum, "hash", key, self._current_size, self._current_encoding, self._current_length, self._len_largest_element)
        self._stream.next_record(record)
        self.end_key()
    
    def start_set(self, key, cardinality, expiry, info):
        # A set is exactly like a hashmap
        self.start_hash(key, cardinality, expiry, info)

    def sadd(self, key, member):
        if(element_length(member) > self._len_largest_element) :
            self._len_largest_element = element_length(member)
            
        if self._current_encoding == 'hashtable':
            self._current_size += self.sizeof_string(member)
            self._current_size += self.hashtable_entry_overhead()
            self._current_size += self.robj_overhead()
    
    def end_set(self, key):
        record = MemoryRecord(self._dbnum, "set", key, self._current_size, self._current_encoding, self._current_length, self._len_largest_element)
        self._stream.next_record(record)
        self.end_key()
    
    def start_list(self, key, length, expiry, info):
        self._current_length = length
        self._current_encoding = info['encoding']
        size = self.sizeof_string(key)
        size += 2*self.robj_overhead()
        size += self.top_level_object_overhead()
        size += self.key_expiry_overhead(expiry)
        
        if 'sizeof_value' in info:
            size += info['sizeof_value']
        elif 'encoding' in info and info['encoding'] == 'linkedlist':
            size += self.linkedlist_overhead()
        else:
            raise Exception('start_list', 'Could not find encoding or sizeof_value in info object %s' % info)
        self._current_size = size
            
    def rpush(self, key, value) :
        if(element_length(value) > self._len_largest_element) :
            self._len_largest_element = element_length(value)
        
        if self._current_encoding == 'linkedlist':
            self._current_size += self.sizeof_string(value)
            self._current_size += self.linkedlist_entry_overhead()
            self._current_size += self.robj_overhead()
    
    def end_list(self, key):
        record = MemoryRecord(self._dbnum, "list", key, self._current_size, self._current_encoding, self._current_length, self._len_largest_element)
        self._stream.next_record(record)
        self.end_key()
    
    def start_sorted_set(self, key, length, expiry, info):
        self._current_length = length
        self._current_encoding = info['encoding']
        size = self.sizeof_string(key)
        size += 2*self.robj_overhead()
        size += self.top_level_object_overhead()
        size += self.key_expiry_overhead(expiry)
        
        if 'sizeof_value' in info:
            size += info['sizeof_value']
        elif 'encoding' in info and info['encoding'] == 'skiplist':
            size += self.skiplist_overhead(length)
        else:
            raise Exception('start_sorted_set', 'Could not find encoding or sizeof_value in info object %s' % info)
        self._current_size = size
    
    def zadd(self, key, score, member):
        if(element_length(member) > self._len_largest_element):
            self._len_largest_element = element_length(member)
        
        if self._current_encoding == 'skiplist':
            self._current_size += 8 # self.sizeof_string(score)
            self._current_size += self.sizeof_string(member)
            self._current_size += 2*self.robj_overhead()
            self._current_size += self.skiplist_entry_overhead()
    
    def end_sorted_set(self, key):
        record = MemoryRecord(self._dbnum, "sortedset", key, self._current_size, self._current_encoding, self._current_length, self._len_largest_element)
        self._stream.next_record(record)
        self.end_key()
        
    def end_key(self):
        self._current_encoding = None
        self._current_size = 0
        self._len_largest_element = 0
    
    def sizeof_string(self, string):
        # See struct sdshdr over here https://github.com/antirez/redis/blob/unstable/src/sds.h
        # int len :  4 bytes
        # int free : 4 bytes
        # char buf[] : size will be the length of the string
        # 1 extra byte is used to store the null character at the end of the string
        # Redis internally stores integers as a long
        #  Integers less than REDIS_SHARED_INTEGERS are stored in a shared memory pool
        try:
            num = int(string)
            if num < REDIS_SHARED_INTEGERS :
                return 0
            else :
                return 8
        except ValueError:
            pass
        return len(string) + 8 + 1 + self.malloc_overhead()

    def top_level_object_overhead(self):
        # Each top level object is an entry in a dictionary, and so we have to include 
        # the overhead of a dictionary entry
        return self.hashtable_entry_overhead()

    def key_expiry_overhead(self, expiry):
        # If there is no expiry, there isn't any overhead
        if not expiry:
            return 0
        # Key expiry is stored in a hashtable, so we have to pay for the cost of a hashtable entry
        # The timestamp itself is stored as an int64, which is a 8 bytes
        return self.hashtable_entry_overhead() + 8
        
    def hashtable_overhead(self, size):
        # See  https://github.com/antirez/redis/blob/unstable/src/dict.h
        # See the structures dict and dictht
        # 2 * (3 unsigned longs + 1 pointer) + 2 ints + 2 pointers
        #   = 56 + 4 * sizeof_pointer()
        # 
        # Additionally, see **table in dictht
        # The length of the table is the next power of 2
        # When the hashtable is rehashing, another instance of **table is created
        # We are assuming 0.5 percent probability of rehashing, and so multiply 
        # the size of **table by 1.5
        return 56 + 4*self.sizeof_pointer() + self.next_power(size)*self.sizeof_pointer()*1.5
        
    def hashtable_entry_overhead(self):
        # See  https://github.com/antirez/redis/blob/unstable/src/dict.h
        # Each dictEntry has 3 pointers 
        return 3*self.sizeof_pointer()
    
    def linkedlist_overhead(self):
        # See https://github.com/antirez/redis/blob/unstable/src/adlist.h
        # A list has 5 pointers + an unsigned long
        return 8 + 5*self.sizeof_pointer()
    
    def linkedlist_entry_overhead(self):
        # See https://github.com/antirez/redis/blob/unstable/src/adlist.h
        # A node has 3 pointers
        return 3*self.sizeof_pointer()
    
    def skiplist_overhead(self, size):
        return 2*self.sizeof_pointer() + self.hashtable_overhead(size) + (2*self.sizeof_pointer() + 16)
    
    def skiplist_entry_overhead(self):
        return self.hashtable_entry_overhead() + 2*self.sizeof_pointer() + 8 + (self.sizeof_pointer() + 8) * self.zset_random_level()
    
    def robj_overhead(self):
        return self.sizeof_pointer() + 8
        
    def malloc_overhead(self):
        return self.size_t()

    def size_t(self):
        return self.sizeof_pointer()
        
    def sizeof_pointer(self):
        return self._pointer_size
        
    def next_power(self, size):
        power = 1
        while (power <= size) :
            power = power << 1
        return power
 
    def zset_random_level(self):
        level = 1
        rint = random.randint(0, 0xFFFF)
        while (rint < ZSKIPLIST_P * 0xFFFF):
            level += 1
            rint = random.randint(0, 0xFFFF)        
        if level < ZSKIPLIST_MAXLEVEL :
            return level
        else:
            return ZSKIPLIST_MAXLEVEL
        

def element_length(element):
    if isinstance(element, int):
        return 8
    if isinstance(element, long):
        return 16
    else:
        return len(element)
    

########NEW FILE########
__FILENAME__ = parser
import struct
import io
import sys
import datetime
import re

try :
    from StringIO import StringIO
except ImportError:
    from io import StringIO
    
REDIS_RDB_6BITLEN = 0
REDIS_RDB_14BITLEN = 1
REDIS_RDB_32BITLEN = 2
REDIS_RDB_ENCVAL = 3

REDIS_RDB_OPCODE_EXPIRETIME_MS = 252
REDIS_RDB_OPCODE_EXPIRETIME = 253
REDIS_RDB_OPCODE_SELECTDB = 254
REDIS_RDB_OPCODE_EOF = 255

REDIS_RDB_TYPE_STRING = 0
REDIS_RDB_TYPE_LIST = 1
REDIS_RDB_TYPE_SET = 2
REDIS_RDB_TYPE_ZSET = 3
REDIS_RDB_TYPE_HASH = 4
REDIS_RDB_TYPE_HASH_ZIPMAP = 9
REDIS_RDB_TYPE_LIST_ZIPLIST = 10
REDIS_RDB_TYPE_SET_INTSET = 11
REDIS_RDB_TYPE_ZSET_ZIPLIST = 12
REDIS_RDB_TYPE_HASH_ZIPLIST = 13

REDIS_RDB_ENC_INT8 = 0
REDIS_RDB_ENC_INT16 = 1
REDIS_RDB_ENC_INT32 = 2
REDIS_RDB_ENC_LZF = 3

DATA_TYPE_MAPPING = {
    0 : "string", 1 : "list", 2 : "set", 3 : "sortedset", 4 : "hash", 
    9 : "hash", 10 : "list", 11 : "set", 12 : "sortedset", 13 : "hash"}

class RdbCallback:
    """
    A Callback to handle events as the Redis dump file is parsed.
    This callback provides a serial and fast access to the dump file.
    
    """
    def start_rdb(self):
        """
        Called once we know we are dealing with a valid redis dump file
        
        """
        pass
        
    def start_database(self, db_number):
        """
        Called to indicate database the start of database `db_number` 
        
        Once a database starts, another database cannot start unless 
        the first one completes and then `end_database` method is called
        
        Typically, callbacks store the current database number in a class variable
        
        """     
        pass
    
    def set(self, key, value, expiry, info):
        """
        Callback to handle a key with a string value and an optional expiry
        
        `key` is the redis key
        `value` is a string or a number
        `expiry` is a datetime object. None and can be None
        `info` is a dictionary containing additional information about this object.
        
        """
        pass
    
    def start_hash(self, key, length, expiry, info):
        """Callback to handle the start of a hash
        
        `key` is the redis key
        `length` is the number of elements in this hash. 
        `expiry` is a `datetime` object. None means the object does not expire
        `info` is a dictionary containing additional information about this object.
        
        After `start_hash`, the method `hset` will be called with this `key` exactly `length` times.
        After that, the `end_hash` method will be called.
        
        """
        pass
    
    def hset(self, key, field, value):
        """
        Callback to insert a field=value pair in an existing hash
        
        `key` is the redis key for this hash
        `field` is a string
        `value` is the value to store for this field
        
        """
        pass
    
    def end_hash(self, key):
        """
        Called when there are no more elements in the hash
        
        `key` is the redis key for the hash
        
        """
        pass
    
    def start_set(self, key, cardinality, expiry, info):
        """
        Callback to handle the start of a hash
        
        `key` is the redis key
        `cardinality` is the number of elements in this set
        `expiry` is a `datetime` object. None means the object does not expire
        `info` is a dictionary containing additional information about this object.
        
        After `start_set`, the  method `sadd` will be called with `key` exactly `cardinality` times
        After that, the `end_set` method will be called to indicate the end of the set.
        
        Note : This callback handles both Int Sets and Regular Sets
        
        """
        pass

    def sadd(self, key, member):
        """
        Callback to inser a new member to this set
        
        `key` is the redis key for this set
        `member` is the member to insert into this set
        
        """
        pass
    
    def end_set(self, key):
        """
        Called when there are no more elements in this set 
        
        `key` the redis key for this set
        
        """
        pass
    
    def start_list(self, key, length, expiry, info):
        """
        Callback to handle the start of a list
        
        `key` is the redis key for this list
        `length` is the number of elements in this list
        `expiry` is a `datetime` object. None means the object does not expire
        `info` is a dictionary containing additional information about this object.
        
        After `start_list`, the method `rpush` will be called with `key` exactly `length` times
        After that, the `end_list` method will be called to indicate the end of the list
        
        Note : This callback handles both Zip Lists and Linked Lists.
        
        """
        pass
    
    def rpush(self, key, value) :
        """
        Callback to insert a new value into this list
        
        `key` is the redis key for this list
        `value` is the value to be inserted
        
        Elements must be inserted to the end (i.e. tail) of the existing list.
        
        """
        pass
    
    def end_list(self, key):
        """
        Called when there are no more elements in this list
        
        `key` the redis key for this list
        
        """
        pass
    
    def start_sorted_set(self, key, length, expiry, info):
        """
        Callback to handle the start of a sorted set
        
        `key` is the redis key for this sorted
        `length` is the number of elements in this sorted set
        `expiry` is a `datetime` object. None means the object does not expire
        `info` is a dictionary containing additional information about this object.
        
        After `start_sorted_set`, the method `zadd` will be called with `key` exactly `length` times. 
        Also, `zadd` will be called in a sorted order, so as to preserve the ordering of this sorted set.
        After that, the `end_sorted_set` method will be called to indicate the end of this sorted set
        
        Note : This callback handles sorted sets in that are stored as ziplists or skiplists
        
        """
        pass
    
    def zadd(self, key, score, member):
        """Callback to insert a new value into this sorted set
        
        `key` is the redis key for this sorted set
        `score` is the score for this `value`
        `value` is the element being inserted
        """
        pass
    
    def end_sorted_set(self, key):
        """
        Called when there are no more elements in this sorted set
        
        `key` is the redis key for this sorted set
        
        """
        pass
    
    def end_database(self, db_number):
        """
        Called when the current database ends
        
        After `end_database`, one of the methods are called - 
        1) `start_database` with a new database number
            OR
        2) `end_rdb` to indicate we have reached the end of the file
        
        """
        pass
    
    def end_rdb(self):
        """Called to indicate we have completed parsing of the dump file"""
        pass

class RdbParser :
    """
    A Parser for Redis RDB Files
    
    This class is similar in spirit to a SAX parser for XML files.
    The dump file is parsed sequentially. As and when objects are discovered,
    appropriate methods in the callback are called. 
        
    Typical usage :
        callback = MyRdbCallback() # Typically a subclass of RdbCallback
        parser = RdbParser(callback)
        parser.parse('/var/redis/6379/dump.rdb')
    
    filter is a dictionary with the following keys
        {"dbs" : [0, 1], "keys" : "foo.*", "types" : ["hash", "set", "sortedset", "list", "string"]}
        
        If filter is None, results will not be filtered
        If dbs, keys or types is None or Empty, no filtering will be done on that axis
    """
    def __init__(self, callback, filters = None) :
        """
            `callback` is the object that will receive parse events
        """
        self._callback = callback
        self._key = None
        self._expiry = None
        self.init_filter(filters)

    def parse(self, filename):
        """
        Parse a redis rdb dump file, and call methods in the 
        callback object during the parsing operation.
        """
        with open(filename, "rb") as f:
            self.verify_magic_string(f.read(5))
            self.verify_version(f.read(4))
            self._callback.start_rdb()
            
            is_first_database = True
            db_number = 0
            while True :
                self._expiry = None
                data_type = read_unsigned_char(f)
                
                if data_type == REDIS_RDB_OPCODE_EXPIRETIME_MS :
                    self._expiry = to_datetime(read_unsigned_long(f) * 1000)
                    data_type = read_unsigned_char(f)
                elif data_type == REDIS_RDB_OPCODE_EXPIRETIME :
                    self._expiry = to_datetime(read_unsigned_int(f) * 1000000)
                    data_type = read_unsigned_char(f)
                
                if data_type == REDIS_RDB_OPCODE_SELECTDB :
                    if not is_first_database :
                        self._callback.end_database(db_number)
                    is_first_database = False
                    db_number = self.read_length(f)
                    self._callback.start_database(db_number)
                    continue
                
                if data_type == REDIS_RDB_OPCODE_EOF :
                    self._callback.end_database(db_number)
                    self._callback.end_rdb()
                    break

                if self.matches_filter(db_number) :
                    self._key = self.read_string(f)
                    if self.matches_filter(db_number, self._key, data_type):
                        self.read_object(f, data_type)
                    else:
                        self.skip_object(f, data_type)
                else :
                    self.skip_key_and_object(f, data_type)

    def read_length_with_encoding(self, f) :
        length = 0
        is_encoded = False
        bytes = []
        bytes.append(read_unsigned_char(f))
        enc_type = (bytes[0] & 0xC0) >> 6
        if enc_type == REDIS_RDB_ENCVAL :
            is_encoded = True
            length = bytes[0] & 0x3F
        elif enc_type == REDIS_RDB_6BITLEN :
            length = bytes[0] & 0x3F
        elif enc_type == REDIS_RDB_14BITLEN :
            bytes.append(read_unsigned_char(f))
            length = ((bytes[0]&0x3F)<<8)|bytes[1]
        else :
            length = ntohl(f)
        return (length, is_encoded)

    def read_length(self, f) :
        return self.read_length_with_encoding(f)[0]

    def read_string(self, f) :
        tup = self.read_length_with_encoding(f)
        length = tup[0]
        is_encoded = tup[1]
        val = None
        if is_encoded :
            if length == REDIS_RDB_ENC_INT8 :
                val = read_signed_char(f)
            elif length == REDIS_RDB_ENC_INT16 :
                val = read_signed_short(f)
            elif length == REDIS_RDB_ENC_INT32 :
                val = read_signed_int(f)
            elif length == REDIS_RDB_ENC_LZF :
                clen = self.read_length(f)
                l = self.read_length(f)
                val = self.lzf_decompress(f.read(clen), l)
        else :
            val = f.read(length)
        return val

    # Read an object for the stream
    # f is the redis file 
    # enc_type is the type of object
    def read_object(self, f, enc_type) :
        if enc_type == REDIS_RDB_TYPE_STRING :
            val = self.read_string(f)
            self._callback.set(self._key, val, self._expiry, info={'encoding':'string'})
        elif enc_type == REDIS_RDB_TYPE_LIST :
            # A redis list is just a sequence of strings
            # We successively read strings from the stream and create a list from it
            # The lists are in order i.e. the first string is the head, 
            # and the last string is the tail of the list
            length = self.read_length(f)
            self._callback.start_list(self._key, length, self._expiry, info={'encoding':'linkedlist' })
            for count in xrange(0, length) :
                val = self.read_string(f)
                self._callback.rpush(self._key, val)
            self._callback.end_list(self._key)
        elif enc_type == REDIS_RDB_TYPE_SET :
            # A redis list is just a sequence of strings
            # We successively read strings from the stream and create a set from it
            # Note that the order of strings is non-deterministic
            length = self.read_length(f)
            self._callback.start_set(self._key, length, self._expiry, info={'encoding':'hashtable'})
            for count in xrange(0, length) :
                val = self.read_string(f)
                self._callback.sadd(self._key, val)
            self._callback.end_set(self._key)
        elif enc_type == REDIS_RDB_TYPE_ZSET :
            length = self.read_length(f)
            self._callback.start_sorted_set(self._key, length, self._expiry, info={'encoding':'skiplist'})
            for count in xrange(0, length) :
                val = self.read_string(f)
                dbl_length = read_unsigned_char(f)
                score = f.read(dbl_length)
                if isinstance(score, str):
                    score = float(score)
                self._callback.zadd(self._key, score, val)
            self._callback.end_sorted_set(self._key)
        elif enc_type == REDIS_RDB_TYPE_HASH :
            length = self.read_length(f)
            self._callback.start_hash(self._key, length, self._expiry, info={'encoding':'hashtable'})
            for count in xrange(0, length) :
                field = self.read_string(f)
                value = self.read_string(f)
                self._callback.hset(self._key, field, value)
            self._callback.end_hash(self._key)
        elif enc_type == REDIS_RDB_TYPE_HASH_ZIPMAP :
            self.read_zipmap(f)
        elif enc_type == REDIS_RDB_TYPE_LIST_ZIPLIST :
            self.read_ziplist(f)
        elif enc_type == REDIS_RDB_TYPE_SET_INTSET :
            self.read_intset(f)
        elif enc_type == REDIS_RDB_TYPE_ZSET_ZIPLIST :
            self.read_zset_from_ziplist(f)
        elif enc_type == REDIS_RDB_TYPE_HASH_ZIPLIST :
            self.read_hash_from_ziplist(f)
        else :
            raise Exception('read_object', 'Invalid object type %d for key %s' % (enc_type, self._key))

    def skip_key_and_object(self, f, data_type):
        self.skip_string(f)
        self.skip_object(f, data_type)

    def skip_string(self, f):
        tup = self.read_length_with_encoding(f)
        length = tup[0]
        is_encoded = tup[1]
        bytes_to_skip = 0
        if is_encoded :
            if length == REDIS_RDB_ENC_INT8 :
                bytes_to_skip = 1
            elif length == REDIS_RDB_ENC_INT16 :
                bytes_to_skip = 2
            elif length == REDIS_RDB_ENC_INT32 :
                bytes_to_skip = 4
            elif length == REDIS_RDB_ENC_LZF :
                clen = self.read_length(f)
                l = self.read_length(f)
                bytes_to_skip = clen
        else :
            bytes_to_skip = length
        
        skip(f, bytes_to_skip)

    def skip_object(self, f, enc_type):
        skip_strings = 0
        if enc_type == REDIS_RDB_TYPE_STRING :
            skip_strings = 1
        elif enc_type == REDIS_RDB_TYPE_LIST :
            skip_strings = self.read_length(f)
        elif enc_type == REDIS_RDB_TYPE_SET :
            skip_strings = self.read_length(f)
        elif enc_type == REDIS_RDB_TYPE_ZSET :
            skip_strings = self.read_length(f) * 2
        elif enc_type == REDIS_RDB_TYPE_HASH :
            skip_strings = self.read_length(f) * 2
        elif enc_type == REDIS_RDB_TYPE_HASH_ZIPMAP :
            skip_strings = 1
        elif enc_type == REDIS_RDB_TYPE_LIST_ZIPLIST :
            skip_strings = 1
        elif enc_type == REDIS_RDB_TYPE_SET_INTSET :
            skip_strings = 1
        elif enc_type == REDIS_RDB_TYPE_ZSET_ZIPLIST :
            skip_strings = 1
        elif enc_type == REDIS_RDB_TYPE_HASH_ZIPLIST :
            skip_strings = 1
        else :
            raise Exception('read_object', 'Invalid object type %d for key %s' % (enc_type, self._key))
        for x in xrange(0, skip_strings):
            self.skip_string(f)


    def read_intset(self, f) :
        raw_string = self.read_string(f)
        buff = StringIO(raw_string)
        encoding = read_unsigned_int(buff)
        num_entries = read_unsigned_int(buff)
        self._callback.start_set(self._key, num_entries, self._expiry, info={'encoding':'intset', 'sizeof_value':len(raw_string)})
        for x in xrange(0, num_entries) :
            if encoding == 8 :
                entry = read_unsigned_long(buff)
            elif encoding == 4 :
                entry = read_unsigned_int(buff)
            elif encoding == 2 :
                entry = read_unsigned_short(buff)
            else :
                raise Exception('read_intset', 'Invalid encoding %d for key %s' % (encoding, self._key))
            self._callback.sadd(self._key, entry)
        self._callback.end_set(self._key)

    def read_ziplist(self, f) :
        raw_string = self.read_string(f)
        buff = StringIO(raw_string)
        zlbytes = read_unsigned_int(buff)
        tail_offset = read_unsigned_int(buff)
        num_entries = read_unsigned_short(buff)
        self._callback.start_list(self._key, num_entries, self._expiry, info={'encoding':'ziplist', 'sizeof_value':len(raw_string)})
        for x in xrange(0, num_entries) :
            val = self.read_ziplist_entry(buff)
            self._callback.rpush(self._key, val)
        zlist_end = read_unsigned_char(buff)
        if zlist_end != 255 : 
            raise Exception('read_ziplist', "Invalid zip list end - %d for key %s" % (zlist_end, self._key))
        self._callback.end_list(self._key)

    def read_zset_from_ziplist(self, f) :
        raw_string = self.read_string(f)
        buff = StringIO(raw_string)
        zlbytes = read_unsigned_int(buff)
        tail_offset = read_unsigned_int(buff)
        num_entries = read_unsigned_short(buff)
        if (num_entries % 2) :
            raise Exception('read_zset_from_ziplist', "Expected even number of elements, but found %d for key %s" % (num_entries, self._key))
        num_entries = num_entries /2
        self._callback.start_sorted_set(self._key, num_entries, self._expiry, info={'encoding':'ziplist', 'sizeof_value':len(raw_string)})
        for x in xrange(0, num_entries) :
            member = self.read_ziplist_entry(buff)
            score = self.read_ziplist_entry(buff)
            if isinstance(score, str) :
                score = float(score)
            self._callback.zadd(self._key, score, member)
        zlist_end = read_unsigned_char(buff)
        if zlist_end != 255 : 
            raise Exception('read_zset_from_ziplist', "Invalid zip list end - %d for key %s" % (zlist_end, self._key))
        self._callback.end_sorted_set(self._key)

    def read_hash_from_ziplist(self, f) :
        raw_string = self.read_string(f)
        buff = StringIO(raw_string)
        zlbytes = read_unsigned_int(buff)
        tail_offset = read_unsigned_int(buff)
        num_entries = read_unsigned_short(buff)
        if (num_entries % 2) :
            raise Exception('read_hash_from_ziplist', "Expected even number of elements, but found %d for key %s" % (num_entries, self._key))
        num_entries = num_entries /2
        self._callback.start_hash(self._key, num_entries, self._expiry, info={'encoding':'ziplist', 'sizeof_value':len(raw_string)})
        for x in xrange(0, num_entries) :
            field = self.read_ziplist_entry(buff)
            value = self.read_ziplist_entry(buff)
            self._callback.hset(self._key, field, value)
        zlist_end = read_unsigned_char(buff)
        if zlist_end != 255 : 
            raise Exception('read_hash_from_ziplist', "Invalid zip list end - %d for key %s" % (zlist_end, self._key))
        self._callback.end_hash(self._key)
    
    
    def read_ziplist_entry(self, f) :
        length = 0
        value = None
        prev_length = read_unsigned_char(f)
        if prev_length == 254 :
            prev_length = read_unsigned_int(f)
        entry_header = read_unsigned_char(f)
        if (entry_header >> 6) == 0 :
            length = entry_header & 0x3F
            value = f.read(length)
        elif (entry_header >> 6) == 1 :
            length = ((entry_header & 0x3F) << 8) | read_unsigned_char(f)
            value = f.read(length)
        elif (entry_header >> 6) == 2 :
            length = read_big_endian_unsigned_int(f)
            value = f.read(length)
        elif (entry_header >> 4) == 12 :
            value = read_signed_short(f)
        elif (entry_header >> 4) == 13 :
            value = read_signed_int(f)
        elif (entry_header >> 4) == 14 :
            value = read_signed_long(f)
        elif (entry_header == 240) :
            value = read_24bit_signed_number(f)
        elif (entry_header == 254) :
            value = read_signed_char(f)
        elif (entry_header >= 241 and entry_header <= 253) :
            value = entry_header - 241
        else :
            raise Exception('read_ziplist_entry', 'Invalid entry_header %d for key %s' % (entry_header, self._key))
        return value
        
    def read_zipmap(self, f) :
        raw_string = self.read_string(f)
        buff = io.BytesIO(bytearray(raw_string))
        num_entries = read_unsigned_char(buff)
        self._callback.start_hash(self._key, num_entries, self._expiry, info={'encoding':'zipmap', 'sizeof_value':len(raw_string)})
        while True :
            next_length = self.read_zipmap_next_length(buff)
            if next_length is None :
                break
            key = buff.read(next_length)
            next_length = self.read_zipmap_next_length(buff)
            if next_length is None :
                raise Exception('read_zip_map', 'Unexepcted end of zip map for key %s' % self._key)        
            free = read_unsigned_char(buff)
            value = buff.read(next_length)
            try:
                value = int(value)
            except ValueError:
                pass
            
            skip(buff, free)
            self._callback.hset(self._key, key, value)
        self._callback.end_hash(self._key)

    def read_zipmap_next_length(self, f) :
        num = read_unsigned_char(f)
        if num < 254:
            return num
        elif num == 254:
            return read_unsigned_int(f)
        else:
            return None

    def verify_magic_string(self, magic_string) :
        if magic_string != 'REDIS' :
            raise Exception('verify_magic_string', 'Invalid File Format')

    def verify_version(self, version_str) :
        version = int(version_str)
        if version < 1 or version > 6 : 
            raise Exception('verify_version', 'Invalid RDB version number %d' % version)

    def init_filter(self, filters):
        self._filters = {}
        if not filters:
            filters={}

        if not 'dbs' in filters:
            self._filters['dbs'] = None
        elif isinstance(filters['dbs'], int):
            self._filters['dbs'] = (filters['dbs'], )
        elif isinstance(filters['dbs'], list):
            self._filters['dbs'] = [int(x) for x in filters['dbs']]
        else:
            raise Exception('init_filter', 'invalid value for dbs in filter %s' %filters['dbs'])
        
        if not ('keys' in filters and filters['keys']):
            self._filters['keys'] = re.compile(".*")
        else:
            self._filters['keys'] = re.compile(filters['keys'])

        if not 'types' in filters:
            self._filters['types'] = ('set', 'hash', 'sortedset', 'string', 'list')
        elif isinstance(filters['types'], str):
            self._filters['types'] = (filters['types'], )
        elif isinstance(filters['types'], list):
            self._filters['types'] = [str(x) for x in filters['types']]
        else:
            raise Exception('init_filter', 'invalid value for types in filter %s' %filters['types'])
        
    def matches_filter(self, db_number, key=None, data_type=None):
        if self._filters['dbs'] and (not db_number in self._filters['dbs']):
            return False
        if key and (not self._filters['keys'].match(str(key))):
            return False

        if data_type is not None and (not self.get_logical_type(data_type) in self._filters['types']):
            return False
        return True
    
    def get_logical_type(self, data_type):
        return DATA_TYPE_MAPPING[data_type]
        
    def lzf_decompress(self, compressed, expected_length):
        in_stream = bytearray(compressed)
        in_len = len(in_stream)
        in_index = 0
        out_stream = bytearray()
        out_index = 0
    
        while in_index < in_len :
            ctrl = in_stream[in_index]
            if not isinstance(ctrl, int) :
                raise Exception('lzf_decompress', 'ctrl should be a number %s for key %s' % (str(ctrl), self._key))
            in_index = in_index + 1
            if ctrl < 32 :
                for x in xrange(0, ctrl + 1) :
                    out_stream.append(in_stream[in_index])
                    #sys.stdout.write(chr(in_stream[in_index]))
                    in_index = in_index + 1
                    out_index = out_index + 1
            else :
                length = ctrl >> 5
                if length == 7 :
                    length = length + in_stream[in_index]
                    in_index = in_index + 1
                
                ref = out_index - ((ctrl & 0x1f) << 8) - in_stream[in_index] - 1
                in_index = in_index + 1
                for x in xrange(0, length + 2) :
                    out_stream.append(out_stream[ref])
                    ref = ref + 1
                    out_index = out_index + 1
        if len(out_stream) != expected_length :
            raise Exception('lzf_decompress', 'Expected lengths do not match %d != %d for key %s' % (len(out_stream), expected_length, self._key))
        return str(out_stream)

def skip(f, free):
    if free :
        f.read(free)

def ntohl(f) :
    val = read_unsigned_int(f)
    new_val = 0
    new_val = new_val | ((val & 0x000000ff) << 24)
    new_val = new_val | ((val & 0xff000000) >> 24)
    new_val = new_val | ((val & 0x0000ff00) << 8)
    new_val = new_val | ((val & 0x00ff0000) >> 8)
    return new_val

def to_datetime(usecs_since_epoch):
    seconds_since_epoch = usecs_since_epoch / 1000000
    useconds = usecs_since_epoch % 1000000
    dt = datetime.datetime.utcfromtimestamp(seconds_since_epoch)
    delta = datetime.timedelta(microseconds = useconds)
    return dt + delta
    
def read_signed_char(f) :
    return struct.unpack('b', f.read(1))[0]
    
def read_unsigned_char(f) :
    return struct.unpack('B', f.read(1))[0]

def read_signed_short(f) :
    return struct.unpack('h', f.read(2))[0]
        
def read_unsigned_short(f) :
    return struct.unpack('H', f.read(2))[0]

def read_signed_int(f) :
    return struct.unpack('i', f.read(4))[0]
    
def read_unsigned_int(f) :
    return struct.unpack('I', f.read(4))[0]

def read_big_endian_unsigned_int(f):
    return struct.unpack('>I', f.read(4))[0]

def read_24bit_signed_number(f):
    s = '0' + f.read(3)
    num = struct.unpack('i', s)[0]
    return num >> 8
    
def read_signed_long(f) :
    return struct.unpack('q', f.read(8))[0]
    
def read_unsigned_long(f) :
    return struct.unpack('Q', f.read(8))[0]

def string_as_hexcode(string) :
    for s in string :
        if isinstance(s, int) :
            print(hex(s))
        else :
            print(hex(ord(s)))


class DebugCallback(RdbCallback) :
    def start_rdb(self):
        print('[')
    
    def start_database(self, db_number):
        print('{')
    
    def set(self, key, value, expiry):
        print('"%s" : "%s"' % (str(key), str(value)))
    
    def start_hash(self, key, length, expiry):
        print('"%s" : {' % str(key))
        pass
    
    def hset(self, key, field, value):
        print('"%s" : "%s"' % (str(field), str(value)))
    
    def end_hash(self, key):
        print('}')
    
    def start_set(self, key, cardinality, expiry):
        print('"%s" : [' % str(key))

    def sadd(self, key, member):
        print('"%s"' % str(member))
    
    def end_set(self, key):
        print(']')
    
    def start_list(self, key, length, expiry):
        print('"%s" : [' % str(key))
    
    def rpush(self, key, value) :
        print('"%s"' % str(value))
    
    def end_list(self, key):
        print(']')
    
    def start_sorted_set(self, key, length, expiry):
        print('"%s" : {' % str(key))
    
    def zadd(self, key, score, member):
        print('"%s" : "%s"' % (str(member), str(score)))
    
    def end_sorted_set(self, key):
        print('}')
    
    def end_database(self, db_number):
        print('}')
    
    def end_rdb(self):
        print(']')



########NEW FILE########
__FILENAME__ = create_lists
import string
import redis
import random

r = redis.StrictRedis()

def main():
    for x in range(5000):
        create_list_of_words()

def create_list_of_words():
    key = random_string(random.randint(10,25))
    num_items = random.randint(5, 1000)
    pipe = r.pipeline()
    for x in range(num_items):
        value = random_string(random.randint(5, 100))
        pipe.rpush(key, value)
    pipe.execute()
    
def random_string(length) :
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(length))

if __name__ == '__main__':
    main()
    

########NEW FILE########
__FILENAME__ = create_sorted_sets
import string
import redis
import random

r = redis.StrictRedis()

def main():
    for x in range(5000):
        create_sorted_set()

def create_sorted_set():
    key = random_string(random.randint(10,25))
    num_items = random.randint(5, 1000)
    pipe = r.pipeline()
    for x in range(num_items):
        value = random_string(random.randint(5, 100))
        score = random_double()
        pipe.zadd(key, score, value)
    pipe.execute()
    
def random_string(length) :
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(length))

def random_double():
    numerator = float(random.randint(0, 0xffff))
    denominator = float(random.randint(0, 0xffff))
    if denominator > 0 :
        return numerator / denominator
    else :
        return numerator
    
if __name__ == '__main__':
    main()
    

########NEW FILE########
__FILENAME__ = create_test_rdb
import redis
import random
import string
import shutil
import os

r = redis.StrictRedis()
r2 = redis.StrictRedis(db=2)

def create_test_rdbs(path_to_redis_dump, dump_folder) :
    clean_database()
    tests = (
#                empty_database,
#                multiple_databases,
#                keys_with_expiry, 
#                integer_keys, 
#                uncompressible_string_keys, 
#                easily_compressible_string_key, 
#                zipmap_that_doesnt_compress, 
#                zipmap_that_compresses_easily, 
#                zipmap_with_big_values,
#                dictionary, 
#                ziplist_that_compresses_easily, 
#                ziplist_that_doesnt_compress, 
                ziplist_with_integers, 
#                linkedlist, 
#                intset_16, 
#                intset_32, 
#                intset_64, 
#                regular_set, 
#                sorted_set_as_ziplist, 
#                regular_sorted_set
            )
    for t in tests :
        create_rdb_file(t, path_to_redis_dump, dump_folder)

def create_rdb_file(test, path_to_rdb, dump_folder):
    clean_database()
    test()
    save_database()
    file_name = "%s.rdb" % test.__name__
    shutil.copy(path_to_rdb, os.path.join(dump_folder, file_name))
    
def clean_database() :
    r.flushall()

def save_database() :
    r.save()
    
def empty_database() :
    pass

def keys_with_expiry() :
    r.set("expires_ms_precision", "2022-12-25 10:11:12.573 UTC")
    r.execute_command('PEXPIREAT', "expires_ms_precision", 1671963072573)

def multiple_databases() :
    r.set("key_in_zeroth_database", "zero")
    r2.set("key_in_second_database", "second")
    
def integer_keys() :
    r.set(-123, "Negative 8 bit integer")
    r.set(125, "Positive 8 bit integer")
    r.set(0xABAB, "Positive 16 bit integer")
    r.set(-0x7325, "Negative 16 bit integer")
    r.set(0x0AEDD325, "Positive 32 bit integer")
    r.set(-0x0AEDD325, "Negative 32 bit integer")

def uncompressible_string_keys() :
    r.set(random_string(60, "length within 6 bits"), "Key length within 6 bits")
    r.set(random_string(16382, "length within 14 bits"), "Key length more than 6 bits but less than 14 bits")
    r.set(random_string(16386, "length within 32 bits"), "Key length more than 14 bits but less than 32")

def easily_compressible_string_key() :
    r.set("".join('a' for x in range(0, 200)), "Key that redis should compress easily")

def zipmap_that_compresses_easily() :
    r.hset("zipmap_compresses_easily", "a", "aa")
    r.hset("zipmap_compresses_easily", "aa", "aaaa")
    r.hset("zipmap_compresses_easily", "aaaaa", "aaaaaaaaaaaaaa")
    
def zipmap_that_doesnt_compress() :
    r.hset("zimap_doesnt_compress", "MKD1G6", "2")
    r.hset("zimap_doesnt_compress", "YNNXK", "F7TI")

def zipmap_with_big_values():
    r.hset("zipmap_with_big_values", "253bytes", random_string(253, 'seed1'))
    r.hset("zipmap_with_big_values", "254bytes", random_string(254, 'seed2'))
    r.hset("zipmap_with_big_values", "255bytes", random_string(255, 'seed3'))
    r.hset("zipmap_with_big_values", "300bytes", random_string(300, 'seed4'))
    r.hset("zipmap_with_big_values", "20kbytes", random_string(20000, 'seed5'))
    
def dictionary() :
    num_entries = 1000
    for x in xrange(0, num_entries) :
        r.hset("force_dictionary", random_string(50, x), random_string(50, x + num_entries))

def ziplist_that_compresses_easily() :
    for length in (6, 12, 18, 24, 30, 36) :
        r.rpush("ziplist_compresses_easily", ("".join("a" for x in xrange(length))))
    
def ziplist_that_doesnt_compress() :
    r.rpush("ziplist_doesnt_compress", "aj2410")
    r.rpush("ziplist_doesnt_compress", "cc953a17a8e096e76a44169ad3f9ac87c5f8248a403274416179aa9fbd852344")

def ziplist_with_integers() :
    
    # Integers between 0 and 12, both inclusive, are encoded differently
    for x in range(0,13):
        r.rpush("ziplist_with_integers", x)
    
    
    # Dealing with 1 byte integers
    r.rpush("ziplist_with_integers", -2)
    r.rpush("ziplist_with_integers", 13)
    r.rpush("ziplist_with_integers", 25)
    r.rpush("ziplist_with_integers", -61)
    r.rpush("ziplist_with_integers", 63)
    
    # Dealing with 2 byte integers
    r.rpush("ziplist_with_integers", 16380)
    r.rpush("ziplist_with_integers", -16000)
    
    # Dealing with 4 byte signed integers
    r.rpush("ziplist_with_integers", 65535)
    r.rpush("ziplist_with_integers", -65523)
    
    # Dealing with 8 byte signed integers
    r.rpush("ziplist_with_integers", 4194304)
    r.rpush("ziplist_with_integers", 0x7fffffffffffffff)

def linkedlist() :
    num_entries = 1000
    for x in xrange(0, num_entries) :
        r.rpush("force_linkedlist", random_string(50, x))

def intset_16() :
    r.sadd("intset_16", 0x7ffe)
    r.sadd("intset_16", 0x7ffd)
    r.sadd("intset_16", 0x7ffc)

def intset_32() :
    r.sadd("intset_32", 0x7ffefffe)
    r.sadd("intset_32", 0x7ffefffd)
    r.sadd("intset_32", 0x7ffefffc)
    
def intset_64() :
    r.sadd("intset_64", 0x7ffefffefffefffe)
    r.sadd("intset_64", 0x7ffefffefffefffd)
    r.sadd("intset_64", 0x7ffefffefffefffc)

def regular_set() :
    r.sadd("regular_set", "alpha")
    r.sadd("regular_set", "beta")
    r.sadd("regular_set", "gamma")
    r.sadd("regular_set", "delta")
    r.sadd("regular_set", "phi")
    r.sadd("regular_set", "kappa")

def sorted_set_as_ziplist() :
    r.zadd("sorted_set_as_ziplist", 1, "8b6ba6718a786daefa69438148361901")
    r.zadd("sorted_set_as_ziplist", 2.37, "cb7a24bb7528f934b841b34c3a73e0c7")
    r.zadd("sorted_set_as_ziplist", 3.423, "523af537946b79c4f8369ed39ba78605")
    
def regular_sorted_set() :
    num_entries = 500
    for x in xrange(0, num_entries) :
        r.zadd("force_sorted_set", float(x) / 100, random_string(50, x))
    
def random_string(length, seed) :
    random.seed(seed)
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(length))

def backup_redis_dump(redis_dump, backup_folder):
    backup_file = os.path.join(backup_folder, 'dump.rdb.backup')
    shutil.copy(redis_dump, backup_file)
    
def main() :
    dump_folder = os.path.join(os.path.dirname(__file__), 'dumps')
    if not os.path.exists(dump_folder) :
        os.makedirs(dump_folder)
    
    redis_dump = '/var/redis/6379/dump.rdb'
    
    backup_redis_dump(redis_dump, dump_folder)
    create_test_rdbs(redis_dump, dump_folder)

if __name__ == '__main__' :
    main()


########NEW FILE########
__FILENAME__ = memory_observer
import redis
import time

def main():
    r = redis.StrictRedis()
    curr_memory = prev_memory = r.info()['used_memory']
    while True:
        if prev_memory != curr_memory:
            print('Delta Memory : %d, Total Memory : %d' % ((curr_memory - prev_memory), curr_memory))
        
        time.sleep(1)
        prev_memory = curr_memory
        curr_memory = r.info()['used_memory']
    
if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = memprofiler_tests
import unittest

from rdbtools import RdbParser
from rdbtools import MemoryCallback
import os

class Stats():
    def __init__(self):
        self.records = {}
        
    def next_record(self, record):
        self.records[record.key] = record

def get_stats(file_name):
    stats = Stats()
    callback = MemoryCallback(stats, 64)
    parser = RdbParser(callback)
    parser.parse(os.path.join(os.path.dirname(__file__), 'dumps', file_name))
    return stats.records
    
class MemoryCallbackTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_len_largest_element(self):
        stats = get_stats('ziplist_that_compresses_easily.rdb')
        self.assertEqual(stats['ziplist_compresses_easily'].len_largest_element, 36, "Length of largest element does not match")
        
    
########NEW FILE########
__FILENAME__ = parser_tests
import unittest
import os
import math
from rdbtools import RdbCallback, RdbParser

class RedisParserTestCase(unittest.TestCase):
    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_empty_rdb(self):
        r = load_rdb('empty_database.rdb')
        self.assert_('start_rdb' in r.methods_called)
        self.assert_('end_rdb' in r.methods_called)
        self.assertEquals(len(r.databases), 0, msg = "didn't expect any databases")

    def test_multiple_databases(self):
        r = load_rdb('multiple_databases.rdb')
        self.assert_(len(r.databases), 2)
        self.assert_(1 not in r.databases)
        self.assertEquals(r.databases[0]["key_in_zeroth_database"], "zero")
        self.assertEquals(r.databases[2]["key_in_second_database"], "second")
        
    def test_keys_with_expiry(self):
        r = load_rdb('keys_with_expiry.rdb')
        expiry = r.expiry[0]['expires_ms_precision']
        self.assertEquals(expiry.year, 2022)
        self.assertEquals(expiry.month, 12)
        self.assertEquals(expiry.day, 25)
        self.assertEquals(expiry.hour, 10)
        self.assertEquals(expiry.minute, 11)
        self.assertEquals(expiry.second, 12)
        self.assertEquals(expiry.microsecond, 573000)        
        
    def test_integer_keys(self):
        r = load_rdb('integer_keys.rdb')
        self.assertEquals(r.databases[0][125], "Positive 8 bit integer")
        self.assertEquals(r.databases[0][0xABAB], "Positive 16 bit integer")
        self.assertEquals(r.databases[0][0x0AEDD325], "Positive 32 bit integer")
        
    def test_negative_integer_keys(self):
        r = load_rdb('integer_keys.rdb')
        self.assertEquals(r.databases[0][-123], "Negative 8 bit integer")
        self.assertEquals(r.databases[0][-0x7325], "Negative 16 bit integer")
        self.assertEquals(r.databases[0][-0x0AEDD325], "Negative 32 bit integer")
    
    def test_string_key_with_compression(self):
        r = load_rdb('easily_compressible_string_key.rdb')
        key = "".join('a' for x in range(0, 200))
        value = "Key that redis should compress easily"
        self.assertEquals(r.databases[0][key], value)

    def test_zipmap_thats_compresses_easily(self):
        r = load_rdb('zipmap_that_compresses_easily.rdb')
        self.assertEquals(r.databases[0]["zipmap_compresses_easily"]["a"], "aa")
        self.assertEquals(r.databases[0]["zipmap_compresses_easily"]["aa"], "aaaa")
        self.assertEquals(r.databases[0]["zipmap_compresses_easily"]["aaaaa"], "aaaaaaaaaaaaaa")
        
    def test_zipmap_that_doesnt_compress(self):
        r = load_rdb('zipmap_that_doesnt_compress.rdb')
        self.assertEquals(r.databases[0]["zimap_doesnt_compress"]["MKD1G6"], 2)
        self.assertEquals(r.databases[0]["zimap_doesnt_compress"]["YNNXK"], "F7TI")
    
    def test_zipmap_with_big_values(self):
        ''' See issue https://github.com/sripathikrishnan/redis-rdb-tools/issues/2
            Values with length around 253/254/255 bytes are treated specially in the parser
            This test exercises those boundary conditions

            In order to test a bug with large ziplists, it is necessary to start
            Redis with "hash-max-ziplist-value 21000", create this rdb file,
            and run the test. That forces the 20kbyte value to be stored as a
            ziplist with a length encoding of 5 bytes.
        '''
        r = load_rdb('zipmap_with_big_values.rdb')
        self.assertEquals(len(r.databases[0]["zipmap_with_big_values"]["253bytes"]), 253)
        self.assertEquals(len(r.databases[0]["zipmap_with_big_values"]["254bytes"]), 254)
        self.assertEquals(len(r.databases[0]["zipmap_with_big_values"]["255bytes"]), 255)
        self.assertEquals(len(r.databases[0]["zipmap_with_big_values"]["300bytes"]), 300)
        self.assertEquals(len(r.databases[0]["zipmap_with_big_values"]["20kbytes"]), 20000)
        
    def test_hash_as_ziplist(self):
        '''In redis dump version = 4, hashmaps are stored as ziplists'''
        r = load_rdb('hash_as_ziplist.rdb')
        self.assertEquals(r.databases[0]["zipmap_compresses_easily"]["a"], "aa")
        self.assertEquals(r.databases[0]["zipmap_compresses_easily"]["aa"], "aaaa")
        self.assertEquals(r.databases[0]["zipmap_compresses_easily"]["aaaaa"], "aaaaaaaaaaaaaa")
        
    def test_dictionary(self):
        r = load_rdb('dictionary.rdb')
        self.assertEquals(r.lengths[0]["force_dictionary"], 1000)
        self.assertEquals(r.databases[0]["force_dictionary"]["ZMU5WEJDG7KU89AOG5LJT6K7HMNB3DEI43M6EYTJ83VRJ6XNXQ"], 
                    "T63SOS8DQJF0Q0VJEZ0D1IQFCYTIPSBOUIAI9SB0OV57MQR1FI")
        self.assertEquals(r.databases[0]["force_dictionary"]["UHS5ESW4HLK8XOGTM39IK1SJEUGVV9WOPK6JYA5QBZSJU84491"], 
                    "6VULTCV52FXJ8MGVSFTZVAGK2JXZMGQ5F8OVJI0X6GEDDR27RZ")
    
    def test_ziplist_that_compresses_easily(self):
        r = load_rdb('ziplist_that_compresses_easily.rdb')
        self.assertEquals(r.lengths[0]["ziplist_compresses_easily"], 6)
        for idx, length in enumerate([6, 12, 18, 24, 30, 36]) :
            self.assertEquals(("".join("a" for x in xrange(length))), r.databases[0]["ziplist_compresses_easily"][idx])
    
    def test_ziplist_that_doesnt_compress(self):
        r = load_rdb('ziplist_that_doesnt_compress.rdb')
        self.assertEquals(r.lengths[0]["ziplist_doesnt_compress"], 2)
        self.assert_("aj2410" in r.databases[0]["ziplist_doesnt_compress"])
        self.assert_("cc953a17a8e096e76a44169ad3f9ac87c5f8248a403274416179aa9fbd852344" 
                        in r.databases[0]["ziplist_doesnt_compress"])
    
    def test_ziplist_with_integers(self):
        r = load_rdb('ziplist_with_integers.rdb')
        
        expected_numbers = []
        for x in range(0,13):
            expected_numbers.append(x)
        
        expected_numbers += [-2, 13, 25, -61, 63, 16380, -16000, 65535, -65523, 4194304, 0x7fffffffffffffff]
        
        self.assertEquals(r.lengths[0]["ziplist_with_integers"], len(expected_numbers))
        
        for num in expected_numbers :
            self.assert_(num in r.databases[0]["ziplist_with_integers"], "Cannot find %d" % num)

    def test_linkedlist(self):
        r = load_rdb('linkedlist.rdb')
        self.assertEquals(r.lengths[0]["force_linkedlist"], 1000)
        self.assert_("JYY4GIFI0ETHKP4VAJF5333082J4R1UPNPLE329YT0EYPGHSJQ" in r.databases[0]["force_linkedlist"])
        self.assert_("TKBXHJOX9Q99ICF4V78XTCA2Y1UYW6ERL35JCIL1O0KSGXS58S" in r.databases[0]["force_linkedlist"])

    def test_intset_16(self):
        r = load_rdb('intset_16.rdb')
        self.assertEquals(r.lengths[0]["intset_16"], 3)
        for num in (0x7ffe, 0x7ffd, 0x7ffc) :
            self.assert_(num in r.databases[0]["intset_16"])

    def test_intset_32(self):
        r = load_rdb('intset_32.rdb')
        self.assertEquals(r.lengths[0]["intset_32"], 3)
        for num in (0x7ffefffe, 0x7ffefffd, 0x7ffefffc) :
            self.assert_(num in r.databases[0]["intset_32"])

    def test_intset_64(self):
        r = load_rdb('intset_64.rdb')
        self.assertEquals(r.lengths[0]["intset_64"], 3)
        for num in (0x7ffefffefffefffe, 0x7ffefffefffefffd, 0x7ffefffefffefffc) :
            self.assert_(num in r.databases[0]["intset_64"])

    def test_regular_set(self):
        r = load_rdb('regular_set.rdb')
        self.assertEquals(r.lengths[0]["regular_set"], 6)
        for member in ("alpha", "beta", "gamma", "delta", "phi", "kappa") :
            self.assert_(member in r.databases[0]["regular_set"], msg=('%s missing' % member))

    def test_sorted_set_as_ziplist(self):
        r = load_rdb('sorted_set_as_ziplist.rdb')
        self.assertEquals(r.lengths[0]["sorted_set_as_ziplist"], 3)
        zset = r.databases[0]["sorted_set_as_ziplist"]
        self.assert_(floateq(zset['8b6ba6718a786daefa69438148361901'], 1))
        self.assert_(floateq(zset['cb7a24bb7528f934b841b34c3a73e0c7'], 2.37))
        self.assert_(floateq(zset['523af537946b79c4f8369ed39ba78605'], 3.423))

    def test_filtering_by_keys(self):
        r = load_rdb('parser_filters.rdb', filters={"keys":"k[0-9]"})
        self.assertEquals(r.databases[0]['k1'], "ssssssss")
        self.assertEquals(r.databases[0]['k3'], "wwwwwwww")
        self.assertEquals(len(r.databases[0]), 2)

    def test_filtering_by_type(self):
        r = load_rdb('parser_filters.rdb', filters={"types":["sortedset"]})
        self.assert_('z1' in r.databases[0])
        self.assert_('z2' in r.databases[0])
        self.assert_('z3' in r.databases[0])
        self.assert_('z4' in r.databases[0])
        self.assertEquals(len(r.databases[0]), 4)

    def test_filtering_by_database(self):
        r = load_rdb('multiple_databases.rdb', filters={"dbs":[2]})
        self.assert_('key_in_zeroth_database' not in r.databases[0])
        self.assert_('key_in_second_database' in r.databases[2])
        self.assertEquals(len(r.databases[0]), 0)
        self.assertEquals(len(r.databases[2]), 1)

    def test_rdb_version_5_with_checksum(self):
        r = load_rdb('rdb_version_5_with_checksum.rdb')
        self.assertEquals(r.databases[0]['abcd'], 'efgh')
        self.assertEquals(r.databases[0]['foo'], 'bar')
        self.assertEquals(r.databases[0]['bar'], 'baz')
        self.assertEquals(r.databases[0]['abcdef'], 'abcdef')
        self.assertEquals(r.databases[0]['longerstring'], 'thisisalongerstring.idontknowwhatitmeans')

def floateq(f1, f2) :
    return math.fabs(f1 - f2) < 0.00001

def load_rdb(file_name, filters=None) :
    r = MockRedis()
    parser = RdbParser(r, filters)
    parser.parse(os.path.join(os.path.dirname(__file__), 'dumps', file_name))
    return r
    
class MockRedis(RdbCallback):
    def __init__(self) :
        self.databases = {}
        self.lengths = {}
        self.expiry = {}
        self.methods_called = []
        self.dbnum = 0

    def currentdb(self) :
        return self.databases[self.dbnum]
    
    def store_expiry(self, key, expiry) :
        self.expiry[self.dbnum][key] = expiry
    
    def store_length(self, key, length) :
        if not self.dbnum in self.lengths :
            self.lengths[self.dbnum] = {}
        self.lengths[self.dbnum][key] = length

    def get_length(self, key) :
        if not key in self.lengths[self.dbnum] :
            raise Exception('Key %s does not have a length' % key)
        return self.lengths[self.dbnum][key]
        
    def start_rdb(self):
        self.methods_called.append('start_rdb')
    
    def start_database(self, dbnum):
        self.dbnum = dbnum
        self.databases[dbnum] = {}
        self.expiry[dbnum] = {}
        self.lengths[dbnum] = {}
    
    def set(self, key, value, expiry, info):
        self.currentdb()[key] = value
        if expiry :
            self.store_expiry(key, expiry)
    
    def start_hash(self, key, length, expiry, info):
        if key in self.currentdb() :
            raise Exception('start_hash called with key %s that already exists' % key)
        else :
            self.currentdb()[key] = {}
        if expiry :
            self.store_expiry(key, expiry)
        self.store_length(key, length)
    
    def hset(self, key, field, value):
        if not key in self.currentdb() :
            raise Exception('start_hash not called for key = %s', key)
        self.currentdb()[key][field] = value
    
    def end_hash(self, key):
        if not key in self.currentdb() :
            raise Exception('start_hash not called for key = %s', key)
        if len(self.currentdb()[key]) != self.lengths[self.dbnum][key] :
            raise Exception('Lengths mismatch on hash %s, expected length = %d, actual = %d'
                                 % (key, self.lengths[self.dbnum][key], len(self.currentdb()[key])))
    
    def start_set(self, key, cardinality, expiry, info):
        if key in self.currentdb() :
            raise Exception('start_set called with key %s that already exists' % key)
        else :
            self.currentdb()[key] = []
        if expiry :
            self.store_expiry(key, expiry)
        self.store_length(key, cardinality)

    def sadd(self, key, member):
        if not key in self.currentdb() :
            raise Exception('start_set not called for key = %s', key)
        self.currentdb()[key].append(member)
    
    def end_set(self, key):
        if not key in self.currentdb() :
            raise Exception('start_set not called for key = %s', key)
        if len(self.currentdb()[key]) != self.lengths[self.dbnum][key] :
            raise Exception('Lengths mismatch on set %s, expected length = %d, actual = %d'
                                 % (key, self.lengths[self.dbnum][key], len(self.currentdb()[key])))

    def start_list(self, key, length, expiry, info):
        if key in self.currentdb() :
            raise Exception('start_list called with key %s that already exists' % key)
        else :
            self.currentdb()[key] = []
        if expiry :
            self.store_expiry(key, expiry)
        self.store_length(key, length)
    
    def rpush(self, key, value) :
        if not key in self.currentdb() :
            raise Exception('start_list not called for key = %s', key)
        self.currentdb()[key].append(value)
    
    def end_list(self, key):
        if not key in self.currentdb() :
            raise Exception('start_set not called for key = %s', key)
        if len(self.currentdb()[key]) != self.lengths[self.dbnum][key] :
            raise Exception('Lengths mismatch on list %s, expected length = %d, actual = %d'
                                 % (key, self.lengths[self.dbnum][key], len(self.currentdb()[key])))

    def start_sorted_set(self, key, length, expiry, info):
        if key in self.currentdb() :
            raise Exception('start_sorted_set called with key %s that already exists' % key)
        else :
            self.currentdb()[key] = {}
        if expiry :
            self.store_expiry(key, expiry)
        self.store_length(key, length)
    
    def zadd(self, key, score, member):
        if not key in self.currentdb() :
            raise Exception('start_sorted_set not called for key = %s', key)
        self.currentdb()[key][member] = score
    
    def end_sorted_set(self, key):
        if not key in self.currentdb() :
            raise Exception('start_set not called for key = %s', key)
        if len(self.currentdb()[key]) != self.lengths[self.dbnum][key] :
            raise Exception('Lengths mismatch on sortedset %s, expected length = %d, actual = %d'
                                 % (key, self.lengths[self.dbnum][key], len(self.currentdb()[key])))

    def end_database(self, dbnum):
        if self.dbnum != dbnum :
            raise Exception('start_database called with %d, but end_database called %d instead' % (self.dbnum, dbnum))
    
    def end_rdb(self):
        self.methods_called.append('end_rdb')



########NEW FILE########
