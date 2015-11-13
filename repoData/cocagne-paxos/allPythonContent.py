__FILENAME__ = durable
'''
This module implements a very simple mechanism for crash-proof storage
of an object's internal state.

The DurableObjectHandler class is given an object to durably persist along with
an object_id that is used to distinguish between multiple durable objects
persisted to the same directory. Whenever a savepoint is reached in the
application, the handler's save() method may be used to store the objects state
to disk. The application or machine is permitted to fail at any point. If
the failure occurs mid-write, the corruption will be detected by the
DurableObjectHandler constructor and the previously stored state will be
loaded.

This implementation does not reliably protect against on-disk corruption.  That
is to say, if the most-recently saved file is modified after it is successfully
written to the disk, such as through hardware or software errors, the saved
state will be permanently lost. As this implementation provides now way to
distinguish between files that failed to write and files that were
corrupted-on-disk, the implementation will assume the initial write failed and
will return the previously saved state (assuming it isn't similarly
corrupted). Consequently, there is a small but real chance that an application
may save its state with this implementation, make promises to external
entities, crash, and reneg on those promises after recovery. The likelyhood is,
of course, very very low so this implementation should be suitable for most
"good" reliability systems. Just don't implement a life-support system based on
this code...

Design Approach:

* Toggle writes between two different files
* Include a monotonically incrementing serial number in each write to
  allow determination of the most recent version
* md5sum the entire content of the data to be written and prefix the write
  with the digest
* fsync() after each write

'''

import os
import os.path
import hashlib
import struct

try:
    import cPickle as pickle
except ImportError:
    import pickle

# This module is primarily concerned with flushing data to the disk. The 
# default os.fsync goes a bit beyond that so os.fdatasync is used instead
# if it's available. Failing that, fcntl.fcntl(fd, fcntl.F_FULLSYNC) is
# attempted (OSX equivalent). Failing that, os.fsync is used (Windows).
#
_fsync = None

if hasattr(os, 'fdatasync'):
    _fsync = os.fdatasync

if _fsync is None:
    try:
        import fcntl
        if hasattr(fcntl, 'F_FULLFSYNC'):
            _fsync = lambda fd : fcntl.fcntl(fd, fcntl.F_FULLFSYNC)
    except (ImportError, AttributeError):
        pass

if _fsync is None:
    _fsync = os.fsync


# File format
#
#  0:  md5sum of file content
# 16:  serial_number
# 24:  pickle_length
# 32+: pickle_data

class DurabilityFailure (Exception):
    pass

class UnrecoverableFailure (DurabilityFailure):
    pass

class FileCorrupted (DurabilityFailure):
    pass

class HashMismatch (FileCorrupted):
    pass

class FileTruncated (FileCorrupted):
    pass



def read( fd ):
    '''
    Returns: (serial_number, unpickled_object) or raises a FileCorrupted exception
    '''
    os.lseek(fd, 0, os.SEEK_SET)
        
    md5hash       = os.read(fd, 16)
    data1         = os.read(fd, 8)
    data2         = os.read(fd, 8)
    
    if ( (not md5hash or len(md5hash) != 16) or
         (not data1   or len(data1)   !=  8) or
         (not data2   or len(data2)   !=  8) ):
        raise FileTruncated()
    
    serial_number = struct.unpack('>Q', data1)[0]
    pickle_length = struct.unpack('>Q', data2)[0]

    data3         = os.read(fd, pickle_length)

    if not data3 or len(data3) != pickle_length:
        raise FileTruncated()

    m = hashlib.md5()
    m.update( data1 )
    m.update( data2 )
    m.update( data3 )
    
    if not m.digest() == md5hash:
        raise HashMismatch()
    
    return serial_number, pickle.loads(data3)
    

    
def write( fd, serial_number, pyobject ):
    os.lseek(fd, 0, os.SEEK_SET)

    data_pickle = pickle.dumps(pyobject, pickle.HIGHEST_PROTOCOL)
    data_serial = struct.pack('>Q', serial_number)
    data_length = struct.pack('>Q', len(data_pickle))

    m = hashlib.md5()
    m.update( data_serial )
    m.update( data_length )
    m.update( data_pickle )

    os.write(fd, ''.join([m.digest(), data_serial, data_length, data_pickle]))

    _fsync(fd)


class DurableObjectHandler (object):
    
    def __init__(self, dirname, object_id):
        '''
        Throws UnrecoverableFailure if both files are corrupted
        '''
        
        if not os.path.isdir(dirname):
            raise Exception('Invalid directory: ' + dirname)

        sid = str(object_id)

        self.fn_a = os.path.join(dirname, sid + '_a.durable')
        self.fn_b = os.path.join(dirname, sid + '_b.durable')

        sync_dir = False
        
        if not os.path.exists(self.fn_a) or not os.path.exists(self.fn_b):
            sync_dir = True

        bin_flag = 0 if not hasattr(os, 'O_BINARY') else os.O_BINARY
        
        self.fd_a = os.open(self.fn_a, os.O_CREAT | os.O_RDWR | bin_flag)
        self.fd_b = os.open(self.fn_b, os.O_CREAT | os.O_RDWR | bin_flag)

        if sync_dir and hasattr(os, 'O_DIRECTORY'):
            fdd = os.open(dirname, os.O_DIRECTORY | os.O_RDONLY)
            os.fsync(fdd)
            os.close(fdd)

        self.recover()


    def recover(self):

        sa, sb, obja, objb = (None, None, None, None)
            
        try:
            sa, obja = read(self.fd_a)
        except FileCorrupted:
            pass

        try:
            sb, objb = read(self.fd_b)
        except FileCorrupted:
            pass

        if sa is not None and sb is not None:
            s, obj, fd = (sa, obja, self.fd_b) if sa > sb else (sb, objb, self.fd_a)
        else:
            s, obj, fd = (sa, obja, self.fd_b) if sa is not None else (sb, objb, self.fd_a)
                
        if s is None:
            if os.stat(self.fn_a).st_size == 0 and os.stat(self.fn_b).st_size == 0:
                self.serial    = 1
                self.fd_next   = self.fd_a
                self.recovered = None
            else:
                raise UnrecoverableFailure('Unrecoverable Durability failure')
            
        else:
            self.serial    = s + 1
            self.fd_next   = fd
            self.recovered = obj

        return self.recovered


    def close(self):
        if self.fd_a is not None:
            os.close(self.fd_a)
            os.close(self.fd_b)
            self.fd_a = None
            self.fd_b = None

            
    def save(self, obj):
        serial = self.serial
        fd     = self.fd_next
        
        self.serial += 1
        self.fd_next = self.fd_a if self.fd_next == self.fd_b else self.fd_b
        self.recovered = None
    
        write( fd, serial, obj )

        

########NEW FILE########
__FILENAME__ = essential
'''
This module provides a minimal implementation of the Paxos algorithm
that is independent of the underlying messaging mechanism. These
classes implement only the essential Paxos components and omit
the practical considerations (such as durability, message
retransmissions, NACKs, etc). 
'''

import collections

# In order for the Paxos algorithm to function, all proposal ids must be
# unique. A simple way to ensure this is to include the proposer's UID
# in the proposal id. This prevents the possibility of two Proposers
# from proposing different values for the same proposal ID.
#
# Python tuples are a simple mechanism that allow the proposal number
# and the UID to be combined easily and in a manner that supports
# comparison. To simplify the code, we'll use "namedtuple" instances
# from the collections module which allows us to write
# "proposal_id.number" instead of "proposal_id[0]".
#
ProposalID = collections.namedtuple('ProposalID', ['number', 'uid'])


class Messenger (object):
    def send_prepare(self, proposal_id):
        '''
        Broadcasts a Prepare message to all Acceptors
        '''

    def send_promise(self, proposer_uid, proposal_id, previous_id, accepted_value):
        '''
        Sends a Promise message to the specified Proposer
        '''

    def send_accept(self, proposal_id, proposal_value):
        '''
        Broadcasts an Accept! message to all Acceptors
        '''

    def send_accepted(self, proposal_id, accepted_value):
        '''
        Broadcasts an Accepted message to all Learners
        '''

    def on_resolution(self, proposal_id, value):
        '''
        Called when a resolution is reached
        '''


    
class Proposer (object):

    messenger            = None
    proposer_uid         = None
    quorum_size          = None

    proposed_value       = None
    proposal_id          = None 
    last_accepted_id     = None
    next_proposal_number = 1
    promises_rcvd        = None

    
    def set_proposal(self, value):
        '''
        Sets the proposal value for this node iff this node is not already aware of
        another proposal having already been accepted. 
        '''
        if self.proposed_value is None:
            self.proposed_value = value


    def prepare(self):
        '''
        Sends a prepare request to all Acceptors as the first step in attempting to
        acquire leadership of the Paxos instance. 
        '''
        self.promises_rcvd = set()
        self.proposal_id   = ProposalID(self.next_proposal_number, self.proposer_uid)
        
        self.next_proposal_number += 1

        self.messenger.send_prepare(self.proposal_id)

    
    def recv_promise(self, from_uid, proposal_id, prev_accepted_id, prev_accepted_value):
        '''
        Called when a Promise message is received from an Acceptor
        '''

        # Ignore the message if it's for an old proposal or we have already received
        # a response from this Acceptor
        if proposal_id != self.proposal_id or from_uid in self.promises_rcvd:
            return

        self.promises_rcvd.add( from_uid )
        
        if prev_accepted_id > self.last_accepted_id:
            self.last_accepted_id = prev_accepted_id
            # If the Acceptor has already accepted a value, we MUST set our proposal
            # to that value.
            if prev_accepted_value is not None:
                self.proposed_value = prev_accepted_value

        if len(self.promises_rcvd) == self.quorum_size:
            
            if self.proposed_value is not None:
                self.messenger.send_accept(self.proposal_id, self.proposed_value)


        
class Acceptor (object):

    messenger      = None    
    promised_id    = None
    accepted_id    = None
    accepted_value = None


    def recv_prepare(self, from_uid, proposal_id):
        '''
        Called when a Prepare message is received from a Proposer
        '''
        if proposal_id == self.promised_id:
            # Duplicate prepare message
            self.messenger.send_promise(from_uid, proposal_id, self.accepted_id, self.accepted_value)
        
        elif proposal_id > self.promised_id:
            self.promised_id = proposal_id
            self.messenger.send_promise(from_uid, proposal_id, self.accepted_id, self.accepted_value)

                    
    def recv_accept_request(self, from_uid, proposal_id, value):
        '''
        Called when an Accept! message is received from a Proposer
        '''
        if proposal_id >= self.promised_id:
            self.promised_id     = proposal_id
            self.accepted_id     = proposal_id
            self.accepted_value  = value
            self.messenger.send_accepted(proposal_id, self.accepted_value)


    
class Learner (object):

    quorum_size       = None

    proposals         = None # maps proposal_id => [accept_count, retain_count, value]
    acceptors         = None # maps from_uid => last_accepted_proposal_id
    final_value       = None
    final_proposal_id = None


    @property
    def complete(self):
        return self.final_proposal_id is not None


    def recv_accepted(self, from_uid, proposal_id, accepted_value):
        '''
        Called when an Accepted message is received from an acceptor
        '''
        if self.final_value is not None:
            return # already done

        if self.proposals is None:
            self.proposals = dict()
            self.acceptors = dict()
        
        last_pn = self.acceptors.get(from_uid)

        if not proposal_id > last_pn:
            return # Old message

        self.acceptors[ from_uid ] = proposal_id
        
        if last_pn is not None:
            oldp = self.proposals[ last_pn ]
            oldp[1] -= 1
            if oldp[1] == 0:
                del self.proposals[ last_pn ]

        if not proposal_id in self.proposals:
            self.proposals[ proposal_id ] = [0, 0, accepted_value]

        t = self.proposals[ proposal_id ]

        assert accepted_value == t[2], 'Value mismatch for single proposal!'
        
        t[0] += 1
        t[1] += 1

        if t[0] == self.quorum_size:
            self.final_value       = accepted_value
            self.final_proposal_id = proposal_id
            self.proposals         = None
            self.acceptors         = None

            self.messenger.on_resolution( proposal_id, accepted_value )

########NEW FILE########
__FILENAME__ = external
'''
This module extends practical.Node to support external failure detection.
'''
from paxos import practical

from paxos.practical import ProposalID


class ExternalMessenger (practical.Messenger):

    def send_leadership_proclamation(self):
        '''
        Sends a leadership proclamation to all nodes
        '''
    
    def on_leadership_lost(self):
        '''
        Called when loss of leadership is detected
        '''

    def on_leadership_change(self, prev_leader_uid, new_leader_uid):
        '''
        Called when a change in leadership is detected. Either UID may
        be None.
        '''

        
    
class ExternalNode (practical.Node):
    '''
    This implementation is completely passive. An external entity must monitor peer nodes
    for failure and call prepare() when the node should attempt to acquire leadership
    of the Paxos instance. Continual polling of the prepare() function and prevention
    of eternal leadership battles is also the responsibility of the caller.

    When leadership is acquired, the node will broadcast a leadership proclamation,
    delcaring itself the leader of the instance. This relieves peer nodes of the
    responsibility of tracking promises for all prepare messages.
    '''

    def __init__(self, messenger, my_uid, quorum_size, leader_uid=None):
        
        super(ExternalNode, self).__init__(messenger, my_uid, quorum_size)

        self.leader_uid          = leader_uid
        self.leader_proposal_id  = ProposalID(1, leader_uid)
        self._nacks              = set()

        if self.node_uid == leader_uid:
            self.leader                = True
            self.proposal_id           = ProposalID(self.next_proposal_number, self.node_uid)
            self.next_proposal_number += 1


    def prepare(self, *args, **kwargs):
        self._nacks.clear()
        return super(ExternalNode, self).prepare(*args, **kwargs)


    def recv_leadership_proclamation(self, from_uid, proposal_id):
        if proposal_id > self.leader_proposal_id:
            old_leader_uid = self.leader_uid
            
            self.leader_uid         = from_uid
            self.leader_proposal_id = proposal_id

            self.observe_proposal( from_uid, proposal_id )
            
            if old_leader_uid == self.node_uid:
                self.messenger.on_leadership_lost()
                
            self.messenger.on_leadership_change( old_leader_uid, from_uid )
        
        
    def recv_promise(self, acceptor_uid, proposal_id, prev_proposal_id, prev_proposal_value):

        pre_leader = self.leader
        
        super(ExternalNode, self).recv_promise(acceptor_uid, proposal_id, prev_proposal_id, prev_proposal_value)

        if not pre_leader and self.leader:
            old_leader_uid = self.leader_uid

            self.leader_uid         = self.node_uid
            self.leader_proposal_id = self.proposal_id
            
            self.messenger.send_leadership_proclamation( proposal_id )
            
            self.messenger.on_leadership_change( old_leader_uid, self.node_uid )

            
    def recv_accept_nack(self, from_uid, proposal_id, promised_id):
        if proposal_id == self.proposal_id:
            self._nacks.add(from_uid)

        if self.leader and len(self._nacks) >= self.quorum_size:
            self.leader             = False
            self.promises_rcvd      = set()
            self.leader_uid         = None
            self.leader_proposal_id = None
            self.messenger.on_leadership_lost()
            self.messenger.on_leadership_change(self.node_uid, None)
            self.observe_proposal( from_uid, promised_id )


########NEW FILE########
__FILENAME__ = functional
'''
This module provides a fully functional Paxos implementation based on a
simple heartbeating mechanism.
'''
import time

from paxos import practical

from paxos.practical import ProposalID


class HeartbeatMessenger (practical.Messenger):

    def send_heartbeat(self, leader_proposal_id):
        '''
        Sends a heartbeat message to all nodes
        '''

    def schedule(self, msec_delay, func_obj):
        '''
        While leadership is held, this method is called by pulse() to schedule
        the next call to pulse(). If this method is not overridden appropriately, 
        subclasses must use the on_leadership_acquired()/on_leadership_lost() callbacks
        to ensure that pulse() is called every hb_period while leadership is held.
        '''

    def on_leadership_lost(self):
        '''
        Called when loss of leadership is detected
        '''

    def on_leadership_change(self, prev_leader_uid, new_leader_uid):
        '''
        Called when a change in leadership is detected. Either UID may
        be None.
        '''

        
    
class HeartbeatNode (practical.Node):
    '''
    This class implements a Paxos node that provides a reasonable assurance of
    progress through a simple heartbeating mechanism that is used to detect
    leader failure and initiate leadership acquisition.

    If one or more heartbeat messages are not received within the
    'liveness_window', leadership acquisition will be attempted by sending out
    phase 1a, Prepare messages. If a quorum of replies acknowledging leadership
    is received, the node has successfully gained leadership and will begin
    sending out heartbeat messages. If a quorum is not received, the node will
    continually send a prepare every 'liveness_window' until either a quorum is
    established or a heartbeat with a proposal number greater than its own is
    received. The units for hb_period and liveness_window is seconds and floating
    point values may be used for sub-second precision.

    Leadership loss is detected by way of receiving a heartbeat message from a proposer
    with a higher proposal number (which must be obtained through a successful phase 1).
    Or by receiving a quorum of NACK responses to Accept! messages.

    This process does not modify the basic Paxos algorithm in any way, it merely seeks
    to ensure recovery from failures in leadership. Consequently, the basic Paxos
    safety mechanisms remain intact.
    '''

    hb_period       = 1
    liveness_window = 5

    timestamp       = time.time

    
    def __init__(self, messenger, my_uid, quorum_size, leader_uid=None,
                 hb_period=None, liveness_window=None):
        
        super(HeartbeatNode, self).__init__(messenger, my_uid, quorum_size)

        self.leader_uid          = leader_uid
        self.leader_proposal_id  = ProposalID(1, leader_uid)
        self._tlast_hb           = self.timestamp()
        self._tlast_prep         = self.timestamp()
        self._acquiring          = False
        self._nacks              = set()

        if hb_period:       self.hb_period       = hb_period
        if liveness_window: self.liveness_window = liveness_window

        if self.node_uid == leader_uid:
            self.leader                = True
            self.proposal_id           = ProposalID(self.next_proposal_number, self.node_uid)
            self.next_proposal_number += 1


    def prepare(self, *args, **kwargs):
        self._nacks.clear()
        return super(HeartbeatNode, self).prepare(*args, **kwargs)
        
        
    def leader_is_alive(self):
        return self.timestamp() - self._tlast_hb <= self.liveness_window


    def observed_recent_prepare(self):
        return self.timestamp() - self._tlast_prep <= self.liveness_window * 1.5

    
    def poll_liveness(self):
        '''
        Should be called every liveness_window. This method checks to see if the
        current leader is active and, if not, will begin the leadership acquisition
        process.
        '''
        if not self.leader_is_alive() and not self.observed_recent_prepare():
            if self._acquiring:
                self.prepare()
            else:
                self.acquire_leadership()

            
    def recv_heartbeat(self, from_uid, proposal_id):

        if proposal_id > self.leader_proposal_id:
            # Change of leadership            
            self._acquiring = False
            
            old_leader_uid = self.leader_uid

            self.leader_uid         = from_uid
            self.leader_proposal_id = proposal_id

            if self.leader and from_uid != self.node_uid:
                self.leader = False
                self.messenger.on_leadership_lost()
                self.observe_proposal( from_uid, proposal_id )

            self.messenger.on_leadership_change( old_leader_uid, from_uid )

        if self.leader_proposal_id == proposal_id:
            self._tlast_hb = self.timestamp()
                
            
    def pulse(self):
        '''
        Must be called every hb_period while this node is the leader
        '''
        if self.leader:
            self.recv_heartbeat(self.node_uid, self.proposal_id)
            self.messenger.send_heartbeat(self.proposal_id)
            self.messenger.schedule(self.hb_period, self.pulse)

            
    def acquire_leadership(self):
        '''
        Initiates the leadership acquisition process if the current leader
        appears to have failed.
        '''
        if self.leader_is_alive():
            self._acquiring = False

        else:
            self._acquiring = True
            self.prepare()


    def recv_prepare(self, node_uid, proposal_id):
        super(HeartbeatNode, self).recv_prepare( node_uid, proposal_id )
        if node_uid != self.node_uid:
            self._tlast_prep = self.timestamp()
    
        
    def recv_promise(self, acceptor_uid, proposal_id, prev_proposal_id, prev_proposal_value):

        pre_leader = self.leader
        
        super(HeartbeatNode, self).recv_promise(acceptor_uid, proposal_id, prev_proposal_id, prev_proposal_value)

        if not pre_leader and self.leader:
            old_leader_uid = self.leader_uid

            self.leader_uid         = self.node_uid
            self.leader_proposal_id = self.proposal_id
            self._acquiring         = False
            self.pulse()
            self.messenger.on_leadership_change( old_leader_uid, self.node_uid )

            
    def recv_prepare_nack(self, from_uid, proposal_id, promised_id):
        super(HeartbeatNode, self).recv_prepare_nack(from_uid, proposal_id, promised_id)
        if self._acquiring:
            self.prepare()


    def recv_accept_nack(self, from_uid, proposal_id, promised_id):
        if proposal_id == self.proposal_id:
            self._nacks.add(from_uid)

        if self.leader and len(self._nacks) >= self.quorum_size:
            self.leader             = False
            self.promises_rcvd      = set()
            self.leader_uid         = None
            self.leader_proposal_id = None
            self.messenger.on_leadership_lost()
            self.messenger.on_leadership_change(self.node_uid, None)
            self.observe_proposal( from_uid, promised_id )


    

########NEW FILE########
__FILENAME__ = practical
'''
This module builds upon the essential Paxos implementation and adds
functionality required for most practical uses of the algorithm. 
'''
from paxos import essential

from paxos.essential import ProposalID


class Messenger (essential.Messenger):
    
    def send_prepare_nack(self, to_uid, proposal_id, promised_id):
        '''
        Sends a Prepare Nack message for the proposal to the specified node
        '''

    def send_accept_nack(self, to_uid, proposal_id, promised_id):
        '''
        Sends a Accept! Nack message for the proposal to the specified node
        '''

    def on_leadership_acquired(self):
        '''
        Called when leadership has been aquired. This is not a guaranteed
        position. Another node may assume leadership at any time and it's
        even possible that another may have successfully done so before this
        callback is exectued. Use this method with care.

        The safe way to guarantee leadership is to use a full Paxos instance
        whith the resolution value being the UID of the leader node. To avoid
        potential issues arising from timing and/or failure, the election
        result may be restricted to a certain time window. Prior to the end of
        the window the leader may attempt to re-elect itself to extend it's
        term in office.
        '''

        
class Proposer (essential.Proposer):
    '''
    This class extends the functionality of the essential Proposer
    implementation by tracking whether the proposer believes itself to
    be the current leader of the Paxos instance. It also supports a flag
    to disable active paritcipation in the Paxos instance.

    The 'leader' attribute is a boolean value indicating the Proposer's
    belief in whether or not it is the current leader. As the documentation
    for the Messenger.on_leadership_acquired() method describes, multiple
    nodes may simultaneously believe themselves to be the leader.

    The 'active' attribute is a boolean value indicating whether or not
    the Proposer should send outgoing messages (defaults to True). Setting
    this attribute to false places the Proposer in a "passive" mode where
    it processes all incoming messages but drops all messages it would
    otherwise send. 
    '''
    
    leader = False 
    active = True  

    
    def set_proposal(self, value):
        '''
        Sets the proposal value for this node iff this node is not already aware of
        another proposal having already been accepted. 
        '''
        if self.proposed_value is None:
            self.proposed_value = value

            if self.leader and self.active:
                self.messenger.send_accept( self.proposal_id, value )


    def prepare(self, increment_proposal_number=True):
        '''
        Sends a prepare request to all Acceptors as the first step in
        attempting to acquire leadership of the Paxos instance. If the
        'increment_proposal_number' argument is True (the default), the
        proposal id will be set higher than that of any previous observed
        proposal id. Otherwise the previously used proposal id will simply be
        retransmitted.
        '''
        if increment_proposal_number:
            self.leader        = False
            self.promises_rcvd = set()
            self.proposal_id   = (self.next_proposal_number, self.proposer_uid)
        
            self.next_proposal_number += 1

        if self.active:
            self.messenger.send_prepare(self.proposal_id)

    
    def observe_proposal(self, from_uid, proposal_id):
        '''
        Optional method used to update the proposal counter as proposals are
        seen on the network.  When co-located with Acceptors and/or Learners,
        this method may be used to avoid a message delay when attempting to
        assume leadership (guaranteed NACK if the proposal number is too low).
        '''
        if from_uid != self.proposer_uid:
            if proposal_id >= (self.next_proposal_number, self.proposer_uid):
                self.next_proposal_number = proposal_id.number + 1

            
    def recv_prepare_nack(self, from_uid, proposal_id, promised_id):
        '''
        Called when an explicit NACK is sent in response to a prepare message.
        '''
        self.observe_proposal( from_uid, promised_id )

    
    def recv_accept_nack(self, from_uid, proposal_id, promised_id):
        '''
        Called when an explicit NACK is sent in response to an accept message
        '''

        
    def resend_accept(self):
        '''
        Retransmits an Accept! message iff this node is the leader and has
        a proposal value
        '''
        if self.leader and self.proposed_value and self.active:
            self.messenger.send_accept(self.proposal_id, self.proposed_value)


    def recv_promise(self, from_uid, proposal_id, prev_accepted_id, prev_accepted_value):
        '''
        Called when a Promise message is received from the network
        '''
        self.observe_proposal( from_uid, proposal_id )

        if self.leader or proposal_id != self.proposal_id or from_uid in self.promises_rcvd:
            return

        self.promises_rcvd.add( from_uid )
        
        if prev_accepted_id > self.last_accepted_id:
            self.last_accepted_id = prev_accepted_id
            # If the Acceptor has already accepted a value, we MUST set our proposal
            # to that value. Otherwise, we may retain our current value.
            if prev_accepted_value is not None:
                self.proposed_value = prev_accepted_value

        if len(self.promises_rcvd) == self.quorum_size:
            self.leader = True

            self.messenger.on_leadership_acquired()
            
            if self.proposed_value is not None and self.active:
                self.messenger.send_accept(self.proposal_id, self.proposed_value)


                
class Acceptor (essential.Acceptor):
    '''
    Acceptors act as the fault-tolerant memory for Paxos. To ensure correctness
    in the presense of failure, Acceptors must be able to remember the promises
    they've made even in the event of power outages. Consequently, any changes
    to the promised_id, accepted_id, and/or accepted_value must be persisted to
    stable media prior to sending promise and accepted messages. After calling
    the recv_prepare() and recv_accept_request(), the property
    'persistence_required' should be checked to see if persistence is required.

    Note that because Paxos permits any combination of dropped packets, not
    every promise/accepted message needs to be sent. This implementation only
    responds to the first prepare/accept_request message received and ignores
    all others until the Acceptor's values are persisted to stable media (which
    is typically a slow process). After saving the promised_id, accepted_id,
    and accepted_value variables, the "persisted" method must be called to send
    the pending promise and/or accepted messages.

    The 'active' attribute is a boolean value indicating whether or not
    the Acceptor should send outgoing messages (defaults to True). Setting
    this attribute to false places the Acceptor in a "passive" mode where
    it processes all incoming messages but drops all messages it would
    otherwise send. 
    '''

    pending_promise  = None # None or the UID to send a promise message to
    pending_accepted = None # None or the UID to send an accepted message to
    active           = True
    
    
    @property
    def persistance_required(self):
        return self.pending_promise is not None or self.pending_accepted is not None


    def recover(self, promised_id, accepted_id, accepted_value):
        self.promised_id    = promised_id
        self.accepted_id    = accepted_id
        self.accepted_value = accepted_value
    

    def recv_prepare(self, from_uid, proposal_id):
        '''
        Called when a Prepare message is received from the network
        '''
        if proposal_id == self.promised_id:
            # Duplicate prepare message. No change in state is necessary so the response
            # may be sent immediately
            if self.active:
                self.messenger.send_promise(from_uid, proposal_id, self.accepted_id, self.accepted_value)
        
        elif proposal_id > self.promised_id:
            if self.pending_promise is None:
                self.promised_id = proposal_id
                if self.active:
                    self.pending_promise = from_uid

        else:
            if self.active:
                self.messenger.send_prepare_nack(from_uid, proposal_id, self.promised_id)

                    
    def recv_accept_request(self, from_uid, proposal_id, value):
        '''
        Called when an Accept! message is received from the network
        '''
        if proposal_id == self.accepted_id and value == self.accepted_value:
            # Duplicate accepted proposal. No change in state is necessary so the response
            # may be sent immediately
            if self.active:
                self.messenger.send_accepted(proposal_id, value)
            
        elif proposal_id >= self.promised_id:
            if self.pending_accepted is None:
                self.promised_id      = proposal_id
                self.accepted_value   = value
                self.accepted_id      = proposal_id
                if self.active:
                    self.pending_accepted = from_uid
            
        else:
            if self.active:
                self.messenger.send_accept_nack(from_uid, proposal_id, self.promised_id)


    def persisted(self):
        '''
        This method sends any pending Promise and/or Accepted messages. Prior to
        calling this method, the application must ensure that the promised_id
        accepted_id, and accepted_value variables have been persisted to stable
        media.
        '''
        if self.active:
            
            if self.pending_promise:
                self.messenger.send_promise(self.pending_promise,
                                            self.promised_id,
                                            self.accepted_id,
                                            self.accepted_value)
                
            if self.pending_accepted:
                self.messenger.send_accepted(self.accepted_id,
                                             self.accepted_value)
                
        self.pending_promise  = None
        self.pending_accepted = None


        
class Learner (essential.Learner):
    '''
    This class extends the base in track which peers have accepted the final value.
    on_resolution() is still called only once. At the time of the call, the
    final_acceptors member variable will contain exactly quorum_size uids. Subsequent
    calls to recv_accepted will add the uid of the sender if the accepted_value
    matches the final_value. 
    '''
    final_acceptors = None
    
    def recv_accepted(self, from_uid, proposal_id, accepted_value):
        '''
        Called when an Accepted message is received from an acceptor
        '''
        if self.final_value is not None:
            if accepted_value == self.final_value:
                self.final_acceptors.add( from_uid )
            return # already done
            
        if self.proposals is None:
            self.proposals = dict()
            self.acceptors = dict()
            
        last_pn = self.acceptors.get(from_uid)

        if not proposal_id > last_pn:
            return # Old message

        self.acceptors[ from_uid ] = proposal_id
        
        if last_pn is not None:
            oldp = self.proposals[ last_pn ]
            oldp[1].remove( from_uid )
            if len(oldp[1]) == 0:
                del self.proposals[ last_pn ]

        if not proposal_id in self.proposals:
            self.proposals[ proposal_id ] = [set(), set(), accepted_value]

        t = self.proposals[ proposal_id ]

        assert accepted_value == t[2], 'Value mismatch for single proposal!'
        
        t[0].add( from_uid )
        t[1].add( from_uid )

        if len(t[0]) == self.quorum_size:
            self.final_value       = accepted_value
            self.final_proposal_id = proposal_id
            self.final_acceptors   = t[0]
            self.proposals         = None
            self.acceptors         = None

            self.messenger.on_resolution( proposal_id, accepted_value )

            

    
class Node (Proposer, Acceptor, Learner):
    '''
    This class supports the common model where each node on a network preforms
    all three Paxos roles, Proposer, Acceptor, and Learner.
    '''

    def __init__(self, messenger, node_uid, quorum_size):
        self.messenger   = messenger
        self.node_uid    = node_uid
        self.quorum_size = quorum_size


    @property
    def proposer_uid(self):
        return self.node_uid
            

    def change_quorum_size(self, quorum_size):
        self.quorum_size = quorum_size

        
    def recv_prepare(self, from_uid, proposal_id):
        self.observe_proposal( from_uid, proposal_id )
        return super(Node,self).recv_prepare( from_uid, proposal_id )



########NEW FILE########
__FILENAME__ = java_test_essential
#!/usr/bin/env jython

import sys
import os.path
import unittest

#sys.path.append
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append( os.path.join(os.path.dirname(this_dir),'bin') )

from cocagne.paxos.essential import ProposalID
from cocagne.paxos import essential

import test_essential

def PID(proposalID):
    if proposalID is not None:
        return test_essential.PID(proposalID.getNumber(), proposalID.getUID())

class MessengerAdapter (object):

    def sendPrepare(self, proposalID):
        self.send_prepare(PID(proposalID))

    def sendPromise(self, proposerUID, proposalID, previousID, acceptedValue):
        self.send_promise(proposerUID, PID(proposalID), PID(previousID), acceptedValue)

    def sendAccept(self, proposalID, proposalValue):
        self.send_accept(PID(proposalID), proposalValue)

    def sendAccepted(self, proposalID, acceptedValue):
        self.send_accepted(PID(proposalID), acceptedValue)
    
    def onResolution(self, proposalID, value):
        self.on_resolution(PID(proposalID), value)


class EssentialMessengerAdapter(MessengerAdapter, essential.EssentialMessenger, test_essential.EssentialMessenger):
    pass



class ProposerAdapter(object):

    @property
    def proposer_uid(self):
        return self.getProposerUID()

    @property
    def quorum_size(self):
        return self.getQuorumSize()
    
    @property
    def proposed_value(self):
        return self.getProposedValue()
    
    @property
    def proposal_id(self):
        return PID(self.getProposalID())

    @property
    def last_accepted_id(self):
        return PID(self.getLastAcceptedID())

    def set_proposal(self, value):
        self.setProposal(value)
        
    def recv_promise(self, from_uid, proposal_id, prev_accepted_id, prev_accepted_value):
        if prev_accepted_id is not None:
            prev_accepted_id = essential.ProposalID(prev_accepted_id.number, prev_accepted_id.uid)

        self.receivePromise(from_uid, essential.ProposalID(proposal_id.number, proposal_id.uid),
                            prev_accepted_id, prev_accepted_value)


        
class AcceptorAdapter(object):

    @property
    def promised_id(self):
        return PID(self.getPromisedID())

    @property
    def accepted_id(self):
        return PID(self.getAcceptedID())

    @property
    def accepted_value(self):
        return self.getAcceptedValue()

    def recv_prepare(self, from_uid, proposal_id):
        self.receivePrepare(from_uid, essential.ProposalID(proposal_id.number, proposal_id.uid))

    def recv_accept_request(self, from_uid, proposal_id, value):
        self.receiveAcceptRequest(from_uid, essential.ProposalID(proposal_id.number, proposal_id.uid), value)



class LearnerAdapter(object):

    @property
    def quorum_size(self):
        return self.getQuorumSize()

    @property
    def complete(self):
        return self.isComplete()

    @property
    def final_value(self):
        return self.getFinalValue()

    @property
    def final_proposal_id(self):
        return PID(self.getFinalProposalID())

    def recv_accepted(self, from_uid, proposal_id, accepted_value):
        self.receiveAccepted(from_uid,
                             essential.ProposalID(proposal_id.number, proposal_id.uid),
                             accepted_value)

        
class EssentialProposerAdapter(essential.EssentialProposerImpl, ProposerAdapter):
    pass

class EssentialAcceptorAdapter(essential.EssentialAcceptorImpl, AcceptorAdapter):
    pass

class EssentialLearnerAdapter(essential.EssentialLearnerImpl, LearnerAdapter):
    pass

        
class EssentialProposerTester(test_essential.EssentialProposerTests, EssentialMessengerAdapter, unittest.TestCase):

    def __init__(self, test_name):
        unittest.TestCase.__init__(self, test_name)
        
    def proposer_factory(self, messenger, uid, quorum_size):
        return EssentialProposerAdapter(messenger, uid, quorum_size)


class EssentialAcceptorTester(test_essential.EssentialAcceptorTests, EssentialMessengerAdapter, unittest.TestCase):

    def __init__(self, test_name):
        unittest.TestCase.__init__(self, test_name)
        
    def acceptor_factory(self, messenger, uid, quorum_size):
        return EssentialAcceptorAdapter(messenger)


class EssentialLearnerTester(test_essential.EssentialLearnerTests, EssentialMessengerAdapter, unittest.TestCase):

    def __init__(self, test_name):
        unittest.TestCase.__init__(self, test_name)
        
    def learner_factory(self, messenger, uid, quorum_size):
        return EssentialLearnerAdapter(messenger, quorum_size)



    
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = java_test_functional
#!/usr/bin/env jython

import sys
import os.path
import unittest

#sys.path.append
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append( os.path.join(os.path.dirname(this_dir),'bin') )

from cocagne.paxos.essential import ProposalID
from cocagne.paxos import essential, practical, functional

import test_essential
import test_practical
import test_functional
import java_test_essential
import java_test_practical

from java_test_essential import PID


def JPID(pid):
    return essential.ProposalID(pid.number, pid.uid) if pid is not None else None


class MessengerAdapter (java_test_practical.MessengerAdapter):

    def sendPrepareNACK(self, proposerUID, proposalID, promisedID):
        self.send_prepare_nack(proposerUID, PID(proposalID), PID(promisedID))

    def sendAcceptNACK(self, proposerUID, proposalID, promisedID):
        self.send_accept_nack(proposerUID, PID(proposalID), PID(promisedID))

    def onLeadershipAcquired(self):
        self.on_leadership_acquired()

    def sendHeartbeat(self, leaderProposalID):
        self.send_heartbeat(leaderProposalID)

    def schedule(self, millisecondDelay, callback):
        self._do_schedule(millisecondDelay, lambda : callback.execute())

    def onLeadershipLost(self):
        self.on_leadership_lost()

    def onLeadershipChange(self, previousLeaderUID, newLeaderUID):
        self.on_leadership_change(previousLeaderUID, newLeaderUID)


class HeartbeatMessengerAdapter(MessengerAdapter, functional.HeartbeatMessenger, test_functional.HeartbeatMessenger):
    def _do_schedule(self, ms, cb):
        test_functional.HeartbeatMessenger.schedule(self, ms, cb)


class HNode(functional.HeartbeatNode, java_test_practical.GenericProposerAdapter, java_test_practical.GenericAcceptorAdapter, java_test_essential.LearnerAdapter):
    hb_period       = 2
    liveness_window = 6

    def __init__(self, messenger, uid, quorum):
        functional.HeartbeatNode.__init__(self, messenger, uid, quorum, None, 2, 6)

    @property
    def leader_uid(self):
        return self.getLeaderUID()

    @property
    def proposal_id(self):
        pid = PID(self.getProposalID())
        if pid is not None and pid.number == 0:
            return None
        return pid

    @property
    def leader_proposal_id(self):
        return PID(self.getLeaderProposalID())

    @leader_proposal_id.setter
    def leader_proposal_id(self, value):
        self.setLeaderProposalID( JPID(value) )

    @property
    def _acquiring(self):
        return self.isAcquiringLeadership()

    def timestamp(self):
        return self.messenger.timestamp()

    def leader_is_alive(self):
        return self.leaderIsAlive()

    def observed_recent_prepare(self):
        return self.observedRecentPrepare()
    
    def poll_liveness(self):
        self.pollLiveness()

    def recv_heartbeat(self, from_uid, proposal_id):
        self.receiveHeartbeat(from_uid, JPID(proposal_id))

    def acquire_leadership(self):
        self.acquireLeadership()


class HeartbeatTester(test_functional.HeartbeatTests, HeartbeatMessengerAdapter, unittest.TestCase):
    node_factory = HNode

    def __init__(self, test_name):
        unittest.TestCase.__init__(self, test_name)

    def setUp(self):
        super(HeartbeatTester,self).setUp()
        self.msetup()
        self.create_node()



class NodeProposerAdapter(functional.HeartbeatNode, java_test_practical.GenericProposerAdapter):
    pass

class NodeAcceptorAdapter(functional.HeartbeatNode, java_test_practical.GenericAcceptorAdapter):
    def recover(self, promised_id, accepted_id, accepted_value):
        functional.HeartbeatNode.recover(self, JPID(promised_id), JPID(accepted_id), accepted_value)

class NodeLearnerAdapter(functional.HeartbeatNode, java_test_essential.LearnerAdapter):
    pass


class HeartbeatNodeProposerTester(test_practical.PracticalProposerTests, HeartbeatMessengerAdapter, unittest.TestCase):

    def __init__(self, test_name):
        unittest.TestCase.__init__(self, test_name)
        
    def proposer_factory(self, messenger, uid, quorum_size):
        return NodeProposerAdapter(messenger, uid, quorum_size, None, 1, 5)

    def setUp(self):
        super(HeartbeatNodeProposerTester,self).setUp()
        self.msetup()

class HeartbeatNodeAcceptorTester(test_practical.PracticalAcceptorTests, HeartbeatMessengerAdapter, unittest.TestCase):

    def __init__(self, test_name):
        unittest.TestCase.__init__(self, test_name)
        
    def acceptor_factory(self, messenger, uid, quorum_size):
        return NodeAcceptorAdapter(messenger, uid, quorum_size, None, 1, 5)

    def setUp(self):
        super(HeartbeatNodeAcceptorTester,self).setUp()
        self.msetup()

class HeartbeatNodeLearnerTester(test_practical.PracticalLearnerTests, HeartbeatMessengerAdapter, unittest.TestCase):

    def __init__(self, test_name):
        unittest.TestCase.__init__(self, test_name)
        
    def learner_factory(self, messenger, uid, quorum_size):
        return NodeLearnerAdapter(messenger, uid, quorum_size, None, 1, 5)

    def setUp(self):
        super(HeartbeatNodeLearnerTester,self).setUp()
        self.msetup()


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = java_test_practical
#!/usr/bin/env jython

import sys
import os.path
import unittest

#sys.path.append
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append( os.path.join(os.path.dirname(this_dir),'bin') )

from cocagne.paxos.essential import ProposalID
from cocagne.paxos import practical, essential

import test_essential
import test_practical
import java_test_essential

from java_test_essential import PID

def JPID(pid):
    return essential.ProposalID(pid.number, pid.uid) if pid is not None else None


class MessengerAdapter (java_test_essential.MessengerAdapter):

    def sendPrepareNACK(self, proposerUID, proposalID, promisedID):
        self.send_prepare_nack(proposerUID, PID(proposalID), PID(promisedID))

    def sendAcceptNACK(self, proposerUID, proposalID, promisedID):
        self.send_accept_nack(proposerUID, PID(proposalID), PID(promisedID))

    def onLeadershipAcquired(self):
        self.on_leadership_acquired()


class PracticalMessengerAdapter(MessengerAdapter, practical.PracticalMessenger, test_practical.PracticalMessenger):
    pass





class GenericProposerAdapter(java_test_essential.ProposerAdapter):

    @property
    def leader(self):
        return self.isLeader()

    @leader.setter
    def leader(self, value):
        self.setLeader(value)

    @property
    def active(self):
        return self.isActive()

    @active.setter
    def active(self, value):
        self.setActive(value)

    def observe_proposal(self, from_uid, proposal_id):
        self.observeProposal(from_uid, JPID(proposal_id))

    def recv_prepare_nack(self, from_uid, proposal_id, promised_id):
        self.receivePrepareNACK(from_uid, JPID(proposal_id), JPID(promised_id))

    def recv_accept_nack(self, from_uid, proposal_id, promised_id):
        self.receiveAcceptNACK(from_uid, JPID(proposal_id), JPID(promised_id))

    def resend_accept(self):
        self.resendAccept()


class ProposerAdapter(practical.PracticalProposerImpl, GenericProposerAdapter):
    pass

class NodeProposerAdapter(practical.PracticalNode, GenericProposerAdapter):
    pass


class GenericAcceptorAdapter(test_practical.AutoSaveMixin, java_test_essential.AcceptorAdapter):

    @property
    def active(self):
        return self.isActive()

    @active.setter
    def active(self, value):
        self.setActive(value)

    @property
    def persistance_required(self):
        return self.persistenceRequired()

    #def recover(self, promised_id, accepted_id, accepted_value):
    #    practical.PracticalAcceptor.recover(self, JPID(promised_id), JPID(accepted_id), accepted_value)


class AcceptorAdapter(practical.PracticalAcceptorImpl, GenericAcceptorAdapter):
    def recover(self, promised_id, accepted_id, accepted_value):
        practical.PracticalAcceptor.recover(self, JPID(promised_id), JPID(accepted_id), accepted_value)


class NodeAcceptorAdapter(practical.PracticalNode, GenericAcceptorAdapter):
    def recover(self, promised_id, accepted_id, accepted_value):
        practical.PracticalNode.recover(self, JPID(promised_id), JPID(accepted_id), accepted_value)


class PracticalProposerTester(test_practical.PracticalProposerTests, PracticalMessengerAdapter, unittest.TestCase):

    def __init__(self, test_name):
        unittest.TestCase.__init__(self, test_name)
        
    def proposer_factory(self, messenger, uid, quorum_size):
        return ProposerAdapter(messenger, uid, quorum_size)


class PracticalAcceptorTester(test_practical.PracticalAcceptorTests, PracticalMessengerAdapter, unittest.TestCase):

    def __init__(self, test_name):
        unittest.TestCase.__init__(self, test_name)
        
    def acceptor_factory(self, messenger, uid, quorum_size):
        return AcceptorAdapter(messenger)


class PracticalNodeProposerTester(test_practical.PracticalProposerTests, PracticalMessengerAdapter, unittest.TestCase):

    def __init__(self, test_name):
        unittest.TestCase.__init__(self, test_name)
        
    def proposer_factory(self, messenger, uid, quorum_size):
        return NodeProposerAdapter(messenger, uid, quorum_size)


class PracticalNodeAcceptorTester(test_practical.PracticalAcceptorTests, PracticalMessengerAdapter, unittest.TestCase):

    def __init__(self, test_name):
        unittest.TestCase.__init__(self, test_name)
        
    def acceptor_factory(self, messenger, uid, quorum_size):
        return NodeAcceptorAdapter(messenger, uid, quorum_size)


    

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_durable

import sys
import os
import os.path
import hashlib
import struct
import tempfile
import shutil
import pickle

#from twisted.trial import unittest
import unittest

this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append( os.path.dirname(this_dir) )

from paxos import durable


class DObj(object):

    def __init__(self):
        self.state = 'initial'
        

        
class DurableReadTester (unittest.TestCase):

    
    def setUp(self):
        tmpfs_dir = '/dev/shm' if os.path.exists('/dev/shm') else None
        self.tdir   = tempfile.mkdtemp(dir=tmpfs_dir)
        self.fds    = list()

        
    def tearDown(self):
        shutil.rmtree(self.tdir)
        for fd in self.fds:
            os.close(fd)


    def newfd(self, data=None):
        bin_flag = 0 if not hasattr(os, 'O_BINARY') else os.O_BINARY
        
        fd = os.open( os.path.join(self.tdir, str(len(self.fds))),  os.O_CREAT | os.O_RDWR | bin_flag)

        self.fds.append( fd )

        if data is not None:
            os.write(fd, data)

        return fd
        
        
    def test_read_zero_length(self):
        self.assertRaises(durable.FileTruncated, durable.read, self.newfd())

    def test_read_header_too_small(self):
        self.assertRaises(durable.FileTruncated, durable.read, self.newfd('\0'*31))

    def test_read_no_pickle_data(self):
        data = '\0'*24 + struct.pack('>Q', 5)
        self.assertRaises(durable.FileTruncated, durable.read, self.newfd(data))

    def test_read_bad_hash_mismatch(self):
        data = '\0'*24 + struct.pack('>Q', 5) + 'x'*5
        self.assertRaises(durable.HashMismatch, durable.read, self.newfd(data))

    def test_read_ok(self):
        pdata = 'x'*5
        p     = pickle.dumps(pdata, pickle.HIGHEST_PROTOCOL)
        data  = '\0'*8 + struct.pack('>Q', len(p)) + p
        data  = hashlib.md5(data).digest() + data
        self.assertEqual( durable.read(self.newfd(data) ), (0, pdata) )
        
        

class DurableObjectHandlerTester (unittest.TestCase):

    
    def setUp(self):
        tmpfs_dir = '/dev/shm' if os.path.exists('/dev/shm') else None
        self.o      = DObj()
        self.tdir   = tempfile.mkdtemp(dir=tmpfs_dir)
        self.doh    = durable.DurableObjectHandler(self.tdir, 'id1')

        self.dohs   = [self.doh,]

        
    def tearDown(self):
        for doh in self.dohs:
            doh.close()
        shutil.rmtree(self.tdir)
        

    def newdoh(self, obj_id=None):
        if obj_id is None:
            obj_id = 'id' + str(len(self.dohs))
        doh = durable.DurableObjectHandler(self.tdir, obj_id)
        self.dohs.append(doh)
        return doh


    def test_bad_directory(self):
        self.assertRaises(Exception, durable.DurableObjectHandler, '/@#$!$^FOOBARBAZ', 'blah')
        

    def test_no_save(self):
        self.doh.close()
        d = self.newdoh('id1')
        self.assertEquals(d.recovered, None)
        self.assertEquals(d.serial, 1)

    def test_one_save(self):
        self.doh.save(self.o)
        self.doh.close()
        d = self.newdoh('id1')
        self.assertTrue( os.stat(self.doh.fn_a).st_size > 0 )
        self.assertTrue( os.stat(self.doh.fn_b).st_size == 0 )
        self.assertTrue( isinstance(d.recovered, DObj) )
        self.assertEquals(d.recovered.state, 'initial')


    def test_two_save(self):
        self.doh.save(self.o)
        self.o.state = 'second'
        self.doh.save(self.o)
        self.doh.close()
        d = self.newdoh('id1')
        self.assertTrue( os.stat(self.doh.fn_a).st_size > 0 )
        self.assertTrue( os.stat(self.doh.fn_b).st_size > 0 )
        self.assertTrue( isinstance(d.recovered, DObj) )
        self.assertEquals(d.recovered.state, 'second')

    def test_three_save(self):
        self.doh.save(self.o)
        self.o.state = 'second'
        self.doh.save(self.o)
        self.o.state = 'third'
        self.doh.save(self.o)
        self.doh.close()
        d = self.newdoh('id1')
        self.assertTrue( isinstance(d.recovered, DObj) )
        self.assertEquals(d.recovered.state, 'third')

        
    def test_new_object_corrupted(self):
        self.test_two_save()

        with open(self.doh.fn_b, 'wb') as f:
            f.write('\0')
            f.flush()
            
        d = self.newdoh('id1')
        self.assertTrue( isinstance(d.recovered, DObj) )
        self.assertEquals(d.recovered.state, 'initial')

        
    def test_old_object_corrupted(self):
        self.test_two_save()

        with open(self.doh.fn_a, 'wb') as f:
            f.write('\0')
            f.flush()
            
        d = self.newdoh('id1')
        self.assertTrue( isinstance(d.recovered, DObj) )
        self.assertEquals(d.recovered.state, 'second')


    def test_unrecoverable_corruption(self):
        self.test_two_save()

        with open(self.doh.fn_a, 'wb') as f:
            f.write('\0')
            f.flush()

        with open(self.doh.fn_b, 'wb') as f:
            f.write('\0')
            f.flush()

        def diehorribly():
            self.newdoh('id1')

        self.assertRaises(durable.UnrecoverableFailure, diehorribly)

########NEW FILE########
__FILENAME__ = test_essential
import sys
import itertools
import os.path
import pickle

#from twisted.trial import unittest
import unittest

this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append( os.path.dirname(this_dir) )

from paxos import essential


PID = essential.ProposalID


class EssentialMessenger (object):

    resolution = None

    def setUp(self):
        self._msgs = list()

    def _append(self, *args):
        self._msgs.append(args)
        
    def send_prepare(self, proposal_id):
        self._append('prepare', proposal_id)

    def send_promise(self, to_uid, proposal_id, proposal_value, accepted_value):
        self._append('promise', to_uid, proposal_id, proposal_value, accepted_value)
        
    def send_accept(self, proposal_id, proposal_value):
        self._append('accept', proposal_id, proposal_value)

    def send_accepted(self, proposal_id, accepted_value):
        self._append('accepted', proposal_id, accepted_value)

    def on_resolution(self, proposal_id, value):
        self.resolution = (proposal_id, value)

    @property
    def last_msg(self):
        return self._msgs[-1]

    def nmsgs(self):
        return len(self._msgs)

    def clear_msgs(self):
        self._msgs = list()

    def am(self, *args):
        self.assertTrue(len(self._msgs) == 1)
        self.assertEquals( self.last_msg, args )
        self._msgs = list()

    def amm(self, msgs):
        self.assertEquals( len(self._msgs), len(msgs) )
        for a, e in itertools.izip(self._msgs, msgs):
            self.assertEquals( a, e )
        self._msgs = list()

    def an(self):
        self.assertTrue( len(self._msgs) == 0 )

    def ae(self, *args):
        self.assertEquals(*args)

    def at(self, *args):
        self.assertTrue(*args)





class EssentialProposerTests (object):

    proposer_factory = None 

    def setUp(self):
        super(EssentialProposerTests, self).setUp()
        
        self.p = self.proposer_factory(self, 'A', 2)


    def al(self, value):
        if hasattr(self.p, 'leader'):
            self.assertEquals( self.p.leader, value )

    def num_promises(self):
        if hasattr(self.p, 'promises_rcvd'):
            return len(self.p.promises_rcvd) # python version
        else:
            return self.p.numPromises() # java version

        
    def test_set_proposal_no_value(self):
        self.ae( self.p.proposed_value, None )
        self.p.set_proposal( 'foo' )
        self.ae( self.p.proposed_value, 'foo' )
        self.an()

        
    def test_set_proposal_with_previous_value(self):
        self.p.set_proposal( 'foo' )
        self.p.set_proposal( 'bar' )
        self.ae( self.p.proposed_value, 'foo' )
        self.an()
        

    def test_prepare(self):
        self.al( False )
        self.ae( self.p.proposer_uid, 'A' )
        self.ae( self.p.quorum_size,  2  )
        self.p.prepare()
        self.am('prepare', PID(1, 'A'))
        self.al( False )


    def test_prepare_two(self):
        self.p.prepare()
        self.am('prepare', PID(1,'A'))
        self.p.prepare()
        self.am('prepare', PID(2,'A'))

        
    def test_prepare_with_promises_rcvd(self):
        self.p.prepare()
        self.am('prepare', PID(1, 'A'))
        self.ae( self.num_promises(), 0 )
        self.p.recv_promise('B', PID(1,'A'), None, None)
        self.ae( self.num_promises(), 1 )
        self.p.prepare()
        self.am('prepare', PID(2,'A'))
        self.ae( self.num_promises(), 0 )

        
    def test_recv_promise_ignore_other_nodes(self):
        self.p.prepare()
        self.am('prepare', PID(1,'A'))
        self.ae( self.num_promises(), 0 )
        self.p.recv_promise( 'B', PID(1,'B'), None, None )
        self.ae( self.num_promises(), 0 )
    
        
    def test_recv_promise_ignore_duplicate_response(self):
        self.p.prepare()
        self.am('prepare', PID(1,'A'))
        self.ae( self.num_promises(), 0 )
        self.p.recv_promise( 'B', PID(1,'A'), None, None )
        self.ae( self.num_promises(), 1 )
        self.p.recv_promise( 'B', PID(1,'A'), None, None )
        self.ae( self.num_promises(), 1 )


    def test_recv_promise_set_proposal_from_null(self):
        self.p.prepare()
        self.clear_msgs()
        self.p.prepare()
        self.am('prepare', PID(2,'A'))
        self.ae( self.p.last_accepted_id, None )
        self.ae( self.p.proposed_value, None )
        self.p.recv_promise( 'B', PID(2,'A'), PID(1,'B'), 'foo' )
        self.ae( self.p.last_accepted_id, PID(1,'B') )
        self.ae( self.p.proposed_value, 'foo' )

        
    def test_recv_promise_override_previous_proposal_value(self):
        self.p.prepare()
        self.p.prepare()
        self.p.prepare()
        self.p.recv_promise( 'B', PID(3,'A'), PID(1,'B'), 'foo' )
        self.clear_msgs()
        self.p.prepare()
        self.am('prepare', PID(4,'A'))
        self.p.recv_promise( 'B', PID(4,'A'), PID(3,'B'), 'bar' )
        self.ae( self.p.last_accepted_id, PID(3,'B') )
        self.ae( self.p.proposed_value, 'bar' )

        
    def test_recv_promise_ignore_previous_proposal_value(self):
        self.p.prepare()
        self.p.prepare()
        self.p.prepare()
        self.p.recv_promise( 'B', PID(3,'A'), PID(1,'B'), 'foo' )
        self.clear_msgs()
        self.p.prepare()
        self.am('prepare', PID(4,'A'))
        self.p.recv_promise( 'B', PID(4,'A'), PID(3,'B'), 'bar' )
        self.ae( self.p.last_accepted_id, PID(3,'B') )
        self.ae( self.p.proposed_value, 'bar' )
        self.p.recv_promise( 'C', PID(4,'A'), PID(2,'B'), 'baz' )
        self.ae( self.p.last_accepted_id, PID(3,'B') )
        self.ae( self.p.proposed_value, 'bar' )



        
class EssentialAcceptorTests (object):

    acceptor_factory = None 

    def setUp(self):
        super(EssentialAcceptorTests, self).setUp()
        
        self.a = self.acceptor_factory(self, 'A', 2)


    def test_recv_prepare_initial(self):
        self.ae( self.a.promised_id    , None)
        self.ae( self.a.accepted_value , None)
        self.ae( self.a.accepted_id    , None)
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)

        
    def test_recv_prepare_duplicate(self):
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)

        
    def test_recv_prepare_override(self):
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.clear_msgs()
        self.a.recv_prepare( 'B', PID(2,'B') )
        self.am('promise', 'B', PID(2,'B'), PID(1,'A'), 'foo')


    def test_recv_accept_request_initial(self):
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.am('accepted', PID(1,'A'), 'foo')

        
    def test_recv_accept_request_promised(self):
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.am('accepted', PID(1,'A'), 'foo')

        
    def test_recv_accept_request_greater_than_promised(self):
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)
        self.a.recv_accept_request('A', PID(5,'A'), 'foo')
        self.am('accepted', PID(5,'A'), 'foo')


    def test_recv_accept_request_less_than_promised(self):
        self.a.recv_prepare( 'A', PID(5,'A') )
        self.am('promise', 'A', PID(5,'A'), None, None)
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.ae( self.a.accepted_value, None )
        self.ae( self.a.accepted_id,    None )
        self.ae( self.a.promised_id,    PID(5,'A'))



class EssentialLearnerTests (object):

    learner_factory = None 

    def setUp(self):
        super(EssentialLearnerTests, self).setUp()
        
        self.l = self.learner_factory(self, 'A', 2)

    def test_basic_resolution(self):
        self.ae( self.l.quorum_size,       2    )
        self.ae( self.l.final_value,       None )
        self.ae( self.l.final_proposal_id, None )

        self.l.recv_accepted( 'A', PID(1,'A'), 'foo' )
        self.ae( self.l.final_value, None )
        self.l.recv_accepted( 'B', PID(1,'A'), 'foo' )
        self.ae( self.l.final_value, 'foo' )
        self.ae( self.l.final_proposal_id, PID(1,'A') )


    def test_ignore_after_resolution(self):
        self.l.recv_accepted( 'A', PID(1,'A'), 'foo' )
        self.ae( self.l.final_value, None )
        self.at( not self.l.complete )
        self.l.recv_accepted( 'B', PID(1,'A'), 'foo' )
        self.ae( self.l.final_value, 'foo' )
        self.ae( self.l.final_proposal_id, PID(1,'A') )

        self.l.recv_accepted( 'A', PID(5,'A'), 'bar' )
        self.l.recv_accepted( 'B', PID(5,'A'), 'bar' )
        self.ae( self.l.final_value, 'foo' )
        self.ae( self.l.final_proposal_id, PID(1,'A') )
        


    def test_ignore_duplicate_messages(self):
        self.l.recv_accepted( 'A', PID(1,'A'), 'foo' )
        self.ae( self.l.final_value, None )
        self.l.recv_accepted( 'A', PID(1,'A'), 'foo' )
        self.ae( self.l.final_value, None )
        self.l.recv_accepted( 'B', PID(1,'A'), 'foo' )
        self.ae( self.l.final_value, 'foo' )
        self.ae( self.l.final_proposal_id, PID(1,'A') )

        
    def test_ignore_old_messages(self):
        self.l.recv_accepted( 'A', PID(5,'A'), 'foo' )
        self.ae( self.l.final_value, None )
        self.l.recv_accepted( 'A', PID(1,'A'), 'bar' )
        self.ae( self.l.final_value, None )
        self.l.recv_accepted( 'B', PID(5,'A'), 'foo' )
        self.ae( self.l.final_value, 'foo' )
        self.ae( self.l.final_proposal_id, PID(5,'A') )


    def test_overwrite_old_messages(self):
        self.l.recv_accepted( 'A', PID(1,'A'), 'bar' )
        self.ae( self.l.final_value, None )
        self.l.recv_accepted( 'B', PID(5,'A'), 'foo' )
        self.ae( self.l.final_value, None )
        self.l.recv_accepted( 'A', PID(5,'A'), 'foo' )
        self.ae( self.l.final_value, 'foo' )
        self.ae( self.l.final_proposal_id, PID(5,'A') )



class TPax(object):
    def __init__(self, messenger, uid, quorum_size):
        self.messenger     = messenger
        self.proposer_uid  = uid
        self.quorum_size   = quorum_size

        
class TProposer (essential.Proposer, TPax):
    pass

class TAcceptor (essential.Acceptor, TPax):
    pass

class TLearner (essential.Learner, TPax):
    pass


class EssentialProposerTester(EssentialProposerTests, EssentialMessenger, unittest.TestCase):
    proposer_factory = TProposer

class EssentialAcceptorTester(EssentialAcceptorTests, EssentialMessenger, unittest.TestCase):
    acceptor_factory = TAcceptor

class EssentialLearnerTester(EssentialLearnerTests, EssentialMessenger, unittest.TestCase):
    learner_factory = TLearner

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_external
import sys
import os.path
import heapq

import unittest

this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append( os.path.dirname(this_dir) )

from paxos import external

import test_practical
from test_practical import PID


class ExternalMessenger (test_practical.PracticalMessenger):

    procs   = 0
    tleader = None

    
    def send_leadership_proclamation(self, pnum):
        self.procs += 1

        
    def on_leadership_acquired(self):
        super(ExternalMessenger,self).on_leadership_acquired()
        self.tleader = 'gained'

        
    def on_leadership_lost(self):
        self.tleader = 'lost'

        
    def on_leadership_change(self, old_uid, new_uid):
        pass
        


        
        
class ExternalTests (object):

    node_factory = None
    
    def create_node(self):
        self.l = self.node_factory(self, 'A', 3)

        

    def test_initial_leader(self):
        self.l = self.node_factory(self, 'A', 3, 'A')
        self.assertTrue(self.l.leader)
        self.assertEquals( self.procs, 0 )

        
    def test_gain_leader(self):
        self.l.set_proposal('foo')
        self.l.prepare()
        
        self.am('prepare', PID(1,'A'))

        self.l.recv_promise('A', PID(1,'A'), None, None)
        self.l.recv_promise('B', PID(1,'A'), None, None)
        
        self.an()
        
        self.l.recv_promise('C', PID(1,'A'), None, None)
        
        self.am('accept', PID(1,'A'), 'foo')

        self.assertEquals( self.tleader, 'gained' )
        self.assertEquals( self.l.leader_uid, 'A' )



    def test_gain_leader_nack(self):
        self.l.set_proposal('foo')
        
        self.l.prepare()

        self.am('prepare', PID(1,'A'))

        self.l.recv_promise('A', PID(1,'A'), None, None)

        self.l.recv_prepare_nack('B', PID(1,'A'), PID(2,'C'))

        self.l.prepare()

        self.am('prepare', PID(3,'A'))
        


    def test_lose_leader(self):
        self.test_gain_leader()

        self.assertEquals( self.l.leader_proposal_id, PID(1,'A') )
        
        self.l.recv_leadership_proclamation( 'B', PID(5,'B') )

        self.assertEquals( self.l.leader_proposal_id, PID(5,'B') )
        self.assertEquals( self.tleader, 'lost' )


    def test_lose_leader_via_nacks(self):
        self.test_gain_leader()

        self.assertEquals( self.l.leader_proposal_id, PID(1,'A') )
        
        self.l.recv_accept_nack( 'B', PID(1,'A'), PID(2,'B') )
        self.l.recv_accept_nack( 'C', PID(1,'A'), PID(2,'B') )

        self.assertEquals( self.tleader, 'gained' )
        self.assertEquals( self.l.leader_proposal_id, PID(1,'A') )

        self.l.recv_accept_nack( 'D', PID(1,'A'), PID(2,'B') )

        self.assertEquals( self.l.leader_proposal_id, None )
        self.assertEquals( self.tleader, 'lost' )


    def test_regain_leader(self):
        self.test_lose_leader()
                
        self.l.prepare()

        self.am('prepare', PID(6,'A'))

        self.l.recv_promise('B', PID(6,'A'), None, None)
        self.l.recv_promise('C', PID(6,'A'), None, None)
        self.an()
        self.l.recv_promise('D', PID(6,'A'), None, None)
        self.am('accept', PID(6,'A'), 'foo')

        self.assertEquals( self.tleader, 'gained' )
        
        

    def test_ignore_old_leader_proclamation(self):
        self.test_lose_leader()

        self.l.recv_leadership_proclamation( 'A', PID(1,'A') )

        self.assertEquals( self.l.leader_proposal_id, PID(5,'B') )


    def test_proposal_id_increment(self):
        self.l.set_proposal('foo')

        self.l.prepare()

        self.am('prepare', PID(1,'A'))

        self.l.recv_promise('A', PID(1,'A'), None, None)
        self.l.recv_promise('B', PID(1,'A'), None, None)
        self.an()
        
        self.l.prepare()
        self.am('prepare', PID(2,'A'))

        self.l.recv_promise('A', PID(2,'A'), None, None)
        self.l.recv_promise('B', PID(2,'A'), None, None)
        self.l.recv_promise('C', PID(2,'A'), None, None)
        
        self.am('accept', PID(2,'A'), 'foo')

        self.assertEquals( self.tleader, 'gained' )


class ExternalTester(ExternalTests, ExternalMessenger, unittest.TestCase):
    node_factory = external.ExternalNode

    def setUp(self):
        super(ExternalTester,self).setUp()
        self.create_node()
        


class TNode(test_practical.AutoSaveMixin, external.ExternalNode):
    pass

class ExternalProposerTester(test_practical.PracticalProposerTests,
                              ExternalMessenger,
                              unittest.TestCase):
    proposer_factory = TNode

    def setUp(self):
        super(ExternalProposerTester,self).setUp()


class ExternalAcceptorTester(test_practical.PracticalAcceptorTests,
                              ExternalMessenger,
                              unittest.TestCase):
    acceptor_factory = TNode

    def setUp(self):
        super(ExternalAcceptorTester,self).setUp()


class ExternalLearnerTester(test_practical.PracticalLearnerTests,
                              ExternalMessenger,
                              unittest.TestCase):
    learner_factory = TNode

    def setUp(self):
        super(ExternalLearnerTester,self).setUp()


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_functional
import sys
import os.path
import heapq

import unittest

this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append( os.path.dirname(this_dir) )

from paxos import functional

import test_practical
from test_practical import PID


class HeartbeatMessenger (test_practical.PracticalMessenger):
        
    def msetup(self):
        self.t       = 1
        self.q       = []
        self.hb      = 0
        self.hbcount = 0
        self.tleader = None


    def tadvance(self, incr=1):
        self.t += incr

        while self.q and self.q[0][0] <= self.t:
            heapq.heappop(self.q)[1]()

            
    def timestamp(self):
        return self.t

    
    def schedule(self, when, func_obj):
        whence = when + self.timestamp()
        heapq.heappush(self.q, (when + self.timestamp(), func_obj))

        
    def send_heartbeat(self, pnum):
        self.hb       = pnum
        self.hbcount += 1

        
    def on_leadership_acquired(self):
        super(HeartbeatMessenger,self).on_leadership_acquired()
        self.tleader = 'gained'

        
    def on_leadership_lost(self):
        self.tleader = 'lost'

        
    def on_leadership_change(self, old_uid, new_uid):
        pass
        


class HNode(functional.HeartbeatNode):
    hb_period       = 2
    liveness_window = 6

    def timestamp(self):
        return self.messenger.timestamp()

        
        
class HeartbeatTests (object):

    node_factory = None
    
    def create_node(self):
        self.l = self.node_factory(self, 'A', 3)

        
    def p(self):
        self.tadvance(1)
        self.l.poll_liveness()

        
    def pre_acq(self, value=None):
        if value:
            self.l.set_proposal(value)
            
        for i in range(1,10):
            self.p()
            self.assertEquals( self.l.proposal_id, None )

        self.an()

        
    def test_initial_wait(self):
        self.pre_acq()
            
        self.p()
        
        self.assertEquals( self.l.proposal_id, PID(1,'A') )



    def test_initial_leader(self):
        self.l.leader_proposal_id = PID(1, 'B')

        self.pre_acq()

        # test_initial_wait() shows that the next call to p() will
        # result in the node attempting to assume leadership by
        # generating a new proposal_id. Reception of this heartbeat
        # should reset the liveness timer and suppress the coup attempt.
        self.l.recv_heartbeat('B', PID(1,'B'))
        
        self.p()
        self.assertEquals( self.l.proposal_id, None )

        
    def test_gain_leader(self):
        self.pre_acq('foo')
        
        self.p()

        self.am('prepare', PID(1,'A'))

        self.l.recv_promise('A', PID(1,'A'), None, None)
        self.l.recv_promise('B', PID(1,'A'), None, None)
        
        self.an()
        
        self.l.recv_promise('C', PID(1,'A'), None, None)
        
        self.am('accept', PID(1,'A'), 'foo')

        self.assertEquals( self.tleader, 'gained' )


    def test_gain_leader_abort(self):
        self.pre_acq('foo')
        
        self.p()

        self.am('prepare', PID(1,'A'))

        self.l.recv_promise('A', PID(1,'A'), None, None)
        self.l.recv_promise('B', PID(1,'A'), None, None)

        self.at( self.l._acquiring )
        self.l.recv_heartbeat( 'B', PID(5,'B') )
        self.at( not self.l._acquiring )
        self.l.acquire_leadership()
        self.an()


    def test_gain_leader_nack(self):
        self.pre_acq('foo')
        
        self.p()

        self.am('prepare', PID(1,'A'))

        self.l.recv_promise('A', PID(1,'A'), None, None)

        self.l.recv_prepare_nack('B', PID(1,'A'), PID(2,'C'))

        self.am('prepare', PID(3,'A'))
        


    def test_lose_leader(self):
        self.test_gain_leader()

        self.assertEquals( self.l.leader_proposal_id, PID(1,'A') )
        
        self.l.recv_heartbeat( 'B', PID(5,'B') )

        self.assertEquals( self.l.leader_proposal_id, PID(5,'B') )
        self.assertEquals( self.tleader, 'lost' )


    def test_lose_leader_via_nacks(self):
        self.test_gain_leader()

        self.assertEquals( self.l.leader_proposal_id, PID(1,'A') )
        
        self.l.recv_accept_nack( 'B', PID(1,'A'), PID(2,'B') )
        self.l.recv_accept_nack( 'C', PID(1,'A'), PID(2,'B') )

        self.assertEquals( self.tleader, 'gained' )
        self.assertEquals( self.l.leader_proposal_id, PID(1,'A') )

        self.l.recv_accept_nack( 'D', PID(1,'A'), PID(2,'B') )

        self.assertEquals( self.l.leader_proposal_id, None )
        self.assertEquals( self.tleader, 'lost' )


    def test_regain_leader(self):
        self.test_lose_leader()
        
        for i in range(1, 7):
            self.p()
            self.an()

        self.p()

        # The 6 here comes from using PID(5,'B') as the heartbeat proposal
        # id the caused the loss of leadership
        #
        self.am('prepare', PID(6,'A'))

        self.l.recv_promise('B', PID(6,'A'), None, None)
        self.l.recv_promise('C', PID(6,'A'), None, None)
        self.an()
        self.l.recv_promise('D', PID(6,'A'), None, None)
        self.am('accept', PID(6,'A'), 'foo')

        self.assertEquals( self.tleader, 'gained' )
        
        

    def test_ignore_old_leader_heartbeat(self):
        self.test_lose_leader()

        self.l.recv_heartbeat( 'A', PID(1,'A') )

        self.assertEquals( self.l.leader_proposal_id, PID(5,'B') )


    def test_pulse(self):
        self.test_gain_leader()

        for i in range(0,8):
            self.tadvance()

        self.assertEquals( self.hbcount, 5 )
        self.assertEquals( self.l.leader_proposal_id, PID(1,'A') )
        self.assertTrue( self.l.leader_is_alive() )


    def test_proposal_id_increment(self):
        self.pre_acq('foo')

        self.p()

        self.am('prepare', PID(1,'A'))

        self.l.recv_promise('A', PID(1,'A'), None, None)
        self.l.recv_promise('B', PID(1,'A'), None, None)
        self.an()
        
        self.p()
        self.am('prepare', PID(2,'A'))

        self.l.recv_promise('A', PID(2,'A'), None, None)
        self.l.recv_promise('B', PID(2,'A'), None, None)
        self.l.recv_promise('C', PID(2,'A'), None, None)
        
        self.am('accept', PID(2,'A'), 'foo')

        self.assertEquals( self.tleader, 'gained' )


class HeartbeatTester(HeartbeatTests, HeartbeatMessenger, unittest.TestCase):
    node_factory = HNode

    def setUp(self):
        super(HeartbeatTester,self).setUp()
        self.msetup()
        self.create_node()
        


class TNode(test_practical.AutoSaveMixin, functional.HeartbeatNode):
    pass

class HeartbeatProposerTester(test_practical.PracticalProposerTests,
                              HeartbeatMessenger,
                              unittest.TestCase):
    proposer_factory = TNode

    def setUp(self):
        super(HeartbeatProposerTester,self).setUp()
        self.msetup()

class HeartbeatAcceptorTester(test_practical.PracticalAcceptorTests,
                              HeartbeatMessenger,
                              unittest.TestCase):
    acceptor_factory = TNode

    def setUp(self):
        super(HeartbeatAcceptorTester,self).setUp()
        self.msetup()

class HeartbeatLearnerTester(test_practical.PracticalLearnerTests,
                              HeartbeatMessenger,
                              unittest.TestCase):
    learner_factory = TNode

    def setUp(self):
        super(HeartbeatLearnerTester,self).setUp()
        self.msetup()

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_practical
import sys
import itertools
import os.path
import pickle

import unittest

this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append( os.path.dirname(this_dir) )

from paxos import practical

import test_essential 
from   test_essential import PID



class PracticalMessenger (test_essential.EssentialMessenger):
    leader_acquired = False

    def send_prepare_nack(self, to_uid, proposal_id, promised_id):
        self._append('prepare_nack', to_uid, proposal_id, promised_id)

    def send_accept_nack(self, to_uid, proposal_id, promised_id):
        self._append('accept_nack', to_uid, proposal_id, promised_id)

    def on_leadership_acquired(self):
        self.leader_acquired = True


        
class PracticalProposerTests (test_essential.EssentialProposerTests):
    
    def set_leader(self):
        self.p.prepare()
        self.am('prepare', PID(1, 'A'))
        self.p.leader = True
        self.ae( self.p.proposed_value, None )

        
    def test_set_proposal_no_previous_value_as_leader(self):
        self.set_leader()
        self.p.set_proposal( 'foo' )
        self.ae( self.p.proposed_value, 'foo' )
        self.am('accept', PID(1,'A'), 'foo')


    def test_resend_accept(self):
        self.set_leader()
        self.p.set_proposal( 'foo' )
        self.ae( self.p.proposed_value, 'foo' )
        self.am('accept', PID(1,'A'), 'foo')
        self.p.resend_accept()
        self.am('accept', PID(1,'A'), 'foo')


    def test_resend_accept_not_active(self):
        self.set_leader()
        self.p.set_proposal( 'foo' )
        self.ae( self.p.proposed_value, 'foo' )
        self.am('accept', PID(1,'A'), 'foo')
        self.p.active = False
        self.p.resend_accept()
        self.an()

        
    def test_set_proposal_no_previous_value_as_leader_not_active(self):
        self.set_leader()
        self.p.active = False
        self.p.set_proposal( 'foo' )
        self.ae( self.p.proposed_value, 'foo' )
        self.an()


    def test_prepare_increment_on_foriegn_promise(self):
        self.p.recv_promise('B', PID(5,'C'), None, None)
        self.p.prepare()
        self.am('prepare', PID(6,'A'))

        
    def test_prepare_increment_on_foriegn_promise_not_active(self):
        self.p.active = False
        self.p.recv_promise('B', PID(5,'C'), None, None)
        self.p.prepare()
        self.an()


    def test_preare_no_increment(self):
        self.p.prepare()
        self.am('prepare', PID(1,'A'))
        self.ae( self.num_promises(), 0 )
        self.p.recv_promise('B', PID(1,'A'), None, None)
        self.ae( self.num_promises(), 1 )
        self.p.prepare(False)
        self.am('prepare', PID(1,'A'))
        self.ae( self.num_promises(), 1 )
        
        
    def test_recv_promise_ignore_when_leader(self):
        self.p.prepare()
        self.am('prepare', PID(1,'A'))
        self.ae( self.num_promises(), 0 )
        self.p.leader = True
        self.p.recv_promise( 'B', PID(1,'A'), None, None )
        self.ae( self.num_promises(), 0 )

        
    def test_recv_promise_acquire_leadership_with_proposal(self):
        self.p.set_proposal('foo')
        self.p.prepare()
        self.am('prepare', PID(1,'A'))
        self.ae( self.num_promises(), 0 )
        self.p.recv_promise( 'B', PID(1,'A'), None, None )
        self.ae( self.num_promises(), 1 )
        self.at(not self.p.leader)
        self.at(not self.leader_acquired)
        self.p.recv_promise( 'C', PID(1,'A'), None, None )
        self.ae( self.num_promises(), 2 )
        self.at(self.p.leader)
        self.at(self.leader_acquired)
        self.am('accept', PID(1,'A'), 'foo')


    def test_recv_promise_acquire_leadership_with_proposal_not_active(self):
        self.p.set_proposal('foo')
        self.p.prepare()
        self.am('prepare', PID(1,'A'))
        self.ae( self.num_promises(), 0 )
        self.p.recv_promise( 'B', PID(1,'A'), None, None )
        self.ae( self.num_promises(), 1 )
        self.at(not self.p.leader)
        self.at(not self.leader_acquired)
        self.p.active = False
        self.p.recv_promise( 'C', PID(1,'A'), None, None )
        self.ae( self.num_promises(), 2 )
        self.at(self.p.leader)
        self.at(self.leader_acquired)
        self.an()


    def test_recv_promise_acquire_leadership_without_proposal(self):
        self.p.prepare()
        self.am('prepare', PID(1,'A'))
        self.ae( self.num_promises(), 0 )
        self.p.recv_promise( 'B', PID(1,'A'), None, None )
        self.ae( self.num_promises(), 1 )
        self.at(not self.p.leader)
        self.at(not self.leader_acquired)
        self.p.recv_promise( 'C', PID(1,'A'), None, None )
        self.ae( self.num_promises(), 2 )
        self.at(self.p.leader)
        self.at(self.leader_acquired)
        self.an()

        
    def test_resend_accept(self):
        self.p.resend_accept()
        self.an()
        self.set_leader()
        self.p.resend_accept()
        self.an()
        self.p.set_proposal( 'foo' )
        self.ae( self.p.proposed_value, 'foo' )
        self.am('accept', PID(1,'A'), 'foo')
        self.p.resend_accept()
        self.am('accept', PID(1,'A'), 'foo')


    def test_observe_proposal(self):
        self.p.prepare()
        self.am('prepare', PID(1,'A'))
        self.p.observe_proposal( 'B', PID(5,'B') )
        self.p.prepare()
        self.am('prepare', PID(6,'A'))


    def test_recv_prepare_nack(self):
        self.p.prepare()
        self.am('prepare', PID(1,'A'))
        self.p.recv_prepare_nack( 'B', PID(1,'A'), PID(5,'B') )
        self.p.prepare()
        self.am('prepare', PID(6,'A'))



class PracticalAcceptorTests (test_essential.EssentialAcceptorTests):

    def recover(self):
        prev = self.a
        self.a = self.acceptor_factory(self, 'A', 2)
        self.a.recover(prev.promised_id, prev.accepted_id, prev.accepted_value)

    def test_recv_prepare_nack(self):
        self.a.recv_prepare( 'A', PID(2,'A') )
        self.am('promise', 'A', PID(2,'A'), None, None)
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('prepare_nack', 'A', PID(1,'A'), PID(2,'A'))


    def test_recv_prepare_nack_not_active(self):
        self.a.recv_prepare( 'A', PID(2,'A') )
        self.am('promise', 'A', PID(2,'A'), None, None)
        self.a.active = False
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.an()


    def test_recv_accept_request_less_than_promised(self):
        super(PracticalAcceptorTests, self).test_recv_accept_request_less_than_promised()
        self.am('accept_nack', 'A', PID(1,'A'), PID(5,'A'))


    def test_recv_accept_request_less_than_promised(self):
        self.a.recv_prepare( 'A', PID(5,'A') )
        self.am('promise', 'A', PID(5,'A'), None, None)
        self.a.active = False
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.ae( self.a.accepted_value, None )
        self.ae( self.a.accepted_id,    None )
        self.ae( self.a.promised_id,    PID(5,'A'))
        self.an()


    def test_recv_prepare_initial_not_active(self):
        self.ae( self.a.promised_id    , None)
        self.ae( self.a.accepted_value , None)
        self.ae( self.a.accepted_id    , None)
        self.a.active = False
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.an()

        
    def test_recv_prepare_duplicate_not_active(self):
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)
        self.a.active = False
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.an()


    def test_recv_accept_request_duplicate(self):
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.am('accepted', PID(1,'A'), 'foo')
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.am('accepted', PID(1,'A'), 'foo')

        
    def test_recv_accept_request_duplicate_not_active(self):
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.am('accepted', PID(1,'A'), 'foo')
        self.a.active = False
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.an()


    def test_recv_accept_request_initial_not_active(self):
        self.a.active = False
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.an()

        
    def test_recv_accept_request_promised_not_active(self):
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)
        self.a.active = False
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.an()


    # --- Durability Tests ---

    def test_durable_recv_prepare_duplicate(self):
        self.a.recv_prepare( 'A', PID(2,'A') )
        self.am('promise', 'A', PID(2,'A'), None, None)
        self.recover()
        self.a.recv_prepare( 'A', PID(2,'A') )
        self.am('promise', 'A', PID(2,'A'), None, None)

        
    def test_durable_recv_prepare_override(self):
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.clear_msgs()
        self.a.recv_prepare( 'B', PID(2,'B') )
        self.am('promise', 'B', PID(2,'B'), PID(1,'A'), 'foo')


    def test_durable_ignore_prepare_override_until_persisted(self):
        self.a.auto_save = False
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.an()
        self.a.recv_prepare( 'B', PID(2,'B') )
        self.an()
        self.a.persisted()
        self.am('promise', 'A', PID(1,'A'), None, None)


    def test_durable_recv_accept_request_promised(self):
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)
        self.recover()
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.am('accepted', PID(1,'A'), 'foo')

        
    def test_durable_recv_accept_request_greater_than_promised(self):
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)
        self.recover()
        self.a.recv_accept_request('A', PID(5,'A'), 'foo')
        self.am('accepted', PID(5,'A'), 'foo')


    def test_durable_ignore_new_accept_request_until_persisted(self):
        self.a.recv_prepare( 'A', PID(1,'A') )
        self.am('promise', 'A', PID(1,'A'), None, None)
        self.a.auto_save = False
        self.a.recv_accept_request('A', PID(5,'A'), 'foo')
        self.an()
        self.a.recv_accept_request('A', PID(6,'A'), 'foo')
        self.an()
        self.a.persisted()
        self.am('accepted', PID(5,'A'), 'foo')


    def test_durable_recv_accept_request_less_than_promised(self):
        self.a.recv_prepare( 'A', PID(5,'A') )
        self.am('promise', 'A', PID(5,'A'), None, None)
        self.a.recv_accept_request('A', PID(1,'A'), 'foo')
        self.am('accept_nack', 'A', PID(1,'A'), PID(5,'A'))
        


class PracticalLearnerTests (test_essential.EssentialLearnerTests):

    def test_basic_resolution_final_acceptors(self):
        self.ae( self.l.final_acceptors, None )
        self.l.recv_accepted( 'A', PID(1,'A'), 'foo' )
        self.l.recv_accepted( 'B', PID(1,'A'), 'foo' )
        self.ae( self.l.final_acceptors, set(['A','B']) )

    def test_add_to_final_acceptors_after_resolution(self):
        self.test_basic_resolution_final_acceptors()
        self.l.recv_accepted( 'C', PID(1,'A'), 'foo' )
        self.ae( self.l.final_acceptors, set(['A','B', 'C']) )

    def test_add_to_final_acceptors_after_resolution_with_pid_mismatch(self):
        self.test_basic_resolution_final_acceptors()
        self.l.recv_accepted( 'C', PID(0,'A'), 'foo' )
        self.ae( self.l.final_acceptors, set(['A','B', 'C']) )
        


    
class NodeTester(PracticalMessenger, unittest.TestCase):

    def test_change_quorum_size(self):
        n = practical.Node(self, 'A', 2)
        self.ae(n.quorum_size, 2)
        n.change_quorum_size(3)
        self.ae(n.quorum_size, 3)
        


class AutoSaveMixin(object):

    auto_save = True
    
    def recv_prepare(self, from_uid, proposal_id):
        super(AutoSaveMixin, self).recv_prepare(from_uid, proposal_id)
        if self.persistance_required and self.auto_save:
            self.persisted()

    def recv_accept_request(self, from_uid, proposal_id, value):
        super(AutoSaveMixin, self).recv_accept_request(from_uid, proposal_id, value)
        if self.persistance_required and self.auto_save:
            self.persisted()


    
class TNode(AutoSaveMixin, practical.Node):
    pass



class PracticalProposerTester(PracticalProposerTests, PracticalMessenger, unittest.TestCase):
    proposer_factory = TNode

class PracticalAcceptorTester(PracticalAcceptorTests, PracticalMessenger, unittest.TestCase):
    acceptor_factory = TNode

class PracticalLearnerTester(PracticalLearnerTests, PracticalMessenger, unittest.TestCase):
    learner_factory = TNode

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
