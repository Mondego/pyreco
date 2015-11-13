__FILENAME__ = example
import time
import numpy
import mmap
from itertools import count

from kaylee import Server

# Note, we never load the whole file into memory.
f = open('mobydick.txt')
mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

# This just enumerates all lines in the file, but is able to
# get data from disk into ZeroMQ much faster than read/writes.

def datafn():
    i = count(0)
    total = mm.size()
    while mm.tell() < total:
        yield next(i), mm.readline()
    mm.close()

# map :: (k1,v1) -> [ (k2, v2) ]
def mapfn(k1, v):
    for w in v.bytes.split():
        yield w, 1

# reduce :: (k2, [v2]) -> [ (k3, v3) ]
def reducefn(k2, v):
    return sum(v)

# Server
s = Server()
s.connect()

s.mapfn    = mapfn
s.reducefn = reducefn
s.datafn   = datafn

start = time.time()
s.start()
stop = time.time()

print stop-start
#print s.results()
print sorted(s.results().iteritems(), key=lambda x: x[1], reverse=True)[1:25]

########NEW FILE########
__FILENAME__ = client
import sys
import uuid
import numpy
import types
import signal
import logging
from itertools import imap
from collections import deque
from utils import zmq_addr

import zmq.green as zmq

try:
    import msgpack as srl
except ImportError:
    import cPickle as srl

try:
    import marshal as marshal
    #import dill as marshal
except ImportError:
    import marshal

# Server instructions
# -------------------
MAP       = 'map'
REDUCE    = 'reduce'
DONE      = 'done'
BYTECODE  = 'bytecode'
HEARTBEAT = 'heartbeat'

# Client instructions
# -------------------
CONNECT     = 'connect'
MAPATOM     = 'mapdone'
MAPCHUNK    = 'mapkeydone'
REDUCEATOM  = 'reducedone'

# Heartbeat
# ----------

PING = 'ping'
PONG = 'pong'

class Client(object):
    """
    The MapReduce worker is a stateless worker, it receives a
    value over ZMQ, calls the map/reduce function.
    """

    def __init__(self):
        self.worker_id = str(uuid.uuid4())

        self.push_socket = None
        self.pull_socket = None
        self.ctrl_socket = None

        self.have_bytecode = False

        self.mapfn = None
        self.reducefn = None
        self.datasource = None

        logging.basicConfig(logging=logging.DEBUG)
        logging.getLogger("").setLevel(logging.INFO)
        self.logging = logging

    def connect(self, push_addr = None,
                      pull_addr = None,
                      ctrl_addr = None):

        c = zmq.Context()

        if not pull_addr:
            addr = zmq_addr(5555, transport='tcp')

        self.pull_socket = c.socket(zmq.PULL)
        self.pull_socket.connect(addr)

        if not push_addr:
            addr = zmq_addr(6666, transport='tcp')

        self.push_socket = c.socket(zmq.PUSH)
        self.push_socket.connect(addr)

        if not ctrl_addr:
            addr = zmq_addr(7777, transport='tcp')

        self.ctrl_socket = c.socket(zmq.ROUTER)
        self.ctrl_socket.setsockopt(zmq.IDENTITY, self.worker_id)
        self.ctrl_socket.connect(addr)

    def start(self):
        self.logging.info('Started Worker %s' % self.worker_id)
        self.collect()

    def kill(self):
        self.ctrl_socket.close()
        self.pull_socket.close()
        self.push_socket.close()
        self.logging.info('Stopped Worker')

    def collect(self):
        poller = zmq.Poller()
        poller.register(self.pull_socket, zmq.POLLIN)
        poller.register(self.ctrl_socket, zmq.POLLIN)

        pull_socket = self.pull_socket
        ctrl_socket = self.ctrl_socket

        while True:

            if self.have_bytecode:

                try:
                    events = dict(poller.poll())
                except zmq.ZMQError:
                    self._kill()
                    break

                if events.get(pull_socket) == zmq.POLLIN:

                    command = self.pull_socket.recv(flags=zmq.SNDMORE)
                    key = self.pull_socket.recv(flags=zmq.SNDMORE)
                    data = self.pull_socket.recv(copy=False)

                    if command == MAP:
                        self.call_mapfn(key, data)
                    elif command == REDUCE:
                        self.call_reducefn(key, data)

                if events.get(ctrl_socket) == zmq.POLLIN:
                    worker_id, command = self.ctrl_socket.recv_multipart()
                    if command == HEARTBEAT:
                        self.ctrl_socket.send(PONG)
                        print 'pong'
                    if command == DONE:
                        self.kill()
                        break

            else:
                self.logging.info('Waiting for server')

                # Associate with the server
                self.push_socket.send_multipart([CONNECT, self.worker_id])

                # Wait for the server to route us the bytecode,
                # then start the work cycle
                worker_id, payload = self.ctrl_socket.recv_multipart()
                command, (mapbc, reducebc) = srl.loads(payload)

                assert command == BYTECODE
                self.set_bytecode(mapbc, reducebc)
                self.logging.info('Received Bytecode')

    def set_bytecode(self, mapbc, reducebc):
        '''
        Load the bytecode sent by the server and flag that we are
        ready for work.
        '''

        self.mapfn = types.FunctionType(
            marshal.loads(mapbc),
            globals(),
            'mapfn'
        )
        self.reducefn = types.FunctionType(
            marshal.loads(reducebc),
            globals(),
            'reducefn'
        )

        self.have_bytecode = True

    def set_llvm(self, bitcode, mapsig=None, reducesig=None):
        import llvm.ee as le
        import llvm.core as lc

        lmodule = lc.Module.from_bitcode(bitcode)
        eb = le.EngineBuilder.new(lmodule)
        tc = le.TargetMachine.new(features='', cm=le.CM_JITDEFAULT)

        engine = eb.create(tc)

        self.mapfn = engine.get_pointer_to_function('mapfn')
        self.reducefn = engine.get_pointer_to_function('reducefn')

        self.have_bytecode = True

    def call_mapfn(self, key, value):
        # TODO: specify the granulariy of chunks to flush to the
        # server.

        for k1, v1 in self.mapfn(key, value):
            print 'mapping', k1, v1
            self.push_socket.send_multipart([MAPATOM, key, k1], flags=zmq.SNDMORE)
            self.push_socket.send(srl.dumps(v1))

        # Signal that k1 has been completed. The system sees this
        # as an atomic unit of work.
        self.push_socket.send(MAPCHUNK, flags=zmq.SNDMORE)
        self.push_socket.send(key)

    def call_reducefn(self, key, value):
        # Lazily deserialize since not all the output may be
        # needed by the reducer so don't waste cycles.
        it = imap(srl.loads, srl.loads(value))
        results = self.reducefn(key, it)

        print 'reducing', key, results
        self.push_socket.send(REDUCEATOM, flags=zmq.SNDMORE)
        self.push_socket.send(key, flags=zmq.SNDMORE)

        if isinstance(results, numpy.ndarray):
            self.push_socket.send(results, copy=False)
        else:
            self.push_socket.send(srl.dumps(results))

if __name__ == "__main__":
    c = Client()
    c.connect()
    c.start()

########NEW FILE########
__FILENAME__ = server
import signal
import gevent
import random
import marshal
import logging
from StringIO import StringIO

import zmq.green as zmq
from collections import defaultdict
from utils import zmq_addr

try:
    import msgpack as srl
except ImportError:
    import cPickle as srl

try:
    import marshal as marshal
    #import dill as marshal
except ImportError:
    import marshal

# States
# ------
START     = 0
MAP       = 1
SHUFFLE   = 2
PARTITION = 3
REDUCE    = 4
COLLECT   = 5

# Shufle Backends
# ---------------
MEMORY = 0

# Server instructions
# -------------------
#MAP      = 'map'
#REDUCE   = 'reduce'
#DONE     = 'done'
#BYTECODE = 'bytecode'

# Client instructions
# -------------------
CONNECT     = 'connect'
MAPATOM     = 'mapdone'
MAPCHUNK    = 'mapkeydone'
REDUCEATOM  = 'reducedone'

# Heartbeat
# ---------

PING = 'ping'
PONG = 'pong'

class Server(object):

    def __init__(self, backend=MEMORY):
        self.workers = set()
        self.state = START

        self.backend = backend

        self.mapfn = None
        self.reducefn = None
        self.datafn = None

        self.bytecode = None

        self.started = False
        self.completed = False

        self.working_maps = {}

        logging.basicConfig(logging=logging.DEBUG)
        logging.getLogger("").setLevel(logging.INFO)
        self.logging = logging

    def heartbeat_loop(self):
        while True:
            for worker in self.workers:
                print 'ping'
                self.ctrl_socket.send_multipart([worker, 'heartbeat'])
            gevent.sleep(1)

    def main_loop(self):
        self.started = True

        poller = zmq.Poller()

        poller.register(self.pull_socket, zmq.POLLIN  | zmq.POLLERR)
        poller.register(self.push_socket, zmq.POLLOUT | zmq.POLLERR)
        poller.register(self.ctrl_socket, zmq.POLLOUT | zmq.POLLERR)

        while self.started and not self.completed:
            try:
                events = dict(poller.poll())
            except zmq.ZMQError:
                self._kill()
                break

            if any(ev & zmq.POLLERR for ev in events.itervalues()):
                self.logging.error('Socket error')
                self._kill()
                break

            # TODO: Specify number of nodes
            if len(self.workers) > 0:
                if events.get(self.push_socket) == zmq.POLLOUT:
                    self.start_new_task()
                if events.get(self.ctrl_socket) == zmq.POLLIN:
                    self.manage()
                if events.get(self.pull_socket) == zmq.POLLIN:
                    self.collect_task()
            else:
                if events.get(self.pull_socket) == zmq.POLLIN:
                    self.collect_task()
                if events.get(self.ctrl_socket) == zmq.POLLIN:
                    self.manage()

            gevent.sleep(1)

    def connect(self, push_addr=None, pull_addr=None, control_addr=None):
        c = zmq.Context()

        # Pull tasks across manager
        pull_addr = zmq_addr(6666, transport='tcp')

        self.pull_socket = c.socket(zmq.PULL)
        self.pull_socket.bind(pull_addr)

        push_addr = zmq_addr(5555, transport='tcp')

        self.push_socket = c.socket(zmq.PUSH)
        self.push_socket.bind(push_addr)

        ctrl_addr = zmq_addr(7777, transport='tcp')

        self.ctrl_socket = c.socket(zmq.ROUTER)
        self.ctrl_socket.bind(ctrl_addr)

    def start(self, timeout=None):
        gevent.signal(signal.SIGQUIT, gevent.shutdown)

        self.gen_bytecode()
        self.logging.info('Started Server')

        main      = gevent.spawn(self.main_loop)
        heartbeat = gevent.spawn(self.heartbeat_loop)

        gevent.joinall([
            main,
            heartbeat,
        ])

        # Clean exit
        self.done()

    def done(self):
        for worker in self.workers:
            self.ctrl_socket.send_multipart([worker, 'done'])

    def manage(self):
        """
        Manage hearbeats on workers. Keep track of clients that
        are alive.
        """
        msg = self.ctrl_socket.recv_multipart()

    def _kill(self):
        gr = gevent.getcurrent()
        gr.kill()

    def results(self):
        if self.completed:
            return self.reduce_results
        else:
            return None

    def send_datum(self, command, key, data):
        self.push_socket.send(command, flags=zmq.SNDMORE)
        self.push_socket.send(str(key), flags=zmq.SNDMORE)

        if self.state == MAP:
            self.push_socket.send(data, copy=False)
        else:
            self.push_socket.send(srl.dumps(data))

    def send_command(self, command, payload=None):

        if payload:
            self.send_datum(command, *payload)
        else:
            self.push_socket.send(command)

    def start_new_task(self):
        action = self.next_task()
        if action:
            command, payload = action
            self.send_command(command, payload)

    def next_task(self):
        """
        The main work cycle, does all the distribution.
        """

        # -------------------------------------------
        if self.state == START:
            self.map_iter = self.datafn()

            if self.backend is MEMORY:
                self.map_results = defaultdict(list)
            else:
                raise NotImplementedError()

            self.state = MAP
            self.logging.info('Mapping')

        # -------------------------------------------
        if self.state == MAP:
            try:
                map_key, map_item = next(self.map_iter)
                self.working_maps[str(map_key)] = map_item
                return 'map', (map_key, map_item)
            except StopIteration:
                self.logging.info('Shuffling')
                self.state = SHUFFLE

        # -------------------------------------------
        if self.state == SHUFFLE:
            self.reduce_iter = self.map_results.iteritems()
            self.working_reduces = set()
            self.reduce_results = {}

            if len(self.working_maps) == 0:
                self.logging.info('Reducing')
                self.state = PARTITION
            else:
                self.logging.debug('Remaining %s ' % len(self.working_maps))
                #self.logging.debug('Pending chunks %r' % self.working_maps.keys())

        # -------------------------------------------
        if self.state == PARTITION:
            # Normally we would define some sort way to balance the work
            # across workers ( key modulo n ) but ZMQ PUSH/PULL load
            # balances for us.
            self.state = REDUCE

        # -------------------------------------------
        if self.state == REDUCE:
            try:
                reduce_key, reduce_value = next(self.reduce_iter)
                self.working_reduces.add(reduce_key)
                return 'reduce', (reduce_key, reduce_value)
            except StopIteration:
                self.logging.info('Collecting')
                self.state = COLLECT
        # -------------------------------------------

        if self.state == COLLECT:
            if len(self.working_reduces) == 0:
                self.completed = True
                self.logging.info('Finished')
            else:
                self.logging.debug('Still collecting %s' % len(self.working_reduces))

    def collect_task(self):
        # Don't use the results if they've already been counted
        command = self.pull_socket.recv(flags=zmq.SNDMORE)

        if command == CONNECT:
            worker_id = self.pull_socket.recv()
            self.send_code(worker_id)

        # Maps Units
        # ==========

        elif command == MAPCHUNK:
            key = self.pull_socket.recv()
            del self.working_maps[key]

        elif command == MAPATOM:
            key = self.pull_socket.recv(flags=zmq.SNDMORE)
            tkey = self.pull_socket.recv(flags=zmq.SNDMORE)
            value = self.pull_socket.recv()

            self.map_results[tkey].extend(value)

        # Reduce Units
        # ============

        elif command == REDUCEATOM:
            key = self.pull_socket.recv(flags=zmq.SNDMORE)
            value = srl.loads(self.pull_socket.recv())

            # Don't use the results if they've already been counted
            if key not in self.working_reduces:
                return

            self.reduce_results[key] = value
            self.working_reduces.remove(key)

        else:
            raise RuntimeError("Unknown wire chatter")

    def gen_bytecode(self):
        self.bytecode = (
            marshal.dumps(self.mapfn.func_code),
            marshal.dumps(self.reducefn.func_code),
        )

    def gen_llvm(self, mapfn, reducefn):
        mapbc = StringIO()
        reducebc = StringIO()

        mapfn.mod.to_bitcode(mapbc)
        mapfn.mod.to_bitcode(reducebc)

        return (mapbc, reducebc)

    def send_code(self, worker_id):
        # A new worker
        if worker_id not in self.workers:
            self.logging.info('Worker Registered: %s' % worker_id)
            self.workers.add(worker_id)

            payload = ('bytecode', self.bytecode)
            # The worker_id uniquely identifies the worker in
            # the ZMQ topology.
            self.ctrl_socket.send_multipart([worker_id, srl.dumps(payload)])
            self.logging.info('Sending Bytecode to %s' % worker_id)
        else:
            self.logging.debug('Worker asking for code again?')

if __name__ == '__main__':
    import sys
    import imp
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('path', help='Verbose logging')
    parser.add_argument('--verbose', help='Verbose logging')
    parser.add_argument('--config',  help='Configuration')
    parser.add_argument('--backend', help='Storage backend')

    args = parser.parse_args()

    #fp, pathname, description = imp.find_module(args.path)
    #mod = imp.load_module(args.path, fp, pathname, description)

    srv = Server(backend=args.backend)
    srv.connect()

########NEW FILE########
__FILENAME__ = utils
import time
import msgpack

transports = frozenset(['udp', 'tcp', 'ipc', 'inproc'])

def print_timing(func):
  def wrapper(*arg):
    t1 = time.time()
    res = func(*arg)
    t2 = time.time()
    print '%s took %0.3f ms' % (func.func_name, (t2-t1)*1000.0)
    return res
  return wrapper

def sub_subscription_prefix(worker_id, n=3):
    """
    Listen for n-tuples with the worker id prefix without
    deserialization. Very fast for PUB/SUB.
    """
    return msgpack.dumps(tuple([worker_id] + [None]*(n-1)))[0:2]

def zmq_addr(port, transport=None, host=None):
    if host is None:
        host = '127.0.0.1'

    if transport is None:
        transport = 'tcp'

    assert transport in transports
    assert 1000 < port < 10000

    return '{transport}://{host}:{port}'.format(
        transport = transport,
        host      = host,
        port      = port,
    )

########NEW FILE########
