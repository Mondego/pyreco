__FILENAME__ = key_value
'''
This module implements a simple, distributed Key-Value database that uses Paxos
for ensuring consistency between nodes. The goal of this module is to provide a
simple and correct implementation that is useful both as an example for using
zpax for distributed consensus as well as an actual, embedded database for real
applications. Due to the simplicity goal, the performance of this
implementation is not stellar but should be sufficient for lightweight usage.
'''

# Potential future extensions:
#
#   * Buffered key=value assignments. Writes to different keys guarantee not to
#     conflict.
#
#   * Multi-key commit: Check all key-sequence numbers in request match the current
#     db state. If so, pass though to paxos for decision. If not, send nack.


import os.path
import sqlite3
import json

from zpax import multi

from twisted.internet import defer, task, reactor


_ZPAX_CONFIG_KEY = '__zpax_config__'

tables = dict()

# Deletions update the deltion key with the
# instance number
tables['kv'] = '''
key      text PRIMARY KEY,
value    text,
instance integer
'''


class SqliteDB (object):

    def __init__(self, fn):
        self._fn = fn
        create = not os.path.exists(fn)
        
        self._con = sqlite3.connect(fn)
        self._cur = self._con.cursor()

        if create:
            self.create_db()

            
    def create_db(self):
        cur = self._con.cursor()

        for k,v in tables.iteritems():
            cur.execute('create table {} ({})'.format(k,v))

        cur.execute('create index instance_index on kv (instance)')

        self._con.commit()
        cur.close()


    def get_value(self, key):
        r = self._cur.execute('SELECT value FROM kv WHERE key=?', (key,)).fetchone()
        if r:
            return r[0]

        
    def get_instance(self, key):
        r = self._cur.execute('SELECT instance FROM kv WHERE key=?', (key,)).fetchone()
        if r:
            return r[0]

        
    def update_key(self, key, value, instance_number):
        prevpn = self.get_instance(key)

        if prevpn is None:
            self._cur.execute('INSERT INTO kv VALUES (?, ?, ?)',
                              (key, value, instance_number))
            self._con.commit()
            
        elif instance_number > prevpn:
            self._cur.execute('UPDATE kv SET value=?, instance=? WHERE key=?',
                              (value, instance_number, key))
            self._con.commit()

            
    def get_last_instance(self):
        r = self._cur.execute('SELECT MAX(instance) FROM kv').fetchone()[0]

        return r if r is not None else 0

    
    def iter_updates(self, start_instance, end_instance=2**32):
        c = self._con.cursor()
        c.execute('SELECT key,value,instance FROM kv WHERE instance>=? AND instance<?  ORDER BY instance',
                  (start_instance, end_instance))
        return c



class KeyValNode (multi.MultiPaxosHeartbeatNode):
    '''
    This class implements the Paxos logic for KeyValueDB. It extends the
    base class functionality in two primary ways. First, it monitors the
    heartbeat messages for currency and uses them as a trigger for
    initiating and completing the database synchronization
    process. Second, it disables participation in the Paxos algorithm while
    during the synchronization process. This prevents newly chosen values
    from entering the database in an out-of-order manner.
    '''

    def __init__(self, kvdb, net_channel, quorum_size, durable_data_id, durable_data_store, **kwargs):
        super(KeyValNode,self).__init__( net_channel.create_subchannel('paxos'), quorum_size,
                                         durable_data_id, durable_data_store, **kwargs)
        self.kvdb = kvdb

        self.initialize()


    def receive_prepare(self, from_uid, msg):
        if msg['instance'] > self.instance:
            self.kvdb.catchup(msg['instance'])
            
        super(KeyValNode,self).receive_prepare(from_uid, msg)

        
    def receive_heartbeat(self, from_uid, kw):

        super(KeyValNode,self).receive_heartbeat(from_uid, kw)

        self.enabled = kw['instance'] == self.kvdb.last_instance + 1

        if not self.enabled:
            self.kvdb.catchup(kw['instance'])
        

    def on_resolution(self, proposal_id, tpl):
        key, value = tpl
        
        if self.instance == self.kvdb.last_instance + 1:
            self.kvdb.on_paxos_resolution( key, value, self.instance )

        super(KeyValNode,self).on_resolution(proposal_id, value)
        

        
    def on_leadership_acquired(self):
        super(KeyValNode, self).on_leadership_acquired(self)
        self.kvdb.on_leadership_acquired()

    def on_leadership_lost(self):
        super(KeyValNode, self).on_leadership_lost(self)
        self.kvdb.on_leadership_lost()



class KeyValueDB (object):
    '''
    This class implements a distributed key=value database that uses Paxos to
    coordinate database updates. Unlike the replacated state machine design
    typically discussed in Paxos literature, this implementation takes a
    simpler approach to ensure consistency. Each key/value update includes in
    the database the Multi-Paxos instance number used to set the value for that
    key.

    Nodes detect that their database is out of sync with their peers when it
    sees a heartbeat message for for a Multi-Paxos instance ahead of what it is
    expecting. When this occurs, the node suspends it's participation in the
    Paxos protocol and synchronizes it's database. This is accomplished by
    continually requesting key-value pairs with instance ids greater than what
    it has already received. These are requested in ascending order until the
    node recieves the key-value pair with an instance number that is 1 less
    than the current Multi-Paxos instance under negotiation. This indicates
    that the node has fully synchronized with it's peers and may rejoin the
    Paxos protocol.

    To support the addition and removal of nodes, the configuration for the
    paxos configuration is, itself, stored in the database. This
    automatically ensures that at least a quorum number of nodes always agree
    on what the current configuration is and, consequently, ensures that
    progress can always be made. Note, however, that if encryption is
    being used and the encryption key changes, some additional work will be
    required to enable the out-of-date nodes to catch up.

    With this implementation, queries to nodes may return data that is out of
    date. "Retrieve the most recent value" is not an operation that this
    implementation can reliably handle; it is imposible to reliably detect
    whether this node's data is consistent with it's peers at any given point
    in time. Successful handling of this operation requires either that the
    read operation flow through the Paxos algorighm itself (and in which case
    the value could be rendered out-of-date even before it is delivered to the
    client) or leadership-leases must be used. Leadership leases are relatively
    straight-forward to implement but are omitted here for the sake of
    simplicity.
    '''

    catchup_retry_delay = 2.0
    catchup_num_items   = 2
    
    def __init__(self, net_channel, quorum_size, durable_data_id, durable_data_store,
                 database_dir,
                 database_filename=None,
                 **kwargs):

        if database_filename is None:
            database_filename = os.path.join(database_dir, 'db.sqlite')

        # By default, prevent arbitrary clients from proposing new
        # configuration values
        self.allow_config_proposals = False

        self.db               = SqliteDB( database_filename )
        self.last_instance    = self.db.get_last_instance()
        self.catching_up      = False
        self.catchup_retry    = None
        self.active_instance  = None

        self.kv_node  = KeyValNode(self, net_channel, quorum_size, durable_data_id,
                                   durable_data_store, **kwargs)
        self.net      = net_channel.create_subchannel('kv')

        self.net.add_message_handler(self)

        if self.initialized:
            self._load_configuration()


    def _load_configuration(self):

        self.last_instance = self.db.get_last_instance()

        cfg = json.loads( self.db.get_value(_ZPAX_CONFIG_KEY) )

        zpax_nodes = dict()
        all_nodes  = set()

        for n in cfg['nodes']:
            zpax_nodes[ n['uid'] ] = (n['pax_rtr_addr'], n['pax_pub_addr'])
            all_nodes.add( n['uid'] )
            
        quorum_size = len(cfg['nodes'])/2 + 1

        if self.kv_node.quorum_size != quorum_size:
            self.kv_node.change_quorum_size( quorum_size )

        if not self.net.node_uid in all_nodes:
            # We've been removed from the inner circle
            self.shutdown()

        self.net.connect( zpax_nodes )


    @property
    def initialized(self):
        return self.db.get_value(_ZPAX_CONFIG_KEY) is not None


    def initialize(self, config_str):
        if self.initialized:
            raise Exception('Node already initialized')
        
        self.db.update_key(_ZPAX_CONFIG_KEY, config_str, 0)
        self._load_configuration()

                
    def shutdown(self):
        if self.catchup_retry and self.catchup_retry.active():
            self.catchup_retry.cancel()
        self.kv_node.shutdown()

            
    def on_paxos_resolution(self, key, value, instance_num):
        assert not self.catching_up
        
        self.db.update_key( key, value, instance_num )        
        self.last_instance = instance_num
        
        if key == _ZPAX_CONFIG_KEY:
            self._load_configuration()


    def on_leadership_acquired(self):
        pass

    def on_leadership_lost(self):
        pass

    def on_caughtup(self):
        pass
        

    def catchup(self, active_instance):
        self.active_instance = active_instance
        
        if self.catching_up:
            return

        self.catching_up = True

        try:
            self._catchup()
        except:
            import traceback
            traceback.print_exc()
        

    def _catchup(self):
        if self.catching_up:
            self.catchup_retry = reactor.callLater(self.catchup_retry_delay,
                                                   self._catchup)

            if self.kv_node.leader_uid is not None:
                self.net.unicast( self.kv_node.leader_uid,
                                  'catchup_request',
                                  dict(last_known_instance=self.last_instance) )
            else:
                self.net.broadcast( 'catchup_request',
                                    dict(last_known_instance=self.last_instance) )
        

    #--------------------------------------------------------------------------
    # Messaging
    #           
    def unicast(self, to_uid, message_type, **kwargs):
        self.net.unicast( to_uid, message_type, kwargs )


    def receive_catchup_request(self, from_uid, msg):
        l = list()
        
        for tpl in self.db.iter_updates(msg['last_known_instance']):
            l.append( tpl )
            if len(l) == self.catchup_num_items:
                break

        self.unicast( from_uid, 'catchup_data',
                      from_instance = msg['last_known_instance'],
                      key_val_instance_list = l )

    
    def receive_catchup_data(self, from_uid, msg):        
        if self.last_instance != msg['from_instance']:
            # This is a reply to an old request. Ignore it.
            return
            
        if self.catchup_retry and self.catchup_retry.active():
            self.catchup_retry.cancel()
            self.catchup_retry = None

        reload_config = False
        
        for key, val, instance_num in msg['key_val_instance_list']:
            self.db.update_key(key, val, instance_num)
            
            if key == _ZPAX_CONFIG_KEY:
                reload_config = True

        if reload_config:
            self._load_configuration()
                
        self.last_instance = self.db.get_last_instance()
        
        self.kv_node.next_instance( self.last_instance + 1 )
        
        self.catching_up = self.active_instance != self.last_instance + 1

        if self.catching_up:
            self._catchup()
        else:
            self.on_caughtup()

    
    def receive_propose_value(self, from_uid, msg):        
        if not self.allow_config_proposals and msg['key'] == _ZPAX_CONFIG_KEY:
            self.unicast(from_uid, 'propose_reply', request_id=msg['request_id'], error='Access Denied')
        else:
            self.kv_node.set_proposal( msg['key'], msg['value'] )
            self.unicast(from_uid, 'propose_reply', request_id=msg['request_id'])

            

            
    def receive_query_value(self, from_uid, msg):
        if not self.allow_config_proposals and msg['key'] == _ZPAX_CONFIG_KEY:
            self.unicast(from_uid, 'query_result', error='Access Denied')
        else:
            self.unicast(from_uid, 'query_result', value=self.db.get_value(msg['key']) )


########NEW FILE########
__FILENAME__ = single_value
from twisted.internet import defer, task, reactor

from zpax import multi


class SingleValueNode (multi.MultiPaxosHeartbeatNode):
    '''
    This class implements a network node that uses Paxos to coordinate changes
    to a single, shared value.
    '''
    catchup_delay = 10
    
    def __init__(self, paxos_net_channel, quorum_size, durable_data_id, durable_data_store):
        '''
        paxos_net_channel  - net.Channel instance
        quorum_size        - Paxos quorum size
        durable_data_id    - Unique ID for use with the durable_data_store
        durable_data_store - Implementer of durable.IDurableDataStore
        '''

        super(SingleValueNode,self).__init__(paxos_net_channel.create_subchannel('paxos'),
                                             quorum_size, durable_data_id, durable_data_store)

        self.catchup_channel  = paxos_net_channel.create_subchannel('catchup')
        self.client_channel   = paxos_net_channel.create_subchannel('clients')
        self.current_value    = None
        self.behind           = False
        self.catchup_cb       = None

        self.waiting_clients  = set() # Contains router addresses of clients waiting for updates

        self.catchup_channel.add_message_handler(self)
        self.client_channel.add_message_handler(self)
        
        
        
    def shutdown(self):
        if self.catchup_cb and self.catchup_cb.active():
            self.catchup_cb.cancel()
        super(SingleValueNode,self).shutdown()


    def _get_additional_persistent_state(self):
        x = dict( value = self.current_value )
        x.update( super(SingleValueNode,self)._get_additional_persistent_state() )
        return x

    
    def _recover_from_persistent_state(self, state):
        super(SingleValueNode,self)._recover_from_persistent_state(state)
        self.current_value = state.get('value', None)
        

    def behind_in_sequence(self, current_instance):
        super(SingleValueNode,self).behind_in_sequence(current_instance)
        self.behind = True
        self.catchup()


    def catchup(self):
        if self.behind:
            if self.leader_uid is not None:
                self.catchup_channel.unicast( self.leader_uid, 'get_value', dict() )
            else:
                self.catchup_channel.broadcast( 'get_value', dict() )
            self.catchup_cb = reactor.callLater(self.catchup_delay, self.catchup)

            
    def caught_up(self):
        self.behind = False
        
        if self.catchup_cb and self.catchup_cb.active():
            self.catchup_cb.cancel()
            self.catchup_cb = None


    def on_resolution(self, proposal_id, value):
        self.current_value = value
        super(SingleValueNode,self).on_resolution(proposal_id, value)
        self.caught_up()
        

    #--------------------------------------------------------------------------
    # Messaging
    #
    def receive_get_value(self, from_uid, msg):
        try:
            if not self.behind:
                self.catchup_channel.unicast( from_uid, 'current_value',
                                              dict(value=self.current_value,
                                                   current_instance=self.instance) )
        except:
            import traceback
            traceback.print_exc()
        

    def receive_current_value(self, from_uid, msg):
        self.current_value = msg['value']
        self.next_instance(msg['current_instance'])
        self.caught_up()

            
        
    def receive_propose_value(self, from_uid, msg):
        try:
            self.set_proposal(msg['request_id'],
                              msg['proposed_value'],
                              msg['instance'])
            self.client_channel.unicast( from_uid, 'proposal_result', dict() )
        except multi.ProposalFailed, e:
            self.client_channel.unicast( from_uid, 'proposal_result',
                                         dict(error_message=str(e), current_instance=e.current_instance))

            
    def receive_query_value(self, from_uid, msg):
        self.client_channel.unicast( from_uid, 'query_result',
                                    dict( current_instance=self.instance,
                                          value=self.current_value ))

        

########NEW FILE########
__FILENAME__ = test_commit
import os
import os.path
import sys
import tempfile
import shutil

pd = os.path.dirname

this_dir = pd(os.path.abspath(__file__))

sys.path.append( pd(this_dir) )
sys.path.append( os.path.join(pd(pd(this_dir)), 'zpax') )
sys.path.append( os.path.join(pd(pd(this_dir)), 'paxos') )

from twisted.internet import reactor, defer
from twisted.trial import unittest

from zpax import durable

from zpax.network import test_node
from zpax.network.test_node import gatherResults, trace_messages

from zpax.commit import TransactionManager


class TransactionTester (unittest.TestCase):

    def setUp(self):
        test_node.setup()

        self.all_nodes = set(['A', 'B', 'C'])
        self.tms       = dict()               # Node ID => TransactionManager

        self.zpax_nodes = dict() # dict of node_id => (zmq_rtr_addr, zmq_pub_addr)
                                 # we'll fake it for the test_node.NetworkNode
        
        for nid in self.all_nodes:
            self.zpax_nodes[nid] = ('foo','foo')
            
            tm = TransactionManager( test_node.Channel('test_channel', test_node.NetworkNode(nid)),    #network_channel
                                     2,                              #quorum_size,
                                     self.all_nodes,                 #all_node_ids,
                                     2,                              #threshold,
                                     durable.MemoryOnlyStateStore()) #durable

            tm.timeout_duration = 5
            tm.get_current_time = lambda : 0
            
            self.tms[ nid ] = tm

            setattr(self, nid, tm)

        for nid in self.all_nodes:
            self.tms[nid].net.connect( self.zpax_nodes )

        self.auto_flush(True)

            
    def auto_flush(self, value):
        for nid in self.all_nodes:
            getattr(self, nid).durable.auto_flush = value
            

    @defer.inlineCallbacks
    def test_simple_commit(self):
        da = self.A.propose_result('tx1', 'commit')
        db = self.B.propose_result('tx1', 'commit')

        r = yield gatherResults([da, db])

        self.assertEquals(r, [('tx1','committed'), ('tx1','committed')])


    #@trace_messages
    @defer.inlineCallbacks
    def test_simple_all_commit(self):
        da = self.A.propose_result('tx1', 'commit')
        db = self.B.propose_result('tx1', 'commit')
        dc = self.C.propose_result('tx1', 'commit')

        r = yield gatherResults([da, db, dc])

        self.assertEquals(r, [('tx1','committed'), ('tx1','committed'), ('tx1','committed')])

        
    #@trace_messages
    @defer.inlineCallbacks
    def test_simple_abort(self):
        self.A.net.link_up = False
        da = self.A.propose_result('tx1', 'commit')
        self.A.net.link_up = True
        
        self.A.heartbeat(6, True)
        
        db = self.B.propose_result('tx1', 'commit')

        dc = self.C.propose_result('tx1', 'commit')

        r = yield gatherResults([da, db, dc])

        self.assertEquals(r, [('tx1','aborted'), ('tx1','aborted'), ('tx1','aborted')])

        
    #@trace_messages
    @defer.inlineCallbacks
    def test_complex_abort(self):
        
        da = self.A.propose_result('tx1', 'commit')

        self.assertEquals( self.A.get_transaction('tx1').num_committed, 1 )
        
        self.B.net.link_up = False
        self.C.net.link_up = False
        
        db = self.B.propose_result('tx1', 'commit')
        dc = self.C.propose_result('tx1', 'commit')
        
        self.B.net.link_up = True
        self.C.net.link_up = True
        
        self.A.heartbeat(6, True)
        
        r = yield gatherResults([da, db, dc])

        self.assertEquals(r, [('tx1','aborted'), ('tx1','aborted'), ('tx1','aborted')])

        

        
        
    

########NEW FILE########
__FILENAME__ = test_encoders
import os
import os.path
import sys

from twisted.internet import reactor, defer
from twisted.trial import unittest


pd = os.path.dirname

this_dir = pd(os.path.abspath(__file__))

sys.path.append( pd(this_dir) )


from zpax.network import json_encoder

class JSONEncoderTester(unittest.TestCase):

    def test_json_encoder(self):
        e = json_encoder.JSONEncoder()

        orig = [ dict(foo='bar'), 'baz', 1 ]

        enc = e.encode( 'william', 'wallace', orig )

        from_uid, msg_type, dec = e.decode(enc)

        self.assertEquals( from_uid, 'william' )
        self.assertEquals( msg_type, 'wallace' )
        self.assertEquals( dec, orig )

########NEW FILE########
__FILENAME__ = test_key_value
import os
import os.path
import sys
import random
import json
import tempfile
import shutil

from twisted.internet import reactor, defer
from twisted.trial import unittest

pd = os.path.dirname

this_dir = pd(os.path.abspath(__file__))

sys.path.append( pd(this_dir) )
sys.path.append( os.path.join(pd(this_dir), 'examples') )
sys.path.append( os.path.join(pd(pd(this_dir)), 'paxos') )

from zpax import durable

from zpax.network import test_node
from zpax.network.test_node import trace_messages, show_stacktrace

import key_value


def delay(t):
    d = defer.Deferred()
    reactor.callLater(t, lambda : d.callback(None) )
    return d



class TestReq (object):
    d = None
    last_val = None

    def __init__(self, channel='test_channel.kv', node_id='client'):
        self.net = test_node.NetworkNode(node_id)
        self.channel = channel
        self.net.add_message_handler(channel, self)
        self.net.connect([])

    def close(self):
        if self.d is not None and not self.d.called:
            self.d.cancel()
    
    def propose(self, to_id, key, value, req_id='req_id'):
        self.d = defer.Deferred()
        self.net.unicast_message(to_id, self.channel, 'propose_value', dict(key=key, value=value, request_id=req_id))
        return self.d

    def query(self, to_id, key, req_id='req_id'):
        self.d = defer.Deferred()
        self.net.unicast_message(to_id, self.channel, 'query_value', dict(key=key, request_id=req_id))
        return self.d

    def receive_propose_reply(self, from_uid, msg):
        #print 'Propose Reply Received:', msg
        self.d.callback(msg)

    def receive_query_result(self, from_uid, msg):
        #print 'Query Result Received:', msg
        self.d.callback(msg)
        




class KeyValueDBTester(unittest.TestCase):

    durable_key = 'durable_id_{0}'

    def setUp(self):
        tmpfs_dir = '/dev/shm' if os.path.exists('/dev/shm') else None
        
        self.tdir        = tempfile.mkdtemp(dir=tmpfs_dir)
        self.nodes       = dict()
        self.leader      = None
        self.dleader     = defer.Deferred()
        self.dlost       = None
        self.clients     = list()
        self.all_nodes   = 'a b c'.split()

        self.dd_store = durable.MemoryOnlyStateStore()

        test_node.setup()

        
    @property
    def json_config(self):
        nodes = list()
        
        for uid in self.all_nodes:
            pax_rtr = 'ipc:///tmp/ts_{}_pax_rtr'.format(uid)
            pax_pub = 'ipc:///tmp/ts_{}_pax_pub'.format(uid)
            kv_rep  = 'ipc:///tmp/ts_{}_kv_rep'.format(uid)
            nodes.append( dict(uid          = uid,
                               pax_pub_addr = pax_pub,
                               pax_rtr_addr = pax_rtr,
                               kv_rep_addr  = kv_rep) )
            
        return json.dumps( dict( nodes = nodes ) )
            
        
    def tearDown(self):
        for c in self.clients:
            c.close()
            
        for n in self.all_nodes:
            self.stop(n)

        shutil.rmtree(self.tdir)
        
        # In ZeroMQ 2.1.11 there is a race condition for socket deletion
        # and recreation that can render sockets unusable. We insert
        # a short delay here to prevent the condition from occuring.
        #return delay(0.05)


    def new_client(self):
        zreq = TestReq()
        self.clients.append(zreq)
        return zreq
            

    def start(self,  node_names, caughtup=None):

        def gen_cb(x, func):
            def cb():
                func(x)
            return cb

        zpax_nodes = dict()
        
        for node_name in node_names.split():
            if not node_name in self.all_nodes or node_name in self.nodes:
                continue

            n = key_value.KeyValueDB(test_node.Channel('test_channel', test_node.NetworkNode(node_name)),
                                  2,
                                  self.durable_key.format(node_name),
                                  self.dd_store,
                                  self.tdir, os.path.join(self.tdir, node_name + '.sqlite'),
                                  hb_period = 0.05,
                                  liveness_window = 0.15)

            n.allow_config_proposals = True

            n.kv_node.on_leadership_acquired = gen_cb(node_name, self._on_leader_acq)
            n.kv_node.on_leadership_lost     = gen_cb(node_name, self._on_leader_lost)

            n.kv_node.hb_period       = 0.05
            n.kv_node.liveness_window = 0.15

            n.name = node_name

            if caughtup:
                n.on_caughtup = caughtup
            
            self.nodes[node_name] = n

            if not n.initialized:
                n.initialize( self.json_config )


        
    def stop(self, node_names):
        for node_name in node_names.split():
            if node_name in self.nodes:
                self.nodes[node_name].shutdown()
                del self.nodes[node_name]


    def _on_leader_acq(self, node_id):
        prev        = self.leader
        self.leader = node_id
        if self.dleader:
            d, self.dleader = self.dleader, None
            reactor.callLater(0.01, lambda : d.callback( (prev, self.leader) ))

            
    def _on_leader_lost(self, node_id):
        if self.dlost:
            d, self.dlost = self.dlost, None
            d.callback(node_id)

    @defer.inlineCallbacks
    def set_key(self, client, to_id, key, value):
        
        v = None
        while v != value:
            yield client.propose(to_id, key,value)
            yield delay(0.01)
            r = yield client.query(to_id, key)
            v = r['value']
            #print 'set_key', key, value, v, v != value



    def get_key(self, to_id, client, key):
        d = client.query(to_id, key)
        d.addCallback( lambda r : r['value'] )
        return d

    def wait_for_key_equals(self, client, to_id, key, value):
        keyval = None
        while keyval != value:
            yield delay(0.05)
            r = yield client.query(to_id, key)
            keyval = r['value']
    

    #@trace_messages
    @defer.inlineCallbacks
    def test_initial_leader(self):
        self.start('a b')
        yield self.dleader


    #@trace_messages
    @defer.inlineCallbacks
    def test_set_key_val_pair(self):
        self.start('a b')

        d = defer.Deferred()
        c = self.new_client()

        yield self.dleader
        
        yield c.propose('a', 'foo', 'bar')

        keyval = None
        while keyval != 'bar':
            yield delay(0.05)
            r = yield c.query('a', 'foo')
            keyval = r['value']


    @defer.inlineCallbacks
    def test_set_keys(self):
        self.start('a b')

        d = defer.Deferred()
        c = self.new_client()

        yield self.dleader

        yield self.set_key(c, 'a', 'foo0', 'bar')
        yield self.set_key(c, 'a', 'foo1', 'bar')
        yield self.set_key(c, 'a', 'foo2', 'bar')
        yield self.set_key(c, 'a', 'foo3', 'bar')
        yield self.set_key(c, 'a', 'foo4', 'bar')
        yield self.set_key(c, 'a', 'foo5', 'bar')
        yield self.set_key(c, 'a', 'foo6', 'bar')
        yield self.set_key(c, 'a', 'foo7', 'bar')
        yield self.set_key(c, 'a', 'foo8', 'bar')
        yield self.set_key(c, 'a', 'foo9', 'bar')

        yield self.set_key(c, 'a', 'foo0', 'baz')
        yield self.set_key(c, 'a', 'foo1', 'baz')
        yield self.set_key(c, 'a', 'foo2', 'baz')
        yield self.set_key(c, 'a', 'foo3', 'baz')
        yield self.set_key(c, 'a', 'foo4', 'baz')
        yield self.set_key(c, 'a', 'foo5', 'baz')
        yield self.set_key(c, 'a', 'foo6', 'baz')
        yield self.set_key(c, 'a', 'foo7', 'baz')
        yield self.set_key(c, 'a', 'foo8', 'baz')
        yield self.set_key(c, 'a', 'foo9', 'baz')


    @show_stacktrace
    #    @trace_messages
    @defer.inlineCallbacks
    def test_shutdown_and_restart(self):
        self.start('a b')

        d = defer.Deferred()
        c = self.new_client()

        yield self.dleader
        
        yield self.set_key(c, 'a', 'foo0', 'bar')
        yield self.set_key(c, 'a', 'foo1', 'bar')

        self.stop('a b')

        yield delay(0.05)

        self.dleader = defer.Deferred()

        self.start('a b')

        yield self.dleader

        v = yield self.get_key('a', c, 'foo0')

        self.assertEquals(v, 'bar')

        yield self.set_key(c, 'a', 'foo1', 'baz')



    #@trace_messages
    @defer.inlineCallbacks
    def test_shutdown_and_restart_with_outstanding_proposal(self):
        self.start('a b')

        d = defer.Deferred()
        c = self.new_client()

        yield self.dleader
        
        yield self.set_key(c, 'a', 'foo0', 'bar')

        self.stop('b')

        yield c.propose('a', 'foo1', 'bar')

        self.assertTrue( self.nodes['a'].kv_node.pax.proposed_value is not None )

        self.stop('a')

        yield delay(0.05)

        self.dleader = defer.Deferred()
        
        self.start('a b')

        yield self.dleader
        
        v = None
        while v != 'bar':
            v = yield self.get_key('a', c, 'foo1')
            yield delay(0.01)

        self.assertEquals(v, 'bar')

            
        
    @defer.inlineCallbacks
    def test_dynamic_add_node(self, chatty=False):

        self.start('a c')

        d = defer.Deferred()
        c = self.new_client()

        yield self.dleader

        yield self.set_key(c, 'a', 'foo', 'bar')
        
        # Add a node to config
        self.all_nodes.append('d')

        #print '*'*30

        self.assertEquals(self.nodes['a'].kv_node.quorum_size, 2)
        
        yield self.set_key(c, 'a', key_value._ZPAX_CONFIG_KEY, self.json_config)

        # Quorum is now 3. No changes can be made until 3 functioning nodes
        # are up. Start the newly added node to reach a total of three then
        # set a key


        self.assertEquals(self.nodes['a'].kv_node.quorum_size, 3)
        
        dcaughtup = defer.Deferred()

        self.start('d', caughtup = lambda : dcaughtup.callback(None))

        yield dcaughtup

        # Trying to set key with quorum 3
        yield self.set_key(c, 'a', 'test_key', 'foo')
        yield self.set_key(c, 'a', 'test_key2', 'foo')
        defer.returnValue(c)
        

    @defer.inlineCallbacks
    def test_dynamic_remove_node(self):
        
        c = yield self.test_dynamic_add_node()

        self.assertEquals(self.nodes['a'].kv_node.quorum_size, 3)

        self.all_nodes.remove('c')

        yield self.set_key(c, 'a', 'test_key3', 'foo')
        
        yield self.set_key(c, 'a', key_value._ZPAX_CONFIG_KEY, self.json_config)

        self.stop('c')

        self.assertEquals(self.nodes['a'].kv_node.quorum_size, 2)
        
        yield self.set_key(c, 'a', 'test_remove', 'foo')


        

    @defer.inlineCallbacks
    def test_node_recovery(self):
        self.start('a b c')

        d = defer.Deferred()
        c = self.new_client()

        yield self.dleader

        yield self.set_key(c, 'a', 'foo', 'bar')

        self.stop('c')
    
        yield self.set_key(c, 'a', 'baz', 'bish')
        yield self.set_key(c, 'a', 'william', 'wallace')

        dcaughtup = defer.Deferred()
        
        self.start('c', caughtup = lambda : dcaughtup.callback(None))

        yield dcaughtup

        c2 = self.new_client()

        r = yield c2.query('c', 'william')
        self.assertEquals(r['value'], 'wallace')
            





class SqliteDBTest(unittest.TestCase):

    def setUp(self):
        self.db = key_value.SqliteDB(':memory:')

    def test_update_missing_value(self):
        self.assertTrue(self.db.get_value('foo') is None)
        self.db.update_key('foo', 'bar', 5)
        self.assertEquals(self.db.get_value('foo'), 'bar')

    def test_update_new_value(self):
        self.assertTrue(self.db.get_value('foo') is None)
        self.db.update_key('foo', 'bar', 5)
        self.assertEquals(self.db.get_value('foo'), 'bar')
        self.db.update_key('foo', 'bish', 6)
        self.assertEquals(self.db.get_value('foo'), 'bish')

    def test_update_ignore_previous_resolution(self):
        self.assertTrue(self.db.get_value('foo') is None)
        self.db.update_key('foo', 'bar', 5)
        self.assertEquals(self.db.get_value('foo'), 'bar')
        self.db.update_key('foo', 'baz', 4)
        self.assertEquals(self.db.get_value('foo'), 'bar')

    def test_iter_updates_empty(self):
        l = [ x for x in self.db.iter_updates(100,200) ]
        self.assertEquals(l, [])

    def test_iter_updates_middle(self):
        for x in range(0,10):
            self.db.update_key(str(x), str(x), x)
        l = [ x for x in self.db.iter_updates(2,6) ]
        self.assertEquals(l, [(str(x),str(x),x) for x in range(2,6)])

    def test_iter_updates_ends(self):
        for x in range(0,10):
            self.db.update_key(str(x), str(x), x)
        l = [ x for x in self.db.iter_updates(0,10) ]
        self.assertEquals(l, [(str(x),str(x),x) for x in range(0,10)])

    def test_iter_updates_random_shuffle(self):
        rng = range(0,100)
        random.shuffle(rng)
        for x in rng:
            self.db.update_key(str(x), str(x), x)
        l = [ x for x in self.db.iter_updates(0,100) ]
        self.assertEquals(l, [(str(x),str(x),x) for x in range(0,100)])
        

########NEW FILE########
__FILENAME__ = test_multi
import os
import os.path
import sys
import pickle

from twisted.internet import reactor, defer
from twisted.trial import unittest


pd = os.path.dirname

this_dir = pd(os.path.abspath(__file__))

sys.path.append( pd(this_dir) )
sys.path.append( os.path.join(pd(pd(this_dir)), 'paxos') )


from zpax import multi, durable
from zpax.network import test_node

from zpax.network.test_node import gatherResults, trace_messages, show_stacktrace


def delay(t):
    d = defer.Deferred()
    reactor.callLater(t, lambda : d.callback(None) )
    return d

    
all_nodes = 'A B C'.split()

    

class HBTestNode(multi.MultiPaxosHeartbeatNode):

    def __init__(self, *args, **kwargs):
        super(HBTestNode,self).__init__(*args, **kwargs)

        self.dleader_acq = defer.Deferred()
        self.dresolution = defer.Deferred()

    def __getstate__(self):
        d = super(HBTestNode,self).__getstate__()
        d.pop('dleader_acq')
        d.pop('dresolution')
        return d

    def __setstate__(self, d):
        self.__dict__ = d
        self.dleader_acq = defer.Deferred()
        self.dresolution = defer.Deferred()


    def on_leadership_acquired(self, *args):
        if test_node.TRACE:
            print self.node_uid, 'Leadership Acquired'
        super(HBTestNode,self).on_leadership_acquired(*args)

        self.dleader_acq.callback(None)


    def on_leadership_lost(self, *args):
        if test_node.TRACE:
            print self.node_uid, 'Leadership Lost'
        self.dleader_acq = defer.Deferred()
        super(HBTestNode,self).on_leadership_lost(*args)

    def on_resolution(self, proposal_id, value):
        if test_node.TRACE:
            print self.node_uid, 'Resolution:', proposal_id, value
        #print 'RESOLUTION: ', proposal_id, value
        d = self.dresolution
        self.dresolution = defer.Deferred()
        super(HBTestNode,self).on_resolution(proposal_id, value)
        d.callback((proposal_id, value))


class MultiTesterBase(object):

    @defer.inlineCallbacks
    def setUp(self):
        
        self.nodes = dict()
        
        yield self._setup()

        for name, mn in self.nodes.iteritems():
            setattr(self, name, mn)

    
    def tearDown(self):
        for n in self.nodes.itervalues():
            n.shutdown()

        return self._teardown()

    def _setup(self):
        pass

    def _teardown(self):
        pass


    #    @trace_messages
    @defer.inlineCallbacks
    def test_initial_leadership_acquisition(self):
        self.A.pax.acquire_leadership()
        yield self.A.dleader_acq

    #@trace_messages
    @show_stacktrace
    @defer.inlineCallbacks
    def test_leadership_recovery_on_failure(self):
        self.A.pax.acquire_leadership()
        yield self.A.dleader_acq

        d = defer.Deferred()

        self.B.dleader_acq.addCallback( d.callback )
        self.C.dleader_acq.addCallback( d.callback )
        
        self.A.net.link_up = False

        yield d

        self.assertTrue(self.A.pax.leader)
        
        self.A.net.link_up = True

        yield delay(0.06)

        self.assertTrue(not self.A.pax.leader)


    # Durability tests:
    #  use pickle directly to load/restore from strings
    #  test in various circumstances

        
    @defer.inlineCallbacks
    def test_leader_resolution(self):
        self.A.pax.acquire_leadership()
        yield self.A.dleader_acq

        d = gatherResults( [self.A.dresolution,
                            self.B.dresolution,
                            self.C.dresolution] )
        
        self.A.set_proposal( 'reqid', 'foobar' )

        r = yield d

        self.assertEquals(r, [((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar'))] )

        #@trace_messages
    @defer.inlineCallbacks
    def test_accept_nack(self):
        self.A.pax.acquire_leadership()
        
        yield self.A.dleader_acq

        d = gatherResults( [self.A.dresolution,
                            self.B.dresolution,
                            self.C.dresolution] )

        self.A.net.link_up = False
        
        self.A.set_proposal( 'reqid', 'foobar' )

        self.assertEquals( self.A.pax.next_proposal_number, 2 )
        self.assertTrue( self.A.pax.leader )

        self.A.receive_accept_nack( 'B', dict(proposal_id=self.A.pax.proposal_id,
                                              instance=1,
                                              promised_id=(2, 'B')))
        self.A.receive_accept_nack( 'C', dict(proposal_id=self.A.pax.proposal_id,
                                              instance=1,
                                              promised_id=(2, 'B')))

        self.assertEquals( self.A.pax.next_proposal_number, 3 )
        self.assertTrue( not self.A.pax.leader )

        
    @defer.inlineCallbacks
    def test_non_leader_resolution(self):
        self.A.pax.acquire_leadership()
        yield self.A.dleader_acq

        d = gatherResults( [self.A.dresolution,
                            self.B.dresolution,
                            self.C.dresolution] )
        
        
        self.B.set_proposal( 'reqid', 'foobar' )

        r = yield d

        self.assertEquals(r, [((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar'))] )


        #@trace_messages
    @defer.inlineCallbacks
    def test_proposal_advocate_retry(self):
        self.A.pax.acquire_leadership()
        yield self.A.dleader_acq

        d = gatherResults( [self.A.dresolution,
                            self.B.dresolution,
                            self.C.dresolution] )

        self.B.net.link_up = False
        
        self.B.advocate.retry_delay = 0.01
        
        self.B.set_proposal( 'reqid', 'foobar' )

        yield delay( 0.03 )

        self.assertTrue( not self.A.dresolution.called )

        self.B.net.link_up = True

        r = yield d

        self.assertEquals(r, [((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar'))] )


    #@trace_messages
    @defer.inlineCallbacks
    def test_proposal_advocate_retry_with_crash_recovery(self):
        self.A.pax.acquire_leadership()
        
        yield self.A.dleader_acq

        self.B.net.link_up = False
        
        self.B.advocate.retry_delay = 0.01
        
        self.B.set_proposal( 'reqid', 'foobar' )

        self.B.persist()

        yield delay( 0.03 )

        self.assertTrue( not self.A.dresolution.called )
        
        self.fail_node( 'B' )
        yield self.recover_node( 'B' )

        d = gatherResults( [self.A.dresolution,
                            self.B.dresolution,
                            self.C.dresolution] )

        r = yield d

        self.assertEquals(r, [((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar'))] )

    
    @defer.inlineCallbacks
    def test_resolution_with_leadership_failure_and_isolated_node(self):
        self.A.pax.acquire_leadership()
        yield self.A.dleader_acq

        d = gatherResults( [self.B.dresolution,
                            self.C.dresolution] )
                           
        self.A.net.link_up = False
        self.B.net.link_up = False
        
        self.B.advocate.retry_delay = 0.01
        
        self.B.set_proposal( 'reqid', 'foobar' )
        
        yield delay( 0.05 )

        self.assertTrue( not self.A.dresolution.called )

        self.B.net.link_up = True

        r = yield d

        self.assertTrue(r in ( [((1, 'B'), ('reqid', 'foobar')),
                                ((1, 'B'), ('reqid', 'foobar'))],
                               [((1, 'C'), ('reqid', 'foobar')),
                                ((1, 'C'), ('reqid', 'foobar'))]) )


    @defer.inlineCallbacks
    def test_multiple_instances(self):
        self.A.pax.acquire_leadership()
        yield self.A.dleader_acq

        self.assertEquals( self.A.instance, 1 )

        d = gatherResults( [self.A.dresolution,
                            self.B.dresolution,
                            self.C.dresolution] )
                            
        
        self.A.set_proposal( 'reqid', 'foobar' )

        r = yield d

        self.assertEquals(r, [((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar'))] )

        self.assertEquals( self.A.instance, 2 )

        d = gatherResults( [self.A.dresolution,
                            self.B.dresolution,
                            self.C.dresolution] )
                            
        
        self.A.set_proposal( 'reqid', 'baz' )

        r = yield d

        self.assertEquals(r, [((1, 'A'), ('reqid', 'baz')),
                              ((1, 'A'), ('reqid', 'baz')),
                              ((1, 'A'), ('reqid', 'baz'))] )

        self.assertEquals( self.A.instance, 3 )


    @defer.inlineCallbacks
    def test_multiple_instances_with_crash_recovery(self):
        self.A.pax.acquire_leadership()
        
        yield self.A.dleader_acq

        self.assertEquals( self.A.instance, 1 )

        d = gatherResults( [self.A.dresolution,
                            self.B.dresolution,
                            self.C.dresolution] )
                            
        
        self.A.set_proposal( 'reqid', 'foobar' )

        r = yield d

        self.assertEquals(r, [((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar'))] )


        self.assertEquals( self.A.instance, 2 )
        
        for uid in 'ABC':
            self.fail_and_recover(uid, False)

        self.A.net.link_up = True
        self.B.net.link_up = True
        self.C.net.link_up = True

        #------------------------------------------------
        # Recovery will return to the previous instance. We'll
        # need to re-resolve the same result.
        #
        self.assertEquals( self.A.instance, 1 )

        d = gatherResults( [self.A.dresolution,
                            self.B.dresolution,
                            self.C.dresolution] )
                            

        r = yield d

        self.assertEquals(r, [((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar'))] )

        #------------------------------------------------
        # Back to instance 2
        #
        self.assertEquals( self.A.instance, 2 )

        d = gatherResults( [self.A.dresolution,
                            self.B.dresolution,
                            self.C.dresolution] )
        
        self.A.set_proposal( 'reqid', 'baz' )

        r = yield d

        self.assertEquals(r, [((1, 'A'), ('reqid', 'baz')),
                              ((1, 'A'), ('reqid', 'baz')),
                              ((1, 'A'), ('reqid', 'baz'))] )

        self.assertEquals( self.A.instance, 3 )


    @defer.inlineCallbacks
    def test_behind_in_sequence(self):
        self.A.pax.acquire_leadership()
        yield self.A.dleader_acq

        self.assertEquals( self.A.instance, 1 )

        self.B.net.link_up = False

        d = gatherResults( [self.A.dresolution,
                            self.C.dresolution] )
                            
        
        self.A.set_proposal( 'reqid', 'foobar' )

        r = yield d
        

        self.assertEquals(r, [((1, 'A'), ('reqid', 'foobar')),
                              ((1, 'A'), ('reqid', 'foobar'))] )

        self.assertEquals( self.A.instance, 2 )
        self.assertEquals( self.B.instance, 1 )
        
        self.B.net.link_up = True

        yield delay(0.05)

        d = gatherResults( [self.A.dresolution,
                            self.B.dresolution,
                            self.C.dresolution] )
                            
        
        self.A.set_proposal( 'reqid', 'baz' )
        
        r = yield d

        self.assertEquals(r, [((1, 'A'), ('reqid', 'baz')),
                              ((1, 'A'), ('reqid', 'baz')),
                              ((1, 'A'), ('reqid', 'baz'))] )

        self.assertEquals( self.A.instance, 3 )
        self.assertEquals( self.B.instance, 3 )
        




class HeartbeatTester(MultiTesterBase, unittest.TestCase):

    durable_key = 'durable_id_{0}'

    @defer.inlineCallbacks
    def _setup(self):

        test_node.setup()

        self.dd_store = durable.MemoryOnlyStateStore()

        self.zpax_nodes = dict()
        
        for uid in all_nodes:

            self.nodes[uid] =  HBTestNode( test_node.Channel('test_channel', test_node.NetworkNode(uid)),
                                           2,
                                           self.durable_key.format(uid),
                                           self.dd_store,
                                           hb_period       = 0.01,
                                           liveness_window = 0.03 )

            yield self.nodes[uid].initialize()
            
            self.zpax_nodes[uid] = ('foo','foo')

        for uid in all_nodes:
            self.nodes[uid].net.connect( self.zpax_nodes )
            
        self.nodes['A'].pax._tlast_hb   = 0
        self.nodes['A'].pax._tlast_prep = 0


    def fail_node(self, node_uid):
        self.nodes[ node_uid ].shutdown()
        del self.nodes[ node_uid ]


    @defer.inlineCallbacks
    def recover_node(self, node_uid, link_up = True):
        n = HBTestNode( test_node.Channel('test_channel', test_node.NetworkNode(node_uid)),
                        2,
                        self.durable_key.format(node_uid),
                        self.dd_store,
                        hb_period       = 0.01,
                        liveness_window = 0.03 )
        
        self.nodes[node_uid] = n

        n.advocate.retry_delay = 0.01

        yield n.initialize()
            
        n.net.connect( self.zpax_nodes )
        n.net.link_up = link_up

        setattr(self, node_uid, n)

        
    @defer.inlineCallbacks
    def fail_and_recover(self, node_uid, link_up = True):
        self.fail_node( node_uid )
        yield self.recover_node( node_uid, link_up )

########NEW FILE########
__FILENAME__ = test_network
import os
import os.path
import sys

from twisted.internet import reactor, defer
from twisted.trial import unittest


pd = os.path.dirname

this_dir = pd(os.path.abspath(__file__))

sys.path.append( pd(this_dir) )


from zpax.network import zmq_node, test_node


def delay(t):
    d = defer.Deferred()
    reactor.callLater(t, lambda : d.callback(None) )
    return d

    
all_nodes = 'A B C'.split()


class NetworkNodeTesterBase(object):

    NodeKlass  = None
    need_delay = False

    def setUp(self):
        self._pre_setup()
        
        self.nodes = dict()
        
        for node_uid in all_nodes:
            self.nodes[ node_uid ] = self.NodeKlass( node_uid )

        return self._setup()

    
    def tearDown(self):
        for n in self.nodes.itervalues():
            n.shutdown()

        return self._teardown()


    def _pre_setup(self):
        pass
    
    def _setup(self):
        pass

    def _teardown(self):
        pass


    def delay(self, t):
        if self.need_delay:
            return delay(t)
        else:
            return defer.succeed(None)

        
    def connect(self, recv_self=True):
        zpax_nodes = dict()
        
        for node_uid in all_nodes:
            zpax_nodes[ node_uid ] = ('ipc:///tmp/ts_{}_rtr'.format(node_uid),
                                      'ipc:///tmp/ts_{}_pub'.format(node_uid))
            
        for n in self.nodes.itervalues():
            n.connect( zpax_nodes )

            
    @defer.inlineCallbacks
    def test_unicast_connections(self):
        self.connect()
        
        yield self.delay(1) # wait for connections to establish

        msgs = dict()

        class H(object):
            def __init__(self, nid):
                self.nid = nid

            def receive_foomsg(self, from_uid, arg):
                msgs[ self.nid ].append( (from_uid, arg) )

        for n in all_nodes:
            msgs[ n ] = list()
            self.nodes[n].add_message_handler('test_channel', H(n))
            
        def s(src, dst, msg):
            self.nodes[src].unicast_message(dst, 'test_channel', 'foomsg', msg)

        s('A', 'B', 'AB')
        s('A', 'C', 'AC')
        s('B', 'A', 'BA')
        s('B', 'C', 'BC')
        s('C', 'A', 'AC')
        s('C', 'B', 'CB')

        yield self.delay(0.05) # process messages

        for l in msgs.itervalues():
            l.sort()

        expected = {'A': [('B', 'BA'), ('C', 'AC')],
                    'B': [('A', 'AB'), ('C', 'CB')],
                    'C': [('A', 'AC'), ('B', 'BC')]}

        self.assertEquals( msgs, expected )


    @defer.inlineCallbacks
    def test_multiple_arguments(self):
        self.connect()
        
        yield self.delay(1) # wait for connections to establish

        msgs = dict()

        class H(object):
            def __init__(self, nid):
                self.nid = nid

            def receive_foomsg(self, from_uid, arg0, arg1, arg2):
                msgs[ self.nid ].append( (from_uid, arg0, arg1, arg2) )

        for n in all_nodes:
            msgs[ n ] = list()
            self.nodes[n].add_message_handler('test_channel', H(n))
            
        def s(src, dst, msg0, msg1, msg2):
            self.nodes[src].unicast_message(dst, 'test_channel', 'foomsg', msg0, msg1, msg2)

        s('A', 'B', 'AB', 'foo', 'bar')

        yield self.delay(0.05) # process messages

        for l in msgs.itervalues():
            l.sort()

        expected = {'A': [],
                    'B': [('A', 'AB', 'foo', 'bar')],
                    'C': [] }

        self.assertEquals( msgs, expected )

        

        
    @defer.inlineCallbacks
    def test_broadcast_connections_recv(self):
        self.connect()
        
        yield self.delay(1) # wait for connections to establish

        msgs = dict()

        class H(object):
            def __init__(self, nid):
                self.nid = nid

            def receive_foomsg(self, from_uid, arg):
                msgs[ self.nid ].append( (from_uid, arg) )

        for n in all_nodes:
            msgs[ n ] = list()
            self.nodes[n].add_message_handler('test_channel', H(n))
            
        def s(src, msg):
            self.nodes[src].broadcast_message('test_channel', 'foomsg', msg)

        s('A', 'msgA')
        s('B', 'msgB')
        s('C', 'msgC')

        yield self.delay(0.05) # process messages

        for l in msgs.itervalues():
            l.sort()

        expected = {'A': [('A', 'msgA'), ('B', 'msgB'), ('C', 'msgC')],
                    'B': [('A', 'msgA'), ('B', 'msgB'), ('C', 'msgC')],
                    'C': [('A', 'msgA'), ('B', 'msgB'), ('C', 'msgC')]}


        self.assertEquals( msgs, expected )


    @defer.inlineCallbacks
    def test_multiple_handlers(self):
        self.connect()
        
        yield self.delay(1) # wait for connections to establish

        msgs = dict()

        class H(object):
            def __init__(self, nid):
                self.nid = nid

            def receive_foomsg(self, from_uid, arg):
                msgs[ self.nid ].append( (from_uid, arg) )

        for n in all_nodes:
            msgs[ n ] = list()
            self.nodes[n].add_message_handler('test_channel', H(n))


        class H2(object):
            def receive_special(self, from_uid, arg):
                msgs['C'].append( (from_uid, 'special', arg) )

        self.nodes['C'].add_message_handler( 'test_channel', H2() )
            
        def s(src, msg):
            self.nodes[src].broadcast_message('test_channel', 'foomsg', msg)

        s('A', 'msgA')
        s('B', 'msgB')
        s('C', 'msgC')

        self.nodes['A'].broadcast_message('test_channel', 'special', 'blah')

        yield self.delay(0.05) # process messages

        for l in msgs.itervalues():
            l.sort()

        expected = {'A': [('A', 'msgA'), ('B', 'msgB'), ('C', 'msgC')],
                    'B': [('A', 'msgA'), ('B', 'msgB'), ('C', 'msgC')],
                    'C': [('A', 'msgA'), ('A', 'special', 'blah'), ('B', 'msgB'), ('C', 'msgC')]}


        self.assertEquals( msgs, expected )



class ZeroMQNodeTester(NetworkNodeTesterBase, unittest.TestCase):

    NodeKlass  = zmq_node.NetworkNode
    need_delay = True

    def _teardown(self):
        # In ZeroMQ 2.1.11 there is a race condition for socket deletion
        # and recreation that can render sockets unusable. We insert
        # a short delay here to prevent the condition from occuring.
        return delay(0.05)
    
    

class TestNodeTester(NetworkNodeTesterBase, unittest.TestCase):
    
    NodeKlass      = test_node.NetworkNode

    def _pre_setup(self):
        test_node.setup()

########NEW FILE########
__FILENAME__ = test_pub_sub
import os
import os.path
import sys
import json

import random

pd = os.path.dirname

this_dir = pd(os.path.abspath(__file__))

sys.path.append( pd(this_dir) )
sys.path.append( os.path.join(pd(pd(this_dir)), 'paxos') )


from zpax.network import zed

from twisted.internet import reactor, defer
from twisted.trial import unittest


def delay(tsec):
    d = defer.Deferred()
    reactor.callLater(tsec, lambda : d.callback(None))
    return d

        
class PS (object):

    def __init__(self, name, pub_addr, sub_addrs):
        self.name = name
        self.pub  = zed.ZmqPubSocket()
        self.sub  = zed.ZmqSubSocket()

        self.pub.bind( pub_addr )
        for a in sub_addrs:
            self.sub.connect(a)

        def on_recv( parts ):
            self.jrecv( [ json.loads(p) for p in parts[1:] ] )

        self.sub.subscribe       = 'test_zmq'
        self.sub.messageReceived = on_recv

    def close(self):
        self.pub.close()
        self.sub.close()

    def jsend(self, **kwargs):
        kwargs.update( dict(name=self.name) )
        self.pub.send( ['test_zmq', json.dumps(kwargs) ] )

    def jrecv(self, jparts):
        pass

    

    
class SimpleTest(unittest.TestCase):

    def setUp(self):
        self.sockets = dict()
        
    def tearDown(self):
        for s in self.sockets.itervalues():
            s.close()

        return delay(0.05)
            

    def start(self, snames):

        l    = list()
        pubs = [ 'ipc:///tmp/tzmq_{0}_pub'.format(n) for n in snames.split() ]
        
        for sname in snames.split():
            s = PS(sname, 'ipc:///tmp/tzmq_{0}_pub'.format(sname), pubs)
            self.sockets[sname] = s
            l.append(s)

        return l
    
    def stop(self, sock_name):
        self.socket[sock_name].shutdown()
        del self.nodes[node_name]

    def test_connectivity(self):
        a, b, c = self.start('a b c')

        all_set = set('a b c'.split())

        def setup(s):
            s.d = defer.Deferred()
            s.r = set()
            
            def jrecv(parts):
                #print 'Recv', s.name, parts[0]['name'], '    ', s.r, s.sub.fd
                s.r.add( parts[0]['name'] )
                if s.r == all_set:
                    #print 'DONE: ', s.name
                    if not s.d.called:
                        s.d.callback(None)

            s.jrecv = jrecv

            def send():
                #print 'Send', s.name
                s.jsend(foo='bar')
                s.t = reactor.callLater(0.5, send)

            send()

        for x in (a, b, c):
            setup(x)

            
        d = defer.DeferredList([a.d, b.d, c.d])

        def done(_):
            for s in self.sockets.itervalues():
                if s.t.active():
                    s.t.cancel()
                    
        d.addCallback(done)
        
        return d



########NEW FILE########
__FILENAME__ = test_single_value
import os
import os.path
import sys
import random
import json
import tempfile
import shutil

from twisted.internet import reactor, defer
from twisted.trial import unittest

pd = os.path.dirname

this_dir = pd(os.path.abspath(__file__))

sys.path.append( pd(this_dir) )
sys.path.append( os.path.join(pd(this_dir), 'examples') )
sys.path.append( os.path.join(pd(pd(this_dir)), 'paxos') )

from zpax import durable

from zpax.network import test_node
from zpax.network.test_node import trace_messages, show_stacktrace

import single_value


def delay(t):
    d = defer.Deferred()
    reactor.callLater(t, lambda : d.callback(None) )
    return d



class TestReq (object):
    d = None
    last_val = None

    def __init__(self, channel='test_channel.clients', node_id='testcli'):
        self.net = test_node.NetworkNode(node_id)
        self.channel = channel
        self.net.add_message_handler(channel, self)
        self.net.connect([])

    def close(self):
        if self.d is not None and not self.d.called:
            self.d.cancel()
    
    def propose(self, to_id, instance, value, req_id='req_id'):
        self.d = defer.Deferred()
        self.net.unicast_message(to_id, self.channel, 'propose_value', dict(instance=instance,
                                                                            proposed_value=value,
                                                                            request_id=req_id))
        return self.d

    def query(self, to_id):
        self.d = defer.Deferred()
        self.net.unicast_message(to_id, self.channel, 'query_value', dict())
        return self.d

    def receive_proposal_result(self, from_uid, msg):
        #print 'Propose Reply Received:', msg
        self.d.callback(msg)

    def receive_query_result(self, from_uid, msg):
        #print 'Query Result Received:', msg
        self.d.callback(msg)
        




class SingleValueTester(unittest.TestCase):

    durable_key = 'durable_id_{0}'
    
    def setUp(self):
        self.nodes       = dict()
        self.leader      = None
        self.dleader     = defer.Deferred()
        self.dlost       = None
        self.clients     = list()
        self.all_nodes   = 'a b c'.split()

        self.dd_store = durable.MemoryOnlyStateStore()

        test_node.setup()

        
    def tearDown(self):
        for c in self.clients:
            c.close()
            
        for n in self.all_nodes:
            self.stop(n)
        
        # In ZeroMQ 2.1.11 there is a race condition for socket deletion
        # and recreation that can render sockets unusable. We insert
        # a short delay here to prevent the condition from occuring.
        #return delay(0.05)


    def new_client(self):
        zreq = TestReq()
        self.clients.append(zreq)
        return zreq
            

    def start(self,  node_names):

        def gen_cb(x, func):
            def cb():
                func(x)
            return cb

        zpax_nodes = dict()
        
        for node_name in node_names.split():
            if not node_name in self.all_nodes or node_name in self.nodes:
                continue

            n = single_value.SingleValueNode(test_node.Channel('test_channel', test_node.NetworkNode(node_name)),
                                             2,
                                             self.durable_key.format(node_name),
                                             self.dd_store)

            n.on_leadership_acquired = gen_cb(node_name, self._on_leader_acq)
            n.on_leadership_lost     = gen_cb(node_name, self._on_leader_lost)

            n.hb_period       = 0.05
            n.liveness_window = 0.15

            n.name = node_name

            self.nodes[node_name] = n

            n.net.connect([])
            n.initialize()


        
    def stop(self, node_names):
        for node_name in node_names.split():
            if node_name in self.nodes:
                self.nodes[node_name].shutdown()
                del self.nodes[node_name]


    def _on_leader_acq(self, node_id):
        prev        = self.leader
        self.leader = node_id
        if self.dleader:
            d, self.dleader = self.dleader, None
            reactor.callLater(0.01, lambda : d.callback( (prev, self.leader) ))

            
    def _on_leader_lost(self, node_id):
        if self.dlost:
            d, self.dlost = self.dlost, None
            d.callback(node_id)


    @defer.inlineCallbacks
    def wait_for_value_equals(self, client, to_id, value):
        qval = None
        while qval != value:
            yield delay(0.05)
            r = yield client.query(to_id)
            if r['value'] is not None:
                qval = r['value'][1]

            
    @defer.inlineCallbacks
    def set_value(self, client, to_id, instance, value):
        yield client.propose(to_id, instance, value)
        yield self.wait_for_value_equals( client, to_id, value )
    

    #@trace_messages
    @defer.inlineCallbacks
    def test_initial_leader(self):
        self.start('a b')
        yield self.dleader


    #trace_messages
    @defer.inlineCallbacks
    def test_set_initial_value(self):
        self.start('a b')

        d = defer.Deferred()
        c = self.new_client()

        yield self.dleader

        msg = yield c.query('a')

        self.assertEquals(msg, dict(current_instance=1, value=None))
        
        yield c.propose('a', 1, 'foo')

        yield self.wait_for_value_equals( c, 'a', 'foo' )
        

    @defer.inlineCallbacks
    def test_set_multiple_values(self):
        self.start('a b')

        d = defer.Deferred()
        c = self.new_client()

        yield self.dleader

        msg = yield c.query('a')

        self.assertEquals(msg, dict(current_instance=1, value=None))
        
        yield c.propose('a', 1, 'foo')
        yield self.wait_for_value_equals( c, 'a', 'foo' )

        yield c.propose('a', 2, 'bar')
        yield self.wait_for_value_equals( c, 'a', 'bar' )

        yield c.propose('a', 3, 'baz')
        yield self.wait_for_value_equals( c, 'a', 'baz' )





    @show_stacktrace
    #@trace_messages
    @defer.inlineCallbacks
    def test_shutdown_and_restart(self):
        self.start('a b')

        d = defer.Deferred()
        c = self.new_client()

        yield self.dleader

        yield c.propose('a', 1, 'foo')
        yield self.wait_for_value_equals( c, 'a', 'foo' )

        self.stop('a b')

        yield delay(0.05)

        self.dleader = defer.Deferred()

        self.start('a b')

        yield self.dleader

        msg = yield c.query('a')

        self.assertEquals(msg['value'], ('req_id', 'foo'))



        
    #trace_messages
    @defer.inlineCallbacks
    def test_shutdown_and_restart_with_outstanding_proposal(self):
        self.start('a b')

        d = defer.Deferred()
        c = self.new_client()

        yield self.dleader

        yield c.propose('a', 1, 'foo')
        yield self.wait_for_value_equals( c, 'a', 'foo' )

        self.stop('b')

        yield c.propose('a', 2, 'bar')

        self.assertTrue( self.nodes['a'].pax.proposed_value is not None )

        self.stop('a')

        yield delay(0.05)

        self.dleader = defer.Deferred()
        
        self.start('a b')

        yield self.dleader
        
        yield self.wait_for_value_equals( c, 'a', 'bar' )
        

            

    @defer.inlineCallbacks
    def test_node_recovery(self):
        self.start('a b c')

        d = defer.Deferred()
        c = self.new_client()

        yield self.dleader

        yield self.set_value(c, 'a', 1, 'foo')

        yield self.wait_for_value_equals( c, 'c', 'foo' )

        self.stop('c')

        yield self.set_value(c, 'a', 2, 'bar')
        yield self.set_value(c, 'a', 3, 'baz')
    
        self.start('c')

        yield self.wait_for_value_equals( c, 'c', 'baz' )

########NEW FILE########
__FILENAME__ = commit
'''
This module provides a Paxos Commit implementation.

Implementation Strategy:

Liveness:    To ensure forward progress, each transaction manager is assigned
             a MultiPaxos instance. The leader of the MultiPaxos session is
             responsible for driving all outstanding transactions to conclusion.
             In essence, this re-uses the liveness solution for MultiPaxos.

Parallelism: All transactions are executed in parallel and no guarantees
             are made about the order in which they complete.

Durability:  To achieve any measure of performance with multiple,
             concurrent transactions, some manner of batched writes to
             disk will be required.  The transaction manager requires a
             "durability" object that implements the durable.IDurableStateStore
             interface. When TransactionNodes need to save their state
             prior to sending promise/accepted messages, they will call
             the "save_state()" method of the durable object and send
             the message when the returned deferred fires.  

Threshold:   In traditional Paxos Commit, every node must respond with the
             commit/abort decision before the overall transaction may be
             considered complete. For quorum-based applications that can
             tolerate one or more "aborts" and still consider the overall
             transaction a success, a "threshold" parameter may be used to
             indicate the required number of "comitted" messages needed
             for overall success. This defaults to the total number of
             nodes.

Messaging:   This implementation avoids the final "commit"/"abort" message
             by having all nodes listen to each other directly. When a node
             sees that enough of its peers have responded with their own
             "commit"/"abort" decision, it can determine the overall result
             for itself.

Recovery:    Each node maintains a cache of transaction results. When a
             message arrives for an already concluded transaction that is
             contained within the cache, the result is sent directly.
             Applications should override the default cache implementation
             and provide a "check" function that can look further back
             in time than the in-memory cache allows. Otherwise,
             old transactions from a recovered node may either appear to
             be new or may never complete.
'''

import time

from   twisted.internet import defer

import paxos.practical
from   paxos.practical import ProposalID


class TransactionHistory(object):

    max_entries = 1000
    
    def __init__(self):
        self.recent_list = list()
        self.recent_map  = dict()

    def add(self, tx_uuid, result):
        self.recent_list.append( tx_uuid )
        self.recent_map[ tx_uuid ] = result
        if len(self.recent_list) > self.max_entries:
            del self.recent_map[ self.recent_list.pop(0) ]

    def lookup(self, tx_uuid):
        return self.recent_map.get(tx_uuid, None)




class TransactionManager (object):
    '''
    
    Transaction Managers monitor and ensure the progress of Transaction
    instances. Battles for Paxos leadership are avoided through the use of a
    dedicated MultiPaxos instance. Only the leader of the MultiPaxos session
    will attempt to drive timed-out transactions to resolution.  Leadership
    battles are still possible as multiple MultiPaxos instances may
    simultaneously believe themselves to be the leader.  However, the durations
    of these battles should be brief and it greatly simplifies the logic behind
    this implementation.

    A further use of the MultiPaxos instance is that it may be used to make
    decisions for the nodes in the transaction pool. To add or remove a node
    from the pool, for example, the MultiPaxos instance could be used to
    resolve "pause_new_transaction_acceptance", the instances would then
    disable sending "accepted" messages on the MultiPaxos instance until all of
    the outstanding transactions are complete. Then, "transactions_paused"
    would be resolved. At this point, the new node configuration would be
    resolved and all of the nodes would transition to the new
    configuration. Finally, "resume_new_transactions" would be resolved to
    re-enable normal behavior.
    
    '''

    timeout_duration   = 30.0 # seconds

    get_current_time   = time.time

    tx_history_factory = TransactionHistory

    # all_node_ids = set() of node ids
    def __init__(self, net_channel, quorum_size,
                 all_node_ids, threshold, durable):
        self.net           = net_channel
        self.node_uid      = net_channel.node_uid
        self.quorum_size   = quorum_size
        self.all_node_ids  = all_node_ids
        self.threshold     = threshold
        self.durable       = durable
        self.transactions  = dict()       # uuid => Transaction instance
        self.results_cache = self.tx_history_factory()

        self.net.add_message_handler( self )


    def heartbeat(self, current_time, transaction_leader=False):
        for tx in self.transactions.values():
            tx.heartbeat(current_time, transaction_leader)
            

    def get_transaction(self, tx_uuid):
        return self.transactions.get(tx_uuid, None)


    def get_result(self, tx_uuid):
        d = defer.Deferred()
        
        r = self.results_cache.lookup(tx_uuid)
        if r:
            d.callback(r)
            return d

        tx = self.transactions.get(tx_uuid)
        if tx:
            tx.dcomplete.addCallback( lambda *ignore: d.callback( tx.result ) )
            return d

        d.errback(KeyError('Unknown Transaction Id'))
        return d
            

    def propose_result(self, tx_uuid, result, **kwargs):
        assert result in ('commit', 'abort')

        r = self.results_cache.lookup(tx_uuid)
        if r:
            return defer.succeed( (tx_uuid, r) )
        
        tx = self.transactions.get(tx_uuid, None)

        if tx is None:
            tx = self.create_transaction(tx_uuid, kwargs)

        tx.tx_nodes[ self.node_uid ].set_proposal( result )

        return tx.dcomplete

        
    def get_transaction_node(self, from_uid, msg):
        try:
            tx_uuid = msg['tx_uuid']
            tx_node = msg['tx_node']
        except KeyError:
            return


        if not tx_node in self.all_node_ids:
            return
        
        tx = self.transactions.get(tx_uuid, None)

        if tx is not None:
            return tx.tx_nodes[ tx_node ]
        
        r = self.results_cache.lookup( tx_uuid )
        
        if r is not None:
            self.net.unicast(from_uid, 'transaction_result',
                             dict( tx_uuid=tx_uuid, result=r ))
            return
        
        tx = self.create_transaction( tx_uuid, msg )

        if tx is None:
            return
        
        return tx.tx_nodes[ tx_node ]

        
    def create_transaction(self, tx_uuid, msg):
        tx =  Transaction(self, tx_uuid,
                          self.get_current_time() + self.timeout_duration,
                          self.node_uid,
                          self.quorum_size, self.threshold)
        self.transactions[ tx_uuid ] = tx
        tx.dcomplete.addCallback( self.transaction_complete )
        return tx

    
    def transaction_complete(self, tpl):
        tx_uuid, result = tpl
        del self.transactions[ tx_uuid ]
        self.results_cache.add( tx_uuid, result )
        return tpl

    
    def receive_transaction_result(self, from_uid, msg):
        try:
            tx_uuid = msg['tx_uuid']
            result  = msg['result']
            tx      = self.transactions[ tx_uuid ]
        except KeyError:
            return
        
        tx.set_resolution( result )
        

    def _tx_handler(func):
        def wrapper(self, from_uid, msg):
            txn = self.get_transaction_node( from_uid, msg )
            if txn:
                func(self, txn, from_uid, msg)
        return wrapper

    @_tx_handler
    def receive_prepare(self, txn, from_uid, msg):
        txn.receive_prepare(from_uid, msg)

    @_tx_handler
    def receive_accept(self, txn, from_uid, msg):
        txn.receive_accept(from_uid, msg)

    @_tx_handler
    def receive_promise(self, txn, from_uid, msg):
        txn.receive_promise(from_uid, msg)

    @_tx_handler
    def receive_prepare_nack(self, txn, from_uid, msg):
        txn.receive_prepare_nack(from_uid, msg)

    @_tx_handler
    def receive_accept_nack(self, txn, from_uid, msg):
        txn.receive_accept_nack(from_uid, msg)

    @_tx_handler
    def receive_accepted(self, txn, from_uid, msg):
        txn.receive_accepted(from_uid, msg)


    
class TransactionNode(paxos.practical.Node):
    '''
    For each transaction, there will be once instance of this class for each
    node participating in the transaction. Only two proposed values are
    permitted: "commit" and "abort". Only the node with the id matching
    the node id assigned to the TransactionNode instance may propose
    "commit". All other nodes may propose "abort" (and only "abort") once
    the overall transaction timeout has expired.
    '''

    def __init__(self, tx, tx_node_id, node_uid, quorum_size):
        super(TransactionNode,self).__init__(self, node_uid, quorum_size)
        self.tx           = tx
        self.tx_node_id   = tx_node_id
        self.is_this_node = tx_node_id == node_uid
        self.saving       = False

        if self.is_this_node:
            self.active = False # Disable to prevent prepare() from sending a message
            self.prepare()      # Allocate the first proposal id
            self.active = True  # Re-enable messaging
            self.leader = True  # Own-node is the leader for the first message

        
    def heartbeat(self, drive_to_abort):
        '''
        Called periodically to retransmit messages and drive the node to completion.

        If drive_to_abort is True, the TransactionNode will attempt to assume
        leadership of the Paxos instance and drive the "abort" decision to
        concensus.
        '''
        if drive_to_abort:
            if self.proposed_value is None:
                self.set_proposal('abort')
                
            if self.leader:                
                self.resend_accept()
            else:
                self.prepare()
                
        elif self.is_this_node:
            self.resend_accept()


    def set_proposal(self, value):
        super(TransactionNode,self).set_proposal(value)
        

    def observe_proposal(self, from_uid, proposal_id):
        #TODO: Does this need to be called from 'recv_accept_request()' ?
        super(TransactionNode,self).observe_proposal(from_uid, proposal_id)
        if self.leader and proposal_id > self.proposal_id:
            self.leader = False

            
    @defer.inlineCallbacks
    def save_state(self):
        if not self.saving:
            self.saving = True

            yield self.tx.manager.durable.set_state( (self.tx.uuid, self.tx_node_id), (self.promised_id,
                                                     self.accepted_id, self.accepted_value) )
            self.saving = False
            
            self.persisted()

            
    def recv_prepare(self, *args):
        super(TransactionNode, self).recv_prepare(*args)
        if self.persistance_required:
            self.save_state()

            
    def recv_accept_request(self, *args):
        super(TransactionNode, self).recv_accept_request(*args)
        if self.persistance_required:
            self.save_state()

            
    # --- Messenger Interface ---

    
    def broadcast(self, message_type, **kwargs):
        kwargs.update( { 'tx_uuid' : self.tx.uuid,
                         'tx_node' : self.tx_node_id } )
        self.tx.manager.net.broadcast( message_type, kwargs )

    def unicast(self, to_uid, message_type, **kwargs):
        kwargs.update( { 'tx_uuid' : self.tx.uuid,
                         'tx_node' : self.tx_node_id } )
        self.tx.manager.net.unicast( to_uid, message_type, kwargs )
                                           
    def send_prepare(self, proposal_id):
        self.broadcast( 'prepare', proposal_id = proposal_id )
        
    def send_promise(self, proposer_uid, proposal_id, previous_id, accepted_value):
        self.unicast( proposer_uid, 'promise',
                      proposal_id    = proposal_id,
                      previous_id    = previous_id,
                      accepted_value = accepted_value )
        
    def send_accept(self, proposal_id, proposal_value):
        self.broadcast( 'accept',
                        proposal_id    = proposal_id,
                        proposal_value = proposal_value )
        
    def send_accepted(self, proposal_id, accepted_value):
        self.broadcast( 'accepted',
                        proposal_id    = proposal_id,
                        accepted_value = accepted_value )

    def send_prepare_nack(self, to_uid, proposal_id, promised_id):
        self.unicast( to_uid, 'prepare_nack',
                      proposal_id = proposal_id )

    def send_accept_nack(self, to_uid, proposal_id, promised_id):
        self.unicast( to_uid, 'accept_nack',
                      proposal_id = proposal_id,
                      promised_id = promised_id )
        
    def receive_prepare(self, from_uid, msg):
        self.recv_prepare( from_uid, ProposalID(*msg['proposal_id']) )

    def receive_promise(self, from_uid, msg):
        self.recv_promise( from_uid, ProposalID(*msg['proposal_id']),
                         ProposalID(*msg['previous_id']) if msg['previous_id'] else None,
                         msg['accepted_value'] )

    def receive_prepare_nack(self, from_uid, msg):
        self.recv_prepare_nack( from_uid, ProposalID(*msg['proposal_id']) )
        
    def receive_accept(self, from_uid, msg):
        self.recv_accept_request( from_uid, ProposalID(*msg['proposal_id']), msg['proposal_value'] )

    def receive_accept_nack(self, from_uid, msg):
        self.recv_accept_nack( from_uid, ProposalID(*msg['proposal_id']), ProposalID(*msg['promised_id']) )

    def receive_accepted(self, from_uid, msg):
        self.recv_accepted( from_uid, ProposalID(*msg['proposal_id']), msg['accepted_value'] )
        
    def on_resolution(self, proposal_id, value):
        self.tx.node_resolved(self)

    def on_leadership_acquired(self):
        pass



class Transaction (object):
    '''
    
    This class represents a single transaction. Each transaction has a UUID
    assigned to it and uses a modified version of Paxos Commit to arrive at
    concensus on the commit/abort decision. A TransactionNode instance (which
    encapsulates a single Paxos instance) is created for each node
    participatring in the decision. Once a node has made it's commit/abort
    decision, it proposes that value for it's corresponding TransactionNode.

    The transaction's heartbeat method should be called periodically to
    ensure forward progress on the transaction. 
    
    '''

    def __init__(self, tx_mgr, tx_uuid, timeout_time, node_uid, quorum_size, threshold):
        self.manager        = tx_mgr
        self.uuid           = tx_uuid
        self.timeout_time   = timeout_time
        self.quorum_size    = quorum_size
        self.threshold      = threshold
        self.tx_nodes       = dict()
        self.num_committed  = 0
        self.num_aborted    = 0
        self.result         = None
        self.dcomplete      = defer.Deferred()
        
        for pax_node_id in self.manager.all_node_ids:
            self.tx_nodes[ pax_node_id ] = TransactionNode(self, pax_node_id, node_uid, quorum_size)

        self.this_node = self.tx_nodes[ node_uid ]


    @property
    def channel_name(self):
        return self.manager.channel_name

            
    def heartbeat(self, current_time, transaction_leader=False):
        if self.timeout_time <= current_time and transaction_leader:
            
            for tx in self.tx_nodes.itervalues():
                if not tx.complete:
                    tx.heartbeat( drive_to_abort=True )
        else:
            if not self.this_node.complete and self.this_node.proposed_value is not None:
                self.this_node.resend_accept()


    def set_resolution(self, final_value):
        '''
        Used when concensus on the final value has already been reached
        '''
        if self.result is None:
            #print '********** RESOLVED: ', self.manager.node_uid, self.uuid, final_value
            self.result = final_value
            self.dcomplete.callback( (self.uuid, self.result) )
        
        
    def node_resolved(self, txn):
        if self.result is not None:
            return

        if txn.final_value == 'commit':
            self.num_committed += 1
        else:
            self.num_aborted += 1
            
        if self.num_committed >= self.manager.threshold:
            self.set_resolution( 'committed' )
                
        elif self.num_aborted > len(self.manager.all_node_ids) - self.manager.threshold:
            self.set_resolution('aborted')

            

########NEW FILE########
__FILENAME__ = durable
'''
The Paxos algorithm requires state to be flushed to stable media prior to sending
certain messages over the network. This module provides an interface for doing so.

As these operations occur frequent and slow to complete, buffering must be used
to achieve any level of performance. The IDurableStateStore provides an interface
that uses deferreds with the get/set methods to abstract the backend implementation.

MemoryOnlyStateStore may be used in unit tests to avoid the performance penalty
associated with file I/O.
'''

from twisted.internet import defer



class IDurableStateStore(object):
    
    def set_state(self, data_id, new_state):
        '''
        Replaces the previous (if any) state associated with 'data_id' with the
        new state. If 'new_state' is None, the data_id is deleted from
        the store.

        Returns a deferred to the new data (or deletion flag) being written
        to disk. 
        '''

    def get_state(self, data_id):
        '''
        Returns a Deferred to the data associated with the id. Returns None if
        no state is associated with the data_id
        '''

    def flush(self):
        '''
        Flushes state to stable media. Returns a deferred that will fire once the
        data is at rest and all "set_state" deferreds have been fired.
        '''



class _DItem(object):
    __slots__ = ['data_id', 'data']
        
    def __init__(self, data_id, data):
        self.data_id  = data_id
        self.data     = data

        
class MemoryOnlyStateStore(object):

    def __init__(self):
        self.data       = dict()
        self.dflush     = dict() # maps data_id => Deferred
        self.auto_flush = True

        
    def set_state(self, data_id, new_state):
        di = self.data.get(data_id, None)
        
        if di:
            di.data = new_state
        else:
            self.data[ data_id ] = _DItem(data_id, new_state)

        if new_state is None:
            del self.data[ data_id ]
            
        dflush = self.dflush.get(data_id, None)
        
        if dflush is None:
            dflush = defer.Deferred()
            self.dflush[data_id] = dflush

            def onflush(_):
                del self.dflush[data_id]
                return _

            dflush.addCallback(onflush)
            

        if self.auto_flush:
            dflush.callback(None)
            
        return dflush

        
    def get_state(self, data_id):
        return defer.succeed(self.data[data_id].data if data_id in self.data else None)

    
    def flush(self):
        t = self.dflush
        self.dflush = dict()
        for d in t.itervalues():
            d.callback(None)
        return defer.succeed(None)

            

########NEW FILE########
__FILENAME__ = multi
'''
This module provides a Multi-Paxos node implementation. The implementation is
broken into two separate components. MultiPaxosNode implements the basic logic
required for Multi-Paxos operation. MultiPaxosHeartbeatNode enhances the basic
implementation with a heartbeating mechanism used to detect and recover from
failed leaders. The heartbeating mechanism is only one of potentially many
mechanisms that could be used to serve this purpose so it is isolated from
the rest of the Multi-Paxoxs logic to facilitate reuse of the generic component.
'''

import os
import random

from   twisted.internet import defer, task, reactor

import paxos.functional
from   paxos.functional import ProposalID


class ProposalFailed(Exception):
    pass


class InstanceMismatch(ProposalFailed):

    def __init__(self, current):
        super(InstanceMismatch,self).__init__('Instance Number Mismatch')
        self.current_instance = current


class ProposalAdvocate (object):
    '''
    Instances of this class ensure that the leader receives the proposed value.
    '''
    callLater   = reactor.callLater
    retry_delay = 10 # seconds

    instance    = None
    proposal    = None
    request_id  = None
    retry_cb    = None

    
    def __init__(self, mnode, retry_delay = None):
        '''
        mnode       - MultiPaxosNode
        retry_delay - Floating point delay in seconds between retry attempts. Defaults
                      to 10
        '''
        self.mnode = mnode
        if retry_delay:
            self.retry_delay = None
        
        
    def cancel(self):
        '''
        Called at:
           * Application shutdown
           * On instance resolution & prior to switching to the next instance
        '''
        if self.retry_cb and self.retry_cb.active():
            self.retry_cb.cancel()
            
        self.retry_cb   = None
        self.instance   = None
        self.proposal   = None
        self.request_id = None

        
    def recover(self, mnode):
        '''
        Called when recovering from durable state
        '''
        self.mnode = mnode
        if self.request_id is not None:
            self._send_proposal()
            
        
    def proposal_acknowledged(self, request_id):
        '''
        Once the current leader has been informed, we can suspend retransmits.
        Transmitting will resume if the current leader changes.
        '''
        if self.request_id == request_id and self.retry_cb.active():
            self.retry_cb.cancel()

        
    def leadership_changed(self):
        '''
        The proposal must be re-sent on every leadership acquisition to
        ensure that the current leader is aware that a proposal is awaiting
        resolution.
        '''
        self._send_proposal()
    

    def set_proposal(self, instance, request_id, proposed_value):
        '''
        Sets the proposal value if one hasn't already been set and begins 
        attempting to notify the current leader of the proposed value.
        '''
        if self.request_id is None:
            self.instance   = instance
            self.proposal   = proposed_value
            self.request_id = request_id

            self._send_proposal()
            
            
    def _send_proposal(self):
        if self.proposal is None:
            return
        
        if self.retry_cb and self.retry_cb.active():
            self.retry_cb.cancel()

        if self.instance == self.mnode.instance:
            self.retry_cb = self.callLater(self.retry_delay,
                                           self._send_proposal)

            if self.mnode.pax.leader:
                self.mnode.pax.resend_accept()
            else:
                self.mnode.send_proposal_to_leader(self.instance, self.request_id, self.proposal)
        else:
            self.cancel()


        
class MultiPaxosNode(object):
    '''
    This is an abstract class that provides an implementation for the majority
    of the required Multi-Paxos components. The only omitted component is the
    Detection of and recovery from leadership failures. There are multiple
    strategies for handling this so it is left for subclasses to define.
    '''

    def __init__(self, net_channel, quorum_size, durable_data_id, durable_data_store):
        '''
        net_channel        - net.Channel instance
        quorum_size        - Paxos quorum size
        durable_data_id    - Unique ID for use with the durable_data_store
        durable_data_store - Implementer of durable.IDurableDataStore
        '''
        self.net         = net_channel
        self.node_uid    = net_channel.node_uid
        self.quorum_size = quorum_size
        self.dd_store    = durable_data_store
        self.dd_id       = durable_data_id
        self.instance    = 0
        self.leader_uid  = None
        self.pax         = None
        self.pax_ignore  = False # True if all Paxos messages should be ignored
        self.persisting  = False
        self.advocate    = ProposalAdvocate(self)

        self.instance_exceptions  = set() # message types that should be processed
                                          # even if the instance number is not current

        self.net.add_message_handler(self)
        

    @defer.inlineCallbacks
    def initialize(self):
        '''
        Initilizes the node from the durable state saved for a pre-existing,
        multi-paxos session or creates a new session if no durable state is found.
        '''
        state = yield self.dd_store.get_state(self.dd_id)

        if state is None:
            self.next_instance()
        else:
            self.instance = state['instance']
            
            yield self._recover_from_persistent_state( state )
            
            self.advocate.set_proposal( self.instance, state['request_id'],
                                        state['proposal'] )


    def _recover_from_persistent_state(self, state):
        '''
        This method may be used by subclasses to recover the multi-paxos
        session from durable state. The 'state' argument is a dictionary
        containing the Acceptor's promised_id, accepted_id, and accepted_value
        attributes. The subclass may add additional state to this dictionary by
        overriding the _get_additional_persistent_state method.
        '''
    

    def _get_additional_persistent_state(self):
        '''
        Called when multi-paxos state is being persisted to disk prior to sending
        a promise/accepted message. The return value is a dictionary of key-value
        pairs to persist
        '''
        return {}
        
        
    def shutdown(self):
        '''
        Shuts down the node.
        '''
        self.advocate.cancel()
        self.net.shutdown()


    def change_quorum_size(self, quorum_size):
        '''
        If nodes are added/removed from the Paxos group, this method may be used
        to update the quorum size. Note: negotiation of the new Paxos membership
        and resulting quorum size should occur within the context of the
        previous multi-paxos instance. Doing so outside the multi-paxos chain of
        resolutions will almost certainly result in an inconsistent view of the
        membership list which, in turn, breaks the safety guarantees provided
        by Paxos.
        '''
        self.quorum_size = quorum_size
        self.pax.change_quorum_size( quorum_size )


    def _new_paxos_node(self):
        '''
        Abstract function that returns a new paxos.node.Node instance
        '''

        
    @defer.inlineCallbacks
    def persist(self):
        '''
        Uses the durable state store to flush recovery state to disk.
        Subclasses may add to the flushed state by overriding the
        _get_additional_persistent_state() method.
        '''
        if not self.persisting:
            self.persisting = True

            state = dict( instance       = self.instance,
                          proposal       = self.advocate.proposal,
                          request_id     = self.advocate.request_id,
                          promised_id    = self.pax.promised_id,
                          accepted_id    = self.pax.accepted_id,
                          accepted_value = self.pax.accepted_value )

            state.update( self._get_additional_persistent_state() )
            
            yield self.dd_store.set_state( self.dd_id, state )
            
            self.persisting = False
            
            self.pax.persisted()
            



    def next_instance(self, set_instance_to=None):
        '''
        Advances to the next multi-paxos instance or to the specified
        instance number if one is provided. 
        '''
        self.advocate.cancel()
        
        if set_instance_to is None:
            self.instance += 1
        else:
            self.instance = set_instance_to
            
        self.pax = self._new_paxos_node()


    def broadcast(self, msg_type, **kwargs):
        '''
        Broadcasts a message to all peers
        '''
        kwargs.update( dict(instance=self.instance) )
        self.net.broadcast(msg_type, kwargs)

        
    def unicast(self, dest_uid, msg_type, **kwargs):
        '''
        Sends a message to the specified peer only
        '''
        kwargs.update( dict(instance=self.instance) )
        self.net.unicast(dest_uid, msg_type, kwargs)
        
    
    def behind_in_sequence(self, current_instance):
        '''
        Nodes can only send messages for an instance once the previous instance
        has been completed. Consequently, observance of a "future" message
        indicates that this node has fallen behind it's peers. This method is
        called when that case is detected. Application-specific logic must then
        preform some form of catchup mechanism to bring the node back in sync
        with it's peers.
        '''
        

    def _mpax_filter(func):
        '''
        Function decorator that filters out messages that do not match the
        current instance number
        '''
        def wrapper(self, from_uid, msg):
            if msg['instance'] == self.instance and not self.pax_ignore:
                func(self, from_uid, msg)
        return wrapper

        
    #------------------------------------------------------------------
    #
    # Proposal Management
    #
    #------------------------------------------------------------------

    
    def set_proposal(self, request_id, proposal_value, instance=None):
        '''
        Proposes a value for the current instance.

        request_id - arbitrary string that may be used to match the resolved
                     value to the originating request

        proposal_value - Value proposed for resolution

        instance - Optional instance number for which the proposal is valid.
                   InstanceMismatch is thrown If the current proposal number
                   does not match this parameter.
        '''
        if instance is None:
            instance = self.instance
            
        if instance == self.instance:
            self.pax.set_proposal( (request_id, proposal_value) )
            self.advocate.set_proposal( instance, request_id, proposal_value )
        else:
            raise InstanceMismatch(self.instance)
        

    def send_proposal_to_leader(self, instance, request_id, proposal_value):
        if instance == self.instance and self.leader_uid is not None:
            self.unicast( self.leader_uid, 'set_proposal',
                          request_id     = request_id,
                          proposal_value = proposal_value )


    @_mpax_filter
    def receive_set_proposal(self, from_uid, msg):
        self.set_proposal(msg['request_id'], msg['proposal_value'])
        self.unicast( from_uid, 'set_proposal_ack', request_id = msg['request_id'] )

        
    @_mpax_filter
    def receive_set_proposal_ack(self, from_uid, msg):
        if from_uid == self.leader_uid:
            self.advocate.proposal_acknowledged( msg['request_id'] )

    #------------------------------------------------------------------
    #
    # Messenger interface required by paxos.node.Node
    #
    #------------------------------------------------------------------

    def send_prepare(self, proposal_id):
        self.broadcast( 'prepare', proposal_id = proposal_id )

        
    def receive_prepare(self, from_uid, msg):
        '''
        Prepare messages must be inspected for "future" instance numbers and
        the catchup mechanism must be invoked if they are seen. This protects
        against the following case:
        
           * A threshold number of nodes resolve on a proposal
           * One of the nodes crashes before learning of the resolution
           * The rest of the nodes crash
           * All nodes recover
           * At this point, leadership cannot be obtained since the first node that
             crashed believes it is still working with paxos instance N whereas the
             other nodes believe they are working on paxos instance N+1. No quorum
             can be achieved.
        '''
        if msg['instance'] > self.instance:
            self.behind_in_sequence( msg['instance'] )

        elif msg['instance'] == self.instance:
            self.pax.recv_prepare( from_uid, ProposalID(*msg['proposal_id']) )

            if self.pax.persistance_required:
                self.persist()
        

    def send_promise(self, to_uid, proposal_id, previous_id, accepted_value):
        self.unicast( to_uid, 'promise', proposal_id    = proposal_id,
                                         previous_id    = previous_id,
                                         accepted_value = accepted_value )

        
    @_mpax_filter
    def receive_promise(self, from_uid, msg):
        self.pax.recv_promise( from_uid, ProposalID(*msg['proposal_id']),
                               ProposalID(*msg['previous_id']) if msg['previous_id'] else None,
                               msg['accepted_value'] )

        
    def send_prepare_nack(self, propser_obj, to_uid, proposal_id):
        self.unicast( to_uid, 'prepare_nack', proposal_id = proposal_id )

        
    @_mpax_filter
    def receive_prepare_nack(self, from_uid, msg):
        self.pax.recv_prepare_nack( from_uid, ProposalID(*msg['proposal_id']) )

        
    def send_accept(self, proposal_id, proposal_value):
        self.broadcast( 'accept', proposal_id    = proposal_id,
                                  proposal_value = proposal_value )


    @_mpax_filter
    def receive_accept(self, from_uid, msg):
        self.pax.recv_accept_request( from_uid, ProposalID(*msg['proposal_id']), msg['proposal_value'] )

        # TODO: Actual durability implementation
        if self.pax.persistance_required:
            self.persist()

        
    def send_accept_nack(self, to_uid, proposal_id, promised_id):
        self.unicast( to_uid, 'accept_nack', proposal_id = proposal_id,
                                             promised_id = promised_id )


    @_mpax_filter
    def receive_accept_nack(self, from_uid, msg):
        self.pax.recv_accept_nack( from_uid, ProposalID(*msg['proposal_id']), ProposalID(*msg['promised_id']) )
        

    def send_accepted(self, proposal_id, accepted_value):
        self.broadcast( 'accepted', proposal_id    = proposal_id,
                                    accepted_value = accepted_value )


    @_mpax_filter
    def receive_accepted(self, from_uid, msg):
        self.pax.recv_accepted( from_uid, ProposalID(*msg['proposal_id']), msg['accepted_value'] )

        
    def on_leadership_acquired(self):
        pass

    
    def on_resolution(self, proposal_id, value):
        self.next_instance()



        
class MultiPaxosHeartbeatNode(MultiPaxosNode):
    '''
    This class provides a concrete implementation of MultiPaxosNode that uses
    the heartbeating mechanism defined in paxos.functional.HeartbeatNode to
    detect and recover from leadership failures.

    Instance Variables:
    
    hb_period       - Floating-point time in seconds between heartbeats
    liveness_window - Window of time within which at least one heartbeat message
                      must be seen for the the leader to be considered alive.
    '''

    hb_period         = 60  # Seconds
    liveness_window   = 180 # Seconds

    hb_poll_task      = None
    leader_pulse_task = None
    is_leader         = False

    def __init__(self, *args, **kwargs):

        self.hb_period       = kwargs.pop('hb_period',       self.hb_period)
        self.liveness_window = kwargs.pop('liveness_window', self.liveness_window)
            
        super(MultiPaxosHeartbeatNode, self).__init__(*args, **kwargs)

        self.instance_exceptions.add('heartbeat')


    def shutdown(self):
        if self.hb_poll_task.running:
            self.hb_poll_task.stop()

        if self.leader_pulse_task.running:
            self.leader_pulse_task.stop()

        super(MultiPaxosHeartbeatNode, self).shutdown()


    @defer.inlineCallbacks
    def initialize(self):
        yield super(MultiPaxosHeartbeatNode,self).initialize()
        self._start_tasks()


    def _recover_from_persistent_state(self, state):
        self.pax = self._new_paxos_node()
        
        self.pax.recover( state['promised_id'],
                          state['accepted_id'],
                          state['accepted_value'] )
        
        self._start_tasks()
        
        return defer.succeed(None)
        

    def _start_tasks(self):
        if self.hb_poll_task is None:
            self.hb_poll_task      = task.LoopingCall( lambda : self.pax.poll_liveness()  )
            self.leader_pulse_task = task.LoopingCall( lambda : self.pax.pulse()          )

            self.hb_poll_task.start( self.liveness_window )

        
    def _new_paxos_node(self):
        return paxos.functional.HeartbeatNode(self, self.node_uid, self.quorum_size,
                                              leader_uid      = self.leader_uid,
                                              hb_period       = self.hb_period,
                                              liveness_window = self.liveness_window)

    
    def on_leadership_acquired(self):
        self.is_leader = True
        self.leader_pulse_task.start( self.hb_period )
        super(MultiPaxosHeartbeatNode, self).on_leadership_acquired()


    #------------------------------------------------------------
    #
    # Messenger methods required by paxos.functional.HeartbeatNode
    #
    #------------------------------------------------------------

    
    def send_heartbeat(self, leader_proposal_id):
        '''
        Sends a heartbeat message to all nodes
        '''
        self.broadcast( 'heartbeat', leader_proposal_id = leader_proposal_id )


    def receive_heartbeat(self, from_uid, msg):
        if msg['instance'] > self.instance:
            self.next_instance( set_instance_to = msg['instance'] )
            self.pax.recv_heartbeat( from_uid, ProposalID(*msg['leader_proposal_id']) )
            self.behind_in_sequence( msg['instance'] )
        elif msg['instance'] == self.instance:
            self.pax.recv_heartbeat( from_uid, ProposalID(*msg['leader_proposal_id']) )
        

    def schedule(self, msec_delay, func_obj):
        pass # we use Twisted's task.LoopingCall mechanism instead

        
    def on_leadership_lost(self):
        '''
        Called when loss of leadership is detected
        '''
        self.is_leader = False
        if self.leader_pulse_task.running:
            self.leader_pulse_task.stop()

            
    def on_leadership_change(self, prev_leader_uid, new_leader_uid):
        '''
        Called when a change in leadership is detected
        '''
        self.leader_uid = new_leader_uid
        self.advocate.leadership_changed()
        

########NEW FILE########
__FILENAME__ = channel

class Channel (object):
    '''
    Wraps a NetworkNode object with an interface that sends and receives over
    a specific channel
    '''

    def __init__(self, channel_name, net_node):
        self.channel_name = channel_name
        self.net_node     = net_node

        
    @property
    def node_uid(self):
        return self.net_node.node_uid

    
    def create_subchannel(self, sub_channel_name):
        return Channel( self.channel_name + '.' + sub_channel_name, self.net_node )

        
    def add_message_handler(self, handler):
        self.net_node.add_message_handler(self.channel_name, handler)
        

    def connect(self, *args, **kwargs):
        self.net_node.connect(*args, **kwargs)


    def shutdown(self):
        self.net_node.shutdown()


    def broadcast(self, message_type, *parts):
        self.net_node.broadcast_message(self.channel_name, message_type, *parts)


    def unicast(self, to_uid, message_type, *parts):
        self.net_node.unicast_message(to_uid, self.channel_name, message_type, *parts)
        

########NEW FILE########
__FILENAME__ = json_encoder
'''
This module provides a simple message encoder that converts messages to and from
JSON text.
'''

import json

from twisted.python import log


def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv
            
def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv


class JSONEncoder (object):

    def encode(self, node_uid, message_type, parts):
        header = dict()

        header['type'] = message_type
        header['from'] = node_uid

        plist = [ header ]
        
        if parts:
            plist.extend( parts )
        
        return [ str(json.dumps(p)) for p in plist ]


    def decode(self, jparts):
        if not jparts:
            return
        
        try:
            parts = [ json.loads(j, object_hook=_decode_dict) for j in jparts ]
        except ValueError:
            print 'Invalid JSON: ', jparts
            return

        header = parts[0]
        parts  = parts[1:]

        return header['from'], header['type'], parts

########NEW FILE########
__FILENAME__ = test_node
'''
This module provides an "in memory" implementation of the NetworkNode interface.
As the module's name implies, it's intended for use in testing code. This
implementation provides deterministic messaging that always deliveres messages
in the same order across repeated runs of the same test.
'''

from twisted.internet import defer, task, reactor

from zpax.network import channel

TRACE = False

nodes = dict() # uid => NetworkNode object


def setup():
    nodes.clear()


try:
    defer.gatherResults( [defer.succeed(None),], consumeErrors=True )
    use_consume = True
except TypeError:
    use_consume = False

def gatherResults( l ):
    if use_consume:
        return defer.gatherResults(l, consumeErrors=True)
    else:
        return defer.gatherResults(l)


def trace_messages( fn ):
    '''
    Function decorator that may be applied to a test_ method to display all
    messages exchanged during the test
    '''
    @defer.inlineCallbacks
    def wrapit(self, *args, **kwargs):
        global TRACE
        TRACE = True
        print ''
        print 'Trace:'
        yield fn(self, *args, **kwargs)
        TRACE = False
        print ''
    return wrapit


def show_stacktrace( fn ):
    '''
    Function decorator that catches exceptions and prints a traceback
    '''
    @defer.inlineCallbacks
    def wrapit(self, *args, **kwargs):
        try:
            yield fn(self, *args, **kwargs)
        except:
            import traceback
            traceback.print_exc()
            raise
    return wrapit



def broadcast_message( src_uid, channel_name, message_type, *parts ):
    if len(parts) == 1 and isinstance(parts[0], (list, tuple)):
        parts = parts[0]
    for n in nodes.values():
        if n.link_up:
            n.recv_message( src_uid, channel_name, message_type, parts )
            

def unicast_message( src_uid, dst_uid, channel_name, message_type, *parts ):
    if len(parts) == 1 and isinstance(parts[0], (list, tuple)):
        parts = parts[0]
    if dst_uid in nodes:
        nodes[dst_uid].recv_message( src_uid, channel_name, message_type, parts )


class Channel( channel.Channel ):

    
    def get_link_up(self):
        return self.net_node.link_up

    def set_link_up(self, v):
        self.net_node.link_up = v

    link_up = property(get_link_up, set_link_up)

    
    def create_subchannel(self, sub_channel_name):
        return Channel( self.channel_name + '.' + sub_channel_name, self.net_node )
    

class NetworkNode (object):


    def __init__(self, node_uid):

        self.node_uid         = node_uid
        self.zpax_nodes       = None # Dictionary of node_uid -> (rtr_addr, pub_addr)
        self.message_handlers = dict()
        self.link_up          = False


    def add_message_handler(self, channel_name, handler):
        if not channel_name in self.message_handlers:
            self.message_handlers[ channel_name ] = list()
        self.message_handlers[channel_name].append( handler )
        

    def connect(self, zpax_nodes):
        self.zpax_nodes        = zpax_nodes
        self.link_up           = True
        nodes[ self.node_uid ] = self
        

    def shutdown(self):
        self.link_up = False
        if self.node_uid in nodes:
            del nodes[ self.node_uid ]


    def _dispatch_message(self, from_uid, channel_name, message_type, parts):
        handlers = self.message_handlers.get(channel_name, None)
        if handlers:
            for h in handlers:
                f = getattr(h, 'receive_' + message_type, None)
                if f:
                    f(from_uid, *parts)
                    break


    def recv_message(self, src_uid, channel_name, message_type, parts):
        if self.link_up:
            if TRACE:
                print src_uid, '=>', self.node_uid, '[rcv]', '[{0}]'.format(channel_name), message_type.ljust(15), parts
            self._dispatch_message( src_uid, channel_name, message_type, parts )
        else:
            if TRACE:
                print src_uid, '=>', self.node_uid, '[drp]', '[{0}]'.format(channel_name), message_type.ljust(15), parts


    def broadcast_message(self, channel_name, message_type, *parts):
        if not self.link_up:
            return
        
        if len(parts) == 1 and isinstance(parts[0], (list, tuple)):
            parts = parts[0]
        if isinstance(parts, tuple):
            parts = list(parts)
        broadcast_message(self.node_uid, channel_name, message_type, parts)


    def unicast_message(self, to_uid, channel_name, message_type, *parts):
        if not self.link_up:
            return
        
        if len(parts) == 1 and isinstance(parts[0], (list, tuple)):
            parts = parts[0]
        if isinstance(parts, tuple):
            parts = list(parts)
        unicast_message(self.node_uid, to_uid, channel_name, message_type, parts)


########NEW FILE########
__FILENAME__ = zed
'''
zed is Twisted zmq (twist the second and third glyphs of zmq aound a bit and
you wind up with zed. Get it? Ha! I kill me....)

This module wraps the pyzmq interface in a thin layer that integrates with
the Twisted reactor. Unlike txZMQ (upon which this code is based) no
attempt is made to change the API to conform with Twisted norms. The
goal of this module is simply to integrate ZeroMQ sockets as-is into the
Twisted reactor.
'''

from collections import deque

from zmq.core         import constants, error
from zmq.core.socket  import Socket
from zmq.core.context import Context

from zope.interface import implements

from twisted.internet.interfaces import IFileDescriptor, IReadDescriptor
from twisted.internet import reactor
from twisted.python   import log

from zmq.core.constants import PUB, SUB, REQ, REP, PUSH, PULL, ROUTER, DEALER, PAIR


_context = None # ZmqContext singleton


POLL_IN_OUT = constants.POLLOUT & constants.POLLIN


def getContext():
    if _context is not None:
        return _context
    else:
        return _ZmqContext()

def _cleanup():
    global _context
    if _context:
        _context.shutdown()
    

class _ZmqContext(object):
    """
    This class wraps a ZeroMQ Context object and integrates it into the
    Twisted reactor framework.
    
    @cvar reactor: reference to Twisted reactor used by all the sockets

    @ivar sockets: set of instanciated L{ZmqSocket}s
    @type sockets: C{set}
    @ivar _zctx: ZeroMQ context
    @type _zctx: L{Context}
    """

    reactor = reactor

    def __init__(self, io_threads=1):
        """
        @param io_threads; Passed through to zmq.core.context.Context
        """
        global _context

        assert _context is None, 'Only one ZmqContext instance is permitted'
        
        self._sockets = set()
        self._zctx    = Context(io_threads)

        _context = self

        reactor.addSystemEventTrigger('during', 'shutdown', _cleanup)

    def shutdown(self):
        """
        Shutdown the ZeroMQ context and all associated sockets.
        """
        global _context

        if self._zctx is not None:
        
            for socket in self._sockets.copy():
                socket.close()

            self._sockets = None

            self._zctx.term()
            self._zctx = None

        _context = None
        



class ZmqSocket(object):
    """
    Wraps a ZeroMQ socket and integrates it into the Twisted reactor

    @ivar zsock: ZeroMQ Socket
    @type zsock: L{zmq.core.socket.Socket}
    @ivar queue: output message queue
    @type queue: C{deque}
    """
    implements(IReadDescriptor, IFileDescriptor)

    socketType = None
    
    def __init__(self, socketType=None):
        """
        @param context: Context this socket is to be associated with
        @type factory: L{ZmqFactory}
        @param socketType: Type of socket to create
        @type socketType: C{int}
        """
        if socketType is not None:
            self.socketType = socketType
            
        assert self.socketType is not None
        
        self._ctx   = getContext()
        self._zsock = Socket(getContext()._zctx, self.socketType)
        self._queue = deque()

        self.fd     = self._zsock.getsockopt(constants.FD)
        
        self._ctx._sockets.add(self)

        self._ctx.reactor.addReader(self)

        
    def _sockopt_property( i, totype=int):
        return property( lambda zs: zs._zsock.getsockopt(i),
                         lambda zs,v: zs._zsock.setsockopt(i,totype(v)) )

    
    linger     = _sockopt_property( constants.LINGER         )
    rate       = _sockopt_property( constants.RATE           )
    identity   = _sockopt_property( constants.IDENTITY,  str )
    subscribe  = _sockopt_property( constants.SUBSCRIBE, str )

    # Removed in 3.2
    #   mcast_loop = _sockopt_property( constants.MCAST_LOOP     )
    #   hwm        = _sockopt_property( constants.HWM            )

    def close(self):
        self._ctx.reactor.removeReader(self)

        self._ctx._sockets.discard(self)

        self._zsock.close()
        
        self._zsock = None
        self._ctx   = None


    def __repr__(self):
        t = _type_map[ self.socketType ].lower()
        t = t[0].upper() + t[1:]
        return "Zmq%sSocket(%s)" % (t, repr(self._zsock))


    def logPrefix(self):
        """
        Part of L{ILoggingContext}.

        @return: Prefix used during log formatting to indicate context.
        @rtype: C{str}
        """
        return 'ZMQ'


    def fileno(self):
        """
        Part of L{IFileDescriptor}.

        @return: The platform-specified representation of a file descriptor
                 number.
        """
        return self.fd

    
    def connectionLost(self, reason):
        """
        Called when the connection was lost. This will only be called during
        reactor shutdown with active ZeroMQ sockets.

        Part of L{IFileDescriptor}.

        """
        if self._ctx:
            self._ctx.reactor.removeReader(self)

    
    def doRead(self):
        """
        Some data is available for reading on your descriptor.

        ZeroMQ is signalling that we should process some events,
        we're starting to send queued messages and to receive
        incoming messages.

        Note that the ZeroMQ FD is used in an edge-triggered manner.
        Consequently, this function must read all pending messages
        before returning.

        Part of L{IReadDescriptor}.
        """
        if self._ctx is None:  # disconnected
                return

        while self._queue and self._zsock is not None:
            try:
                self._zsock.send_multipart( self._queue[0], constants.NOBLOCK )
                self._queue.popleft()
            except error.ZMQError as e:
                if e.errno == constants.EAGAIN:
                    break
                raise e
        
        while self._zsock is not None:
            try:
                msg_list = self._zsock.recv_multipart( constants.NOBLOCK )
                log.callWithLogger(self, self.messageReceived, msg_list)
            except error.ZMQError as e:
                if e.errno == constants.EAGAIN:
                    break
                
                # This exception can be thrown during socket closing process
                if e.errno == 156384763 or str(e) == 'Operation cannot be accomplished in current state':
                    break

                # Seen in 3.2 for an unknown reason
                if e.errno == 95:
                    break

                raise e
                

            
    
    def send(self, *message_parts):
        """
        Sends a ZeroMQ message. Each positional argument is converted into a message part
        """
        if len(message_parts) == 1 and isinstance(message_parts[0], (list, tuple)):
            message_parts = message_parts[0]

        self._queue.append( message_parts )
            
        self.doRead()


    def connect(self, addr):
        return self._zsock.connect(addr)

    
    def bind(self, addr):
        return self._zsock.bind(addr)

    
    def bindToRandomPort(self, addr, min_port=49152, max_port=65536, max_tries=100):
        return self._zsock.bind_to_random_port(addr, min_port, max_port, max_tries)

    
    def messageReceived(self, message_parts):
        """
        Called on incoming message from ZeroMQ.

        @param message_parts: list of message parts
        """
        raise NotImplementedError(self)


_type_map = dict( PUB    = PUB,
                  SUB    = SUB,
                  REQ    = REQ,
                  REP    = REP,
                  PUSH   = PUSH,
                  PULL   = PULL,
                  ROUTER = ROUTER,
                  DEALER = DEALER,
                  PAIR   = PAIR )

for k,v in _type_map.items():
    _type_map[v] = k

class ZmqPubSocket(ZmqSocket):
    socketType = PUB

class ZmqSubSocket(ZmqSocket):
    socketType = SUB

class ZmqReqSocket(ZmqSocket):
    socketType = REQ

class ZmqRepSocket(ZmqSocket):
    socketType = REP

class ZmqPushSocket(ZmqSocket):
    socketType = PUSH

class ZmqPullSocket(ZmqSocket):
    socketType = PULL

class ZmqRouterSocket(ZmqSocket):
    socketType = ROUTER

class ZmqDealerSocket(ZmqSocket):
    socketType = DEALER

class ZmqPairSocket(ZmqSocket):
    socketType = PAIR

########NEW FILE########
__FILENAME__ = zmq_node
'''
This module provides a NetworkNode implementation on top of ZeroMQ sockets.
'''

from twisted.internet import defer, task, reactor

from zpax.network import zed
from zpax.network.channel import Channel


class SimpleEncoder(object):
    '''
    An in-process "encoder" that is primarily useful for unit testing.
    '''
    def encode(self, node_uid, message_type, parts):
        return ['{0}\0{1}'.format(node_uid, message_type)] + list(parts)

    def decode(self, parts):
        from_uid, message_type = parts[0].split('\0')
        return from_uid, message_type, parts[1:]

    
        
class NetworkNode (object):
    '''
    Messages are handled by adding instances to the message_handlers list. The
    first instance that contains a method named 'receive_<message_type>'
    will have that method called. The first argument is always the message
    sender's node_uid. The remaining positional arguments are filled with the
    parts of the ZeroMQ message.
    '''

    def __init__(self, node_uid, encoder=SimpleEncoder()):

        self.node_uid         = node_uid

        self.zpax_nodes       = None # Dictionary of node_uid -> (rtr_addr, pub_addr)

        self.pax_rtr          = None
        self.pax_pub          = None
        self.pax_sub          = None
        self.encoder          = encoder
        self.message_handlers = dict() # Dictionary of channel_name => list( message_handlers )

        
    def add_message_handler(self, channel_name, handler):
        if not channel_name in self.message_handlers:
            self.message_handlers[ channel_name ] = list()
        self.message_handlers[channel_name].append( handler )
        

    def connect(self, zpax_nodes):
        '''
        zpax_nodes - Dictionary of node_uid => (zmq_rtr_addr, zmq_pub_addr)
        '''
        if not self.node_uid in zpax_nodes:
            raise Exception('Missing local node configuration')

        self.zpax_nodes = zpax_nodes
        
        if self.pax_rtr:
            self.pax_rtr.close()
            self.pax_pub.close()
            self.pax_sub.close()

        self.pax_rtr = zed.ZmqRouterSocket()
        self.pax_pub = zed.ZmqPubSocket()
        self.pax_sub = zed.ZmqSubSocket()

        self.pax_rtr.identity = self.node_uid
                    
        self.pax_rtr.linger = 0
        self.pax_pub.linger = 0
        self.pax_sub.linger = 0
        
        self.pax_rtr.bind(zpax_nodes[self.node_uid][0])
        self.pax_pub.bind(zpax_nodes[self.node_uid][1])

        self.pax_rtr.messageReceived = self._on_rtr_received
        self.pax_sub.messageReceived = self._on_sub_received

        self.pax_sub.subscribe = 'zpax'
        
        for node_uid, tpl in zpax_nodes.iteritems():
            self.pax_sub.connect(tpl[1])
                
            if self.node_uid < node_uid:
                # We only need 1 connection between any two router nodes so
                # we'll make it the responsibility of the lower UID node to
                # initiate the connection
                self.pax_rtr.connect(tpl[0])


    def shutdown(self):
        self.pax_rtr.close()
        self.pax_pub.close()
        self.pax_sub.close()
        self.pax_rtr = None
        self.pax_pub = None
        self.pax_sub = None


    def broadcast_message(self, channel_name, message_type, *parts):
        if len(parts) == 1 and isinstance(parts[0], (list, tuple)):
            parts = parts[0]
        l = ['zpax', channel_name]
        l.extend( self.encoder.encode(self.node_uid, message_type, parts) )
        self.pax_pub.send( l )


    def unicast_message(self, to_uid, channel_name, message_type, *parts):
        if to_uid == self.node_uid:
            self.dispatch_message( self.node_uid, channel_name, message_type, parts )
            return
        if len(parts) == 1 and isinstance(parts[0], (list, tuple)):
            parts = parts[0]
        l = [str(to_uid), channel_name]
        l.extend( self.encoder.encode(self.node_uid, message_type, parts) )
        self.pax_rtr.send( l )


    def _dispatch_message(self, from_uid, channel_name, message_type, parts):
        handlers = self.message_handlers.get(channel_name, None)
        if handlers:
            for h in handlers:
                f = getattr(h, 'receive_' + message_type, None)
                if f:
                    f(from_uid, *parts)
                    break
            
    def _on_rtr_received(self, raw_parts):
        # discard source address. We'll use the one embedded in the message
        # for consistency
        channel_name = raw_parts[1]
        from_uid, message_type, parts = self.encoder.decode( raw_parts[2:] )
        self._dispatch_message( from_uid, channel_name, message_type, parts )

        
    def _on_sub_received(self, raw_parts):
        # discard the message header. Can address targeted subscriptions
        # later
        channel_name = raw_parts[1]
        from_uid, message_type, parts = self.encoder.decode( raw_parts[2:] )
        self._dispatch_message( from_uid, channel_name, message_type, parts )

########NEW FILE########
