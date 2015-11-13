__FILENAME__ = agenda
import time

class AgendaStoreError(Exception): pass

class Agenda(object):
    """ An agenda is like an append-only list structure that's partitioned by
        "time buckets" (think unrolled linked list). The time-based indexes
        make it easy to query timespans, namely items since and items until,
        which lets it be used for scheduling items in the future. """
    
    retries = 3
    
    def __init__(self, client, prefix, resolution=10, ttl=0):
        self.client = client
        self.prefix = prefix
        self.resolution = resolution
        self.ttl = ttl
    
    def add(self, item, at=None):
        bucket = self._bucket(at or time.time())
        for retry in range(self.retries):
            if self.client.append(bucket, ',%s' % str(item), self.ttl) or \
                self.client.add(bucket, str(item), self.ttl):
                return True
        raise AgendaStoreError()      
    
    def get(self, since=None, until=None):
        since = self._time(since or time.time())
        until = self._time(until or time.time())
        num_buckets = (until - since) / self.resolution
        keys = [self._bucket(since + (i * self.resolution)) for i in range(num_buckets)]
        buckets = self.client.get_multi(keys)
        if buckets:
            return ','.join(buckets).split(',')
    
    def _time(self, time):
        return int(time) - int(time) % self.resolution
    
    def _bucket(self, time):
        return '%s-%s' % (self.prefix, self._time(time))


# in progress flag, remember in node <- cleanup, check if still around
# emitter catches internal jobs


########NEW FILE########
__FILENAME__ = bigtest


# spawn workers
# initiate restiator (pointed to http.py)
# show enqueue rate, sent count
# wait for results from workers
# show dequeue rate, received count
# show aggregated throughput rate (noting concurrency)
########NEW FILE########
__FILENAME__ = cluster
import sys
import os
import random
import eventlet
import collections

from eventlet.green import socket
from eventlet.green import zmq
from eventlet.hubs import use_hub
from zmq import devices

import memcache

use_hub('zeromq')

class CoordinationError(Exception): pass

class ClusterNode(object):
    """ This is a simple cluster management system using memcache to coordinate.
        It uses heartbeats to keep the local cluster representation fresh while
        refreshing the node's record in memcache for the others. If a node
        doesn't heartbeat before its TTL, it will be dropped from peers when
        they heartbeat. """
    
    retries = 3
    
    def __init__(self, context, client, prefix, id, ttl=30, port=7777):
        self.context = context
        self.client = client
        self.index = prefix
        self.id = id
        self.ttl = ttl
        self.port = port
        self.cluster = set()
        self.control = None
        self.callbacks = collections.defaultdict(list)
    
    def join(self):
        for retry in range(self.retries):
            cluster = self.client.gets(self.index) or ''
            if cluster:
                cluster = self._cleanup_index(set(cluster.split(',')))
            else:
                cluster = set()
            self.client.set('%s.%s' % (self.index, self.id), self.id, time=self.ttl)
            cluster.add(self.id)
            if self.client.cas(self.index, ','.join(cluster)):
                print "[Cluster] Joined as %s" % self.id
                self.cluster = cluster
                self._schedule_heartbeat()
                self._create_sockets(self.cluster)
                return True
        raise CoordinationError()
    
    def leave(self):
        for retry in range(self.retries):
            self.client.delete('%s.%s' % (self.index, self.id))
            cluster = self.client.gets(self.index) or ''
            if cluster:
                cluster = self._cleanup_index(set(cluster.split(',')))
            else:
                cluster = set()
            if self.client.cas(self.index, ','.join(cluster)):
                self.cluster = set()
                return True
        raise CoordinationError()
    
    def peers(self):
        return list(self.cluster - set([self.id]))
    
    def all(self):
        return list(self.cluster)
    
    def _cleanup_index(self, cluster):
        index = self.client.get_multi(cluster, '%s.' % self.index) 
        return set([n for n in index if n])
    
    def _create_sockets(self, addresses=None):
        self.control = self.context.socket(zmq.SUB)
        self.control.setsockopt(zmq.SUBSCRIBE, '')
        self._control_out = self.context.socket(zmq.PUB)
        self._control_out.bind('tcp://%s:%s' % (self.id, self.port))
        if addresses:
            self._connect_sockets(addresses)
    
    def _connect_sockets(self, addresses):
        for address in addresses:
            self.control.connect('tcp://%s:%s' % (address, self.port))
        
    def send(self, message):
        self._control_out.send(message)
    
    def _schedule_heartbeat(self):
        if len(self.cluster):
            random_interval = random.randint(self.ttl/2, self.ttl-(self.ttl/5))
            def update():
                self.client.set('%s.%s' % (self.index, self.id), self.id, time=self.ttl)
                old_cluster = self.cluster
                self.cluster = self._cleanup_index(set(self.client.get(self.index).split(',')))
                print self.cluster
                added = self.cluster - old_cluster
                if added:
                    print "[Cluster] Added %s" % ', '.join(added)
                    self._connect_sockets(added)
                    for cb in self.callbacks['add']:
                        cb(added)
                self._schedule_heartbeat()
            eventlet.spawn_after(random_interval, update)


########NEW FILE########
__FILENAME__ = core
import sys
import os
import eventlet
import uuid
import time
import json

from eventlet.green import socket
from eventlet.green import zmq
from eventlet.hubs import use_hub
from eventlet import wsgi
from zmq import devices

import memcache
import webob

from utils import Device
from cluster import ClusterNode
from agenda import Agenda

use_hub('zeromq')

interface = sys.argv[1]

cluster_address, cluster_key = sys.argv[2].split('/')

datastore = memcache.Client([cluster_address], debug=0)

ctx = zmq.Context()

cluster = ClusterNode(ctx, datastore, cluster_key, interface, ttl=10)
cluster.join()

agenda = Agenda(datastore, 'miyamoto-data')

dispatch_timeout = 60

# These need to have a max size
enqueued = set()

frontend = Device(zmq.QUEUE, zmq.XREP, zmq.XREQ, ctx)
frontend.bind_in('tcp://%s:7000' % interface)
frontend.bind_out('inproc://frontend-out')
print "Starting frontend on 7000..."
frontend.start()

enqueue_out = ctx.socket(zmq.PUSH)

# token::{task}
# :time:{task}
# token:time:{task}
# ::{task}
# {task}
def enqueuer():
    incoming = ctx.socket(zmq.REP)
    incoming.connect('inproc://frontend-out')
    
    while True:
        msg = incoming.recv()
        params, task = msg.split('{', 1)
        task = '{%s' % task
        if params:
            token, time, x = params.split(':')
        else:
            token = None
            time = None

        id = enqueue(task, time, token)
        if id:
            incoming.send('{"status":"stored", "id": "%s"}' % id)
        elif id == False:
            incoming.send('{"status":"duplicate"}')
        else:
            incoming.send('{"status":"failure"}')

def enqueue(task, time=None, token=None):
    if token and token in enqueued:
        return False
    id = uuid.uuid4().hex
    if agenda.add(id, at=time or None) and datastore.set(id, task):
        if token:
            enqueued.add(token)
        enqueue_out.send_pyobj((id, task))
        return id
    else:
        return None
        
def dispatcher():
    incoming = ctx.socket(zmq.PULL)
    incoming.bind('tcp://%s:7050' % interface)
    incoming.bind('inproc://dispatcher-in')
    outgoing = ctx.socket(zmq.PUSH)
    print "Binding dispatcher on 8000..."
    outgoing.bind('tcp://%s:8000' % interface)
    while True:
        id, task = incoming.recv_pyobj()
        if not datastore.get('%s-dispatch' % id):
            outgoing.send("%s:%s" % (id, task))
            datastore.set('%s-dispatch' % id, dispatch_timeout)

def finisher():
    incoming = ctx.socket(zmq.SUB)
    incoming.setsockopt(zmq.SUBSCRIBE, "")
    print "Binding finisher on 9000..."
    incoming.bind('tcp://%s:9000' % interface)
    while True:
        id = incoming.recv()
        datastore.delete('%s-dispatch' % id)
        datastore.delete(id)

def control():
    while True:
        cmd, payload = cluster.control.recv().split(',')
        # ...

def web_enqueuer(env, start_response):
    req = webob.Request(env)
    task = dict(req.POST)
    if '_time' in task:
        del task['_time']
    if '_token' in task:
        del task['_token']
    task = json.dumps(task)
    id = enqueue(task, req.POST.get('_time'), req.POST.get('_token'))
    if id:
        start_response('200 OK', [('Content-Type', 'application/json')])
        return ['{"status":"stored", "id": "%s"}\n' % id]
        outgoing.send_pyobj((id, task))
    elif id == False:
        start_response('400 Bad request', [('Content-Type', 'application/json')])
        return ['{"status":"duplicate"}\n']
    else:
        start_response('500 Server error', [('Content-Type', 'application/json')])
        return ['{"status":"failure"}\n']
    

def setup_enqueue():
    def connect(node):
        print "Enqueuer connecting to %s..." % node
        if node == interface:
            enqueue_out.connect('inproc://dispatcher-in')
        else:
            enqueue_out.connect('tcp://%s:7050' % node)
    for node in cluster.all():
        connect(node)
    cluster.callbacks['add'].append(lambda x: map(connect,x))

try:
    
    for n in range(2):
        eventlet.spawn_after(1, enqueuer)
    eventlet.spawn_n(dispatcher)
    eventlet.spawn_n(finisher)
    
    eventlet.spawn_after(1, setup_enqueue)
    
    
    wsgi.server(eventlet.listen((interface, 8080)), web_enqueuer)
    #while True:
    #    eventlet.sleep(1)
        
except (KeyboardInterrupt, SystemExit):
    print "Exiting..."
    cluster.leave()
    ctx.term()
########NEW FILE########
__FILENAME__ = debug
import sys
import eventlet

from eventlet.green import socket
from eventlet.green import zmq
from eventlet.hubs import use_hub

import utils

use_hub('zeromq')

ctx = zmq.Context()

nodes = utils.cluster(sys.argv[1])

def worker():
    dispatcher = ctx.socket(zmq.PULL)
    finisher = ctx.socket(zmq.PUB)
    for node in nodes:
        dispatcher.connect('tcp://%s:8000' % node)
        finisher.connect('tcp://%s:9000' % node)
    while True:
        id, job = dispatcher.recv().split(':', 1)
        print job
        finisher.send(id)
        

try:
    eventlet.spawn_n(worker)
    while True: eventlet.sleep(1)
        
except (KeyboardInterrupt, SystemExit):
    print "Exiting."
########NEW FILE########
__FILENAME__ = fabfile
import os
import os.path
import sys
import time
import boto
from fabric.api import *

ami = 'ami-9c9f6ef5'
key_name = 'progrium'

conn = boto.connect_ec2()

#if os.path.exists('hosts'):
#    f = open('hosts', 'r')
#    env.roledefs = f.read()

def start():
    reservation = conn.get_image(ami).run(key_name=key_name)
    instance = reservation.instances[0]
    while instance.update() == 'pending':
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(1)
    env.hosts = ['root@%s' % instance.public_dns_name]
    time.sleep(60)

def touch():
    run("touch testfile")

########NEW FILE########
__FILENAME__ = http
import cgi
import sys
import eventlet
from eventlet.green import socket
from eventlet.green import zmq
from eventlet.hubs import use_hub

from eventlet import wsgi

import utils

use_hub('zeromq')

port = int(sys.argv[1])
nodes = utils.cluster(sys.argv[2])


ctx = zmq.Context()

pool = []
for n in range(2):
    enqueuer = ctx.socket(zmq.REQ)
    for node in nodes:
        print "Connecting to %s..." % node
        enqueuer.connect('tcp://%s:7000' % node)
    pool.append(enqueuer)

def enqueue(env, start_response):
    for n in range(len(pool)):
        try:
            pool[n].send(env['wsgi.input'].read())
            resp = pool[n].recv()
            if 'stored' in resp:
                start_response('200 OK', [('Content-Type', 'text/plain')])
            else:
                start_response('503 Error', [('Content-Type', 'text/plain')])
            return ['%s\r\n' % resp]
        except:
            pass
    start_response('503 Error', [('Content-Type', 'text/plain')])
    return ['%s\r\n' % resp]

wsgi.server(eventlet.listen(('', port)), enqueue)
########NEW FILE########
__FILENAME__ = perf
import sys
import os
import eventlet
import uuid
import time
import random

from eventlet.green import socket
from eventlet.green import zmq
from eventlet.hubs import use_hub
from zmq import devices

import memcache

import utils

use_hub('zeromq')

task = sys.argv[1]
nodes = utils.cluster(sys.argv[2])
ctx = zmq.Context()


messages = []

def stopped(count, td):
    print count
    print td
    print 1/(td/count)
    sys.exit(0)

def enqueuer(n):
    frontend = ctx.socket(zmq.REQ)
    for node in nodes:
        frontend.connect('tcp://%s:7000' % node)
    for m in range(n):
        job = '%s::{"job":%s}' % (random.random(), time.time())
        frontend.send(job)
        resp = frontend.recv()
        messages.append(job)
        #print resp

def dequeuer():
    dispatcher = ctx.socket(zmq.PULL)
    finisher = ctx.socket(zmq.PUB)
    for node in nodes:
        dispatcher.connect('tcp://%s:8000' % node)
        finisher.connect('tcp://%s:9000' % node)
    timeout = None
    t1 = None
    while True:
        id, job = dispatcher.recv().split(':', 1)
        if not timeout is None:
            timeout.cancel()
        if not t1:
            t1 = time.time()
        messages.append(job)
        finisher.send(id)
        td = time.time() - t1
        timeout = eventlet.spawn_after(5, stopped, len(messages), td)
        
        

try:
    if task == 'enqueue':
        size = int(os.environ.get('MESSAGES', 10000))
        t1 = time.time()
        eventlet.spawn_n(enqueuer, size)
        while len(messages) < size:
            eventlet.sleep(0.1)
        td = time.time() - t1
        stopped(len(messages), td)
        
    elif task == 'dequeue':
        eventlet.spawn_n(dequeuer)
        while True:
            eventlet.sleep(0.1)
        
except (KeyboardInterrupt, SystemExit):
    sys.exit(0)
########NEW FILE########
__FILENAME__ = sampler
import sys
import os
import eventlet
import time

from eventlet.green import socket
from eventlet.green import zmq
from eventlet.hubs import use_hub

import utils

use_hub('zeromq')

ctx = zmq.Context()

nodes = utils.cluster(sys.argv[1])


def sampler(rate):
    dispatcher = ctx.socket(zmq.PULL)
    finisher = ctx.socket(zmq.PUB)
    for node in nodes:
        dispatcher.connect("tcp://%s:8000" % node)
        finisher.connect("tcp://%s:9000" % node)
    while True:
        id, job = dispatcher.recv().split(':', 1)
        rate.tick()
        finisher.send(id)

def redraw(v, t):
    os.system("clear")
    print "Last sample: %s messages/sec" % v

try:
    rate = utils.SampledRate(0.5, 3, callback=redraw, name='messages')
    eventlet.spawn_n(sampler, rate)
        
    while True:
        eventlet.sleep(1)
        
except (KeyboardInterrupt, SystemExit):
    print "Exiting."
########NEW FILE########
__FILENAME__ = utils
from zmq import devices
import collections
import time
import operator
import memcache

def cluster(spec):
    address, key = spec.split('/')
    return memcache.Client([address]).get(key).split(',')

def elect(client, name, candidate, ttl=60):
    """ Simple leader election-esque distributed selection method """
    if not client.append(name, ',%' % cadidate, time=ttl):
        if client.add(name, candidate, time=ttl):
            return True
        else:
            return False
    else:
        return False

class SampledRate(object):
    """Tool for pushing rate over time data"""
    
    def __init__(self, frequency=1, resolution=1, parent=None, callback=None, name=None):
        """ frequency:  Rate update frequency in seconds
            resolution: Interval to average data over in seconds
            parent:     Another SampledRate that ticks will propagate to
            callback:   Optional callback when frequency is updated"""
        self.frequency  = frequency
        self.resolution = resolution
        self.parent     = parent
        self.callback   = callback
        self.samples    = collections.defaultdict(int)
        self.ticks      = 0
        self.last_start = None
        self.last_value = 0 
        if not name and parent:
            self.name   = parent.name
        else:
            self.name   = name
    
    def _update(self):
        if self.last_start and int(time.time() - self.last_start) > self.frequency:
            # Add empty samples
            for x in range(self.frequency-len(self.samples)):
                self.samples[x] = 0
            self.last_value = reduce(operator.add, self.samples.values()) / self.resolution / self.frequency
            self.last_start = int(time.time())
            if self.callback:
                # reactor.callLater(0, self.callback, self.last_value, self.ticks)
                self.callback(self.last_value, self.ticks)
            self.ticks      = 0
            self.samples    = collections.defaultdict(int)
    
    def tick(self, ticks=1):
        if not self.last_start:
            self.last_start = int(time.time())
        self._update()
        if self.parent:
            self.parent.tick(ticks)
        self.samples[int(time.time() / self.resolution)] += ticks
        self.ticks += ticks
        return self
    
    def getvalue(self):
        self._update()
        return self.last_value
    
    def __int__(self):
        return self.getvalue()
    
    def __str__(self):
        # Okay, hardcoding 1 sec resolutions for now
        return "%i %s/sec" % (self.getvalue(), self.name or 'ticks')
    
    def __repr__(self):
        return "<SampledRate: %i  avg/%is updated/%is>" % (self.getvalue(), self.frequency, self.resolution)
    
class Device(devices.ThreadDevice):
    def __init__(self, type, in_type, out_type, ctx):
        self._context = ctx
        devices.ThreadDevice.__init__(self, type, in_type, out_type)
    
    def _setup_sockets(self):        
        # create the sockets
        ins = self._context.socket(self.in_type)
        if self.out_type < 0:
            outs = ins
        else:
            outs = self._context.socket(self.out_type)
        
        # set sockopts (must be done first, in case of zmq.IDENTITY)
        for opt,value in self._in_sockopts:
            ins.setsockopt(opt, value)
        for opt,value in self._out_sockopts:
            outs.setsockopt(opt, value)
        
        for iface in self._in_binds:
            ins.bind(iface)
        for iface in self._out_binds:
            outs.bind(iface)
        
        for iface in self._in_connects:
            ins.connect(iface)
        for iface in self._out_connects:
            outs.connect(iface)
        
        return ins,outs
########NEW FILE########
__FILENAME__ = cluster
"""A distributed group membership module

This provides distributed group membership for easily building clustered
applications with gevent. Using this in your app, you just provide the IP
of another node in the cluster and it will receive the IPs of all nodes in
the cluster. When a node joins or drops from the cluster, all other nodes find
out immediately.

The roster is managed by a leader. When you create a cluster, you tell the
first node it is the leader (by simply pointing it to its own IP). As you
add nodes, you can point them to the leader or any other node. If a node
is not the leader, it will redirect the connection to the leader. All nodes
also maintain a keepalive with the leader.

If the leader drops from the cluster, the nodes will dumbly pick a new leader
by taking the remaining node list, sorting it, and picking the first node. If
a node happens to get a different leader, as long as it is in the cluster, it
will be redirected to the right leader. 

To try it out on one machine, you need to make several more loopback interfaces:

In OSX:
 ifconfig lo0 inet 127.0.0.2 add
 ifconfig lo0 inet 127.0.0.3 add
 ifconfig lo0 inet 127.0.0.4 add

In Linux:
 ifconfig lo:2 127.0.0.2 up
 ifconfig lo:3 127.0.0.3 up
 ifconfig lo:4 127.0.0.4 up
 
Now you can start the first node on 127.0.0.1:
 INTERFACE=127.0.0.1 python cluster.py

The first argument is the leader, the second is the interface to bind to.
 
Start the others pointing to 127.0.0.1:
 INTERFACE=127.0.0.2 LEADER=127.0.0.1 python cluster.py
 INTERFACE=127.0.0.3 LEADER=127.0.0.1 python cluster.py

Try starting the last one pointing to a non-leader:
 INTERFACE=127.0.0.4 LEADER=127.0.0.3 python cluster.py

Now you can kill any node (including the leader) and bring up another node 
pointing to any other node, and they all get updated immediately.

"""
import gevent.monkey; gevent.monkey.patch_all()

import logging
import socket
import json

import gevent
import gevent.server
import gevent.socket

import constants
import util

logger = logging.getLogger('cluster')

class ClusterError(Exception): pass
class NewLeader(Exception): pass

class ClusterManager(object):
    def __init__(self, leader, callback=None, interface=None, port=constants.DEFAULT_CLUSTER_PORT):
        """ Callback argument is called when the cluster updates. """
        if interface is None:
            interface = socket.gethostbyname(socket.gethostname())
        self.interface = interface
        self.leader = leader
        self.callback = callback
        self.port = port
        self.cluster = set()
        self.pool = []
        self.server = gevent.server.StreamServer((self.interface, self.port), self._connection_handler)
        self.connections = {}
    
    def is_leader(self):
        return self.interface == self.leader
    
    def start(self):
        logger.info("Cluster manager starting for %s on port %s" % (self.interface, self.port))
        self.server.start()
        if self.is_leader():
            self.cluster.add(self.interface)
            if self.callback:
                self.callback(self.cluster.copy())
        else:
            gevent.spawn(self.connect)
    
    def connect(self):
        """ 
        Connects to the currently known leader. It maintains a connection expecting
        JSON lists of hosts in the cluster. It should receive a list on connection,
        however, if a list of one, this is a redirect to the leader (you hit a node
        in the cluster that's not the leader). We also maintain a keepalive. If we
        disconnect, it does a leader elect and reconnects.
        """
        while True:
            logger.info("Connecting to leader %s on port %s" % (self.leader, self.port))
            try:
                client = util.connect_and_retry((self.leader, self.port), 
                        source_address=(self.interface, 0), max_retries=5)
            except IOError:
                raise ClusterError("Unable to connect to leader: %s" % self.leader)
            logger.info("Connected to leader")
            # Use TCP keepalives
            keepalive = gevent.spawn_later(5, lambda: client.send('\n'))
            try:
                for line in util.line_protocol(client, strip=False):
                    if line == '\n':
                        # Keepalive ack from leader
                        keepalive.kill()
                        keepalive = gevent.spawn_later(5, lambda: client.send('\n'))
                    else:
                        new_cluster = json.loads(line)
                        if len(new_cluster) == 1:
                            # Cluster of one means you have the wrong leader
                            self.leader = new_cluster[0]
                            logger.info("Redirected to %s..." % self.leader)
                            raise NewLeader()
                        else:
                            self.cluster = set(new_cluster)
                            if self.callback:
                                self.callback(self.cluster.copy())
                self.cluster.remove(self.leader)
                candidates = list(self.cluster)
                candidates.sort()
                self.leader = candidates[0]
                logger.info("New leader %s..." % self.leader)
                # TODO: if i end up thinking i'm the leader when i'm not
                # then i will not rejoin the cluster
                raise NewLeader()
            except NewLeader:
                if self.callback:
                    self.callback(self.cluster.copy())
                if not self.is_leader():
                    gevent.sleep(1) # TODO: back off loop, not a sleep
                else:
                    break

    def _connection_handler(self, socket, address):
        """
        If not a leader, a node will simply return a single item list pointing
        to the leader. Otherwise, it will add the host of the connected client
        to the cluster roster, broadcast to all nodes the new roster, and wait
        for keepalives. If no keepalive within timeout or the client drops, it
        drops it from the roster and broadcasts to all remaining nodes. 
        """
        #print 'New connection from %s:%s' % address
        if not self.is_leader():
            socket.send(json.dumps([self.leader]))
            socket.close()
        else:
            self._update(add={'host': address[0], 'socket': socket})
            timeout = gevent.spawn_later(10, lambda: self._shutdown(socket))            
            for line in util.line_protocol(socket, strip=False):
                timeout.kill()
                timeout = gevent.spawn_later(10, lambda: self._shutdown(socket))
                socket.send('\n')
                #print "keepalive from %s:%s" % address
            #print "client disconnected"
            self._update(remove=address[0])
    
    def _shutdown(self, socket):
        try:
            socket.shutdown(0)
        except IOError:
            pass
    
    def _update(self, add=None, remove=None):
        """ Used by leader to manage and broadcast roster """
        if add is not None:
            self.cluster.add(add['host'])
            self.connections[add['host']] = add['socket']
        if remove is not None:
            self.cluster.remove(remove)
            del self.connections[remove]
        for conn in self.connections:
            self.connections[conn].send('%s\n' % json.dumps(list(self.cluster)))
        if self.callback:
            self.callback(self.cluster.copy())


if __name__ == '__main__':
    import os
    
    interface = os.environ.get('INTERFACE')
    leader = os.environ.get('LEADER', interface)
    
    def print_cluster(cluster):
        print json.dumps(list(cluster))
    
    print "%s: Using leader %s..." % (interface, leader)
    
    ClusterManager(leader, callback=print_cluster, interface=interface).start()

    while True:
        gevent.sleep()
########NEW FILE########
__FILENAME__ = constants

DEFAULT_CLUSTER_PORT = 6000
DEFAULT_FRONTEND_PORT = 8088
DEFAULT_BACKEND_PORT = 6001

DEFAULT_REPLICA_FACTOR = 2

DEFAULT_REPLICA_SECS_OFFSET = 5

WORKER_TIMEOUT = 5
########NEW FILE########
__FILENAME__ = dispatcher
import gevent.monkey; gevent.monkey.patch_all()

import socket
import urllib2
try:
    import json
except ImportError:
    import simplejson as json

from gevent_zeromq import zmq
import gevent
import gevent.monkey
import gevent.server
import gevent.socket
import gevent.queue
import gevent.event
import gevent.coros
import httplib2

from task import Task
import util
import constants

class TaskFailure(Exception): pass

class DispatchClient(object):
    def __init__(self, interface, callback):
        self.interface = interface
        self.callback = callback
        self.socket = None
    
    def start(self):
        gevent.spawn(self._run)
    
    def dispatch(self, task):
        if self.socket:
            self.socket.send('%s\n' % task.serialize())
    
    def _run(self):
        while True:
            try:
                self.socket = gevent.socket.create_connection((self.interface, 6002), source_address=(self.interface, 0))
            
                for line in util.line_protocol(self.socket):
                    event, payload = line.split(':', 1)
                    self.callback(event, payload)
            except IOError:
                pass
                    
            print "disconnected from dispatcher, retrying..."
        

class Dispatcher(object):
    def __init__(self, interface, zmq_context, workers=10):
        # hardcoding for now
        self.workers = workers
        self.server = gevent.server.StreamServer((interface, 6002), self._connection_handler)
        self.queue = gevent.queue.Queue()
        self.scheduler = None
        self.zmq = zmq_context
        self.zmq_sockets = {}
    
    def start(self, block=True):
        self.server.start()
        for n in xrange(self.workers):
            gevent.spawn(self._dispatcher)
        
        while block:
            gevent.sleep(1)
    
    def _dispatcher(self):
        http = httplib2.Http()
        while True:
            try:
                task = Task.unserialize(self.queue.get())
                timeout = gevent.Timeout(constants.WORKER_TIMEOUT)
                timeout.start()
                self.scheduler.send('start:%s\n' % task.id)
                
                if task.url.startswith('http'):
                    headers = {"User-Agent": "Miyamoto/0.1", "X-Task": task.id, "X-Queue": task.queue_name}
                    resp, content = http.request(task.url, method=task.method, headers=headers)
                else:
                    zmq_remotes = frozenset(task.url.split(','))
                    if not zmq_remotes in self.zmq_sockets:
                        sock = self.zmq.socket(zmq.REQ)
                        lock = gevent.coros.Semaphore()
                        for remote in zmq_remotes:
                            sock.connect(remote)
                        self.zmq_sockets[zmq_remotes] = (sock, lock)
                    else:
                        sock, lock = self.zmq_sockets[zmq_remotes]
                    try:
                        lock.acquire() # Because send/recv have to be done together
                        sock.send(task.url)
                        resp = sock.recv()
                    except zmq.ZMQError:
                        raise
                    finally:
                        lock.release()
                self.scheduler.send('success:%s\n' % task.id)
            except (gevent.Timeout, zmq.ZMQError, TaskFailure), e:
                self.scheduler.send('failure:%s:%s\n' % (task.id, str(e)))
            finally:
                timeout.cancel()
    
    def _connection_handler(self, socket, address):
        print "pair connected"
        self.scheduler = socket
        for line in util.line_protocol(socket):
            self.queue.put(line)
        print "pair dropped"
    

########NEW FILE########
__FILENAME__ = queue
import gevent.monkey; gevent.monkey.patch_all()

import socket
import urllib2
try:
    import json
except ImportError:
    import simplejson as json

import gevent
import gevent.pywsgi
import gevent.queue

from cluster import ClusterManager
from scheduler import DistributedScheduler
from task import Task
import constants

class QueueServer(object):
    # TODO: make args list
    def __init__(self, leader, replica_factor=constants.DEFAULT_REPLICA_FACTOR, 
        replica_offset=constants.DEFAULT_REPLICA_SECS_OFFSET, interface=None, 
        frontend_port=constants.DEFAULT_FRONTEND_PORT, 
        backend_port=constants.DEFAULT_BACKEND_PORT, 
        cluster_port=constants.DEFAULT_CLUSTER_PORT):
        if interface is None:
            interface = socket.gethostbyname(socket.gethostname())
        self.queue = gevent.queue.Queue()
        self.frontend = gevent.pywsgi.WSGIServer((interface, frontend_port), self._frontend_app, log=None)
        self.scheduler = DistributedScheduler(self.queue, leader, replica_factor=replica_factor, 
            replica_offset=replica_offset, interface=interface, port=backend_port, cluster_port=cluster_port)
        self._ready_event = None
    
    def start(self, block=True):
        self.frontend.start()
        self.scheduler.start()
        
        while not self.frontend.started:
            gevent.sleep(1)
        
        self._ready_event.set()
        
        while block:
            gevent.sleep(1)
    
    def _frontend_app(self, env, start_response):
        try:
            queue_name = env['PATH_INFO']
            content_type = env['CONTENT_TYPE']
            body = env['wsgi.input'].read()
            task = Task(queue_name, content_type, body)
            
            self.scheduler.schedule(task) # TODO: needs queue on the other end
            
            start_response('200 OK', [('Content-Type', 'application/json')])
            return ['{"status": "scheduled", "id": "%s"}\n' % task.id]
        except NotImplemented, e:
            start_response('500 Error', [('Content-Type', 'application/json')])
            return [json.dumps({"status": "error", "reason": repr(e)})]

########NEW FILE########
__FILENAME__ = scheduler
import gevent.monkey; gevent.monkey.patch_all()

import socket
import time

import gevent
import gevent.server
import gevent.socket
import gevent.queue

from cluster import ClusterManager
from dispatcher import DispatchClient
from task import Task
import util
import constants

class ScheduleError(Exception): pass

class DistributedScheduler(object):
    def __init__(self, queue, leader, replica_factor=2, replica_offset=5, interface=None, 
        port=6001, cluster_port=6000):
        if interface is None:
            interface = socket.gethostbyname(socket.gethostname())
        self.interface = interface
        self.port = port
        
        self.dispatcher = DispatchClient(interface, self._dispatcher_event)
        self.cluster = ClusterManager(leader, callback=self._cluster_update, 
                            interface=interface, port=cluster_port)
        self.backend = gevent.server.StreamServer((interface, port), self._backend_server)
        self.peers = set()
        self.connections = {}
        
        self.queue = queue
        self.scheduled = {}
        self.scheduled_acks = {}
        self.schedules = 0
        
        self.replica_factor = replica_factor
        self.replica_offset = replica_offset

        
    def start(self):
        self.dispatcher.start()
        self.backend.start()
        self.cluster.start()
    
    def schedule(self, task):
        host_list = list(self.peers)
        # This implements the round-robin N replication method for picking
        # which hosts to send the task. In short, every schedule moves along the
        # cluster ring by one, then picks N hosts, where N is level of replication
        replication_factor = min(self.replica_factor, len(host_list))
        host_ids = [(self.schedules + n) % len(host_list) for n in xrange(replication_factor)]
        hosts = [host_list[id] for id in host_ids]
        task.replica_hosts = hosts
        self.scheduled_acks[task.id] = gevent.queue.Queue()
        for host in hosts:
            self.connections[host].send('schedule:%s\n' % task.serialize())
            task.replica_offset += self.replica_offset
        try:
            # TODO: document, wrap this whole operation in timeout
            return all([self.scheduled_acks[task.id].get(timeout=2) for h in hosts])
        except gevent.queue.Empty:
            raise ScheduleError("not all hosts acked")
        finally:
            self.schedules += 1 
            self.scheduled_acks.pop(task.id)

    
    def _cluster_update(self, hosts):
        add_hosts = hosts - self.peers
        remove_hosts = self.peers - hosts
        for host in remove_hosts:
            print "disconnecting from peer %s" % host
            gevent.spawn(self._remove_peer, host)
        for host in add_hosts:
            print "connecting to peer %s" % (host)
            gevent.spawn(self._add_peer, host)
        self.peers = hosts
    
    def _add_peer(self, host):
        client = gevent.socket.create_connection((host, self.port), source_address=(self.interface, 0))
        self.connections[host] = client
        for line in util.line_protocol(client):
            ack, task_id = line.split(':', 1)
            if ack == 'scheduled' and task_id in self.scheduled_acks:
                self.scheduled_acks[task_id].put(True)
        print "disconnected from peer %s" % host
        self._remove_peer(host)
    
    def _remove_peer(self, host):
        if host in self.connections:
            peer = self.connections.pop(host)
            try:
                peer.shutdown(0)
            except:
                pass

    def _dispatcher_event(self, event, payload):
        if event == 'start':
            task = self.scheduled[payload]
            eta = int(time.time() + constants.WORKER_TIMEOUT)
            self._sendto_replicas(task, 'reschedule:%s:%s\n' % (task.id, eta))
        
        elif event == 'success':
            task = self.scheduled[payload]
            self._sendto_replicas(task, 'cancel:%s\n' % task.id)
            self.scheduled.pop(task.id)
        
        elif event == 'failure':
            task_id, reason = payload.split(':', 1)
            self.scheduled.pop(task.id)
            print "FAILURE %s: %s" % (task_id, reason)
    
    def _sendto_replicas(self, task, message):
        other_replica_hosts = set(task.replica_hosts) - set([self.interface])
        for host in other_replica_hosts:
            if host in self.connections:
                self.connections[host].send(message)
    
    def _backend_server(self, socket, address):
        for line in util.line_protocol(socket):
            action, payload = line.split(':', 1)
            
            if action == 'schedule':
                task = Task.unserialize(payload)
                task.schedule(self.dispatcher)
                self.scheduled[task.id] = task
                socket.send('scheduled:%s\n' % task.id)
                print "scheduled: %s" % task.id
            
            elif action == 'cancel':
                task_id = payload
                print "canceled: %s" % task_id
                self.scheduled.pop(task_id).cancel()
            
            elif action == 'reschedule':
                task_id, eta = payload.split(':', 1)
                eta = int(eta)
                print "rescheduled: %s for %s" % (task_id, eta)
                self.scheduled[task_id].reschedule(self.dispatcher, eta)

########NEW FILE########
__FILENAME__ = service
import gevent
import gevent.baseserver
import gevent.event
import gevent.pool

READY = True

class Service(object):
    """Service interface for creating standalone or composable services
    
    This is similar to a subset of the gevent baseserver interface (intentional)
    so that you can treat them as children services. 
    """
    stop_timeout = 1
    ready_timeout = 2
    
    def __init__(self):
        self._stopped_event = gevent.event.Event()
        self._ready_event = gevent.event.Event()
        self._children = []
        self._greenlets = gevent.pool.Group()
        self.started = False
    
    @property
    def ready(self):
        return self._ready_event.isSet()
    
    def spawn(self, *args, **kwargs):
        self._greenlets.spawn(*args, **kwargs)
    
    def start(self, block_until_ready=True):
        assert not self.started, '%s already started' % self.__class__.__name__
        self._stopped_event.clear()
        self._ready_event.clear()
        try:
            for child in self._children:
                if isinstance(child, Service):
                    child.start(block_until_ready)
                elif isinstance(child, gevent.baseserver.BaseServer):
                    child.start()
            ready = self._start()
            if ready is True:
                self._ready_event.set()
            elif not ready and block_until_ready is True:
                self._ready_event.wait(self.ready_timeout)
            self.started = True
        except:
            self.stop()
            raise
    
    def _start(self):
        raise NotImplementedError()
    
    def stop(self, timeout=None):
        """Stop accepting the connections and close the listening socket.

        If the server uses a pool to spawn the requests, then :meth:`stop` also waits
        for all the handlers to exit. If there are still handlers executing after *timeout*
        has expired (default 1 second), then the currently running handlers in the pool are killed."""
        self.started = False
        try:
            for child in self._children:
                child.stop()
            self._stop()
        finally:
            if timeout is None:
                timeout = self.stop_timeout
            if self._greenlets:
                self._greenlets.join(timeout=timeout)
                self._greenlets.kill(block=True, timeout=1)
            self._ready_event.clear()
            self._stopped_event.set()
    
    def _stop(self):
        raise NotImplementedError()
    
    def serve_forever(self, stop_timeout=None):
        """Start the service if it hasn't been already started and wait until it's stopped."""
        if not self.started:
            self.start()
        try:
            self._stopped_event.wait()
        except:
            self.stop(timeout=stop_timeout)
            raise
########NEW FILE########
__FILENAME__ = task
import base64
import cPickle
import json
import time
import urllib
import urllib2
import urlparse
import uuid

import gevent

class Task(object):
    def __init__(self, queue_name, content_type, body):
        self.queue_name = queue_name
        if content_type == 'application/json':
            data = json.loads(body)
            self.url = data['url']
            self.method = data.get('method', 'POST')
            countdown = data.get('countdown')
            self.eta = data.get('eta')
            self.params = data.get('params', {})
        elif content_type == 'application/x-www-form-urlencoded':
            data = urlparse.parse_qs(body)
            self.url = data['task.url'][0]
            self.method = data.get('task.method', ['POST'])[0]
            countdown = data.get('task.countdown', [None])[0]
            self.eta = data.get('task.eta', [None])[0]
            self.params = dict([(k,v[0]) for k,v in data.items() if not k.startswith('task.')])
        else:
            raise NotImplementedError("content type not supported")
        if countdown and not self.eta:
            self.eta = int(time.time()+int(countdown))
        self.id = str(uuid.uuid4()) # vs time.time() is about 100 req/sec slower
        self.replica_hosts = []
        self.replica_offset = 0
        self._greenlet = None
        self._serialize_cache = None
    
    def time_until(self):
        if self.eta:
            countdown = int(int(self.eta) - time.time())
            if countdown < 0:
                return self.replica_offset
            else:
                return countdown + self.replica_offset
        else:
            return self.replica_offset
    
    def schedule(self, dispatcher):
        self._greenlet = gevent.spawn_later(self.time_until(), dispatcher.dispatch, self)
    
    def reschedule(self, dispatcher, eta):
        self.cancel()
        self.eta = eta
        self.schedule(dispatcher)
    
    def cancel(self):
        self._greenlet.kill()
    
    def serialize(self):
        if self._serialize_cache:
            return self._serialize_cache
        else:
            return base64.b64encode(cPickle.dumps(self, cPickle.HIGHEST_PROTOCOL))
    
    @classmethod
    def unserialize(cls, data):
        task = cPickle.loads(base64.b64decode(data))
        task._serialize_cache = data
        return task
########NEW FILE########
__FILENAME__ = test_cluster
import multiprocessing

import gevent
from nose import with_setup

from miyamoto.test import Cluster
from miyamoto.test import TaskCountdown
from miyamoto import constants

_cluster = Cluster(size=2, replica_factor=2)

def start_cluster():
    _cluster.start()

def stop_cluster():
    _cluster.stop()

@with_setup(start_cluster, stop_cluster)
def test_cluster_starts_and_all_nodes_work():
    countdown = TaskCountdown(len(_cluster))
    url = countdown.start()
    for node in _cluster.nodes:
        node.enqueue('test', {'url': url})
    countdown.wait(1)
    assert countdown.finished()

@with_setup(start_cluster, stop_cluster)
def test_replication_by_killing_node_after_schedule():
    countdown = TaskCountdown(1)
    url = countdown.start()
    assert _cluster.nodes[0].enqueue('test', {'url': url, 'countdown': 1})
    assert not countdown.finished()
    _cluster.nodes[0].terminate()
    countdown.wait(1)
    assert countdown.finished()

@with_setup(start_cluster, stop_cluster)
def test_add_node_and_that_it_replicates_into_cluster():
    countdown = TaskCountdown(2)
    url = countdown.start()
    node = _cluster.add()
    gevent.sleep(2)
    print url
    assert node.enqueue('test', {'url': url})
    assert node.enqueue('test', {'url': url})
    #node.enqueue('test', {'url': url, 'countdown': 2})
    #node.terminate()
    countdown.wait(2)
    print countdown.count
    assert countdown.finished()

def test_killing_the_leader_means_nothing():
    # start cluster
    # kill leader
    # add node
    # hit nodes twice
    # assert tasks
    pass



########NEW FILE########
__FILENAME__ = test_service
import gevent

from miyamoto import service

class BasicService(service.Service):
    def __init__(self, name):
        super(BasicService, self).__init__()
        self.name = name
    
    def _start(self):
        return service.READY
    
    def _stop(self):
        pass

class SlowReadyService(BasicService):
    def _start(self):
        self.spawn(self._run)
    
    def _run(self):
        gevent.sleep(0.5)
        self._ready_event.set()

def test_basic_service():
    s = BasicService('test')
    s.start()
    assert s.started == True, "Service is not started"
    assert s.ready == True, "Service is not ready"
    s.stop()
    assert s.started == False, "Service did not stop"

def test_slow_ready_service():
    s = SlowReadyService('test')
    s.start(block_until_ready=False)
    assert s.ready == False, "Service was ready too quickly"
    assert s.started == True, "Service is not started"
    s.stop()
    assert s.ready == False, "Service was still ready after stop"
    assert s.started == False, "Service did not stop"
    
    s.start()
    assert s.ready == True, "Service was not ready after blocking start"
    s.stop()
    assert s.ready == False, "Service was still ready after stop"

def test_child_service():
    class ParentService(BasicService):
        def __init__(self, name):
            super(ParentService, self).__init__(name)
            self.child = SlowReadyService('child')
            self._children.append(self.child)
            
        def _start(self):
            return service.READY
    
    s = ParentService('parent')
    s.start()
    assert s.child.ready == True, "Child service is not ready"
    assert s.ready == True, "Parent service is not ready"
    s.stop()
    assert s.child.started == False, "Child service is still started"
    assert s.child.ready == False, "Child service is still ready"

def test_service_greenlets():
    class GreenletService(BasicService):
        def _start(self):
            for n in xrange(3):
                self.spawn(self._run, n)
            return service.READY

        def _run(self, index):
            while True:
                gevent.sleep(0.1)
    
    s = GreenletService('greenlets')
    s.start()
    for greenlet in s._greenlets:
        assert not greenlet.ready(), "Greenlet is ready when it shouldn't be"
    s.stop()
    for greenlet in s._greenlets:
        assert greenlet.ready(), "Greenlet isn't ready after stop"
                
########NEW FILE########
__FILENAME__ = util
import random

import gevent.socket

def line_protocol(socket, strip=True):
    fileobj = socket.makefile()
    while True:
        try:
            line = fileobj.readline() # returns None on EOF
            if line is not None and strip:
                line = line.strip()
        except IOError:
            line = None
        if line:
            yield line
        else:
            break

def connect_and_retry(address, source_address=None, max_retries=None):
    max_delay = 3600
    factor = 2.7182818284590451 # (math.e)
    jitter = 0.11962656472 # molar Planck constant times c, joule meter/mole
    delay = 1.0
    retries = 0
    
    while True:
        try:
            return gevent.socket.create_connection(address, source_address=source_address)
        except IOError:
            retries += 1
            if max_retries is not None and (retries > max_retries):
                raise IOError("Unable to connect after %s retries" % max_retries)
            delay = min(delay * factor, max_delay)
            delay = random.normalvariate(delay, delay * jitter)
            gevent.sleep(delay)

########NEW FILE########
__FILENAME__ = sampler
import collections
import operator
import time
import os

import gevent.pywsgi
from gevent_zeromq import zmq

class RateSampler(object):
    """Tool for pushing rate over time data"""
    
    def __init__(self, frequency=1, resolution=1, parent=None, callback=None, name=None):
        """ frequency:  Rate update frequency in seconds
            resolution: Interval to average data over in seconds
            parent:     Another RateSampler that ticks will propagate to
            callback:   Optional callback when frequency is updated"""
        self.frequency  = frequency
        self.resolution = resolution
        self.parent     = parent
        self.callback   = callback
        self.samples    = collections.defaultdict(int)
        self.ticks      = 0
        self.last_start = None
        self.last_value = 0 
        if not name and parent:
            self.name   = parent.name
        else:
            self.name   = name
    
    def _update(self):
        if self.last_start and int(time.time() - self.last_start) > self.frequency:
            # Add empty samples
            for x in range(self.frequency-len(self.samples)):
                self.samples[x] = 0
            self.last_value = reduce(operator.add, self.samples.values()) / self.resolution / self.frequency
            self.last_start = int(time.time())
            if self.callback:
                # reactor.callLater(0, self.callback, self.last_value, self.ticks)
                self.callback(self.last_value, self.ticks)
            self.ticks      = 0
            self.samples    = collections.defaultdict(int)
    
    def tick(self, ticks=1):
        if not self.last_start:
            self.last_start = int(time.time())
        self._update()
        if self.parent:
            self.parent.tick(ticks)
        self.samples[int(time.time() / self.resolution)] += ticks
        self.ticks += ticks
        return self
    
    def getvalue(self):
        self._update()
        return self.last_value
    
    def __int__(self):
        return self.getvalue()
    
    def __str__(self):
        # Okay, hardcoding 1 sec resolutions for now
        return "%i %s/sec" % (self.getvalue(), self.name or 'ticks')
    
    def __repr__(self):
        return "<SampledRate: %i  avg/%is updated/%is>" % (self.getvalue(), self.frequency, self.resolution)


def redraw(v, t):
    os.system("clear")
    print "Last sample: %s tasks/sec" % v

rate = RateSampler(1, 5, callback=redraw, name='tasks')
ctx = zmq.Context()

def http_sampler(env, start_response):
    rate.tick()
    start_response('200 OK', [])
    return ['ok']

def zmq_sampler():
    socket = ctx.socket(zmq.REP)
    socket.bind('tcp://127.0.0.1:9999')
    while True:
        socket.recv()
        rate.tick()
        socket.send("ok")

gevent.spawn(zmq_sampler)
server = gevent.pywsgi.WSGIServer(('', int(os.environ.get('PORT', 9099))), http_sampler, log=None)
server.serve_forever()

########NEW FILE########
__FILENAME__ = start
import sys
import os

from miyamoto import start

interface = os.environ.get('INTERFACE')
leader = os.environ.get('LEADER', interface)
replicas = int(os.environ.get('REPLICAS', 2))

print "%s: Using leader %s..." % (interface, leader)

start(leader, replicas, interface)

########NEW FILE########
__FILENAME__ = worker
from gevent import wsgi
import gevent

def outputter(env, start):
    print env
    #gevent.sleep(4)
    start('200 OK', {})
    return ["ok"]

print 'Serving on 8080...'
wsgi.WSGIServer(('', 8080), outputter).serve_forever()
########NEW FILE########
