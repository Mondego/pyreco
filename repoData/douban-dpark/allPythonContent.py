__FILENAME__ = accumulator
from operator import add
import copy

from dpark.serialize import load_func, dump_func

class AccumulatorParam:
    def __init__(self, zero, addInPlace):
        self.zero = zero
        self.addInPlace = addInPlace

    def __getstate__(self):
        return dump_func(self.addInPlace), self.zero

    def __setstate__(self, state):
        add, self.zero = state
        self.addInPlace = load_func(add)

numAcc = AccumulatorParam(0, add)
listAcc = AccumulatorParam([], lambda x,y:x.extend(y) or x)
mapAcc = AccumulatorParam({}, lambda x,y:x.update(y) or x)
setAcc = AccumulatorParam(set(), lambda x,y:x.update(y) or x)


class Accumulator:
    def __init__(self, initialValue=0, param=numAcc):
        self.id = self.newId()
        if param is None:
            param = numAcc
        self.param = param
        self.value = initialValue
        self.register(self, True)

    def add(self, v):
        self.value = self.param.addInPlace(self.value, v)
        self.register(self, False)

    def reset(self):
        v = self.value
        self.value = copy.copy(self.param.zero)
        return v

    def __getstate__(self):
        return self.id, self.param

    def __setstate__(self, s):
        self.id, self.param = s
        self.value = copy.copy(self.param.zero)
        self.register(self, False)

    nextId = 0
    @classmethod
    def newId(cls):
        cls.nextId += 1
        return cls.nextId

    originals = {}
    localAccums = {}
    @classmethod
    def register(cls, acc, original):
        if original:
            cls.originals[acc.id] = acc
        else:
            cls.localAccums[acc.id] = acc

    @classmethod
    def clear(cls):
        for acc in cls.localAccums.values():
            acc.reset()
        cls.localAccums.clear()

    @classmethod
    def values(cls):
        v = dict((id, accum.value) for id,accum in cls.localAccums.items())
        cls.clear()
        return v

    @classmethod
    def merge(cls, values):
        for id, value in values.items():
            cls.originals[id].add(value)

ReadBytes = Accumulator()
WriteBytes = Accumulator()

RemoteReadBytes = Accumulator()
LocalReadBytes = Accumulator()

CacheHits = Accumulator()
CacheMisses = Accumulator()

########NEW FILE########
__FILENAME__ = bagel
import sys
import os, os.path
import time
import logging
import shutil
import operator

logger = logging.getLogger("bagel")

class Vertex:
    def __init__(self, id, value, outEdges, active):
        self.id = id
        self.value = value
        self.outEdges = outEdges
        self.active = active
    def __repr__(self):
        return "<Vertex(%s, %s, %s)>" % (self.id, self.value, self.active)

class Edge:
    def __init__(self, target_id, value=0):
        self.target_id = target_id
        self.value = value
    def __repr__(self):
        return '<Edge(%s, %s)>' % (self.target_id, self.value)

class Message:
    def __init__(self, target_id, value):
        self.target_id = target_id
        self.value = value
    def __repr__(self):
        return "<Message(%s, %s)>" % (self.target_id, self.value)


class Combiner(object):
    def createCombiner(self, msg): raise NotImplementedError
    def mergeValue(self, combiner, msg): raise NotImplementedError
    def mergeCombiners(self, a, b): raise NotImplementedError

class Aggregator(object):
    def createAggregator(self, vert): raise NotImplementedError
    def mergeAggregator(self, a, b): raise NotImplementedError

class BasicCombiner(Combiner):
    def __init__(self, op):
        self.op = op
    def createCombiner(self, msg):
        return msg
    def mergeValue(self, combiner, msg):
        return self.op(combiner, msg)
    def mergeCombiners(self, a, b):
        return self.op(a, b)

DefaultValueCombiner = BasicCombiner(operator.add)

class DefaultListCombiner(Combiner):
    def createCombiner(self, msg):
        return [msg]
    def mergeValue(self, combiner, msg):
        return combiner+[msg]
    def mergeCombiners(self, a, b):
        return a + b

class Bagel(object):
    @classmethod
    def run(cls, ctx, verts, msgs, compute,
            combiner=DefaultValueCombiner, aggregator=None,
            max_superstep=sys.maxint, numSplits=None, snapshot_dir=None):

        superstep = 0
        snapshot_dir = snapshot_dir or ctx.options.snapshot_dir

        while superstep < max_superstep:
            logger.info("Starting superstep %d", superstep)
            start = time.time()
            aggregated = cls.agg(verts, aggregator) if aggregator else None
            combinedMsgs = msgs.combineByKey(combiner, numSplits)
            grouped = verts.groupWith(combinedMsgs, numSplits=numSplits)
            verts, msgs, numMsgs, numActiveVerts = cls.comp(ctx, grouped,
                lambda v, ms: compute(v, ms, aggregated, superstep), snapshot_dir)
            logger.info("superstep %d took %.1f s %d messages, %d active nodes",
                    superstep, time.time()-start, numMsgs, numActiveVerts)

            superstep += 1
            if numMsgs == 0 and numActiveVerts == 0:
                break
        return verts

    @classmethod
    def agg(cls, verts, aggregator):
        r = verts.map(lambda (id, vert): aggregator.createAggregator(vert))
        return r.reduce(aggregator.mergeAggregators)

    @classmethod
    def comp(cls, ctx, grouped, compute, snapshot_dir=None):
        numMsgs = ctx.accumulator(0)
        numActiveVerts = ctx.accumulator(0)
        def proc((vs, cs)):
            if not vs:
                return []
            newVert, newMsgs = compute(vs[0], cs)
            numMsgs.add(len(newMsgs))
            if newVert.active:
                numActiveVerts.add(1)
            return [(newVert, newMsgs)]
        processed = grouped.flatMapValue(proc)
        verts = processed.mapValue(lambda (vert, msgs): vert)
        msgs = processed.flatMap(lambda (id, (vert, msgs)): msgs)
        if snapshot_dir:
            verts = verts.snapshot(snapshot_dir)
        #else:
        #    processed = processed.cache()
        # force evaluation of processed RDD for accurate performance measurements
        n = verts.count()
        return verts, msgs, numMsgs.value, numActiveVerts.value

    @classmethod
    def addAggregatorArg(cls, compute):
        def _(vert, messages, aggregator, superstep):
            return compute(vert, messages)
        return _

########NEW FILE########
__FILENAME__ = bitindex
import itertools
import marshal
import math
from dpark.portable_hash import portable_hash

BYTE_SHIFT = 3
BYTE_SIZE = 1 << BYTE_SHIFT
BYTE_MASK = BYTE_SIZE - 1

_table = [(), (0,), (1,), (0,1), (2,), (0,2), (1,2), (0,1,2), (3,),
          (0,3), (1,3), (0,1,3), (2,3), (0,2,3), (1,2,3), (0,1,2,3)]

class BitIndex(object):
    def __init__(self):
        self.array = bytearray()
        self.size = 0

    def __nonzero__(self):
        return any(self.array)

    def __repr__(self):
        def to_bin(x, s):
            return bin(x)[2:].zfill(s)[::-1]

        index, offset = self._get_offset(self.size)
        rep = [to_bin(x, BYTE_SIZE) for x in self.array[:index]]
        if offset:
            rep.append(to_bin(self.array[index] & (1 << offset) - 1, offset))
        return ''.join(rep)

    def __len__(self):
        return self.size

    @staticmethod
    def _get_offset(pos):
        return pos >> BYTE_SHIFT, pos & BYTE_MASK

    @staticmethod
    def _bitwise(iterable, op):
        for i, it in enumerate(iterable):
            if op:
                byte = reduce(op, it)
            else:
                byte = it

            if not byte:
                continue

            for x in _table[byte & 0xF]:
                yield i * BYTE_SIZE + x

            for x in _table[byte >> 4]:
                yield i * BYTE_SIZE + 4 + x

    def set(self, pos, value = True):
        if pos < 0:
            raise ValueError('pos must great or equal zero!')

        index, offset = self._get_offset(pos)
        length = len(self.array)
        if index >= length:
            self.array.extend([0] * (index - length + 1))

        if value:
            self.array[index] |= (1 << offset)
        else:
            self.array[index] &= ~(1 << offset)

        self.size = max(self.size, pos + 1)

    def sets(self, positions, value = True):
        for pos in positions:
            self.set(pos, value)

    def append(self, value = True):
        self.set(self.size, value)

    def appends(self, values):
        for value in values:
            self.append(value)

    def get(self, pos):
        if pos < 0:
            raise ValueError('pos must great or equal zero!')

        if pos >= self.size:
            return False

        index, offset = self._get_offset(pos)
        return (self.array[index] & (1 << offset)) != 0

    def gets(self, positions):
        for pos in positions:
            yield self.get(pos)

    def intersect(self, *other):
        return self._bitwise(
            itertools.izip(self.array, *[o.array for o in other]), lambda x, y: x & y)

    def union(self, *other):
        return self._bitwise(
            itertools.izip_longest(self.array, *[o.array for o in other], fillvalue=0),
            lambda x, y: x | y)

    def xor(self, other):
        return self._bitwise(itertools.izip_longest(self.array, other.array, fillvalue=0),
                        lambda x, y: x ^ y)

    def excepts(self, *other):
        return self._bitwise(
            itertools.izip_longest(self.array, *[o.array for o in other], fillvalue=0),
            lambda x, y: x & ~y)

    def positions(self):
        return self._bitwise(self.array, None)

class Bloomfilter(object):
    def __init__(self, m, k):
        self.m = m
        self.k = k
        self.bitindex = BitIndex()

    """ Bloomfilter calculator (http://hur.st/bloomfilter)
    n: Number of items in the filter
    p: Probability of false positives, float between 0 and 1 or a number
    indicating 1-in-p
    m: Number of bits in the filter
    k: Number of hash functions
    m = ceil((n * log(p)) / log(1.0 / (pow(2.0, log(2.0)))))
    k = round(log(2.0) * m / n)
    """
    @staticmethod
    def calculate_parameters(n, p):
        m = int(math.ceil(n * math.log(p) * -2.0813689810056073))
        k = int(round(0.6931471805599453 * m / n))
        return m, k


    '''
    we're using only two hash functions with different settings, as described
    by Kirsch & Mitzenmacher: http://www.eecs.harvard.edu/~kirsch/pubs/bbbf/esa06.pdf
    '''
    def _get_offsets(self, obj):
        hash_1 = portable_hash(obj)
        hash_2 = portable_hash(marshal.dumps(obj))

        for i in xrange(self.k):
            yield ((hash_1 + i * hash_2) & 0xFFFFFFFF) % self.m

    def add(self, objs):
        for obj in objs:
            self.bitindex.sets(self._get_offsets(obj))

    def _match(self, objs):
        for obj in objs:
            yield all(self.bitindex.gets(self._get_offsets(obj)))

    def match(self, objs):
        return list(self._match(objs))

    def __contains__(self, obj):
        return self._match([obj]).next()


########NEW FILE########
__FILENAME__ = broadcast
import os
import zmq
import time
import uuid
import zlib
import random
import socket
import struct
import cPickle
import logging
import marshal

from dpark.util import compress, decompress, spawn
from dpark.cache import Cache
from dpark.serialize import marshalable
from dpark.env import env

logger = logging.getLogger("broadcast")

MARSHAL_TYPE, PICKLE_TYPE = range(2)
BLOCK_SHIFT = 20
BLOCK_SIZE = 1 << BLOCK_SHIFT

class BroadcastManager:
    header_fmt = '>BI'
    header_len = struct.calcsize(header_fmt)

    def start(self, is_master):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

    def register(self, uuid, value):
        raise NotImplementedError

    def clear(self, uuid):
        raise NotImplementedError

    def fetch(self, uuid, block_num):
        raise NotImplementedError

    def to_blocks(self, uuid, obj):
        try:
            if marshalable(obj):
                buf = marshal.dumps((uuid, obj))
                type = MARSHAL_TYPE
            else:
                buf = cPickle.dumps((uuid, obj), -1)
                type = PICKLE_TYPE

        except Exception:
            buf = cPickle.dumps((uuid, obj), -1)
            type = PICKLE_TYPE

        checksum = zlib.crc32(buf) & 0xFFFF
        stream = struct.pack(self.header_fmt, type, checksum) + buf
        blockNum = (len(stream) + (BLOCK_SIZE - 1)) >> BLOCK_SHIFT
        blocks = [compress(stream[i*BLOCK_SIZE:(i+1)*BLOCK_SIZE]) for i in range(blockNum)]
        return blocks

    def from_blocks(self, uuid, blocks):
        stream = ''.join(map(decompress,  blocks))
        type, checksum = struct.unpack(self.header_fmt, stream[:self.header_len])
        buf = stream[self.header_len:]
        _checksum = zlib.crc32(buf) & 0xFFFF
        if _checksum != checksum:
            raise RuntimeError('Wrong blocks: checksum: %s, expected: %s' % (
                _checksum, checksum))

        if type == MARSHAL_TYPE:
            _uuid, value = marshal.loads(buf)
        elif type == PICKLE_TYPE:
            _uuid, value = cPickle.loads(buf)
        else:
            raise RuntimeError('Unknown serialization type: %s' % type)

        if uuid != _uuid:
            raise RuntimeError('Wrong blocks: uuid: %s, expected: %s' % (_uuid, uuid))

        return value

GUIDE_STOP, GUIDE_INFO, GUIDE_SOURCES, GUIDE_REPORT_BAD = range(4)
SERVER_STOP, SERVER_FETCH, SERVER_FETCH_FAIL, SERVER_FETCH_OK = range(4)

class P2PBroadcastManager(BroadcastManager):
    def __init__(self):
        self.published = {}
        self.cache = Cache()
        self.host = socket.gethostname()
        self.server_thread = None
        random.seed(os.getpid() + int(time.time()*1000)%1000)

    def start(self, is_master):
        if is_master:
            self.guides = {}
            self.guide_addr, self.guide_thread = self.start_guide()
            env.register('BroadcastGuideAddr', self.guide_addr)
        else:
            self.guide_addr = env.get('BroadcastGuideAddr')

        logger.debug("broadcast started: %s", self.guide_addr)

    def shutdown(self):
        sock = env.ctx.socket(zmq.REQ)
        sock.setsockopt(zmq.LINGER, 0)
        sock.connect(self.guide_addr)
        sock.send_pyobj((GUIDE_STOP, None))
        sock.recv_pyobj()
        sock.close()

    def register(self, uuid, value):
        if uuid in self.published:
            raise RuntimeError('broadcast %s has already registered' % uuid)

        if not self.server_thread:
            self.server_addr, self.server_thread = self.start_server()

        blocks = self.to_blocks(uuid, value)
        self.published[uuid] = blocks
        self.guides[uuid] = {self.server_addr: [1] * len(blocks)}
        self.cache.put(uuid, value)
        return len(blocks)

    def fetch(self, uuid, block_num):
        if not self.server_thread:
            self.server_addr, self.server_thread = self.start_server()

        value = self.cache.get(uuid)
        if value is not None:
            return value

        blocks = self.fetch_blocks(uuid, block_num)
        value = self.from_blocks(uuid, blocks)
        return value

    def clear(self, uuid):
        self.cache.put(uuid, None)
        del self.published[uuid]

    def fetch_blocks(self, uuid, block_num):
        guide_sock = env.ctx.socket(zmq.REQ)
        guide_sock.connect(self.guide_addr)
        logger.debug("connect to guide %s", self.guide_addr)

        blocks = [None] * block_num
        bitmap = [0] * block_num
        self.published[uuid] = blocks
        def _report_bad(addr):
            guide_sock.send_pyobj((GUIDE_REPORT_BAD, (uuid, addr)))
            guide_sock.recv_pyobj()

        def _fetch(addr, indices):
            sock = env.ctx.socket(zmq.REQ)
            try:
                sock.setsockopt(zmq.LINGER, 0)
                sock.connect(addr)
                for i in indices:
                    sock.send_pyobj((SERVER_FETCH, (uuid, i)))
                    avail = sock.poll(5 * 1000, zmq.POLLIN)
                    if not avail:
                        logger.debug("%s recv broadcast %d from %s timeout",
                                       self.server_addr, i, addr)
                        _report_bad(addr)
                        return
                    result, msg = sock.recv_pyobj()

                    if result == SERVER_FETCH_FAIL:
                        _report_bad(addr)
                        return
                    if result == SERVER_FETCH_OK:
                        id, block = msg
                        if i == id and block is not None:
                            blocks[id] = block
                            bitmap[id] = 1
                    else:
                        raise RuntimeError('Unknown server response: %s %s' % (result, msg))

            finally:
                sock.close()

        while not all(bitmap):
            guide_sock.send_pyobj((GUIDE_SOURCES, (uuid, self.server_addr, bitmap)))
            sources = guide_sock.recv_pyobj()
            logger.debug("received SourceInfo from master: %s", sources.keys())
            local = []
            remote = []
            for addr, _bitmap in sources.iteritems():
                if addr.startswith('tcp://%s:' % self.host):
                    local.append((addr, _bitmap))
                else:
                    remote.append((addr, _bitmap))

            for addr, _bitmap in local:
                indices = [i for i in xrange(block_num) if not bitmap[i] and _bitmap[i]]
                if indices:
                    _fetch(addr, indices)

            random.shuffle(remote)
            for addr, _bitmap in remote:
                indices = [i for i in xrange(block_num) if not bitmap[i] and _bitmap[i]]
                if indices:
                    _fetch(addr, [random.choice(indices)])

        guide_sock.close()
        return blocks

    def start_guide(self):
        sock = env.ctx.socket(zmq.REP)
        port = sock.bind_to_random_port("tcp://0.0.0.0")
        guide_addr = "tcp://%s:%d" % (self.host, port)

        def run():
            logger.debug("guide start at %s", guide_addr)

            while True:
                type, msg = sock.recv_pyobj()
                if type == GUIDE_STOP:
                    sock.send_pyobj(0)
                    break
                elif type == GUIDE_SOURCES:
                    uuid, addr, bitmap = msg
                    sources = self.guides[uuid]
                    sock.send_pyobj(sources)
                    if any(bitmap):
                        sources[addr] = bitmap
                elif type == GUIDE_REPORT_BAD:
                    uuid, addr = msg
                    sock.send_pyobj(0)
                    sources = self.guides[uuid]
                    if addr in sources:
                        del sources[addr]
                else:
                    logger.error('Unknown guide message: %s %s', type, msg)

            sock.close()
            logger.debug("Sending stop notification to all servers ...")
            for uuid, sources in self.guides.iteritems():
                for addr in sources:
                    self.stop_server(addr)

        return guide_addr, spawn(run)

    def start_server(self):
        sock = env.ctx.socket(zmq.REP)
        sock.setsockopt(zmq.LINGER, 0)
        port = sock.bind_to_random_port("tcp://0.0.0.0")
        server_addr = 'tcp://%s:%d' % (self.host,port)

        def run():
            logger.debug("server started at %s", server_addr)

            while True:
                type, msg = sock.recv_pyobj()
                logger.debug('server recv: %s %s', type, msg)
                if type == SERVER_STOP:
                    sock.send_pyobj(None)
                    break
                elif type == SERVER_FETCH:
                    uuid, id = msg
                    if uuid not in self.published:
                        sock.send_pyobj((SERVER_FETCH_FAIL, None))
                    else:
                        blocks = self.published[uuid]
                        if id >= len(blocks):
                            sock.send_pyobj((SERVER_FETCH_FAIL, None))
                        else:
                            sock.send_pyobj((SERVER_FETCH_OK, (id, blocks[id])))
                else:
                    logger.error('Unknown server message: %s %s', type, msg)

            sock.close()
            logger.debug("stop Broadcast server %s", server_addr)
            for uuid in self.published.keys():
                self.clear(uuid)

        return server_addr, spawn(run)

    def stop_server(self, addr):
        req = env.ctx.socket(zmq.REQ)
        req.setsockopt(zmq.LINGER, 0)
        req.connect(addr)
        req.send_pyobj((SERVER_STOP, None))
        avail = req.poll(1 * 100, zmq.POLLIN)
        if avail:
            req.recv_pyobj()
        req.close()


_manager = P2PBroadcastManager()

def start_manager(is_master):
    _manager.start(is_master)

def stop_manager():
    _manager.shutdown()

class Broadcast:
    def __init__(self, value):
        assert value is not None, 'broadcast object should not been None'
        self.uuid = str(uuid.uuid4())
        self.value = value
        self.block_num = _manager.register(self.uuid, self.value)
        self.bytes = self.block_num * BLOCK_SIZE
        logger.info("broadcast %s in %d blocks", self.uuid, self.block_num)

    def clear(self):
        _manager.clear(self.uuid)

    def __getstate__(self):
        return (self.uuid, self.block_num)

    def __setstate__(self, v):
        self.uuid, self.block_num = v

    def __getattr__(self, name):
        if name != 'value':
            return getattr(self.value, name)

        value = _manager.fetch(self.uuid, self.block_num)
        if value is None:
            raise RuntimeError("fetch broadcast failed")
        self.value = value
        return value


########NEW FILE########
__FILENAME__ = cache
import os
import multiprocessing
import logging
import marshal
import cPickle
import shutil
import struct
import urllib

import msgpack

from dpark.env import env
from dpark.tracker import GetValueMessage, AddItemMessage, RemoveItemMessage

logger = logging.getLogger("cache")

class Cache:
    data = {}

    def get(self, key):
        return self.data.get(key)

    def put(self, key, value, is_iterator=False):
        if value is not None:
            if is_iterator:
                value = list(value)
            self.data[key] = value
            return value
        else:
            self.data.pop(key, None)

    def clear(self):
        self.data.clear()

class DiskCache(Cache):
    def __init__(self, tracker, path):
        if not os.path.exists(path):
            try: os.makedirs(path)
            except: pass
        self.tracker = tracker
        self.root = path

    def get_path(self, key):
        return os.path.join(self.root, '%s_%s' % key)

    def get(self, key):
        p = self.get_path(key)
        if os.path.exists(p):
            return self.load(open(p, 'rb'))

        # load from other node
        if not env.get('SERVER_URI'):
            return
        rdd_id, index = key
        locs = self.tracker.getCacheUri(rdd_id, index)
        if not locs:
            return

        serve_uri = locs[-1]
        uri = '%s/cache/%s' % (serve_uri, os.path.basename(p))
        f = urllib.urlopen(uri)
        if f.code == 404:
            logger.warning('load from cache %s failed', uri)
            self.tracker.removeHost(rdd_id, index, serve_uri)
            f.close()
            return
        return self.load(f)

    def put(self, key, value, is_iterator=False):
        p = self.get_path(key)
        if value is not None:
            return self.save(self.get_path(key), value)
        else:
            os.remove(p)

    def clear(self):
        try:
            shutil.rmtree(self.root)
        except OSError, e:
            pass

    def load(self, f):
        count, = struct.unpack("I", f.read(4))
        if not count: return
        unpacker = msgpack.Unpacker(f, use_list=False)
        for i in xrange(count):
            _type, data = unpacker.next()
            if _type == 0:
                yield marshal.loads(data)
            else:
                yield cPickle.loads(data)
        f.close()

    def save(self, path, items):
        # TODO: purge old cache
        tp = "%s.%d" % (path, os.getpid())
        with open(tp, 'wb') as f:
            c = 0
            f.write(struct.pack("I", c))
            try_marshal = True
            for v in items:
                if try_marshal:
                    try:
                        r = 0, marshal.dumps(v)
                    except Exception:
                        r = 1, cPickle.dumps(v, -1)
                        try_marshal = False
                else:
                    r = 1, cPickle.dumps(v, -1)
                f.write(msgpack.packb(r))
                c += 1
                yield v

            bytes = f.tell()
            if bytes > 10<<20:
                logger.warning("cached result is %dMB (larger than 10MB)", bytes>>20)
            # count
            f.seek(0)
            f.write(struct.pack("I", c))

        os.rename(tp, path)

class BaseCacheTracker(object):
    cache = None

    def registerRDD(self, rddId, numPartitions):
        pass

    def getLocationsSnapshot(self):
        pass

    def getCachedLocs(self, rdd_id, index):
        pass

    def getCacheUri(self, rdd_id, index):
        pass

    def addHost(self, rdd_id, index, host):
        pass

    def removeHost(self, rdd_id, index, host):
        pass

    def clear(self):
        self.cache.clear()

    def getOrCompute(self, rdd, split):
        key = (rdd.id, split.index)
        cachedVal = self.cache.get(key)
        if cachedVal is not None:
            logger.debug("Found partition in cache! %s", key)
            for i in cachedVal:
                yield i

        else:
            logger.debug("partition not in cache, %s", key)
            for i in self.cache.put(key, rdd.compute(split), is_iterator=True):
                yield i

            serve_uri = env.get('SERVER_URI')
            if serve_uri:
                self.addHost(rdd.id, split.index, serve_uri)

    def stop(self):
        self.clear()

class LocalCacheTracker(BaseCacheTracker):
    def __init__(self):
        self.locs = {}
        self.cache = Cache()

    def registerRDD(self, rddId, numPartitions):
        if rddId not in self.locs:
            logger.debug("Registering RDD ID %d with cache", rddId)
            self.locs[rddId] = [[] for i in range(numPartitions)]

    def getLocationsSnapshot(self):
        return self.locs

    def getCachedLocs(self, rdd_id, index):
        def parse_hostname(uri):
            if uri.startswith('http://'):
                h = uri.split(':')[1].rsplit('/', 1)[-1]
                return h
            return ''
        return map(parse_hostname, self.getCacheUri(rdd_id, index))

    def getCacheUri(self, rdd_id, index):
        return self.locs[rdd_id][index]

    def addHost(self, rdd_id, index, host):
        self.locs[rdd_id][index].append(host)

    def removeHost(self, rdd_id, index, host):
        if host in self.locs[rdd_id][index]:
            self.locs[rdd_id][index].remove(host)

class CacheTracker(BaseCacheTracker):
    def __init__(self):
        cachedir = os.path.join(env.get('WORKDIR')[0], 'cache')
        self.cache = DiskCache(self, cachedir)
        self.client = env.trackerClient
        if env.isMaster:
            self.locs = env.trackerServer.locs
        self.rdds = {}

    def registerRDD(self, rddId, numPartitions):
        self.rdds[rddId] = numPartitions

    def getLocationsSnapshot(self):
        result = {}
        for rdd_id, partitions in self.rdds.items():
            result[rdd_id] = [self.locs.get('cache:%s-%s' % (rdd_id, index), [])
                    for index in xrange(partitions)]

        return result

    def getCachedLocs(self, rdd_id, index):
        def parse_hostname(uri):
            if uri.startswith('http://'):
                h = uri.split(':')[1].rsplit('/', 1)[-1]
                return h
            return ''
        return map(parse_hostname, self.locs.get('cache:%s-%s' % (rdd_id, index), []))

    def getCacheUri(self, rdd_id, index):
        return self.client.call(GetValueMessage('cache:%s-%s' % (rdd_id, index)))

    def addHost(self, rdd_id, index, host):
        return self.client.call(AddItemMessage('cache:%s-%s' % (rdd_id, index), host))

    def removeHost(self, rdd_id, index, host):
        return self.client.call(RemoveItemMessage('cache:%s-%s' % (rdd_id, index), host))

    def getOrCompute(self, rdd, split):
        key = (rdd.id, split.index)
        cachedVal = self.cache.get(key)
        if cachedVal is not None:
            logger.debug("Found partition in cache! %s", key)
            for i in cachedVal:
                yield i

        else:
            logger.debug("partition not in cache, %s", key)
            for i in self.cache.put(key, rdd.compute(split), is_iterator=True):
                yield i

            serve_uri = env.get('SERVER_URI')
            if serve_uri:
                self.addHost(rdd.id, split.index, serve_uri)

    def __getstate__(self):
        raise Exception("!!!")


def test():
    logging.basicConfig(level=logging.DEBUG)
    from dpark.context import DparkContext
    dc = DparkContext("local")
    dc.start()
    nums = dc.parallelize(range(100), 10)
    tracker = CacheTracker(True)
    tracker.registerRDD(nums.id, len(nums))
    split = nums.splits[0]
    print list(tracker.getOrCompute(nums, split))
    print list(tracker.getOrCompute(nums, split))
    print tracker.getLocationsSnapshot()
    tracker.stop()

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = conf
import os.path
import logging

logger = logging.getLogger(__name__)

# workdir used in slaves for internal files
#
DPARK_WORK_DIR = '/tmp/dpark'
if os.path.exists('/dev/shm'):
    DPARK_WORK_DIR = '/dev/shm,/tmp/dpark'

# uri of mesos master, host[:5050] or or zk://...
MESOS_MASTER = 'localhost'

# mount points of MooseFS, must be available on all slaves
# for example:  '/mfs' : 'mfsmaster',
MOOSEFS_MOUNT_POINTS = {
}
# consistant dir cache in client, need patched mfsmaster
MOOSEFS_DIR_CACHE = False

def load_conf(path):
    if not os.path.exists(path):
        logger.error("conf %s do not exists", path)
        raise Exception("conf %s do not exists" % path)

    try:
        data = open(path).read()
        exec data in globals(), globals()
    except Exception, e:
        logger.error("error while load conf from %s: %s", path, e)
        raise

########NEW FILE########
__FILENAME__ = context
import os, sys
import atexit
import optparse
import signal
import logging
import gc

from dpark.rdd import *
from dpark.accumulator import Accumulator
from dpark.schedule import LocalScheduler, MultiProcessScheduler, MesosScheduler
from dpark.env import env
from dpark.moosefs import walk
from dpark.tabular import TabularRDD
import dpark.conf as conf
from math import ceil

logger = logging.getLogger("context")

def singleton(cls):
    instances = {}
    def getinstance(*a, **kw):
        key = (cls, tuple(a), tuple(sorted(kw.items())))
        if key not in instances:
            instances[key] = cls(*a, **kw)
        return instances[key]
    return getinstance

def setup_conf(options):
    if options.conf:
        conf.load_conf(options.conf)
    elif 'DPARK_CONF' in os.environ:
        conf.load_conf(os.environ['DPARK_CONF'])
    elif os.path.exists('/etc/dpark.conf'):
        conf.load_conf('/etc/dpark.conf')

    conf.__dict__.update(os.environ)
    import moosefs
    moosefs.MFS_PREFIX = conf.MOOSEFS_MOUNT_POINTS
    moosefs.master.ENABLE_DCACHE = conf.MOOSEFS_DIR_CACHE

@singleton
class DparkContext(object):
    nextShuffleId = 0
    def __init__(self, master=None):
        self.master = master
        self.initialized = False
        self.started = False
        self.defaultParallelism = 2

    def init(self):
        if self.initialized:
            return

        options = parse_options()
        self.options = options
        setup_conf(options)

        master = self.master or options.master
        if master == 'local':
            self.scheduler = LocalScheduler()
            self.isLocal = True
        elif master == 'process':
            self.scheduler = MultiProcessScheduler(options.parallel)
            self.isLocal = False
        else:
            if master == 'mesos':
                master = conf.MESOS_MASTER

            if master.startswith('mesos://'):
                if '@' in master:
                    master = master[master.rfind('@')+1:]
                else:
                    master = master[master.rfind('//')+2:]
            elif master.startswith('zoo://'):
                master = 'zk' + master[3:]

            if ':' not in master:
                master += ':5050'
            self.scheduler = MesosScheduler(master, options)
            self.isLocal = False

        self.master = master

        if options.parallel:
            self.defaultParallelism = options.parallel
        else:
            self.defaultParallelism = self.scheduler.defaultParallelism()
        self.defaultMinSplits = max(self.defaultParallelism, 2)

        self.initialized = True

    def newShuffleId(self):
        self.nextShuffleId += 1
        return self.nextShuffleId

    def parallelize(self, seq, numSlices=None):
        self.init()
        if numSlices is None:
            numSlices = self.defaultParallelism
        return ParallelCollection(self, seq, numSlices)

    def makeRDD(self, seq, numSlices=None):
        return self.parallelize(seq, numSlices)

    def textFile(self, path, ext='', followLink=True, maxdepth=0, cls=TextFileRDD, *ka, **kws):
        self.init()
        if isinstance(path, (list, tuple)):
            return self.union([self.textFile(p, ext, followLink, maxdepth, cls, *ka, **kws)
                for p in path])

        path = os.path.realpath(path)
        def create_rdd(cls, path, *ka, **kw):
            if cls is TextFileRDD:
                if path.endswith('.bz2'):
                    return BZip2FileRDD(self, path, *ka, **kw)
                elif path.endswith('.gz'):
                    return GZipFileRDD(self, path, *ka, **kw)
            return cls(self, path, *ka, **kw)

        if os.path.isdir(path):
            paths = []
            for root,dirs,names in walk(path, followlinks=followLink):
                if maxdepth > 0:
                    depth = len(filter(None, root[len(path):].split('/'))) + 1
                    if depth > maxdepth:
                        break
                for n in sorted(names):
                    if n.endswith(ext) and not n.startswith('.'):
                        p = os.path.join(root, n)
                        if followLink or not os.path.islink(p):
                            paths.append(p)
                dirs.sort()
                for d in dirs[:]:
                    if d.startswith('.'):
                        dirs.remove(d)

            rdds = [create_rdd(cls, p, *ka, **kws)
                     for p in paths]
            return self.union(rdds)
        else:
            return create_rdd(cls, path, *ka, **kws)

    def partialTextFile(self, path, begin, end, splitSize=None, numSplits=None):
        self.init()
        return PartialTextFileRDD(self, path, begin, end, splitSize, numSplits)

    def bzip2File(self, *args, **kwargs):
        "deprecated"
        logger.warning("bzip2File() is deprecated, use textFile('xx.bz2') instead")
        return self.textFile(cls=BZip2FileRDD, *args, **kwargs)

    def csvFile(self, path, dialect='excel', *args, **kwargs):
        return self.textFile(path, cls=TextFileRDD, *args, **kwargs).fromCsv(dialect)

    def binaryFile(self, path, fmt=None, length=None, *args, **kwargs):
        return self.textFile(path, cls=BinaryFileRDD, fmt=fmt, length=length, *args, **kwargs)

    def tableFile(self, path, *args, **kwargs):
        return self.textFile(path, cls=TableFileRDD, *args, **kwargs)

    def tabular(self, path, **kw):
        self.init()
        return TabularRDD(self, path, **kw)

    def table(self, path, **kwargs):
        dpath = path[0] if isinstance(path, (list, tuple)) else path
        for root, dirs, names in walk(dpath):
            if '.field_names' in names:
                p = os.path.join(root, '.field_names')
                fields = open(p).read().split('\t')
                break
        else:
            raise Exception("no .field_names found in %s" % path)
        return self.tableFile(path, **kwargs).asTable(fields)

    def beansdb(self, path, depth=None, filter=None, fullscan=False, raw=False, only_latest=False):
        "(Key, (Value, Version, Timestamp)) data in beansdb"
        self.init()
        if isinstance(path, (tuple, list)):
            return self.union([self.beansdb(p, depth, filter, fullscan, raw, only_latest)
                    for p in path])

        path = os.path.realpath(path)
        assert os.path.exists(path), "%s no exists" % path
        if os.path.isdir(path):
            subs = []
            if not depth:
                subs = [os.path.join(path, n) for n in os.listdir(path) if n.endswith('.data')]
            if subs:
                rdd = self.union([BeansdbFileRDD(self, p, filter, fullscan, True)
                        for p in subs])
            else:
                subs = [os.path.join(path, '%x'%i) for i in range(16)]
                rdd = self.union([self.beansdb(p, depth and depth-1, filter, fullscan, True, only_latest)
                        for p in subs if os.path.exists(p)])
                only_latest = False
        else:
            rdd = BeansdbFileRDD(self, path, filter, fullscan, True)

        # choose only latest version
        if only_latest:
            rdd = rdd.reduceByKey(lambda v1,v2: v1[2] > v2[2] and v1 or v2, int(ceil(len(rdd) / 4)))
        if not raw:
            rdd = rdd.mapValue(lambda (v,ver,t): (restore_value(*v), ver, t))
        return rdd

    def union(self, rdds):
        return UnionRDD(self, rdds)

    def zip(self, rdds):
        return ZippedRDD(self, rdds)

    def accumulator(self, init=0, param=None):
        return Accumulator(init, param)

    def broadcast(self, v):
        self.start()
        from dpark.broadcast import Broadcast
        return Broadcast(v)

    def start(self):
        if self.started:
            return

        self.init()

        env.start(True, isLocal=self.isLocal)
        self.scheduler.start()
        self.started = True
        atexit.register(self.stop)

        def handler(signm, frame):
            logger.error("got signal %d, exit now", signm)
            self.scheduler.shutdown()
        try:
            signal.signal(signal.SIGTERM, handler)
            signal.signal(signal.SIGHUP, handler)
            signal.signal(signal.SIGABRT, handler)
            signal.signal(signal.SIGQUIT, handler)
        except: pass

        try:
            from rfoo.utils import rconsole
            rconsole.spawn_server(locals(), 0)
        except ImportError:
            pass

    def runJob(self, rdd, func, partitions=None, allowLocal=False):
        self.start()

        if partitions is None:
            partitions = range(len(rdd))
        try:
            gc.disable()
            for it in self.scheduler.runJob(rdd, func, partitions, allowLocal):
                yield it
        finally:
            gc.collect()
            gc.enable()

    def clear(self):
        if not self.started:
            return

        self.scheduler.clear()
        gc.collect()

    def stop(self):
        if not self.started:
            return

        env.stop()
        self.scheduler.stop()
        self.started = False

    def __getstate__(self):
        raise ValueError("should not pickle ctx")


parser = optparse.OptionParser(usage="Usage: %prog [options] [args]")

def add_default_options():
    parser.disable_interspersed_args()

    group = optparse.OptionGroup(parser, "Dpark Options")

    group.add_option("-m", "--master", type="string", default="local",
            help="master of Mesos: local, process, host[:port], or mesos://")
#    group.add_option("-n", "--name", type="string", default="dpark",
#            help="job name")
    group.add_option("-p", "--parallel", type="int", default=0,
            help="number of processes")

    group.add_option("-c", "--cpus", type="float", default=1.0,
            help="cpus used per task")
    group.add_option("-M", "--mem", type="float", default=1000.0,
            help="memory used per task")
    group.add_option("-g", "--group", type="string", default="",
            help="which group of machines")
    group.add_option("--err", type="float", default=0.0,
            help="acceptable ignored error record ratio (0.01%)")
    group.add_option("--snapshot_dir", type="string", default="",
            help="shared dir to keep snapshot of RDDs")

    group.add_option("--conf", type="string",
            help="path for configuration file")
    group.add_option("--self", action="store_true",
            help="user self as exectuor")
    group.add_option("--profile", action="store_true",
            help="do profiling")
    group.add_option("--keep-order", action="store_true",
            help="deprecated, always keep order")

    parser.add_option_group(group)

    parser.add_option("-q", "--quiet", action="store_true")
    parser.add_option("-v", "--verbose", action="store_true")

add_default_options()

def parse_options():
    options, args = parser.parse_args()
    options.logLevel = (options.quiet and logging.ERROR
                  or options.verbose and logging.DEBUG or logging.INFO)

    logging.basicConfig(format='%(asctime)-15s [%(levelname)s] [%(name)-9s] %(message)s',
        level=options.logLevel)

    return options

########NEW FILE########
__FILENAME__ = decorator
# -*- coding: utf-8 -*-
class LazyJIT(object):
    this = None
    def __init__(self, decorator, f, *args, **kwargs):
        self.f = f
        self.args = args
        self.kwargs = kwargs
        self.decorator = decorator

    def __call__(self, *args, **kwargs):
        if self.this is None:
            try:
                mod = __import__('numba', fromlist=[self.decorator])
                d = getattr(mod, self.decorator)
                self.this = d(*self.args, **self.kwargs)(self.f)
            except ImportError, e:
                self.this = self.f
        return getattr(self.this, '__call__')(*args, **kwargs)


def jit(signature, **kwargs):
    if not isinstance(signature, (str, unicode)):
        raise ValueError('First argument should be signature')
    def _(f):
        return LazyJIT('jit', f, signature, **kwargs)
    return _

def autojit(*args, **kwargs):
    if len(args) ==1 and not kwargs and callable(args[0]):
        f = args[0]
        return LazyJIT('autojit', f)
    else:
        def _(f):
            return LazyJIT('autojit', f, *args, **kwargs)
        return _

########NEW FILE########
__FILENAME__ = dependency
import bisect

from dpark.util import portable_hash
from dpark.serialize import load_func, dump_func

class Dependency:
    def __init__(self, rdd):
        self.rdd = rdd

    def __getstate__(self):
        raise ValueError("Should not pickle dependency: %r" % self)

class NarrowDependency(Dependency):
    isShuffle = False
    def getParents(self, outputPartition):
        raise NotImplementedError

class OneToOneDependency(NarrowDependency):
    def getParents(self, pid):
        return [pid]

class OneToRangeDependency(NarrowDependency):
    def __init__(self, rdd, splitSize, length):
        Dependency.__init__(self, rdd)
        self.splitSize = splitSize
        self.length = length

    def getParents(self, pid):
        return range(pid * self.splitSize,
                min((pid+1) * self.splitSize, self.length))

class CartesianDependency(NarrowDependency):
    def __init__(self, rdd, first, numSplitsInRdd2):
        NarrowDependency.__init__(self, rdd)
        self.first = first
        self.numSplitsInRdd2 = numSplitsInRdd2

    def getParents(self, pid):
        if self.first:
            return [pid / self.numSplitsInRdd2]
        else:
            return [pid % self.numSplitsInRdd2]

class RangeDependency(NarrowDependency):
    def __init__(self, rdd, inStart, outStart, length):
        Dependency.__init__(self, rdd)
        self.inStart = inStart
        self.outStart = outStart
        self.length = length

    def getParents(self, pid):
        if pid >= self.outStart and pid < self.outStart + self.length:
            return [pid - self.outStart + self.inStart]
        return []

class ShuffleDependency(Dependency):
    isShuffle = True
    def __init__(self, shuffleId, rdd, aggregator, partitioner):
        Dependency.__init__(self, rdd)
        self.shuffleId = shuffleId
        self.aggregator = aggregator
        self.partitioner = partitioner


class Aggregator:
    def __init__(self, createCombiner, mergeValue,
            mergeCombiners):
        self.createCombiner = createCombiner
        self.mergeValue = mergeValue
        self.mergeCombiners = mergeCombiners

    def __getstate__(self):
        return (dump_func(self.createCombiner),
            dump_func(self.mergeValue),
            dump_func(self.mergeCombiners))

    def __setstate__(self, state):
        c1, c2, c3 = state
        self.createCombiner = load_func(c1)
        self.mergeValue = load_func(c2)
        self.mergeCombiners = load_func(c3)

class AddAggregator:
    def createCombiner(self, x):
        return x
    def mergeValue(self, s, x):
        return s + x
    def mergeCombiners(self, x, y):
        return x + y

class MergeAggregator:
    def createCombiner(self, x):
        return [x]
    def mergeValue(self, s, x):
        s.append(x)
        return s
    def mergeCombiners(self, x, y):
        x.extend(y)
        return x

class UniqAggregator:
    def createCombiner(self, x):
        return set([x])
    def mergeValue(self, s, x):
        s.add(x)
        return s
    def mergeCombiners(self, x, y):
        x |= y
        return x

class Partitioner:
    @property
    def numPartitions(self):
        raise NotImplementedError
    def getPartition(self, key):
        raise NotImplementedError

class HashPartitioner(Partitioner):
    def __init__(self, partitions):
        self.partitions = max(1, int(partitions))

    @property
    def numPartitions(self):
        return self.partitions

    def getPartition(self, key):
        return portable_hash(key) % self.partitions

    def __eq__(self, other):
        if isinstance(other, Partitioner):
            return other.numPartitions == self.numPartitions
        return False

class RangePartitioner(Partitioner):
    def __init__(self, keys, reverse=False):
        self.keys = sorted(keys)
        self.reverse = reverse

    @property
    def numPartitions(self):
        return len(self.keys) + 1

    def getPartition(self, key):
        idx = bisect.bisect(self.keys, key)
        return len(self.keys) - idx if self.reverse else idx

    def __eq__(self, other):
        if isinstance(other, RangePartitioner):
            return other.keys == self.keys and self.reverse == other.reverse
        return False

########NEW FILE########
__FILENAME__ = dstream
import os
import time
import math
import itertools
import logging
import random

from dpark.util import spawn
from dpark.dependency import Partitioner, HashPartitioner, Aggregator
from dpark.context import DparkContext
from dpark.rdd import CoGroupedRDD

logger = logging.getLogger(__name__)

class Interval(object):
    def __init__(self, beginTime, endTime):
        self.begin = beginTime
        self.end = endTime
    @property
    def duration(self):
        return self.end - self.begin
    def __add__(self, d):
        return Interval(self.begin + d, self.end + d)
    def __sub__(self, d):
        return Interval(self.begin - d, self.end - d)
    def __le__(self, that):
        assert self.duration == that.duration
        return self.begin < that.begin
    def __ge__(self, that):
        return not self < that
    def __str__(self):
        return '[%s, %s]' % (self.begin, self.end)
    @classmethod
    def current(cls, duration):
        now = int(time.time())
        ss = int(duration)
        begin = now / ss * ss
        return cls(begin, begin + duration)


class DStreamGraph(object):
    def __init__(self, batchDuration):
        self.inputStreams = []
        self.outputStreams = []
        self.zeroTime = None
        self.batchDuration = batchDuration
        self.rememberDuration = None

    def start(self, time):
        self.zeroTime = int(time / self.batchDuration) * self.batchDuration
        for out in self.outputStreams:
            #out.initialize(time)
            out.remember(self.rememberDuration)
        for ins in self.inputStreams:
            ins.start()

    def stop(self):
        for ins in self.inputStreams:
            ins.stop()

    #def setContext(self, ssc):
    #    for out in self.outputStreams:
    #        out.setContext(ssc)

    def remember(self, duration):
        self.rememberDuration = duration

    def addInputStream(self, input):
        input.setGraph(self)
        self.inputStreams.append(input)

    def addOutputStream(self, output):
        output.setGraph(self)
        self.outputStreams.append(output)

    def generateRDDs(self, time):
        #print 'generateRDDs', self, time
        return filter(None, [out.generateJob(time) for out in self.outputStreams])

    def forgetOldRDDs(self, time):
        for out in self.outputStreams:
            out.forgetOldRDDs(time)

    def updateCheckpointData(self, time):
        for out in self.outputStreams:
            out.updateCheckpointData(time)

    def restoreCheckpointData(self, time):
        for out in self.outputStreams:
            out.restoreCheckpointData(time)


class StreamingContext(object):
    def __init__(self, batchDuration, sc=None):
        if isinstance(sc, str) or not sc: # None
            sc = DparkContext(sc)
        self.sc = sc
        batchDuration = int(batchDuration)
        self.batchDuration = batchDuration
        self.graph = DStreamGraph(batchDuration)
        self.checkpointDir = None
        self.checkpointDuration = None
        self.networkInputTracker = None
        self.scheduler = None
        self.receiverJobThread = None

   # def load(self, cp):
   #     if isinstance(cp, str):
   #         cp = Checkpoint.read(cp)
   #     self.cp = cp
   #     self.sc = DparkContext(cp.master)
   #     self.graph = cp.graph
   #     self.graph.setContext(self)
   #     self.graph.restoreCheckpointData()
   #     #self.sc.setCheckpointDir(cp.checkpointDir, True)
   #     self.checkpointDir = cp.checkpointDir
   #     self.checkpointDuration = cp.checkpointDuration

    def remember(self, duration):
        self.graph.remember(duration)

    def checkpoint(self, directory, interval):
        #if directory:
        #    self.sc.setCheckpointDir(directory)
        self.checkpointDir = directory
        self.checkpointDuration = interval

    #def getInitialCheckpoint(self):
    #    return self.cp

    def registerInputStream(self, ds):
        return self.graph.addInputStream(ds)

    def registerOutputStream(self, ds):
        return self.graph.addOutputStream(ds)

    def networkTextStream(self, hostname, port):
        ds = SocketInputDStream(self, hostname, port)
        self.registerInputStream(ds)
        return ds

    def fileStream(self, directory, filter=None, newFilesOnly=True):
        ds = FileInputDStream(self, directory, filter, newFilesOnly)
        self.registerInputStream(ds)
        return ds

    def textFileStream(self, directory, filter=None, newFilesOnly=True):
        return self.fileStream(directory, filter, newFilesOnly).map(lambda (k,v):v)

    def makeStream(self, rdd):
        return ConstantInputDStream(self, rdd)

    def queueStream(self, queue, oneAtTime=True, defaultRDD=None):
        ds = QueueInputDStream(self, queue, oneAtTime, defaultRDD)
        self.registerInputStream(ds)
        return ds

    def union(self, streams):
        return UnionDStream(streams)

    def start(self, t=None):
        if not self.checkpointDuration:
            self.checkpointDuration = self.batchDuration

        # TODO
        #nis = [ds for ds in self.graph.inputStreams
        #            if isinstance(ds, NetworkInputDStream)]
        #if nis:
        #    self.networkInputTracker = NetworkInputTracker(self, nis)
        #    self.networkInputTracker.start()

        self.sc.start()
        self.scheduler = Scheduler(self)
        self.scheduler.start(t or time.time())

    def stop(self):
        if self.scheduler:
            self.scheduler.stop()
        if self.networkInputTracker:
            self.networkInputTracker.stop()
        if self.receiverJobThread:
            self.receiverJobThread.stop()
        self.sc.stop()
        logger.info("StreamingContext stopped successfully")

    def getSparkCheckpointDir(self, dir):
        return os.path.join(dir, str(random.randint(0, 1000)))


class Checkpoint(object):
    def __init__(self, ssc, time):
        self.ssc = ssc
        self.time = time
        self.master = ssc.sc.master
        self.framework = ssc.sc.jobName
        self.graph = ssc.graph
        self.checkpointDir = ssc.checkpointDir
        self.checkpointDuration = ssc.checkpointDuration

    def write(self, dir):
        pass

    @classmethod
    def read(cls, dir):
        pass


class Job(object):
    def __init__(self, time, func):
        self.time = time
        self.func = func

    def run(self):
        start = time.time()
        self.func()
        end = time.time()
        return end - start

    def __str__(self):
        return '<Job %s at %s>' % (self.func, self.time)

class JobManager(object):
    def __init__(self, numThreads):
        pass

    def runJob(self, job):
        logger.debug("start to run job %s", job)
        used = job.run()
        delayed = time.time() - job.time
        logger.info("job used %s, delayed %s", used, delayed)

class RecurringTimer(object):
    def __init__(self, period, callback):
        self.period = period
        self.callback = callback
        self.thread = None
        self.stopped = False

    def start(self, start):
        self.nextTime = (int(start / self.period) + 1) * self.period
        self.stopped = False
        self.thread = spawn(self.run)
        logger.debug("RecurringTimer started, nextTime is %d", self.nextTime)

    def stop(self):
        self.stopped = True
        if self.thread:
            self.thread.join()

    def run(self):
        while not self.stopped:
            now = time.time()
            if now >= self.nextTime:
                logger.debug("start call %s with %d (delayed %f)", self.callback,
                        self.nextTime, now - self.nextTime)
                self.callback(self.nextTime)
                self.nextTime += self.period
            else:
                time.sleep(max(min(self.nextTime - now, 1), 0.01))

class Scheduler(object):
    def __init__(self, ssc):
        self.ssc = ssc
        self.graph = ssc.graph
        self.jobManager = JobManager(1)
        #self.checkpointWriter = CheckpointWriter(ssc.checkpointDir) if ssc.checkpointDir else None
        self.timer = RecurringTimer(ssc.batchDuration, self.generateRDDs)

    def start(self, t):
        self.graph.start(t)
        self.timer.start(t)
        logger.info("Scheduler started")

    def stop(self):
        self.timer.stop()
        self.graph.stop()

    def generateRDDs(self, time):
        for job in self.graph.generateRDDs(time):
            logger.debug("start to run job %s", job)
            self.jobManager.runJob(job)
        self.graph.forgetOldRDDs(time)
    #    self.doCheckpoint(time)

    #def doCheckpoint(self, time):
    #    return
    #    if self.ssc.checkpointDuration and (time-self.graph.zeroTime):
    #        startTime = time.time()
    #        self.ssc.graph.updateCheckpointData()
    #        Checkpoint(self.ssc, time).write(self.ssc.checkpointDir)
    #        stopTime = time.time()
    #        logger.info("Checkpointing the graph took %.0f ms", (stopTime - startTime)*1000)


class DStream(object):
    """
 * A Discretized Stream (DStream), the basic abstraction in Spark Streaming, is a continuous
 * sequence of RDDs (of the same type) representing a continuous stream of data (see [[spark.RDD]]
 * for more details on RDDs). DStreams can either be created from live data (such as, data from
 * HDFS, Kafka or Flume) or it can be generated by transformation existing DStreams using operations
 * such as `map`, `window` and `reduceByKeyAndWindow`. While a Spark Streaming program is running, each
 * DStream periodically generates a RDD, either from live data or by transforming the RDD generated
 * by a parent DStream.
 *
 * This class contains the basic operations available on all DStreams, such as `map`, `filter` and
 * `window`. In addition, [[spark.streaming.PairDStreamFunctions]] contains operations available
 * only on DStreams of key-value pairs, such as `groupByKeyAndWindow` and `join`. These operations
 * are automatically available on any DStream of the right type (e.g., DStream[(Int, Int)] through
 * implicit conversions when `spark.streaming.StreamingContext._` is imported.
 *
 * DStreams internally is characterized by a few basic properties:
 *  - A list of other DStreams that the DStream depends on
 *  - A time interval at which the DStream generates an RDD
 *  - A function that is used to generate an RDD after each time interval
    """
    def __init__(self, ssc):
        self.ssc = ssc
        self.slideDuration = None
        self.dependencies = []

        self.generatedRDDs = {}
        self.rememberDuration = None
        self.mustCheckpoint = False
        self.checkpointDuration = None
        self.checkpointData = []
        self.graph = None

    @property
    def zeroTime(self):
        return self.graph.zeroTime

    @property
    def parentRememberDuration(self):
        return self.rememberDuration

    def checkpoint(self, interval):
        self.checkpointDuration = interval

#    def initialize(self):
#        if self.mustCheckpoint and not self.checkpointDuration:
#            self.checkpointDuration = max(10, self.slideDuration)
#        for dep in self.dependencies:
#            dep.initialize()

    #def setContext(self, ssc):
    #    self.ssc = ssc
    #    for dep in self.dependencies:
    #        dep.setContext(ssc)

    def setGraph(self, g):
        self.graph = g
        for dep in self.dependencies:
            dep.setGraph(g)

    def remember(self, duration):
        if duration and duration > self.rememberDuration:
            self.rememberDuration = duration
        for dep in self.dependencies:
            dep.remember(self.parentRememberDuration)

    def isTimeValid(self, t):
        d = (t - self.zeroTime)
        dd = d / self.slideDuration * self.slideDuration
        return abs(d-dd) < 1e-3

    def compute(self, time):
        raise NotImplementedError

    def getOrCompute(self, time):
        if time in self.generatedRDDs:
            return self.generatedRDDs[time]
        if self.isTimeValid(time):
            rdd = self.compute(time)
            self.generatedRDDs[time] = rdd
            # do checkpoint TODO
            return rdd
        #else:
            #print 'invalid time', time, (time - self.zeroTime) / self.slideDuration * self.slideDuration

    def generateJob(self, time):
        rdd = self.getOrCompute(time)
        if rdd:
            return Job(time, lambda : self.ssc.sc.runJob(rdd, lambda x:{}))

    def forgetOldRDDs(self, time):
        oldest = time - (self.rememberDuration or 0)
        for k in self.generatedRDDs.keys():
            if k < oldest:
                self.generatedRDDs.pop(k)
        for dep in self.dependencies:
            dep.forgetOldRDDs(time)

    def updateCheckpointData(self, time):
        newRdds = [(t, rdd.getCheckpointFile) for t, rdd in self.generatedRDDs.items()
                    if rdd.getCheckpointFile]
        oldRdds = self.checkpointData
        if newRdds:
            self.checkpointData = dict(newRdds)
        for dep in self.dependencies:
            dep.updateCheckpointData(time)
        ns = dict(newRdds)
        for t, p in oldRdds:
            if t not in ns:
                os.unlink(p)
                logger.info("remove %s %s", t, p)
        logger.info("updated checkpoint data for time %s (%d)", time, len(newRdds))

    def restoreCheckpointData(self):
        for t, path in self.checkpointData:
            self.generatedRDDs[t] = self.ssc.sc.checkpointFile(path)
        for dep in self.dependencies:
            dep.restoreCheckpointData()
        logger.info("restoreCheckpointData")

    def slice(self, beginTime, endTime):
        rdds = []
        t = endTime # - self.slideDuration
        while t > self.zeroTime and t > beginTime:
            rdd = self.getOrCompute(t)
            if rdd:
                rdds.append(rdd)
            t -= self.slideDuration
        return rdds

    def register(self):
        self.ssc.registerOutputStream(self)

    #  DStream Operations
    def union(self, that):
        return UnionDStream([self, that])

    def map(self, func):
        return MappedDStream(self, func)

    def flatMap(self, func):
        return FlatMappedDStream(self, func)

    def filter(self, func):
        return FilteredDStream(self, func)

    def glom(self):
        return GlommedDStream(self)

    def mapPartitions(self, func, preserve=False):
        return MapPartitionedDStream(self, func, preserve)

    def reduce(self, func):
        return self.map(lambda x:(None, x)).reduceByKey(func, 1).map(lambda (x,y):y)

    def count(self):
        return self.map(lambda x:1).reduce(lambda x,y:x+y)

    def foreach(self, func):
        out = ForEachDStream(self, func)
        self.ssc.registerOutputStream(out)
        return out

    def transform(self, func):
        return TransformedDStream(self, func)

    def show(self):
        def forFunc(rdd, t):
            some = rdd.take(11)
            print "-" * 80
            print "Time:", time.asctime(time.localtime(t))
            print "-" * 80
            for i in some[:10]:
                print i
            if len(some) > 10:
                print '...'
            print
        return self.foreach(forFunc)

    def window(self, duration, slideDuration=None):
        if slideDuration is None:
            slideDuration = self.slideDuration
        return WindowedDStream(self, duration, slideDuration)

    def tumble(self, batch):
        return self.window(batch, batch)

    def reduceByWindow(self, func, window, slideDuration=None, invFunc=None):
        if invFunc is not None:
            return self.map(lambda x:(1, x)).reduceByKeyAndWindow(func, invFunc,
                window, slideDuration, 1).map(lambda (x,y): y)
        return self.window(window, slideDuration).reduce(func)

    def countByWindow(self, windowDuration, slideDuration=None):
        return self.map(lambda x:1).reduceByWindow(lambda x,y:x+y,
            windowDuration, slideDuration, lambda x,y:x-y)

    def defaultPartitioner(self, part=None):
        if part is None:
            part = self.ssc.sc.defaultParallelism
        return HashPartitioner(part)

    def groupByKey(self, numPart=None):
        createCombiner = lambda x: [x]
        mergeValue = lambda l,x: l.append(x) or l
        mergeCombiner = lambda x,y: x.extend(y) or x
        if not isinstance(numPart, Partitioner):
            numPart = self.defaultPartitioner(numPart)
        return self.combineByKey(createCombiner, mergeValue, mergeCombiner, numPart)

    def reduceByKey(self, func, part=None):
        if not isinstance(part, Partitioner):
            part = self.defaultPartitioner(part)
        return self.combineByKey(lambda x:x, func, func, part)

    def combineByKey(self, createCombiner, mergeValue, mergeCombiner, partitioner):
        agg = Aggregator(createCombiner, mergeValue, mergeCombiner)
        return ShuffledDStream(self, agg, partitioner)

    def countByKey(self, numPartitions=None):
        return self.map(lambda (k,_):(k, 1)).reduceByKey(lambda x,y:x+y, numPartitions)

    def groupByKeyAndWindow(self, window, slideDuration=None, numPartitions=None):
        return self.window(window, slideDuration).groupByKey(numPartitions)

    def reduceByKeyAndWindow(self, func, invFunc, windowDuration, slideDuration=None, partitioner=None):
        if invFunc is None:
            return self.window(windowDuration, slideDuration).reduceByKey(func, partitioner)
        if slideDuration is None:
            slideDuration = self.slideDuration
        if not isinstance(partitioner, Partitioner):
            partitioner = self.defaultPartitioner(partitioner)
        return ReducedWindowedDStream(self, func, invFunc, windowDuration, slideDuration, partitioner)

    def countByKeyAndWindow(self, windowDuration, slideDuration=None, numPartitions=None):
        return self.map(lambda (k,_):(k, 1)).reduceByKeyAndWindow(
                lambda x,y:x+y, lambda x,y:x-y, windowDuration, slideDuration, numPartitions)

    def updateStateByKey(self, func, partitioner=None, remember=True):
        if not isinstance(partitioner, Partitioner):
            partitioner = self.defaultPartitioner(partitioner)
        def newF(it):
            for k, (vs, r) in it:
                nr = func(vs, r)
                if nr is not None:
                    yield (k, nr)
        return StateDStream(self, newF, partitioner, remember)

    def mapValues(self, func):
        return MapValuedDStream(self, func)

    def flatMapValues(self, func):
        return FlatMapValuedDStream(self, func)

    def cogroup(self, other, partitioner=None):
        if not isinstance(partitioner, Partitioner):
            partitioner = self.defaultPartitioner(partitioner)
        return CoGroupedDStream([self, other], partitioner)

    def join(self, other, partitioner=None):
        return self.cogroup(other, partitioner).flatMapValues(lambda (x,y): itertools.product(x,y))



class DerivedDStream(DStream):
    transformer = None
    def __init__(self, parent, func=None):
        DStream.__init__(self, parent.ssc)
        self.parent = parent
        self.func = func
        self.dependencies = [parent]
        self.slideDuration = parent.slideDuration

    def compute(self, t):
        rdd = self.parent.getOrCompute(t)
        if rdd:
            return getattr(rdd, self.transformer)(self.func)

class MappedDStream(DerivedDStream):
    transformer = 'map'

class FlatMappedDStream(DerivedDStream):
    transformer = 'flatMap'

class FilteredDStream(DerivedDStream):
    transformer = 'filter'

class MapValuedDStream(DerivedDStream):
    transformer = 'mapValue'

class FlatMapValuedDStream(DerivedDStream):
    transformer = 'flatMapValue'

class GlommedDStream(DerivedDStream):
    transformer = 'glom'
    def compute(self, t):
        rdd = self.parent.getOrCompute(t)
        if rdd:
            return rdd.glom()

class MapPartitionedDStream(DerivedDStream):
    def __init__(self, parent, func, preserve=True):
        DerivedDStream.__init__(self, parent, func)
        self.preserve = preserve

    def compute(self, t):
        rdd = self.parent.getOrCompute(t)
        if rdd:
            return rdd.mapPartitions(self.func) # TODO preserve

class TransformedDStream(DerivedDStream):
    def compute(self, t):
        rdd = self.parent.getOrCompute(t)
        if rdd:
            return self.func(rdd, t)

class ForEachDStream(DerivedDStream):
    def compute(self, t):
        return self.parent.getOrCompute(t)

    def generateJob(self, time):
        rdd = self.getOrCompute(time)
        if rdd:
            return Job(time, lambda :self.func(rdd, time))

class StateDStream(DerivedDStream):
    def __init__(self, parent, updateFunc, partitioner, preservePartitioning=True):
        DerivedDStream.__init__(self, parent, updateFunc)
        self.partitioner = partitioner
        self.preservePartitioning = preservePartitioning
        self.mustCheckpoint = True
        self.rememberDuration = self.slideDuration # FIXME

    def compute(self, t):
        if t <= self.zeroTime:
            #print 'less', t, self.zeroTime
            return
        prevRDD = self.getOrCompute(t - self.slideDuration)
        parentRDD = self.parent.getOrCompute(t)
        updateFuncLocal = self.func
        if prevRDD:
            if parentRDD:
                cogroupedRDD = parentRDD.cogroup(prevRDD)
                return cogroupedRDD.mapValue(lambda (vs, rs):(vs, rs and rs[0] or None)).mapPartitions(updateFuncLocal) # preserve TODO
            else:
                return prevRDD
        else:
            if parentRDD:
                groupedRDD = parentRDD.groupByKey(self.partitioner)
                return groupedRDD.mapValue(lambda v:(v, None)).mapPartitions(updateFuncLocal)

class UnionDStream(DStream):
    def __init__(self, parents):
        DStream.__init__(self, parents[0].ssc)
        self.parents = parents
        self.dependencies = parents
        self.slideDuration = parents[0].slideDuration

    def compute(self, t):
        rdds = filter(None, [p.getOrCompute(t) for p in self.parents])
        if rdds:
            return self.ssc.sc.union(rdds)

class WindowedDStream(DStream):
    def __init__(self, parent, windowDuration, slideDuration):
        DStream.__init__(self, parent.ssc)
        self.parent = parent
        self.windowDuration = windowDuration
        self.slideDuration = slideDuration
        self.dependencies = [parent]

    @property
    def parentRememberDuration(self):
        if self.rememberDuration:
            return self.rememberDuration + self.windowDuration

    def compute(self, t):
        currentWindow = Interval(t - self.windowDuration, t)
        rdds = self.parent.slice(currentWindow.begin, currentWindow.end)
        if rdds:
            return self.ssc.sc.union(rdds)


class CoGroupedDStream(DStream):
    def __init__(self, parents, partitioner):
        DStream.__init__(self, parents[0].ssc)
        self.parents = parents
        self.partitioner = partitioner
        assert len(set([p.slideDuration for p in parents])) == 1, "the slideDuration must be same"
        self.dependencies = parents
        self.slideDuration = parents[0].slideDuration

    def compute(self, t):
        rdds = filter(None, [p.getOrCompute(t) for p in self.parents])
        if rdds:
            return CoGroupedRDD(rdds, self.partitioner)


class ShuffledDStream(DerivedDStream):
    def __init__(self, parent, agg, partitioner):
        assert isinstance(parent, DStream)
        DerivedDStream.__init__(self, parent, agg)
        self.agg = agg
        self.partitioner = partitioner

    def compute(self, t):
        rdd = self.parent.getOrCompute(t)
        if rdd:
            return rdd.combineByKey(self.agg, self.partitioner)

class ReducedWindowedDStream(DerivedDStream):
    def __init__(self, parent, func, invReduceFunc,
            windowDuration, slideDuration, partitioner):
        DerivedDStream.__init__(self, parent, func)
        self.invfunc = invReduceFunc
        self.windowDuration = windowDuration
        self.slideDuration = slideDuration
        self.partitioner = partitioner
        self.reducedStream = parent.reduceByKey(func, partitioner)
        self.dependencies = [self.reducedStream]
        self.mustCheckpoint = True

    @property
    def parentRememberDuration(self):
        if self.rememberDuration:
            return self.windowDuration + self.rememberDuration
        # persist

    def compute(self, t):
        if t <= self.zeroTime:
            return
        reduceF = self.func
        invReduceF = self.invfunc
        currWindow = Interval(t - self.windowDuration, t)
        prevWindow = currWindow - self.slideDuration

        oldRDDs = self.reducedStream.slice(prevWindow.begin, currWindow.begin)
        newRDDs = self.reducedStream.slice(prevWindow.end, currWindow.end)
        prevWindowRDD = self.getOrCompute(prevWindow.end) or self.ssc.sc.makeRDD([])
        allRDDs = [prevWindowRDD] + oldRDDs + newRDDs
        cogroupedRDD = CoGroupedRDD(allRDDs, self.partitioner)

        nOld = len(oldRDDs)
        nNew = len(newRDDs)
        def mergeValues(values):
            #print values, nOld, nNew
            assert len(values) == 1+nOld+nNew
            oldValues = [values[i][0] for i in range(1, nOld+1) if values[i]]
            newValues = [values[i][0] for i in range(1+nOld, nOld+1+nNew) if values[i]]
            if not values[0]:
                if newValues:
                    return reduce(reduceF, newValues)
            else:
                tmp = values[0][0]
                if oldValues:
                    tmp = invReduceF(tmp, reduce(reduceF, oldValues))
                if newValues:
                    tmp = reduceF(tmp, reduce(reduceF, newValues))
                return tmp
        return cogroupedRDD.mapValue(mergeValues)


class InputDStream(DStream):
    def __init__(self, ssc):
        DStream.__init__(self, ssc)
        self.dependencies = []
        self.slideDuration = ssc.batchDuration

    def start(self):
        pass

    def stop(self):
        pass

class ConstantInputDStream(InputDStream):
    def __init__(self, ssc, rdd):
        InputDStream.__init__(self, ssc)
        self.rdd = rdd
    def compute(self, validTime):
        return self.rdd

def defaultFilter(path):
    if '/.' in path:
        return False
    return True

class ModTimeAndRangeFilter(object):
    def __init__(self, lastModTime, filter):
        self.lastModTime = lastModTime
        self.filter = filter
        self.latestModTime = 0
        self.accessedFiles = {}
        self.oldFiles = set()

    def __call__(self, path):
        if not self.filter(path):
            return

        if path in self.oldFiles:
            return
        mtime = os.path.getmtime(path)
        if mtime < self.lastModTime:
            self.oldFiles.add(path)
            return
        if mtime > self.latestModTime:
            self.latestModTime = mtime

        if os.path.islink(path):
            self.oldFiles.add(path)
            return

        nsize = os.path.getsize(path)
        osize = self.accessedFiles.get(path, 0)
        if nsize <= osize:
            return
        self.accessedFiles[path] = nsize
        logger.info("got new file %s [%d,%d]", path, osize, nsize)
        return path, osize, nsize

    def rotate(self):
        self.lastModTime = self.latestModTime

class FileInputDStream(InputDStream):
    def __init__(self, ssc, directory, filter=None, newFilesOnly=True):
        InputDStream.__init__(self, ssc)
        assert os.path.exists(directory), 'directory %s must exists' % directory
        assert os.path.isdir(directory), '%s is not directory' % directory
        self.directory = directory
        lastModTime = time.time() if newFilesOnly else 0
        self.filter = ModTimeAndRangeFilter(lastModTime, filter or defaultFilter)

    def compute(self, validTime):
        files = []
        for root, dirs, names in os.walk(self.directory):
            for name in names:
                r = self.filter(os.path.join(root, name))
                if r:
                    files.append(r)
        if files:
            self.filter.rotate()
            return self.ssc.sc.union([self.ssc.sc.partialTextFile(path, begin, end)
                    for path, begin, end in files])


class QueueInputDStream(InputDStream):
    def __init__(self, ssc, queue, oneAtAtime=True, defaultRDD=None):
        InputDStream.__init__(self, ssc)
        self.queue = queue
        self.oneAtAtime = oneAtAtime
        self.defaultRDD = defaultRDD

    def compute(self, t):
        if self.queue:
            if self.oneAtAtime:
                return self.queue.pop(0)
            else:
                r = self.ssc.sc.union(self.queue)
                self.queue = []
                return r
        elif self.defaultRDD:
            return self.defaultRDD

class NetworkReceiverMessage: pass
class StopReceiver(NetworkReceiverMessage):
    def __init__(self, msg):
        self.msg = msg
class ReportBlock(NetworkReceiverMessage):
    def __init__(self, blockId, metadata):
        self.blockId = blockId
        self.metadata = metadata
class ReportError(NetworkReceiverMessage):
    def __init__(self, msg):
        self.msg = msg

class NetworkReceiver(object):
    "TODO"

class NetworkInputDStream(InputDStream):
    def __init__(self, ssc):
        InputDStream.__init__(self, ssc)
        self.id = ssc.getNewNetworkStreamId()
    def createReceiver(self):
        return NetworkReceiver()
    def compute(self, t):
        blockIds = self.ssc.networkInputTracker.getBlockIds(self.id, t)
        #return [BlockRDD(self.ssc.sc, blockIds)]


class SocketReceiver(NetworkReceiver):
    pass

class SocketInputDStream(NetworkInputDStream):
    pass


class RawNetworkReceiver:
    "TODO"

class RawInputDStream(NetworkInputDStream):
    def createReceiver(self):
        return RawNetworkReceiver()

########NEW FILE########
__FILENAME__ = env
import os, logging
import time
import socket
import shutil

import zmq

from dpark import util
import dpark.conf as conf

logger = logging.getLogger("env")

class DparkEnv:
    environ = {}
    @classmethod
    def register(cls, name, value):
        cls.environ[name] = value
    @classmethod
    def get(cls, name, default=None):
        return cls.environ.get(name, default)

    def __init__(self):
        self.started = False

    def start(self, isMaster, environ={}, isLocal=False):
        if self.started:
            return
        logger.debug("start env in %s: %s %s", os.getpid(),
                isMaster, environ)
        self.isMaster = isMaster
        self.isLocal = isLocal
        if isMaster:
            roots = conf.DPARK_WORK_DIR
            if isinstance(roots, str):
                roots = roots.split(',')
            if isLocal:
                root = roots[0] # for local mode
                if not os.path.exists(root):
                    os.mkdir(root, 0777)
                    os.chmod(root, 0777) # because of umask

            name = '%s-%s-%d' % (time.strftime("%Y%m%d-%H%M%S"),
                socket.gethostname(), os.getpid())
            self.workdir = [os.path.join(root, name) for root in roots]
            for d in self.workdir:
                if not os.path.exists(d):
                    try: os.makedirs(d)
                    except OSError: pass
            self.environ['WORKDIR'] = self.workdir
            self.environ['COMPRESS'] = util.COMPRESS
        else:
            self.environ.update(environ)
            if self.environ['COMPRESS'] != util.COMPRESS:
                raise Exception("no %s available" % self.environ['COMPRESS'])

        self.ctx = zmq.Context()


        from dpark.tracker import TrackerServer, TrackerClient
        if isMaster:
            self.trackerServer = TrackerServer()
            self.trackerServer.start()
            addr = self.trackerServer.addr
            env.register('TrackerAddr', addr)
        else:
            addr = env.get('TrackerAddr')

        self.trackerClient = TrackerClient(addr)

        from dpark.cache import CacheTracker, LocalCacheTracker
        if isLocal:
            self.cacheTracker = LocalCacheTracker()
        else:
            self.cacheTracker = CacheTracker()

        from dpark.shuffle import LocalFileShuffle, MapOutputTracker, LocalMapOutputTracker
        LocalFileShuffle.initialize(isMaster)
        if isLocal:
            self.mapOutputTracker = LocalMapOutputTracker()
        else:
            self.mapOutputTracker = MapOutputTracker()
        from dpark.shuffle import SimpleShuffleFetcher, ParallelShuffleFetcher
        #self.shuffleFetcher = SimpleShuffleFetcher()
        self.shuffleFetcher = ParallelShuffleFetcher(2)

        from dpark.broadcast import start_manager
        start_manager(isMaster)

        self.started = True
        logger.debug("env started")

    def stop(self):
        if not getattr(self, 'started', False):
            return
        logger.debug("stop env in %s", os.getpid())
        self.shuffleFetcher.stop()
        self.cacheTracker.stop()
        self.mapOutputTracker.stop()
        if self.isMaster:
            self.trackerServer.stop()
        from dpark.broadcast import stop_manager
        stop_manager()

        logger.debug("cleaning workdir ...")
        for d in self.workdir:
            shutil.rmtree(d, True)
        logger.debug("done.")

        self.started = False

env = DparkEnv()

########NEW FILE########
__FILENAME__ = executor
import logging
import os, sys, time
import signal
import os.path
import marshal
import cPickle
import multiprocessing
import threading
import SocketServer
import SimpleHTTPServer
import shutil
import socket
import urllib2
import platform
import gc
import time

import zmq

import pymesos as mesos
import pymesos.mesos_pb2 as mesos_pb2

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dpark.util import compress, decompress, spawn
from dpark.serialize import marshalable
from dpark.accumulator import Accumulator
from dpark.schedule import Success, FetchFailed, OtherFailure
from dpark.env import env
from dpark.shuffle import LocalFileShuffle
from dpark.mutable_dict import MutableDict

logger = logging.getLogger("executor@%s" % socket.gethostname())

TASK_RESULT_LIMIT = 1024 * 256
DEFAULT_WEB_PORT = 5055
MAX_WORKER_IDLE_TIME = 60
MAX_EXECUTOR_IDLE_TIME = 60 * 60 * 24
Script = ''

def setproctitle(x):
    try:
        from setproctitle import setproctitle as _setproctitle
        _setproctitle(x)
    except ImportError:
        pass

def reply_status(driver, task_id, state, data=None):
    status = mesos_pb2.TaskStatus()
    status.task_id.MergeFrom(task_id)
    status.state = state
    status.timestamp = time.time()
    if data is not None:
        status.data = data
    driver.sendStatusUpdate(status)

def run_task(task_data):
    try:
        gc.disable()
        task, ntry = cPickle.loads(decompress(task_data))
        Accumulator.clear()
        result = task.run(ntry)
        accUpdate = Accumulator.values()
        MutableDict.flush()

        if marshalable(result):
            try:
                flag, data = 0, marshal.dumps(result)
            except Exception, e:
                flag, data = 1, cPickle.dumps(result, -1)

        else:
            flag, data = 1, cPickle.dumps(result, -1)
        data = compress(data)

        if len(data) > TASK_RESULT_LIMIT:
            path = LocalFileShuffle.getOutputFile(0, ntry, task.id, len(data))
            f = open(path, 'w')
            f.write(data)
            f.close()
            data = '/'.join([LocalFileShuffle.getServerUri()] + path.split('/')[-3:])
            flag += 2

        return mesos_pb2.TASK_FINISHED, cPickle.dumps((Success(), (flag, data), accUpdate), -1)
    except FetchFailed, e:
        return mesos_pb2.TASK_FAILED, cPickle.dumps((e, None, None), -1)
    except :
        import traceback
        msg = traceback.format_exc()
        return mesos_pb2.TASK_FAILED, cPickle.dumps((OtherFailure(msg), None, None), -1)
    finally:
        gc.collect()
        gc.enable()

def init_env(args):
    env.start(False, args)


class LocalizedHTTP(SimpleHTTPServer.SimpleHTTPRequestHandler):
    basedir = None
    def translate_path(self, path):
        out = SimpleHTTPServer.SimpleHTTPRequestHandler.translate_path(self, path)
        return self.basedir + '/' + os.path.relpath(out)

    def log_message(self, format, *args):
        pass

def startWebServer(path):
    # check the default web server
    if not os.path.exists(path):
        os.makedirs(path)
    testpath = os.path.join(path, 'test')
    with open(testpath, 'w') as f:
        f.write(path)
    default_uri = 'http://%s:%d/%s' % (socket.gethostname(), DEFAULT_WEB_PORT,
            os.path.basename(path))
    try:
        data = urllib2.urlopen(default_uri + '/' + 'test').read()
        if data == path:
            return default_uri
    except IOError, e:
        pass

    logger.warning("default webserver at %s not available", DEFAULT_WEB_PORT)
    LocalizedHTTP.basedir = os.path.dirname(path)
    ss = SocketServer.TCPServer(('0.0.0.0', 0), LocalizedHTTP)
    spawn(ss.serve_forever)
    uri = "http://%s:%d/%s" % (socket.gethostname(), ss.server_address[1],
            os.path.basename(path))
    return uri

def forward(fd, addr, prefix=''):
    f = os.fdopen(fd, 'r')
    ctx = zmq.Context()
    out = [None]
    buf = []
    def send(buf):
        if not out[0]:
            out[0] = ctx.socket(zmq.PUSH)
            out[0].connect(addr)
        out[0].send(prefix+''.join(buf))

    while True:
        try:
            line = f.readline()
            if not line: break
            buf.append(line)
            if line.endswith('\n'):
                send(buf)
                buf = []
        except IOError:
            break
    if buf:
        send(buf)
    if out[0]:
        out[0].close()
    f.close()
    ctx.shutdown()

def get_pool_memory(pool):
    try:
        import psutil
        p = psutil.Process(pool._pool[0].pid)
        return p.get_memory_info()[0] >> 20
    except Exception:
        return 0

def get_task_memory(task):
    for r in task.resources:
        if r.name == 'mem':
            return r.scalar.value
    logger.error("no memory in resource: %s", task.resources)
    return 100 # 100M

def safe(f):
    def _(self, *a, **kw):
        with self.lock:
            r = f(self, *a, **kw)
        return r
    return _

def setup_cleaner_process(workdir):
    ppid = os.getpid()
    pid = os.fork()
    if pid == 0:
        os.setsid()
        pid = os.fork()
        if pid == 0:
            try:
                import psutil
            except ImportError:
                os._exit(1)
            try:
                psutil.Process(ppid).wait()
                os.killpg(ppid, signal.SIGKILL) # kill workers
            except Exception, e:
                pass # make sure to exit
            finally:
                for d in workdir:
                    while os.path.exists(d):
                        try: shutil.rmtree(d, True)
                        except: pass
        os._exit(0)
    os.wait()

class MyExecutor(mesos.Executor):
    def __init__(self):
        self.workdir = []
        self.idle_workers = []
        self.busy_workers = {}
        self.lock = threading.RLock()

        self.stdout, wfd = os.pipe()
        sys.stdout = os.fdopen(wfd, 'w', 0)
        os.close(1)
        assert os.dup(wfd) == 1, 'redirect io failed'

        self.stderr, wfd = os.pipe()
        sys.stderr = os.fdopen(wfd, 'w', 0)
        os.close(2)
        assert os.dup(wfd) == 2, 'redirect io failed'

    def check_memory(self, driver):
        try:
            import psutil
        except ImportError:
            logger.error("no psutil module")
            return

        mem_limit = {}
        idle_since = time.time()

        while True:
            self.lock.acquire()

            for tid, (task, pool) in self.busy_workers.items():
                task_id = task.task_id
                try:
                    pid = pool._pool[0].pid
                    p = psutil.Process(pid)
                    rss = p.get_memory_info()[0] >> 20
                except Exception, e:
                    logger.error("worker process %d of task %s is dead: %s", pid, tid, e)
                    reply_status(driver, task_id, mesos_pb2.TASK_LOST)
                    self.busy_workers.pop(tid)
                    continue

                if p.status == psutil.STATUS_ZOMBIE or not p.is_running():
                    logger.error("worker process %d of task %s is zombie", pid, tid)
                    reply_status(driver, task_id, mesos_pb2.TASK_LOST)
                    self.busy_workers.pop(tid)
                    continue

                offered = get_task_memory(task)
                if not offered:
                    continue
                if rss > offered * 1.5:
                    logger.warning("task %s used too much memory: %dMB > %dMB * 1.5, kill it. "
                            + "use -M argument or taskMemory to request more memory.", tid, rss, offered)
                    reply_status(driver, task_id, mesos_pb2.TASK_KILLED)
                    self.busy_workers.pop(tid)
                    pool.terminate()
                elif rss > offered * mem_limit.get(tid, 1.0):
                    logger.debug("task %s used too much memory: %dMB > %dMB, "
                            + "use -M to request or taskMemory for more memory", tid, rss, offered)
                    mem_limit[tid] = rss / offered + 0.1

            now = time.time()
            n = len([1 for t, p in self.idle_workers if t + MAX_WORKER_IDLE_TIME < now])
            if n:
                for _, p in self.idle_workers[:n]:
                    p.terminate()
                self.idle_workers = self.idle_workers[n:]

            if self.busy_workers or self.idle_workers:
                idle_since = now
            elif idle_since + MAX_EXECUTOR_IDLE_TIME < now:
                os._exit(0)

            self.lock.release()

            time.sleep(1)

    @safe
    def registered(self, driver, executorInfo, frameworkInfo, slaveInfo):
        try:
            global Script
            Script, cwd, python_path, osenv, self.parallel, out_logger, err_logger, logLevel, args = marshal.loads(executorInfo.data)
            self.init_args = args
            sys.path = python_path
            os.environ.update(osenv)
            setproctitle(Script)

            prefix = '[%s] ' % socket.gethostname()
            self.outt = spawn(forward, self.stdout, out_logger, prefix)
            self.errt = spawn(forward, self.stderr, err_logger, prefix)
            logging.basicConfig(format='%(asctime)-15s [%(levelname)s] [%(name)-9s] %(message)s', level=logLevel)

            if os.path.exists(cwd):
                try:
                    os.chdir(cwd)
                except Exception, e:
                    logger.warning("change cwd to %s failed: %s", cwd, e)
            else:
                logger.warning("cwd (%s) not exists", cwd)

            self.workdir = args['WORKDIR']
            root = os.path.dirname(self.workdir[0])
            if not os.path.exists(root):
                os.mkdir(root)
                os.chmod(root, 0777) # because umask
            args['SERVER_URI'] = startWebServer(self.workdir[0])
            if 'MESOS_SLAVE_PID' in os.environ: # make unit test happy
                setup_cleaner_process(self.workdir)

            spawn(self.check_memory, driver)

            logger.debug("executor started at %s", slaveInfo.hostname)

        except Exception, e:
            import traceback
            msg = traceback.format_exc()
            logger.error("init executor failed: %s", msg)
            raise

    def get_idle_worker(self):
        try:
            return self.idle_workers.pop()[1]
        except IndexError:
            p = multiprocessing.Pool(1, init_env, [self.init_args])
            p.done = 0
            return p

    @safe
    def launchTask(self, driver, task):
        task_id = task.task_id
        reply_status(driver, task_id, mesos_pb2.TASK_RUNNING)
        logging.debug("launch task %s", task.task_id.value)
        try:
            def callback((state, data)):
                reply_status(driver, task_id, state, data)
                with self.lock:
                    _, pool = self.busy_workers.pop(task.task_id.value)
                    pool.done += 1
                    self.idle_workers.append((time.time(), pool))

            pool = self.get_idle_worker()
            self.busy_workers[task.task_id.value] = (task, pool)
            pool.apply_async(run_task, [task.data], callback=callback)

        except Exception, e:
            import traceback
            msg = traceback.format_exc()
            reply_status(driver, task_id, mesos_pb2.TASK_LOST, msg)

    @safe
    def killTask(self, driver, taskId):
        reply_status(driver, taskId, mesos_pb2.TASK_KILLED)
        if taskId.value in self.busy_workers:
            task, pool = self.busy_workers.pop(taskId.value)
            pool.terminate()

    @safe
    def shutdown(self, driver=None):
        def terminate(p):
            try:
                for pi in p._pool:
                    os.kill(pi.pid, signal.SIGKILL)
            except Exception, e:
                pass
        for _, p in self.idle_workers:
            terminate(p)
        for _, p in self.busy_workers.itervalues():
            terminate(p)

        # clean work files
        for d in self.workdir:
            try: shutil.rmtree(d, True)
            except: pass

        sys.stdout.close()
        sys.stderr.close()
        os.close(1)
        os.close(2)
        self.outt.join()
        self.errt.join()

def run():
    executor = MyExecutor()
    driver = mesos.MesosExecutorDriver(executor)
    driver.run()

if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = hotcounter
import operator

class HotCounter(object):
    def __init__(self, vs=[], limit=20):
        self.limit = limit
        self.total = {}
        self.updates = {}
        self._max = 0
        for v in vs:
            self.add(v)

    def add(self, v):
        c = self.updates.get(v, 0) + 1
        self.updates[v] = c
        if c > self._max:
            self._max = c

        if len(self.updates) > self.limit * 5 and self._max > 5:
            self._merge()

    def _merge(self):
        for k,c in self.updates.iteritems():
            if c > 1:
                self.total[k] = self.total.get(k, 0) + c
        self._max = 0
        self.updates = {}

        if len(self.total) > self.limit * 5:
            self.total = dict(self.top(self.limit*3))

    def update(self, o):
        self._merge()
        if isinstance(o, HotCounter):
            o._merge()
        for k,c in o.total.iteritems():
            self.total[k] = self.total.get(k,0) + c

    def top(self, limit):
        return sorted(self.total.items(), key=operator.itemgetter(1), reverse=True)[:limit]


if __name__ == '__main__':
    import random
    import math
    t = HotCounter()
    for j in range(10):
        c = HotCounter()
        for i in xrange(10000):
            v = int(math.sqrt(random.randint(0, 1000000)))
            c.add(v)
        t.update(c)
    for k,v in t.top(20):
        print k,v

########NEW FILE########
__FILENAME__ = hyperloglog
import math
from bisect import bisect_right
import array

try:
    import pyhash
    hash_func = pyhash.murmur2_x64_64a()
    HASH_LEN = 64
    raise ImportError
except ImportError:
    HASH_LEN = 30
    def hash_func(v):
        return hash(v) & 0x3fffffff

SPARSE = 0
NORMAL = 1

class HyperLogLog(object):
    def __init__(self, items=[], b=None, err=0.01):
        assert 0.005 <= err < 0.14, 'must 0.005 < err < 0.14'
        if b is None:
            b = int(math.ceil(math.log((1.04 / err) ** 2, 2)))
        self.alpha = self._get_alpha(b)
        self.b = b
        self.m = 1 << b
        self.M = None #array.array('B', [0] * self.m)
        self.threshold = self.m / 20
        self.items = set(items)
        self.mask = (1<<b) -1
        self.big = 1L << (HASH_LEN - b - 1)
        self.big2 = 1L << (HASH_LEN - b - 2)
        self.bitcount_arr = [1L << i for i in range(HASH_LEN - b + 1)]

    @staticmethod
    def _get_alpha(b):
        assert 4 <= b <= 16, 'b=%d should be in range [4,16]' % b
        alpha = (0.673, 0.697, 0.709)
        if b <= 6:
            return alpha[b-4]
        return 0.7213 / (1.0 + 1.079 / (1 << b))

    def _get_rho(self, w):
        # fast path
        if w > self.big:
            return 1
        if w > self.big2:
            return 2
        return len(self.bitcount_arr) - bisect_right(self.bitcount_arr, w)

    def convert(self):
        self.M = array.array('B', [0] * self.m)
        for i in self.items:
            self.add(i)
        self.items = None

    def add(self, value):
        if self.M is None:
            self.items.add(value)
            if len(self.items) > self.threshold:
                self.convert()
            return

        x = hash_func(value)
        j = x & self.mask
        w = x >> self.b
        h = self._get_rho(w)
        if h > self.M[j]:
            self.M[j] = h

    def update(self, other):
        if other.M is None:
            if self.M is None:
                self.items.update(other.items)
            else:
                for i in other.items:
                    self.add(i)
            return

        if self.M is None:
            self.convert()
        self.M = array.array('B', map(max, zip(self.M, other.M)))

    def __len__(self):
        if self.M is None:
            return len(self.items)

        S = sum(math.pow(2.0, -x) for x in self.M)
        E = self.alpha * self.m * self.m / S
        if E <= 2.5 * self.m: # small range correction
            V = self.M.count(0)
            return self.m * math.log(self.m / float(V)) if V > 0 else E
        elif E <= float(1L << HASH_LEN) / 30.0: # intermidiate range correction -> No correction
            return E
        else:
            return -(1L << HASH_LEN) * math.log(1.0 - E / (1L << HASH_LEN))

def test(l, err=0.03):
    hll = HyperLogLog(err)
    for i in l:
        hll.add(str(i)+'ip')
    le = len(hll)
    print err*100.0, len(hll.M), len(l), le, (le-len(l)) * 100.0 / len(l)

if __name__ == '__main__':
    for e in (0.005, 0.01, 0.03, 0.05, 0.1):
        test(xrange(100), e)
        test(xrange(10000), e)
        test(xrange(100000), e)
#        test(xrange(1000000), e)

########NEW FILE########
__FILENAME__ = job
import time
import sys
import logging
import socket
from operator import itemgetter

logger = logging.getLogger("job")

TASK_STARTING = 0
TASK_RUNNING  = 1
TASK_FINISHED = 2
TASK_FAILED   = 3
TASK_KILLED   = 4
TASK_LOST     = 5

def readable(size):
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit = 0
    while size > 1024:
        size /= 1024.0
        unit += 1
    return '%.1f%s' % (size, units[unit])

class Job:
    def __init__(self):
        self.id = self.newJobId()
        self.start = time.time()

    def slaveOffer(self, s, availableCpus):
        raise NotImplementedError

    def statusUpdate(self, t):
        raise NotImplementedError

    def error(self, code, message):
        raise NotImplementedError

    nextJobId = 0
    @classmethod
    def newJobId(cls):
        cls.nextJobId += 1
        return cls.nextJobId

LOCALITY_WAIT = 0
WAIT_FOR_RUNNING = 10
MAX_TASK_FAILURES = 4
MAX_TASK_MEMORY = 15 << 10 # 15GB

# A Job that runs a set of tasks with no interdependencies.
class SimpleJob(Job):

    def __init__(self, sched, tasks, cpus=1, mem=100):
        Job.__init__(self)
        self.sched = sched
        self.tasks = tasks

        for t in tasks:
            t.status = None
            t.tried = 0
            t.used = 0
            t.cpus = cpus
            t.mem = mem

        self.launched = [False] * len(tasks)
        self.finished = [False] * len(tasks)
        self.numFailures = [0] * len(tasks)
        self.blacklist = [[] for i in xrange(len(tasks))]
        self.tidToIndex = {}
        self.numTasks = len(tasks)
        self.tasksLaunched = 0
        self.tasksFinished = 0
        self.total_used = 0

        self.lastPreferredLaunchTime = time.time()

        self.pendingTasksForHost = {}
        self.pendingTasksWithNoPrefs = []
        self.allPendingTasks = []

        self.reasons = set()
        self.failed = False
        self.causeOfFailure = ""
        self.last_check = 0

        for i in range(len(tasks)):
            self.addPendingTask(i)
        self.host_cache = {}

    @property
    def taskEverageTime(self):
        if not self.tasksFinished:
            return 10
        return max(self.total_used / self.tasksFinished, 5)

    def addPendingTask(self, i):
        loc = self.tasks[i].preferredLocations()
        if not loc:
            self.pendingTasksWithNoPrefs.append(i)
        else:
            for host in loc:
                self.pendingTasksForHost.setdefault(host, []).append(i)
        self.allPendingTasks.append(i)

    def getPendingTasksForHost(self, host):
        try:
            return self.host_cache[host]
        except KeyError:
            v = self._getPendingTasksForHost(host)
            self.host_cache[host] = v
            return v

    def _getPendingTasksForHost(self, host):
        try:
            h, hs, ips = socket.gethostbyname_ex(host)
        except Exception:
            h, hs, ips = host, [], []
        tasks = sum((self.pendingTasksForHost.get(h, [])
            for h in [h] + hs + ips), [])
        st = {}
        for t in tasks:
            st[t] = st.get(t, 0) + 1
        ts = sorted(st.items(), key=itemgetter(1), reverse=True)
        return [t for t,_ in ts ]

    def findTaskFromList(self, l, host, cpus, mem):
        for i in l:
            if self.launched[i] or self.finished[i]:
                continue
            if host in self.blacklist[i]:
                continue
            t = self.tasks[i]
            if t.cpus <= cpus+1e-4 and t.mem <= mem:
                return i

    def findTask(self, host, localOnly, cpus, mem):
        localTask = self.findTaskFromList(self.getPendingTasksForHost(host), host, cpus, mem)
        if localTask is not None:
            return localTask, True
        noPrefTask = self.findTaskFromList(self.pendingTasksWithNoPrefs, host, cpus, mem)
        if noPrefTask is not None:
            return noPrefTask, True
        if not localOnly:
            return self.findTaskFromList(self.allPendingTasks, host, cpus, mem), False
#        else:
#            print repr(host), self.pendingTasksForHost
        return None, False

    # Respond to an offer of a single slave from the scheduler by finding a task
    def slaveOffer(self, host, availableCpus=1, availableMem=100):
        now = time.time()
        localOnly = (now - self.lastPreferredLaunchTime < LOCALITY_WAIT)
        i, preferred = self.findTask(host, localOnly, availableCpus, availableMem)
        if i is not None:
            task = self.tasks[i]
            task.status = TASK_STARTING
            task.start = now
            task.host = host
            task.tried += 1
            prefStr = preferred and "preferred" or "non-preferred"
            logger.debug("Starting task %d:%d as TID %s on slave %s (%s)",
                self.id, i, task, host, prefStr)
            self.tidToIndex[task.id] = i
            self.launched[i] = True
            self.tasksLaunched += 1
            self.blacklist[i].append(host)
            if preferred:
                self.lastPreferredLaunchTime = now
            return task
        logger.debug("no task found %s", localOnly)

    def statusUpdate(self, tid, tried, status, reason=None, result=None, update=None):
        logger.debug("job status update %s %s %s", tid, status, reason)
        if tid not in self.tidToIndex:
            logger.error("invalid tid: %s", tid)
            return
        i = self.tidToIndex[tid]
        if self.finished[i]:
            if status == TASK_FINISHED:
                logger.debug("Task %d is already finished, ignore it", tid)
            return

        task = self.tasks[i]
        task.status = status
        # when checking, task been masked as not launched
        if not self.launched[i]:
            self.launched[i] = True
            self.tasksLaunched += 1

        if status == TASK_FINISHED:
            self.taskFinished(tid, tried, result, update)
        elif status in (TASK_LOST, TASK_FAILED, TASK_KILLED):
            self.taskLost(tid, tried, status, reason)
        task.start = time.time()

    def taskFinished(self, tid, tried, result, update):
        i = self.tidToIndex[tid]
        self.finished[i] = True
        self.tasksFinished += 1
        task = self.tasks[i]
        task.used += time.time() - task.start
        self.total_used += task.used
        if sys.stderr.isatty():
            title = "Job %d: task %s finished in %.1fs (%d/%d)     " % (self.id, tid,
                task.used, self.tasksFinished, self.numTasks)
            logger.info("Task %s finished in %.1fs (%d/%d)      \x1b]2;%s\x07\x1b[1A",
                    tid, task.used, self.tasksFinished, self.numTasks, title)

        from dpark.schedule import Success
        self.sched.taskEnded(task, Success(), result, update)

        for t in range(task.tried):
            if t + 1 != tried:
                self.sched.killTask(self.id, task.id, t + 1)

        if self.tasksFinished == self.numTasks:
            ts = [t.used for t in self.tasks]
            tried = [t.tried for t in self.tasks]
            logger.info("Job %d finished in %.1fs: min=%.1fs, avg=%.1fs, max=%.1fs, maxtry=%d",
                self.id, time.time()-self.start,
                min(ts), sum(ts)/len(ts), max(ts), max(tried))
            from dpark.accumulator import LocalReadBytes, RemoteReadBytes
            lb, rb = LocalReadBytes.reset(), RemoteReadBytes.reset()
            if rb > 0:
                logger.info("read %s (%d%% localized)",
                    readable(lb+rb), lb*100/(rb+lb))

            self.sched.jobFinished(self)

    def taskLost(self, tid, tried, status, reason):
        index = self.tidToIndex[tid]

        from dpark.schedule import FetchFailed
        if isinstance(reason, FetchFailed) and self.numFailures[index] >= 1:
            logger.warning("Task %s was Lost due to fetch failure from %s",
                tid, reason.serverUri)
            self.sched.taskEnded(self.tasks[index], reason, None, None)
            # cancel tasks
            if not self.finished[index]:
                self.finished[index] = True
                self.tasksFinished += 1
            for i in range(len(self.finished)):
                if not self.launched[i]:
                    self.launched[i] = True
                    self.tasksLaunched += 1
                    self.finished[i] = True
                    self.tasksFinished += 1
            if self.tasksFinished == self.numTasks:
                self.sched.jobFinished(self) # cancel job
            return

        task = self.tasks[index]
        if status == TASK_KILLED:
            task.mem = min(task.mem * 2, MAX_TASK_MEMORY)
            for i,t in enumerate(self.tasks):
                if not self.launched[i]:
                    t.mem = max(task.mem, t.mem)

        elif status == TASK_FAILED:
            _logger = logger.error if self.numFailures[index] == MAX_TASK_FAILURES\
                    else logger.warning
            if reason not in self.reasons:
                _logger("task %s failed @ %s: %s\n%s", task.id, task.host, task, reason)
                self.reasons.add(reason)
            else:
                _logger("task %s failed @ %s: %s", task.id, task.host, task)

        elif status == TASK_LOST:
            logger.warning("Lost Task %d (task %d:%d:%s) %s at %s", index, self.id,
                    tid, tried, reason, task.host)

        self.numFailures[index] += 1
        if self.numFailures[index] > MAX_TASK_FAILURES:
            logger.error("Task %d failed more than %d times; aborting job",
                index, MAX_TASK_FAILURES)
            self.abort("Task %d failed more than %d times"
                % (index, MAX_TASK_FAILURES))

        self.launched[index] = False
        if self.tasksLaunched == self.numTasks:
            self.sched.requestMoreResources()
	    for i in xrange(len(self.blacklist)):
	    	self.blacklist[i] = []
        self.tasksLaunched -= 1

    def check_task_timeout(self):
        now = time.time()
        if self.last_check + 5 > now:
            return False
        self.last_check = now

        n = self.launched.count(True)
        if n != self.tasksLaunched:
            logger.warning("bug: tasksLaunched(%d) != %d", self.tasksLaunched, n)
            self.tasksLaunched = n

        for i in xrange(self.numTasks):
            task = self.tasks[i]
            if (self.launched[i] and task.status == TASK_STARTING
                    and task.start + WAIT_FOR_RUNNING < now):
                logger.debug("task %d timeout %.1f (at %s), re-assign it",
                        task.id, now - task.start, task.host)
                self.launched[i] = False
                self.tasksLaunched -= 1

        if self.tasksFinished > self.numTasks * 2.0 / 3:
            scale = 1.0 * self.numTasks / self.tasksFinished
            avg = max(self.taskEverageTime, 10)
            tasks = sorted((task.start, i, task)
                for i,task in enumerate(self.tasks)
                if self.launched[i] and not self.finished[i])
            for _t, idx, task in tasks:
                used = now - task.start
                #logger.debug("task %s used %.1f (avg = %.1f)", task.id, used, avg)
                if used > avg * (2 ** task.tried) * scale:
                    # re-submit timeout task
                    if task.tried <= MAX_TASK_FAILURES:
                        logger.debug("re-submit task %s for timeout %.1f, try %d",
                            task.id, used, task.tried)
                        task.used += used
                        task.start = now
                        self.launched[idx] = False
                        self.tasksLaunched -= 1
                    else:
                        logger.error("task %s timeout, aborting job %s",
                            task, self.id)
                        self.abort("task %s timeout" % task)
                else:
                    break
        return self.tasksLaunched < n

    def abort(self, message):
        logger.error("abort the job: %s", message)
        tasks = ' '.join(str(i) for i in xrange(len(self.finished))
                if not self.finished[i])
        logger.error("not finished tasks: %s", tasks)
        self.failed = True
        self.causeOfFailure = message
        self.sched.jobFinished(self)
        self.sched.shutdown()

########NEW FILE########
__FILENAME__ = consts

VERSION_ANY       = 0
CRC_POLY          = 0xEDB88320
MFS_ROOT_ID       = 1
MFS_NAME_MAX      = 255
MFS_MAX_FILE_SIZE = 0x20000000000

# 1.6.21
VERSION = 0x010615

CHUNKSIZE = 1<<26

GETDIR_FLAG_WITHATTR   = 0x01
GETDIR_FLAG_ADDTOCACHE = 0x02
GETDIR_FLAG_DIRCACHE   = 0x04

#type for readdir command
TYPE_FILE      = 'f'
TYPE_SYMLINK   = 'l'
TYPE_DIRECTORY = 'd'
TYPE_FIFO      = 'q'
TYPE_BLOCKDEV  = 'b'
TYPE_CHARDEV   = 'c'
TYPE_SOCKET    = 's'
TYPE_TRASH     = 't'
TYPE_RESERVED  = 'r'
TYPE_UNKNOWN   = '?'

# status code
STATUS_OK            = 0 # OK

ERROR_EPERM          = 1 # Operation not permitted
ERROR_ENOTDIR        = 2 # Not a directory
ERROR_ENOENT         = 3 # No such file or directory
ERROR_EACCES         = 4 # Permission denied
ERROR_EEXIST         = 5 # File exists
ERROR_EINVAL         = 6 # Invalid argument
ERROR_ENOTEMPTY      = 7 # Directory not empty
ERROR_CHUNKLOST      = 8 # Chunk lost
ERROR_OUTOFMEMORY    = 9 # Out of memory

ERROR_INDEXTOOBIG    = 10 # Index too big
ERROR_LOCKED         = 11 # Chunk locked
ERROR_NOCHUNKSERVERS = 12 # No chunk servers
ERROR_NOCHUNK        = 13 # No such chunk
ERROR_CHUNKBUSY      = 14 # Chunk is busy
ERROR_REGISTER       = 15 # Incorrect register BLOB
ERROR_NOTDONE        = 16 # None of chunk servers performed requested operation
ERROR_NOTOPENED      = 17 # File not opened
ERROR_NOTSTARTED     = 18 # Write not started

ERROR_WRONGVERSION   = 19 # Wrong chunk version
ERROR_CHUNKEXIST     = 20 # Chunk already exists
ERROR_NOSPACE        = 21 # No space left
ERROR_IO             = 22 # IO error
ERROR_BNUMTOOBIG     = 23 # Incorrect block number
ERROR_WRONGSIZE      = 24 # Incorrect size
ERROR_WRONGOFFSET    = 25 # Incorrect offset
ERROR_CANTCONNECT    = 26 # Can't connect
ERROR_WRONGCHUNKID   = 27 # Incorrect chunk id
ERROR_DISCONNECTED   = 28 # Disconnected
ERROR_CRC            = 29 # CRC error
ERROR_DELAYED        = 30 # Operation delayed
ERROR_CANTCREATEPATH = 31 # Can't create path

ERROR_MISMATCH       = 32 # Data mismatch
ERROR_EROFS          = 33 # Read-only file system
ERROR_QUOTA          = 34 # Quota exceeded
ERROR_BADSESSIONID   = 35 # Bad session id
ERROR_NOPASSWORD     = 36 # Password is needed
ERROR_BADPASSWORD    = 37 # Incorrect password
ERROR_MAX            = 38

# flags: "flags" fileld in "CUTOMA_FUSE_AQUIRE"
WANT_READ    = 1
WANT_WRITE   = 2
AFTER_CREATE = 4

# flags: "setmask" field in "CUTOMA_FUSE_SETATTR"
# SET_GOAL_FLAG,SET_DELETE_FLAG are no longer supported
# SET_LENGTH_FLAG,SET_OPENED_FLAG are deprecated
# instead of using FUSE_SETATTR with SET_GOAL_FLAG use FUSE_SETGOAL command
# instead of using FUSE_SETATTR with SET_GOAL_FLAG use FUSE_SETTRASH_TIMEOUT command
# instead of using FUSE_SETATTR with SET_LENGTH_FLAG/SET_OPENED_FLAG use FUSE_TRUNCATE command
SET_GOAL_FLAG     = 1 << 0
SET_MODE_FLAG     = 1 << 1
SET_UID_FLAG      = 1 << 2
SET_GID_FLAG      = 1 << 3
SET_LENGTH_FLAG   = 1 << 4
SET_MTIME_FLAG    = 1 << 5
SET_ATIME_FLAG    = 1 << 6
SET_OPENED_FLAG   = 1 << 7
SET_DELETE_FLAG   = 1 << 8
ANTOAN_NOP        = 0

# CHUNKSERVER <-> CLIENT/CHUNKSERVER
CUTOCS_READ = 200
# chunkid:64 version:32 offset:32 size:32
CSTOCU_READ_STATUS = 201
# chunkid:64 status:8
CSTOCU_READ_DATA = 202
# chunkid:64 blocknum:16 offset:16 size:32 crc:32 size*[ databyte:8 ]

CUTOCS_WRITE = 210
# chunkid:64 version:32 N*[ ip:32 port:16 ]
CSTOCU_WRITE_STATUS = 211
# chunkid:64 writeid:32 status:8
CUTOCS_WRITE_DATA = 212
# chunkid:64 writeid:32 blocknum:16 offset:16 size:32 crc:32 size*[ databyte:8 ]
CUTOCS_WRITE_FINISH = 213
# chunkid:64 version:32

#ANY <-> CHUNKSERVER
ANTOCS_CHUNK_CHECKSUM = 300
# chunkid:64 version:32
CSTOAN_CHUNK_CHECKSUM = 301
# chunkid:64 version:32 checksum:32
# chunkid:64 version:32 status:8

ANTOCS_CHUNK_CHECKSUM_TAB = 302
# chunkid:64 version:32
CSTOAN_CHUNK_CHECKSUM_TAB = 303
# chunkid:64 version:32 1024*[checksum:32]
# chunkid:64 version:32 status:8

# CLIENT <-> MASTER

# old attr record:
#   type:8 flags:8 mode:16 uid:32 gid:32 atime:32 mtime:32 ctime:32 length:64
#   total: 32B (1+1+2+4+4+4+4+4+8
#
#   flags: ---DGGGG
#             |\--/
#             |  \------ goal
#             \--------- delete imediatelly

# new attr record:
#   type:8 mode:16 uid:32 gid:32 atime:32 mtime:32 ctime:32 nlink:32 length:64
#   total: 35B
#
#   mode: FFFFMMMMMMMMMMMM
#         \--/\----------/
#           \       \------- mode
#            \-------------- flags
#
#   in case of BLOCKDEV and CHARDEV instead of 'length:64' on the end there is 'mojor:16 minor:16 empty:32'

# NAME type:
# ( leng:8 data:lengB


FUSE_REGISTER_BLOB_NOACL = "kFh9mdZsR84l5e675v8bi54VfXaXSYozaU3DSz9AsLLtOtKipzb9aQNkxeOISx64"
# CUTOMA:
#  clientid:32 [ version:32 ]
# MATOCU:
#  clientid:32
#  status:8

FUSE_REGISTER_BLOB_TOOLS_NOACL = "kFh9mdZsR84l5e675v8bi54VfXaXSYozaU3DSz9AsLLtOtKipzb9aQNkxeOISx63"
# CUTOMA:
#  -
# MATOCU:
#  status:8

FUSE_REGISTER_BLOB_ACL = "DjI1GAQDULI5d2YjA26ypc3ovkhjvhciTQVx3CS4nYgtBoUcsljiVpsErJENHaw0"

REGISTER_GETRANDOM = 1
# rcode==1: generate random blob
# CUTOMA:
#  rcode:8
# MATOCU:
#  randomblob:32B

REGISTER_NEWSESSION = 2
# rcode==2: first register
# CUTOMA:
#  rcode:8 version:32 ileng:32 info:ilengB pleng:32 path:plengB [ passcode:16B ]
# MATOCU:
#  sessionid:32 sesflags:8 rootuid:32 rootgid:32
#  status:8

REGISTER_RECONNECT = 3
# rcode==3: mount reconnect
# CUTOMA:
#  rcode:8 sessionid:32 version:32
# MATOCU:
#  status:8

REGISTER_TOOLS = 4
# rcode==4: tools connect
# CUTOMA:
#  rcode:8 sessionid:32 version:32
# MATOCU:
#  status:8

REGISTER_NEWMETASESSION = 5
# rcode==5: first register
# CUTOMA:
#  rcode:8 version:32 ileng:32 info:ilengB [ passcode:16B ]
# MATOCU:
#  sessionid:32 sesflags:8
#  status:8

CUTOMA_FUSE_REGISTER = 400
# blob:64B ... (depends on blob - see blob descriptions above
MATOCU_FUSE_REGISTER = 401
# depends on blob - see blob descriptions above
CUTOMA_FUSE_STATFS = 402
# msgid:32 -
MATOCU_FUSE_STATFS = 403
# msgid:32 totalspace:64 availspace:64 trashspace:64 inodes:32
CUTOMA_FUSE_ACCESS = 404
# msgid:32 inode:32 uid:32 gid:32 modemask:8
MATOCU_FUSE_ACCESS = 405
# msgid:32 status:8
CUTOMA_FUSE_LOOKUP = 406
# msgid:32 inode:32 name:NAME uid:32 gid:32
MATOCU_FUSE_LOOKUP = 407
# msgid:32 status:8
# msgid:32 inode:32 attr:35B
CUTOMA_FUSE_GETATTR = 408
# msgid:32 inode:32
# msgid:32 inode:32 uid:32 gid:32
MATOCU_FUSE_GETATTR = 409
# msgid:32 status:8
# msgid:32 attr:35B
CUTOMA_FUSE_SETATTR = 410
# msgid:32 inode:32 uid:32 gid:32 setmask:8 attr:32B   - compatibility with very old version
# msgid:32 inode:32 uid:32 gid:32 setmask:16 attr:32B  - compatibility with old version
# msgid:32 inode:32 uid:32 gid:32 setmask:8 attrmode:16 attruid:32 attrgid:32 attratime:32 attrmtime:32
MATOCU_FUSE_SETATTR = 411
# msgid:32 status:8
# msgid:32 attr:35B
CUTOMA_FUSE_READLINK = 412
# msgid:32 inode:32
MATOCU_FUSE_READLINK = 413
# msgid:32 status:8
# msgid:32 length:32 path:lengthB
CUTOMA_FUSE_SYMLINK = 414
# msgid:32 inode:32 name:NAME length:32 path:lengthB uid:32 gid:32
MATOCU_FUSE_SYMLINK = 415
# msgid:32 status:8
# msgid:32 inode:32 attr:35B
CUTOMA_FUSE_MKNOD = 416
# msgid:32 inode:32 name:NAME type:8 mode:16 uid:32 gid:32 rdev:32
MATOCU_FUSE_MKNOD = 417
# msgid:32 status:8
# msgid:32 inode:32 attr:35B
CUTOMA_FUSE_MKDIR = 418
# msgid:32 inode:32 name:NAME mode:16 uid:32 gid:32
MATOCU_FUSE_MKDIR = 419
# msgid:32 status:8
# msgid:32 inode:32 attr:35B
CUTOMA_FUSE_UNLINK = 420
# msgid:32 inode:32 name:NAME uid:32 gid:32
MATOCU_FUSE_UNLINK = 421
# msgid:32 status:8
CUTOMA_FUSE_RMDIR = 422
# msgid:32 inode:32 name:NAME uid:32 gid:32
MATOCU_FUSE_RMDIR = 423
# msgid:32 status:8
CUTOMA_FUSE_RENAME = 424
# msgid:32 inode_src:32 name_src:NAME inode_dst:32 name_dst:NAME uid:32 gid:32
MATOCU_FUSE_RENAME = 425
# msgid:32 status:8
CUTOMA_FUSE_LINK = 426
# msgid:32 inode:32 inode_dst:32 name_dst:NAME uid:32 gid:32
MATOCU_FUSE_LINK = 427
# msgid:32 status:8
# msgid:32 inode:32 attr:35B
CUTOMA_FUSE_GETDIR = 428
# msgid:32 inode:32 uid:32 gid:32 - old version (works like new version with flags==0
# msgid:32 inode:32 uid:32 gid:32 flags:8
MATOCU_FUSE_GETDIR = 429
# msgid:32 status:8
# msgid:32 N*[ name:NAME inode:32 type:8 ] - when GETDIR_FLAG_WITHATTR in flags is not set
# msgid:32 N*[ name:NAME inode:32 type:35B ]   - when GETDIR_FLAG_WITHATTR in flags is set
CUTOMA_FUSE_OPEN = 430
# msgid:32 inode:32 uid:32 gid:32 flags:8
MATOCU_FUSE_OPEN = 431
# msgid:32 status:8
# since 1.6.9 if no error:
# msgid:32 attr:35B

CUTOMA_FUSE_READ_CHUNK = 432
# msgid:32 inode:32 chunkindx:32
MATOCU_FUSE_READ_CHUNK = 433
# msgid:32 status:8
# msgid:32 length:64 chunkid:64 version:32 N*[ip:32 port:16]
# msgid:32 length:64 srcs:8 srcs*[chunkid:64 version:32 ip:32 port:16] - not implemented
CUTOMA_FUSE_WRITE_CHUNK = 434 # it creates, duplicates or sets new version of chunk if necessary */
# msgid:32 inode:32 chunkindx:32
MATOCU_FUSE_WRITE_CHUNK = 435
# msgid:32 status:8
# msgid:32 length:64 chunkid:64 version:32 N*[ip:32 port:16]
CUTOMA_FUSE_WRITE_CHUNK_END = 436
# msgid:32 chunkid:64 inode:32 length:64
MATOCU_FUSE_WRITE_CHUNK_END = 437
# msgid:32 status:8


CUTOMA_FUSE_APPEND = 438
# msgid:32 inode:32 srcinode:32 uid:32 gid:32 - append to existing element
MATOCU_FUSE_APPEND = 439
# msgid:32 status:8


CUTOMA_FUSE_CHECK = 440
# msgid:32 inode:32
MATOCU_FUSE_CHECK = 441
# msgid:32 status:8
# msgid:32 N*[ copies:8 chunks:16 ]

CUTOMA_FUSE_GETTRASHTIME = 442
# msgid:32 inode:32 gmode:8
MATOCU_FUSE_GETTRASHTIME = 443
# msgid:32 status:8
# msgid:32 tdirs:32 tfiles:32 tdirs*[ trashtime:32 dirs:32 ] tfiles*[ trashtime:32 files:32 ]
CUTOMA_FUSE_SETTRASHTIME = 444
# msgid:32 inode:32 uid:32 trashtimeout:32 smode:8
MATOCU_FUSE_SETTRASHTIME = 445
# msgid:32 status:8
# msgid:32 changed:32 notchanged:32 notpermitted:32

CUTOMA_FUSE_GETGOAL = 446
# msgid:32 inode:32 gmode:8
MATOCU_FUSE_GETGOAL = 447
# msgid:32 status:8
# msgid:32 gdirs:8 gfiles:8 gdirs*[ goal:8 dirs:32 ] gfiles*[ goal:8 files:32 ]

CUTOMA_FUSE_SETGOAL = 448
# msgid:32 inode:32 uid:32 goal:8 smode:8
MATOCU_FUSE_SETGOAL = 449
# msgid:32 status:8
# msgid:32 changed:32 notchanged:32 notpermitted:32

CUTOMA_FUSE_GETTRASH = 450
# msgid:32
MATOCU_FUSE_GETTRASH = 451
# msgid:32 status:8
# msgid:32 N*[ name:NAME inode:32 ]

CUTOMA_FUSE_GETDETACHEDATTR = 452
# msgid:32 inode:32 dtype:8
MATOCU_FUSE_GETDETACHEDATTR = 453
# msgid:32 status:8
# msgid:32 attr:35B

CUTOMA_FUSE_GETTRASHPATH = 454
# msgid:32 inode:32
MATOCU_FUSE_GETTRASHPATH = 455
# msgid:32 status:8
# msgid:32 length:32 path:lengthB

CUTOMA_FUSE_SETTRASHPATH = 456
# msgid:32 inode:32 length:32 path:lengthB
MATOCU_FUSE_SETTRASHPATH = 457
# msgid:32 status:8

CUTOMA_FUSE_UNDEL = 458
# msgid:32 inode:32
MATOCU_FUSE_UNDEL = 459
# msgid:32 status:8
CUTOMA_FUSE_PURGE = 460
# msgid:32 inode:32
MATOCU_FUSE_PURGE = 461
# msgid:32 status:8

CUTOMA_FUSE_GETDIRSTATS = 462
# msgid:32 inode:32
MATOCU_FUSE_GETDIRSTATS = 463
# msgid:32 status:8
# msgid:32 inodes:32 dirs:32 files:32 ugfiles:32 mfiles:32 chunks:32 ugchunks:32 mchunks32 length:64 size:64 gsize:64

CUTOMA_FUSE_TRUNCATE = 464
# msgid:32 inode:32 [opened:8] uid:32 gid:32 opened:8 length:64
MATOCU_FUSE_TRUNCATE = 465
# msgid:32 status:8
# msgid:32 attr:35B

CUTOMA_FUSE_REPAIR = 466
# msgid:32 inode:32 uid:32 gid:32
MATOCU_FUSE_REPAIR = 467
# msgid:32 status:8
# msgid:32 notchanged:32 erased:32 repaired:32

CUTOMA_FUSE_SNAPSHOT = 468
# msgid:32 inode:32 inode_dst:32 name_dst:NAME uid:32 gid:32 canoverwrite:8
MATOCU_FUSE_SNAPSHOT = 469
# msgid:32 status:8

CUTOMA_FUSE_GETRESERVED = 470
# msgid:32
MATOCU_FUSE_GETRESERVED = 471
# msgid:32 status:8
# msgid:32 N*[ name:NAME inode:32 ]

CUTOMA_FUSE_GETEATTR = 472
# msgid:32 inode:32 gmode:8
MATOCU_FUSE_GETEATTR = 473
# msgid:32 status:8
# msgid:32 eattrdirs:8 eattrfiles:8 eattrdirs*[ eattr:8 dirs:32 ] eattrfiles*[ eattr:8 files:32 ]

CUTOMA_FUSE_SETEATTR = 474
# msgid:32 inode:32 uid:32 eattr:8 smode:8
MATOCU_FUSE_SETEATTR = 475
# msgid:32 status:8
# msgid:32 changed:32 notchanged:32 notpermitted:32

CUTOMA_FUSE_QUOTACONTROL = 476
# msgid:32 inode:32 qflags:8 - delete quota
# msgid:32 inode:32 qflags:8 sinodes:32 slength:64 ssize:64 srealsize:64 hinodes:32 hlength:64 hsize:64 hrealsize:64 - set quota
MATOCU_FUSE_QUOTACONTROL = 477
# msgid:32 status:8
# msgid:32 qflags:8 sinodes:32 slength:64 ssize:64 srealsize:64 hinodes:32 hlength:64 hsize:64 hrealsize:64 curinodes:32 curlength:64 cursize:64 currealsize:64

CUTOMA_FUSE_DIR_REMOVED = 490
# msgid:32 N*[ inode:32 ]

MATOCU_FUSE_NOTIFY_ATTR = 491
# msgid:32 N*[ parent:32 inode:32 attr:35B ]
MATOCU_FUSE_NOTIFY_DIR = 492
# msgid:32 N*[ inode:32 ]
# special - reserved (opened) inodes - keep opened files.
CUTOMA_FUSE_RESERVED_INODES = 499
# N*[inode:32]

errtab = [
    "OK",
    "Operation not permitted",
    "Not a directory",
    "No such file or directory",
    "Permission denied",
    "File exists",
    "Invalid argument",
    "Directory not empty",
    "Chunk lost",
    "Out of memory",
    "Index too big",
    "Chunk locked",
    "No chunk servers",
    "No such chunk",
    "Chunk is busy",
    "Incorrect register BLOB",
    "None of chunk servers performed requested operation",
    "File not opened",
    "Write not started",
    "Wrong chunk version",
    "Chunk already exists",
    "No space left",
    "IO error",
    "Incorrect block number",
    "Incorrect size",
    "Incorrect offset",
    "Can't connect",
    "Incorrect chunk id",
    "Disconnected",
    "CRC error",
    "Operation delayed",
    "Can't create path",
    "Data mismatch",
    "Read-only file system",
    "Quota exceeded",
    "Bad session id",
    "Password is needed",
    "Incorrect password",
    "Unknown MFS error",
]

def mfs_strerror(code):
    if code > ERROR_MAX:
        code = ERROR_MAX
    return errtab[code]

S_IFMT   = 0170000 # type of file */
S_IFIFO  = 0010000 # named pipe (fifo) */
S_IFCHR  = 0020000 # character special */
S_IFDIR  = 0040000 # directory */
S_IFBLK  = 0060000 # block special */
S_IFREG  = 0100000 # regular */
S_IFLNK  = 0120000 # symbolic link */
S_IFSOCK = 0140000 # socket */
S_IFWHT  = 0160000 # whiteout */
S_ISUID  = 0004000 # set user id on execution */
S_ISGID  = 0002000 # set group id on execution */
S_ISVTX  = 0001000 # save swapped text even after use */
S_IRUSR  = 0000400 # read permission, owner */
S_IWUSR  = 0000200 # write permission, owner */
S_IXUSR  = 0000100 # execute/search permission, owner */

########NEW FILE########
__FILENAME__ = cs
import os
import socket
import logging
import commands

from consts import CHUNKSIZE, CUTOCS_READ, CSTOCU_READ_DATA, CSTOCU_READ_STATUS
from utils import uint64, pack, unpack

logger = logging.getLogger(__name__)

mfsdirs = []
def _scan():
    cmd = """ps -eo cmd| grep mfschunkserver | grep -v grep |
    head -1 | cut -d ' ' -f1 | xargs dirname | sed 's#sbin##g'"""
    mfs_prefix = commands.getoutput(cmd)
    mfs_cfg = '%s/etc/mfshdd.cfg' % mfs_prefix
    mfs_cfg_list = (mfs_cfg, '/etc/mfs/mfshdd.cfg',
    '/etc/mfshdd.cfg', '/usr/local/etc/mfshdd.cfg')
    for conf in mfs_cfg_list:
        if not os.path.exists(conf):
            continue
        f = open(conf)
        for line in f:
            path = line.strip('#* \n')
            if os.path.exists(path):
                mfsdirs.append(path)
        f.close()
_scan()

CHUNKHDRSIZE = 1024 * 5

def read_chunk_from_local(chunkid, version, size, offset=0):
    if offset + size > CHUNKSIZE:
        raise ValueError("size too large %s > %s" %
            (size, CHUNKSIZE-offset))

    from dpark.accumulator import LocalReadBytes
    name = '%02X/chunk_%016X_%08X.mfs' % (chunkid & 0xFF, chunkid, version)
    for d in mfsdirs:
        p = os.path.join(d, name)
        if os.path.exists(p):
            if os.path.getsize(p) < CHUNKHDRSIZE + offset + size:
                logger.error('%s is not completed: %d < %d', name,
                        os.path.getsize(p), CHUNKHDRSIZE + offset + size)
                return
                #raise ValueError("size too large")
            f = open(p)
            f.seek(CHUNKHDRSIZE + offset)
            while size > 0:
                to_read = min(size, 640*1024)
                data = f.read(to_read)
                if not data:
                    return
                LocalReadBytes.add(len(data))
                yield data
                size -= len(data)
            f.close()
            return
    else:
        logger.warning("%s was not found", name)


def read_chunk(host, port, chunkid, version, size, offset=0):
    if offset + size > CHUNKSIZE:
        raise ValueError("size too large %s > %s" %
            (size, CHUNKSIZE-offset))

    from dpark.accumulator import RemoteReadBytes

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.settimeout(10)
    conn.connect((host, port))

    msg = pack(CUTOCS_READ, uint64(chunkid), version, offset, size)
    n = conn.send(msg)
    while n < len(msg):
        if not n:
            raise IOError("write failed")
        msg = msg[n:]
        n = conn.send(msg)

    def recv(n):
        d = conn.recv(n)
        while len(d) < n:
            nd = conn.recv(n-len(d))
            if not nd:
                raise IOError("not enough data")
            d += nd
        return d

    while size > 0:
        cmd, l = unpack("II", recv(8))

        if cmd == CSTOCU_READ_STATUS:
            if l != 9:
                raise Exception("readblock: READ_STATUS incorrect message size")
            cid, code = unpack("QB", recv(l))
            if cid != chunkid:
                raise Exception("readblock; READ_STATUS incorrect chunkid")
            conn.close()
            return

        elif cmd == CSTOCU_READ_DATA:
            if l < 20 :
                raise Exception("readblock; READ_DATA incorrect message size")
            cid, bid, boff, bsize, crc = unpack("QHHII", recv(20))
            if cid != chunkid:
                raise Exception("readblock; READ_STATUS incorrect chunkid")
            if l != 20 + bsize:
                raise Exception("readblock; READ_DATA incorrect message size ")
            if bsize == 0 : # FIXME
                raise Exception("readblock; empty block")
                #yield ""
                #continue
            if bid != offset >> 16:
                raise Exception("readblock; READ_DATA incorrect block number")
            if boff != offset & 0xFFFF:
                raise Exception("readblock; READ_DATA incorrect block offset")
            breq = 65536 - boff
            if size < breq:
                breq = size
            if bsize != breq:
                raise Exception("readblock; READ_DATA incorrect block size")

            while breq > 0:
                data = conn.recv(breq)
                if not data:
                    #print chunkid, version, offset, size, bsize, breq
                    raise IOError("unexpected ending: need %d" % breq)
                RemoteReadBytes.add(len(data))
                yield data
                breq -= len(data)

            offset += bsize
            size -= bsize
        else:
            raise Exception("readblock; unknown message: %s" % cmd)
    conn.close()


def test():
    d = list(read_chunk('192.168.11.3', 9422, 6544760, 1, 6, 0))
    print len(d), sum(len(s) for s in d)
    d = list(read_chunk('192.168.11.3', 9422, 6544936, 1, 46039893, 0))
    print len(d), sum(len(s) for s in d)

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = master
import os
import socket
import threading
import Queue
import time
import struct
import logging

from consts import *
from utils import *

logger = logging.getLogger(__name__)

# mfsmaster need to been patched with dcache
ENABLE_DCACHE = False

class StatInfo:
    def __init__(self, totalspace, availspace, trashspace,
                reservedspace, inodes):
        self.totalspace    = totalspace
        self.availspace    = availspace
        self.trashspace    = trashspace
        self.reservedspace = reservedspace
        self.inodes        = inodes

class Chunk:
    def __init__(self, id, length, version, csdata):
        self.id = id
        self.length = length
        self.version = version
        self.addrs = self._parse(csdata)

    def _parse(self, csdata):
        return [(socket.inet_ntoa(csdata[i:i+4]),
                    unpack("H", csdata[i+4:i+6])[0])
                for i in range(len(csdata))[::6]]

    def __repr__(self):
        return "<Chunk(%d, %d, %d)>" % (self.id, self.version, self.length)

def try_again(f):
    def _(self, *a, **kw):
        for i in range(3):
            try:
                return f(self, *a, **kw)
            except IOError, e:
                self.close()
                logger.warning("mfs master connection: %s", e)
                time.sleep(2**i*0.1)
        else:
            raise
    return _

def spawn(target, *args, **kw):
    t = threading.Thread(target=target, name=target.__name__, args=args, kwargs=kw)
    t.daemon = True
    t.start()
    return t

class MasterConn:
    def __init__(self, host='mfsmaster', port=9421):
        self.host = host
        self.port = port
        self.uid = os.getuid()
        self.gid = os.getgid()
        self.sessionid = 0
        self.conn = None
        self.packetid = 0
        self.fail_count = 0
        self.dcache = {}
        self.dstat = {}

        self.lock = threading.RLock()
        self.reply = Queue.Queue()
        self.is_ready = False
        spawn(self.heartbeat)
        spawn(self.recv_thread)

    def heartbeat(self):
        while True:
            try:
                self.nop()
            except Exception, e:
                self.close()
            time.sleep(2)

    def connect(self):
        if self.conn is not None:
            return

        for _ in range(10):
            try:
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.connect((self.host, self.port))
                break
            except socket.error, e:
                self.conn = None
                #self.next_try = time.time() + 1.5 ** self.fail_count
                self.fail_count += 1
                time.sleep(1.5 ** self.fail_count)

        if not self.conn:
            raise IOError("mfsmaster not availbale")

        regbuf = pack(CUTOMA_FUSE_REGISTER, FUSE_REGISTER_BLOB_NOACL,
                      self.sessionid, VERSION)
        self.send(regbuf)
        recv = self.recv(8)
        cmd, i = unpack("II", recv)
        if cmd != MATOCU_FUSE_REGISTER:
            raise Exception("got incorrect answer from mfsmaster %s" % cmd)

        if i not in (1, 4):
            raise Exception("got incorrect size from mfsmaster")

        data = self.recv(i)
        if i == 1:
            code, = unpack("B", data)
            if code != 0:
                raise Exception("mfsmaster register error: "
                        + mfs_strerror(code))
        if self.sessionid == 0:
            self.sessionid, = unpack("I", data)

        self.is_ready = True

    def close(self):
        with self.lock:
            if self.conn:
                self.conn.close()
                self.conn = None
                self.dcache.clear()
                self.is_ready = False

    def send(self, buf):
        with self.lock:
            conn = self.conn
        if not conn:
            raise IOError("not connected")
        n = conn.send(buf)
        while n < len(buf):
            sent = conn.send(buf[n:])
            if not sent:
                self.close()
                raise IOError("write to master failed")
            n += sent

    def nop(self):
        with self.lock:
            self.connect()
            msg = pack(ANTOAN_NOP, 0)
            self.send(msg)

    def recv(self, n):
        with self.lock:
            conn = self.conn
        if not conn:
            raise IOError("not connected")
        r = conn.recv(n)
        while len(r) < n:
            rr = conn.recv(n - len(r))
            if not rr:
                self.close()
                raise IOError("unexpected error: need %d" % (n-len(r)))
            r += rr
        return r

    def recv_cmd(self):
        d = self.recv(12)
        cmd, size = unpack("II", d)
        data = self.recv(size-4) if size > 4 else ''
        while cmd in (ANTOAN_NOP, MATOCU_FUSE_NOTIFY_ATTR, MATOCU_FUSE_NOTIFY_DIR):
            if cmd == ANTOAN_NOP:
                pass
            elif cmd == MATOCU_FUSE_NOTIFY_ATTR:
                while len(data) >= 43:
                    parent, inode = unpack("II", data)
                    attr = data[8:43]
                    if parent in self.dcache:
                        cache = self.dcache[parent]
                        for name in cache:
                            if cache[name].inode == inode:
                                cache[name] = attrToFileInfo(inode, attr)
                                break
                    data = data[43:]
            elif cmd == MATOCU_FUSE_NOTIFY_DIR:
                while len(data) >= 4:
                    inode, = unpack("I", data)
                    if inode in self.dcache:
                        del self.dcache[inode]
                        with self.lock:
                            self.send(pack(CUTOMA_FUSE_DIR_REMOVED, 0, inode))
                    data = data[4:]
            d = self.recv(12)
            cmd, size = unpack("II", d)
            data = self.recv(size-4) if size > 4 else ''
        return d, data

    def recv_thread(self):
        while True:
            with self.lock:
                if not self.is_ready:
                    time.sleep(0.01)
                    continue
            try:
                r = self.recv_cmd()
                self.reply.put(r)
            except IOError, e:
                self.reply.put(e)

    @try_again
    def sendAndReceive(self, cmd, *args):
        #print 'sendAndReceive', cmd, args
        self.packetid += 1
        msg = pack(cmd, self.packetid, *args)
        with self.lock:
            self.connect()
            while not self.reply.empty():
                self.reply.get_nowait()
            self.send(msg)
        r = self.reply.get()
        if isinstance(r, Exception):
            raise r
        h, d = r
        rcmd, size, pid = unpack("III", h)
        if rcmd != cmd+1 or pid != self.packetid or size <= 4:
            self.close()
            raise Exception("incorrect answer (%s!=%s, %s!=%s, %d<=4",
                rcmd, cmd+1, pid, self.packetid, size)
        if len(d) == 1 and ord(d[0]) != 0:
            raise Error(ord(d[0]))
        return d

    def statfs(self):
        ans = self.sendAndReceive(CUTOMA_FUSE_STATFS)
        return StatInfo(*unpack("QQQQI", ans))

#    def access(self, inode, modemask):
#        return self.sendAndReceive(CUTOMA_FUSE_ACCESS, inode,
#            self.uid, self.gid, uint8(modemask))
#
    def lookup(self, parent, name):
        if ENABLE_DCACHE:
            cache = self.dcache.get(parent)
            if cache is None and self.dstat.get(parent, 0) > 1:
                cache = self.getdirplus(parent)
            if cache is not None:
                return cache.get(name), None

            self.dstat[parent] = self.dstat.get(parent, 0) + 1

        ans = self.sendAndReceive(CUTOMA_FUSE_LOOKUP, parent,
                uint8(len(name)), name, 0, 0)
        if len(ans) == 1:
            return None, ""
        if len(ans) != 39:
            raise Exception("bad length")
        inode, = unpack("I", ans)
        return attrToFileInfo(inode, ans[4:]), None

    def getattr(self, inode):
        ans = self.sendAndReceive(CUTOMA_FUSE_GETATTR, inode,
                self.uid, self.gid)
        return attrToFileInfo(inode, ans)

    def readlink(self, inode):
        ans = self.sendAndReceive(CUTOMA_FUSE_READLINK, inode)
        length, = unpack("I", ans)
        if length+4 != len(ans):
            raise Exception("invalid length")
        return ans[4:-1]

    def getdir(self, inode):
        "return: {name: (inode,type)}"
        ans = self.sendAndReceive(CUTOMA_FUSE_GETDIR, inode,
                self.uid, self.gid)
        p = 0
        names = {}
        while p < len(ans):
            length, = unpack("B", ans[p:p+1])
            p += 1
            if length + p + 5 > len(ans):
                break
            name = ans[p:p+length]
            p += length
            inode, type = unpack("IB", ans)
            names[name] = (inode, type)
            p += 5
        return names

    def getdirplus(self, inode):
        "return {name: FileInfo()}"
        if ENABLE_DCACHE:
            infos = self.dcache.get(inode)
            if infos is not None:
                return infos

        flag = GETDIR_FLAG_WITHATTR
        if ENABLE_DCACHE:
            flag |= GETDIR_FLAG_DIRCACHE
        ans = self.sendAndReceive(CUTOMA_FUSE_GETDIR, inode,
                self.uid, self.gid, uint8(flag))
        p = 0
        infos = {}
        while p < len(ans):
            length, = unpack("B", ans[p:p+1])
            p += 1
            name = ans[p:p+length]
            p += length
            i, = unpack("I", ans[p:p+4])
            attr = ans[p+4:p+39]
            infos[name] = attrToFileInfo(i, attr, name)
            p += 39
        if ENABLE_DCACHE:
            self.dcache[inode] = infos
        return infos

    def opencheck(self, inode, flag=1):
        ans = self.sendAndReceive(CUTOMA_FUSE_OPEN, inode,
                self.uid, self.gid, uint8(flag))
        return ans

    def readchunk(self, inode, index):
        ans = self.sendAndReceive(CUTOMA_FUSE_READ_CHUNK, inode, index)
        n = len(ans)
        if n < 20 or (n-20)%6 != 0:
            raise Exception("read chunk: invalid length: %s" % n)
        length, id, version = unpack("QQI", ans)
        return Chunk(id, length, version, ans[20:])


def test():
    m = MasterConn("mfsmaster")
    m.connect()
    m.close()
    #print m.get_attr(1)
    while True:
        print m.getdir(1)
        print m.getdirplus(1)
        time.sleep(60)
    info, err = m.lookup(1, "test.csv")
    print info, err
    #print m.opencheck(info.inode)
    chunks = m.readchunk(info.inode, 0)
    print chunks, chunks.addrs

    for i in range(1000):
        info, err = m.lookup(1, "test.csv")
        chunks = m.readchunk(info.inode, 0)
        print i,err, chunks
        time.sleep(10)

    m.close()

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = utils
import struct

from consts import *

def uint8(n):
    return struct.pack("B", n)

def uint64(n):
    return struct.pack("!Q", n)

class Error(Exception):
    def __init__(self, code):
        self.code = code
    def __str__(self):
        return mfs_strerror(self.code)

def pack(cmd, *args):
    msg = []
    for a in args:
        if isinstance(a, (int,long)):
            msg.append(struct.pack("!I", a))
        elif isinstance(a, str):
            msg.append(a)
        else:
            raise TypeError(str(type(a))+str(a))
    header = struct.pack("!II", cmd, sum(len(i) for i in msg))
    return header + ''.join(msg)

def unpack(fmt, buf):
    if not fmt.startswith("!"):
        fmt = "!" + fmt
    return struct.unpack(fmt, buf[:struct.calcsize(fmt)])

class FileInfo:
    def __init__(self, inode, name, type, mode, uid, gid,
            atime, mtime, ctime, nlink, length):
        self.inode = inode
        self.name = name
        self.type = chr(type)
        if type == TYPE_DIRECTORY:
            mode |= S_IFDIR
        elif type == TYPE_SYMLINK:
            mode |= S_IFLNK
        elif type == TYPE_FILE:
            mode |= S_IFREG
        self.mode = mode
        self.uid = uid
        self.gid = gid
        self.atime = atime
        self.mtime = mtime
        self.ctime = ctime
        self.nlink = nlink
        self.length = length
        self.blocks = (length + 511) / 512

    def __repr__(self):
        return ("FileInfo(%s, inode=%d, type=%s, length=%d)" %
             (self.name, self.inode, self.type, self.length))

    def is_symlink(self):
        return self.type == TYPE_SYMLINK

def attrToFileInfo(inode, attrs, name=''):
    if len(attrs) != 35:
        raise Exception("invalid length of attrs")
    return FileInfo(inode, name, *struct.unpack("!BHIIIIIIQ", attrs))

########NEW FILE########
__FILENAME__ = mutable_dict
import uuid
import os
import cPickle
import urllib
import struct
import glob
import uuid
from dpark.env import env
from dpark.util import compress, decompress
from dpark.tracker import GetValueMessage, AddItemMessage
from dpark.dependency import HashPartitioner
from collections import OrderedDict

class LRUDict(object):
    def __init__(self, limit=None):
        self.limit = limit
        self.value = OrderedDict()

    def get(self, key, default=None):
        result = self.value.pop(key, None)
        if result is not None:
            self.value[key] = result
            return result

        return default

    def put(self, key, value):
        self.value[key] = value
        if self.limit is not None and len(self.value) > self.limit:
            self.value.popitem(last=False)


class ConflictValues(object):
    def __init__(self, v=[]):
        self.value = list(v)

    def __repr__(self):
        return '<ConflictValues %s>' % self.value

class MutableDict(object):
    def __init__(self, partition_num , cacheLimit=None):
        self.uuid = str(uuid.uuid4())
        self.partitioner = HashPartitioner(partition_num)
        self.data = LRUDict(cacheLimit)
        self.cacheLimit = cacheLimit
        self.updated = {}
        self.generation = 1
        self.register(self)
        self.is_local = True

    def __getstate__(self):
        return (self.uuid, self.partitioner, self.generation, self.cacheLimit)

    def __setstate__(self, v):
        self.uuid, self.partitioner, self.generation, self.cacheLimit = v
        self.data = LRUDict(self.cacheLimit)
        self.updated = {}
        self.is_local = False
        self.register(self)

    def get(self, key):
        values = self.updated.get(key)
        if values is not None:
            return values[0]

        _key = self._get_key(key)
        values = self.data.get((_key, key))
        if values is None:
            for k, v in self._fetch_missing(_key).iteritems():
                self.data.put((_key, k), v)

            values = self.data.get((_key, key))

        return values[0] if values is not None else None

    def put(self, key, value):
        if isinstance(value, ConflictValues):
            raise TypeError('Cannot put ConflictValues into mutable_dict')
        if self.is_local:
            raise RuntimeError('Cannot put in local mode')

        self.updated[key] = (value, self.generation)

    def _flush(self):
        if not self.updated:
            return

        updated_keys = {}
        path = self._get_path()
        uri = env.get('SERVER_URI')
        server_uri = '%s/%s' % (uri, os.path.basename(path))

        for k,v in self.updated.items():
            key = self._get_key(k)
            if key in updated_keys:
                updated_keys[key][k] = v
            else:
                updated_keys[key] = {k:v}

        uid = uuid.uuid4().get_hex()
        for key, updated in updated_keys.items():
            new = self._fetch_missing(key)
            for k,v in updated.items():
                if v is None:
                    new.pop(k)
                else:
                    new[k] = v

            filename = '%s_%s_%s' % (key, self.generation, uid)
            fn = os.path.join(path, filename)
            if os.path.exists(fn):
                raise RuntimeError('conflict uuid for mutable_dict')

            url = '%s/%s' % (server_uri, filename)
            with open(fn+'.tmp', 'wb+') as f:
                data = compress(cPickle.dumps(new))
                f.write(struct.pack('<I', len(data)+4) + data)

            os.rename(fn+'.tmp', fn)
            env.trackerClient.call(AddItemMessage('mutable_dict_new:%s' % key, url))

            files = glob.glob(os.path.join(path, '%s-*' % self.uuid ))
            for f in files:
                if int(f.split('_')[-2]) < self.generation -1:
                    try:
                        os.remove(f)
                    except OSError, e:
                        pass

        self.updated.clear()
        self.data = LRUDict(self.cacheLimit)

    def _merge(self):
        locs = env.trackerServer.locs
        new = []
        for k in locs:
            if k.startswith('mutable_dict_new:%s-' % self.uuid):
                new.append(k)

        if not new:
            return

        self.generation += 1
        length = len('mutable_dict_new:')
        for k in new:
            locs['mutable_dict:%s' % k[length:]] = locs.pop(k)

        self.updated.clear()
        self.data = LRUDict(self.cacheLimit)

    def _fetch_missing(self, key):
        result = {}
        urls = env.trackerClient.call(GetValueMessage('mutable_dict:%s' % key))
        for url in urls:
            f = urllib.urlopen(url)
            if f.code is not None and f.code != 200:
                raise IOError('Open %s failed:%s' % (url, f.code))

            data = f.read()
            if len(data) < 4:
                raise IOError('Transfer %s failed: %s received' % (url, len(data)))

            length, = struct.unpack('<I', data[:4])
            if length != len(data):
                raise IOError('Transfer %s failed: %s received, %s expected' % (url,
                    len(data), length))

            data = cPickle.loads(decompress(data[4:]))
            for k,v in data.items():
                if k in result:
                    r = result[k]
                    if v[1] == r[1]:
                        r0 = r[0]
                        v0 = v[0]
                        merged = r0.value if isinstance(r0, ConflictValues) else [r0]
                        merged += v0.value if isinstance(v0, ConflictValues) else [v0]
                        result[k] = (ConflictValues(merged), r[1])
                    else:
                        result[k] = v if v[1] > r[1] else r
                else:
                    result[k] = v

        return result

    def _get_key(self, key):
        return '%s-%s' % (self.uuid,
                self.partitioner.getPartition(key))

    def _get_path(self):
        dirs = env.get('WORKDIR')
        if not dirs:
            raise RuntimeError('No available workdir')

        path = os.path.join(dirs[0], 'mutable_dict')
        if os.path.exists(path):
            return path

        st = os.statvfs(dirs[0])
        ratio = st.f_bfree * 1.0 / st.f_blocks
        if ratio >= 0.66:
            if not os.path.exists(path):
                try:
                    os.makedirs(path)
                except OSError, e:
                    pass

            return path

        for d in dirs[1:]:
            p = os.path.join(d, 'mutable_dict')
            try:
                os.makedirs(p)
                os.symlink(p, path)
            except OSError, e:
                pass

            return path

        raise RuntimeError('Cannot find suitable workdir')

    _all_mutable_dicts = {}
    @classmethod
    def register(cls, md):
        uuid = md.uuid
        _md = cls._all_mutable_dicts.get(uuid)
        if not _md or _md.generation != md.generation:
            cls._all_mutable_dicts[md.uuid] = md
        else:
            md.data = _md.data
            md.updated = _md.updated

    @classmethod
    def flush(cls):
        for md in cls._all_mutable_dicts.values():
            md._flush()

    @classmethod
    def merge(cls):
        for md in cls._all_mutable_dicts.values():
            md._merge()


########NEW FILE########
__FILENAME__ = detector
try:
    from zookeeper import ZooKeeperException as ZookeeperError
    from zkpython import ZKClient, ChildrenWatch, DataWatch
    def adjust_zk_logging_level():
        pass
except ImportError:
    from kazoo.client import KazooClient as ZKClient
    from kazoo.recipe.watchers import ChildrenWatch, DataWatch
    from kazoo.exceptions import ZookeeperError
    def adjust_zk_logging_level():
        import logging
        import kazoo
        kazoo.client.log.setLevel(logging.WARNING)
        kazoo.protocol.connection.log.setLevel(logging.WARNING)

class MasterDetector(object):
    def __init__(self, uri, agent):
        self.uri = uri
        self.agent = agent
        self.zk = ZKClient(uri, 10)
        self.masterSeq = None

    def choose(self, children):
        if not children:
            self.agent.onNoMasterDetectedMessage()
            return True
        masterSeq = min(children)
        if masterSeq == self.masterSeq:
            return True
        self.masterSeq = masterSeq
        DataWatch(self.zk, '/' + masterSeq, self.notify)
        return True

    def notify(self, master_addr, _):
        self.agent.onNewMasterDetectedMessage(master_addr)
        return False

    def start(self):
        adjust_zk_logging_level()
        self.zk.start()
        try:
            ChildrenWatch(self.zk, '', self.choose)
        except ZookeeperError:
            self.agent.onNoMasterDetectedMessage()
            self.stop()

    def stop(self):
        try: self.zk.stop()
        except: pass


def test():
    import logging
    logging.basicConfig()
    class Agent:
        def onNewMasterDetectedMessage(self, addr):
            print 'got', addr
        def onNoMasterDetectedMessage(self):
            print 'no master'
    d = MasterDetector('zk1:2181/mesos_master2', Agent())
    d.start()
    raw_input("press any key to exit:\n")

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = executor
import os, sys
import time

from process import UPID, Process, async

from mesos_pb2 import FrameworkID, ExecutorID
from messages_pb2 import RegisterExecutorMessage, ExecutorToFrameworkMessage, StatusUpdateMessage

class Executor(object):
    #def disconnected(self, driver): pass
    #def error(self, driver, message): pass
    def registered(self, driver, executrInfo, frameworkInfo, slaveInfo): pass
    def launchTask(self, driver, task): pass
    def killTask(self, driver, taskId): pass
    def frameworkMessage(self, driver, message): pass
    def shutdown(self, driver): pass


class ExecutorDriver(object):
    def start(self): pass
    def join(self): pass
    def run(self): pass
    def abort(self): pass
    def stop(self): pass
    def sendStatusUpdate(self, update): pass
    def sendFrameworkMessage(self, data): pass

class MesosExecutorDriver(Process, ExecutorDriver):
    def __init__(self, executor):
        Process.__init__(self, 'executor')
        self.executor = executor

        env = os.environ
        self.local = bool(env.get('MESOS_LOCAL'))
        slave_pid = env.get('MESOS_SLAVE_PID')
        assert slave_pid, 'expecting MESOS_SLAVE_PID in environment'
        self.slave = UPID(slave_pid)
        self.framework_id = FrameworkID()
        self.framework_id.value = env.get('MESOS_FRAMEWORK_ID')
        self.executor_id = ExecutorID()
        self.executor_id.value = env.get('MESOS_EXECUTOR_ID')
        self.workDirectory = env.get('MESOS_DIRECTORY')

    def onExecutorRegisteredMessage(self, executor_info, framework_id,
            framework_info, slave_id, slave_info):
        assert framework_id == self.framework_id
        self.slave_id = slave_id
        return self.executor.registered(self, executor_info, framework_info,
            slave_info)

    def onRunTaskMessage(self, framework_id, framework, pid, task):
        return self.executor.launchTask(self, task)

    def onKillTaskMessage(self, framework_id, task_id):
        return self.executor.killTask(self, task_id)

    def onFrameworkToExecutorMessage(self, slave_id, framework_id,
            executor_id, data):
        return self.executor.frameworkMessage(self, data)

    def onShutdownExecutorMessage(self):
        self.executor.shutdown(self)
        if not self.local:
            sys.exit(0)
        else:
            self.stop()

    def onStatusUpdateAcknowledgementMessage(self, slave_id, framework_id, task_id, uuid):
        pass

    def start(self):
        Process.start(self)
        msg = RegisterExecutorMessage()
        msg.framework_id.MergeFrom(self.framework_id)
        msg.executor_id.MergeFrom(self.executor_id)
        return self.send(self.slave, msg)

    @async
    def sendFrameworkMessage(self, data):
        msg = ExecutorToFrameworkMessage()
        msg.slave_id.MergeFrom(self.slave_id)
        msg.framework_id.MergeFrom(self.framework_id)
        msg.executor_id.MergeFrom(self.executor_id)
        msg.data = data
        return self.send(self.slave, msg)

    @async
    def sendStatusUpdate(self, status):
        msg = StatusUpdateMessage()
        msg.update.framework_id.MergeFrom(self.framework_id)
        msg.update.executor_id.MergeFrom(self.executor_id)
        msg.update.slave_id.MergeFrom(self.slave_id)
        msg.update.status.MergeFrom(status)
        msg.update.timestamp = time.time()
        msg.update.uuid = os.urandom(16)
        return self.send(self.slave, msg)

########NEW FILE########
__FILENAME__ = launcher
import os, sys
import subprocess
import pwd
import logging

logger = logging.getLogger(__name__)

class Launcher(object):
    """
    This class sets up the environment for an executor and then exec()'s it.
    It can either be used after a fork() in the slave process, or run as a
    standalone program (with the main function in launcher_main.cpp).

    The environment is initialized through for steps:
        1) A work directory for the framework is created by createWorkingDirectory().
        2) The executor is fetched off HDFS if necessary by fetchExecutor().
        3) Environment variables are set by setupEnvironment().
        4) We switch to the framework's user in switchUser().

        Isolation modules that wish to override the default behaviour can subclass
        Launcher and override some of the methods to perform extra actions.
    """
    def __init__(self, framework_id, executor_id, commandInfo, user=None, workDirectory='/tmp',
            slavepid=None, redirectIO=False, switch_user=False):
        self.__dict__.update(locals())

    def run(self):
        self.initializeWorkingDirectory()
        os.chdir(self.workDirectory)
        if self.switch_user:
            self.switchUser()
        if self.redirectIO:
            sys.stdout = open('stdout', 'w')
            sys.stderr = open('stderr', 'w')
        command = self.commandInfo.value
        env = self.setupEnvironment()
        p = subprocess.Popen(['/bin/sh', '-c', command], stdout=sys.stdout,
                stderr=sys.stderr, env=env)
        p.wait()

    def setupEnvironment(self):
        env = {}
        for en in self.commandInfo.environment.variables:
            env[en.name] = en.value
        env['MESOS_DIRECTORY'] = self.workDirectory
        env['MESOS_SLAVE_PID'] = str(self.slavepid)
        env['MESOS_FRAMEWORK_ID'] = self.framework_id.value
        env['MESOS_EXECUTOR_ID'] = self.executor_id.value
        env['LIBPROCESS_PORT'] = '0'
        return env

    def initializeWorkingDirectory(self):
        if self.switch_user:
            try:
                os.chown(self.user, self.workDirectory)
            except IOError, e:
                logger.error("failed to chown: %s", e)

    def switchUser(self):
        try:
            pw = pwd.getpwnam(self.user)
            os.setuid(pw.pw_uid)
            os.setgid(pw.pw_gid)
        except OSError, e:
            logger.error("failed to swith to user %s: %s", self.user, e)

def main():
    from mesos_pb2 import FrameworkID, ExecutorID, CommandInfo
    fid = FrameworkID()
    fid.value = os.environ.get('MESOS_FRAMEWORK_ID', 'fid')
    eid = ExecutorID()
    eid.value = os.environ.get('MESOS_EXECUTOR_ID', 'eid')
    info = CommandInfo()
    info.value = os.environ.get('MESOS_COMMAND')
    return Launcher(fid, eid, info).run()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = mesos_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)



DESCRIPTOR = descriptor.FileDescriptor(
  name='mesos.proto',
  package='mesos',
  serialized_pb='\n\x0bmesos.proto\x12\x05mesos\"\x1c\n\x0b\x46rameworkID\x12\r\n\x05value\x18\x01 \x02(\t\"\x18\n\x07OfferID\x12\r\n\x05value\x18\x01 \x02(\t\"\x18\n\x07SlaveID\x12\r\n\x05value\x18\x01 \x02(\t\"\x17\n\x06TaskID\x12\r\n\x05value\x18\x01 \x02(\t\"\x1b\n\nExecutorID\x12\r\n\x05value\x18\x01 \x02(\t\"\x1c\n\x0b\x43ontainerID\x12\r\n\x05value\x18\x01 \x02(\t\"\xa6\x01\n\rFrameworkInfo\x12\x0c\n\x04user\x18\x01 \x02(\t\x12\x0c\n\x04name\x18\x02 \x02(\t\x12\x1e\n\x02id\x18\x03 \x01(\x0b\x32\x12.mesos.FrameworkID\x12\x1b\n\x10\x66\x61ilover_timeout\x18\x04 \x01(\x01:\x01\x30\x12\x19\n\ncheckpoint\x18\x05 \x01(\x08:\x05\x66\x61lse\x12\x0f\n\x04role\x18\x06 \x01(\t:\x01*\x12\x10\n\x08hostname\x18\x07 \x01(\t\"\xd8\x01\n\x0bHealthCheck\x12%\n\x04http\x18\x01 \x01(\x0b\x32\x17.mesos.HealthCheck.HTTP\x12\x19\n\rdelay_seconds\x18\x02 \x01(\x01:\x02\x31\x35\x12\x1c\n\x10interval_seconds\x18\x03 \x01(\x01:\x02\x31\x30\x12\x1b\n\x0ftimeout_seconds\x18\x04 \x01(\x01:\x02\x32\x30\x12\x13\n\x08\x66\x61ilures\x18\x05 \x01(\r:\x01\x33\x1a\x37\n\x04HTTP\x12\x0c\n\x04port\x18\x01 \x02(\r\x12\x0f\n\x04path\x18\x02 \x01(\t:\x01/\x12\x10\n\x08statuses\x18\x04 \x03(\r\"\xca\x02\n\x0b\x43ommandInfo\x12\x33\n\tcontainer\x18\x04 \x01(\x0b\x32 .mesos.CommandInfo.ContainerInfo\x12$\n\x04uris\x18\x01 \x03(\x0b\x32\x16.mesos.CommandInfo.URI\x12\'\n\x0b\x65nvironment\x18\x02 \x01(\x0b\x32\x12.mesos.Environment\x12\r\n\x05value\x18\x03 \x02(\t\x12\x0c\n\x04user\x18\x05 \x01(\t\x12(\n\x0chealth_check\x18\x06 \x01(\x0b\x32\x12.mesos.HealthCheck\x1a?\n\x03URI\x12\r\n\x05value\x18\x01 \x02(\t\x12\x12\n\nexecutable\x18\x02 \x01(\x08\x12\x15\n\x07\x65xtract\x18\x03 \x01(\x08:\x04true\x1a/\n\rContainerInfo\x12\r\n\x05image\x18\x01 \x02(\t\x12\x0f\n\x07options\x18\x02 \x03(\t\"\xd5\x01\n\x0c\x45xecutorInfo\x12&\n\x0b\x65xecutor_id\x18\x01 \x02(\x0b\x32\x11.mesos.ExecutorID\x12(\n\x0c\x66ramework_id\x18\x08 \x01(\x0b\x32\x12.mesos.FrameworkID\x12#\n\x07\x63ommand\x18\x07 \x02(\x0b\x32\x12.mesos.CommandInfo\x12\"\n\tresources\x18\x05 \x03(\x0b\x32\x0f.mesos.Resource\x12\x0c\n\x04name\x18\t \x01(\t\x12\x0e\n\x06source\x18\n \x01(\t\x12\x0c\n\x04\x64\x61ta\x18\x04 \x01(\x0c\"W\n\nMasterInfo\x12\n\n\x02id\x18\x01 \x02(\t\x12\n\n\x02ip\x18\x02 \x02(\r\x12\x12\n\x04port\x18\x03 \x02(\r:\x04\x35\x30\x35\x30\x12\x0b\n\x03pid\x18\x04 \x01(\t\x12\x10\n\x08hostname\x18\x05 \x01(\t\"\xe4\x01\n\tSlaveInfo\x12\x10\n\x08hostname\x18\x01 \x02(\t\x12\x12\n\x04port\x18\x08 \x01(\x05:\x04\x35\x30\x35\x31\x12\"\n\tresources\x18\x03 \x03(\x0b\x32\x0f.mesos.Resource\x12$\n\nattributes\x18\x05 \x03(\x0b\x32\x10.mesos.Attribute\x12\x1a\n\x02id\x18\x06 \x01(\x0b\x32\x0e.mesos.SlaveID\x12\x19\n\ncheckpoint\x18\x07 \x01(\x08:\x05\x66\x61lse\x12\x16\n\x0ewebui_hostname\x18\x02 \x01(\t\x12\x18\n\nwebui_port\x18\x04 \x01(\x05:\x04\x38\x30\x38\x31\"\xfc\x02\n\x05Value\x12\x1f\n\x04type\x18\x01 \x02(\x0e\x32\x11.mesos.Value.Type\x12#\n\x06scalar\x18\x02 \x01(\x0b\x32\x13.mesos.Value.Scalar\x12#\n\x06ranges\x18\x03 \x01(\x0b\x32\x13.mesos.Value.Ranges\x12\x1d\n\x03set\x18\x04 \x01(\x0b\x32\x10.mesos.Value.Set\x12\x1f\n\x04text\x18\x05 \x01(\x0b\x32\x11.mesos.Value.Text\x1a\x17\n\x06Scalar\x12\r\n\x05value\x18\x01 \x02(\x01\x1a#\n\x05Range\x12\r\n\x05\x62\x65gin\x18\x01 \x02(\x04\x12\x0b\n\x03\x65nd\x18\x02 \x02(\x04\x1a+\n\x06Ranges\x12!\n\x05range\x18\x01 \x03(\x0b\x32\x12.mesos.Value.Range\x1a\x13\n\x03Set\x12\x0c\n\x04item\x18\x01 \x03(\t\x1a\x15\n\x04Text\x12\r\n\x05value\x18\x01 \x02(\t\"1\n\x04Type\x12\n\n\x06SCALAR\x10\x00\x12\n\n\x06RANGES\x10\x01\x12\x07\n\x03SET\x10\x02\x12\x08\n\x04TEXT\x10\x03\"\xc4\x01\n\tAttribute\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x1f\n\x04type\x18\x02 \x02(\x0e\x32\x11.mesos.Value.Type\x12#\n\x06scalar\x18\x03 \x01(\x0b\x32\x13.mesos.Value.Scalar\x12#\n\x06ranges\x18\x04 \x01(\x0b\x32\x13.mesos.Value.Ranges\x12\x1d\n\x03set\x18\x06 \x01(\x0b\x32\x10.mesos.Value.Set\x12\x1f\n\x04text\x18\x05 \x01(\x0b\x32\x11.mesos.Value.Text\"\xb3\x01\n\x08Resource\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x1f\n\x04type\x18\x02 \x02(\x0e\x32\x11.mesos.Value.Type\x12#\n\x06scalar\x18\x03 \x01(\x0b\x32\x13.mesos.Value.Scalar\x12#\n\x06ranges\x18\x04 \x01(\x0b\x32\x13.mesos.Value.Ranges\x12\x1d\n\x03set\x18\x05 \x01(\x0b\x32\x10.mesos.Value.Set\x12\x0f\n\x04role\x18\x06 \x01(\t:\x01*\"\xcc\x02\n\x12ResourceStatistics\x12\x11\n\ttimestamp\x18\x01 \x02(\x01\x12\x1b\n\x13\x63pus_user_time_secs\x18\x02 \x01(\x01\x12\x1d\n\x15\x63pus_system_time_secs\x18\x03 \x01(\x01\x12\x12\n\ncpus_limit\x18\x04 \x01(\x01\x12\x17\n\x0f\x63pus_nr_periods\x18\x07 \x01(\r\x12\x19\n\x11\x63pus_nr_throttled\x18\x08 \x01(\r\x12 \n\x18\x63pus_throttled_time_secs\x18\t \x01(\x01\x12\x15\n\rmem_rss_bytes\x18\x05 \x01(\x04\x12\x17\n\x0fmem_limit_bytes\x18\x06 \x01(\x04\x12\x16\n\x0emem_file_bytes\x18\n \x01(\x04\x12\x16\n\x0emem_anon_bytes\x18\x0b \x01(\x04\x12\x1d\n\x15mem_mapped_file_bytes\x18\x0c \x01(\x04\"\xe9\x01\n\rResourceUsage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\x12(\n\x0c\x66ramework_id\x18\x02 \x02(\x0b\x32\x12.mesos.FrameworkID\x12&\n\x0b\x65xecutor_id\x18\x03 \x01(\x0b\x32\x11.mesos.ExecutorID\x12\x15\n\rexecutor_name\x18\x04 \x01(\t\x12\x1e\n\x07task_id\x18\x05 \x01(\x0b\x32\r.mesos.TaskID\x12-\n\nstatistics\x18\x06 \x01(\x0b\x32\x19.mesos.ResourceStatistics\"O\n\x07Request\x12 \n\x08slave_id\x18\x01 \x01(\x0b\x32\x0e.mesos.SlaveID\x12\"\n\tresources\x18\x02 \x03(\x0b\x32\x0f.mesos.Resource\"\xf4\x01\n\x05Offer\x12\x1a\n\x02id\x18\x01 \x02(\x0b\x32\x0e.mesos.OfferID\x12(\n\x0c\x66ramework_id\x18\x02 \x02(\x0b\x32\x12.mesos.FrameworkID\x12 \n\x08slave_id\x18\x03 \x02(\x0b\x32\x0e.mesos.SlaveID\x12\x10\n\x08hostname\x18\x04 \x02(\t\x12\"\n\tresources\x18\x05 \x03(\x0b\x32\x0f.mesos.Resource\x12$\n\nattributes\x18\x07 \x03(\x0b\x32\x10.mesos.Attribute\x12\'\n\x0c\x65xecutor_ids\x18\x06 \x03(\x0b\x32\x11.mesos.ExecutorID\"\xd8\x01\n\x08TaskInfo\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x1e\n\x07task_id\x18\x02 \x02(\x0b\x32\r.mesos.TaskID\x12 \n\x08slave_id\x18\x03 \x02(\x0b\x32\x0e.mesos.SlaveID\x12\"\n\tresources\x18\x04 \x03(\x0b\x32\x0f.mesos.Resource\x12%\n\x08\x65xecutor\x18\x05 \x01(\x0b\x32\x13.mesos.ExecutorInfo\x12#\n\x07\x63ommand\x18\x07 \x01(\x0b\x32\x12.mesos.CommandInfo\x12\x0c\n\x04\x64\x61ta\x18\x06 \x01(\x0c\"\xa1\x01\n\nTaskStatus\x12\x1e\n\x07task_id\x18\x01 \x02(\x0b\x32\r.mesos.TaskID\x12\x1f\n\x05state\x18\x02 \x02(\x0e\x32\x10.mesos.TaskState\x12\x0f\n\x07message\x18\x04 \x01(\t\x12\x0c\n\x04\x64\x61ta\x18\x03 \x01(\x0c\x12 \n\x08slave_id\x18\x05 \x01(\x0b\x32\x0e.mesos.SlaveID\x12\x11\n\ttimestamp\x18\x06 \x01(\x01\"$\n\x07\x46ilters\x12\x19\n\x0erefuse_seconds\x18\x01 \x01(\x01:\x01\x35\"f\n\x0b\x45nvironment\x12.\n\tvariables\x18\x01 \x03(\x0b\x32\x1b.mesos.Environment.Variable\x1a\'\n\x08Variable\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\r\n\x05value\x18\x02 \x02(\t\"\'\n\tParameter\x12\x0b\n\x03key\x18\x01 \x02(\t\x12\r\n\x05value\x18\x02 \x02(\t\"1\n\nParameters\x12#\n\tparameter\x18\x01 \x03(\x0b\x32\x10.mesos.Parameter\"/\n\nCredential\x12\x11\n\tprincipal\x18\x01 \x02(\t\x12\x0e\n\x06secret\x18\x02 \x01(\x0c\"\xd1\x04\n\x03\x41\x43L\x1ai\n\x06\x45ntity\x12*\n\x04type\x18\x01 \x01(\x0e\x32\x16.mesos.ACL.Entity.Type:\x04SOME\x12\x0e\n\x06values\x18\x02 \x03(\t\"#\n\x04Type\x12\x08\n\x04SOME\x10\x00\x12\x07\n\x03\x41NY\x10\x01\x12\x08\n\x04NONE\x10\x02\x1aS\n\x08RunTasks\x12%\n\nprincipals\x18\x01 \x02(\x0b\x32\x11.mesos.ACL.Entity\x12 \n\x05users\x18\x02 \x02(\x0b\x32\x11.mesos.ACL.Entity\x1aX\n\rReceiveOffers\x12%\n\nprincipals\x18\x01 \x02(\x0b\x32\x11.mesos.ACL.Entity\x12 \n\x05roles\x18\x02 \x02(\x0b\x32\x11.mesos.ACL.Entity\x1a\x96\x01\n\x07HTTPGet\x12$\n\tusernames\x18\x01 \x01(\x0b\x32\x11.mesos.ACL.Entity\x12\x1e\n\x03ips\x18\x02 \x01(\x0b\x32\x11.mesos.ACL.Entity\x12$\n\thostnames\x18\x03 \x01(\x0b\x32\x11.mesos.ACL.Entity\x12\x1f\n\x04urls\x18\x04 \x02(\x0b\x32\x11.mesos.ACL.Entity\x1a\x96\x01\n\x07HTTPPut\x12$\n\tusernames\x18\x01 \x01(\x0b\x32\x11.mesos.ACL.Entity\x12\x1e\n\x03ips\x18\x02 \x01(\x0b\x32\x11.mesos.ACL.Entity\x12$\n\thostnames\x18\x03 \x01(\x0b\x32\x11.mesos.ACL.Entity\x12\x1f\n\x04urls\x18\x04 \x02(\x0b\x32\x11.mesos.ACL.Entity\"\xc6\x01\n\x04\x41\x43Ls\x12\x18\n\npermissive\x18\x01 \x02(\x08:\x04true\x12&\n\trun_tasks\x18\x02 \x03(\x0b\x32\x13.mesos.ACL.RunTasks\x12\x30\n\x0ereceive_offers\x18\x03 \x03(\x0b\x32\x18.mesos.ACL.ReceiveOffers\x12$\n\x08http_get\x18\x04 \x03(\x0b\x32\x12.mesos.ACL.HTTPGet\x12$\n\x08http_put\x18\x05 \x03(\x0b\x32\x12.mesos.ACL.HTTPPut*\\\n\x06Status\x12\x16\n\x12\x44RIVER_NOT_STARTED\x10\x01\x12\x12\n\x0e\x44RIVER_RUNNING\x10\x02\x12\x12\n\x0e\x44RIVER_ABORTED\x10\x03\x12\x12\n\x0e\x44RIVER_STOPPED\x10\x04*\x86\x01\n\tTaskState\x12\x10\n\x0cTASK_STAGING\x10\x06\x12\x11\n\rTASK_STARTING\x10\x00\x12\x10\n\x0cTASK_RUNNING\x10\x01\x12\x11\n\rTASK_FINISHED\x10\x02\x12\x0f\n\x0bTASK_FAILED\x10\x03\x12\x0f\n\x0bTASK_KILLED\x10\x04\x12\r\n\tTASK_LOST\x10\x05\x42\x1a\n\x10org.apache.mesosB\x06Protos')

_STATUS = descriptor.EnumDescriptor(
  name='Status',
  full_name='mesos.Status',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='DRIVER_NOT_STARTED', index=0, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='DRIVER_RUNNING', index=1, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='DRIVER_ABORTED', index=2, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='DRIVER_STOPPED', index=3, number=4,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=4571,
  serialized_end=4663,
)


_TASKSTATE = descriptor.EnumDescriptor(
  name='TaskState',
  full_name='mesos.TaskState',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='TASK_STAGING', index=0, number=6,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='TASK_STARTING', index=1, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='TASK_RUNNING', index=2, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='TASK_FINISHED', index=3, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='TASK_FAILED', index=4, number=3,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='TASK_KILLED', index=5, number=4,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='TASK_LOST', index=6, number=5,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=4666,
  serialized_end=4800,
)


DRIVER_NOT_STARTED = 1
DRIVER_RUNNING = 2
DRIVER_ABORTED = 3
DRIVER_STOPPED = 4
TASK_STAGING = 6
TASK_STARTING = 0
TASK_RUNNING = 1
TASK_FINISHED = 2
TASK_FAILED = 3
TASK_KILLED = 4
TASK_LOST = 5


_VALUE_TYPE = descriptor.EnumDescriptor(
  name='Type',
  full_name='mesos.Value.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='SCALAR', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='RANGES', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='SET', index=2, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='TEXT', index=3, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=1777,
  serialized_end=1826,
)

_ACL_ENTITY_TYPE = descriptor.EnumDescriptor(
  name='Type',
  full_name='mesos.ACL.Entity.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='SOME', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ANY', index=1, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='NONE', index=2, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=3852,
  serialized_end=3887,
)


_FRAMEWORKID = descriptor.Descriptor(
  name='FrameworkID',
  full_name='mesos.FrameworkID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.FrameworkID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=22,
  serialized_end=50,
)


_OFFERID = descriptor.Descriptor(
  name='OfferID',
  full_name='mesos.OfferID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.OfferID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=52,
  serialized_end=76,
)


_SLAVEID = descriptor.Descriptor(
  name='SlaveID',
  full_name='mesos.SlaveID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.SlaveID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=78,
  serialized_end=102,
)


_TASKID = descriptor.Descriptor(
  name='TaskID',
  full_name='mesos.TaskID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.TaskID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=104,
  serialized_end=127,
)


_EXECUTORID = descriptor.Descriptor(
  name='ExecutorID',
  full_name='mesos.ExecutorID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.ExecutorID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=129,
  serialized_end=156,
)


_CONTAINERID = descriptor.Descriptor(
  name='ContainerID',
  full_name='mesos.ContainerID',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.ContainerID.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=158,
  serialized_end=186,
)


_FRAMEWORKINFO = descriptor.Descriptor(
  name='FrameworkInfo',
  full_name='mesos.FrameworkInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='user', full_name='mesos.FrameworkInfo.user', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='name', full_name='mesos.FrameworkInfo.name', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='id', full_name='mesos.FrameworkInfo.id', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='failover_timeout', full_name='mesos.FrameworkInfo.failover_timeout', index=3,
      number=4, type=1, cpp_type=5, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='checkpoint', full_name='mesos.FrameworkInfo.checkpoint', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='role', full_name='mesos.FrameworkInfo.role', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=True, default_value=unicode("*", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='hostname', full_name='mesos.FrameworkInfo.hostname', index=6,
      number=7, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=189,
  serialized_end=355,
)


_HEALTHCHECK_HTTP = descriptor.Descriptor(
  name='HTTP',
  full_name='mesos.HealthCheck.HTTP',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='port', full_name='mesos.HealthCheck.HTTP.port', index=0,
      number=1, type=13, cpp_type=3, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='path', full_name='mesos.HealthCheck.HTTP.path', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=True, default_value=unicode("/", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='statuses', full_name='mesos.HealthCheck.HTTP.statuses', index=2,
      number=4, type=13, cpp_type=3, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=519,
  serialized_end=574,
)

_HEALTHCHECK = descriptor.Descriptor(
  name='HealthCheck',
  full_name='mesos.HealthCheck',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='http', full_name='mesos.HealthCheck.http', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='delay_seconds', full_name='mesos.HealthCheck.delay_seconds', index=1,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=True, default_value=15,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='interval_seconds', full_name='mesos.HealthCheck.interval_seconds', index=2,
      number=3, type=1, cpp_type=5, label=1,
      has_default_value=True, default_value=10,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='timeout_seconds', full_name='mesos.HealthCheck.timeout_seconds', index=3,
      number=4, type=1, cpp_type=5, label=1,
      has_default_value=True, default_value=20,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='failures', full_name='mesos.HealthCheck.failures', index=4,
      number=5, type=13, cpp_type=3, label=1,
      has_default_value=True, default_value=3,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_HEALTHCHECK_HTTP, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=358,
  serialized_end=574,
)


_COMMANDINFO_URI = descriptor.Descriptor(
  name='URI',
  full_name='mesos.CommandInfo.URI',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.CommandInfo.URI.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executable', full_name='mesos.CommandInfo.URI.executable', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='extract', full_name='mesos.CommandInfo.URI.extract', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=True,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=795,
  serialized_end=858,
)

_COMMANDINFO_CONTAINERINFO = descriptor.Descriptor(
  name='ContainerInfo',
  full_name='mesos.CommandInfo.ContainerInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='image', full_name='mesos.CommandInfo.ContainerInfo.image', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='options', full_name='mesos.CommandInfo.ContainerInfo.options', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=860,
  serialized_end=907,
)

_COMMANDINFO = descriptor.Descriptor(
  name='CommandInfo',
  full_name='mesos.CommandInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='container', full_name='mesos.CommandInfo.container', index=0,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='uris', full_name='mesos.CommandInfo.uris', index=1,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='environment', full_name='mesos.CommandInfo.environment', index=2,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.CommandInfo.value', index=3,
      number=3, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='user', full_name='mesos.CommandInfo.user', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='health_check', full_name='mesos.CommandInfo.health_check', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_COMMANDINFO_URI, _COMMANDINFO_CONTAINERINFO, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=577,
  serialized_end=907,
)


_EXECUTORINFO = descriptor.Descriptor(
  name='ExecutorInfo',
  full_name='mesos.ExecutorInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='executor_id', full_name='mesos.ExecutorInfo.executor_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.ExecutorInfo.framework_id', index=1,
      number=8, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='command', full_name='mesos.ExecutorInfo.command', index=2,
      number=7, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='resources', full_name='mesos.ExecutorInfo.resources', index=3,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='name', full_name='mesos.ExecutorInfo.name', index=4,
      number=9, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='source', full_name='mesos.ExecutorInfo.source', index=5,
      number=10, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='data', full_name='mesos.ExecutorInfo.data', index=6,
      number=4, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=910,
  serialized_end=1123,
)


_MASTERINFO = descriptor.Descriptor(
  name='MasterInfo',
  full_name='mesos.MasterInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='id', full_name='mesos.MasterInfo.id', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='ip', full_name='mesos.MasterInfo.ip', index=1,
      number=2, type=13, cpp_type=3, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='port', full_name='mesos.MasterInfo.port', index=2,
      number=3, type=13, cpp_type=3, label=2,
      has_default_value=True, default_value=5050,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pid', full_name='mesos.MasterInfo.pid', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='hostname', full_name='mesos.MasterInfo.hostname', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1125,
  serialized_end=1212,
)


_SLAVEINFO = descriptor.Descriptor(
  name='SlaveInfo',
  full_name='mesos.SlaveInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='hostname', full_name='mesos.SlaveInfo.hostname', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='port', full_name='mesos.SlaveInfo.port', index=1,
      number=8, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=5051,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='resources', full_name='mesos.SlaveInfo.resources', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='attributes', full_name='mesos.SlaveInfo.attributes', index=3,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='id', full_name='mesos.SlaveInfo.id', index=4,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='checkpoint', full_name='mesos.SlaveInfo.checkpoint', index=5,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='webui_hostname', full_name='mesos.SlaveInfo.webui_hostname', index=6,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='webui_port', full_name='mesos.SlaveInfo.webui_port', index=7,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=8081,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1215,
  serialized_end=1443,
)


_VALUE_SCALAR = descriptor.Descriptor(
  name='Scalar',
  full_name='mesos.Value.Scalar',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.Value.Scalar.value', index=0,
      number=1, type=1, cpp_type=5, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1626,
  serialized_end=1649,
)

_VALUE_RANGE = descriptor.Descriptor(
  name='Range',
  full_name='mesos.Value.Range',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='begin', full_name='mesos.Value.Range.begin', index=0,
      number=1, type=4, cpp_type=4, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='end', full_name='mesos.Value.Range.end', index=1,
      number=2, type=4, cpp_type=4, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1651,
  serialized_end=1686,
)

_VALUE_RANGES = descriptor.Descriptor(
  name='Ranges',
  full_name='mesos.Value.Ranges',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='range', full_name='mesos.Value.Ranges.range', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1688,
  serialized_end=1731,
)

_VALUE_SET = descriptor.Descriptor(
  name='Set',
  full_name='mesos.Value.Set',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='item', full_name='mesos.Value.Set.item', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1733,
  serialized_end=1752,
)

_VALUE_TEXT = descriptor.Descriptor(
  name='Text',
  full_name='mesos.Value.Text',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.Value.Text.value', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1754,
  serialized_end=1775,
)

_VALUE = descriptor.Descriptor(
  name='Value',
  full_name='mesos.Value',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='type', full_name='mesos.Value.type', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='scalar', full_name='mesos.Value.scalar', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='ranges', full_name='mesos.Value.ranges', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='set', full_name='mesos.Value.set', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='text', full_name='mesos.Value.text', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_VALUE_SCALAR, _VALUE_RANGE, _VALUE_RANGES, _VALUE_SET, _VALUE_TEXT, ],
  enum_types=[
    _VALUE_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1446,
  serialized_end=1826,
)


_ATTRIBUTE = descriptor.Descriptor(
  name='Attribute',
  full_name='mesos.Attribute',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='mesos.Attribute.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='type', full_name='mesos.Attribute.type', index=1,
      number=2, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='scalar', full_name='mesos.Attribute.scalar', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='ranges', full_name='mesos.Attribute.ranges', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='set', full_name='mesos.Attribute.set', index=4,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='text', full_name='mesos.Attribute.text', index=5,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1829,
  serialized_end=2025,
)


_RESOURCE = descriptor.Descriptor(
  name='Resource',
  full_name='mesos.Resource',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='mesos.Resource.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='type', full_name='mesos.Resource.type', index=1,
      number=2, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='scalar', full_name='mesos.Resource.scalar', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='ranges', full_name='mesos.Resource.ranges', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='set', full_name='mesos.Resource.set', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='role', full_name='mesos.Resource.role', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=True, default_value=unicode("*", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2028,
  serialized_end=2207,
)


_RESOURCESTATISTICS = descriptor.Descriptor(
  name='ResourceStatistics',
  full_name='mesos.ResourceStatistics',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='timestamp', full_name='mesos.ResourceStatistics.timestamp', index=0,
      number=1, type=1, cpp_type=5, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='cpus_user_time_secs', full_name='mesos.ResourceStatistics.cpus_user_time_secs', index=1,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='cpus_system_time_secs', full_name='mesos.ResourceStatistics.cpus_system_time_secs', index=2,
      number=3, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='cpus_limit', full_name='mesos.ResourceStatistics.cpus_limit', index=3,
      number=4, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='cpus_nr_periods', full_name='mesos.ResourceStatistics.cpus_nr_periods', index=4,
      number=7, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='cpus_nr_throttled', full_name='mesos.ResourceStatistics.cpus_nr_throttled', index=5,
      number=8, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='cpus_throttled_time_secs', full_name='mesos.ResourceStatistics.cpus_throttled_time_secs', index=6,
      number=9, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='mem_rss_bytes', full_name='mesos.ResourceStatistics.mem_rss_bytes', index=7,
      number=5, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='mem_limit_bytes', full_name='mesos.ResourceStatistics.mem_limit_bytes', index=8,
      number=6, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='mem_file_bytes', full_name='mesos.ResourceStatistics.mem_file_bytes', index=9,
      number=10, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='mem_anon_bytes', full_name='mesos.ResourceStatistics.mem_anon_bytes', index=10,
      number=11, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='mem_mapped_file_bytes', full_name='mesos.ResourceStatistics.mem_mapped_file_bytes', index=11,
      number=12, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2210,
  serialized_end=2542,
)


_RESOURCEUSAGE = descriptor.Descriptor(
  name='ResourceUsage',
  full_name='mesos.ResourceUsage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.ResourceUsage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.ResourceUsage.framework_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executor_id', full_name='mesos.ResourceUsage.executor_id', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executor_name', full_name='mesos.ResourceUsage.executor_name', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='task_id', full_name='mesos.ResourceUsage.task_id', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='statistics', full_name='mesos.ResourceUsage.statistics', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2545,
  serialized_end=2778,
)


_REQUEST = descriptor.Descriptor(
  name='Request',
  full_name='mesos.Request',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.Request.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='resources', full_name='mesos.Request.resources', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2780,
  serialized_end=2859,
)


_OFFER = descriptor.Descriptor(
  name='Offer',
  full_name='mesos.Offer',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='id', full_name='mesos.Offer.id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.Offer.framework_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.Offer.slave_id', index=2,
      number=3, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='hostname', full_name='mesos.Offer.hostname', index=3,
      number=4, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='resources', full_name='mesos.Offer.resources', index=4,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='attributes', full_name='mesos.Offer.attributes', index=5,
      number=7, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executor_ids', full_name='mesos.Offer.executor_ids', index=6,
      number=6, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2862,
  serialized_end=3106,
)


_TASKINFO = descriptor.Descriptor(
  name='TaskInfo',
  full_name='mesos.TaskInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='mesos.TaskInfo.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='task_id', full_name='mesos.TaskInfo.task_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.TaskInfo.slave_id', index=2,
      number=3, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='resources', full_name='mesos.TaskInfo.resources', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executor', full_name='mesos.TaskInfo.executor', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='command', full_name='mesos.TaskInfo.command', index=5,
      number=7, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='data', full_name='mesos.TaskInfo.data', index=6,
      number=6, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3109,
  serialized_end=3325,
)


_TASKSTATUS = descriptor.Descriptor(
  name='TaskStatus',
  full_name='mesos.TaskStatus',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='task_id', full_name='mesos.TaskStatus.task_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='state', full_name='mesos.TaskStatus.state', index=1,
      number=2, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=6,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='message', full_name='mesos.TaskStatus.message', index=2,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='data', full_name='mesos.TaskStatus.data', index=3,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.TaskStatus.slave_id', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='timestamp', full_name='mesos.TaskStatus.timestamp', index=5,
      number=6, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3328,
  serialized_end=3489,
)


_FILTERS = descriptor.Descriptor(
  name='Filters',
  full_name='mesos.Filters',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='refuse_seconds', full_name='mesos.Filters.refuse_seconds', index=0,
      number=1, type=1, cpp_type=5, label=1,
      has_default_value=True, default_value=5,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3491,
  serialized_end=3527,
)


_ENVIRONMENT_VARIABLE = descriptor.Descriptor(
  name='Variable',
  full_name='mesos.Environment.Variable',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='mesos.Environment.Variable.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.Environment.Variable.value', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3592,
  serialized_end=3631,
)

_ENVIRONMENT = descriptor.Descriptor(
  name='Environment',
  full_name='mesos.Environment',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='variables', full_name='mesos.Environment.variables', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_ENVIRONMENT_VARIABLE, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3529,
  serialized_end=3631,
)


_PARAMETER = descriptor.Descriptor(
  name='Parameter',
  full_name='mesos.Parameter',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='key', full_name='mesos.Parameter.key', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='value', full_name='mesos.Parameter.value', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3633,
  serialized_end=3672,
)


_PARAMETERS = descriptor.Descriptor(
  name='Parameters',
  full_name='mesos.Parameters',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='parameter', full_name='mesos.Parameters.parameter', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3674,
  serialized_end=3723,
)


_CREDENTIAL = descriptor.Descriptor(
  name='Credential',
  full_name='mesos.Credential',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='principal', full_name='mesos.Credential.principal', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='secret', full_name='mesos.Credential.secret', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3725,
  serialized_end=3772,
)


_ACL_ENTITY = descriptor.Descriptor(
  name='Entity',
  full_name='mesos.ACL.Entity',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='type', full_name='mesos.ACL.Entity.type', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='values', full_name='mesos.ACL.Entity.values', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _ACL_ENTITY_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3782,
  serialized_end=3887,
)

_ACL_RUNTASKS = descriptor.Descriptor(
  name='RunTasks',
  full_name='mesos.ACL.RunTasks',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='principals', full_name='mesos.ACL.RunTasks.principals', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='users', full_name='mesos.ACL.RunTasks.users', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3889,
  serialized_end=3972,
)

_ACL_RECEIVEOFFERS = descriptor.Descriptor(
  name='ReceiveOffers',
  full_name='mesos.ACL.ReceiveOffers',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='principals', full_name='mesos.ACL.ReceiveOffers.principals', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='roles', full_name='mesos.ACL.ReceiveOffers.roles', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3974,
  serialized_end=4062,
)

_ACL_HTTPGET = descriptor.Descriptor(
  name='HTTPGet',
  full_name='mesos.ACL.HTTPGet',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='usernames', full_name='mesos.ACL.HTTPGet.usernames', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='ips', full_name='mesos.ACL.HTTPGet.ips', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='hostnames', full_name='mesos.ACL.HTTPGet.hostnames', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='urls', full_name='mesos.ACL.HTTPGet.urls', index=3,
      number=4, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4065,
  serialized_end=4215,
)

_ACL_HTTPPUT = descriptor.Descriptor(
  name='HTTPPut',
  full_name='mesos.ACL.HTTPPut',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='usernames', full_name='mesos.ACL.HTTPPut.usernames', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='ips', full_name='mesos.ACL.HTTPPut.ips', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='hostnames', full_name='mesos.ACL.HTTPPut.hostnames', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='urls', full_name='mesos.ACL.HTTPPut.urls', index=3,
      number=4, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4218,
  serialized_end=4368,
)

_ACL = descriptor.Descriptor(
  name='ACL',
  full_name='mesos.ACL',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[_ACL_ENTITY, _ACL_RUNTASKS, _ACL_RECEIVEOFFERS, _ACL_HTTPGET, _ACL_HTTPPUT, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3775,
  serialized_end=4368,
)


_ACLS = descriptor.Descriptor(
  name='ACLs',
  full_name='mesos.ACLs',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='permissive', full_name='mesos.ACLs.permissive', index=0,
      number=1, type=8, cpp_type=7, label=2,
      has_default_value=True, default_value=True,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='run_tasks', full_name='mesos.ACLs.run_tasks', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='receive_offers', full_name='mesos.ACLs.receive_offers', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='http_get', full_name='mesos.ACLs.http_get', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='http_put', full_name='mesos.ACLs.http_put', index=4,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4371,
  serialized_end=4569,
)

_FRAMEWORKINFO.fields_by_name['id'].message_type = _FRAMEWORKID
_HEALTHCHECK_HTTP.containing_type = _HEALTHCHECK;
_HEALTHCHECK.fields_by_name['http'].message_type = _HEALTHCHECK_HTTP
_COMMANDINFO_URI.containing_type = _COMMANDINFO;
_COMMANDINFO_CONTAINERINFO.containing_type = _COMMANDINFO;
_COMMANDINFO.fields_by_name['container'].message_type = _COMMANDINFO_CONTAINERINFO
_COMMANDINFO.fields_by_name['uris'].message_type = _COMMANDINFO_URI
_COMMANDINFO.fields_by_name['environment'].message_type = _ENVIRONMENT
_COMMANDINFO.fields_by_name['health_check'].message_type = _HEALTHCHECK
_EXECUTORINFO.fields_by_name['executor_id'].message_type = _EXECUTORID
_EXECUTORINFO.fields_by_name['framework_id'].message_type = _FRAMEWORKID
_EXECUTORINFO.fields_by_name['command'].message_type = _COMMANDINFO
_EXECUTORINFO.fields_by_name['resources'].message_type = _RESOURCE
_SLAVEINFO.fields_by_name['resources'].message_type = _RESOURCE
_SLAVEINFO.fields_by_name['attributes'].message_type = _ATTRIBUTE
_SLAVEINFO.fields_by_name['id'].message_type = _SLAVEID
_VALUE_SCALAR.containing_type = _VALUE;
_VALUE_RANGE.containing_type = _VALUE;
_VALUE_RANGES.fields_by_name['range'].message_type = _VALUE_RANGE
_VALUE_RANGES.containing_type = _VALUE;
_VALUE_SET.containing_type = _VALUE;
_VALUE_TEXT.containing_type = _VALUE;
_VALUE.fields_by_name['type'].enum_type = _VALUE_TYPE
_VALUE.fields_by_name['scalar'].message_type = _VALUE_SCALAR
_VALUE.fields_by_name['ranges'].message_type = _VALUE_RANGES
_VALUE.fields_by_name['set'].message_type = _VALUE_SET
_VALUE.fields_by_name['text'].message_type = _VALUE_TEXT
_VALUE_TYPE.containing_type = _VALUE;
_ATTRIBUTE.fields_by_name['type'].enum_type = _VALUE_TYPE
_ATTRIBUTE.fields_by_name['scalar'].message_type = _VALUE_SCALAR
_ATTRIBUTE.fields_by_name['ranges'].message_type = _VALUE_RANGES
_ATTRIBUTE.fields_by_name['set'].message_type = _VALUE_SET
_ATTRIBUTE.fields_by_name['text'].message_type = _VALUE_TEXT
_RESOURCE.fields_by_name['type'].enum_type = _VALUE_TYPE
_RESOURCE.fields_by_name['scalar'].message_type = _VALUE_SCALAR
_RESOURCE.fields_by_name['ranges'].message_type = _VALUE_RANGES
_RESOURCE.fields_by_name['set'].message_type = _VALUE_SET
_RESOURCEUSAGE.fields_by_name['slave_id'].message_type = _SLAVEID
_RESOURCEUSAGE.fields_by_name['framework_id'].message_type = _FRAMEWORKID
_RESOURCEUSAGE.fields_by_name['executor_id'].message_type = _EXECUTORID
_RESOURCEUSAGE.fields_by_name['task_id'].message_type = _TASKID
_RESOURCEUSAGE.fields_by_name['statistics'].message_type = _RESOURCESTATISTICS
_REQUEST.fields_by_name['slave_id'].message_type = _SLAVEID
_REQUEST.fields_by_name['resources'].message_type = _RESOURCE
_OFFER.fields_by_name['id'].message_type = _OFFERID
_OFFER.fields_by_name['framework_id'].message_type = _FRAMEWORKID
_OFFER.fields_by_name['slave_id'].message_type = _SLAVEID
_OFFER.fields_by_name['resources'].message_type = _RESOURCE
_OFFER.fields_by_name['attributes'].message_type = _ATTRIBUTE
_OFFER.fields_by_name['executor_ids'].message_type = _EXECUTORID
_TASKINFO.fields_by_name['task_id'].message_type = _TASKID
_TASKINFO.fields_by_name['slave_id'].message_type = _SLAVEID
_TASKINFO.fields_by_name['resources'].message_type = _RESOURCE
_TASKINFO.fields_by_name['executor'].message_type = _EXECUTORINFO
_TASKINFO.fields_by_name['command'].message_type = _COMMANDINFO
_TASKSTATUS.fields_by_name['task_id'].message_type = _TASKID
_TASKSTATUS.fields_by_name['state'].enum_type = _TASKSTATE
_TASKSTATUS.fields_by_name['slave_id'].message_type = _SLAVEID
_ENVIRONMENT_VARIABLE.containing_type = _ENVIRONMENT;
_ENVIRONMENT.fields_by_name['variables'].message_type = _ENVIRONMENT_VARIABLE
_PARAMETERS.fields_by_name['parameter'].message_type = _PARAMETER
_ACL_ENTITY.fields_by_name['type'].enum_type = _ACL_ENTITY_TYPE
_ACL_ENTITY.containing_type = _ACL;
_ACL_ENTITY_TYPE.containing_type = _ACL_ENTITY;
_ACL_RUNTASKS.fields_by_name['principals'].message_type = _ACL_ENTITY
_ACL_RUNTASKS.fields_by_name['users'].message_type = _ACL_ENTITY
_ACL_RUNTASKS.containing_type = _ACL;
_ACL_RECEIVEOFFERS.fields_by_name['principals'].message_type = _ACL_ENTITY
_ACL_RECEIVEOFFERS.fields_by_name['roles'].message_type = _ACL_ENTITY
_ACL_RECEIVEOFFERS.containing_type = _ACL;
_ACL_HTTPGET.fields_by_name['usernames'].message_type = _ACL_ENTITY
_ACL_HTTPGET.fields_by_name['ips'].message_type = _ACL_ENTITY
_ACL_HTTPGET.fields_by_name['hostnames'].message_type = _ACL_ENTITY
_ACL_HTTPGET.fields_by_name['urls'].message_type = _ACL_ENTITY
_ACL_HTTPGET.containing_type = _ACL;
_ACL_HTTPPUT.fields_by_name['usernames'].message_type = _ACL_ENTITY
_ACL_HTTPPUT.fields_by_name['ips'].message_type = _ACL_ENTITY
_ACL_HTTPPUT.fields_by_name['hostnames'].message_type = _ACL_ENTITY
_ACL_HTTPPUT.fields_by_name['urls'].message_type = _ACL_ENTITY
_ACL_HTTPPUT.containing_type = _ACL;
_ACLS.fields_by_name['run_tasks'].message_type = _ACL_RUNTASKS
_ACLS.fields_by_name['receive_offers'].message_type = _ACL_RECEIVEOFFERS
_ACLS.fields_by_name['http_get'].message_type = _ACL_HTTPGET
_ACLS.fields_by_name['http_put'].message_type = _ACL_HTTPPUT
DESCRIPTOR.message_types_by_name['FrameworkID'] = _FRAMEWORKID
DESCRIPTOR.message_types_by_name['OfferID'] = _OFFERID
DESCRIPTOR.message_types_by_name['SlaveID'] = _SLAVEID
DESCRIPTOR.message_types_by_name['TaskID'] = _TASKID
DESCRIPTOR.message_types_by_name['ExecutorID'] = _EXECUTORID
DESCRIPTOR.message_types_by_name['ContainerID'] = _CONTAINERID
DESCRIPTOR.message_types_by_name['FrameworkInfo'] = _FRAMEWORKINFO
DESCRIPTOR.message_types_by_name['HealthCheck'] = _HEALTHCHECK
DESCRIPTOR.message_types_by_name['CommandInfo'] = _COMMANDINFO
DESCRIPTOR.message_types_by_name['ExecutorInfo'] = _EXECUTORINFO
DESCRIPTOR.message_types_by_name['MasterInfo'] = _MASTERINFO
DESCRIPTOR.message_types_by_name['SlaveInfo'] = _SLAVEINFO
DESCRIPTOR.message_types_by_name['Value'] = _VALUE
DESCRIPTOR.message_types_by_name['Attribute'] = _ATTRIBUTE
DESCRIPTOR.message_types_by_name['Resource'] = _RESOURCE
DESCRIPTOR.message_types_by_name['ResourceStatistics'] = _RESOURCESTATISTICS
DESCRIPTOR.message_types_by_name['ResourceUsage'] = _RESOURCEUSAGE
DESCRIPTOR.message_types_by_name['Request'] = _REQUEST
DESCRIPTOR.message_types_by_name['Offer'] = _OFFER
DESCRIPTOR.message_types_by_name['TaskInfo'] = _TASKINFO
DESCRIPTOR.message_types_by_name['TaskStatus'] = _TASKSTATUS
DESCRIPTOR.message_types_by_name['Filters'] = _FILTERS
DESCRIPTOR.message_types_by_name['Environment'] = _ENVIRONMENT
DESCRIPTOR.message_types_by_name['Parameter'] = _PARAMETER
DESCRIPTOR.message_types_by_name['Parameters'] = _PARAMETERS
DESCRIPTOR.message_types_by_name['Credential'] = _CREDENTIAL
DESCRIPTOR.message_types_by_name['ACL'] = _ACL
DESCRIPTOR.message_types_by_name['ACLs'] = _ACLS

class FrameworkID(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _FRAMEWORKID

  # @@protoc_insertion_point(class_scope:mesos.FrameworkID)

class OfferID(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _OFFERID

  # @@protoc_insertion_point(class_scope:mesos.OfferID)

class SlaveID(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SLAVEID

  # @@protoc_insertion_point(class_scope:mesos.SlaveID)

class TaskID(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _TASKID

  # @@protoc_insertion_point(class_scope:mesos.TaskID)

class ExecutorID(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EXECUTORID

  # @@protoc_insertion_point(class_scope:mesos.ExecutorID)

class ContainerID(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CONTAINERID

  # @@protoc_insertion_point(class_scope:mesos.ContainerID)

class FrameworkInfo(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _FRAMEWORKINFO

  # @@protoc_insertion_point(class_scope:mesos.FrameworkInfo)

class HealthCheck(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType

  class HTTP(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _HEALTHCHECK_HTTP

    # @@protoc_insertion_point(class_scope:mesos.HealthCheck.HTTP)
  DESCRIPTOR = _HEALTHCHECK

  # @@protoc_insertion_point(class_scope:mesos.HealthCheck)

class CommandInfo(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType

  class URI(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _COMMANDINFO_URI

    # @@protoc_insertion_point(class_scope:mesos.CommandInfo.URI)

  class ContainerInfo(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _COMMANDINFO_CONTAINERINFO

    # @@protoc_insertion_point(class_scope:mesos.CommandInfo.ContainerInfo)
  DESCRIPTOR = _COMMANDINFO

  # @@protoc_insertion_point(class_scope:mesos.CommandInfo)

class ExecutorInfo(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EXECUTORINFO

  # @@protoc_insertion_point(class_scope:mesos.ExecutorInfo)

class MasterInfo(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _MASTERINFO

  # @@protoc_insertion_point(class_scope:mesos.MasterInfo)

class SlaveInfo(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SLAVEINFO

  # @@protoc_insertion_point(class_scope:mesos.SlaveInfo)

class Value(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType

  class Scalar(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _VALUE_SCALAR

    # @@protoc_insertion_point(class_scope:mesos.Value.Scalar)

  class Range(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _VALUE_RANGE

    # @@protoc_insertion_point(class_scope:mesos.Value.Range)

  class Ranges(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _VALUE_RANGES

    # @@protoc_insertion_point(class_scope:mesos.Value.Ranges)

  class Set(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _VALUE_SET

    # @@protoc_insertion_point(class_scope:mesos.Value.Set)

  class Text(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _VALUE_TEXT

    # @@protoc_insertion_point(class_scope:mesos.Value.Text)
  DESCRIPTOR = _VALUE

  # @@protoc_insertion_point(class_scope:mesos.Value)

class Attribute(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ATTRIBUTE

  # @@protoc_insertion_point(class_scope:mesos.Attribute)

class Resource(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESOURCE

  # @@protoc_insertion_point(class_scope:mesos.Resource)

class ResourceStatistics(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESOURCESTATISTICS

  # @@protoc_insertion_point(class_scope:mesos.ResourceStatistics)

class ResourceUsage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESOURCEUSAGE

  # @@protoc_insertion_point(class_scope:mesos.ResourceUsage)

class Request(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REQUEST

  # @@protoc_insertion_point(class_scope:mesos.Request)

class Offer(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _OFFER

  # @@protoc_insertion_point(class_scope:mesos.Offer)

class TaskInfo(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _TASKINFO

  # @@protoc_insertion_point(class_scope:mesos.TaskInfo)

class TaskStatus(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _TASKSTATUS

  # @@protoc_insertion_point(class_scope:mesos.TaskStatus)

class Filters(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _FILTERS

  # @@protoc_insertion_point(class_scope:mesos.Filters)

class Environment(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType

  class Variable(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _ENVIRONMENT_VARIABLE

    # @@protoc_insertion_point(class_scope:mesos.Environment.Variable)
  DESCRIPTOR = _ENVIRONMENT

  # @@protoc_insertion_point(class_scope:mesos.Environment)

class Parameter(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _PARAMETER

  # @@protoc_insertion_point(class_scope:mesos.Parameter)

class Parameters(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _PARAMETERS

  # @@protoc_insertion_point(class_scope:mesos.Parameters)

class Credential(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CREDENTIAL

  # @@protoc_insertion_point(class_scope:mesos.Credential)

class ACL(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType

  class Entity(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _ACL_ENTITY

    # @@protoc_insertion_point(class_scope:mesos.ACL.Entity)

  class RunTasks(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _ACL_RUNTASKS

    # @@protoc_insertion_point(class_scope:mesos.ACL.RunTasks)

  class ReceiveOffers(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _ACL_RECEIVEOFFERS

    # @@protoc_insertion_point(class_scope:mesos.ACL.ReceiveOffers)

  class HTTPGet(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _ACL_HTTPGET

    # @@protoc_insertion_point(class_scope:mesos.ACL.HTTPGet)

  class HTTPPut(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _ACL_HTTPPUT

    # @@protoc_insertion_point(class_scope:mesos.ACL.HTTPPut)
  DESCRIPTOR = _ACL

  # @@protoc_insertion_point(class_scope:mesos.ACL)

class ACLs(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ACLS

  # @@protoc_insertion_point(class_scope:mesos.ACLs)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = messages_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import mesos_pb2

DESCRIPTOR = descriptor.FileDescriptor(
  name='messages.proto',
  package='mesos.internal',
  serialized_pb='\n\x0emessages.proto\x12\x0emesos.internal\x1a\x0bmesos.proto\"\x92\x02\n\x04Task\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x1e\n\x07task_id\x18\x02 \x02(\x0b\x32\r.mesos.TaskID\x12(\n\x0c\x66ramework_id\x18\x03 \x02(\x0b\x32\x12.mesos.FrameworkID\x12&\n\x0b\x65xecutor_id\x18\x04 \x01(\x0b\x32\x11.mesos.ExecutorID\x12 \n\x08slave_id\x18\x05 \x02(\x0b\x32\x0e.mesos.SlaveID\x12\x1f\n\x05state\x18\x06 \x02(\x0e\x32\x10.mesos.TaskState\x12\"\n\tresources\x18\x07 \x03(\x0b\x32\x0f.mesos.Resource\x12#\n\x08statuses\x18\x08 \x03(\x0b\x32\x11.mesos.TaskStatus\"+\n\x08RoleInfo\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x11\n\x06weight\x18\x02 \x01(\x01:\x01\x31\"\xc6\x01\n\x0cStatusUpdate\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\x12&\n\x0b\x65xecutor_id\x18\x02 \x01(\x0b\x32\x11.mesos.ExecutorID\x12 \n\x08slave_id\x18\x03 \x01(\x0b\x32\x0e.mesos.SlaveID\x12!\n\x06status\x18\x04 \x02(\x0b\x32\x11.mesos.TaskStatus\x12\x11\n\ttimestamp\x18\x05 \x02(\x01\x12\x0c\n\x04uuid\x18\x06 \x02(\x0c\"\xa4\x01\n\x12StatusUpdateRecord\x12\x35\n\x04type\x18\x01 \x02(\x0e\x32\'.mesos.internal.StatusUpdateRecord.Type\x12,\n\x06update\x18\x02 \x01(\x0b\x32\x1c.mesos.internal.StatusUpdate\x12\x0c\n\x04uuid\x18\x03 \x01(\x0c\"\x1b\n\x04Type\x12\n\n\x06UPDATE\x10\x00\x12\x07\n\x03\x41\x43K\x10\x01\"&\n\x16SubmitSchedulerRequest\x12\x0c\n\x04name\x18\x01 \x02(\t\"\'\n\x17SubmitSchedulerResponse\x12\x0c\n\x04okay\x18\x01 \x02(\x08\"\x9e\x01\n\x1a\x45xecutorToFrameworkMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\x12(\n\x0c\x66ramework_id\x18\x02 \x02(\x0b\x32\x12.mesos.FrameworkID\x12&\n\x0b\x65xecutor_id\x18\x03 \x02(\x0b\x32\x11.mesos.ExecutorID\x12\x0c\n\x04\x64\x61ta\x18\x04 \x02(\x0c\"\x9e\x01\n\x1a\x46rameworkToExecutorMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\x12(\n\x0c\x66ramework_id\x18\x02 \x02(\x0b\x32\x12.mesos.FrameworkID\x12&\n\x0b\x65xecutor_id\x18\x03 \x02(\x0b\x32\x11.mesos.ExecutorID\x12\x0c\n\x04\x64\x61ta\x18\x04 \x02(\x0c\"C\n\x18RegisterFrameworkMessage\x12\'\n\tframework\x18\x01 \x02(\x0b\x32\x14.mesos.FrameworkInfo\"W\n\x1aReregisterFrameworkMessage\x12\'\n\tframework\x18\x02 \x02(\x0b\x32\x14.mesos.FrameworkInfo\x12\x10\n\x08\x66\x61ilover\x18\x03 \x02(\x08\"n\n\x1a\x46rameworkRegisteredMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\x12&\n\x0bmaster_info\x18\x02 \x02(\x0b\x32\x11.mesos.MasterInfo\"p\n\x1c\x46rameworkReregisteredMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\x12&\n\x0bmaster_info\x18\x02 \x02(\x0b\x32\x11.mesos.MasterInfo\"F\n\x1aUnregisterFrameworkMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\"F\n\x1a\x44\x65\x61\x63tivateFrameworkMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\"d\n\x16ResourceRequestMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\x12 \n\x08requests\x18\x02 \x03(\x0b\x32\x0e.mesos.Request\"C\n\x15ResourceOffersMessage\x12\x1c\n\x06offers\x18\x01 \x03(\x0b\x32\x0c.mesos.Offer\x12\x0c\n\x04pids\x18\x02 \x03(\t\"\xc4\x01\n\x12LaunchTasksMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\x12 \n\x08offer_id\x18\x02 \x01(\x0b\x32\x0e.mesos.OfferID\x12\x1e\n\x05tasks\x18\x03 \x03(\x0b\x32\x0f.mesos.TaskInfo\x12\x1f\n\x07\x66ilters\x18\x05 \x02(\x0b\x32\x0e.mesos.Filters\x12!\n\toffer_ids\x18\x06 \x03(\x0b\x32\x0e.mesos.OfferID\"?\n\x1bRescindResourceOfferMessage\x12 \n\x08offer_id\x18\x01 \x02(\x0b\x32\x0e.mesos.OfferID\"?\n\x13ReviveOffersMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\"\x8f\x01\n\x0eRunTaskMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\x12\'\n\tframework\x18\x02 \x02(\x0b\x32\x14.mesos.FrameworkInfo\x12\x0b\n\x03pid\x18\x03 \x02(\t\x12\x1d\n\x04task\x18\x04 \x02(\x0b\x32\x0f.mesos.TaskInfo\"[\n\x0fKillTaskMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\x12\x1e\n\x07task_id\x18\x02 \x02(\x0b\x32\r.mesos.TaskID\"P\n\x13StatusUpdateMessage\x12,\n\x06update\x18\x01 \x02(\x0b\x32\x1c.mesos.internal.StatusUpdate\x12\x0b\n\x03pid\x18\x02 \x01(\t\"\x9e\x01\n\"StatusUpdateAcknowledgementMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\x12(\n\x0c\x66ramework_id\x18\x02 \x02(\x0b\x32\x12.mesos.FrameworkID\x12\x1e\n\x07task_id\x18\x03 \x02(\x0b\x32\r.mesos.TaskID\x12\x0c\n\x04uuid\x18\x04 \x02(\x0c\"4\n\x10LostSlaveMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\"f\n\x15ReconcileTasksMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\x12#\n\x08statuses\x18\x02 \x03(\x0b\x32\x11.mesos.TaskStatus\"(\n\x15\x46rameworkErrorMessage\x12\x0f\n\x07message\x18\x02 \x02(\t\"7\n\x14RegisterSlaveMessage\x12\x1f\n\x05slave\x18\x01 \x02(\x0b\x32\x10.mesos.SlaveInfo\"\xee\x01\n\x16ReregisterSlaveMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\x12\x1f\n\x05slave\x18\x02 \x02(\x0b\x32\x10.mesos.SlaveInfo\x12+\n\x0e\x65xecutor_infos\x18\x04 \x03(\x0b\x32\x13.mesos.ExecutorInfo\x12#\n\x05tasks\x18\x03 \x03(\x0b\x32\x14.mesos.internal.Task\x12?\n\x14\x63ompleted_frameworks\x18\x05 \x03(\x0b\x32!.mesos.internal.Archive.Framework\":\n\x16SlaveRegisteredMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\"<\n\x18SlaveReregisteredMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\":\n\x16UnregisterSlaveMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\"4\n\x10HeartbeatMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\"D\n\x18ShutdownFrameworkMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\"\x19\n\x17ShutdownExecutorMessage\"O\n\x16UpdateFrameworkMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\x12\x0b\n\x03pid\x18\x02 \x02(\t\"k\n\x17RegisterExecutorMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\x12&\n\x0b\x65xecutor_id\x18\x02 \x02(\x0b\x32\x11.mesos.ExecutorID\"\xe7\x01\n\x19\x45xecutorRegisteredMessage\x12*\n\rexecutor_info\x18\x02 \x02(\x0b\x32\x13.mesos.ExecutorInfo\x12(\n\x0c\x66ramework_id\x18\x03 \x02(\x0b\x32\x12.mesos.FrameworkID\x12,\n\x0e\x66ramework_info\x18\x04 \x02(\x0b\x32\x14.mesos.FrameworkInfo\x12 \n\x08slave_id\x18\x05 \x02(\x0b\x32\x0e.mesos.SlaveID\x12$\n\nslave_info\x18\x06 \x02(\x0b\x32\x10.mesos.SlaveInfo\"e\n\x1b\x45xecutorReregisteredMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\x12$\n\nslave_info\x18\x02 \x02(\x0b\x32\x10.mesos.SlaveInfo\"\x9b\x01\n\x15\x45xitedExecutorMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\x12(\n\x0c\x66ramework_id\x18\x02 \x02(\x0b\x32\x12.mesos.FrameworkID\x12&\n\x0b\x65xecutor_id\x18\x03 \x02(\x0b\x32\x11.mesos.ExecutorID\x12\x0e\n\x06status\x18\x04 \x02(\x05\"<\n\x18ReconnectExecutorMessage\x12 \n\x08slave_id\x18\x01 \x02(\x0b\x32\x0e.mesos.SlaveID\"\xbc\x01\n\x19ReregisterExecutorMessage\x12&\n\x0b\x65xecutor_id\x18\x01 \x02(\x0b\x32\x11.mesos.ExecutorID\x12(\n\x0c\x66ramework_id\x18\x02 \x02(\x0b\x32\x12.mesos.FrameworkID\x12\x1e\n\x05tasks\x18\x03 \x03(\x0b\x32\x0f.mesos.TaskInfo\x12-\n\x07updates\x18\x04 \x03(\x0b\x32\x1c.mesos.internal.StatusUpdate\"\'\n\x14RegisterProjdMessage\x12\x0f\n\x07project\x18\x01 \x02(\t\"$\n\x11ProjdReadyMessage\x12\x0f\n\x07project\x18\x01 \x02(\t\"D\n\x1bProjdUpdateResourcesMessage\x12%\n\nparameters\x18\x01 \x01(\x0b\x32\x11.mesos.Parameters\"C\n\x17\x46rameworkExpiredMessage\x12(\n\x0c\x66ramework_id\x18\x01 \x02(\x0b\x32\x12.mesos.FrameworkID\"\"\n\x0fShutdownMessage\x12\x0f\n\x07message\x18\x01 \x01(\t\"\"\n\x13\x41uthenticateMessage\x12\x0b\n\x03pid\x18\x01 \x02(\t\"5\n\x1f\x41uthenticationMechanismsMessage\x12\x12\n\nmechanisms\x18\x01 \x03(\t\"=\n\x1a\x41uthenticationStartMessage\x12\x11\n\tmechanism\x18\x01 \x02(\t\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\t\")\n\x19\x41uthenticationStepMessage\x12\x0c\n\x04\x64\x61ta\x18\x01 \x02(\x0c\" \n\x1e\x41uthenticationCompletedMessage\"\x1d\n\x1b\x41uthenticationFailedMessage\"+\n\x1a\x41uthenticationErrorMessage\x12\r\n\x05\x65rror\x18\x01 \x01(\t\"\xad\x01\n\x07\x41rchive\x12\x35\n\nframeworks\x18\x01 \x03(\x0b\x32!.mesos.internal.Archive.Framework\x1ak\n\tFramework\x12,\n\x0e\x66ramework_info\x18\x01 \x02(\x0b\x32\x14.mesos.FrameworkInfo\x12\x0b\n\x03pid\x18\x02 \x01(\t\x12#\n\x05tasks\x18\x03 \x03(\x0b\x32\x14.mesos.internal.Task')



_STATUSUPDATERECORD_TYPE = descriptor.EnumDescriptor(
  name='Type',
  full_name='mesos.internal.StatusUpdateRecord.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='UPDATE', index=0, number=0,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ACK', index=1, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=708,
  serialized_end=735,
)


_TASK = descriptor.Descriptor(
  name='Task',
  full_name='mesos.internal.Task',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='mesos.internal.Task.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='task_id', full_name='mesos.internal.Task.task_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.Task.framework_id', index=2,
      number=3, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executor_id', full_name='mesos.internal.Task.executor_id', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.Task.slave_id', index=4,
      number=5, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='state', full_name='mesos.internal.Task.state', index=5,
      number=6, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=6,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='resources', full_name='mesos.internal.Task.resources', index=6,
      number=7, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='statuses', full_name='mesos.internal.Task.statuses', index=7,
      number=8, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=48,
  serialized_end=322,
)


_ROLEINFO = descriptor.Descriptor(
  name='RoleInfo',
  full_name='mesos.internal.RoleInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='mesos.internal.RoleInfo.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='weight', full_name='mesos.internal.RoleInfo.weight', index=1,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=324,
  serialized_end=367,
)


_STATUSUPDATE = descriptor.Descriptor(
  name='StatusUpdate',
  full_name='mesos.internal.StatusUpdate',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.StatusUpdate.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executor_id', full_name='mesos.internal.StatusUpdate.executor_id', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.StatusUpdate.slave_id', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='status', full_name='mesos.internal.StatusUpdate.status', index=3,
      number=4, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='timestamp', full_name='mesos.internal.StatusUpdate.timestamp', index=4,
      number=5, type=1, cpp_type=5, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='uuid', full_name='mesos.internal.StatusUpdate.uuid', index=5,
      number=6, type=12, cpp_type=9, label=2,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=370,
  serialized_end=568,
)


_STATUSUPDATERECORD = descriptor.Descriptor(
  name='StatusUpdateRecord',
  full_name='mesos.internal.StatusUpdateRecord',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='type', full_name='mesos.internal.StatusUpdateRecord.type', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='update', full_name='mesos.internal.StatusUpdateRecord.update', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='uuid', full_name='mesos.internal.StatusUpdateRecord.uuid', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _STATUSUPDATERECORD_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=571,
  serialized_end=735,
)


_SUBMITSCHEDULERREQUEST = descriptor.Descriptor(
  name='SubmitSchedulerRequest',
  full_name='mesos.internal.SubmitSchedulerRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='name', full_name='mesos.internal.SubmitSchedulerRequest.name', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=737,
  serialized_end=775,
)


_SUBMITSCHEDULERRESPONSE = descriptor.Descriptor(
  name='SubmitSchedulerResponse',
  full_name='mesos.internal.SubmitSchedulerResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='okay', full_name='mesos.internal.SubmitSchedulerResponse.okay', index=0,
      number=1, type=8, cpp_type=7, label=2,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=777,
  serialized_end=816,
)


_EXECUTORTOFRAMEWORKMESSAGE = descriptor.Descriptor(
  name='ExecutorToFrameworkMessage',
  full_name='mesos.internal.ExecutorToFrameworkMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.ExecutorToFrameworkMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.ExecutorToFrameworkMessage.framework_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executor_id', full_name='mesos.internal.ExecutorToFrameworkMessage.executor_id', index=2,
      number=3, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='data', full_name='mesos.internal.ExecutorToFrameworkMessage.data', index=3,
      number=4, type=12, cpp_type=9, label=2,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=819,
  serialized_end=977,
)


_FRAMEWORKTOEXECUTORMESSAGE = descriptor.Descriptor(
  name='FrameworkToExecutorMessage',
  full_name='mesos.internal.FrameworkToExecutorMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.FrameworkToExecutorMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.FrameworkToExecutorMessage.framework_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executor_id', full_name='mesos.internal.FrameworkToExecutorMessage.executor_id', index=2,
      number=3, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='data', full_name='mesos.internal.FrameworkToExecutorMessage.data', index=3,
      number=4, type=12, cpp_type=9, label=2,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=980,
  serialized_end=1138,
)


_REGISTERFRAMEWORKMESSAGE = descriptor.Descriptor(
  name='RegisterFrameworkMessage',
  full_name='mesos.internal.RegisterFrameworkMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework', full_name='mesos.internal.RegisterFrameworkMessage.framework', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1140,
  serialized_end=1207,
)


_REREGISTERFRAMEWORKMESSAGE = descriptor.Descriptor(
  name='ReregisterFrameworkMessage',
  full_name='mesos.internal.ReregisterFrameworkMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework', full_name='mesos.internal.ReregisterFrameworkMessage.framework', index=0,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='failover', full_name='mesos.internal.ReregisterFrameworkMessage.failover', index=1,
      number=3, type=8, cpp_type=7, label=2,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1209,
  serialized_end=1296,
)


_FRAMEWORKREGISTEREDMESSAGE = descriptor.Descriptor(
  name='FrameworkRegisteredMessage',
  full_name='mesos.internal.FrameworkRegisteredMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.FrameworkRegisteredMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='master_info', full_name='mesos.internal.FrameworkRegisteredMessage.master_info', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1298,
  serialized_end=1408,
)


_FRAMEWORKREREGISTEREDMESSAGE = descriptor.Descriptor(
  name='FrameworkReregisteredMessage',
  full_name='mesos.internal.FrameworkReregisteredMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.FrameworkReregisteredMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='master_info', full_name='mesos.internal.FrameworkReregisteredMessage.master_info', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1410,
  serialized_end=1522,
)


_UNREGISTERFRAMEWORKMESSAGE = descriptor.Descriptor(
  name='UnregisterFrameworkMessage',
  full_name='mesos.internal.UnregisterFrameworkMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.UnregisterFrameworkMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1524,
  serialized_end=1594,
)


_DEACTIVATEFRAMEWORKMESSAGE = descriptor.Descriptor(
  name='DeactivateFrameworkMessage',
  full_name='mesos.internal.DeactivateFrameworkMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.DeactivateFrameworkMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1596,
  serialized_end=1666,
)


_RESOURCEREQUESTMESSAGE = descriptor.Descriptor(
  name='ResourceRequestMessage',
  full_name='mesos.internal.ResourceRequestMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.ResourceRequestMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='requests', full_name='mesos.internal.ResourceRequestMessage.requests', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1668,
  serialized_end=1768,
)


_RESOURCEOFFERSMESSAGE = descriptor.Descriptor(
  name='ResourceOffersMessage',
  full_name='mesos.internal.ResourceOffersMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='offers', full_name='mesos.internal.ResourceOffersMessage.offers', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pids', full_name='mesos.internal.ResourceOffersMessage.pids', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1770,
  serialized_end=1837,
)


_LAUNCHTASKSMESSAGE = descriptor.Descriptor(
  name='LaunchTasksMessage',
  full_name='mesos.internal.LaunchTasksMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.LaunchTasksMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='offer_id', full_name='mesos.internal.LaunchTasksMessage.offer_id', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tasks', full_name='mesos.internal.LaunchTasksMessage.tasks', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='filters', full_name='mesos.internal.LaunchTasksMessage.filters', index=3,
      number=5, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='offer_ids', full_name='mesos.internal.LaunchTasksMessage.offer_ids', index=4,
      number=6, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1840,
  serialized_end=2036,
)


_RESCINDRESOURCEOFFERMESSAGE = descriptor.Descriptor(
  name='RescindResourceOfferMessage',
  full_name='mesos.internal.RescindResourceOfferMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='offer_id', full_name='mesos.internal.RescindResourceOfferMessage.offer_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2038,
  serialized_end=2101,
)


_REVIVEOFFERSMESSAGE = descriptor.Descriptor(
  name='ReviveOffersMessage',
  full_name='mesos.internal.ReviveOffersMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.ReviveOffersMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2103,
  serialized_end=2166,
)


_RUNTASKMESSAGE = descriptor.Descriptor(
  name='RunTaskMessage',
  full_name='mesos.internal.RunTaskMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.RunTaskMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework', full_name='mesos.internal.RunTaskMessage.framework', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pid', full_name='mesos.internal.RunTaskMessage.pid', index=2,
      number=3, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='task', full_name='mesos.internal.RunTaskMessage.task', index=3,
      number=4, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2169,
  serialized_end=2312,
)


_KILLTASKMESSAGE = descriptor.Descriptor(
  name='KillTaskMessage',
  full_name='mesos.internal.KillTaskMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.KillTaskMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='task_id', full_name='mesos.internal.KillTaskMessage.task_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2314,
  serialized_end=2405,
)


_STATUSUPDATEMESSAGE = descriptor.Descriptor(
  name='StatusUpdateMessage',
  full_name='mesos.internal.StatusUpdateMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='update', full_name='mesos.internal.StatusUpdateMessage.update', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pid', full_name='mesos.internal.StatusUpdateMessage.pid', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2407,
  serialized_end=2487,
)


_STATUSUPDATEACKNOWLEDGEMENTMESSAGE = descriptor.Descriptor(
  name='StatusUpdateAcknowledgementMessage',
  full_name='mesos.internal.StatusUpdateAcknowledgementMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.StatusUpdateAcknowledgementMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.StatusUpdateAcknowledgementMessage.framework_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='task_id', full_name='mesos.internal.StatusUpdateAcknowledgementMessage.task_id', index=2,
      number=3, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='uuid', full_name='mesos.internal.StatusUpdateAcknowledgementMessage.uuid', index=3,
      number=4, type=12, cpp_type=9, label=2,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2490,
  serialized_end=2648,
)


_LOSTSLAVEMESSAGE = descriptor.Descriptor(
  name='LostSlaveMessage',
  full_name='mesos.internal.LostSlaveMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.LostSlaveMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2650,
  serialized_end=2702,
)


_RECONCILETASKSMESSAGE = descriptor.Descriptor(
  name='ReconcileTasksMessage',
  full_name='mesos.internal.ReconcileTasksMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.ReconcileTasksMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='statuses', full_name='mesos.internal.ReconcileTasksMessage.statuses', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2704,
  serialized_end=2806,
)


_FRAMEWORKERRORMESSAGE = descriptor.Descriptor(
  name='FrameworkErrorMessage',
  full_name='mesos.internal.FrameworkErrorMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='message', full_name='mesos.internal.FrameworkErrorMessage.message', index=0,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2808,
  serialized_end=2848,
)


_REGISTERSLAVEMESSAGE = descriptor.Descriptor(
  name='RegisterSlaveMessage',
  full_name='mesos.internal.RegisterSlaveMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave', full_name='mesos.internal.RegisterSlaveMessage.slave', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2850,
  serialized_end=2905,
)


_REREGISTERSLAVEMESSAGE = descriptor.Descriptor(
  name='ReregisterSlaveMessage',
  full_name='mesos.internal.ReregisterSlaveMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.ReregisterSlaveMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='slave', full_name='mesos.internal.ReregisterSlaveMessage.slave', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executor_infos', full_name='mesos.internal.ReregisterSlaveMessage.executor_infos', index=2,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tasks', full_name='mesos.internal.ReregisterSlaveMessage.tasks', index=3,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='completed_frameworks', full_name='mesos.internal.ReregisterSlaveMessage.completed_frameworks', index=4,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2908,
  serialized_end=3146,
)


_SLAVEREGISTEREDMESSAGE = descriptor.Descriptor(
  name='SlaveRegisteredMessage',
  full_name='mesos.internal.SlaveRegisteredMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.SlaveRegisteredMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3148,
  serialized_end=3206,
)


_SLAVEREREGISTEREDMESSAGE = descriptor.Descriptor(
  name='SlaveReregisteredMessage',
  full_name='mesos.internal.SlaveReregisteredMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.SlaveReregisteredMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3208,
  serialized_end=3268,
)


_UNREGISTERSLAVEMESSAGE = descriptor.Descriptor(
  name='UnregisterSlaveMessage',
  full_name='mesos.internal.UnregisterSlaveMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.UnregisterSlaveMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3270,
  serialized_end=3328,
)


_HEARTBEATMESSAGE = descriptor.Descriptor(
  name='HeartbeatMessage',
  full_name='mesos.internal.HeartbeatMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.HeartbeatMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3330,
  serialized_end=3382,
)


_SHUTDOWNFRAMEWORKMESSAGE = descriptor.Descriptor(
  name='ShutdownFrameworkMessage',
  full_name='mesos.internal.ShutdownFrameworkMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.ShutdownFrameworkMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3384,
  serialized_end=3452,
)


_SHUTDOWNEXECUTORMESSAGE = descriptor.Descriptor(
  name='ShutdownExecutorMessage',
  full_name='mesos.internal.ShutdownExecutorMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3454,
  serialized_end=3479,
)


_UPDATEFRAMEWORKMESSAGE = descriptor.Descriptor(
  name='UpdateFrameworkMessage',
  full_name='mesos.internal.UpdateFrameworkMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.UpdateFrameworkMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pid', full_name='mesos.internal.UpdateFrameworkMessage.pid', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3481,
  serialized_end=3560,
)


_REGISTEREXECUTORMESSAGE = descriptor.Descriptor(
  name='RegisterExecutorMessage',
  full_name='mesos.internal.RegisterExecutorMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.RegisterExecutorMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executor_id', full_name='mesos.internal.RegisterExecutorMessage.executor_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3562,
  serialized_end=3669,
)


_EXECUTORREGISTEREDMESSAGE = descriptor.Descriptor(
  name='ExecutorRegisteredMessage',
  full_name='mesos.internal.ExecutorRegisteredMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='executor_info', full_name='mesos.internal.ExecutorRegisteredMessage.executor_info', index=0,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.ExecutorRegisteredMessage.framework_id', index=1,
      number=3, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework_info', full_name='mesos.internal.ExecutorRegisteredMessage.framework_info', index=2,
      number=4, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.ExecutorRegisteredMessage.slave_id', index=3,
      number=5, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='slave_info', full_name='mesos.internal.ExecutorRegisteredMessage.slave_info', index=4,
      number=6, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3672,
  serialized_end=3903,
)


_EXECUTORREREGISTEREDMESSAGE = descriptor.Descriptor(
  name='ExecutorReregisteredMessage',
  full_name='mesos.internal.ExecutorReregisteredMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.ExecutorReregisteredMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='slave_info', full_name='mesos.internal.ExecutorReregisteredMessage.slave_info', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3905,
  serialized_end=4006,
)


_EXITEDEXECUTORMESSAGE = descriptor.Descriptor(
  name='ExitedExecutorMessage',
  full_name='mesos.internal.ExitedExecutorMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.ExitedExecutorMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.ExitedExecutorMessage.framework_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='executor_id', full_name='mesos.internal.ExitedExecutorMessage.executor_id', index=2,
      number=3, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='status', full_name='mesos.internal.ExitedExecutorMessage.status', index=3,
      number=4, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4009,
  serialized_end=4164,
)


_RECONNECTEXECUTORMESSAGE = descriptor.Descriptor(
  name='ReconnectExecutorMessage',
  full_name='mesos.internal.ReconnectExecutorMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='slave_id', full_name='mesos.internal.ReconnectExecutorMessage.slave_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4166,
  serialized_end=4226,
)


_REREGISTEREXECUTORMESSAGE = descriptor.Descriptor(
  name='ReregisterExecutorMessage',
  full_name='mesos.internal.ReregisterExecutorMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='executor_id', full_name='mesos.internal.ReregisterExecutorMessage.executor_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.ReregisterExecutorMessage.framework_id', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tasks', full_name='mesos.internal.ReregisterExecutorMessage.tasks', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='updates', full_name='mesos.internal.ReregisterExecutorMessage.updates', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4229,
  serialized_end=4417,
)


_REGISTERPROJDMESSAGE = descriptor.Descriptor(
  name='RegisterProjdMessage',
  full_name='mesos.internal.RegisterProjdMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='project', full_name='mesos.internal.RegisterProjdMessage.project', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4419,
  serialized_end=4458,
)


_PROJDREADYMESSAGE = descriptor.Descriptor(
  name='ProjdReadyMessage',
  full_name='mesos.internal.ProjdReadyMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='project', full_name='mesos.internal.ProjdReadyMessage.project', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4460,
  serialized_end=4496,
)


_PROJDUPDATERESOURCESMESSAGE = descriptor.Descriptor(
  name='ProjdUpdateResourcesMessage',
  full_name='mesos.internal.ProjdUpdateResourcesMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='parameters', full_name='mesos.internal.ProjdUpdateResourcesMessage.parameters', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4498,
  serialized_end=4566,
)


_FRAMEWORKEXPIREDMESSAGE = descriptor.Descriptor(
  name='FrameworkExpiredMessage',
  full_name='mesos.internal.FrameworkExpiredMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_id', full_name='mesos.internal.FrameworkExpiredMessage.framework_id', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4568,
  serialized_end=4635,
)


_SHUTDOWNMESSAGE = descriptor.Descriptor(
  name='ShutdownMessage',
  full_name='mesos.internal.ShutdownMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='message', full_name='mesos.internal.ShutdownMessage.message', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4637,
  serialized_end=4671,
)


_AUTHENTICATEMESSAGE = descriptor.Descriptor(
  name='AuthenticateMessage',
  full_name='mesos.internal.AuthenticateMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='pid', full_name='mesos.internal.AuthenticateMessage.pid', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4673,
  serialized_end=4707,
)


_AUTHENTICATIONMECHANISMSMESSAGE = descriptor.Descriptor(
  name='AuthenticationMechanismsMessage',
  full_name='mesos.internal.AuthenticationMechanismsMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='mechanisms', full_name='mesos.internal.AuthenticationMechanismsMessage.mechanisms', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4709,
  serialized_end=4762,
)


_AUTHENTICATIONSTARTMESSAGE = descriptor.Descriptor(
  name='AuthenticationStartMessage',
  full_name='mesos.internal.AuthenticationStartMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='mechanism', full_name='mesos.internal.AuthenticationStartMessage.mechanism', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='data', full_name='mesos.internal.AuthenticationStartMessage.data', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4764,
  serialized_end=4825,
)


_AUTHENTICATIONSTEPMESSAGE = descriptor.Descriptor(
  name='AuthenticationStepMessage',
  full_name='mesos.internal.AuthenticationStepMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='data', full_name='mesos.internal.AuthenticationStepMessage.data', index=0,
      number=1, type=12, cpp_type=9, label=2,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4827,
  serialized_end=4868,
)


_AUTHENTICATIONCOMPLETEDMESSAGE = descriptor.Descriptor(
  name='AuthenticationCompletedMessage',
  full_name='mesos.internal.AuthenticationCompletedMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4870,
  serialized_end=4902,
)


_AUTHENTICATIONFAILEDMESSAGE = descriptor.Descriptor(
  name='AuthenticationFailedMessage',
  full_name='mesos.internal.AuthenticationFailedMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4904,
  serialized_end=4933,
)


_AUTHENTICATIONERRORMESSAGE = descriptor.Descriptor(
  name='AuthenticationErrorMessage',
  full_name='mesos.internal.AuthenticationErrorMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='error', full_name='mesos.internal.AuthenticationErrorMessage.error', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4935,
  serialized_end=4978,
)


_ARCHIVE_FRAMEWORK = descriptor.Descriptor(
  name='Framework',
  full_name='mesos.internal.Archive.Framework',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='framework_info', full_name='mesos.internal.Archive.Framework.framework_info', index=0,
      number=1, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='pid', full_name='mesos.internal.Archive.Framework.pid', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='tasks', full_name='mesos.internal.Archive.Framework.tasks', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=5047,
  serialized_end=5154,
)

_ARCHIVE = descriptor.Descriptor(
  name='Archive',
  full_name='mesos.internal.Archive',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='frameworks', full_name='mesos.internal.Archive.frameworks', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_ARCHIVE_FRAMEWORK, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4981,
  serialized_end=5154,
)

_TASK.fields_by_name['task_id'].message_type = mesos_pb2._TASKID
_TASK.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_TASK.fields_by_name['executor_id'].message_type = mesos_pb2._EXECUTORID
_TASK.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_TASK.fields_by_name['state'].enum_type = mesos_pb2._TASKSTATE
_TASK.fields_by_name['resources'].message_type = mesos_pb2._RESOURCE
_TASK.fields_by_name['statuses'].message_type = mesos_pb2._TASKSTATUS
_STATUSUPDATE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_STATUSUPDATE.fields_by_name['executor_id'].message_type = mesos_pb2._EXECUTORID
_STATUSUPDATE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_STATUSUPDATE.fields_by_name['status'].message_type = mesos_pb2._TASKSTATUS
_STATUSUPDATERECORD.fields_by_name['type'].enum_type = _STATUSUPDATERECORD_TYPE
_STATUSUPDATERECORD.fields_by_name['update'].message_type = _STATUSUPDATE
_STATUSUPDATERECORD_TYPE.containing_type = _STATUSUPDATERECORD;
_EXECUTORTOFRAMEWORKMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_EXECUTORTOFRAMEWORKMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_EXECUTORTOFRAMEWORKMESSAGE.fields_by_name['executor_id'].message_type = mesos_pb2._EXECUTORID
_FRAMEWORKTOEXECUTORMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_FRAMEWORKTOEXECUTORMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_FRAMEWORKTOEXECUTORMESSAGE.fields_by_name['executor_id'].message_type = mesos_pb2._EXECUTORID
_REGISTERFRAMEWORKMESSAGE.fields_by_name['framework'].message_type = mesos_pb2._FRAMEWORKINFO
_REREGISTERFRAMEWORKMESSAGE.fields_by_name['framework'].message_type = mesos_pb2._FRAMEWORKINFO
_FRAMEWORKREGISTEREDMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_FRAMEWORKREGISTEREDMESSAGE.fields_by_name['master_info'].message_type = mesos_pb2._MASTERINFO
_FRAMEWORKREREGISTEREDMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_FRAMEWORKREREGISTEREDMESSAGE.fields_by_name['master_info'].message_type = mesos_pb2._MASTERINFO
_UNREGISTERFRAMEWORKMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_DEACTIVATEFRAMEWORKMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_RESOURCEREQUESTMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_RESOURCEREQUESTMESSAGE.fields_by_name['requests'].message_type = mesos_pb2._REQUEST
_RESOURCEOFFERSMESSAGE.fields_by_name['offers'].message_type = mesos_pb2._OFFER
_LAUNCHTASKSMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_LAUNCHTASKSMESSAGE.fields_by_name['offer_id'].message_type = mesos_pb2._OFFERID
_LAUNCHTASKSMESSAGE.fields_by_name['tasks'].message_type = mesos_pb2._TASKINFO
_LAUNCHTASKSMESSAGE.fields_by_name['filters'].message_type = mesos_pb2._FILTERS
_LAUNCHTASKSMESSAGE.fields_by_name['offer_ids'].message_type = mesos_pb2._OFFERID
_RESCINDRESOURCEOFFERMESSAGE.fields_by_name['offer_id'].message_type = mesos_pb2._OFFERID
_REVIVEOFFERSMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_RUNTASKMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_RUNTASKMESSAGE.fields_by_name['framework'].message_type = mesos_pb2._FRAMEWORKINFO
_RUNTASKMESSAGE.fields_by_name['task'].message_type = mesos_pb2._TASKINFO
_KILLTASKMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_KILLTASKMESSAGE.fields_by_name['task_id'].message_type = mesos_pb2._TASKID
_STATUSUPDATEMESSAGE.fields_by_name['update'].message_type = _STATUSUPDATE
_STATUSUPDATEACKNOWLEDGEMENTMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_STATUSUPDATEACKNOWLEDGEMENTMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_STATUSUPDATEACKNOWLEDGEMENTMESSAGE.fields_by_name['task_id'].message_type = mesos_pb2._TASKID
_LOSTSLAVEMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_RECONCILETASKSMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_RECONCILETASKSMESSAGE.fields_by_name['statuses'].message_type = mesos_pb2._TASKSTATUS
_REGISTERSLAVEMESSAGE.fields_by_name['slave'].message_type = mesos_pb2._SLAVEINFO
_REREGISTERSLAVEMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_REREGISTERSLAVEMESSAGE.fields_by_name['slave'].message_type = mesos_pb2._SLAVEINFO
_REREGISTERSLAVEMESSAGE.fields_by_name['executor_infos'].message_type = mesos_pb2._EXECUTORINFO
_REREGISTERSLAVEMESSAGE.fields_by_name['tasks'].message_type = _TASK
_REREGISTERSLAVEMESSAGE.fields_by_name['completed_frameworks'].message_type = _ARCHIVE_FRAMEWORK
_SLAVEREGISTEREDMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_SLAVEREREGISTEREDMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_UNREGISTERSLAVEMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_HEARTBEATMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_SHUTDOWNFRAMEWORKMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_UPDATEFRAMEWORKMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_REGISTEREXECUTORMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_REGISTEREXECUTORMESSAGE.fields_by_name['executor_id'].message_type = mesos_pb2._EXECUTORID
_EXECUTORREGISTEREDMESSAGE.fields_by_name['executor_info'].message_type = mesos_pb2._EXECUTORINFO
_EXECUTORREGISTEREDMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_EXECUTORREGISTEREDMESSAGE.fields_by_name['framework_info'].message_type = mesos_pb2._FRAMEWORKINFO
_EXECUTORREGISTEREDMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_EXECUTORREGISTEREDMESSAGE.fields_by_name['slave_info'].message_type = mesos_pb2._SLAVEINFO
_EXECUTORREREGISTEREDMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_EXECUTORREREGISTEREDMESSAGE.fields_by_name['slave_info'].message_type = mesos_pb2._SLAVEINFO
_EXITEDEXECUTORMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_EXITEDEXECUTORMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_EXITEDEXECUTORMESSAGE.fields_by_name['executor_id'].message_type = mesos_pb2._EXECUTORID
_RECONNECTEXECUTORMESSAGE.fields_by_name['slave_id'].message_type = mesos_pb2._SLAVEID
_REREGISTEREXECUTORMESSAGE.fields_by_name['executor_id'].message_type = mesos_pb2._EXECUTORID
_REREGISTEREXECUTORMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_REREGISTEREXECUTORMESSAGE.fields_by_name['tasks'].message_type = mesos_pb2._TASKINFO
_REREGISTEREXECUTORMESSAGE.fields_by_name['updates'].message_type = _STATUSUPDATE
_PROJDUPDATERESOURCESMESSAGE.fields_by_name['parameters'].message_type = mesos_pb2._PARAMETERS
_FRAMEWORKEXPIREDMESSAGE.fields_by_name['framework_id'].message_type = mesos_pb2._FRAMEWORKID
_ARCHIVE_FRAMEWORK.fields_by_name['framework_info'].message_type = mesos_pb2._FRAMEWORKINFO
_ARCHIVE_FRAMEWORK.fields_by_name['tasks'].message_type = _TASK
_ARCHIVE_FRAMEWORK.containing_type = _ARCHIVE;
_ARCHIVE.fields_by_name['frameworks'].message_type = _ARCHIVE_FRAMEWORK
DESCRIPTOR.message_types_by_name['Task'] = _TASK
DESCRIPTOR.message_types_by_name['RoleInfo'] = _ROLEINFO
DESCRIPTOR.message_types_by_name['StatusUpdate'] = _STATUSUPDATE
DESCRIPTOR.message_types_by_name['StatusUpdateRecord'] = _STATUSUPDATERECORD
DESCRIPTOR.message_types_by_name['SubmitSchedulerRequest'] = _SUBMITSCHEDULERREQUEST
DESCRIPTOR.message_types_by_name['SubmitSchedulerResponse'] = _SUBMITSCHEDULERRESPONSE
DESCRIPTOR.message_types_by_name['ExecutorToFrameworkMessage'] = _EXECUTORTOFRAMEWORKMESSAGE
DESCRIPTOR.message_types_by_name['FrameworkToExecutorMessage'] = _FRAMEWORKTOEXECUTORMESSAGE
DESCRIPTOR.message_types_by_name['RegisterFrameworkMessage'] = _REGISTERFRAMEWORKMESSAGE
DESCRIPTOR.message_types_by_name['ReregisterFrameworkMessage'] = _REREGISTERFRAMEWORKMESSAGE
DESCRIPTOR.message_types_by_name['FrameworkRegisteredMessage'] = _FRAMEWORKREGISTEREDMESSAGE
DESCRIPTOR.message_types_by_name['FrameworkReregisteredMessage'] = _FRAMEWORKREREGISTEREDMESSAGE
DESCRIPTOR.message_types_by_name['UnregisterFrameworkMessage'] = _UNREGISTERFRAMEWORKMESSAGE
DESCRIPTOR.message_types_by_name['DeactivateFrameworkMessage'] = _DEACTIVATEFRAMEWORKMESSAGE
DESCRIPTOR.message_types_by_name['ResourceRequestMessage'] = _RESOURCEREQUESTMESSAGE
DESCRIPTOR.message_types_by_name['ResourceOffersMessage'] = _RESOURCEOFFERSMESSAGE
DESCRIPTOR.message_types_by_name['LaunchTasksMessage'] = _LAUNCHTASKSMESSAGE
DESCRIPTOR.message_types_by_name['RescindResourceOfferMessage'] = _RESCINDRESOURCEOFFERMESSAGE
DESCRIPTOR.message_types_by_name['ReviveOffersMessage'] = _REVIVEOFFERSMESSAGE
DESCRIPTOR.message_types_by_name['RunTaskMessage'] = _RUNTASKMESSAGE
DESCRIPTOR.message_types_by_name['KillTaskMessage'] = _KILLTASKMESSAGE
DESCRIPTOR.message_types_by_name['StatusUpdateMessage'] = _STATUSUPDATEMESSAGE
DESCRIPTOR.message_types_by_name['StatusUpdateAcknowledgementMessage'] = _STATUSUPDATEACKNOWLEDGEMENTMESSAGE
DESCRIPTOR.message_types_by_name['LostSlaveMessage'] = _LOSTSLAVEMESSAGE
DESCRIPTOR.message_types_by_name['ReconcileTasksMessage'] = _RECONCILETASKSMESSAGE
DESCRIPTOR.message_types_by_name['FrameworkErrorMessage'] = _FRAMEWORKERRORMESSAGE
DESCRIPTOR.message_types_by_name['RegisterSlaveMessage'] = _REGISTERSLAVEMESSAGE
DESCRIPTOR.message_types_by_name['ReregisterSlaveMessage'] = _REREGISTERSLAVEMESSAGE
DESCRIPTOR.message_types_by_name['SlaveRegisteredMessage'] = _SLAVEREGISTEREDMESSAGE
DESCRIPTOR.message_types_by_name['SlaveReregisteredMessage'] = _SLAVEREREGISTEREDMESSAGE
DESCRIPTOR.message_types_by_name['UnregisterSlaveMessage'] = _UNREGISTERSLAVEMESSAGE
DESCRIPTOR.message_types_by_name['HeartbeatMessage'] = _HEARTBEATMESSAGE
DESCRIPTOR.message_types_by_name['ShutdownFrameworkMessage'] = _SHUTDOWNFRAMEWORKMESSAGE
DESCRIPTOR.message_types_by_name['ShutdownExecutorMessage'] = _SHUTDOWNEXECUTORMESSAGE
DESCRIPTOR.message_types_by_name['UpdateFrameworkMessage'] = _UPDATEFRAMEWORKMESSAGE
DESCRIPTOR.message_types_by_name['RegisterExecutorMessage'] = _REGISTEREXECUTORMESSAGE
DESCRIPTOR.message_types_by_name['ExecutorRegisteredMessage'] = _EXECUTORREGISTEREDMESSAGE
DESCRIPTOR.message_types_by_name['ExecutorReregisteredMessage'] = _EXECUTORREREGISTEREDMESSAGE
DESCRIPTOR.message_types_by_name['ExitedExecutorMessage'] = _EXITEDEXECUTORMESSAGE
DESCRIPTOR.message_types_by_name['ReconnectExecutorMessage'] = _RECONNECTEXECUTORMESSAGE
DESCRIPTOR.message_types_by_name['ReregisterExecutorMessage'] = _REREGISTEREXECUTORMESSAGE
DESCRIPTOR.message_types_by_name['RegisterProjdMessage'] = _REGISTERPROJDMESSAGE
DESCRIPTOR.message_types_by_name['ProjdReadyMessage'] = _PROJDREADYMESSAGE
DESCRIPTOR.message_types_by_name['ProjdUpdateResourcesMessage'] = _PROJDUPDATERESOURCESMESSAGE
DESCRIPTOR.message_types_by_name['FrameworkExpiredMessage'] = _FRAMEWORKEXPIREDMESSAGE
DESCRIPTOR.message_types_by_name['ShutdownMessage'] = _SHUTDOWNMESSAGE
DESCRIPTOR.message_types_by_name['AuthenticateMessage'] = _AUTHENTICATEMESSAGE
DESCRIPTOR.message_types_by_name['AuthenticationMechanismsMessage'] = _AUTHENTICATIONMECHANISMSMESSAGE
DESCRIPTOR.message_types_by_name['AuthenticationStartMessage'] = _AUTHENTICATIONSTARTMESSAGE
DESCRIPTOR.message_types_by_name['AuthenticationStepMessage'] = _AUTHENTICATIONSTEPMESSAGE
DESCRIPTOR.message_types_by_name['AuthenticationCompletedMessage'] = _AUTHENTICATIONCOMPLETEDMESSAGE
DESCRIPTOR.message_types_by_name['AuthenticationFailedMessage'] = _AUTHENTICATIONFAILEDMESSAGE
DESCRIPTOR.message_types_by_name['AuthenticationErrorMessage'] = _AUTHENTICATIONERRORMESSAGE
DESCRIPTOR.message_types_by_name['Archive'] = _ARCHIVE

class Task(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _TASK

  # @@protoc_insertion_point(class_scope:mesos.internal.Task)

class RoleInfo(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ROLEINFO

  # @@protoc_insertion_point(class_scope:mesos.internal.RoleInfo)

class StatusUpdate(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _STATUSUPDATE

  # @@protoc_insertion_point(class_scope:mesos.internal.StatusUpdate)

class StatusUpdateRecord(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _STATUSUPDATERECORD

  # @@protoc_insertion_point(class_scope:mesos.internal.StatusUpdateRecord)

class SubmitSchedulerRequest(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SUBMITSCHEDULERREQUEST

  # @@protoc_insertion_point(class_scope:mesos.internal.SubmitSchedulerRequest)

class SubmitSchedulerResponse(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SUBMITSCHEDULERRESPONSE

  # @@protoc_insertion_point(class_scope:mesos.internal.SubmitSchedulerResponse)

class ExecutorToFrameworkMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EXECUTORTOFRAMEWORKMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ExecutorToFrameworkMessage)

class FrameworkToExecutorMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _FRAMEWORKTOEXECUTORMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.FrameworkToExecutorMessage)

class RegisterFrameworkMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REGISTERFRAMEWORKMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.RegisterFrameworkMessage)

class ReregisterFrameworkMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REREGISTERFRAMEWORKMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ReregisterFrameworkMessage)

class FrameworkRegisteredMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _FRAMEWORKREGISTEREDMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.FrameworkRegisteredMessage)

class FrameworkReregisteredMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _FRAMEWORKREREGISTEREDMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.FrameworkReregisteredMessage)

class UnregisterFrameworkMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _UNREGISTERFRAMEWORKMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.UnregisterFrameworkMessage)

class DeactivateFrameworkMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _DEACTIVATEFRAMEWORKMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.DeactivateFrameworkMessage)

class ResourceRequestMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESOURCEREQUESTMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ResourceRequestMessage)

class ResourceOffersMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESOURCEOFFERSMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ResourceOffersMessage)

class LaunchTasksMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _LAUNCHTASKSMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.LaunchTasksMessage)

class RescindResourceOfferMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RESCINDRESOURCEOFFERMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.RescindResourceOfferMessage)

class ReviveOffersMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REVIVEOFFERSMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ReviveOffersMessage)

class RunTaskMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RUNTASKMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.RunTaskMessage)

class KillTaskMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _KILLTASKMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.KillTaskMessage)

class StatusUpdateMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _STATUSUPDATEMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.StatusUpdateMessage)

class StatusUpdateAcknowledgementMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _STATUSUPDATEACKNOWLEDGEMENTMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.StatusUpdateAcknowledgementMessage)

class LostSlaveMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _LOSTSLAVEMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.LostSlaveMessage)

class ReconcileTasksMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RECONCILETASKSMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ReconcileTasksMessage)

class FrameworkErrorMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _FRAMEWORKERRORMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.FrameworkErrorMessage)

class RegisterSlaveMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REGISTERSLAVEMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.RegisterSlaveMessage)

class ReregisterSlaveMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REREGISTERSLAVEMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ReregisterSlaveMessage)

class SlaveRegisteredMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SLAVEREGISTEREDMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.SlaveRegisteredMessage)

class SlaveReregisteredMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SLAVEREREGISTEREDMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.SlaveReregisteredMessage)

class UnregisterSlaveMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _UNREGISTERSLAVEMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.UnregisterSlaveMessage)

class HeartbeatMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _HEARTBEATMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.HeartbeatMessage)

class ShutdownFrameworkMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SHUTDOWNFRAMEWORKMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ShutdownFrameworkMessage)

class ShutdownExecutorMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SHUTDOWNEXECUTORMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ShutdownExecutorMessage)

class UpdateFrameworkMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _UPDATEFRAMEWORKMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.UpdateFrameworkMessage)

class RegisterExecutorMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REGISTEREXECUTORMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.RegisterExecutorMessage)

class ExecutorRegisteredMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EXECUTORREGISTEREDMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ExecutorRegisteredMessage)

class ExecutorReregisteredMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EXECUTORREREGISTEREDMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ExecutorReregisteredMessage)

class ExitedExecutorMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _EXITEDEXECUTORMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ExitedExecutorMessage)

class ReconnectExecutorMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _RECONNECTEXECUTORMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ReconnectExecutorMessage)

class ReregisterExecutorMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REREGISTEREXECUTORMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ReregisterExecutorMessage)

class RegisterProjdMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REGISTERPROJDMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.RegisterProjdMessage)

class ProjdReadyMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _PROJDREADYMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ProjdReadyMessage)

class ProjdUpdateResourcesMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _PROJDUPDATERESOURCESMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ProjdUpdateResourcesMessage)

class FrameworkExpiredMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _FRAMEWORKEXPIREDMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.FrameworkExpiredMessage)

class ShutdownMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _SHUTDOWNMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.ShutdownMessage)

class AuthenticateMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _AUTHENTICATEMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.AuthenticateMessage)

class AuthenticationMechanismsMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _AUTHENTICATIONMECHANISMSMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.AuthenticationMechanismsMessage)

class AuthenticationStartMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _AUTHENTICATIONSTARTMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.AuthenticationStartMessage)

class AuthenticationStepMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _AUTHENTICATIONSTEPMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.AuthenticationStepMessage)

class AuthenticationCompletedMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _AUTHENTICATIONCOMPLETEDMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.AuthenticationCompletedMessage)

class AuthenticationFailedMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _AUTHENTICATIONFAILEDMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.AuthenticationFailedMessage)

class AuthenticationErrorMessage(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _AUTHENTICATIONERRORMESSAGE

  # @@protoc_insertion_point(class_scope:mesos.internal.AuthenticationErrorMessage)

class Archive(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType

  class Framework(message.Message):
    __metaclass__ = reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _ARCHIVE_FRAMEWORK

    # @@protoc_insertion_point(class_scope:mesos.internal.Archive.Framework)
  DESCRIPTOR = _ARCHIVE

  # @@protoc_insertion_point(class_scope:mesos.internal.Archive)

# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = process
import sys, os
import socket
import time
import threading
import logging
import Queue
import select

from mesos_pb2 import *
from messages_pb2 import *

logger = logging.getLogger(__name__)

def spawn(target, *args, **kw):
    t = threading.Thread(target=target, name=target.__name__, args=args, kwargs=kw)
    t.daemon = True
    t.start()
    return t

class UPID(object):
    def __init__(self, name, addr=None):
        if addr is None and name and '@' in name:
            name, addr = name.split('@')
        self.name = name
        self.addr = addr

    def __str__(self):
        return "%s@%s" % (self.name, self.addr)


def async(f):
    def func(self, *a, **kw):
        self.delay(0, f, self, *a, **kw)
    return func

class Process(UPID):
    def __init__(self, name, port=0):
        UPID.__init__(self, name)
        self.port = port
        self.conn_pool = {}
        self.jobs = Queue.PriorityQueue()
        self.linked = {}
        self.sender = None
        self.aborted = False

    def delay(self, delay, func, *args, **kw):
        self.jobs.put((time.time() + delay, 0, func, args, kw))

    def run_jobs(self):
        while True:
            try:
                job = self.jobs.get(timeout=1)
            except Queue.Empty:
                if self.aborted:
                    break
                continue

            #self.jobs.task_done()
            t, tried, func, args, kw = job
            now = time.time()
            if t > now:
                if self.aborted:
                    break
                self.jobs.put(job)
                time.sleep(min(t-now, 0.1))
                continue

            try:
                #logger.debug("run job %s", func.__name__)
                func(*args, **kw)
                #logger.debug("run job %s comeplete", func.__name__)
            except Exception, e:
                logging.error("error while call %s (tried %d times)", func, tried)
                import traceback; traceback.print_exc()
                if tried < 4:
                    self.jobs.put((t + 3 ** tried, tried + 1, func, args, kw))

    @async
    def link(self, upid, callback):
        self._get_conn(upid.addr)
        self.linked[upid.addr] = callback

    def _get_conn(self, addr):
        if addr not in self.conn_pool:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host, port = addr.split(':')
            s.connect((host, int(port)))
            self.conn_pool[addr] = s
        return self.conn_pool[addr]

    def _encode(self, upid, msg):
        if isinstance(msg, str):
            body = ''
            uri = '/%s/%s' % (upid.name, msg)
        else:
            body = msg.SerializeToString()
            uri = '/%s/mesos.internal.%s' % (upid.name, msg.__class__.__name__)
        agent = 'libprocess/%s@%s' % (self.name, self.addr)
        msg = ['POST %s HTTP/1.0' % str(uri),
               'User-Agent: %s' % agent,
               'Connection: Keep-Alive',]
        if body:
            msg += [
               'Transfer-Encoding: chunked',
               '',
               '%x' % len(body), body,
               '0']
        msg += ['', ''] # for last \r\n\r\n
        return '\r\n'.join(msg)

    #@async
    def send(self, upid, msg):
        logger.debug("send to %s %s", upid, msg.__class__.__name__)
        data = self._encode(upid, msg)
        try:
            conn = self._get_conn(upid.addr)
            conn.send(data)
        except IOError:
            logger.warning("failed to send data to %s, retry again", upid)
            self.conn_pool.pop(upid.addr, None)
            if upid.addr in self.linked: # broken link
                callback = self.linked.pop(upid.addr)
                callback()
            raise

    def reply(self, msg):
        return self.send(self.sender, msg)

    def onPing(self):
        self.reply('PONG')

    @async
    def handle(self, msg):
        if self.aborted:
            return
        name = msg.__class__.__name__
        f = getattr(self, 'on' + name, None)
        assert f, 'should have on%s()' % name
        args = [v for (_,v) in msg.ListFields()]
        f(*args)

    def abort(self):
        self.aborted = True
        self.listen_sock.close()

    def stop(self):
        self.abort()
        self.join()
        for addr in self.conn_pool:
            self.conn_pool[addr].close()
        self.conn_pool.clear()

    def join(self):
        self.delay_t.join()
        return self.accept_t.join()

    def run(self):
        self.start()
        return self.join()

    def start(self):
        self.listen_sock = sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', self.port))
        if not self.port:
            port = sock.getsockname()[1]
            self.addr = '%s:%d' % (socket.gethostname(), port)
        self.accept_t = spawn(self.ioloop, sock)
        self.delay_t = spawn(self.run_jobs)

    def process_message(self, rf):
        headers = []
        while True:
            try:
                line = rf.readline()
            except IOError:
                break
            if not line or line == '\r\n':
                break
            headers.append(line)
        if not headers:
            return False # EoF

        method, uri, _ = headers[0].split(' ')
        _, process, mname = uri.split('/')
        assert process == self.name, 'unexpected messages'
        agent = headers[1].split(' ')[1].strip()
        logger.debug("incoming request: %s from %s", uri, agent)

        sender_name, addr = agent.split('@')
        self.sender = UPID(sender_name.split('/')[1], addr)

        if mname == 'PING':
            self.onPing()
            return True

        size = rf.readline()
        if size:
            size = int(size, 16)
            body = rf.read(size+2)[:-2]
            rf.read(5)  # ending
        else:
            body = ''

        sname = mname.split('.')[2]
        if sname not in globals():
            logger.error("unknown messages: %s", sname)
            return True

        try:
            msg = globals()[sname].FromString(body)
            self.handle(msg)
        except Exception, e:
            logger.error("error while processing message %s: %s", sname, e)
            import traceback; traceback.print_exc()
        return True

    def ioloop(self, sock):
        sock.listen(64)
        sfd = sock.fileno()
        conns = {sfd: sock}
        while not self.aborted:
            rlist = select.select(conns.keys(), [], [], 1)[0]
            for fd in rlist:
                if fd == sfd:
                    conn, addr = sock.accept()
                    logger.debug("accepted conn from %s", addr)
                    conns[conn.fileno()] = conn
                elif fd in conns:
                    try:
                        f = conns[fd].makefile('r')
                        while True:
                            if not self.process_message(f):
                                conns.pop(fd).close()
                                break
                            # is there any data in read buffer ?
                            if not f._rbuf.tell():
                                break
                        f.close()
                    except Exception, e:
                        import traceback; traceback.print_exc()
                        conns.pop(fd).close()
                #logging.debug("stop process event %d", fd)
        sock.close()
    """
    def communicate(self, conn):
        rf = conn.makefile('r', 4096)
        while not self.aborted:
            cont = self.process_message(rf)
            if not cont:
                break
        rf.close()

    def ioloop(self, s):
        s.listen(1)
        conns = []
        while True:
            conn, addr = s.accept()
            logger.debug("accepted conn from %s", addr)
            conns.append(conn)
            if self.aborted:
                break

            spawn(self.communicate, conn)

        for c in conns:
            c.close()
    """

########NEW FILE########
__FILENAME__ = scheduler
import os, sys
import time
import getpass
import logging
import struct
import socket

from process import UPID, Process, async

from mesos_pb2 import TASK_LOST, MasterInfo
from messages_pb2 import (RegisterFrameworkMessage, ReregisterFrameworkMessage,
        DeactivateFrameworkMessage, UnregisterFrameworkMessage,
        ResourceRequestMessage, ReviveOffersMessage, LaunchTasksMessage, KillTaskMessage,
        StatusUpdate, StatusUpdateAcknowledgementMessage, FrameworkToExecutorMessage)

logger = logging.getLogger(__name__)

class Scheduler(object):
    def registered(self, driver, framework_id, masterInfo): pass
    def reregistered(self, driver, masterInfo): pass
    def disconnected(self, driver): pass
    def frameworkMessage(self, driver, slave_id, executor_id, message): pass
    def resourceOffers(self, driver, offers): pass
    def offerRescinded(self, driver, offer_id): pass
    def statusUpdate(self, driver, status): pass
    def executorLost(self, driver, executor_id, slave_id, status): pass
    def slaveLost(self, driver, slave_id): pass
    def error(self, driver, message): pass

class SchedulerDriver(object):
    def start(self): pass
    def join(self): pass
    def run(self): pass
    def abort(self): pass
    def stop(self, failover=False): pass
    def reviveOffers(self): pass
    def requestResources(self, requests): pass
    def declineOffer(self, offerId, filters=None): pass
    def launchTasks(self, offerId, tasks, filters=None): pass
    def killTask(self, taskId): pass
    def sendFrameworkMessage(self, executorId, slaveId, data): pass


class MesosSchedulerDriver(Process):
    def __init__(self, sched, framework, master_uri):
        Process.__init__(self, 'scheduler')
        self.sched = sched
        #self.executor_info = executor_info
        self.master_uri = master_uri
        self.framework = framework
        self.framework.failover_timeout = 100
        self.framework_id = framework.id

        self.master = None
        self.detector = None

        self.connected = False
        self.savedOffers = {}
        self.savedSlavePids = {}

    @async # called by detector
    def onNewMasterDetectedMessage(self, data):
        try:
            info = MasterInfo()
            info.ParseFromString(data)
            ip = socket.inet_ntoa(struct.pack('<I', info.ip))
            self.master = UPID('master@%s:%s' % (ip, info.port))
        except:
            self.master = UPID(data)

        self.connected = False
        self.register()

    @async # called by detector
    def onNoMasterDetectedMessage(self):
        self.connected = False
        self.master = None

    def register(self):
        if self.connected or self.aborted:
            return

        if self.master:
            if not self.framework_id.value:
                msg = RegisterFrameworkMessage()
                msg.framework.MergeFrom(self.framework)
            else:
                msg = ReregisterFrameworkMessage()
                msg.framework.MergeFrom(self.framework)
                msg.failover = True
            self.send(self.master, msg)

        self.delay(2, self.register)

    def onFrameworkRegisteredMessage(self, framework_id, master_info):
        self.framework_id = framework_id
        self.framework.id.MergeFrom(framework_id)
        self.connected = True
        self.link(self.master, self.onDisconnected)
        self.sched.registered(self, framework_id, master_info)

    def onFrameworkReregisteredMessage(self, framework_id, master_info):
        assert self.framework_id == framework_id
        self.connected = True
        self.link(self.master, self.onDisconnected)
        self.sched.reregistered(self, master_info)

    def onDisconnected(self):
        self.connected = False
        logger.warning("disconnected from master")
        self.delay(5, self.register)

    def onResourceOffersMessage(self, offers, pids):
        for offer, pid in zip(offers, pids):
            self.savedOffers.setdefault(offer.id.value, {})[offer.slave_id.value] = UPID(pid)
        self.sched.resourceOffers(self, list(offers))

    def onRescindResourceOfferMessage(self, offer_id):
        self.savedOffers.pop(offer_id.value, None)
        self.sched.offerRescinded(self, offer_id)

    def onStatusUpdateMessage(self, update, pid=''):
        assert self.framework_id == update.framework_id

        if pid and not pid.endswith('0.0.0.0:0'):
            reply = StatusUpdateAcknowledgementMessage()
            reply.framework_id.MergeFrom(self.framework_id)
            reply.slave_id.MergeFrom(update.slave_id)
            reply.task_id.MergeFrom(update.status.task_id)
            reply.uuid = update.uuid
            try: self.send(UPID(pid), reply)
            except IOError: pass

        self.sched.statusUpdate(self, update.status)

    def onLostSlaveMessage(self, slave_id):
        self.sched.slaveLost(self, slave_id)

    def onExecutorToFrameworkMessage(self, slave_id, framework_id, executor_id, data):
        self.sched.frameworkMessage(self, slave_id, executor_id, data)

    def onFrameworkErrorMessage(self, message, code=0):
        self.sched.error(self, code, message)

    def start(self):
        Process.start(self)
        uri = self.master_uri
        if uri.startswith('zk://') or uri.startswith('zoo://'):
            from .detector import MasterDetector
            self.detector = MasterDetector(uri[uri.index('://') + 3:], self)
            self.detector.start()
        else:
            if not ':' in uri:
                uri += ':5050'
            self.onNewMasterDetectedMessage('master@%s' % uri)

    def abort(self):
        if self.connected:
            msg = UnregisterFrameworkMessage()
            msg.framework_id.MergeFrom(self.framework_id)
            self.send(self.master, msg)
        Process.abort(self)

    def stop(self, failover=False):
        if self.connected and not failover:
            msg = DeactivateFrameworkMessage()
            msg.framework_id.MergeFrom(self.framework_id)
            self.send(self.master, msg)
        if self.detector:
            self.detector.stop()
        Process.stop(self)

    @async
    def requestResources(self, requests):
        if not self.connected:
            return
        msg = ResourceRequestMessage()
        msg.framework_id.MergeFrom(self.framework_id)
        for req in requests:
            msg.requests.add().MergeFrom(req)
        self.send(self.master, msg)

    @async
    def reviveOffers(self):
        if not self.connected:
            return
        msg = ReviveOffersMessage()
        msg.framework_id.MergeFrom(self.framework_id)
        self.send(self.master, msg)

    def launchTasks(self, offer_id, tasks, filters):
        if not self.connected or offer_id.value not in self.savedOffers:
            for task in tasks:
                update = StatusUpdate()
                update.framework_id.MergeFrom(self.framework_id)
                update.status.task_id.MergeFrom(task.task_id)
                update.status.state = TASK_LOST
                update.status.message = 'Master disconnected' if not self.connected else "invalid offer_id"
                update.timestamp = time.time()
                update.uuid = ''
                self.onStatusUpdateMessage(update)
            return

        msg = LaunchTasksMessage()
        msg.framework_id.MergeFrom(self.framework_id)
        msg.offer_id.MergeFrom(offer_id)
        msg.filters.MergeFrom(filters)
        for task in tasks:
            msg.tasks.add().MergeFrom(task)
            pid = self.savedOffers.get(offer_id.value, {}).get(task.slave_id.value)
            if pid and task.slave_id.value not in self.savedSlavePids:
                self.savedSlavePids[task.slave_id.value] = pid
        self.savedOffers.pop(offer_id.value)
        self.send(self.master, msg)

    def declineOffer(self, offer_id, filters=None):
        if not self.connected:
            return
        msg = LaunchTasksMessage()
        msg.framework_id.MergeFrom(self.framework_id)
        msg.offer_id.MergeFrom(offer_id)
        if filters:
             msg.filters.MergeFrom(filters)
        self.send(self.master, msg)

    @async
    def killTask(self, task_id):
        if not self.connected:
            return
        msg = KillTaskMessage()
        msg.framework_id.MergeFrom(self.framework_id)
        msg.task_id.MergeFrom(task_id)
        self.send(self.master, msg)

    @async
    def sendFrameworkMessage(self, executor_id, slave_id, data):
        if not self.connected:
            return

        msg = FrameworkToExecutorMessage()
        msg.framework_id.MergeFrom(self.framework_id)
        msg.executor_id.MergeFrom(executor_id)
        msg.slave_id.MergeFrom(slave_id)
        msg.data = data

        slave = self.savedSlavePids.get(slave_id.value, self.master) # can not send to slave directly
        self.send(slave, msg)

########NEW FILE########
__FILENAME__ = slave
import os, sys
import time
import logging
import socket
import threading
import signal

from process import UPID, Process
from launcher import Launcher

from mesos_pb2 import *
from messages_pb2 import *

logger = logging.getLogger("slave")

class Resources(object):
    def __init__(self, cpus, mem):
        self.cpus = cpus
        self.mem = mem

    def __iadd__(self, other):
        if not isinstance(other, Resources):
            other = Resources.new(other)
        self.cpus += other.cpus
        self.mem += other.mem
        return self

    def __isub__(self, other):
        if not isinstance(other, Resources):
            other = Resources.new(other)
        self.cpus -= other.cpus
        self.mem -= other.mem
        return self

    @classmethod
    def new(cls, rs):
        self = cls(0, 0)
        for r in rs:
            self.__dict__[r.name] = r.scalar.value
        return self


class Executor(object):
    def __init__(self, framework_id, info, directory):
        self.framework_id = framework_id
        self.info = info
        self.directory = directory

        self.id = info.executor_id
        self.resources = Resources.new(info.resources)
        self.uuid = os.urandom(16)

        self.pid = None
        self.shutdown = False
        self.launchedTasks = {}
        self.queuedTasks = {}

    def addTask(self, task):
        assert task.task_id.value not in self.launchedTasks
        t = Task()
        t.framework_id.MergeFrom(self.framework_id)
        t.state = TASK_STAGING
        t.name = task.name
        t.task_id.MergeFrom(task.task_id)
        t.slave_id.MergeFrom(task.slave_id)
        t.resources.MergeFrom(task.resources)
        if task.command:
            t.executor_id.MergeFrom(self.id)

        self.launchedTasks[task.task_id.value] = t
        self.resources += task.resources
        return t

    def removeTask(self, task_id):
        tid = task_id.value
        self.queuedTasks.pop(tid, None)
        if tid in self.launchedTasks:
            self.resources -= self.launchedTasks[tid].resources
            del self.launchedTasks[tid]

    def updateTaskState(self, task_id, state):
        if task_id.value in self.launchedTasks:
            self.launchedTasks[task_id.value].state = state


class Framework(object):
    def __init__(self, id, info, pid, conf):
        self.id = id
        self.info = info
        self.pid = pid
        self.conf = conf

        self.executors = {}
        self.updates = {}

    def get_executor_info(self, task):
        assert task.HasField('executor') != task.HasField('command')
        if task.HasField('executor'):
            return task.executor

        info = ExecutorInfo()
        fmt = "Task %s (%s)"
        if len(task.command.value) > 15:
            id = fmt % (task.task_id.value, task.command.value[:12] + '...')
        else:
            id = fmt % (task.task_id.value, task.command.value)
        info.executor_id.value = id
        info.framework_id.value = self.id
        info.command.value = task.command.value
        return info

    def createExecutor(self, info, directory):
        executor = Executor(self.id, info, directory)
        self.executors[executor.id.value] = executor
        return executor

    def destroyExecutor(self, exec_id):
        self.executors.pop(exec_id.value, None)

    def get_executor(self, exec_id):
        if isinstance(exec_id, TaskID):
            tid = exec_id.value
            for executor in self.executors.values():
                if tid in executor.queuedTasks or tid in executor.launchedTasks:
                    return executor
            return
        return self.executors.get(exec_id.value)
    getExecutor = get_executor


class ProcessInfo(object):
    def __init__(self, fid, eid, pid, directory):
        self.framework_id = fid
        self.executor_id = eid
        self.pid = pid
        self.directory = directory


class IsolationModule(object):
    def __init__(self):
        self.infos = {}
        self.pids = {}

    def initialize(self, slave):
        self.slave = slave
        t = threading.Thread(target=self.reaper)
        t.daemon = True
        t.start()

    def launchExecutor(self, framework_id, info, executor_info, directory, resources):
        fid = framework_id.value
        eid = executor_info.executor_id.value
        logger.info("Launching %s (%s) in %s with resources %s for framework %s",
                eid, executor_info.command.value, directory, resources, fid)
        pid = os.fork()
        assert pid >= 0
        if pid:
            logger.info("Forked executor at %d", pid)
            pinfo = ProcessInfo(framework_id, executor_info.executor_id, pid, directory)
            self.infos.setdefault(fid, {})[eid] = pinfo
            self.pids[pid] = pinfo
            self.slave.executorStarted(framework_id, executor_info.executor_id, pid)
        else:
            #pid = os.setsid()
            # copy UPID of slave
            launcher = Launcher(framework_id, executor_info.executor_id, executor_info.command,
                    info.user, directory, self.slave)
            launcher.run()

    def killExecutor(self, framework_id, executor_id):
        pinfo = self.infos.get(framework_id.value, {}).get(executor_id.value)
        if pinfo is None:
            logger.error("ERROR! Asked to kill an unknown executor! %s", executor_id.value)
            return
        pid = pinfo.pid
        os.kill(pid, signal.SIGKILL)
        # remove when waitpid()
        #self._removeExecutor(pinfo)

    def removeExecutor(self, e):
        logger.info("remove executor: %s", e)
        if e.framework_id.value not in self.infos:
            return
        self.infos[e.framework_id.value].pop(e.executor_id.value, None)
        if not self.infos[e.framework_id.value]:
            del self.infos[e.framework_id.value]
        self.pids.pop(e.pid)

    def resourcesChanged(self, framework_id, executor_id, resources):
        pass

    def reaper(self):
        while True:
            if not self.pids:
                time.sleep(1)
                continue

            try:
                pid, status = os.waitpid(-1, 0)
            except OSError, e:
                time.sleep(1)
                logger.error("waitpid: %s", e)
                continue

            if pid > 0 and pid in self.pids and not os.WIFSTOPPED(status):
                e = self.pids[pid]
                logger.info("Telling slave of lost executor %s of framework %s",
                        e.executor_id, e.framework_id)
                self.slave.executorExited(e.framework_id, e.executor_id, status)
                self.removeExecutor(e)


def isTerminalTaskState(state):
    return state in (TASK_FINISHED, TASK_FAILED, TASK_KILLED, TASK_LOST)


class Slave(Process):
    def __init__(self, options):
        Process.__init__(self, "slave")
        self.options = options
        self.resources = Resources(options.cpus, options.mem)
        self.attributes = options.attributes

        self.id = None
        self.isolation = IsolationModule()
        self.info = self.getSlaveInfo()
        self.master = UPID('master', options.master)
        self.frameworks = {}
        self.startTime = time.time()
        self.connected = False

    def getSlaveInfo(self):
        info = SlaveInfo()
        info.hostname = socket.gethostname()
        info.webui_hostname = ''
        info.webui_port = 8081
        cpus = info.resources.add()
        cpus.name = 'cpus'
        cpus.type = 0
        cpus.scalar.value = self.resources.cpus
        mem = info.resources.add()
        mem.name = 'mem'
        mem.type = 0
        mem.scalar.value = self.resources.mem
        if self.attributes:
            for attrs in self.attributes.split(','):
                name,value = attrs.split(':')
                a = self.info.attributes.add()
                a.name = name
                a.type = Value.TEXT # 3 # TEXT
                a.text.value = value
        return info

    def getFramework(self, framework_id):
        return self.frameworks.get(framework_id.value)

    def onNewMasterDetectedMessage(self, pid):
        self.master = UPID(pid)
        self.register()

    def onNoMasterDetectedMessage(self):
        self.master = None
        self.connected = False

    def register(self):
        if self.id is None:
            msg = RegisterSlaveMessage()
            msg.slave.MergeFrom(self.info)
        else:
            msg = ReregisterSlaveMessage()
            msg.slave_id.MergeFrom(self.id)
            msg.slave.MergeFrom(self.info)
            for framework in self.frameworks.itervalues():
                for executor in framework.executors.values():
                    msg.executor_infos.add().MergeFrom(executor.info)
                    for task in executor.launchedTasks.itervalues():
                        msg.tasks.add().MergeFrom(task)
        return self.send(self.master, msg)

    def onSlaveRegisteredMessage(self, slave_id):
        logger.info("slave registed %s", slave_id.value)
        self.id = slave_id
        self.connected = True

    def onSlaveReregisteredMessage(self, slave_id):
        assert self.id == slave_id
        self.connected = True

    def onRunTaskMessage(self, framework_id, framework_info, pid, task):
        logger.info("Got assigned task %s for framework %s",
                task.task_id.value, framework_id.value)
        fid = framework_id.value
        if fid not in self.frameworks:
            framework = Framework(framework_id, framework_info, UPID(pid), self.options)
            self.frameworks[fid] = framework
        else:
            framework = self.frameworks[fid]

        executorInfo = framework.get_executor_info(task)
        eid = executorInfo.executor_id
        executor = framework.getExecutor(eid)
        if executor:
            if executor.shutdown:
                logger.warning("WARNING! executor is shuting down")
            elif not executor.pid:
                executor.queuedTasks[task.task_id.value] = task
            else:
                executor.addTask(task)
                #self.isolation.resourcesChanged(framework_id, executor.id, executor.resources)

                msg = RunTaskMessage()
                msg.framework.MergeFrom(framework.info)
                msg.framework_id.MergeFrom(framework_id)
                msg.pid = str(framework.pid)
                msg.task.MergeFrom(task)
                self.send(executor.pid, msg)
        else:
            directory = self.createUniqueWorkDirectory(framework.id, eid)
            executor = framework.createExecutor(executorInfo, directory)
            executor.queuedTasks[task.task_id.value] = task
            self.isolation.launchExecutor(framework.id, framework.info, executor.info,
                    directory, executor.resources)

    def onKillTaskMessage(self, framework_id, task_id):
        framework = self.getFramework(framework_id)
        if not framework or not framework.getExecutor(task_id):
            msg = StatusUpdateMessage()
            update = msg.update
            update.framework_id.MergeFrom(framework_id)
            update.slave_id.MergeFrom(self.id)
            update.status.task_id.MergeFrom(task_id)
            update.status.state = TASK_LOST
            update.timestamp = time.time()
            update.uuid = os.urandom(16)
            return self.send(self.master, msg)

        executor = framework.getExecutor(task_id)
        if not executor.pid:
            executor.removeTask(task_id)
            msg = StatusUpdateMessage()
            update = msg.update
            update.framework_id.MergeFrom(framework_id)
            update.slave_id.MergeFrom(self.id)
            update.status.task_id.MergeFrom(task_id)
            update.status.state = TASK_KILLED
            update.timestamp = time.time()
            update.uuid = os.urandom(16)
            return self.send(self.master, msg)

        msg = KillTaskMessage()
        msg.framework_id.MergeFrom(framework_id)
        msg.task_id.MergeFrom(task_id)
        return self.send(executor.pid, msg)

    def onShutdownFrameworkMessage(self, framework_id):
        framework = self.getFramework(framework_id)
        if framework:
            for executor in framework.executors.values():
                self.shutdownExecutor(framework, executor)

    def shutdownExecutor(self, framework, executor):
        logger.info("shutdown %s %s", framework.id.value, executor.id.value)
        self.send(executor.pid, ShutdownExecutorMessage())
        executor.shutdown = True

        # delay check TODO
        time.sleep(3)
        self.isolation.killExecutor(framework.id, executor.id)
        framework.destroyExecutor(executor.id)
        if not framework.executors and not framework.updates:
            self.frameworks.pop(framework.id.value)

    def onUpdateFrameworkMessage(self, framework_id, pid):
        framework = self.getFramework(framework_id)
        if framework:
            framework.pid = pid

    def executorStarted(self, framework_id, executor_id, pid):
        pass

    def executorExited(self, framework_id, executor_id, status):
        logger.info("Executor %s of framework %s exited with %d",
                executor_id.value, framework_id.value, status)
        framework = self.getFramework(framework_id)
        if not framework:
            return
        executor = framework.getExecutor(executor_id)
        if not executor:
            return

        isCommandExecutor = False
        for task in executor.launchedTasks.values():
            if not isTerminalTaskState(task.state):
                isCommandExecutor = not task.HasField('executor_id')
                self.transitionLiveTask(task.task_id, executor_id,
                    framework_id, isCommandExecutor, status)

        for task in executor.queuedTasks.values():
            isCommandExecutor = task.HasField('command')
            self.transitionLiveTask(task.task_id, executor_id,
                    framework_id, isCommandExecutor, status)

        if not isCommandExecutor:
            msg = ExitedExecutorMessage()
            msg.slave_id.MergeFrom(self.id)
            msg.framework_id.MergeFrom(framework_id)
            msg.executor_id.MergeFrom(executor_id)
            msg.status = status
            self.send(self.master, msg)
        framework.destroyExecutor(executor_id)

    def onRegisterExecutorMessage(self, framework_id, executor_id):
        framework = self.getFramework(framework_id)
        if not framework:
            # TODO shutdown executor
            return
        executor = framework.getExecutor(executor_id)
        if not executor or executor.pid or executor.shutdown:
            # TODO shutdown executor
            return
        executor.pid = self.sender

        msg = ExecutorRegisteredMessage()
        msg.executor_info.MergeFrom(executor.info)
        msg.framework_id.MergeFrom(framework_id)
        msg.framework_info.MergeFrom(framework.info)
        msg.slave_id.MergeFrom(self.id)
        msg.slave_info.MergeFrom(self.info)
        self.send(executor.pid, msg)

        for task in executor.queuedTasks.values():
            msg = RunTaskMessage()
            msg.framework_id.MergeFrom(framework.id)
            msg.framework.MergeFrom(framework.info)
            msg.pid = str(framework.pid)
            msg.task.MergeFrom(task)
            self.send(executor.pid, msg)

        for task in executor.queuedTasks.values():
            executor.addTask(task)
        executor.queuedTasks.clear()

    def onStatusUpdateMessage(self, update):
        status = update.status
        framework = self.getFramework(update.framework_id)
        if not framework:
            return
        executor = framework.getExecutor(status.task_id)
        if not executor:
            return
        executor.updateTaskState(status.task_id, status.state)
        if isTerminalTaskState(status.state):
            executor.removeTask(status.task_id)

        msg = StatusUpdateMessage()
        msg.update.MergeFrom(update)
        msg.pid = str(self) # pid
        self.send(self.master, msg)

        framework.updates[update.uuid] = update

    def onStatusUpdateAcknowledgementMessage(self, slave_id, framework_id, task_id, uuid):
        framework = self.getFramework(framework_id)
        if framework and uuid in framework.updates:
            framework.updates.pop(uuid)
            if not framework.executors and not framework.updates:
                self.frameworks.pop(framework_id.value)

    def onFrameworkToExecutorMessage(self, slave_id, framework_id, executor_id, data):
        framework = self.getFramework(framework_id)
        if not framework:
            return
        executor = framework.getExecutor(executor_id)
        if not executor:
            return
        if not executor.pid:
            return
        msg = FrameworkToExecutorMessage()
        msg.slave_id.MergeFrom(slave_id)
        msg.framework_id.MergeFrom(framework_id)
        msg.executor_id.MergeFrom(executor_id)
        msg.data = data
        self.send(executor.pid, msg)

    def onExecutorToFrameworkMessage(self, slave_id, framework_id, executor_id, data):
        framework = self.getFramework(framework_id)
        if not framework:
            return
        msg = ExecutorToFrameworkMessage()
        msg.slave_id.MergeFrom(slave_id)
        msg.framework_id.MergeFrom(framework_id)
        msg.executor_id.MergeFrom(executor_id)
        msg.data = data
        self.send(framework_id.pid, msg)

    def onShutdownMessage(self):
        self.stop()

    def start(self):
        Process.start(self)
        self.isolation.initialize(self)
        self.register() # master detector TODO

    def onPing(self):
        self.reply("PONG")

    def createStatusUpdate(self, task_id, executor_id, framework_id,
            taskState, reason):
        status = TaskStatus()
        status.task_id.MergeFrom(task_id)
        status.state = taskState
        status.message = reason

        update = StatusUpdate()
        update.framework_id.MergeFrom(framework_id)
        update.slave_id.MergeFrom(self.id)
        update.executor_id.MergeFrom(executor_id)
        update.status.MergeFrom(status)
        update.timestamp = time.time()
        update.uuid = os.urandom(16)

        return update

    def statusUpdate(self, update):
        logger.info("status update")
        status = update.status
        framework = self.getFramework(update.framework_id)
        if not framework:
            return
        executor = framework.getExecutor(status.task_id)
        if not executor:
            return
        if isTerminalTaskState(status.state):
            executor.removeTask(status.task_id)
        msg = StatusUpdateMessage()
        msg.update.MergeFrom(update)
        msg.pid = str(self)
        self.send(self.master, msg)
        # check
        framework.updates[update.uuid] = update

    def transitionLiveTask(self, task_id, executor_id, framework_id,
            isCommandExecutor, status):
        if isCommandExecutor:
            update = self.createStatusUpdate(task_id, executor_id,
                    framework_id, TASK_FAILED, "Executor running the task's command failed")
        else:
            update = self.createStatusUpdate(task_id, executor_id,
                    framework_id, TASK_LOST, "Executor exited")
        self.statusUpdate(update)

    def createUniqueWorkDirectory(self, framework_id, executor_id):
        root = self.options.work_dir
        path = os.path.join(root, 'slaves', self.id.value,
                'frameworks', framework_id.value,
                'executors', executor_id.value, 'runs')
        for i in range(10000):
            p = os.path.join(path, str(i))
            if not os.path.exists(p):
                os.makedirs(p)
                return p

def main():
    import optparse
    parser = optparse.OptionParser(usage="Usage: %prog [options]")
    parser.add_option("-s", "--master", type="string", default="localhost:5050",
            help="May be one of:\n"
              " host[:5050]"
              "  host:port\n"
              "  zk://host1:port1,host2:port2,.../path\n"
              "  zk://username:password@host1:port1,host2:port2,.../path\n"
              "  file://path/to/file (where file contains one of the above)")
    parser.add_option("-c", "--cpus", type="int", default=2)
    parser.add_option("-m", "--mem", type="int", default=1024)
    parser.add_option("-a", "--attributes", type="string")
    parser.add_option("-w", "--work_dir", type="string", default="/tmp/mesos")
    parser.add_option("-q", "--quiet", action="store_true")
    parser.add_option("-v", "--verbose", action="store_true")

    options, args = parser.parse_args()
    logging.basicConfig(format='[slave] %(asctime)-15s %(message)s',
                    level=options.quiet and logging.ERROR
                        or options.verbose and logging.DEBUG
                        or logging.WARNING)

    slave = Slave(options)
    slave.run()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = zkpython
import zookeeper
import threading
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
zookeeper.set_debug_level(zookeeper.LOG_LEVEL_WARN)



# Mapping of connection state values to human strings.
STATE_NAME_MAPPING = {
    zookeeper.ASSOCIATING_STATE: "associating",
    zookeeper.AUTH_FAILED_STATE: "auth-failed",
    zookeeper.CONNECTED_STATE: "connected",
    zookeeper.CONNECTING_STATE: "connecting",
    zookeeper.EXPIRED_SESSION_STATE: "expired",
}

# Mapping of event type to human string.
TYPE_NAME_MAPPING = {
    zookeeper.NOTWATCHING_EVENT: "not-watching",
    zookeeper.SESSION_EVENT: "session",
    zookeeper.CREATED_EVENT: "created",
    zookeeper.DELETED_EVENT: "deleted",
    zookeeper.CHANGED_EVENT: "changed",
    zookeeper.CHILD_EVENT: "child",
}
class TimeoutException( zookeeper.ZooKeeperException):
    pass

def logevent(h,typ, state, path):
    logger.debug("event,handle:%d, type:%s, state:%s, path:%s", h, TYPE_NAME_MAPPING.get(typ, "unknown"), STATE_NAME_MAPPING.get(state, "unknown"), path)

class ZKClient:
    def __init__(self, servers, timeout= 10):
        self.timeout = timeout
        self.connected = False
        self.handle = -1
        self.servers = servers
        self.watchers  = set()
        self._lock = threading.Lock()
        self.conn_cv = threading.Condition()

    def start(self):
        self.handle = zookeeper.init(self.servers, self.connection_watcher, self.timeout * 1000)
        self.conn_cv.acquire()
        self.conn_cv.wait(self.timeout)
        self.conn_cv.release()
        if not self.connected:
            raise TimeoutException

    def stop(self):
        return zookeeper.close(self.handle)

    def connection_watcher(self, h, typ, state, path):
        logevent(h, typ, state, path)
        if  typ == zookeeper.SESSION_EVENT:
            if state == zookeeper.CONNECTED_STATE:
                self.handle = h
                with self._lock:
                    self.connected = True
                    watchers = list(self.watchers)
                for watcher in watchers:
                    watcher.watch()

        self.conn_cv.acquire()
        self.conn_cv.notifyAll()
        self.conn_cv.release()

    def del_watcher(self, watcher):
        with self._lock:
            self.watchers.discard(watcher)

    def add_watcher(self, watcher):
        with self._lock:
            self.watchers.add(watcher)
        if self.connected:
            watcher.watch()

class DataWatch:
    def __init__(self, client, path, func):
        self._client = client
        self._path = path
        self._func = func
        self._stopped = False
        client.add_watcher(self)

    def watcher(self, h, typ, state, path):
        logevent(h, typ, state, path)
        self.watch()

    def _do(self):
        data, stat = zookeeper.get(self._client.handle, self._path, self.watcher)
        return self._func(data, stat)

    def watch(self):
        if self._stopped:
            return
        try:
            result = self._do()
            if result is False:
                self._stopped = True
        except zookeeper.NoNodeException:
            raise
        except zookeeper.ZooKeeperException as e:
            logger.error("ZooKeeperException, type:%s, msg: %s", type(e), e)


class ChildrenWatch(DataWatch):
    def _do(self):
        children = zookeeper.get_children(self._client.handle, self._path, self.watcher)
        return self._func(children)



########NEW FILE########
__FILENAME__ = rdd
import sys
import os, os.path
import time
import socket
import csv
from cStringIO import StringIO
import itertools
import operator
import math
import cPickle
import random
import bz2
import gzip
import zlib
import logging
from copy import copy
import shutil
import heapq
import struct

from dpark.serialize import load_func, dump_func
from dpark.dependency import *
from dpark.util import spawn, chain
from dpark.shuffle import Merger, CoGroupMerger
from dpark.env import env
from dpark import moosefs

logger = logging.getLogger("rdd")

class Split(object):
    def __init__(self, idx):
        self.index = idx

def cached(func):
    def getstate(self):
        d = getattr(self, '_pickle_cache', None)
        if d is None:
            d = func(self)
            self._pickle_cache = d
        return d
    return getstate

class RDD(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.id = RDD.newId()
        self._splits = []
        self.dependencies = []
        self.aggregator = None
        self._partitioner = None
        self.shouldCache = False
        self.snapshot_path = None
        ctx.init()
        self.err = ctx.options.err
        self.mem = ctx.options.mem

    nextId = 0
    @classmethod
    def newId(cls):
        cls.nextId += 1
        return cls.nextId

    @cached
    def __getstate__(self):
        d = dict(self.__dict__)
        d.pop('dependencies', None)
        d.pop('_splits', None)
        d.pop('ctx', None)
        return d

    def __len__(self):
        return len(self.splits)

    def __getslice__(self, i,j):
        return SliceRDD(self, i, j)

    def mergeSplit(self, splitSize=None, numSplits=None):
        return MergedRDD(self, splitSize, numSplits)

    @property
    def splits(self):
        return self._splits

    def compute(self, split):
        raise NotImplementedError

    @property
    def partitioner(self):
        return self._partitioner

    def _preferredLocations(self, split):
        return []

    def cache(self):
        self.shouldCache = True
        self._pickle_cache = None # clear pickle cache
        return self

    def preferredLocations(self, split):
        if self.shouldCache:
            locs = env.cacheTracker.getCachedLocs(self.id, split.index)
            if locs:
                return locs
        return self._preferredLocations(split)

    def snapshot(self, path=None):
        if path is None:
            path = self.ctx.options.snapshot_dir
        if path:
            ident = '%d_%x' % (self.id, hash(str(self)))
            path = os.path.join(path, ident)
            if not os.path.exists(path):
                try: os.makedirs(path)
                except OSError: pass
            self.snapshot_path = path
        return self

    def iterator(self, split):
        if self.snapshot_path:
            p = os.path.join(self.snapshot_path, str(split.index))
            if os.path.exists(p):
                v = cPickle.loads(open(p).read())
            else:
                v = list(self.compute(split))
                with open(p, 'w') as f:
                    f.write(cPickle.dumps(v))
            return v

        if self.shouldCache:
            return env.cacheTracker.getOrCompute(self, split)
        else:
            return self.compute(split)

    def map(self, f):
        return MappedRDD(self, f)

    def flatMap(self, f):
        return FlatMappedRDD(self, f)

    def filter(self, f):
        return FilteredRDD(self, f)

    def sample(self, faction, withReplacement=False, seed=12345):
        return SampleRDD(self, faction, withReplacement, seed)

    def union(self, rdd):
        return UnionRDD(self.ctx, [self, rdd])

    def sort(self, key=lambda x:x, reverse=False, numSplits=None, taskMemory=None):
        if not len(self):
            return self
        if len(self) == 1:
            return self.mapPartitions(lambda it: sorted(it, key=key, reverse=reverse))
        if numSplits is None:
            numSplits = min(self.ctx.defaultMinSplits, len(self))
        n = numSplits * 10 / len(self)
        samples = self.mapPartitions(lambda x:itertools.islice(x, n)).map(key).collect()
        keys = sorted(samples, reverse=reverse)[5::10][:numSplits-1]
        parter = RangePartitioner(keys, reverse=reverse)
        aggr = MergeAggregator()
        parted = ShuffledRDD(self.map(lambda x:(key(x),x)), aggr, parter, taskMemory).flatMap(lambda (x,y):y)
        return parted.mapPartitions(lambda x:sorted(x, key=key, reverse=reverse))

    def glom(self):
        return GlommedRDD(self)

    def cartesian(self, other):
        return CartesianRDD(self, other)

    def zipWith(self, other):
        return ZippedRDD(self.ctx, [self, other])

    def groupBy(self, f, numSplits=None):
        if numSplits is None:
            numSplits = min(self.ctx.defaultMinSplits, len(self))
        return self.map(lambda x: (f(x), x)).groupByKey(numSplits)

    def pipe(self, command, quiet=False):
        if isinstance(command, str):
            command = command.split(' ')
        return PipedRDD(self, command, quiet)

    def fromCsv(self, dialect='excel'):
        return CSVReaderRDD(self, dialect)

    def mapPartitions(self, f):
        return MapPartitionsRDD(self, f)
    mapPartition = mapPartitions

    def foreach(self, f):
        def mf(it):
            for i in it:
                f(i)
        list(self.ctx.runJob(self, mf))

    def foreachPartition(self, f):
        list(self.ctx.runJob(self, f))

    def enumeratePartition(self):
        return EnumeratePartitionsRDD(self, lambda x,it: itertools.imap(lambda y:(x,y), it))

    def enumerate(self):
        return EnumeratePartitionsRDD(self, lambda x,it:
                                      itertools.imap(lambda (y,z):((x,y),z), enumerate(it)))


    def collect(self):
        return sum(self.ctx.runJob(self, lambda x:list(x)), [])

    def __iter__(self):
        return self.collect()

    def reduce(self, f):
        def reducePartition(it):
            if self.err < 1e-8:
                try:
                    return [reduce(f, it)]
                except TypeError:
                    return []

            s = None
            total, err = 0, 0
            for v in it:
                try:
                    total += 1
                    if s is None:
                        s = v
                    else:
                        s = f(s, v)
                except Exception, e:
                    logging.warning("skip bad record %s: %s", v, e)
                    err += 1
                    if total > 100 and err > total * self.err * 10:
                        raise Exception("too many error occured: %s" % (float(err)/total))

            if err > total * self.err:
                raise Exception("too many error occured: %s" % (float(err)/total))

            return [s] if s is not None else []

        return reduce(f, chain(self.ctx.runJob(self, reducePartition)))

    def uniq(self, numSplits=None, taskMemory=None):
        g = self.map(lambda x:(x,None)).reduceByKey(lambda x,y:None, numSplits, taskMemory)
        return g.map(lambda (x,y):x)

    def top(self, n=10, key=None, reverse=False):
        if reverse:
            def topk(it):
                return heapq.nsmallest(n, it, key)
        else:
            def topk(it):
                return heapq.nlargest(n, it, key)
        return topk(sum(self.ctx.runJob(self, topk), []))

    def hot(self, n=10, numSplits=None, taskMemory=None):
        st = self.map(lambda x:(x,1)).reduceByKey(lambda x,y:x+y, numSplits, taskMemory)
        return st.top(n, key=lambda x:x[1])

    def fold(self, zero, f):
        '''Aggregate the elements of each partition, and then the
        results for all the partitions, using a given associative
        function and a neutral "zero value". The function op(t1, t2)
        is allowed to modify t1 and return it as its result value to
        avoid object allocation; however, it should not modify t2.'''
        return reduce(f,
                      self.ctx.runJob(self, lambda x: reduce(f, x, copy(zero))),
                      zero)

    def aggregate(self, zero, seqOp, combOp):
        '''Aggregate the elements of each partition, and then the
        results for all the partitions, using given combine functions
        and a neutral "zero value". This function can return a
        different result type, U, than the type of this RDD, T. Thus,
        we need one operation for merging a T into an U (seqOp(U, T))
        and one operation for merging two U's (combOp(U, U)). Both of
        these functions are allowed to modify and return their first
        argument instead of creating a new U to avoid memory
        allocation.'''
        return reduce(combOp,
                      self.ctx.runJob(self, lambda x: reduce(seqOp, x, copy(zero))),
                      zero)

    def count(self):
        return sum(self.ctx.runJob(self, lambda x: sum(1 for i in x)))

    def toList(self):
        return self.collect()

    def take(self, n):
        if n == 0: return []
        r = []
        p = 0
        while len(r) < n and p < len(self):
            res = list(self.ctx.runJob(self, lambda x: list(itertools.islice(x, n - len(r))), [p], True))[0]
            if res:
                r.extend(res)
            p += 1
        return r

    def first(self):
        r = self.take(1)
        if r: return r[0]

    def saveAsTextFile(self, path, ext='', overwrite=True, compress=False):
        return OutputTextFileRDD(self, path, ext, overwrite, compress=compress).collect()

    def saveAsTextFileByKey(self, path, ext='', overwrite=True, compress=False):
        return MultiOutputTextFileRDD(self, path, ext, overwrite, compress=compress).collect()

    def saveAsCSVFile(self, path, dialect='excel', overwrite=True, compress=False):
        return OutputCSVFileRDD(self, path, dialect, overwrite, compress).collect()

    def saveAsBinaryFile(self, path, fmt, overwrite=True):
        return OutputBinaryFileRDD(self, path, fmt, overwrite).collect()

    def saveAsTableFile(self, path, overwrite=True):
        return OutputTableFileRDD(self, path, overwrite).collect()

    def saveAsBeansdb(self, path, depth=0, overwrite=True, compress=True, raw=False):
        assert depth<=2, 'only support depth<=2 now'
        if len(self) >= 256:
            self = self.mergeSplit(len(self) / 256 + 1)
        return OutputBeansdbRDD(self, path, depth, overwrite, compress, raw).collect()

    def saveAsTabular(self, path, field_names, **kw):
        from dpark.tabular import OutputTabularRDD
        return OutputTabularRDD(self, path, field_names, **kw).collect()

    # Extra functions for (K,V) pairs RDD
    def reduceByKeyToDriver(self, func):
        def mergeMaps(m1, m2):
            for k,v in m2.iteritems():
                m1[k]=func(m1[k], v) if k in m1 else v
            return m1
        return self.map(lambda (x,y):{x:y}).reduce(mergeMaps)

    def combineByKey(self, aggregator, splits=None, taskMemory=None):
        if splits is None:
            splits = min(self.ctx.defaultMinSplits, len(self))
        if type(splits) is int:
            splits = HashPartitioner(splits)
        return ShuffledRDD(self, aggregator, splits, taskMemory)

    def reduceByKey(self, func, numSplits=None, taskMemory=None):
        aggregator = Aggregator(lambda x:x, func, func)
        return self.combineByKey(aggregator, numSplits, taskMemory)

    def groupByKey(self, numSplits=None, taskMemory=None):
        createCombiner = lambda x: [x]
        mergeValue = lambda x,y:x.append(y) or x
        mergeCombiners = lambda x,y: x.extend(y) or x
        aggregator = Aggregator(createCombiner, mergeValue, mergeCombiners)
        return self.combineByKey(aggregator, numSplits, taskMemory)

    def partitionByKey(self, numSplits=None, taskMemory=None):
        return self.groupByKey(numSplits, taskMemory).flatMapValue(lambda x: x)

    def innerJoin(self, other):
        o_b = self.ctx.broadcast(other.collectAsMap())
        r = self.filter(lambda (k,v):k in o_b.value).map(lambda (k,v):(k,(v,o_b.value[k])))
        r.mem += (o_b.bytes * 10) >> 20 # memory used by broadcast obj
        return r

    def update(self, other, replace_only=False, numSplits=None,
               taskMemory=None):
        rdd = self.mapValue(
            lambda val: (val, 1)  # bin('01') for old rdd
        ).union(
            other.mapValue(
                lambda val: (val, 2)  # bin('10') for new rdd
            )
        ).reduceByKey(
            lambda (val_a, rev_a), (val_b, rev_b): (
                (val_b if rev_b > rev_a else val_a), (rev_a | rev_b)
            ),
            numSplits,
            taskMemory
        )
        # rev:
        #   1(01): old value
        #   2(10): new added value
        #   3(11): new updated value
        if replace_only:
            rdd = rdd.filter(
                lambda (key, (val, rev)): rev != 2
            )
        return rdd.mapValue(
            lambda (val, rev): val
        )

    def join(self, other, numSplits=None, taskMemory=None):
        return self._join(other, (), numSplits, taskMemory)

    def leftOuterJoin(self, other, numSplits=None, taskMemory=None):
        return self._join(other, (1,), numSplits, taskMemory)

    def rightOuterJoin(self, other, numSplits=None, taskMemory=None):
        return self._join(other, (2,), numSplits, taskMemory)

    def outerJoin(self, other, numSplits=None, taskMemory=None):
        return self._join(other, (1,2), numSplits, taskMemory)

    def _join(self, other, keeps, numSplits=None, taskMemory=None):
        def dispatch((k,seq)):
            vbuf, wbuf = seq
            if not vbuf and 2 in keeps:
                vbuf.append(None)
            if not wbuf and 1 in keeps:
                wbuf.append(None)
            for vv in vbuf:
                for ww in wbuf:
                    yield (k, (vv, ww))
        return self.cogroup(other, numSplits, taskMemory).flatMap(dispatch)

    def collectAsMap(self):
        d = {}
        for v in self.ctx.runJob(self, lambda x:list(x)):
            d.update(dict(v))
        return d

    def mapValue(self, f):
        return MappedValuesRDD(self, f)

    def flatMapValue(self, f):
        return FlatMappedValuesRDD(self, f)

    def groupWith(self, others, numSplits=None, taskMemory=None):
        if isinstance(others, RDD):
            others = [others]
        part = self.partitioner or HashPartitioner(numSplits or self.ctx.defaultParallelism)
        return CoGroupedRDD([self]+others, part, taskMemory)

    cogroup = groupWith

    def lookup(self, key):
        if self.partitioner:
            index = self.partitioner.getPartition(key)
            def process(it):
                for k,v in it:
                    if k == key:
                        return v
            return list(self.ctx.runJob(self, process, [index], False))[0]
        else:
            raise Exception("lookup() called on an RDD without a partitioner")

    def asTable(self, fields, name=''):
        from dpark.table import TableRDD
        return TableRDD(self, fields, name)

    def batch(self, size):
        def _batch(iterable):
            sourceiter = iter(iterable)
            while True:
                s = list(itertools.islice(sourceiter, size))
                if s:
                    yield s
                else:
                    return

        return self.glom().flatMap(_batch)

    def adcount(self):
        "approximate distinct counting"
        r = self.map(lambda x:(1, x)).adcountByKey(1).collectAsMap()
        return r and r[1] or 0

    def adcountByKey(self, splits=None, taskMemory=None):
        try:
            from pyhll import HyperLogLog
        except ImportError:
            from hyperloglog import HyperLogLog
        def create(v):
            return HyperLogLog([v], 16)
        def combine(s, v):
            return s.add(v) or s
        def merge(s1, s2):
            return s1.update(s2) or s1
        agg = Aggregator(create, combine, merge)
        return self.combineByKey(agg, splits, taskMemory).mapValue(len)


class DerivedRDD(RDD):
    def __init__(self, rdd):
        RDD.__init__(self, rdd.ctx)
        self.prev = rdd
        self.mem = max(self.mem, rdd.mem)
        self.dependencies = [OneToOneDependency(rdd)]

    def __len__(self):
        return len(self.prev)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.prev)

    @property
    def splits(self):
        return self.prev.splits

    def _preferredLocations(self, split):
        return self.prev.preferredLocations(split)


class MappedRDD(DerivedRDD):
    def __init__(self, prev, func=lambda x:x):
        DerivedRDD.__init__(self, prev)
        self.func = func

    def compute(self, split):
        if self.err < 1e-8:
            return (self.func(v) for v in self.prev.iterator(split))
        return self._compute_with_error(split)

    def _compute_with_error(self, split):
        total, err = 0, 0
        for v in self.prev.iterator(split):
            try:
                total += 1
                yield self.func(v)
            except Exception, e:
                logger.warning("ignored record %r: %s", v, e)
                err += 1
                if total > 100 and err > total * self.err * 10:
                    raise Exception("too many error occured: %s" % (float(err)/total))

        if err > total * self.err:
            raise Exception("too many error occured: %s" % (float(err)/total))

    @cached
    def __getstate__(self):
        d = RDD.__getstate__(self)
        del d['func']
        return d, dump_func(self.func)

    def __setstate__(self, state):
        self.__dict__, code = state
        try:
            self.func = load_func(code)
        except Exception:
            print 'load failed', self.__class__, code[:1024]
            raise

class FlatMappedRDD(MappedRDD):
    def compute(self, split):
        if self.err < 1e-8:
            return chain(self.func(v) for v in self.prev.iterator(split))
        return self._compute_with_error(split)

    def _compute_with_error(self, split):
        total, err = 0, 0
        for v in self.prev.iterator(split):
            try:
                total += 1
                for k in self.func(v):
                    yield k
            except Exception, e:
                logger.warning("ignored record %r: %s", v, e)
                err += 1
                if total > 100 and err > total * self.err * 10:
                    raise Exception("too many error occured: %s, %s" % ((float(err)/total), e))

        if err > total * self.err:
            raise Exception("too many error occured: %s, %s" % ((float(err)/total), e))


class FilteredRDD(MappedRDD):
    def compute(self, split):
        if self.err < 1e-8:
            return (v for v in self.prev.iterator(split) if self.func(v))
        return self._compute_with_error(split)

    def _compute_with_error(self, split):
        total, err = 0, 0
        for v in self.prev.iterator(split):
            try:
                total += 1
                if self.func(v):
                    yield v
            except Exception, e:
                logger.warning("ignored record %r: %s", v, e)
                err += 1
                if total > 100 and err > total * self.err * 10:
                    raise Exception("too many error occured: %s" % (float(err)/total))

        if err > total * self.err:
            raise Exception("too many error occured: %s" % (float(err)/total))

class GlommedRDD(DerivedRDD):
    def compute(self, split):
        yield list(self.prev.iterator(split))

class MapPartitionsRDD(MappedRDD):
    def compute(self, split):
        return self.func(self.prev.iterator(split))

class EnumeratePartitionsRDD(MappedRDD):
    def compute(self, split):
        return self.func(split.index, self.prev.iterator(split))

class PipedRDD(DerivedRDD):
    def __init__(self, prev, command, quiet=False, shell=False):
        DerivedRDD.__init__(self, prev)
        self.command = command
        self.quiet = quiet
        self.shell = shell

    def __repr__(self):
        return '<PipedRDD %s %s>' % (' '.join(self.command), self.prev)

    def compute(self, split):
        import subprocess
        devnull = open(os.devnull, 'w')
        p = subprocess.Popen(self.command, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self.quiet and devnull or sys.stderr,
                shell=self.shell)

        def read(stdin):
            try:
                it = iter(self.prev.iterator(split))
                # fetch the first item
                for first in it:
                    break
                else:
                    return
                try:
                    if isinstance(first, str) and first.endswith('\n'):
                        stdin.write(first)
                        stdin.writelines(it)
                    else:
                        stdin.write("%s\n"%first)
                        stdin.writelines("%s\n"%x for x in it)
                except Exception, e:
                    if not (isinstance(e, IOError) and e.errno == 32): # Broken Pipe
                        self.error = e
                        p.kill()
            finally:
                stdin.close()
                devnull.close()

        self.error = None
        spawn(read, p.stdin)
        return self.read(p)

    def read(self, p):
        for line in p.stdout:
            yield line[:-1]
        if self.error:
            raise self.error
        ret = p.wait()
        #if ret:
        #    raise Exception('Subprocess exited with status %d' % ret)

class MappedValuesRDD(MappedRDD):
    @property
    def partitioner(self):
        return self.prev.partitioner

    def compute(self, split):
        func = self.func
        if self.err < 1e-8:
            return ((k,func(v)) for k,v in self.prev.iterator(split))
        return self._compute_with_error(split)

    def _compute_with_error(self, split):
        func = self.func
        total, err = 0, 0
        for k,v in self.prev.iterator(split):
            try:
                total += 1
                yield (k,func(v))
            except Exception, e:
                logger.warning("ignored record %r: %s", v, e)
                err += 1
                if total > 100 and err > total * self.err * 10:
                    raise Exception("too many error occured: %s" % (float(err)/total))

        if err > total * self.err:
            raise Exception("too many error occured: %s" % (float(err)/total))

class FlatMappedValuesRDD(MappedValuesRDD):
    def compute(self, split):
        total, err = 0, 0
        for k,v in self.prev.iterator(split):
            try:
                total += 1
                for vv in self.func(v):
                    yield k,vv
            except Exception, e:
                logger.warning("ignored record %r: %s", v, e)
                err += 1
                if total > 100 and err > total * self.err * 10:
                    raise Exception("too many error occured: %s" % (float(err)/total))

        if err > total * self.err:
            raise Exception("too many error occured: %s" % (float(err)/total))

class ShuffledRDDSplit(Split):
    def __hash__(self):
        return self.index

class ShuffledRDD(RDD):
    def __init__(self, parent, aggregator, part, taskMemory=None):
        RDD.__init__(self, parent.ctx)
        self.parent = parent
        self.numParts = len(parent)
        self.aggregator = aggregator
        self._partitioner = part
        if taskMemory:
            self.mem = taskMemory
        self._splits = [ShuffledRDDSplit(i) for i in range(part.numPartitions)]
        self.shuffleId = self.ctx.newShuffleId()
        self.dependencies = [ShuffleDependency(self.shuffleId,
                parent, aggregator, part)]
        self.name = '<ShuffledRDD %s>' % self.parent

    def __len__(self):
        return self.partitioner.numPartitions

    def __repr__(self):
        return self.name

    @cached
    def __getstate__(self):
        d = RDD.__getstate__(self)
        d.pop('parent', None)
        return d

    def compute(self, split):
        merger = Merger(self.numParts, self.aggregator.mergeCombiners)
        fetcher = env.shuffleFetcher
        fetcher.fetch(self.shuffleId, split.index, merger.merge)
        return merger


class CartesianSplit(Split):
    def __init__(self, idx, s1, s2):
        self.index = idx
        self.s1 = s1
        self.s2 = s2

class CartesianRDD(RDD):
    def __init__(self, rdd1, rdd2):
        RDD.__init__(self, rdd1.ctx)
        self.rdd1 = rdd1
        self.rdd2 = rdd2
        self.mem = max(rdd1.mem, rdd2.mem) * 1.5
        self.numSplitsInRdd2 = n = len(rdd2)
        self._splits = [CartesianSplit(s1.index*n+s2.index, s1, s2)
            for s1 in rdd1.splits for s2 in rdd2.splits]
        self.dependencies = [CartesianDependency(rdd1, True, n),
                             CartesianDependency(rdd2, False, n)]

    def __len__(self):
        return len(self.rdd1) * len(self.rdd2)

    def __repr__(self):
        return '<cartesian %s and %s>' % (self.rdd1, self.rdd2)

    def _preferredLocations(self, split):
        return self.rdd1.preferredLocations(split.s1) + self.rdd2.preferredLocations(split.s2)

    def compute(self, split):
        b = None
        for i in self.rdd1.iterator(split.s1):
            if b is None:
                b = []
                for j in self.rdd2.iterator(split.s2):
                    yield (i, j)
                    b.append(j)
            else:
                for j in b:
                    yield (i,j)

class CoGroupSplitDep: pass
class NarrowCoGroupSplitDep(CoGroupSplitDep):
    def __init__(self, rdd, split):
        self.rdd = rdd
        self.split = split
class ShuffleCoGroupSplitDep(CoGroupSplitDep):
    def __init__(self, shuffleId):
        self.shuffleId = shuffleId

class CoGroupSplit(Split):
    def __init__(self, idx, deps):
        self.index = idx
        self.deps = deps
    def __hash__(self):
        return self.index

class CoGroupAggregator:
    def createCombiner(self, v):
        return [v]
    def mergeValue(self, c, v):
        return c + [v]
    def mergeCombiners(self, c, v):
        return c + v

class CoGroupedRDD(RDD):
    def __init__(self, rdds, partitioner, taskMemory=None):
        RDD.__init__(self, rdds[0].ctx)
        self.len = len(rdds)
        if taskMemory:
            self.mem = taskMemory
        self.aggregator = CoGroupAggregator()
        self._partitioner = partitioner
        self.dependencies = dep = [rdd.partitioner == partitioner
                and OneToOneDependency(rdd)
                or ShuffleDependency(self.ctx.newShuffleId(),
                    rdd, self.aggregator, partitioner)
                for i,rdd in enumerate(rdds)]
        self._splits = [CoGroupSplit(j,
                          [isinstance(dep[i],ShuffleDependency)
                            and ShuffleCoGroupSplitDep(dep[i].shuffleId)
                            or NarrowCoGroupSplitDep(r, r.splits[j])
                            for i,r in enumerate(rdds)])
                        for j in range(partitioner.numPartitions)]
        self.name = ('<CoGrouped of %s>' % (','.join(str(rdd) for rdd in rdds)))[:80]

    def __len__(self):
        return self.partitioner.numPartitions

    def __repr__(self):
        return self.name

    def _preferredLocations(self, split):
        return sum([dep.rdd.preferredLocations(dep.split) for dep in split.deps
                if isinstance(dep, NarrowCoGroupSplitDep)], [])

    def compute(self, split):
        m = CoGroupMerger(self.len)
        for i,dep in enumerate(split.deps):
            if isinstance(dep, NarrowCoGroupSplitDep):
                m.append(i, dep.rdd.iterator(dep.split))
            elif isinstance(dep, ShuffleCoGroupSplitDep):
                def merge(items):
                    m.extend(i, items)
                env.shuffleFetcher.fetch(dep.shuffleId, split.index, merge)
        return m


class SampleRDD(DerivedRDD):
    def __init__(self, prev, frac, withReplacement, seed):
        DerivedRDD.__init__(self, prev)
        self.frac = frac
        self.withReplacement = withReplacement
        self.seed = seed

    def __repr__(self):
        return '<SampleRDD(%s) of %s>' % (self.frac, self.prev)

    def compute(self, split):
        rd = random.Random(self.seed + split.index)
        if self.withReplacement:
            olddata = list(self.prev.iterator(split))
            sampleSize = int(math.ceil(len(olddata) * self.frac))
            for i in xrange(sampleSize):
                yield rd.choice(olddata)
        else:
            for i in self.prev.iterator(split):
                if rd.random() <= self.frac:
                    yield i


class UnionSplit(Split):
    def __init__(self, idx, rdd, split):
        self.index = idx
        self.rdd = rdd
        self.split = split

class UnionRDD(RDD):
    def __init__(self, ctx, rdds):
        RDD.__init__(self, ctx)
        self.mem = rdds[0].mem if rdds else self.mem
        pos = 0
        for rdd in rdds:
            self._splits.extend([UnionSplit(pos + i, rdd, sp) for i, sp in enumerate(rdd.splits)])
            self.dependencies.append(RangeDependency(rdd, 0, pos, len(rdd)))
            pos += len(rdd)
        self.name = '<UnionRDD %d %s ...>' % (len(rdds), ','.join(str(rdd) for rdd in rdds[:1]))

    def __repr__(self):
        return self.name

    def _preferredLocations(self, split):
        return split.rdd.preferredLocations(split.split)

    def compute(self, split):
        return split.rdd.iterator(split.split)

class SliceRDD(RDD):
    def __init__(self, rdd, i, j):
        RDD.__init__(self, rdd.ctx)
        self.rdd = rdd
        self.mem = rdd.mem
        if j > len(rdd):
            j = len(rdd)
        self.i = i
        self.j = j
        self._splits = rdd.splits[i:j]
        self.dependencies = [RangeDependency(rdd, i, 0, j-i)]

    def __len__(self):
        return self.j - self.i

    def __repr__(self):
        return '<SliceRDD [%d:%d] of %s>' % (self.i, self.j, self.rdd)

    def _preferredLocations(self, split):
        return self.rdd.preferredLocations(split)

    def compute(self, split):
        return self.rdd.iterator(split)


class MultiSplit(Split):
    def __init__(self, index, splits):
        self.index = index
        self.splits = splits

class MergedRDD(RDD):
    def __init__(self, rdd, splitSize=None, numSplits=None):
        RDD.__init__(self, rdd.ctx)
        if splitSize is None:
            splitSize = (len(rdd) + numSplits - 1) / numSplits
        numSplits = (len(rdd) + splitSize - 1) / splitSize
        self.rdd = rdd
        self.mem = rdd.mem
        self.splitSize = splitSize
        self.numSplits = numSplits

        splits = rdd.splits
        self._splits = [MultiSplit(i, splits[i*splitSize:(i+1)*splitSize])
               for i in range(numSplits)]
        self.dependencies = [OneToRangeDependency(rdd, splitSize, len(rdd))]

    def __len__(self):
        return self.numSplits

    def __repr__(self):
        return '<MergedRDD %s:1 of %s>' % (self.splitSize, self.rdd)

    def _preferredLocations(self, split):
        return sum([self.rdd.preferredLocations(sp) for sp in split.splits], [])

    def compute(self, split):
        return chain(self.rdd.iterator(sp) for sp in split.splits)


class ZippedRDD(RDD):
    def __init__(self, ctx, rdds):
        assert len(set([len(rdd) for rdd in rdds])) == 1, 'rdds must have the same length'
        RDD.__init__(self, ctx)
        self.rdds = rdds
        self.mem = max(r.mem for r in rdds)
        self._splits = [MultiSplit(i, splits)
                for i, splits in enumerate(zip(*[rdd.splits for rdd in rdds]))]
        self.dependencies = [OneToOneDependency(rdd) for rdd in rdds]

    def __len__(self):
        return len(self.rdds[0])

    def __repr__(self):
        return '<Zipped %s>' % (','.join(str(rdd) for rdd in self.rdds))

    def _preferredLocations(self, split):
        return sum([rdd.preferredLocations(sp)
            for rdd,sp in zip(self.rdds, split.splits)], [])

    def compute(self, split):
        return itertools.izip(*[rdd.iterator(sp)
            for rdd, sp in zip(self.rdds, split.splits)])


class CSVReaderRDD(DerivedRDD):
    def __init__(self, prev, dialect='excel'):
        DerivedRDD.__init__(self, prev)
        self.dialect = dialect

    def __repr__(self):
        return '<CSVReaderRDD %s of %s>' % (self.dialect, self.prev)

    def compute(self, split):
        return csv.reader(self.prev.iterator(split), self.dialect)


class ParallelCollectionSplit:
    def __init__(self, index, values):
        self.index = index
        self.values = values

class ParallelCollection(RDD):
    def __init__(self, ctx, data, numSlices, taskMemory=None):
        RDD.__init__(self, ctx)
        self.size = len(data)
        if taskMemory:
            self.mem = taskMemory
        slices = self.slice(data, max(1, min(self.size, numSlices)))
        self._splits = [ParallelCollectionSplit(i, slices[i])
                for i in range(len(slices))]
        self.dependencies = []

    def __repr__(self):
        return '<ParallelCollection %d>' % self.size

    def compute(self, split):
        return split.values

    @classmethod
    def slice(cls, data, numSlices):
        if numSlices <= 0:
            raise ValueError("invalid numSlices %d" % numSlices)
        m = len(data)
        if not m:
            return [[]]
        n = m / numSlices
        if m % numSlices != 0:
            n += 1
        if isinstance(data, xrange):
            first = data[0]
            last = data[m-1]
            step = (last - first) / (m-1)
            nstep = step * n
            slices = [xrange(first+i*nstep, first+(i+1)*nstep, step)
                for i in range(numSlices-1)]
            slices.append(xrange(first+(numSlices-1)*nstep,
                min(last+step, first+numSlices*nstep), step))
            return slices
        if not isinstance(data, list):
            data = list(data)
        return [data[i*n : i*n+n] for i in range(numSlices)]



class PartialSplit(Split):
    def __init__(self, index, begin, end):
        self.index = index
        self.begin = begin
        self.end = end

class TextFileRDD(RDD):

    DEFAULT_SPLIT_SIZE = 64*1024*1024

    def __init__(self, ctx, path, numSplits=None, splitSize=None):
        RDD.__init__(self, ctx)
        self.path = path
        self.fileinfo = moosefs.open_file(path)
        self.size = size = self.fileinfo.length if self.fileinfo else os.path.getsize(path)

        if splitSize is None:
            if numSplits is None:
                splitSize = self.DEFAULT_SPLIT_SIZE
            else:
                splitSize = size / numSplits or self.DEFAULT_SPLIT_SIZE
        n = size / splitSize
        if size % splitSize > 0:
            n += 1
        self.splitSize = splitSize
        self.len = n
        self._splits = [PartialSplit(i, i*splitSize, min(size, (i+1) * splitSize))
                    for i in range(self.len)]

    def __len__(self):
        return self.len

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.path)

    def _preferredLocations(self, split):
        if not self.fileinfo:
            return []

        if self.splitSize != moosefs.CHUNKSIZE:
            start = split.begin / moosefs.CHUNKSIZE
            end = (split.end + moosefs.CHUNKSIZE - 1)/ moosefs.CHUNKSIZE
            return sum((self.fileinfo.locs(i) for i in range(start, end)), [])
        else:
            return self.fileinfo.locs(split.begin / self.splitSize)

    def open_file(self):
        if self.fileinfo:
            return moosefs.ReadableFile(self.fileinfo)
        else:
            return open(self.path, 'r', 4096 * 1024)

    def compute(self, split):
        f = self.open_file()
        #if len(self) == 1 and split.index == 0 and split.begin == 0:
        #    return f

        start = split.begin
        end = split.end
        if start > 0:
            f.seek(start-1)
            byte = f.read(1)
            while byte != '\n':
                byte = f.read(1)
                if not byte:
                    return []
                start += 1

        if start >= end:
            return []

        #if self.fileinfo:
        #    # cut by end
        #    if end < self.fileinfo.length:
        #        f.seek(end-1)
        #        while f.read(1) not in ('', '\n'):
        #            end += 1
        #        f.length = end
        #    f.seek(start)
        #    return f

        return self.read(f, start, end)

    def read(self, f, start, end):
        for line in f:
            yield line[:-1]
            start += len(line)
            if start >= end: break
        f.close()


class PartialTextFileRDD(TextFileRDD):
    def __init__(self, ctx, path, firstPos, lastPos, splitSize=None, numSplits=None):
        RDD.__init__(self, ctx)
        self.path = path
        self.fileinfo = moosefs.open_file(path)
        self.firstPos = firstPos
        self.lastPos = lastPos
        self.size = size = lastPos - firstPos

        if splitSize is None:
            if numSplits is None:
                splitSize = self.DEFAULT_SPLIT_SIZE
            else:
                splitSize = size / numSplits or self.DEFAULT_SPLIT_SIZE
        self.splitSize = splitSize
        if size <= splitSize:
            self._splits = [PartialSplit(0, firstPos, lastPos)]
        else:
            first_edge = firstPos / splitSize * splitSize + splitSize
            last_edge = (lastPos-1) / splitSize * splitSize
            ns = (last_edge - first_edge) / splitSize
            self._splits = [PartialSplit(0, firstPos, first_edge)] + [
                PartialSplit(i+1, first_edge + i*splitSize, first_edge + (i+1) * splitSize)
                    for i in  range(ns)
                 ] + [PartialSplit(ns+1, last_edge, lastPos)]
        self.len = len(self._splits)

    def __repr__(self):
        return '<%s %s (%d-%d)>' % (self.__class__.__name__, self.path, self.firstPos, self.lastPos)


class GZipFileRDD(TextFileRDD):
    "the gziped file must be seekable, compressed by pigz -i"
    BLOCK_SIZE = 64 << 10
    DEFAULT_SPLIT_SIZE = 32 << 20

    def __init__(self, ctx, path, splitSize=None):
        TextFileRDD.__init__(self, ctx, path, None, splitSize)

    def find_block(self, f, pos):
        f.seek(pos)
        block = f.read(32*1024)
        if len(block) < 4:
            f.seek(0, 2)
            return f.tell() # EOF
        ENDING = '\x00\x00\xff\xff'
        while True:
            p = block.find(ENDING)
            while p < 0:
                pos += max(len(block) - 3, 0)
                block = block[-3:] + f.read(32<<10)
                if len(block) < 4:
                    return pos + 3 # EOF
                p = block.find(ENDING)
            pos += p + 4
            block = block[p+4:]
            if len(block) < 4096:
                block += f.read(4096)
                if not block:
                    return pos # EOF
            try:
                if zlib.decompressobj(-zlib.MAX_WBITS).decompress(block):
                    return pos # FOUND
            except Exception, e:
                pass

    def compute(self, split):
        f = self.open_file()
        last_line = ''
        if split.index == 0:
            zf = gzip.GzipFile(fileobj=f)
            zf._read_gzip_header()
            start = f.tell()
        else:
            start = self.find_block(f, split.index * self.splitSize)
            if start >= split.index * self.splitSize + self.splitSize:
                return
            for i in xrange(1, 100):
                if start - i * self.BLOCK_SIZE <= 4:
                    break
                last_block = self.find_block(f, start - i * self.BLOCK_SIZE)
                if last_block < start:
                    f.seek(last_block)
                    d = f.read(start - last_block)
                    dz = zlib.decompressobj(-zlib.MAX_WBITS)
                    last_line = dz.decompress(d).split('\n')[-1]
                    if last_line.endswith('\n'):
                        last_line = ''
                    break

        end = self.find_block(f, split.index * self.splitSize + self.splitSize)
        # TODO: speed up
        f.seek(start)
        if self.fileinfo:
            f.length = end
        dz = zlib.decompressobj(-zlib.MAX_WBITS)
        skip_first = False
        while start < end:
            d = f.read(min(64<<10, end-start))
            start += len(d)
            if not d: break

            try:
                io = StringIO(dz.decompress(d))
            except Exception, e:
                if self.err < 1e-6:
                    logger.error("failed to decompress file: %s", self.path)
                    raise
                old = start
                start = self.find_block(f, start)
                f.seek(start)
                logger.error("drop corrupted block (%d bytes) in %s",
                        start - old + len(d), self.path)
                skip_first = True
                continue

            last_line += io.readline()
            if skip_first:
                skip_first = False
            elif last_line.endswith('\n'):
                yield last_line[:-1]
            last_line = ''

            ll = list(io)
            if not ll: continue

            last_line = ll.pop()
            for line in ll:
                yield line[:-1]
            if last_line.endswith('\n'):
                yield last_line[:-1]
                last_line = ''

        f.close()


class TableFileRDD(TextFileRDD):

    DEFAULT_SPLIT_SIZE = 32 << 20

    def __init__(self, ctx, path, splitSize=None):
        TextFileRDD.__init__(self, ctx, path, None, splitSize)

    def find_magic(self, f, pos, magic):
        f.seek(pos)
        block = f.read(32*1024)
        if len(block) < len(magic):
            return -1
        p = block.find(magic)
        while p < 0:
            pos += len(block) - len(magic) + 1
            block = block[1 - len(magic):] + f.read(32<<10)
            if len(block) == len(magic) - 1:
                return -1
            p = block.find(magic)
        return pos + p

    def compute(self, split):
        import msgpack
        f = self.open_file()
        magic = f.read(8)
        start = split.index * self.splitSize
        end = (split.index + 1) * self.splitSize
        start = self.find_magic(f, start, magic)
        if start < 0:
            return
        f.seek(start)
        hdr_size = 12
        while start < end:
            m = f.read(len(magic))
            if m != magic:
                break
            compressed, count, size = struct.unpack("III", f.read(hdr_size))
            d = f.read(size)
            assert len(d) == size, 'unexpected end'
            if compressed:
                d = zlib.decompress(d)
            for r in msgpack.Unpacker(StringIO(d)):
                yield r
            start += len(magic) + hdr_size + size
        f.close()


class BZip2FileRDD(TextFileRDD):
    "the bzip2ed file must be seekable, compressed by pbzip2"

    DEFAULT_SPLIT_SIZE = 32*1024*1024
    BLOCK_SIZE = 9000

    def __init__(self, ctx, path, numSplits=None, splitSize=None):
        TextFileRDD.__init__(self, ctx, path, numSplits, splitSize)

    def compute(self, split):
        f = self.open_file()
        magic = f.read(10)
        f.seek(split.index * self.splitSize)
        d = f.read(self.splitSize)
        fp = d.find(magic)
        if fp > 0:
            d = d[fp:] # drop end of last block

        # real all the block
        nd = f.read(self.BLOCK_SIZE)
        np = nd.find(magic)
        while nd and np < 0:
            t = f.read(len(nd))
            if not t: break
            nd += t
            np = nd.find(magic)
        d += nd[:np] if np >= 0 else nd
        f.close()

        last_line = None if split.index > 0 else ''
        while d:
            try:
                io = StringIO(bz2.decompress(d))
            except IOError, e:
                #bad position, skip it
                pass
            else:
                if last_line is None:
                    io.readline() # skip the first line
                    last_line = ''
                else:
                    last_line += io.readline()
                    if last_line.endswith('\n'):
                        yield last_line[:-1]
                        last_line = ''

                for line in io:
                    if line.endswith('\n'): # drop last line
                        yield line[:-1]
                    else:
                        last_line = line

            np = d.find(magic, len(magic))
            if np <= 0:
                break
            d = d[np:]


class BinaryFileRDD(TextFileRDD):
    def __init__(self, ctx, path, fmt=None, length=None, numSplits=None, splitSize=None):
        TextFileRDD.__init__(self, ctx, path, numSplits, splitSize)
        self.fmt = fmt
        if fmt:
            length = struct.calcsize(fmt)
        self.length = length
        assert length, "fmt or length must been provided"

        self.splitSize = max(self.splitSize / length, 1) * length
        n = self.size / self.splitSize
        if self.size % self.splitSize > 0:
            n += 1
        self.len = n

    def __repr__(self):
        return '<BinaryFileRDD(%s) %s>' % (self.fmt, self.path)

    def compute(self, split):
        start = split.index * self.splitSize
        end = min(start + self.splitSize, self.size)

        f = self.open_file()
        f.seek(start)
        rlen = self.length
        fmt = self.fmt
        for i in xrange((end - start) / rlen):
            d = f.read(rlen)
            if len(d) < rlen: break
            if fmt:
                d = struct.unpack(fmt, d)
            yield d


class OutputTextFileRDD(DerivedRDD):
    def __init__(self, rdd, path, ext='', overwrite=False, compress=False):
        if os.path.exists(path):
            if not os.path.isdir(path):
                raise Exception("output must be dir")
            if overwrite:
                for n in os.listdir(path):
                    p = os.path.join(path, n)
                    if os.path.isdir(p):
                        shutil.rmtree(p)
                    else:
                        os.remove(p)
        else:
            os.makedirs(path)

        DerivedRDD.__init__(self, rdd)
        self.path = os.path.abspath(path)
        if ext and not ext.startswith('.'):
            ext = '.' + ext
        if compress and not ext.endswith('gz'):
            ext += '.gz'
        self.ext = ext
        self.overwrite = overwrite
        self.compress = compress

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self.path, self.prev)

    def compute(self, split):
        path = os.path.join(self.path,
            "%04d%s" % (split.index, self.ext))
        if os.path.exists(path) and not self.overwrite:
            return
        tpath = os.path.join(self.path,
            ".%04d%s.%s.%d.tmp" % (split.index, self.ext,
            socket.gethostname(), os.getpid()))
        try:
            try:
                f = open(tpath,'w', 4096 * 1024 * 16)
            except IOError:
                time.sleep(1) # there are dir cache in mfs for 1 sec
                f = open(tpath,'w', 4096 * 1024 * 16)
            if self.compress:
                have_data = self.write_compress_data(f, self.prev.iterator(split))
            else:
                have_data = self.writedata(f, self.prev.iterator(split))
            f.close()
            if have_data and not os.path.exists(path):
                os.rename(tpath, path)
                yield path
        finally:
            try:
                os.remove(tpath)
            except:
                pass

    def writedata(self, f, lines):
        it = iter(lines)
        try:
            line = it.next()
        except StopIteration:
            return False
        f.write(line)
        if line.endswith('\n'):
            f.write(''.join(it))
        else:
            f.write('\n')
            s = '\n'.join(it)
            if s:
                f.write(s)
                f.write('\n')
        return True

    def write_compress_data(self, f, lines):
        empty = True
        f = gzip.GzipFile(filename='', mode='w', fileobj=f)
        size = 0
        for line in lines:
            f.write(line)
            if not line.endswith('\n'):
                f.write('\n')
            size += len(line) + 1
            if size >= 256 << 10:
                f.flush()
                f.compress = zlib.compressobj(9, zlib.DEFLATED,
                    -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
                size = 0
            empty = False
        if not empty:
            f.flush()
        return not empty

class MultiOutputTextFileRDD(OutputTextFileRDD):
    MAX_OPEN_FILES = 512
    BLOCK_SIZE = 256 << 10

    def get_tpath(self, key):
        tpath = self.paths.get(key)
        if not tpath:
            dpath = os.path.join(self.path, str(key))
            if not os.path.exists(dpath):
                try: os.mkdir(dpath)
                except: pass
            tpath = os.path.join(dpath,
                ".%04d%s.%s.%d.tmp" % (self.split.index, self.ext,
                socket.gethostname(), os.getpid()))
            self.paths[key] = tpath
        return tpath

    def get_file(self, key):
        f = self.files.get(key)
        if f is None or self.compress and f.fileobj is None:
            tpath = self.get_tpath(key)
            try:
                nf = open(tpath,'a+', 4096 * 1024)
            except IOError:
                time.sleep(1) # there are dir cache in mfs for 1 sec
                nf = open(tpath,'a+', 4096 * 1024)
            if self.compress:
                if f:
                    f.fileobj = nf
                else:
                    f = gzip.GzipFile(filename='', mode='a+', fileobj=nf)
                f.myfileobj = nf # force f.myfileobj.close() in f.close()
            else:
                f = nf
            self.files[key] = f
        return f

    def flush_file(self, key, f):
        f.flush()
        if self.compress:
            f.compress = zlib.compressobj(9, zlib.DEFLATED,
                -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)

        if len(self.files) > self.MAX_OPEN_FILES:
            if self.compress:
                open_files = sum(1 for f in self.files.values() if f.fileobj is not None)
                if open_files > self.MAX_OPEN_FILES:
                    f.fileobj.close()
                    f.fileobj = None
            else:
                f.close()
                self.files.pop(key)

    def compute(self, split):
        self.split = split
        self.paths = {}
        self.files = {}

        buffers = {}
        try:
            for k, v in self.prev.iterator(split):
                b = buffers.get(k)
                if b is None:
                    b = StringIO()
                    buffers[k] = b

                b.write(v)
                if not v.endswith('\n'):
                    b.write('\n')

                if b.tell() > self.BLOCK_SIZE:
                    f = self.get_file(k)
                    f.write(b.getvalue())
                    self.flush_file(k, f)
                    del buffers[k]

            for k, b in buffers.items():
                f = self.get_file(k)
                f.write(b.getvalue())
                f.close()
                del self.files[k]

            for k, f in self.files.items():
                if self.compress:
                    f = self.get_file(k) # make sure fileobj is open
                f.close()

            for k, tpath in self.paths.items():
                path = os.path.join(self.path, str(k), "%04d%s" % (split.index, self.ext))
                if not os.path.exists(path):
                    os.rename(tpath, path)
                    yield path
        finally:
            for k, tpath in self.paths.items():
                try:
                    os.remove(tpath)
                except:
                    pass


class OutputCSVFileRDD(OutputTextFileRDD):
    def __init__(self, rdd, path, dialect, overwrite, compress):
        OutputTextFileRDD.__init__(self, rdd, path, '.csv', overwrite, compress)
        self.dialect = dialect

    def writedata(self, f, rows):
        writer = csv.writer(f, self.dialect)
        empty = True
        for row in rows:
            if not isinstance(row, (tuple, list)):
                row = (row,)
            writer.writerow(row)
            empty = False
        return not empty

    def write_compress_data(self, f, rows):
        empty = True
        f = gzip.GzipFile(filename='', mode='w', fileobj=f)
        writer = csv.writer(f, self.dialect)
        last_flush = 0
        for row in rows:
            if not isinstance(row, (tuple, list)):
                row = (row,)
            writer.writerow(row)
            empty = False
            if f.tell() - last_flush >= 256 << 10:
                f.flush()
                f.compress = zlib.compressobj(9, zlib.DEFLATED,
                    -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
                last_flush = f.tell()
        if not empty:
            f.flush()
        return not empty

class OutputBinaryFileRDD(OutputTextFileRDD):
    def __init__(self, rdd, path, fmt, overwrite):
        OutputTextFileRDD.__init__(self, rdd, path, '.bin', overwrite)
        self.fmt = fmt

    def writedata(self, f, rows):
        empty = True
        for row in rows:
            if isinstance(row, (tuple, list)):
                f.write(struct.pack(self.fmt, *row))
            else:
                f.write(struct.pack(self.fmt, row))
            empty = False
        return not empty

class OutputTableFileRDD(OutputTextFileRDD):
    MAGIC = '\x00\xDE\x00\xAD\xFF\xBE\xFF\xEF'
    BLOCK_SIZE = 256 << 10 # 256K

    def __init__(self, rdd, path, overwrite=True, compress=True):
        OutputTextFileRDD.__init__(self, rdd, path, ext='.tab', overwrite=overwrite, compress=False)
        self.compress = compress

    def writedata(self, f, rows):
        import msgpack
        def flush(buf):
            d = buf.getvalue()
            if self.compress:
                d = zlib.compress(d, 1)
            f.write(self.MAGIC)
            f.write(struct.pack("III", self.compress, count, len(d)))
            f.write(d)

        count, buf = 0, StringIO()
        for row in rows:
            msgpack.pack(row, buf)
            count += 1
            if buf.tell() > self.BLOCK_SIZE:
                flush(buf)
                count, buf = 0, StringIO()

        if count > 0:
            flush(buf)

        return f.tell() > 0

    write_compress_data = writedata

#
# Beansdb
#
import marshal
import binascii
try:
    import quicklz
except ImportError:
    quicklz = None

try:
    from fnv1a import get_hash
    from fnv1a import get_hash_beansdb
    def fnv1a(d):
        return get_hash(d) & 0xffffffff
    def fnv1a_beansdb(d):
        return get_hash_beansdb(d) & 0xffffffff
except ImportError:
    FNV_32_PRIME = 0x01000193
    FNV_32_INIT = 0x811c9dc5
    def fnv1a(d):
        h = FNV_32_INIT
        for c in d:
            h ^= ord(c)
            h *= FNV_32_PRIME
            h &= 0xffffffff
        return h
    fnv1a_beansdb = fnv1a



FLAG_PICKLE   = 0x00000001
FLAG_INTEGER  = 0x00000002
FLAG_LONG     = 0x00000004
FLAG_BOOL     = 0x00000008
FLAG_COMPRESS1= 0x00000010 # by cmemcached
FLAG_MARSHAL  = 0x00000020
FLAG_COMPRESS = 0x00010000 # by beansdb

PADDING = 256

def restore_value(flag, val):
    if flag & FLAG_COMPRESS:
        val = quicklz.decompress(val)
    if flag & FLAG_COMPRESS1:
        val = zlib.decompress(val)

    if flag & FLAG_BOOL:
        val = bool(int(val))
    elif flag & FLAG_INTEGER:
        val = int(val)
    elif flag & FLAG_MARSHAL:
        val = marshal.loads(val)
    elif flag & FLAG_PICKLE:
        val = cPickle.loads(val)
    return val

def prepare_value(val, compress):
    flag = 0
    if isinstance(val, str):
        pass
    elif isinstance(val, (bool)):
        flag = FLAG_BOOL
        val = str(int(val))
    elif isinstance(val, (int, long)):
        flag = FLAG_INTEGER
        val = str(val)
    elif type(val) is unicode:
        flag = FLAG_MARSHAL
        val = marshal.dumps(val, 2)
    else:
        try:
            val = marshal.dumps(val, 2)
            flag = FLAG_MARSHAL
        except ValueError:
                val = cPickle.dumps(val, -1)
                flag = FLAG_PICKLE

    if compress and len(val) > 1024:
        flag |= FLAG_COMPRESS
        val = quicklz.compress(val)

    return flag, val


class BeansdbFileRDD(TextFileRDD):
    def __init__(self, ctx, path, filter=None, fullscan=False, raw=False):
        if not fullscan:
            hint = path[:-5] + '.hint'
            if not os.path.exists(hint) and not os.path.exists(hint + '.qlz'):
                fullscan = True
            if not filter:
                fullscan = True
        TextFileRDD.__init__(self, ctx, path, numSplits=None if fullscan else 1)
        self.func = filter
        self.fullscan = fullscan
        self.raw = raw

    @cached
    def __getstate__(self):
        d = RDD.__getstate__(self)
        del d['func']
        return d, dump_func(self.func)

    def __setstate__(self, state):
        self.__dict__, code = state
        try:
            self.func = load_func(code)
        except Exception:
            print 'load failed', self.__class__, code[:1024]
            raise

    def compute(self, split):
        if self.fullscan:
            return self.full_scan(split)
        hint = self.path[:-5] + '.hint.qlz'
        if os.path.exists(hint):
            return self.scan_hint(hint)
        hint = self.path[:-5] + '.hint'
        if os.path.exists(hint):
            return self.scan_hint(hint)
        return self.full_scan(split)

    def scan_hint(self, hint_path):
        hint = open(hint_path).read()
        if hint_path.endswith('.qlz'):
            try:
                hint = quicklz.decompress(hint)
            except ValueError, e:
                msg = str(e.message)
                if msg.startswith('compressed length not match'):
                    hint = hint[:int(msg.split('!=')[1])]
                    hint = quicklz.decompress(hint)

        func = self.func or (lambda x:True)
        dataf = open(self.path)
        p = 0
        while p < len(hint):
            pos, ver, hash = struct.unpack("IiH", hint[p:p+10])
            p += 10
            ksz = pos & 0xff
            key = hint[p: p+ksz]
            if func(key):
                dataf.seek(pos & 0xffffff00)
                r = self.read_record(dataf)
                if r:
                    rsize, key, value = r
                    yield key, value
                else:
                    logger.error("read failed from %s at %d", self.path, pos & 0xffffff00)
            p += ksz + 1 # \x00

    def restore(self, flag, val):
        if self.raw:
            return (flag, val)
        return restore_value(flag, val)

    def try_read_record(self, f):
        block = f.read(PADDING)
        if not block:
            return

        crc, tstamp, flag, ver, ksz, vsz = struct.unpack("IiiiII", block[:24])
        if not (0 < ksz < 255 and 0 <= vsz < (50<<20)):
            return
        rsize = 24 + ksz + vsz
        if rsize & 0xff:
            rsize = ((rsize >> 8) + 1) << 8
        if rsize > PADDING:
            block += f.read(rsize-PADDING)
        crc32 = binascii.crc32(block[4:24 + ksz + vsz]) & 0xffffffff
        if crc != crc32:
            return
        return True

    def read_record(self, f):
        block = f.read(PADDING)
        if len(block) < 24:
            return

        crc, tstamp, flag, ver, ksz, vsz = struct.unpack("IiiiII", block[:24])
        if not (0 < ksz < 255 and 0 <= vsz < (50<<20)):
            logger.warning('bad key length %d %d', ksz, vsz)
            return

        rsize = 24 + ksz + vsz
        if rsize & 0xff:
            rsize = ((rsize >> 8) + 1) << 8
        if rsize > PADDING:
            block += f.read(rsize-PADDING)
        #crc32 = binascii.crc32(block[4:24 + ksz + vsz]) & 0xffffffff
        #if crc != crc32:
        #    print 'crc broken', crc, crc32
        #    return
        key = block[24:24+ksz]
        value = block[24+ksz:24+ksz+vsz]
        if not self.func or self.func(key):
            value = self.restore(flag, value)
        return rsize, key, (value, ver, tstamp)

    def full_scan(self, split):
        f = self.open_file()

        # try to find first record
        begin, end = split.begin, split.end
        while True:
            f.seek(begin)
            r = self.try_read_record(f)
            if r: break
            begin += PADDING
            if begin >= end: break
        if begin >= end:
            return

        f.seek(begin)
        func = self.func or (lambda x:True)
        while begin < end:
            r = self.read_record(f)
            if not r:
                begin += PADDING
                logger.error('read fail at %s pos: %d', self.path, begin)
                while begin < end:
                    f.seek(begin)
                    if self.try_read_record(f):
                        break
                    begin += PADDING
                continue
            size, key, value = r
            if func(key):
                yield key, value
            begin += size


class OutputBeansdbRDD(DerivedRDD):
    def __init__(self, rdd, path, depth, overwrite, compress=False, raw=False):
        DerivedRDD.__init__(self, rdd)
        self.path = path
        self.depth = depth
        self.overwrite = overwrite
        if not quicklz:
            compress = False
        self.compress = compress
        self.raw = raw

        for i in range(16 ** depth):
            if depth > 0:
                ps = list(('%%0%dx' % depth) % i)
                p = os.path.join(path, *ps)
            else:
                p = path
            if os.path.exists(p):
                if overwrite:
                    for n in os.listdir(p):
                        if n[:3].isdigit():
                            os.remove(os.path.join(p, n))
            else:
                os.makedirs(p)


    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self.path, self.prev)

    def prepare(self, val):
        if self.raw:
            return val

        return prepare_value(val, self.compress)

    def gen_hash(self, d):
        # used in beansdb
        h = len(d) * 97
        if len(d) <= 1024:
            h += fnv1a_beansdb(d)
        else:
            h += fnv1a_beansdb(d[:512])
            h *= 97
            h += fnv1a_beansdb(d[-512:])
        return h & 0xffff

    def write_record(self, f, key, flag, value, now=None):
        header = struct.pack('IIIII', now, flag, 1, len(key), len(value))
        crc32 = binascii.crc32(header)
        crc32 = binascii.crc32(key, crc32)
        crc32 = binascii.crc32(value, crc32) & 0xffffffff
        f.write(struct.pack("I", crc32))
        f.write(header)
        f.write(key)
        f.write(value)
        rsize = 24 + len(key) + len(value)
        if rsize & 0xff:
            f.write('\x00' * (PADDING - (rsize & 0xff)))
            rsize = ((rsize >> 8) + 1) << 8
        return rsize

    def compute(self, split):
        N = 16 ** self.depth
        if self.depth > 0:
            fmt='%%0%dx' % self.depth
            ds = [os.path.join(self.path, *list(fmt % i)) for i in range(N)]
        else:
            ds = [self.path]
        pname = '%03d.data' % split.index
        tname = '.%03d.data.%s.tmp' % (split.index, socket.gethostname())
        p = [os.path.join(d, pname) for d in ds]
        tp = [os.path.join(d, tname) for d in ds]
        pos = [0] * N
        f = [open(t, 'w', 1<<20) for t in tp]
        now = int(time.time())
        hint = [[] for d in ds]

        bits = 32 - self.depth * 4
        for key, value in self.prev.iterator(split):
            key = str(key)
            i = fnv1a(key) >> bits
            flag, value = self.prepare(value)
            h = self.gen_hash(value)
            hint[i].append(struct.pack("IIH", pos[i] + len(key), 1, h) + key + '\x00')
            pos[i] += self.write_record(f[i], key, flag, value, now)
            if pos[i] > (4000<<20):
                raise Exception("split is large than 4000M")
        [i.close() for i in f]

        for i in range(N):
            if hint[i] and not os.path.exists(p[i]):
                os.rename(tp[i], p[i])
                hintdata = ''.join(hint[i])
                hint_path = os.path.join(os.path.dirname(p[i]), '%03d.hint' % split.index)
                if self.compress:
                    hintdata = quicklz.compress(hintdata)
                    hint_path += '.qlz'
                open(hint_path, 'w').write(hintdata)
            else:
                os.remove(tp[i])

        return sum([([p[i]] if hint[i] else []) for i in range(N)], [])

########NEW FILE########
__FILENAME__ = schedule
import os, sys
import socket
import logging
import marshal
import cPickle
import threading, Queue
import time
import random
import urllib
import warnings
import weakref
import multiprocessing
import platform

import zmq

import pymesos as mesos
import pymesos.mesos_pb2 as mesos_pb2

from dpark.util import compress, decompress, spawn, getuser
from dpark.dependency import NarrowDependency, ShuffleDependency
from dpark.accumulator import Accumulator
from dpark.task import ResultTask, ShuffleMapTask
from dpark.job import SimpleJob
from dpark.env import env
from dpark.mutable_dict import MutableDict

logger = logging.getLogger("scheduler")

MAX_FAILED = 3
EXECUTOR_MEMORY = 64 # cache
POLL_TIMEOUT = 0.1
RESUBMIT_TIMEOUT = 60
MAX_IDLE_TIME = 60 * 30

class TaskEndReason: pass
class Success(TaskEndReason): pass
class FetchFailed(TaskEndReason):
    def __init__(self, serverUri, shuffleId, mapId, reduceId):
        self.serverUri = serverUri
        self.shuffleId = shuffleId
        self.mapId = mapId
        self.reduceId = reduceId
    def __str__(self):
        return '<FetchFailed(%s, %d, %d, %d)>' % (self.serverUri,
                self.shuffleId, self.mapId, self.reduceId)

class OtherFailure(TaskEndReason):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return '<OtherFailure %s>' % self.message

class Stage:
    def __init__(self, rdd, shuffleDep, parents):
        self.id = self.newId()
        self.rdd = rdd
        self.shuffleDep = shuffleDep
        self.parents = parents
        self.numPartitions = len(rdd)
        self.outputLocs = [[] for i in range(self.numPartitions)]

    def __str__(self):
        return '<Stage(%d) for %s>' % (self.id, self.rdd)

    def __getstate__(self):
        raise Exception("should not pickle stage")

    @property
    def isAvailable(self):
        if not self.parents and self.shuffleDep == None:
            return True
        return all(self.outputLocs)

    def addOutputLoc(self, partition, host):
        self.outputLocs[partition].append(host)

#    def removeOutput(self, partition, host):
#        prev = self.outputLocs[partition]
#        self.outputLocs[partition] = [h for h in prev if h != host]

    def removeHost(self, host):
        becameUnavailable = False
        for ls in self.outputLocs:
            if host in ls:
                ls.remove(host)
                becameUnavailable = True
        if becameUnavailable:
            logger.info("%s is now unavailable on host %s", self, host)

    nextId = 0
    @classmethod
    def newId(cls):
        cls.nextId += 1
        return cls.nextId


class Scheduler:
    def start(self): pass
    def runJob(self, rdd, func, partitions, allowLocal): pass
    def clear(self): pass
    def stop(self): pass
    def defaultParallelism(self):
        return 2

class CompletionEvent:
    def __init__(self, task, reason, result, accumUpdates):
        self.task = task
        self.reason = reason
        self.result = result
        self.accumUpdates = accumUpdates


class DAGScheduler(Scheduler):

    def __init__(self):
        self.completionEvents = Queue.Queue()
        self.idToStage = weakref.WeakValueDictionary()
        self.shuffleToMapStage = {}
        self.cacheLocs = {}
        self._shutdown = False

    def check(self):
        pass

    def clear(self):
        self.idToStage.clear()
        self.shuffleToMapStage.clear()
        self.cacheLocs.clear()
        self.cacheTracker.clear()
        self.mapOutputTracker.clear()

    def shutdown(self):
        self._shutdown = True

    @property
    def cacheTracker(self):
        return env.cacheTracker

    @property
    def mapOutputTracker(self):
        return env.mapOutputTracker

    def submitTasks(self, tasks):
        raise NotImplementedError

    def taskEnded(self, task, reason, result, accumUpdates):
        self.completionEvents.put(CompletionEvent(task, reason, result, accumUpdates))

    def getCacheLocs(self, rdd):
        return self.cacheLocs.get(rdd.id, [[] for i in range(len(rdd))])

    def updateCacheLocs(self):
        self.cacheLocs = self.cacheTracker.getLocationsSnapshot()

    def newStage(self, rdd, shuffleDep):
        stage = Stage(rdd, shuffleDep, self.getParentStages(rdd))
        self.idToStage[stage.id] = stage
        logger.debug("new stage: %s", stage)
        return stage

    def getParentStages(self, rdd):
        parents = set()
        visited = set()
        def visit(r):
            if r.id in visited:
                return
            visited.add(r.id)
            if r.shouldCache:
                self.cacheTracker.registerRDD(r.id, len(r))
            for dep in r.dependencies:
                if isinstance(dep, ShuffleDependency):
                    parents.add(self.getShuffleMapStage(dep))
                else:
                    visit(dep.rdd)
        visit(rdd)
        return list(parents)

    def getShuffleMapStage(self, dep):
        stage = self.shuffleToMapStage.get(dep.shuffleId, None)
        if stage is None:
            stage = self.newStage(dep.rdd, dep)
            self.shuffleToMapStage[dep.shuffleId] = stage
        return stage

    def getMissingParentStages(self, stage):
        missing = set()
        visited = set()
        def visit(r):
            if r.id in visited:
                return
            visited.add(r.id)
            if r.shouldCache and all(self.getCacheLocs(r)):
                return

            for dep in r.dependencies:
                if isinstance(dep, ShuffleDependency):
                    stage = self.getShuffleMapStage(dep)
                    if not stage.isAvailable:
                        missing.add(stage)
                elif isinstance(dep, NarrowDependency):
                    visit(dep.rdd)

        visit(stage.rdd)
        return list(missing)

    def runJob(self, finalRdd, func, partitions, allowLocal):
        outputParts = list(partitions)
        numOutputParts = len(partitions)
        finalStage = self.newStage(finalRdd, None)
        results = [None]*numOutputParts
        finished = [None]*numOutputParts
        lastFinished = 0
        numFinished = 0

        waiting = set()
        running = set()
        failed = set()
        pendingTasks = {}
        lastFetchFailureTime = 0

        self.updateCacheLocs()

        logger.debug("Final stage: %s, %d", finalStage, numOutputParts)
        logger.debug("Parents of final stage: %s", finalStage.parents)
        logger.debug("Missing parents: %s", self.getMissingParentStages(finalStage))

        if allowLocal and (not finalStage.parents or not self.getMissingParentStages(finalStage)) and numOutputParts == 1:
            split = finalRdd.splits[outputParts[0]]
            yield func(finalRdd.iterator(split))
            return

        def submitStage(stage):
            logger.debug("submit stage %s", stage)
            if stage not in waiting and stage not in running:
                missing = self.getMissingParentStages(stage)
                if not missing:
                    submitMissingTasks(stage)
                    running.add(stage)
                else:
                    for parent in missing:
                        submitStage(parent)
                    waiting.add(stage)

        def submitMissingTasks(stage):
            myPending = pendingTasks.setdefault(stage, set())
            tasks = []
            have_prefer = True
            if stage == finalStage:
                for i in range(numOutputParts):
                    if not finished[i]:
                        part = outputParts[i]
                        if have_prefer:
                            locs = self.getPreferredLocs(finalRdd, part)
                            if not locs:
                                have_prefer = False
                        else:
                            locs = []
                        tasks.append(ResultTask(finalStage.id, finalRdd,
                            func, part, locs, i))
            else:
                for p in range(stage.numPartitions):
                    if not stage.outputLocs[p]:
                        if have_prefer:
                            locs = self.getPreferredLocs(stage.rdd, p)
                            if not locs:
                                have_prefer = False
                        else:
                            locs = []
                        tasks.append(ShuffleMapTask(stage.id, stage.rdd,
                            stage.shuffleDep, p, locs))
            logger.debug("add to pending %s tasks", len(tasks))
            myPending |= set(t.id for t in tasks)
            self.submitTasks(tasks)

        submitStage(finalStage)

        while numFinished != numOutputParts:
            try:
                evt = self.completionEvents.get(False)
            except Queue.Empty:
                self.check()
                if self._shutdown:
                    sys.exit(1)

                if failed and time.time() > lastFetchFailureTime + RESUBMIT_TIMEOUT:
                    self.updateCacheLocs()
                    for stage in failed:
                        logger.info("Resubmitting failed stages: %s", stage)
                        submitStage(stage)
                    failed.clear()
                else:
                    time.sleep(0.1)
                continue

            task, reason = evt.task, evt.reason
            stage = self.idToStage[task.stageId]
            if stage not in pendingTasks: # stage from other job
                continue
            logger.debug("remove from pending %s from %s", task, stage)
            pendingTasks[stage].remove(task.id)
            if isinstance(reason, Success):
                Accumulator.merge(evt.accumUpdates)
                if isinstance(task, ResultTask):
                    finished[task.outputId] = True
                    numFinished += 1
                    results[task.outputId] = evt.result
                    while lastFinished < numOutputParts and finished[lastFinished]:
                        yield results[lastFinished]
                        results[lastFinished] = None
                        lastFinished += 1

                elif isinstance(task, ShuffleMapTask):
                    stage = self.idToStage[task.stageId]
                    stage.addOutputLoc(task.partition, evt.result)
                    if not pendingTasks[stage] and all(stage.outputLocs):
                        logger.debug("%s finished; looking for newly runnable stages", stage)
                        MutableDict.merge()
                        running.remove(stage)
                        if stage.shuffleDep != None:
                            self.mapOutputTracker.registerMapOutputs(
                                    stage.shuffleDep.shuffleId,
                                    [l[-1] for l in stage.outputLocs])
                        self.updateCacheLocs()
                        newlyRunnable = set(stage for stage in waiting if not self.getMissingParentStages(stage))
                        waiting -= newlyRunnable
                        running |= newlyRunnable
                        logger.debug("newly runnable: %s, %s", waiting, newlyRunnable)
                        for stage in newlyRunnable:
                            submitMissingTasks(stage)
            elif isinstance(reason, FetchFailed):
                if stage in running:
                    waiting.add(stage)
                mapStage = self.shuffleToMapStage[reason.shuffleId]
                mapStage.removeHost(reason.serverUri)
                failed.add(mapStage)
                lastFetchFailureTime = time.time()
            else:
                logger.error("task %s failed: %s %s %s", task, reason, type(reason), reason.message)
                raise Exception(reason.message)

        MutableDict.merge()
        assert not any(results)
        return

    def getPreferredLocs(self, rdd, partition):
        return rdd.preferredLocations(rdd.splits[partition])


def run_task(task, aid):
    logger.debug("Running task %r", task)
    try:
        Accumulator.clear()
        result = task.run(aid)
        accumUpdates = Accumulator.values()
        MutableDict.flush()
        return (task.id, Success(), result, accumUpdates)
    except Exception, e:
        logger.error("error in task %s", task)
        import traceback
        traceback.print_exc()
        return (task.id, OtherFailure("exception:" + str(e)), None, None)


class LocalScheduler(DAGScheduler):
    attemptId = 0
    def nextAttempId(self):
        self.attemptId += 1
        return self.attemptId

    def submitTasks(self, tasks):
        logger.debug("submit tasks %s in LocalScheduler", tasks)
        for task in tasks:
#            task = cPickle.loads(cPickle.dumps(task, -1))
            _, reason, result, update = run_task(task, self.nextAttempId())
            self.taskEnded(task, reason, result, update)

def run_task_in_process(task, tid, environ):
    from dpark.env import env
    workdir = environ.get('WORKDIR')
    environ['SERVER_URI'] = 'file://%s' % workdir[0]
    env.start(False, environ)

    logger.debug("run task in process %s %s", task, tid)
    try:
        return run_task(task, tid)
    except KeyboardInterrupt:
        sys.exit(0)

class MultiProcessScheduler(LocalScheduler):
    def __init__(self, threads):
        LocalScheduler.__init__(self)
        self.threads = threads
        self.tasks = {}
        self.pool = multiprocessing.Pool(self.threads or 2)

    def submitTasks(self, tasks):
        if not tasks:
            return

        logger.info("Got a job with %d tasks: %s", len(tasks), tasks[0].rdd)

        total, self.finished, start = len(tasks), 0, time.time()
        def callback(args):
            logger.debug("got answer: %s", args)
            tid, reason, result, update = args
            task = self.tasks.pop(tid)
            self.finished += 1
            logger.info("Task %s finished (%d/%d)        \x1b[1A",
                tid, self.finished, total)
            if self.finished == total:
                logger.info("Job finished in %.1f seconds" + " "*20,  time.time() - start)
            self.taskEnded(task, reason, result, update)

        for task in tasks:
            logger.debug("put task async: %s", task)
            self.tasks[task.id] = task
            self.pool.apply_async(run_task_in_process,
                [task, self.nextAttempId(), env.environ],
                callback=callback)

    def stop(self):
        self.pool.terminate()
        self.pool.join()
        logger.debug("process pool stopped")


def profile(f):
    def func(*args, **kwargs):
        path = '/tmp/worker-%s.prof' % os.getpid()
        import cProfile
        import pstats
        func = f
        cProfile.runctx('func(*args, **kwargs)',
            globals(), locals(), path)
        stats = pstats.Stats(path)
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        stats.print_stats(20)
        stats.sort_stats('cumulative')
        stats.print_stats(20)
    return func

def safe(f):
    def _(self, *a, **kw):
        with self.lock:
            r = f(self, *a, **kw)
        return r
    return _

def int2ip(n):
    return "%d.%d.%d.%d" % (n & 0xff, (n>>8)&0xff, (n>>16)&0xff, n>>24)

class MesosScheduler(DAGScheduler):

    def __init__(self, master, options):
        DAGScheduler.__init__(self)
        self.master = master
        self.use_self_as_exec = options.self
        self.cpus = options.cpus
        self.mem = options.mem
        self.task_per_node = options.parallel or multiprocessing.cpu_count()
        self.group = options.group
        self.logLevel = options.logLevel
        self.options = options
        self.started = False
        self.last_finish_time = 0
        self.isRegistered = False
        self.executor = None
        self.driver = None
        self.out_logger = None
        self.err_logger = None
        self.lock = threading.RLock()
        self.init_job()

    def init_job(self):
        self.activeJobs = {}
        self.activeJobsQueue = []
        self.taskIdToJobId = {}
        self.taskIdToSlaveId = {}
        self.jobTasks = {}
        self.slaveTasks = {}
        self.slaveFailed = {}

    def clear(self):
        DAGScheduler.clear(self)
        self.init_job()

    def start(self):
        if not self.out_logger:
            self.out_logger = self.start_logger(sys.stdout)
        if not self.err_logger:
            self.err_logger = self.start_logger(sys.stderr)

    def start_driver(self):
        name = '[dpark] ' + os.path.abspath(sys.argv[0]) + ' ' + ' '.join(sys.argv[1:])
        if len(name) > 256:
            name = name[:256] + '...'
        framework = mesos_pb2.FrameworkInfo()
        framework.user = getuser()
        if framework.user == 'root':
            raise Exception("dpark is not allowed to run as 'root'")
        framework.name = name
        framework.hostname = socket.gethostname()

        self.driver = mesos.MesosSchedulerDriver(self, framework,
                                                 self.master)
        self.driver.start()
        logger.debug("Mesos Scheudler driver started")

        self.started = True
        self.last_finish_time = time.time()
        def check():
            while self.started:
                now = time.time()
                if not self.activeJobs and now - self.last_finish_time > MAX_IDLE_TIME:
                    logger.info("stop mesos scheduler after %d seconds idle",
                            now - self.last_finish_time)
                    self.stop()
                    break
                time.sleep(1)

        spawn(check)

    def start_logger(self, output):
        sock = env.ctx.socket(zmq.PULL)
        port = sock.bind_to_random_port("tcp://0.0.0.0")

        def collect_log():
            while not self._shutdown:
                if sock.poll(1000, zmq.POLLIN):
                    line = sock.recv()
                    output.write(line)

        spawn(collect_log)

        host = socket.gethostname()
        addr = "tcp://%s:%d" % (host, port)
        logger.debug("log collecter start at %s", addr)
        return addr

    @safe
    def registered(self, driver, frameworkId, masterInfo):
        self.isRegistered = True
        logger.debug("connect to master %s:%s(%s), registered as %s",
            int2ip(masterInfo.ip), masterInfo.port, masterInfo.id,
            frameworkId.value)
        self.executor = self.getExecutorInfo(str(frameworkId.value))

    @safe
    def reregistered(self, driver, masterInfo):
        logger.warning("re-connect to mesos master %s:%s(%s)",
            int2ip(masterInfo.ip), masterInfo.port, masterInfo.id)

    @safe
    def disconnected(self, driver):
        logger.debug("framework is disconnected")

    @safe
    def getExecutorInfo(self, framework_id):
        info = mesos_pb2.ExecutorInfo()
        if hasattr(info, 'framework_id'):
            info.framework_id.value = framework_id

        if self.use_self_as_exec:
            info.command.value = os.path.abspath(sys.argv[0])
            info.executor_id.value = sys.argv[0]
        else:
            info.command.value = '%s %s' % (
                sys.executable,
                os.path.abspath(os.path.join(os.path.dirname(__file__), 'executor.py'))
            )
            info.executor_id.value = "default"

        mem = info.resources.add()
        mem.name = 'mem'
        mem.type = 0 #mesos_pb2.Value.SCALAR
        mem.scalar.value = EXECUTOR_MEMORY
        Script = os.path.realpath(sys.argv[0])
        if hasattr(info, 'name'):
            info.name = Script

        info.data = marshal.dumps((Script, os.getcwd(), sys.path, dict(os.environ),
            self.task_per_node, self.out_logger, self.err_logger, self.logLevel, env.environ))
        return info

    @safe
    def submitTasks(self, tasks):
        if not tasks:
            return

        job = SimpleJob(self, tasks, self.cpus, tasks[0].rdd.mem or self.mem)
        self.activeJobs[job.id] = job
        self.activeJobsQueue.append(job)
        self.jobTasks[job.id] = set()
        logger.info("Got job %d with %d tasks: %s", job.id, len(tasks), tasks[0].rdd)

        need_revive = self.started
        if not self.started:
            self.start_driver()
        while not self.isRegistered:
            self.lock.release()
            time.sleep(0.01)
            self.lock.acquire()

        if need_revive:
            self.requestMoreResources()

    def requestMoreResources(self):
        logger.debug("reviveOffers")
        self.driver.reviveOffers()

    @safe
    def resourceOffers(self, driver, offers):
        rf = mesos_pb2.Filters()
        if not self.activeJobs:
            rf.refuse_seconds = 60 * 5
            for o in offers:
                driver.launchTasks(o.id, [], rf)
            return

        start = time.time()
        random.shuffle(offers)
        cpus = [self.getResource(o.resources, 'cpus') for o in offers]
        mems = [self.getResource(o.resources, 'mem')
                - (o.slave_id.value not in self.slaveTasks
                    and EXECUTOR_MEMORY or 0)
                for o in offers]
        logger.debug("get %d offers (%s cpus, %s mem), %d jobs",
            len(offers), sum(cpus), sum(mems), len(self.activeJobs))

        tasks = {}
        for job in self.activeJobsQueue:
            while True:
                launchedTask = False
                for i,o in enumerate(offers):
                    sid = o.slave_id.value
                    if self.group and (self.getAttribute(o.attributes, 'group') or 'none') not in self.group:
                        continue
                    if self.slaveFailed.get(sid, 0) >= MAX_FAILED:
                        continue
                    if self.slaveTasks.get(sid, 0) >= self.task_per_node:
                        continue
                    if mems[i] < self.mem or cpus[i]+1e-4 < self.cpus:
                        continue
                    t = job.slaveOffer(str(o.hostname), cpus[i], mems[i])
                    if not t:
                        continue
                    task = self.createTask(o, job, t, cpus[i])
                    tasks.setdefault(o.id.value, []).append(task)

                    logger.debug("dispatch %s into %s", t, o.hostname)
                    tid = task.task_id.value
                    self.jobTasks[job.id].add(tid)
                    self.taskIdToJobId[tid] = job.id
                    self.taskIdToSlaveId[tid] = sid
                    self.slaveTasks[sid] = self.slaveTasks.get(sid, 0)  + 1
                    cpus[i] -= min(cpus[i], t.cpus)
                    mems[i] -= t.mem
                    launchedTask = True

                if not launchedTask:
                    break

        used = time.time() - start
        if used > 10:
            logger.error("use too much time in slaveOffer: %.2fs", used)

        rf.refuse_seconds = 5
        for o in offers:
            driver.launchTasks(o.id, tasks.get(o.id.value, []), rf)

        logger.debug("reply with %d tasks, %s cpus %s mem left",
            sum(len(ts) for ts in tasks.values()), sum(cpus), sum(mems))

    @safe
    def offerRescinded(self, driver, offer_id):
        logger.debug("rescinded offer: %s", offer_id)
        if self.activeJobs:
            self.requestMoreResources()

    def getResource(self, res, name):
        for r in res:
            if r.name == name:
                return r.scalar.value

    def getAttribute(self, attrs, name):
        for r in attrs:
            if r.name == name:
                return r.text.value

    def createTask(self, o, job, t, available_cpus):
        task = mesos_pb2.TaskInfo()
        tid = "%s:%s:%s" % (job.id, t.id, t.tried)
        task.name = "task %s" % tid
        task.task_id.value = tid
        task.slave_id.value = o.slave_id.value
        task.data = compress(cPickle.dumps((t, t.tried), -1))
        task.executor.MergeFrom(self.executor)
        if len(task.data) > 1000*1024:
            logger.warning("task too large: %s %d",
                t, len(task.data))

        cpu = task.resources.add()
        cpu.name = 'cpus'
        cpu.type = 0 #mesos_pb2.Value.SCALAR
        cpu.scalar.value = min(t.cpus, available_cpus)
        mem = task.resources.add()
        mem.name = 'mem'
        mem.type = 0 #mesos_pb2.Value.SCALAR
        mem.scalar.value = t.mem
        return task

    @safe
    def statusUpdate(self, driver, status):
        tid = status.task_id.value
        state = status.state
        logger.debug("status update: %s %s", tid, state)

        jid = self.taskIdToJobId.get(tid)
        if jid not in self.activeJobs:
            logger.debug("Ignoring update from TID %s " +
                "because its job is gone", tid)
            return

        job = self.activeJobs[jid]
        _, task_id, tried = map(int, tid.split(':'))
        if state == mesos_pb2.TASK_RUNNING:
            return job.statusUpdate(task_id, tried, state)

        del self.taskIdToJobId[tid]
        self.jobTasks[jid].remove(tid)
        slave_id = self.taskIdToSlaveId[tid]
        if slave_id in self.slaveTasks:
            self.slaveTasks[slave_id] -= 1
        del self.taskIdToSlaveId[tid]

        if state in (mesos_pb2.TASK_FINISHED, mesos_pb2.TASK_FAILED) and status.data:
            try:
                reason,result,accUpdate = cPickle.loads(status.data)
                if result:
                    flag, data = result
                    if flag >= 2:
                        try:
                            data = urllib.urlopen(data).read()
                        except IOError:
                            # try again
                            data = urllib.urlopen(data).read()
                        flag -= 2
                    data = decompress(data)
                    if flag == 0:
                        result = marshal.loads(data)
                    else:
                        result = cPickle.loads(data)
            except Exception, e:
                logger.warning("error when cPickle.loads(): %s, data:%s", e, len(status.data))
                state = mesos_pb2.TASK_FAILED
                return job.statusUpdate(task_id, tried, mesos_pb2.TASK_FAILED, 'load failed: %s' % e)
            else:
                return job.statusUpdate(task_id, tried, state,
                    reason, result, accUpdate)

        # killed, lost, load failed
        job.statusUpdate(task_id, tried, state, status.data)
        #if state in (mesos_pb2.TASK_FAILED, mesos_pb2.TASK_LOST):
        #    self.slaveFailed[slave_id] = self.slaveFailed.get(slave_id,0) + 1

    def jobFinished(self, job):
        logger.debug("job %s finished", job.id)
        if job.id in self.activeJobs:
            del self.activeJobs[job.id]
            self.activeJobsQueue.remove(job)
            for id in self.jobTasks[job.id]:
                del self.taskIdToJobId[id]
                del self.taskIdToSlaveId[id]
            del self.jobTasks[job.id]
            self.last_finish_time = time.time()

            if not self.activeJobs:
                self.slaveTasks.clear()
                self.slaveFailed.clear()

    @safe
    def check(self):
        for job in self.activeJobs.values():
            if job.check_task_timeout():
                self.requestMoreResources()

    @safe
    def error(self, driver, code, message):
        logger.warning("Mesos error message: %s (code: %s)", message, code)
        #if self.activeJobs:
        #    self.requestMoreResources()

    #@safe
    def stop(self):
        if not self.started:
            return
        logger.debug("stop scheduler")
        self.started = False
        self.isRegistered = False
        self.driver.stop(False)
        self.driver = None

    def defaultParallelism(self):
        return 16

    def frameworkMessage(self, driver, slave, executor, data):
        logger.warning("[slave %s] %s", slave.value, data)

    def executorLost(self, driver, executorId, slaveId, status):
        logger.warning("executor at %s %s lost: %s", slaveId.value, executorId.value, status)
        self.slaveTasks.pop(slaveId.value, None)
        self.slaveFailed.pop(slaveId.value, None)

    def slaveLost(self, driver, slaveId):
        logger.warning("slave %s lost", slaveId.value)
        self.slaveTasks.pop(slaveId.value, None)
        self.slaveFailed.pop(slaveId.value, None)

    def killTask(self, job_id, task_id, tried):
        tid = mesos_pb2.TaskID()
        tid.value = "%s:%s:%s" % (job_id, task_id, tried)
        self.driver.killTask(tid)

########NEW FILE########
__FILENAME__ = serialize
import sys, types
from cStringIO import StringIO
import marshal, new, cPickle
import itertools
from pickle import Pickler, whichmodule
import logging
logger = logging.getLogger(__name__)

class MyPickler(Pickler):
    dispatch = Pickler.dispatch.copy()

    @classmethod
    def register(cls, type, reduce):
        def dispatcher(self, obj):
            rv = reduce(obj)
            if isinstance(rv, str):
                self.save_global(obj, rv)
            else:
                self.save_reduce(obj=obj, *rv)
        cls.dispatch[type] = dispatcher

def dumps(o):
    io = StringIO()
    MyPickler(io, -1).dump(o)
    return io.getvalue()

def loads(s):
    return cPickle.loads(s)

dump_func = dumps
load_func = loads

def reduce_module(mod):
    return load_module, (mod.__name__, )

def load_module(name):
    __import__(name)
    return sys.modules[name]

MyPickler.register(types.ModuleType, reduce_module)

class RecursiveFunctionPlaceholder(object):
    """
    Placeholder for a recursive reference to the current function,
    to avoid infinite recursion when serializing recursive functions.
    """
    def __eq__(self, other):
        return isinstance(other, RecursiveFunctionPlaceholder)

RECURSIVE_FUNCTION_PLACEHOLDER = RecursiveFunctionPlaceholder()

def marshalable(o):
    if o is None: return True
    t = type(o)
    if t in (str, unicode, bool, int, long, float, complex):
        return True
    if t in (tuple, list, set):
        for i in itertools.islice(o, 100):
            if not marshalable(i):
                return False
        return True
    if t == dict:
        for k,v in itertools.islice(o.iteritems(), 100):
            if not marshalable(k) or not marshalable(v):
                return False
        return True
    return False

OBJECT_SIZE_LIMIT = 100 << 10

def create_broadcast(name, obj, func_name):
    import dpark
    logger.info("use broadcast for object %s %s (used in function %s)",
        name, type(obj), func_name)
    return dpark._ctx.broadcast(obj)

def dump_obj(f, name, obj):
    if obj is f:
        # Prevent infinite recursion when dumping a recursive function
        return dumps(RECURSIVE_FUNCTION_PLACEHOLDER)

    try:
        if sys.getsizeof(obj) > OBJECT_SIZE_LIMIT:
            obj = create_broadcast(name, obj, f.__name__)
    except TypeError:
        pass

    b = dumps(obj)
    if len(b) > OBJECT_SIZE_LIMIT:
        b = dumps(create_broadcast(name, obj, f.__name__))
    if len(b) > OBJECT_SIZE_LIMIT:
        logger.warning("broadcast of %s obj too large", type(obj))
    return b

def get_co_names(code):
    co_names = code.co_names
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            co_names += get_co_names(const)

    return co_names

def dump_closure(f):
    code = f.func_code
    glob = {}
    for n in get_co_names(code):
        r = f.func_globals.get(n)
        if r is not None:
            glob[n] = dump_obj(f, n, r)

    closure = None
    if f.func_closure:
        closure = tuple(dump_obj(f, 'cell%d' % i, c.cell_contents)
                for i, c in enumerate(f.func_closure))
    return marshal.dumps((code, glob, f.func_name, f.func_defaults, closure, f.__module__))

def load_closure(bytes):
    code, glob, name, defaults, closure, mod = marshal.loads(bytes)
    glob = dict((k, loads(v)) for k,v in glob.items())
    glob['__builtins__'] = __builtins__
    closure = closure and reconstruct_closure([loads(c) for c in closure]) or None
    f = new.function(code, glob, name, defaults, closure)
    f.__module__ = mod
    # Replace the recursive function placeholders with this simulated function pointer
    for key, value in glob.items():
        if RECURSIVE_FUNCTION_PLACEHOLDER == value:
            f.func_globals[key] = f
    return f

def make_cell(value):
    return (lambda: value).func_closure[0]

def reconstruct_closure(values):
    return tuple([make_cell(v) for v in values])

def get_global_function(module, name):
    __import__(module)
    mod = sys.modules[module]
    return getattr(mod, name)

def reduce_function(obj):
    name = obj.__name__
    if not name or name == '<lambda>':
        return load_closure, (dump_closure(obj),)

    module = getattr(obj, "__module__", None)
    if module is None:
        module = whichmodule(obj, name)

    if module == '__main__' and name not in ('load_closure','load_module',
            'load_method', 'load_local_class'): # fix for test
        return load_closure, (dump_closure(obj),)

    try:
        f = get_global_function(module, name)
    except (ImportError, KeyError, AttributeError):
        return load_closure, (dump_closure(obj),)
    else:
        if f is not obj:
            return load_closure, (dump_closure(obj),)
        return name

classes_dumping = set()
internal_fields = {
    '__weakref__': False,
    '__dict__': False,
    '__doc__': True
}
def dump_local_class(cls):
    name = cls.__name__
    if cls in classes_dumping:
        return dumps(name)

    classes_dumping.add(cls)
    internal = {}
    external = {}
    for k in cls.__dict__:
        if k not in internal_fields:
            v = getattr(cls, k)
            if isinstance(v, property):
                k = ('property', k)
                v = (v.fget, v.fset, v.fdel, v.__doc__)

            if isinstance(v, types.FunctionType):
                k = ('staticmethod', k)

            external[k] = v

        elif internal_fields[k]:
            internal[k] = getattr(cls, k)

    result = dumps((cls.__name__, cls.__bases__, internal, dumps(external)))
    if cls in classes_dumping:
        classes_dumping.remove(cls)

    return result

classes_loaded = {}
def load_local_class(bytes):
    t = loads(bytes)
    if not isinstance(t, tuple):
        return classes_loaded[t]

    name, bases, internal, external = t
    if name in classes_loaded:
        return classes_loaded[name]

    cls = type(name, bases, internal)
    classes_loaded[name] = cls
    for k, v in loads(external).items():
        if isinstance(k, tuple):
            t, k = k
            if t == 'property':
                fget, fset, fdel, doc = v
                v = property(fget, fset, fdel, doc)

            if t == 'staticmethod':
                v = staticmethod(v)

        setattr(cls, k, v)

    return cls

def reduce_class(obj):
    name = obj.__name__
    module = getattr(obj, "__module__", None)
    if module == '__main__' and name not in ('MyPickler', 'RecursiveFunctionPlaceholder'):
        result = load_local_class, (dump_local_class(obj),)
        return result

    return name

CLS_TYPES = [types.TypeType, types.ClassType]
def dump_method(method):
    obj = method.im_self
    cls = method.im_class
    func = method.im_func
    if cls in CLS_TYPES:
        cls_name = CLS_TYPES.index(cls)
    else:
        cls_name = cls.__name__

    return dumps((obj, cls_name, func))

def load_method(bytes):
    obj, cls_name, func = loads(bytes) # cls referred in func.func_globals
    if isinstance(cls_name, int):
        cls = CLS_TYPES[cls_name]
    else:
        cls = classes_loaded[cls_name]

    return types.MethodType(func, obj, cls)

def reduce_method(method):
    module = method.im_func.__module__
    return load_method, (dump_method(method), )

MyPickler.register(types.LambdaType, reduce_function)
MyPickler.register(types.ClassType, reduce_class)
MyPickler.register(types.TypeType, reduce_class)
MyPickler.register(types.MethodType, reduce_method)

if __name__ == "__main__":
    assert marshalable(None)
    assert marshalable("")
    assert marshalable(u"")
    assert not marshalable(buffer(""))
    assert marshalable(0)
    assert marshalable(0L)
    assert marshalable(0.0)
    assert marshalable(True)
    assert marshalable(complex(1,1))
    assert marshalable((1,1))
    assert marshalable([1,1])
    assert marshalable(set([1,1]))
    assert marshalable({1:None})

    some_global = 'some global'
    def glob_func(s):
        return "glob:" + s
    def get_closure(x):
        glob_func(some_global)
        last = " last"
        def foo(y): return "foo: " + y
        def the_closure(a, b=1):
            marshal.dumps(a)
            return (a * x + int(b), glob_func(foo(some_global)+last))
        return the_closure

    f = get_closure(10)
    ff = loads(dumps(f))
    #print globals()
    print f(2)
    print ff(2)
    glob_func = loads(dumps(glob_func))
    get_closure = loads(dumps(get_closure))

    # Test recursive functions
    def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)
    assert fib(8) == loads(dumps(fib))(8)

    class Foo1:
        def foo(self):
            return 1234

    class Foo2(object):
        def foo(self):
            return 5678

    class Foo3(Foo2):
        x = 1111

        def foo(self):
            return super(Foo3, self).foo() + Foo3.x

    class Foo4(object):
        @classmethod
        def x(cls):
            return 1

        @property
        def y(self):
            return 2

        @staticmethod
        def z():
            return 3

    df1 = dumps(Foo1)
    df2 = dumps(Foo2)
    df3 = dumps(Foo3)
    df4 = dumps(Foo4)

    del Foo1
    del Foo2
    del Foo3
    del Foo4

    Foo1 = loads(df1)
    Foo2 = loads(df2)
    Foo3 = loads(df3)
    Foo4 = loads(df4)

    f1 = Foo1()
    f2 = Foo2()
    f3 = Foo3()
    f4 = Foo4()

    assert f1.foo() == 1234
    assert f2.foo() == 5678
    assert f3.foo() == 5678 + 1111
    assert Foo4.x() == 1

    f = loads(dumps(lambda:(some_global for i in xrange(1))))
    print list(f())
    assert list(f()) == [some_global]

########NEW FILE########
__FILENAME__ = shuffle
import os, os.path
import random
import urllib
import logging
import marshal
import struct
import time
import cPickle
import gzip
import Queue
import heapq
import platform

from dpark.util import decompress, spawn
from dpark.env import env
from dpark.tracker import GetValueMessage, SetValueMessage

MAX_SHUFFLE_MEMORY = 2000  # 2 GB

logger = logging.getLogger("shuffle")

class LocalFileShuffle:
    serverUri = None
    shuffleDir = None
    @classmethod
    def initialize(cls, isMaster):
        cls.shuffleDir = [p for p in env.get('WORKDIR')
                if os.path.exists(os.path.dirname(p))]
        if not cls.shuffleDir:
            return
        cls.serverUri = env.get('SERVER_URI', 'file://' + cls.shuffleDir[0])
        logger.debug("shuffle dir: %s", cls.shuffleDir)

    @classmethod
    def getOutputFile(cls, shuffleId, inputId, outputId, datasize=0):
        path = os.path.join(cls.shuffleDir[0], str(shuffleId), str(inputId))
        if not os.path.exists(path):
            try: os.makedirs(path)
            except OSError: pass
        p = os.path.join(path, str(outputId))

        if datasize > 0 and len(cls.shuffleDir) > 1:
            st = os.statvfs(path)
            free = st.f_bfree * st.f_bsize
            ratio = st.f_bfree * 1.0 / st.f_blocks
            if free < max(datasize, 1<<30) or ratio < 0.66:
                d2 = os.path.join(random.choice(cls.shuffleDir[1:]), str(shuffleId), str(inputId))
                if not os.path.exists(d2):
                    try: os.makedirs(d2)
                    except IOError: pass
                assert os.path.exists(d2), 'create %s failed' % d2
                p2 = os.path.join(d2, str(outputId))
                os.symlink(p2, p)
                if os.path.islink(p2):
                    os.unlink(p2) # p == p2
                return p2
        return p

    @classmethod
    def getServerUri(cls):
        return cls.serverUri


class ShuffleFetcher:
    def fetch(self, shuffleId, reduceId, func):
        raise NotImplementedError
    def stop(self):
        pass

class SimpleShuffleFetcher(ShuffleFetcher):
    def fetch_one(self, uri, shuffleId, part, reduceId):
        if uri == LocalFileShuffle.getServerUri():
            # urllib can open local file
            url = LocalFileShuffle.getOutputFile(shuffleId, part, reduceId)
        else:
            url = "%s/%d/%d/%d" % (uri, shuffleId, part, reduceId)
        logger.debug("fetch %s", url)

        tries = 2
        while True:
            try:
                f = urllib.urlopen(url)
                if f.code == 404:
                    f.close()
                    raise IOError("not found")

                d = f.read()
                flag = d[:1]
                length, = struct.unpack("I", d[1:5])
                if length != len(d):
                    raise ValueError("length not match: expected %d, but got %d" % (length, len(d)))
                d = decompress(d[5:])
                f.close()
                if flag == 'm':
                    d = marshal.loads(d)
                elif flag == 'p':
                    d = cPickle.loads(d)
                else:
                    raise ValueError("invalid flag")
                return d
            except Exception, e:
                logger.debug("Fetch failed for shuffle %d, reduce %d, %d, %s, %s, try again",
                        shuffleId, reduceId, part, url, e)
                tries -= 1
                if not tries:
                    logger.warning("Fetch failed for shuffle %d, reduce %d, %d, %s, %s",
                            shuffleId, reduceId, part, url, e)
                    from dpark.schedule import FetchFailed
                    raise FetchFailed(uri, shuffleId, part, reduceId)
                time.sleep(2**(2-tries)*0.1)

    def fetch(self, shuffleId, reduceId, func):
        logger.debug("Fetching outputs for shuffle %d, reduce %d", shuffleId, reduceId)
        serverUris = env.mapOutputTracker.getServerUris(shuffleId)
        parts = zip(range(len(serverUris)), serverUris)
        random.shuffle(parts)
        for part, uri in parts:
            d = self.fetch_one(uri, shuffleId, part, reduceId)
            func(d.iteritems())


class ParallelShuffleFetcher(SimpleShuffleFetcher):
    def __init__(self, nthreads):
        self.nthreads = nthreads
        self.start()

    def start(self):
        self.requests = Queue.Queue()
        self.results = Queue.Queue(self.nthreads)
        self.threads = [spawn(self._worker_thread) for i in range(self.nthreads)]

    def _worker_thread(self):
        from dpark.schedule import FetchFailed
        while True:
            r = self.requests.get()
            if r is None:
                break

            uri, shuffleId, part, reduceId = r
            try:
                d = self.fetch_one(*r)
                self.results.put((shuffleId, reduceId, part, d))
            except FetchFailed, e:
                self.results.put(e)

    def fetch(self, shuffleId, reduceId, func):
        logger.debug("Fetching outputs for shuffle %d, reduce %d", shuffleId, reduceId)
        serverUris = env.mapOutputTracker.getServerUris(shuffleId)
        if not serverUris:
            return

        parts = zip(range(len(serverUris)), serverUris)
        random.shuffle(parts)
        for part, uri in parts:
            self.requests.put((uri, shuffleId, part, reduceId))

        from dpark.schedule import FetchFailed
        for i in xrange(len(serverUris)):
            r = self.results.get()
            if isinstance(r, FetchFailed):
                self.stop() # restart
                self.start()
                raise r

            sid, rid, part, d = r
            func(d.iteritems())

    def stop(self):
        logger.debug("stop parallel shuffle fetcher ...")
        while not self.requests.empty():
            self.requests.get_nowait()
        while not self.results.empty():
            self.results.get_nowait()
        for i in range(self.nthreads):
            self.requests.put(None)
        for t in self.threads:
            t.join()


class Merger(object):

    def __init__(self, total, mergeCombiner):
        self.mergeCombiner = mergeCombiner
        self.combined = {}

    def merge(self, items):
        combined = self.combined
        mergeCombiner = self.mergeCombiner
        for k,v in items:
            o = combined.get(k)
            combined[k] = mergeCombiner(o, v) if o is not None else v

    def __iter__(self):
        return self.combined.iteritems()

class CoGroupMerger(object):
    def __init__(self, size):
        self.size = size
        self.combined = {}

    def get_seq(self, k):
        return self.combined.setdefault(k, tuple([[] for i in range(self.size)]))

    def append(self, i, items):
        for k, v in items:
            self.get_seq(k)[i].append(v)

    def extend(self, i, items):
        for k, v in items:
            self.get_seq(k)[i].extend(v)

    def __iter__(self):
        return self.combined.iteritems()

def heap_merged(items_lists, combiner):
    heap = []
    def pushback(it):
        try:
            k,v = it.next()
            # put i before value, so do not compare the value
            heapq.heappush(heap, (k, i, v))
        except StopIteration:
            pass
    for i, it in enumerate(items_lists):
        if isinstance(it, list):
            items_lists[i] = it = (k for k in it)
        pushback(it)
    if not heap: return

    last_key, i, last_value = heapq.heappop(heap)
    pushback(items_lists[i])

    while heap:
        k, i, v = heapq.heappop(heap)
        if k != last_key:
            yield last_key, last_value
            last_key, last_value = k, v
        else:
            last_value = combiner(last_value, v)
        pushback(items_lists[i])

    yield last_key, last_value

class sorted_items(object):
    next_id = 0
    @classmethod
    def new_id(cls):
        cls.next_id += 1
        return cls.next_id

    def __init__(self, items):
        self.id = self.new_id()
        self.path = path = os.path.join(LocalFileShuffle.shuffleDir,
            'shuffle-%d-%d.tmp.gz' % (os.getpid(), self.id))
        f = gzip.open(path, 'wb+')

        items = sorted(items)
        try:
            for i in items:
                s = marshal.dumps(i)
                f.write(struct.pack("I", len(s)))
                f.write(s)
            self.loads = marshal.loads
        except Exception, e:
            f.rewind()
            for i in items:
                s = cPickle.dumps(i)
                f.write(struct.pack("I", len(s)))
                f.write(s)
            self.loads = cPickle.loads
        f.close()

        self.f = gzip.open(path)
        self.c = 0

    def __iter__(self):
        self.f = gzip.open(self.path)
        self.c = 0
        return self

    def next(self):
        f = self.f
        b = f.read(4)
        if not b:
            f.close()
            if os.path.exists(self.path):
                os.remove(self.path)
            raise StopIteration
        sz, = struct.unpack("I", b)
        self.c += 1
        return self.loads(f.read(sz))

    def __dealloc__(self):
        self.f.close()
        if os.path.exists(self.path):
            os.remove(self.path)


class DiskMerger(Merger):
    def __init__(self, total, combiner):
        Merger.__init__(self, total, combiner)
        self.total = total
        self.archives = []
        self.base_memory = self.get_used_memory()
        self.max_merge = None
        self.merged = 0

    def get_used_memory(self):
        if platform.system() == 'Linux':
            for line in open('/proc/self/status'):
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) >> 10
        return 0

    def merge(self, items):
        Merger.merge(self, items)

        self.merged += 1
        #print 'used', self.merged, self.total, self.get_used_memory() - self.base_memory, self.base_memory
        if self.max_merge is None:
            if self.merged < self.total/5 and self.get_used_memory() - self.base_memory > MAX_SHUFFLE_MEMORY:
                self.max_merge = self.merged

        if self.max_merge is not None and self.merged >= self.max_merge:
            t = time.time()
            self.rotate()
            self.merged = 0
            #print 'after rotate', self.get_used_memory() - self.base_memory, time.time() - t

    def rotate(self):
        self.archives.append(sorted_items(self.combined.iteritems()))
        self.combined = {}

    def __iter__(self):
        if not self.archives:
            return self.combined.iteritems()

        if self.combined:
            self.rotate()
        return heap_merged(self.archives, self.mergeCombiner)

class BaseMapOutputTracker(object):
    def registerMapOutputs(self, shuffleId, locs):
        pass

    def getServerUris(self):
        pass

    def stop(self):
        pass

class LocalMapOutputTracker(BaseMapOutputTracker):
    def __init__(self):
        self.serverUris = {}

    def clear(self):
        self.serverUris.clear()

    def registerMapOutputs(self, shuffleId, locs):
        self.serverUris[shuffleId] = locs

    def getServerUris(self, shuffleId):
        return self.serverUris.get(shuffleId)

    def stop(self):
        self.clear()

class MapOutputTracker(BaseMapOutputTracker):
    def __init__(self):
        self.client = env.trackerClient
        logger.debug("MapOutputTracker started")

    def registerMapOutputs(self, shuffleId, locs):
        self.client.call(SetValueMessage('shuffle:%s' % shuffleId, locs))

    def getServerUris(self, shuffleId):
        locs = self.client.call(GetValueMessage('shuffle:%s' % shuffleId))
        logger.debug("Fetch done: %s", locs)
        return locs

def test():
    l = []
    for i in range(10):
        d = zip(range(10000), range(10000))
        l.append(sorted_items(d))
    hl = heap_merged(l, lambda x,y:x+y)
    for i in range(10):
        print i, hl.next()

    import logging
    logging.basicConfig(level=logging.INFO)
    from dpark.env import env
    import cPickle
    env.start(True)

    path = LocalFileShuffle.getOutputFile(1, 0, 0)
    f = open(path, 'w')
    f.write(cPickle.dumps([('key','value')], -1))
    f.close()

    uri = LocalFileShuffle.getServerUri()
    env.mapOutputTracker.registerMapOutputs(1, [uri])
    fetcher = SimpleShuffleFetcher()
    def func(k,v):
        assert k=='key'
        assert v=='value'
    fetcher.fetch(1, 0, func)

    tracker = MapOutputTracker(True)
    tracker.registerMapOutputs(2, [None, uri, None, None, None])
    assert tracker.getServerUris(2) == [None, uri, None, None, None]
    ntracker = MapOutputTracker(False)
    assert ntracker.getServerUris(2) == [None, uri, None, None, None]
    ntracker.stop()
    tracker.stop()

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = table
import os, sys
import re
import logging
from collections import namedtuple
import itertools

import msgpack

from dpark.rdd import DerivedRDD, OutputTableFileRDD
from dpark.dependency import Aggregator, OneToOneDependency

try:
    from pyhll import HyperLogLog
except ImportError:
    from dpark.hyperloglog import HyperLogLog

from hotcounter import HotCounter

SimpleAggs = {
    'sum': lambda x,y: x+y,
    'last': lambda x,y: y,
    'min': lambda x,y: x if x < y else y,
    'max': lambda x,y: x if x > y else y,
}

FullAggs = {
        'avg': (
            lambda v:(v, 1),
            lambda (s,c), v: (s+v, c+1),
            lambda (s1,c1), (s2,c2):(s1+s2, c1+c2),
            lambda (s,c): float(s)/c,
         ),
        'count': (
            lambda v: 1 if v is not None else 0,
            lambda s,v: s + (1 if v is not None else 0),
            lambda s1,s2: s1+s2,
            lambda s: s
         ),
        'adcount': (
            lambda v: HyperLogLog([v]),
            lambda s,v: s.add(v) or s,
            lambda s1,s2: s1.update(s2) or s1,
            lambda s: len(s)
        ),
        'group_concat': (
            lambda v: [v],
            lambda s,v: s.append(v) or s,
            lambda s1,s2: s1.extend(s2) or s1,
            lambda s: ','.join(s),
        ),
        'top': (
            lambda v: HotCounter([v], 20),
            lambda s,v: s.add(v) or s,
            lambda s1,s2: s1.update(s2) or s1,
            lambda s: s.top(20)
        ),
}

Aggs = dict(SimpleAggs)
Aggs.update(FullAggs)

Globals = {}
Globals.update(Aggs)
import math
Globals.update(math.__dict__)

__eval = eval
def eval(code, g={}, l={}):
    return __eval(code, g or Globals, l)

def table_join(f):
    def _join(self, other, left_keys=None, right_keys=None):
        if not left_keys:
            left_keys = [n for n in self.fields if n in other.fields]
        assert left_keys, 'need field names to join'
        if right_keys is None:
            right_keys = left_keys

        joined = f(self, other, left_keys, right_keys)

        ln = [n for n in self.fields if n not in left_keys]
        rn = [n for n in other.fields if n not in right_keys]
        def conv((k, (v1, v2))):
            return list(k) + (v1 or [None]*len(ln)) + (v2 or [None]*len(rn))
        return joined.map(conv).asTable(left_keys + ln + rn, self.name)

    return _join

class TableRDD(DerivedRDD):
    def __init__(self, rdd, fields, name='', field_types=None):
        DerivedRDD.__init__(self, rdd)
        self.name = name
        if isinstance(fields, str):
            fields = [n.strip() for n in fields.split(',')]
        self.fields = fields
        self.field_types = field_types

    def __str__(self):
        return '<Table(%s) from %s>' % (','.join(self.fields), self.prev)

    def iterator(self, split):
        cls = namedtuple(self.name or ('Row%d' % self.id), self.fields)
        return itertools.imap(lambda x:cls(*x), super(TableRDD, self).iterator(split))

    def compute(self, split):
        return self.prev.iterator(split)

    def _split_expr(self, expr):
        rs = []
        last, n = [], 0
        for part in expr.split(','):
            last.append(part)
            n += part.count('(') - part.count(')')
            if n == 0:
                rs.append(','.join(last))
                last = []
                n = 0
        assert not last, '() not match in expr'
        return rs

    def _replace_attr(self, e):
        es = re.split(r'([()\-+ */%,><=.\[\]]+)', e)
        named_fields = ['%s.%s' % (self.name, f) for f in self.fields]
        for i in range(len(es)):
            if es[i] in self.fields:
                es[i] = '_v[%d]' % self.fields.index(es[i])
            elif es[i] in named_fields:
                es[i] = '_v[%d]' % named_fields.index(es[i])
        return ''.join(es)

    def _create_expression(self, e):
        if callable(e):
            return e
        e = re.compile(r' as (\w+)', re.I).split(e)[0]
        return self._replace_attr(e)

    def _create_field_name(self, e):
        asp = re.compile(r' as (\w+)', re.I)
        m = asp.search(e)
        if m: return m.group(1)
        return re.sub(r'[(, )+*/\-]', '_', e).strip('_')

    def select(self, *fields, **named_fields):
        if len(fields) == 1 and not named_fields and fields[0] == '*':
            fields = self.fields
        new_fields = [self._create_field_name(e) for e in fields] + named_fields.keys()
        if len(set(new_fields)) != len(new_fields):
            raise Exception("dupicated fields: " + (','.join(new_fields)))

        selector = [self._create_expression(e) for e in fields] + \
            [self._create_expression(named_fields[n]) for n in new_fields[len(fields):]]
        _select = eval('lambda _v:(%s,)' % (','.join(e for e in selector)))

        need_attr = any(callable(f) for f in named_fields.values())
        return (need_attr and self or self.prev).map(_select).asTable(new_fields, self.name)

    def _create_reducer(self, index, e):
        """ -> creater, merger, combiner"""
        if '(' not in e:
            e = '(%s)' % e

        func_name, args = e.split('(', 1)
        func_name = func_name.strip()
        args = self._replace_attr(args.rsplit(')', 1)[0])
        if args == '*':
            args = '1'
        ag = '_x[%d]' % index
        if func_name in SimpleAggs:
            return (args, '%s(%s,%s)' % (func_name, ag, args),
                '%s(_x[%d],_y[%d])' % (func_name, index, index), ag)
        elif func_name in FullAggs:
            return ('%s[0](%s)' % (func_name, args),
                    '%s[1](%s, %s)' % (func_name, ag, args),
                    '%s[2](_x[%d], _y[%d])' % (func_name, index, index),
                    '%s[3](_x[%d])' % (func_name, index),)
        elif func_name:
            raise Exception("invalid aggregator function: %s" % func_name)
        else: # group by
            return ('[%s]' % args, '_x[%d].append(%s) or _x[%d]' % (index, args, index),
                    '_x[%d] + _y[%d]' % (index, index), ag)

    def selectOne(self, *fields, **named_fields):
        new_fields = [self._create_field_name(e) for e in fields] + named_fields.keys()
        if len(set(new_fields)) != len(new_fields):
            raise Exception("dupicated fields: " + (','.join(new_fields)))

        codes = ([self._create_reducer(i, e) for i,e in enumerate(fields)]
              + [self._create_reducer(i + len(fields), named_fields[n])
                    for i,n in enumerate(new_fields[len(fields):])])

        creater = eval('lambda _v:(%s,)' % (','.join(c[0] for c in codes)))
        merger = eval('lambda _x, _v:(%s,)' % (','.join(c[1] for c in codes)))
        combiner = eval('lambda _x, _y:(%s,)' % (','.join(c[2] for c in codes)))
        mapper = eval('lambda _x:(%s,)' % ','.join(c[3] for c in codes))

        def reducePartition(it):
            r = None
            iter(it)
            for i in it:
                if r is None:
                    r = creater(i)
                else:
                    r = merger(r, i)
            return r
        rs = self.ctx.runJob(self.prev, reducePartition)
        return [mapper(reduce(combiner, (x for x in rs if x is not None)))]

    def atop(self, field):
        return self.selectOne('top(%s)' % field)[0][0]

    def where(self, *conditions):
        need_attr = any(callable(f) for f in conditions)
        conditions = ' and '.join(['(%s)' % self._create_expression(c) for c in conditions])
        _filter = eval('lambda _v: %s' % conditions)
        return (need_attr and self or self.prev).filter(_filter).asTable(self.fields, self.name)

    def groupBy(self, keys, *fields, **kw):
        numSplits = kw.pop('numSplits', None)

        if not isinstance(keys, (list, tuple)):
            keys = [keys]
        key_names = [self._create_field_name(e) for e in keys]
        expr = ','.join(self._create_expression(e) for e in keys)
        gen_key = eval('lambda _v:(%s,)' % expr)

        values = [self._create_field_name(e) for e in fields] + kw.keys()
        kw.update((values[i], fields[i]) for i in range(len(fields)))
        codes = [self._create_reducer(i, kw[n]) for i,n in enumerate(values)]
        creater = eval('lambda _v:(%s,)' % (','.join(c[0] for c in codes)))
        merger = eval('lambda _x, _v:(%s,)' % (','.join(c[1] for c in codes)))
        combiner = eval('lambda _x, _y:(%s,)' % (','.join(c[2] for c in codes)))
        mapper = eval('lambda _x:(%s,)' % ','.join(c[3] for c in codes))

        agg = Aggregator(creater, merger, combiner)
        g = self.prev.map(lambda v:(gen_key(v), v)).combineByKey(agg, numSplits)
        return g.map(lambda (k,v): k + mapper(v)).asTable(key_names + values, self.name)

    def indexBy(self, keys=None):
        if keys is None:
            keys = self.fields[:1]
        if not isinstance(keys, (list, tuple)):
            keys = (keys,)

        def pick(keys, fields):
            ki = [fields.index(n) for n in keys]
            vi = [i for i in range(len(fields)) if fields[i] not in keys]
            def _(v):
                return tuple(v[i] for i in ki), [v[i] for i in vi]
            return _
        return self.prev.map(pick(keys, self.fields))

    @table_join
    def join(self, other, left_keys=None, right_keys=None):
        return self.indexBy(left_keys).join(other.indexBy(right_keys))

    @table_join
    def innerJoin(self, other, left_keys=None, right_keys=None):
        return self.indexBy(left_keys).innerJoin(other.indexBy(right_keys))

    @table_join
    def outerJoin(self, other, left_keys=None, right_keys=None):
        return self.indexBy(left_keys).outerJoin(other.indexBy(right_keys))

    @table_join
    def leftOuterJoin(self, other, left_keys=None, right_keys=None):
        o = other.indexBy(right_keys).collectAsMap()
        r = self.indexBy(left_keys).map(lambda (k,v):(k,(v,o.get(k))))
        r.mem += (sys.getsizeof(o) * 10) >> 20 # memory used by broadcast obj
        return r

    @table_join
    def rightOuterJoin(self, other, left_keys=None, right_keys=None):
        return self.indexBy(left_keys).rightOuterJoin(other.indexBy(right_keys))

    def sort(self, fields, reverse=False, numSplits=None):
        if isinstance(fields, str):
            keys = [self.fields.index(fields)]
        else:
            keys = [self.fields.index(n) for n in fields]
        def key(v):
            return tuple(v[i] for i in keys)

        if len(self) <= 16: # maybe grouped
            data = sorted(self.prev.collect(), key=key, reverse=reverse)
            return self.ctx.makeRDD(data).asTable(self.fields, self.name)

        return self.prev.sort(key, reverse, numSplits).asTable(self.fields, self.name)

    def top(self, n, fields, reverse=False):
        keys = [self.fields.index(i) for i in fields]
        def key(v):
            return tuple(v[i] for i in keys)
        return self.prev.top(n, key=key, reverse=reverse)

    def collect(self):
        return self.prev.collect()

    def take(self, n):
        return self.prev.take(n)

    def execute(self, sql, asTable=False):
        sql_p = re.compile(r'(select|from|(?:inner|left outer)? join(?: each)?|where|group by|having|order by|limit) ', re.I)
        parts = [i.strip() for i in sql_p.split(sql)[1:]]
        kw = dict(zip([i.lower() for i in parts[::2]], parts[1::2]))

        for type in kw:
            if 'join' not in type:
                continue

            table, cond = re.split(r' on ', kw[type], re.I)
            if '(' in table:
                last_index = table.rindex(')')
                name = table[last_index + 1:].split(' ')[-1]
                expr = table[:last_index + 1]
            else:
                name = table.strip()
                expr = ''
            other = create_table(self.ctx, name, expr)

            left_keys, right_keys = [], []
            for expr in re.split(r' and ', cond, re.I):
                lf, rf = re.split(r'=+', expr)
                if lf.startswith(name + '.'):
                    lf, rf = rf, lf
                left_keys.append(lf[lf.rindex('.') + 1:].strip())
                right_keys.append(rf[rf.rindex('.') + 1:].strip())
            if 'left outer' in type:
                r = self.leftOuterJoin(other, left_keys, right_keys)
            else:
                r = self.innerJoin(other, left_keys, right_keys)
            # remove table prefix in colnames
            for n in (self.name, name):
                if not n: continue
                p = re.compile(r'(%s\.)(?=[\w])' % n)
                for k in ('select', 'where', 'group by', 'having', 'order by'):
                    if k in kw:
                        kw[k] = p.sub('', kw[k])
            break
        else:
            r = self

        # select needed cols
        #r = self.select(*[n for n in self.fields if n in sql])
        cols = [n.strip() for n in self._split_expr(kw['select'])]

        if 'where' in kw:
            r = r.where(kw['where'])

        if 'top(' in kw['select']:
            field = re.match(r'top\((.*?)\)', kw['select']).group(1)
            rs = r.atop(field)
            if asTable:
                rs = self.ctx.makeRDD(rs).asTable([field, 'count'], self.name)
            return rs

        elif 'group by' in kw:
            keys = [n.strip() for n in kw['group by'].split(',')]
            values = dict([(r._create_field_name(n), n) for n in cols if n not in keys])
            r = r.groupBy(keys, *cols)

            if 'having' in kw:
                r = r.where(kw['having'])

        elif 'select' in kw:
            for name in Aggs:
                if (name + '(') in kw['select']:
                    return r.selectOne(*cols)
            r = r.select(*cols)

        if 'order by' in kw:
            keys = kw['order by']
            reverse = False
            if keys.endswith(' desc'):
                reverse = True
                keys = keys[:-5].strip()
            keys = [n.strip() for n in keys.split(',')]
            if 'limit' in kw:
                return r.top(int(kw['limit']), keys, not reverse)
            r = r.sort(keys, reverse)

        if 'limit' in kw:
            return r.take(int(kw['limit']))
        if asTable:
            return r
        else:
            return r.collect()

    def save(self, path, overwrite=True, compress=True):
        r = OutputTableFileRDD(self.prev, path,
            overwrite=overwrite, compress=compress).collect()
        open(os.path.join(path, '.field_names'), 'w').write('\t'.join(self.fields))
        return r


CachedTables = {
}

def create_table(ctx, name, expr):
    if name in CachedTables:
        return CachedTables[name]

    assert expr, 'table %s is not defined' % name
    t = eval('ctx.' + expr, Globals, locals())
    if isinstance(t, TableRDD):
        t.name = name
        CachedTables[name] = t
        return t

    # TODO: try to find .fields

    # guess format
    row = t.first()
    if isinstance(row, str):
        if '\t' in row:
            t = t.fromCsv(dialet='excel-tab')
        elif ',' in row:
            t = t.fromCsv(dialet='excel')
        else:
            t = t.map(lambda line:line.strip().split(' '))

    # fake fields names
    row = t.first()
    fields = ['f%d' % i for i in range(len(row))]
    t = t.asTable(fields, name)
    CachedTables[name] = t
    return t


########NEW FILE########
__FILENAME__ = tabular
import os
import zlib
import types
import socket
import struct
import marshal
import cPickle
from lz4 import compress, decompress
from dpark.rdd import RDD, MultiSplit, TextFileRDD, Split, ParallelCollection, cached
from dpark.util import chain
from dpark.moosefs import walk
from dpark.bitindex import Bloomfilter, BitIndex
from dpark.serialize import dumps, loads
from dpark.dependency import OneToOneDependency, OneToRangeDependency

'''
Strip Format:
+---------------+-----------------+---------------+-------+---------------+------------------+
|  Header_Size  |     *Header     |   *Column_0   |  ...  |   *Column_n   |        \0        |
|      (4)      |  (Header_Size)  |  (Header[0])  |       |  (Header[n])  |  (Padding_Size)  |
+---------------+-----------------+---------------+-------+---------------+------------------+

Padding_Size = STRIPE_SIZE - Header_Size - sum(Header)

Footer Format:
+------------------+-----------------+---------------+----------------+
|     +Indices     |     +Fields     |  Fields_Size  |  Indices_Size  |
|  (Indices_Size)  |  (Fields_Size)  |      (4)      |      (4)       |
+------------------+-----------------+---------------+----------------+

*: lz4 + marshal
+: zlib + cPickle
'''

STRIPE_SIZE = 1 << 26
STRIPE_HEADER_SIZE = 1 << 15
STRIPE_DATA_SIZE = STRIPE_SIZE - STRIPE_HEADER_SIZE

BF_SIZE = 1 << 27
BF_HASHES = 3

MAX_BIT_INDEX_SIZE = 1 << 14

BITMAP_INDEX = 0
BLOOMFILTER_INDEX = 1

class NamedTuple(object):
    _fields = []
    _values = ()
    def __init__(self, fields, values):
        if isinstance(fields, types.StringTypes):
            fields = fields.replace(',', ' ').split()

        fields = list(fields)
        values = tuple(values)
        if len(set(fields)) != len(fields):
            raise ValueError('Duplicated field names!')

        if len(fields) != len(values):
            raise ValueError('Key/value length not match!')

        self._fields = fields
        self._values = values

    def __getattr__(self, key):
        if key in self._fields:
            return self._values[self._fields.index(key)]
        return getattr(self._values, key)

    def __repr__(self):
        return '<%s(%s)>' % (
            self.__class__.__name__,
            ', '.join('%s=%s' % (k, v) for k, v in zip(self._fields, self._values))
        )

    def __nonzero__(self):
        return bool(self._values)

    def __len__(self):
        return len(self._values)

    def __getitem__(self, key):
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __contains__(self, item):
        return item in self._values

class AdaptiveIndex(object):
    def __init__(self):
        self.index = {}
        self.index_type = BITMAP_INDEX

    def add(self, value, position):
        if self.index_type == BITMAP_INDEX and len(self.index) > MAX_BIT_INDEX_SIZE:
            index = self.index
            self.index_type = BLOOMFILTER_INDEX
            self.index = Bloomfilter(BF_SIZE, BF_HASHES)
            for v in index:
                for pos in index[v].positions():
                    self.index.add([(v, pos)])

        if self.index_type == BITMAP_INDEX:
            if value not in self.index:
                self.index[value] = BitIndex()
            index = self.index[value]
            index.set(position)

        if self.index_type == BLOOMFILTER_INDEX:
            self.index.add([(value, position)])
            assert (value, position) in self.index

    def get(self, value, pos):
        if self.index_type == BITMAP_INDEX:
            return self.index[value].get(pos) if value in self.index else False
        else:
            return (value, pos) in self.index

    def filter(self, fun):
        if self.index_type == BITMAP_INDEX:
            return chain(v.positions() for k, v in self.index.items() if fun(k))

class TabularSplit(Split):
    def __init__(self, index, rdd, sp):
        self.index = index
        self.rdd = rdd
        self.split = sp

class TabularRDD(RDD):
    def __init__(self, ctx, path, fields = None, taskMemory=None):
        RDD.__init__(self, ctx)
        if taskMemory:
            self.mem = taskMemory

        if isinstance(path, basestring):
            files = self._get_files(path)
        else:
            files = chain(self._get_files(p) for p in path)

        self.rdds = [TabularFileRDD(ctx, f, fields) for f in files]
        self._splits = []
        i = 0
        for rdd in self.rdds:
            for sp in rdd.splits:
                self._splits.append(TabularSplit(i, rdd, sp))
                i += 1
        self.dependencies = [OneToOneDependency(rdd) for rdd in self.rdds]

    def _get_files(self, path):
        path = os.path.realpath(path)
        if os.path.isdir(path):
            for root,dirs,names in walk(path):
                for n in sorted(names):
                    if not n.startswith('.'):
                        yield os.path.join(root, n)

        else:
            yield path

    def __repr__(self):
        return '<%s %d %s...>' % (self.__class__.__name__, len(self.rdds),
                                  ','.join(str(rdd) for rdd in self.rdds[:1]))

    def _preferredLocations(self, split):
        return split.rdd.preferredLocations(split.split)

    def compute(self, split):
        return split.rdd.iterator(split.split)

    def filterByIndex(self, **kw):
        return FilteredByIndexRDD(self, kw)

class FilteredByIndexRDD(RDD):
    def __init__(self, rdd, filters):
        RDD.__init__(self, rdd.ctx)
        self.rdd = rdd
        self.filters = filters
        self.mem = max(self.mem, rdd.mem)
        self.dependencies = [OneToOneDependency(rdd)]
        self._splits = self._get_splits()

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.rdd)

    def _preferredLocations(self, split):
        return self.rdd.preferredLocations(split)

    @cached
    def __getstate__(self):
        d = RDD.__getstate__(self)
        del d['filters']
        return d, dumps(self.filters)

    def __setstate__(self, state):
        self.__dict__, filters = state
        self.filters = loads(filters)

    def _get_splits(self):
        filters = self.filters
        def _filter(v):
            path, splits = v
            result_set = set(sp.split.begin / STRIPE_SIZE for sp in splits)
            with open(path, 'rb') as f:
                f.seek(-8, 2)
                footer_fields_size, footer_indices_size = struct.unpack('II', f.read(8))
                f.seek(-8 -footer_fields_size -footer_indices_size, 2)
                indices = cPickle.loads(zlib.decompress(f.read(footer_indices_size)))
                _fields = marshal.loads(decompress(f.read(footer_fields_size)))
                for k, v in filters.iteritems():
                    result = set()
                    if k not in _fields:
                        raise RuntimeError('%s is not in fields!' % k)

                    if k not in indices:
                        raise RuntimeError('%s is not indexed' % k)

                    index = indices[k]
                    if isinstance(v, types.FunctionType):
                        r = index.filter(v)
                        if r is not None:
                            result = set(r)
                        else:
                            result = result_set
                    else:
                        if not isinstance(v, list):
                            v = [v]

                        for vv in v:
                            for id in result_set:
                                if index.get(vv, id):
                                    result.add(id)

		    result_set &= result

            for sp in splits:
                id = sp.split.begin / STRIPE_SIZE
                if id in result:
                    yield sp

        sp_dict = {}
        for sp in self.rdd.splits:
            path = sp.rdd.path
            if path not in sp_dict:
                sp_dict[path] = [sp]
            else:
                sp_dict[path].append(sp)

        rdd = ParallelCollection(self.ctx, sp_dict.items(), len(sp_dict))
        return rdd.flatMap(_filter).collect()

    def compute(self, split):
        for t in self.rdd.iterator(split):
            for k, v in self.filters.iteritems():
                value = getattr(t, k)
                if isinstance(v, types.FunctionType):
                    if not v(value):
                        break

                else:
                    if not isinstance(v, list):
                        v = [v]

                    if value not in v:
                        break
            else:
                yield t

class TabularFileRDD(TextFileRDD):
    def __init__(self, ctx, path, fields = None):
        TextFileRDD.__init__(self, ctx, path, splitSize = STRIPE_SIZE)
        if isinstance(fields, basestring):
            fields = fields.replace(',', ' ').split()

        self.fields = map(str, fields) if fields is not None else None

    def compute(self, split):
        with self.open_file() as f:
            f.seek(-8,2)
            footer_fields_size, footer_indices_size = struct.unpack('II', f.read(8))
            footer_offset = self.size - 8 - footer_fields_size - footer_indices_size
            footer_fields_offset = self.size - 8 - footer_fields_size
            if split.begin >= footer_offset:
                return

            start = split.begin
            end = min(split.end, footer_offset)
            stripe_id = start / STRIPE_SIZE
            f.seek(footer_fields_offset)
            _fields = marshal.loads(decompress(f.read(footer_fields_size)))

            if self.fields is None:
                field_ids = range(len(_fields))
                field_names = _fields
            else:
                field_names = []
                field_ids = [None] * len(_fields)
                for i, v in enumerate(self.fields):
                    if v in _fields:
                        index = _fields.index(v)
                        field_ids[index] = i
                        field_names.append(v)
                    else:
                        raise RuntimeError('Unknown field: %s' % v)

            f.seek(start)
            header_size, = struct.unpack('I', f.read(4))
            header = marshal.loads(decompress(f.read(header_size)))
            content = [None] * len(field_names)
            for id, size in enumerate(header):
                index = field_ids[id]
                if index is not None:
                    content[index] = marshal.loads(decompress(f.read(size)))
                else:
                    f.seek(size, 1)

            for r in zip(*content):
                yield NamedTuple(field_names, r)

class OutputTabularRDD(RDD):
    def __init__(self, rdd, path, field_names, indices=None, numSplits=None):
        RDD.__init__(self, rdd.ctx)
        self.prev = rdd
        self.mem = rdd.mem + 600
        self.path = path
        if os.path.exists(path):
            raise RuntimeError('path already exists: %s' % path)

        os.makedirs(path)
        if isinstance(field_names, basestring):
            field_names = field_names.replace(',', ' ').split()

        if len(set(field_names)) != len(field_names):
            raise ValueError('duplicated field names')

        self.fields = map(str, field_names)
        if isinstance(indices, types.StringTypes):
            indices = indices.replace(',', ' ').split()

        self.indices = set()
        if indices:
            for i in indices:
                i = str(i)
                if i not in self.fields:
                    raise ValueError('index field %s not in field list' % i)

                self.indices.add(i)

        prev_splits = len(rdd)
        numSplits = min(numSplits or prev_splits, prev_splits)
        self.numSplits = min(numSplits, prev_splits)
        s = [int(round(1.0*prev_splits/numSplits*i)) for i in xrange(numSplits + 1)]
        self._splits = [MultiSplit(i, rdd.splits[s[i]:s[i+1]]) for i in xrange(numSplits)]
        self.dependencies = [OneToRangeDependency(rdd, int(prev_splits/numSplits),
                                                  prev_splits)]

    def __repr__(self):
        return '<OutputTabularRDD %s %s>' % (self.path, self.prev)

    def compute(self, split):
        buffers = [list() for i in self.fields]
        remain_size = STRIPE_DATA_SIZE
        path = os.path.join(self.path, '%04d.dt' % split.index)
        tpath = os.path.join(self.path, '.%04d_%s_%s.dt' % (
            split.index, socket.gethostname(), os.getpid()))
        indices = dict((i, AdaptiveIndex()) for i in self.indices)

        def write_stripe(f, compressed, header, padding=True):
            h = compress(marshal.dumps(header))
            assert len(h) < STRIPE_HEADER_SIZE
            f.write(struct.pack('I', len(h)))
            f.write(h)
            padding_size = STRIPE_SIZE - len(h) - 4
            for c in compressed:
                f.write(c)
                padding_size -= len(c)

            if padding:
                f.write('\0' * padding_size)

        try:
            with open(tpath, 'wb+') as f:
                stripe_id = 0
                for it in chain(self.prev.iterator(sp) for sp in split.splits):
                    row = it[:len(self.fields)]
                    size = len(marshal.dumps(tuple(row)))
                    if size > STRIPE_DATA_SIZE:
                        raise RuntimeError('Row too big')

                    if size > remain_size:
                        compressed = [compress(marshal.dumps(tuple(b))) for b in buffers]
                        _sizes = tuple(map(len, compressed))
                        _remain_size = STRIPE_DATA_SIZE - sum(_sizes)
                        if size > _remain_size:
                            write_stripe(f, compressed, _sizes)
                            buffers = [list() for i in self.fields]
                            remain_size = STRIPE_DATA_SIZE
                            stripe_id += 1
                        else:
                            remain_size = _remain_size

                    remain_size -= size
                    for i, value in enumerate(row):
                        buffers[i].append(value)
                        field = self.fields[i]
                        if field in self.indices:
                            indices[field].add(value, stripe_id)

                if any(buffers):
                    compressed = [compress(marshal.dumps(tuple(b))) for b in buffers]
                    _sizes = tuple(map(len, compressed))
                    write_stripe(f, compressed, _sizes, False)

                footer_indices = zlib.compress(cPickle.dumps(indices, -1))
                footer_fields = compress(marshal.dumps(self.fields))
                f.write(footer_indices)
                f.write(footer_fields)
                f.write(struct.pack('II', len(footer_fields), len(footer_indices)))

            try:
                os.rename(tpath, path)
            except OSError:
                pass

            yield path
        finally:
            try:
                os.remove(tpath)
            except OSError:
                pass


########NEW FILE########
__FILENAME__ = task
import os,os.path
import socket
import marshal
import cPickle
import logging
import struct

from dpark.util import compress, decompress
from dpark.serialize import marshalable, load_func, dump_func
from dpark.shuffle import LocalFileShuffle

logger = logging.getLogger("dpark")

class Task:
    def __init__(self):
        self.id = Task.newId()

    nextId = 0
    @classmethod
    def newId(cls):
        cls.nextId += 1
        return cls.nextId

    def run(self, id):
        raise NotImplementedError

    def preferredLocations(self):
        raise NotImplementedError


class DAGTask(Task):
    def __init__(self, stageId):
        Task.__init__(self)
        self.stageId = stageId

    def __repr__(self):
        return '<task %d:%d>'%(self.stageId, self.id)


class ResultTask(DAGTask):
    def __init__(self, stageId, rdd, func, partition, locs, outputId):
        DAGTask.__init__(self, stageId)
        self.rdd = rdd
        self.func = func
        self.partition = partition
        self.split = rdd.splits[partition]
        self.locs = locs
        self.outputId = outputId

    def run(self, attemptId):
        logger.debug("run task %s with %d", self, attemptId)
        return self.func(self.rdd.iterator(self.split))

    def preferredLocations(self):
        return self.locs

    def __repr__(self):
        return "<ResultTask(%d) of %s" % (self.partition, self.rdd)

    def __getstate__(self):
        d = dict(self.__dict__)
        del d['func']
        return d, dump_func(self.func)

    def __setstate__(self, state):
        self.__dict__, code = state
        self.func = load_func(code)


class ShuffleMapTask(DAGTask):
    def __init__(self, stageId, rdd, dep, partition, locs):
        DAGTask.__init__(self, stageId)
        self.rdd = rdd
        self.shuffleId = dep.shuffleId
        self.aggregator = dep.aggregator
        self.partitioner = dep.partitioner
        self.partition = partition
        self.split = rdd.splits[partition]
        self.locs = locs

    def __repr__(self):
        return '<ShuffleTask(%d, %d) of %s>' % (self.shuffleId, self.partition, self.rdd)

    def preferredLocations(self):
        return self.locs

    def run(self, attempId):
        logger.debug("shuffling %d of %s", self.partition, self.rdd)
        numOutputSplits = self.partitioner.numPartitions
        getPartition = self.partitioner.getPartition
        mergeValue = self.aggregator.mergeValue
        createCombiner = self.aggregator.createCombiner

        buckets = [{} for i in range(numOutputSplits)]
        for k,v in self.rdd.iterator(self.split):
            bucketId = getPartition(k)
            bucket = buckets[bucketId]
            r = bucket.get(k, None)
            if r is not None:
                bucket[k] = mergeValue(r, v)
            else:
                bucket[k] = createCombiner(v)

        for i in range(numOutputSplits):
            try:
                if marshalable(buckets[i]):
                    flag, d = 'm', marshal.dumps(buckets[i])
                else:
                    flag, d = 'p', cPickle.dumps(buckets[i], -1)
            except ValueError:
                flag, d = 'p', cPickle.dumps(buckets[i], -1)
            cd = compress(d)
            for tried in range(1, 4):
                try:
                    path = LocalFileShuffle.getOutputFile(self.shuffleId, self.partition, i, len(cd) * tried)
                    tpath = path + ".%s.%s" % (socket.gethostname(), os.getpid())
                    f = open(tpath, 'wb', 1024*4096)
                    f.write(flag + struct.pack("I", 5 + len(cd)))
                    f.write(cd)
                    f.close()
                    os.rename(tpath, path)
                    break
                except IOError, e:
                    logging.warning("write %s failed: %s, try again (%d)", path, e, tried)
                    try: os.remove(tpath)
                    except OSError: pass
            else:
                raise

        return LocalFileShuffle.getServerUri()

########NEW FILE########
__FILENAME__ = tracker
import socket
import zmq
import logging
import time

from dpark.env import env
from dpark.util import spawn

logger = logging.getLogger("tracker")

class TrackerMessage(object):
    pass

class StopTrackerMessage(TrackerMessage):
    pass

class SetValueMessage(TrackerMessage):
    def __init__(self, key, value):
        self.key = key
        self.value = value

class AddItemMessage(TrackerMessage):
    def __init__(self, key, item):
        self.key = key
        self.item = item

class RemoveItemMessage(TrackerMessage):
    def __init__(self, key, item):
        self.key = key
        self.item = item

class GetValueMessage(TrackerMessage):
    def __init__(self, key):
        self.key = key

class TrackerServer(object):
    locs = {}
    def __init__(self):
        self.addr = None
        self.thread = None

    def start(self):
        self.thread = spawn(self.run)
        while self.addr is None:
            time.sleep(0.01)

    def stop(self):
        sock = env.ctx.socket(zmq.REQ)
        sock.connect(self.addr)
        sock.send_pyobj(StopTrackerMessage())
        confirm_msg = sock.recv_pyobj()
        sock.close()
        self.thread.join()
        return confirm_msg

    def get(self, key):
        return self.locs.get(key, [])

    def set(self, key, value):
        if not isinstance(value, list):
            value = [value]

        self.locs[key] = value

    def add(self, key, item):
        if key not in self.locs:
            self.locs[key] = []

        self.locs[key].append(item)

    def remove(self, key, item):
        if item in self.locs[key]:
            self.locs[key].remove(item)

    def run(self):
        locs = self.locs
        sock = env.ctx.socket(zmq.REP)
        port = sock.bind_to_random_port("tcp://0.0.0.0")
        self.addr = "tcp://%s:%d" % (socket.gethostname(), port)
        logger.debug("TrackerServer started at %s", self.addr)
        def reply(msg):
            sock.send_pyobj(msg)
        while True:
            msg = sock.recv_pyobj()
            if isinstance(msg, SetValueMessage):
                self.set(msg.key, msg.value)
                reply('OK')
            elif isinstance(msg, AddItemMessage):
                self.add(msg.key, msg.item)
                reply('OK')
            elif isinstance(msg, RemoveItemMessage):
                self.remove(msg.key, msg.item)
                reply('OK')
            elif isinstance(msg, GetValueMessage):
                reply(self.get(msg.key))
            elif isinstance(msg, StopTrackerMessage):
                reply('OK')
                break
            else:
                logger.error("unexpected msg %s %s", msg, type(msg))
                reply('ERROR')
        sock.close()
        logger.debug("stop TrackerServer %s", self.addr)

class TrackerClient(object):
    def __init__(self, addr):
        self.addr = addr

    def call(self, msg):
        try:
            sock = env.ctx.socket(zmq.REQ)
            sock.connect(self.addr)
            sock.send_pyobj(msg)
            return sock.recv_pyobj()
        finally:
            sock.close()


########NEW FILE########
__FILENAME__ = util
# util
import types
from zlib import compress as _compress, decompress
import threading
import warnings
try:
    from dpark.portable_hash import portable_hash as _hash
except ImportError:
    import pyximport
    pyximport.install(inplace=True)
    from dpark.portable_hash import portable_hash as _hash

try:
    import os
    import pwd
    def getuser():
        return pwd.getpwuid(os.getuid()).pw_name
except:
    import getpass
    def getuser():
        return getpass.getuser()

COMPRESS = 'zlib'
def compress(s):
    return _compress(s, 1)

try:
    from lz4 import compress, decompress
    COMPRESS = 'lz4'
except ImportError:
    try:
        from snappy import compress, decompress
        COMPRESS = 'snappy'
    except ImportError:
        pass

def spawn(target, *args, **kw):
    t = threading.Thread(target=target, name=target.__name__, args=args, kwargs=kw)
    t.daemon = True
    t.start()
    return t

# hash(None) is id(None), different from machines
# http://effbot.org/zone/python-hash.htm
def portable_hash(value):
    return _hash(value)

# similar to itertools.chain.from_iterable, but faster in PyPy
def chain(it):
    for v in it:
        for vv in v:
            yield vv

def izip(*its):
    its = [iter(it) for it in its]
    try:
        while True:
            yield tuple([it.next() for it in its])
    except StopIteration:
        pass

########NEW FILE########
__FILENAME__ = cos
import sys
sys.path.append('../')
import logging
import dpark

name = 'rating.txt'

def parse(line):
    sid, uid, r, f = line.strip().split('\t')
    defaults = {'F':4.5, 'P':3.7, 'N':4.0}
    if r == 'None':
        r = defaults[f]
    return (sid, (uid, float(r)))
rating = dpark.textFile(name, numSplits=2).map(parse).groupByKey(2)#.cache()
#print 'us', rating.first()
print rating.count()

def reverse(it):
    s = {}
    for k, us in it:
        for u,r in us:
            s.setdefault(u, {})[k] = r
    return s

def vsum(a, b):
#    return 1
    if len(a) < len(b):
        a, b = b, a
    d = dict(a)
    s = 0
    for u,r in b:
        s += r * d.get(u, 0)
    return s

# should replace this function with c extension for best performance.
def cos((l1, l2)):
    l1 = list(l1)
    l2 = list(l2)
    d2 = dict(l2)
    u2 = reverse(l2)
    for sid1, us1 in l1:
        s = {}
        for u,r in us1:
            if u in u2:
                for sid2 in u2[u]:
                    if sid2 not in s:
                        s[sid2] = (vsum(us1, d2[sid2]),sid2)
        sim = sorted(s.values(), reverse=True)[:5]
#        sim = sorted([(vsum(us1, us2),sid2) for sid2,us2 in l2
#            if sid2!=sid1], reverse=True)[:5]
        yield sid1, sim

final = rating.glom().cartesian(rating.glom())
print final.count()
final = final.flatMap(cos)
#print 'sim', final.first()
final = final.reduceByKey(lambda x,y:x+y).mapValue(lambda x:sorted(x,reverse=True)[:5])
print 'final',final.count()

########NEW FILE########
__FILENAME__ = cos_c
import logging
from context import SparkContext
import gc
gc.disable()

spark = SparkContext()

name = 'rating.txt'
name = 'rating.txt.medium'
name = 'rating.txt.large'
def parse(line):
    try:
        sid, uid, r, f = line.split('\t')
        defaults = {'F':4.5, 'P':3.7, 'N':4.0}
        if r == 'None':
            r = defaults.get(f, 0)
        return (int(sid), (int(uid), float(r)))
    except Exception:
        return (int(sid), (int(uid), 0))
rating = spark.textFile(name, numSplits=32).map(parse).groupByKey(16).filter(lambda (x,y):len(y)>10)#.cache()
#print 'us', rating.first()

def convert(it):
    s = {}
    for k, us in it:
        for u,r in us:
            s.setdefault(k, {})[u] = r
    return s

def cos((l1, l2)):
    import map_sim
    r = map_sim.map_sim([], convert(l1), convert(l2), 10)
    for k in r:
        yield k, r[k]

final = rating.glom().cartesion(rating.glom()).flatMap(cos)
#print 'sim', final.first()
final = final.reduceByKey(lambda x,y:x+y).mapValue(lambda x:sorted(x,reverse=True)[:5])
print 'final',final.count()

########NEW FILE########
__FILENAME__ = demo
import math
import random
import os, sys
from pprint import pprint
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dpark

# range
nums = dpark.parallelize(range(100), 4)
print nums.count()
print nums.reduce(lambda x,y:x+y)

# text search
f = dpark.textFile("./", ext='py').map(lambda x:x.strip())
log = f.filter(lambda line: 'logging' in line).cache()
print 'logging', log.count()
print 'error', log.filter(lambda line: 'error' in line).count()
for line in log.filter(lambda line: 'error' in line).collect():
    print line

# word count
counts = f.flatMap(lambda x:x.split()).map(lambda x:(x,1)).reduceByKey(lambda x,y:x+y).cache()
pprint(counts.filter(lambda (_,v): v>50).collectAsMap())
pprint(sorted(counts.filter(lambda (_,v): v>20).map(lambda (x,y):(y,x)).groupByKey().collect()))
pprint(counts.map(lambda v: "%s:%s"%v ).saveAsTextFile("wc/"))

# Pi
import random
def rand(i):
    x = random.random()
    y = random.random()
    return (x*x + y*y) < 1.0 and 1 or 0

N = 100000
count = dpark.parallelize(range(N), 4).map(rand).reduce(lambda x,y:x+y)
print 'pi is ', 4.0 * count / N

# Logistic Regression
def parsePoint(line):
    ns = map(int, line.split())
    return (ns[:-1], ns[-1])

def dot(a, b):
    return sum(i*j for i,j in zip(a,b))

def incm(w):
    def inc((x, y)):
        wx = dot(w,x)
        if wx < -500:
            wx = -500
        yy = y-1/(1+math.exp(-wx))
        return [yy * xx for xx in x]
    return inc
add = lambda x,y: [x[i]+y[i] for i in range(len(x))]

points = dpark.textFile("point.txt").map(parsePoint).cache()
print points.collect()
w = [1,-160]
for i in range(10):
    gradient = points.map(incm(w)).reduce(add)
    print w, gradient
    if sum(abs(g) for g in gradient) < 0.001:
        break
    w = [a + b/(i+1)  for a, b in zip(w, gradient)]
print "Final separating plane: ", w
print 1/(1+math.exp(-dot(w, [150, 1])))
print 1/(1+math.exp(-dot(w, [180, 1])))

########NEW FILE########
__FILENAME__ = dsgd
# -*- coding: utf-8 -*-
from dpark import _ctx as dpark
from dpark.mutable_dict import MutableDict
from random import shuffle
import cPickle
import numpy

with open('ab.mat') as f:
    ori = cPickle.loads(f.read())

k = 50
d = 20
M = len(ori)
V = len(ori[0])
assert M % d == 0
assert V % d == 0

m = M / d
v = V / d

GAMMA = 0.02
LAMBDA = 0.1
STEP=0.9


W = MutableDict(d)
H = MutableDict(d)

ori_b = dpark.broadcast(ori)
def sgd((i, j)):
    Wi = W.get(i)
    if Wi is None:
        Wi = numpy.random.rand(m, k)
        W.put(i, Wi)

    Hj = H.get(j)
    if Hj is None:
        Hj = numpy.random.rand(v, k)
        H.put(j, Hj)

    ori = ori_b.value
    Oij = ori[i*m:(i+1)*m, j*v:(j+1)*v]

    for x in xrange(m):
        for y in xrange(v):
            pred = Wi[x].dot(Hj[y])
            err = int(Oij[x][y]) - int(pred)
            w = Wi[x] + GAMMA * (Hj[y]*err - LAMBDA*Wi[x])
            h = Hj[y] + GAMMA * (Wi[x]*err - LAMBDA*Hj[y])

            Wi[x] = w
            Hj[y] = h

    W.put(i, Wi)
    H.put(j, Hj)

rdd = dpark.makeRDD(range(d))
rdd = rdd.cartesian(rdd).cache()

def calc_err((i, j)):
    Wi = W.get(i)
    Hj = H.get(j)

    ori = ori_b.value
    Rij = Wi.dot(Hj.T)
    Oij = ori[i*m:(i+1)*m, j*v:(j+1)*v]
    return ((Rij - Oij) ** 2).sum()

J = range(d)
while True:
    for i in xrange(d):
        dpark.makeRDD(zip(range(d), J), d).foreach(sgd)
        J = J[1:] + [J[0]]

    GAMMA *= STEP
    shuffle(J)
    err = rdd.map(calc_err).reduce(lambda x,y:x+y)
    rmse = numpy.sqrt(err/(M*V))
    print rmse
    if rmse < 0.01:
        break


########NEW FILE########
__FILENAME__ = jit
'''
    Notice:
    1. The function for jit should locate in mfs
    2. For the usage of jit types and signatures, please refer Numba documentation <http://numba.github.com/numba-doc/0.10/index.html>
'''
from dpark import _ctx as dpark, jit, autojit
import numpy

@jit('f8(f8[:])')
def add1(x):
    sum = 0.0
    for i in xrange(x.shape[0]):
        sum += i*x[i]
    return sum

@autojit
def add2(x):
    sum = 0.0
    for i in xrange(x.shape[0]):
        sum += i*x[i]
    return sum

def add3(x):
    sum = 0.0
    for i in xrange(x.shape[0]):
        sum += i*x[i]
    return sum

rdd = dpark.makeRDD(range(0, 10)).map(lambda x: numpy.arange(x*1e7, (x+1)*1e7))

print rdd.map(add1).collect()
print rdd.map(add2).collect()
print rdd.map(add3).collect()

########NEW FILE########
__FILENAME__ = kmeans
#!/usr/bin/env python
import sys, os, os.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import random
import dpark
from vector import Vector

def parseVector(line):
    return Vector(map(float, line.strip().split(' ')))

def closestCenter(p, centers):
    bestDist = p.squaredDist(centers[0])
    bestIndex = 0
    for i in range(1, len(centers)):
        d = p.squaredDist(centers[i])
        if d < bestDist:
            bestDist = d
            bestIndex = i
    return bestIndex


if __name__ == '__main__':
    D = 4
    K = 3
    IT = 10
    MIN_DIST = 0.01
    centers = [Vector([random.random() for j in range(D)]) for i in range(K)]
    points = dpark.textFile('kmeans_data.txt').map(parseVector).cache()

    for it in range(IT):
        print 'iteration', it
        mappedPoints = points.map(lambda p:(closestCenter(p, centers), (p, 1)))
        ncenters = mappedPoints.reduceByKey(
                lambda (s1,c1),(s2,c2): (s1+s2,c1+c2)
            ).map(
                lambda (id, (sum, count)): (id, sum/count)
            ).collectAsMap()

        updated = False
        for i in ncenters:
            if centers[i].dist(ncenters[i]) > MIN_DIST:
                centers[i] = ncenters[i]
                updated = True
        if not updated:
            break
        print centers

    print 'final', centers

########NEW FILE########
__FILENAME__ = pagerank
#!/usr/bin/env python
import sys, os.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dpark import DparkContext
from dpark.bagel import Vertex, Edge, Bagel

def parse_vertex(line, numV):
    fields = line.split(' ')
    title, refs = fields[0], fields[1:]
    outEdges = [Edge(ref) for ref in refs]
    return (title, Vertex(title, 1.0/numV, outEdges, True))

def gen_compute(num, epsilon):
    def compute(self, messageSum, agg, superstep):
        if messageSum and messageSum[0]:
            newValue = 0.15 / num + 0.85 * messageSum[0]
        else:
            newValue = self.value
        terminate = (superstep >= 10 and abs(newValue-self.value) < epsilon) or superstep > 30
        outbox = [(edge.target_id, newValue / len(self.outEdges))
                for edge in self.outEdges] if not terminate else []
        return Vertex(self.id, newValue, self.outEdges, not terminate), outbox
    return compute

if __name__ == '__main__':
    inputFile = 'wikipedia.txt'
    threshold = 0.01

    dpark = DparkContext()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), inputFile)
    input = dpark.textFile(path)
    numVertex = input.count()
    vertices = input.map(lambda line: parse_vertex(line, numVertex)).cache()
    epsilon = 0.01 / numVertex
    messages = dpark.parallelize([])
    result = Bagel.run(dpark, vertices, messages,
        gen_compute(numVertex, epsilon))

    for id, v in result.filter(lambda (id, v): v.value>threshold).collect():
        print id, v

########NEW FILE########
__FILENAME__ = shortpath
#!/usr/bin/env python2.6
import sys, os.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dpark import Bagel, DparkContext
from dpark.bagel import Vertex, Edge, BasicCombiner

def to_vertex((id, lines)):
    outEdges = [Edge(tid, int(v))
        for _, tid, v in lines]
    return (id, Vertex(id, sys.maxint, outEdges, True))

def compute(self, vs, agg, superstep):
    newValue = min(self.value, vs[0]) if vs else self.value
    if newValue != self.value:
        outbox = [(edge.target_id, newValue + edge.value)
                for edge in self.outEdges]
    else:
        outbox = []
    return Vertex(self.id, newValue, self.outEdges, False), outbox

if __name__ == '__main__':
    ctx = DparkContext()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graph.txt')
    lines = ctx.textFile(path).map(lambda line:line.split(' '))
    vertices = lines.groupBy(lambda line:line[0]).map(to_vertex)
    startVertex = str(0)
    messages = ctx.makeRDD([(startVertex, 0)])

    print 'read', vertices.count(), 'vertices and ', messages.count(), 'messages.'

    result = Bagel.run(ctx, vertices, messages, compute, BasicCombiner(min), numSplits=2)

    print 'Shortest path from %s to all vertices:' % startVertex
    for id, v in result.collect():
        if v.value == sys.maxint:
            v.value = 'inf'
        print v.id, v.value

########NEW FILE########
__FILENAME__ = vector
import math

class Vector:

    def __init__(self, l):
        self.data = l

    def __add__(self, o):
        return Vector([a+b for a,b in zip(self.data, o.data)])

    def __sub__(self, o):
        return Vector([a-b for a,b in zip(self.data, o.data)])

    def __div__(self, n):
        return Vector([i/n for i in self.data])

    def __repr__(self):
        return '[%s]' % (','.join('%.1f'% i for i in self.data))

    def dot(self, o):
        return sum(a*b for a,b in zip(self.data, o.data))

    def squaredDist(self, o):
        return sum((a-b)*(a-b) for a,b in zip(self.data, o.data))

    def sum(self):
        return sum(self.data)

    def dist(self, o):
        return math.sqrt(self.squaredDist(o))

########NEW FILE########
__FILENAME__ = wc
import sys
sys.path.append('../')
from dpark import DparkContext

dpark = DparkContext()

name = '/mfs/tmp/weblog-pre-20111019.csv'
name = '/mfs/tmp/weblog-20111019.csv'
name = '/tmp/weblog-20111019.csv.small'
#name = '/tmp/weblog-20111019.csv.medium'
pv = dpark.textFile(name)
pv = pv.map(lambda x:x.split(',')).map(lambda l:(l[3],l[7]))
pv = pv.flatMap(lambda (i,u):(u.startswith('/movie') and [(i,2)]
        or u.startswith('/group') and [(i,3)]
        or []))
#print pv.take(50)
pv = pv.reduceByKey(lambda x,y:x*y)
#print pv.take(50)
print pv.filter(lambda (_,y):y%2==0 and y%3==0).count()

#movie = pv.filter(lambda (bid,url): url.startswith('/movie')).reduceByKey(lambda x,y:None)
#group = pv.filter(lambda (bid,url): url.startswith('/group')).reduceByKey(lambda x,y:None)
#print movie.join(group).count()

#print pv.map(lambda x:x.split(',')[2]).uniq().count()
#print pv.map(lambda x:(x.split(',')[2],None)).reduceByKey(lambda x,y:None).count()
#.filter(lambda uid:uid)
#print upv.count()
#print upv.reduceByKey(lambda x,y:x+y).count()

########NEW FILE########
__FILENAME__ = test_bitindex
import os, sys
import unittest
import random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dpark.bitindex import BitIndex, Bloomfilter

class TestBitIndex(unittest.TestCase):
    def test_sets(self):
        a = BitIndex()
        self.assertEqual(a.size, 0)
        self.assertEqual(len(a.array), 0)
        self.assertFalse(bool(a))
        self.assertEqual(str(a), '')

        a.set(100, True)
        self.assertEqual(a.size, 101)
        self.assertEqual(len(a.array), (a.size + 7) >> 3)
        self.assertEqual(a.array, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10')
        self.assertTrue(bool(a))
        self.assertEqual(str(a), ''.join(['0']*100 + ['1']))

        a.sets([1,3,16])
        self.assertEqual(a.size, 101)
        self.assertEqual(len(a.array), (a.size + 7) >> 3)
        self.assertEqual(a.array, b'\x0a\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10')

        a.append()
        self.assertEqual(a.size, 102)
        self.assertEqual(len(a.array), (a.size + 7) >> 3)
        self.assertEqual(a.array, b'\x0a\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x30')

        a.append(0)
        self.assertEqual(a.size, 103)
        self.assertEqual(len(a.array), (a.size + 7) >> 3)
        self.assertEqual(a.array, b'\x0a\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x30')

        a.appends([1,0,1,True,1, None])
        self.assertEqual(a.size, 109)
        self.assertEqual(len(a.array), (a.size + 7) >> 3)
        self.assertEqual(a.array, b'\x0a\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb0\x0e')

    def test_gets(self):
        a = BitIndex()
        pos = [random.randint(0, 1000) for i in xrange(100)]
        a.sets(pos)
        self.assertEqual(a.size, max(pos) + 1)
        self.assertEqual(len(a.array), (a.size + 7) >> 3)

        self.assertTrue(a.get(pos[0]))
        self.assertTrue(all(a.gets(pos)))
        self.assertEqual(list(a.positions()), sorted(set(pos)))

    def test_operations(self):
        a = BitIndex()
        pos_a = set(random.randint(0, 1000) for i in xrange(100))
        a.sets(pos_a)
        b = BitIndex()
        pos_b = set(random.randint(0, 1000) for i in xrange(100))
        b.sets(pos_b)
        c = BitIndex()
        pos_c = set(random.randint(0, 1000) for i in xrange(100))
        c.sets(pos_c)

        self.assertEqual(list(a.intersect(b)), sorted(pos_a & pos_b))
        self.assertEqual(list(a.intersect(b, c)), sorted(pos_a & pos_b & pos_c))

        self.assertEqual(list(a.union(b)), sorted(pos_a | pos_b))
        self.assertEqual(list(a.union(b, c)), sorted(pos_a | pos_b | pos_c))

        self.assertEqual(list(a.excepts(b)), sorted(pos_a ^ (pos_a & pos_b)))
        self.assertEqual(list(a.excepts(b, c)), sorted(pos_a ^ (pos_a & (pos_b | pos_c))))

        self.assertEqual(list(a.xor(b)), sorted(pos_a ^ pos_b))

    def test_bloomfilter(self):
        m, k = Bloomfilter.calculate_parameters(100000, 0.01)
        b = Bloomfilter(m, k)
        keys = [random.randint(0, 80000) for i in xrange(40000)]
        b.add(keys)
        self.assertTrue(keys[0] in b)
        self.assertTrue(all(b.match(keys)))
        self.assertTrue(len(filter(None, b.match(xrange(80000, 100000)))) < 100000 * 0.01)



########NEW FILE########
__FILENAME__ = test_dstream
import os, sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dpark.dstream import *

class TestInputStream(InputDStream):
    def __init__(self, ssc, input, numPart=2):
        InputDStream.__init__(self, ssc)
        self.input = input
        self.numPart = numPart
        self.index = -1

    def compute(self, t):
        self.index += 1
        index = (t - self.zeroTime) / self.slideDuration - 1
        if 0 <= index < len(self.input):
            d = self.input[index]
            return self.ssc.sc.makeRDD(d, self.numPart)

class TestOutputStream(ForEachDStream):
    def __init__(self, parent, output):
        def collect(rdd, t):
            r = rdd.collect()
            #print 'collect', t, r
            return self.output.append(r)
        ForEachDStream.__init__(self, parent, collect)
        self.output = output


class TestDStream(unittest.TestCase):
    def _setupStreams(self, intput1, input2, operation):
        ssc = StreamingContext(2, "local")
        is1 = TestInputStream(ssc, intput1)
        ssc.registerInputStream(is1)
        if input2:
            is2 = TestInputStream(ssc, input2)
            ssc.registerInputStream(is2)
            os = operation(is1, is2)
        else:
            os = operation(is1)
        output = TestOutputStream(os, [])
        ssc.registerOutputStream(output)
        return ssc

    def _runStreams(self, ssc, numBatches, numExpectedOuput):
        output = ssc.graph.outputStreams[0].output
        try:
            #print 'expected', numExpectedOuput
            first = int(time.time()) - numBatches * ssc.batchDuration
            #print 'start', first, numBatches
            ssc.start(first)
            while len(output) < numExpectedOuput:
                time.sleep(.01)
        finally:
            ssc.stop()
        return output

    def _verifyOutput(self, output, expected, useSet):
        #self.assertEqual(len(output), len(expected))
        assert len(output) >= len(expected)
        #print output
        for i in range(len(expected)):
            #print i
            if useSet:
                self.assertEqual(set(output[i]), set(expected[i]))
            elif isinstance(output[i], list) and isinstance(expected[i], list):
                self.assertEqual(sorted(output[i]), sorted(expected[i]))
            else:
                self.assertEqual(output[i], expected[i])

    def _testOperation(self, input1, input2, operation, expectedOutput, numBatches=0, useSet=False):
        if numBatches <= 0:
            numBatches = len(expectedOutput)
        ssc = self._setupStreams(input1, input2, operation)
        output = self._runStreams(ssc, numBatches, len(expectedOutput))
        self._verifyOutput(output, expectedOutput, useSet)

class TestBasic(TestDStream):
    def test_map(self):
        d = [range(i*4, i*4+4) for i in range(4)]
        r = [[str(i) for i in row] for row in d]
        self._testOperation(d, None, lambda x: x.map(str), r, 4, False)
        r = [sum([range(x,x*2) for x in row], []) for row in d]
        self._testOperation(d, None, lambda x: x.flatMap(lambda x:range(x, x*2)), r)

    def test_filter(self):
        d = [range(i*4, i*4+4) for i in range(4)]
        self._testOperation(d, None, lambda x: x.filter(lambda y: y%2==0),
            [[i for i in row if i%2 ==0] for row in d])

    def test_glom(self):
        d = [range(i*4, i*4+4) for i in range(4)]
        r = [[row[:2], row[2:]] for row in d]
        self._testOperation(d, None, lambda s: s.glom().map(lambda x:list(x)), r)

    def test_mapPartitions(self):
        d = [range(i*4, i*4+4) for i in range(4)]
        r = [[sum(row[:2]), sum(row[2:])] for row in d]
        self._testOperation(d, None, lambda s: s.mapPartitions(lambda l: [reduce(lambda x,y:x+y, l)]), r)

    def test_groupByKey(self):
        d = [["a", "a", "b"], ["", ""], []]
        r = [[("a", [1, 1]), ("b", [1])], [("", [1,1])], []]
        self._testOperation(d, None, lambda s: s.map(lambda x:(x,1)).groupByKey(), r, useSet=False)

    def test_reduceByKey(self):
        d = [["a", "a", "b"], ["", ""], []]
        r = [[("a", 2), ("b", 1)], [("", 2)], []]
        self._testOperation(d, None, lambda s: s.map(lambda x:(x,1)).reduceByKey(lambda x,y:x+y), r, useSet=True)

    def test_reduce(self):
        d = [range(i*4, i*4+4) for i in range(4)]
        r = [[sum(row)] for row in d]
        self._testOperation(d, None, lambda s: s.reduce(lambda x,y:x+y), r)

    def test_cogroup(self):
        d1 = [["a", "a", "b"], ["a", ""], [""]]
        d2 = [["a", "a", "b"], ["b", ""], []]
        r = [[("a", ([1,1], ["x", "x"])), ("b", ([1,], ["x"]))],
             [("a", ([1], [])), ("b", ([], ["x"])), ("", ([1],["x"]))],
             [("", ([1],[]))],
        ]
        def op(s1, s2):
            return s1.map(lambda x:(x,1)).cogroup(s2.map(lambda x:(x,"x")))
        self._testOperation(d1, d2, op, r)

    def test_updateStateByKey(self):
        d = [["a"], ["a", "b",], ['a', 'b','c'], ['a','b'], ['a'], []]
        r = [[("a", 1)],
             [("a", 2), ("b", 1)],
             [("a", 3), ("b", 2), ("c", 1)],
             [("a", 4), ("b", 3), ("c", 1)],
             [("a", 5), ("b", 3), ("c", 1)],
             [("a", 5), ("b", 3), ("c", 1)],
        ]

        def op(s):
            def updatef(vs, state):
                return sum(vs) + (state or 0)
            return s.map(lambda x: (x,1)).updateStateByKey(updatef)
        self._testOperation(d, None, op, r, useSet=True)

    #def test_window(self):
    #    d = [range(i, i+1) for i in range(10)]
    #    def op(s):
    #        return s.map(lambda x:(x % 10, 1)).window(2, 1).window(4, 2)
    #    ssc = self._setupStreams(d, None, op)
    #    ssc.remember(3)
    #    self._runStreams(ssc, 10, 10/2)


class TestWindow(TestDStream):
    largerSlideInput = [
        [("a", 1)],
        [("a", 2)],
        [("a", 3)],
        [("a", 4)],
        [("a", 5)],
        [("a", 6)],
        [],
        [],
    ]
    largerSlideReduceOutput = [
        [("a", 3)],
        [("a", 10)],
        [("a", 18)],
        [("a", 11)],
    ]
    bigInput = [
        [("a", 1)],
        [("a", 1), ("b", 1)],
        [("a", 1), ("b", 1), ("c", 1)],
        [("a", 1), ("b", 1)],
        [("a", 1)],
        [],
        [("a", 1)],
        [("a", 1), ("b", 1)],
        [("a", 1), ("b", 1), ("c", 1)],
        [("a", 1), ("b", 1)],
        [("a", 1)],
        [],
    ]
    bigGroupByOutput = [
        [("a", [1])],
        [("a", [1, 1]), ("b", [1])],
        [("a", [1, 1]), ("b", [1, 1]), ("c", [1])],
        [("a", [1, 1]), ("b", [1, 1]), ("c", [1])],
        [("a", [1, 1]), ("b", [1])],
        [("a", [1])],
        [("a", [1])],
        [("a", [1, 1]), ("b", [1])],
        [("a", [1, 1]), ("b", [1, 1]), ("c", [1])],
        [("a", [1, 1]), ("b", [1, 1]), ("c", [1])],
        [("a", [1, 1]), ("b", [1])],
        [("a", [1])],
    ]
    bigReduceOutput = [
        [("a", 1)],
        [("a", 2), ("b", 1)],
        [("a", 2), ("b", 2), ("c", 1)],
        [("a", 2), ("b", 2), ("c", 1)],
        [("a", 2), ("b", 1)],
        [("a", 1)],
        [("a", 1)],
        [("a", 2), ("b", 1)],
        [("a", 2), ("b", 2), ("c", 1)],
        [("a", 2), ("b", 2), ("c", 1)],
        [("a", 2), ("b", 1)],
        [("a", 1)],
    ]
    bigReduceInvOutput = [
        [("a", 1)],
        [("a", 2), ("b", 1)],
        [("a", 2), ("b", 2), ("c", 1)],
        [("a", 2), ("b", 2), ("c", 1)],
        [("a", 2), ("b", 1), ("c", 0)],
        [("a", 1), ("b", 0), ("c", 0)],
        [("a", 1), ("b", 0), ("c", 0)],
        [("a", 2), ("b", 1), ("c", 0)],
        [("a", 2), ("b", 2), ("c", 1)],
        [("a", 2), ("b", 2), ("c", 1)],
        [("a", 2), ("b", 1), ("c", 0)],
        [("a", 1), ("b", 0), ("c", 0)],
    ]
    def _testWindow(self, input, expectedOutput, window=4, slide=2):
        self._testOperation(input, None, lambda s: s.window(window, slide), expectedOutput,
            len(expectedOutput) * slide / 2, useSet=True)

    def _testReduceByKeyAndWindow(self, input, expectedOutput, window=4, slide=2):
        self._testOperation(input, None, lambda s: s.reduceByKeyAndWindow(lambda x,y:x+y, None, window, slide),
            expectedOutput, len(expectedOutput) * slide / 2, useSet=True)

    def _testReduceByKeyAndWindowInv(self, input, expectedOutput, window=4, slide=2):
        self._testOperation(input, None,
            lambda s: s.reduceByKeyAndWindow(lambda x,y: x+y, lambda x,y: x-y, window, slide),
            expectedOutput, len(expectedOutput) * slide / 2, useSet=True)

    def test_window(self):
        # basic window
        self._testWindow([[i] for i in range(6)],
            [range(max(i-1, 0), i+1) for i in range(6)])
        # tumbling window
        self._testWindow([[i] for i in range(6)],
            [range(i*2, i*2+2) for i in range(3)], 4, 4)
        # large window
        self._testWindow([[i] for i in range(6)],
            [[0, 1], range(4), range(2, 6), range(4, 6)], 8, 4)
        # non-overlapping window
        self._testWindow([[i] for i in range(6)],
            [range(1, 3), range(4, 6)], 4, 6)

    def test_reduceByKeyAndWindow(self):
        # basic reduction
        self._testReduceByKeyAndWindow(
            [[("a", 1), ("a", 3)]],
            [[("a", 4)]]
        )
        # key already in window and new value added into window
        self._testReduceByKeyAndWindow(
            [[("a", 1)], [("a", 1)]],
            [[("a", 1)], [("a", 2)]],
        )
        # new key added to window
        self._testReduceByKeyAndWindow(
            [[("a", 1)], [("a", 1), ("b", 1)]],
            [[("a", 1)], [("a", 2), ("b", 1)]],
        )
        # new removed from window
        self._testReduceByKeyAndWindow(
            [[("a", 1)], [("a", 1)], [], []],
            [[("a", 1)], [("a", 2)], [("a", 1)], []],
        )
        # larger slide time
        self._testReduceByKeyAndWindow(
            self.largerSlideInput, self.largerSlideReduceOutput, 8, 4)
        # big test
        self._testReduceByKeyAndWindow(self.bigInput, self.bigReduceOutput)

    def test_reduce_and_window_inv(self):
        # basic reduction
        self._testReduceByKeyAndWindowInv(
            [[("a", 1), ("a", 3)]],
            [[("a", 4)]]
        )
        # key already in window and new value added into window
        self._testReduceByKeyAndWindowInv(
            [[("a", 1)], [("a", 1)]],
            [[("a", 1)], [("a", 2)]],
        )
        # new key added to window
        self._testReduceByKeyAndWindowInv(
            [[("a", 1)], [("a", 1), ("b", 1)]],
            [[("a", 1)], [("a", 2), ("b", 1)]],
        )
        # new removed from window
        self._testReduceByKeyAndWindowInv(
            [[], []],
            [[], []],
        )
        self._testReduceByKeyAndWindowInv(
            [[("a", 1)], [("a", 1)], [], []],
            [[("a", 1)], [("a", 2)], [("a", 1)], [("a", 0)]],
        )
        # large slide time
        self._testReduceByKeyAndWindowInv(self.largerSlideInput,
            self.largerSlideReduceOutput, 8, 4)
        # big test
        self._testReduceByKeyAndWindowInv(self.bigInput, self.bigReduceInvOutput)

    def test_group_by_window(self):
        r = [[(k,set(v))  for k,v in row] for row in self.bigGroupByOutput]
        def op(s):
            return s.groupByKeyAndWindow(4, 2).mapValues(lambda x:set(x))
        self._testOperation(self.bigInput, None, op, r)

    def test_count_by_window(self):
        d = [[1], [1], [1,2], [0], [], []]
        r =  [[1], [2], [3], [3], [1], [0]]
        self._testOperation(d, None, lambda s: s.countByWindow(4, 2), r)

    def test_count_by_key_and_window(self):
        d = [[("a", 1)], [("b", 1), ("b", 2)], [("a", 10), ("b", 20)]]
        r = [[("a", 1)], [("a", 1), ("b", 2)], [("a", 1), ("b", 3)]]
        self._testOperation(d, None, lambda s: s.countByKeyAndWindow(4, 2), r)


class TestInputDStream(TestDStream):
    def test_input_stream(self):
        pass

    def test_failure(self):
        pass

    def test_checkpoint(self):
        pass


if __name__ == '__main__':
    import logging
    unittest.main()

########NEW FILE########
__FILENAME__ = test_job
import sys
import unittest
import socket

from dpark.job import *
from dpark import pymesos as mesos
from dpark.pymesos import mesos_pb2 as mesos_pb2

class MockSchduler:
    def taskEnded(self, task, reason, result, update):
        pass
    def requestMoreResources(self):
        pass
    def jobFinished(self, job):
        pass
    def killTask(self, job_id, task_id, tried):
        pass

class MockTask:
    def __init__(self, id):
        self.id = id
    def preferredLocations(self):
        return []

class TestJob(unittest.TestCase):
    def test_job(self):
        sched = MockSchduler()
        tasks = [MockTask(i) for i in range(10)]
        job = SimpleJob(sched, tasks, 1, 10)
        ts = [job.slaveOffer('localhost') for i in range(10)]
        assert len(ts) == 10
        assert job.tasksLaunched == 10
        assert job.slaveOffer('localhost') is None
        [job.statusUpdate(t.id, 0, mesos_pb2.TASK_FINISHED) for t in ts]
        assert job.tasksFinished == 10

    def test_retry(self):
        sched = MockSchduler()
        tasks = [MockTask(i) for i in range(10)]
        job = SimpleJob(sched, tasks)
        ts = [job.slaveOffer('localhost') for i in range(10)]
        [job.statusUpdate(t.id, 0, mesos_pb2.TASK_FINISHED) for t in ts[1:]]
        assert job.tasksFinished == 9
        job.statusUpdate(ts[0].id, 0, mesos_pb2.TASK_FAILED)
        t = job.slaveOffer('localhost1')
        assert t.id == 0
        assert job.slaveOffer('localhost') is None
        assert job.tasksLaunched == 10
        job.statusUpdate(t.id, 1, mesos_pb2.TASK_FINISHED)
        assert job.tasksFinished == 10

if __name__ == '__main__':
    sys.path.append('../')
    logging.basicConfig(level=logging.INFO)
    unittest.main()

########NEW FILE########
__FILENAME__ = test_rdd
import sys, os.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cPickle
import unittest
import pprint
import random
import operator
import shutil
from dpark.context import *
from dpark.rdd import *
from dpark.accumulator import *

class TestRDD(unittest.TestCase):
    def setUp(self):
        self.sc = DparkContext("local")

    def tearDown(self):
        self.sc.stop()

    def test_parallel_collection(self):
        slices = ParallelCollection.slice(xrange(5), 3)
        self.assertEqual(len(slices), 3)
        self.assertEqual(list(slices[0]), range(2))
        self.assertEqual(list(slices[1]), range(2, 4))
        self.assertEqual(list(slices[2]), range(4, 5))

    def test_basic_operation(self):
        d = range(4)
        nums = self.sc.makeRDD(d, 2)
        self.assertEqual(len(nums.splits), 2)
        self.assertEqual(nums.collect(), d)
        self.assertEqual(nums.reduce(lambda x,y:x+y), sum(d))
        self.assertEqual(nums.map(lambda x:str(x)).collect(), ["0", "1", "2", "3"])
        self.assertEqual(nums.filter(lambda x:x>1).collect(), [2, 3])
        self.assertEqual(nums.flatMap(lambda x:range(x)).collect(), [0, 0,1, 0,1,2])
        self.assertEqual(nums.union(nums).collect(), d + d)
        self.assertEqual(nums.cartesian(nums).map(lambda (x,y):x*y).reduce(lambda x,y:x+y), 36)
        self.assertEqual(nums.glom().map(lambda x:list(x)).collect(),[[0,1],[2,3]])
        self.assertEqual(nums.mapPartitions(lambda x:[sum(x)]).collect(),[1, 5])
        self.assertEqual(nums.map(lambda x:str(x)+"/").reduce(lambda x,y:x+y),
            "0/1/2/3/")
        self.assertEqual(nums.pipe('grep 3').collect(), ['3'])
        self.assertEqual(nums.sample(0.5, True).count(), 2)

        self.assertEqual(len(nums[:1]), 1)
        self.assertEqual(nums[:1].collect(), range(2))
        self.assertEqual(len(nums.mergeSplit(2)), 1)
        self.assertEqual(nums.mergeSplit(2).collect(), range(4))
        self.assertEqual(nums.zipWith(nums).collectAsMap(), dict(zip(d,d)))

    def test_ignore_bad_record(self):
        d = range(100)
        self.sc.options.err = 0.02
        nums = self.sc.makeRDD(d, 2)
        self.assertEqual(nums.filter(lambda x:1.0/x).count(), 99)
        self.assertEqual(nums.map(lambda x:1/x).count(), 99)
        self.assertEqual(nums.flatMap(lambda x:[1/x]).count(), 99)
        self.assertEqual(nums.reduce(lambda x,y:x+100/y), 431)

    def test_pair_operation(self):
        d = zip([1,2,3,3], range(4,8))
        nums = self.sc.makeRDD(d, 2)
        self.assertEqual(nums.reduceByKey(lambda x,y:x+y).collectAsMap(), {1:4, 2:5, 3:13})
        self.assertEqual(nums.reduceByKeyToDriver(lambda x,y:x+y), {1:4, 2:5, 3:13})
        self.assertEqual(nums.groupByKey().collectAsMap(), {1:[4], 2:[5], 3:[6,7]})

        # join
        nums2 = self.sc.makeRDD(zip([2,3,4], [1,2,3]), 2)
        self.assertEqual(nums.join(nums2).collect(),
                [(2, (5, 1)), (3, (6, 2)), (3, (7, 2))])
        self.assertEqual(sorted(nums.leftOuterJoin(nums2).collect()),
                [(1, (4,None)), (2, (5, 1)), (3, (6, 2)), (3, (7, 2))])
        self.assertEqual(sorted(nums.rightOuterJoin(nums2).collect()),
                [(2, (5,1)), (3, (6,2)), (3, (7,2)), (4,(None,3))])
        self.assertEqual(nums.innerJoin(nums2).collect(),
                [(2, (5, 1)), (3, (6, 2)), (3, (7, 2))])

        self.assertEqual(nums.mapValue(lambda x:x+1).collect(),
                [(1, 5), (2, 6), (3, 7), (3, 8)])
        self.assertEqual(nums.flatMapValue(lambda x:range(x)).count(), 22)
        self.assertEqual(nums.groupByKey().lookup(3), [6,7])

        # group with
        self.assertEqual(sorted(nums.groupWith(nums2).collect()),
                [(1, ([4],[])), (2, ([5],[1])), (3,([6,7],[2])), (4,([],[3]))])
        nums3 = self.sc.makeRDD(zip([4,5,1], [1,2,3]), 1).groupByKey(2).flatMapValue(lambda x:x)
        self.assertEqual(sorted(nums.groupWith([nums2, nums3]).collect()),
                [(1, ([4],[],[3])), (2, ([5],[1],[])), (3,([6,7],[2],[])),
                (4,([],[3],[1])), (5,([],[],[2]))])

        # update
        rdd4 = self.sc.makeRDD([('foo', 1), ('wtf', 233)])
        rdd5 = self.sc.makeRDD([('foo', 2), ('bar', 3), ('wtf', None)])
        rdd6 = self.sc.makeRDD([('dup', 1), ('dup', 2), ('duq', 3), ('duq', 4),
                                ('foo', 5)])
        rdd7 = self.sc.makeRDD([('duq', 6), ('duq', 7), ('duq', 8), ('dup', 9),
                                ('bar', 10)])
        dct = rdd6.update(rdd7).collectAsMap()
        dct2 = rdd7.update(rdd6).collectAsMap()

        self.assertEqual(
            rdd4.update(rdd5, replace_only=True).collectAsMap(),
            dict([('foo', 2), ('wtf', None)])
        )
        self.assertEqual(
            rdd5.update(rdd4, replace_only=True).collectAsMap(),
            dict([('foo', 1), ('bar', 3), ('wtf', 233)])
        )
        self.assertEqual(
            rdd4.update(rdd5).collectAsMap(),
            dict([('foo', 2), ('bar', 3), ('wtf', None)])
        )
        self.assertEqual(
            rdd5.update(rdd4).collectAsMap(),
            dict([('foo', 1), ('bar', 3), ('wtf', 233)])
        )
        self.assertEqual(dct.get('dup'), 9)
        self.assertEqual(dct.get('foo'), 5)
        self.assertTrue(dct.get('duq') in {6, 7, 8})
        self.assertEqual(dct.get('bar'), 10)
        self.assertTrue(dct2.get('dup') in {1, 2})
        self.assertEqual(dct2.get('foo'), 5)
        self.assertTrue(dct2.get('duq') in {3, 4})
        self.assertEqual(dct2.get('bar'), 10)

    def test_accumulater(self):
        d = range(4)
        nums = self.sc.makeRDD(d, 2)

        acc = self.sc.accumulator()
        nums.map(lambda x: acc.add(x)).count()
        self.assertEqual(acc.value, 6)

        acc = self.sc.accumulator([], listAcc)
        nums.map(lambda x: acc.add([x])).count()
        self.assertEqual(list(sorted(acc.value)), range(4))

    def test_sort(self):
        d = range(100)
        self.assertEqual(self.sc.makeRDD(d, 10).collect(), range(100))
        random.shuffle(d)
        rdd = self.sc.makeRDD(d, 10)
        self.assertEqual(rdd.sort(numSplits=10).collect(), range(100))
        self.assertEqual(rdd.sort(reverse=True, numSplits=5).collect(), list(reversed(range(100))))
        self.assertEqual(rdd.sort(key=lambda x:-x, reverse=True, numSplits=4).collect(), range(100))

        self.assertEqual(rdd.top(), range(90, 100)[::-1])
        self.assertEqual(rdd.top(15, lambda x:-x), range(0, 15))

        for i in range(10):
            for j in range(i+1):
                d.append(i)
        rdd = self.sc.makeRDD(d, 10)
        self.assertEqual(rdd.hot(), zip(range(9, -1, -1), range(11, 1, -1)))

    def test_empty_rdd(self):
        rdd = self.sc.union([])
        self.assertEqual(rdd.count(), 0)
        self.assertEqual(rdd.sort().collect(), [])

    def test_text_file(self):
        path = 'tests/test_rdd.py'
        f = self.sc.textFile(path, splitSize=1000).mergeSplit(numSplits=1)
        n = len(open(path).read().split())
        fs = f.flatMap(lambda x:x.split()).cache()
        self.assertEqual(fs.count(), n)
        self.assertEqual(fs.map(lambda x:(x,1)).reduceByKey(lambda x,y: x+y).collectAsMap()['class'], 1)
        prefix = 'prefix:'
        self.assertEqual(f.map(lambda x:prefix+x).saveAsTextFile('/tmp/tout'),
            ['/tmp/tout/0000'])
        self.assertEqual(f.map(lambda x:('test', prefix+x)).saveAsTextFileByKey('/tmp/tout'),
            ['/tmp/tout/test/0000'])
        d = self.sc.textFile('/tmp/tout')
        n = len(open(path).readlines())
        self.assertEqual(d.count(), n)
        self.assertEqual(fs.map(lambda x:(x,1)).reduceByKey(operator.add
            ).saveAsCSVFile('/tmp/tout'),
            ['/tmp/tout/0000.csv'])
        shutil.rmtree('/tmp/tout')

    def test_compressed_file(self):
        # compress
        d = self.sc.makeRDD(range(100000), 1)
        self.assertEqual(d.map(str).saveAsTextFile('/tmp/tout', compress=True),
            ['/tmp/tout/0000.gz'])
        rd = self.sc.textFile('/tmp/tout', splitSize=10<<10)
        self.assertEqual(rd.count(), 100000)

        self.assertEqual(d.map(lambda i:('x', str(i))).saveAsTextFileByKey('/tmp/tout', compress=True),
            ['/tmp/tout/x/0000.gz'])
        rd = self.sc.textFile('/tmp/tout', splitSize=10<<10)
        self.assertEqual(rd.count(), 100000)
        shutil.rmtree('/tmp/tout')

    def test_binary_file(self):
        d = self.sc.makeRDD(range(100000), 1)
        self.assertEqual(d.saveAsBinaryFile('/tmp/tout', fmt="I"),
            ['/tmp/tout/0000.bin'])
        rd = self.sc.binaryFile('/tmp/tout', fmt="I", splitSize=10<<10)
        self.assertEqual(rd.count(), 100000)
        shutil.rmtree('/tmp/tout')

    def test_table_file(self):
        N = 100000
        d = self.sc.makeRDD(zip(range(N), range(N)), 1)
        self.assertEqual(d.saveAsTableFile('/tmp/tout'), ['/tmp/tout/0000.tab',])
        rd = self.sc.tableFile('/tmp/tout', splitSize=64<<10)
        self.assertEqual(rd.count(), N)
        self.assertEqual(rd.map(lambda x:x[0]).reduce(lambda x,y:x+y), sum(xrange(N)))

        d.asTable(['f1', 'f2']).save('/tmp/tout')
        rd = self.sc.table('/tmp/tout')
        self.assertEqual(rd.map(lambda x:x.f1+x.f2).reduce(lambda x,y:x+y), 2*sum(xrange(N)))
        shutil.rmtree('/tmp/tout')

    def test_batch(self):
        from math import ceil
        d = range(1234)
        rdd = self.sc.makeRDD(d, 10).batch(100)
        self.assertEqual(rdd.flatMap(lambda x:x).collect(), d)
        self.assertEqual(rdd.filter(lambda x: len(x)<=2 or len(x) >100).collect(), [])

    def test_partial_file(self):
        p = 'tests/test_rdd.py'
        l = 300
        d = open(p).read(l+50)
        start = 100
        while d[start-1] != '\n':
            start += 1
        while d[l-1] != '\n':
            l += 1
        d = d[start:l-1]
        rdd = self.sc.partialTextFile(p, start, l, l)
        self.assertEqual('\n'.join(rdd.collect()), d)
        rdd = self.sc.partialTextFile(p, start, l, (l-start)/5)
        self.assertEqual('\n'.join(rdd.collect()), d)

    def test_beansdb(self):
        N = 100
        l = range(N)
        d = zip(map(str, l), l)
        rdd = self.sc.makeRDD(d, 10)
        self.assertEqual(rdd.saveAsBeansdb('/tmp/beansdb'),
                       ['/tmp/beansdb/%03d.data' % i for i in range(10)])
        rdd = self.sc.beansdb('/tmp/beansdb', depth=0)
        self.assertEqual(len(rdd), 10)
        self.assertEqual(rdd.count(), N)
        self.assertEqual(sorted(rdd.map(lambda (k,v):(k,v[0])).collect()), sorted(d))
        s = rdd.map(lambda x:x[1][0]).reduce(lambda x,y:x+y)
        self.assertEqual(s, sum(l))

        rdd = self.sc.beansdb('/tmp/beansdb', depth=0, fullscan=True)
        self.assertEqual(len(rdd), 10)
        self.assertEqual(rdd.count(), N)
        self.assertEqual(sorted(rdd.map(lambda (k,v):(k,v[0])).collect()), sorted(d))
        s = rdd.map(lambda x:x[1][0]).reduce(lambda x,y:x+y)
        self.assertEqual(s, sum(l))
        shutil.rmtree('/tmp/beansdb')

    def test_enumerations(self):
        N = 100
        p = 10
        l = range(N)
        d1 = sorted(map(lambda x: (x/p, x), l))
        d2 = sorted(map(lambda x: ((x/p, x%p), x), l))
        rdd = self.sc.makeRDD(l, p)
        self.assertEqual(sorted(rdd.enumeratePartition().collect()), d1)
        self.assertEqual(sorted(rdd.enumerate().collect()), d2)

    def test_tabular(self):
        d = range(10000)
        d = zip(d, map(str, d), map(float, d))
        path = '/tmp/tabular-%s' % os.getpid()
        try:
            self.sc.makeRDD(d).saveAsTabular(path, 'f_int, f_str, f_float', indices=['f_str', 'f_float'])
            r = self.sc.tabular(path, fields=['f_float', 'f_str']).collect()
            for f, s in r:
                self.assertEqual(type(f), float)
                self.assertEqual(type(s), str)
                self.assertEqual(str(int(f)), s)
            self.assertEqual(sorted(x.f_float for x in r), sorted(x[2] for x in d))

            r = self.sc.tabular(path, fields='f_int f_float').filterByIndex(f_float=lambda x:hash(x) % 2).collect()
            for i, f in r:
                self.assertEqual(type(i), int)
                self.assertEqual(type(f), float)
                self.assertEqual(i, int(f))
                self.assertTrue(hash(f) % 2)

            self.assertEqual(sorted(x.f_int for x in r), sorted(x[0] for x in d if hash(x[2]) %2))
        finally:
            try:
                shutil.rmtree(path)
            except OSError:
                pass



#class TestRDDInProcess(TestRDD):
#    def setUp(self):
#        self.sc = DparkContext("process")


if __name__ == "__main__":
    import logging
    unittest.main()

########NEW FILE########
__FILENAME__ = test_schedule
import sys
import pickle
import unittest

from dpark.task import *
from dpark.schedule import *
from dpark.env import env
from dpark.context import parse_options

class MockDriver:
    def __init__(self):
        self.tasks = []
    def reviveOffers(self):
        pass
    def launchTasks(self, oid, tasks):
        self.tasks.extend(tasks)


class TestScheduler(unittest.TestCase):
    def setUp(self):
        return
        env.start(True)
        self.sched = MesosScheduler('mesos://localhost:5050', parse_options())
        self.driver = MockDriver()
        self.sched.driver = self.driver
        self.sched.start()

    def test_sched(self):
        return
        sched = self.sched
        driver = self.driver

        self.sched.registered(driver, "test")
        assert self.sched.isRegistered is True

        info = self.sched.getExecutorInfo()
        assert isinstance(info, mesos_pb2.ExecutorInfo)

        tasks = [Task() for i in range(10)]
        sched.submitTasks(tasks)
        assert len(sched.activeJobs) == 1
        assert len(sched.activeJobQueue) == 1
        assert len(sched.jobTasks) == 1

        offer = mesos_pb2.SlaveOffer()
        offer.hostname = 'localhost'
        offer.slave_id.value = '1'
        cpus = offer.resources.add()
        cpus.name = 'cpus'
        cpus.type = mesos_pb2.Resource.SCALAR
        cpus.scalar.value = 15
        mem = offer.resources.add()
        mem.name = 'mem'
        mem.type = mesos_pb2.Resource.SCALAR
        mem.scalar.value = 2000
        sched.resourceOffer(driver, "1", [offer])
        assert len(driver.tasks)  == 10
        assert len(sched.jobTasks[1]) == 10
        assert len(sched.taskIdToSlaveId) == 10

        status = mesos_pb2.TaskStatus()
        status.state = 3
        status.task_id.value = ":1:"
        status.data = pickle.dumps((1, OtherFailure("failed"), [], {}))
        sched.statusUpdate(driver, status)
        assert len(self.taskIdToSlaveId) == 9

        sched.resourceOffer(driver, "2", [offer])
        assert len(self.driver.tasks)  == 11

        status.state = 2 # finished
        for i in range(10):
            status.task_id.value = ":%s:" % str(tasks[i].id)
            sched.statusUpdate(driver, status)
        assert len(sched.jobTasks) == 0
        assert len(sched.taskIdToSlaveId) == 0
        assert len(sched.activeJobs) == 0
        assert len(sched.activeJobQueue) == 0

        sched.error(driver, 1, 'error')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = executor
#!/usr/bin/env python

# hook for virtualenv
# switch to the virtualenv where the executor belongs,
# replace all the path for modules
import sys, os.path
P = 'site-packages'
apath = os.path.abspath(__file__)
if P in apath:
    virltualenv = apath[:apath.index(P)]
    sysp = [p[:-len(P)] for p in sys.path if p.endswith(P)][0]
    if sysp != virltualenv:
        sys.path = [p.replace(sysp, virltualenv) for p in sys.path]

import os
import pickle
import subprocess
import threading
from threading import Thread
import socket
import psutil
import time

import zmq

import dpark.pymesos as mesos
from dpark.pymesos import mesos_pb2

ctx = zmq.Context()

def forword(fd, addr, prefix=''):
    f = os.fdopen(fd, 'r', 4096)
    out = ctx.socket(zmq.PUSH)
    out.connect(addr)
    while True:
        try:
            line = f.readline()
            if not line: break
            out.send(prefix+line)
        except IOError:
            break
    f.close()
    out.close()

def reply_status(driver, task_id, status):
    update = mesos_pb2.TaskStatus()
    update.task_id.MergeFrom(task_id)
    update.state = status
    update.timestamp = time.time()
    driver.sendStatusUpdate(update)

def launch_task(self, driver, task):
    reply_status(driver, task.task_id, mesos_pb2.TASK_RUNNING)

    host = socket.gethostname()
    cwd, command, _env, shell, addr1, addr2, addr3 = pickle.loads(task.data)

    prefix = "[%s@%s] " % (str(task.task_id.value), host)
    outr, outw = os.pipe()
    errr, errw = os.pipe()
    t1 = Thread(target=forword, args=[outr, addr1, prefix])
    t1.daemon = True
    t1.start()
    t2 = Thread(target=forword, args=[errr, addr2, prefix])
    t2.daemon = True
    t2.start()
    wout = os.fdopen(outw,'w',0)
    werr = os.fdopen(errw,'w',0)


    if addr3:
        subscriber = ctx.socket(zmq.SUB)
        subscriber.connect(addr3)
        subscriber.setsockopt(zmq.SUBSCRIBE, '')
        poller = zmq.Poller()
        poller.register(subscriber, zmq.POLLIN)
        socks = dict(poller.poll(60 * 1000))
        if socks and socks.get(subscriber) == zmq.POLLIN:
            hosts = pickle.loads(subscriber.recv(zmq.NOBLOCK))
            line = hosts.get(host)
            if line:
                command = line.split(' ')
            else:
                return reply_status(driver, task.task_id, mesos_pb2.TASK_FAILED)
        else:
            return reply_status(driver, task.task_id, mesos_pb2.TASK_FAILED)

    mem = 100
    for r in task.resources:
        if r.name == 'mem':
            mem = r.scalar.value
            break

    try:
        env = dict(os.environ)
        env.update(_env)
        if not os.path.exists(cwd):
            print >>werr, 'CWD %s is not exists, use /tmp instead' % cwd
            cwd = '/tmp'
        p = subprocess.Popen(command,
                stdout=wout, stderr=werr,
                cwd=cwd, env=env, shell=shell)
        tid = task.task_id.value
        self.ps[tid] = p
        code = None
        last_time = 0
        while True:
            time.sleep(0.1)
            code = p.poll()
            if code is not None:
                break

            now = time.time()
            if now < last_time + 2:
                continue

            last_time = now
            try:
                process = psutil.Process(p.pid)

                rss = sum((proc.get_memory_info().rss
                          for proc in process.get_children(recursive=True)),
                          process.get_memory_info().rss)
                rss = (rss >> 20)
            except Exception, e:
                continue

            if rss > mem * 1.5:
                print >>werr, "task %s used too much memory: %dMB > %dMB * 1.5, kill it. " \
                "use -m argument to request more memory." % (
                    tid, rss, mem)
                p.kill()
            elif rss > mem:
                print >>werr, "task %s used too much memory: %dMB > %dMB, " \
                "use -m to request for more memory" % (
                    tid, rss, mem)

        if code == 0:
            status = mesos_pb2.TASK_FINISHED
        else:
            print >>werr, ' '.join(command) + ' exit with %s' % code
            status = mesos_pb2.TASK_FAILED
    except Exception, e:
        status = mesos_pb2.TASK_FAILED
        import traceback
        print >>werr, 'exception while open ' + ' '.join(command)
        for line in traceback.format_exc():
            werr.write(line)

    reply_status(driver, task.task_id, status)

    wout.close()
    werr.close()
    t1.join()
    t2.join()

    self.ps.pop(tid, None)
    self.ts.pop(tid, None)

class MyExecutor(mesos.Executor):
    def __init__(self):
        self.ps = {}
        self.ts = {}

    def launchTask(self, driver, task):
        t = Thread(target=launch_task, args=(self, driver, task))
        t.daemon = True
        t.start()
        self.ts[task.task_id.value] = t

    def killTask(self, driver, task_id):
        try:
            if task_id.value in self.ps:
                self.ps[task_id.value].kill()
                reply_status(driver, task_id, mesos_pb2.TASK_KILLED)
        except: pass

    def shutdown(self, driver):
        for p in self.ps.values():
            try: p.kill()
            except: pass
        for t in self.ts.values():
            t.join()

if __name__ == "__main__":
    executor = MyExecutor()
    mesos.MesosExecutorDriver(executor).run()

########NEW FILE########
__FILENAME__ = scheduler
#!/usr/bin/env python
import os
import pickle
import sys
import time
import socket
import random
from optparse import OptionParser
import threading
import subprocess
from operator import itemgetter
import logging
import signal

import zmq
ctx = zmq.Context()

import dpark.pymesos as mesos
import dpark.pymesos.mesos_pb2 as mesos_pb2
import dpark.conf as conf
from dpark.util import getuser
from dpark import moosefs

class Task:
    def __init__(self, id):
        self.id = id
        self.tried = 0
        self.state = -1
        self.state_time = 0

REFUSE_FILTER = mesos_pb2.Filters()
REFUSE_FILTER.refuse_seconds = 10*60 # 10 mins

def parse_mem(m):
    try:
        return float(m)
    except ValueError:
        number, unit = float(m[:-1]), m[-1].lower()
        if unit == 'g':
            number *= 1024
        elif unit == 'k':
            number /= 1024
        return number

def safe(f):
    def _(self, *a, **kw):
        with self.lock:
            r = f(self, *a, **kw)
        return r
    return _


class SubmitScheduler(object):
    def __init__(self, options, command):
        self.framework_id = None
        self.executor = None
        self.framework = mesos_pb2.FrameworkInfo()
        self.framework.user = getuser()
        if self.framework.user == 'root':
            raise Exception("drun is not allowed to run as 'root'")
        name = '[drun] ' + ' '.join(sys.argv[1:])
        if len(name) > 256:
            name = name[:256] + '...'
        self.framework.name = name
        self.framework.hostname = socket.gethostname()
        self.cpus = options.cpus
        self.mem = parse_mem(options.mem)
        self.options = options
        self.command = command
        self.total_tasks = list(reversed([Task(i)
            for i in range(options.start, options.tasks)]))
        self.task_launched = {}
        self.slaveTasks = {}
        self.started = False
        self.stopped = False
        self.status = 0
        self.next_try = 0
        self.lock = threading.RLock()
        self.last_offer_time = time.time()

    def getExecutorInfo(self):
        frameworkDir = os.path.abspath(os.path.dirname(sys.argv[0]))
        executorPath = os.path.join(frameworkDir, "executor.py")
        execInfo = mesos_pb2.ExecutorInfo()
        execInfo.executor_id.value = "default"
        execInfo.command.value = executorPath
        if hasattr(execInfo, 'framework_id'):
            execInfo.framework_id.value = str(self.framework_id)
        return execInfo

    def create_port(self, output):
        sock = ctx.socket(zmq.PULL)
        host = socket.gethostname()
        port = sock.bind_to_random_port("tcp://0.0.0.0")

        def redirect():
            poller = zmq.Poller()
            poller.register(sock, zmq.POLLIN)
            while True:
                socks = poller.poll(100)
                if not socks:
                    if self.stopped:
                        break
                    continue
                line = sock.recv()
                output.write(line)

        t = threading.Thread(target=redirect)
        t.daemon = True
        t.start()
        return t, "tcp://%s:%d" % (host, port)

    @safe
    def registered(self, driver, fid, masterInfo):
        logging.debug("Registered with Mesos, FID = %s" % fid.value)
        self.framework_id = fid.value
        self.executor = self.getExecutorInfo()
        self.std_t, self.std_port = self.create_port(sys.stdout)
        self.err_t, self.err_port = self.create_port(sys.stderr)

    def getResource(self, offer):
        cpus, mem = 0, 0
        for r in offer.resources:
            if r.name == 'cpus':
                cpus = float(r.scalar.value)
            elif r.name == 'mem':
                mem = float(r.scalar.value)
        return cpus, mem

    def getAttributes(self, offer):
        attrs = {}
        for a in offer.attributes:
            attrs[a.name] = a.text.value
        return attrs

    @safe
    def resourceOffers(self, driver, offers):
        tpn = self.options.task_per_node
        random.shuffle(offers)
        self.last_offer_time = time.time()
        for offer in offers:
            attrs = self.getAttributes(offer)
            if self.options.group and attrs.get('group', 'None') not in self.options.group:
                driver.launchTasks(offer.id, [], REFUSE_FILTER)
                continue

            cpus, mem = self.getResource(offer)
            logging.debug("got resource offer %s: cpus:%s, mem:%s at %s",
                offer.id.value, cpus, mem, offer.hostname)
            sid = offer.slave_id.value
            tasks = []
            while (self.total_tasks and cpus+1e-4 >= self.cpus and mem >= self.mem
                    and (tpn ==0 or tpn > 0 and len(self.slaveTasks.get(sid,set())) < tpn)):
                logging.debug("Accepting slot on slave %s (%s)",
                    offer.slave_id.value, offer.hostname)
                t = self.total_tasks.pop()
                task = self.create_task(offer, t, cpus)
                tasks.append(task)
                t.state = mesos_pb2.TASK_STARTING
                t.state_time = time.time()
                self.task_launched[t.id] = t
                self.slaveTasks.setdefault(sid, set()).add(t.id)
                cpus -= self.cpus
                mem -= self.mem
                if not self.total_tasks:
                    break

            logging.debug("dispatch %d tasks to slave %s", len(tasks), offer.hostname)
            driver.launchTasks(offer.id, tasks, REFUSE_FILTER)

    def create_task(self, offer, t, cpus):
        task = mesos_pb2.TaskInfo()
        task.task_id.value = "%d-%d" % (t.id, t.tried)
        task.slave_id.value = offer.slave_id.value
        task.name = "task %s/%d" % (t.id, self.options.tasks)
        task.executor.MergeFrom(self.executor)
        env = dict(os.environ)
        env['DRUN_RANK'] = str(t.id)
        env['DRUN_SIZE'] = str(self.options.tasks)
        command = self.command[:]
        if self.options.expand:
            for i, x in enumerate(command):
                command[i] = x % {'RANK': t.id, 'SIZE': self.options.tasks}
        task.data = pickle.dumps([os.getcwd(), command, env, self.options.shell,
            self.std_port, self.err_port, None])

        cpu = task.resources.add()
        cpu.name = "cpus"
        cpu.type = 0 # mesos_pb2.Value.SCALAR
        cpu.scalar.value = min(self.cpus, cpus)

        mem = task.resources.add()
        mem.name = "mem"
        mem.type = 0 # mesos_pb2.Value.SCALAR
        mem.scalar.value = self.mem
        return task

    @safe
    def statusUpdate(self, driver, update):
        logging.debug("Task %s in state %d" % (update.task_id.value, update.state))
        tid = int(update.task_id.value.split('-')[0])
        if tid not in self.task_launched:
            # check failed after launched
            for t in self.total_tasks:
                if t.id == tid:
                    self.task_launched[tid] = t
                    self.total_tasks.remove(t)
                    break
            else:
                logging.debug("Task %d is finished, ignore it", tid)
                return

        t = self.task_launched[tid]
        t.state = update.state
        t.state_time = time.time()

        if update.state == mesos_pb2.TASK_RUNNING:
            self.started = True

        elif update.state == mesos_pb2.TASK_LOST:
            logging.warning("Task %s was lost, try again", tid)
            if not self.total_tasks:
                driver.reviveOffers() # request more offers again
            t.tried += 1
            t.state = -1
            self.task_launched.pop(tid)
            self.total_tasks.append(t)

        elif update.state in (mesos_pb2.TASK_FINISHED, mesos_pb2.TASK_FAILED):
            t = self.task_launched.pop(tid)
            slave = None
            for s in self.slaveTasks:
                if tid in self.slaveTasks[s]:
                    slave = s
                    self.slaveTasks[s].remove(tid)
                    break

            if update.state >= mesos_pb2.TASK_FAILED:
                if t.tried < self.options.retry:
                    t.tried += 1
                    logging.warning("task %d failed with %d, retry %d", t.id, update.state, t.tried)
                    if not self.total_tasks:
                        driver.reviveOffers() # request more offers again
                    self.total_tasks.append(t) # try again
                else:
                    logging.error("task %d failed with %d on %s", t.id, update.state, slave)
                    self.stop(1)

            if not self.task_launched and not self.total_tasks:
                self.stop(0)

    @safe
    def check(self, driver):
        now = time.time()
        for tid, t in self.task_launched.items():
            if t.state == mesos_pb2.TASK_STARTING and t.state_time + 30 < now:
                logging.warning("task %d lauched failed, assign again", tid)
                if not self.total_tasks:
                    driver.reviveOffers() # request more offers again
                t.tried += 1
                t.state = -1
                self.task_launched.pop(tid)
                self.total_tasks.append(t)
            # TODO: check run time

    @safe
    def offerRescinded(self, driver, offer):
        logging.debug("resource rescinded: %s", offer)
        # task will retry by checking

    @safe
    def slaveLost(self, driver, slave):
        logging.warning("slave %s lost", slave.value)

    @safe
    def error(self, driver, code, message):
        logging.error("Error from Mesos: %s (error code: %d)" % (message, code))

    @safe
    def stop(self, status):
        if self.stopped:
            return
        self.stopped = True
        self.status = status
        self.std_t.join()
        self.err_t.join()
        logging.debug("scheduler stopped")


class MPIScheduler(SubmitScheduler):
    def __init__(self, options, command):
        SubmitScheduler.__init__(self, options, command)
        self.used_hosts = {}
        self.used_tasks = {}
        self.id = 0
        self.p = None
        self.publisher = ctx.socket(zmq.PUB)
        port = self.publisher.bind_to_random_port('tcp://0.0.0.0')
        host = socket.gethostname()
        self.publisher_port = 'tcp://%s:%d' % (host, port)

    def start_task(self, driver, offer, k):
        t = Task(self.id)
        self.id += 1
        self.task_launched[t.id] = t
        self.used_tasks[t.id] = (offer.hostname, k)
        task = self.create_task(offer, t, k)
        logging.debug("lauching %s task with offer %s on %s, slots %d", t.id,
                     offer.id.value, offer.hostname, k)
        driver.launchTasks(offer.id, [task], REFUSE_FILTER)

    @safe
    def resourceOffers(self, driver, offers):
        random.shuffle(offers)
        launched = sum(self.used_hosts.values())
        self.last_offer_time = time.time()

        for offer in offers:
            cpus, mem = self.getResource(offer)
            logging.debug("got resource offer %s: cpus:%s, mem:%s at %s",
                offer.id.value, cpus, mem, offer.hostname)
            if launched >= self.options.tasks or offer.hostname in self.used_hosts:
                driver.launchTasks(offer.id, [], REFUSE_FILTER)
                continue

            attrs = self.getAttributes(offer)
            if self.options.group and attrs.get('group', 'None') not in self.options.group:
                driver.launchTasks(offer.id, [], REFUSE_FILTER)
                continue

            slots = int(min(cpus/self.cpus, mem/self.mem) + 1e-5)
            if self.options.task_per_node:
                slots = min(slots, self.options.task_per_node)
            slots = min(slots, self.options.tasks - launched)
            if slots >= 1:
                self.used_hosts[offer.hostname] = slots
                launched += slots
                self.start_task(driver, offer, slots)
            else:
                driver.launchTasks(offer.id, [], REFUSE_FILTER)

        if launched < self.options.tasks:
            logging.warning('not enough offers: need %d offer %d, waiting more resources',
                            self.options.tasks, launched)

    @safe
    def statusUpdate(self, driver, update):
        logging.debug("Task %s in state %d" % (update.task_id.value, update.state))
        tid = int(update.task_id.value.split('-')[0])
        if tid not in self.task_launched:
            logging.error("Task %d not in task_launched", tid)
            return

        t = self.task_launched[tid]
        t.state = update.state
        t.state_time = time.time()
        hostname, slots = self.used_tasks[tid]

        if update.state == mesos_pb2.TASK_RUNNING:
            launched = sum(self.used_hosts.values())
            ready = all(t.state == mesos_pb2.TASK_RUNNING for t in self.task_launched.values())
            if launched == self.options.tasks and ready:
                logging.debug("all tasks are ready, start to run")
                self.start_mpi()

        elif update.state in (mesos_pb2.TASK_LOST, mesos_pb2.TASK_FAILED):
            if not self.started:
                logging.warning("Task %s was lost, try again", tid)
                driver.reviveOffers() # request more offers again
                t.tried += 1
                t.state = -1
                self.used_hosts.pop(hostname)
                self.used_tasks.pop(tid)
                self.task_launched.pop(tid)
            else:
                logging.error("Task %s failed, cancel all tasks", tid)
                self.stop(1)

        elif update.state == mesos_pb2.TASK_FINISHED:
            if not self.started:
                logging.warning("Task %s has not started, ignore it %s", tid, update.state)
                return

            t = self.task_launched.pop(tid)
            if not self.task_launched:
                self.stop(0)

    @safe
    def check(self, driver):
        now = time.time()
        for tid, t in self.task_launched.items():
            if t.state == mesos_pb2.TASK_STARTING and t.state_time + 30 < now:
                logging.warning("task %d lauched failed, assign again", tid)
                driver.reviveOffers() # request more offers again
                t.tried += 1
                t.state = -1
                hostname, slots = self.used_tasks[tid]
                self.used_hosts.pop(hostname)
                self.used_tasks.pop(tid)
                self.task_launched.pop(tid)

    def create_task(self, offer, t, k):
        task = mesos_pb2.TaskInfo()
        task.task_id.value = "%s-%s" % (t.id, t.tried)
        task.slave_id.value = offer.slave_id.value
        task.name = "task %s" % t.id
        task.executor.MergeFrom(self.executor)
        env = dict(os.environ)
        task.data = pickle.dumps([os.getcwd(), None, env, self.options.shell, self.std_port, self.err_port, self.publisher_port])

        cpus, mem = self.getResource(offer)
        cpu = task.resources.add()
        cpu.name = "cpus"
        cpu.type = 0 #mesos_pb2.Value.SCALAR
        cpu.scalar.value = min(self.cpus * k, cpus)

        mem = task.resources.add()
        mem.name = "mem"
        mem.type = 0 #mesos_pb2.Value.SCALAR
        mem.scalar.value = min(self.mem * k, mem)

        return task

    def start_mpi(self):
        try:
            slaves = self.try_to_start_mpi(self.command, self.options.tasks, self.used_hosts.items())
        except Exception:
            self.broadcast_command({})
            self.next_try = time.time() + random.randint(5,10)
            return

        commands = dict(zip(self.used_hosts.keys(), slaves))
        self.broadcast_command(commands)
        self.started = True

    def broadcast_command(self, command):
        def repeat_pub():
            for i in xrange(10):
                self.publisher.send(pickle.dumps(command))
                time.sleep(1)
                if self.stopped: break

        t = threading.Thread(target=repeat_pub)
        t.deamon = True
        t.start()
        return t

    def try_to_start_mpi(self, command, tasks, items):
        if self.p:
            try: self.p.kill()
            except: pass
        hosts = ','.join("%s:%d" % (hostname, slots) for hostname, slots in items)
        logging.debug("choosed hosts: %s", hosts)
        cmd = ['mpirun', '-prepend-rank', '-launcher', 'none', '-hosts', hosts, '-np', str(tasks)] + command
        self.p = p = subprocess.Popen(cmd, bufsize=0, stdout=subprocess.PIPE)
        slaves = []
        prefix = 'HYDRA_LAUNCH: '
        while True:
            line = p.stdout.readline()
            if not line: break
            if line.startswith(prefix):
                slaves.append(line[len(prefix):-1].strip())
            if line == 'HYDRA_LAUNCH_END\n':
                break
        if len(slaves) != len(items):
            logging.error("hosts: %s, slaves: %s", items, slaves)
            raise Exception("slaves not match with hosts")
        def output(f):
            while True:
                line = f.readline()
                if not line: break
                sys.stdout.write(line)
        self.tout = t = threading.Thread(target=output, args=[p.stdout])
        t.deamon = True
        t.start()
        return slaves

    @safe
    def stop(self, status):
        if self.started:
            try:
                self.p.kill()
                self.p.wait()
            except: pass
            self.tout.join()
        self.publisher.close()
        super(MPIScheduler, self).stop(status)


if __name__ == "__main__":
    parser = OptionParser(usage="Usage: drun [options] <command>")
    parser.allow_interspersed_args=False
    parser.add_option("-s", "--master", type="string",
                default="mesos",
                        help="url of master (default: mesos)")
    parser.add_option("-i", "--mpi", action="store_true",
                        help="run MPI tasks")

    parser.add_option("-n", "--tasks", type="int", default=1,
                        help="number task to launch (default: 1)")
    parser.add_option("-b", "--start", type="int", default=0,
                        help="which task to start (default: 0)")
    parser.add_option("-p", "--task_per_node", type="int", default=0,
                        help="max number of tasks on one node (default: 0)")
    parser.add_option("-r","--retry", type="int", default=0,
                        help="retry times when failed (default: 0)")
    parser.add_option("-t", "--timeout", type="int", default=3600*24,
                        help="timeout of job in seconds (default: 86400)")

    parser.add_option("-c","--cpus", type="float", default=1.0,
            help="number of CPUs per task (default: 1)")
    parser.add_option("-m","--mem", type="string", default='100m',
            help="MB of memory per task (default: 100m)")
    parser.add_option("-g","--group", type="string", default='',
            help="which group to run (default: ''")


    parser.add_option("--expand", action="store_true",
                        help="expand expression in command line")
    parser.add_option("--shell", action="store_true",
                      help="using shell re-intepret the cmd args")
#    parser.add_option("--kill", type="string", default="",
#                        help="kill a job with frameword id")

    parser.add_option("-q", "--quiet", action="store_true",
                        help="be quiet", )
    parser.add_option("-v", "--verbose", action="store_true",
                        help="show more useful log", )

    (options, command) = parser.parse_args()

    if 'DPARK_CONF' in os.environ:
        conf.load_conf(os.environ['DPARK_CONF'])
    elif os.path.exists('/etc/dpark.conf'):
        conf.load_conf('/etc/dpark.conf')

    conf.__dict__.update(os.environ)
    moosefs.MFS_PREFIX = conf.MOOSEFS_MOUNT_POINTS
    moosefs.master.ENABLE_DCACHE = conf.MOOSEFS_DIR_CACHE

    if options.master == 'mesos':
        options.master = conf.MESOS_MASTER
    elif options.master.startswith('mesos://'):
        if '@' in options.master:
            options.master = options.master[options.master.rfind('@')+1:]
        else:
            options.master = options.master[options.master.rfind('//')+2:]
    elif options.master.startswith('zoo://'):
        options.master = 'zk' + options.master[3:]

    if ':' not in options.master:
        options.master += ':5050'

#    if options.kill:
#        sched = MPIScheduler(options, command)
#        fid = mesos_pb2.FrameworkID()
#        fid.value =  options.kill
#        driver = mesos.MesosSchedulerDriver(sched, sched.framework,
#            options.master, fid)
#        driver.start()
#        driver.stop(False)
#        sys.exit(0)

    if not command:
        parser.print_help()
        sys.exit(2)

    logging.basicConfig(format='[drun] %(threadName)s %(asctime)-15s %(message)s',
                    level=options.quiet and logging.ERROR
                        or options.verbose and logging.DEBUG
                        or logging.WARNING)

    if options.mpi:
        if options.retry > 0:
            logging.error("MPI application can not retry")
            options.retry = 0
        sched = MPIScheduler(options, command)
    else:
        sched = SubmitScheduler(options, command)

    logging.debug("Connecting to mesos master %s", options.master)
    driver = mesos.MesosSchedulerDriver(sched, sched.framework,
        options.master)

    driver.start()
    def handler(signm, frame):
        logging.warning("got signal %d, exit now", signm)
        sched.stop(3)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGHUP, handler)
    signal.signal(signal.SIGABRT, handler)
    signal.signal(signal.SIGQUIT, handler)

    try:
        from rfoo.utils import rconsole
        rconsole.spawn_server(locals(), 0)
    except ImportError:
        pass

    start = time.time()
    try:
        while not sched.stopped:
            time.sleep(0.1)

            now = time.time()
            sched.check(driver)
            if not sched.started and sched.next_try > 0 and now > sched.next_try:
                sched.next_try = 0
                driver.reviveOffers()

            if not sched.started and now > sched.last_offer_time + 60 + random.randint(0,5):
                logging.warning("too long to get offer, reviving...")
                sched.last_offer_time = now
                driver.reviveOffers()

            if now - start > options.timeout:
                logging.warning("job timeout in %d seconds", options.timeout)
                sched.stop(2)
                break

    except KeyboardInterrupt:
        logging.warning('stopped by KeyboardInterrupt')
        sched.stop(4)

    driver.stop(False)
    ctx.term()
    sys.exit(sched.status)

########NEW FILE########
